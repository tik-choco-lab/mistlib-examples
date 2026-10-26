#!/usr/bin/env bash
#
# リリースまたは mistlib-dev からエンジン成果物を取得して配置する。
# ソースからのビルド設定は .env で行う (.env.example を参照)。
#
#   cp .env.example .env && ./scripts/sync-mistlib.sh
#   ./scripts/sync-mistlib.sh --release 0.7.1
#
# 配置先はラッパーの探索パスに合わせてある:
#   target/release/libmistlib.so                  <- wrappers/python/mist/core.py
#   mistlib-wasm/pkg/                             <- wrappers/web/index.js
#   wrappers/unity/MistLib/Runtime/Plugins/       <- Unity のネイティブプラグイン

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

MISTLIB_DEV_REPO="${MISTLIB_DEV_REPO:-}"
MISTLIB_DEV_REF="${MISTLIB_DEV_REF:-}"
MISTLIB_DEV_PATH="${MISTLIB_DEV_PATH:-}"
MISTLIB_SKIP_BUILD="${MISTLIB_SKIP_BUILD:-0}"

CACHE_DIR="$ROOT/.mistlib-dev"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m警告:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31mエラー:\033[0m %s\n' "$*" >&2; exit 1; }

if [ "${1:-}" = "--release" ]; then
    [ "$#" -eq 2 ] || die "使い方: $0 --release 0.7.1"
    version="${2#v}"
    [[ "$version" =~ ^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]] || die "無効なバージョン: $version"
    [ "$version" = "0.7.1" ] || die "mistlib 0.7.1 が必要です"
    command -v gh >/dev/null 2>&1 || die "GitHub CLI (gh) が必要です"
    command -v unzip >/dev/null 2>&1 || die "unzip が必要です"
    release_dir="$(mktemp -d)"
    trap 'rm -rf "$release_dir"' EXIT
    SRC="$release_dir/staged"
    mkdir -p "$SRC/target/release" "$SRC/mistlib-wasm"
    log "リリースを取得: tik-choco-lab/mistlib v$version"
    gh release download "v$version" -R tik-choco-lab/mistlib --dir "$release_dir" \
        --pattern "mistlib-native-linux-x86_64-v$version.zip" \
        --pattern "mistlib-native-windows-x86_64-v$version.zip" \
        --pattern "mistlib-native-macos-aarch64-v$version.zip" \
        --pattern "mistlib-wasm-v$version.zip"
    for platform in linux-x86_64 windows-x86_64 macos-aarch64; do
        unzip -q "$release_dir/mistlib-native-$platform-v$version.zip" -d "$release_dir/$platform"
    done
    cp "$release_dir/linux-x86_64/libmistlib.so" "$SRC/target/release/"
    cp "$release_dir/windows-x86_64/mistlib.dll" "$SRC/target/release/"
    cp "$release_dir/macos-aarch64/libmistlib.dylib" "$SRC/target/release/"
    unzip -q "$release_dir/mistlib-wasm-v$version.zip" -d "$release_dir/wasm"
    cp -R "$release_dir/wasm/pkg" "$SRC/mistlib-wasm/pkg"
    grep -Eq "\"version\"[[:space:]]*:[[:space:]]*\"${version//./\\.}\"" \
        "$SRC/mistlib-wasm/pkg/package.json" || die "wasm のバージョンが v$version と一致しません"
else
    [ "$#" -eq 0 ] || die "使い方: $0 [--release 0.7.1]"

    # --- 取得元の決定 -----------------------------------------------------------
    #
    # MISTLIB_DEV_PATH が指定された場合、それは利用者自身の作業チェックアウトなので
    # 絶対に変更しない (fetch / checkout / reset は行わない)。ref がずれていても
    # 警告するだけに留める。管理下の clone のみスクリプトが更新する。

    if [ -n "$MISTLIB_DEV_PATH" ]; then
        case "$MISTLIB_DEV_PATH" in
            /*) SRC="$MISTLIB_DEV_PATH" ;;
            *) SRC="$ROOT/$MISTLIB_DEV_PATH" ;;
        esac
        [ -d "$SRC/.git" ] || die "MISTLIB_DEV_PATH が git リポジトリではない: $SRC"
        SRC="$(cd "$SRC" && pwd)"
        log "既存のチェックアウトを使用 (変更しません): $SRC"

        current_ref="$(git -C "$SRC" rev-parse --abbrev-ref HEAD)"
        if [ -n "$MISTLIB_DEV_REF" ] && [ "$current_ref" != "$MISTLIB_DEV_REF" ]; then
            warn "チェックアウトは '$current_ref' で、MISTLIB_DEV_REF='$MISTLIB_DEV_REF' と異なります。"
            warn "そのままビルドします。切り替える場合は手動で行ってください。"
        fi
        if [ -n "$(git -C "$SRC" status --porcelain)" ]; then
            warn "作業ツリーに未コミットの変更があります。その状態のままビルドします。"
        fi
    else
        [ -n "$MISTLIB_DEV_REF" ] || die "MISTLIB_DEV_REF が未設定です。.env で取得するブランチ / タグ / コミットを指定してください (.env.example 参照)。"
        SRC="$CACHE_DIR"
        if [ -d "$SRC/.git" ]; then
            log "更新中: $SRC ($MISTLIB_DEV_REF)"
            git -C "$SRC" fetch --prune origin
        else
            [ -n "$MISTLIB_DEV_REPO" ] || die "MISTLIB_DEV_REPO が未設定です。.env で取得元を指定するか、MISTLIB_DEV_PATH で既存のチェックアウトを指してください (.env.example 参照)。"
            log "clone 中: $MISTLIB_DEV_REPO -> $SRC"
            git clone "$MISTLIB_DEV_REPO" "$SRC"
            git -C "$SRC" fetch --prune origin
        fi
        # 管理下の clone なので、常に指定 ref の状態に合わせる。
        if git -C "$SRC" rev-parse --verify --quiet "origin/$MISTLIB_DEV_REF" >/dev/null; then
            git -C "$SRC" checkout --detach "origin/$MISTLIB_DEV_REF"
        else
            git -C "$SRC" checkout --detach "$MISTLIB_DEV_REF"
        fi
    fi

    log "取得元 HEAD: $(git -C "$SRC" rev-parse --short HEAD) $(git -C "$SRC" log -1 --format=%s)"

    # --- ビルド -----------------------------------------------------------------

    if [ "$MISTLIB_SKIP_BUILD" = "1" ]; then
        log "MISTLIB_SKIP_BUILD=1 のためビルドを省略"
    else
        if command -v just >/dev/null 2>&1; then
            log "ネイティブライブラリをビルド (just build-native)"
            (cd "$SRC" && just build-native)
            log "wasm をビルド (just build-wasm-release)"
            (cd "$SRC" && just build-wasm-release)
        else
            command -v cargo >/dev/null 2>&1 || die "cargo が必要です"
            command -v wasm-pack >/dev/null 2>&1 || die "wasm-pack が必要です"
            log "ネイティブライブラリをビルド (cargo)"
            (cd "$SRC" && cargo build --release -p mistlib-native)
            log "wasm をビルド (wasm-pack)"
            (cd "$SRC/mistlib-wasm" && wasm-pack build --target web --release)
        fi
    fi

fi

# --- 配置 -------------------------------------------------------------------

[ -f "$SRC/mistlib-wasm/pkg/mistlib_wasm_bg.wasm" ] || die "wasm バイナリが見つかりません"
grep -Eq '"version"[[:space:]]*:[[:space:]]*"0\.7\.1"' \
    "$SRC/mistlib-wasm/pkg/package.json" || die "mistlib 0.7.1 が必要です"
for symbol in get_version get_build_info leave_all_rooms; do
    grep -q "export function $symbol(" "$SRC/mistlib-wasm/pkg/mistlib_wasm.js" \
        || die "wasm に $symbol がありません。mistlib 0.7.1 で再ビルドしてください"
done

copied=0

# ネイティブライブラリ: Python ラッパーと Unity プラグイン向け。
mkdir -p "$ROOT/target/release" "$ROOT/wrappers/unity/MistLib/Runtime/Plugins"
for lib in libmistlib.so libmistlib.dylib mistlib.dll; do
    if [ -f "$SRC/target/release/$lib" ]; then
        cp -f "$SRC/target/release/$lib" "$ROOT/target/release/$lib"
        cp -f "$SRC/target/release/$lib" "$ROOT/wrappers/unity/MistLib/Runtime/Plugins/$lib"
        log "配置: target/release/$lib と Unity Plugins/$lib"
        copied=$((copied + 1))
    fi
done
[ "$copied" -gt 0 ] || die "ネイティブライブラリが見つかりません: $SRC/target/release/"

# wasm: Web ラッパーの import 先。
[ -d "$SRC/mistlib-wasm/pkg" ] || die "wasm 成果物が見つかりません: $SRC/mistlib-wasm/pkg"
mkdir -p "$ROOT/mistlib-wasm"
rm -rf "$ROOT/mistlib-wasm/pkg"
cp -R "$SRC/mistlib-wasm/pkg" "$ROOT/mistlib-wasm/pkg"
log "配置: mistlib-wasm/pkg/"

# --- 検証 -------------------------------------------------------------------

[ -f "$ROOT/mistlib-wasm/pkg/mistlib_wasm.js" ] || die "mistlib_wasm.js が配置されていません"
log "完了。wrappers/web/index.js の import が解決するようになりました。"
