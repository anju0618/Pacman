"""
orange ghost (Otoboke/Clyde)
target: パックマンとの距離が8タイル以上ならパックマンの現在マス（Blinky同様の直接追跡）
    8タイル未満に近づくと臆病になり、自分のスタート地点（縄張り）へ逃げる
"""
from src.character.ghost import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Clyde(Ghost):
    """オレンジゴースト「オトボケ」。CHASE中は遠くにいる時だけ
    追跡し、近づくと臆病になって自陣へ逃げる気まぐれなAI。
    """

    # このマス数未満までパックマンに近づくと、追跡をやめて
    # 自陣(home_position)へ逃げる。
    SHY_DISTANCE = 8

    def __init__(self, start_x: float, start_y: float) -> None:
        """出現位置(右下の角)を受け取って初期化する。"""
        super().__init__(start_x, start_y, GhostType.CLYDE)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list[Ghost]
    ) -> Direction:
        """CHASEモード時のターゲット決定。

        パックマンとの距離がSHY_DISTANCE以上ならBlinky同様に直接
        パックマンを追い、それより近づくと逆に自陣(home_position)
        へ引き返す(近づいたり離れたりを繰り返す、本家の「オトボケ」
        らしい挙動)。
        """
        pacman_x, pacman_y = pacman.get_current_grid()
        self_x, self_y = self.get_current_grid()
        distance_sq = (pacman_x - self_x) ** 2 + (pacman_y - self_y) ** 2

        if distance_sq >= self.SHY_DISTANCE ** 2:
            target_x, target_y = pacman_x, pacman_y
        else:
            target_x, target_y = self.home_position

        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction_bfs(
            available_directions, maze_data, target_x, target_y
        )
