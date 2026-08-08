"""
mod loading maze grid from mazegen pack
"""
from typing import cast
from mazegenerator import MazeGenerator


class MazeLoader:
    def __init__(self, width: int, height: int, seed: int) -> None:
        self.generator = MazeGenerator(
            size=(width, height),
            perfect=False,
            seed=seed
        )
        self.generator.generate(seed)

    def get_maze_data(self) -> list[list[int]]:
        """生成された迷路の2次元リスト（16進数ビットマスク）を返す"""
        return cast(list[list[int]], self.generator.maze)

    def get_binary_grid(self) -> list[list[int]]:
        """
        16進数の迷路を、壁=1、通路=0のブロックグリッドに変換
        """
        maze_data = self.get_maze_data()
        orig_height = len(maze_data)
        orig_width = len(maze_data[0])
        new_height = orig_height * 2 + 1
        new_width = orig_width * 2 + 1
        binary_grid = [[1 for _ in range(new_width)] for _ in range(new_height)]

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
