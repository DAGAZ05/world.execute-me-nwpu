"""The motifs from `想法.md` that the film had listed and never drawn.

`参考及想法/想法.md` is a list of eighteen sections of graphics the user wanted, roughly one line per
part of the song, and by batch 9 about half of them existed: the PCB traces, the five polyhedra, the
point set, the heart, the Voronoi shatter. This module is the other half - the ones that are a *second*
drawing inside a pane that already exists, because the pane owns that lyric and the motif belongs to it.

Two things make that possible without touching the panes themselves:

  * the panes in the first two acts were written for an eleven-row box and the layout now hands them
    thirty-three, so there is a band of empty rows under nearly every one of them; and
  * `school_scenes.draw_pane` finds that band by looking at the buffer (`_last_ink`) and draws the motif
    in it, which is the same mechanism the course panes use for their vocabulary footer.

**Parallel animation** is the point of the placement, not a side effect. A motif gets the pane's own
progress `u` for its reveal *and* the song's clock `t` for its own oscillation, so the host drawing and
the motif move on different clocks at the same time - the tree walking while the curve grows, the
epicycles turning while the heart is being written. The user's note was that the animations were
"monotone, not parallel"; a second clock inside the same box is the cheapest honest answer to it.

Every function here is `(k, t)` and pure in `t`: same time, same frame, seek or play.
"""
from __future__ import annotations

import math
from functools import lru_cache

import school_courses as _C

# a terminal cell is this many times taller than it is wide, so every circle in this file divides by it
_CA = 2.1

BOX_H = _C.BOX_H
BOX_V = _C.BOX_V


def _ph(t: float, period: float, offset: float = 0.0) -> float:
    """A 0..1 phase on the *song's* clock, which is what makes two drawings independent."""
    return (t / max(1e-6, period) + offset) % 1.0


def _ui(lv: float = 1.0):
    return _C._ui(lv)


def _mix(c, lv: float = 1.0):
    return _C._mix(c, lv)


def he_init(k, t: float) -> None:
    """He initialisation: `N(0, 2/n)` drawn as the histogram it is, and the envelope over it.

    The pane it sits in is `pane_power_on` - the line is "Switch on the power line", and the first thing
    a network does after power is draw its weights. The curve is the density `sqrt(n/4pi)·exp(-n x^2/4)`
    and the bars are a hundred deterministic draws from the same distribution, so the bars fill the
    curve rather than the other way round.
    """
    k.section(k.by0, "He \u521d\u59cb\u5316 N(0, 2/n)", 0.28)
    bins = max(12, min(48, k.bw - 10))
    span = k.by1 - k.by0 - 2
    if span < 2:
        return
    n = 9.0                                   # the fan-in of the layer being initialised
    counts = [0] * bins
    for i in range(400):
        # a deterministic normal: Box-Muller on a hash, so the histogram is the same every frame
        h1 = ((i * 2654435761 + 12345) & 0xFFFF) / 65536.0
        h2 = ((i * 40503 + 7919) & 0xFFFF) / 65536.0
        z = math.sqrt(-2 * math.log(max(1e-6, h1))) * math.cos(2 * math.pi * h2)
        x = z * math.sqrt(2.0 / n)             # the He scale
        b = int((x + 1.2) / 2.4 * bins)
        if 0 <= b < bins:
            counts[b] += 1
    top = max(counts) or 1
    for b, c in enumerate(counts):
        hgt = int(span * c / top * 0.92)
        x = k.bx0 + b
        for y in range(hgt):
            k.put(x, k.by1 - y, "\u2588", _mix(_C.BLUE, 0.45 + 0.01 * y))
    # the density, on the same axis, moving on its own clock: nothing about a distribution is static
    wob = 0.10 * math.sin(t * 1.7)
    for i in range(bins * 2):
        x = k.bx0 + i * 0.5
        xx = (i / (bins * 2.0) - 0.5) * 2.4
        d = math.exp(-n * xx * xx / 4.0) * (1.0 + wob * math.sin(xx * 6 + t * 2.0))
        y = int(k.by1 - span * d * 0.92)
        k.put(int(x), max(k.by0, min(k.by1, y)), "\u00b7", _mix(_C.AMBER, 0.85))
    k.put(k.bx0, k.by1, "\u00b1\u221a(2/n) = "
                        f"{math.sqrt(2.0 / n):.2f}   n = {int(n)}", _ui(0.55))


def rectifier(k, t: float) -> None:
    """Full-wave rectification and the RC filter: `|sin|` going in, a rippled flat line coming out."""
    k.section(k.by0, "\u5168\u6ce2\u6574\u6d41 |sin| \u00b7 RC \u6ee4\u6ce2", 0.28)
    n = max(20, k.bw - 8)
    hi = k.by0 + 1
    lo = k.by1 - 3
    if lo - hi < 3:
        return
    mid = (hi + lo) // 2
    k.hline(k.bx0 + 2, mid, k.bx0 + 2 + n - 1, BOX_V, _ui(0.18))
    k.vline(k.bx0 + 1, hi, lo, BOX_V, _ui(0.3))
    ph = t * 1.4
    keep = 0.0
    for i in range(n):
        f = i / max(1, n - 1)
        raw = abs(math.sin(2 * math.pi * (f * 3.0 + ph)))
        # The capacitor charges to the peak and sags between peaks, and the sag is *linear* in time -
        # `keep * 0.90` is proportional, so at this sample rate it sags slower than the sine falls and
        # the filter does nothing. `keep - 0.12` is the RC curve at this resolution, and it is the
        # difference between a rectifier with a filter and a rectifier.
        keep = max(raw, keep - 0.12)
        yr = mid - int((mid - hi) * raw * 0.9)
        yk = mid - int((mid - hi) * keep * 0.9)
        k.put(k.bx0 + 2 + i, yr, "\u00b7", _mix(_C.DIM, 0.7))
        k.put(k.bx0 + 2 + i, yk, "\u2500", _mix(_C.GREEN, 0.9))
    k.put(k.bx0 + 2, lo + 1, "|sin| \u8f93\u5165 \u00b7 \u7535\u5bb9\u4fdd\u6301\u5cf0\u503c", _ui(0.5))
    k.put(k.bx0 + 2, lo + 2, f"\u7eb9\u6ce2 {1 - keep:.2f} \u00b7 \u8d8a\u5927\u7684\u7535\u5bb9\u8d8a\u5e73",
          _mix(_C.AMBER, 0.7))


