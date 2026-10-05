"""Ad-hoc: read a `<pre>` of coloured `<b>` cells - the "0/1 picture" pages - and draw it as a PNG.

`参考及想法/何尊.html` is one of those: 54 lines of `<b style="color:#RRGGBB">0</b>`, a picture made of
binary digits in the source pixels' own colours. This parses it so the thing can be *looked at* (and
compared with what the player would draw) without a browser.

    python _dev/html_art.py "..\\参考及想法\\何尊.html"
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
import mascot_glyphs as MG      # noqa: E402

CELL_W, CELL_H = 9, 18
CELL = re.compile(r'<b style="color:(#[0-9A-Fa-f]{6})">(.*?)</b>', re.S)


def parse(path: Path):
    """`[(char, (r, g, b))]` per line, one entry per character.

    A `<b>` holds *several* characters when they share a colour (the generator merges runs), so the text
    has to be expanded character by character - treating one `<b>` as one cell squashes the picture into
    unreadable stripes, which is what the first version of this did.
    """
    text = path.read_text(encoding="utf8")
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("<pre"):
            continue
        row = []
        for col, chunk in CELL.findall(line):
            rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
            for ch in html.unescape(chunk):
                row.append((ch, rgb))
        if row:
            out.append(row)
    return out


def draw(rows, bg=(0, 0, 0)) -> Image.Image:
    w = max(len(r) for r in rows)
    im = Image.new("RGB", (w * CELL_W, len(rows) * CELL_H), bg)
    d = ImageDraw.Draw(im)
    font = MG.font(CELL_H)
    for y, row in enumerate(rows):
        for x, (ch, col) in enumerate(row):
            d.text((x * CELL_W, y * CELL_H), ch, font=font, fill=col)
    return im


if __name__ == "__main__":
    p = Path(sys.argv[1] if len(sys.argv) > 1
             else ROOT.parent / "\u53c2\u8003\u53ca\u60f3\u6cd5" / "\u4f55\u5c0a.html")
    rows = parse(p)
    im = draw(rows)
    out = Path(__file__).resolve().parent / "out" / "html_art.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    chars = set(c for r in rows for c, _ in r)
    print(f"{len(rows)} lines x {max(len(r) for r in rows)} cells, chars {sorted(chars)}")
    print(out)
