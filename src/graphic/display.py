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
from src.enums import Direction, GameState
from src.game_state import PacmanGameContext
from src.highscore import HighScoreSystem
from src.parse import Config, DEFAULT_LEVELS

GHOST_COLORS: dict[type, tuple[int, int, int]] = {
    Blinky: (255, 0, 0),
    Pinky: (255, 184, 255),
    Inky: (0, 255, 255),
    Clyde: (255, 184, 82),
}

MENU_OPTIONS = ("Start Game", "View Highscores", "Instructions", "Exit")
END_STATES = (GameState.GAME_OVER, GameState.VICTORY)
MAX_WINDOW_SIZE = 800
MAX_CELL_SIZE = 30
MIN_CELL_SIZE = 8


class Display:

    def __init__(
        self,
        game_context: PacmanGameContext,
        highscore_system: HighScoreSystem | None = None,
    ) -> None:
        pygame.init()

        self.game_context = game_context
        self.config = game_context.config
        self.highscores = highscore_system or HighScoreSystem(
            self.config.highscore_filename
        )
        self.highscores.load()
        self.levels = list(self.config.level) or [DEFAULT_LEVELS[0].copy()]
        self.current_level_index = 0
        self.current_level = self.levels[0]["id"]
        self.game_cleared = False
        self.cell_size = MAX_CELL_SIZE
        self.menu_index = 0
        self.name_input = ""
        self.input_error = ""
        self.score_message = ""
        self.score_submitted = False
        self._score_entry_state: GameState | None = None

        self._load_level()
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 48)
        self.text_font = pygame.font.Font(None, 32)
        self.small_font = pygame.font.Font(None, 24)

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
        self.game_context.current_level = self.current_level
        self.cell_size = self._cell_size_for_maze(
            len(self.maze_data[0]), len(self.maze_data)
        )

        start_x, start_y = self.maze_loader.find_center_start_position()
        self.pacman = Pacman(float(start_x), float(start_y))

        corners = self.maze_loader.find_corner_positions()
        self.goal_position = corners[-1]
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

    @staticmethod
    def _cell_size_for_maze(width: int, height: int) -> int:
        """Choose a cell size within the window limit."""
        largest_dimension = max(width, height)
        if largest_dimension <= 0:
            return MAX_CELL_SIZE
        return max(
            MIN_CELL_SIZE,
            min(MAX_CELL_SIZE, MAX_WINDOW_SIZE // largest_dimension),
        )

    def _start_game(self) -> None:
        self.current_level_index = 0
        self.game_cleared = False
        self._score_entry_state = None
        self.game_context.reset_for_new_game()
        self._load_level()

    def is_cleared(self) -> bool:
        """Return whether Pac-Man reached the bottom-right passage."""
        return self.pacman.get_current_grid() == self.goal_position

    def advance_to_next_level(self) -> bool:
        """クリア判定後にConfigの次の迷路へ進む。"""
        next_level_index = self.current_level_index + 1
        if next_level_index >= len(self.levels):
            self.game_cleared = True
            self.game_context.state = GameState.VICTORY
            return False

        self.current_level_index = next_level_index
        self._load_level()
        return True

    def _ensure_score_entry(self) -> None:
        state = self.game_context.state
        if state not in END_STATES or self._score_entry_state is state:
            return
        self._score_entry_state = state
        self.name_input = ""
        self.input_error = ""
        self.score_message = ""
        self.score_submitted = False

    def _submit_highscore(self) -> None:
        if not self.highscores.is_valid_name(self.name_input):
            self.input_error = "Use 1-10 letters, digits, or spaces."
            return

        previous_entries = list(self.highscores.entries)
        try:
            retained = self.highscores.add(
                self.name_input, self.game_context.score
            )
        except ValueError as error:
            self.input_error = str(error)
            return
        if not self.highscores.save():
            self.highscores.entries = previous_entries
            self.score_message = "The score could not be saved."
        elif retained:
            self.score_message = "Score saved in the top 10."
        else:
            self.score_message = "Score submitted outside the top 10."
        self.input_error = ""
        self.score_submitted = True

    def _handle_main_menu_event(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_UP:
            self.menu_index = (self.menu_index - 1) % len(MENU_OPTIONS)
        elif event.key == pygame.K_DOWN:
            self.menu_index = (self.menu_index + 1) % len(MENU_OPTIONS)
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.menu_index == 0:
                self._start_game()
            elif self.menu_index == 1:
                self.game_context.state = GameState.HIGHSCORES
            elif self.menu_index == 2:
                self.game_context.state = GameState.INSTRUCTIONS
            else:
                return False
        elif event.key == pygame.K_ESCAPE:
            return False
        return True

    def _handle_end_event(self, event: pygame.event.Event) -> None:
        if self.score_submitted:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.game_context.state = GameState.MAIN_MENU
            return

        if event.key == pygame.K_BACKSPACE:
            self.name_input = self.name_input[:-1]
            self.input_error = ""
        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            self._submit_highscore()
        elif len(self.name_input) < 10:
            character = event.unicode
            if character.isascii() and (
                character.isalnum() or character == " "
            ):
                self.name_input += character
                self.input_error = ""

    def _handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.QUIT:
            return False
        if event.type != pygame.KEYDOWN:
            return True

        state = self.game_context.state
        if state == GameState.MAIN_MENU:
            return self._handle_main_menu_event(event)
        if state in (GameState.HIGHSCORES, GameState.INSTRUCTIONS):
            if event.key in (
                pygame.K_ESCAPE,
                pygame.K_RETURN,
                pygame.K_KP_ENTER,
            ):
                self.game_context.state = GameState.MAIN_MENU
        elif state == GameState.IN_GAME:
            if event.key == pygame.K_UP or event.key == pygame.K_w:
                self.pacman.set_direction(Direction.UP)
            elif event.key == pygame.K_DOWN or event.key == pygame.K_s:
                self.pacman.set_direction(Direction.DOWN)
            elif event.key == pygame.K_LEFT or event.key == pygame.K_a:
                self.pacman.set_direction(Direction.LEFT)
            elif event.key == pygame.K_RIGHT or event.key == pygame.K_d:
                self.pacman.set_direction(Direction.RIGHT)
            elif event.key == pygame.K_ESCAPE:
                self.game_context.state = GameState.PAUSED
        elif state == GameState.PAUSED:
            if event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                self.game_context.state = GameState.IN_GAME
            elif event.key == pygame.K_m:
                self.game_context.state = GameState.MAIN_MENU
        elif state in END_STATES:
            self._ensure_score_entry()
            self._handle_end_event(event)
        return True

    def _draw_centered(
        self,
        text: str,
        y: int,
        color: tuple[int, int, int] = (255, 255, 255),
        font: pygame.font.Font | None = None,
    ) -> None:
        rendered = (font or self.text_font).render(text, True, color)
        x = (self.screen.get_width() - rendered.get_width()) // 2
        self.screen.blit(rendered, (x, y))

    def _render_main_menu(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_centered("Pac-Man", 45, (255, 255, 0), self.title_font)
        for index, option in enumerate(MENU_OPTIONS):
            color = (255, 255, 0) if index == self.menu_index else (
                255, 255, 255
            )
            self._draw_centered(option, 120 + index * 45, color)

    def _render_highscores(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_centered("High Scores", 35, (255, 255, 0), self.title_font)
        row_spacing = min(
            28, max(18, (self.screen.get_height() - 130) // 10)
        )
        self._draw_highscore_entries(70, row_spacing)
        self._draw_centered(
            "Enter or Esc: back", self.screen.get_height() - 35,
            font=self.small_font
        )

    def _draw_highscore_entries(self, start_y: int, row_spacing: int) -> None:
        if not self.highscores.entries:
            self._draw_centered("No scores yet", start_y)
            return

        for index, entry in enumerate(self.highscores.entries, start=1):
            line = f"{index:2}. {entry.name:<10} {entry.score:>8}"
            self._draw_centered(
                line, start_y + index * row_spacing, font=self.small_font
            )

    def _render_instructions(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_centered("Instructions", 50, (255, 255, 0), self.title_font)
        instructions = (
            "Arrow keys / WASD: move",
            "Esc: pause",
            "Eat every pacgum and avoid ghosts.",
            "Enter or Esc: back",
        )
        for index, line in enumerate(instructions):
            self._draw_centered(line, 125 + index * 38, font=self.small_font)

    def _render_pause(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_centered("Paused", 90, (255, 255, 0), self.title_font)
        self._draw_centered("Enter or Esc: Resume", 170)
        self._draw_centered("M: Return to main menu", 215)

    def _render_end_screen(self) -> None:
        self._ensure_score_entry()
        self.screen.fill((0, 0, 0))
        heading = (
            "Victory"
            if self.game_context.state == GameState.VICTORY
            else "Game Over"
        )
        self._draw_centered(heading, 55, (255, 255, 0), self.title_font)
        if self.score_submitted:
            self._draw_centered(f"Final score: {self.game_context.score}", 80)
            self._draw_centered(self.score_message, 105, font=self.small_font)
            self._draw_centered("High Scores", 135, font=self.small_font)
            row_spacing = min(
                18, max(12, (self.screen.get_height() - 190) // 10)
            )
            self._draw_highscore_entries(145, row_spacing)
            self._draw_centered(
                "Enter: main menu", self.screen.get_height() - 25,
                font=self.small_font
            )
        else:
            self._draw_centered(f"Final score: {self.game_context.score}", 130)
            self._draw_centered("Enter your name:", 180, font=self.small_font)
            self._draw_centered(f"> {self.name_input}_", 215)
            if self.input_error:
                self._draw_centered(
                    self.input_error, 260, (255, 80, 80), self.small_font
                )

    def _render_game(self) -> None:
        self.screen.fill((0, 0, 0))

        for y, row in enumerate(self.maze_data):
            for x, cell in enumerate(row):
                if cell == 1:
                    rect = (
                        x * self.cell_size,
                        y * self.cell_size,
                        self.cell_size,
                        self.cell_size,
                    )
                    pygame.draw.rect(self.screen, (0, 0, 255), rect)

        self.pacman.update(self.maze_data)

        if self.is_cleared():
            self.advance_to_next_level()
            return

        pac_px = int(self.pacman.x * self.cell_size + self.cell_size / 2)
        pac_py = int(self.pacman.y * self.cell_size + self.cell_size / 2)
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

    def run(self) -> None:
        """
        main loop
        """
        running = True

        while running:
            for event in pygame.event.get():
                if not self._handle_event(event):
                    running = False
            if not running:
                break

            state = self.game_context.state
            if state == GameState.MAIN_MENU:
                self._render_main_menu()
            elif state == GameState.HIGHSCORES:
                self._render_highscores()
            elif state == GameState.INSTRUCTIONS:
                self._render_instructions()
            elif state == GameState.IN_GAME:
                self._render_game()
            elif state == GameState.PAUSED:
                self._render_pause()
            elif state in END_STATES:
                self._render_end_screen()

            self.clock.tick(60)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    config = Config()
    game_context = PacmanGameContext(config=config)
    game_display = Display(game_context)
    game_display.run()
