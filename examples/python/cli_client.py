import os
import time
from utils import initialize_config
from client import MistClient

def run_cli():
    final_args = initialize_config(description="MistLib CLI Client", is_gui=False)

    print(f"[*] Starting CLI Client: {final_args.id} in room: {final_args.room}")
    client = MistClient(final_args)
    client.start()

    try:
        print("[*] Client running. Press Ctrl+C to stop.")
        last_print = 0
        while True:
            client.tick()
            if time.time() - last_print > 5.0:
                pos = client.local_transform.position
                print(f"[Status] Pos:({pos[0]:.1f}, {pos[1]:.1f}) | Conn:{len(client.connected_nodes)} | Neighbors:{len(client.neighbor_nodes)}")
                last_print = time.time()

            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[*] Stopping...")
    finally:
        client.leave_room()

if __name__ == "__main__":
    run_cli()
