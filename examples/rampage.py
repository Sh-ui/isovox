"""Rampage -- a kaiju demo. Arrows walk, space smashes buildings, q quits.

Run it:     python3 rampage.py              (from examples/, any cwd)
       or:  python3 -m examples.rampage     (from the repo root)
Peek at it: python -m isovox.snapshot examples.rampage --frames 40 --ansi
"""

from __future__ import annotations

import os
import sys
import random

if __package__ in (None, ""):   # running as a plain script, not `-m examples.rampage`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from isovox import Entity, Game, VoxModel, fx, run
from isovox.palette import UMBRA, lerp

ASSETS = os.path.join(os.path.dirname(__file__), "..", "isovox", "assets")
CITY = 26           # city is CITY x CITY cells


class Rampage(Game):
    def setup(self):
        rng = random.Random(3)
        ground = lerp("slate", UMBRA, 0.75)
        for u in range(-2, CITY + 2):
            for v in range(-2, CITY + 2):
                self.world.set(u, v, 0, ground, ".")
        # city blocks on a loose grid
        for bu in range(0, CITY, 5):
            for bv in range(0, CITY, 5):
                if rng.random() < 0.2:
                    continue
                w, d = rng.randint(2, 3), rng.randint(2, 3)
                hgt = rng.randint(3, 8)
                color = rng.choice(["blue", "purple", "teal", "orange", "slate"])
                tower = VoxModel.box(w, d, hgt, lerp(color, UMBRA, 0.25), "#")
                self.world.stamp(tower, bu + 1, bv + 1, 1)

        self.kaiju_base = VoxModel.load(os.path.join(ASSETS, "kaiju.ivx"))
        self.kaiju = self.world.spawn(Entity(
            self.kaiju_base, pos=(CITY // 2, CITY // 2, 1),
            gravity=True, tag="kaiju"))
        self.camera.follow(self.kaiju)
        self.smashed = 0
        self.facing = (1, 0)
        self.t = 0.0
        self.move_until = 0.0    # walk keeps going briefly past the last repeat

    def update(self, dt, events):
        self.t += dt
        k = self.kaiju
        for e in events:
            du, dv = {"up": (-1, 0), "down": (1, 0),
                      "left": (0, 1), "right": (0, -1)}.get(e.name, (0, 0))
            if du or dv:
                self.facing = (du, dv)
                # one .ivx, four facings: the sprite turns as it walks
                turns = {(1, 0): 0, (0, 1): 1, (-1, 0): 2, (0, -1): 3}
                k.model = self.kaiju_base.rotated(turns[self.facing])
                k.vel[0], k.vel[1] = du * 8.0, dv * 8.0
                self.move_until = self.t + 0.55   # outlast the repeat delay
            elif e.name == " ":
                fu, fv = self.facing
                cu = round(k.pos[0]) + fu * 2
                cv = round(k.pos[1]) + fv * 2
                for h in (1, 3, 5):      # swipe a column of the building face
                    rubble = self.world.carve(cu, cv, h, radius=1)
                    self.smashed += len(rubble)
                    fx.debris(self.world, rubble)
        if self.t >= self.move_until:
            k.vel[0] = k.vel[1] = 0.0

    def draw_hud(self, buf):
        buf.text(0, 2, f" voxels smashed: {self.smashed} ", "yellow")
        buf.text(buf.height - 1, 2, " arrows walk - space smash - q quits ", "slate")


if __name__ == "__main__":
    run(Rampage())
