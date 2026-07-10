"""Procedural voxel sprites: chunky rigs and primitives that read as 3D.

Why this module exists: hand-authored .ivx sprites drifted toward 1-3 voxel
stick figures, which starve the isometric raster -- with almost no wall face
to shade and no stepped silhouette, nothing reads as a cube. The wallpaper
renderer this engine was extracted from looked solid because its field was
DENSE: many adjacent, stacked voxels giving real occlusion, three-face
shading, and glinted edges. These builders generate geometry at that density.

Everything here is pure: parameters in, VoxModel out. Use the result
directly, bake it into terrain with world.stamp(), or write it to an asset
file with VoxModel.dumps() -- the shipped assets in isovox/assets/ are dumps
of the rig functions below with default arguments (tests pin that).

Building blocks
    vox(color, glyph, top=, left=, right=)   one voxel value, optionally
                                             textured per face
    box(du, dv, dh, color, ...)              solid cuboid of one material
    assemble((model, du, dv, dh), ...)       overlay parts into one model

Rigs (each returns a VoxModel; footprints noted because physics uses them)
    humanoid()   2 x 2 x 4   legs / torso / head, hair top, eye texture
    vehicle()    1 x L x 3   chassis / body / glazed cabin, headlight
    tree()       3 x 3 x 7   tall trunk, 3x3 leaf canopy you can walk under
    kaiju()      3 x 3 x 7   legs + tail / banded torso / claws / eyed head
    tower(...)   parametric stepped building with lit-window walls

Face specs: anywhere a face keyword is accepted, pass a color (name or hex)
to retint that face, or a (glyph, color) pair to change its texture too.
Face materials are SCREEN-space (top / camera-left / camera-right as drawn):
VoxModel.rotated() turns the geometry and the face data rides along, which
is the right cheat when there is exactly one camera angle.

Density rule of thumb: at the default WIDE metrics one voxel is a 4x2-char
top plus 2 wall rows, so anything the player should read as an object wants
a footprint of at least 2x2 or a long axis of 4, and 3+ voxels of height
with at least one silhouette step (cabin, head, canopy, taper).
"""

from __future__ import annotations

import random
from typing import Optional, Tuple, Union

from .model import Face, VoxModel, Voxel
from .palette import lerp, resolve

# a face spec: None (inherit), a color, or an explicit (glyph, color)
FaceSpec = Union[None, str, Tuple[str, str]]


def _face(spec: FaceSpec, glyph: str) -> Optional[Face]:
    if spec is None:
        return None
    if isinstance(spec, str):
        return (glyph, resolve(spec))
    return (spec[0], resolve(spec[1]))


def vox(color: str, glyph: str = "#", *, top: FaceSpec = None,
        left: FaceSpec = None, right: FaceSpec = None) -> Voxel:
    """One voxel value: (glyph, color) plus optional per-face materials."""
    color = resolve(color)
    faces = (_face(top, glyph), _face(left, glyph), _face(right, glyph))
    if faces == (None, None, None):
        return (glyph, color)
    return (glyph, color, faces)


def box(du: int, dv: int, dh: int, color: str, glyph: str = "#", *,
        top: FaceSpec = None, left: FaceSpec = None,
        right: FaceSpec = None) -> VoxModel:
    """Solid cuboid, optionally face-textured. The workhorse primitive."""
    V = vox(color, glyph, top=top, left=left, right=right)
    return VoxModel({(u, v, h): V
                     for u in range(du) for v in range(dv) for h in range(dh)})


def assemble(*parts: Tuple[VoxModel, int, int, int]) -> VoxModel:
    """Overlay (model, du, dv, dh) parts into one model; later parts win."""
    voxels: dict = {}
    for model, du, dv, dh in parts:
        for (u, v, h), V in model.voxels.items():
            voxels[(u + du, v + dv, h + dh)] = V
    return VoxModel(voxels)


# ---------------------------------------------------------------- buildings

