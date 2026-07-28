# Python examples

Samples using mistlib from Python.

日本語版: [README.ja.md](README.ja.md)

- `gui_client.py`: 2D visualization of the space with Pygame. Shows your own position and the bots in real time.
- `cli_client.py`: Console-based position updates.
- `log/`: gRPC log collection server and sender.

## Running

Install the dependencies and place the engine binary (see the [root README](../../README.md)):

```sh
just deps
just sync
```

Then run a sample from the repository root:

```sh
python examples/python/gui_client.py --id my-node --room demo-room
```

Or via `just`: `just gui`, `just cli`, `just bot` (headless).

## Options

| Option | Description |
| --- | --- |
| `--id` | Node ID |
| `--room` | Room to join |
| `--headless` | Run without a GUI (for bots) |
| `--min-speed`, `--max-speed` | Movement speed range |
| `--world-size` | Size of the space |
| `--config` | Client config file (YAML/JSON); `PyYAML` is required for YAML |
| `--rust-config-path` | Config file passed to the engine via `set_config` before `MistNode.init()`; its keys match the Rust-side `Config` struct |

CLI arguments take precedence over the config file.
