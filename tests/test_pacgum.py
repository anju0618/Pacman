from src.pacgum import Pacgum, PacgumKind
from src.maze_loader import MazeLoader

MAZE = [
    [1, 1, 1, 1, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 0, 0, 0, 1],
    [1, 1, 1, 1, 1],
]
SUPER_POSITIONS = [(1, 1), (3, 1), (1, 3), (3, 3)]
CENTER = (2, 2)
AVAILABLE_NORMAL_CELLS = {(2, 1), (1, 2), (3, 2), (2, 3)}


def test_places_super_pacgums_at_given_positions() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
    )

    assert pacgum.super_positions == set(SUPER_POSITIONS)


def test_normal_pacgums_fill_every_remaining_open_cell() -> None:
    """VI.1/VI.4: pacgums belong in most corridors, so every open cell
    that isn't the spawn point or a super-pacgum corner gets one."""
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
    )

    assert pacgum.normal_positions == AVAILABLE_NORMAL_CELLS


def test_collect_removes_and_reports_the_matching_kind() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
    )

    assert pacgum.collect((1, 1)) is PacgumKind.SUPER
    assert (1, 1) not in pacgum.super_positions

    assert pacgum.collect((2, 1)) is PacgumKind.NORMAL
    assert (2, 1) not in pacgum.normal_positions

    assert pacgum.collect((1, 1)) is None
    assert pacgum.collect((0, 0)) is None


def test_is_empty_once_every_pacgum_is_collected() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
    )
    assert not pacgum.is_empty()

    for position in list(pacgum.super_positions) + list(
        pacgum.normal_positions
    ):
        pacgum.collect(position)

    assert pacgum.is_empty()
    assert pacgum.remaining_count() == 0


def test_does_not_place_pacgums_on_unreachable_cells() -> None:
    loader = MazeLoader(width=21, height=21, seed=42)
    maze_data = loader.get_binary_grid()
    start_position = loader.find_center_start_position()
    super_positions = loader.find_corner_positions()
    pacgum = Pacgum(
        maze_data=maze_data,
        super_positions=super_positions,
        excluded_positions=[start_position],
    )

    open_cells = {
        (x, y)
        for y, row in enumerate(maze_data)
        for x, cell in enumerate(row)
        if cell == 0
    }
    reachable = Pacgum._reachable_open_cells(
        maze_data, {start_position}
    )

    assert open_cells - reachable
    assert pacgum.normal_positions <= reachable
