"""
ゴーストキャラクターとそのAIを定義するモジュール。

移動の物理演算はCharacterに任せ、Ghostは「次にどちらへ進むか」を
決めるAI部分(モード管理・BFS経路探索)を担当する。4匹の個性
(Blinky/Pinky/Inky/Clyde)はサブクラスがdetermine_direction()だけを
オーバーライドして表現し、モード切替(Scatter/Chase/Frightened/Eaten)
自体はこの基底クラスに一元化してある。
"""
import random
from collections import deque
from src.enums import Direction, GhostMode, GhostType
from src.character.base import Character
from src.character.pacman import Pacman


class Ghost(Character):
    """
    ゴーストの基底クラス。移動のAI部分(ターゲット決定・経路探索・
    モード管理)を持つ。4匹ごとの個性の違いはサブクラスが
    determine_direction()をオーバーライドするだけで表現され、
    それ以外のロジック(モード切替・BFS探索・振動防止など)は
    完全に共通で、この基底クラスにまとめてある。
    """

    FRIGHTENED_SPEED_FACTOR = 0.5
    EATEN_SPEED_FACTOR = 2.0

    def __init__(
        self,
        start_x: float,
        start_y: float,
        ghost_type: GhostType
    ) -> None:
        """出現位置(四隅)と種類を受け取り、初期状態を整える。

        Args:
            start_x: 出現位置のグリッドx座標(四隅のいずれか)。
            start_y: 出現位置のグリッドy座標(四隅のいずれか)。
            ghost_type: このゴーストの種類(Blinky/Pinky/Inky/Clyde)。
                描画時の色分けなどに使う。
        """
        super().__init__(start_x, start_y)
        self.speed *= 0.8
        self.base_speed: float = self.speed
        self.type: GhostType = ghost_type
        # モードコントローラ（Display側）が管理しない限りは常にCHASE。
        # SCATTER/FRIGHTENED/EATENへはset_mode()経由でのみ遷移する。
        self.mode: GhostMode = GhostMode.CHASE
        # SCATTER/EATEN時の帰還先（自分が出現した四隅のマス）
        self.home_position: tuple[int, int] = self.get_current_grid()
        # 直近に方向決定を行ったマス（本家同様、方向転換は交差点＝マスに
        # 侵入した瞬間だけ判断する。毎フレーム再計算すると、パックマンが
        # 静止している時に強制Uターン地点で判断がすぐ覆り、行ったり来たり
        # 振動してしまう）
        self._decided_grid: tuple[int, int] | None = None
        # 直近に通過したマスの履歴（交差点で来た道へ戻ることを抑え、
        # 本家のUターン禁止と行ったり来たりの防止を維持する）
        self._recent_cells: deque[tuple[int, int]] = deque(maxlen=12)
        self._bfs_target: tuple[int, int] | None = None
        self._bfs_maze: list[list[int]] | None = None
        self._bfs_distances: dict[tuple[int, int], int] = {}

    def set_mode(self, mode: GhostMode) -> None:
        """モードを切り替え、速度と（必要なら）向きを追従させる"""
        if mode == self.mode:
            return
        self.mode = mode
        self._decided_grid = None
        if mode == GhostMode.FRIGHTENED:
            self.speed = self.base_speed * self.FRIGHTENED_SPEED_FACTOR
            self.direction = self._opposite_direction(self.direction)
        elif mode == GhostMode.EATEN:
            self.speed = self.base_speed * self.EATEN_SPEED_FACTOR
        else:
            self.speed = self.base_speed

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
            self.next_direction = self._decide_direction_for_mode(
                pacman, maze_data, ghosts
            )
        self.move_forward(maze_data)

    def _decide_direction_for_mode(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list["Ghost"]
    ) -> Direction:
        """現在のGhostModeに応じてターゲット/移動方針を切り替える"""
        available_directions = self.get_available_directions(maze_data)

        if self.mode == GhostMode.FRIGHTENED:
            return self._decide_frightened_direction(available_directions)

        if self.mode in (GhostMode.SCATTER, GhostMode.EATEN):
            home_x, home_y = self.home_position
            return self.decide_next_direction_bfs(
                available_directions, maze_data, home_x, home_y
            )

        return self.determine_direction(pacman, maze_data, ghosts)

    def _decide_frightened_direction(
        self, available_directions: list[Direction]
    ) -> Direction:
        """イジケ中はパックマンから逃げる意味で、ランダムに方向を選ぶ"""
        if not available_directions:
            return self.direction
        return random.choice(available_directions)

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
        current_grid = self.get_current_grid()

        for direction in Direction:
            next_x, next_y = self._get_neighbor_grid(
                current_grid, direction
            )
            if (
                0 <= next_y < len(maze_data)
                and 0 <= next_x < len(maze_data[next_y])
                and maze_data[next_y][next_x] == 0
            ):
                open_directions.append(direction)

        non_reverse = [d for d in open_directions if d != opposite]
        if not non_reverse:
            return open_directions

        unvisited = [
            d for d in non_reverse
            if self._get_neighbor_grid(current_grid, d)
            not in self._recent_cells
        ]
        return unvisited if unvisited else non_reverse

    def decide_next_direction_bfs(
        self,
        available_directions: list[Direction],
        maze_data: list[list[int]],
        target_x: int,
        target_y: int
    ) -> Direction:
        """ターゲットまでのBFS最短経路から次の方向を選ぶ"""
        target = self._correct_target_to_open_cell(
            maze_data, (target_x, target_y)
        )
        if target is None:
            return self.decide_next_direction(
                available_directions, target_x, target_y
            )

        distances = self._get_bfs_distances(maze_data, target)
        bfs_direction = self._select_bfs_direction(
            available_directions, distances
        )
        if bfs_direction is not None:
            return bfs_direction

        # ターゲットとゴーストが別の領域にいる場合は補正先を使う
        return self.decide_next_direction(
            available_directions, target[0], target[1]
        )

    def _correct_target_to_open_cell(
        self,
        maze_data: list[list[int]],
        target: tuple[int, int]
    ) -> tuple[int, int] | None:
        """壁・迷路外のターゲットを最寄りの通路マスへ補正する"""
        if self._is_open_cell(maze_data, target):
            return target

        nearest_target: tuple[int, int] | None = None
        nearest_distance = float("inf")
        target_x, target_y = target

        for y, row in enumerate(maze_data):
            for x, cell in enumerate(row):
                if cell != 0:
                    continue

                distance = (x - target_x) ** 2 + (y - target_y) ** 2
                if distance < nearest_distance:
                    nearest_distance = distance
                    nearest_target = x, y

        return nearest_target

    def _get_bfs_distances(
        self,
        maze_data: list[list[int]],
        target: tuple[int, int]
    ) -> dict[tuple[int, int], int]:
        """ターゲットから各通路マスまでの距離をBFSで求める"""
        if self._bfs_target == target and self._bfs_maze is maze_data:
            return self._bfs_distances

        distances: dict[tuple[int, int], int] = {}
        if self._is_open_cell(maze_data, target):
            distances[target] = 0
            queue: deque[tuple[int, int]] = deque([target])

            while queue:
                current = queue.popleft()
                current_distance = distances[current]

                for direction in Direction:
                    neighbor = self._get_neighbor_grid(current, direction)
                    if (
                        self._is_open_cell(maze_data, neighbor)
                        and neighbor not in distances
                    ):
                        distances[neighbor] = current_distance + 1
                        queue.append(neighbor)

        self._bfs_target = target
        self._bfs_maze = maze_data
        self._bfs_distances = distances
        return distances

    def _select_bfs_direction(
        self,
        available_directions: list[Direction],
        distances: dict[tuple[int, int], int]
    ) -> Direction | None:
        """最短方向を選ぶ。同距離なら現在の進行方向を優先する"""
        best_direction: Direction | None = None
        shortest_distance = float("inf")
        current_grid = self.get_current_grid()

        for direction in available_directions:
            neighbor = self._get_neighbor_grid(current_grid, direction)
            distance = distances.get(neighbor)
            if distance is None:
                continue

            if distance < shortest_distance:
                shortest_distance = distance
                best_direction = direction
            elif (
                distance == shortest_distance
                and best_direction is not None
            ):
                if direction == self.direction:
                    best_direction = direction
                elif best_direction != self.direction:
                    best_direction = self._tie_breaker(
                        best_direction, direction
                    )

        return best_direction

    @staticmethod
    def _get_neighbor_grid(
        grid: tuple[int, int], direction: Direction
    ) -> tuple[int, int]:
        """指定マスからdirection方向へ1マス進んだグリッド座標を返す。"""
        x, y = grid
        if direction == Direction.UP:
            return x, y - 1
        if direction == Direction.DOWN:
            return x, y + 1
        if direction == Direction.LEFT:
            return x - 1, y
        return x + 1, y

    @staticmethod
    def _is_open_cell(
        maze_data: list[list[int]], grid: tuple[int, int]
    ) -> bool:
        """指定グリッド座標が迷路の範囲内かつ通路(0)であるかを判定する。"""
        x, y = grid
        return (
            0 <= y < len(maze_data)
            and 0 <= x < len(maze_data[y])
            and maze_data[y][x] == 0
        )

    def decide_next_direction(
        self,
        available_directions: list[Direction],
        target_x: int,
        target_y: int
    ) -> Direction:
        """BFSが使えない場合のフォールバック: 直線距離が最短の方向を選ぶ。

        BFSによる最短経路探索(decide_next_direction_bfs)がターゲットに
        到達できない場合(別の孤立した領域にいる等)のフォールバックと
        して使う、シンプルな貪欲法。各候補方向へ1マス進んだ時の
        ターゲットまでのユークリッド距離(の2乗)を比較し、最も近づく
        方向を選ぶ。同距離の場合は_tie_breakerで優先順位を決める。

        Args:
            available_directions: 壁ではなく、来た道でない方向のリスト
                (get_available_directionsの戻り値)。
            target_x: 目標地点のグリッドx座標。
            target_y: 目標地点のグリッドy座標。

        Returns:
            選ばれた方向。available_directionsが空なら現在の向きを維持する。
        """

        if not available_directions:
            return self.direction

        best_direction: Direction = available_directions[0]
        shortest_distance: float = float('inf')
        current_grid = self.get_current_grid()

        for direction in available_directions:
            next_x, next_y = self._get_neighbor_grid(
                current_grid, direction
            )
            distance_sq = (next_x - target_x) ** 2 + (next_y - target_y) ** 2

            if distance_sq < shortest_distance:
                shortest_distance = distance_sq
                best_direction = direction

            elif distance_sq == shortest_distance:
                # 距離が同じ場合は、優先順位（上 > 左 > 下 > 右）タイブレーカー
                best_direction = self._tie_breaker(best_direction, direction)

        return best_direction

    def _opposite_direction(self, direction: Direction) -> Direction:
        """指定方向の真逆(180度反対)の方向を返す。"""
        opposite_of = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposite_of[direction]

    def _tie_breaker(self, dir1: Direction, dir2: Direction) -> Direction:
        """2方向が同じ距離で並んだ時に選ぶ方を決める(優先順位: 上>左>下>右)。

        本家パックマンのゴーストAIの仕様に合わせた固定優先順位。
        """
        priority = {
            Direction.UP: 1,
            Direction.LEFT: 2,
            Direction.DOWN: 3,
            Direction.RIGHT: 4
        }
        return dir1 if priority[dir1] < priority[dir2] else dir2
