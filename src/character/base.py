"""
MOD difining the base chara class
"""
from src.enums import Direction


class Character:
    """
    chara base class (pac ghost)
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """
        全キャラエンティティはスタート位置を持つ
        """
        self.x: float = start_x
        self.y: float = start_y
        self.direction: Direction = Direction.RIGHT  # デフォルト
        self.speed: float = 0.15  # ピクセル移動用の速度

    def get_current_grid(self) -> tuple[int, int]:
        """
        現在地getter
        """
        return int(self.x + 0.5), int(self.y + 0.5)

    def _collides_with_wall(self, check_x: float, check_y: float, maze_data: list[list[int]]) -> bool:
        """指定した座標に移動したとき、壁(1)にめり込むかを判定する"""
        margin = 0.3
        corners = [
            (check_x - margin, check_y - margin),
            (check_x + margin, check_y - margin),
            (check_x - margin, check_y + margin),
            (check_x + margin, check_y + margin)
        ]

        for cx, cy in corners:
            grid_x, grid_y = int(cx + 0.5), int(cy + 0.5)

            if grid_y < 0 or grid_y >= len(maze_data) or grid_x < 0 or grid_x >= len(maze_data[0]):
                return True
            if maze_data[grid_y][grid_x] == 1:
                return True

        return False

    def move_forward(self, maze_data: list[list[int]]) -> bool:
        """
        directionへspeed分移動を試みる。
        壁にぶつからなければ座標を更新して True を返し、壁なら False を返す。
        """
        next_x = self.x
        next_y = self.y

        if self.direction == Direction.UP:
            next_y -= self.speed
        elif self.direction == Direction.DOWN:
            next_y += self.speed
        elif self.direction == Direction.LEFT:
            next_x -= self.speed
        elif self.direction == Direction.RIGHT:
            next_x += self.speed

        if not self._collides_with_wall(next_x, next_y, maze_data):
            self.x = next_x
            self.y = next_y
            return True

        return False
