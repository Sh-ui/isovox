"""Engine + raster integration, fully headless -- the way an AI agent runs it."""

from isovox import Engine, Entity, Game, VoxModel
from isovox.adapters.headless import (FixedClock, NullRenderer, ScriptedInput,
                                      SnapshotRenderer)
from isovox.buffer import CharBuffer
from isovox.project import Camera
from isovox.raster import raster
from isovox.world import World


class Cube(Game):
    size = (40, 20)

    def setup(self):
        self.world.fill(0, 0, 2, 2, 0, 2, "red", "#")
        self.camera.center = (1, 1, 1)
        self.moved = []

    def update(self, dt, events):
        self.moved += [e.name for e in events]

    def draw_hud(self, buf):
        buf.text(0, 0, "HUD")


def test_raster_draws_cube_top_and_walls():
    w = World()
    w.fill(0, 0, 1, 1, 0, 2, "red", "#")     # single column, 2 tall
    cam = Camera(center=(0, 0, 1))
    buf = CharBuffer(20, 12)
    raster(w, cam, buf)
    txt = buf.to_text()
    assert "#" in txt
    colors = {c for row in buf.cells for _, c in row}
    assert len(colors) >= 3                   # bg + top + two wall shades


def test_entity_renders():
    w = World()
    w.spawn(Entity(VoxModel.box(1, 1, 1, "mint", "@"), pos=(0, 0, 0)))
    buf = CharBuffer(20, 12)
    raster(w, Camera(), buf)
    assert "@" in buf.to_text()


def test_walls_survive_an_overhang_in_front():
    """A floating voxel diagonally in front must not erase walls behind it.

    The old rule skipped every wall below the front column's MAX height, so
    anything behind a tree canopy or a legged rig lost its lower walls. The
    per-height occupancy rule only skips walls the front column truly covers.
    """
    w = World(floor_h=None)
    w.fill(0, 0, 1, 1, 0, 2, "red", "#")      # column at (0,0), h=0..1
    w.set(1, 1, 4, "blue", "*")               # floater in front, gap below
    buf = CharBuffer(24, 16)
    raster(w, Camera(center=(0, 0, 0)), buf)  # (0,0,0) -> col 12, row 8
    # wall rows of voxel h=0 sit at rows 8..9, cols 12..15 (WIDE metrics)
    assert buf.cells[9][12][0] == "#"
    assert buf.cells[7][12][0] == "#"         # h=1 wall too
    assert "*" in buf.to_text()               # the floater itself drew


def test_stipple_ground_keeps_interior_walls_hidden():
    w = World(floor_h=None)
    for u in range(3):
        for v in range(3):
            w.set(u, v, 0, "green", ".")
    buf = CharBuffer(32, 18)
    raster(w, Camera(center=(1, 1, 0)), buf)  # (0,0) col 16, ground row 7
    # interior lawn cell (0,0): front cell (1,1) exists -> wall skipped
    assert buf.cells[8][16][0] == " "
    # front-edge cell (2,2) has nothing in front -> wall drawn as ':'
    assert ":" in buf.to_text()


def test_face_overrides_paint_top_and_walls():
    from isovox.palette import shades
    m = VoxModel({(0, 0, 0): ("#", "#888888",
                              (("T", "#888888"),
                               ("L", "#1987E8"), ("R", "#ED4B40")))})
    w = World(floor_h=None)
    w.spawn(Entity(m, pos=(0, 0, 0)))
    buf = CharBuffer(20, 12)
    raster(w, Camera(), buf)
    txt = buf.to_text()
    assert "T" in txt and "L" in txt and "R" in txt and "#" not in txt
    lcell = next(c for row in buf.cells for c in row if c[0] == "L")
    assert lcell[1] == shades("#1987E8", buf.bg)[1]   # face color, wall-shaded


def test_engine_runs_headless_and_snapshots():
    game = Cube()
    snap = SnapshotRenderer()
    eng = Engine(game, snap, ScriptedInput(["up", ".", "left", "quit"]),
                 clock=FixedClock())
    eng.run()
    assert game.over
    assert game.moved == ["up", "left"]
    assert snap.frames == 4
    assert "HUD" in snap.text()
    assert "#" in snap.text()


def test_null_renderer_counts():
    game = Cube()
    r = NullRenderer()
    eng = Engine(game, r, ScriptedInput(["quit"]), clock=FixedClock())
    eng.run()
    assert r.frames == 1


def test_snapshot_cli(capsys):
    from isovox.snapshot import main
    main(["examples.hopper", "--frames", "10", "--size", "60x20"])
    out = capsys.readouterr().out
    assert len(out.splitlines()) == 20
