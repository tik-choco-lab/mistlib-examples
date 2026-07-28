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
