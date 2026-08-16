"""Loads and scales the game's PNG sprites.

Every visual element is drawn from a PNG file in ``assets/sprites/`` instead
of a hardcoded shape. Replacing a file there (keeping the same name) swaps
that element's look with no code changes.
"""
from pathlib import Path
import pygame

ASSET_DIR = Path(__file__).resolve().parents[2] / "assets" / "sprites"

SPRITE_FILENAMES: dict[str, str] = {
    "wall": "wall.png",
    "pacman_open": "pacman_open.png",
    "pacman_half": "pacman_half.png",
    "pacman_closed": "pacman_closed.png",
    "pacgum": "pacgum.png",
    "super_pacgum": "super_pacgum.png",
    "blinky": "ghost_blinky.png",
    "pinky": "ghost_pinky.png",
    "inky": "ghost_inky.png",
    "clyde": "ghost_clyde.png",
    "frightened": "ghost_frightened.png",
    "eaten": "ghost_eaten.png",
}


class SpriteSet:
    """Loads each sprite once and caches per-cell-size scaled copies."""

    def __init__(self, asset_dir: Path = ASSET_DIR) -> None:
        self._originals: dict[str, pygame.Surface] = {
            key: pygame.image.load(
                str(asset_dir / filename)
            ).convert_alpha()
            for key, filename in SPRITE_FILENAMES.items()
        }
        self._scaled_cache: dict[tuple[str, int], pygame.Surface] = {}

    def get(self, key: str, cell_size: int) -> pygame.Surface:
        """Return ``key``'s sprite scaled to ``cell_size`` x ``cell_size``."""
        cache_key = (key, cell_size)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        scaled = pygame.transform.smoothscale(
            self._originals[key], (cell_size, cell_size)
        )
        self._scaled_cache[cache_key] = scaled
        return scaled
