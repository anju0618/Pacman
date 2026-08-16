from typing import Iterator

import pygame
import pytest

from src.graphic.sprites import SPRITE_FILENAMES, SpriteSet


@pytest.fixture(autouse=True)
def _pygame_display(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_loads_every_declared_sprite() -> None:
    sprites = SpriteSet()

    for key in SPRITE_FILENAMES:
        sprite = sprites.get(key, 32)
        assert sprite.get_size() == (32, 32)


def test_scaled_sprites_are_cached_per_size() -> None:
    sprites = SpriteSet()

    first = sprites.get("pacman_open", 40)
    second = sprites.get("pacman_open", 40)
    third = sprites.get("pacman_open", 20)

    assert first is second
    assert first is not third
    assert third.get_size() == (20, 20)
