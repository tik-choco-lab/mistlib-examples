# Python wrapper

mistlib のダイナミックライブラリ (`.dll` / `.so` / `.dylib`) を Python から呼び出す ctypes ラッパーです。

エンジン 0.7.1 は [GitHub Releases](https://github.com/tik-choco-lab/mistlib/releases/tag/v0.7.1)
と [npm](https://www.npmjs.com/package/@tik-choco/mistlib/v/0.7.1) で公開されています。
セットアップと共通イベント表は [ルート README](../../README.ja.md) を参照してください。

English: [README.md](README.md)

- `mist/core.py`: C FFI 定義と `MistNode` クラス
- `mist/transform.py`: 位置同期用ユーティリティ

## 使い方

このディレクトリを `PYTHONPATH` に追加して import します。

```python
import sys
sys.path.append("path/to/mistlib-examples/wrappers/python")
from mist import MistNode, get_version, get_build_info

print(get_version())                 # 読み込んだエンジンのバージョン (例: 0.7.1)
print(get_build_info())              # ビルド情報の JSON 文字列
```

動作例は [examples/python](../../examples/python) を参照してください。

mistlib ネイティブ **0.7.1**が必要です。リポジトリルートで `just fetch 0.7.1` を
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

`DeliveryMethod` はコード 0〜3 の型エイリアスです。コード 3 は mistlib 0.7.1 で利用できます。
相手が未対応の場合は信頼性と順序を保証するチャネルへフォールバックします。

```python
from mist import DELIVERY_RELIABLE_UNORDERED
node.send_message("peer-id", b"hello", delivery=DELIVERY_RELIABLE_UNORDERED)
```

設定辞書は `storageTransfer` を含めそのままエンジンへ渡されます。
省略時には mistlib 0.7.1 の CP50 既定値が適用されます。

リポジトリルートで `python3 -m unittest discover -s wrappers/python/tests` を実行すると
ネイティブバイナリなしでラッパーのテストを実行できます。

## ルームからの退出

```python
node.leave_room("my-room")  # 指定ルームのみ退出
node.leave_all_rooms()     # 全ルームを退出してエンジンを解放
```

`leave_room(id)` は 0.7.1 のルーム単位の関数 `leave_room_id` を呼び出します。
`leave_all_rooms()` はネイティブの `leave_all_rooms` を呼び出します。
引数なしの `node.leave_room()` と `node.leave_room_id(id)` は非推奨で、
`DeprecationWarning` を出します。それぞれ `leave_all_rooms()` と `leave_room(id)` に移行してください。

## イベントと変更履歴

Python は独立した版番号を持たないソース配布パッケージです。今回の変更では
エンジン 0.7.1 のみを対象にし、`EVENT_JOIN` / `EVENT_LEAVE` を
`EVENT_PEER_CONNECTED` / `EVENT_PEER_DISCONNECTED` に改名しました（alias なし）。
イベント 0〜12 をすべて公開し、`EVENT_NODE_POSITION_UPDATED` (7)、
`EVENT_ROOM_JOINED` (10)、`EVENT_ROOM_JOIN_FAILED` (11)、`EVENT_ROOM_LEFT` (12) を含みます。
複数ルームの場合は 7 引数の v2 callback
`(type, room_ptr, room_len, from_ptr, from_len, data_ptr, data_len)` を使います。
ルームイベントの送信元は空です。5 引数の単一ルーム callback も利用できます。
callback 内で必要なバイト列をコピーしてください。
