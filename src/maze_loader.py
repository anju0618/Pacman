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
        """生成された迷路の2次元リストを返す"""
        return cast(list[list[int]], self.generator.maze)
