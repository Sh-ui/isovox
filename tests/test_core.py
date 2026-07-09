"""Core unit tests: projection, model parsing, buffer, palette."""

import pytest

from isovox.buffer import CharBuffer
from isovox.model import VoxModel
from isovox.palette import lerp, resolve, shades
from isovox.project import Camera, project


def test_project_shear():
    assert project(0, 0, 0) == (0.0, 0.0)
    assert project(1, 0, 0) == (2.0, 1.0)     # u: down-right
    assert project(0, 1, 0) == (-2.0, 1.0)    # v: down-left
    assert project(0, 0, 3) == (0.0, -3.0)    # h: straight up


def test_camera_centers_target():
    cam = Camera(center=(5, 5, 0))
    col, row = cam.to_screen(5, 5, 0, 100, 40)
    assert (col, row) == (50, 20)


def test_model_parse_layers_and_palette():
    m = VoxModel.parse("""
; comment
@r red
@b #112233 #
#0
rr
.b
#2
r.
""")
    assert m.voxels[(0, 0, 0)] == ("r", resolve("red"))
    assert m.voxels[(0, 1, 0)] == ("r", resolve("red"))
    assert m.voxels[(1, 1, 0)] == ("#", "#112233")
    assert (1, 0, 0) not in m.voxels          # '.' is empty
    assert m.voxels[(0, 0, 2)] == ("r", resolve("red"))
    assert m.size == (2, 2, 3)


def test_model_parse_rejects_unknown_key():
    with pytest.raises(ValueError):
        VoxModel.parse("#0\nx\n")


def test_box():
    m = VoxModel.box(2, 3, 4, "blue")
    assert len(m.voxels) == 24
    assert m.size == (2, 3, 4)


def test_buffer_put_and_bounds():
    b = CharBuffer(10, 4)
    b.put(1, 2, "@", "#ff0000")
    b.put(99, 99, "@", "#ff0000")   # silently ignored
    assert b.cells[1][2] == ("@", "#ff0000")
    assert "@" in b.to_text()


def test_buffer_text_helper():
    b = CharBuffer(20, 3)
    b.text(0, 1, "hi", "cream")
    assert b.to_text().splitlines()[0][1:3] == "hi"


def test_lerp_and_shades():
    assert lerp("#000000", "#ffffff", 0.5) == "#808080"
    top, wl, wr = shades("red", "#1F1E1D")
    assert top == resolve("red")
    assert wl != wr != top
