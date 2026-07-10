# isovox

A tiny isometric ASCII voxel game engine that runs **live in your terminal**.
Zero dependencies. Pure Python. Hexagonal to the bone.

```
                    ##  <- a building you can smash
                  ######
                  ######            oo  <- a little guy you can hop
                  ######            @@
      - - - - - - - - - - - - - -   <- a road with cars that flatten him
```

Born from a one-off generative wallpaper renderer (isometric circuit board in
ASCII) that turned out to be a perfectly good game renderer once it learned to
redraw 30 times a second.

## What it does

- **Isometric voxel worlds** on a diamond lattice: 2:1 character shear,
  painter's-algorithm occlusion, three-face shading (lit top, mid left wall,
  dark right wall) -- the classic look, in truecolor ANSI.
- **Playable in the terminal**: raw keyboard input, diff-based rendering
  (only changed cells are rewritten), comfortably 30+ fps.
- **Arcade physics**: gravity, jumps, terrain blocking, entity overlap events.
  Enough for a crossy-road, a smashy-road, or a kaiju stomping buildings --
  the three games it was designed around.
- **Procedural sprites** (`isovox.sprites`): dense humanoid / vehicle / tree /
  kaiju rigs and stepped, windowed towers that actually read as chunky 3D
  cubes, with per-face texturing (glass cabins, lit windows, bark, scales).
- **Fully destructible terrain** by construction (it's a dict of voxels).
- **Headless by design**: every game can run without a TTY, print frames as
  plain text, or export PNG stills. Tests and AI coding agents drive the
  exact same engine the player plays.

## Install

Needs Python 3.9+. No dependencies for playing in the terminal.

```sh
git clone <this repo> && cd isovox
python3 -m examples.hopper      # crossy-road: arrows hop, q quits
python3 -m examples.rampage     # kaiju: arrows walk, space smashes
```

(Or `cd examples && python3 hopper.py` -- both work from anywhere.)

Optional: `pip install pillow` if you want PNG export.

## Write a game in 20 lines

```python
from isovox import Game, Entity, run
from isovox.sprites import humanoid, tower

class Sandbox(Game):
    def setup(self):
        for u in range(12):
            for v in range(12):
                self.world.set(u, v, 0, "#3A5F3A", ".")
        self.world.stamp(tower(4, 4, 6, "blue", step=3, window="#16324A"), 5, 5, 1)
        self.player = self.world.spawn(Entity(
            humanoid(), pos=(1, 1, 1), gravity=True))
        self.camera.follow(self.player)

    def update(self, dt, events):
        for e in events:
            du, dv = {"up": (-1, 0), "down": (1, 0),
                      "left": (0, 1), "right": (0, -1)}.get(e.name, (0, 0))
            self.player.vel[0], self.player.vel[1] = du * 6.0, dv * 6.0

run(Sandbox())
```

Full guide: **[docs/making-games.md](docs/making-games.md)**.
Working with an AI agent: **[AGENTS.md](AGENTS.md)**.

## See a frame without a terminal

The snapshot CLI runs any game headless for N frames (optionally feeding
scripted keys) and prints the frame -- this is how an AI agent, a test, or a
CI job "looks at" the game:

```sh
python3 -m isovox.snapshot examples.hopper --frames 60 --keys up,.,.,up
python3 -m isovox.snapshot examples.rampage --ansi          # truecolor
python3 -m isovox.snapshot examples.rampage --png frame.png # needs pillow
```

## Architecture (hexagonal)

The core is pure -- no I/O, no ANSI, no fonts, no clocks. Adapters plug into
three small ports.

```
            +---------------------------- core (pure) ---+
            |  world.py    voxel terrain + entities      |
            |  physics.py  gravity / blocking / overlaps |
            |  raster.py   world -> CharBuffer           |
            |  project.py  iso math + camera             |
            |  model.py    .ivx voxel sprites            |
            |  sprites.py  procedural rigs + primitives  |
            |  engine.py   the game loop                 |
            +----+-----------------+----------------+----+
                 |                 |                |
             Renderer port     Input port       Clock port
                 |                 |                |
       +---------+-------+   +-----+------+   +----+------+
       | terminal (ANSI) |   | terminal   |   | SysClock  |
       | headless (text) |   | scripted   |   | FixedClock|
       | png (Pillow)    |   +------------+   +-----------+
       +-----------------+
```

Want SDL, a web canvas, or sixel graphics? Write one class satisfying the
`Renderer` protocol in `isovox/ports.py`. The core never changes.

## Coordinates, 10 seconds

- `u` runs down-right on screen, `v` runs down-left, `h` is up.
- Default (`wide`) metrics: one world cell = a 4x2-char top face,
  `col = 4*(u-v)`, `row = u+v - 2*h`, 2 wall rows per voxel of height --
  true 2:1 isometric on ~1:2 terminal cells. (`square` metrics are the
  original wallpaper's 2x2 geometry, for near-square cells / PNG export.)
- Depth sort is just `u+v` ascending. That's the whole trick.

## Sprites that read as cubes

One lonely voxel is a 4x2 blob; the iso illusion comes from *stacked,
adjacent* voxels -- wall faces to shade, edges to glint, steps in the
silhouette. `isovox.sprites` generates geometry at that density: `humanoid()`
(2x2x4: legs/torso/head), `vehicle()` (glazed cabin + headlight), `tree()`
(walk-under canopy), `kaiju()` (3x3x7 with claws and eyes), and parametric
`tower(...)` buildings with stepped shoulders and lit windows. Every face
(top / left wall / right wall) can carry its own color and glyph. The shipped
`.ivx` assets are `dumps()` of these rigs; see
[docs/making-games.md](docs/making-games.md#4b-procedural-sprites-isovoxsprites).

## Why not <existing thing>?

python-tcod / asciimatics / blessed are fine libraries, but they solve
terminal plumbing, not isometric voxel worlds -- and the plumbing this needs
(one raw-mode input, one diff renderer) is ~150 lines with zero deps. The
interesting part is the raster + world model, which nothing on the shelf
provided. The ports mean any of those libraries can still become an adapter.

## License

MIT.
