"""Rasterize a World into a CharBuffer -- the wallpaper renderer, generalized.

Per frame: merge terrain voxels and entity voxels into per-column stacks,
paint columns back-to-front (ascending u + v), and inside each column paint
contiguous stacks as a 2x2-char top face plus one wall row per voxel of
height (left char lit, right char dark). Painter order gives occlusion free.

Terrain columns are cached against World.version (terrain changes rarely;
entities move every frame), so the per-frame cost is proportional to entity
voxels plus visible columns, not total terrain size. Matters on small CPUs.
"""

from __future__ import annotations

from .buffer import CharBuffer
from .palette import glint, shades
from .project import Camera
from .world import World

Column = dict[tuple[int, int], list[tuple[int, str, str]]]  # (u,v) -> [(h, glyph, color)]

_NEG_INF = -(10 ** 9)


def _terrain_columns(world: World) -> tuple[Column, dict[tuple[int, int], int]]:
    """Sorted terrain stacks + per-column top height, cached by world.version."""
    cached = getattr(world, "_raster_cache", None)
    if cached is not None and cached[0] == world.version:
        return cached[1], cached[2]
    cols: Column = {}
    for (u, v, h), (glyph, color) in world.terrain.items():
        cols.setdefault((u, v), []).append((h, glyph, color))
    for stack in cols.values():
        stack.sort()
    top = {uv: stack[-1][0] for uv, stack in cols.items()}
    world._raster_cache = (world.version, cols, top)
    return cols, top


def raster(world: World, camera: Camera, buf: CharBuffer) -> None:
    buf.clear()
    c0, r0 = camera.anchor(buf.width, buf.height)
    base_cols, base_top = _terrain_columns(world)

    # merge entity voxels copy-on-write: only touched columns get copied
    cols: Column = dict(base_cols)
    top_of = dict(base_top)
    touched = set()
    for e in world.entities:
        if not e.alive:
            continue
        eu, ev, eh = round(e.pos[0]), round(e.pos[1]), round(e.pos[2])
        for (mu, mv, mh), (glyph, color) in e.model.voxels.items():
            key = (eu + mu, ev + mv)
            h = eh + mh
            if key not in touched:
                cols[key] = list(cols.get(key, ()))
                touched.add(key)
            cols[key].append((h, glyph, color))
            if top_of.get(key, _NEG_INF) < h:
                top_of[key] = h
    for key in touched:
        cols[key].sort()

    w = buf.width
    bg = buf.bg
    put = buf.put

    for (u, v) in sorted(cols, key=lambda k: k[0] + k[1]):
        c = round(c0 + 2 * (u - v))
        rb = round(r0 + u + v)          # row of the h=0 ground line
        if c < -1 or c >= w:
            continue
        stack = cols[(u, v)]            # ascending h

        # top face (2x2 block) of each local stack top (no voxel directly above)
        present = {h for h, _, _ in stack}
        for h, gl, color in stack:
            if h + 1 in present:
                continue
            rt = rb - h - 1             # top rows rt, rt+1; walls start at rt+2
            exposed = any(
                top_of.get(nb, _NEG_INF) < h
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
