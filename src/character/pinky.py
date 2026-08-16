"""
pink ghost (Machibuse/Pinky)
target: パックマンが向いている方向の4タイル先
Note: オリジナルで、パックマンが上を向いているときだけ、
    ターゲットが上4タイルかつ左4タイルにずれるバグある
"""

from src.character.ghost import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Pinky(Ghost):
    """ピンクゴースト「マチブセ」。CHASE中はパックマンの4マス先を
    先回りするように狙う待ち伏せ型AI。
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """出現位置(右上の角)を受け取って初期化する。"""
        super().__init__(start_x, start_y, GhostType.PINKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list[Ghost]
    ) -> Direction:
        """CHASEモード時のターゲット決定。

        パックマンが向いている方向の4マス先をターゲットにする
        (本家の仕様通り、上向きの時だけ上4マス+左4マスにズレる
        バグも再現している。モジュールdocstring参照)。
        """
        target_x, target_y = pacman.get_current_grid()
        if pacman.direction == Direction.UP:
            target_x -= 4
            target_y -= 4
        elif pacman.direction == Direction.DOWN:
            target_y += 4
        elif pacman.direction == Direction.LEFT:
            target_x -= 4
        elif pacman.direction == Direction.RIGHT:
            target_x += 4
        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction_bfs(
            available_directions, maze_data, target_x, target_y
        )
