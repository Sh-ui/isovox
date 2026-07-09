"""World: sparse voxel terrain + entities. Pure domain state, no I/O.

Terrain is a dict of (u, v, h) -> (glyph, color): fully destructible by
construction (kaiju games just del cells). Entities are movable voxel models
with float positions; physics.py moves them, raster.py draws them.
"""

from __future__ import annotations

import math
from itertools import count

from .model import VoxModel, Voxel
from .palette import resolve

_ids = count(1)


class Entity:
    """A movable thing: a voxel model at a float position.

    Subclass freely in games; the engine only touches the fields below.
    """

    def __init__(self, model: VoxModel, pos=(0.0, 0.0, 0.0), *,
                 solid: bool = True, gravity: bool = False, tag: str = "",
                 ttl: float | None = None):
        self.id = next(_ids)
        self.model = model
        self.pos = list(map(float, pos))   # [u, v, h]
        self.vel = [0.0, 0.0, 0.0]
        self.solid = solid          # blocks / is blocked by terrain and entities
        self.gravity = gravity      # falls until supported
        self.on_ground = False
        self.tag = tag              # free-form label games filter on
        self.alive = True           # set False to despawn at end of frame
        self.ttl = ttl              # seconds to live (None = forever); engine reaps

    @property
    def footprint(self) -> tuple[int, int, int]:
        return self.model.size

    def cells(self) -> tuple[range, range, range]:
        """Integer cell ranges currently occupied (u, v, h).

        u/v round, h floors -- same convention as physics._blocked.
        """
        du, dv, dh = self.model.size
        u, v = round(self.pos[0]), round(self.pos[1])
        h = math.floor(self.pos[2])
        return range(u, u + du), range(v, v + dv), range(h, h + dh)

    def overlaps(self, other: "Entity") -> bool:
        for a, b in zip(self.cells(), other.cells()):
            if a.start >= b.stop or b.start >= a.stop:
                return False
        return True


class World:
    def __init__(self, floor_h: int | None = 0):
        self.terrain: dict[tuple[int, int, int], Voxel] = {}
        self.entities: list[Entity] = []
        # floor_h: implicit infinite floor entities rest on (None = bottomless)
        self.floor_h = floor_h
        # bumped on every terrain change; raster caches terrain columns by it
        self.version = 0
        self.gravity = 30.0     # cells/s^2; crank it for snappy arcade hops

    # -- terrain ---------------------------------------------------------
    def set(self, u: int, v: int, h: int, color: str, glyph: str = "#") -> None:
        self.terrain[(u, v, h)] = (glyph, resolve(color))
        self.version += 1

    def clear(self, u: int, v: int, h: int) -> None:
        self.terrain.pop((u, v, h), None)
        self.version += 1

    def fill(self, u0: int, v0: int, u1: int, v1: int,
             h0: int, h1: int, color: str, glyph: str = "#") -> None:
        """Fill a box, half-open on the top of each range: [u0,u1) x [v0,v1) x [h0,h1)."""
        vox = (glyph, resolve(color))
        for u in range(u0, u1):
            for v in range(v0, v1):
                for h in range(h0, h1):
                    self.terrain[(u, v, h)] = vox
        self.version += 1

    def stamp(self, model: VoxModel, u: int, v: int, h: int = 0) -> None:
        """Bake a voxel model into terrain (buildings, props)."""
        for (mu, mv, mh), vox in model.voxels.items():
            self.terrain[(u + mu, v + mv, h + mh)] = vox
        self.version += 1

    def carve(self, u: int, v: int, h: int, radius: int = 1) -> list:
        """Remove terrain in a cube around a point.

        Returns the removed voxels as [((u, v, h), (glyph, color)), ...] --
        feed them to isovox.fx.debris for flying-rubble effects.
        """
        removed = []
        for du in range(-radius, radius + 1):
            for dv in range(-radius, radius + 1):
                for dh in range(-radius, radius + 1):
                    key = (u + du, v + dv, h + dh)
                    vox = self.terrain.pop(key, None)
                    if vox is not None:
                        removed.append((key, vox))
        if removed:
            self.version += 1
        return removed

    def is_solid(self, u: int, v: int, h: int) -> bool:
        if self.floor_h is not None and h < self.floor_h:
            return True
        return (u, v, h) in self.terrain

    def top_h(self, u: int, v: int) -> int | None:
        """Height of the first free cell above the tallest solid at (u, v)."""
        hs = [h for (tu, tv, h) in self.terrain if tu == u and tv == v]
        if hs:
            return max(hs) + 1
        return self.floor_h

    # -- entities --------------------------------------------------------
    def spawn(self, entity: Entity) -> Entity:
        self.entities.append(entity)
        return entity

    def by_tag(self, tag: str) -> list[Entity]:
        return [e for e in self.entities if e.tag == tag and e.alive]

    def reap(self) -> None:
        self.entities = [e for e in self.entities if e.alive]
