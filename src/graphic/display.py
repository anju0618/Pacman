"""
display config mod
"""
import pygame
from src.maze_loader import MazeLoader
from src.character.pacman import Pacman
from src.character.ghost import Ghost
from src.character.blinky import Blinky
from src.character.pinky import Pinky
from src.character.inky import Inky
from src.character.clyde import Clyde
from src.enums import Direction

GHOST_COLORS: dict[type, tuple[int, int, int]] = {
    Blinky: (255, 0, 0),
    Pinky: (255, 184, 255),
    Inky: (0, 255, 255),
    Clyde: (255, 184, 82),
}


class Display:

    def __init__(
        self,
        maze_width: int = 28,
        maze_height: int = 31,
        level: int = 1
    ) -> None:
        pygame.init()

        # 最初のレベルのみ固定シード、以降はランダム
        # （MazeGenerator は seed<=0 のとき random.seed() で真の乱数を使う）
        seed = 42 if level == 1 else 0
        self.maze_loader = MazeLoader(
            width=maze_width, height=maze_height, seed=seed
        )
        self.maze_data = self.maze_loader.get_binary_grid()

        start_x, start_y = self.maze_loader.find_center_start_position()
        self.pacman = Pacman(float(start_x), float(start_y))

        corners = self.maze_loader.find_corner_positions()
        ghost_classes = (Blinky, Pinky, Inky, Clyde)
        self.ghosts: list[Ghost] = [
            ghost_cls(float(corner_x), float(corner_y))
            for ghost_cls, (corner_x, corner_y)
            in zip(ghost_classes, corners)
        ]

        self.cell_size = 20

        screen_width = len(self.maze_data[0]) * self.cell_size
        screen_height = len(self.maze_data) * self.cell_size
        self.screen = pygame.display.set_mode((screen_width, screen_height))

        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()

    def run(self) -> None:
        """
        main loop
        """
        running = True

        while running:

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP or event.key == pygame.K_w:
                        self.pacman.set_direction(Direction.UP)
                    elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                        self.pacman.set_direction(Direction.DOWN)
                    elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                        self.pacman.set_direction(Direction.LEFT)
                    elif (
                        event.key == pygame.K_RIGHT or event.key == pygame.K_d
                            ):
                        self.pacman.set_direction(Direction.RIGHT)

            self.screen.fill((0, 0, 0))

            for y, row in enumerate(self.maze_data):
                for x, cell in enumerate(row):

                    if cell == 1:
                        rect = (
                            x * self.cell_size,
                            y * self.cell_size,
                            self.cell_size,
                            self.cell_size
                            )
                        pygame.draw.rect(self.screen, (0, 0, 255), rect)

            self.pacman.update(self.maze_data)
            pac_px = int(self.pacman.x * self.cell_size + self.cell_size / 2)
            pac_py = int(self.pacman.y * self.cell_size + self.cell_size / 2)
            # 当たり判定(self.pacman.radius)と同じ半径で描くことで、
            # 壁ギリギリで止まった時に見た目が壁にめり込まないようにする
            radius = int(self.pacman.radius * self.cell_size)
            pygame.draw.circle(
                self.screen, (255, 255, 0), (pac_px, pac_py), radius
            )

            for ghost in self.ghosts:
                ghost.update(self.pacman, self.maze_data)
                ghost_px = int(ghost.x * self.cell_size + self.cell_size / 2)
                ghost_py = int(ghost.y * self.cell_size + self.cell_size / 2)
                ghost_radius = int(ghost.radius * self.cell_size)
                color = GHOST_COLORS[type(ghost)]
                pygame.draw.circle(
                    self.screen, color, (ghost_px, ghost_py), ghost_radius
                )

            self.clock.tick(60)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    game_display = Display()
    game_display.run()
