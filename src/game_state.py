# src/game_state.py
"""
module defining game state class
"""

from dataclasses import dataclass
from src.enums import GameState
from src.parse import Config


@dataclass
class PacmanGameContext:
    """ゲーム進行に必要な現在の状態を保持するクラス"""
    config: Config
    state: GameState = GameState.MAIN_MENU
    current_level: int = 1
    score: int = 0
    lives: int = 3  # 初期残機要件
    time_remaining: float = 90.0  # デフォルトの時間制限
    is_cheat_mode_active: bool = False  # チートモードのフラグ

    CHEAT_EXTRA_LIVES = 2

    def reset_for_new_game(self) -> None:
        """新規ゲーム開始時にconfigからロード"""
        self.state = GameState.IN_GAME
        self.current_level = 1
        self.score = 0
        self.lives = self.config.lives
        if self.is_cheat_mode_active:
            self.lives += self.CHEAT_EXTRA_LIVES
        self.time_remaining = self.config.level_max_time

    def lose_life(self) -> None:
        """残機を減らし、ゲームオーバー判定を行う"""
        self.lives -= 1
        if self.lives <= 0:
            self.state = GameState.GAME_OVER

    def add_score(self, points: int) -> None:
        """スコアを加算する（スコアは減少しない要件）"""
        if points > 0:
            self.score += points
