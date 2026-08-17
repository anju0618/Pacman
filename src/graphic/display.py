"""
pygameウィンドウの生成・メインループ・全画面の描画を担当するモジュール。

Displayクラスが、状態遷移(GameStateに基づく画面切り替え)・入力処理
・毎フレームの更新と描画・ゴーストのモード管理(Scatter/Chase/
Frightened/Eaten)・当たり判定・HUD表示・チートモードの効果など、
ゲーム全体を統括する「司令塔」の役割を持つ。
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
from src.graphic.sprites import SpriteSet

# ゴーストのクラス(型)から、対応するスプライトキー(src/graphic/sprites.py
# のSPRITE_FILENAMES)への対応表。
GHOST_SPRITE_KEYS: dict[type, str] = {
    Blinky: "blinky",
    Pinky: "pinky",
    Inky: "inky",
    Clyde: "clyde",
}
# Pacmanのスプライトは右向きで描かれているため、実際の進行方向に
# あわせて回転させる角度(度・反時計回り)。LEFTは180度回転だと目の
# 位置まで上下反転してしまうため、回転ではなく左右反転で描く。
PACMAN_ROTATION_DEGREES: dict[Direction, int] = {
    Direction.RIGHT: 0,
    Direction.UP: 90,
    Direction.DOWN: 270,
}

# メインメニューの選択肢(課題要件VI.8: Start Game/View Highscores/
# Instructions/Exitの4つ)。
MENU_OPTIONS = ("Start Game", "View Highscores", "Instructions", "Exit")
# ゲーム終了(勝敗確定)を表す状態の集合。ハイスコア入力画面の表示や
# 入力イベントの振り分けで、この2状態をまとめて扱う箇所が多いため。
END_STATES = (GameState.GAME_OVER, GameState.VICTORY)
# ウィンドウ・セルサイズの上限/下限(迷路が大きくても小さくても
# 見やすいウィンドウサイズに収まるよう調整するための定数)。
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
# EATENゴーストが自分の角（home_position）に帰り着いてから、
# 再びSCATTER/CHASEへ復帰するまでに待機する秒数。
EATEN_RESPAWN_WAIT = 5.0
CHEAT_SPEED_FACTOR = 1.5
CHOMP_INTERVAL = 0.1
# closed -> half -> full open -> half -> (repeat): a natural chomp cycle
# instead of a plain open/closed toggle.
PACMAN_CHOMP_FRAMES = (
    "pacman_closed", "pacman_half", "pacman_open", "pacman_half"
)


class Display:
    """pygameウィンドウ・メインループ・全画面描画を統括するクラス。

    PacmanGameContext(スコア・残機・現在の画面など、レベルをまたいで
    保持したい状態)を受け取り、それに基づいてメニュー・インゲーム・
    ポーズ・ハイスコア・ゲームオーバー/勝利画面の描画と入力処理を
    行う。レベルが変わるたびに迷路・Pacman・ゴースト・パグムは
    _load_level()で作り直されるが、game_context自体は使い回される。
    """

    def __init__(
        self,
        game_context: PacmanGameContext,
        highscore_system: HighScoreSystem | None = None,
    ) -> None:
        """pygameを初期化し、フォント・ハイスコア・最初のレベルを準備する。

        Args:
            game_context: スコア・残機・現在の画面などを保持する
                ゲーム全体の状態オブジェクト。
            highscore_system: 使用するハイスコアシステム。省略時は
                config.highscore_filenameを使って新規作成する
                (テストで差し替えられるように引数化してある)。
        """
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
        self.pacman_chomp_timer = 0.0

        self._load_level()
        self.sprites = SpriteSet()
        self.clock = pygame.time.Clock()
        self.title_font = pygame.font.Font(None, 80)
        self.text_font = pygame.font.Font(None, 50)
        self.small_font = pygame.font.Font(None, 35)

    def _load_level(self) -> None:
        """現在のレベル番号に対応する迷路・キャラクター一式を作り直す。

        新規ゲーム開始時(__init__/_start_game)だけでなく、レベル
        クリア時(advance_to_next_level)にも呼ばれる「レベルの
        初期状態を作る」共通処理。迷路生成・ワープトンネルの穴あけ・
        Pacman/ゴースト/パグムの再配置・ゴーストモードのリセット・
        ウィンドウサイズの再計算まで、1レベル分の初期化を全て行う。
        game_context(スコア・残機など)には触れないため、レベルを
        またいでもスコアや残機は保持される。
        """
        level = self.levels[self.current_level_index]

        # 最初のレベルは設定されたシード、それ以降はランダムに生成する。
        # （MazeGenerator は seed<=0 のとき random.seed() で真の乱数を使う）
        seed = self.config.seed if self.current_level_index == 0 else 0
        self.maze_loader, self.maze_data = self._build_maze(
            level["width"], level["height"], seed
        )
        self.current_level = level["id"]
        self.game_context.current_level = self.current_level
        self.game_context.time_remaining = self.config.level_max_time
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
    def _build_maze(
        width: int, height: int, seed: int
    ) -> tuple[MazeLoader, list[list[int]]]:
        """外部の迷路生成パッケージを呼び出し、失敗時は安全に処理する

        課題要件(V.4)により、割り当てられたA-Maze-ingパッケージが失敗
        した場合はトレースバックでクラッシュせずクリーンに処理しなければ
        ならない。生成(MazeLoaderの構築)だけでなく、そこから通路データ
        を取り出すget_binary_grid()の失敗も同じ経路でカバーする。
        まず指定サイズで生成を試み、失敗したらデフォルトのレベル1サイズ
        で再試行し、それも失敗したら分かりやすいメッセージを出して終了
        する（迷路が無いと起動を継続できないため）。
        """
        try:
            loader = MazeLoader(width=width, height=height, seed=seed)
            return loader, loader.get_binary_grid()
        except Exception as error:
            print(
                f"Maze generation failed for size {width}x{height}: "
                f"{error}"
            )

        fallback_width = DEFAULT_LEVELS[0]["width"]
        fallback_height = DEFAULT_LEVELS[0]["height"]
        try:
            print(
                "Retrying with the default maze size "
                f"{fallback_width}x{fallback_height}."
            )
            loader = MazeLoader(
                width=fallback_width, height=fallback_height, seed=seed
            )
            return loader, loader.get_binary_grid()
        except Exception as fallback_error:
            print(f"Fallback maze generation also failed: {fallback_error}")
            pygame.quit()
            raise SystemExit(1) from fallback_error

    @staticmethod
    def _cell_size_for_maze(width: int, height: int) -> int:
        """迷路の縦横マス数から、ウィンドウ上限に収まる1マスのピクセル数を決める。

        大きい迷路ほどセルを小さくしてウィンドウがMAX_WINDOW_SIZEを
        超えないようにしつつ、MIN_CELL_SIZEより小さくはしない
        (小さすぎると壁や自機が視認できなくなるため)。
        """
        largest_dimension = max(width, height)
        if largest_dimension <= 0:
            return MAX_CELL_SIZE
        return max(
            MIN_CELL_SIZE,
            min(MAX_CELL_SIZE, MAX_WINDOW_SIZE // largest_dimension),
        )

    def _start_game(self) -> None:
        """メインメニューの「Start Game」を選んだ時の処理。

        レベル1から新規ゲームを開始する。game_context.reset_for_new_game()
        でスコア・残機・制限時間をリセットしてから、_load_level()で
        レベル1の迷路を生成する。
        """
        self.current_level_index = 0
        self.game_cleared = False
        self._score_entry_state = None
        self.game_context.reset_for_new_game()
        self._load_level()

    def is_cleared(self) -> bool:
        """このレベルの全パグムを回収し終えたか(レベルクリア条件)を返す。"""
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
        """FRIGHTENED/EATEN/WAITING中でないゴーストを
        現在のScatter/Chase局面へ揃える"""
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            if ghost.mode not in (
                GhostMode.FRIGHTENED, GhostMode.EATEN, GhostMode.WAITING
            ):
                ghost.set_mode(mode)

    def _end_frightened(self) -> None:
        """イジケ状態のゴーストだけを現在の局面へ復帰させる

        _apply_scheduled_mode()はFRIGHTENED中のゴーストを意図的に
        スキップするため、イジケ終了時にそれを呼んでも対象のゴースト
        自身が除外されて永久にFRIGHTENEDのまま止まってしまう。
        """
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            if ghost.mode == GhostMode.FRIGHTENED:
                ghost.set_mode(mode)

    def _advance_ghost_modes(self, delta_time: float) -> None:
        """Scatter/Chaseのスケジュール進行、FRIGHTENEDの残り時間管理、
        および巣で待機中(WAITING)ゴーストの復帰処理を行う"""
        self._advance_waiting_ghosts(delta_time)

        if self.frightened_timer > 0:
            self.frightened_timer -= delta_time
            if self.frightened_timer <= 0:
                self.frightened_timer = 0.0
                self._end_frightened()
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
        """スーパーパグムを食べた時、EATEN/WAITING中でない
        全ゴーストをイジケさせる"""
        self.frightened_timer = FRIGHTENED_DURATION
        for ghost in self.ghosts:
            if ghost.mode not in (GhostMode.EATEN, GhostMode.WAITING):
                ghost.set_mode(GhostMode.FRIGHTENED)

    def _resolve_eaten_ghosts(self) -> None:
        """巣（角）に帰り着いたEATENゴーストをWAITING状態にする。
        実際にScatter/Chaseへ復帰するのは、_advance_waiting_ghosts()が
        EATEN_RESPAWN_WAIT秒待った後に行う。"""
        for ghost in self.ghosts:
            if (
                ghost.mode == GhostMode.EATEN
                and ghost.get_current_grid() == ghost.home_position
            ):
                ghost.set_mode(GhostMode.WAITING)
                ghost.wait_timer = EATEN_RESPAWN_WAIT

    def _advance_waiting_ghosts(self, delta_time: float) -> None:
        """巣（角）で待機中(WAITING)のゴーストのタイマーを進め、
        EATEN_RESPAWN_WAIT秒経過したら現在の局面へ復帰させる"""
        mode, _ = SCATTER_CHASE_SCHEDULE[self.mode_schedule_index]
        for ghost in self.ghosts:
            if ghost.mode != GhostMode.WAITING:
                continue
            ghost.wait_timer -= delta_time
            if ghost.wait_timer <= 0:
                ghost.set_mode(mode)

    def _check_ghost_collisions(self) -> None:
        """Pacmanとゴーストの円同士の当たり判定"""
        for ghost in self.ghosts:
            if ghost.mode in (GhostMode.EATEN, GhostMode.WAITING):
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
            ghost.wait_timer = 0.0
            ghost.set_mode(mode)

        self.game_context.time_remaining = self.config.level_max_time

    def _apply_tunnel_wrap(self, character: Character) -> None:
        """トンネル行の端まで来たキャラクターを反対側へ運ぶ

        マス目の範囲外は常に壁として扱われる（Character._collides_with_wall）
        ため、x座標が実際に0未満やwidth以上へ到達することはない。従って
        「範囲外に出たら戻す」という判定では発火せず、キャラクターは端で
        物理的にブロックされて詰まったままになる。ここでは範囲外に出る
        のを待たず、端のマスで外向きに壁へ突き当たった時点でワープする。
        """
        if round(character.y) != self.tunnel_row:
            return

        width = len(self.maze_data[0])
        if (
            character.direction == Direction.LEFT
            and character.x <= character.radius
        ):
            character.x = float(width - 1)
        elif (
            character.direction == Direction.RIGHT
            and character.x >= width - 1 - character.radius
        ):
            character.x = 0.0

    def _ensure_score_entry(self) -> None:
        """GAME_OVER/VICTORY画面に初めて入った時だけ、名前入力欄をリセットする。

        _render_end_screen()や_handle_event()の冒頭で毎フレーム呼ばれる
        が、同じ終了状態(_score_entry_state)にいる間は何もしない。
        こうすることで、名前を入力している途中で毎フレームリセット
        されてしまう(入力できなくなる)のを防いでいる。
        """
        state = self.game_context.state
        if state not in END_STATES or self._score_entry_state is state:
            return
        self._score_entry_state = state
        self.name_input = ""
        self.input_error = ""
        self.score_message = ""
        self.score_submitted = False

    def _submit_highscore(self) -> None:
        """入力された名前で現在のスコアをハイスコアに登録する。

        名前が不正、またはHighScoreSystem.saveが失敗した場合は
        (エラーメッセージ/元の状態への復元も含めて)ユーザーに
        分かる形でフィードバックし、クラッシュしない。
        """
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
        """メインメニュー表示中のキー入力を処理する。

        上下キーで選択項目を移動し、Enterで決定する。「Exit」を
        選ぶかEscを押すとFalseを返し、run()のメインループを終了させる。

        Returns:
            ゲームを続行するならTrue、終了するならFalse。
        """
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
        """ゲームオーバー/勝利画面での名前入力・確定操作を処理する。

        スコア送信済みならEnterでメインメニューへ戻る。未送信なら
        BackSpaceで1文字削除、Enterで送信、それ以外の半角英数字/
        スペースの入力は名前欄(最大10文字)へ追加する
        (課題要件のプレイヤー名バリデーションに合わせて、
        ASCII英数字とスペース以外は最初から受け付けない)。
        """
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
        """1件のpygameイベントを、現在の画面(GameState)に応じて振り分ける。

        ウィンドウを閉じるイベント(QUIT)を受けたらFalseを返して
        メインループを終了させる。キー入力以外のイベントは無視する。
        キー入力は現在のGameStateに応じてメニュー操作・移動入力・
        ポーズ操作・名前入力などへ振り分ける。

        Returns:
            ゲームを続行するならTrue、終了するならFalse。
        """
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
        """指定y座標に、テキストを画面の水平中央揃えで描画する。

        Args:
            text: 描画する文字列。
            y: 描画するy座標(上端)。
            color: 文字色(RGB)。省略時は白。
            font: 使用するフォント。省略時はself.text_font。
        """
        rendered = (font or self.text_font).render(text, True, color)
        x = (self.screen.get_width() - rendered.get_width()) // 2
        self.screen.blit(rendered, (x, y))

    def _highscore_entry_layout(
        self, start_y: int, end_y: int
    ) -> tuple[pygame.font.Font, int]:
        """ハイスコア一覧を指定範囲に収めるためのフォント・行間を計算する。

        表示件数(最大10件)や画面の高さは状況によって変わるため、
        固定のフォントサイズだと項目数が多い時に画面からはみ出したり
        重なったりする。ここでは、指定された縦幅(start_y〜end_y)に
        全件がちょうど収まるよう、フォントサイズを動的に縮小する。

        Args:
            start_y: 一覧の描画開始y座標。
            end_y: 一覧を収めたい終了y座標。

        Returns:
            (使用するフォント, 行間のピクセル数)のタプル。
        """
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
        """メインメニュー画面を描画する(課題要件VI.8)。

        現在選択中の項目(self.menu_index)だけ黄色でハイライトする。
        """
        self.screen.fill((0, 0, 0))
        self._draw_centered("Pac-Man", 45, (255, 255, 0), self.title_font)
        for index, option in enumerate(MENU_OPTIONS):
            color = (255, 255, 0) if index == self.menu_index else (
                255, 255, 255
            )
            self._draw_centered(option, 120 + index * 45, color)

    def _render_highscores(self) -> None:
        """ハイスコア一覧画面を描画する(課題要件VI.8: View Highscores)。"""
        self.screen.fill((0, 0, 0))
        title_y = 20
        footer_y = (
            self.screen.get_height() - self.small_font.get_height() - 10
        )
        entries_start_y = title_y + self.title_font.get_height() + 15
        entries_end_y = footer_y - 10
        entry_font, row_spacing = self._highscore_entry_layout(
            entries_start_y, entries_end_y
        )
        self._draw_centered(
            "High Scores", title_y, (255, 255, 0), self.title_font
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
        """順位・名前・スコアの3列を中央揃えの表として描画する。

        ハイスコア画面(_render_highscores)とゲーム終了画面
        (_render_end_screen)の両方から呼ばれる共通描画処理。
        1件も無い場合は「No scores yet」とだけ表示する。各列の幅は
        実際に表示する文字列から動的に計算し、表全体を画面中央に
        配置する(順位は右詰め、名前は左詰め、スコアは右詰め)。

        Args:
            start_y: 1件目を描画するy座標。
            row_spacing: 1件ごとの行間(ピクセル)。
            font: 使用するフォント。省略時はself.small_font。
        """
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
        """操作説明画面を描画する(課題要件VI.8: Instructions)。

        チートモード有効時は、専用のキー操作(F/N)の説明も追加表示する。
        """
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
        """ポーズ画面を描画する(課題要件VI.8: Resume / Return to main menu)。"""
        self.screen.fill((0, 0, 0))
        self._draw_centered("Paused", 90, (255, 255, 0), self.title_font)
        self._draw_centered("Enter or Esc: Resume", 170)
        self._draw_centered("M: Return to main menu", 215)

    def _render_end_screen(self) -> None:
        """ゲームオーバー/勝利画面を描画する(課題要件VI.8)。

        スコア送信前は名前入力フォームを、送信後は結果メッセージと
        更新後のハイスコア一覧を表示する。勝利時は見出しの下に
        祝福メッセージを追加する。
        """
        self._ensure_score_entry()
        self.screen.fill((0, 0, 0))
        is_victory = self.game_context.state == GameState.VICTORY
        heading = "Victory" if is_victory else "Game Over"
        heading_y = 20
        self._draw_centered(heading, heading_y, (255, 255, 0), self.title_font)

        content_top = heading_y + self.title_font.get_height() + 8
        if is_victory:
            self._draw_centered(
                "Congratulations, you cleared every level!",
                content_top, font=self.small_font,
            )
            content_top += self.small_font.get_height() + 8

        if self.score_submitted:
            score_y = content_top
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
            score_y = content_top + 10
            self._draw_centered(
                f"Final score: {self.game_context.score}", score_y
            )
            self._draw_centered(
                "Enter your name:", score_y + 50, font=self.small_font
            )
            self._draw_centered(f"> {self.name_input}_", score_y + 85)
            if self.input_error:
                self._draw_centered(
                    self.input_error, score_y + 130,
                    (255, 80, 80), self.small_font
                )

    def _draw_pacgums(self) -> None:
        """迷路上に残っている通常パグムとスーパーパグムを描画する。"""
        pacgum_sprite = self.sprites.get("pacgum", self.cell_size)
        for x, y in self.pacgum.normal_positions:
            self.screen.blit(
                pacgum_sprite, (x * self.cell_size, y * self.cell_size)
            )

        super_sprite = self.sprites.get("super_pacgum", self.cell_size)
        for x, y in self.pacgum.super_positions:
            self.screen.blit(
                super_sprite, (x * self.cell_size, y * self.cell_size)
            )

    def _draw_hud(self) -> None:
        """スコア・残機・レベル・残り時間を画面左上に常時表示する。

        課題要件VI.8のIn-Game HUD(常に表示すべき4項目)に対応する。
        """
        status = (
            f"Score: {self.game_context.score}  "
            f"Lives: {self.game_context.lives}  "
            f"Level: {self.current_level}  "
            f"Time: {max(0, int(self.game_context.time_remaining))}"
        )
        rendered = self.small_font.render(status, True, (255, 255, 255))
        self.screen.blit(rendered, (6, 4))

    def _render_game(self) -> None:
        """インゲーム中の1フレーム分の更新と描画を全て行う。

        毎フレーム、以下の順序で処理する。

        1. 壁を描画する。
        2. 経過時間(delta_time)を計算し、残り時間を減らす。
           0以下になったらライフを失う処理(_handle_life_lost)を
           呼び、ゲームオーバーになっていればここで打ち切る。
        3. ゴーストのモード(Scatter/Chase/Frightened)のスケジュールを
           進める(_advance_ghost_modes)。
        4. Pacmanを移動させ、ワープトンネルの処理をし、実際に動いた
           かどうかでパクパクアニメーションのタイマーを進める。
        5. Pacmanの現在マスのパグムを回収し、加点する。スーパーパグム
           ならゴーストをイジケさせる(_trigger_frightened)。
        6. 全パグムを回収し終えていれば次のレベルへ進み、この
           フレームの残りの処理は打ち切る。
        7. (凍結されていなければ)ゴーストを移動させ、ワープトンネル
           処理と、巣に帰り着いたEATENゴーストの復帰処理を行う。
        8. Pacmanとゴーストの当たり判定を行う。ここでライフを失って
           ゲームオーバーになっていれば打ち切る。
        9. パグム・Pacman・ゴースト・HUDを描画する。

        このように「更新」と「描画」を1つのメソッドにまとめている
        のは、ライフロスやレベルクリアなど、フレームの途中で処理を
        打ち切りたいケースが多く、更新と描画を分離すると打ち切り
        タイミングの整合を取るのが逆に複雑になるため。
        """
        self.screen.fill((0, 0, 0))

        wall_sprite = self.sprites.get("wall", self.cell_size)
        for y, row in enumerate(self.maze_data):
            for x, cell in enumerate(row):
                if cell == 1:
                    self.screen.blit(
                        wall_sprite,
                        (x * self.cell_size, y * self.cell_size),
                    )

        delta_time = self.clock.get_time() / 1000.0

        self.game_context.time_remaining -= delta_time
        if self.game_context.time_remaining <= 0:
            self._handle_life_lost()
            if self.game_context.state != GameState.IN_GAME:
                return

        self._advance_ghost_modes(delta_time)

        position_before_move = (self.pacman.x, self.pacman.y)
        self.pacman.update(self.maze_data)
        self._apply_tunnel_wrap(self.pacman)
        if (self.pacman.x, self.pacman.y) != position_before_move:
            self.pacman_chomp_timer += delta_time
        else:
            self.pacman_chomp_timer = 0.0

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

        chomp_phase = (
            int(self.pacman_chomp_timer / CHOMP_INTERVAL)
            % len(PACMAN_CHOMP_FRAMES)
        )
        pacman_sprite_key = PACMAN_CHOMP_FRAMES[chomp_phase]
        pacman_sprite = self.sprites.get(pacman_sprite_key, self.cell_size)
        if self.pacman.direction == Direction.LEFT:
            rotated_pacman = pygame.transform.flip(pacman_sprite, True, False)
        else:
            rotated_pacman = pygame.transform.rotate(
                pacman_sprite, PACMAN_ROTATION_DEGREES[self.pacman.direction]
            )
        pac_px = self.pacman.x * self.cell_size + self.cell_size / 2
        pac_py = self.pacman.y * self.cell_size + self.cell_size / 2
        self.screen.blit(
            rotated_pacman, rotated_pacman.get_rect(center=(pac_px, pac_py))
        )

        for ghost in self.ghosts:
            if ghost.mode == GhostMode.FRIGHTENED:
                sprite_key = "frightened"
            elif ghost.mode in (GhostMode.EATEN, GhostMode.WAITING):
                sprite_key = "eaten"
            else:
                sprite_key = GHOST_SPRITE_KEYS[type(ghost)]
            ghost_sprite = self.sprites.get(sprite_key, self.cell_size)
            ghost_px = ghost.x * self.cell_size + self.cell_size / 2
            ghost_py = ghost.y * self.cell_size + self.cell_size / 2
            self.screen.blit(
                ghost_sprite,
                ghost_sprite.get_rect(center=(ghost_px, ghost_py)),
            )

        self._draw_hud()

    def run(self) -> None:
        """
        main loop

        課題要件(III.1)により、未処理の例外によるクラッシュは許されない。
        1フレームの描画・更新処理のどこかで想定外の例外が起きても、
        トレースバックを出さずにメッセージを出して安全に終了する。
        pygame.quit()は正常終了・異常終了のどちらでも必ず呼ぶ。
        """
        running = True

        try:
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
        except Exception as error:
            print(f"Unexpected error, shutting down cleanly: {error}")
        finally:
            pygame.quit()


if __name__ == "__main__":
    config = Config()
    game_context = PacmanGameContext(config=config)
    game_display = Display(game_context)
    game_display.run()
