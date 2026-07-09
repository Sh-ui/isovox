"""Headless adapters: run games with no TTY at all.

This is how tests -- and AI agents building games -- drive the engine:

    game = MyGame()
    snap = SnapshotRenderer()
    eng = Engine(game, snap, ScriptedInput(["up", "up", "left"]))
    game.setup()
    for _ in range(60):
        eng.frame()
    print(snap.text())    # "look" at the frame as plain text

See also `python -m isovox.snapshot` for the one-line CLI version.
"""

from ..buffer import CharBuffer
from ..ports import Event, Key, Quit


class NullRenderer:
    """Discards frames (pure logic tests)."""
    frames = 0

    def open(self, width: int, height: int) -> None: ...
    def draw(self, buf: CharBuffer) -> None:
        self.frames += 1
    def close(self) -> None: ...


class SnapshotRenderer:
    """Keeps the last frame so you can inspect it after stepping the engine."""

    def __init__(self):
        self.buf: CharBuffer | None = None
        self.frames = 0

    def open(self, width: int, height: int) -> None: ...

    def draw(self, buf: CharBuffer) -> None:
        self.buf = buf
        self.frames += 1

    def close(self) -> None: ...

    def text(self) -> str:
        return self.buf.to_text() if self.buf else ""

    def ansi(self) -> str:
        return self.buf.to_ansi() if self.buf else ""


class ScriptedInput:
    """Feeds one scripted key per poll; '.' means 'no key this frame'.

    ScriptedInput(["up", "up", ".", " ", "left"]) -- then silence forever.
    """

    def __init__(self, keys: list[str] | None = None):
        self.queue = list(keys or [])

    def open(self) -> None: ...

    def poll(self) -> list[Event]:
        if not self.queue:
            return []
        k = self.queue.pop(0)
        if k == ".":
            return []
        if k == "quit":
            return [Quit()]
        return [Key(k)]

    def close(self) -> None: ...


class FixedClock:
    """Constant dt, no sleeping -- deterministic and fast for tests."""

    def __init__(self, dt: float = 1 / 30):
        self.dt = dt

    def tick(self, fps: int) -> float:
        return self.dt
