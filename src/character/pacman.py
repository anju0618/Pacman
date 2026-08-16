"""
プレイヤーが操作するPacmanクラスを定義するモジュール。
"""
from src.character.base import Character
from src.enums import Direction


class Pacman(Character):
    """プレイヤーキャラクター。移動の物理演算自体はCharacter任せで、
    このクラスは「キー入力で次の方向を予約する」役割だけを持つ。
    """

    # 角を少し内側へ切り込み、Ghostより小さい旋回半径にする
    CORNER_CUT_DISTANCE = 0.08

    def __init__(self, x: float, y: float) -> None:
        """初期位置を受け取り、右向きでスタートする。

        Args:
            x: 開始位置のグリッドx座標(通常は迷路の中心)。
            y: 開始位置のグリッドy座標(通常は迷路の中心)。
        """
        super().__init__(x, y)
        self.direction = Direction.RIGHT

    def set_direction(self, direction: Direction) -> None:
        """入力された方向を次の移動方向として予約する。

        即座に向きを変えるのではなく、Character.move_forward側の
        タイミング(Uターン即時／交差点で曲がる)に従って反映される。
        """
        self.next_direction = direction

    def update(self, maze_data: list[list[int]]) -> None:
        """毎フレーム呼ばれる更新処理。移動処理を1フレーム分進める。"""
        self.move_forward(maze_data)
