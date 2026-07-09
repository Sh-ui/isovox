"""Rampage -- a kaiju demo. Arrows walk, space smashes buildings, q quits.

Run it:     python -m examples.rampage      (from the repo root)
Peek at it: python -m isovox.snapshot examples.rampage --frames 40 --ansi
"""

import os
import random

from isovox import Entity, Game, VoxModel, run
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

        self.kaiju = self.world.spawn(Entity(
            VoxModel.load(os.path.join(ASSETS, "kaiju.ivx")),
            pos=(CITY // 2, CITY // 2, 1), gravity=True, tag="kaiju"))
        self.camera.follow(self.kaiju)
        self.smashed = 0
        self.facing = (1, 0)

    def update(self, dt, events):
        k = self.kaiju
        k.vel[0] = k.vel[1] = 0.0
        for e in events:
            du, dv = {"up": (-1, 0), "down": (1, 0),
                      "left": (0, 1), "right": (0, -1)}.get(e.name, (0, 0))
            if du or dv:
                self.facing = (du, dv)
                k.vel[0], k.vel[1] = du * 7.0, dv * 7.0
            elif e.name == " ":
                fu, fv = self.facing
                cu = round(k.pos[0]) + fu * 2
                cv = round(k.pos[1]) + fv * 2
                for h in (1, 3, 5):      # swipe a column of the building face
                    self.smashed += self.world.carve(cu, cv, h, radius=1)

    def draw_hud(self, buf):
        buf.text(0, 2, f" voxels smashed: {self.smashed} ", "yellow")
        buf.text(buf.height - 1, 2, " arrows walk - space smash - q quits ", "slate")


if __name__ == "__main__":
    run(Rampage())
