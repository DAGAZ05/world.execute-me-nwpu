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
        s.put(x0 + 2, y0, "\u26a0 ESD", _mix(ANOM, 0.5 + 0.5 * closed))
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
            s.put(x1 - 2, yy, "\u2713", _mix((120, 220, 160), 0.9))
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
        s.put(x0, y0 + int(t * 2.0) % n, "\u25b8", _mix(ANOM, 0.7))
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

    It sits after the gate (136.90-147.52) rather than in the first act, because it is the answer to the
    college the student just chose.
    """
    rows = [
        ("\u5927\u4e00", ["\u2605\u5d4c\u5165\u5f0f\u7535\u5b50\u5fae\u7cfb\u7edf",
                        "\u2605\u7a0b\u5e8f\u8bbe\u8ba1\u57fa\u7840\uff08C\uff09",
                        "\u2605\u6570\u636e\u7ed3\u6784",
                        "\u5fae\u79ef\u5206", "\u7ebf\u6027\u4ee3\u6570",
                        "\u667a\u80fd\u65f6\u4ee3\u7684\u8f6f\u5de5", "\u519b\u4e8b\u7406\u8bba",
                        "\u79bb\u6563\u6570\u5b66", "\u5927\u5b66\u7269\u7406"]),
        ("\u5927\u4e8c", ["\u2605\u9762\u5411\u5bf9\u8c61\uff08java\uff09", "\u2605\u8f6f\u4ef6\u5de5\u7a0b",
                        "\u2605\u8ba1\u7b97\u673a\u7f51\u7edc", "\u2605\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf",
                        "\u2605\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406", "\u2605\u6570\u636e\u5e93\u7cfb\u7edf",
                        "\u6570\u5b66\u5efa\u6a21", "\u4eba\u5de5\u667a\u80fd\u5bfc\u8bba", "\u6982\u7387\u8bba",
                        "\u590d\u53d8\u51fd\u6570", "\u8ba1\u7b97\u65b9\u6cd5", "\u6bdb\u6982", "\u4e60\u6982"]),
        ("\u5927\u4e09", ["\u2605\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406", "\u2605\u7b97\u6cd5\u8bbe\u8ba1",
                        "\u2605\u8f6f\u4ef6\u6d4b\u8bd5", "\u2605\u6df1\u5ea6\u5b66\u4e60",
                        "\u2605\u7f16\u8bd1\u539f\u7406",
                        "\u2605\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6", "\u4fe1\u53f7\u4e0e\u7ebf\u6027\u7cfb\u7edf",
                        "\u9a6c\u539f", "\u5de5\u4e1a\u6a21\u578b", "\u8f6f\u4ef6\u5f00\u53d1\u8bad\u7ec3"]),
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
        for ci, (year, courses) in enumerate(rows):
            cx = x0 + 1 + ci * cw
            s.put(cx, y0, _clip(year + (" \u25b8" if ci == active else ""), cw - 1),
                  _mix(ANOM, 0.95 if ci == active else 0.45))
            s.put(cx, y0 + 1, "\u2500" * max(1, cw - 2), _ui(0.25))
            walk = int(t * 3.0) % max(1, len(courses))
            for j, name in enumerate(courses):
                y = y0 + 2 + j
                if y > y1 - 3:
                    break
                if u < 0.04 + 0.10 * j + 0.05 * ci:
                    break
                star = name.startswith("\u2605")
                body = name[1:] if star else name
                if star:
                    col = _mix(AMBER, 0.95 if (ci == active and j == walk) else 0.75)
                else:
                    col = _ui(0.75 if (ci == active and j == walk) else 0.5)
                s.put(cx, y, _clip(("\u2605" if star else " ") + body, cw - 1), col)
            if u < 0.04 + 0.10 * len(courses):
                if int(t * 2) % 2 == 0:
                    s.put(cx, min(y1 - 3, y0 + 2 + len(courses)), "\u2588", _mix(ME_TEXT, 0.9))
        s.put(x0 + 1, y1 - 1, _clip("\u2605 = \u4f60\u8981\u91cd\u70b9\u8bb0\u7684\uff1b"
                                    "\u5176\u4f59\u662f\u540c\u4e00\u5b66\u671f\u4e00\u8d77\u4e0a\u7684",
                                    w - 2), _mix(ME_TEXT, 0.75))
        s.put(x0 + 1, y1, _clip("\u56db\u5e74\u7684\u8bfe\u8868\uff1a\u5927\u56db\u53ea\u5269"
                                "\u6bd5\u8bbe\u548c\u5b9e\u4e60", w - 2), _ui(0.5))
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
    """`all the execution` -> `only execution` (02:44.07-02:47.75): seven diagrams into one class.

    `02b` §4.3 calls this the core action of the software-engineering courseload, and it is also the
    song's own figure: "give them all" arrives, and what is left is "your only". **Seven** small diagrams
    - the seven the chat window names on this very line (`需求 · DFD · ER · 盒图 · 活动图 · 状态图 ·
    时序图`) - are laid out three to a row, each drawn small enough to read as its own notation, and then
    they collapse into a single UML class in the middle. The collapse is on `u`, so seeking into the pane
    lands mid-collapse in the same place playing into it would.

    The seventh arrived late: the pane drew six while the dialogue beside it listed seven, which batch 31's
    audit caught by counting the boxes and the words in the same frame.
    """
    import school_courses as _C
    w, h = x1 - x0, y1 - y0
    if w < 16 or h < 5:
        return
    titles = ["\u9700\u6c42", "DFD", "ER", "\u76d2\u56fe", "\u6d3b\u52a8\u56fe", "\u72b6\u6001\u56fe",
              "\u65f6\u5e8f\u56fe"]
    cols = 3
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
    glyphs = ["{ }", "\u25a1", ">_", "\u2261", "\u2207"]
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
          "\u25b8", _C._mix(_C.RED, 0.9))
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
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(min(cw, k.bw)):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(ox + c, oy + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
    elif name in SC.DIGITS:
        # the picture as binary digits, one per cell: `参考及想法/何尊.html`'s rule, on the pane's clock.
        # Drawn in the aspect-fitted `cols`x`rows`, not the whole box: the vessel is a tall drawing and a
        # 95x33 pane wants a 64x31 plate, so filling the box made `_fit` crop the mouth and the base off -
        # which is most of what makes it a vessel.
        got = SC.digit_cells(name, cols, rows, phase=phase)
        if got:
            cells, cw, ch = got
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(min(cw, k.bw)):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(ox + c, oy + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
    elif name in SC.SILHOUETTE:
        # a solid shape: the picture's alpha, one character, with its own luminance as the tone. For a
        # monument in white on white this is the only one of the three routes that reads - see
        # `school_sculpture.SILHOUETTE`.
        got = SC.silhouette_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(cw):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(ox + c, oy + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
    elif name in SC.LINE:
        # a drawing of *lines*: one glyph per cell a stroke passes through and nothing anywhere else,
        # which is the only route that works for the vector 何尊 and for 为国铸剑's white-on-white
        # sculpture. `stroke_cells` explains why the older glyph route cannot do it.
        got = SC.stroke_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(cw):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(ox + c, oy + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
    elif name in SC.GLYPH:
        got = SC.glyph_cells(name, cols, rows)
        if got:
            cells, cw, ch = got
            for r in range(min(ch, k.by1 - oy + 1)):
                for c in range(cw):
                    cell = cells[r][c]
                    if cell is None:
                        continue
                    ch_, lv = cell
                    k.put(ox + c, oy + r, ch_, _mix(BLUE, dim * (lv / 255)), 1.0)
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


def pane_landmark_dialogue(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`对话` - the machine hand and the human hand, not yet touching.

    Three lyric lines use this one work and each asks for a different crop of it, which is why the
    pane takes a `phase` rather than being three panes: `unite` shows both hands approaching, `deeply`
    shows the star between them, and `only God` shows the star alone with the hands gone.
    """
    import school_courses as _C
    phase = 0 if lt < 1.2 else (1 if lt < 2.4 else 2)
    titles = ("\u5bf9\u8bdd \u00b7 we can unite", "\u5bf9\u8bdd \u00b7 so deeply",
              "\u5bf9\u8bdd \u00b7 the only God")
    caps = ("\u4e24\u53ea\u624b\u8fd8\u6ca1\u78b0\u5230", "\u624b\u6307\u4e4b\u95f4\u90a3\u9897\u661f",
            "\u53ea\u5269\u90a3\u9897\u661f")
    k, ox, oy = _landmark("dialogue", s, x0, y0, x1, y1, u, titles[phase], caps[phase],
                          dim=1.0 if phase < 2 else 0.35)
    # the star: the one thing in this pane that moves, and it pulses on the song's beat
    if phase >= 1:
        cx = k.bx0 + k.bw // 2
        cy = max(k.by0, oy - 1)
        pulse = 0.55 + 0.45 * abs(math.sin(lt * 3.2))
        k.put(cx - 3, cy, "\u2727 \u2726 \u2727", _mix(_C.AMBER, pulse))
        if phase == 2:
            k.put(cx - 8, cy + 2, "\u4e0d\u662f\u63a5\u89e6\uff0c\u662f\u90a3\u9897\u661f", _ui(0.6))


