import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import pygame
import math
from utils import initialize_config
from client import MistClient

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SPACING = 50
FPS = 60

COLOR_BACKGROUND = (20, 20, 25)
COLOR_GRID = (40, 40, 50)
COLOR_PEER = (200, 80, 80)
COLOR_SELF = (80, 200, 80)
COLOR_NEIGHBOR = (100, 100, 150)
COLOR_LABEL = (200, 200, 200)
COLOR_TEXT_INFO = (255, 255, 255)

PEER_RADIUS = 8
SELF_RADIUS = 10
LABEL_OFFSET_X = 10
LABEL_OFFSET_Y = 10
INFO_MARGIN = 10
TRUNCATE_ID_LENGTH = 8

def run_simulation():
    final_args = initialize_config(description="MistLib GUI Client", is_gui=True)

    client = MistClient(final_args)
    client.start()

    screen = None
    clock = None
    font = None
    scale = 1.0
    if not final_args.headless:
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(f"Mist Simulator: {final_args.id}")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("Consolas", 12)
        scale_x = SCREEN_WIDTH / final_args.world_size
        scale_y = SCREEN_HEIGHT / final_args.world_size
        scale = min(scale_x, scale_y)

    def world_to_screen(pos):
        return (int(pos[0] * scale), int(pos[2] * scale))

    def screen_to_world(pos):
        return [pos[0] / scale, client.local_transform.position[1], pos[1] / scale]

    running = True
    try:
        while running:
            if not final_args.headless:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and not final_args.auto:
                        client.local_transform.position = screen_to_world(event.pos)

            client.tick()

            if not final_args.headless and screen:
                screen.fill(COLOR_BACKGROUND)
                dynamic_grid = GRID_SPACING
                while dynamic_grid * scale < 20:
                    dynamic_grid *= 2

                for i in range(0, int(final_args.world_size) + dynamic_grid, dynamic_grid):
                    pygame.draw.line(screen, COLOR_GRID, world_to_screen((i, 0)), world_to_screen((i, final_args.world_size)))
                for i in range(0, int(final_args.world_size) + dynamic_grid, dynamic_grid):
                    pygame.draw.line(screen, COLOR_GRID, world_to_screen((0, i)), world_to_screen((final_args.world_size, i)) )

                sorted_peers = []
                for pid, p in client.peers.items():
                    dx = p.position[0] - client.local_transform.position[0]
                    dy = p.position[1] - client.local_transform.position[1]
                    dz = p.position[2] - client.local_transform.position[2]
                    dist = math.sqrt(dx * dx + dy * dy + dz * dz)
                    color = COLOR_PEER
                    if pid in client.visible_nodes: color = COLOR_SELF
                    elif pid in client.connected_nodes: color = COLOR_NEIGHBOR
                    sorted_peers.append((dist, pid, p, color))

                sorted_peers.sort(key=lambda x: x[0], reverse=True)

                display_count = 0
                self_screen_pos = world_to_screen(client.local_transform.position)
                for dist, pid, p, color in sorted_peers:
                    if display_count >= final_args.visible_count: break

                    from mist import MistTransform
                    pos = p.position if isinstance(p, MistTransform) else [p["x"], p["y"], p.get("z", 0.0)]
                    screen_pos = world_to_screen(pos)
                    pygame.draw.circle(screen, color, screen_pos, PEER_RADIUS)

                    label = font.render(pid[:TRUNCATE_ID_LENGTH], True, COLOR_LABEL)
                    screen.blit(label, (screen_pos[0] + LABEL_OFFSET_X, screen_pos[1] + LABEL_OFFSET_Y))
                    display_count += 1

                pygame.draw.circle(screen, COLOR_SELF, self_screen_pos, SELF_RADIUS)
                info_text = [
                    f"ID: {final_args.id}",
                    f"Room: {final_args.room}",
                    f"Pos: ({client.local_transform.position[0]:.1f}, {client.local_transform.position[1]:.1f}, {client.local_transform.position[2]:.1f})",
                    f"Peers: {len(client.peers)} (Display: {display_count}/{final_args.visible_count})",
                    f"Connections: {len(client.connected_nodes)}",
                    f"Neighbors: {len(client.neighbor_nodes)}"
                ]
                for i, text in enumerate(info_text):
                    surf = font.render(text, True, COLOR_TEXT_INFO)
                    screen.blit(surf, (INFO_MARGIN, INFO_MARGIN + i * 15))

                pygame.display.flip()
                clock.tick(FPS)
            else:
                import time
                time.sleep(max(0, (1.0/FPS) - (time.time() - client.last_time)))
    except KeyboardInterrupt:
        pass
    finally:
        client.leave_all_rooms()
        if not final_args.headless:
            pygame.quit()

if __name__ == "__main__":
    run_simulation()
