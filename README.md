# mistlib-examples

MistLib のクライアントラッパー (Python / Web / Unity) と、その利用例です。

エンジン本体 (Rust コア、ネイティブ / WebAssembly ビルド) は別リポジトリで管理されており、
このリポジトリには配布用のクライアントコードとサンプルのみが含まれます。

## 構成

| パス | 内容 |
| --- | --- |
| `wrappers/python/` | Python ラッパー (`mist` パッケージ、ctypes 経由でネイティブライブラリを呼び出し) |
| `wrappers/web/` | Web ラッパー (WebAssembly ビルドを読み込む ES モジュール) |
| `wrappers/unity/` | Unity パッケージ (`com.tik-choco.mistlib`、P/Invoke 経由) |
| `examples/python/` | CLI / GUI クライアントと、gRPC ログ収集のサンプル |
| `examples/web/` | ブラウザ向けデモ (3D メタバース、メディア、最適化デモ) |

## セットアップ

各ラッパーは MistLib エンジンのビルド済みバイナリを必要とします。これらはこの
リポジトリには含まれず、`scripts/sync-mistlib.sh` でエンジン側リポジトリから取得します。

```sh
cp .env.example .env   # 取得元とブランチを設定
just sync              # または ./scripts/sync-mistlib.sh
```

成果物は各ラッパーが探索するパスへ配置されます (いずれも git 管理外)。

| 配置先 | 参照元 |
| --- | --- |
| `target/release/libmistlib.so` | `wrappers/python/mist/core.py` |
| `mistlib-wasm/pkg/` | `wrappers/web/index.js` |
| `wrappers/unity/MistLib/Runtime/Plugins/` | Unity のネイティブプラグイン |

設定項目は `.env.example` を参照してください。`MISTLIB_DEV_PATH` に既存のローカル
チェックアウトを指定した場合、スクリプトはそのチェックアウトを一切変更しません
(fetch も checkout も行いません)。空にすると `.mistlib-dev/` に clone して
スクリプト側で管理します。

エンジン側リポジトリへのアクセス権が必要です。

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

デフォルトのシグナリング方式は Nostr です。既定のリレー設定はラッパーごとに異なります。

- Python / Unity: ローカルリレー `ws://127.0.0.1:7777` を参照するため、リレーを起動するか設定を上書きしてください。
- Web: `relays` が空のため、エンジン既定のリレーリストが使われます。任意のリレーを使う場合は設定で明示してください。

## ライセンス

[Apache License 2.0](LICENSE)
