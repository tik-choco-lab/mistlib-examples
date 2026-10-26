# Python examples

mistlib を Python から使うサンプルです。

エンジン 0.7.1 は [GitHub Releases](https://github.com/tik-choco-lab/mistlib/releases/tag/v0.7.1)
と [npm](https://www.npmjs.com/package/@tik-choco/mistlib/v/0.7.1) で公開されています。
セットアップと共通イベント表は [ルート README](../../README.ja.md) を参照してください。

English: [README.md](README.md)

- `gui_client.py`: Pygame による 2D 空間の可視化。自分とボットの位置をリアルタイムに表示します。
- `cli_client.py`: コンソールベースの位置更新。
- `log/`: gRPC のログ収集サーバーと送信クライアント。

## 実行

依存関係のインストールとエンジンバイナリの配置を行います ([ルートの README](../../README.md) を参照)。

```sh
just deps
just fetch 0.7.1
```

リポジトリのルートから実行します。

```sh
python examples/python/gui_client.py --id my-node --room demo-room
```

`just` からも起動できます: `just gui`, `just cli`, `just bot` (headless)。

サンプルは起動時に読み込んだエンジンのバージョンを表示します。MistLib 0.7.1 が必要です。

## オプション

| オプション | 内容 |
| --- | --- |
| `--id` | ノード ID |
| `--room` | 接続するルーム名 |
| `--headless` | GUI なしで実行 (ボット用) |
| `--min-speed`, `--max-speed` | 移動速度の範囲 |
| `--world-size` | 空間のサイズ |
| `--config` | クライアント側の設定ファイル (YAML/JSON)。YAML には `PyYAML` が必要 |
| `--rust-config-path` | `MistNode.init()` の前に `set_config` でエンジンへ渡す設定ファイル。キーは Rust 側の `Config` 構造に対応 |

CLI 引数は設定ファイルより優先されます。

## ルームからの退出

Python は `node.leave_room(id)` / `node.leave_all_rooms()`、Web は
`node.leaveRoom(id)` / `node.leaveAllRooms()`、Unity は
`MistEngine.I.LeaveRoom(id)` / `MistEngine.I.LeaveAllRooms()` を使います。
前者は指定ルームのみ、後者は全ルームを退出します。
すべてのラッパーには mistlib 0.7.1 が必要です。
引数なしのルーム退出呼び出しは非推奨です。
