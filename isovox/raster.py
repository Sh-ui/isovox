"""Rasterize a World into a CharBuffer -- the wallpaper renderer, generalized.

Per frame: merge terrain voxels and entity voxels into per-column stacks,
paint columns back-to-front (ascending u + v), and inside each column paint
each exposed voxel top as a topw x toph char block plus hrow wall rows per
voxel (left half lit, right half dark). Painter order gives occlusion free.

Depth cues, straight from the wallpaper:
 - atmospheric fade: columns far behind the camera center blend toward the
   background (quantized so the color cache stays hot)
 - rim glint: BACK edges only (a lower neighbor at u-1 or v-1) get a cream
   lift, outlining top surfaces without flattening the front walls

Terrain columns are cached against World.version (terrain changes rarely;
entities move every frame), so the per-frame cost is proportional to entity
voxels plus visible columns, not total terrain size. Matters on small CPUs.
"""

from __future__ import annotations

from .buffer import CharBuffer
from .palette import glint, lerp, shades
from .project import Camera
from .world import World

Column = dict[tuple[int, int], list[tuple[int, str, str]]]  # (u,v) -> [(h, glyph, color)]

_NEG_INF = -(10 ** 9)
FADE_PER_STEP = 0.035   # how fast far columns sink into the background
FADE_FREE = 6           # steps behind camera center before fading starts
FADE_MAX = 0.55


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
    m = camera.metrics
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
    cdepth = camera.center[0] + camera.center[1]
    half = m.topw // 2

    for (u, v) in sorted(cols, key=lambda k: k[0] + k[1]):
        c = round(c0 + m.ucol * (u - v))
        if c <= -m.topw or c >= w:
            continue
        rb = round(r0 + m.urow * (u + v))     # h=0 ground line
        stack = cols[(u, v)]                  # ascending h

        # atmospheric fade: dead zone keeps the play area uniform (no banding
        # across nearby flat surfaces), then coarse 0.1 steps into the distance
        dist = cdepth - (u + v) - FADE_FREE
        fade = 0.0 if dist <= 0 else min(FADE_MAX, round(dist * FADE_PER_STEP * 10) / 10)

        # top face of each local stack top (no voxel directly above)
        present = {h for h, _, _ in stack}
        for h, gl, color in stack:
            if h + 1 in present:
                continue
            if fade:
                color = lerp(color, bg, fade)
            top_end = rb + m.toph - 1 - m.hrow * (h + 1)
            # back-edge glint only: lower back neighbors outline the surface
            exposed = (top_of.get((u - 1, v), _NEG_INF) < h or
                       top_of.get((u, v - 1), _NEG_INF) < h)
            tc = glint(color) if exposed else color
            if gl == ".":
                # stipple: one dot per world cell, wallpaper-style, instead
                # of a solid block of periods
                put(top_end, c + half - 1, ".", tc)
            else:
                for rr in range(top_end - m.toph + 1, top_end + 1):
                    for cc in range(c, c + m.topw):
                        put(rr, cc, gl, tc)

        # walls after tops: hrow rows per voxel, left half lit, right half dark.
        # a wall is only visible if the column diagonally in front is lower;
        # interior walls of flat surfaces are skipped (thinned "." tops no
        # longer over-paint them, and it is cheaper besides)
        front_top = top_of.get((u + 1, v + 1), _NEG_INF)
        for h, gl, color in stack:
            if front_top >= h:
                continue
            if fade:
                color = lerp(color, bg, fade)
            _, wl_col, wr_col = shades(color, bg)
            wg = gl if gl not in (".", " ") else ":"
            hi = rb + m.toph - 1 - m.hrow * h
            for rr in range(hi - m.hrow + 1, hi + 1):
                for cc in range(c, c + half):
                    put(rr, cc, wg, wl_col)
                for cc in range(c + half, c + m.topw):
                    put(rr, cc, wg, wr_col)
