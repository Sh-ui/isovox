"""Sprite generator: rig density, face materials, .ivx round-trips, assets."""

import os
import random

import pytest

from isovox import sprites
from isovox.model import VoxModel
from isovox.palette import resolve

ASSETS = os.path.join(os.path.dirname(__file__), "..", "isovox", "assets")


def faces_of(vox):
    return vox[2] if len(vox) > 2 else (None, None, None)


# ------------------------------------------------------------- primitives

def test_vox_plain_stays_two_tuple():
    assert sprites.vox("red", "#") == ("#", resolve("red"))


def test_vox_with_faces():
    v = sprites.vox("red", "#", left="blue", right=("o", "yellow"))
    assert v[0] == "#" and v[1] == resolve("red")
    top, left, right = v[2]
    assert top is None
    assert left == ("#", resolve("blue"))        # inherits base glyph
    assert right == ("o", resolve("yellow"))     # explicit glyph


def test_box_solid_and_textured():
    m = sprites.box(2, 3, 4, "blue", top="cream")
    assert m.size == (2, 3, 4)
    assert len(m.voxels) == 24
    assert all(faces_of(v)[0] == ("#", resolve("cream"))
               for v in m.voxels.values())


def test_assemble_overlays_later_parts_win():
    a = sprites.box(2, 2, 1, "red")
    b = sprites.box(1, 1, 1, "blue")
    m = sprites.assemble((a, 0, 0, 0), (b, 1, 1, 0), (b, 0, 0, 5))
    assert m.voxels[(1, 1, 0)] == ("#", resolve("blue"))
    assert m.voxels[(0, 0, 0)] == ("#", resolve("red"))
    assert m.size == (2, 2, 6)


# ------------------------------------------------------------------ tower

def test_tower_steps_taper_the_footprint():
    m = sprites.tower(5, 5, 6, "blue", step=2)
    per_layer = [len([1 for (u, v, h) in m.voxels if h == hh])
                 for hh in range(6)]
    # inset grows by one each 2 layers, capped at (5-1)//2 = 2
    assert per_layer == [25, 25, 9, 9, 1, 1]
    m2 = sprites.tower(5, 5, 3, "blue", step=0)
    assert len([1 for (u, v, h) in m2.voxels if h == 2]) == 25  # no taper


def test_tower_windows_and_roof():
    rng = random.Random(7)
    m = sprites.tower(4, 4, 6, "slate", step=3, roof="grey",
                      window="#16324A", rng=rng)
    panes = [v for v in m.voxels.values()
             if faces_of(v)[1] is not None and faces_of(v)[1][0] == "="]
    assert panes, "windowed walls expected"
    # every exposed ledge/crown voxel got the roof top face
    for (u, v, h), vox in m.voxels.items():
        if (u, v, h + 1) not in m.voxels:
            assert faces_of(vox)[0] == ("#", resolve("grey"))


# ------------------------------------------------------------------- rigs

@pytest.mark.parametrize("rig,size,min_voxels", [
    (sprites.humanoid, (2, 2, 4), 14),
    (sprites.vehicle, (1, 4, 3), 9),
    (sprites.tree, (3, 3, 7), 15),
    (sprites.kaiju, (3, 3, 7), 30),
])
def test_rigs_are_dense_enough_to_read_as_cubes(rig, size, min_voxels):
    m = rig()
    assert m.size == size
    assert len(m.voxels) >= min_voxels


def test_vehicle_has_glazed_cabin_and_headlight():
    m = sprites.vehicle(body="red", glass="#9FD4E8", length=4)
    cabin = faces_of(m.voxels[(0, 1, 2)])
    assert cabin[1] == ("#", "#9FD4E8") and cabin[2] == ("#", "#9FD4E8")
    assert faces_of(m.voxels[(0, 3, 1)])[1] == ("o", "#F5E9C8")


def test_tree_canopy_clears_head_height():
    m = sprites.tree(height=4)
    trunk_only = {(u, v) for (u, v, h) in m.voxels if h < 4}
    assert trunk_only == {(1, 1)}   # only the trunk blocks below the canopy


def test_rotation_preserves_count_and_face_data():
    m = sprites.kaiju()
    r = m.rotated(1)
    assert len(r.voxels) == len(m.voxels)
    assert sorted(m.voxels.values(), key=repr) == \
        sorted(r.voxels.values(), key=repr)     # values ride along unchanged
    assert set(m.rotated(2).rotated(2).voxels) == set(m.voxels)


# --------------------------------------------------------- .ivx round-trip

@pytest.mark.parametrize("rig", [sprites.humanoid, sprites.vehicle,
                                 sprites.tree, sprites.kaiju])
def test_dumps_parse_roundtrip(rig):
    m = rig()
    assert VoxModel.parse(m.dumps("roundtrip")).voxels == m.voxels


def test_dumps_roundtrip_with_tower():
    m = sprites.tower(4, 4, 7, "teal", step=2, roof="grey",
                      window="#16324A", rng=random.Random(1))
    assert VoxModel.parse(m.dumps()).voxels == m.voxels


@pytest.mark.parametrize("name,rig", [
    ("guy.ivx", sprites.humanoid),
    ("car.ivx", sprites.vehicle),
    ("tree.ivx", sprites.tree),
    ("kaiju.ivx", sprites.kaiju),
])
def test_shipped_assets_match_generator_defaults(name, rig):
    """The assets ARE dumps of the default rigs; regenerate, don't hand-edit."""
    shipped = VoxModel.load(os.path.join(ASSETS, name))
    assert shipped.voxels == rig().voxels
