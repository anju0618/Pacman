"""assets/sprites_horror/ 用のグロテスク版スプライトを生成するスクリプト。

通常のassets/sprites/と同じファイル名・同じ128x128の解像度で、
pygameの図形描画(円・多角形・線)だけを使って不気味な見た目の
スプライト一式を手続き的に生成する。外部の画像素材やAI画像生成は
使わず、形状はすべてこのスクリプトのコードで組み立てている
(README「Resources」セクション参照)。

実行方法:
    SDL_VIDEODRIVER=dummy uv run python scripts/generate_horror_sprites.py

生成物はリポジトリにコミットされるため、通常のプレイではこの
スクリプトを実行する必要はない。差し替えたい場合のみ再実行する。
"""
import math
import os
import random
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

SIZE = 128
CENTER = (SIZE // 2, SIZE // 2)
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "assets" / "sprites_horror"

BONE = (176, 168, 132)
BONE_DARK = (132, 122, 88)
BLOOD = (110, 8, 8)
BLOOD_DARK = (60, 4, 4)
SCLERA = (222, 214, 188)
VEIN = (150, 15, 15)
PUPIL = (12, 8, 8)
CRACK = (25, 15, 15)

GHOST_COLORS = {
    "blinky": ((150, 20, 20), (90, 10, 10)),
    "pinky": ((160, 70, 120), (95, 35, 70)),
    "inky": ((40, 110, 120), (15, 60, 70)),
    "clyde": ((150, 95, 30), (95, 55, 15)),
}
FRIGHTENED_COLOR = ((60, 30, 90), (30, 12, 55))


def new_surface() -> pygame.Surface:
    return pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)


