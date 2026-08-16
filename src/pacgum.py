"""
パグムの配置とか接触アルゴリズムを定義
"""
import random
from collections.abc import Iterable
from enum import Enum, auto


class PacgumKind(Enum):
    """接触したパグムの種類。得点への変換は呼び出し側(config依存)が行う"""
    NORMAL = auto()
    SUPER = auto()


class Pacgum:
    """迷路上のパグム(小ドット)とスーパーパグム(パワーペレット)の配置・回収を管理する"""

    def __init__(
            self,
            maze_data: list[list[int]],
            super_positions: list[tuple[int, int]],
            excluded_positions: Iterable[tuple[int, int]],
            count: int
            ) -> None:
        self.super_positions: set[tuple[int, int]] = set(super_positions)

        excluded = set(excluded_positions) | self.super_positions
        available = self._open_cells(maze_data, excluded)
        placed_count = min(count, len(available))
        self.normal_positions: set[tuple[int, int]] = set(
            random.sample(available, placed_count)
        )

    @staticmethod
    def _open_cells(
        maze_data: list[list[int]],
        excluded_positions: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """壁でも除外対象でもない通路セルの座標(x, y)を列挙する"""
        return [
            (x, y)
            for y, row in enumerate(maze_data)
            for x, cell in enumerate(row)
            if cell == 0 and (x, y) not in excluded_positions
        ]

    def collect(self, position: tuple[int, int]) -> PacgumKind | None:
        """指定座標のパグムを回収する。無ければNoneを返す"""
        if position in self.normal_positions:
            self.normal_positions.remove(position)
            return PacgumKind.NORMAL
        if position in self.super_positions:
            self.super_positions.remove(position)
            return PacgumKind.SUPER
        return None

    def remaining_count(self) -> int:
        """未回収のパグム(通常＋スーパー)の総数"""
        return len(self.normal_positions) + len(self.super_positions)

    def is_empty(self) -> bool:
        """全てのパグムが回収済みかどうか(レベルクリア判定に利用予定)"""
        return self.remaining_count() == 0
