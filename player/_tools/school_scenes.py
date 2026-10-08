"""The school variant's right-hand column: what the machine is running, shot by shot.

The film's right column holds the film's own world - the corpus river, the loss curve, the causal mask, the KV
cache wall, the EXECUTION hits. This module holds 西工大's, and the one rule it is written under is
that it must read as **one machine the whole way through**: the same three bands, the same border
weight, the same palette, and content that goes from a first-year's board to a third-year's project
without ever becoming a different application.

Every function here is a *pane*: `f(s, x0, y0, x1, y1, t, lt, dur, u)` drawing into the rectangle
the player hands it, exactly like `tui_live.draw_corpus` and its siblings. `draw_body` picks one by
name from the shot table; a pane that cannot fit its content is expected to draw less, never to
overflow - the player gives a pane as little as six rows.

Two house rules, borrowed from the film's own panels:

  * **Nothing turns on that does not turn off.** A state opened in a pane is closed in the same pane
    (`visual-system.md`: "everything that turns on must have an explicit exit").
  * **A value on screen is either measured or declared.** Numbers that describe the school come from
    `02_叙事设计.md` §9 (the official figures); numbers that describe the *drawing* (trace widths,
    resistor counts) come from a seeded generator, so the same `t` gives the same board.
"""
from __future__ import annotations

import math
import random

# the film's own two colour helpers are passed in rather than imported, so this module never has to
# know whether it is being drawn by `tui_live` or by a probe. `PANE_CTX` is filled by `school_panels`
# at import: (ui, mix, ME_TEXT, ANOM, RED, BG).
PANE_CTX: dict = {}


def _ui(level: float = 1.0):
    return PANE_CTX["ui"](level)


def _mix(c, level: float = 1.0):
    return PANE_CTX["mix"](c, level)


def _beat(t: float) -> float:
    """The film's own beat pulse at `t`: 1 on the beat, decaying over 140 ms (`FP.pulse`).

    Imported lazily and guarded, because this module is also loaded by probes that do not import the
    film's clock. A pane that has to move on the beat and cannot find the clock falls back to a sine at
    the beat's own rate rather than to a constant - a constant would make `_dev/clock_probe.py` call the
    pane a still frame, and the sine at least keeps the *rate* honest in a probe context.
    """
    try:
        import film_panels as _FP
        return _FP.pulse(t)
    except Exception:
        return 0.5 + 0.5 * math.sin(2 * math.pi * t / 0.4615)


ME_TEXT = (126, 152, 255)          # the film's own colours; resolved again at import if present
ANOM = (255, 204, 0)
RED = (255, 59, 48)
BG = (4, 7, 15)
COPPER = (196, 146, 74)            # a PCB trace, lit
COPPER_DIM = (74, 58, 34)          # ...and unlit
SILK = (196, 208, 228)             # the silkscreen

def _palette() -> None:
    """Pick up the player's palette once, if `school_panels` supplied it."""
    g = globals()
    for name in ("ME_TEXT", "ANOM", "RED", "BG"):
        if name in PANE_CTX:
            g[name] = PANE_CTX[name]


# --------------------------------------------------------------------------- drawing helpers

