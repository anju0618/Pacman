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
from src.parse import Config, DEFAULT_LEVELS

GHOST_COLORS: dict[type, tuple[int, int, int]] = {
    Blinky: (255, 0, 0),
    Pinky: (255, 184, 255),
    Inky: (0, 255, 255),
    Clyde: (255, 184, 82),
}


class Display:

    def __init__(self, config: Config) -> None:
        pygame.init()

        self.config = config
        self.levels = list(config.level) or [DEFAULT_LEVELS[0].copy()]
        self.current_level_index = 0
        self.current_level = self.levels[0]["id"]
        self.game_cleared = False
        self.cell_size = 30

        self._load_level()
        self.clock = pygame.time.Clock()

    def _load_level(self) -> None:
        level = self.levels[self.current_level_index]

        # 最初のレベルは設定されたシード、それ以降はランダムに生成する。
        # （MazeGenerator は seed<=0 のとき random.seed() で真の乱数を使う）
        seed = self.config.seed if self.current_level_index == 0 else 0
        self.maze_loader = MazeLoader(
            width=level["width"], height=level["height"], seed=seed
        )
        self.maze_data = self.maze_loader.get_binary_grid()
        self.current_level = level["id"]

        start_x, start_y = self.maze_loader.find_center_start_position()
        self.pacman = Pacman(float(start_x), float(start_y))

        corners = self.maze_loader.find_corner_positions()
        ghost_classes = (Blinky, Pinky, Inky, Clyde)
        self.ghosts: list[Ghost] = [
            ghost_cls(float(corner_x), float(corner_y))
            for ghost_cls, (corner_x, corner_y)
            in zip(ghost_classes, corners)
        ]

        screen_width = len(self.maze_data[0]) * self.cell_size
        screen_height = len(self.maze_data) * self.cell_size
        self.screen = pygame.display.set_mode((screen_width, screen_height))

        pygame.display.set_caption(f"Pac-Man - Level {self.current_level}")

    def is_cleared(self) -> bool:
        """現在のレベルがクリアされたかを返す。クリア条件は未実装。"""
        return False

    def advance_to_next_level(self) -> bool:
        """クリア判定後にConfigの次の迷路へ進む。"""
        next_level_index = self.current_level_index + 1
        if next_level_index >= len(self.levels):
            self.game_cleared = True
            return False

        self.current_level_index = next_level_index
        self._load_level()
        return True

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

            if self.is_cleared():
                if not self.advance_to_next_level():
                    running = False
                continue

            pac_px = int(self.pacman.x * self.cell_size + self.cell_size / 2)
            pac_py = int(self.pacman.y * self.cell_size + self.cell_size / 2)
            # 当たり判定(self.pacman.radius)と同じ半径で描くことで、
            # 壁ギリギリで止まった時に見た目が壁にめり込まないようにする
            radius = int(self.pacman.radius * self.cell_size)
            pygame.draw.circle(
                self.screen, (255, 255, 0), (pac_px, pac_py), radius
            )

            for ghost in self.ghosts:
                ghost.update(self.pacman, self.maze_data, self.ghosts)
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
    game_display = Display(Config())
    game_display.run()
