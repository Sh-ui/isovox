"""VoxModel: a small voxel sprite, hand-authorable as plain text (.ivx).

Format (see isovox/assets/*.ivx for live examples):

    ; comment
    @r red          ; map key 'r' to palette color "red" (glyph defaults to 'r')
    @b #1987E8 #    ; map key 'b' to a hex color, rendered with glyph '#'
    #0              ; start layer h=0 (bottom)
    rr
    rr
    #1              ; layer h=1
    .b              ; '.' = empty
    b.

Within a layer, each text line advances u by 1 (down-right axis) and each
character advances v by 1 (down-left axis). Layers stack upward in h.

Face materials
--------------
A voxel is normally one material, (glyph, color); the raster derives the lit
top / mid left wall / dark right wall from that single color. A voxel may
instead carry per-face overrides -- (glyph, color, (top, left, right)) where
each face slot is None or its own (glyph, color) -- so a cabin voxel can have
a painted roof on top and glass on its walls. In .ivx, faces hang off the
palette line:

    @c red = top=#802020 left=#9FD4E8:# right=#9FD4E8:#

i.e. face=COLOR or face=COLOR:GLYPH (one glyph char; omitted = base glyph).
Faces are SCREEN-space (top / camera-left / camera-right as drawn), not
object-space: rotated() turns the geometry but face data rides along
unchanged, which is exactly what you want with one fixed camera angle.

isovox.sprites generates dense models programmatically; dumps() writes any
model back out as .ivx, which is how the shipped assets are produced.
"""

from __future__ import annotations

from .palette import resolve

Face = tuple[str, str]         # (glyph, "#rrggbb")
Voxel = tuple                  # (glyph, color) or (glyph, color, (top, left, right))

_FACE_NAMES = ("top", "left", "right")
# keys dumps() may assign; excludes '.', ' ', '@', ';', '#' (format syntax)
_DUMP_KEYS = ("abcdefghijklmnopqrstuvwxyz"
              "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


def _parse_face(spec: str, base_glyph: str) -> Face:
    """COLOR or COLOR:GLYPH (glyph is exactly one char, may itself be ':')."""
    if len(spec) >= 2 and spec[-2] == ":":
        return (spec[-1], resolve(spec[:-2]))
    return (base_glyph, resolve(spec))


class VoxModel:
    def __init__(self, voxels: dict[tuple[int, int, int], Voxel]):
        self.voxels = voxels  # (u, v, h) -> (glyph, color)
        if voxels:
            us, vs, hs = zip(*voxels)
            self.size = (max(us) + 1, max(vs) + 1, max(hs) + 1)
        else:
            self.size = (0, 0, 0)

    def rotated(self, quarters: int) -> "VoxModel":
        """This model rotated by quarter turns around the h axis (cached).

        The lazy way to face a sprite in 4 directions: author one .ivx,
        then `entity.model = base.rotated(k)` as it turns.
        """
        q = quarters % 4
        if q == 0:
            return self
        cache = getattr(self, "_rot_cache", None)
        if cache is None:
            cache = self._rot_cache = {}
        if q not in cache:
            du = self.size[0]
            vox = {(v, du - 1 - u, h): x for (u, v, h), x in self.voxels.items()}
            model = VoxModel(vox)
            cache[q] = model if q == 1 else VoxModel.rotated(model, q - 1)
        return cache[q]

    @classmethod
    def box(cls, du: int, dv: int, dh: int, color: str, glyph: str = "#") -> "VoxModel":
        """Solid cuboid -- handy for buildings and placeholders."""
        color = resolve(color)
        return cls({
            (u, v, h): (glyph, color)
            for u in range(du) for v in range(dv) for h in range(dh)
        })

    @classmethod
    def parse(cls, text: str) -> "VoxModel":
        key_map: dict[str, Voxel] = {}
        voxels: dict[tuple[int, int, int], Voxel] = {}
        layer = None
        u = 0
        for raw in text.splitlines():
            line = raw.split(";")[0].rstrip()
            if not line.strip():
                continue
            if line.startswith("@"):
                parts = line[1:].split()
                if len(parts) < 2:
                    raise ValueError(f"bad palette line: {raw!r}")
                key, color = parts[0], resolve(parts[1])
                glyph, face_parts = key, []
                for p in parts[2:]:
                    name = p.split("=", 1)[0]
                    if name in _FACE_NAMES and "=" in p:
                        face_parts.append((name, p.split("=", 1)[1]))
                    elif not face_parts and len(p) == 1:
                        glyph = p           # base glyph (may be '=' etc.)
                    else:
                        raise ValueError(f"bad palette token {p!r} in {raw!r}")
                if face_parts:
                    faces = [None, None, None]
                    for name, spec in face_parts:
                        faces[_FACE_NAMES.index(name)] = _parse_face(spec, glyph)
                    key_map[key] = (glyph, color, tuple(faces))
                else:
                    key_map[key] = (glyph, color)
            elif line.startswith("#"):
                layer = int(line[1:].strip())
                u = 0
            else:
                if layer is None:
                    raise ValueError("grid row before any '#<h>' layer header")
                for v, ch in enumerate(line):
                    if ch in (".", " "):
                        continue
                    if ch not in key_map:
                        raise ValueError(f"key {ch!r} not declared with '@' line")
                    voxels[(u, v, layer)] = key_map[ch]
                u += 1
        return cls(voxels)

    @classmethod
    def load(cls, path: str) -> "VoxModel":
        with open(path, encoding="utf-8") as f:
            return cls.parse(f.read())

    def dumps(self, comment: str = "") -> str:
        """Serialize back to .ivx text; parse(dumps(m)) reproduces m.voxels.

        This is how generated sprites (isovox.sprites) become shipped asset
        files. Keys are assigned per distinct material, a-z then A-Z then 0-9.
        """
        seen: dict[Voxel, str] = {}
        lines = ["; " + comment] if comment else []
        palette_lines = []
        for pos in sorted(self.voxels):
            vox = self.voxels[pos]
            if vox in seen:
                continue
            if len(seen) >= len(_DUMP_KEYS):
                raise ValueError("too many distinct materials for .ivx keys")
            key = _DUMP_KEYS[len(seen)]
            seen[vox] = key
            glyph, color = vox[0], vox[1]
            parts = [f"@{key}", color, glyph]
            if len(vox) > 2:
                for name, f in zip(_FACE_NAMES, vox[2]):
                    if f is not None:
                        fg, fc = f
                        parts.append(f"{name}={fc}" + ("" if fg == glyph
                                                       else ":" + fg))
            palette_lines.append(" ".join(parts))
        lines += palette_lines
        du, dv, dh = self.size
        for h in range(dh):
            rows = ["".join(seen[self.voxels[(u, v, h)]]
                            if (u, v, h) in self.voxels else "."
                            for v in range(dv))
                    for u in range(du)]
            if any(r.strip(".") for r in rows):
                lines.append(f"#{h}")
                lines += rows
        return "\n".join(lines) + "\n"
