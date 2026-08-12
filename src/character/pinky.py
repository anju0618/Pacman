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

    def __init__(self, start_x: float, start_y: float) -> None:
        super().__init__(start_x, start_y, GhostType.PINKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]],
        ghosts: list[Ghost]
    ) -> Direction:

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
