"""Which sub-cell glyphs can this machine actually draw? Quadrants, braille, sextants, blocks.

    python _dev/glyph_probe.py

The film draws its pictures with `▀` plus a foreground and a background colour, which is one sub-cell
pair per cell. A quadrant (`▖▝▞▟`...) is 2x2 sub-cells with the same two colours, and a braille cell is
2x4 - four and eight times the detail for nothing but a different character. Whether they are *usable*
is a font question, not a taste question: the terminal's font has to have the glyph, and this project
already knows what a missing one costs (the waveform ramp rendered as `?` boxes until `tui_shot` sent
everything past ASCII to msyh). So this renders each family with the fonts the player and the renderer
use and reports whether the glyph came out empty or as a `.notdef` box.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FAMILIES = {
    "blocks U+2580-259F": [chr(c) for c in range(0x2580, 0x25A0)],
    "quadrants U+2596-259F": [chr(c) for c in range(0x2596, 0x25A0)],
    "braille U+2800-28FF": [chr(c) for c in range(0x2800, 0x2900, 0x11)],
    "sextants U+1FB00-1FB3B": [chr(c) for c in range(0x1FB00, 0x1FB3C, 5)],
    "shade U+2591-2593": [chr(c) for c in (0x2591, 0x2592, 0x2593)],
    "geometric U+25A0-25FF": [chr(c) for c in (0x25A0, 0x25AA, 0x25CF, 0x25CB, 0x25B2)],
}
FONTS = ["C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/simsun.ttc",
         "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/SimHei.ttf"]


def glyph_ink(font: ImageFont.FreeTypeFont, ch: str, size: int = 16) -> int:
    """How many pixels the glyph actually puts on the mask. 0 = blank, a full box = a fallback `.notdef`."""
    try:
        mask = font.getmask(ch)
    except Exception:
        return -1
    w, h = mask.size
    if not w or not h:
        return 0
    data = mask.tobytes() if hasattr(mask, "tobytes") else bytes(mask)
    return sum(1 for b in data if b > 40)


def main() -> None:
    for path in FONTS:
        p = Path(path)
        if not p.exists():
            print(f"{p.name:14s} (not installed)")
            continue
        try:
            font = ImageFont.truetype(path, 16)
        except Exception as exc:                      # noqa: BLE001
            print(f"{p.name:14s} cannot be loaded: {exc}")
            continue
        print(f"{p.name}")
        for family, chars in FAMILIES.items():
            inks = [glyph_ink(font, c) for c in chars]
            blank = sum(1 for i in inks if i == 0)
            # a `.notdef` is the same ink for every character in the run, and it is a full box
            same = len(set(inks)) == 1 and inks[0] > 0
            note = "all identical (a fallback box?)" if same else f"{blank} blank of {len(chars)}"
            sample = " ".join(f"{c}:{i}" for c, i in list(zip(chars, inks))[:6])
            print(f"   {family:22s} {note:32s} {sample}")
        print()
    # and what the renderer would actually show, as one PNG
    im = Image.new("RGB", (760, 40 * len(FAMILIES) + 10), (10, 12, 18))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except Exception:
        f = ImageFont.load_default()
    y = 5
    for family, chars in FAMILIES.items():
        d.text((6, y), "".join(chars[:24]), font=f, fill=(230, 236, 248))
        d.text((640, y), family.split()[0], font=f, fill=(120, 140, 180))
        y += 40
    out = Path(__file__).resolve().parent / "out" / "glyphs.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(f"sample sheet -> {out}")


if __name__ == "__main__":
    main()
