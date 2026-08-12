import pytest

from src.character.blinky import Blinky
from src.character.pacman import Pacman
from src.enums import Direction


OPEN_MAZE = [[0] * 5 for _ in range(5)]


@pytest.mark.parametrize("maze_data", [[], [[0, 0], []]])
def test_pacman_treats_invalid_maze_shape_as_blocked(
    maze_data: list[list[int]]
) -> None:
    pacman = Pacman(0.0, 1.0)
    start_position = pacman.x, pacman.y

    pacman.update(maze_data)

    assert (pacman.x, pacman.y) == start_position


def test_pacman_cuts_inside_corner_without_speed_bonus() -> None:
    maze_data = [row.copy() for row in OPEN_MAZE]
    maze_data[1][1] = 1
    pacman = Pacman(2.0, 2.0)
    pacman.x -= pacman.speed + 0.07
    pacman.direction = Direction.RIGHT
    pacman.set_direction(Direction.UP)

    start_x, start_y = pacman.x, pacman.y
    pacman.update(maze_data)

    displacement = (
        (pacman.x - start_x) ** 2 + (pacman.y - start_y) ** 2
    ) ** 0.5

    assert displacement == pytest.approx(pacman.speed)
    assert pacman.x < 2.0
    assert pacman.y < 2.0
    assert pacman.direction == Direction.UP
    assert pacman.next_direction is None

    for _ in range(2):
        pacman.update(maze_data)

    assert pacman.x == pytest.approx(2.0)


def test_pacman_does_not_snap_to_unreachable_turn_center() -> None:
    pacman = Pacman(1.7, 2.0)
    pacman.direction = Direction.RIGHT
    pacman.set_direction(Direction.UP)

    pacman.update(OPEN_MAZE)

    assert pacman.x == pytest.approx(1.7 + pacman.speed)
    assert pacman.y == pytest.approx(2.0)
    assert pacman.direction == Direction.RIGHT
    assert pacman.next_direction == Direction.UP


def test_pacman_does_not_turn_into_wall() -> None:
    maze_data = [row.copy() for row in OPEN_MAZE]
    maze_data[1][2] = 1
    pacman = Pacman(1.9, 2.0)
    pacman.direction = Direction.RIGHT
    pacman.set_direction(Direction.UP)

    pacman.update(maze_data)

    assert pacman.x == pytest.approx(1.9 + pacman.speed)
    assert pacman.y == pytest.approx(2.0)
    assert pacman.direction == Direction.RIGHT
    assert pacman.next_direction == Direction.UP


def test_pacman_can_turn_after_slightly_passing_center_at_wall() -> None:
    maze_data = [row.copy() for row in OPEN_MAZE]
    maze_data[2][3] = 1
    pacman = Pacman(2.035, 2.0)
    pacman.direction = Direction.RIGHT
    pacman.set_direction(Direction.UP)

    start_x, start_y = pacman.x, pacman.y
    pacman.update(maze_data)

    displacement = (
        (pacman.x - start_x) ** 2 + (pacman.y - start_y) ** 2
    )
    assert displacement ** 0.5 == pytest.approx(pacman.speed)
    assert pacman.x == pytest.approx(2.0)
    assert pacman.y < start_y
    assert pacman.direction == Direction.UP
    assert pacman.next_direction is None


def test_ghost_does_not_cut_inside_corner() -> None:
    ghost = Blinky(2.0, 2.0)
    ghost.x -= ghost.speed + 0.01
    ghost.direction = Direction.RIGHT
    ghost.next_direction = Direction.UP

    start_x, start_y = ghost.x, ghost.y
    ghost.move_forward(OPEN_MAZE)

    traveled_distance = (
        abs(ghost.x - start_x) + abs(ghost.y - start_y)
    )
    assert traveled_distance == pytest.approx(ghost.speed)
    assert ghost.y == pytest.approx(start_y)
    assert ghost.direction == Direction.RIGHT
    assert ghost.next_direction == Direction.UP
