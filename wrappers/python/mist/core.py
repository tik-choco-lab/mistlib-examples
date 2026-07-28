import ctypes
import inspect
import os
import sys
import json

EVENT_RAW = 0
EVENT_OVERLAY = 1
EVENT_JOIN = 2
EVENT_LEAVE = 3
EVENT_NEIGHBORS = 4
EVENT_AOI_ENTERED = 5
EVENT_AOI_LEFT = 6
EVENT_NODE_POSITION_UPDATED = 7
EVENT_AOI_NODES = 8
EVENT_ALL_CONNECTIONS_LOST = 9

DELIVERY_RELIABLE = 0
DELIVERY_UNRELIABLE_ORDERED = 1
DELIVERY_UNRELIABLE = 2

if sys.platform == "win32":
    lib_name = "mistlib.dll"
elif sys.platform == "darwin":
    lib_name = "libmistlib.dylib"
else:
    lib_name = "libmistlib.so"

release_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../target/release", lib_name))
debug_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../target/debug", lib_name))
if os.path.exists(release_path):
    DLL_PATH = release_path
else:
    DLL_PATH = debug_path

DEFAULT_NOSTR_RELAY_URL = "ws://127.0.0.1:7777"


def default_config():
    return {
        "signaling": {
            "mode": "nostr",
            "nostr": {
                "relays": [DEFAULT_NOSTR_RELAY_URL],
                "discoveryKind": 25049,
                "messageKind": 25050,
                "ttlSeconds": 60,
                "maxClockSkewSeconds": 300,
                "inviteSalt": "nostr-sig-test-local-salt",
                "inviteCode": "dev-invite-001",
            },
        },
    }

EVENT_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)
# v2: same shape as EVENT_CALLBACK, with a room_id (ptr, len) pair inserted
# right after message_type (mirrors the Rust EventCallbackV2 ABI, SPEC-12).
EVENT_CALLBACK_V2 = ctypes.CFUNCTYPE(
    None,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t,
)
LOG_CALLBACK = ctypes.CFUNCTYPE(None, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t)

# ctypes caches CDLL handles per path (the OS loader dedupes them), so every
# MistNode would otherwise drive the same process-wide Rust engine. Guard
# against a second instance until the first releases via leave_room() (all
# rooms).
_active_instance = None

def _adapt_event_callback(event_cb):
    """Wrap a v1-shaped user event_cb so it can be driven by register_event_callback_v2.

    Callbacks written for the v1 signature (event_type, from_ptr, from_len,
    data_ptr, data_len) keep working unmodified; callbacks that also accept
    the room_id (event_type, room_ptr, room_len, from_ptr, from_len,
    data_ptr, data_len) receive it too.
    """
    wants_room = len(inspect.signature(event_cb).parameters) >= 7

    def trampoline(event_type, room_ptr, room_len, from_ptr, from_len, data_ptr, data_len):
        if wants_room:
            event_cb(event_type, room_ptr, room_len, from_ptr, from_len, data_ptr, data_len)
        else:
            event_cb(event_type, from_ptr, from_len, data_ptr, data_len)

    return trampoline

