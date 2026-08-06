# tests/test_maze.py
from mazegenerator import MazeGenerator


def test_maze_generation_settings() -> None:
    # 課題要件の perfect=False で迷路が作れるか
    generator = MazeGenerator(size=(21, 21), perfect=False, seed=42)
    generator.generate(42)

    # 迷路データ（mazeプロパティ）が取得できること
    maze_data = generator.maze
    assert maze_data is not None
    assert len(maze_data) > 0
