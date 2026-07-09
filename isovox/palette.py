"""Colors: named palette, hex math, shade caching.

Everything downstream works with plain "#rrggbb" strings. Shading toward the
background is precomputed and cached so the raster loop never does hex math.
"""

from __future__ import annotations

from functools import lru_cache

# House palette (from the umbra circuit wallpaper). Games may use any hex color;
# these names are just convenient defaults.
PALETTE = {
    "cream": "#F8F2E9", "red": "#ED4B40", "pink": "#D35D92", "magenta": "#C353CC",
    "purple": "#9668E6", "blue": "#1987E8", "teal": "#00ACC1", "mint": "#1BBAA0",
    "green": "#43A047", "yellow": "#BF9800", "orange": "#C47623", "coffee": "#AD774E",
    "slate": "#797B86", "grey": "#7E7E7E", "umbra": "#1F1E1D", "white": "#FFFFFF",
    "black": "#000000",
}
UMBRA = PALETTE["umbra"]


def resolve(color: str) -> str:
    """Accept a palette name or a #rrggbb hex string; return #rrggbb."""
    if color.startswith("#"):
        return color
    try:
        return PALETTE[color]
    except KeyError:
        raise ValueError(f"unknown color {color!r} (use a palette name or #rrggbb)")


def rgb(color: str) -> tuple[int, int, int]:
    c = resolve(color)
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


@lru_cache(maxsize=4096)
def lerp(a: str, b: str, t: float) -> str:
    """Blend color a toward color b by t in [0, 1]."""
    ra, ga, ba = rgb(a)
    rb, gb, bb = rgb(b)
    return "#%02x%02x%02x" % (
        round(ra + (rb - ra) * t),
        round(ga + (gb - ga) * t),
        round(ba + (bb - ba) * t),
    )


# Face-shading ratios: how far each face falls toward the background color.
# Matches the wallpaper renderer: bright top, mid left wall, dark right wall.
TOP_GLINT = 0.30    # top face blends toward cream on exposed edges
WALL_LEFT = 0.38
WALL_RIGHT = 0.60


@lru_cache(maxsize=4096)
def shades(color: str, bg: str) -> tuple[str, str, str]:
    """(top, wall_left, wall_right) for a voxel color against a background."""
    c = resolve(color)
    return c, lerp(c, bg, WALL_LEFT), lerp(c, bg, WALL_RIGHT)


@lru_cache(maxsize=4096)
def glint(color: str) -> str:
    return lerp(color, PALETTE["cream"], TOP_GLINT)
