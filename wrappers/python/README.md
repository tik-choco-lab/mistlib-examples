# Python wrapper

A ctypes wrapper that calls the mistlib dynamic library (`.dll` / `.so` / `.dylib`) from Python.

日本語版: [README.ja.md](README.ja.md)

- `mist/core.py`: C FFI definitions and the `MistNode` class
- `mist/transform.py`: Utilities for position synchronization

## Usage

Add this directory to `PYTHONPATH`, then import the package:

```python
import sys
sys.path.append("path/to/mistlib-examples/wrappers/python")
from mist import MistNode, get_version, get_build_info

print(get_version())                 # Loaded engine version, e.g. 0.7.0
print(get_build_info())              # Build details as a JSON string
```

See [examples/python](../../examples/python) for working code.

Requires mistlib native **0.7.0 or later**. Run `just fetch 0.7.0` at the repository
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
MistLib 0.7.0 supplies CP50 defaults when it is omitted.

Run the wrapper tests with `python3 -m unittest discover -s wrappers/python/tests`
from the repository root; no native binary is needed.

## Leaving rooms

```python
node.leave_room("my-room")  # Leave only this room
node.leave_all_rooms()     # Leave every room and release the engine
```

`leave_room(id)` uses native `leave_room_id`, the per-room symbol in 0.7.0.
`leave_all_rooms()` uses native `leave_all_rooms`.
The no-argument `node.leave_room()` and `node.leave_room_id(id)` aliases emit
`DeprecationWarning`; use `leave_all_rooms()` and `leave_room(id)` respectively.
