"""A very small SVG rasteriser, for the one asset that was supplied as a vector drawing.

`参考及想法/何尊.svg` is the vessel as a line drawing - 1600x900, stroke-only paths, one mirrored
group - and the user's note was that the character art made from the *scan* is not good enough
("何尊的字符画效果较差，我在参考及想法中准备了一张何尊svg，请使用它"). The character art is only as good
as the pixels it starts from, so the fix is to start from the vector.

Nothing here is a general SVG implementation and it should not grow into one. It reads what this file
uses and says so when it meets something else:

  * elements   `<svg>`, `<g>`, `<path>`, `<circle>`, `<rect>`, `<line>`, `<polyline>`, `<polygon>`
  * transform  `translate`, `scale`, `matrix`, `rotate`, nested and inherited
  * path data  `M L H V C S Q T Z` absolute and relative, curves flattened to line segments
  * painting   stroke (with width and round joins) and fill; `none` means neither

What it does not do: arcs (`A`), dashes, gradients, text, opacity, or `use`. An `A` command is
flattened to its chord, which is wrong in general and does not matter here - the file has none - and
is reported by `unsupported()` so a future asset that needs it fails loudly instead of drawing
something subtly wrong.

    from school_svg import render
    im = render(Path(".../何尊.svg"), size=420)          # RGBA, ink on transparent
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw

NS = "{http://www.w3.org/2000/svg}"
# every command letter and every number, in one pass: this is the whole of the path syntax used
_TOKEN = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|(-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
_CURVE_STEPS = 10                      # a flattened quadratic/cubic, in segments

# what this renderer has met and could not do properly, filled in as it goes; the caller prints it
UNSUPPORTED: set[str] = set()


def unsupported() -> set[str]:
    return set(UNSUPPORTED)


# ---------------------------------------------------------------- transforms

def _matrix(spec: str):
    """An SVG `transform` list as one 2x3 matrix `(a, b, c, d, e, f)`."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", spec or ""):
        v = [float(x) for x in re.findall(r"-?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?", args)]
        if name == "translate":
            n = (1.0, 0.0, 0.0, 1.0, v[0], v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            sx = v[0]
            sy = v[1] if len(v) > 1 else sx
            n = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "matrix":
            n = tuple(v[:6])
        elif name == "rotate":
            a = math.radians(v[0])
            ca, sa = math.cos(a), math.sin(a)
            n = (ca, sa, -sa, ca, 0.0, 0.0)
            if len(v) > 2:                     # rotate(a cx cy)
                n = _mul((1.0, 0.0, 0.0, 1.0, v[1], v[2]),
                         _mul(n, (1.0, 0.0, 0.0, 1.0, -v[1], -v[2])))
        else:
            UNSUPPORTED.add(f"transform:{name}")
            continue
        m = _mul(m, n)
    return m


def _mul(m, n):
    """The matrix product `m * n`: `n` is applied to the point first, `m` last.

    This ordering is the whole of SVG's transform model and the first version of this function had it
    wrong - it mixed the row and column forms, so `translate(1600 0) scale(-1 1)` (the mirrored right
    half of the vessel) came out as `x' = -x - 1600` instead of `1600 - x`. The drawing then had ink
    from -2160 to 1115, and since `render` sizes the image by the *ink* box, the vessel was rasterised
    as a 420x86 sliver of almost nothing: the aspect came out 4.9 where the drawing's own is 0.94.
    """
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (a1 * a2 + c1 * b2, b1 * a2 + d1 * b2,
            a1 * c2 + c1 * d2, b1 * c2 + d1 * d2,
            a1 * e2 + c1 * f2 + e1, b1 * e2 + d1 * f2 + f1)


def _apply(m, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


# ---------------------------------------------------------------- path data

def _path_subpaths(d: str, m) -> list[list[tuple[float, float]]]:
    """`d` as a list of polylines in the parent's coordinates, curves already flattened."""
    toks = _TOKEN.findall(d)
    items: list[tuple[str, float | None]] = [(c or "n", float(v) if v else None) for c, v in toks]
    out: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = 0.0
    sx = sy = 0.0                        # the subpath's start, for Z
    prev_ctrl = None
    cmd = None
    i = 0
    while i < len(items):
        kind, val = items[i]
        if kind != "n":
            cmd = kind
            i += 1
            if cmd in ("Z", "z"):
                if cur:
                    cur.append((sx, sy))
                    out.append(cur)
                    cur = []
                x, y = sx, sy
                prev_ctrl = None
                continue
        elif cmd is None:
            i += 1
            continue
        elif cmd == "M":
            cmd = "L"                    # an implicit repeat of M is L
        elif cmd == "m":
            cmd = "l"
        n = _ARGS.get(cmd.upper(), 0)
        if n == 0 or i + n > len(items):
            break
        v = [items[i + k][1] for k in range(n)]
        i += n
        rel = cmd.islower()
        up = cmd.upper()
        if up == "A":
            # not implemented: the chord is drawn instead, and the caller is told
            UNSUPPORTED.add("path:A")
            px, py = (x + v[5], y + v[6]) if rel else (v[5], v[6])
            cur.append(_apply(m, px, py))
            x, y = px, py
            prev_ctrl = None
            continue
        if up == "H":
            px, py = (x + v[0] if rel else v[0]), y
        elif up == "V":
            px, py = x, (y + v[0] if rel else v[0])
        elif up == "M":
            px, py = (x + v[0], y + v[1]) if rel else (v[0], v[1])
        else:
            px, py = (x + v[-2], y + v[-1]) if rel else (v[-2], v[-1])
        if up == "M":
            if cur:
                out.append(cur)
            cur = [_apply(m, px, py)]
            sx, sy = px, py
        elif up == "L":
            cur.append(_apply(m, px, py))
        elif up in ("Q", "T", "C", "S"):
            if up in ("Q", "T"):
                cx, cy = ((x + v[0], y + v[1]) if rel else (v[0], v[1])) if up == "Q" \
                    else (2 * x - prev_ctrl[0], 2 * y - prev_ctrl[1]) if prev_ctrl else (x, y)
                ctrl = (cx, cy)
                p0 = (x, y)
                for s in range(1, _CURVE_STEPS + 1):
                    t = s / _CURVE_STEPS
                    bx = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * cx + t * t * px
                    by = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * cy + t * t * py
                    cur.append(_apply(m, bx, by))
                prev_ctrl = ctrl
            else:
                c1 = ((x + v[0], y + v[1]) if rel else (v[0], v[1])) if up == "C" \
                    else (2 * x - prev_ctrl[0], 2 * y - prev_ctrl[1]) if prev_ctrl else (x, y)
                c2 = (x + v[2], y + v[3]) if rel else (v[2], v[3])
                p0 = (x, y)
                for s in range(1, _CURVE_STEPS + 1):
                    t = s / _CURVE_STEPS
                    mt = 1 - t
                    bx = (mt ** 3 * p0[0] + 3 * mt * mt * t * c1[0]
                          + 3 * mt * t * t * c2[0] + t ** 3 * px)
                    by = (mt ** 3 * p0[1] + 3 * mt * mt * t * c1[1]
                          + 3 * mt * t * t * c2[1] + t ** 3 * py)
                    cur.append(_apply(m, bx, by))
                prev_ctrl = c2
            if up not in ("Q", "T"):
                pass
        x, y = px, py
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- the renderer

def _colour(text: str, default):
    text = (text or "").strip()
    if not text or text == "none":
        return None
    if text.startswith("#") and len(text) in (4, 7):
        h = text[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
    if text.startswith("rgb("):
        return tuple(int(float(x)) for x in text[4:-1].split(",")[:3])
    return default


def _walk(el, m, style, out) -> None:
    """Depth-first, carrying the transform and the inherited paint down the tree."""
    tag = el.tag.replace(NS, "")
    st = dict(style)
    for k in ("fill", "stroke", "stroke-width", "stroke-linejoin", "stroke-linecap"):
        if k in el.attrib:
            st[k] = el.attrib[k]
    if "transform" in el.attrib:
        m = _mul(m, _matrix(el.attrib["transform"]))
    if tag in ("svg", "g", "defs"):
        for child in el:
            _walk(child, m, st, out)
        return
    if tag == "path":
        subs = _path_subpaths(el.attrib.get("d", ""), m)
    elif tag == "circle":
        cx, cy, r = (float(el.attrib.get(k, 0)) for k in ("cx", "cy", "r"))
        pts = [_apply(m, cx + r * math.cos(a), cy + r * math.sin(a))
               for a in [k * math.pi / 24 for k in range(49)]]
        subs = [pts]
    elif tag in ("rect", "line", "polyline", "polygon"):
        if tag == "rect":
            x0, y0 = float(el.attrib.get("x", 0)), float(el.attrib.get("y", 0))
            w, h = float(el.attrib.get("width", 0)), float(el.attrib.get("height", 0))
            pts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
        elif tag == "line":
            pts = [(float(el.attrib.get("x1", 0)), float(el.attrib.get("y1", 0))),
                   (float(el.attrib.get("x2", 0)), float(el.attrib.get("y2", 0)))]
        else:
            v = [float(x) for x in re.findall(r"-?(?:\d+\.?\d*|\.\d+)", el.attrib.get("points", ""))]
            pts = list(zip(v[0::2], v[1::2]))
        if tag in ("polygon", "rect"):
            pts = pts + [pts[0]]
        subs = [[_apply(m, px, py) for px, py in pts]]
    else:
        UNSUPPORTED.add(f"element:{tag}")
        return
    out.append((subs, st))


def render(path: Path, size: int = 420, supersample: int = 2, bg=(255, 255, 255)) -> Image.Image:
    """The SVG as an image whose *ink* is `size` pixels on its long side.

    Drawn at `supersample` times the final resolution and reduced, because a 4.5-unit stroke on a
    1600-unit canvas is a hairline at cell resolution and an aliased hairline is what makes a line
    drawing turn to mud once it is sampled into characters.

    `bg` defaults to white and that is not cosmetic: a stroke-only SVG rasterised on a *transparent*
    ground has an RGB of (0,0,0) behind it, so the drawing is 23-on-0 - a luminance difference of 23 out
    of 255 - and the Sobel that turns it into characters sees almost nothing. Rendered on paper it is
    23-on-255 and every stroke is a full-contrast edge. The first version did the transparent thing and
    the vessel came out as forty scattered marks.
    """
    tree = ET.parse(str(path))
    root = tree.getroot()
    vb = re.findall(r"-?(?:\d+\.?\d*|\.\d+)", root.attrib.get("viewBox", ""))
    if len(vb) == 4:
        vx, vy, vw, vh = (float(x) for x in vb)
    else:
        vw = float(root.attrib.get("width", "100").rstrip("px"))
        vh = float(root.attrib.get("height", "100").rstrip("px"))
        vx = vy = 0.0
    out: list = []
    _walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0),
          {"fill": "black", "stroke": "none", "stroke-width": "1"}, out)
    # the ink's own box, so `size` means the drawing rather than the canvas it was authored on
    xs = [p[0] for subs, _st in out for sub in subs for p in sub]
    ys = [p[1] for subs, _st in out for sub in subs for p in sub]
    if not xs:
        return Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    pad = 8.0
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    scale = size * supersample / max(1e-6, max(x1 - x0, y1 - y0))
    w = max(1, int(round((x1 - x0) * scale)))
    h = max(1, int(round((y1 - y0) * scale)))
    im = Image.new("RGBA", (w, h), tuple(bg) + (255,) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(im)

    def px(p):
        return ((p[0] - x0) * scale, (p[1] - y0) * scale)

    for subs, st in out:
        stroke = _colour(st.get("stroke"), None)
        fill = _colour(st.get("fill"), (0, 0, 0))
        try:
            sw = float(st.get("stroke-width", 1))
        except ValueError:
            sw = 1.0
        for sub in subs:
            pts = [px(p) for p in sub]
            if fill is not None and len(pts) >= 3:
                d.polygon(pts, fill=tuple(fill) + (255,))
            if stroke is not None and len(pts) >= 2:
                d.line(pts, fill=tuple(stroke) + (255,), width=max(1, int(round(sw * scale))),
                       joint="curve")
    if supersample > 1:
        im = im.resize((max(1, w // supersample), max(1, h // supersample)), Image.LANCZOS)
    return im
