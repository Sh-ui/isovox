"""World + physics behavior: gravity, landing, blocking, carving, overlaps."""

from isovox import Entity, VoxModel, World
from isovox.physics import step


def make_ground(world, size=10):
    for u in range(size):
        for v in range(size):
            world.set(u, v, 0, "slate")


def test_gravity_lands_on_terrain():
    w = World(floor_h=None)
    make_ground(w)
    e = w.spawn(Entity(VoxModel.box(1, 1, 1, "red"), pos=(2, 2, 5), gravity=True))
    for _ in range(120):
        step(w, 1 / 30)
    assert e.pos[2] == 1.0
    assert e.on_ground


def test_on_ground_is_stable_every_frame():
    w = World(floor_h=None)
    make_ground(w)
    e = w.spawn(Entity(VoxModel.box(1, 1, 1, "red"), pos=(2, 2, 1), gravity=True))
    step(w, 1 / 30)
    for _ in range(30):
        step(w, 1 / 30)
        assert e.on_ground, "ground contact must not flicker"
        assert e.pos[2] == 1.0


def test_wall_blocks_horizontal_motion():
    w = World(floor_h=None)
    make_ground(w)
    w.fill(5, 0, 6, 10, 1, 4, "blue")       # wall across v at u=5
    e = w.spawn(Entity(VoxModel.box(1, 1, 2, "red"), pos=(2, 2, 1), gravity=True))
    e.vel[0] = 4.0
    for _ in range(90):
        step(w, 1 / 30)
        e.vel[0] = 4.0                       # keep pushing
    assert e.pos[0] < 5                      # never inside the wall
    assert round(e.pos[0]) == 4              # parked against it


def test_jump_clears_low_ledge():
    w = World(floor_h=None)
    make_ground(w)
    w.gravity = 22.0
    e = w.spawn(Entity(VoxModel.box(1, 1, 1, "red"), pos=(2, 2, 1), gravity=True))
    e.vel[2] = 10.0                          # v^2/2g ~= 2.3 cells of rise
    peaked = 1.0
    for _ in range(60):
        step(w, 1 / 30)
        peaked = max(peaked, e.pos[2])
    assert peaked > 2.0
    assert e.pos[2] == 1.0                   # back down


def test_carve_removes_and_counts():
    w = World()
    w.fill(0, 0, 3, 3, 1, 4, "blue")         # 3x3x3 building = 27 voxels
    removed = w.carve(1, 1, 2, radius=1)     # 3x3x3 cube around center
    assert len(removed) == 27
    assert all(len(pos) == 3 and len(vox) == 2 for pos, vox in removed)
    assert not w.terrain


def test_ttl_reaps_and_debris_flies():
    from isovox import Engine, Game
    from isovox import fx
    from isovox.adapters.headless import FixedClock, NullRenderer, ScriptedInput

    class G(Game):
        size = (40, 16)
        def setup(self):
            self.world.fill(0, 0, 2, 2, 1, 3, "blue")
            rubble = self.world.carve(0, 0, 1, radius=1)
            fx.debris(self.world, rubble, count=6, ttl=0.2)

    g = G()
    eng = Engine(g, NullRenderer(), ScriptedInput(), clock=FixedClock())
    g.setup()
    n0 = len(g.world.by_tag("fx"))
    assert n0 > 0
    for _ in range(30):                      # 1s at fixed 1/30 dt
        eng.frame()
    assert len(g.world.by_tag("fx")) == 0    # all ttl-reaped


def test_entity_overlap_pairs_reported():
    w = World()
    a = w.spawn(Entity(VoxModel.box(2, 2, 2, "red"), pos=(0, 0, 0)))
    b = w.spawn(Entity(VoxModel.box(2, 2, 2, "blue"), pos=(1, 1, 1)))
    c = w.spawn(Entity(VoxModel.box(1, 1, 1, "mint"), pos=(8, 8, 0)))
    hits = step(w, 1 / 30)
    assert (a, b) in hits or (b, a) in hits
    assert all(c not in pair for pair in hits)


def test_reap_removes_dead():
    w = World()
    e = w.spawn(Entity(VoxModel.box(1, 1, 1, "red")))
    e.alive = False
    w.reap()
    assert w.entities == []
