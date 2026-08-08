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

    def __init__(self, start_x: float, start_y: float) -> None:
        super().__init__(start_x, start_y, GhostType.BLINKY)

    def determine_direction(
        self,
        pacman: Pacman,
        maze_data: list[list[int]]
    ) -> Direction:
        target_x, target_y = pacman.get_current_grid()
        available_directions = self.get_available_directions(maze_data)
        return self.decide_next_direction(
            available_directions, target_x, target_y
        )
