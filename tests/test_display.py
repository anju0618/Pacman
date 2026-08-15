from pathlib import Path

import pygame
import pytest

from src.enums import GameState
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
        assert display.cell_size == 30
        assert display.screen.get_size() == (330, 330)
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
        level=[{"id": 1, "width": 21, "height": 21}],
    )
    game_context = PacmanGameContext(config=config)
    display = Display(game_context)
    try:
        assert len(display.maze_data) == 43
        assert display.cell_size == 18
        assert display.screen.get_size() == (774, 774)
    finally:
        pygame.quit()


def test_display_clears_at_bottom_right_goal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    game_context = PacmanGameContext(
        config=Config(level=[{"id": 1, "width": 5, "height": 5}])
    )
    display = Display(game_context)
    try:
        assert not display.is_cleared()

        goal_x, goal_y = display.goal_position
        display.pacman.x = float(goal_x)
        display.pacman.y = float(goal_y)

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
