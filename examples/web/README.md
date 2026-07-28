# Web Examples: Metaverse Demo

このディレクトリには、MistLib の機能を活用したリッチな Web フロントエンドのサンプルが含まれています。

## 構成
- `index.html`: Web Crypto API と Three.js を使用した、アカウント不要の 3D メタバースデモ。
- `media.html`: `wrapper/web` の media API を使った音声・映像・画面共有サンプル。システム音声共有、共有画面の切り替え、共有終了時の表示改善も含みます。
- `optimization_demo.html`: DNVE3 の接続最適化を可視化するデモ。

## 主な機能
- **自動アイデンティティ生成**: Web Crypto API を使用し、ブラウザを開いた瞬間に ECDSA 鍵ペアを自動生成します。公開鍵のハッシュが P2P ネットワーク上の Node ID となり、LocalStorage に保存されるため「ログインなしで常に同じ自分」として参加できます。
- **3D グラフィックス**: Three.js を使用した無限グリッド空間。
- **glTF アバター**: 外部の glTF モデル（デフォルトで Fox モデル）をロードして操作できます。
- **P2P 同期**: `W/A/S/D` で移動した座標を MistLib 経由で周辺ノードにリアルタイム共有します。他の参加者は青いカプセルとして表示されます。

## 実行方法
このディレクトリ（またはプロジェクトのルート）で HTTP サーバーを起動してください。

```bash
# Python を使用する場合
python -m http.server 8000
```

その後、ブラウザで以下の URL を開きます。
`http://localhost:8000/examples/web/index.html`

メディアサンプルは以下です。
`http://localhost:8000/examples/web/media.html`

最適化デモは以下です。
`http://localhost:8000/examples/web/optimization_demo.html`

## 操作方法
- `W / A / S / D`: 前後左右に移動・旋回
- `マウス ドラッグ`: カメラの回転
- `マウス ホイール`: ズームイン / アウト
