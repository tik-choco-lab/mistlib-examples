"""
gRPC log sender for MistLib.

Forwards log entries (from Python or Rust) to a LogService gRPC server
defined in log.proto. Runs a background thread that streams entries from
an internal queue so callers never block.

Usage:
    sender = LogSender(node_id="my-node", server_addr="localhost:50051")
    sender.send_log("INFO", "hello from python", source="python")
    sender.stop()

Requires:
    pip install grpcio grpcio-tools
"""

import os
import subprocess
import sys
import queue
import threading
import time
from datetime import datetime, timezone, timedelta

_JST = timezone(timedelta(hours=9))

_PROTO_DIR = os.path.dirname(os.path.abspath(__file__))

_LEVEL_MAP = {0: "DEBUG", 1: "INFO", 2: "WARN", 3: "ERROR"}


def _ensure_proto():
    """Generate log_pb2.py / log_pb2_grpc.py from log.proto if missing."""
    if os.path.exists(os.path.join(_PROTO_DIR, "log_pb2.py")):
        return
    proto_file = os.path.join(_PROTO_DIR, "log.proto")
    if not os.path.exists(proto_file):
        raise FileNotFoundError(f"log.proto not found at {proto_file}")
    try:
        subprocess.run(
            [
                sys.executable, "-m", "grpc_tools.protoc",
                f"-I{_PROTO_DIR}",
                f"--python_out={_PROTO_DIR}",
                f"--grpc_python_out={_PROTO_DIR}",
                proto_file,
            ],
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to generate proto stubs: {e.stderr.decode()}\n"
            "Make sure grpcio-tools is installed: pip install grpcio-tools"
        ) from e


_ensure_proto()

# These imports work after _ensure_proto() runs.
sys.path.insert(0, _PROTO_DIR)
import log_pb2        # type: ignore  # noqa: E402
import log_pb2_grpc  # type: ignore  # noqa: E402


class LogSender:
    """Thread-safe gRPC log sender with automatic reconnect."""

    def __init__(self, node_id: str, server_addr: str = "localhost:50051"):
        self.node_id = node_id
        self.server_addr = server_addr
        self._queue: queue.Queue = queue.Queue(maxsize=2000)
        self._stop = threading.Event()
        self._connect_done = threading.Event()
        self._connect_ok = False
        self._thread = threading.Thread(target=self._run, daemon=True, name="log-sender")
        self._thread.start()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_log(self, level: str, message: str, trace_id: str = "", **fields):
        """Enqueue a log entry for async delivery. Non-blocking; drops on full queue."""
        try:
            import grpc  # noqa: F401 (check import here to fail early)
        except ImportError:
            return
        entry = log_pb2.LogEntry(
            node_id=self.node_id,
            trace_id=trace_id,
            level=level,
            message=message,
            timestamp=datetime.now(_JST).isoformat(timespec='milliseconds'),
            fields={k: str(v) for k, v in fields.items()},
        )
        try:
            self._queue.put_nowait(entry)
        except queue.Full:
            pass  # drop oldest-first strategy is not worth the lock overhead

    def send_rust_log(self, level_int: int, message: str):
        """Convenience wrapper for Rust log callbacks (level is an int 0-3)."""
        self.send_log(_LEVEL_MAP.get(level_int, "INFO"), message, source="rust")

    def wait_connected(self, timeout: float = 3.0) -> bool:
        """Block until the first connection attempt completes. Returns True if connected."""
        self._connect_done.wait(timeout=timeout)
        return self._connect_ok

    def stop(self, timeout: float = 5.0):
        """Signal the sender thread to stop and wait for it to finish."""
        self._stop.set()
        self._thread.join(timeout=timeout)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _entries(self):
        """Generator that yields queued LogEntry objects until stopped."""
        while not self._stop.is_set():
            try:
                yield self._queue.get(timeout=0.1)
            except queue.Empty:
                continue

    def _run(self):
        try:
            import grpc
        except ImportError:
            return

        while not self._stop.is_set():
            try:
                channel = grpc.insecure_channel(self.server_addr)
                try:
                    grpc.channel_ready_future(channel).result(timeout=3)
                    self._connect_ok = True
                except grpc.FutureTimeoutError:
                    self._connect_ok = False
                finally:
                    self._connect_done.set()
                if not self._connect_ok:
                    print(f"[LogSender] Could not reach {self.server_addr}, retrying in 3s")
                    channel.close()
                    time.sleep(3)
                    continue
                stub = log_pb2_grpc.LogServiceStub(channel)
                ack = stub.StreamLogs(self._entries())
                if not self._stop.is_set():
                    print(f"[LogSender] Stream ended, server acknowledged {ack.received_count} entries")
            except Exception as e:
                if not self._stop.is_set():
                    self._connect_done.set()
                    print(f"[LogSender] Connection to {self.server_addr} failed: {e!r}, retrying in 3s")
                    time.sleep(3)
