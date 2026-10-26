# mistlib-examples

mistlib のクライアントラッパー (Python / Web / Unity) と、その利用例です。

エンジン本体 (Rust コア、ネイティブ / WebAssembly ビルド) は別リポジトリで管理されており、
このリポジトリには配布用のクライアントコードとサンプルのみが含まれます。

English: [README.md](README.md)

## 構成

| パス | 内容 |
| --- | --- |
| `wrappers/python/` | Python ラッパー (`mist` パッケージ、ctypes 経由でネイティブライブラリを呼び出し) |
| `wrappers/web/` | Web ラッパー (WebAssembly ビルドを読み込む ES モジュール) |
| `wrappers/unity/` | Unity パッケージ (`com.tik-choco.mistlib`、P/Invoke 経由) |
| `examples/python/` | CLI / GUI クライアントと、gRPC ログ収集のサンプル |
| `examples/web/` | ブラウザ向けデモ (3D メタバース、メディア、最適化デモ) |

## セットアップ

各ラッパーはビルド済みのエンジンバイナリを必要とします。これらはこのリポジトリには含まれず、
[mistlib](https://github.com/tik-choco-lab/mistlib) 側で公開されています。

- **Web** — WebAssembly ビルドは npm の
  [`@tik-choco/mistlib`](https://www.npmjs.com/package/@tik-choco/mistlib)。
- **Python / Unity** — ネイティブライブラリは
  [各リリース](https://github.com/tik-choco-lab/mistlib/releases/latest) の
  `mistlib-native-<platform>-<version>.zip`。

すべてのラッパーは **MistLib 0.7.1 のみ**を対象にします。ネイティブと WASM の成果物は
[v0.7.1 リリース](https://github.com/tik-choco-lab/mistlib/releases/tag/v0.7.1) で、
エンジンは npm の `@tik-choco/mistlib@0.7.1` として公開されています。
GitHub CLI (`gh`) と `unzip` を用意して取得します。

```sh
just fetch 0.7.1        # または ./scripts/sync-mistlib.sh --release 0.7.1
```

WASM と Linux x86_64 / Windows x86_64 / macOS aarch64 のネイティブライブラリを
下表のパスへ配置します。エンジンのソースからビルドする場合は次を使います。

```sh
cp .env.example .env   # 取得元とブランチを設定
just sync              # または ./scripts/sync-mistlib.sh
```

web のデモは各ページの import map 経由で CDN からエンジンを読むため、ローカルビルドは
不要です（使いたい場合は import map を `../../mistlib-wasm/pkg/mistlib_wasm.js` に向けて
ください）。他のラッパーはディスク上の成果物を読みます (いずれも git 管理外)。

| 配置先 | 参照元 |
| --- | --- |
| `target/release/libmistlib.so` | `wrappers/python/mist/core.py` |
| `mistlib-wasm/pkg/` | `wrappers/web/index.js` |
| `wrappers/unity/MistLib/Runtime/Plugins/` | Unity のネイティブプラグイン |

設定項目は `.env.example` を参照してください。`MISTLIB_DEV_PATH` に既存のローカル
チェックアウトを指定した場合、スクリプトはそのチェックアウトを一切変更しません
(fetch も checkout も行いません)。空にすると `.mistlib-dev/` に clone して
スクリプト側で管理します。

## コマンド

[just](https://github.com/casey/just) を使います。`just` で一覧を表示できます。

| コマンド | 内容 |
| --- | --- |
| `just fetch 0.7.1` | リリース成果物を取得して配置 (Rust ビルド不要) |
| `just sync` | エンジンをビルドして成果物を配置 |
| `just sync-fast` | ビルドを省略してコピーのみ |
| `just serve` | Web サンプル用の HTTP サーバーを起動 |
| `just deps` | Python サンプルの依存関係をインストール |
| `just gui` / `just cli` / `just bot` | Python サンプルを起動 |
| `just log-server` | gRPC ログ収集サーバーを起動 |
| `just proto` | `log.proto` から Python スタブを再生成 |
| `just check` | Python / JavaScript の構文チェック |
| `just clean` | 取得した成果物を削除 |

## シグナリング

シグナリングは Nostr です。`inviteSalt` と `inviteCode` の両方が一致するピア同士だけが
互いを見つけられるため、ラッパーは既定値を持ちません。アプリごとに固有の値を設定してください。

```js
new MistNode(id, { signaling: { mode: "nostr", nostr: {
  inviteSalt: "my-app", inviteCode: "a-shared-secret",
} } });
```

リレーはラッパーごとに異なります。Python と Unity は `ws://127.0.0.1:7777` のローカルリレーを
参照し、web ラッパーは `relays` を空にしてエンジンが起動時にリレー一覧を取得します。任意の
リレーを使う場合は設定で明示してください。

## 配送方式

| コード | 方式 | 保証 |
| --- | --- | --- |
| 0 | ReliableOrdered | 完全な信頼性、順序保証あり |
| 1 | UnreliableOrdered | 欠落の可能性あり、順序保証あり |
| 2 | Unreliable | 欠落・順序入れ替わりの可能性あり（既定） |
| 3 | ReliableUnordered | 完全な信頼性、順序保証なし |

コード 3 は mistlib 0.7.1 で利用できます。相手が未対応の場合、エンジンは
信頼性と順序を保証するチャネルへフォールバックします。コード 0〜2 は変更ありません。

Python と Web は `DELIVERY_RELIABLE` (0)、`DELIVERY_UNRELIABLE_ORDERED` (1)、
`DELIVERY_UNRELIABLE` (2)、`DELIVERY_RELIABLE_UNORDERED` (3) を公開します。
Unity は上表の方式名を `MistEngine.DeliveryMethod` で公開します。

mistlib 0.7.1 は `storageTransfer` の CP50 既定値も提供します。ラッパーは設定を
そのまま渡すため、既定値の指定は不要です。flat FFI JSON のキーは `storageTransfer`
です（エンジンの完全な設定では `storage.transfer`）。

## エンジンのバージョン

Python は `mist` と `MistNode` の `get_version()` / `get_build_info()`、
Web は非同期の `getVersion()` / `getBuildInfo()`、Unity は
`MistEngine.I.GetVersion()` / `GetBuildInfo()` を公開します。ビルド情報は JSON 文字列です。
ラッパーのパッケージバージョンとは別に、読み込まれたエンジンを確認できます。

Web でバージョンの export が見つからない場合は `@tik-choco/mistlib` を 0.7.1に
更新してください。ローカルの import map を使う場合は `just fetch 0.7.1` または
`just sync` を再実行してページを再読み込みしてください。古い `mistlib-wasm/pkg` には
7 月の 0.1.0 ビルドが残っていることがあります。

## イベントコード

native / Web のアプリケーションイベントは共通です。Python / Web は `EVENT_<NAME>`、
Unity は `MistLibMessageType` の PascalCase メンバーを使います。

| コード | 名前 | 送信元 / ペイロード |
| --- | --- | --- |
| 0 | RAW | ピア / アプリケーションのバイト列 |
| 1 | OVERLAY | ピア / overlay バイト列 |
| 2 | PEER_CONNECTED | ピア / UTF-8 `joined` |
| 3 | PEER_DISCONNECTED | ピア / UTF-8 `left` |
| 4 | NEIGHBORS | `rust` / ノード一覧 JSON |
| 5 | AOI_ENTERED | ノード / UTF-8 `entered` |
| 6 | AOI_LEFT | ノード / UTF-8 `left` |
| 7 | NODE_POSITION_UPDATED | ノード / 座標 JSON `{x,y,z}`（AOI 内、毎 tick） |
| 8 | AOI_NODES | `rust` / AOI 内ノード一覧 JSON |
| 9 | ALL_CONNECTIONS_LOST | 自ノード / `{"reason":"allConnectionsLost","connectedCount":0}` |
| 10 | ROOM_JOINED | 空 ID / 空バイト列 |
| 11 | ROOM_JOIN_FAILED | 空 ID / UTF-8 の理由文字列 |
| 12 | ROOM_LEFT | 空 ID / 空バイト列 |

Web 専用の media callback は別 API で、100 (`MEDIA_EVENT_TRACK_ADDED`) / 101
(`MEDIA_EVENT_TRACK_REMOVED`) は変更ありません。native の通常 callback には届きません。
コード 9 は接続数 >0 から 0 への遷移で一度通知し、再接続で再び有効になります。
初期空室や明示的な退出では通知せず、ルームへの参加状態は維持します。

Web の peer / AOI 入退域ペイロードは native と同じ固定文字列です。`TextDecoder` や
Python の `.decode('utf-8')` で読み、JSON として扱わないでください。
ルームイベントの送信元は空なので、複数ルームでは native v2 callback の room id、
Web callback の第 4 引数、Unity の `OnRoomEvent` で識別します。

Python の `EVENT_JOIN` / `EVENT_LEAVE` は `EVENT_PEER_CONNECTED` /
`EVENT_PEER_DISCONNECTED` に改名し、alias は残しません。Unity の enum 型名は維持し、
`Location` / `Message` は `Raw` / `Overlay` に改名しました。エンジンイベントではない
未使用の `Heartbeat` / `RequestNodeList` / `NodeList` は削除しました。
ルーム退出メソッドの非推奨 alias は、この変更に不要な破壊を避けるため維持します。

`node scripts/check-engine-api.mjs --source` でバイナリ取得なしの検証ができます。
公開後に `node scripts/check-engine-api.mjs 0.7.1` で配布エンジンの export と enum を検証します。
自動更新も `scripts/engine-api.json` の指定バージョンだけを使います。
変更履歴は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## ライセンス

[Apache License 2.0](LICENSE)

## ルームからの退出

Python は `node.leave_room(id)` / `node.leave_all_rooms()`、Web は
`node.leaveRoom(id)` / `node.leaveAllRooms()`、Unity は
`MistEngine.I.LeaveRoom(id)` / `MistEngine.I.LeaveAllRooms()` を使います。
前者は指定ルームのみ、後者は全ルームを退出します。
すべてのラッパーには mistlib 0.7.1 が必要です。
引数なしのルーム退出呼び出しは非推奨です。
