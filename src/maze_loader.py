"""
mod loading maze grid from mazegen pack
"""
from typing import cast
from mazegenerator import MazeGenerator


class MazeLoader:
    def __init__(self, width: int, height: int, seed: int) -> None:
        # MazeGenerator.__init__ が内部で generate() を呼ぶので、
        # ここで改めて generate() を呼ぶ必要はない（呼ぶと二重生成になる）。
        # entry_cell はライブラリのデフォルト(0, 0)のまま使う。
        # 中央付近に埋め込まれる「42」の飾り文字セルは生成前から
        # 全方向が壁として確定しているため、そこを起点に指定すると
        # 迷路生成そのものが失敗する（起点が完全に孤立する）。
        self.generator = MazeGenerator(
            size=(width, height),
            perfect=False,
            seed=seed
        )

    def get_maze_data(self) -> list[list[int]]:
        """生成された迷路の2次元リスト（16進数ビットマスク）を返す"""
        return cast(list[list[int]], self.generator.maze)

    def find_center_start_position(self) -> tuple[int, int]:
        """
        パックマンの初期位置・リスポーン位置は「真ん中」という要件のため、
        生成済みの迷路の幾何学的な中心に最も近い通路セルを
        バイナリグリッド座標で返す。
        """
        binary_grid = self.get_binary_grid()
        height = len(binary_grid)
        width = len(binary_grid[0])
        center_x, center_y = width // 2, height // 2

        return self._find_nearest_open_cell(binary_grid, center_x, center_y)

    def find_corner_positions(self) -> list[tuple[int, int]]:
        """
        4匹のゴーストの初期出現位置として、迷路の四隅
        （左上・右上・左下・右下）に最も近い通路セルを返す。
        """
        binary_grid = self.get_binary_grid()
        height = len(binary_grid)
        width = len(binary_grid[0])
        corners = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
        ]
        return [
            self._find_nearest_open_cell(binary_grid, corner_x, corner_y)
            for corner_x, corner_y in corners
        ]

    def _find_nearest_open_cell(
        self,
        binary_grid: list[list[int]],
        target_x: int,
        target_y: int
    ) -> tuple[int, int]:
        """指定座標に最も近い通路セル（0）のグリッド座標を返す"""
        if binary_grid[target_y][target_x] == 0:
            return target_x, target_y

        height = len(binary_grid)
        width = len(binary_grid[0])
        best_position = (target_x, target_y)
        best_distance = None
        for y in range(height):
            for x in range(width):
                if binary_grid[y][x] != 0:
                    continue
                distance = (x - target_x) ** 2 + (y - target_y) ** 2
                if best_distance is None or distance < best_distance:
                    best_distance = distance
                    best_position = (x, y)

        return best_position

    def get_binary_grid(self) -> list[list[int]]:
        """
        16進数の迷路を、壁=1、通路=0のブロックグリッドに変換
        """
        maze_data = self.get_maze_data()
        orig_height = len(maze_data)
        orig_width = len(maze_data[0])
        new_height = orig_height * 2 + 1
        new_width = orig_width * 2 + 1
        binary_grid = [
            [1 for _ in range(new_width)] for _ in range(new_height)
        ]

        for y in range(orig_height):
            for x in range(orig_width):
                cell = maze_data[y][x]
                cy, cx = y * 2 + 1, x * 2 + 1

                binary_grid[cy][cx] = 0

                if not (cell & 1):
                    binary_grid[cy - 1][cx] = 0

                if not (cell & 2):
                    binary_grid[cy][cx + 1] = 0

                if not (cell & 4):
                    binary_grid[cy + 1][cx] = 0

                if not (cell & 8):
                    binary_grid[cy][cx - 1] = 0

        return binary_grid
