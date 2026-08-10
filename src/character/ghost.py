"""
Module defining the ghost characters and their AI.
"""
from src.enums import Direction, GhostMode, GhostType
from src.character.base import Character


class Ghost(Character):
    """
    Ghost base class
    4匹ごと違う
    """

    def __init__(
        self,
        start_x: float,
        start_y: float,
        ghost_type: GhostType
    ) -> None:
        super().__init__(start_x, start_y)
        self.type: GhostType = ghost_type
        # default mode == SCATTER
        self.mode: GhostMode = GhostMode.SCATTER

    def get_available_directions(
        self,
        maze_data: list[list[int]]
    ) -> list[Direction]:
        """
        壁ではない方向のリストを返す。
        来た道（現在の進行方向の逆）は、行き止まりでない限り除外する
        （本家のUターン禁止ルール）。
        """
        opposite = self._opposite_direction(self.direction)
        open_directions = []

        for direction in Direction:
            next_x, next_y = self._get_next_grid_coords(direction)
            if (
                0 <= next_y < len(maze_data)
                and 0 <= next_x < len(maze_data[0])
                and maze_data[next_y][next_x] == 0
            ):
                open_directions.append(direction)

        non_reverse = [d for d in open_directions if d != opposite]
        return non_reverse if non_reverse else open_directions

    def decide_next_direction(
        self,
        available_directions: list[Direction],
        target_x: int,
        target_y: int
    ) -> Direction:
        """
        available_directions = 壁ではなく、来た道でない方向のリスト
        """

        if not available_directions:
            return self.direction

        best_direction: Direction = available_directions[0]
        shortest_distance: float = float('inf')

        for direction in available_directions:
            next_x, next_y = self._get_next_grid_coords(direction)
            distance_sq = (next_x - target_x) ** 2 + (next_y - target_y) ** 2

            if distance_sq < shortest_distance:
                shortest_distance = distance_sq
                best_direction = direction

            elif distance_sq == shortest_distance:
                # 距離が同じ場合は、優先順位（上 > 左 > 下 > 右）タイブレーカー
                # pinkyのバグはこれ由来？
                best_direction = self._tie_breaker(best_direction, direction)

        return best_direction

    def _get_next_grid_coords(self, direction: Direction) -> tuple[int, int]:
        """指定した方向に1マス進んだ場合のグリッド座標を返す"""
        current_x, current_y = self.get_current_grid()
        if direction == Direction.UP:
            return current_x, current_y - 1
        elif direction == Direction.DOWN:
            return current_x, current_y + 1
        elif direction == Direction.LEFT:
            return current_x - 1, current_y
        elif direction == Direction.RIGHT:
            return current_x + 1, current_y
        return current_x, current_y

    def _opposite_direction(self, direction: Direction) -> Direction:
        opposite_of = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposite_of[direction]

    def _tie_breaker(self, dir1: Direction, dir2: Direction) -> Direction:
        priority = {
            Direction.UP: 1,
            Direction.LEFT: 2,
            Direction.DOWN: 3,
            Direction.RIGHT: 4
        }
        return dir1 if priority[dir1] < priority[dir2] else dir2
