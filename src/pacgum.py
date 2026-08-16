"""
パグムの配置とか接触アルゴリズムを定義
"""
from collections.abc import Iterable
from enum import Enum, auto


class PacgumKind(Enum):
    """接触したパグムの種類。得点への変換は呼び出し側(config依存)が行う"""
    NORMAL = auto()
    SUPER = auto()


class Pacgum:
    """迷路上のパグム(小ドット)とスーパーパグム(パワーペレット)の配置・回収を管理する

    課題仕様(VI.1/VI.4)の「ほとんどの通路に小ドットを置く」という要件を
    満たすため、Pacman初期位置と四隅(スーパーパグム)を除いた通路セルの
    全てに通常パグムを配置する(個数の上限は設けない)。
    """

    def __init__(
            self,
            maze_data: list[list[int]],
            super_positions: list[tuple[int, int]],
            excluded_positions: Iterable[tuple[int, int]],
            ) -> None:
        """迷路データを元に、通常パグムとスーパーパグムを配置する。

        Args:
            maze_data: 壁=1/通路=0のバイナリグリッド(MazeLoader由来)。
            super_positions: スーパーパグムを置く座標(通常は迷路の
                四隅、MazeLoader.find_corner_positions()の戻り値)。
            excluded_positions: パグムを置かない座標
                (Pacmanの初期位置など)。super_positionsとあわせて
                除外集合として扱う。
        """
        self.super_positions: set[tuple[int, int]] = set(super_positions)

        excluded = set(excluded_positions) | self.super_positions
        self.normal_positions: set[tuple[int, int]] = set(
            self._open_cells(maze_data, excluded)
        )

    @staticmethod
    def _open_cells(
        maze_data: list[list[int]],
        excluded_positions: set[tuple[int, int]],
    ) -> list[tuple[int, int]]:
        """壁でも除外対象でもない通路セルの座標(x, y)を列挙する。

        Args:
            maze_data: 壁=1/通路=0のバイナリグリッド。
            excluded_positions: 通路であっても除外したい座標の集合。

        Returns:
            通常パグムを配置してよい座標のリスト。
        """
        return [
            (x, y)
            for y, row in enumerate(maze_data)
            for x, cell in enumerate(row)
            if cell == 0 and (x, y) not in excluded_positions
        ]

    def collect(self, position: tuple[int, int]) -> PacgumKind | None:
        """指定座標のパグムを回収する(集合から取り除く)。

        Args:
            position: Pacmanの現在グリッド座標(x, y)。

        Returns:
            回収できた場合はその種類(NORMAL/SUPER)、
            その座標に何も無ければNone。
        """
        if position in self.normal_positions:
            self.normal_positions.remove(position)
            return PacgumKind.NORMAL
        if position in self.super_positions:
            self.super_positions.remove(position)
            return PacgumKind.SUPER
        return None

    def remaining_count(self) -> int:
        """未回収のパグム(通常＋スーパー)の総数を返す。"""
        return len(self.normal_positions) + len(self.super_positions)

    def is_empty(self) -> bool:
        """全てのパグムが回収済みかどうかを返す。

        Display.is_cleared()がこれを使ってレベルクリア判定
        (課題要件: 全パグムを食べたらレベルクリア)を行う。
        """
        return self.remaining_count() == 0
