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
from mist import MistNode
```

See [examples/python](../../examples/python) for working code.

## Delivery methods

`send_message(to_id, payload, delivery=DELIVERY_UNRELIABLE, room=None)` accepts:

| Constant (import from `mist`) | Code | Guarantee |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | Fully reliable, ordered |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | May drop messages, ordered |
| `DELIVERY_UNRELIABLE` | 2 | May drop or reorder messages (default) |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | Fully reliable, unordered |

`DeliveryMethod` is the type alias for codes 0–3. Code 3 requires the upcoming
mistlib release; unsupported peers use the reliable ordered channel. Codes 0–2
are unchanged. For example:

```python
from mist import DELIVERY_RELIABLE_UNORDERED
node.send_message("peer-id", b"hello", delivery=DELIVERY_RELIABLE_UNORDERED)
```

Configuration dictionaries pass through to the engine, including `storageTransfer`.
The upcoming engine supplies CP50 defaults when it is omitted.

Run the wrapper tests with `python3 -m unittest discover -s wrappers/python/tests`
from the repository root; no native binary is needed.
