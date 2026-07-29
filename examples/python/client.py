import ctypes
import json
import math
import os
import queue
import random
import sys
import time
import tracemalloc

import websocket

try:
    import psutil as _psutil
except ImportError:
    _psutil = None

from utils import decode_rust_str, load_sim_config, setup_mist_path

setup_mist_path()
from mist import MistNode, MistTransform, EVENT_RAW, EVENT_NEIGHBORS, EVENT_LEAVE, EVENT_JOIN, EVENT_AOI_NODES, DELIVERY_UNRELIABLE, default_config

_ARG_CONFIG_MAP = {
    'max_connection_count': 'maxConnectionCount',
    'aoi_range': 'aoiRange',
    'direction_threshold': 'directionThreshold',
    'density_resolution': 'densityResolution',
}


def _world_size(args, default=1000.0):
    return getattr(args, "world_size", default)


class MistClient:
    def __init__(self, args):
        self.args = args
        self.node = None
        self.event_queue = queue.Queue(maxsize=20000)
        self.log_sender = None

        self._headless = getattr(args, 'headless', False)

        self.id = getattr(args, 'id', None)
        if not self.id or self.id == "bot-default":
            suffix = f"{os.getpid()}-{random.randint(100, 999)}"
            self.id = f"bot-{suffix}"
            if hasattr(args, 'id'):
                args.id = self.id

        self.local_transform = MistTransform(is_owner=True)
        world_size = _world_size(args)
        self.local_transform.position = [
            random.uniform(0, max(0.0, world_size)),
            random.uniform(0, max(0.0, world_size)),
            random.uniform(0, max(0.0, world_size)),
        ]

        min_speed = getattr(args, 'min_speed', 0.0)
        if min_speed is None:
            min_speed = 0.0
        max_speed = getattr(args, 'max_speed', 2.0)
        if max_speed is None:
            max_speed = 0.0
        if max_speed < min_speed:
            min_speed, max_speed = max_speed, min_speed

        self.speed = min_speed
        if max_speed > min_speed:
            self.speed = random.uniform(min_speed, max_speed)

        azimuth = random.uniform(0, 2 * math.pi)
        polar = math.acos(1.0 - 2.0 * random.random())
        self.velocity_vec = [
            math.sin(polar) * math.cos(azimuth) * self.speed,
            math.cos(polar) * self.speed,
            math.sin(polar) * math.sin(azimuth) * self.speed,
        ]

        self.peers = {}
        self.neighbor_nodes = {}
        self.connected_nodes = set()
        self.connected_last_seen = {}
        self.visible_nodes = set()

        self.last_broadcast_time = 0
        self.last_eval_time = 0
        self.last_eval_recv_poll = 0
        self.last_diag_time = 0
        self.send_sequence = 0
        self.last_time = time.time()
        self._last_rust_diag = {}

        self.stale_connected_seconds = 15.0
        self.diag_interval_seconds = 30.0
        self.eval_recv_poll_interval_sec = 0.05
        self.eval_recv_max_per_tick = 32
        self.max_events_per_tick = 3000

        self.eval_ws = None
        self.eval_next_reconnect_time = 0.0
        self.eval_reconnect_interval_sec = 5.0

        self.max_conn = 30
        self.aoi_nodes = {}  # {node_id: {"x": float, "y": float, "z": float}}

    @staticmethod
    def _make_3d_pos(x, y, z):
        return {"x": x, "y": y, "z": z}

    def on_log(self, level, data_ptr, length):
        msg = ctypes.string_at(data_ptr, length).decode('utf-8', errors='ignore')
        if self.log_sender:
            self.log_sender.send_rust_log(level, msg)
        if "[CS]" in msg:
            if not self._headless:
                print(f"[RUST-GUI] {msg}")
        else:
            print(f"[RUST] {msg}")

    def log(self, level: str, message: str, **fields):
        """Send a Python-side log entry to the gRPC log server (no-op if not configured)."""
        if self.log_sender:
            self.log_sender.send_log(level, message, source="python", **fields)

    def on_event(self, event_type, from_ptr, from_len, data_ptr, data_len):
        from_id = decode_rust_str(from_ptr, from_len)
        data = ctypes.string_at(data_ptr, data_len)
        event = (event_type, from_id, data)
        try:
            self.event_queue.put_nowait(event)
        except queue.Full:
            self.log("WARN", "event_queue_full", qsize=self.event_queue.qsize())
            try: self.event_queue.get_nowait()
            except queue.Empty: pass
            try: self.event_queue.put_nowait(event)
            except queue.Full: pass

    def start(self):
        tracemalloc.start()

        signaling_raw = getattr(self.args, 'signaling', None)
        signaling_url = signaling_raw.encode('utf-8') if signaling_raw and signaling_raw.strip() else None

        # Peers find each other only if they share these two values, so they double
        # as this demo's namespace. Change them for your own app -- anyone who knows
        # the pair can join.
        demo_config = default_config()
        demo_config["signaling"]["nostr"]["inviteSalt"] = "mistlib-example-python"
        demo_config["signaling"]["nostr"]["inviteCode"] = "public-demo"
        self.node = (
            MistNode(self.args.id, signaling_url=signaling_url)
            if signaling_url
            else MistNode(self.args.id, config=demo_config)
        )
        final_rust_config = {}
        rust_config_path = getattr(self.args, 'rust_config_path', None)
        if rust_config_path:
            final_rust_config = load_sim_config(rust_config_path, self._headless, normalize_keys=False)
        for attr, key in _ARG_CONFIG_MAP.items():
            if hasattr(self.args, attr):
                final_rust_config[key] = getattr(self.args, attr)
        if hasattr(self.args, 'density_encoding') and self.args.density_encoding:
            final_rust_config["densityEncoding"] = self.args.density_encoding
        if final_rust_config:
            try:
                self.node.set_config(final_rust_config)
                if not self._headless:
                    print(f"[Config] Applied Rust engine config: {final_rust_config}")
            except Exception as e:
                if not self._headless:
                    print(f"[Config] Failed to apply Rust config: {e}")

        log_server = getattr(self.args, 'log_server', None)
        if log_server and log_server.strip():
            try:
                _log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
                if _log_dir not in sys.path:
                    sys.path.insert(0, _log_dir)
                from log_sender import LogSender
                self.log_sender = LogSender(self.id, log_server)
                ok = self.log_sender.wait_connected(timeout=3.0)
                status = "Connected" if ok else "FAILED to connect"
                print(f"[LogSender] {status}: {log_server}")
            except Exception as e:
                if not self._headless:
                    print(f"[LogSender] Disabled: {e}")

        self.node.register_callbacks(self.on_log, self.on_event)
        self.node.init()
        self.node.join_room(self.args.room)
        try:
            _cfg = json.loads(self.node.get_config())
            self.max_conn = _cfg.get("maxConnectionCount", 30)
        except Exception:
            pass

        self.connect_eval_server(time.time())
        self.log("INFO", "node started", room=self.args.room, signaling=signaling_raw or "")

    def connect_eval_server(self, now_ts):
        eval_server = getattr(self.args, 'eval_server', None)
        if not eval_server or not eval_server.strip() or "your-eval-server" in eval_server:
            return

        _reconnect = self.last_eval_time > 0
        try:
            self.eval_ws = websocket.create_connection(eval_server, timeout=3)
            self.eval_ws.settimeout(0.01)
            config_data = json.loads(self.node.get_config())
            config_data["visibleCount"] = getattr(self.args, "visible_count", 5)
            world_size = _world_size(self.args)
            config_data["worldSize"] = world_size
            config_data["worldWidth"] = world_size
            config_data["worldHeight"] = world_size
            config_data["worldDepth"] = world_size
            if getattr(self.args, "min_speed", None) is not None:
                config_data["minSpeed"] = self.args.min_speed
            if getattr(self.args, "max_speed", None) is not None:
                config_data["maxSpeed"] = self.args.max_speed
            settings_msg = {
                "type": "nodeSettings",
                "payload": {
                    "nodeId": self.args.id,
                    "config": config_data
                }
            }
            self.eval_ws.send(json.dumps(settings_msg))
            if not self._headless:
                _gap = now_ts - self.last_eval_time if self.last_eval_time else 0
                label = f"Reconnected (gap={_gap:.1f}s)" if _reconnect else "Connected"
                print(f"[Eval] {label}: {eval_server}")
        except Exception as e:
            self.eval_next_reconnect_time = now_ts + self.eval_reconnect_interval_sec
            if not self._headless:
                print(f"[Eval] Connect failed: {e}")
            self.eval_ws = None

    def tick(self):
        _tick_start = time.time()
        current_time = _tick_start
        dt = current_time - self.last_time
        self.last_time = current_time

        if self.eval_ws is None and getattr(self.args, 'eval_server', None) and current_time >= self.eval_next_reconnect_time:
            self.connect_eval_server(current_time)

        if getattr(self.args, 'auto', False):
            prev_pos = list(self.local_transform.position)
            self.local_transform.position[0] += self.velocity_vec[0] * dt
            self.local_transform.position[1] += self.velocity_vec[1] * dt
            self.local_transform.position[2] += self.velocity_vec[2] * dt

            world_size = _world_size(self.args)
            if self.local_transform.position[0] < 0 or self.local_transform.position[0] > world_size:
                self.velocity_vec[0] *= -1
                self.local_transform.position[0] = max(0, min(world_size, self.local_transform.position[0]))
            if self.local_transform.position[1] < 0 or self.local_transform.position[1] > world_size:
                self.velocity_vec[1] *= -1
                self.local_transform.position[1] = max(0, min(world_size, self.local_transform.position[1]))
            if self.local_transform.position[2] < 0 or self.local_transform.position[2] > world_size:
                self.velocity_vec[2] *= -1
                self.local_transform.position[2] = max(0, min(world_size, self.local_transform.position[2]))

            self.local_transform.velocity = [
                (self.local_transform.position[0] - prev_pos[0]) / dt if dt > 0 else 0,
                (self.local_transform.position[1] - prev_pos[1]) / dt if dt > 0 else 0,
                (self.local_transform.position[2] - prev_pos[2]) / dt if dt > 0 else 0,
            ]

        self._update_aoi_nodes()
        sync_interval = max(self.local_transform.calculate_sync_interval(self.local_transform.position), getattr(self.args, 'min_sync_interval', 0.2))
        if current_time - self.last_broadcast_time > sync_interval:
            self.node.update_position(
                self.local_transform.position[0],
                self.local_transform.position[1],
                self.local_transform.position[2],
            )
            payload = json.dumps({
                "type": "sync_pos",
                "position": {
                    "x": self.local_transform.position[0],
                    "y": self.local_transform.position[1],
                    "z": self.local_transform.position[2],
                },
                "velocity": {
                    "x": self.local_transform.velocity[0],
                    "y": self.local_transform.velocity[1],
                    "z": self.local_transform.velocity[2],
                },
                "time": sync_interval,
                "sequence": self.send_sequence
            }).encode('utf-8')
            for nid in self.visible_nodes:
                self.node.send_message(nid, payload, DELIVERY_UNRELIABLE)
            self.send_sequence = (self.send_sequence + 1) & 0xFFFF
            self.last_broadcast_time = current_time

        _t0 = time.time()
        self._poll_eval_messages(current_time)
        _poll_ms = (time.time() - _t0) * 1000

        eval_interval = getattr(self.args, 'eval_interval', 3.0)
        if self.eval_ws and current_time - self.last_eval_time > eval_interval:
            _since_last = current_time - self.last_eval_time if self.last_eval_time else 0
            _t1 = time.time()
            self._report_node_state(current_time)
            _report_ms = (time.time() - _t1) * 1000
            _tick_ms = (time.time() - _tick_start) * 1000
            _ts = time.strftime("%H:%M:%S")
            if not self._headless:
                print(f"[Timing] {_ts} tick={_tick_ms:.1f}ms poll={_poll_ms:.1f}ms report={_report_ms:.1f}ms since_last_eval={_since_last:.1f}s")

        self._process_events(current_time)
        for p in self.peers.values():
            p.update_interpolation(dt)
        self._cleanup_stale(current_time)
        self._run_diagnostics(current_time)

    def _cleanup_stale(self, current_time):
        self.peers = {k: v for k, v in self.peers.items() if current_time - v.last_seen < 2.0}
        for nid in [nid for nid, n in self.neighbor_nodes.items() if current_time - n.get("last_seen", 0) > 5.0]:
            del self.neighbor_nodes[nid]
        stale = [nid for nid in self.connected_nodes if (current_time - self.connected_last_seen.get(nid, 0)) > self.stale_connected_seconds]
        for nid in stale:
            self.connected_nodes.remove(nid)
            self.connected_last_seen.pop(nid, None)

    def _run_diagnostics(self, current_time):
        if current_time - self.last_diag_time < self.diag_interval_seconds:
            return
        if not self._headless:
            mem_str = ""
            if _psutil:
                mem_str = f" mem={_psutil.Process(os.getpid()).memory_info().rss / (1024*1024):.1f}MB"
            _rp = self._last_rust_diag.get('diagPeers', '?')
            _rc = self._last_rust_diag.get('diagConnectionStates', '?')
            _rpc = self._last_rust_diag.get('diagPendingCandidates', '?')
            print(f"[Diag] conn={len(self.connected_nodes)} peers={len(self.peers)} neighbors={len(self.neighbor_nodes)} queue={self.event_queue.qsize()}{mem_str} rust_peers={_rp} conn_states={_rc} pending_cands={_rpc}")

            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')
            total_py_mem = sum(stat.size for stat in top_stats) / (1024*1024)
            print(f"[Diag] Python Alloc: {total_py_mem:.1f}MB | Top 2: {top_stats[0]} / {top_stats[1]}")
        self.last_diag_time = current_time

    def _update_aoi_nodes(self):
        visible_count = getattr(self.args, 'visible_count', 5)
        px, py, pz = self.local_transform.position

        candidates = []
        for nid, node in self.aoi_nodes.items():
            dx = node["x"] - px
            dy = node["y"] - py
            dz = node.get("z", 0.0) - pz
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            candidates.append((nid, d))

        candidates.sort(key=lambda item: (item[1], item[0]))
        limit = min(self.max_conn, max(1, visible_count))
        self.visible_nodes = {nid for nid, _ in candidates[:limit]}

    def _poll_eval_messages(self, current_time):
        if not self.eval_ws or (current_time - self.last_eval_recv_poll) < self.eval_recv_poll_interval_sec:
            return
        try:
            recv_count = 0
            _recv_start = time.time()
            while recv_count < self.eval_recv_max_per_tick:
                recv_raw = self.eval_ws.recv()
                if not recv_raw: break
                if isinstance(recv_raw, bytes): recv_raw = recv_raw.decode("utf-8", errors="ignore")
                recv_msg = json.loads(recv_raw)
                if recv_msg.get("type") == "networkPartitionCheck":
                    recv_payload = recv_msg.get("payload", {})
                    self.eval_ws.send(json.dumps({
                        "type": "networkPartitionCheckResponse",
                        "payload": {"id": recv_payload.get("id", ""), "nodeId": self.args.id}
                    }))
                recv_count += 1
        except websocket.WebSocketTimeoutException: pass
        except Exception as _e:
            if not self._headless:
                print(f"[EvalRecv] Exception: {_e}")
            self.log("WARN", "eval_recv_error", error=str(_e))
            self.eval_ws = None
            self.eval_next_reconnect_time = current_time + self.eval_reconnect_interval_sec
        else:
            _recv_ms = (time.time() - _recv_start) * 1000
            if recv_count > 0 and not self._headless:
                print(f"[EvalRecv] {recv_count} msgs in {_recv_ms:.1f}ms")
        self.last_eval_recv_poll = current_time

    def _report_node_state(self, current_time):
        try:
            _t_gs = time.time()
            _raw_stats = self.node.get_stats()
            rust_stats = json.loads(_raw_stats)
            _gs_ms = (time.time() - _t_gs) * 1000
            is_dict = isinstance(rust_stats, dict)

            if not self._headless:
                _dp = rust_stats.get("diagPeers", "?") if is_dict else "?"
                _dc = rust_stats.get("diagConnectionStates", "?") if is_dict else "?"
                _dpc = rust_stats.get("diagPendingCandidates", "?") if is_dict else "?"
                _slow = " (SLOW)" if _gs_ms > 10 else ""
                print(f"[EvalSend] get_stats={_gs_ms:.1f}ms{_slow} rust_peers={_dp} conn_states={_dc} pending_cands={_dpc}")
                if _dp == "?":
                    _serde_err = rust_stats.get("diagSerdeError", "") if is_dict else ""
                    _nan_count = rust_stats.get("diagNanCount", 0) if is_dict else 0
                    _keys = list(rust_stats.keys()) if is_dict else str(type(rust_stats))
                    print(f"[EvalSend] DEBUG: serde_error={_serde_err} nan_count={_nan_count} keys={_keys} raw_len={len(_raw_stats)}")

            if is_dict:
                self._last_rust_diag = rust_stats
            eval_stats = dict(rust_stats) if is_dict else {}

            if _psutil:
                eval_stats["pythonMemoryMb"] = round(_psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 2)

            eval_stats.pop("nodes", None)
            rust_sctp_by_node = {}
            for node_stat in (rust_stats.get("nodes", []) if is_dict else []):
                if isinstance(node_stat, dict):
                    nid = node_stat.get("id")
                    if nid: rust_sctp_by_node[nid] = node_stat.get("sctpStats", {})

            eval_node_ids = set(self.neighbor_nodes.keys())
            eval_node_ids.update(self.connected_nodes)
            eval_node_ids.update(self.aoi_nodes.keys())

            eval_nodes = []
            for nid in eval_node_ids:
                if nid == self.args.id: continue
                neighbor = self.neighbor_nodes.get(nid) or self.aoi_nodes.get(nid)
                pos_x = neighbor["x"] if neighbor else 0
                pos_y = neighbor["y"] if neighbor else 0
                pos_z = neighbor.get("z", 0) if neighbor else 0
                sctp = rust_sctp_by_node.get(nid, {})
                sctp_state = sctp.get("state", "")

                if nid in self.visible_nodes: state = "visible"
                elif nid in self.connected_nodes or sctp_state in ("connected", "connecting", "reconnecting"): state = "connected"
                else: state = "disconnected"

                eval_nodes.append({
                    "id": nid, "position": self._make_3d_pos(pos_x, pos_y, pos_z), "state": state, "sctpStats": sctp
                })

            _t_send = time.time()
            self.eval_ws.send(json.dumps({
                "type": "nodeState",
                "payload": {
                    "node": {
                        "id": self.args.id,
                        "position": self._make_3d_pos(
                            self.local_transform.position[0],
                            self.local_transform.position[1],
                            self.local_transform.position[2],
                        ),
                        "state": "visible",
                    },
                    "nodes": eval_nodes, "stats": eval_stats
                }
            }))
            _send_ms = (time.time() - _t_send) * 1000
            if not self._headless and _send_ms > 50:
                print(f"[EvalSend] ws.send took {_send_ms:.1f}ms (SLOW)")
            self.last_eval_time = current_time
        except Exception as _e:
            if not self._headless:
                print(f"[EvalSend] Exception: {_e}")
            self.log("WARN", "eval_send_error", error=str(_e))
            self.eval_ws = None
            self.eval_next_reconnect_time = current_time + self.eval_reconnect_interval_sec

    def _process_events(self, current_time):
        processed = 0
        while not self.event_queue.empty() and processed < self.max_events_per_tick:
            etype, from_id, data_bytes = self.event_queue.get_nowait()
            processed += 1
            if etype == EVENT_RAW:
                try:
                    data = json.loads(data_bytes.decode('utf-8'))
                    if data.get("type") == "sync_pos" and from_id != self.args.id:
                        self.connected_last_seen[from_id] = current_time
                        if from_id not in self.peers:
                            self.peers[from_id] = MistTransform(is_owner=False)
                            self.peers[from_id].position = [
                                data["position"]["x"],
                                data["position"]["y"],
                                data["position"].get("z", 0.0),
                            ]
                        self.peers[from_id].receive_location(data, current_time)
                        self.peers[from_id].last_seen = current_time
                        if from_id in self.neighbor_nodes: self.neighbor_nodes[from_id]["last_seen"] = current_time
                except Exception: pass
            elif etype == EVENT_NEIGHBORS:
                try:
                    nodes = json.loads(data_bytes.decode('utf-8'))
                    received_ids = set()
                    for n in nodes:
                        nid = n["id"]
                        if nid != self.args.id:
                            received_ids.add(nid)
                            self.neighbor_nodes[nid] = {
                                "x": n["x"],
                                "y": n["y"],
                                "z": n.get("z", 0.0),
                                "last_seen": current_time,
                            }
                            if nid in self.connected_nodes: self.connected_last_seen[nid] = current_time
                    to_remove = [nid for nid in self.neighbor_nodes if nid not in received_ids]
                    for nid in to_remove: del self.neighbor_nodes[nid]
                except Exception: pass
            elif etype == EVENT_JOIN:
                self.connected_nodes.add(from_id)
                self.connected_last_seen[from_id] = current_time
                self.log("INFO", "peer_connected", peer=from_id, total_connected=len(self.connected_nodes))
            elif etype == EVENT_LEAVE:
                if from_id in self.connected_nodes: self.connected_nodes.remove(from_id)
                self.connected_last_seen.pop(from_id, None)
                self.peers.pop(from_id, None)
                self.neighbor_nodes.pop(from_id, None)
                self.log("INFO", "peer_disconnected", peer=from_id, total_connected=len(self.connected_nodes))
            elif etype == EVENT_AOI_NODES:
                try:
                    nodes = json.loads(data_bytes.decode('utf-8'))
                    self.aoi_nodes = {n["id"]: n for n in nodes if n["id"] != self.args.id}
                except Exception: pass

    def leave_room(self):
        if self.node: self.node.leave_room()
        if self.eval_ws:
            try: self.eval_ws.close()
            except Exception: pass
        if self.log_sender:
            self.log_sender.stop()

    def send_raw_event(self, from_id, data_bytes):
        """Manually inject an event (useful for some CLI testing)"""
        self.event_queue.put((EVENT_RAW, from_id, data_bytes))