def pane_landmark_sword(s, x0, y0, x1, y1, t, lt, dur, u) -> None:
    """`为国铸剑` - the figure holding the sword overhead.

    Used twice in the film with opposite meanings: at `Challenging your God` as the accusation, and
    over the twelve "Execution" hits as the thing being executed. The pane does not know which it is -
    it draws the work and a white sweep passes over it once per shot, which reads as a blade being
    drawn either way.
    """
    k, ox, oy = _landmark("sword", s, x0, y0, x1, y1, u, "\u4e3a\u56fd\u94f8\u5251",
                          "\u4e3e\u5251\u7684\u4e0d\u662f\u795e")
    # The sweep is on the pane's own clock, not on the reveal: on `u` it crosses the plate once, in the
    # last frame of the slot, and the pane - a photograph with a caption - is then still for the other
    # eleven seconds of it. On `lt` the blade is drawn again and again, which is what the plate is of.
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
    if k.bw > 46 and k.by0 + 1 <= k.by1:
        import school_courses as _C
        k.put(k.bx0 + 2, k.by0 + 1, "origin = \"\u5b85\u5179\u4e2d\u56fd\"", _mix(_C.AMBER, 0.85))
        k.put(k.bx0 + 2, k.by0 + 2, "// \u4f55\u5c0a\u94ed\u6587\uff0c\u7ea6\u516c\u5143\u524d 11 \u4e16\u7eaa"
                                     "\uff08\u5468\u6210\u738b\u4e94\u5e74\uff09", _ui(0.45))


