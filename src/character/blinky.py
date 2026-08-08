"""
red ghost (Oikake/Blinky)
target: パックマンが現在いるマス
パックマンの背後から最短距離で追跡
"""
from src.character.ghoast import Ghost
from src.enums import GhostType
from src.character.pacman import Pacman
from src.enums import Direction


class Blinky(Ghost):

    def __init__(self, start_x: float, start_y:float) -> None:
        super().__init__(start_x, start_y, GhostType.BLINKY)

    def determine_direction(self, packman: Pacman) -> list[Direction]:
        target_x: float = packman.x
        target_y: float = packman.y