class MistNode:
    def __init__(self, node_id, signaling_url=None, config=None):
        global _active_instance
        if _active_instance is not None:
            raise RuntimeError(
                "mistlib supports one active MistNode per process; call leave_room() "
                "before initializing another node."
            )

        if not os.path.exists(DLL_PATH):
            raise FileNotFoundError(f"DLL not found: {DLL_PATH}")

        self.lib = ctypes.CDLL(DLL_PATH)
        self.node_id = node_id
        self.signaling_url = signaling_url
        self.config = default_config() if signaling_url is None and config is None else config

        self.lib.init.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
        self.lib.init_with_config.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t]
        self.lib.init_with_config.restype = ctypes.c_bool
        self.lib.join_room.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        self.lib.register_log_callback.argtypes = [LOG_CALLBACK]
        self.lib.register_event_callback.argtypes = [EVENT_CALLBACK]
        self.lib.register_event_callback_v2.argtypes = [EVENT_CALLBACK_V2]
        self.lib.update_position.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float]
        self.lib.update_position_in_room.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_float, ctypes.c_float, ctypes.c_float]
        self.lib.send_message.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32]
        self.lib.send_message_in_room.argtypes = [ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint32]
        self.lib.leave_room.argtypes = []
        self.lib.leave_room_id.argtypes = [ctypes.c_char_p, ctypes.c_size_t]
        self.lib.get_stats.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        self.lib.get_stats.restype = ctypes.c_uint32
        self.lib.get_config.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
        self.lib.get_config.restype = ctypes.c_uint32
        self.lib.set_config.argtypes = [ctypes.c_char_p, ctypes.c_size_t]

        _active_instance = self

    def register_callbacks(self, log_cb, event_cb):
        self._log_cb_ref = LOG_CALLBACK(log_cb)
        self._event_cb_ref = EVENT_CALLBACK_V2(_adapt_event_callback(event_cb))
        self.lib.register_log_callback(self._log_cb_ref)
        self.lib.register_event_callback_v2(self._event_cb_ref)

    def init(self):
        id_bytes = self.node_id.encode('utf-8')
        if self.config is not None:
            config_bytes = self._encode_config(self.config)
            ok = self.lib.init_with_config(id_bytes, len(id_bytes), config_bytes, len(config_bytes))
            if not ok:
                raise RuntimeError("mistlib rejected config")
            return
        signaling_url = self._encode_text(self.signaling_url)
        self.lib.init(id_bytes, len(id_bytes), signaling_url, len(signaling_url))

    def join_room(self, room_id):
        # Callable multiple times with different room_ids; re-joining the
        # same room is an idempotent re-announce.
        room_bytes = room_id.encode('utf-8')
        self.lib.join_room(room_bytes, len(room_bytes))

    def update_position(self, x, y, z=0.0, room=None):
        if room is not None:
            room_bytes = room.encode('utf-8')
            self.lib.update_position_in_room(room_bytes, len(room_bytes), float(x), float(y), float(z))
            return
        self.lib.update_position(float(x), float(y), float(z))

    def send_message(self, to_id, payload, delivery=DELIVERY_UNRELIABLE, room=None):
        to_id_bytes = to_id.encode('utf-8') if to_id else b""
        if room is not None:
            room_bytes = room.encode('utf-8')
            self.lib.send_message_in_room(room_bytes, len(room_bytes), to_id_bytes, len(to_id_bytes), payload, len(payload), delivery)
            return
        self.lib.send_message(to_id_bytes, len(to_id_bytes), payload, len(payload), delivery)

    def leave_room(self, room_id=None):
        global _active_instance
        if room_id is not None:
            room_bytes = room_id.encode('utf-8')
            self.lib.leave_room_id(room_bytes, len(room_bytes))
            return
        self.lib.leave_room()
        if _active_instance is self:
            _active_instance = None

    def get_stats(self):
        buffer = (ctypes.c_uint8 * 65536)()
        written = self.lib.get_stats(buffer, len(buffer))
        if written > 0:
            return ctypes.string_at(buffer, written).decode('utf-8')
        return "{}"

    def get_config(self):
        buffer = (ctypes.c_uint8 * 4096)()
        written = self.lib.get_config(buffer, len(buffer))
        if written > 0:
            return ctypes.string_at(buffer, written).decode('utf-8')
        return "{}"

    def set_config(self, config):
        data = self._encode_config(config)
        self.lib.set_config(data, len(data))

    @staticmethod
    def _encode_config(config):
        if isinstance(config, dict):
            return json.dumps(config).encode('utf-8')
        if isinstance(config, str):
            return config.encode('utf-8')
        if isinstance(config, (bytes, bytearray)):
            return bytes(config)
        raise TypeError("config must be dict, str, bytes, or bytearray")

    @staticmethod
    def _encode_text(value):
        if isinstance(value, str):
            return value.encode('utf-8')
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        raise TypeError("value must be str, bytes, or bytearray")
