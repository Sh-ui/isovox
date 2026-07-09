"""Engine: the game loop. Wires a Game to whatever adapters you hand it.

    class MyGame(Game):
        def setup(self): ...            # build self.world, spawn entities
        def update(self, dt, events): ...  # game logic, once per frame
        def draw_hud(self, buf): ...    # optional text overlay

    run(MyGame())                       # terminal, 30 fps

`run()` picks the terminal adapters; tests and AI agents instead construct
Engine(...) with headless adapters and step it by hand. Same core either way.
"""

from __future__ import annotations

import time

from . import physics
from .buffer import CharBuffer
from .palette import UMBRA
from .ports import Clock, Input, Key, Quit, Renderer
from .project import Camera
from .world import World


class Game:
    bg = UMBRA
    fps = 30
    size: tuple[int, int] | None = None   # (cols, rows); None = fill terminal

    def __init__(self):
        self.world = World()
        self.camera = Camera()
        self.over = False        # set True to end the game

    # override these three
    def setup(self) -> None: ...
    def update(self, dt: float, events: list) -> None: ...
    def draw_hud(self, buf: CharBuffer) -> None: ...

    # called by the engine after physics; override for hit reactions
    def on_collide(self, a, b) -> None: ...


class SysClock:
    def __init__(self):
        self._last = None

    def tick(self, fps: int) -> float:
        now = time.perf_counter()
        if self._last is None:
            self._last = now
            return 1.0 / fps
        target = self._last + 1.0 / fps
        if now < target:
            time.sleep(target - now)
            now = target
        dt = now - self._last
        self._last = now
        return min(dt, 3.0 / fps)   # clamp: no physics explosions after a stall


class Engine:
    def __init__(self, game: Game, renderer: Renderer, input_: Input,
                 clock: Clock | None = None, size: tuple[int, int] = (100, 34)):
        self.game = game
        self.renderer = renderer
        self.input = input_
        self.clock = clock or SysClock()
        w, h = game.size or size
        self.buf = CharBuffer(w, h, game.bg)

    def frame(self, dt: float | None = None) -> None:
        """One tick: input -> game.update -> physics -> raster -> draw."""
        events = self.input.poll()
        if any(isinstance(e, Quit) for e in events):
            self.game.over = True
        dt = dt if dt is not None else 1.0 / self.game.fps
        self.game.update(dt, [e for e in events if isinstance(e, Key)])
        for a, b in physics.step(self.game.world, dt):
            self.game.on_collide(a, b)
        self.game.world.reap()
        self.game.camera.update()
        from .raster import raster
        raster(self.game.world, self.game.camera, self.buf)
        self.game.draw_hud(self.buf)
        self.renderer.draw(self.buf)

    def run(self) -> None:
        self.renderer.open(self.buf.width, self.buf.height)
        self.input.open()
        try:
            self.game.setup()
            while not self.game.over:
                dt = self.clock.tick(self.game.fps)
                self.frame(dt)
        except KeyboardInterrupt:
            pass
        finally:
            self.input.close()
            self.renderer.close()


def run(game: Game) -> None:
    """Play a Game live in the current terminal."""
    from .adapters.terminal import TermInput, TermRenderer, term_size
    w, h = game.size or term_size()
    game.size = (w, h)
    Engine(game, TermRenderer(), TermInput(), size=(w, h)).run()
