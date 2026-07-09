"""Terminal adapters: ANSI truecolor diff renderer + raw-mode key input.

Zero dependencies: straight escape sequences and termios. macOS + Linux.
The renderer keeps the previous frame and only rewrites cells that changed,
batching color changes -- comfortably 30+ fps on a normal terminal.
"""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import tty

from ..buffer import CharBuffer
from ..ports import Event, Key, Quit


def term_size() -> tuple[int, int]:
    """Usable (cols, rows), leaving one row so the last newline never scrolls."""
    cols, rows = shutil.get_terminal_size((100, 35))
    return cols, rows - 1


def _sgr(color: str) -> str:
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return f"\x1b[38;2;{r};{g};{b}m"


class TermRenderer:
    def __init__(self, out=None):
        self.out = out or sys.stdout
        self._prev: list[list] | None = None
        self._bg = None

    def open(self, width: int, height: int) -> None:
        # alt screen, hidden cursor, cleared
        self.out.write("\x1b[?1049h\x1b[?25l\x1b[2J")
        self.out.flush()
        self._prev = None

    def draw(self, buf: CharBuffer) -> None:
        w = []
        if self._bg != buf.bg:
            self._bg = buf.bg
            r, g, b = int(buf.bg[1:3], 16), int(buf.bg[3:5], 16), int(buf.bg[5:7], 16)
            w.append(f"\x1b[48;2;{r};{g};{b}m\x1b[2J")
            self._prev = None
        prev = self._prev
        color = None
        for rown, row in enumerate(buf.cells):
            prow = prev[rown] if prev else None
            col = 0
            while col < buf.width:
                if prow and prow[col] == row[col]:
                    col += 1
                    continue
                # start of a dirty run: position cursor once, stream until clean
                w.append(f"\x1b[{rown + 1};{col + 1}H")
                while col < buf.width and not (prow and prow[col] == row[col]):
                    ch, c = row[col]
                    if c != color:
                        w.append(_sgr(c))
                        color = c
                    w.append(ch)
                    col += 1
        self._prev = [list(r) for r in buf.cells]
        self.out.write("".join(w))
        self.out.flush()

    def close(self) -> None:
        self.out.write("\x1b[0m\x1b[?25h\x1b[?1049l")
        self.out.flush()


_ESCAPES = {
    "[A": "up", "[B": "down", "[C": "right", "[D": "left",
    "OA": "up", "OB": "down", "OC": "right", "OD": "left",
}


class TermInput:
    def __init__(self):
        self._fd = None
        self._saved = None

    def open(self) -> None:
        self._fd = sys.stdin.fileno()
        self._saved = termios.tcgetattr(self._fd)
        tty.setcbreak(self._fd)   # cbreak keeps Ctrl-C working

    def poll(self) -> list[Event]:
        events: list[Event] = []
        while select.select([self._fd], [], [], 0)[0]:
            ch = os.read(self._fd, 1).decode(errors="ignore")
            if ch == "\x1b":
                seq = ""
                while len(seq) < 2 and select.select([self._fd], [], [], 0.002)[0]:
                    seq += os.read(self._fd, 1).decode(errors="ignore")
                name = _ESCAPES.get(seq)
                events.append(Key(name) if name else Key("esc"))
            elif ch in ("\x03", "q"):
                events.append(Quit())
            elif ch in ("\r", "\n"):
                events.append(Key("enter"))
            elif ch == "\x7f":
                events.append(Key("backspace"))
            elif ch == "\t":
                events.append(Key("tab"))
            elif ch:
                events.append(Key(ch))
        return events

    def close(self) -> None:
        if self._saved is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            self._saved = None
