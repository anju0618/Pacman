"""ゲーム内の画像(PNGスプライト)を読み込み・拡縮するモジュール。

全ての見た目要素は`assets/sprites/`内のPNGファイルから描画される
(円や矩形の直接描画ではない)。同じファイル名のまま画像を差し替える
だけで、コードを一切変更せずに見た目を変更できる設計にしている。
"""
from pathlib import Path
import pygame

from src.resources import resource_path

# ソース実行時はリポジトリ直下のassets/sprites/、パッケージ版では
# 実行ファイルに同梱されたassets/sprites/を指す(src/resources.py参照)。
ASSET_DIR = resource_path("assets", "sprites")
# --horrorフラグ指定時に使う、グロテスク版スプライト一式
# (scripts/generate_horror_sprites.pyで生成。ファイル名はASSET_DIRと共通)。
HORROR_ASSET_DIR = resource_path("assets", "sprites_horror")

# 「見た目の種類」と「対応するPNGファイル名」の対応表。
# キーを変えずにファイルの中身だけ差し替えれば絵を変えられる。
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
    """各スプライトを1度だけ読み込み、セルサイズごとの拡縮結果をキャッシュするクラス。

    迷路のセルサイズ(cell_size)はレベルによって変わる(_cell_size_for_maze
    参照)ため、同じ元画像でも毎回違うサイズへスケーリングする必要が
    ある。毎フレーム拡縮するのは無駄なので、(種類, セルサイズ)の
    組み合わせごとに結果をキャッシュして再利用する。
    """

    def __init__(self, asset_dir: Path = ASSET_DIR) -> None:
        """全スプライトの元画像を読み込む。

        Args:
            asset_dir: PNGファイルが置かれているディレクトリ。
                テストではダミー画像を置いた別ディレクトリを渡せる
                ように、引数で差し替え可能にしてある。
        """
        self._originals: dict[str, pygame.Surface] = {
            key: pygame.image.load(
                str(asset_dir / filename)
            ).convert_alpha()
            for key, filename in SPRITE_FILENAMES.items()
        }
        self._scaled_cache: dict[tuple[str, int], pygame.Surface] = {}

    def get(self, key: str, cell_size: int) -> pygame.Surface:
        """keyに対応するスプライトを、cell_size x cell_sizeへ拡縮して返す。

        同じ(key, cell_size)の組み合わせは2回目以降キャッシュから
        即座に返す。
        """
        cache_key = (key, cell_size)
        cached = self._scaled_cache.get(cache_key)
        if cached is not None:
            return cached

        scaled = pygame.transform.smoothscale(
            self._originals[key], (cell_size, cell_size)
        )
        self._scaled_cache[cache_key] = scaled
        return scaled
