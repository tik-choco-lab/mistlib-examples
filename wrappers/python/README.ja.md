# Python wrapper

mistlib のダイナミックライブラリ (`.dll` / `.so` / `.dylib`) を Python から呼び出す ctypes ラッパーです。

English: [README.md](README.md)

- `mist/core.py`: C FFI 定義と `MistNode` クラス
- `mist/transform.py`: 位置同期用ユーティリティ

## 使い方

このディレクトリを `PYTHONPATH` に追加して import します。

```python
import sys
sys.path.append("path/to/mistlib-examples/wrappers/python")
from mist import MistNode
```

動作例は [examples/python](../../examples/python) を参照してください。
