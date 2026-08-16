"""
Inky ghost (Kimagure/Bashful)
target:
  1. パックマンが向いている方向の2タイル先を「基準点」とする
     （Pinky同様、上向き時は上2＋左2にズレる本家バグを再現）
  2. Blinkyの現在地から基準点へ引いたベクトルを2倍延長した先のタイル
     target = pivot + (pivot - blinky) = 2*pivot - blinky
Note: Blinkyの位置に依存するため、Blinkyが見つからない場合は基準点を
    そのままターゲットにする（フォールバック）
"""

from src.character.ghost import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Inky(Ghost):
    """水色ゴースト「キマグレ」。CHASE中はBlinkyの位置も参照して
    ターゲットを決める、最も気まぐれ(予測しにくい)なAI。
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """出現位置(左下の角)を受け取って初期化する。"""
        super().__init__(start_x, start_y, GhostType.INKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list[Ghost]
    ) -> Direction:
        """CHASEモード時のターゲット決定。

        モジュールdocstring記載の通り、パックマン前方2マスの
        「基準点」からBlinkyの位置へのベクトルを2倍延長した先を
        ターゲットにする(target = 2*pivot - blinky_pos)。ghosts
        の中からBlinkyを探して位置を参照するため、Blinkyが見つから
        ない場合は基準点自体をターゲットにフォールバックする。
        """
        pivot_x, pivot_y = pacman.get_current_grid()
        if pacman.direction == Direction.UP:
            pivot_x -= 2
            pivot_y -= 2
        elif pacman.direction == Direction.DOWN:
            pivot_y += 2
        elif pacman.direction == Direction.LEFT:
            pivot_x -= 2
        elif pacman.direction == Direction.RIGHT:
            pivot_x += 2

        blinky = next(
            (g for g in ghosts if g.type == GhostType.BLINKY), None
        )
        if blinky is not None:
            blinky_x, blinky_y = blinky.get_current_grid()
            target_x = 2 * pivot_x - blinky_x
            target_y = 2 * pivot_y - blinky_y
        else:
            target_x, target_y = pivot_x, pivot_y

        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction_bfs(
            available_directions, maze_data, target_x, target_y
        )
