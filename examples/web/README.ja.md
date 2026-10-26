# Web examples

mistlib の Web ラッパーを使ったブラウザ向けサンプルです。

English: [README.md](README.md)

- `index.html`: 3D メタバースデモ。初回アクセス時に Web Crypto API で ECDSA 鍵ペアを生成し
  LocalStorage に保存するため、アカウントなしで参加できます (公開鍵のハッシュがノード ID)。
  移動した座標は周辺ノードへ同期され、他の参加者は青いカプセルとして表示されます。
  描画は Three.js で、glTF アバター (既定は Fox モデル) を読み込みます。
- `media.html`: media API による音声・映像・画面共有。システム音声の共有や共有画面の切り替えを含みます。
- `optimization_demo.html`: DNVE3 の接続最適化の可視化。

## 実行

サンプルは ES モジュールのため、`file://` では動きません。HTTP サーバーを起動してください。

```sh
just serve   # または python -m http.server 8000
```

その後 `http://localhost:8000/examples/web/index.html` を開きます。

import map はエンジン 0.7.0 を指定しています。各デモは起動時にバージョンを
ブラウザのコンソール (media は画面のログ) へ表示します。ローカルビルドを使う場合は
`just fetch 0.7.0` を実行し、import map を
`../../mistlib-wasm/pkg/mistlib_wasm.js` に向けてください。バージョンの export が
見つからない場合は古いローカル成果物を更新してください。

## 操作

- `W / A / S / D`: 移動・旋回
- マウスドラッグ: カメラの回転
- マウスホイール: ズーム

## ルームからの退出

Python は `node.leave_room(id)` / `node.leave_all_rooms()`、Web は
`node.leaveRoom(id)` / `node.leaveAllRooms()`、Unity は
`MistEngine.I.LeaveRoom(id)` / `MistEngine.I.LeaveAllRooms()` を使います。
前者は指定ルームのみ、後者は全ルームを退出します。
すべてのラッパーには mistlib 0.7.0 以降が必要です。
引数なしのルーム退出呼び出しは非推奨です。
