"""
MOD difining the base chara class
"""
from math import sqrt

from src.enums import Direction


class Character:
    """
    chara base class (pac ghost)
    """

    CORNER_CUT_DISTANCE = 0.0

    def __init__(self, start_x: float, start_y: float) -> None:
        self.x: float = start_x
        self.y: float = start_y
        self.direction: Direction = Direction.RIGHT
        self.next_direction: Direction | None = None
        self.speed: float = 0.14
        # 当たり判定と描画の両方で共有する半径（食い違うと壁にめり込んで見える）
        self.radius: float = 0.45  # 0.45にすると食い込まない

    def get_current_grid(self) -> tuple[int, int]:
        return int(self.x + 0.5), int(self.y + 0.5)

    def _collides_with_wall(
        self,
        check_x: float,
        check_y: float,
        maze_data: list[list[int]],
        collision_radius: float | None = None
    ) -> bool:
        """指定した座標のボックスが壁(1)に接触しているかを正確に判定する"""
        radius = self.radius if collision_radius is None else collision_radius

        left = check_x - radius
        right = check_x + radius
        top = check_y - radius
        bottom = check_y + radius

        min_x = int(left + 0.5)
        max_x = int(right + 0.5)
        min_y = int(top + 0.5)
        max_y = int(bottom + 0.5)

        height = len(maze_data)

        for gy in range(min_y, max_y + 1):
            for gx in range(min_x, max_x + 1):
                if gy < 0 or gy >= height:
                    return True
                if gx < 0 or gx >= len(maze_data[gy]):
                    return True
                if maze_data[gy][gx] == 1:
                    return True

        return False

    def move_forward(self, maze_data: list[list[int]]) -> bool:
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

        if self._move_during_corner_alignment(maze_data):
            return True

        if self._move_through_turn(maze_data):
            return True

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

    def _move_during_corner_alignment(
        self,
        maze_data: list[list[int]]
    ) -> bool:
        """切り込んだ旋回中は、速度を保ちながら通路中央へ寄せる"""
        if self.CORNER_CUT_DISTANCE <= 0:
            return False

        grid_x = round(self.x)
        grid_y = round(self.y)
        if self.direction in (Direction.UP, Direction.DOWN):
            alignment_distance = abs(grid_x - self.x)
        else:
            alignment_distance = abs(grid_y - self.y)

        if alignment_distance <= 1e-9:
            return False

        alignment_step = min(
            alignment_distance,
            self.speed / sqrt(2.0)
        )
        forward_step = sqrt(
            max(0.0, self.speed ** 2 - alignment_step ** 2)
        )

        next_x, next_y = self._position_in_direction(
            self.x,
            self.y,
            self.direction,
            forward_step
        )
        if self.direction in (Direction.UP, Direction.DOWN):
            next_x += alignment_step if self.x < grid_x else -alignment_step
        else:
            next_y += alignment_step if self.y < grid_y else -alignment_step

        corner_radius = max(0.0, self.radius - self.CORNER_CUT_DISTANCE)
        if self._collides_with_wall(
            next_x, next_y, maze_data, corner_radius
        ):
            return False

        self.x = next_x
        self.y = next_y
        return True

    def _move_through_turn(self, maze_data: list[list[int]]) -> bool:
        """交差点の中心を基準に、残りの移動量で曲がる"""
        if self.next_direction is None:
            return False

        is_current_horizontal = self.direction in (
            Direction.LEFT, Direction.RIGHT
        )
        is_next_horizontal = self.next_direction in (
            Direction.LEFT, Direction.RIGHT
        )
        if is_current_horizontal == is_next_horizontal:
            return False

        grid_x = round(self.x)
        grid_y = round(self.y)

        if self.direction == Direction.UP:
            signed_distance_to_center = self.y - grid_y
        elif self.direction == Direction.DOWN:
            signed_distance_to_center = grid_y - self.y
        elif self.direction == Direction.LEFT:
            signed_distance_to_center = self.x - grid_x
        else:
            signed_distance_to_center = grid_x - self.x

        distance_to_center = abs(signed_distance_to_center)
        corner_entry_distance = self.speed
        if signed_distance_to_center >= 0:
            corner_entry_distance += self.CORNER_CUT_DISTANCE
        if distance_to_center > corner_entry_distance:
            return False

        test_x, test_y = self._position_in_direction(
            float(grid_x),
            float(grid_y),
            self.next_direction,
            self.speed
        )
        if self._collides_with_wall(test_x, test_y, maze_data):
            return False

        if distance_to_center > self.speed:
            diagonal_step = self.speed / sqrt(2.0)
            next_x, next_y = self._position_in_direction(
                self.x,
                self.y,
                self.direction,
                diagonal_step
            )
            next_x, next_y = self._position_in_direction(
                next_x,
                next_y,
                self.next_direction,
                diagonal_step
            )
            corner_radius = max(
                0.0, self.radius - self.CORNER_CUT_DISTANCE
            )
            if self._collides_with_wall(
                next_x, next_y, maze_data, corner_radius
            ):
                return False

            self.x = next_x
            self.y = next_y
            self.direction = self.next_direction
            self.next_direction = None
            return True

        remaining_distance = self.speed - distance_to_center
        if self.CORNER_CUT_DISTANCE > 0:
            diagonal_remaining = sqrt(
                max(0.0, self.speed ** 2 - distance_to_center ** 2)
            )
            remaining_distance = min(
                remaining_distance + self.CORNER_CUT_DISTANCE,
                diagonal_remaining
            )
        self.x, self.y = self._position_in_direction(
            float(grid_x),
            float(grid_y),
            self.next_direction,
            remaining_distance
        )
        self.direction = self.next_direction
        self.next_direction = None
        return True

    @staticmethod
    def _position_in_direction(
        x: float,
        y: float,
        direction: Direction,
        distance: float
    ) -> tuple[float, float]:
        if direction == Direction.UP:
            y -= distance
        elif direction == Direction.DOWN:
            y += distance
        elif direction == Direction.LEFT:
            x -= distance
        elif direction == Direction.RIGHT:
            x += distance
        return x, y
