# MistLib Python Examples

MistLibをPythonから使用するサンプル集です。

## 📁 コンテンツ
- `gui_client.py`: Pygameを使用した2D空間の視覚化シミュレーター。ボットや自分自身の位置をリアルタイムで表示します。
- `cli_client.py`: コンソールベースのシンプルな位置更新サンプル。

## 🚀 動かし方

### 1. 依存関係のインストール
PygameとWebSocketクライアントが必要です。
`config.yaml` を使う場合は `PyYAML` も入れてください（未導入時は JSON 形式ファイルとしても読めます）。

```bash
pip install pygame websocket-client python-dotenv pyyaml
```

### 2. Rustライブラリのビルド
事前にCoreライブラリをビルドしておく必要があります。

```bash
cargo build
```

### 3. サンプルの実行
ルートディレクトリから実行する場合：

```bash
python examples/python/gui_client.py
```

#### オプション
- `--id`: ノードIDの指定
- `--room`: 接続するルーム名
- `--headless`: GUIなしで実行 (ボット用)
- `--min-speed`, `--max-speed`: 移動速度の範囲
- `--world-size`: 空間のサイズ
- `--config`: 設定ファイル（YAML/JSON）
- `--rust-config-path`: Rustエンジンへ `set_config` する設定ファイル（YAML/JSON）

### 4. configファイルで実行（推奨）

`tests/config/node.yaml` を編集して実行できます。

```bash
python examples/python/gui_client.py --config tests/config/node.yaml
```

CLI引数を指定した場合は、`config.yaml` よりCLI引数が優先されます。

`rust-config-path` を指定すると、`MistNode.init()` の前に Python wrapper から `set_config` が呼ばれます。
このファイルは Rust 側の `Config` 構造に対応したキーで定義してください。

```bash
python examples/python/gui_client.py --id my-node --room demo-room --min-speed 0.0 --max-speed 5.0
```
