"""
gRPC log server for MistLib.

Receives structured log entries (LogEntry) streamed by Python or Rust nodes
and prints them to stdout. Can be extended to write to files, databases, etc.

Usage:
    python log_server.py [--port 50051]

Proto definition: log.proto
    service LogService { rpc StreamLogs(stream LogEntry) returns (Ack); }

Requires:
    pip install grpcio grpcio-tools
"""

import argparse
import os
import subprocess
import sys
import time
from concurrent import futures

_PROTO_DIR = os.path.dirname(os.path.abspath(__file__))

_LEVEL_COLORS = {
    "DEBUG": "\033[90m",   # grey
    "INFO":  "\033[37m",   # white
    "WARN":  "\033[33m",   # yellow
    "ERROR": "\033[31m",   # red
}
_RESET = "\033[0m"


def _ensure_proto():
    if os.path.exists(os.path.join(_PROTO_DIR, "log_pb2.py")):
        return
    proto_file = os.path.join(_PROTO_DIR, "log.proto")
    if not os.path.exists(proto_file):
        raise FileNotFoundError(f"log.proto not found at {proto_file}")
    try:
        subprocess.run(
            [
                sys.executable, "-m", "grpc_tools.protoc",
                f"-I{_PROTO_DIR}",
                f"--python_out={_PROTO_DIR}",
                f"--grpc_python_out={_PROTO_DIR}",
                proto_file,
            ],
            check=True,
            capture_output=True,
        )
        print("[LogServer] Generated proto stubs from log.proto")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            f"Failed to generate proto stubs: {e.stderr.decode()}\n"
            "Install grpcio-tools first: pip install grpcio-tools"
        ) from e


_ensure_proto()

sys.path.insert(0, _PROTO_DIR)
import log_pb2        # type: ignore  # noqa: E402
import log_pb2_grpc  # type: ignore  # noqa: E402
import grpc           # noqa: E402


class LogServicer(log_pb2_grpc.LogServiceServicer):
    """Receives streaming log entries and prints them."""

    def StreamLogs(self, request_iterator, context):
        count = 0
        peer = context.peer()
        print(f"[LogServer] New stream from {peer}")
        try:
            for entry in request_iterator:
                count += 1
                _print_entry(entry)
        except Exception as e:
            print(f"[LogServer] Stream error from {peer}: {e!r}")
        print(f"[LogServer] Stream closed from {peer}, received {count} entries")
        return log_pb2.Ack(received_count=count)


def _print_entry(entry: log_pb2.LogEntry):
    ts = time.strftime("%H:%M:%S", time.localtime(entry.timestamp / 1_000_000_000))
    level = entry.level.upper()
    color = _LEVEL_COLORS.get(level, "")
    node = entry.node_id[:12] if entry.node_id else "?"
    trace = f" trace={entry.trace_id}" if entry.trace_id else ""
    fields = ""
    if entry.fields:
        fields = " " + " ".join(f"{k}={v}" for k, v in entry.fields.items())
    print(f"{color}[{ts}][{level}][{node}]{_RESET}{trace} {entry.message}{fields}")


def serve(port: int = 50051):
    try:
        import grpc  # noqa: F401
    except ImportError:
        print("grpcio is not installed. Run: pip install grpcio grpcio-tools")
        sys.exit(1)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=16))
    log_pb2_grpc.add_LogServiceServicer_to_server(LogServicer(), server)
    addr = f"[::]:{port}"
    server.add_insecure_port(addr)
    server.start()
    print(f"[LogServer] Listening on {addr}  (Ctrl+C to stop)")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        print("\n[LogServer] Shutting down...")
        server.stop(grace=1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MistLib gRPC Log Server")
    parser.add_argument("--port", type=int, default=50051, help="gRPC listen port (default: 50051)")
    args = parser.parse_args()
    serve(args.port)
