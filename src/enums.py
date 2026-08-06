"""
module difining classes something do with game
"""
# src/enums.py
from enum import Enum, auto


class GameState(Enum):
    """ゲーム全体の進行状態を管理する"""
    MAIN_MENU = auto()
    IN_GAME = auto()
    PAUSED = auto()
    LEVEL_CLEARED = auto()
    GAME_OVER = auto()
    VICTORY = auto()


class Direction(Enum):
    """キャラクターの移動方向"""
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


class GhostType(Enum):
    """ゴーストの種類と性格"""
    BLINKY = auto()  # 赤 / オイカケ
    PINKY = auto()   # ピンク / マチブセ
    INKY = auto()    # 水色 / キマグレ
    CLYDE = auto()   # オレンジ / オトボケ
