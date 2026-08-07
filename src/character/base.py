"""
MOD difining the base chara class
"""
from src.enums import Direction


class Character:
    """
    chara base class (pac ghoast)
    """

    def __init__(self, start_x: float, start_y: float) -> None:
        """
        全キャラエンティティはスタート位置を持つ
        """
        self.x: float = start_x  # setterいるかな？いらないよね
        self.y: float = start_y
        self.direction: Direction = Direction.LEFT
        self.speed: float = 1.0  # 本家はフェーズによって速度変わる

    def get_current_grid(self) -> tuple[int, int]:
        """
        現在地getter
        """
        return int(self.x), int(self.y)

    def move_foward(self) -> None:
        """
        directionへspeed分移動
        """
        if self.direction == Direction.UP:
            self.y -= self.speed
        elif self.direction == Direction.DOWN:
            self.y += self.speed
        elif self.direction == Direction.LEFT:
            self.x -= self.speed
        elif self.direction == Direction.RIGHT:
            self.x += self.speed
