set shell := ["bash", "-lc"]

py := "python3"

default:
    @just --list

# --- エンジン成果物の取得 (設定は .env / .env.example を参照) ---

# GitHub リリースから全プラットフォームの成果物を取得する (gh / unzip が必要)。
fetch version="0.7.1":
    ./scripts/sync-mistlib.sh --release {{quote(version)}}

# mistlib-dev からエンジンをビルドして成果物を配置する。
sync:
    ./scripts/sync-mistlib.sh

# ビルドを省略し、既存の成果物をコピーするだけ。
sync-fast:
    MISTLIB_SKIP_BUILD=1 ./scripts/sync-mistlib.sh

# 取得した成果物を削除する (ソースには触れない)。
clean:
    rm -rf target mistlib-wasm wrappers/unity/MistLib/Runtime/Plugins

# --- Web サンプル ---

# Web サンプル用の HTTP サーバーを起動する (ES モジュールのため file:// では動かない)。
serve port="8000":
    @echo "http://localhost:{{port}}/examples/web/index.html"
    @echo "http://localhost:{{port}}/examples/web/media.html"
    @echo "http://localhost:{{port}}/examples/web/optimization_demo.html"
    {{py}} -m http.server {{port}}

# --- Python サンプル ---

# Python サンプルの依存関係をインストールする。
deps:
    pip install pygame websocket-client python-dotenv pyyaml grpcio grpcio-tools

# 2D 可視化クライアント (GUI)。例: just gui --room demo-room
gui *args:
    {{py}} examples/python/gui_client.py {{args}}

# コンソールクライアント。例: just cli --id node-1
cli *args:
    {{py}} examples/python/cli_client.py {{args}}

# GUI なしのボットとして起動する。
bot *args:
    {{py}} examples/python/gui_client.py --headless {{args}}

# --- gRPC ログ ---

# gRPC ログ収集サーバーを起動する。
log-server port="50051":
    {{py}} examples/python/log/log_server.py --port {{port}}

# log.proto から Python スタブを再生成する (grpcio-tools が必要)。
proto:
    {{py}} -m grpc_tools.protoc -I examples/python/log \
        --python_out=examples/python/log \
        --grpc_python_out=examples/python/log \
        examples/python/log/log.proto

# --- チェック ---

# Python と JavaScript の構文チェック。
check:
    {{py}} -m compileall -q examples/python wrappers/python
    for f in wrappers/web/*.js; do node --check "$f"; done
    node scripts/check-engine-api.mjs --source
    @echo "OK"