def tower(du: int, dv: int, dh: int, color: str, *, step: int = 0,
          roof: FaceSpec = None, window: Optional[str] = None,
          lit: str = "#E8C468", lit_chance: float = 0.3,
          rng: Optional[random.Random] = None, glyph: str = "#") -> VoxModel:
    """A stepped/tapered building with optional windowed walls.

    step=N insets the footprint by one cell on every side each N layers
    (ziggurat silhouette; 0 = straight box). window="#223" puts that glass
    on checkered perimeter voxels of every other floor; a `lit_chance` slice
    of them glow `lit` instead (pass rng for a deterministic skyline).
    """
    color = resolve(color)
    rng = rng or random.Random(0)
    window = resolve(window) if window else None
    voxels: dict = {}
    inset = 0
    for h in range(dh):
        if step and h and h % step == 0:
            inset = min(inset + 1, (min(du, dv) - 1) // 2)
        base: Voxel = (glyph, color)
        for u in range(inset, du - inset):
            for v in range(inset, dv - inset):
                V = base
                if (window and h % 2 == 1 and (u + v) % 2 == 0 and
                        (u in (inset, du - inset - 1) or
                         v in (inset, dv - inset - 1))):
                    pane = ("=", lit if rng.random() < lit_chance else window)
                    V = (glyph, color, (None, pane, pane))
                voxels[(u, v, h)] = V
    if roof is not None:
        rf = _face(roof, glyph)
        for (u, v, h), V in list(voxels.items()):
            if (u, v, h + 1) not in voxels:      # every exposed ledge + crown
                old = V[2] if len(V) > 2 else (None, None, None)
                voxels[(u, v, h)] = (V[0], V[1], (rf, old[1], old[2]))
    return VoxModel(voxels)


# --------------------------------------------------------------------- rigs

def humanoid(shirt: str = "mint", skin: str = "#E8C6A0",
             pants: Optional[str] = None, hair: str = "#4A3524") -> VoxModel:
    """A 2x2x4 little person: pants legs, shirt torso, head with hair + eyes.

    Base facing is +u (toward the camera); rotated(k) for other headings.
    """
    shirt = resolve(shirt)
    skin = resolve(skin)
    pants = resolve(pants) if pants else lerp(shirt, "#000000", 0.5)
    voxels: dict = {}
    for u in range(2):
        for v in range(2):
            voxels[(u, v, 0)] = ("#", pants)                 # legs
            voxels[(u, v, 1)] = ("@", shirt)                 # torso
            voxels[(u, v, 2)] = ("@", shirt)
            if (u, v) == (1, 1):   # front-corner head voxel gets the eyes
                eye = ("o", skin)
                voxels[(u, v, 3)] = ("@", skin,
                                     (("~", resolve(hair)), eye, eye))
            else:
                voxels[(u, v, 3)] = ("@", skin, (("~", resolve(hair)),
                                                 None, None))
    return VoxModel(voxels)


def vehicle(body: str = "red", glass: str = "#9FD4E8",
            trim: Optional[str] = None, length: int = 4) -> VoxModel:
    """A 1 x length x 3 car: dark chassis, body, glazed cabin, headlight.

    Long axis is v (its direction of travel in a lane); one cell deep in u so
    it stays inside a one-cell road lane. rotated(2) about-faces it (cabin
    and headlight swap ends) for opposite traffic.
    """
    body = resolve(body)
    glass = resolve(glass)
    trim = resolve(trim) if trim else lerp(body, "#000000", 0.55)
    roof = ("-", lerp(body, "#000000", 0.2))
    voxels: dict = {}
    for v in range(length):
        voxels[(0, v, 0)] = ("=", trim)                      # chassis/wheels
        voxels[(0, v, 1)] = ("=", body)                      # body
    for v in range(1, length - 1):                           # cabin, hood free
        pane = ("#", glass)
        voxels[(0, v, 2)] = ("=", body, (roof, pane, pane))
    lamp = ("o", "#F5E9C8")
    voxels[(0, length - 1, 1)] = ("=", body, (None, lamp, lamp))
    return VoxModel(voxels)


def tree(trunk: str = "coffee", leaf: str = "green",
         height: int = 4, canopy: int = 3) -> VoxModel:
    """A tall tree: 1x1 bark trunk, canopy x canopy x 2 leaf crown + tip.

    The trunk is `height` voxels; the canopy floats above it, so anything
    shorter than `height` walks UNDER the leaves and only the trunk blocks.
    Model footprint is canopy x canopy with the trunk at the center -- stamp
    at (u - canopy//2, v - canopy//2) to plant the trunk on cell (u, v).
    """
    trunk = resolve(trunk)
    leaf = resolve(leaf)
    dark = lerp(leaf, "#000000", 0.22)
    c = canopy // 2
    bark = ("|", trunk)
    voxels: dict = {}
    for h in range(height):
        voxels[(c, c, h)] = ("|", trunk, (None, bark, bark))
    for h in (height, height + 1):
        for u in range(canopy):
            for v in range(canopy):
                if (h == height + 1 and u in (0, canopy - 1)
                        and v in (0, canopy - 1)):
                    continue                                 # round the crown
                voxels[(u, v, h)] = ("&", leaf if (u + v + h) % 2 else dark)
    voxels[(c, c, height + 2)] = ("&", leaf)
    return VoxModel(voxels)


def kaiju(hide: str = "magenta", belly: Optional[str] = None,
          eye: str = "yellow", claw: str = "#F8F2E9") -> VoxModel:
    """A 3x3x7 monster rig: legs + tail, banded torso with belly plates,
    claw-textured arms, and a 2x2 eyed head with a horn.

    Base facing is +u (eyes toward the camera); rotated(k) turns it.
    """
    hide = resolve(hide)
    belly = resolve(belly) if belly else lerp(hide, "#F8F2E9", 0.35)
    dark = lerp(hide, "#000000", 0.25)
    voxels: dict = {}
    for h in (0, 1):
        voxels[(0, 1, h)] = ("%", dark)                      # tail
        voxels[(2, 0, h)] = ("%", dark)                      # legs
        voxels[(2, 2, h)] = ("%", dark)
    for h in (2, 3, 4):                                      # torso
        band = hide if h % 2 else dark
        for u in range(3):
            for v in range(3):
                if u == 0 and v in (0, 2):
                    continue                                 # taper the back
                if u == 2 and v == 1:
                    voxels[(u, v, h)] = ("%", belly)         # belly plates
                elif u == 0 and v == 1:
                    voxels[(u, v, h)] = ("%", band,
                                         (("^", dark), None, None))  # spines
                else:
                    voxels[(u, v, h)] = ("%", band)
    talon = ("w", resolve(claw))
    for v in (0, 2):                                         # clawed arms
        voxels[(2, v, 3)] = ("%", dark, (None, talon, talon))
    for h in (5, 6):                                         # head
        for u in (1, 2):
            for v in (0, 1):
                if h == 5 and u == 2:
                    look = ("o", resolve(eye))
                    voxels[(u, v, h)] = ("%", hide, (None, look, look))
                else:
                    voxels[(u, v, h)] = ("%", hide)
    voxels[(1, 2, 5)] = ("^", dark)                          # horn
    return VoxModel(voxels)