def _kit(s, x0: int, y0: int, x1: int, y1: int, run: int = 0, title: str = ""):
    """A `school_courses._Kit` for a pane that wants the sections, columns and captions.

    The kit lives in `school_courses` because that is where the course diagrams are; a scene pane that
    wants a ruled section or a column split borrows it rather than growing a second, slightly different
    set of primitives (`_landmark` already does the same thing for its own title and caption).
    """
    from school_courses import _Kit
    return _Kit(s, x0, y0, x1, y1, title, run, 0, 1.0)


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
              "(|\u751f\u27e9 + |\u6b7b\u27e9) / \u221a2 \u2014\u2014 \u53e0\u52a0\u6001\u4e0d\u662f\u4e0d\u77e5\u9053\uff0c"
              "\u662f\u4e24\u4e2a\u90fd\u5728", _ui(0.5))
    # ...and something for the cat to watch: a dot circling its head on the song clock. The pane's only
    # motion used to be the motif band under it, and the cat is the one drawing here that is *alive*.
    ang = t * 1.5
    k.put(int(k.bx0 + 5 + 4 * math.cos(ang)), int(k.by0 + 3 + 3 * math.sin(ang)),
          "\u00b7", _mix(_C.GREEN, 0.7))


def pane_everything_point(s, x0, y0, x1, y1, t, lt, dur, u, panel: str = "") -> None:
    """万物皆点: three things that are points, and the picture each one actually has.

    `想法.md` gives this section four: 茄子＝USDA 营养流向图, 番茄＝番茄红素吸收光谱 (444/472/503 nm),
    猫＝薛定谔叠加态, 神＝∃!. The cat has its own pane; these are the other three, and they are drawn
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
        k.vline(x, hi, lo, "\u254c", _mix(_C.AMBER, 0.35))
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
    """`\u2203!` - the uniqueness proof, as the diagram it is: two candidates, one struck out."""
    import school_courses as _C
    k.section(k.by0, "\u795e \u00b7 \u2203! \u552f\u4e00\u5b58\u5728", 0.25)
    mid = k.by0 + 3
    if k.bh < 6:
        return
    k.put(k.bx0 + 2, mid, "\u2203 x", _mix(_C.GREEN, 0.9))
    k.put(k.bx0 + 2, mid + 2, "\u2203 y", _mix(_C.GREEN, 0.9))
    k.put(k.bx0 + 8, mid, "P(x)", _ui(0.7))
    k.put(k.bx0 + 8, mid + 2, "P(y)", _ui(0.7))
    k.put(k.bx0 + 8, mid + 1, "\u21d3", _mix(_C.AMBER, 0.9))
    k.put(k.bx0 + 12, mid + 1, "x = y", _mix(_C.AMBER, 0.95))
    # the two candidates are looked at one at a time, and the second one is struck out on the same
    # beat. A proof is a sequence of looks, not a still page, and this is the pane's half of the
    # parallelism the user asked for. The beat is a *position* on a 1.7 Hz clock and a *brightness* on
    # a continuous one: a two-state blink alone can land on the same phase at three samples of a short
    # slot, and then the pane reads as still to `_dev/clock_probe.py` even though it blinks.
    look = int(t * 1.7) % 2
    k.put(k.bx0, mid if not look else mid + 2, "\u25b8",
          _mix(_C.AMBER, 0.55 + 0.4 * abs(math.sin(t * 2.6))))
    # and the second candidate being struck out, which is the "!" in ∃!
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
    double cover of a day, the braid group σ₁, moiré, and the superellipse. The section had **no school
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
    """The braid group: σ₁ is two strands crossing, and its inverse undoes it."""
    import school_courses as _C
    k.section(k.by0, "\u8fab\u7fa4 \u03c3\u2081 \u00b7 \u53ef\u9006", 0.25)
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
    k.put(k.bx0, k.by1, "\u03c3\u2081 \u00b7 \u03c3\u2081\u207b\u00b9 = e", _mix(_C.GREEN, 0.7))


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
    # the field: nine points a row, each one going out on its own beat. The order is by distance from
    # the middle, so what is left at the end is the point the whole drawing is about - and it is a
    # function of `u`, not of a random number, so it is the same every time the second is played.
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
            k.put(x, y, "\u00b7", _C._ui(0.30))
    cx = k.bx0 + 2 + 4 * step_x
    cy = k.by0 + 2 + middle * 2
    beat = 0.62 + 0.38 * abs(math.sin(t * 2.1))
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
            k.put(x, y, "\u2591", _C._ui(0.34))
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
        band = max(4, min(k.bh - 2, 15))
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
