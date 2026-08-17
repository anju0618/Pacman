"""
ゲーム全体で共有するenum(列挙型)をまとめたモジュール。

画面遷移(GameState)、移動方向(Direction)、ゴーストのAIモード
(GhostMode)、ゴーストの種類(GhostType)を定義する。複数のモジュール
から参照される値なので、循環importを避けるためここに集約している。
"""
# src/enums.py
from enum import Enum, auto


class GameState(Enum):
    """ゲーム全体の進行状態(画面)を表す。

    Display.run()のメインループがこの値を見て、どの
    _render_...()/_handle_..._event()を呼ぶかを振り分ける
    (簡易的なステートマシン)。LEVEL_CLEAREDは現状未使用
    (レベルクリア時はそのままIN_GAMEのまま次レベルへ進む)。
    """
    MAIN_MENU = auto()
    HIGHSCORES = auto()
    INSTRUCTIONS = auto()
    IN_GAME = auto()
    PAUSED = auto()
    LEVEL_CLEARED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Direction(Enum):
    """キャラクターの移動方向(上下左右の4方向)。"""
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()


class GhostMode(Enum):
    """ゴーストの現在のAIモード"""
    SCATTER = auto()     # 縄張りを巡回（オリジナル仕様の要件）
    CHASE = auto()       # パックマンを追跡
    FRIGHTENED = auto()  # イジケ状態（逃亡）
    EATEN = auto()       # 目玉になって巣へ帰還中
    WAITING = auto()     # 巣（角）に帰り着き、復活までしばし待機中


class GhostType(Enum):
    """ゴーストの種類と性格"""
    BLINKY = auto()  # 赤 / オイカケ
    PINKY = auto()   # ピンク / マチブセ
    INKY = auto()    # 水色 / キマグレ
    CLYDE = auto()   # オレンジ / オトボケ
