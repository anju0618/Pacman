"""
module defining game state class
"""
# src/game_state.py
from dataclasses import dataclass
from src.enums import GameState


@dataclass
class PacmanGameContext:
    """ゲーム進行に必要な現在のコンテキスト（状態）を保持する"""
    state: GameState = GameState.MAIN_MENU
    current_level: int = 1
    score: int = 0
    lives: int = 3  # 初期残機要件
    time_remaining: float = 90.0  # デフォルトの時間制限
    is_cheat_mode_active: bool = False  # チートモードのフラグ

    def reset_for_new_game(
            self,
            starting_lives: int = 3,
            level_time: float = 90.0
            ) -> None:
        """新規ゲーム開始時に状態を初期化する"""
        self.state = GameState.IN_GAME
        self.current_level = 1
        self.score = 0
        self.lives = starting_lives
        self.time_remaining = level_time

    def lose_life(self) -> None:
        """残機を減らし、ゲームオーバー判定を行う"""
        self.lives -= 1
        if self.lives <= 0:
            self.state = GameState.GAME_OVER

    def add_score(self, points: int) -> None:
        """スコアを加算する（スコアは減少しない要件）"""
        if points > 0:
            self.score += points
