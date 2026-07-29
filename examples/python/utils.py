import os
import sys
import json
import ctypes
import argparse
import re

def setup_mist_path():
    """Add wrapper path to sys.path."""
    wrapper_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../wrappers/python"))
    if wrapper_path not in sys.path:
        sys.path.append(wrapper_path)

def decode_rust_str(ptr, length):
    """Safely decode a string coming from Rust FFI."""
    try:
        if not ptr or length <= 0:
            return ""
        return ctypes.string_at(ptr, length).decode('utf-8')
    except:
        return ""

def load_sim_config(config_path, headless=False, normalize_keys=True):
    """Load YAML or JSON config for simulation."""
    if not config_path or not os.path.exists(config_path):
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()

        try:
            import yaml
            loaded = yaml.safe_load(raw) or {}
        except ImportError:
            if not headless:
                print("[Config] WARNING: PyYAML not installed. To use YAML configs, run: pip install PyYAML")
            try:
                loaded = json.loads(raw)
            except json.JSONDecodeError:
                if not headless:
                    print(f"[Config] Error: Could not parse {config_path} as JSON (and PyYAML is missing).")
                return {}

        if not isinstance(loaded, dict):
            return {}

        if not normalize_keys:
            return loaded

        normalized = {}
        for key, value in loaded.items():
            normalized_key = str(key).replace("-", "_")
            normalized_key = re.sub(r"(?<!^)(?=[A-Z])", "_", normalized_key).lower()
            normalized[normalized_key] = value
        return normalized
    except Exception as e:
        if not headless:
            print(f"[Config] Failed to load {config_path}: {e}")
        return {}


PYTHON_CONFIG_KEYS = {
    "room",
    "headless",
    "world_size",
    "min_speed",
    "max_speed",
    "auto",
    "signaling",
    "visible_count",
    "min_sync_interval",
    "eval_server",
    "eval_interval",
    "log_server",
}


def _snake_to_camel(name: str) -> str:
    parts = name.split("_")
    return parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:]) if parts else name


def get_mistlib_config_defaults() -> dict:
    """Load the current MistLib config schema/defaults directly from the Rust engine."""
    try:
        setup_mist_path()
        from mist import MistNode, default_config  # type: ignore

        # Never joins a room; the invite is only here because the engine validates
        # the whole config at init.
        schema_config = default_config()
        schema_config["signaling"]["nostr"]["inviteSalt"] = "mistlib-example-schema"
        schema_config["signaling"]["nostr"]["inviteCode"] = "unused"
        node = MistNode("config-schema", config=schema_config)
        raw = node.get_config()
        data = json.loads(raw) if raw else {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def extract_python_config(config: dict) -> dict:
    """Return only the Python/client-side settings from a merged config."""
    python_config = {key: value for key, value in config.items() if key in PYTHON_CONFIG_KEYS}
    if "visible_count" in python_config:
        python_config["visibleCount"] = python_config.pop("visible_count")
    return python_config


def extract_mistlib_config(config: dict, defaults: dict | None = None) -> dict:
    """Return only the MistLib/Rust-engine settings using keys discovered from MistLib itself."""
    mistlib_config = dict(defaults or get_mistlib_config_defaults())
    if not mistlib_config:
        return {}

    for source_key, value in config.items():
        target_key = _snake_to_camel(source_key)
        if target_key in mistlib_config and value is not None:
            mistlib_config[target_key] = value
    return mistlib_config


def _canonicalize_world_size(config: dict, fallback: float) -> None:
    world_size = config.get("world_size")
    if world_size is None:
        world_size = fallback

    config["world_size"] = world_size

def get_python_hard_defaults(is_gui=False, default_rust_config=None) -> dict:
    script_dir = os.path.dirname(__file__)
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    if default_rust_config is None:
        default_rust_config = os.path.join(repo_root, "tests", "config", "mistlib.yaml")

    return {
        "world_size": 100.0,
        "min_speed": 0.0,
        "max_speed": 5.0,
        "visible_count": 5,
        "auto": True,
        "room": "simulation-room",
        "id": f"{('gui' if is_gui else 'bot')}-{os.getpid()}",
        "eval_interval": 0.5,
        "min_sync_interval": 0.2,
        "rust_config_path": default_rust_config,
    }


def initialize_config(description="MistLib Client", is_gui=False, argv=None):
    """
    Common entry point to set up paths, load config, parse CLI, and merge everything.
    Priority: CLI Argument > Environment Variable > Config File > Hardcoded Default
    """
    setup_mist_path()
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    default_config = os.path.join(repo_root, "tests", "config", "node.yaml")
    default_rust_config = os.path.join(repo_root, "tests", "config", "mistlib.yaml")
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--config", type=str, default=default_config)
    pre_parser.add_argument("--headless", action="store_true", default=not is_gui)
    pre_args, _ = pre_parser.parse_known_args(argv)
    config = load_sim_config(pre_args.config, pre_args.headless)
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", type=str, default=pre_args.config)
    parser.add_argument("--id", type=str)
    parser.add_argument("--room", type=str)
    parser.add_argument("--headless", action="store_true", default=pre_args.headless)
    parser.add_argument("--world-size", dest="world_size", type=float)
    parser.add_argument("--min-speed", type=float)
    parser.add_argument("--max-speed", type=float)
    parser.add_argument("--auto", action="store_true", default=None)
    parser.add_argument("--signaling", type=str)
    parser.add_argument("--visible-count", type=int)
    parser.add_argument("--max-connection-count", type=int)
    parser.add_argument("--aoi-range", type=float)
    parser.add_argument("--density-encoding", type=str, choices=["float", "byte"])
    parser.add_argument("--rust-config-path", type=str)
    parser.add_argument("--min-sync-interval", type=float)
    parser.add_argument("--eval-server", type=str)
    parser.add_argument("--eval-interval", type=float)
    parser.add_argument("--log-server", type=str, help="gRPC log server address (e.g. localhost:50051)")

    cli_args = parser.parse_args(argv)
    for key, value in vars(cli_args).items():
        if value is not None:
            config[key] = value
    if not config.get("eval_server"):
        config["eval_server"] = os.getenv("MIST_EVAL_SERVER_URL", "")
    if not config.get("log_server"):
        config["log_server"] = os.getenv("MIST_LOG_SERVER_ADDR", "")
    hard_defaults = get_python_hard_defaults(is_gui=is_gui, default_rust_config=default_rust_config)
    for key, val in hard_defaults.items():
        if key not in config:
            config[key] = val
    _canonicalize_world_size(config, hard_defaults["world_size"])

    return argparse.Namespace(**config)
