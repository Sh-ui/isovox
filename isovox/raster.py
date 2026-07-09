"""Rasterize a World into a CharBuffer -- the wallpaper renderer, generalized.

Per frame: merge terrain voxels and entity voxels into per-column stacks,
paint columns back-to-front (ascending u + v), and inside each column paint
contiguous stacks as a 2x2-char top face plus one wall row per voxel of
height (left char lit, right char dark). Painter order gives occlusion free.
"""

from __future__ import annotations

from .buffer import CharBuffer
from .palette import glint, shades
from .project import Camera
from .world import World

Column = dict[tuple[int, int], list[tuple[int, str, str]]]  # (u,v) -> [(h, glyph, color)]


def _columns(world: World) -> Column:
    cols: Column = {}
    for (u, v, h), (glyph, color) in world.terrain.items():
        cols.setdefault((u, v), []).append((h, glyph, color))
    for e in world.entities:
        if not e.alive:
            continue
        eu, ev, eh = round(e.pos[0]), round(e.pos[1]), round(e.pos[2])
        for (mu, mv, mh), (glyph, color) in e.model.voxels.items():
            cols.setdefault((eu + mu, ev + mv), []).append((eh + mh, glyph, color))
    return cols


def raster(world: World, camera: Camera, buf: CharBuffer) -> None:
    buf.clear()
    c0, r0 = camera.anchor(buf.width, buf.height)
    cols = _columns(world)
    top_of: dict[tuple[int, int], int] = {
        uv: max(h for h, _, _ in stack) for uv, stack in cols.items()
    }
    w, hgt = buf.width, buf.height
    bg = buf.bg
    put = buf.put

    for (u, v) in sorted(cols, key=lambda k: k[0] + k[1]):
        c = round(c0 + 2 * (u - v))
        rb = round(r0 + u + v)          # row of the h=0 ground line
        if c < -1 or c >= w:
            continue
        stack = sorted(cols[(u, v)])    # ascending h; later (higher) wins ties

        # top face (2x2 block) of each local stack top (no voxel directly above)
        present = {h for h, _, _ in stack}
        for h, gl, color in stack:
            if h + 1 in present:
                continue
            rt = rb - h - 1             # top rows rt, rt+1; walls start at rt+2
            exposed = any(
                top_of.get(nb, -10**9) < h
                for nb in ((u - 1, v), (u + 1, v), (u, v - 1), (u, v + 1))
            )
            tc = glint(color) if exposed else color
            put(rt, c, gl, tc)
            put(rt, c + 1, gl, tc)
            put(rt + 1, c, gl, tc)
            put(rt + 1, c + 1, gl, tc)

        # walls after tops: one row per voxel (its front face), left lit, right dark
        for h, gl, color in stack:
            wr = rb + 1 - h
            _, wl_col, wr_col = shades(color, bg)
            wg = gl if gl not in (".", " ") else ":"
            put(wr, c, wg, wl_col)
            put(wr, c + 1, wg, wr_col)
