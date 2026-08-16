# src/game_state.py
"""
ゲームの進行状況(スコア・残機・現在の画面など)を保持するモジュール。

PacmanGameContextは、レベル遷移(Display._load_level)をまたいでも
保持し続けたい値を1箇所にまとめたもの。レベルが変わるたびにDisplayは
再構築されるが、このオブジェクト自体は使い回されるので、スコアや
残機がレベルをまたいでリセットされずに引き継がれる。
"""

from dataclasses import dataclass
from src.enums import GameState
from src.parse import Config


@dataclass
class PacmanGameContext:
    """ゲーム進行に必要な現在の状態を保持するクラス。

    Displayが画面(メニュー/インゲーム/ポーズ等)を再構築しても、
    このオブジェクトへの参照は同じものを使い続けるため、スコアや
    残機・チートフラグなどが自然に引き継がれる。
    """

    config: Config
    state: GameState = GameState.MAIN_MENU
    current_level: int = 1
    score: int = 0
    lives: int = 3  # 初期残機要件
    time_remaining: float = 90.0  # デフォルトの時間制限
    is_cheat_mode_active: bool = False  # チートモードのフラグ

    # チートモード(--cheat)有効時に、通常の初期残機へ上乗せするボーナス。
    CHEAT_EXTRA_LIVES = 2

    def reset_for_new_game(self) -> None:
        """メインメニューから「Start Game」を選んだ時の初期化処理。

        スコア・レベル・残機・制限時間をconfigの値へ戻し、状態を
        IN_GAMEにする。チートモードが有効な場合は、残機に
        CHEAT_EXTRA_LIVES分のボーナスを追加する
        (課題要件のチート機能「Extra lives」に対応)。
        """
        self.state = GameState.IN_GAME
        self.current_level = 1
        self.score = 0
        self.lives = self.config.lives
        if self.is_cheat_mode_active:
            self.lives += self.CHEAT_EXTRA_LIVES
        self.time_remaining = self.config.level_max_time

    def lose_life(self) -> None:
        """残機を1つ減らし、0以下になったらゲームオーバー状態にする。"""
        self.lives -= 1
        if self.lives <= 0:
            self.state = GameState.GAME_OVER

    def add_score(self, points: int) -> None:
        """スコアを加算する(課題要件: スコアは減少しない)。

        pointsが0以下の場合は何もしない(誤って減点を渡しても
        スコアが減らないようにするための安全策)。
        """
        if points > 0:
            self.score += points
