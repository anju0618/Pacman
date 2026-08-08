"""
pacman mod
"""
from src.character.base import Character
from src.enums import Direction


class Pacman(Character):

    def __init__(self, x: float, y: float):
        super().__init__(x, y)
        self.direction = Direction.RIGHT

    def set_direction(self, direction: Direction):
        """プレイヤーからの入力方向を受け取る"""
        self.direction = direction

    def update(self, maze_data: list[list[int]]):
        """毎フレーム呼ばれる更新処理"""
        self.move_forward(maze_data)

