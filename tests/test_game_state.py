# tests/test_game_state.py
from src.enums import GameState
from src.game_state import PacmanGameContext
from src.parse import Config


def test_initial_game_state() -> None:
    context = PacmanGameContext(config=Config())
    assert context.state == GameState.MAIN_MENU
    assert context.lives == 3
    assert context.score == 0


def test_add_score() -> None:
    context = PacmanGameContext(config=Config())
    context.add_score(10)
    assert context.score == 10
    # スコアが減らないことのテスト（負の値は無視される設計）
    context.add_score(-5)
    assert context.score == 10


def test_lose_life_and_game_over() -> None:
    context = PacmanGameContext(config=Config())
    context.state = GameState.IN_GAME

    context.lose_life()
    assert context.lives == 2
    assert context.state == GameState.IN_GAME

    context.lose_life()
    context.lose_life()
    final_state: GameState = context.state
    assert final_state == GameState.GAME_OVER