def phyllotaxis(k, t: float) -> None:
    """Sunflower phyllotaxis: `r = c\u221an`, `\u03b8 = n \u00b7 137.508\u00b0`, and the spiral nobody
    programmed.

    The golden angle is why the seeds do not line up: it is the worst-approximable number, so each
    seed lands in the largest gap left. Drawn as dots by density, turning slowly, because a still
    phyllotaxis looks like a mistake and a turning one looks inevitable.
    """
    k.section(k.by0, "\u5411\u65e5\u8475\u53f6\u5e8f \u03b8 = n \u00b7 137.508\u00b0", 0.28)
    cx = k.bx0 + min(20, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    rw = max(3, min(16, k.bw // 4))
    rh = max(2, min(14, (k.by1 - k.by0) // 3))
    if rh < 2:
        return
    ga = math.radians(137.507764)
    spin = t * 0.35
    n = 220
    for i in range(1, n):
        r = math.sqrt(i / n)
        a = i * ga + spin
        x = int(cx + rw * r * math.cos(a))
        y = int(cy + rh * r * math.sin(a))
        if k.bx0 <= x <= k.bx1 and k.by0 <= y <= k.by1:
            k.put(x, y, "\u00b7" if i % 3 else "\u2022",
                  _mix(_C.AMBER if i % 8 else _C.GREEN, 0.4 + 0.5 * (i / n)))
    k.put(k.bx0 + 2 * rw + 3, cy - 2, "137.508\u00b0 = 360\u00b0 \u00d7 (1 \u2212 1/\u03c6)", _ui(0.55))
    k.put(k.bx0 + 2 * rw + 3, cy - 1, "\u9ec4\u91d1\u89d2\uff1a\u6700\u96be\u8fd1\u4f3c\u7684\u65e0\u7406\u6570", _ui(0.5))
    k.put(k.bx0 + 2 * rw + 3, cy, "\u6240\u4ee5\u6bcf\u4e00\u7c92\u90fd\u843d\u5728", _ui(0.5))
    k.put(k.bx0 + 2 * rw + 3, cy + 1, "\u4e0a\u4e00\u7c92\u7559\u4e0b\u7684\u6700\u5927\u7f3a\u53e3\u91cc", _ui(0.5))


def byrne(k, t: float) -> None:
    """A plate from Byrne's Euclid: proposition I.47 with the squares on the sides, tilted.

    `想法.md` names "Byrne 版《几何原本》图版" for the 定义 section, and Byrne's plates are the reason
    to draw this rather than a formula: they are coloured, they are tilted, and the proof is the picture.
    The right triangle turns through `t`, so the three squares stay attached to their sides on their own
    clock while the pane's own reveal runs.
    """
    k.section(k.by0, "Byrne \u00b7 \u51e0\u4f55\u539f\u672c I.47", 0.28)
    # The plate has to *fit*: the triangle is (0,0), (3s,0), (0,4s) and the hypotenuse square reaches
    # 7s to the right and 7s down, so `s` is what the height allows - `(by1-by0)//5` was a third too
    # generous and the plate and its labels ran off the band (batch 31's audit measured it).
    s = max(2, min(6, (k.by1 - k.by0 - 4) // 7, k.bw // 16))
    cx = k.bx0 + min(26, k.bw // 2)
    cy = k.by0 + 3 + s
    a = 0.42 + 0.10 * math.sin(t * 0.8)          # the tilt, breathing
    ca, sa = math.cos(a), math.sin(a)

    def put(dx, dy, ch, lv):
        x = int(cx + dx * ca - dy * sa * 0.5)
        y = int(cy + dx * sa * 0.5 + dy * ca)
        k.put(x, y, ch, lv)

    p = ((0, 0), (3 * s, 0), (0, 4 * s))          # the 3-4-5 right triangle

    def seg(p0, p1, ch, lv):
        steps = max(1, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1])))
        for i in range(steps + 1):
            f = i / steps
            put(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, ch, lv)

    def square_on(p0, p1, sign, hatch, lv):
        """The square on the side `p0`-`p1`, *closed*: four edges, the outward quarter turn.

        `sign` picks the outward side (the plate's own orientation decides which that is, so it is given
        rather than guessed). The first version drew one interior line per leg square and no outline,
        so the thing advertised as "the squares on the sides" was not on screen at all.
        """
        nx, ny = sign * -(p1[1] - p0[1]), sign * (p1[0] - p0[0])
        c0, c1 = (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny)
        for q0, q1 in ((p0, p1), (p0, c0), (p1, c1), (c0, c1)):
            seg(q0, q1, "\u2500", lv)
        for j in range(1, 3):                     # one dotted diagonal, Byrne's hatching
            f = j / 3
            seg((p0[0] + nx * f, p0[1] + ny * f), (p1[0] + nx * f, p1[1] + ny * f),
                "\u00b7", hatch)

    square_on(p[0], p[1], -1, _mix(_C.GREEN, 0.35), _mix(_C.GREEN, 0.75))     # the leg on the x axis
    square_on(p[0], p[2], +1, _mix(_C.BLUE, 0.35), _mix(_C.BLUE, 0.75))      # the leg on the y axis
    square_on(p[1], p[2], -1, _mix(_C.AMBER, 0.35), _mix(_C.AMBER, 0.85))    # the hypotenuse
    for i in range(3):
        seg(p[i], p[(i + 1) % 3], "\u2500", _mix(_C.INK, 0.9))
    # the two labels are placed in the band, not at screen offsets from a tilted origin - that is how
    # they ended up outside the pane and clipped to "\u00b7\u00b7\u00b7" on a short window
    k.put(k.bx0 + 1, k.by1 - 1, "a\u00b2 + b\u00b2 = c\u00b2    3 \u00b7 4 \u00b7 5",
          _mix(_C.AMBER, 0.9))


def quantize(k, t: float) -> None:
    """`2\u2075\u00b3`: the last integer a double can hold exactly, and the gap after it.

    `想法.md` asks for "2\u2075\u00b3 \u5904\u7684\u6d6e\u70b9\u91cf\u5316" in the 定义 section and it is the most
    on-theme drawing in the list for this film: the whole song is about a world that executes what it
    is told, in a machine that cannot represent most of the numbers it is told. The dots are the
    representable integers; the gap opens where they stop being one apart.
    """
    k.section(k.by0, "2\u2075\u00b3 \u5904\u7684\u91cf\u5316", 0.28)
    y = (k.by0 + k.by1) // 2
    if k.bw < 20:
        return
    n = k.bw - 6
    k.put(k.bx0, y - 2, f"2\u2075\u00b3 = {2 ** 53}", _mix(_C.AMBER, 0.9))
    # The axis is **compressed and says so**. A linear number line cannot show this at all: the gap is 2
    # right after 2^53 and the next doubling is 2^53 further along, so 90 cells of linear axis show one
    # octave and then nothing. What is drawn instead is the *spacing itself*, one segment per octave.
    # The first version instead doubled the gap twelve times along a linear axis and labelled it as the
    # number line (batch 31's audit: "not the double model"), which claimed something false about both.
    seg = max(1, min(12, n // 7))
    for i in range(n):
        f = i / max(1, n - 1)
        gap = 2.0 ** min(12, int(f * seg))
        x = k.bx0 + 2 + i
        on = (i % max(1, int(gap))) == 0
        k.put(x, y, "\u2022" if on else "\u00b7", _mix(_C.BLUE if on else _C.DIM, 0.85 if on else 0.3))
    k.put(k.bx0 + 2, y + 2, "\u95f4\u8ddd 1 \u00b7 2 \u00b7 4 \u00b7 8 \u2026\uff08\u6a2a\u8f74\u5df2\u538b\u7f29\uff09",
          _ui(0.5))
    k.put(k.bx0 + int(n * 0.42), y + 2, "\u6bcf\u7ffb\u4e00\u500d\uff0c\u80fd\u7cbe\u786e\u8868\u793a\u7684\u6570"
                                        "\u5c31\u7a00\u4e00\u500d", _mix(_C.RED, 0.8))
    # ...and a cursor walks the number line. This drawing had **no clock at all** while it was a band
    # under `pane_landmark_sword`, which was fine there - the host pane moved - and is not fine now that
    # `pane_motif_<name>` can be a pane of its own ("禁止重复" needed more drawings, so the motifs became
    # panes). `_dev/clock_probe.py` is what asks, and a pane that never moves is a still frame.
    k.put(k.bx0 + 2 + int((t * 7.0) % max(1, n)), y - 1, "\u25bc", _mix(_C.AMBER, 0.9))


@lru_cache(maxsize=1)
def _dijkstra_anchor() -> float:
    """When `pane_motif_dijkstra`'s own row starts, read out of the school's schedule.

    Read rather than written here so that re-timing the row re-phases the drawing with it. Only the
    school schedules this motif (`school_motifs.draw_motif`'s band route was removed in batch 32), so a
    miss cannot happen in a real frame and falls back to the song's first frame.
    """
    try:
        import school_panels as _SP
        for r in _SP.shot_rows():
            if r.get("name") == "pane_motif_dijkstra":
                return float(r["at"])
    except Exception:
        pass
    return 0.0


# ------------------------------------------------------------------ the algorithm, not a picture of one
#
# Batch 49. The pane used to draw `Dijkstra 裂纹`: a crack grown along the least-cost route over a hash
# field, with a real Dijkstra *inside* it (`_crack_path`) deciding the route. The user's note on seeing
# it: "我要求的 dijkstra 是 dijkstra 算法，不是裂纹" - a drawing whose subject is a crack teaches
# nothing about the algorithm, and the algorithm was hidden in a helper nobody could see. What follows
# is the run itself: a weighted graph, the frontier closing, and every label change on screen.
#
# Six nodes on a 3x2 lattice, so each edge is one straight run of cells (`─`, `│`, `╲`) and its weight
# has a cell to sit in. `S -> T` costs 7 (S-A-C-T); the diagonal S-C is there to be *relaxed and lose*,
# and T->D is the last relaxation that improves nothing - both are steps a viewer can read off the table.

_D_NODES = ("S", "A", "D", "B", "C", "T")
#: node -> (column, row) on the lattice
_D_AT = {0: (0, 0), 1: (1, 0), 2: (2, 0), 3: (0, 1), 4: (1, 1), 5: (2, 1)}
#: (a, b, weight) - undirected, and the run relaxes both ends
_D_EDGES = ((0, 1, 4), (1, 2, 5), (0, 3, 2), (1, 4, 1), (2, 5, 2), (3, 4, 8), (4, 5, 2), (0, 4, 10))
#: seconds per step; 15 steps is 2.25 s, which is the visible life of the row (see `school_panels`)
_D_STEP = 0.15
_D_HOLD = 0.7                    # how long the finished run sits before the wave starts again


@lru_cache(maxsize=1)
def _dijkstra_run():
    """Dijkstra from `S`, as one snapshot per step: `[(settled, dist, parent, step), ...]`.

    A real run - take the unsettled node with the smallest tentative distance, then relax every edge
    out of it - and the **snapshots are the drawing**, because the algorithm is the picture: which nodes
    are settled, what every label currently says, and which edge is being looked at right now. `step` is
    `("lift", u, None, 0, True)` or `("relax", u, v, w, improved)`.

    The first snapshot is the initial state (`d[S] = 0`, everything else unknown), so `len(run)` is one
    more than the number of steps and the drawing indexes it directly.
    """
    n = len(_D_NODES)
    dist: list = [None] * n
    parent: list = [None] * n
    dist[0] = 0
    settled: set = set()
    run = [(frozenset(settled), tuple(dist), tuple(parent), None)]
    while len(settled) < n:
        cand = [i for i in range(n) if i not in settled and dist[i] is not None]
        if not cand:
            break
        u = min(cand, key=lambda i: dist[i])
        settled.add(u)
        run.append((frozenset(settled), tuple(dist), tuple(parent), ("lift", u, None, 0, True)))
        for a, b, w in _D_EDGES:
            v = b if a == u else (a if b == u else None)
            if v is None or v in settled:
                continue
            nd = dist[u] + w
            old = dist[v]
            better = old is None or nd < old
            if better:
                dist[v] = nd
                parent[v] = u
            run.append((frozenset(settled), tuple(dist), tuple(parent),
                        ("relax", u, v, w, better, old)))
    return tuple(run)


def _seg(k, x0: int, y0: int, x1: int, y1: int, colour) -> None:
    """A straight run of line glyphs between two cells: `─`, `│`, `╲` or `╱`, whichever the slope is."""
    dx, dy = x1 - x0, y1 - y0
    steps = max(abs(dx), abs(dy))
    if steps <= 0:
        return
    ch = "\u2500" if dy == 0 else ("\u2502" if dx == 0 else
                                   ("\u2572" if (dx > 0) == (dy > 0) else "\u2571"))
    for i in range(steps + 1):
        k.put(x0 + int(round(dx * i / steps)), y0 + int(round(dy * i / steps)), ch, colour)


def dijkstra_route(k, t: float) -> None:
    """`Dijkstra 最短路` - the algorithm running, one relaxation at a time.

    Left: the graph, with the settled set, the frontier and the shortest-path tree as they stand. Right:
    the label table (`d[v]` and `π[v]`), which is where the algorithm's actual output lives - the
    numbers change on screen and a viewer can check the arithmetic of the step named in the footer.
    """
    run = _dijkstra_run()
    k.section(k.by0, "\u6bcf\u6b21\u53d6 d \u6700\u5c0f\u7684\u672a\u5b9a\u8282\u70b9\uff0c"
                     "\u677e\u5f1b\u5b83\u7684\u6bcf\u6761\u8fb9", 0.28)
    if k.bw < 46 or k.bh < 6:
        return
    cycle = len(run) * _D_STEP + _D_HOLD
    i = min(len(run) - 1, int(((t - _dijkstra_anchor()) % cycle) / _D_STEP))
    settled, dist, parent, step = run[i]
    cur = step[1] if step else None
    edge_now = (min(step[1], step[2]), max(step[1], step[2])) if step and step[2] is not None else None

    t0, b0 = k.by0 + 1, k.by1
    gw = max(30, int(k.bw * 0.56))
    gx = (k.bx0 + 3, k.bx0 + gw // 2, k.bx0 + gw - 3)
    gr = (t0 + 1, max(t0 + 5, b0 - 2))
    tree = {(min(parent[v], v), max(parent[v], v))
            for v in range(len(_D_NODES)) if parent[v] is not None}

    # ---- the edges and their weights, then the same edges again for the state they are in
    for a, b, w in _D_EDGES:
        (ca, ra), (cb, rb) = _D_AT[a], _D_AT[b]
        key = (min(a, b), max(a, b))
        if key == edge_now:
            col = _mix(_C.RED, 1.0 if step[4] else 0.45)
        elif key in tree:
            col = _mix(_C.BLUE, 0.95)
        else:
            # `_ui` carries the film's global drain and it is at 0.42 by 02:22, so an un-settled edge
            # has to ask for a high level to be a line at all: at 0.28 this graph read as an empty box
            # (measured on the rendered frame, batch 49).
            col = _ui(0.62)
        if ra == rb:                                        # a horizontal edge on one of the two rows
            _seg(k, gx[ca] + 1, gr[ra], gx[cb] - 1, gr[rb], col)
        elif ca == cb:                                      # a vertical edge in one of the columns
            _seg(k, gx[ca], gr[ra] + 1, gx[cb], gr[rb] - 1, col)
        else:                                               # the one diagonal, S -> C
            sx = 1 if cb > ca else -1
            sy = 1 if rb > ra else -1
            _seg(k, gx[ca] + sx, gr[ra] + sy, gx[cb] - sx, gr[rb] - sy, col)
        # the weight, off the line rather than on it: above a top row, below a bottom one, beside a
        # vertical, and below-left on the diagonal
        if ra == rb:
            wy = gr[ra] - 1 if ra == 0 else gr[ra] + 1
            k.put((gx[ca] + gx[cb]) // 2, wy, str(w), _ui(0.72) if key != edge_now else col)
        elif ca == cb:
            k.put(gx[ca] + 2, (gr[0] + gr[1]) // 2, str(w), _ui(0.72) if key != edge_now else col)
        else:
            k.put((gx[ca] + gx[cb]) // 2 - 3, (gr[0] + gr[1]) // 2 + 1, str(w),
                  _ui(0.6) if key != edge_now else col)

    # ---- the nodes
    for v, name in enumerate(_D_NODES):
        cx, ry = gx[_D_AT[v][0]], gr[_D_AT[v][1]]
        if v in settled:
            col = _mix(_C.AMBER, 1.0) if v == cur else _mix(_C.BLUE, 1.0)
        elif dist[v] is not None:
            col = _mix(_C.AMBER, 0.8)
        else:
            col = _ui(0.5)
        k.put(cx, ry, name, col)

    # ---- the label table: the algorithm's output, and the only place the numbers are written down
    tx = k.bx0 + gw + 2
    if tx < k.bx1 - 6:
        k.put(tx, t0, "d[v]  \u03c0[v]", _ui(0.6))
        for v, name in enumerate(_D_NODES):
            y = t0 + 1 + v
            if y > gr[1]:
                break
            if v in settled:
                col, word = _mix(_C.BLUE, 0.95), "\u5df2\u5b9a"
            elif dist[v] is not None:
                col, word = _mix(_C.AMBER, 0.85), "\u524d\u6cbf"
            else:
                col, word = _ui(0.35), "\u672a\u8fbe"
            if v == cur:
                col = _mix(_C.RED, 1.0)
            num = "--" if dist[v] is None else f"{dist[v]:>2}"
            par = "-" if parent[v] is None else _D_NODES[parent[v]]
            k.put(tx, y, f"{name} {num}   {par}   {word}", col)
        k.put(tx, t0 + 1 + len(_D_NODES) + 1,
              f"\u6b65 {i:>2}/{len(run) - 1}  d[T] = "
              + ("--" if dist[5] is None else str(dist[5])), _ui(0.6))

    # ---- the footer says what this step *is*, so the numbers can be checked against it
    if step is None:
        foot = "\u521d\u59cb\u5316\uff1ad[S]=0\uff0c\u5176\u4f59\u672a\u77e5"
    elif step[0] == "lift":
        foot = (f"\u53d6\u51fa {_D_NODES[step[1]]}\uff08d = {dist[step[1]]}\uff09"
                f"\uff0c\u5b83\u5df2\u786e\u5b9a")
    else:
        _, u, v, w, better, old = step
        foot = (f"\u677e\u5f1b {_D_NODES[u]}\u2192{_D_NODES[v]}\uff1a{old if old is not None else '--'}"
                f" \u2192 {dist[u]} + {w} = {dist[u] + w}"
                + ("\uff0c\u66f4\u65b0" if better else "\uff0c\u4e0d\u6539\u5584"))
    k.put(k.bx0, b0, foot, _ui(0.62))


def epicycles(k, t: float) -> None:
    """Fourier epicycles: circles on circles drawing a heart, and the coefficients that do it.

    The one motif in the list that is *both* the maths and the joke of this film: any curve is a sum of
    rotations, and this one is a sum of rotations that comes out as a heart. Each circle turns at its own
    harmonic, which is the parallel animation the pane inside a pane can show at its clearest.
    """
    k.section(k.by0, "\u5085\u91cc\u53f6\u672c\u8f6e \u00b7 \u5fc3\u5f62\u7684\u5206\u89e3", 0.28)
    # Separate x and y scales, in the ratio a cell actually has: a terminal cell is ~2x taller than it
    # is wide, so `sy = sx / 2` draws the circles round *on screen* and the heart un-squashed. The first
    # version used 11 and 4 (a 2.75:1 stretch) and took its width from `bw // 8` regardless of height.
    sx = max(4, min(20, k.bw // 8, k.bh - 4))
    sy = max(2.0, sx / 2.0)
    cx = k.bx0 + sx + 4
    cy = (k.by0 + k.by1) // 2 + 1
    # the heart, as a parametric sum of rotations: c_n ~ 1/|n| with a phase, which is what makes the
    # little circles worth drawing instead of a formula
    # The heart's **own** Fourier coefficients, not five numbers that look like a heart. `z(t) = x + iy`
    # with the standard heart (`x = 16 sin³t`, `y = 13cos t - 5cos2t - 2cos3t - cos4t`) integrated over
    # one period gives exactly these terms; the previous list (1.0/0.55/0.32/0.20/0.12 with made-up
    # phases) drew a self-intersecting tangle while the title said "心形的分解" (batch 31's audit measured
    # the crossing and the missing cusp). Scale = 1/23, the sum of |c_n|, so the curve spans ±1.
    #
    # **The harmonics were conjugated**, and that is why the heart hung upside down: the amplitudes were
    # right and the *sign of every harmonic* was reversed, which is a reflection of the curve about the
    # real axis. Measured by batch 37's maths audit against the closed form: the list as written came out
    # top +0.739 / bottom -0.518 (cusp on top - a spade), the conjugated list +0.518 / -0.739 (cusp on
    # the bottom - a heart), and the mean distance to the true curve is **0.0001 against 0.1726**. The
    # same reversal also put the phase offsets on the wrong side, so both are flipped below.
    terms = [(0.5435, -1, 1.5708), (0.1087, -2, -1.5708), (0.1304, -3, -1.5708),
             (0.0217, 1, 1.5708), (0.1087, 2, -1.5708), (0.0435, 3, 1.5708),
             (0.0217, -4, -1.5708), (0.0217, 4, -1.5708)]
    n_pts = 48
    path = []
    for i in range(n_pts + 1):
        th = 2 * math.pi * i / n_pts
        x = y = 0.0
        for amp, harm, phs in terms:
            x += amp * math.cos(harm * th + phs)
            y += amp * math.sin(harm * th + phs)
        path.append((x, y))
    draw_to = int(len(path) * min(1.0, (t % 5.0) / 4.0))
    px = py = 0.0
    for amp, harm, phs in terms:
        th = harm * 2 * math.pi * (t * 0.5) + phs
        k.put(int(cx + px - amp * sx), int(cy + py), "\u25cb" if amp * sx > 1 else "\u00b7", _ui(0.25))
        for a in range(0, 360, 24):
            aa = math.radians(a)
            k.put(int(cx + px + amp * sx * math.cos(aa)),
                  int(cy + py + amp * sy * math.sin(aa)), "\u00b7", _ui(0.15))
        px += amp * math.cos(th)
        py += amp * math.sin(th)
    for x, y in path[:draw_to]:
        k.put(int(cx + x * sx), int(cy + y * sy), "\u2022", _mix(_C.RED, 0.9))
    k.put(cx + sx + 6, cy - 1, "\u4efb\u4f55\u66f2\u7ebf\u90fd\u662f", _ui(0.55))
    k.put(cx + sx + 6, cy, "\u4e00\u5806\u5300\u901f\u65cb\u8f6c\u4e4b\u548c", _ui(0.55))
    k.put(cx + sx + 6, cy + 2, "\u5305\u62ec\u8fd9\u4e2a", _mix(_C.RED, 0.85))


def hearts9(k, t: float) -> None:
    """**One** heart curve, big - "心形曲线可以只画1个大的".

    This was nine: `想法.md` lists five heart formulae and asks for nine, so it drew a 3x3 contact sheet
    of tiny dotted loops with nine equations printed over them. The user's note at this batch is
    "有些演出太复杂导致图像精细度不够，可以进行简化，重点放在细节刻画（比如心形曲线可以只画1个大的）", and
    they are right about the cause: at a band's height each cell of that sheet had three rows, so every
    heart was a dash and the equations overlapped. Nine shapes at three rows each is not nine times the
    information, it is no information - what the sheet was for ("同一个形状，九个方程") survives as one
    line of text under one heart that can actually be seen.

    The curve is `r = 1 - sin θ`: the one polar heart everybody recognises, with the cusp at the top and
    the point at the bottom. It is drawn at the band's own size with the cell aspect divided out, so it is
    a heart rather than a squashed heart, and with a second contour inside it at 0.82 - two passes are
    what give a curve *weight* at terminal resolution. The whole thing breathes, so the pane's clock
    (`_dev/clock_probe.py`) sees it move.
    """
    k.section(k.by0, "\u5fc3\u5f62\u66f2\u7ebf r = 1 \u2212 sin \u03b8", 0.28)
    if k.bw < 14 or k.bh < 5:
        return
    # The heart hangs *below* its cusp: `r = 1 - sin θ` is 0 at the top (the notch) and 2 at the bottom
    # (the point), so `cy` is the top of the drawing rather than its middle - the first version centred
    # `cy` and clipped the point off the bottom of every box. Both radii come from what is left: the width
    # is `2 rx` and the height `2 ry`, and a cell is `_CA` times taller than it is wide.
    cx = k.bx0 + k.bw // 2
    cy = k.by0 + 2
    room = max(4, (k.by1 - cy) - 1)
    ry = max(3, min(room // 2, int((k.bw // 2 - 2) / _CA)))
    rx = max(5, int(ry * _CA))
    beat = 0.62 + 0.38 * abs(math.sin(t * 1.9))
    for i in range(0, 360, 2):
        th = math.radians(i)
        r = 1.0 - math.sin(th)
        x = cx + int(rx * r * math.cos(th))
        y = cy - int(ry * r * math.sin(th))
        k.put(x, y, "\u00b7", _mix(_C.RED, beat))
        if i % 6 == 0:                              # every third sample again, brighter: the contour
            k.put(x, y, "\u2022", _mix(_C.RED, min(1.0, beat + 0.25)))
    for i in range(0, 360, 3):                      # the inner contour, the curve's own body
        th = math.radians(i)
        r = (1.0 - math.sin(th)) * 0.82
        k.put(cx + int(rx * r * math.cos(th)), cy - int(ry * r * math.sin(th)),
              "\u00b7", _mix(_C.VIOLET, 0.34 + 0.2 * beat))
    k.put(k.bx0, k.by1, "\u540c\u4e00\u4e2a\u5f62\u72b6\uff0c\u4e5d\u4e2a\u65b9\u7a0b\uff1a"
                        "\u6ca1\u6709\u54ea\u4e2a\u662f\u201c\u5bf9\u201d\u7684", _ui(0.5))


def fork_bomb(k, t: float) -> None:
    """The fork bomb, drawn as the doubling it actually is: one process, then two, then 4096.

    `想法.md` asks for `:(){ :|:& };:` growing under 处决, and the doubling is the whole drawing - what
    makes a fork bomb a fork bomb is that the count explodes. 4096 = 2\u00b9\u00b2, so the drawing needs
    **twelve** generations and one row each; the first version spent two rows per generation and stopped
    at six, so its own counter could never pass 64 while the title promised 4096 (batch 31's audit:
    "never reaches the generation its title names"). Past ~32 children a row can no longer hold one dot
    per process, so those generations are drawn as a bar whose length is the generation - the count on
    the right is what carries the number, and it *is* the number.
    """
    k.section(k.by0, "fork \u70b8\u5f39 \u00b7 1 \u2192 4096", 0.28)
    depth = max(1, min(12, k.by1 - k.by0 - 1))
    # the generation is the pane's own progress, not `t % 4`: the course panes live for 0.83 s and the
    # absolute clock put a different generation in each of them for no reason at all.
    #
    # ...and it *rolls* on the song clock as well, which it did not have to while this was a band: as a
    # pane it has to move for `_dev/clock_probe.py`, whose samples pin `u` and vary `t`, and a fork bomb
    # that keeps re-forking every couple of seconds is what the drawing is about anyway.
    gen = int(min(depth, ((t * 0.35) % 1.0) * (depth + 1)))
    w = k.bw - 22
    if w < 12:
        return
    x0, y0 = k.bx0, k.by0 + 1
    for g in range(gen + 1):
        n = 2 ** g
        y = y0 + g
        if y > k.by1 - 1:
            break
        if n * 2 <= w:                               # one dot per process still fits
            step = max(1, w // (n * 2))
            for i in range(n):
                x = x0 + 2 + i * step * 2
                if x > k.bx1 - 20:
                    break
                k.put(x, y, "\u25cf", _mix(_C.GREEN if g == gen else _C.BLUE, 0.85))
        else:                                        # ...it does not: the generation as a bar
            fill = max(1, int((k.bw - 24) * g / depth))
            k.put(x0 + 2, y, "\u2588" * fill, _mix(_C.GREEN if g == gen else _C.BLUE, 0.7))
    k.put(k.bx1 - 18, k.by0 + 1, f"\u4ee3 {gen}", _mix(_C.AMBER, 0.9))
    k.put(k.bx1 - 18, k.by0 + 2, f"{2 ** gen:5d} \u8fdb\u7a0b", _mix(_C.RED, 0.9))
    # Batch 49, the user: "fork 炸弹下面的文字中有乱码（？）". It was not mojibake - it was the fork
    # bomb's own one-liner, drawn correctly - but ` :(){ :|:& };:` **reads** as corruption: twelve cells
    # of punctuation with no word attached. On a screen where everything else is a labelled drawing, a
    # bare shell definition is indistinguishable from a decoding failure, so the line says what it is and
    # what it does, and the one-liner is kept as the thing being named rather than as the whole caption.
    k.put(k.bx0, k.by1, "\u672c\u4f53  :(){ :|:& };:  \u2014\u2014 \u81ea\u5df1\u8c03\u7528\u81ea"
                        "\u5df1\uff0c\u5341\u4e8c\u4ee3\u7ffb\u5230 4096", _ui(0.55))


def sine(k, t: float) -> None:
    """`sin x` and its tangent envelope, drawn.

    The user's note for this batch: "动图部分以视觉效果优先，比如优先画 sin(x) 的函数图像而不是写表达式
    f=sin(x)". This is that note taken literally - the motif *is* the plot, and the only text on it is
    the axis. `想法.md` asks for "sin θ 与切线包络" in the 定义 section, so the envelope is drawn too:
    the two lines y=±1 that the curve touches, and the tangent at the point that is moving, which is
    where the word "envelope" comes from.
    """
    k.section(k.by0, "sin x \u4e0e\u5207\u7ebf\u5305\u7edc", 0.28)
    n = max(20, k.bw - 6)
    hi, lo = k.by0 + 2, k.by1 - 3
    if lo - hi < 4:
        return
    mid = (hi + lo) // 2
    amp = max(2, (lo - hi) // 2 - 1)
    k.hline(k.bx0, mid, k.bx0 + n - 1, BOX_H, _ui(0.18))
    for i in range(n):                                   # the curve
        x = k.bx0 + i
        ph = (i / max(1, n - 1)) * 4 * math.pi + t * 0.9
        y = mid - int(amp * math.sin(ph))
        k.put(x, max(hi, min(lo, y)), "\u2022", _mix(_C.BLUE, 0.9))
    k.hline(k.bx0, mid - amp, k.bx0 + n - 1, "\u00b7", _mix(_C.GREEN, 0.45))
    k.hline(k.bx0, mid + amp, k.bx0 + n - 1, "\u00b7", _mix(_C.GREEN, 0.45))
    k.put(k.bx0 + n - 10 if k.bw > 30 else k.bx0, mid - amp, "y = \u00b11", _mix(_C.GREEN, 0.8))
    # the tangent at the moving point: the tangent to sin at p is y = cos(p)(x-p) + sin(p)
    p = (t * 0.9) % (4 * math.pi)
    i0 = int((p / (4 * math.pi)) * (n - 1))
    # **The curve's own phase at that column**, not `p`: the curve is `sin(ph)` with
    # `ph = i/(n-1)*4pi + t*0.9`, so evaluating the dot (and the tangent) at `p` puts the time term in
    # twice and the red dot sits off the curve - which is what the user reported in batch 34
    # ("sin 曲线红点的位置没有沿在曲线上").
    ph0 = (i0 / max(1, n - 1)) * 4 * math.pi + t * 0.9
    for i in range(n):                                   # only the stretch that is on screen
        dx = i - i0
        yy = math.sin(ph0) + math.cos(ph0) * (dx * (4 * math.pi / max(1, n - 1)))
        y = mid - int(amp * yy)
        if hi <= y <= lo:
            k.put(k.bx0 + i, y, "\u2500", _mix(_C.AMBER, 0.55))
    y0 = mid - int(amp * math.sin(ph0))
    k.put(k.bx0 + i0, max(hi, min(lo, y0)), "\u25cf", _mix(_C.RED, 0.95))
    k.put(k.bx0, k.by1, "\u66f2\u7ebf\u78b0\u5230\u7684\u4e24\u6761\u76f4\u7ebf\uff0c\u5c31\u662f\u5b83\u7684"
                        "\u5305\u7edc", _ui(0.5))


def chladni(k, t: float) -> None:
    """A Chladni figure: sand on a vibrating plate, collecting on the lines that do not move.

    `想法.md` asks for "百万沙粒的克拉尼图形" under 振动, and it is the best fit of anything left on the
    list for a character grid, because it is already a *density*: the plate's displacement is
    `cos(n\u03c0x)cos(m\u03c0y) - cos(m\u03c0x)cos(n\u03c0y)`, sand leaves the parts that move and piles on the
    nodal lines, and a shaded cell is exactly how much sand is there. The mode numbers walk, so the
    figure changes shape the way a real plate does when the frequency is swept.
    """
    k.section(k.by0, "\u514b\u62c9\u5c3c\u56fe\u5f62 \u00b7 \u6c99\u5728\u4e0d\u52a8\u7684\u7ebf\u4e0a", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 10 or h < 4:
        return
    m = int(t * 0.35) % 4 + 1
    n = int(t * 0.22) % 5 + 2
    # The plate is the band's own rectangle, and the comment here used to claim a *square* sample grid -
    # which is not what the code does. `fx` and `fy` are both divided by the same `S`, so the pattern is
    # not distorted (a circle in (fx, fy) is a circle on screen); what is rectangular is the *plate*, at
    # `w` cells by `2h` pixels - 95x50 px at the pane's own size, i.e. 1.83:1. That is not a defect: the
    # same shape functions `cos(nπx)cos(mπy) - cos(mπx)cos(nπy)` with coordinates normalised to the plate
    # are the standard **rectangular**-plate modes, and drawing them across the full band is what makes
    # the figure fill the pane instead of sitting in a square in the middle of it. (Batch 37 measured this
    # with a ruler that counts only shape glyphs: 1.77:1 - and `bessel`, which really was distorted at
    # 3.41:1, is the one that got fixed.)
    S = max(w, 2 * h)
    for j in range(h):
        y = k.by0 + 1 + j
        fy = (j + 0.5 - h / 2) * 2 / S
        for i in range(w):
            x = k.bx0 + i
            fx = (i + 0.5 - w / 2) / S
            v = (math.cos(n * math.pi * fx) * math.cos(m * math.pi * fy)
                 - math.cos(m * math.pi * fx) * math.cos(n * math.pi * fy))
            a = min(1.0, abs(v))
            # Sand leaves the parts that move and piles on the lines that do not, so the *nodal* cells
            # are the dense ones and the moving cells are nearly empty. The first version selected the
            # character with `" ░▒▓█" if a > 0.22 else "█"` - a five-character *string* used as one
            # character, which put five cells in every cell and printed the pane as solid blocks.
            if a <= 0.22:
                k.put(x, y, "\u2588", _mix(_C.AMBER, 0.9))
            else:
                k.put(x, y, "\u2591\u2592\u2593 " [min(3, int((a - 0.22) / 0.78 * 3.99))],
                      _mix(_C.BLUE, 0.25 + 0.35 * a))
    k.put(k.bx0, k.by1, f"\u6a21\u5f0f n={n} m={m}\uff1a\u6c99\u5806\u5728\u8282\u7ebf\u4e0a", _ui(0.5))


def moire(k, t: float) -> None:
    """Moiré: two grids of the same pitch, one of them turned, and the pattern neither one contains.

    The other motif from the list that a character grid draws better than a photograph does. Two line
    gratings at a small angle to each other produce fringes whose spacing is `p / (2 sin(\u03b8/2))` - which
    means a one-degree difference produces fringes thirty times the pitch. The second grid's angle
    breathes, so the fringes sweep across the pane and the picture is *about* interference.
    """
    k.section(k.by0, "\u83ab\u5c14\u6761\u7eb9 \u00b7 \u4e24\u5c42\u5149\u6805", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 10 or h < 4:
        return
    ang = 0.05 + 0.16 * (0.5 + 0.5 * math.sin(t * 0.5))       # the second grating's angle
    ca, sa = math.cos(ang), math.sin(ang)
    pitch = 3.0
    # ...and the fringe the formula predicts, in cells, printed with it. The audit measured the pane's
    # column period as a constant 2*pitch (6.2 cells) - grating A's own period - because the fringe was
    # drawn as "both gratings open", which is dominated by A. The fringe *is* where the two disagree, so
    # it is drawn as the XOR, and the number beside the formula is the width it should have.
    fringe = pitch / (2 * math.sin(ang / 2)) if ang > 1e-6 else 0.0
    for j in range(h):
        y = k.by0 + 1 + j
        if j % 2:                                 # every other row: see below
            continue
        for i in range(w):
            x = k.bx0 + i
            a = 1 if int((i / pitch) % 2) == 0 else 0          # the horizontal grating
            u_ = (i - w / 2) * ca - (j - h / 2) * sa
            b = 1 if int((u_ / pitch) % 2) == 0 else 0
            # What the eye sees is where the *two* gratings disagree: that is the fringe. Drawing a
            # cell for "either grating open" instead fills half the pane with a half-tone and the fringes
            # disappear into it; drawing every row at full strength then made the panel the loudest thing
            # in the frame, which is the clutter the user's note is about. Every other row, and the
            # fringes read the same.
            if a != b:
                k.put(x, y, "\u2588", _mix(_C.VIOLET, 0.62))
            else:
                k.put(x, y, "\u00b7", _mix(_C.VIOLET, 0.14))
    k.put(k.bx0, k.by1, f"\u5939\u89d2 {math.degrees(ang):4.1f}\u00b0\uff1a"
                        f"\u6761\u7eb9\u95f4\u8ddd = \u5149\u6805\u95f4\u8ddd \u00f7 2sin(\u03b8/2)"
                        f" \u2248 {fringe:4.0f} \u683c",
          _mix(_C.AMBER, 0.7))


def galaxy(k, t: float) -> None:
    """A three-armed spiral galaxy, winding on its own clock.

    `想法.md` asks for "三旋臂星系" under 标题, and the section it belongs to is the one that names the
    three arms of this school - 航空、航天、航海. A logarithmic spiral is `r = a e^{bθ}`; three of them a
    third of a turn apart, with the arms drawn as dots whose density falls off outward, is what a face-on
    galaxy looks like at terminal resolution.
    """
    k.section(k.by0, "\u4e09\u65cb\u81c2 \u00b7 \u822a\u7a7a / \u822a\u5929 / \u822a\u6d77", 0.28)
    # A galaxy seen face-on is **round**, so the two radii have to be the same length *in pixels*: a cell
    # is 2 px tall, so `rx = 2 * ry` in cells. The first version took `bw // 4` for rx and the band's own
    # height for ry (23 cells against 4 rows at 95x11), which is a 2.9:1 ellipse - the arms came out as a
    # nearly straight horizontal smear (batch 31's audit measured it).
    ry = max(2, min(6, (k.by1 - k.by0) // 2 - 1))
    rx = 2 * ry
    cx = k.bx0 + rx + 2
    cy = (k.by0 + k.by1) // 2
    spin = t * 0.25
    for arm in range(3):
        base = arm * (2 * math.pi / 3)
        for i in range(150):
            th = i * 0.16
            r = 0.12 * math.exp(0.19 * th)
            if r > 1.02:
                break
            a = base + th + spin
            x = int(cx + rx * r * math.cos(a))
            y = int(cy + ry * r * math.sin(a))
            if k.bx0 <= x <= k.bx1 and k.by0 <= y <= k.by1:
                lv = 0.25 + 0.7 * (1.0 - r)
                k.put(x, y, "\u00b7" if i % 3 else "\u2022",
                      _mix((120, 180, 255) if arm == 0 else ((255, 200, 120) if arm == 1
                                                             else (140, 240, 200)), lv))
    k.put(cx - 2, cy, "\u25cf", _mix(_C.AMBER, 0.95))
    # the labels sit *outside* the round galaxy, in the room the wide band leaves
    k.put(k.bx0 + 2 * rx + 4, cy - 2, "\u822a\u7a7a \u00b7 \u822a\u5929 \u00b7 \u822a\u6d77", _ui(0.7))
    k.put(k.bx0 + 2 * rx + 4, cy - 1, "r = a\u00b7e^{b\u03b8}\uff1a\u81c2\u4e0d\u662f\u76f4\u7684", _ui(0.5))
    k.put(k.bx0 + 2 * rx + 4, cy, "\u4e09\u6761\u81c2\uff0c\u5dee\u4e00\u4e2a\u4e09\u5206\u4e4b\u4e00\u5708",
          _ui(0.45))


def fragmentation(k, t: float) -> None:
    """Memory fragmentation, and the compaction that fixes it.

    `想法.md` lists "内存碎片整理" under 碎片, which is the section whose lyric is "Erase all the
    pointless fragments" - so this is the motif that belongs to that line. A row of blocks, allocated and
    freed in a pattern that leaves holes, then compacted; the free space is the point, and the animation
    is the compaction itself, which is the only thing in the film that literally moves the fragments
    together.
    """
    k.section(k.by0, "\u5185\u5b58\u788e\u7247\u4e0e\u6574\u7406", 0.28)
    n = max(10, min(40, k.bw - 4))
    rows = max(2, min(4, (k.by1 - k.by0) // 3))
    phase = (t % 6.0) / 6.0                       # 0..0.5 allocate/free, 0.5..1 compact
    for r in range(rows):
        y = k.by0 + 2 + r * 2
        if y > k.by1 - 2:
            break
        for i in range(n):
            h = ((i * 2654435761 + r * 40503) >> 9) % 100
            used = h > (30 + r * 4)
            if phase > 0.5:                       # compacted: everything used is packed to the left
                count = int(n * (1 - (30 + r * 4) / 100))
                used = i < count
            k.put(k.bx0 + i, y, "\u2588" if used else "\u00b7",
                  _mix(_C.BLUE, 0.8) if used else _ui(0.2))
        if phase > 0.5:
            k.put(k.bx0, y + 1, "\u2190 \u6574\u7406\u540e\uff1a\u7a7a\u95f2\u8fde\u6210\u4e00\u6574\u5757",
                  _ui(0.45))
    k.put(k.bx0, k.by1, f"\u788e\u7247\u7387 {[74, 68, 62, 55][min(3, int(t * 0.4) % 4)]}% "
                        "\u2014\u2014 \u6574\u7406\u4e0d\u662f\u5220\u9664", _ui(0.5))


#: the five coverage glyphs a brightness key can land on, indexed by `v // 22`. The colour is per cell
#: and cannot be tabulated here: `_mix` goes through the palette the player installs at start-up.
_PIXEL_GLYPH = " \u2591\u2592\u2593\u2588"


def pixelsort(k, t: float) -> None:
    """Pixel sorting: the frame's own rows, ordered by brightness, as a sort you can watch.

    `想法.md` puts "GPU 像素排序" under 崩溃, and the crash section is where the machine stops being able
    to hold its own picture together. Drawing it as a *partially* sorted field - passes of an insertion
    sort over a brightness key - is both the algorithm and the collapse, and it is very legible:
    unsorted noise resolves into a gradient and then into bands.

    **Two defects, and the second was hiding the first** (batch 49, the user: "GPU 像素排序在演出中没有
    视觉变化"). ① `seed.sort()` sat between the hash and the sort, so the insertion sort ran over an
    already sorted list: `srt` was the finished gradient at *every* pass count, and the only cell that
    changed across the row's whole 4.17 s was the caption's `第 N 趟`. The audit that added the pass count
    was reading that caption, which is why it reported a sort in progress. ② The count was capped at six
    (`min(1.0, ...) * 6`) of a ninety-five-cell row, so even unsorted it could only ever order the first
    six cells. `passes` is now a share of the row's own width: the sorted region sweeps left to right
    across the whole drawing and the raw hash is what it is sweeping through.
    """
    k.section(k.by0, "GPU \u50cf\u7d20\u6392\u5e8f \u00b7 \u6309\u4eae\u5ea6", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 8 or h < 3:
        return
    # 2.6 s to sort the row, then 0.8 s of the finished gradient before the wave starts again: the
    # row runs 02:02.0-02:06.2, so a viewer sees the sweep, the completion and one restart.
    passes = int(min(1.0, (t % 3.4) / 2.6) * w)
    for j in range(h):
        y = k.by0 + 1 + j
        # **Not pre-sorted.** The line `seed.sort()` used to sit right here, before `srt = seed[:]`, and
        # it made everything below it a no-op: the "sort in progress" was an insertion sort run over an
        # already sorted list, so `srt` was the finished gradient at every `passes` and the only cell
        # that changed across the row's whole 4.17 s was the caption's pass number. That is exactly what
        # the user reported in batch 49 - "GPU 像素排序在演出中没有视觉变化" - and it is why the audit that
        # counted the passes could not see it: it was measuring the caption. The hash stays as drawn; the
        # *sort* is what makes the row resolve.
        seed = [((i * 2654435761 + j * 40503) >> 11) % 100 for i in range(w)]
        # `passes` passes of an **insertion** sort, in closed form: after `k` passes an insertion sort
        # holds `sorted(seed[:k])` followed by the untouched rest, because pass `p` inserts element `p`
        # into the prefix of the first `p` elements. Writing it out is the same drawing - checked against
        # the loop on 4000 random rows, 0 differences - and it is O(w log w) instead of O(w^2): the loop
        # was 9025 comparisons per row x 11 rows per frame and it took the film's worst frame from
        # t=193.69 to t=62.23 (38.8 ms of a 41.7 ms budget) the moment `passes` was allowed past six.
        srt = sorted(seed[:passes]) + seed[passes:]
        for i, v in enumerate(srt):
            k.put(k.bx0 + i, y, _PIXEL_GLYPH[min(4, v // 22)], _mix(_C.AMBER, 0.25 + 0.7 * v / 100))
    # ...and the caption describes what is on screen: the row is sorted *along itself* by the brightness
    # key, so nothing "floats up" - which is what the first version's caption said.
    k.put(k.bx0, k.by1, f"\u7b2c {passes} \u8d9f\uff1a\u4e00\u884c\u91cc\u7684\u989c\u8272\u6b63\u5728"
                        f"\u6309\u4eae\u5ea6\u5f52\u4f4d", _ui(0.5))


def powerdown(k, t: float) -> None:
    """The shutdown, played backwards: `N: 262144 \u2192 1`, halving.

    `想法.md` ends with "关机｜开机序列倒放；N: 262144 \u2192 1；光标". The closing pane of the film is the
    crest, and this is the counter under it: the boot log's own numbers, divided by two each step, until
    the machine has one thing left to say - which is the film's last line.
    """
    k.section(k.by0, "\u5173\u673a \u00b7 N \u2192 1", 0.28)
    hi, lo = k.by0 + 2, k.by1 - 3
    if lo - hi < 3:
        return
    steps = max(3, int((k.bh - 4) / 1.6))
    n = 262144
    for i in range(steps):
        y = hi + int(i * (lo - hi) / max(1, steps - 1))
        on = (t % 8.0) / 8.0 * (steps + 1) >= i
        k.put(k.bx0 + 1, y, f"{n:>7d}", _mix(_C.AMBER, 0.9) if on else _ui(0.25))
        k.put(k.bx0 + 10, y, "\u2190" if i else "", _ui(0.3))
        for j in range(min(24, k.bw - 14)):
            if on and j < int(24 * n / 262144):
                k.put(k.bx0 + 12 + j, y, "\u2588", _mix(_C.BLUE, 0.7))
        n = max(1, n // 2)
        if n == 1:
            break
    k.put(k.bx0 + 1, min(k.by1 - 1, lo + 1), "1", _mix(_C.GREEN, 0.95))
    k.put(k.bx0 + 3, min(k.by1 - 1, lo + 1), "\u2014\u2014 \u53ea\u5269\u4e00\u4ef6\u4e8b\u6ca1\u8bf4", _ui(0.55))
    if int(t * 2) % 2 == 0:
        k.put(k.bx0 + 1, k.by1, "\u2588", _mix(_C.INK, 0.9))


def bessel(k, t: float) -> None:
    """A circular plate mode, `J\u2084(j\u2084,\u2085 r)\u00b7cos 4\u03b8`, drawn as sand would show it.

    `想法.md` asks for this next to the Chladni figure under 振动, and it is the *other* half of the same
    physics: a square plate has `cos(n\u03c0x)cos(m\u03c0y)` modes and a circular one has Bessel modes. The
    Bessel function is approximated rather than imported - twelve terms of its series is plenty at this
    resolution - and the sand piles where the plate does not move.
    """
    k.section(k.by0, "\u5706\u677f\u6a21\u6001 \u00b7 J\u2084(j\u2084,\u2085r)cos4\u03b8", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 10 or h < 4:
        return

    def j4(x: float) -> float:
        s, term = 0.0, (x / 2) ** 4 / 24.0
        for m in range(12):
            s += term
            term *= -(x * x / 4) / ((m + 1) * (m + 5))
        return s
    k4 = 11.06                                   # j(4,5), the fifth root of J4
    # **The plate is round on screen, and it was not.** The radius used to be `hypot(fx, fy * 2.0)`
    # where `fx` and `fy` are both normalised to -1..1 over the *whole* body: that reaches r=1 at
    # |fx|=1 (the full width) but at |fy|=0.5 (half the height), so the disc came out twice as wide as
    # tall in cells - and a cell is already 2.1x taller than it is wide, so on screen the "circular
    # plate" was about 3.4:1. Measured with a ruler that counts only shape glyphs (batch 37): body
    # 93x13 cells = **3.41:1** where a disc must be 1.00:1. The radius is now measured in cells with
    # the row height weighted by `_CA`, so the largest inscribed disc is genuinely a disc.
    rmax = min(w / 2.0, (h / 2.0) * _CA)
    if rmax < 2.0:
        return
    for j in range(h):
        y = k.by0 + 1 + j
        py = (j + 0.5 - h / 2.0) * _CA
        for i in range(w):
            x = k.bx0 + i
            px = (i + 0.5 - w / 2.0)
            r = math.hypot(px, py) / rmax
            if r > 1.0:
                continue
            th = math.atan2(py, px)
            v = j4(k4 * r) * math.cos(4 * th + t * 0.4)
            a = min(1.0, abs(v) * 3.0)
            if a <= 0.25:
                k.put(x, y, "\u2588", _mix(_C.AMBER, 0.85))
            else:
                k.put(x, y, "\u2591\u2592\u2593 "[min(3, int(a * 3.99))],
                      _mix(_C.BLUE, 0.25 + 0.3 * a))
    k.put(k.bx0, k.by1, "\u5706\u677f\u7684\u8282\u7ebf\u662f\u540c\u5fc3\u5706\u4e0e\u5341\u5b57\u7ebf", _ui(0.5))


def hyperellipse(k, t: float) -> None:
    """The superellipse `|x|^n + |y|^n = r^n`, morphing from a diamond to a square.

    `想法.md` lists it under 互换 - the section about a thing being the same thing in another shape. The
    exponent breathes between 1 and 6, so the curve passes through the circle at n=2 and ends up looking
    like a rounded rectangle, which is the only way to see what the exponent *does*.
    """
    k.section(k.by0, "\u8d85\u692d\u5706 |x|\u207f+|y|\u207f=r\u207f", 0.28)
    cx = k.bx0 + min(24, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    rx = max(4, min(20, k.bw // 5))
    ry = max(2, min(10, (k.by1 - k.by0) // 3))
    n = 1.0 + 2.5 * (1.0 + math.sin(t * 0.45))       # 1 .. 6, through the circle at 2
    for a in range(0, 360, 3):
        th = math.radians(a)
        ct, st = math.cos(th), math.sin(th)
        r = (abs(ct) ** n + abs(st) ** n) ** (-1.0 / n)
        x = int(cx + rx * r * ct)
        y = int(cy + ry * r * st)
        k.put(x, y, "\u2022", _mix(_C.VIOLET, 0.9))
    k.put(cx - rx - 1, cy, "\u2190 n = 1 \u83f1\u5f62", _ui(0.45))
    k.put(cx + rx + 1, cy, "n \u2192 6 \u65b9\u89d2 \u2192", _ui(0.45))
    k.put(k.bx0, k.by1, f"n = {n:4.2f}\uff1a1 \u662f\u83f1\u5f62\uff0c2 \u662f\u5706\uff0c"
                        f"\u518d\u5927\u5c31\u50cf\u65b9\u6846\u4e86", _mix(_C.AMBER, 0.7))


def stardiff(k, t: float) -> None:
    """A six-blade diffraction star: what a point source looks like through a bladed aperture.

    `想法.md` asks for "六叶光圈的衍射星芒" under 电与时间. An odd blade count gives twice as many
    spikes as blades, so six blades make twelve rays - which is why a twelve-pointed star is the thing
    everybody recognises and nobody can name. The blades turn slowly.
    """
    k.section(k.by0, "\u516d\u53f6\u5149\u5708 \u00b7 \u884d\u5c04\u661f\u8292", 0.28)
    cx = k.bx0 + min(24, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    r = max(3, min(18, (k.by1 - k.by0) // 2 - 1, k.bw // 4))
    if r < 3:
        return
    spin = t * 0.18
    blades = 6
    for i in range(blades * 2):
        a = spin + i * math.pi / blades
        for step in range(r):
            x = int(cx + step * math.cos(a))
            y = int(cy + step * math.sin(a) * 0.5)
            lv = 0.95 * (1 - step / r) ** 1.6
            k.put(x, y, "\u2022" if step < r * 0.4 else "\u00b7",
                  _mix(_C.AMBER if i % 2 else _C.BLUE, 0.15 + lv))
    for i in range(blades):
        a = spin + i * 2 * math.pi / blades
        for s2 in range(2, r):
            x = int(cx + s2 * math.cos(a) * 0.14)
            y = int(cy + s2 * math.sin(a) * 0.14)
            k.put(x, y, "\u2591", _ui(0.2))
    k.put(cx - 2, cy, "\u25cf", _mix(_C.INK, 1.0))
    k.put(k.bx0, k.by1, "\u516d\u7247\u53f6\u7ed9\u5341\u4e8c\u6761\u661f\u8292\uff1a"
                        "\u53f6\u6570 n \u2192 2n \u6761", _ui(0.5))


def en_limit(k, t: float) -> None:
    """The `\u03b5`-`N` definition of a limit, drawn as the bands it is.

    `想法.md` asks for "ε–N 极限" under 定义, and the picture is the whole definition: an ε-band around the
    limit, and a point N after which the sequence never leaves it. The band narrows on its own clock, and
    N moves right as it does - which is exactly the sentence "for every ε there is an N".
    """
    k.section(k.by0, "\u03b5\u2013N \u6781\u9650", 0.28)
    w = max(10, k.bw - 14)
    hi, lo = k.by0 + 2, k.by1 - 3
    if lo - hi < 4:
        return
    mid = (hi + lo) // 2
    eps = 0.45 * (0.35 + 0.65 * (0.5 + 0.5 * math.sin(t * 0.5)))
    band = max(1, int((lo - hi) * eps))
    for y in (mid - band, mid + band):
        k.put(k.bx0 + 6, max(k.by0, min(k.by1, y)), "\u2500" * w, _mix(_C.AMBER, 0.55))
    k.put(k.bx0 + 6 + w - 6, mid - band, " y = L + \u03b5", _mix(_C.AMBER, 0.8))
    k.put(k.bx0 + 6 + w - 6, mid + band, " y = L \u2212 \u03b5", _mix(_C.AMBER, 0.8))
    k.vline(k.bx0 + 5, hi, lo, "\u2502", _ui(0.3))
    # the sequence: it wanders, then stays inside the band for good
    n_at = int(w * (0.25 + 0.55 * (1.0 - eps)))
    v = 0.0
    for i in range(w):
        f = i / max(1, w - 1)
        if i < n_at:
            v = 0.9 * math.sin(i * 1.7) * (1.0 - f)
        else:
            v = eps * 0.55 * math.sin(i * 1.7)
        y = mid - int((lo - hi) * v * 0.5)
        k.put(k.bx0 + 6 + i, max(hi, min(lo, y)), "\u2022",
              _mix(_C.GREEN if i >= n_at else _C.DIM, 0.9))
    k.vline(k.bx0 + 6 + n_at, hi, lo, "\u254c", _mix(_C.RED, 0.7))
    # N is labelled *inside* the band, not one row above it: at `hi - 1` it lands on whatever the host
    # pane drew on its top row - which only a dump shows, because the label is still inside the pane
    k.put(k.bx0 + 7 + n_at, min(lo, hi + 1), "N", _mix(_C.RED, 0.9))
    k.put(k.bx0, k.by1, f"\u03b5 = {eps:4.2f}\uff1a\u8fd9\u4e48\u7a84\u7684\u5e26\u5b50\uff0c"
                        f"\u4ece N={n_at} \u4ee5\u540e\u518d\u4e5f\u4e0d\u51fa\u53bb", _ui(0.5))


def binary(k, t: float) -> None:
    """Two stars spiralling together: `a \u221d (t_c \u2212 t)^{1/4}`, and the chirp that gives them away.

    `想法.md` asks for "双星旋近 a∝(t_c−t)^¼" under 电与时间. The separation shrinks as a quarter power of
    the time left, so it looks almost static and then rushes - which is why gravitational-wave
    observatories see a chirp. Both the narrowing orbit and the rising frequency are drawn.
    """
    k.section(k.by0, "\u53cc\u661f\u65cb\u8fd1 a \u221d (t_c\u2212t)^\u00bc", 0.28)
    cx = k.bx0 + min(24, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    rmax = max(4, min(20, k.bw // 5))
    ry = max(2, min(9, (k.by1 - k.by0) // 3))
    # one merger every 8 seconds: `left` is the time to coalescence
    left = 8.0 - (t % 8.0)
    a = rmax * min(1.0, (left / 8.0) ** 0.25)
    ang = t * (2.0 + 6.0 / max(0.35, left))
    for i, col in ((0, _C.AMBER), (1, _C.BLUE)):
        th = ang + i * math.pi
        x = int(cx + a * math.cos(th))
        y = int(cy + ry * (a / rmax) * math.sin(th))
        k.put(x, y, "\u25cf" if a > 6 else "\u2022", _mix(col, 0.95))
        for pr in range(1, 4):                       # the trails they leave
            th2 = th - pr * 0.22
            k.put(int(cx + a * math.cos(th2)), int(cy + ry * (a / rmax) * math.sin(th2)),
                  "\u00b7", _mix(col, 0.35 / pr))
    k.put(k.bx0, k.by1 - 1, f"\u5269\u4e0b {left:4.1f} s\uff1a\u8f68\u9053\u8d8a\u5c0f\uff0c"
                            f"\u9891\u7387\u8d8a\u9ad8", _mix(_C.AMBER, 0.75))
    chirp = max(6, k.bw - 6)
    for i in range(chirp):
        f = i / max(1, chirp - 1)
        fr = 1.0 + 9.0 * (f ** 3)
        if int(t * fr * 3) % 2 == 0:
            k.put(k.bx0 + i, k.by1, "\u2581", _mix(_C.GREEN, 0.3 + 0.6 * f))


def lattice(k, t: float) -> None:
    """A ray-marched lattice: an infinite grid seen at an angle, marching toward the camera.

    `想法.md` asks for "光线步进的晶格巨构" under 标题. A character grid cannot ray-march properly, but it
    can do the thing that makes the shot legible: a receding lattice whose verticals converge on a
    vanishing point and whose horizontals are spaced by `1/z`, with the whole field advancing.
    """
    k.section(k.by0, "\u5149\u7ebf\u6b65\u8fdb \u00b7 \u6676\u683c\u5de8\u6784", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 12 or h < 4:
        return
    vpx = k.bx0 + w // 2
    vpy = k.by0 + max(1, h // 4)
    march = (t * 1.4) % 1.0
    drawn: set[int] = set()
    for j in range(h):
        y = k.by0 + 1 + j
        f = (j + 0.5) / h                                    # 0 at the horizon, 1 at the near edge
        z = 1.0 / max(0.06, f)                               # depth
        for i in range(-6, 7):                               # the verticals
            x = int(vpx + i * (w / 12.0) * (f ** 1.3))
            if k.bx0 <= x <= k.bx1:
                k.put(x, y, "\u2502" if abs(i) > 1 else "\u2551",
                      _mix(_C.BLUE, 0.15 + 0.5 * (1 - f)))
        # the horizontals: at depth z = k + march for k = 1, 2, 3 ..., and z = 1/f, so their rows are
        # `h / (k + march)`. The first version asked, row by row, whether `1/f` was near an integer: on an
        # 11-row band that fires on one or two rows and the caption's "横线按 1/z 变密" was not on screen
        # (the audit measured 1-3 lines, all near the viewer). Placing the rows *from* the law gives the
        # density the caption promises.
        for kk in range(1, 4 * h + 8):                 # kk, not k: `k` is the kit
            j = int(round(h / (kk + march))) - 1
            if 0 <= j < h and j not in drawn:
                drawn.add(j)
                k.put(k.bx0, k.by0 + 1 + j, "\u2500" * w,
                      _mix(_C.VIOLET, 0.15 + 0.5 * (1 - (j + 0.5) / h)))
    k.put(vpx - 3, vpy, "\u25c6", _mix(_C.INK, 0.9))
    k.put(k.bx0, k.by1, "\u6d88\u5931\u70b9\u5728\u90a3\u91cc\uff1a\u7eb5\u7ebf\u6536\u655b\uff0c"
                        "\u6a2a\u7ebf\u6309 1/z \u53d8\u5bc6", _ui(0.5))


def one_path(k, t: float) -> None:
    """`Be your only execution`: every branch the run could take, and the one it takes.

    The lyric's figure - "then I can, then I can / be your only execution" - is *selection*. A program
    with four decisions has sixteen possible executions; the panel draws them as the binary tree they
    are, lights the one this run is actually on, and walks a token down it. The other branches stay
    visible as what did not happen, which is the half of the line that is about being chosen.

    It replaced Byrne's plate from Euclid I.47 on this row: a picture about *proof* on a line about
    *selection* (the user: "几何原本的那个展示效果不好，"
    "换一个和歌词贴合的").
    """
    k.section(k.by0, "唯一执行 · one path", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 16 or h < 4:
        return
    levels = max(2, min(4, (h - 1) // 2, (w - 8) // 12))
    # the choice made at each level, on the song clock: the path is a prefix of these bits
    bits = [(int(t * 0.6) >> i) & 1 for i in range(levels)]

    def node_x(level: int, j: int) -> int:
        n = 2 ** level
        return k.bx0 + 4 + int((w - 8) * (j + 0.5) / n)

    def path_at(level: int) -> int:
        return sum(bits[i] << (level - 1 - i) for i in range(level))

    for d in range(levels):
        n = 2 ** d
        y = k.by0 + 2 + d * 2
        if y > k.by1 - 1:
            break
        for j in range(n):
            x = node_x(d, j)
            lit = (j == path_at(d))
            if d:
                px = node_x(d - 1, j // 2)
                for xx in range(min(px, x) + 1, max(px, x)):
                    k.put(xx, y - 1, BOX_H, _mix(_C.BLUE, 0.5 if lit else 0.14))
            k.put(x, y, "●" if lit else "·",
                  _mix(_C.GREEN if lit else _C.BLUE, 0.95 if lit else 0.3))
    # the token, one level at a time down the chosen chain
    dl = int(t * 1.3) % levels
    ty = k.by0 + 2 + dl * 2
    if ty <= k.by1 - 1:
        k.put(node_x(dl, path_at(dl)), ty, "▶", _mix(_C.AMBER, 0.95))
    k.put(k.bx0, k.by1, f"{2 ** levels} 条可能，只有 1 条真的跑了",
          _ui(0.5))


def resonance(k, t: float) -> None:
    """`Feel your vibrations`: the resonance curve, and the peak that is the answer.

    Amplitude against driving frequency for a driven oscillator,
    `A(f) = 1 / sqrt((1 - r²)² + (r/Q)²)` with `r = f/f0`: flat, a peak at `f0`, then falling
    away. `f0` walks on the song clock, so the peak moves and the pane is never a still frame. It takes
    the slot the second superellipse had - the user's rule is that a performance appears once, and the
    superellipse's first appearance is the 互换 panel at 50.95.
    """
    k.section(k.by0, "共振 · resonance", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 2
    if w < 14 or h < 4:
        return
    Q = 6.0
    f0 = 0.30 + 0.35 * (0.5 + 0.5 * math.sin(t * 0.35))
    base = k.by0 + 1 + h
    prev = None

    def amp(f: float) -> float:
        r = f / max(1e-6, f0)
        return min(1.0, (1.0 / math.sqrt((1 - r * r) ** 2 + (r / Q) ** 2)) / Q * 1.7)

    for i in range(w):
        f = 0.02 + 1.7 * i / max(1, w - 1)
        y = base - int((h - 1) * amp(f))
        y = max(k.by0 + 1, min(base, y))
        if prev is not None:
            for yy in range(min(prev, y), max(prev, y) + 1):
                k.put(k.bx0 + i, yy, "·", _mix(_C.VIOLET, 0.85))
        prev = y
    px = k.bx0 + int((w - 1) * (f0 - 0.02) / 1.7)
    k.put(px, k.by0 + 1, "▼", _mix(_C.AMBER, 0.9))
    k.put(k.bx0, k.by1, "f = f₀ 时振幅最大：频率对上了",
          _ui(0.5))


MOTIFS = {
    "he_init": ("He \u521d\u59cb\u5316", he_init),
    "rectifier": ("\u6574\u6d41\u4e0e\u6ee4\u6ce2", rectifier),
    "phyllotaxis": ("\u53f6\u5e8f", phyllotaxis),
    # "byrne" is not scheduled any more: its plate sat on a line about selection (see `one_path`)
    "quantize": ("2\u2075\u00b3 \u91cf\u5316", quantize),
    "dijkstra": ("Dijkstra \u6700\u77ed\u8def", dijkstra_route),
    "epicycles": ("\u672c\u8f6e", epicycles),
    "hearts9": ("\u4e5d\u79cd\u5fc3\u5f62", hearts9),
    "fork_bomb": ("fork \u70b8\u5f39", fork_bomb),
    "sine": ("sin \u4e0e\u5305\u7edc", sine),
    "chladni": ("\u514b\u62c9\u5c3c", chladni),
    "moire": ("\u83ab\u5c14\u6761\u7eb9", moire),
    "galaxy": ("\u4e09\u65cb\u81c2", galaxy),
    "fragmentation": ("\u788e\u7247\u6574\u7406", fragmentation),
    "pixelsort": ("\u50cf\u7d20\u6392\u5e8f", pixelsort),
    "powerdown": ("\u5173\u673a\u5012\u653e", powerdown),
    "bessel": ("\u5706\u677f\u6a21\u6001", bessel),
    # "hyperellipse" is not scheduled any more: it played twice, and the rule is once (see
    # `school_scenes._ex_hyper`, the 41.92-54.74 互换 panel, which is its first appearance)
    "stardiff": ("\u884d\u5c04\u661f\u8292", stardiff),
    "en_limit": ("\u03b5\u2013N \u6781\u9650", en_limit),
    "binary": ("\u53cc\u661f\u65cb\u8fd1", binary),
    "lattice": ("\u6676\u683c\u5de8\u6784", lattice),
    "one_path": ("\u552f\u4e00\u6267\u884c", one_path),
    "resonance": ("\u5171\u632f", resonance),
}


def draw_motif(name: str, k, t: float) -> bool:
    """Draw one motif into a sub-kit that already has the band the pane left free."""
    spec = MOTIFS.get(name)
    if spec is None:
        return False
    spec[1](k, t)
    return True
