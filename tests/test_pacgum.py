from src.pacgum import Pacgum, PacgumKind

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
        count=0,
    )

    assert pacgum.super_positions == set(SUPER_POSITIONS)
    assert pacgum.normal_positions == set()


def test_normal_pacgums_avoid_walls_super_and_excluded_cells() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
        count=100,
    )

    assert pacgum.normal_positions == AVAILABLE_NORMAL_CELLS


def test_normal_pacgum_count_is_clamped_to_requested_amount() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
        count=2,
    )

    assert len(pacgum.normal_positions) == 2
    assert pacgum.normal_positions <= AVAILABLE_NORMAL_CELLS


def test_collect_removes_and_reports_the_matching_kind() -> None:
    pacgum = Pacgum(
        maze_data=MAZE,
        super_positions=SUPER_POSITIONS,
        excluded_positions=[CENTER],
        count=100,
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
        count=100,
    )
    assert not pacgum.is_empty()

    for position in list(pacgum.super_positions) + list(
        pacgum.normal_positions
    ):
        pacgum.collect(position)

    assert pacgum.is_empty()
    assert pacgum.remaining_count() == 0
