"""
Module defining the ghost characters and their AI.
"""
from src.enums import Direction, GhostMode, GhostType
from src.character.base import Character


class Ghost(Character):
    """
    Ghoast class
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
        # defaul mode == SCATTER
        self.mode: GhostMode = GhostMode.SCATTER

    def dicide_next_direction(
        self,
        available_direction: list[Direction],
        target_x: int,
        target_y: int
    ) -> Direction:
        """
        available = 壁ではなく、来た道でない方向のリスト
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

    def _tie_breaker(self, dir1: Direction, dir2: Direction) -> Direction:
        priority = {
            Direction.UP: 1,
            Direction.LEFT: 2,
            Direction.DOWN: 3,
            Direction.RIGHT: 4
        }
        return dir1 if priority[dir1] < priority[dir2] else dir2
