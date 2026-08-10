"""
MOD difining the base chara class
"""
from src.enums import Direction


class Character:
    """
    chara base class (pac ghost)
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        self.x: float = start_x
        self.y: float = start_y
        self.direction: Direction = Direction.RIGHT
        self.next_direction: Direction | None = None
        self.speed: float = 0.15
        # 当たり判定と描画の両方で共有する半径（食い違うと壁にめり込んで見える）
        self.radius: float = 0.45 # 0.45にすると食い込まない

    def get_current_grid(self) -> tuple[int, int]:
        return int(self.x + 0.5), int(self.y + 0.5)

    def _collides_with_wall(
        self,
        check_x: float,
        check_y: float,
        maze_data: list[list[int]]
    ) -> bool:
        """指定した座標のボックスが壁(1)に接触しているかを正確に判定する"""
        radius = self.radius

        left = check_x - radius
        right = check_x + radius
        top = check_y - radius
        bottom = check_y + radius

        min_x = int(left + 0.5)
        max_x = int(right + 0.5)
        min_y = int(top + 0.5)
        max_y = int(bottom + 0.5)

        height = len(maze_data)
        width = len(maze_data[0])

        for gy in range(min_y, max_y + 1):
            for gx in range(min_x, max_x + 1):
                if gy < 0 or gy >= height or gx < 0 or gx >= width:
                    return True
                if maze_data[gy][gx] == 1:
                    return True

        return False

    def move_forward(self, maze_data: list[list[int]]) -> bool:
        # 0. 逆方向への入力なら、いつでも即座にUターンを許可する（本家の超重要テクニック！）
        if self.next_direction is not None:
            is_horizontal_opposite = (
                self.direction in (Direction.LEFT, Direction.RIGHT) and
                self.next_direction in (Direction.LEFT, Direction.RIGHT) and
                self.direction != self.next_direction
            )
            is_vertical_opposite = (
                self.direction in (Direction.UP, Direction.DOWN) and
                self.next_direction in (Direction.UP, Direction.DOWN) and
                self.direction != self.next_direction
            )
            if is_horizontal_opposite or is_vertical_opposite:
                self.direction = self.next_direction
                self.next_direction = None

        if self.next_direction is not None:
            grid_x = round(self.x)
            grid_y = round(self.y)
            offset_x = abs(self.x - grid_x)
            offset_y = abs(self.y - grid_y)

            vertical_to_horizontal = (
                self.direction in (Direction.UP, Direction.DOWN)
                and self.next_direction in (Direction.LEFT, Direction.RIGHT)
            )
            horizontal_to_vertical = (
                self.direction in (Direction.LEFT, Direction.RIGHT)
                and self.next_direction in (Direction.UP, Direction.DOWN)
            )
            is_turning_sideways = (
                vertical_to_horizontal or horizontal_to_vertical
            )

            if is_turning_sideways and (offset_x <= 0.35 and offset_y <= 0.35):
                test_x, test_y = float(grid_x), float(grid_y)
                if self.next_direction == Direction.UP:
                    test_y -= self.speed
                elif self.next_direction == Direction.DOWN:
                    test_y += self.speed
                elif self.next_direction == Direction.LEFT:
                    test_x -= self.speed
                elif self.next_direction == Direction.RIGHT:
                    test_x += self.speed

                if not self._collides_with_wall(test_x, test_y, maze_data):
                    self.direction = self.next_direction
                    self.next_direction = None
                    self.x = float(grid_x)
                    self.y = float(grid_y)

        # 2. 現在の方向へ進む
        next_x, next_y = self.x, self.y
        if self.direction == Direction.UP:
            next_y -= self.speed
        elif self.direction == Direction.DOWN:
            next_y += self.speed
        elif self.direction == Direction.LEFT:
            next_x -= self.speed
        elif self.direction == Direction.RIGHT:
            next_x += self.speed

        # 3. 壁がなければ座標を確定
        if not self._collides_with_wall(next_x, next_y, maze_data):
            self.x = next_x
            self.y = next_y
            return True

        return False
