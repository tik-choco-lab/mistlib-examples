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

Every wrapper needs a prebuilt engine binary. Those binaries are not part of this repository;
`scripts/sync-mistlib.sh` fetches them from the engine repository, which you need access to.

```sh
cp .env.example .env   # configure the source repository and branch
just sync              # or ./scripts/sync-mistlib.sh
```

The artifacts are placed where each wrapper looks for them (all untracked).

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

The default signaling method is Nostr. The default relay configuration differs per wrapper.

- Python / Unity: they point at the local relay `ws://127.0.0.1:7777`, so either run a relay or override the setting.
- Web: `relays` is empty, so the engine's built-in relay list is used. Set it explicitly to use your own relays.

## License

[Apache License 2.0](LICENSE)
