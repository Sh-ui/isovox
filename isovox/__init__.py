"""isovox -- a tiny isometric ASCII voxel game engine for the terminal.

Public API. Everything a game needs:

    from isovox import Game, run, VoxModel, Entity, Key

    class My(Game):
        def setup(self): ...
        def update(self, dt, events): ...

    if __name__ == "__main__":
        run(My())
"""

from __future__ import annotations

__version__ = "0.1.0"

from .buffer import CharBuffer
from .engine import Engine, Game, run
from .model import VoxModel
from .palette import PALETTE, UMBRA, lerp
from .ports import Key, Quit
from .project import Camera
from .world import Entity, World

__all__ = [
    "Camera", "CharBuffer", "Engine", "Entity", "Game", "Key", "PALETTE",
    "Quit", "UMBRA", "VoxModel", "World", "lerp", "run", "__version__",
]
