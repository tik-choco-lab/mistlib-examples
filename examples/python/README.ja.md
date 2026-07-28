# Python examples

mistlib を Python から使うサンプルです。

English: [README.md](README.md)

- `gui_client.py`: Pygame による 2D 空間の可視化。自分とボットの位置をリアルタイムに表示します。
- `cli_client.py`: コンソールベースの位置更新。
- `log/`: gRPC のログ収集サーバーと送信クライアント。

## 実行

依存関係のインストールとエンジンバイナリの配置を行います ([ルートの README](../../README.md) を参照)。

```sh
just deps
just sync
```

リポジトリのルートから実行します。

```sh
python examples/python/gui_client.py --id my-node --room demo-room
```

`just` からも起動できます: `just gui`, `just cli`, `just bot` (headless)。

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
