"""What is actually in `航小天篮球.json`? Render frame 0 as the artist drew it, at 1:1.

    python _dev/basket_view.py            -> _dev/out/basket_as_drawn.png  and  _basket_inverted.png

The player draws this art inverted - bright figure, no paper - because the film's ground is dark. Before
changing how it is drawn again it is worth looking at the file the way it was authored: light paper, dark
figure, exactly the colours in `colors`. If the figure is only legible that way, the answer is to draw it
as a lit panel rather than to keep inverting it.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
from tui_shot import Painter    # noqa: E402

ASSET = ROOT / "assets" / "航小天篮球.json"
OUT = Path(__file__).resolve().parent / "out"


def frame0():
    data = json.loads(ASSET.read_text(encoding="utf8"))
    fr = data["frames"][0]
    lines = fr["contentString"].splitlines()
    colours = {}
    for key in ("background", "foreground"):
        d = fr["colors"].get(key)
        d = json.loads(d) if isinstance(d, str) else (d or {})
        for k, hexv in d.items():
            if isinstance(hexv, str) and len(hexv) == 7:
                colours[k] = tuple(int(hexv[i:i + 2], 16) for i in (1, 3, 5))
    return lines, colours, data.get("canvas", {})


def build(cols: int, rows: int, invert: bool, paper: bool) -> T.Screen:
    lines, colours, canvas = frame0()
    s = T.Screen(cols, rows)
    for y, ln in enumerate(lines[:rows]):
        for x, ch in enumerate(ln[:cols]):
            rgb = colours.get(f"{x},{y}")
            if rgb is None:
                rgb = (229, 229, 229)
            pale = rgb[0] > 222 and rgb[1] > 222 and rgb[2] > 222
            if pale:
                if paper:
                    s.put(x, y, ch, (0, 0, 0), rgb)
                continue
            if invert:
                ink = 1.0 - sum(rgb) / 765.0
                warm = rgb[0] > rgb[1] + 12 and rgb[0] > rgb[2] + 12
                base = (255, 170, 90) if warm else (176, 206, 245)
                s.put(x, y, ch, tuple(int(c * (0.30 + 0.70 * min(1.0, ink * 1.2))) for c in base))
            else:
                s.put(x, y, ch, rgb)
    return s


def build_panel(cols: int = 70, rows: int = 40, texture: bool = True, dim: float = 0.72,
                ink=None, mass: bool = False) -> T.Screen:
    """The player's own panel, at 1:1 and at the size the box gives it - what `dunk` really draws.

    `mass=True` gives every figure cell its own colour as a *background* and a darker version of it as
    the glyph, so the figure is a solid mass with detail in it rather than a scatter of characters.
    """
    import school_fx as FX
    s = T.Screen(cols, rows)

    def col(rgb, f=1.0):
        return tuple(max(0, min(255, int(k * f * dim * t))) for k, t in zip(rgb, FX.PANEL_TINT))

    paper = col(FX.PAPER)
    for y in range(rows):
        for x in range(cols):
            s.put(x, y, " ", (0, 0, 0), paper)
    grid, w, h = FX.basket_frames()[0]
    if (cols, rows) != (w, h):
        grid, w, h = FX._fit_cells(grid, w, h, cols, rows)
    ox, oy = max(0, (cols - w) // 2), max(0, (rows - h) // 2)
    for r in range(h):
        for c in range(w):
            cell = grid[r][c]
            if cell is None:
                continue
            ch, lv, rgb = cell
            if lv < 0:
                s.put(ox + c, oy + r, ch, col(rgb, 0.82) if texture else paper, paper)
            elif mass:
                body = col(rgb)
                s.put(ox + c, oy + r, ch, tuple(int(k * 0.55) for k in body), body)
            else:
                s.put(ox + c, oy + r, ch, ink or col(rgb), paper)
    return s


def main() -> None:
    lines, _, canvas = frame0()
    cols, rows = canvas.get("width", 70), canvas.get("height", 40)
    p = Painter()
    for name, invert, paper in (("basket_as_drawn", False, True),
                                ("basket_inverted", True, False)):
        s = build(cols, rows, invert, paper)
        print(p.paint(s, OUT / f"{name}.png", name))
    variants = [
        ("basket_panel_full", dict(dim=1.0)),
        ("basket_panel_mass", dict(dim=1.0, mass=True)),
        ("basket_panel_massdim", dict(mass=True)),
    ]
    for name, kw in variants:
        for cc, rr in ((70, 40), (98, 34), (60, 16)):
            s = build_panel(cc, rr, **kw)
            print(p.paint(s, OUT / f"{name}_{cc}x{rr}.png", f"{name} {cc}x{rr}"))


if __name__ == "__main__":
    main()
