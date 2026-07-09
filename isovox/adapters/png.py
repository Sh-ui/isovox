"""PNG adapter: render a CharBuffer to an image file. Optional -- needs Pillow.

Two uses: wallpaper-grade stills of game scenes, and letting an AI agent
(or a human on the other end of a chat) *see* a frame with real colors.
"""

import os

from ..buffer import CharBuffer

_FONTS = [
    "/System/Library/Fonts/Menlo.ttc",                      # macOS
    "/System/Library/Fonts/Monaco.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
]


def save_png(buf: CharBuffer, path: str, font_size: int = 14,
             supersample: int = 2) -> str:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        raise ImportError("PNG export needs Pillow: pip install pillow") from None

    fs = font_size * supersample
    font = None
    for p in _FONTS:
        if os.path.exists(p):
            font = ImageFont.truetype(p, fs)
            break
    if font is None:
        font = ImageFont.load_default()

    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    cw = probe.textlength("M", font=font)
    rh = round(cw * 2.0)   # ~2:1 cell like a terminal
    W, H = round(buf.width * cw), buf.height * rh
    img = Image.new("RGB", (W, H), buf.bg)
    d = ImageDraw.Draw(img)
    for r, row in enumerate(buf.cells):
        for c, (ch, color) in enumerate(row):
            if ch != " ":
                d.text((c * cw, r * rh), ch, font=font, fill=color)
    if supersample > 1:
        img = img.resize((W // supersample, H // supersample), Image.LANCZOS)
    img.save(path, optimize=True)
    return path
