"""
display config mod
"""
import pygame
from src.maze_loader import MazeLoader
from src.character.base import Character
from src.character.pacman import Pacman
from src.character.ghost import Ghost
from src.character.blinky import Blinky
from src.character.pinky import Pinky
from src.character.inky import Inky
from src.character.clyde import Clyde
from src.enums import Direction, GameState, GhostMode
from src.game_state import PacmanGameContext
from src.highscore import HighScoreSystem
from src.pacgum import Pacgum, PacgumKind
from src.parse import Config, DEFAULT_LEVELS

GHOST_COLORS: dict[type, tuple[int, int, int]] = {
    Blinky: (255, 0, 0),
    Pinky: (255, 184, 255),
    Inky: (0, 255, 255),
    Clyde: (255, 184, 82),
}
FRIGHTENED_COLOR = (33, 33, 222)
EATEN_COLOR = (200, 200, 200)

MENU_OPTIONS = ("Start Game", "View Highscores", "Instructions", "Exit")
END_STATES = (GameState.GAME_OVER, GameState.VICTORY)
MAX_WINDOW_SIZE = 2000
MAX_CELL_SIZE = 45
MIN_CELL_SIZE = 10

# Scatter/Chaseを交互に切り替えるスケジュール（本家ライクな簡略版）。
# FRIGHTENED中は一時停止し、終了後はこのスケジュールへ復帰する。
SCATTER_CHASE_SCHEDULE: tuple[tuple[GhostMode, float], ...] = (
    (GhostMode.SCATTER, 7.0),
    (GhostMode.CHASE, 20.0),
)
FRIGHTENED_DURATION = 6.0
CHEAT_SPEED_FACTOR = 1.5


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
        self.ghosts_frozen = False

        self._load_level()
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 80)
        self.text_font = pygame.font.Font(None, 50)
        self.small_font = pygame.font.Font(None, 35)

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

        # ワープトンネル: 生成された迷路は外周が常に壁なので、Pacmanの
        # 出発行をまるごと開通させて左右端をトンネルの出入り口にする。
        self.tunnel_row = start_y
        self.maze_data[start_y] = [0] * len(self.maze_data[start_y])

        self.pacman = Pacman(float(start_x), float(start_y))
        if self.game_context.is_cheat_mode_active:
            self.pacman.speed *= CHEAT_SPEED_FACTOR

        corners = self.maze_loader.find_corner_positions()
        ghost_classes = (Blinky, Pinky, Inky, Clyde)
        self.ghosts: list[Ghost] = [
            ghost_cls(float(corner_x), float(corner_y))
            for ghost_cls, (corner_x, corner_y)
            in zip(ghost_classes, corners)
        ]

        self.pacgum = Pacgum(
            maze_data=self.maze_data,
            super_positions=corners,
            excluded_positions=[(start_x, start_y)],
            count=self.config.pacgum,
        )

        self.mode_schedule_index = 0
        self.mode_timer = 0.0
        self.frightened_timer = 0.0
        self._apply_scheduled_mode()

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
        """Return whether every pacgum on this level has been collected."""
        return self.pacgum.is_empty()

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

    def _apply_scheduled_mode(self) -> None:
        """FRIGHTENED/EATEN中でないゴーストを現在のScatter/Chase局面へ揃える"""
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            if ghost.mode not in (GhostMode.FRIGHTENED, GhostMode.EATEN):
                ghost.set_mode(mode)

    def _advance_ghost_modes(self, delta_time: float) -> None:
        """Scatter/Chaseのスケジュール進行、およびFRIGHTENEDの残り時間管理"""
        if self.frightened_timer > 0:
            self.frightened_timer -= delta_time
            if self.frightened_timer <= 0:
                self.frightened_timer = 0.0
                self._apply_scheduled_mode()
            return

        self.mode_timer += delta_time
        _, duration = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        if self.mode_timer >= duration:
            self.mode_timer = 0.0
            self.mode_schedule_index = (
                self.mode_schedule_index + 1
            ) % len(SCATTER_CHASE_SCHEDULE)
            self._apply_scheduled_mode()

    def _trigger_frightened(self) -> None:
        """スーパーパグムを食べた時、EATEN中でない全ゴーストをイジケさせる"""
        self.frightened_timer = FRIGHTENED_DURATION
        for ghost in self.ghosts:
            if ghost.mode != GhostMode.EATEN:
                ghost.set_mode(GhostMode.FRIGHTENED)

    def _resolve_eaten_ghosts(self) -> None:
        """巣に帰り着いたEATENゴーストを現在の局面へ復帰させる"""
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            if (
                ghost.mode == GhostMode.EATEN
                and ghost.get_current_grid() == ghost.home_position
            ):
                ghost.set_mode(mode)

    def _check_ghost_collisions(self) -> None:
        """Pacmanとゴーストの円同士の当たり判定"""
        for ghost in self.ghosts:
            if ghost.mode == GhostMode.EATEN:
                continue

            dx = self.pacman.x - ghost.x
            dy = self.pacman.y - ghost.y
            contact_distance = self.pacman.radius + ghost.radius
            if dx * dx + dy * dy >= contact_distance * contact_distance:
                continue

            if ghost.mode == GhostMode.FRIGHTENED:
                ghost.set_mode(GhostMode.EATEN)
                self.game_context.add_score(self.config.points_per_ghost)
            elif not self.game_context.is_cheat_mode_active:
                self._handle_life_lost()
                return

    def _handle_life_lost(self) -> None:
        """残機を減らし（チート無敵時は減らさず）、初期配置へ戻す"""
        if not self.game_context.is_cheat_mode_active:
            self.game_context.lose_life()
        self._reset_positions()

    def _reset_positions(self) -> None:
        """Pacman・ゴーストを初期位置へ戻し、モード・タイマーをリセットする"""
        start_x, start_y = self.maze_loader.find_center_start_position()
        self.pacman.x, self.pacman.y = float(start_x), float(start_y)
        self.pacman.direction = Direction.RIGHT
        self.pacman.next_direction = None

        self.mode_schedule_index = 0
        self.mode_timer = 0.0
        self.frightened_timer = 0.0
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            home_x, home_y = ghost.home_position
            ghost.x, ghost.y = float(home_x), float(home_y)
            ghost.direction = Direction.RIGHT
            ghost.next_direction = None
            ghost.set_mode(mode)

        self.game_context.time_remaining = self.config.level_max_time

    def _apply_tunnel_wrap(self, character: Character) -> None:
        """トンネル行にいるキャラクターが端まで来たら反対側へ折り返す"""
        if round(character.y) != self.tunnel_row:
            return

        width = len(self.maze_data[0])
        if character.x < -0.5:
            character.x += width
        elif character.x > width - 0.5:
            character.x -= width

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
            elif (
                event.key == pygame.K_f
                and self.game_context.is_cheat_mode_active
            ):
                self.ghosts_frozen = not self.ghosts_frozen
            elif (
                event.key == pygame.K_n
                and self.game_context.is_cheat_mode_active
            ):
                self.advance_to_next_level()
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

    def _highscore_entry_layout(
        self, start_y: int, end_y: int
    ) -> tuple[pygame.font.Font, int]:
        """Return a non-overlapping font and row spacing for high scores."""
        entry_count = len(self.highscores.entries)
        if entry_count == 0:
            return self.small_font, self.small_font.get_linesize()

        available_height = max(1, end_y - start_y)
        if entry_count == 1:
            max_row_spacing = available_height
        else:
            max_row_spacing = max(
                1,
                (available_height - self.small_font.get_height())
                // (entry_count - 1),
            )

        font = self.small_font
        font_size = max(12, max_row_spacing)
        if font.get_linesize() > max_row_spacing:
            font = pygame.font.Font(None, font_size)
            while font.get_linesize() > max_row_spacing and font_size > 12:
                font_size -= 1
                font = pygame.font.Font(None, font_size)

        row_spacing = min(font.get_linesize() + 4, max_row_spacing)
        row_spacing = max(font.get_linesize(), row_spacing)
        return font, row_spacing

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
        title_y = 20
        footer_y = (
            self.screen.get_height() - self.small_font.get_height() - 10
        )
        entries_start_y = title_y + self.small_font.get_height() + 15
        entries_end_y = footer_y - 10
        entry_font, row_spacing = self._highscore_entry_layout(
            entries_start_y, entries_end_y
        )
        self._draw_centered(
            "High Scores", title_y, (255, 255, 0), entry_font
        )
        self._draw_highscore_entries(
            entries_start_y, row_spacing, font=entry_font
        )
        self._draw_centered(
            "Enter or Esc: back", footer_y,
            font=entry_font
        )

    def _draw_highscore_entries(
        self,
        start_y: int,
        row_spacing: int,
        font: pygame.font.Font | None = None,
    ) -> None:
        entry_font = font or self.small_font
        if not self.highscores.entries:
            self._draw_centered("No scores yet", start_y, font=entry_font)
            return

        rank_width = entry_font.size(f"{len(self.highscores.entries):>2}.")[0]
        name_width = max(
            entry_font.size(entry.name)[0]
            for entry in self.highscores.entries
        )
        score_width = max(
            entry_font.size(str(entry.score))[0]
            for entry in self.highscores.entries
        )
        column_gap = entry_font.size("  ")[0]
        table_width = rank_width + column_gap + name_width
        table_width += column_gap + score_width
        table_left = (self.screen.get_width() - table_width) // 2
        name_x = table_left + rank_width + column_gap
        score_right = table_width + table_left

        for index, entry in enumerate(self.highscores.entries):
            y = start_y + index * row_spacing
            rank_surface = entry_font.render(
                f"{index + 1:>2}.", True, (255, 255, 255)
            )
            name_surface = entry_font.render(
                entry.name, True, (255, 255, 255)
            )
            score_surface = entry_font.render(
                str(entry.score), True, (255, 255, 255)
            )
            self.screen.blit(
                rank_surface,
                (table_left + rank_width - rank_surface.get_width(), y),
            )
            self.screen.blit(name_surface, (name_x, y))
            self.screen.blit(
                score_surface,
                (score_right - score_surface.get_width(), y),
            )

    def _render_instructions(self) -> None:
        self.screen.fill((0, 0, 0))
        self._draw_centered("Instructions", 50, (255, 255, 0), self.title_font)
        instructions = (
            "Arrow keys / WASD: move",
            "Esc: pause",
            "Eat every pacgum and avoid ghosts.",
            "Eat a super pacgum to hunt ghosts for a while.",
            "Enter or Esc: back",
        )
        for index, line in enumerate(instructions):
            self._draw_centered(line, 115 + index * 32, font=self.small_font)
        if self.game_context.is_cheat_mode_active:
            self._draw_centered(
                "Cheat: F freezes ghosts, N skips the level",
                115 + len(instructions) * 32 + 20,
                (255, 220, 0), self.small_font
            )

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
        heading_y = 20
        self._draw_centered(heading, heading_y, (255, 255, 0), self.title_font)
        if self.score_submitted:
            score_y = heading_y + self.title_font.get_height() + 8
            message_y = score_y + self.text_font.get_height() + 6
            highscore_title_y = (
                message_y + self.small_font.get_height() + 8
            )
            entries_start_y = (
                highscore_title_y + self.small_font.get_height() + 8
            )
            footer_y = (
                self.screen.get_height() - self.small_font.get_height() - 10
            )
            entries_end_y = footer_y - 8
            entry_font, row_spacing = self._highscore_entry_layout(
                entries_start_y, entries_end_y
            )

            self._draw_centered(
                f"Final score: {self.game_context.score}", score_y
            )
            self._draw_centered(
                self.score_message, message_y, font=self.small_font
            )
            self._draw_centered(
                "High Scores", highscore_title_y, font=entry_font
            )
            self._draw_highscore_entries(
                entries_start_y, row_spacing, font=entry_font
            )
            self._draw_centered(
                "Enter: main menu", footer_y,
                font=entry_font
            )
        else:
            self._draw_centered(f"Final score: {self.game_context.score}", 130)
            self._draw_centered("Enter your name:", 180, font=self.small_font)
            self._draw_centered(f"> {self.name_input}_", 215)
            if self.input_error:
                self._draw_centered(
                    self.input_error, 260, (255, 80, 80), self.small_font
                )

    def _draw_pacgums(self) -> None:
        normal_radius = max(1, int(self.cell_size * 0.16))
        for x, y in self.pacgum.normal_positions:
            px = x * self.cell_size + self.cell_size // 2
            py = y * self.cell_size + self.cell_size // 2
            pygame.draw.circle(
                self.screen, (255, 220, 170), (px, py), normal_radius
            )

        super_radius = max(1, int(self.cell_size * 0.32))
        for x, y in self.pacgum.super_positions:
            px = x * self.cell_size + self.cell_size // 2
            py = y * self.cell_size + self.cell_size // 2
            pygame.draw.circle(
                self.screen, (255, 220, 170), (px, py), super_radius
            )

    def _draw_hud(self) -> None:
        status = (
            f"Score: {self.game_context.score}  "
            f"Lives: {self.game_context.lives}  "
            f"Level: {self.current_level}  "
            f"Time: {max(0, int(self.game_context.time_remaining))}"
        )
        rendered = self.small_font.render(status, True, (255, 255, 255))
        self.screen.blit(rendered, (6, 4))

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

        delta_time = self.clock.get_time() / 1000.0

        self.game_context.time_remaining -= delta_time
        if self.game_context.time_remaining <= 0:
            self._handle_life_lost()
            if self.game_context.state != GameState.IN_GAME:
                return

        self._advance_ghost_modes(delta_time)

        self.pacman.update(self.maze_data)
        self._apply_tunnel_wrap(self.pacman)

        collected = self.pacgum.collect(self.pacman.get_current_grid())
        if collected == PacgumKind.NORMAL:
            self.game_context.add_score(self.config.points_per_pacgum)
        elif collected == PacgumKind.SUPER:
            self.game_context.add_score(self.config.points_per_super_pacgum)
            self._trigger_frightened()

        if self.is_cleared():
            self.advance_to_next_level()
            return

        if not self.ghosts_frozen:
            for ghost in self.ghosts:
                ghost.update(self.pacman, self.maze_data, self.ghosts)
                self._apply_tunnel_wrap(ghost)
        self._resolve_eaten_ghosts()

        self._check_ghost_collisions()
        if self.game_context.state != GameState.IN_GAME:
            return

        self._draw_pacgums()

        pac_px = int(self.pacman.x * self.cell_size + self.cell_size / 2)
        pac_py = int(self.pacman.y * self.cell_size + self.cell_size / 2)
        radius = int(self.pacman.radius * self.cell_size)
        pygame.draw.circle(
            self.screen, (255, 255, 0), (pac_px, pac_py), radius
        )

        for ghost in self.ghosts:
            ghost_px = int(ghost.x * self.cell_size + self.cell_size / 2)
            ghost_py = int(ghost.y * self.cell_size + self.cell_size / 2)
            ghost_radius = int(ghost.radius * self.cell_size)
            if ghost.mode == GhostMode.FRIGHTENED:
                color = FRIGHTENED_COLOR
            elif ghost.mode == GhostMode.EATEN:
                color = EATEN_COLOR
            else:
                color = GHOST_COLORS[type(ghost)]
            pygame.draw.circle(
                self.screen, color, (ghost_px, ghost_py), ghost_radius
            )

        self._draw_hud()

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
