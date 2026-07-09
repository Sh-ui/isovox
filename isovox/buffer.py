"""CharBuffer: the frame the core renders into and adapters consume.

A dense grid of (char, fg_color) cells over a uniform background color. This is
the boundary object between the pure raster code and any renderer adapter
(terminal, PNG, snapshot); it knows nothing about ANSI or fonts.
"""

from __future__ import annotations

from .palette import UMBRA, resolve

Cell = tuple[str, str]  # (single char, "#rrggbb")


class CharBuffer:
    def __init__(self, width: int, height: int, bg: str = UMBRA):
        self.width = width
        self.height = height
        self.bg = resolve(bg)
        self._blank: Cell = (" ", self.bg)
        self.cells: list[list[Cell]] = [
            [self._blank] * width for _ in range(height)
        ]

    def clear(self) -> None:
        blank = self._blank
        for row in self.cells:
            for c in range(self.width):
                row[c] = blank

    def put(self, row: int, col: int, ch: str, color: str) -> None:
        """Set one cell; silently ignores out-of-bounds (culling is cheap here)."""
        if 0 <= row < self.height and 0 <= col < self.width:
            self.cells[row][col] = (ch, color)

    def text(self, row: int, col: int, s: str, color: str = "cream") -> None:
        """Write a string horizontally (HUD, labels)."""
        color = resolve(color)
        for i, ch in enumerate(s):
            self.put(row, col + i, ch, color)

    def to_text(self) -> str:
        """Plain characters, no color -- what a headless agent reads."""
        return "\n".join("".join(ch for ch, _ in row) for row in self.cells)

    def to_ansi(self) -> str:
        """Full-frame ANSI truecolor string (no cursor movement, no diffing)."""
        out = []
        last = None
        for row in self.cells:
            line = []
            for ch, color in row:
                if color != last:
                    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
                    line.append(f"\x1b[38;2;{r};{g};{b}m")
                    last = color
                line.append(ch)
            out.append("".join(line))
        return "\n".join(out) + "\x1b[0m"
