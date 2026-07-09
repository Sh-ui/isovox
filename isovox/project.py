"""Isometric projection: world (u, v, h) -> character grid (row, col).

The world sits on a diamond lattice: u runs down-right on screen, v runs
down-left, h runs straight up. How many character cells one world step spans
is a Metrics choice, because terminal cells are ~1:2 (w:h) while image pixels
are square -- the same math at one size looks stretched at the other.

    col = ucol * (u - v)
    row = urow * (u + v) - hrow * h

Presets:
  WIDE   -- 4 cols per step, 2 rows per height unit. True 2:1 isometric in a
            normal terminal (1:2 cells). The default for live play.
  SQUARE -- 2 cols / 1 row. The original wallpaper geometry; correct on
            square-ish cells (PNG export at cell_ratio ~1.16, or a terminal
            tuned to near-square cells).

Painter order is ascending (u + v) either way: columns nearer the camera are
drawn later and overwrite what is behind them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Metrics:
    """Screen geometry of one world step. See module docstring."""
    name: str
    ucol: int   # cols per +u step (a +v step mirrors to -ucol)
    urow: int   # rows per +u or +v step
    hrow: int   # rows per +h (wall rows per voxel)
    topw: int   # top-face width in chars
    toph: int   # top-face height in rows


WIDE = Metrics("wide", 4, 1, 2, 4, 2)
SQUARE = Metrics("square", 2, 1, 1, 2, 2)
METRICS = {"wide": WIDE, "square": SQUARE}


def project(u: float, v: float, h: float, m: Metrics = WIDE) -> tuple[float, float]:
    """World -> unanchored (col, row). Camera adds the screen offset."""
    return m.ucol * (u - v), m.urow * (u + v) - m.hrow * h


@dataclass
class Camera:
    """Anchors the projection to a buffer. Follow a target or set center directly."""
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)  # world point at buffer center
    metrics: Metrics = WIDE
    _target: object = field(default=None, repr=False)

    def follow(self, entity) -> None:
        """Track an entity's position each frame (pass None to stop)."""
        self._target = entity

    def update(self) -> None:
        if self._target is not None:
            u, v, h = self._target.pos
            self.center = (u, v, h)

    def anchor(self, width: int, height: int) -> tuple[float, float]:
        """(c0, r0) such that self.center lands mid-buffer."""
        cu, cv, ch = self.center
        pc, pr = project(cu, cv, ch, self.metrics)
        return width / 2.0 - pc, height / 2.0 - pr

    def to_screen(self, u: float, v: float, h: float,
                  width: int, height: int) -> tuple[int, int]:
        """World point -> (col, row) ints on a buffer of the given size."""
        c0, r0 = self.anchor(width, height)
        pc, pr = project(u, v, h, self.metrics)
        return round(c0 + pc), round(r0 + pr)
