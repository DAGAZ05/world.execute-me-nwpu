"""Ad-hoc: the basketball animation JSON, drawn as a contact sheet - look at it before wiring it in.

    python _dev/dunk_sheet.py                 frames 0,4,8,...,28 as one PNG
    python _dev/dunk_sheet.py --frame 12      one frame, as text
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "\u53c2\u8003\u53ca\u60f3\u6cd5" / "hangxiaotian.json"
CELL_W, CELL_H = 7, 13


def load() -> dict:
    return json.loads(SRC.read_text(encoding="utf8"))


def cells(fr: dict):
    """`[(char, (r, g, b))]` per line, with the frame's own per-cell colours applied."""
    c = fr.get("colors") or {}
    fg = c.get("foreground")
    if isinstance(fg, str):
        fg = json.loads(fg)
    fg = fg or {}
    lines = fr["contentString"].splitlines()
    # the character carries the shade (measured: mean grey runs 238 for `&`/`8` down to 153 for `J`/`U`),
    # so a cell with no override still has a grey - taken as the mean of the same character elsewhere
    seen: dict[str, list[int]] = {}
    for key, hexv in fg.items():
        x, y = (int(v) for v in key.split(","))
        if y < len(lines) and x < len(lines[y]):
            seen.setdefault(lines[y][x], []).append(sum(int(hexv[i:i + 2], 16) for i in (1, 3, 5)) // 3)
    grey = {k: sum(v) // len(v) for k, v in seen.items()}
    out = []
    for y, ln in enumerate(lines):
        row = []
        for x, ch in enumerate(ln):
            hexv = fg.get(f"{x},{y}")
            if hexv:
                rgb = tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5))
            else:
                g = grey.get(ch, 90)
                rgb = (g, g, g)
            row.append((ch, rgb))
        out.append(row)
    return out


def draw(rows) -> Image.Image:
    w = max(len(r) for r in rows)
    im = Image.new("RGB", (w * CELL_W, len(rows) * CELL_H), (0, 0, 0))
    d = ImageDraw.Draw(im)
    from PIL import ImageFont
    font = None
    for p in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/DejaVuSansMono.ttf"):
        try:
            font = ImageFont.truetype(p, CELL_H)
            break
        except OSError:
            continue
    font = font or ImageFont.load_default()
    for y, row in enumerate(rows):
        for x, (ch, rgb) in enumerate(row):
            d.text((x * CELL_W, y * CELL_H), ch, font=font, fill=rgb)
    return im


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frame", type=int, default=-1)
    ap.add_argument("--step", type=int, default=4)
    a = ap.parse_args()
    # draw what the *player* draws: `school_fx.basket_frames` is the loader the film uses, so a probe with
    # its own copy of the rules is a probe that can disagree with the player
    sys.path.insert(0, str(ROOT / "player" / "_tools"))
    import school_fx as FX
    frames = FX.basket_frames()
    if not frames:
        print("the animation did not load")
        raise SystemExit(1)
    if a.frame >= 0:
        for y, row in enumerate(frames[a.frame][0]):
            print(f"{y:3}|" + "".join(" " if c is None else c[0] for c in row))
        raise SystemExit(0)
    picked = list(range(0, len(frames), a.step))
    shots = []
    for i in picked:
        grid, w, h = frames[i]
        im = Image.new("RGB", (w * CELL_W, h * CELL_H), (0, 0, 0))
        d = ImageDraw.Draw(im)
        from PIL import ImageFont
        font = None
        for p in ("C:/Windows/Fonts/consola.ttf", "C:/Windows/Fonts/DejaVuSansMono.ttf"):
            try:
                font = ImageFont.truetype(p, CELL_H)
                break
            except OSError:
                continue
        font = font or ImageFont.load_default()
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell is None:
                    continue
                # `(char, level, fg, bg)` - the panel is drawn the way the player draws it, background
                # first, so this sheet is the picture and not a negative of it
                ch, _lv, fg, bg = cell
                d.rectangle([x * CELL_W, y * CELL_H, (x + 1) * CELL_W - 1, (y + 1) * CELL_H - 1], fill=bg)
                d.text((x * CELL_W, y * CELL_H), ch, font=font, fill=fg)
        shots.append(im)
    cw = max(s.width for s in shots) + 8
    ch = max(s.height for s in shots) + 8
    cols = 4
    rows_n = (len(shots) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cw, rows_n * ch), (20, 20, 24))
    for k, s in enumerate(shots):
        r, c = divmod(k, cols)
        sheet.paste(s, (c * cw + 4, r * ch + 4))
    out = Path(__file__).resolve().parent / "out" / "dunk_sheet.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print(f"{len(picked)} frames -> {out}  ({sheet.size})")
