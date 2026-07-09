"""Ports: the protocols adapters must satisfy, and the event vocabulary.

The core (world, physics, raster, engine) depends only on these shapes.
Adapters (terminal, headless, PNG, or anything you write) plug in here.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from .buffer import CharBuffer


# -- events ---------------------------------------------------------------
@dataclass(frozen=True)
class Key:
    """A key press. `name` is a single character ('a', ' ') or one of:
    'up', 'down', 'left', 'right', 'esc', 'enter', 'tab', 'backspace'."""
    name: str


@dataclass(frozen=True)
class Quit:
    """The player or platform asked to stop (Ctrl-C, q, window close...)."""


Event = Key | Quit


# -- ports ----------------------------------------------------------------
@runtime_checkable
class Renderer(Protocol):
    def open(self, width: int, height: int) -> None: ...
    def draw(self, buf: CharBuffer) -> None: ...
    def close(self) -> None: ...


@runtime_checkable
class Input(Protocol):
    def open(self) -> None: ...
    def poll(self) -> list[Event]: ...
    def close(self) -> None: ...


@runtime_checkable
class Clock(Protocol):
    def tick(self, fps: int) -> float:
        """Sleep as needed to hold fps; return elapsed seconds since last tick."""
        ...
