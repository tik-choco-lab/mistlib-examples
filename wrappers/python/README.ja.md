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

## 配送方式

`send_message(to_id, payload, delivery=DELIVERY_UNRELIABLE, room=None)` は次を受け付けます。

| 定数（`mist` から import） | コード | 保証 |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | 完全な信頼性、順序保証あり |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | 欠落の可能性あり、順序保証あり |
| `DELIVERY_UNRELIABLE` | 2 | 欠落・順序入れ替わりの可能性あり（既定） |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | 完全な信頼性、順序保証なし |

`DeliveryMethod` はコード 0〜3 の型エイリアスです。コード 3 には次の mistlib リリースが
必要です。相手が未対応の場合は信頼性と順序を保証するチャネルへフォールバックします。
コード 0〜2 は変更ありません。

```python
from mist import DELIVERY_RELIABLE_UNORDERED
node.send_message("peer-id", b"hello", delivery=DELIVERY_RELIABLE_UNORDERED)
```

設定辞書は `storageTransfer` を含めそのままエンジンへ渡されます。
省略時には次のエンジンリリースの CP50 既定値が適用されます。

リポジトリルートで `python3 -m unittest discover -s wrappers/python/tests` を実行すると
ネイティブバイナリなしでラッパーのテストを実行できます。
