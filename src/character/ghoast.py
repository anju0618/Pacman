"""
Module defining the ghost characters and their AI.
"""
from src.enums import Direction, GhostMode, GhostType
from src.character.base import Character

class Ghost(Character):
    """
	Ghoast class
	4匹ごと違う
	"""
    
    def __init__(
        self, 
        start_x: float, 
        start_y: float, 
        ghost_type: GhostType
    ) -> None:
        super().__init__(start_x, start_y)
        self.type: GhostType = ghost_type
		# defaul mode == SCATTER
        self.mode: GhostMode = GhostMode.SCATTER