def bloodshot_eye(
    surf: pygame.Surface,
    center: tuple[float, float],
    radius: float,
    rng: random.Random,
    hollow: bool = False,
) -> None:
    """血走った目(または虚ろな眼窩)を描く。"""
    cx, cy = center
    if hollow:
        pygame.draw.circle(surf, CRACK, center, radius)
        rim_width = max(1, int(radius * 0.25))
        pygame.draw.circle(surf, BLOOD_DARK, center, radius, rim_width)
        return

    pygame.draw.circle(surf, SCLERA, center, radius)
    for _ in range(5):
        angle = rng.uniform(0, math.tau)
        edge = (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
        mid = (
            cx + math.cos(angle) * radius * rng.uniform(0.25, 0.55),
            cy + math.sin(angle) * radius * rng.uniform(0.25, 0.55),
        )
        pygame.draw.line(surf, VEIN, edge, mid, 2)

    pupil_radius = radius * 0.48
    offset = radius * 0.22
    pupil_center = (
        cx + rng.uniform(-offset, offset),
        cy + rng.uniform(-offset, offset),
    )
    pygame.draw.circle(surf, PUPIL, pupil_center, pupil_radius)
    pygame.draw.circle(surf, BLOOD, pupil_center, pupil_radius, 2)


def crack_line(
    surf: pygame.Surface,
    start: tuple[float, float],
    rng: random.Random,
    segments: int,
    step: float,
    color: tuple[int, int, int] = CRACK,
) -> None:
    """ジグザグなひび割れの線を描く。"""
    x, y = start
    angle = rng.uniform(0, math.tau)
    for _ in range(segments):
        angle += rng.uniform(-1.2, 1.2)
        nx = x + math.cos(angle) * step
        ny = y + math.sin(angle) * step
        pygame.draw.line(surf, color, (x, y), (nx, ny), 2)
        x, y = nx, ny


def drip(
    surf: pygame.Surface,
    top: tuple[float, float],
    rng: random.Random,
    color: tuple[int, int, int],
    length: float,
) -> None:
    """滴り落ちる血のしずくを描く。"""
    x, y = top
    width = rng.uniform(3, 6)
    points = [
        (x - width, y),
        (x + width, y),
        (x + width * 0.4, y + length * 0.7),
        (x, y + length),
        (x - width * 0.4, y + length * 0.7),
    ]
    pygame.draw.polygon(surf, color, points)


def jagged_teeth(
    surf: pygame.Surface,
    left: tuple[float, float],
    right: tuple[float, float],
    rng: random.Random,
    count: int,
    depth: float,
    color: tuple[int, int, int],
) -> None:
    """左右2点の間に、上下互い違いの尖った牙を並べて描く。"""
    lx, ly = left
    rx, ry = right
    for i in range(count):
        t0 = i / count
        t1 = (i + 1) / count
        base_left = (lx + (rx - lx) * t0, ly + (ry - ly) * t0)
        base_right = (lx + (rx - lx) * t1, ly + (ry - ly) * t1)
        mid_x = (base_left[0] + base_right[0]) / 2
        mid_y = (base_left[1] + base_right[1]) / 2
        jitter = rng.uniform(0.7, 1.15)
        if i % 2 == 0:
            tip_y = mid_y + depth * jitter
        else:
            tip_y = mid_y - depth * jitter * 0.4
        pygame.draw.polygon(
            surf, color, [base_left, base_right, (mid_x, tip_y)]
        )


def make_pacman(mouth_half_angle: float, rng_seed: int) -> pygame.Surface:
    """血まみれパックマン(口の開き具合はmouth_half_angleで指定、度数)。"""
    rng = random.Random(rng_seed)
    surf = new_surface()
    radius = 56

    pygame.draw.circle(surf, BONE, CENTER, radius)

    if mouth_half_angle > 0:
        rad = math.radians(mouth_half_angle)
        tip = CENTER
        cx, cy = CENTER
        top = (cx + math.cos(rad) * radius, cy - math.sin(rad) * radius)
        bottom = (cx + math.cos(rad) * radius, cy + math.sin(rad) * radius)
        # 口の部分を、白いマスクを描いてからRGBA_SUBで減算し透明にくり抜く。
        hole_points: list[tuple[float, float]] = [tip]
        steps = 10
        for i in range(steps + 1):
            angle = -rad + (2 * rad) * i / steps
            hole_points.append(
                (cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
            )
        mask = new_surface()
        pygame.draw.polygon(mask, (255, 255, 255, 255), hole_points)
        surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

        jagged_teeth(
            surf, top, tip, rng, count=3, depth=10, color=BONE_DARK
        )
        jagged_teeth(
            surf, tip, bottom, rng, count=3, depth=10, color=BONE_DARK
        )
    else:
        crack_line(surf, (CENTER[0] - 30, CENTER[1] + 6), rng, 5, 9)
        crack_line(surf, (CENTER[0] + 5, CENTER[1] - 2), rng, 4, 8)

    bloodshot_eye(surf, (CENTER[0] - 6, CENTER[1] - 26), 11, rng)
    crack_line(surf, (CENTER[0] + 30, CENTER[1] - 30), rng, 3, 7)
    drip(surf, (CENTER[0] - 40, CENTER[1] - 50), rng, BLOOD, 14)
    return surf


def ghost_outline(rng: random.Random) -> list[tuple[float, float]]:
    cx, top_y, r = 64.0, 58.0, 46.0
    points: list[tuple[float, float]] = []
    steps = 14
    for i in range(steps + 1):
        angle = math.pi - (math.pi * i / steps)
        points.append((cx + math.cos(angle) * r, top_y - math.sin(angle) * r))

    bottom_y = 108.0
    teeth = 6
    xs = [cx + r - (2 * r) * i / teeth for i in range(teeth + 1)]
    for i, x in enumerate(xs):
        if i % 2 == 0:
            points.append((x, bottom_y + rng.uniform(3, 12)))
        else:
            points.append((x, bottom_y - rng.uniform(4, 14)))
    return points


def make_ghost(
    body_color: tuple[int, int, int],
    shadow_color: tuple[int, int, int],
    rng_seed: int,
    hollow_eyes: bool = False,
) -> pygame.Surface:
    rng = random.Random(rng_seed)
    surf = new_surface()
    outline = ghost_outline(rng)
    pygame.draw.polygon(surf, body_color, outline)

    for i in range(0, len(outline) - 1, 3):
        crack_line(surf, outline[i], rng, 2, 5, color=shadow_color)

    bloodshot_eye(surf, (48, 56), 13, rng, hollow=hollow_eyes)
    bloodshot_eye(surf, (80, 56), 13, rng, hollow=hollow_eyes)

    jagged_teeth(
        surf, (44, 84), (84, 84), rng, count=5, depth=8, color=shadow_color
    )

    if rng.random() < 0.9:
        drip_top = (rng.uniform(30, 96), 96)
        drip(surf, drip_top, rng, BLOOD_DARK, rng.uniform(10, 20))
    return surf


def make_eaten_eyes(rng_seed: int) -> pygame.Surface:
    rng = random.Random(rng_seed)
    surf = new_surface()
    bloodshot_eye(surf, (48, 64), 14, rng)
    bloodshot_eye(surf, (80, 64), 14, rng)
    return surf


def make_gum(radius: float, rng_seed: int) -> pygame.Surface:
    rng = random.Random(rng_seed)
    surf = new_surface()
    bloodshot_eye(surf, CENTER, radius, rng)
    return surf


def make_wall(rng_seed: int) -> pygame.Surface:
    rng = random.Random(rng_seed)
    surf = new_surface()
    surf.fill(BLOOD_DARK)
    pygame.draw.rect(surf, (35, 2, 2), (0, 0, SIZE, SIZE), 6)

    for _ in range(4):
        start = (rng.uniform(10, SIZE - 10), rng.uniform(10, SIZE - 10))
        crack_line(surf, start, rng, rng.randint(4, 7), 10, color=(15, 5, 5))

    for _ in range(3):
        drip(
            surf,
            (rng.uniform(15, SIZE - 15), rng.uniform(0, 20)),
            rng,
            BLOOD,
            rng.uniform(20, 45),
        )
    return surf


def main() -> None:
    pygame.init()
    pygame.display.set_mode((1, 1))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sprites: dict[str, pygame.Surface] = {
        "wall.png": make_wall(1),
        "pacman_open.png": make_pacman(45, 2),
        "pacman_half.png": make_pacman(20, 3),
        "pacman_closed.png": make_pacman(0, 4),
        "pacgum.png": make_gum(14, 5),
        "super_pacgum.png": make_gum(30, 6),
        "ghost_blinky.png": make_ghost(*GHOST_COLORS["blinky"], rng_seed=7),
        "ghost_pinky.png": make_ghost(*GHOST_COLORS["pinky"], rng_seed=8),
        "ghost_inky.png": make_ghost(*GHOST_COLORS["inky"], rng_seed=9),
        "ghost_clyde.png": make_ghost(*GHOST_COLORS["clyde"], rng_seed=10),
        "ghost_frightened.png": make_ghost(
            *FRIGHTENED_COLOR, rng_seed=11, hollow_eyes=True
        ),
        "ghost_eaten.png": make_eaten_eyes(12),
    }

    for filename, surface in sprites.items():
        pygame.image.save(surface, str(OUTPUT_DIR / filename))
        print(f"wrote {OUTPUT_DIR / filename}")


if __name__ == "__main__":
    main()
