"""Isometric projection: world (u, v, h) -> character grid (row, col).

The world sits on a diamond lattice: u runs down-right on screen, v runs
down-left, h runs straight up. Each world cell projects to a 2x2 character
block (the 2:1 shear that makes character-cell isometrics read correctly):

    col = 2 * (u - v)
    row = u + v - h

Painter order is simply ascending (u + v): columns nearer the camera are drawn
later and overwrite what is behind them. Height is handled inside a column by
drawing stacks bottom-up.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def project(u: float, v: float, h: float) -> tuple[float, float]:
    """World -> unanchored (col, row). Camera adds the screen offset."""
    return 2.0 * (u - v), (u + v) - h


@dataclass
class Camera:
    """Anchors the projection to a buffer. Follow a target or set center directly."""
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)  # world point at buffer center
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
        pc, pr = project(cu, cv, ch)
        return width / 2.0 - pc, height / 2.0 - pr

    def to_screen(self, u: float, v: float, h: float,
                  width: int, height: int) -> tuple[int, int]:
        """World point -> (col, row) ints on a buffer of the given size."""
        c0, r0 = self.anchor(width, height)
        pc, pr = project(u, v, h)
        return round(c0 + pc), round(r0 + pr)
