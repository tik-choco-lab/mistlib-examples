# Python wrapper

A ctypes wrapper that calls the mistlib dynamic library (`.dll` / `.so` / `.dylib`) from Python.

Engine 0.7.1 is available on [GitHub Releases](https://github.com/tik-choco-lab/mistlib/releases/tag/v0.7.1)
and [npm](https://www.npmjs.com/package/@tik-choco/mistlib/v/0.7.1). See the
[root README](../../README.md) for setup and the unified event table. This wrapper targets engine 0.7.1 exactly.

日本語版: [README.ja.md](README.ja.md)

- `mist/core.py`: C FFI definitions and the `MistNode` class
- `mist/transform.py`: Utilities for position synchronization

## Usage

Add this directory to `PYTHONPATH`, then import the package:

```python
import sys
sys.path.append("path/to/mistlib-examples/wrappers/python")
from mist import MistNode, get_version, get_build_info

print(get_version())                 # Loaded engine version, e.g. 0.7.1
print(get_build_info())              # Build details as a JSON string
```

See [examples/python](../../examples/python) for working code.

Requires mistlib native **0.7.1**. Run `just fetch 0.7.1` at the repository
root to install it. Metadata uses the native size-query API and is also available
as `node.get_version()` / `node.get_build_info()` before `node.init()`.

Storage methods are `storage_add(name, data)`,
`storage_add_at(name, data, x, y, z)` and `storage_get(cid)` (bytes or `None`).

## Delivery methods

`send_message(to_id, payload, delivery=DELIVERY_UNRELIABLE, room=None)` accepts:

| Constant (import from `mist`) | Code | Guarantee |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | Fully reliable, ordered |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | May drop messages, ordered |
| `DELIVERY_UNRELIABLE` | 2 | May drop or reorder messages (default) |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | Fully reliable, unordered |

`DeliveryMethod` is the type alias for codes 0–3. Unsupported peers use the
reliable ordered channel for code 3. For example:

```python
from mist import DELIVERY_RELIABLE_UNORDERED
node.send_message("peer-id", b"hello", delivery=DELIVERY_RELIABLE_UNORDERED)
```

Configuration dictionaries pass through to the engine, including `storageTransfer`.
MistLib 0.7.1 supplies CP50 defaults when it is omitted.

Run the wrapper tests with `python3 -m unittest discover -s wrappers/python/tests`
from the repository root; no native binary is needed.

## Leaving rooms

```python
node.leave_room("my-room")  # Leave only this room
node.leave_all_rooms()     # Leave every room and release the engine
```

`leave_room(id)` uses native `leave_room_id`, the per-room symbol in 0.7.1.
`leave_all_rooms()` uses native `leave_all_rooms`.
The no-argument `node.leave_room()` and `node.leave_room_id(id)` aliases emit
`DeprecationWarning`; use `leave_all_rooms()` and `leave_room(id)` respectively.

## Events and changes

The source-only Python package has no independent package version. This unreleased
engine 0.7.1 migration removes `EVENT_JOIN` / `EVENT_LEAVE`; import
`EVENT_PEER_CONNECTED` / `EVENT_PEER_DISCONNECTED` instead. All application events
0–12 are exported, including `EVENT_NODE_POSITION_UPDATED` (7), `EVENT_ROOM_JOINED`
(10), `EVENT_ROOM_JOIN_FAILED` (11), and `EVENT_ROOM_LEFT` (12).

`register_callbacks(log_cb, event_cb)` accepts a seven-argument native v2 callback:
`(type, room_ptr, room_len, from_ptr, from_len, data_ptr, data_len)`. Room events have
empty senders, so use the room id for multi-room clients. The existing five-argument
single-room callback also works. Copy callback bytes before returning. Peer/AOI
entry and exit carry UTF-8 fixed strings; JSON events require separate decoding.
