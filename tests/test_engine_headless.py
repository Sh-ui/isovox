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
