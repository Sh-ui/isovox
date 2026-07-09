# Working on isovox games with an AI agent

This repo is designed so an AI coding agent can build and *see* games without
a human relaying screenshots. If you are that agent, this file is for you.

## Your eyes: the snapshot CLI

You cannot watch the live terminal, but you never need to. Any game runs
headless:

```sh
python3 -m isovox.snapshot examples.hopper --frames 60
python3 -m isovox.snapshot examples.hopper --frames 60 --keys up,.,.,up,left
python3 -m isovox.snapshot examples.hopper --png /tmp/frame.png   # then view the image
```

- Plain output = the frame as text. Read it to check layout, HUD, positions.
- `--keys` simulates the player (one entry per frame, `.` = no key). Use it
  to verify movement, collisions, scoring -- like a tiny replay.
- `--png` gives you real colors if you can view images.

Iterate like this: edit game -> snapshot -> read frame -> repeat. Only ask
the human to playtest when the frames already look right; their time is the
scarce resource.

## Tests

```sh
python3 -m pytest -q        # (pip install pytest, or use a venv)
```

Run them after touching anything in `isovox/`. Games in `examples/` or your
own module don't need engine tests, but game *logic* (scoring, spawning,
death) is easy to test with the headless adapters -- see
`tests/test_engine_headless.py` for the pattern.

## Rules of the architecture

1. **The core stays pure.** Nothing under `isovox/` except `adapters/` may
   import ANSI codes, termios, PIL, time-sleeps, or anything platform-ish.
   If you need a new capability (sound? mouse? sixels?), add a port in
   `ports.py` and an adapter in `adapters/` -- never a special case in core.
2. **Games live outside the engine.** A game is a `Game` subclass plus
   `.ivx` assets. Don't patch engine files to make one game work; if the
   engine genuinely lacks something, add it as a general feature with a test.
3. **Zero mandatory dependencies.** The playable path must keep working on a
   bare Python 3.10+ install. Pillow stays optional.
4. **Small files, small functions.** The whole engine is ~1k lines; keep it
   readable in one sitting.

## Map of the code

| File | What it is |
|------|-----------|
| `isovox/world.py` | terrain dict + entities (the game state) |
| `isovox/physics.py` | gravity, blocking, overlap pairs |
| `isovox/raster.py` | world -> CharBuffer (the look) |
| `isovox/project.py` | iso math + camera |
| `isovox/model.py` | .ivx sprite format |
| `isovox/engine.py` | game loop, `Game` base class |
| `isovox/ports.py` | Renderer / Input / Clock protocols |
| `isovox/adapters/` | terminal, headless, png |
| `docs/making-games.md` | the game-building guide -- read it first |

## Starting a new game

1. Read `docs/making-games.md` end to end (it's short).
2. Copy the closest example (`hopper.py` = hop games, `rampage.py` =
   walk/drive/destroy games) into a new file and reshape it.
3. Author models as `.ivx` files next to your game; load with
   `VoxModel.load`.
4. Snapshot early, snapshot often.
