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
"""

from __future__ import annotations

from .palette import resolve

Voxel = tuple[str, str]  # (glyph, "#rrggbb")


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
                if len(parts) not in (2, 3):
                    raise ValueError(f"bad palette line: {raw!r}")
                key, color = parts[0], resolve(parts[1])
                glyph = parts[2] if len(parts) == 3 else key
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
