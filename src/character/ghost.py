"""
Module defining the ghost characters and their AI.
"""
from collections import deque
from src.enums import Direction, GhostMode, GhostType
from src.character.base import Character
from src.character.pacman import Pacman


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
        # 直近に方向決定を行ったマス（本家同様、方向転換は交差点＝マスに
        # 侵入した瞬間だけ判断する。毎フレーム再計算すると、パックマンが
        # 静止している時に強制Uターン地点で判断がすぐ覆り、行ったり来たり
        # 振動してしまう）
        self._decided_grid: tuple[int, int] | None = None
        # 直近に通過したマスの履歴（直進距離だけで進行方向を決める貪欲法は、
        # 目的地が動かないと迷路内の小さな輪っか状の通路をぐるぐる無限に
        # 周回してしまうことがある＝行ったり来たり振動して見える原因。
        # 直近に通ったマスへは行き止まりでない限り戻らないようにして防ぐ）
        self._recent_cells: deque[tuple[int, int]] = deque(maxlen=12)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list["Ghost"]
    ) -> Direction:
        """各ゴーストのサブクラスがターゲット算出込みで実装する"""
        raise NotImplementedError

    def update(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list["Ghost"]
    ) -> None:
        """毎フレーム呼ばれる更新処理：新しいマスに入った時だけAIで方向を
        決定し、移動は毎フレーム行う"""
        current_grid = self.get_current_grid()
        if current_grid != self._decided_grid:
            self._decided_grid = current_grid
            self._recent_cells.append(current_grid)
            self.next_direction = self.determine_direction(
                pacman, maze_data, ghosts
            )
        self.move_forward(maze_data)

    def get_available_directions(
        self,
        maze_data: list[list[int]]
    ) -> list[Direction]:
        """
        壁ではない方向のリストを返す
        来た道（現在の進行方向の逆）は、行き止まりでない限り除外する
        （本家のUターン禁止ルール）
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
        if not non_reverse:
            return open_directions

        unvisited = [
            d for d in non_reverse
            if self._get_next_grid_coords(d) not in self._recent_cells
        ]
        return unvisited if unvisited else non_reverse

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
