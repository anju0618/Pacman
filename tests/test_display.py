from pathlib import Path

import pygame
import pytest

from src.enums import GameState, GhostMode
from src.game_state import PacmanGameContext
from src.graphic.display import Display
from src.highscore import HighScoreEntry, HighScoreSystem
from src.parse import Config


def test_display_advances_to_next_configured_level(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(
        level=[
            {"id": 1, "width": 5, "height": 5},
            {"id": 2, "width": 7, "height": 7},
        ]
    )

    game_context = PacmanGameContext(config=config)
    display = Display(game_context)
    try:
        assert display.game_context is game_context
        assert display.current_level == 1
        assert len(display.maze_data) == 11
        assert display.cell_size == 45
        assert display.screen.get_size() == (495, 495)
        assert len(config.level) == 10
        assert not display.is_cleared()

        game_context.add_score(10)
        assert display.advance_to_next_level()
        assert display.game_context.score == 10
        assert display.current_level == 2
        assert len(display.maze_data) == 15

        while display.advance_to_next_level():
            pass

        assert display.current_level == 10
        assert not display.advance_to_next_level()
        assert display.game_cleared
        assert game_context.state == GameState.VICTORY
    finally:
        pygame.quit()


def test_display_scales_large_maze_to_window_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(
        level=[{"id": 1, "width": 45, "height": 45}],
    )
    game_context = PacmanGameContext(config=config)
    display = Display(game_context)
    try:
        assert len(display.maze_data) == 91
        assert display.cell_size == 21
        assert display.screen.get_size() == (1911, 1911)
    finally:
        pygame.quit()


def test_display_clears_when_all_pacgums_collected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game_context = PacmanGameContext(
        config=Config(level=[{"id": 1, "width": 5, "height": 5}])
    )
    display = Display(game_context)
    try:
        assert not display.is_cleared()

        remaining_positions = (
            list(display.pacgum.normal_positions)
            + list(display.pacgum.super_positions)
        )
        for position in remaining_positions:
            display.pacgum.collect(position)

        assert display.is_cleared()
    finally:
        pygame.quit()


def test_display_submits_final_score(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    highscore_filename = tmp_path / "highscores.json"
    highscore_system = HighScoreSystem(str(highscore_filename))
    game_context = PacmanGameContext(config=Config())
    display = Display(game_context, highscore_system)
    try:
        game_context.state = GameState.GAME_OVER
        game_context.score = 123
        display.name_input = "PLAYER 1"

        display._submit_highscore()

        assert display.score_submitted
        assert highscore_filename.exists()
        assert highscore_system.entries == [
            HighScoreEntry("PLAYER 1", 123)
        ]
        display._render_end_screen()
    finally:
        pygame.quit()


def test_display_does_not_keep_unsaved_score(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    highscore_system = HighScoreSystem(
        str(tmp_path / "missing" / "highscores.json")
    )
    game_context = PacmanGameContext(config=Config(), score=123)
    display = Display(game_context, highscore_system)
    try:
        game_context.state = GameState.GAME_OVER
        display.name_input = "PLAYER 1"

        display._submit_highscore()

        assert display.score_submitted
        assert highscore_system.entries == []
        assert display.score_message == "The score could not be saved."
    finally:
        pygame.quit()


def test_trigger_frightened_scares_ghosts_and_starts_timer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game_context = PacmanGameContext(
        config=Config(level=[{"id": 1, "width": 9, "height": 9}])
    )
    display = Display(game_context)
    try:
        display._trigger_frightened()

        assert display.frightened_timer > 0
        assert all(
            ghost.mode == GhostMode.FRIGHTENED for ghost in display.ghosts
        )
    finally:
        pygame.quit()


def test_touching_a_frightened_ghost_eats_it_and_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(level=[{"id": 1, "width": 9, "height": 9}])
    game_context = PacmanGameContext(config=config)
    display = Display(game_context)
    try:
        ghost = display.ghosts[0]
        ghost.set_mode(GhostMode.FRIGHTENED)
        ghost.x, ghost.y = display.pacman.x, display.pacman.y

        display._check_ghost_collisions()

        assert ghost.mode == GhostMode.EATEN
        assert game_context.score == config.points_per_ghost
        assert game_context.lives == config.lives
    finally:
        pygame.quit()


def test_touching_a_dangerous_ghost_costs_a_life_and_resets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(level=[{"id": 1, "width": 9, "height": 9}])
    game_context = PacmanGameContext(config=config)
    display = Display(game_context)
    try:
        ghost = display.ghosts[0]
        start_x, start_y = display.pacman.get_current_grid()
        display.pacman.x, display.pacman.y = 0.0, 0.0
        ghost.x, ghost.y = display.pacman.x, display.pacman.y

        display._check_ghost_collisions()

        assert game_context.lives == config.lives - 1
        assert (display.pacman.x, display.pacman.y) == (
            float(start_x), float(start_y)
        )
    finally:
        pygame.quit()


def test_cheat_invincibility_ignores_dangerous_ghost_contact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(level=[{"id": 1, "width": 9, "height": 9}])
    game_context = PacmanGameContext(
        config=config, is_cheat_mode_active=True
    )
    display = Display(game_context)
    try:
        ghost = display.ghosts[0]
        ghost.x, ghost.y = display.pacman.x, display.pacman.y

        display._check_ghost_collisions()

        assert game_context.lives == config.lives
    finally:
        pygame.quit()


def test_timeout_costs_a_life_and_resets_the_clock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(level=[{"id": 1, "width": 9, "height": 9}])
    game_context = PacmanGameContext(
        config=config, state=GameState.IN_GAME
    )
    display = Display(game_context)
    try:
        game_context.time_remaining = 0.0
        display.clock.tick(60)

        display._render_game()

        assert game_context.lives == config.lives - 1
        assert game_context.time_remaining == config.level_max_time
    finally:
        pygame.quit()


def test_tunnel_wrap_teleports_across_the_maze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game_context = PacmanGameContext(
        config=Config(level=[{"id": 1, "width": 9, "height": 9}])
    )
    display = Display(game_context)
    try:
        width = len(display.maze_data[0])
        display.pacman.y = float(display.tunnel_row)
        display.pacman.x = -1.0

        display._apply_tunnel_wrap(display.pacman)
        assert display.pacman.x == pytest.approx(width - 1.0)

        display.pacman.x = float(width)
        display._apply_tunnel_wrap(display.pacman)
        assert display.pacman.x == pytest.approx(0.0)
    finally:
        pygame.quit()


def test_cheat_mode_boosts_speed_and_grants_extra_lives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(level=[{"id": 1, "width": 9, "height": 9}])
    plain_context = PacmanGameContext(config=config)
    plain_display = Display(plain_context)
    cheat_context = PacmanGameContext(
        config=config, is_cheat_mode_active=True
    )
    cheat_display = Display(cheat_context)
    try:
        assert cheat_display.pacman.speed > plain_display.pacman.speed

        cheat_context.reset_for_new_game()
        assert cheat_context.lives == (
            config.lives + PacmanGameContext.CHEAT_EXTRA_LIVES
        )
    finally:
        pygame.quit()


def test_cheat_ghost_freeze_and_level_skip_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    config = Config(
        level=[
            {"id": 1, "width": 9, "height": 9},
            {"id": 2, "width": 9, "height": 9},
        ]
    )
    game_context = PacmanGameContext(
        config=config,
        is_cheat_mode_active=True,
        state=GameState.IN_GAME,
    )
    display = Display(game_context)
    try:
        freeze_event = pygame.event.Event(
            pygame.KEYDOWN, key=pygame.K_f
        )
        display._handle_event(freeze_event)
        assert display.ghosts_frozen

        skip_event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_n)
        display._handle_event(skip_event)
        assert display.current_level == 2
    finally:
        pygame.quit()
