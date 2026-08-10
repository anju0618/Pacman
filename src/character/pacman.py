"""
pacman mod
"""
from src.character.base import Character
from src.enums import Direction


class Pacman(Character):
    def __init__(self, x: float, y: float) -> None:
        super().__init__(x, y)
        self.direction = Direction.RIGHT

    def set_direction(self, direction: Direction) -> None:
        """ 入力された方向を予約する"""
        self.next_direction = direction

    def update(self, maze_data: list[list[int]]) -> None:
        """毎フレーム呼ばれる更新処理"""
        self.move_forward(maze_data)
