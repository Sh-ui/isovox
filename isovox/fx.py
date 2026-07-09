"""Effects helpers: tiny entities doing juice, no engine changes required.

Debris = 1-voxel entities with velocity, gravity, and a ttl. They are
non-solid (fly through everything) and reap themselves -- cheap enough to
throw a couple dozen per smash.
"""

from __future__ import annotations

import random

from .model import VoxModel
from .world import Entity, World

_GLYPHS = "*+x'`."


def debris(world: World, removed: list, *, count: int = 12,
           speed: float = 7.0, lift: float = 8.0, ttl: float = 0.9,
           rng: random.Random | None = None) -> None:
    """Spray rubble from carved voxels.

    `removed` is world.carve()'s return value: the rubble reuses the real
    positions and colors of what just broke.

        rubble = self.world.carve(u, v, h, radius=1)
        fx.debris(self.world, rubble)
    """
    if not removed:
        return
    rng = rng or random
    picks = removed if len(removed) <= count else rng.sample(removed, count)
    for (u, v, h), (_, color) in picks:
        m = VoxModel({(0, 0, 0): (rng.choice(_GLYPHS), color)})
        e = Entity(m, pos=(u, v, h), solid=False, gravity=True,
                   tag="fx", ttl=ttl * rng.uniform(0.6, 1.2))
        e.vel = [rng.uniform(-speed, speed),
                 rng.uniform(-speed, speed),
                 rng.uniform(lift * 0.3, lift)]
        world.spawn(e)
