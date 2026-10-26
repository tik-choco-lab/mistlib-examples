# mistlib-examples

Client wrappers for mistlib (Python / Web / Unity) and usage examples.

The engine itself (the Rust core and its native / WebAssembly builds) lives in a separate
repository. This repository contains only the client code and the samples.

日本語版: [README.ja.md](README.ja.md)

## Layout

| Path | Contents |
| --- | --- |
| `wrappers/python/` | Python wrapper (the `mist` package, calling the native library through ctypes) |
| `wrappers/web/` | Web wrapper (an ES module that loads the WebAssembly build) |
| `wrappers/unity/` | Unity package (`com.tik-choco.mistlib`, via P/Invoke) |
| `examples/python/` | CLI / GUI clients and a gRPC log collection sample |
| `examples/web/` | Browser demos (3D metaverse, media, optimization) |

## Setup

Every wrapper needs a prebuilt engine binary. Those binaries are not part of this repository —
they are published by [mistlib](https://github.com/tik-choco-lab/mistlib):

- **Web** — the WebAssembly build is on npm as
  [`@tik-choco/mistlib`](https://www.npmjs.com/package/@tik-choco/mistlib).
- **Python / Unity** — the native library ships in
  [each release](https://github.com/tik-choco-lab/mistlib/releases/latest) as
  `mistlib-native-<platform>-<version>.zip`.

All wrappers require **MistLib 0.7.0 or later**. Download the 0.7.0 release artifacts
with GitHub CLI (`gh`) and `unzip` installed:

```sh
just fetch 0.7.0        # or ./scripts/sync-mistlib.sh --release 0.7.0
```

This installs WASM and the Linux x86_64, Windows x86_64 and macOS aarch64 native
libraries at the paths below. To build from engine sources instead:

```sh
cp .env.example .env   # configure the source repository and branch
just sync              # or ./scripts/sync-mistlib.sh
```

The web demos load the engine from a CDN through each page's import map, so they need no
local build; point that map at `../../mistlib-wasm/pkg/mistlib_wasm.js` to use one. The other
wrappers read the artifacts from disk (all untracked).

| Destination | Referenced by |
| --- | --- |
| `target/release/libmistlib.so` | `wrappers/python/mist/core.py` |
| `mistlib-wasm/pkg/` | `wrappers/web/index.js` |
| `wrappers/unity/MistLib/Runtime/Plugins/` | Unity native plugins |

See `.env.example` for the available settings. If `MISTLIB_DEV_PATH` points at an existing
local checkout, the script leaves that checkout untouched — it neither fetches nor checks out.
Leave it empty to have the script clone into `.mistlib-dev/` and manage it itself.

## Commands

We use [just](https://github.com/casey/just). Run `just` to list the recipes.

| Command | Description |
| --- | --- |
| `just fetch 0.7.0` | Download and place the release artifacts (no Rust build needed) |
| `just sync` | Build the engine and place the artifacts |
| `just sync-fast` | Skip the build and only copy existing artifacts |
| `just serve` | Start an HTTP server for the web samples |
| `just deps` | Install the Python sample dependencies |
| `just gui` / `just cli` / `just bot` | Run the Python samples |
| `just log-server` | Start the gRPC log collection server |
| `just proto` | Regenerate the Python stubs from `log.proto` |
| `just check` | Syntax-check the Python and JavaScript sources |
| `just clean` | Remove the fetched artifacts |

## Signaling

Signaling is Nostr. Peers find each other only if their `inviteSalt` and `inviteCode` both
match, so the wrappers ship no defaults for them — pick values unique to your application:

```js
new MistNode(id, { signaling: { mode: "nostr", nostr: {
  inviteSalt: "my-app", inviteCode: "a-shared-secret",
} } });
```

Relays differ per wrapper: Python and Unity point at a local relay on `ws://127.0.0.1:7777`,
while the web wrapper leaves `relays` empty and lets the engine fetch a relay list at startup.
Set it explicitly to use your own.

## Delivery methods

| Code | Method | Guarantee |
| --- | --- | --- |
| 0 | ReliableOrdered | Fully reliable, ordered |
| 1 | UnreliableOrdered | May drop messages, ordered |
| 2 | Unreliable | May drop or reorder messages (default) |
| 3 | ReliableUnordered | Fully reliable, unordered |

Code 3 is available in mistlib 0.7.0. When a peer lacks the capability,
the engine uses its reliable ordered channel.

Python and Web export `DELIVERY_RELIABLE` (0), `DELIVERY_UNRELIABLE_ORDERED` (1),
`DELIVERY_UNRELIABLE` (2), and `DELIVERY_RELIABLE_UNORDERED` (3). Unity exposes
`MistEngine.DeliveryMethod` with the method names above.

MistLib 0.7.0 also supplies the `storageTransfer` CP50 defaults; wrappers
pass configuration through without needing to set them. The flat FFI JSON key is
`storageTransfer` (the full engine configuration uses `storage.transfer`).

## Engine version

Python exposes `get_version()` / `get_build_info()` both on `mist` and `MistNode`.
Web exposes async `getVersion()` / `getBuildInfo()`; Unity exposes
`MistEngine.I.GetVersion()` / `GetBuildInfo()`. Build information is a JSON string.
These report the loaded engine, independently of the wrapper package version.

If Web reports a missing version export, update `@tik-choco/mistlib` to >= 0.7.0.
For a local import map, rerun `just fetch 0.7.0` or `just sync` and reload the page;
older `mistlib-wasm/pkg` directories can still contain the July 0.1.0 build.

## License

[Apache License 2.0](LICENSE)

## Leaving rooms

Use `node.leave_room(id)` / `node.leave_all_rooms()` in Python,
`node.leaveRoom(id)` / `node.leaveAllRooms()` on the Web, or
`MistEngine.I.LeaveRoom(id)` / `MistEngine.I.LeaveAllRooms()` in Unity.
The first operation leaves one room; the second leaves all rooms.
All wrappers require mistlib 0.7.0 or later. No-argument room-leave calls are deprecated.
