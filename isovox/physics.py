"""Minimal arcade physics: velocity integration, gravity, terrain blocking,
entity overlap detection. Deliberately simple -- enough for crossy-road hops,
smashy-road driving, and kaiju stomps; not a rigid-body sim.

Axis-by-axis movement against the terrain grid: each axis moves independently
and stops (zeroing that velocity component) if the entity's footprint would
enter a solid cell. Gravity pulls h down until supported.
"""

import math

from .world import World, Entity

GRAVITY = 22.0  # cells / s^2, tuned for chunky arcade jumps


def _blocked(world: World, e: Entity, u: float, v: float, h: float) -> bool:
    """Would footprint at (u, v, h) intersect solid terrain?

    u and v round to the nearest cell; h floors, so an entity resting at
    integer height sits exactly on the surface and any dip below it collides.
    That asymmetry keeps ground contact stable (no on_ground flicker).
    """
    du, dv, dh = e.model.size
    ui, vi, hi = round(u), round(v), math.floor(h)
    for cu in range(ui, ui + du):
        for cv in range(vi, vi + dv):
            for ch in range(hi, hi + dh):
                if world.is_solid(cu, cv, ch):
                    return True
    return False


def step(world: World, dt: float) -> list[tuple[Entity, Entity]]:
    """Advance all entities by dt. Returns overlapping (solid) entity pairs."""
    for e in world.entities:
        if not e.alive:
            continue
        u, v, h = e.pos
        vu, vv, vh = e.vel

        if e.gravity:
            vh -= GRAVITY * dt

        if not e.solid:
            e.pos = [u + vu * dt, v + vv * dt, h + vh * dt]
            e.vel[2] = vh
            continue

        # u axis
        nu = u + vu * dt
        if _blocked(world, e, nu, v, h):
            nu, vu = u, 0.0
        # v axis
        nv = v + vv * dt
        if _blocked(world, e, nu, nv, h):
            nv, vv = v, 0.0
        # h axis (gravity / jumps)
        nh = h + vh * dt
        e.on_ground = False
        if _blocked(world, e, nu, nv, nh):
            if vh < 0:
                # land: snap up to the first free integer height
                nh = float(math.ceil(nh))
                while _blocked(world, e, nu, nv, nh):
                    nh += 1.0
                e.on_ground = True
            else:
                nh = h  # bonked a ceiling
            vh = 0.0

        e.pos = [nu, nv, nh]
        e.vel = [vu, vv, vh]

    # overlap pairs among solid entities (games decide what a hit means)
    hits = []
    ents = [e for e in world.entities if e.alive and e.solid]
    for i, a in enumerate(ents):
        for b in ents[i + 1:]:
            if a.overlaps(b):
                hits.append((a, b))
    return hits
