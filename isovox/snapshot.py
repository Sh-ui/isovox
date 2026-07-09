"""Snapshot CLI: run any Game headless for N frames, print (or save) a frame.

This is the AI-agent eyeball. No TTY needed:

    python -m isovox.snapshot examples.hopper --frames 90 --keys up,up,.,left
    python -m isovox.snapshot examples.hopper --ansi          # colored, for humans
    python -m isovox.snapshot examples.hopper --png /tmp/f.png

The module must expose a Game subclass; the first one found is used, or name
it explicitly with module:ClassName.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import sys

from .adapters.headless import FixedClock, ScriptedInput, SnapshotRenderer
from .engine import Engine, Game


def load_game(spec: str) -> Game:
    mod_name, _, cls_name = spec.partition(":")
    mod = importlib.import_module(mod_name)
    if cls_name:
        return getattr(mod, cls_name)()
    for _, obj in inspect.getmembers(mod, inspect.isclass):
        if issubclass(obj, Game) and obj is not Game and obj.__module__ == mod.__name__:
            return obj()
    raise SystemExit(f"no Game subclass found in {mod_name}")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(prog="python -m isovox.snapshot", description=__doc__)
    ap.add_argument("game", help="module path of the game, e.g. examples.hopper")
    ap.add_argument("--frames", type=int, default=60)
    ap.add_argument("--keys", default="", help="comma list, one per frame; '.'=none")
    ap.add_argument("--size", default="100x34", help="COLSxROWS")
    ap.add_argument("--ansi", action="store_true", help="print with truecolor")
    ap.add_argument("--png", default="", help="also save the frame as PNG (needs Pillow)")
    args = ap.parse_args(argv)

    game = load_game(args.game)
    w, h = (int(x) for x in args.size.lower().split("x"))
    game.size = (w, h)
    keys = [k for k in args.keys.split(",") if k] if args.keys else []
    snap = SnapshotRenderer()
    eng = Engine(game, snap, ScriptedInput(keys), clock=FixedClock(), size=(w, h))
    game.setup()
    for _ in range(args.frames):
        if game.over:
            break
        eng.frame()
    if args.png:
        from .adapters.png import save_png
        print(save_png(snap.buf, args.png), file=sys.stderr)
    print(snap.ansi() if args.ansi else snap.text())


if __name__ == "__main__":
    main()
