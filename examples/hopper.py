"""Hopper -- a crossy-road demo. Arrows hop, cars flatten, q quits.

Run it:     python3 hopper.py               (from examples/, any cwd)
       or:  python3 -m examples.hopper      (from the repo root)
Peek at it: python -m isovox.snapshot examples.hopper --frames 40 --ansi
"""

from __future__ import annotations

import os
import sys
import random

if __package__ in (None, ""):   # running as a plain script, not `-m examples.hopper`
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from isovox import Entity, Game, VoxModel, run
from isovox.palette import UMBRA, lerp

ASSETS = os.path.join(os.path.dirname(__file__), "..", "isovox", "assets")

LANES = 60          # how far the road stretches ahead
WIDTH = 10          # playfield half-width along v
START_U = 4


class Hopper(Game):
    def setup(self):
        self.world.floor_h = None            # only painted ground exists
        self.rng = random.Random(11)
        self.grass = lerp("green", UMBRA, 0.72)
        self.road = lerp("slate", UMBRA, 0.62)
        self.car_model = VoxModel.load(os.path.join(ASSETS, "car.ivx"))
        self.tree = VoxModel.load(os.path.join(ASSETS, "tree.ivx"))
        self.roads = set()

        for u in range(-LANES, START_U + 3):
            is_road = u < START_U - 1 and self.rng.random() < 0.5
            if is_road:
                self.roads.add(u)
            base = self.road if is_road else self.grass
            color = lerp(base, UMBRA, 0.10) if u % 2 else base   # lane banding
            for v in range(-WIDTH, WIDTH + 1):
                self.world.set(u, v, 0, color, "-" if is_road else ".")
            if is_road:
                self._spawn_cars(u)
            else:
                for v in self.rng.sample(range(-WIDTH + 1, WIDTH), 3):
                    if u < START_U - 1:
                        self.world.stamp(self.tree, u, v, 1)

        self.world.gravity = 60.0        # short snappy hop arcs
        self.pending = None              # buffered input: land -> hop immediately
        self.player = self.world.spawn(Entity(
            VoxModel.load(os.path.join(ASSETS, "guy.ivx")),
            pos=(START_U, 0, 1), gravity=True, tag="player"))
        self.camera.follow(self.player)
        self.best = 0

    def _spawn_cars(self, u):
        speed = self.rng.choice([3.0, 4.5, 6.0]) * self.rng.choice([1, -1])
        for i in range(self.rng.randint(1, 2)):
            v = self.rng.uniform(-WIDTH, WIDTH)
            car = self.world.spawn(Entity(self.car_model, pos=(u, v, 1), tag="car"))
            car.vel[1] = speed

    def update(self, dt, events):
        p = self.player
        # buffer the newest direction; consume it the moment we can hop.
        # (keys pressed mid-hop land the next hop instead of vanishing)
        for e in events:
            d = {"up": (-1, 0), "down": (1, 0),
                 "left": (0, 1), "right": (0, -1)}.get(e.name)
            if d:
                self.pending = d
        if self.pending and p.on_ground:
            du, dv = self.pending
            self.pending = None
            nu, nv = round(p.pos[0]) + du, round(p.pos[1]) + dv
            if abs(nv) <= WIDTH and not self.world.is_solid(nu, nv, 1):
                p.pos[0], p.pos[1] = float(nu), float(nv)
                p.vel[2] = 9.0           # with gravity 60: ~0.3s, ~0.7 cell arc
        # cars wrap around the playfield edges
        for car in self.world.by_tag("car"):
            if car.pos[1] > WIDTH + 4:
                car.pos[1] = -WIDTH - 4.0
            elif car.pos[1] < -WIDTH - 4:
                car.pos[1] = WIDTH + 4.0
        self.best = max(self.best, START_U - round(p.pos[0]))
        if p.pos[2] < -8:                # hopped off the world
            self._reset()

    def on_collide(self, a, b):
        if {a.tag, b.tag} == {"player", "car"}:
            self._reset()

    def _reset(self):
        self.player.pos = [float(START_U), 0.0, 1.0]
        self.player.vel = [0.0, 0.0, 0.0]

    def draw_hud(self, buf):
        buf.text(0, 2, f" hops ahead: {self.best}  best-run scoring ", "cream")
        buf.text(buf.height - 1, 2, " arrows hop - q quits ", "slate")


if __name__ == "__main__":
    run(Hopper())
