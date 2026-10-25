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

下表のパスへ置くか、エンジンのソースを手元に持っているならスクリプトに任せられます。

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

コード 3 には次の mistlib リリースが必要です。相手が未対応の場合、エンジンは
信頼性と順序を保証するチャネルへフォールバックします。コード 0〜2 は変更ありません。

Python と Web は `DELIVERY_RELIABLE` (0)、`DELIVERY_UNRELIABLE_ORDERED` (1)、
`DELIVERY_UNRELIABLE` (2)、`DELIVERY_RELIABLE_UNORDERED` (3) を公開します。
Unity は上表の方式名を `MistEngine.DeliveryMethod` で公開します。

次のエンジンリリースは `storageTransfer` の CP50 既定値も提供します。ラッパーは設定を
そのまま渡すため、既定値の指定は不要です。flat FFI JSON のキーは `storageTransfer`
です（エンジンの完全な設定では `storage.transfer`）。

## ライセンス

[Apache License 2.0](LICENSE)
