# devlog: how a wallpaper became a game engine

*A running journal, kept while building isovox. Lightly edited, honesty intact.*

---

## Entry 1 -- the heist

Today's job: steal from myself.

A while back I wrote a one-off script that renders a fake isometric circuit
board in ASCII and saves it as a wallpaper. 160 lines, runs once, exits. It
has no idea it's about to become a game engine.

Reading it back, the whole magic trick is four lines:

```
col = 2 * (u - v)
row = u + v - h
sort everything by (u + v)
draw back to front
```

That's it. That's isometric rendering. The 2:1 shear makes character cells
(which are tall) come out looking like proper diamond tiles, and the sort
means anything nearer the camera simply stamps over whatever was behind it.
No z-buffer, no math with the letter theta in it. The wallpaper also shades
each voxel three ways -- bright top, mid left wall, dark right wall -- which
is 100% of why it reads as 3D instead of as soup.

The plan: rip the projection and shading out, wrap a world model and a game
loop around them, and keep the whole thing so small that a person (or a
patient younger sibling armed with an AI) can read the entire engine before
lunch.

Rules I'm setting for myself before I write a line:

1. **Zero dependencies.** It has to run on a Mac Mini with nothing but
   Python on it. Pillow allowed only as an optional extra for PNG export.
2. **Hexagonal or bust.** Pure core, three ports (draw, keys, time),
   adapters on the outside. When someone inevitably asks "can it render to
   a web page," the answer must be "write one adapter class" and not
   nervous laughter.
3. **The engine must be playable by something with no eyes.** An AI agent
   is going to co-develop games in this thing. It needs a way to run the
   game without a terminal and read the frame like a book.

Rule 3 is secretly the interesting one.

## Entry 2 -- did anyone already build this?

Due diligence hour. Surely someone has made "isometric voxel games in the
terminal" already?

Sort of, and no. python-tcod is a beautiful roguelike library that wants to
own your whole screen model and drags a compiled dependency along.
asciimatics does effects and TUIs. blessed does capable terminal plumbing.
None of them knows what a voxel is, and the plumbing I actually need -- one
raw-mode keyboard reader, one diff renderer -- is about 150 lines of stdlib.
The interesting 70% (world model, physics, iso raster) doesn't exist on the
shelf in any form I can use.

So: build the interesting part, keep the plumbing behind ports so any of
those libraries could still be swapped in later by someone who disagrees
with me. This is the correct amount of wheel reinvention. Noted in the
README so future archaeologists know it was a decision and not ignorance.

## Entry 3 -- the core goes in clean

Good run. Palette, buffer, projection, the .ivx sprite format (voxel models
as literal text files with layers -- a five-year-old or a language model can
author these, which is the point), world-as-a-dict-of-voxels.

The dict thing deserves a sentence. Terrain is `{(u, v, h): voxel}`. That's
the entire map format. No chunks, no arrays, no bounds. It means the kaiju
game gets destructible buildings *for free* -- smashing a building is
`del`. Sometimes the laziest data structure is also the best one.

## Entry 4 -- in which I draw half a cube

First raster bug, and it's a classic: my voxel tops were 2 characters wide
and **1** tall. The wallpaper uses 2x2 blocks per cell -- that's load-bearing!
The 2:1 aspect of the block is what cancels the 2:1 aspect of a character
cell. With 2x1 tops everything came out looking like it had been stepped on.

Fixed, and then immediately hit the subtler cousin: I was drawing walls
first, then tops, which meant a floating voxel's wall got painted over by
the surface *underneath* it in the same column. Swapped to tops-then-walls
and the layering sorted itself out. Painter's algorithm giveth, painter's
algorithm demands you think about order within the column too.

## Entry 5 -- the flicker, or: round() is not a physics engine

Best bug of the project so far.

Gravity worked. Landing worked. But an entity standing on the ground would
report `on_ground = True` roughly one frame in six. Hop inputs got eaten
five times out of six. Infuriating in exactly the way that makes you sure
it's your own fault.

It was. I was `round()`ing heights for collision. An entity resting at
h=1.0 gets nudged down by gravity to h=0.976, which *rounds back to 1*, so
no collision, so it keeps sinking -- for six frames -- until it crosses
0.5, finally collides, and snaps back up. Sink, snap, sink, snap, forever.
A tiny invisible pogo stick.

The fix is asymmetry: `floor()` for height, so the instant you dip below
your resting integer you're colliding, and `ceil()` to snap back up when
you land. Standing is now stable every single frame. Wrote a test whose
entire job is to stand still for thirty frames and assert nothing flickers.
It is my favorite test.

## Entry 6 -- the test suite argues with Newton, loses

One red test: "jump clears a low ledge." My little cube jumped with
velocity 6 and peaked at 1.72 cells; test wanted > 2.0.

Suspicion fell on the physics for about a minute before I did the actual
math: peak height is v²/2g = 36/44 = 0.82 cells of rise. The physics was
*exactly right*; my test had made up a number. Bumped the jump to 8 (rise
1.45) and moved on, slightly embarrassed for having doubted the equations.

Lesson re-learned: when a test fails, check who's wrong before you check
what's wrong.

## Entry 7 -- the demos, and the noise problem

Two demo games, one per archetype I care about:

- **hopper** -- crossy-road. Lanes, cars, trees, hop-with-an-arc, death by
  sedan, best-run scoring.
- **rampage** -- kaiju. A procedurally-scattered city, a 2x2x4 monster with
  one yellow eye, and a smash key that carves 3x3x3 holes in architecture.

First PNG snapshot of hopper was... a lot. Every grass cell had a dot,
every road cell a dash, sixty lanes of cars -- visual static. The wallpaper
had already solved this and I'd ignored its advice: it stipples. Dots on
~30% of ground cells, blank on the rest, and suddenly the eye finds the
player instantly. Also banded alternate lanes a shade darker. Rampage
needed no such rescue; a city of shaded towers with a magenta kaiju in it
apparently just looks correct on the first try. Some scenes are born lucky.

## Entry 8 -- proving it's actually playable (without playing it)

The part I can't vibe-check by looking at pictures: the real terminal path.
So I forked a pty, ran hopper inside it like a genuine terminal, and had
the test send an actual arrow-key escape sequence and then `q`.

Result: enters the alt screen, hides the cursor, takes the input, quits
clean, puts the terminal back exactly as it found it. Exit code 0. And the
whole session -- dozens of frames -- emitted 37KB, which is the diff
renderer earning its keep (naive full-screen redraws would be megabytes).

Then the benchmark: the rampage city is ~2,000 terrain voxels, and the
engine pushes **227 fps** headless at 120x40. Target was 30. In *Python*.
It turns out when your entire graphics pipeline is dictionary lookups and
string concatenation, computers from this century barely notice.

## Entry 9 -- closing thoughts

Final shape: ~1,000 lines of engine, zero dependencies, 20 green tests, two
playable games, and a snapshot CLI that lets a blindfolded AI agent
develop a game by reading frames as text -- `--keys up,.,.,left` is a
replay system that fits in a flag.

The thing I'm happiest about isn't a feature, it's a property: every piece
is boring. The projection is two multiplications. The physics is three
axis checks. The renderer is a dict diff. Nothing in here requires
cleverness to modify, which is the whole gift when the next person to open
the hood is your sister and a robot.

The wallpaper never knew what it had in it.
