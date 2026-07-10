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

Wall visibility is per-voxel against the occupancy of the column diagonally
in front (u+1, v+1): the wall at height h is skipped only when that column
holds a voxel at h (its top face lands exactly on our wall rows) or at h+1
(its own wall rows do). This keeps stippled "." ground from exposing a wall
under every lawn cell, without the old whole-column-top shortcut that starved
sprites and overhangs of their wall faces (anything behind a tree canopy or a
legged rig used to lose all walls below the front column's max height).

Voxels may carry per-face materials -- (glyph, color, (top, left, right)),
see model.py. Face colors still receive the standard face shading (lerp
toward the background at the wall ratios), so a glass window still reads as
part of the same lit cube.

Terrain columns are cached against World.version (terrain changes rarely;
entities move every frame), so the per-frame cost is proportional to entity
voxels plus visible columns, not total terrain size. Matters on small CPUs.
"""

from __future__ import annotations

from .buffer import CharBuffer
from .palette import glint, lerp, shades
from .project import Camera
from .world import World

# (u,v) -> ascending [(h, voxel)]; voxel = (glyph, color[, faces])
Column = dict[tuple[int, int], list[tuple]]

_NEG_INF = -(10 ** 9)
_EMPTY: frozenset = frozenset()
FADE_PER_STEP = 0.035   # how fast far columns sink into the background
FADE_FREE = 6           # steps behind camera center before fading starts
FADE_MAX = 0.55


def _terrain_columns(world: World):
    """Terrain stacks + per-column top height + occupancy, cached by version."""
    cached = getattr(world, "_raster_cache", None)
    if cached is not None and cached[0] == world.version:
        return cached[1], cached[2], cached[3]
    cols: Column = {}
    for (u, v, h), vox in world.terrain.items():
        cols.setdefault((u, v), []).append((h, vox))
    for stack in cols.values():
        stack.sort(key=lambda t: t[0])
    top = {uv: stack[-1][0] for uv, stack in cols.items()}
    occ = {uv: {h for h, _ in stack} for uv, stack in cols.items()}
    world._raster_cache = (world.version, cols, top, occ)
    return cols, top, occ


def raster(world: World, camera: Camera, buf: CharBuffer) -> None:
    buf.clear()
    m = camera.metrics
    c0, r0 = camera.anchor(buf.width, buf.height)
    base_cols, base_top, base_occ = _terrain_columns(world)

    # merge entity voxels copy-on-write: only touched columns get copied
    cols: Column = dict(base_cols)
    top_of = dict(base_top)
    occ = dict(base_occ)
    touched = set()
    for e in world.entities:
        if not e.alive:
            continue
        eu, ev, eh = round(e.pos[0]), round(e.pos[1]), round(e.pos[2])
        for (mu, mv, mh), vox in e.model.voxels.items():
            key = (eu + mu, ev + mv)
            h = eh + mh
            if key not in touched:
                cols[key] = list(cols.get(key, ()))
                occ[key] = set(occ.get(key, ()))
                touched.add(key)
            cols[key].append((h, vox))
            occ[key].add(h)
            if top_of.get(key, _NEG_INF) < h:
                top_of[key] = h
    for key in touched:
        cols[key].sort(key=lambda t: t[0])

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
        present = occ[(u, v)]

        # atmospheric fade: dead zone keeps the play area uniform (no banding
        # across nearby flat surfaces), then coarse 0.1 steps into the distance
        dist = cdepth - (u + v) - FADE_FREE
        fade = 0.0 if dist <= 0 else min(FADE_MAX, round(dist * FADE_PER_STEP * 10) / 10)

        # top face of each local stack top (no voxel directly above)
        for h, vox in stack:
            if h + 1 in present:
                continue
            faces = vox[2] if len(vox) > 2 else None
            tf = faces[0] if faces else None
            tg, tc = tf if tf else (vox[0], vox[1])
            if fade:
                tc = lerp(tc, bg, fade)
            top_end = rb + m.toph - 1 - m.hrow * (h + 1)
            # back-edge glint only: lower back neighbors outline the surface
            if (top_of.get((u - 1, v), _NEG_INF) < h or
                    top_of.get((u, v - 1), _NEG_INF) < h):
                tc = glint(tc)
            if tg == ".":
                # stipple: one dot per world cell, wallpaper-style, instead
                # of a solid block of periods
                put(top_end, c + half - 1, ".", tc)
            else:
                for rr in range(top_end - m.toph + 1, top_end + 1):
                    for cc in range(c, c + m.topw):
                        put(rr, cc, tg, tc)

        # walls after tops: hrow rows per voxel, left half lit, right half
        # dark. skip only walls provably covered by the front column's own
        # geometry at these exact rows (voxel at h or h+1); see module doc.
        focc = occ.get((u + 1, v + 1), _EMPTY)
        for h, vox in stack:
            if h in focc or h + 1 in focc:
                continue
            gl, color = vox[0], vox[1]
            faces = vox[2] if len(vox) > 2 else None
            wg = gl if gl not in (".", " ") else ":"
            lg, lc = faces[1] if faces and faces[1] else (wg, color)
            rg, rc = faces[2] if faces and faces[2] else (wg, color)
            if fade:
                lc = lerp(lc, bg, fade)
                rc = lerp(rc, bg, fade)
            wl_col = shades(lc, bg)[1]
            wr_col = shades(rc, bg)[2]
            hi = rb + m.toph - 1 - m.hrow * h
            for rr in range(hi - m.hrow + 1, hi + 1):
                for cc in range(c, c + half):
                    put(rr, cc, lg, wl_col)
                for cc in range(c + half, c + m.topw):
                    put(rr, cc, rg, wr_col)
