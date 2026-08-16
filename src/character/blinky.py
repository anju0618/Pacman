"""
red ghost (Oikake/Blinky)
target: パックマンが現在いるマス
パックマンの背後から最短距離で追跡
"""
from src.character.ghost import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Blinky(Ghost):
    """赤ゴースト「オイカケ」。CHASE中はパックマンの現在地を
    直接ターゲットにする、最もシンプルな追跡AI。
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """出現位置(左上の角)を受け取って初期化する。"""
        super().__init__(start_x, start_y, GhostType.BLINKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list[Ghost]
    ) -> Direction:
        """CHASEモード時のターゲット決定: パックマンの現在マスへBFSで向かう。"""
        target_x, target_y = pacman.get_current_grid()
        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction_bfs(
            available_directions, maze_data, target_x, target_y
        )
