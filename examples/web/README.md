# Web examples

Browser samples using the mistlib web wrapper.

日本語版: [README.ja.md](README.ja.md)

- `index.html`: 3D metaverse demo. An ECDSA key pair is generated with the Web Crypto API on first
  visit and kept in LocalStorage, so no account is needed — the hash of the public key is the node
  ID. Movement is synced to nearby nodes, which are drawn as blue capsules. Uses Three.js and loads
  a glTF avatar (the Fox model by default).
- `media.html`: Audio, video and screen sharing through the media API, including system audio and
  switching the shared screen.
- `optimization_demo.html`: Visualization of DNVE3 connection optimization.

## Running

The samples are ES modules, so they need an HTTP server — `file://` will not work.

```sh
just serve   # or: python -m http.server 8000
```

Then open `http://localhost:8000/examples/web/index.html`.

The import maps pin engine 0.7.0. Each demo logs its loaded version at startup
(in the browser console, or the media demo log). To use a local build, run
`just fetch 0.7.0` and point the import map at
`../../mistlib-wasm/pkg/mistlib_wasm.js`. Refresh old local artifacts if version
exports are missing.

## Controls

- `W / A / S / D`: Move and turn
- Mouse drag: Rotate the camera
- Mouse wheel: Zoom

## Leaving rooms

Use `node.leave_room(id)` / `node.leave_all_rooms()` in Python,
`node.leaveRoom(id)` / `node.leaveAllRooms()` on the Web, or
`MistEngine.I.LeaveRoom(id)` / `MistEngine.I.LeaveAllRooms()` in Unity.
The first operation leaves one room; the second leaves all rooms.
All wrappers require mistlib 0.7.0 or later. No-argument room-leave calls are deprecated.
