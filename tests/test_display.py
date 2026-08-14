import pygame
import pytest

from src.game_state import PacmanGameContext
from src.graphic.display import Display
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
    finally:
        pygame.quit()
