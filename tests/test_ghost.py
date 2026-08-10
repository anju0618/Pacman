# tests/test_ghost.py
from src.character.blinky import Blinky
from src.character.clyde import Clyde
from src.character.inky import Inky
from src.character.pacman import Pacman
from src.character.pinky import Pinky
from src.enums import Direction
from src.maze_loader import MazeLoader


def test_ghosts_reach_a_stationary_pacman_without_looping_forever() -> None:
    """
    パックマンが静止していても、貪欲法のゴーストAIが迷路内の小さな輪っか
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