def _trace(rnd: random.Random, w: int, h: int) -> list[tuple[int, int, str]]:
    """One PCB trace as `(x, y, char)` cells: an L, the way a real board routes one net.

    Always starts on the left edge and always ends on the right, so a set of them reads as a bus
    rather than as scattered lines. `char` is filled in by the caller's junction pass.
    """
    y0 = rnd.randrange(1, max(2, h - 1))
    y1 = rnd.randrange(1, max(2, h - 1))
    xk = rnd.randrange(max(2, w // 4), max(3, w - w // 4))
    out = []
    for x in range(0, xk):
        out.append((x, y0, "\u2500"))
    for y in range(min(y0, y1), max(y0, y1) + 1):
        if y != y0 and y != y1:
            out.append((xk, y, "\u2502"))
    out.append((xk, y0, "\u2510" if y1 > y0 else "\u2518"))
    for x in range(xk + 1, w):
        out.append((x, y1, "\u2500"))
    out.append((xk, y1, "\u2514" if y1 > y0 else "\u250c"))
    return out


def _bus(w: int, h: int, n: int, seed: int) -> list[list[tuple[int, int, str]]]:
    rnd = random.Random(seed)
    return [_trace(rnd, w, h) for _ in range(n)]


# --------------------------------------------------------------------------- panes

def pane_power_on(s, x0: int, y0: int, x1: int, y1: int, t: float, lt: float, dur: float, u: float) -> None:
    """`Switch on the power line` (0.03 s): the board's traces light up one net at a time.

    The current does not fade in over the whole board - it *travels*, which is the only reading of
    the line that is not a decoration. Each trace gets its own switch time inside the first word;
    the trace being switched shows a single bright cell walking along it; a trace that has arrived
    stays lit and never goes dark again. The last trace to arrive is the one that is not connected
    to anything yet, and it flashes red - the film's own first warning, planted at 0.9 s with no
    line of dialogue to explain it.

    `dur` is the shot's length, so all of this is placed in *shot progress* and the pane looks the
    same whether the shot is reached by playing or by seeking.
    """
    w, h = x1 - x0, y1 - y0
    if w < 8 or h < 3:
        return
    inner_h = h
    traces = _bus(w - 1, inner_h, max(3, min(11, inner_h)), seed=1938)
    n = len(traces)
    # the switch times: the first 80 % of the first word's shot, then a hold
    switch_at = [0.06 + 0.62 * (k / max(1, n - 1)) for k in range(n)]
    for k, cells in enumerate(traces):
        a = switch_at[k]
        if u < a:
            fg, walk = COPPER_DIM, None
        else:
            # the walker crosses the trace in 0.22 of the shot, from this trace's own switch
            v = min(1.0, (u - a) / 0.22)
            walk = int(v * (len(cells) - 1))
            fg = COPPER if v >= 1.0 else COPPER
        last = (k == n - 1)
        for i, (cx, cy, ch) in enumerate(cells):
            if cx < 0 or cy < 0 or cx >= w or cy >= h:
                continue
            c = fg
            if walk is not None and i <= walk:
                # the leading cell is nearly white; behind it the trace is at its own colour
                c = _mix((255, 236, 200), 1.0) if i == walk else fg
            if last and u >= switch_at[k] and int(lt * 6) % 2 == 0:
                c = RED
            s.put(x0 + cx, y0 + cy, ch, c)
    # the silkscreen the board carries, and the one net that is not terminated
    if h >= 3:
        s.put(x0, y0 + h - 1, "VCC 5V", _mix(SILK, 0.7))
        lab = "GND"
        s.put(x0 + w - len(lab) - 1, y0 + h - 1, lab, _mix(SILK, 0.7))
    if w >= 22 and h >= 5:
        s.put(x0 + 2, y0 + h - 3, "UNO R3", _mix(SILK, 0.45))


def pane_protection(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Remember to put on protection` (1.33 s): the wrist strap, closing onto the ground.

    The trace bus from the previous shot is still on the board, dimmed: this is the same machine one
    second later, not a new panel. On top of it a strap closes and a fuse seats itself.
    """
    w, h = x1 - x0, y1 - y0
    if w < 10 or h < 4:
        return
    traces = _bus(w - 1, h, max(3, min(9, h)), seed=1938)
    for cells in traces:
        for cx, cy, ch in cells:
            if 0 <= cx < w and 0 <= cy < h:
                s.put(x0 + cx, y0 + cy, ch, _mix(COPPER_DIM, 0.55))
    cy = y0 + h // 2
    # the strap: a band around the wrist, tightening as the line is sung
    band_w = max(6, w // 3)
    bx = x0 + max(1, (w - band_w) // 2)
    closed = min(1.0, u / 0.55)
    for i, ch in enumerate("\u250c" + "\u2500" * (band_w - 2) + "\u2510"):
        s.put(bx + i, cy - 1, ch, _mix(SILK, 0.85))
    for i, ch in enumerate("\u2514" + "\u2500" * (band_w - 2) + "\u2518"):
        s.put(bx + i, cy + 1, ch, _mix(SILK, 0.85))
    s.put(bx - 2, cy, "\u25cf", _mix(ANOM, 0.35 + 0.65 * closed))
    s.put(bx + band_w + 1, cy, "\u25cf", _mix(ANOM, 0.35 + 0.65 * closed))
    if w >= 20:
        s.put(x0 + 2, y0, "! ESD", _mix(ANOM, 0.5 + 0.5 * closed))
    if h >= 4:
        s.put(x0 + 2, y0 + h - 1, "fuse 0.5A", _mix(SILK, 0.5 * closed))
    # ...and the board is live: a signal runs the bus on the song clock. Without it this pane is a still
    # frame once its reveal is over, which the motif band underneath used to hide (batch 32 removed the
    # bands, so every pane has to carry its own clock).
    pulse = x0 + 1 + int((t * 11.0) % max(1, w - 3))
    s.put(pulse, y0 + 1, "\u25cf", _mix(ANOM, 0.55 + 0.35 * math.sin(t * 6.0)))


def pane_pieces(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Lay down your pieces` (3.58 s): the bill of materials arriving on the bench, one part at a time.

    **Not currently scheduled.** The opening was cut from six panes to four when the crest took 0.03 s
    (see `school_panels.SHOT_ROWS`), and this is the one that lost its slot - `Lay down your pieces`
    is now drawn by `pane_protection`, which is the pane that follows it. It is kept because the
    drawing is finished and correct and the bench sequence is the obvious thing to restore if the
    opening is ever given more room; it is reachable from `PANE_BY_NAME` and passes the pane probe.

    The parts and their order are the reference wiring diagram's own (`assets/嵌入式-超声波红外测距.jpg`):
    UNO, LCD1602, HC-SR04, the IR module, the breadboard, the 9 V cell, the jumpers. Each lands on its
    own word of the line, so the count of parts on the bench is a function of how far the line has
    been sung.
    """
    w, h = x1 - x0, y1 - y0
    if w < 12 or h < 4:
        return
    parts = [("UNO R3", 0.02), ("LCD1602", 0.16), ("HC-SR04", 0.30), ("IR", 0.42),
             ("breadboard", 0.54), ("9V", 0.66), ("jumpers", 0.78)]
    rows = min(len(parts), max(1, h - 1))
    for i, (name, at) in enumerate(parts[:rows]):
        on = u >= at
        yy = y0 + i
        mark = "\u25aa" if on else "\u25ab"
        s.put(x0 + 1, yy, mark, _mix(ME_TEXT, 0.95 if on else 0.35))
        s.put(x0 + 3, yy, name[: max(0, w - 6)], _ui(0.9 if on else 0.4))
        if on:
            # a landed part gets a right-hand check; the count is what the line is about
            s.put(x1 - 2, yy, "\u221a", _mix((120, 220, 160), 0.9))
    done = sum(1 for _, at in parts[:rows] if u >= at)
    s.put(x0 + 1, y0 + rows, f"{done}/{rows}", _ui(0.5))


def pane_class(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`And let's begin object creation` (5.16 s): the class the bench became, fields filling in."""
    src = [
        "class World(UNO):",
        "    name     = \"NWPU\"",
        "    campus   = \"CHANG'AN\"",
        "    sensors  = []",
        "    display  = None",
        "    def __init__(self):",
        "        self.begin()",
    ]
    w, h = x1 - x0, y1 - y0
    n = min(len(src), max(1, h))
    for i in range(n):
        # each source line arrives on its own beat of the shot
        at = 0.05 + 0.80 * (i / max(1, n - 1))
        if u < at:
            continue
        line = src[i][: max(0, w - 2)]
        col = _mix(ME_TEXT, 0.95) if i == 0 else _ui(0.85)
        s.put(x0 + 1, y0 + i, line, col)
    # a cursor walking the listing on the song clock: the class is *being* written, and a pane that stops
    # moving after its reveal is the failure `_dev/clock_probe.py` exists to catch
    cur = int(t * 1.6) % max(1, n)
    s.put(x0 + 2 + len(src[cur][: max(0, w - 2)]), y0 + cur, "\u258c", _mix(ANOM, 0.85))


def pane_parameters(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Fill in my data parameters` (7.19 s): a real parameter table, filled a cell at a time.

    The right-hand column carries the *source* of each value, and that is the point of the shot: the
    film's own panels are all measured, and this variant keeps that promise. Every figure here is
    from `02_叙事设计.md` §9, which quotes the school's own site, data as of 2026-08-05.
    """
    # The user's own four years (batch 34). `\u2605` is the major's spine - the courses this variant
    # treats as the software college - and every other line is a course that runs beside them; the footer
    # says exactly that, and each year is the complete list rather than "the first few".
    rows = [
        ("name", "\"西北工业大学\"", "\u6821\u53f2"),
        ("campus", "\"\u957f\u5b89\u6821\u533a \u4e1c\u7965\u8def1\u53f7\"", "\u5b98\u7f51"),
        ("founded", "1938", "\u6821\u53f2"),
        ("renamed", "1957", "\u6821\u53f2"),
        ("colleges", "24", "\u5b98\u7f51"),
        ("majors", "72", "\u5b98\u7f51"),
        ("students", "40000", "\u5b98\u7f51"),
    ]
    w, h = x1 - x0, y1 - y0
    n = min(len(rows), max(1, h))
    for i in range(n):
        at = 0.04 + 0.86 * (i / max(1, n - 1))
        if u < at:
            continue
        k, v, src = rows[i]
        s.put(x0 + 1, y0 + i, f"{k:<10}"[: max(0, w - 4)], _ui(0.7))
        if w >= 16:
            s.put(x0 + 12, y0 + i, v[: max(0, w - 16)], _mix(ME_TEXT, 0.9))
        if w >= 24:
            s.put(x1 - len(src) - 1, y0 + i, src, _ui(0.4))
    # the table is being filled: a cursor walks its rows on the song clock (see `pane_class`)
    if n:
        s.put(x0, y0 + int(t * 2.0) % n, ">", _mix(ANOM, 0.7))
    # the source of the oldest value in the table, drawn beside it: 何尊 is where "中国" is first
    # written down, so it annotates the table rather than replacing it (see `LANDMARK_ROWS`)
    if w >= 34 and h >= 8:
        try:
            from PIL import Image as _I  # noqa: F401
            import school_sculpture as SC
            box = (x0 + w - 18, y0 + max(0, h - 8), x1 - 1, y1 - 1)
            if SC.has("he_zun") and box[2] - box[0] >= 8 and box[3] - box[1] >= 3:
                got = SC.glyph_cells("he_zun", box[2] - box[0] + 1, box[3] - box[1] + 1)
                if got:
                    cells, cw, ch = got
                    # ...and only if there is ink in it: at the 18x8 box this leaves, the carried 何尊
                    # measured 0 of 144 cells - a picture that is not there, drawn anyway
                    inked = sum(1 for r in range(ch) for c in range(cw) if cells[r][c] is not None)
                    if inked < max(8, cw * ch // 20):
                        return
                    for r in range(ch):
                        for c in range(cw):
                            cell = cells[r][c]
                            if cell is None:
                                continue
                            ch_, lv = cell
                            s.put(box[0] + c, box[1] + r, ch_, _mix(ME_TEXT, 0.30 + 0.45 * (lv / 255)))
        except Exception:
            pass


def pane_polyhedra(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`If I'm a circle` / `Then I will give you my circumference` (33.01-36.77): n sides, and the limit.

    This pane used to draw five "Platonic solids" that were **the same diamond glyph five times** - the
    geometry did not depend on the index, only the labels changed - parked on the line about a circle,
    with the ops ticker promising `|x|^n / n=2 / CIRCLE` that was nowhere on screen (batch 31's audit:
    "the whole pane has no circle in it"). The couplet is about a circle and its circumference, so it is
    drawn as what it is: regular polygons of 3, 4, 5, 6, 8 and 36 sides, each *labelled with its own n*,
    all inscribed in one radius - and each one's perimeter written under it, converging on 2πr, which
    is the circumference the second line gives away. `n` walks on the song clock, so it is never still.
    """
    w, h = x1 - x0, y1 - y0
    if w < 20 or h < 5:
        return
    ns = [3, 4, 5, 6, 8, 36]
    lab = 2 if h >= 8 else 0
    pitch = max(7, min(14, (w - 4) // len(ns)))
    cy = y0 + (h - lab) // 2
    # One common radius for every polygon: that is the point of the drawing (all inscribed in one
    # circle). A cell is twice as tall as it is wide, so `ry = rx / 2` makes them round on screen.
    rx = max(2, min(pitch // 2, (h - lab) // 2))
    ry = max(1, rx // 2)
    step = (t * 0.6) % 1.0
    for i, n_sides in enumerate(ns):
        at = 0.05 + 0.75 * (i / max(1, len(ns) - 1))
        if u < at:
            continue
        cx = x0 + 3 + i * pitch + rx
        if cx + rx > x1:
            break
        pts = []
        for k in range(n_sides):
            th = 2 * math.pi * k / n_sides - math.pi / 2
            pts.append((cx + rx * math.cos(th), cy + ry * math.sin(th)))
        # the last one walks its own sides on the clock; the rest are revealed with the pane
        live = n_sides if n_sides <= 8 else max(3, int(n_sides * (0.35 + 0.65 * step)))
        for k in range(live):
            p0, p1 = pts[k % n_sides], pts[(k + 1) % n_sides]
            steps = max(1, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1]) * 2))
            for q in range(steps + 1):
                f = q / steps
                s.put(int(p0[0] + (p1[0] - p0[0]) * f),
                      int(round(p0[1] + (p1[1] - p0[1]) * f)),
                      "\u2022" if n_sides >= 36 else "\u00b7",
                      _mix(ME_TEXT, 0.8 if n_sides >= 36 else 0.95))
        if lab and cy + ry + 2 <= y1:
            s.put(cx - rx, cy + ry + 1, f"{n_sides:>2} \u8fb9" if n_sides < 36 else "\u5706", _ui(0.75))
            s.put(cx - rx, cy + ry + 2, f"{2 * n_sides * math.sin(math.pi / n_sides):.3f} r",
                  _mix(ANOM, 0.7))
    s.put(x0 + 1, y1 - 1, "n \u8fb9\u5f62\u7684\u5468\u957f \u2192 2\u03c0r\uff1a\u8fb9\u6570"
                          "\u8d8a\u591a\uff0c\u8d8a\u50cf\u5706", _ui(0.5))


def pane_three_arms(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Set up our new world` (10.90 s): three spiral arms - 航空 / 航天 / 航海.

    The film's own picture for this line is a three-armed galaxy, and the school's is the same shape
    for a real reason: 三航 is literally the school's own name for its three fields. The labels are
    the school's own (`02_叙事设计.md` §9), and the arms are drawn as a logarithmic spiral sampled at
    terminal cells, so the rotation is a function of `lt` and seeking lands in the same place.
    """
    w, h = x1 - x0, y1 - y0
    if w < 10 or h < 5:
        return
    cx, cy = x0 + w / 2.0, y0 + h / 2.0
    arms = [("\u822a\u7a7a", "ARJ21"), ("\u822a\u5929", "\u5317\u6597"), ("\u822a\u6d77", "\u86df\u9f99")]
    grow = min(1.0, u / 0.75)
    phase = lt * 0.55
    rmax = min(w / 2.4, h * 1.15)
    for a, (label, sub) in enumerate(arms):
        theta0 = a * (2 * math.pi / 3) + phase
        for k in range(1, 40):
            f = k / 39.0
            if f > grow:
                break
            th = theta0 + f * 2.4
            r = rmax * f
            xx = int(round(cx + r * math.cos(th)))
            yy = int(round(cy + r * math.sin(th) * 0.5))
            if x0 <= xx <= x1 and y0 <= yy <= y1:
                ch = "\u00b7" if k % 3 else "\u2022"
                s.put(xx, yy, ch, _mix(ME_TEXT, 0.45 + 0.5 * f))
        # the label rides the arm's head
        f = grow
        th = theta0 + f * 2.4
        r = rmax * f * 0.72
        lx = int(round(cx + r * math.cos(th)))
        ly = int(round(cy + r * math.sin(th) * 0.5))
        if x0 <= lx <= x1 - 4 and y0 <= ly <= y1:
            s.put(lx, ly, label, _mix(ANOM, 0.9))
            if h >= 9:
                s.put(lx, ly + 1, sub, _ui(0.55))
    # ---- the outer field (batch 51, the user: "学校部分某些右侧 panel 的图像周边比较空旷，可以使用装饰
    #      填充，也可以重复多个图形"). Three more arms, interleaved between the three and drawn dimmer and
    #      longer, so the galaxy has the outer structure a three-armed galaxy actually has - and a dust of
    #      stars between them. The six arms are still one figure: the labels ride the three bright ones.
    import school_courses as _CC
    for a in range(3):
        theta0 = a * (2 * math.pi / 3) + phase + math.pi / 3
        for k2 in range(1, 44):
            f2 = k2 / 43.0
            if f2 > min(1.0, grow * 1.2):
                break
            th = theta0 + f2 * 1.8
            r = rmax * 1.22 * f2
            xx = int(round(cx + r * math.cos(th)))
            yy = int(round(cy + r * math.sin(th) * 0.5))
            if x0 <= xx <= x1 and y0 <= yy <= y1 and k2 % 2:
                s.put(xx, yy, "\u00b7", _mix(ME_TEXT, 0.10 + 0.28 * f2))
    _CC.dust(s, x0, y0, x1, y1, t, int(max(20, w * h * 0.05)), seed=7, colour=ME_TEXT, spread=0.5)


def pane_countdown(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`And let's begin the simulation` (12.47 s): 3 - 2 - 1, then the clock starts.

    The film's own `shot_begin_sim` prints a countdown and then `simulation: running`. Same device,
    the school's words: the sim that starts here is the one the whole film is about.

    The digits are drawn *big* and the block fills the box it is given, because of what the density probe
    said about it: three lines centred in an eighteen-row pane left a twelve-row hole, which is the one
    PATCHY verdict left in the film. A countdown that is a big number is also just better than one that is
    a small number with a lot of black around it.
    """
    w, h = x1 - x0, y1 - y0
    if w < 10 or h < 3:
        return
    n = int(u / 0.20)                       # ~0.8 s of countdown, then running
    # `3` had both edges lit on rows 2-3 and no middle or bottom bar, so the countdown opened on a "Π"
    # (batch 31's audit rendered it); a 3 is top bar, right edge, middle bar, right edge, bottom bar.
    digits = {3: ("\u2588\u2588\u2588\u2588", "    \u2588", "\u2588\u2588\u2588\u2588",
                  "    \u2588", "\u2588\u2588\u2588\u2588"),
              2: ("\u2588\u2588\u2588\u2588", "    \u2588", "\u2588\u2588\u2588\u2588",
                  "\u2588   ", "\u2588\u2588\u2588\u2588"),
              1: ("    \u2588", "    \u2588", "    \u2588", "    \u2588", "    \u2588")}
    cy = y0 + max(2, h // 2 - 2)
    if n < 3 and h >= 8:
        glyph = digits[3 - n]
        for i, line in enumerate(glyph):
            s.put(x0 + max(0, (w - 4) // 2), cy + i, line, _mix(ANOM, 0.95))
        s.put(x0 + 1, y0 + h - 2, "simulation starts in", _ui(0.5))
        s.put(x0 + 1, y0 + h - 1, "\u2500" * max(1, w - 2), _ui(0.3))
        return
    if n < 3:
        s.put(x0 + max(0, (w - 5) // 2), cy, ["  3  ", "  2  ", "  1  "][n], _mix(ANOM, 0.95))
        return
    # running: the banner, a timer that is visibly counting, and the flat line at the bottom of the box -
    # spread over the rows rather than stacked in the middle
    s.put(x0 + 1, y0 + 1, "simulation: running", _mix((120, 220, 160), 0.95))
    if h >= 8:
        span = max(1, h - 8)
        s.put(x0 + 1, y0 + 3, f"t = {lt:7.3f} s", _ui(0.7))
        for i in range(span):
            s.put(x0 + 1 + i, y0 + 5 + i, "\u00b7", _mix(ANOM, 0.25 + 0.6 * (i / span)))
    if h >= 5:
        # a flat line: nothing is happening yet, and that is the line's own joke.
        # `y1 - y0 - 1` is a *height*, not a row: used as a row it drew 288 cells outside the pane (the
        # only pane that leaked - batch 31's audit measured it landing inside the feature-bands box on a
        # 44-row window). The row it wants is the pane's own last one.
        s.put(x0 + 1, y1 - 1, "\u2500" * max(1, w - 2), _ui(0.35))


def pane_curriculum(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """The four years, printed a line at a time, with the student's own courses marked.

    The user's correction (2026-10-03): "我们学院并非只有我列的那些专业课，我举的都是印象深或重要的".
    The first version printed exactly the thirteen courses from the brief, which read as *the syllabus* -
    a claim nobody made. This version prints a term's worth per line, marks the courses the brief named
    with `★`, and says in the footer that the stars are the ones worth naming and not the whole list.

    Batch 50 read "各年不止那几门课程" as "add more courses" and invented fourteen for this table - one of
    which duplicated 大三's `马原` as 大二's `马克思主义基本原理` - while replacing four of the user's own
    (`微积分` → `高等数学`, `毛概`/`习概` → `思想道德与法治`/`马克思主义基本原理`). **The list is the user's
    own and is not to be filled in** (batch 53): "课程表里大三已经有马原了，你大二又加了一个马克思主义
    基本原理，删掉，顺便复核一下课程表，去掉你自行加的（比如就业指导）". It is the 34 courses of batch 34/49
    exactly, and the only later change that survives is the one they asked for by name: `信号与线性系统`
    carries a star, because its own pane is one of the sixteen hits.

    What batch 50 got right and keeps: the reveal is a **share of the longest column**, not a fixed `0.10`
    per course, which used to cap a column at ten printed courses and clip the tail of a long one.

    It sits after the gate (136.90-142.00) rather than in the first act, because it is the answer to the
    college the student just chose.
    """
    rows = [
        ("\u5927\u4e00", ["\u2605\u5d4c\u5165\u5f0f\u7535\u5b50\u5fae\u7cfb\u7edf", 
                          "\u2605\u7a0b\u5e8f\u8bbe\u8ba1\u57fa\u7840\uff08C\uff09", 
                          "\u2605\u6570\u636e\u7ed3\u6784", "\u5fae\u79ef\u5206", 
                          "\u7ebf\u6027\u4ee3\u6570", "\u667a\u80fd\u65f6\u4ee3\u7684\u8f6f\u5de5", 
                          "\u519b\u4e8b\u7406\u8bba", "\u79bb\u6563\u6570\u5b66", 
                          "\u5927\u5b66\u7269\u7406"]),
        ("\u5927\u4e8c", ["\u2605\u9762\u5411\u5bf9\u8c61\uff08java\uff09", 
                          "\u2605\u8f6f\u4ef6\u5de5\u7a0b", "\u2605\u8ba1\u7b97\u673a\u7f51\u7edc", 
                          "\u2605\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf", 
                          "\u2605\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406", 
                          "\u2605\u6570\u636e\u5e93\u7cfb\u7edf", "\u6570\u5b66\u5efa\u6a21", 
                          "\u4eba\u5de5\u667a\u80fd\u5bfc\u8bba", "\u6982\u7387\u8bba", 
                          "\u590d\u53d8\u51fd\u6570", "\u8ba1\u7b97\u65b9\u6cd5", "\u6bdb\u6982", 
                          "\u4e60\u6982"]),
        ("\u5927\u4e09", ["\u2605\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406", 
                          "\u2605\u7b97\u6cd5\u8bbe\u8ba1", "\u2605\u8f6f\u4ef6\u6d4b\u8bd5", 
                          "\u2605\u6df1\u5ea6\u5b66\u4e60", "\u2605\u7f16\u8bd1\u539f\u7406", 
                          "\u2605\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6", 
                          "\u2605\u4fe1\u53f7\u4e0e\u7ebf\u6027\u7cfb\u7edf", "\u9a6c\u539f", 
                          "\u5de5\u4e1a\u6a21\u578b", "\u8f6f\u4ef6\u5f00\u53d1\u8bad\u7ec3"]),
        ("\u5927\u56db", ["\u2605\u6bd5\u8bbe", "\u5b9e\u4e60"]),
    ]
    w, h = x1 - x0, y1 - y0
    from school_courses import _clip
    import school_courses as _CC
    AMBER = _CC.AMBER
    # A tall box gets the four years side by side; a short one gets the original line-by-line list. The
    # pane used to print seven lines and stop, which left twenty rows of black in the column it now
    # occupies (it moved here from the first act, where it had eleven rows and fitted).
    if h >= 12 and w >= 64:
        cw = max(14, (w - 2) // 4)
        # The four years are *walked*, one at a time, for as long as the pane is up: the column being
        # read gets a brighter header and an arrow, and one course in it is lit at a time. The pane had
        # a cursor, but only while the columns were still printing - once they had finished it was a
        # still image, which for the one drawing in the film that is a plain list is the wrong answer
        # (`_dev/clock_probe.py` is the check: at full reveal, every pane has to move).
        active = int(t * 0.7) % len(rows)
        # **The reveal is a share of the longest column, not a fixed ten steps** (batch 50). It used to be
        # `u < 0.04 + 0.10 * j + 0.05 * ci`, which caps a column at ten printed courses and does not reach
        # its end until `u = 1.4` - so the tail of a long column never appeared at all, however long the row
        # was on screen (the user: "各年不止那几门课程"). It is a share of the whole list now, and it is
        # still keyed on the **row** index, so the four years print side by side the way they always did.
        longest = max(1, max(len(cs) for _yr, cs in rows))
        for ci, (year, courses) in enumerate(rows):
            cx = x0 + 1 + ci * cw
            s.put(cx, y0, _clip(year + (" >" if ci == active else ""), cw - 1),
                  _mix(ANOM, 0.95 if ci == active else 0.45))
            s.put(cx, y0 + 1, "\u2500" * max(1, cw - 2), _ui(0.25))
            walk = int(t * 3.0) % max(1, len(courses))
            for j, name in enumerate(courses):
                y = y0 + 2 + j
                if y > y1 - 3:
                    break
                reveal = 0.04 + 0.82 * (j / longest)
                if u < reveal:
                    break
                star = name.startswith("\u2605")
                body = name[1:] if star else name
                if star:
                    col = _mix(AMBER, 0.95 if (ci == active and j == walk) else 0.75)
                else:
                    col = _ui(0.75 if (ci == active and j == walk) else 0.5)
                s.put(cx, y, _clip(("\u2605" if star else " ") + body, cw - 1), col)
            if u < reveal:
                if int(t * 2) % 2 == 0:
                    s.put(cx, min(y1 - 3, y0 + 2 + len(courses)), "\u2588", _mix(ME_TEXT, 0.9))
        s.put(x0 + 1, y1 - 1, _clip("\u2605 = \u4f60\u8981\u91cd\u70b9\u8bb0\u7684\uff1b"
                                    "\u5176\u4f59\u662f\u540c\u4e00\u5b66\u671f\u4e00\u8d77\u4e0a\u7684",
                                    w - 2), _mix(ME_TEXT, 0.75))
        s.put(x0 + 1, y1, _clip(f"\u56db\u5e74\u7684\u8bfe\u8868\uff1a\u5171 "
                                f"{sum(len(cs) for _yr, cs in rows)} \u95e8\uff08"
                                f"\u53ea\u5217\u4e86\u8fd9\u4e9b\uff09", w - 2), _ui(0.5))
        return
    flat = [(yr, nm) for yr, cs in rows for nm in cs]
    n = min(len(flat), max(1, h - 2))
    for i in range(n):
        at = 0.02 + 0.88 * (i / max(1, len(flat) - 1))
        if u < at:
            break
        yr, nm = flat[i]
        s.put(x0 + 1, y0 + i, yr, _mix(ANOM, 0.85))
        s.put(x0 + 5, y0 + i, _clip(nm, max(0, w - 6)), _ui(0.85))
    # the cursor stops on the last line printed: nothing here loops
    if n:
        yy = y0 + min(n, len(flat)) - 1
        if int(t * 2) % 2 == 0:
            s.put(x1 - 2, yy, "\u2588", _mix(ME_TEXT, 0.9))


def pane_point_set(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`If I'm a set of point` (29.28 s): the IF/THEN device, and the points it will become.

    Batch 1 rule R3: the conditional's two-cell frame is the film's one device for the whole
    `If I'm X -> Then Y` family, and it is introduced here. The left cell fills on `If`, the right
    cell stays **empty** until the next line's `Then` - that emptiness is the design, not an
    unfinished panel.
    """
    w, h = x1 - x0, y1 - y0
    if w < 14 or h < 4:
        return
    half = max(6, (w - 3) // 2)
    # (half - 2) made the top border one cell shorter than the bottom one (95 against 96)
    s.put(x0, y0, "\u250c" + "\u2500" * (half - 1) + "\u252c" + "\u2500" * (w - half - 2) + "\u2510",
          _mix(ME_TEXT, 0.7))
    s.put(x0 + 2, y0, "IF", _mix(ME_TEXT, 0.95))
    s.put(x0 + half + 2, y0, "THEN", _ui(0.45))
    s.put(x0, y0 + 1, "\u2502" + " " * (w - 2) + "\u2502", _mix(ME_TEXT, 0.7))
    s.put(x0 + 2, y0 + 1, "a set of point"[: max(0, half - 4)], _ui(0.9))
    if h >= 4:
        s.put(x0, y0 + 2, "\u2514" + "\u2500" * (w - 2) + "\u2518", _mix(ME_TEXT, 0.7))
    # scattered points below: the line says "point", not "grid", and a grid would say the wrong thing
    rnd = random.Random(2928)
    for k in range(max(4, (h - 3) * 6)):
        px = x0 + 1 + rnd.randrange(0, max(1, w - 2))
        py = y0 + 3 + rnd.randrange(0, max(1, h - 3))
        if py <= y1:
            # ...and each point breathes on the song clock: a point *set* that never changes is a still
            # picture, and this pane's only motion used to come from the motif band under it
            s.put(px, py, "\u00b7", _mix(ME_TEXT, 0.30 + 0.55 * min(1.0, u / 0.6)
                                          + 0.15 * math.sin(t * 2.0 + px * 0.7)))


PANE_BY_NAME = {
    "pane_power_on": pane_power_on,
    "pane_protection": pane_protection,
    "pane_pieces": pane_pieces,
    "pane_class": pane_class,
    "pane_parameters": pane_parameters,
    "pane_polyhedra": pane_polyhedra,
    "pane_three_arms": pane_three_arms,
    "pane_countdown": pane_countdown,
    "pane_curriculum": pane_curriculum,
    "pane_point_set": pane_point_set,
}
# the closing panes and the landmarks are added at the *bottom* of this file (`PANE_BY_NAME.update`):
# a dict literal here can only name functions that already exist, and that is a rule worth keeping
# rather than working around by moving the definitions above a growing table.


def pane_converge(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`all the execution` -> `only execution` (02:44.07-02:47.75): twelve drawings into one class.

    `02b` §4.3 calls this the core action of the software-engineering courseload, and it is also the
    song's own figure: "give them all" arrives, and what is left is "your only". The diagrams are laid
    out four to a row, each drawn small enough to read as its own notation, and then they collapse into a
    single UML class in the middle. The collapse is on `u`, so seeking into the pane lands mid-collapse in
    the same place playing into it would.

    **Twelve, not seven** (batch 50, the user: "软工不止7个图"). Seven was the set the chat window used to
    name, and the pane and the words had to agree (batch 31's audit counted the boxes against the words in
    one frame), so both were extended together: the twelve are the deliverables of the four documents the
    course actually produces - 需求规格 (需求, 数据字典, 用例图), 概要设计 (DFD, ER, 结构图, 接口),
    详细设计 (盒图, 判定表, 活动图, 状态图, 时序图). The class they converge into is unchanged.
    """
    import school_courses as _C
    w, h = x1 - x0, y1 - y0
    if w < 16 or h < 5:
        return
    titles = ["\u9700\u6c42", "\u6570\u636e\u5b57\u5178", "\u7528\u4f8b\u56fe", "DFD",
              "ER", "\u7ed3\u6784\u56fe", "\u63a5\u53e3", "\u76d2\u56fe",
              "\u5224\u5b9a\u8868", "\u6d3b\u52a8\u56fe", "\u72b6\u6001\u56fe", "\u65f6\u5e8f\u56fe"]
    cols = 4
    rows = (len(titles) + cols - 1) // cols
    collapse = max(0.0, min(1.0, (u - 0.55) / 0.40))       # 0 while the seven are apart, 1 when merged
    cw = max(6, (w - 4) // cols)
    ch = max(2, (h - (rows - 1)) // rows)
    # the one class the seven become: computed *before* the loop, because the seven have to be able to
    # aim at it. It is drawn from the start of the collapse and its weight rises with `collapse`, so what
    # the audience sees is seven drawings *contracting into* a class.
    #
    # The old version could not show that, and the maths audit said so: it moved each box to the middle
    # while keeping it its full size, so near the end seven full-size rectangles overlapped into a
    # tangle; then at `collapse >= 1.0` it dropped all seven with a `break`, and *afterwards* drew the
    # class in the same place. There was therefore no frame in which a box and the class coexisted - the
    # audience saw a pile-up, a cut to empty, and a new box appearing. "收敛/归约" is the single most
    # important action in this pane and it was two fades.
    tbw = min(w - 4, 34)
    tbh = min(h - 2, 6)
    tbx, tby = x0 + (w - tbw) // 2, y0 + (h - tbh) // 2
    for i, name in enumerate(titles):
        r, c = divmod(i, cols)
        bx = x0 + 1 + c * (cw + 1)
        by = y0 + r * (ch + 1)
        bw_i, bh_i = cw, ch
        if collapse > 0:
            # **the rect interpolates, not just the position.** Width and height travel toward the class
            # rect along with the corner, so at `collapse == 1` all seven are *coincident with* the class
            # box - one rectangle, drawn seven times over itself and therefore idempotent - rather than
            # seven full-size rectangles stacked in the middle.
            bx = int(bx + (tbx - bx) * collapse)
            by = int(by + (tby - by) * collapse)
            bw_i = max(3, int(cw + (tbw - cw) * collapse))
            bh_i = max(2, int(ch + (tbh - ch) * collapse))
        if not (x0 <= bx and bx + bw_i <= x1 and y0 <= by and by + bh_i <= y1):
            continue
        # the seven give up their own weight as they give up their own shape
        lv = 0.5 * (1.0 - collapse) + 0.95 * collapse
        for xx in range(bx, bx + bw_i):
            s.put(xx, by, _C.BOX_H if xx not in (bx, bx + bw_i - 1)
                  else ("\u250c" if xx == bx else "\u2510"), _C._mix(_C.BLUE if collapse < 1.0
                                                                    else _C.AMBER, lv))
            s.put(xx, by + bh_i - 1, _C.BOX_H if xx not in (bx, bx + bw_i - 1)
                  else ("\u2514" if xx == bx else "\u2518"), _C._mix(_C.BLUE if collapse < 1.0
                                                                    else _C.AMBER, lv))
        for yy in range(by + 1, by + bh_i - 1):
            s.put(bx, yy, _C.BOX_V, _C._mix(_C.BLUE if collapse < 1.0 else _C.AMBER, lv))
            s.put(bx + bw_i - 1, yy, _C.BOX_V, _C._mix(_C.BLUE if collapse < 1.0 else _C.AMBER, lv))
        if collapse < 0.78:
            # the labels and the notation go last, not first. They have to survive long enough to be seen
            # *inside* the class that is forming around them - otherwise the collapse is again "everything
            # vanishes, then a box appears", which is what it was. The batch-37 probe measured the first
            # attempt at this fix: labels dropped at 0.45 while the class only arrived at 0.72, so there
            # were **zero** frames in which a source label and the target class were both on screen.
            s.put(bx + 2, by, f" {name} ", _C._ui(0.7))
            dots = ("\u00b7" * 16)[int(t * 3.0 + i * 2) % 8:][: max(0, bw_i - 4)]
            s.put(bx + 2, by + 1, dots, _C._ui(0.4))
    # the class's own interior, once the seven are on top of it: the fields are the reduction's result
    if collapse > 0.72:
        lit = _C._mix(_C.AMBER, 0.95)
        s.put(tbx + 2, tby, " class ", lit)
        if collapse > 0.85:
            s.put(tbx + 2, tby + 1, "+ giver", _C._ui(0.8 * collapse))
            s.put(tbx + 2, tby + 2, "- taker", _C._ui(0.8 * collapse))
            s.put(tbx + 2, tby + 3, "give()", _C._mix(_C.AMBER, 0.7 * collapse))


def pane_sw_project(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """软件项目管理, in the closing chapter: the agile manifesto, a sprint, and a working task board.

    Batch 50's instruction moved this subject here from the twelve hits - "这部分替换为我给你说的软件项目
    管理的内容（scrum、任务看板）" - because the closing chapter is literally named 软工与爱, and because
    what the course is *for* is the thing the song's last verse is about: a plan that survives contact with
    a week. The hit that used to carry it now carries 信号与线性系统.

    Three parts, left to right, and they are the three things a project actually has:

      * **敏捷宣言**: the four value pairs, each with the left-hand side heavier - which is what `>` means
        and is the whole content of the manifesto (the right column is not worthless, it is worth less);
      * **一个冲刺**: the four ceremonies in order, with the one the clock is in lit, and the sprint's
        burndown - remaining work stepping down to zero - underneath;
      * **任务看板**: three columns, cards walking 待办 → 进行中 → 完成. Unlike `pane_backlog`, whose Done
        column can never fill because "trapped" means exactly that, this board *finishes*: a course about
        project management that cannot ship is not showing project management.
    """
    import school_courses as _C
    # The heading names both halves of the course (batch 51: "软件项目管理任务看板那，抬头课程名改为
    # '软件项目管理/软件开发综合训练'"): they are one line of the college's 培养方案 - the theory and the
    # course-long project that runs beside it - and this pane draws both of them, a sprint's ceremonies and
    # the board the project is worked on.
    k = _kit(s, x0, y0, x1, y1, 0, "\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406 / \u8f6f\u4ef6\u5f00\u53d1"
                                    "\u7efc\u5408\u8bad\u7ec3")
    if k is None or k.bw < 40 or k.bh < 8:
        return
    k.section(k.by0, "\u654f\u6377 \u00b7 \u51b2\u523a \u00b7 \u770b\u677f", 0.28)
    body = k.sub(k.bx0, k.by0 + 1, k.bx1, k.by1)
    # `columns` refuses rather than squeezing (its own docstring: "a caller that said this drawing needs
    # thirty cells is telling the truth"), and `layout_probe` fails a pane that *asks* for a layout it does
    # not get - so the ask is guarded, and a narrow pane draws the board alone instead of nothing.
    cols = body.columns(2, mins=[32, 26], weights=[3, 4]) if body.bw >= 60 else []
    if cols:
        (lx0, lx1), (rx0, rx1) = cols
    else:
        lx0 = lx1 = None
        rx0, rx1 = body.bx0, body.bx1
    # ---------------------------------------------------------------- the manifesto, and the sprint
    values = (("\u4e2a\u4f53\u4e0e\u4ea4\u4e92", "\u6d41\u7a0b\u4e0e\u5de5\u5177"),
              ("\u53ef\u7528\u8f6f\u4ef6", "\u8be6\u5c3d\u6587\u6863"),
              ("\u5ba2\u6237\u5408\u4f5c", "\u5408\u540c\u8c08\u5224"),
              ("\u54cd\u5e94\u53d8\u5316", "\u9075\u5faa\u8ba1\u5212"))
    if lx0 is not None:
        body.put(lx0, body.by0, "\u654f\u6377\u5ba3\u8a00", _mix(_C.AMBER, 0.9))
        for i, (left, right) in enumerate(values):
            y = body.by0 + 1 + i
            if y > body.by1 - 4:
                break
            on = i == int(t * 0.8) % len(values)
            body.put(lx0, y, left, _mix(_C.AMBER, 0.95 if on else 0.7))
            body.put(lx0 + 10, y, ">", _ui(0.5))
            body.put(lx0 + 12, y, right, _ui(0.35))
        # the sprint: four ceremonies, the current one lit, and the burndown under them
        sy = min(body.by1 - 1, body.by0 + 1 + len(values) + 1)
        ceremonies = ("\u8ba1\u5212", "\u5f00\u53d1", "\u8bc4\u5ba1", "\u56de\u987e")
        phase = int(min(0.999, lt / max(1e-6, dur)) * len(ceremonies))
        body.put(lx0, sy, "sprint 3", _ui(0.45))
        for i, name in enumerate(ceremonies):
            xx = lx0 + 10 + i * 8
            if xx + 6 > lx1:
                break
            body.put(xx, sy, f"[{name}]" if i == phase else f" {name} ",
                     _mix(_C.GREEN, 0.95) if i == phase else _ui(0.45))
            if i < len(ceremonies) - 1 and xx + 7 <= lx1:
                body.put(xx + 6, sy, "\u2192", _ui(0.35))
        if sy + 2 <= body.by1:
            w = max(6, lx1 - lx0 - 2)
            for c in range(w):
                frac = c / max(1, w - 1)
                remain = 1.0 - frac
                y = sy + 2 + int((1.0 - remain) * 3)
                body.put(lx0 + c, min(body.by1, y), "\u2588",
                         _mix(_C.BLUE, 0.8 if frac <= lt / max(1e-6, dur) else 0.22))
            body.put(lx0, body.by1, "\u71c3\u5c3d\uff1a\u5269\u4e0b\u7684\u5de5\u4f5c\u9010\u6b65\u5230 0",
                     _ui(0.5))
    # ---------------------------------------------------------------- the task board, which finishes
    board = (("\u5f85\u529e", 0.85), ("\u8fdb\u884c\u4e2d", 0.45), ("\u5b8c\u6210", 0.0))
    cw = max(6, (rx1 - rx0 + 1) // 3)
    for i, (name, _share) in enumerate(board):
        bx = rx0 + i * cw
        if bx + 4 > rx1:
            break
        for xx in range(bx, min(bx + cw - 1, rx1)):
            body.put(xx, body.by0, _C.BOX_H, _mix(_C.BLUE, 0.45))
            body.put(xx, body.by1, _C.BOX_H, _mix(_C.BLUE, 0.45))
        body.put(bx, body.by0, "\u250c", _mix(_C.BLUE, 0.6))
        body.put(min(bx + cw - 2, rx1), body.by0, "\u2510", _mix(_C.BLUE, 0.6))
        body.put(bx + 1, body.by0, f" {name} ", _mix(_C.GREEN if i == 2 else _C.BLUE, 0.9))
    # six cards; card `c` is done once the sprint has passed its own two-thirds, and the cards that are
    # still moving are the ones in the middle column - the board is a clock, not a picture
    total = 6
    done = int(min(1.0, lt / max(1e-6, dur * 0.9)) * total)
    moving = int(min(1.0, lt / max(1e-6, dur * 0.6)) * total)
    for c in range(total):
        col = 2 if c < done else (1 if c < max(done, moving) else 0)
        row_in = (c if col == 2 else c - done if col == 1 else c - moving)
        cx = rx0 + col * cw + 1
        cy = body.by0 + 2 + max(0, row_in) * 2
        if cy + 1 > body.by1 - 1 or cx + 5 > rx1:
            continue
        body.put(cx, cy, "\u25aa", _mix(_C.AMBER if col < 2 else _C.GREEN, 0.9))
        body.put(cx + 2, cy, ("\u9700\u6c42", "\u8bbe\u8ba1", "\u7f16\u7801", "\u6d4b\u8bd5",
                              "\u8bc4\u5ba1", "\u53d1\u5e03")[c % 6][: max(2, cw - 5)],
                 _ui(0.7))


def pane_backlog(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Though we are trapped` (02:49.61-02:56.96): a Scrum board whose Done column never fills.

    `02b` §4.4. Three columns and cards that are pushed from the right back to the left; the one thing
    that has to be visible is that `Done` stays empty, because that is what "trapped" means in a Sprint
    and the song means it too.
    """
    import school_courses as _C
    w, h = x1 - x0, y1 - y0
    if w < 18 or h < 4:
        return
    cols = [("\u5f85\u529e", 0.18), ("\u8fdb\u884c\u4e2d", 0.42), ("\u5b8c\u6210", 0.0)]
    cw = max(6, (w - 2) // 3)
    for i, (name, fill) in enumerate(cols):
        bx = x0 + i * (cw + 1)
        for xx in range(bx, min(bx + cw, x1)):
            s.put(xx, y0, _C.BOX_H, _C._mix(_C.BLUE, 0.45))
            if h > 2:
                s.put(xx, y1, _C.BOX_H, _C._mix(_C.BLUE, 0.45))
        s.put(bx, y0, "\u250c", _C._mix(_C.BLUE, 0.6))
        s.put(min(bx + cw - 1, x1), y0, "\u2510", _C._mix(_C.BLUE, 0.6))
        s.put(bx + 2, y0, f" {name} ", _C._ui(0.75))
        # The count has to *move*: `1 + int(fill * 4 * (0.6 + 0.4|sin|))` floors to a constant for both
        # 0.18 and 0.42, so the board never changed - `clock_probe` called the whole pane STILL and the
        # audit counted a constant three cards over sixty samples.
        n = 1 + int(round(fill * 6 * (0.55 + 0.45 * abs(math.sin(lt * 1.3 + i)))))
        if i == 2:
            # Done never fills: one ghost card at most, and it is on its way back
            n = 0
        for c in range(n):
            yy = y0 + 2 + c * 2
            if yy + 1 > y1 - 1:
                break
            label = "\u25aa \u9700\u6c42"
            s.put(bx + 1, yy, label[: cw - 2], _C._mix(_C.BLUE if i == 1 else _C.DIM, 0.8))
        if i == 2 and h > 3:
            s.put(bx + 2, y0 + 2, "\u2014", _C._ui(0.3))
    # ...and the card on its way back: it walks right-to-left across the board, one lap per 3.4 s, which
    # is the gesture the lyric is about (the docstring has promised it since batch 1)
    if h > 4:
        f = (lt % 3.4) / 3.4
        s.put(int(x0 + 2 + (w - 8) * (1.0 - f)), y1 - 2,
              "\u25aa \u9700\u6c42"[: max(4, cw - 2)], _C._mix(_C.RED, 0.55 + 0.35 * f))
    if h > 3:
        s.put(x0, y1 - 1, "\u5361\u7247\u4e00\u76f4\u88ab\u63a8\u56de\u53bb", _C._mix(_C.RED, 0.8))


def pane_knowledge(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`I've studied how to properly love` (02:56.96-03:04.33): the three years as one curve.

    `02b` §4.5: not a course list. Five points on an ability curve, one per thing actually learned
    (C, Java, OpenEuler, PostgreSQL, backpropagation), with a tiny glyph beside each. The curve is drawn
    left to right on `u`, so the song's own progress and the drawing's are the same thing.
    """
    import school_courses as _C
    w, h = x1 - x0, y1 - y0
    if w < 20 or h < 5:
        return
    pts = [("C", 0.06), ("Java", 0.28), ("OpenEuler", 0.50), ("PGSQL", 0.70), ("\u53cd\u5411\u4f20\u64ad", 0.90)]
    glyphs = ["{ }", "\u25a1", ">_", "\u2261", "grad"]
    # the curve: an ease that starts slow and accelerates, which is what learning something looks like
    n = max(10, w - 4)
    for c in range(n):
        f = c / max(1, n - 1)
        v = f ** 1.6
        yy = y1 - 1 - int((h - 3) * v)
        if f > u:
            break
        s.put(x0 + 2 + c, max(y0, yy), "\u00b7", _C._mix(_C.BLUE, 0.75))
    for i, (name, at) in enumerate(pts):
        if u < at:
            continue
        c = int((n - 1) * at)
        yy = y1 - 1 - int((h - 3) * (at ** 1.6))
        s.put(x0 + 2 + c, max(y0, yy), "\u25cf", _C._mix(_C.AMBER, 0.95))
        s.put(x0 + 2 + c - 1, max(y0, yy) - 1, glyphs[i], _C._mix(_C.GREEN, 0.8))
        if h > 6:
            s.put(x0 + 2 + c - len(name) // 2, min(y1, yy + 1), name, _C._ui(0.6))
    # a marker walking the curve on the song clock: the five stars are the syllabus, this is the term
    # in progress - and without it the pane stops the moment its reveal ends
    fm = (t * 0.12) % 1.0
    s.put(x0 + 2 + int((n - 1) * fm), max(y0, y1 - 1 - int((h - 3) * (fm ** 1.6))),
          ">", _C._mix(_C.RED, 0.9))
    s.put(x0, y0, "\u5927\u4e00 \u2192 \u5927\u4e09", _C._ui(0.5))


def pane_love_class(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`the algebraic expression of lo-o-ove` (03:04.33-03:13.46): the class, and **one big heart**.

    `02b` §4.6 wants the class the previous pane collapsed to, magnified to fill the column, and
    **nothing moving** - "every other pane in this bar animates, and this one does not, because the
    answer has been written". So this is the only pane in the variant with no `lt` in it at all, and
    the `u` reveal is a typewriter rather than an animation.

    It used to be that listing *plus two motif bands* underneath it - the Fourier epicycles and a 3x3
    contact sheet of nine heart equations. The user's note this batch is "有些演出太复杂导致图像精细度不够，
    可以进行简化，重点放在细节刻画（比如心形曲线可以只画1个大的）", and this pane was the example: in the
    rows that were left, each of the nine hearts got three and the equations printed over each other. The
    listing keeps its four lines - the expression is what the lyric names - and everything below it is now
    one heart at the size the box can carry, drawn by `school_motifs.hearts9` (which is the same curve,
    rewritten for a whole box rather than a band).
    """
    lines = [
        # Java, not Python: this project's programming course is 程序设计基础（C 语言）+ 面向对象（java）
        # - there is no Python course in the curriculum (the user's note, batch 34)
        "public class Love {",
        "    Person giver;",
        "    Person taker;",
        "    public void give() { }",
    ]
    import school_courses as _C
    w, h = x1 - x0, y1 - y0
    if w < 12 or h < 3:
        return
    # The kit is created **first** and the class is drawn under its header rule. `_Kit.__init__` writes a
    # progress rule on `y0 + 1`; the class used to be drawn there and the kit made afterwards, so the rule
    # painted over `class Love:` and the pane's own first line never reached the screen (batch 31's audit:
    # "the pane erases its own first line").
    k = _kit(s, x0, y0, x1, y1, 0, "")
    # the box is the lines that fit, not all of them: a short pane gets a shorter class rather than its
    # bottom line written outside it (caught by the probe at 60x7 and 34x5)
    fit = max(1, min(len(lines), max(1, (h - 3) // 2)))
    lines = lines[:fit]
    bx, by = x0 + 1, y0 + 2
    bw = min(w - 2, 46)
    for xx in range(bx, bx + bw):
        s.put(xx, by, _C.BOX_H, _C._mix(_C.AMBER, 0.8))
    revealed = int(len(lines) * min(1.0, u * 1.25))
    for i, line in enumerate(lines):
        if i >= revealed:
            break
        s.put(bx + 2, by + 1 + i, line[: max(0, bw - 4)],
              _C._mix(_C.AMBER, 0.95) if i == 0 else _C._ui(0.85))
    s.put(bx + 2, by, " Love ", _C._mix(_C.AMBER, 0.95))
    # ...and the heart, in whatever is left: one curve, as big as the box allows
    top = by + len(lines) + 2
    if y1 - top >= 5:
        import school_motifs as _M
        _M.hearts9(k.sub(k.bx0, top, k.bx1, y1), t)


# --------------------------------------------------------------- the campus landmarks
#
# `02b_图像对位与可视化表达.md` §3 pins four campus works to four specific moments, and each of these
# panes is that pinning. They are drawn through `school_courses._Kit` rather than freehand so that a
# photograph and a diagram still arrive in the same frame: the title row, the progress rule and the
# letterboxing are what stop a characterised sculpture reading as a picture someone pasted in.

_CA = 2.1                       # one terminal cell is this many times taller than it is wide


def _landmark(name: str, s, x0: int, y0: int, x1: int, y1: int, u: float, title: str,
              caption: str = "", dim: float = 1.0, scale: float = 1.0, max_rows: int | None = None,
              phase: float = 0.0):
    """Draw one landmark centred in the pane, with its title above it and a caption below.

    Returns the kit so a caller can add its own animation on top (the star between the two hands,
    the white sweep over the sword) - the landmark itself never animates, because these are works of
    art and the one thing that would cheapen them is moving them. `phase` is the exception: it is the
    pane's clock, for a route whose *medium* moves rather than its subject (the binary digits settle).
    """
    from school_courses import _Kit, _mix, _ui, BLUE
    import school_courses as _C
    import school_sculpture as SC
    k = _Kit(s, x0, y0, x1, y1, title, 0, 0, u)
    if not SC.has(name):
        k.put(k.bx0, k.by0, f"({name}: asset missing)", _mix(RED, 0.8))
        return k, 0, 0
    rows = k.bh - 2
    if max_rows:
        rows = min(rows, max_rows)
    # The columns are derived from the *source image's* own aspect, not from the pane. Filling the
    # pane's width instead made `_fit` centre-crop a 1080x672 photograph down to a 118x11 letterbox -
    # about 160 pixels of a 672-pixel-tall image, so 对话 arrived as a horizontal sliver of two wrists
    # with the star cropped out. That was caught by looking at the frame, and it is the same failure
    # `her_glyphs.fit` documents for the whale: a wide pane does not want a wide crop of a tall thing.
    src = SC.source(name)
    aspect = (src.width / src.height) if src else 1.0
    # `CELL_ASPECT`, not 2: a terminal cell is 2.1 times taller than it is wide, so a plate sized with a
    # 2 here is 5 % too wide for its picture and `_fit` trims the difference off both sides. On 何尊 that
    # is the two flanges - the parts that make it a vessel rather than a pot - and the stroke count at
    # 62x36 came out 157 against 217 at the aspect that fits. The two numbers have to be the same one.
    rows = max(2, min(rows, int(k.bw / (aspect * _CA)) if aspect > 0 else rows))
    cols = max(6, min(k.bw, int(round(rows * _CA * aspect))))
    cols = max(6, min(cols, k.bw))
    ox = k.bx0 + max(0, (k.bw - cols) // 2)
    oy = k.by0 + max(0, (k.bh - 1 - rows) // 2)
    if name in SC.BANNER_FOR:
        # the supplied lettering instead of the work itself - see `school_sculpture.BANNER`
        got = SC.banner_cells(SC.BANNER_FOR[name], k.bw, k.bh)
        if got:
            cells, cw, ch = got
            for r in range(min(ch, k.bh)):
                for c in range(min(cw, k.bw)):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(k.bx0 + c, k.by0 + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
    elif name in SC.HTML_ART:
        # the page the user drew the vessel as, as supplied: `参考及想法/何尊.html`, 100x52 cells of
        # coloured binary digits, scaled when the pane is smaller than that.
        got = SC.html_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            k.blit(cells, ox, oy, BLUE, dim)
    elif name in SC.DIGITS:
        # the picture as binary digits, one per cell: `参考及想法/何尊.html`'s rule, on the pane's clock.
        # Drawn in the aspect-fitted `cols`x`rows`, not the whole box: the vessel is a tall drawing and a
        # 95x33 pane wants a 64x31 plate, so filling the box made `_fit` crop the mouth and the base off -
        # which is most of what makes it a vessel.
        got = SC.digit_cells(name, cols, rows, phase=phase)
        if got:
            cells, cw, ch = got
            k.blit(cells, ox, oy, BLUE, dim)
    elif name in SC.SILHOUETTE:
        # a solid shape: the picture's alpha, one character, with its own luminance as the tone. For a
        # monument in white on white this is the only one of the three routes that reads - see
        # `school_sculpture.SILHOUETTE`.
        got = SC.silhouette_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            k.blit(cells, ox, oy, BLUE, dim)
    elif name in SC.LINE:
        # a drawing of *lines*: one glyph per cell a stroke passes through and nothing anywhere else,
        # which is the only route that works for the vector 何尊 and for 为国铸剑's white-on-white
        # sculpture. `stroke_cells` explains why the older glyph route cannot do it.
        got = SC.stroke_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            k.blit(cells, ox, oy, BLUE, dim)
    elif name in SC.GLYPH:
        got = SC.glyph_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            k.blit(cells, ox, oy, BLUE, dim)
    else:
        got = SC.halfblock(name, cols, rows)
        if got:
            (block, colour), cw, ch = got
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(cw):
                    top, bot = block[r][c]
                    if top is None and bot is None:
                        continue
                    ink = colour[r][c] or (196, 208, 228)
                    if top is not None:
                        k.put(ox + c, oy + r, "\u2580", _mix(ink, dim), 1.0)
                    elif bot is not None:
                        # `▄` and the full `dim`: this was `SHADE[1]` (`░`, a quarter-covered *medium
                        # grey*) at 0.7 brightness, so the lower edge of every plate in this path came
                        # out washed out - and the lower edge is most of a silhouette's outline.
                        # (Batch 35; the same fix as `school_fx.sprite`'s lower-half case.)
                        k.put(ox + c, oy + r, "\u2584", _mix(ink, dim), 1.0)
    if caption and k.by1 >= oy + rows:
        k.put(k.bx0, k.by1, caption, _ui(0.55))
    return k, ox, oy


def _sparkle(k, x: int, y: int, colour, centre: float = 1.0) -> None:
    """A four-point star of five cells: `·` above, below and either side of a `*`.

    **A glyph-safety fix, not a style choice.** This mark used to be `* * *` (U+2727 U+2726 U+2727) in
    `pane_landmark_dialogue`, and **neither font the exporter has carries those codepoints** - checked
    against `consola.ttf` and `msyh.ttc` with fontTools, and visible as two `.notdef` boxes in the
    rendered frame at 01:24.60 (`_dev/out/b50/crop_dialogue_star.png`). A terminal font is a third font
    this project cannot check, so the rule is the conservative one: build the mark out of `*` and `·`,
    which every monospace face has. `centre` scales the middle cell only, so the sparkle can twinkle by
    brightness without moving.
    """
    k.put(x, y - 1, "\u00b7", _mix(colour, 0.55))
    k.put(x - 1, y, "\u00b7", _mix(colour, 0.55))
    k.put(x, y, "*", _mix(colour, centre))
    k.put(x + 1, y, "\u00b7", _mix(colour, 0.55))
    k.put(x, y + 1, "\u00b7", _mix(colour, 0.55))


def pane_landmark_dialogue(s, x0, y0, x1, y1, t, lt, dur, u, phase=None, max_phase=2) -> None:
    """`对话` - the machine hand and the human hand, not yet touching.

    Three lyric lines use this one work and each asks for a different crop of it: `unite` shows both
    hands approaching, `deeply` shows the star between them, and `only God` shows the star alone with
    the hands gone.

    **The third act lives on its own line now.** The three used to be phases of a single row, chosen by
    how far into that row the clock was (`lt < 1.2`, `< 2.4`), so the whole work played across
    54.74-60.57 - which put "只剩那颗星" under `If I can, if I can` at ~57 s, while `02b §3.3` pins it to
    `If I'm the only God`. The user's ruling: *the third act belongs at 84.60*. So the row keeps acts 1
    and 2 (`max_phase=1` from the schedule) and act 3 is its own row on its own lyric, selected by
    `phase=2` - the same mechanism `pane_memory` uses to be six drawings: the schedule says which one,
    rather than the drawing guessing from the clock.

    **No caption on it** (batch 49, the user: "对话雕塑…不要附近文字"). The phase titles and captions used
    to name the act; the crop already does. **The header is back** though (batch 55: "右侧 panel 出现对话
    雕塑时，加上抬头'对话'"): a one-word title on the pane's own header row is not a caption under the
    picture - it is what every other pane in the column has, and without it this one pane was the only
    drawing in the film with an unlabelled box. The `* * *` mark between the hands stays - it is the star
    the pane is about, not a label for it.
    """
    import school_courses as _C
    if phase is None:
        phase = 0 if lt < 1.2 else (1 if lt < 2.4 else 2)
    phase = max(0, min(int(phase), int(max_phase)))
    k, ox, oy = _landmark("dialogue", s, x0, y0, x1, y1, u, "\u5bf9\u8bdd", "",
                          dim=1.0 if phase < 2 else 0.35)
    # the star: the one thing in this pane that moves, and it pulses on the song's beat. Drawn from `*`
    # and `·` rather than `*`/`*`: see `_sparkle`.
    if phase >= 1:
        cx = k.bx0 + k.bw // 2
        cy = max(k.by0 + 1, oy - 2)
        pulse = 0.55 + 0.45 * abs(math.sin(lt * 3.2))
        _sparkle(k, cx, cy, _C.AMBER, centre=pulse)


def pane_landmark_sword(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`为国铸剑` - the figure holding the sword overhead.

    Used twice in the film with opposite meanings: at `Challenging your God` as the accusation, and
    over the twelve "Execution" hits as the thing being executed. The pane does not know which it is -
    it draws the work and a white sweep passes over it once per shot, which reads as a blade being
    drawn either way.

    **No words on it** (batch 49, the user: "铸剑雕塑…不要附近文字"): the pane used to print `为国铸剑`
    above the plate and `举剑的不是神` under it. The plate is the 为国铸剑 sculpture, and a title saying so
    is the third thing on screen saying what the picture already is.
    """
    k, ox, oy = _landmark("sword", s, x0, y0, x1, y1, u, "", "")
    # The sweep is on the pane's own clock, not on the reveal: on `u` it crosses the plate once, in the
    # last frame of the slot, and the pane - a photograph - is then still for the other eleven seconds of
    # it. On `lt` the blade is drawn again and again, which is what the plate is of.
    sweep = int(k.bw * ((lt * 0.35) % 1.0))
    if 0 < sweep < k.bw:
        for r in range(max(0, oy), min(k.by1, oy + k.bh) + 1):
            k.put(k.bx0 + sweep, r, "\u2502", _mix((255, 255, 255), 0.20))


def pane_landmark_hezun(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`何尊` - the vessel, as binary digits, because that is what the user drew it as.

    Two lines use it and they use different parts of it: `Fill in my data parameters` wants the
    inscription (the earliest surviving 中国), and the 定义 line wants the taotie pattern as a frame.
    The pane draws the vessel and captions it with the one fact that makes it belong here.
    """
    k, ox, oy = _landmark("he_zun", s, x0, y0, x1, y1, u, "\u4f55\u5c0a",
                          "\u201c\u5b85\u5179\u4e2d\u56fd\u201d \u00b7 \u94ed\u6587\u91cc\u6700\u65e9\u7684"
                          "\u4e2d\u56fd\u4e8c\u5b57", dim=0.9, phase=lt)
    # The vessel is a picture of a drawing, so its clock has to be the *light*: a highlight row walks
    # down it on the song clock. `phase=lt` has been passed in since batch 1 and never honoured - the
    # HTML-art route has no phase - so the pane used to freeze at u=1 (batch 31's audit).
    hy = k.by0 + int((t * 3.0) % max(1, k.bh))
    for xx in range(k.bx0, min(k.bx1 + 1, s.cols)):
        ch, fg, _bg = s.buf[hy][xx]
        if ch.strip():
            s.put(xx, hy, ch, tuple(min(255, int(c * 1.45)) for c in fg))
    # **The two captions were drawn on top of the vessel** (batch 50, the user: "何尊的较小的字符画需要优化
    # 一下"). The plate is aspect-fitted and centred and at pane size it fills the box, so `by0+1`/`by0+2`
    # are *inside* the drawing: `origin = "宅兹中国"` sat across the mouth of the vessel and the vessel's own
    # digits ran through it, so neither could be read. There is exactly one free row - `y0+1`, between the
    # pane's title rule and the plate's top - and one line fits the two facts, so the caption moved there
    # instead of taking a bite out of the drawing.
    if k.bw > 46 and k.by0 >= y0 + 2:
        import school_courses as _C
        s.put(k.bx0 + 2, y0 + 1,
              _C._clip("origin = \"\u5b85\u5179\u4e2d\u56fd\"  \u00b7  \u4f55\u5c0a\u94ed\u6587\uff0c\u7ea6"
                       "\u516c\u5143\u524d 11 \u4e16\u7eaa\uff08\u5468\u6210\u738b\u4e94\u5e74\uff09",
                       max(0, k.bw - 3)),
              _mix(_C.AMBER, 0.85))


def _kit(s, x0: int, y0: int, x1: int, y1: int, run: int = 0, title: str = ""):
    """A `school_courses._Kit` for a pane that wants the sections, columns and captions.

    The kit lives in `school_courses` because that is where the course diagrams are; a scene pane that
    wants a ruled section or a column split borrows it rather than growing a second, slightly different
    set of primitives (`_landmark` already does the same thing for its own title and caption).
    """
    from school_courses import _Kit
    return _Kit(s, x0, y0, x1, y1, title, run, 0, 1.0)


def _motes(k, glyphs: str, t: float, n: int = 0, level: float = 0.35, seed: int = 7) -> int:
    """A deterministic field of `glyphs` over the pane, on **blank cells only**.

    Batch 53, the user: "互换、茄子营养、猫学长图像那里比较空旷，可以加装饰或者复数图案". Same three rules as
    `school_courses.dust` - blank cells only (`_C.blank`, which also refuses the placeholder half of a wide
    glyph), a hash of the index rather than `random()` (`clock_probe --selftest` draws every row twice and
    compares), glyphs the renderer's fonts have - and it differs in *what* it sprinkles: each panel brings
    its own vocabulary, so the fill reads as that panel's subject scattered rather than as generic stars.
    Returns how many it drew, so a caller can tell whether it filled anything.
    """
    import school_courses as _C
    n = n or max(10, k.bw * k.bh // 30)
    drawn = 0
    for i in range(n):
        hx = (i * 2654435761 + seed * 40503) & 0xFFFF
        hy = (i * 1103515245 + seed * 12345) & 0xFFFF
        x = k.bx0 + hx % max(1, k.bw)
        y = k.by0 + hy % max(1, k.bh)
        if not _C.blank(k.s, x, y):
            continue
        tw = abs(math.sin(t * 1.2 + i * 0.9))
        k.put(x, y, glyphs[(hx >> 4) % len(glyphs)],
              _mix(_C.BLUE, level * (0.30 + 0.70 * tw)))
        drawn += 1
    return drawn


def pane_landmark_cat(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`猫学长` - the campus cat, as the character art the user supplied, not as a photograph.

    The user's note was that both the reference photographs *and* the two pieces of supplied character
    art should be used ("我参考的图像和字符画最好都用到"). The vessel has had a pane since batch 1; the cat
    used to appear twice - once as a one-second overlay (`school_fx.GLYPH_EVENTS`, 66.30) and once here.
    The overlay is gone (batch 30: "shot 31 还是 32 出现了一只意外的猫，请删除它" - it landed on the chorus,
    which is not about a cat), so this pane is the cat's one appearance, on the line it belongs to - the
    万物皆点 section, where `想法.md` asks for 猫＝薛定谔叠加态.

    The art is eleven lines, so it is centred and lit top-down rather than scaled: character art that is
    already terminal art must not be resampled.
    """
    import school_courses as _C
    art = ""
    import school_fx as _FX
    p = _FX.LANDMARKS / "\u732b\u5b66\u957f_\u5b57\u7b26\u753b.txt"
    try:
        art = p.read_text(encoding="utf8")
    except Exception:
        art = ""
    lines = [ln for ln in art.splitlines() if ln.strip()]
    # no `run`: this pane is not one of the numbered course hits, and passing the band height here (as
    # the first version did) put a bogus `EXEC 16/00` in the header rule - batch 31's audit caught it
    k = _kit(s, x0, y0, x1, y1)
    if k is None:
        return
    k.section(k.by0, "\u732b\u5b66\u957f", 0.30)
    if lines:
        w = max(_C._cells(ln) for ln in lines)
        ax = max(k.bx0, k.bx0 + (k.bw - w) // 2)
        top = k.by0 + 2
        shown = int(len(lines) * min(1.0, u * 1.8)) or 1
        # **The superposition, drawn.** The pane's own caption is `(|生> + |死>) / √2 — 叠加态不是不知道，
        # 是两个都在`, and the picture was one cat: the argument and the drawing disagreed. Two ghost
        # copies of the same art, either side of the real one and dim (batch 53, the user: "猫学长图像那里
        # 比较空旷，可以加装饰或者复数图案"). Drawn first, so the cat itself is the bright one in the middle.
        for off, lev in ((-4, 0.15), (4, 0.15)):
            for i, ln in enumerate(lines[:shown]):
                y = top + i
                if y > k.by1 - 2:
                    break
                k.put(ax + off, y, ln.replace("$", " "), _mix(_C.AMBER, lev))
        for i, ln in enumerate(lines[:shown]):
            y = top + i
            if y > k.by1 - 2:
                break
            k.put(ax, y, ln.replace("$", " "), _mix(_C.AMBER, 0.55 + 0.40 * (i / max(1, len(lines)))))
    y = k.by1 - 1
    if y > k.by0:
        k.put(k.bx0, y, "\u732b\u5728\u4e0d\u5728\u91cc\u9762\uff0c\u8981\u6253\u5f00\u624d\u77e5\u9053",
              _mix(_C.GREEN, 0.8))
        k.put(k.bx0, min(k.by1, y + 1),
              "(|\u751f> + |\u6b7b>) / \u221a2 \u2014\u2014 \u53e0\u52a0\u6001\u4e0d\u662f\u4e0d\u77e5\u9053\uff0c"
              "\u662f\u4e24\u4e2a\u90fd\u5728", _ui(0.5))
    # ...and something for the cat to watch: a dot circling its head on the song clock. The pane's only
    # motion used to be the motif band under it, and the cat is the one drawing here that is *alive*.
    ang = t * 1.5
    k.put(int(k.bx0 + 5 + 4 * math.cos(ang)), int(k.by0 + 3 + 3 * math.sin(ang)),
          "\u00b7", _mix(_C.GREEN, 0.7))
    # ...and the rest of the box: the cat is eleven lines of character art in a box several times that
    # wide, so both sides were black. `*` and `o` are the paw-print vocabulary of the art itself.
    _motes(k, "*o\u00b7", t, level=0.30, seed=11)


def pane_everything_point(s, x0, y0, x1, y1, t, lt, dur, u, panel: str = "") -> None:
    """万物皆点: three things that are points, and the picture each one actually has.

    `想法.md` gives this section four: 茄子＝USDA 营养流向图, 番茄＝番茄红素吸收光谱 (444/472/503 nm),
    猫＝薛定谔叠加态, 神＝存在!. The cat has its own pane; these are the other three, and they are drawn
    rather than described, which is the user's other note for this batch ("动图部分以视觉效果优先，
    比如优先画 sin(x) 的函数图像而不是写表达式"): a spectrum is a curve with three peaks marked, a flow
    diagram is boxes and arrows, and a uniqueness proof is a diagram with two dots and one of them crossed
    out - not the words for any of those things.

    **`panel` is which one to draw, and the schedule uses it.** All three at once, held from 01:13.5 to
    01:24.6, was eleven seconds of one pane - and the film cuts six times inside that window (eggplant,
    nutrients, tomato, antioxidants, tabby, purr), so the right column stopped following the song. The
    user's note was exactly that: "确保不会出现占时过长的演出，比如右边panel的西红柿那个光谱界面占了过长
    时间，和左侧歌词都不对应了". Now each panel gets the two film shots whose words it belongs to, and the
    cat gets its own pane on the two lines about a cat. No `panel` still draws all three, for a probe or a
    caller that wants the whole subject at once.
    """
    import school_courses as _C
    k = _kit(s, x0, y0, x1, y1, 0)
    if k is None:
        return
    k.section(k.by0, "\u4e07\u7269\u7686\u70b9", 0.30)
    if panel == "food":
        _ev_food(k, t, u)
        return
    if panel == "tomato":
        _ev_tomato(k, t, u)
        return
    if panel == "exists":
        _ev_exists(k, t, u)
        return
    bands = k.columns(3, [1, 1, 1], mins=[28, 30, 24]) if k.bw >= 60 else []
    if len(bands) == 3:
        _ev_food(k.sub(bands[0][0], k.by0, bands[0][1], k.by1), t, u)
        _ev_tomato(k.sub(bands[1][0], k.by0, bands[1][1], k.by1), t, u)
        _ev_exists(k.sub(bands[2][0], k.by0, bands[2][1], k.by1), t, u)
        for i, (cx0, _cx1) in enumerate(bands[1:], start=1):
            k.vline(cx0 - 2, k.by0, k.by1, "\u2502", _ui(0.18))
    else:
        _ev_tomato(k, t, u)


def _ev_food(k, t: float, u: float) -> None:
    """The aubergine as a flow diagram: field, packer, truck, kitchen, and the losses at each joint."""
    import school_courses as _C
    k.section(k.by0, "\u8304\u5b50 \u00b7 \u8425\u517b\u6d41\u5411", 0.25)
    names = ("\u7530\u95f4", "\u52a0\u5de5", "\u8fd0\u8f93", "\u9910\u684c")
    bw = max(6, min(9, k.bw - 6))
    step = max(4, (k.bh - 4) // len(names))
    # hexagons rather than rectangles: the user allows non-rectangular panels, and a flow diagram is the
    # one place in this film where the *nodes* are the thing being looked at. `school_courses.hexagon` is
    # the shared primitive, so the shape is the same one the embedded course uses.
    from school_courses import hexagon
    for i, nm in enumerate(names):
        y = k.by0 + 2 + i * step
        if y > k.by1 - 3:
            break
        # one character inside the hex, the full name beside it: at r=1 the cell's middle row is five cells
        # wide and a two-character label runs over its own right edge. The fill breathes on the pane's
        # clock, so the flow reads as flowing - and the falling dot below only exists when the wire is long
        # enough to hold one, which is why the pulse is here rather than there.
        hexagon(k, k.bx0 + bw // 2 + 1, y + 1, 1,
                _mix(_C.BLUE, 0.62 + 0.12 * math.sin(t * 1.7 - i)), nm[:1])
        k.put(k.bx0 + bw + 3, y + 1, nm, _ui(0.7))
        if i < len(names) - 1:
            k.vline(k.bx0 + bw // 2 + 1, y + 3, y + step - 1, "\u2502", _ui(0.3))
            k.put(k.bx0 + bw // 2 + 1, y + step - 1, "\u25bc", _mix(_C.RED, 0.7))
            k.put(k.bx0 + bw + 3, y + step - 1, f"-{8 + i * 6}%", _mix(_C.RED, 0.6))
            # what is being lost, falling down the wire: one dot per joint, on the pane's clock, and
            # the pane kept *some* motion after its reveal without this - but a flow diagram whose only
            # moving part is a caption is a diagram, and the caption is not what is flowing. Only drawn
            # when the wire is long enough to have a free cell between the hexagon and its arrow.
            if step >= 6:
                drop = y + 4 + (int(t * 4.0) + i * 3) % (step - 5)
                k.put(k.bx0 + bw // 2 + 1, drop, "\u25cf", _mix(_C.RED, 0.9))
    # the numbers on the wires are 8 %, 14 % and 20 %, so what arrives is 0.92*0.86*0.80 = 63 % - the
    # caption said "只剩一半" and the audit read the two against each other (batch 31, A-7)
    k.put(k.bx0, k.by1, "\u6bcf\u4e00\u6bb5\u90fd\u5728\u6389\uff1a"
                        "\u4ece\u5730\u91cc\u5230\u7897\u91cc\u53ea\u5269\u516d\u6210", _ui(0.5))
    # **...and the right two thirds of the box** (batch 53, the user: "茄子营养那里比较空旷"). The flow is
    # nine cells of hexagon and a label, so seventy columns of a ninety-five column pane were black. What
    # goes there is the same numbers as a waterfall - the three losses and what arrives - which is the one
    # thing this diagram is about that it was only saying in prose.
    free_x0 = k.bx0 + bw + 14
    span = k.bx1 - free_x0
    if span >= 30:
        xr = free_x0 + max(0, (span - 26) // 2)
        base = k.by1 - 4
        high = max(4, (k.by1 - k.by0) // 2)
        k.put(xr, k.by0 + 1, "\u5404\u6bb5\u635f\u8017\u4e0e\u5230\u8fbe", _ui(0.55))
        for j, (pc, nm, col) in enumerate(((8, "\u52a0\u5de5", _C.RED), (14, "\u8fd0\u8f93", _C.RED),
                                           (20, "\u9910\u684c", _C.RED), (63, "\u5269\u4e0b", _C.AMBER))):
            x = xr + j * 6
            h = max(1, int(high * pc / 70.0))
            for yy in range(base - h, base):
                k.put(x, yy, "\u2588", _mix(col, 0.55 + 0.30 * math.sin(t * 1.4 - j)))
            k.put(x, base + 1, f"{pc}%", _mix(col, 0.85))
            k.put(x, base + 2, nm, _ui(0.45))
    _motes(k, "o\u00b7", t, n=max(20, k.bw * k.bh // 22), level=0.28, seed=5)


def _ev_tomato(k, t: float, u: float) -> None:
    """Lycopene's absorption spectrum - a curve with three peaks, because that is what it is.

    The three wavelengths in `想法.md` (444, 472, 503 nm) are the peaks *in the blue*, which is why a
    tomato is red: it absorbs blue and reflects the rest. The pane draws the curve and marks the three
    peaks, and the drawing is the explanation - the first version of this idea was a caption with the
    numbers in it, which is what the user is asking to stop doing.
    """
    import school_courses as _C
    k.section(k.by0, "\u756a\u8304\u7ea2\u7d20 \u00b7 444/472/503 nm", 0.25)
    w = max(8, k.bw - 12)
    hi, lo = k.by0 + 2, k.by1 - 4
    if lo - hi < 3:
        return
    k.vline(k.bx0 + 9, hi, lo, "\u2502", _ui(0.3))
    k.hline(k.bx0 + 9, lo, k.bx0 + 9 + w, "\u2500", _ui(0.3))
    peaks = (0.30, 0.46, 0.62)
    # the markers go down *first*: drawn after the curve, three dashed verticals at the peak columns
    # paint over the three points they are supposed to be pointing at, and the picture then shows a
    # spectrum whose peaks are missing - which is what the first version of this panel did
    for pp, nm in zip(peaks, ("444", "472", "503")):
        x = k.bx0 + 10 + int(w * pp)
        k.vline(x, hi, lo, ":", _mix(_C.AMBER, 0.35))
        k.put(x - 1, hi - 1, nm, _mix(_C.AMBER, 0.85))
    prev = None
    for i in range(w + 1):
        f = i / max(1, w)
        # three gaussians on a falling baseline: drawn, not tabulated. The width matters - at 0.004 the
        # peaks are one sample wide and the curve reads as noise with three lines through it
        v = sum(0.9 * math.exp(-((f - pp) ** 2) / 0.012) for pp in peaks) * (1.0 - 0.30 * f)
        v = min(1.0, v)
        x = k.bx0 + 10 + i
        y = lo - 1 - int((lo - hi - 2) * v)
        if prev:
            for xx in range(prev[0] + 1, x):
                yy = int(prev[1] + (y - prev[1]) * (xx - prev[0]) / max(1, x - prev[0]))
                k.put(xx, yy, "\u00b7", _mix(_C.RED, 0.75))
        k.put(x, y, "\u2022", _mix(_C.RED, 0.95))
        prev = (x, y)
    k.put(k.bx0, lo + 1, "\u5438\u6536\u84dd\u5149\uff0c\u6240\u4ee5\u770b\u8d77\u6765\u662f\u7ea2\u7684", _ui(0.5))
    k.put(k.bx0, min(k.by1, lo + 2), "\u4e09\u4e2a\u5cf0\u5c31\u662f\u4e09\u4e2a\u6ce2\u957f", _ui(0.45))
    # a wavelength cursor sweeping the axis, with what happens to that colour: blue comes down onto
    # the curve and red goes back up. It is the same sentence as the caption below it, drawn instead
    # of written - and after the three peaks are on screen this is the only thing left that can move.
    x = k.bx0 + 10 + int(w * ((t * 0.22) % 1.0))
    k.put(x, lo, "\u2534", _mix(_C.AMBER, 0.9))
    k.put(x, hi + 1, "\u2193", _mix(_C.BLUE, 0.9))
    k.put(x, max(hi + 2, lo - 2), "\u2191", _mix(_C.RED, 0.9))


def _ev_exists(k, t: float, u: float) -> None:
    """`\u5b58\u5728!` - the uniqueness proof, as the diagram it is: two candidates, one struck out."""
    import school_courses as _C
    k.section(k.by0, "\u795e \u00b7 \u5b58\u5728! \u552f\u4e00\u5b58\u5728", 0.25)
    mid = k.by0 + 3
    if k.bh < 6:
        return
    k.put(k.bx0 + 2, mid, "\u5b58\u5728 x", _mix(_C.GREEN, 0.9))
    k.put(k.bx0 + 2, mid + 2, "\u5b58\u5728 y", _mix(_C.GREEN, 0.9))
    k.put(k.bx0 + 8, mid, "P(x)", _ui(0.7))
    k.put(k.bx0 + 8, mid + 2, "P(y)", _ui(0.7))
    k.put(k.bx0 + 8, mid + 1, "\u2193", _mix(_C.AMBER, 0.9))
    k.put(k.bx0 + 12, mid + 1, "x = y", _mix(_C.AMBER, 0.95))
    # the two candidates are looked at one at a time, and the second one is struck out on the same
    # beat. A proof is a sequence of looks, not a still page, and this is the pane's half of the
    # parallelism the user asked for. The beat is a *position* on a 1.7 Hz clock and a *brightness* on
    # a continuous one: a two-state blink alone can land on the same phase at three samples of a short
    # slot, and then the pane reads as still to `_dev/clock_probe.py` even though it blinks.
    look = int(t * 1.7) % 2
    k.put(k.bx0, mid if not look else mid + 2, ">",
          _mix(_C.AMBER, 0.55 + 0.4 * abs(math.sin(t * 2.6))))
    # and the second candidate being struck out, which is the "!" in 存在!
    if u > 0.55:
        for i in range(7):
            k.put(k.bx0 + 2 + i, mid + 2, "\u2500", _mix(_C.RED, 0.85 if look else 0.5))
        k.put(k.bx0 + 2, mid + 4, "\u4e0d\u5b58\u5728\u7b2c\u4e8c\u4e2a", _mix(_C.RED, 0.8))
    k.put(k.bx0, k.by1 - 1, "\u5b58\u5728\u4e14\u552f\u4e00\uff1a\u4e24\u4e2a\u90fd\u884c\u5c31\u7b49\u4e8e"
                            "\u4e00\u4e2a\u90fd\u4e0d\u884c", _ui(0.5))
    k.put(k.bx0, k.by1, "world.execute(me); \u91cc\u7684\u795e\u4e5f\u53ea\u80fd\u6709\u4e00\u4e2a",
          _mix(_C.AMBER, 0.7))


def pane_exchange(s, x0, y0, x1, y1, t, lt, dur, u, panel: str = "") -> None:
    """互换: four things that are the same thing twice, on the lines about switching roles.

    `想法.md` gives this section five: `F→M` flipping exactly three bits, the twelve-hour clock as a
    double cover of a day, the braid group σ1, moiré, and the superellipse. The section had **no school
    pane at all** - 41.9 to 54.7 was the film's own panels - so this is new content in a gap as well as
    the drawing those five were waiting for. Three panels, because the song's line is about a role
    changing and the interesting part is that nothing is lost: a bit flip is reversible, a clock face
    comes back around, and a braid can be undone.
    """
    import school_courses as _C
    k = _kit(s, x0, y0, x1, y1, 0, "互换")
    if k is None:
        return
    # `panel` draws one of the four at full width. The row was 12.8 s and seven lyric lines with all four
    # small at once - the "占时过长" the user objected to on the tomato pane - so the schedule gives each
    # of them the line it belongs to: the bit flip on "Switch my current", the clock on "To AC, to DC",
    # the braid on "blind my vision", the superellipse on "we can travel".
    one = {"bits": _ex_bits, "clock": _ex_clock, "braid": _ex_braid, "hyper": _ex_hyper}.get(panel)
    if one is not None:
        one(k, t, u)
        # Each of the four is one figure in a 95-cell box, so a `panel=` row was a small drawing in a large
        # black field (batch 53, the user: "互换...图像那里比较空旷，可以加装饰或者复数图案"). The fill is the
        # panel's own vocabulary - bit digits for the flip, rings for the clock, strand strokes for the
        # braid, nested outlines for the superellipse - so it reads as the subject scattered, not as stars.
        _motes(k, {"bits": "01", "clock": "o\u00b7", "braid": "/\\",
                   "hyper": "o\u00b7\u00b7"}.get(panel, "\u00b7"), t, level=0.34, seed=13)
        return
    # Four columns when the pane is wide enough for all of them, three when it is not, one when it is
    # narrow: the superellipse is the fourth of `想法.md`'s five motifs for this section and it was left
    # out in the last batch only because the pane was laid out as three.
    #
    # The thresholds are the real widths, measured rather than guessed: the right-hand column is 95 cells
    # across at 197 columns (`lx = cols * 0.50`), so the first version's `bw >= 108` fell back to three
    # columns in every frame and the fourth panel was never on screen anywhere.
    cols = k.columns(4, [1, 1, 1, 1], mins=[20, 22, 22, 18]) if k.bw >= 90 else []
    if len(cols) == 4:
        for i, fn in enumerate((_ex_bits, _ex_clock, _ex_braid, _ex_hyper)):
            if i:
                k.vline(cols[i][0] - 2, k.by0, k.by1, "\u2502", _ui(0.18))
            fn(k.sub(cols[i][0], k.by0, cols[i][1], k.by1), t, u)
        return
    cols = k.columns(3, [1, 1, 1], mins=[26, 26, 26]) if k.bw >= 78 else []
    if len(cols) == 3:
        _ex_bits(k.sub(cols[0][0], k.by0, cols[0][1], k.by1), t, u)
        _ex_clock(k.sub(cols[1][0], k.by0, cols[1][1], k.by1), t, u)
        _ex_braid(k.sub(cols[2][0], k.by0, cols[2][1], k.by1), t, u)
        for cx0, _cx1 in cols[1:]:
            k.vline(cx0 - 2, k.by0, k.by1, "\u2502", _ui(0.18))
    else:
        _ex_bits(k, t, u)


def _ex_hyper(k, t: float, u: float) -> None:
    """`|x|^n + |y|^n = r^n`, with the exponent breathing from a diamond to a rounded square.

    The fifth of this section's motifs and the one the songs's line is *about*: `Switch my current` is a
    shape changing while staying the same shape. At n=1 it is a diamond, at n=2 the circle, and past that
    a rectangle with round corners - one equation, three things everybody would name differently.
    """
    import school_courses as _C
    k.section(k.by0, "\u8d85\u692d\u5706", 0.25)
    cx = k.bx0 + max(4, k.bw // 2 - 2)
    cy = (k.by0 + k.by1) // 2
    rx = max(3, min(12, k.bw // 3))
    ry = max(2, min(8, (k.by1 - k.by0) // 3))
    n = 1.0 + 2.5 * (1.0 + math.sin(t * 0.45))
    for a in range(0, 360, 4):
        th = math.radians(a)
        ct, st = math.cos(th), math.sin(th)
        r = (abs(ct) ** n + abs(st) ** n) ** (-1.0 / n)
        k.put(int(cx + rx * r * ct), int(cy + ry * r * st), "\u2022", _mix(_C.VIOLET, 0.9))
    k.put(k.bx0, k.by1 - 1, f"n = {n:4.2f}", _mix(_C.AMBER, 0.8))
    k.put(k.bx0, k.by1, "1 \u83f1\u5f62 \u00b7 2 \u5706 \u00b7 6 \u65b9\u6846", _ui(0.45))


def _ex_bits(k, t: float, u: float) -> None:
    """`F` to `M` is three bits: 0x46 XOR 0x4D = 0x0B, which has three bits set."""
    import school_courses as _C
    k.section(k.by0, "F \u2192 M \u00b7 3 \u4f4d", 0.25)
    a, b = ord("F"), ord("M")
    y = k.by0 + 2
    # The bit the reader is being shown, on the pane's clock: a cursor walks the eight positions and the
    # three rows answer under it. Without it this panel was a still diagram - `_dev/clock_probe.py` counts
    # the cells that change, and a drawing that only reveals is a drawing that stops.
    cur = int(t * 3.0) % 8
    for i, (lab, v) in enumerate((("F", a), ("M", b), ("XOR", a ^ b))):
        bits = "".join("1" if v & (1 << (7 - j)) else "0" for j in range(8))
        yy = y + i * 2
        if yy > k.by1 - 2:
            break
        k.put(k.bx0, yy, f"{lab:>3}", _ui(0.7))
        for j, bit in enumerate(bits):
            flip = i == 2 and bit == "1"
            on = j == cur
            k.put(k.bx0 + 5 + j * 2, yy, bit,
                  _mix(_C.AMBER if on else (_C.RED if flip else _C.BLUE), 0.95 if on else 0.55))
        if i == 2:
            k.put(k.bx0 + 5 + 8 * 2, yy, "\u2190 3 \u4f4d\u4e0d\u540c", _mix(_C.AMBER, 0.85))
    if y + 6 <= k.by1 - 3:
        k.put(k.bx0 + 5 + cur * 2, y + 6, "\u25b2", _mix(_C.AMBER, 0.9))
    k.put(k.bx0, k.by1 - 1, "\u6539\u53d8\u4e00\u4e2a\u5b57\u6bcd\uff0c\u53ea\u52a8\u4e09\u4f4d", _ui(0.5))
    k.put(k.bx0, k.by1, "0x46 \u2295 0x4D = 0x0B", _mix(_C.GREEN, 0.7))


def _ex_clock(k, t: float, u: float) -> None:
    """The twelve-hour clock: two laps of the dial are one day, and the dial does not say which."""
    import school_courses as _C
    k.section(k.by0, "12 \u5c0f\u65f6 \u00b7 \u53cc\u91cd\u8986\u76d6", 0.25)
    cx = k.bx0 + min(16, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    r = max(3, min(9, (k.by1 - k.by0) // 3, k.bw // 5))
    for a in range(0, 360, 6):
        th = math.radians(a)
        k.put(int(cx + r * math.cos(th)), int(cy + r * math.sin(th) * 0.5), "\u00b7", _ui(0.3))
    spin = (t * 0.8) % (2 * math.pi)
    for lap in range(2):
        th = spin + lap * math.pi
        k.put(int(cx + r * math.cos(th)), int(cy + r * math.sin(th) * 0.5),
              "\u25cf" if lap == 0 else "\u25cb", _mix(_C.AMBER if lap == 0 else _C.BLUE, 0.9))
    k.put(cx - 1, cy, "\u2295", _mix(_C.RED, 0.9))
    # the captions go *under* the dial, clipped to the column: beside it they ran into the next panel,
    # which the pane probe cannot see (they are inside the pane, just in the wrong panel)
    from school_courses import _clip
    for i, line in enumerate(("\u4e24\u5708 = \u4e00\u5929", "\u8868\u76d8\u4e0d\u544a\u8bc9\u4f60\u54ea\u4e00\u5708",
                              "12h \u662f 24h \u7684\u4e8c\u91cd\u8986\u76d6")):
        y = cy + r // 2 + 1 + i
        if y <= k.by1 - 1:
            k.put(k.bx0, y, _clip(line, k.bw), _ui(0.55 - 0.05 * i))
    k.put(k.bx0, k.by1, "\u4e0a\u5348\u4e0e\u4e0b\u5348\u662f\u540c\u4e00\u4e2a\u4f4d\u7f6e", _ui(0.5))


def _ex_braid(k, t: float, u: float) -> None:
    """The braid group: σ1 is two strands crossing, and its inverse undoes it."""
    import school_courses as _C
    k.section(k.by0, "\u8fab\u7fa4 \u03c31 \u00b7 \u53ef\u9006", 0.25)
    n = 3
    w = max(6, k.bw - 4)
    rows = max(6, min(18, k.by1 - k.by0 - 3))
    for j in range(rows):
        # the braid is *travelling*: the crossing points slide down the strands on the pane's clock, which
        # is what a braid looks like while it is being combed - and what stops this panel being a still
        # picture (the same reason `_ex_bits` grew a cursor)
        f = ((j + t * 1.6) % rows) / max(1, rows - 1)
        y = k.by0 + 2 + j
        for s_ in range(n):
            x0f = (s_ + 0.5) / n
            amp = 0.28 if s_ == 0 else (-0.28 if s_ == 1 else 0.0)
            if f < 0.45:
                x = x0f + amp * (f / 0.45)
                going = amp > 0
            else:
                g = (f - 0.45) / 0.55
                x = x0f + amp * (1 - g)
                going = amp < 0
            xx = k.bx0 + 2 + int(w * min(0.98, max(0.02, x)))
            # the stroke leans the way the strand is travelling: a braid drawn entirely in `╱` is a fence
            k.put(xx, y, "\u2502" if abs(x - x0f) < 0.02 else ("\u2571" if going else "\u2572"),
                  _mix(_C.BLUE, 0.7))
    k.put(k.bx0, k.by1 - 1, "\u4ea4\u53c9\u4e00\u6b21\u518d\u4ea4\u53c9\u56de\u53bb\uff0c"
                            "\u7ed3\u679c\u7b49\u4e8e\u6ca1\u52a8", _ui(0.5))
    k.put(k.bx0, k.by1, "\u03c31 \u00b7 \u03c31^-1 = e", _mix(_C.GREEN, 0.7))


def pane_landmark_crest(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """The crest, on the first shot and the last.

    Opening: it is a watermark under the traces of `pane_power_on`. Closing: it is the only thing
    left, and then it is not.

    The bus that used to run across it is gone, and the crest now takes the pane. Both changes are the
    user's: "\u5fae\u7f29\u6821\u5fbd\u5b57\u7b26\u753b\u4e2d\u6709 2 \u6761\u7ebf\uff0c\u53bb\u6389\uff0c\u8ba9\u6821\u5fbd\u53ef\u89c6\u5316\u7a0b\u5ea6\u9ad8\u4e00\u70b9". The lines were
    `pane_power_on`'s copper bus, repeated here as a watermark on the theory that the crest should
    belong to that shot - but at nine rows the emblem is 19 cells across, and two of the four lines
    landed straight through it, so what the pane said was "copper bus" and not "校徽". The emblem is
    also the one thing in this variant that has to survive being recognised: it is on the first frame
    and the last. So the lines are dropped and the rows `max_rows=9` was throwing away are given back
    to it (the pane has eighteen), which is four times the drawn area - the difference between a
    striped ball and the university's mark.
    """
    closing = t > 190.0
    _landmark("crest", s, x0, y0, x1, y1, u,
              "\u897f\u5317\u5de5\u4e1a\u5927\u5b66",
              "\u516c\u8bda\u52c7\u6bc5 \u00b7 \u4e09\u5b9e\u4e00\u65b0" if closing else "",
              dim=0.72 + 0.16 * math.sin(t * 1.1) if not closing
              else max(0.3, 1.0 - (lt / max(1e-6, dur))),
              max_rows=None if closing else 15)


def pane_isolation(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`You have left me in isolation` - one point left, and the field emptying around it.

    The user's note is that MEMORY held the column for fifteen seconds ("memory 停留时间太长了，增加其他动画
    修改"). The sculpture is the right drawing for the five "You have left" lines - its own idea is one
    word printed more times than the last time - but the row after them sat there for another five and a
    half seconds over "Erase all the pointless fragments" and "Then maybe, then maybe", which are not
    about a graduation sculpture at all. So the run is cut: the layers climb, and then the pane becomes
    *this* on the line that says what the empty column means.

    The drawing is the lyric: a lattice of points, all but one of them going out one at a time, and the
    one that is left breathing. `u` decides how much of the field is still lit - so a seek lands on the
    same frame as playing, and the pane is never a still picture (the failure `_dev/clock_probe.py`
    exists to catch).
    """
    import school_courses as _C
    k = _kit(s, x0, y0, x1, y1, 0, "\u5b64\u7acb \u00b7 in isolation")
    if k is None:
        return
    k.section(k.by0, "\u4e00\u4e2a\u70b9\u7559\u4e0b", 0.25)
    top = k.by0 + 2
    rows = list(range(top, k.by1 - 2, 2))
    if not rows or k.bw < 12:
        k.put(k.bx0, k.by1, "\u53ea\u5269\u4e00\u4e2a\u70b9", _C._ui(0.6))
        return
    step_x = max(4, k.bw // 9)
    # the field: nine points a row, erased in order of distance from the middle, so what is left at the
    # end is the point the whole drawing is about - and the order is a function of `u` rather than of a
    # random number, so it is the same every time the second is played.
    #
    # **The surviving point pulses on the beat**, which is what the comment here claimed and the code did
    # not do. It was `0.62 + 0.38 * abs(sin(t * 2.1))` - a sine at 2.1 rad/s, i.e. a 3.0 s period against
    # a 0.4615 s beat, so it was in phase with the song about once every seven beats and drifted the rest
    # of the time. It read as "something is breathing" and never as "the machine is still counting". This
    # is the same beat clock the film's boxes breathe on (`FP.pulse`: 1 on the beat, decaying over 140 ms)
    # and the same one the course counter answers to now; the last point standing is one of the few places
    # in the film where a single cell *is* the subject, so it is worth the one exponent.
    beat = 0.55 + 0.45 * _beat(t)
    middle = len(rows) // 2
    gone = 0
    for i, y in enumerate(rows):
        for j in range(9):
            x = k.bx0 + 2 + j * step_x
            far = abs(i - middle) * 9 + abs(j - 4)
            # the last point to go is the middle one, and it never does
            if far == 0:
                continue
            if far <= int(u * 60):
                gone += 1
                continue
            # ...and the points that are still there are being left in order, so the ones about to go
            # are drawn dimmer than the ones with time left: the field is emptying *toward* the middle
            # rather than blinking out, which is the difference between a countdown and a still image
            near = far > int(u * 60) + 24
            k.put(x, y, "\u00b7", _C._ui(0.40 if near else 0.22))
    cx = k.bx0 + 2 + 4 * step_x
    cy = k.by0 + 2 + middle * 2
    k.put(cx, cy, "\u25cf", _C._mix(_C.AMBER, beat))
    k.put(cx - 1, cy, "\u25cb", _C._mix(_C.AMBER, beat * 0.5))
    # ...and the count has to agree with the point that is drawn: this read "剩 0 / 116" with the
    # surviving dot right there (batch 31's audit: off-by-one in the denominator)
    total = 9 * len(rows)
    k.put(k.bx0, k.by1 - 1, f"\u5269 {total - gone} / {total}", _C._ui(0.5))
    k.put(k.bx0, k.by1, "\u4f60\u8d70\u4e86\uff0c\u5269\u4e0b\u7684\u90fd\u5728\u706d", _C._ui(0.55))


def pane_fragments(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`Erase all the pointless fragments` - the field wiped a fragment at a time.

    The second half of the same cut. The lyric is an instruction to delete, and the pane is that
    instruction carried out: a grid of small marks whose cells are erased on the clock, with a cursor
    walking the grid rather than a wipe sweeping it. `_dev/clock_probe.py` asks every pane to move; the
    cursor is what moves here, and it is why the drawing does not read as a still frame once the grid
    has mostly gone.

    Deliberately *not* one of the four AI motifs: those belong to the last fifty seconds, and reusing
    `pane_ai_diffusion`'s denoise here would have spent it twice.
    """
    import school_courses as _C
    k = _kit(s, x0, y0, x1, y1, 0, "\u5220\u9664 \u00b7 erase fragments")
    if k is None or k.bw < 12 or k.bh < 5:
        return
    k.section(k.by0, "\u65e0\u610f\u4e49\u7684\u788e\u7247", 0.25)
    cells_w = max(6, min(34, k.bw // 3))
    cells_h = max(2, min(13, (k.bh - 6) // 2))
    ox, oy = k.bx0 + max(0, (k.bw - cells_w * 2) // 2), k.by0 + 2
    total = cells_w * cells_h
    # four cells are never deleted, so the pane does not end as an empty box: the lyric is an instruction
    # to erase the *pointless* fragments, and this drawing leaves the last few standing.
    live = max(1, total - 4)
    cut = min(live, int(u * live))             # how many have been deleted, in reading order
    # The cursor walks the whole grid, deleted cells included, and it is drawn *over* them.
    #
    # That is what keeps the drawing moving at every `u`, including u=1 - and u=1 is not hypothetical:
    # `_dev/clock_probe.py` samples the slot at 0.15, 0.55 and **1.0** with `u` pinned, so a cursor
    # constrained to the cells that are left reads as a still frame there and the row fails. A cursor
    # that walks the field it has already erased is also the truer picture: the pass goes on.
    step = int(t * 6.0) % max(1, total)
    for i in range(total):
        y, x = oy + i // cells_w, ox + (i % cells_w) * 2
        if y > k.by1 - 2:
            break
        if i == step:
            k.put(x, y, "\u2588", _C._mix(_C.RED, 0.85))
        elif i < cut:
            continue                           # deleted
        else:
            # Batch 49, the user: "无意义的碎片中灰色碎片太暗了，看不清，需要调亮". Two things were
            # stacking against it and both had to go: the glyph was `░` (a quarter-covered cell) and the
            # colour was `_ui(0.34)` - and `_ui` carries the film's global drain, which is at 0.42 by
            # 02:00, so the cell was (29, 31, 34) on a (4, 7, 15) background. That is a *black* cell with
            # a shade glyph in it. `▒` is twice the coverage and the level is now 0.85, which lands about
            # four times the ink: the fragments have to be visible or "erase the pointless fragments" is
            # an instruction with nothing to erase.
            k.put(x, y, "\u2592", _C._ui(0.85))
    k.put(k.bx0, k.by1 - 1, f"{cut} / {total} \u5df2\u5220", _C._ui(0.5))
    k.put(k.bx0, k.by1, "\u788e\u7247\u4e0d\u662f\u75d5\u8ff9\uff0c\u5220\u4e86\u5c31\u6ca1\u4e86",
          _C._mix(_C.BLUE, 0.7))


def pane_memory(s, x0, y0, x1, y1, t, lt, dur, u, layers: int = 1, ghost: float = 0.42) -> None:
    """`MEMORY` - the graduation sculpture, drawn rather than characterised.

    The work is one word printed twice: a solid gold MEMORY in front and a pale ghost of the same word
    behind it. `_dev/campus_probe.py` showed that characterising the photograph reads for the single
    layer and smears for the ghosted one, so this draws the *meaning* instead: five-row block letters,
    repeated `layers` times, each ghost layer dimmed and offset.

    That is also what makes it parameterisable, and it has to be: `You have left` is the same sentence
    five times and the sculpture is the only thing in this variant that can be *counted* in the same
    way - one more layer each time the line comes round. `layers` therefore comes from the schedule
    (`school_panels.LANDMARK_ROWS`), not from the clock.

    The ghost layers fade geometrically rather than linearly, which is what the sculpture's own
    photograph does: the second MEMORY is clearly readable and the fourth is barely there. The offset
    grows with the layer index so that six layers read as a smear and two read as a doubled word.
    """
    import school_courses as _C
    k = _C._Kit(s, x0, y0, x1, y1, "MEMORY", 0, 0, u)
    word = "MEMORY"
    cell_w = 6                                     # one block letter is 6 cells wide, 5 rows tall
    total = len(word) * cell_w
    if k.bw < 8 or k.bh < 2:
        return
    if k.bw < total or k.bh < 5:
        # too small for the block letters: the word itself, at the weight the pane can carry
        k.put(k.bx0, k.by0, (word * layers)[: max(1, k.bw)], _C._mix(_C.AMBER, 1.0 if layers == 1 else ghost))
        k.put(k.bx0, min(k.by1, k.by0 + 1), f"x{layers}", _C._ui(0.5))
        # the pane degrades to one line here and the motif band is skipped at this height, so it needs
        # its own mark or it is a still frame in a sixty-column window
        if k.bh >= 3:
            k.put(k.bx0 + (int(t * 2.0) % max(1, k.bw)), min(k.by1, k.by0 + 2), "\u2581",
                  _C._mix(_C.AMBER, 0.7))
        return
    # Which layer is lit: the ghosts are the same word repeated, and lighting them in turn is the
    # sculpture being *counted* - which is what this pane is for ("one more layer each time the line
    # comes round"). All six equally lit is a photograph of six words, and a still one: the drawing
    # itself had no clock at all until `_dev/clock_probe.py` asked for one.
    active = int(t * 1.1) % max(1, layers)
    for layer in range(layers - 1, -1, -1):
        # geometric falloff: 1.0, then ghost, ghost^2, ... so the far layers are ghosts of ghosts -
        # measured from the lit layer rather than from the front, so the bright word walks back
        level = 1.0 if layer == active else max(0.10, ghost ** abs(layer - active))
        if layers == 1:
            # ...and the single layer breathes, which is not decoration: `_dev/clock_probe.py` asks every
            # pane to move, and with one layer there is no second layer to walk to - the word would be a
            # still frame for as long as it is on screen (it is on screen for 1.9 s at 01:57.95, alone,
            # after the field has emptied).
            level = 0.84 + 0.16 * abs(math.sin(t * 2.4))
        off = layer * 2
        ox = k.bx0 + max(0, (k.bw - total) // 2) + (off // 2) - (off // 2 if layers > 3 else 0)
        oy = k.by0 + max(0, (k.bh - 5) // 2) + (off % 3) - (1 if layers > 3 else 0)
        for i, ch in enumerate(word):
            _block_letter(k, ox + i * cell_w, oy, ch, _C._mix(_C.AMBER, level))
    # ...and the field around it, which was empty (batch 50, the user: "memory 字符画周边有些单调了，可以
    # 加一些装饰（比如星纹）"). The sculpture is a graduation present photographed at night, so the
    # decoration is its own backdrop: a field of stars that twinkle on the song clock. Three rules:
    # deterministic (a hash of the index, never `random()` - `clock_probe --selftest` draws every row
    # twice and compares), never on the word (the cell has to be blank already), and glyph-safe (`*`,
    # `·`, `o` only - see `_sparkle`; `*`/`*` are in neither of the exporter's fonts).
    if k.bw > 20 and k.bh > 6:
        for i in range(max(10, int(k.bw * k.bh * 0.035))):
            hx = (i * 2654435761 + layers * 40503) & 0xFFFF
            hy = (i * 1103515245 + layers * 12345) & 0xFFFF
            x = k.bx0 + hx % max(1, k.bw)
            y = k.by0 + hy % max(1, k.bh)
            if not (k.by0 + 1 < y < k.by1) or not _C.blank(k.s, x, y):
                continue
            tw = 0.30 + 0.70 * abs(math.sin(t * 1.6 + i * 0.7))
            # `_sparkle` is five cells, not one, so all five have to be free before it is drawn: a star
            # whose *centre* is blank can still land its left or right arm on half of a wide glyph.
            star = ((x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1))
            if (hx >> 5) % 11 == 0 and all(_C.blank(k.s, xx, yy) for xx, yy in star):
                _sparkle(k, x, y, _C.AMBER, centre=0.45 + 0.55 * tw)
            elif (hx >> 3) % 5 == 0:
                k.put(x, y, "o", _C._mix(_C.BLUE, 0.35 + 0.45 * tw))
            else:
                k.put(x, y, "\u00b7", _C._ui(0.25 + 0.5 * tw))
    k.put(k.bx0, k.by0, f"layers {layers}", _C._ui(0.5))


# five-row block letters, the shape the sculpture's own type has: heavy, squared, no serifs. Only the
# six letters of MEMORY are needed, so this is a table rather than a font.
_LETTERS = {
    "M": ["\u2588   \u2588", "\u2588\u2588 \u2588\u2588", "\u2588 \u2588 \u2588", "\u2588   \u2588",
          "\u2588   \u2588"],
    "E": ["\u2588\u2588\u2588\u2588\u2588", "\u2588    ", "\u2588\u2588\u2588\u2588 ", "\u2588    ",
          "\u2588\u2588\u2588\u2588\u2588"],
    "O": [" \u2588\u2588\u2588 ", "\u2588   \u2588", "\u2588   \u2588", "\u2588   \u2588", " \u2588\u2588\u2588 "],
    "R": ["\u2588\u2588\u2588\u2588 ", "\u2588   \u2588", "\u2588\u2588\u2588\u2588 ", "\u2588  \u2588 ",
          "\u2588   \u2588"],
    "Y": ["\u2588   \u2588", " \u2588 \u2588 ", "  \u2588  ", "  \u2588  ", "  \u2588  "],
}


def _block_letter(k, x: int, y: int, ch: str, colour) -> None:
    rows = _LETTERS.get(ch)
    if not rows:
        return
    for r, line in enumerate(rows):
        k.put(x, y + r, line, colour)


# the landmark panes and the closing panes are added to the dispatch *after* their definitions: a dict
# literal near the top of the file that named them would be evaluated before the functions existed.
def _motif(name: str):
    """A dispatch entry for one of `school_motifs`' twenty-two drawings, as a pane of its own.

    The motifs were written as *bands* - a strip under the pane whose lyric they belong to - because
    `想法.md` lists them as decoration for a drawing that already exists. The user's note this batch is
    "有些演出重复了很多次，除了校徽、铸剑雕塑外的演出禁止重复，请依据歌词给出合适的图案演出", and that
    asks for the opposite: more distinct drawings, one per lyric. Twenty-two motifs that already have a
    title, an animation and a clock are exactly the vocabulary for that, so they are promoted here rather
    than invented again.

    They are still drawn as **bands**, though - a block of rows in the middle of the pane with the title
    above and a caption below - and that is `density_probe`'s doing rather than a style choice: drawn to
    fill a 95x33 box, `pixelsort` and the Chladni plate came out as walls of ink (its criterion for "this
    stopped being a drawing and became texture" is a third of the cells, and both were well past it). A
    band is what they were designed for; the pane gives them the room to be looked at.
    """
    import school_motifs as _M

    def pane(s, x0, y0, x1, y1, t, lt, dur, u, args=None) -> None:
        title, fn = _M.MOTIFS[name]
        k = _kit(s, x0, y0, x1, y1, 0, title)
        if k is None or k.bh < 5:
            return
        band = max(4, min(k.bh - 2, _M.BAND_MAX.get(name, 99)))
        fn(k.sub(k.bx0, k.by0 + 1, k.bx1, k.by0 + band), t)

    pane.__name__ = "pane_motif_" + name
    return pane


def _ai(name: str):
    """A dispatch entry for one of `school_courses`' four AI panes, in this module's calling shape.

    Every pane here takes `(s, x0, y0, x1, y1, t, lt, dur, u, args=None)`; the AI drawings take a
    `_Kit` and `(lt, dur)` like the course panes do, so the adapter is one extra argument and one
    `draw_ai` call rather than a second copy of their signatures.
    """
    import school_courses as _C

    def pane(s, x0, y0, x1, y1, t, lt, dur, u, args=None) -> None:
        _C.draw_ai(name, s, x0, y0, x1, y1, t, lt, dur, u)

    pane.__name__ = name
    return pane


PANE_BY_NAME.update({
    "pane_landmark_dialogue": pane_landmark_dialogue,
    "pane_landmark_sword": pane_landmark_sword,
    "pane_landmark_hezun": pane_landmark_hezun,
    "pane_landmark_cat": pane_landmark_cat,
    "pane_exchange": pane_exchange,
    "pane_everything_point": pane_everything_point,
    "pane_landmark_crest": pane_landmark_crest,
    "pane_memory": pane_memory,
    "pane_isolation": pane_isolation,
    "pane_fragments": pane_fragments,
    # the closing three sections (`02b_图像对位与可视化表达.md` §4.3-4.6)
    "pane_converge": pane_converge,
    "pane_backlog": pane_backlog,
    "pane_sw_project": pane_sw_project,
    "pane_knowledge": pane_knowledge,
    "pane_love_class": pane_love_class,
    # the four AI motifs. Their drawings live in `school_courses` with the rest of the diagrams - they
    # use the same `_Kit`, the same terms footer and the same palette - and are registered here because
    # this is the module the schedule dispatches through.
    "pane_ai_cnn": _ai("pane_ai_cnn"),
    "pane_ai_attention": _ai("pane_ai_attention"),
    "pane_ai_rl": _ai("pane_ai_rl"),
    "pane_ai_diffusion": _ai("pane_ai_diffusion"),
})

# ...and every motif of `school_motifs`, each as a pane in its own right: `pane_motif_he_init`,
# `pane_motif_byrne`, and so on. The schedule picks them by lyric - see `_motif`.
import school_motifs as _MOT            # noqa: E402

for _m in _MOT.MOTIFS:
    PANE_BY_NAME["pane_motif_" + _m] = _motif(_m)

# the same names, for the schedule in `school_panels` to hang on lyric times
LANDMARK_PANES = ["pane_landmark_crest", "pane_landmark_dialogue", "pane_landmark_sword",
                  "pane_landmark_hezun", "pane_memory"]

# The drawings that own their whole rect - no header row, no rule, the picture from `y0` down. They are
# the first act's board and code panes plus the timetable, and they were written that way on purpose (the
# traces of `pane_power_on` are the whole box). `draw_pane` gives them a header, with the title below,
# only when the schedule row has a subtitle to put after it.
HEADERLESS = {
    "pane_power_on": "上电",
    "pane_protection": "防护",
    "pane_class": "类与对象",
    "pane_parameters": "参数表",
    "pane_point_set": "点集",
    "pane_polyhedra": "多面体",
    "pane_three_arms": "三旋臂",
    "pane_countdown": "倒计时",
    "pane_curriculum": "四年课表",
    # ...and the closing three, which are also drawings rather than framed panels: the four diagram types
    # merging into one class, the kanban, and the knowledge graph. `_dev/pane_probe.py` is what found
    # these three - its "every pane must show the row's sentence" check is the reason the list is not a
    # guess.
    "pane_converge": "收敛",
    "pane_backlog": "看板",
    "pane_knowledge": "知识图谱",
}


def draw_pane(name: str, s, x0: int, y0: int, x1: int, y1: int, t: float,
              lt: float, dur: float, u: float, args: dict | None = None) -> bool:
    """Draw the named pane; False if there is no such pane (the caller keeps the ops ticker then).

    `args` is how a *schedule* tells a drawing what it is: `pane_memory` is one pane drawn at six
    different layer counts on the five "You have left" lines, and the count is the whole point of the
    drawing, so it has to come from the row in `school_panels` rather than be guessed from the time.
    A pane that takes no arguments ignores it.

    **There is no motif band any more** (batch 32). Until then this function split the box and drew one
    of `school_motifs`' pictures in the lower part whenever the pane was listed in `MOTIF_IN`/`MOTIF_ALSO`
    - and sixteen of those motifs *also* have a pane of their own (`pane_motif_<name>`), so the same
    drawing played twice in one song. That is the repeat the user forbade ("除了校徽、铸剑雕塑外的演出禁止
    重复"), and `_dev/repeat_probe.py` could not see it because it compares pane names in the schedule while
    the band was a second drawing inside one pane's box. The motifs are panes now, and the panes that used
    to borrow a band for motion have their own clock.
    """
    fn = PANE_BY_NAME.get(name)
    if fn is None:
        return False
    # **Nine of the first-act drawings have no header row** (batch 58): the board, the strap, the class
    # code, the parameter table, the point set, the polyhedra, the three arms, the countdown and the
    # timetable all draw *their own* first row, so there is no title for the row's subtitle to sit
    # after - and the user's note is about "抬头部分，标题后加上 · 说明". They get one here, in the same
    # shape every other pane uses (`_Kit` draws `▏ title · sub` and the rule), and the drawing is given
    # the body rect under it. Two rows of their own drawings is the cost, and it is the same two rows
    # every framed pane in the film gives up.
    if name in HEADERLESS:
        import school_courses as _C
        if _C.PANE_SUB[0]:
            k = _C._Kit(s, x0, y0, x1, y1, HEADERLESS[name], 0, 0, u)
            if k.bh < 3 or k.bw < 8:
                return True                 # no room for the drawing: the header is the pane
            x0, y0, x1, y1 = k.bx0, k.by0, k.bx1, k.by1
    if args:
        try:
            fn(s, x0, y0, x1, y1, t, lt, dur, u, **args)
            return True
        except TypeError:
            # a pane that does not accept the keyword is not an error: the schedule's annotations are
            # optional metadata and every pane must remain drawable without them
            pass
    fn(s, x0, y0, x1, y1, t, lt, dur, u)
    return True


# The motif bands are **gone** (batch 32). `MOTIF_IN` / `MOTIF_ALSO` / `MOTIF_SHARE` and the band
# helper `_motif(name, s, ...)` drew one of `school_motifs`' pictures a second time underneath the pane
# whose lyric it belonged to - while that same motif also had a pane of its own, registered below as
# `pane_motif_<name>`. Sixteen motifs therefore played twice. `_motif(name)` - the *pane* factory just
# below - is the one that stays, and the panes that used to borrow a band for motion now move on their own
# clock, because a pane that stops moving is what `_dev/clock_probe.py` exists to catch.


_palette()
