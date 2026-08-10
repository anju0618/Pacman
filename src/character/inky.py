"""
Inky ghost (Kimagure/Bashful)
target: パックマンが向いている方向の2タイル先
Note: オリジナルで、パックマンが上を向いているときだけ、
    ターゲットが上2タイルかつ左2タイルにずれるバグある
"""

from src.character.ghost import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Inky(Ghost):

    def __init__(self, start_x: float, start_y: float) -> None:
        super().__init__(start_x, start_y, GhostType.INKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]]
    ) -> Direction:

        target_x, target_y = pacman.get_current_grid()
        if pacman.direction == Direction.UP:
            target_x -= 2
            target_y -= 2
        elif pacman.direction == Direction.DOWN:
            target_y += 2
        elif pacman.direction == Direction.LEFT:
            target_x -= 2
        elif pacman.direction == Direction.RIGHT:
            target_x +=2
        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction(
            available_directions, target_x, target_y
        )
