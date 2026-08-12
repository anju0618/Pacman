from unittest.mock import patch

from src.character.blinky import Blinky
from src.character.clyde import Clyde
from src.character.inky import Inky
from src.character.pacman import Pacman
from src.character.pinky import Pinky
from src.enums import Direction
from src.maze_loader import MazeLoader


def test_ghost_speed_is_80_percent_of_pacman_speed() -> None:
    pacman = Pacman(0.0, 0.0)
    ghost = Blinky(0.0, 0.0)

    assert ghost.speed == pacman.speed * 0.8


def test_ghost_treats_missing_ragged_cells_as_walls() -> None:
    ghost = Blinky(0.0, 1.0)
    maze_data = [[1, 1], []]

    assert ghost.get_available_directions(maze_data) == []


def test_blinky_uses_bfs_to_avoid_a_dead_end() -> None:
    maze_data = [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 1, 0, 0, 1],
        [1, 0, 1, 1, 0, 1, 1],
        [1, 0, 0, 0, 0, 1, 1],
        [1, 1, 1, 1, 1, 1, 1],
    ]
    blinky = Blinky(1.0, 1.0)
    pacman = Pacman(5.0, 1.0)

    direction = blinky.determine_direction(pacman, maze_data, [blinky])

    assert direction == Direction.DOWN


def test_blinky_prefers_going_straight_when_bfs_paths_are_equal() -> None:
    maze_data = [
        [1, 1, 1, 1, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 0, 0, 0, 1],
        [1, 1, 1, 1, 1],
    ]
    blinky = Blinky(1.0, 1.0)
    pacman = Pacman(3.0, 3.0)

    direction = blinky.determine_direction(pacman, maze_data, [blinky])

    assert direction == Direction.RIGHT


def test_all_ghosts_use_shared_bfs_direction_selection() -> None:
    maze_data = [[0] * 7 for _ in range(7)]
    pacman = Pacman(3.0, 3.0)
    ghosts = [
        Blinky(1.0, 1.0),
        Pinky(1.0, 1.0),
        Inky(1.0, 1.0),
        Clyde(1.0, 1.0),
    ]

    for ghost in ghosts:
        with patch.object(
            ghost,
            "decide_next_direction_bfs",
            wraps=ghost.decide_next_direction_bfs
        ) as decide_direction:
            ghost.determine_direction(pacman, maze_data, ghosts)

        assert decide_direction.call_count == 1


def test_inky_corrects_invalid_target_before_bfs() -> None:
    maze_data = [
        [1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 0, 0, 0, 0, 0, 1],
        [1, 1, 1, 1, 1, 1, 1],
    ]
    inky = Inky(1.0, 1.0)
    pacman = Pacman(2.0, 2.0)
    pacman.direction = Direction.RIGHT
    blinky = Blinky(1.0, 2.0)

    with patch.object(
        inky,
        "decide_next_direction",
        wraps=inky.decide_next_direction
    ) as fallback:
        inky.determine_direction(pacman, maze_data, [blinky, inky])

    # target=(7,2) is outside the maze; the nearest open cell is (5,2).
    assert inky._bfs_target == (5, 2)
    assert fallback.call_count == 0


def test_ghosts_reach_a_stationary_pacman_without_looping_forever() -> None:
    """
    パックマンが静止していても、ゴーストAIが迷路内の小さな輪っか
    状の通路を無限に周回し続けて、いつまでもパックマンに到達できない
    （＝行ったり来たりに見える）バグの回帰テスト。
    レベル1固定シード(42)の迷路では、四隅から出発した4匹全員が
    十分なフレーム数以内にパックマンの居るマスへ到達できるはずである。
    """
    loader = MazeLoader(width=21, height=21, seed=42)
    maze_data = loader.get_binary_grid()

    start_x, start_y = loader.find_center_start_position()
    pacman = Pacman(float(start_x), float(start_y))

    corners = loader.find_corner_positions()
    ghost_classes = (Blinky, Pinky, Inky, Clyde)
    ghosts = [
        ghost_cls(float(cx), float(cy))
        for ghost_cls, (cx, cy) in zip(ghost_classes, corners)
    ]

    target = pacman.get_current_grid()
    reached = {type(ghost).__name__: False for ghost in ghosts}

    for _ in range(5000):
        for ghost in ghosts:
            ghost.update(pacman, maze_data, ghosts)
            if ghost.get_current_grid() == target:
                reached[type(ghost).__name__] = True
        if all(reached.values()):
            break

    assert all(reached.values()), reached


def test_inky_target_uses_blinky_position() -> None:
    """
    Inkyのターゲットは「パックマン前方2マスの基準点」そのものではなく、
    Blinkyから基準点へのベクトルを2倍延長した先のマスになる
    （本家Wikiのアルゴリズム: target = 2 * pivot - blinky_pos）。

    パックマン(10,10)が右向きなら基準点は(12,10)。Inkyをちょうど
    基準点の位置に置くと、
      - 旧実装（基準点をそのまま狙う実装）は「自分の現在地」を狙う形になり、
        移動してもどの方向も距離が変わらずタイブレーカーの優先順位で
        常にUPを選んでしまう。
      - 正しい実装はBlinkyが(2,10)にいる時、target=(22,10)となり、
        明確にRIGHTを選ぶはずである。
    """
    maze_data = [[0] * 26 for _ in range(26)]

    blinky = Blinky(2.0, 10.0)
    inky = Inky(12.0, 10.0)
    pacman = Pacman(10.0, 10.0)
    pacman.direction = Direction.RIGHT

    direction = inky.determine_direction(pacman, maze_data, [blinky, inky])

    assert direction == Direction.RIGHT
