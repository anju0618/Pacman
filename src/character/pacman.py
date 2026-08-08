"""
pacman mod
"""
from src.character.base import Character


class Pacman(Character):

    def __init__(self, start_x: float, start_y: float) -> None:
        super().__init__(start_x, start_y)
        self.c_gum: int = 0
