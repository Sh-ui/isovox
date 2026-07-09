# Making games with isovox

Everything you need to build a game, in the order you'll need it. The two
examples (`examples/hopper.py`, `examples/rampage.py`) are the reference
implementations of everything below -- read them side by side with this.

## 1. The Game skeleton

```python
from isovox import Game, run

class MyGame(Game):
    fps = 30                 # optional
    bg = "#1F1E1D"           # optional background color
    size = None              # optional (cols, rows); None = fill the terminal

    def setup(self):
        """Called once. Build the world, spawn entities, aim the camera."""

    def update(self, dt, events):
        """Called every frame. dt = seconds elapsed. events = list of Key."""

    def on_collide(self, a, b):
        """Called when two solid entities overlap (after physics)."""

    def draw_hud(self, buf):
        """Called after the world is drawn. Write text on top."""

if __name__ == "__main__":
    run(MyGame())
```

`self.world` is a `World`, `self.camera` a `Camera`. Set `self.over = True`
to end the game.

## 2. The world: coordinates

- `u` = down-right on screen, `v` = down-left, `h` = up.
- Terrain lives on integer cells; entities have float positions.
- The screen shows roughly `(terminal_width / 4)` cells across a diagonal,
  so a playfield ~20-30 cells wide fills a normal terminal nicely.

## 3. Terrain

```python
self.world.set(u, v, h, "green", ".")        # one voxel (color, glyph)
self.world.fill(0, 0, 10, 10, 0, 1, "slate") # box, half-open ranges
self.world.stamp(model, u, v, h)             # bake a VoxModel in
self.world.clear(u, v, h)                    # remove one voxel
self.world.carve(u, v, h, radius=2)          # blast a cube, returns count
self.world.is_solid(u, v, h)                 # query
```

Terrain is a plain dict of voxels -- **everything is destructible** and there
is no map size; build sparse, build anywhere.

Ground rule of thumb: paint your floor at `h=0` and put things on top at
`h=1`. Set `world.floor_h = None` if falling off the map should be possible
(the default `0` is an invisible infinite floor).

Texture tip: a floor where every cell has a glyph looks noisy. Stipple it --
glyph `"."` on ~30% of cells, `" "` on the rest (the color still shows on the
walls at edges). See hopper's lawn.

## 4. Models (.ivx sprites)

Ship them as text files:

```
; car.ivx -- keys are letters you choose
@b red =        ; key 'b' -> color red, drawn as '='
@g #B8B2A9 -    ; hex colors work anywhere color names do
#0              ; layer h=0, bottom
bb
bb
#1              ; next layer up
.g              ; '.' = empty
g.
```

Rows advance `u`, characters advance `v`, layers advance `h`.

```python
from isovox import VoxModel
car = VoxModel.load("assets/car.ivx")
tower = VoxModel.box(3, 3, 8, "purple", "#")   # or generate in code
```

## 5. Entities

```python
from isovox import Entity
e = self.world.spawn(Entity(model, pos=(u, v, h),
                            gravity=True,   # falls until supported
                            solid=True,     # blocks / gets blocked / overlaps
                            tag="enemy"))   # your label, filter with world.by_tag
```

- Move by setting `e.vel = [du_per_sec, dv_per_sec, dh_per_sec]` or by
  assigning `e.pos` directly (teleport-style hops -- check
  `world.is_solid` first).
- Jump: `e.vel[2] = 8.0` while `e.on_ground`. Gravity is 22 cells/s^2;
  peak rise is `v*v / 44` cells, so 8.0 clears a 1-high ledge.
- Despawn: `e.alive = False` (removed at end of frame).
- Solid entities are blocked by **terrain** automatically; entity-vs-entity
  overlaps don't block, they call your `on_collide(a, b)` -- decide there
  what a hit means (crossy: death; smashy: bounce; kaiju: squash).

## 6. Input

`events` in `update()` is a list of `Key` objects. `key.name` is `'up'`,
`'down'`, `'left'`, `'right'`, `'enter'`, `'esc'`, `'tab'`, `'backspace'`,
or a single character like `'a'` or `' '`.

Terminals send key *repeats*, not key-up events. Two idioms:

- **Hop games** (crossy): each event = one discrete move. Just handle it.
- **Drive/walk games** (smashy, kaiju): zero velocity at the top of
  `update`, set it again on every arrow event -- holding a key streams
  repeats, so motion continues; release stops it. See rampage.

`q` and Ctrl-C always quit (the engine handles it).

## 7. Camera

```python
self.camera.follow(self.player)        # track an entity every frame
self.camera.center = (u, v, h)         # or place it by hand
```

## 8. HUD

```python
def draw_hud(self, buf):
    buf.text(0, 2, f" score: {self.score} ", "yellow")
    buf.text(buf.height - 1, 2, " arrows move - q quits ", "slate")
```

## 9. Colors

Named palette (`red`, `blue`, `mint`, `slate`, ... see `isovox/palette.py`)
or any `#rrggbb`. Shade a color toward the background for depth:

```python
from isovox.palette import lerp, UMBRA
dark_green = lerp("green", UMBRA, 0.7)
```

Faces shade automatically: top bright, left wall mid, right wall dark, and
exposed edges get a cream glint. You pick one color per voxel; the renderer
does the rest.

## 10. See it without playing it

While developing (especially if you are an AI agent -- see AGENTS.md):

```sh
python3 -m isovox.snapshot mygame --frames 60 --keys up,.,.,left
python3 -m isovox.snapshot mygame --ansi         # with color
python3 -m isovox.snapshot mygame --png f.png    # real pixels (pip install pillow)
```

`--keys` feeds one entry per frame; `.` means no key that frame. Or drive it
from Python with `SnapshotRenderer` / `ScriptedInput` / `FixedClock` from
`isovox.adapters.headless` -- that's also exactly how the tests work.

## 11. Recipes for the three archetypes

- **Crossy-road** (`hopper.py`): lanes indexed by `u`; cars are entities with
  constant `vel[1]` that wrap at the edges; player hops by setting `pos`;
  `on_collide` = death; score = furthest lane reached.
- **Smashy-road**: same bones as hopper, but the *player* has velocity
  (rampage-style input), cops are entities that steer toward you each frame
  (`vel` toward player), and buildings are stamped terrain you must drive
  around.
- **Kaiju** (`rampage.py`): city = `VoxModel.box` towers stamped into
  terrain; smashing = `world.carve` in front of the player; score = voxels
  removed.
