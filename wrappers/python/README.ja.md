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
from mist import MistNode, get_version, get_build_info

print(get_version())                 # 読み込んだエンジンのバージョン (例: 0.7.0)
print(get_build_info())              # ビルド情報の JSON 文字列
```

動作例は [examples/python](../../examples/python) を参照してください。

mistlib ネイティブ **0.7.0 以降**が必要です。リポジトリルートで `just fetch 0.7.0` を
実行して配置してください。メタデータはネイティブのサイズ照会 API で取得し、
`node.init()` の前に `node.get_version()` / `node.get_build_info()` からも呼び出せます。

ストレージは `storage_add(name, data)`、`storage_add_at(name, data, x, y, z)`、
`storage_get(cid)` (bytes または `None`) を使います。

## 配送方式

`send_message(to_id, payload, delivery=DELIVERY_UNRELIABLE, room=None)` は次を受け付けます。

| 定数（`mist` から import） | コード | 保証 |
| --- | --- | --- |
| `DELIVERY_RELIABLE` | 0 | 完全な信頼性、順序保証あり |
| `DELIVERY_UNRELIABLE_ORDERED` | 1 | 欠落の可能性あり、順序保証あり |
| `DELIVERY_UNRELIABLE` | 2 | 欠落・順序入れ替わりの可能性あり（既定） |
| `DELIVERY_RELIABLE_UNORDERED` | 3 | 完全な信頼性、順序保証なし |

`DeliveryMethod` はコード 0〜3 の型エイリアスです。コード 3 は mistlib 0.7.0 で利用できます。
相手が未対応の場合は信頼性と順序を保証するチャネルへフォールバックします。

```python
from mist import DELIVERY_RELIABLE_UNORDERED
node.send_message("peer-id", b"hello", delivery=DELIVERY_RELIABLE_UNORDERED)
```

設定辞書は `storageTransfer` を含めそのままエンジンへ渡されます。
省略時には mistlib 0.7.0 の CP50 既定値が適用されます。

リポジトリルートで `python3 -m unittest discover -s wrappers/python/tests` を実行すると
ネイティブバイナリなしでラッパーのテストを実行できます。

## ルームからの退出

```python
node.leave_room("my-room")  # 指定ルームのみ退出
node.leave_all_rooms()     # 全ルームを退出してエンジンを解放
```

`leave_room(id)` は 0.7.0 のルーム単位の関数 `leave_room_id` を呼び出します。
`leave_all_rooms()` はネイティブの `leave_all_rooms` を呼び出します。
引数なしの `node.leave_room()` と `node.leave_room_id(id)` は非推奨で、
`DeprecationWarning` を出します。それぞれ `leave_all_rooms()` と `leave_room(id)` に移行してください。
