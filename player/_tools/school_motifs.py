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

import school_courses as _C

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
    # the plate is placed from the top of the band, not centred in it: its triangle is (0,0), (3s,0),
    # (0,4s) with y downward, so a centred origin drops 4s below the middle and the hypotenuse square
    # runs off the bottom of the pane - which is what the first version did
    s = max(2, min(7, (k.by1 - k.by0) // 5, k.bw // 12))
    cx = k.bx0 + min(30, k.bw // 2)
    cy = k.by0 + 2 + s
    a = 0.42 + 0.10 * math.sin(t * 0.8)          # the tilt, breathing
    ca, sa = math.cos(a), math.sin(a)

    def put(dx, dy, ch, lv):
        x = int(cx + dx * ca - dy * sa * 0.5)
        y = int(cy + dx * sa * 0.5 + dy * ca)
        k.put(x, y, ch, lv)

    # the triangle: 3-4-5, the one everyone knows, so the squares can be judged by eye
    p = ((0, 0), (3 * s, 0), (0, 4 * s))

    def seg(p0, p1, ch, lv):
        steps = max(1, int(math.hypot(p1[0] - p0[0], p1[1] - p0[1])))
        for i in range(steps + 1):
            f = i / steps
            put(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, ch, lv)
    for i in range(3):
        seg(p[i], p[(i + 1) % 3], "\u2500", _mix(_C.INK, 0.9))
    # the square on the hypotenuse, hatched, and the two smaller ones on the legs
    seg((0, 0), (-3 * s, 4 * s), "\u2500", _mix(_C.INK, 0.9))
    for j in range(1, 4):
        seg((-(j * 3 * s / 4), j * s), (3 * s - j * 3 * s / 4, j * s), "\u00b7", _mix(_C.BLUE, 0.5))
    for j in range(1, 3):
        seg((j * s, 0), (j * s, -3 * s), "\u00b7", _mix(_C.GREEN, 0.45))
    k.put(cx + 2 * s, cy + 5 * s, "a\u00b2 + b\u00b2 = c\u00b2", _mix(_C.AMBER, 0.9))
    k.put(cx - 4 * s, cy - 5 * s, "3 \u00b7 4 \u00b7 5", _ui(0.55))


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
    for i in range(n):
        f = i / max(1, n - 1)
        # before 2^53 the integers are one apart; after it the spacing doubles every octave, so the
        # dots thin out - and the frame is the number line
        gap = 1.0 if f < 0.35 else 2.0 ** int((f - 0.35) * 12)
        x = k.bx0 + 2 + i
        on = (i % max(1, int(gap))) == 0
        k.put(x, y, "\u2022" if on else "\u00b7", _mix(_C.BLUE if on else _C.DIM, 0.85 if on else 0.3))
    k.put(k.bx0 + 2, y + 2, "1 \u00b7 2 \u00b7 3 \u2026" if k.bw > 40 else "1 2 3 \u2026", _ui(0.5))
    k.put(k.bx0 + int(n * 0.42), y + 2, "\u2191 \u6b64\u540e\u6bcf\u9694\u4e00\u4e2a\u6570\u90fd\u4e0d\u80fd"
                                        "\u7cbe\u786e\u8868\u793a", _mix(_C.RED, 0.8))


def dijkstra_cracks(k, t: float) -> None:
    """Cracks grown by Dijkstra: the shortest path from one edge point to another, on a random field.

    `想法.md` lists "Dijkstra \u88c2\u7eb9" under \u788e\u7247, and it is the honest version of a crack: a crack
    is not random, it is the *cheapest* way through the material. The field is a deterministic hash, the
    path walks to the lowest-cost neighbour, and the growth is on `t` so the crack keeps opening.
    """
    k.section(k.by0, "Dijkstra \u88c2\u7eb9", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 12 or h < 4:
        return

    def cost(x, yy):
        return ((x * 2654435761 + yy * 40503) >> 7) % 100
    grown = max(2, int(w * 0.9 * min(1.0, (t % 6.0) / 4.0 + 0.25)))
    x, y = k.bx0, k.by0 + 1 + (h // 2)
    for step in range(min(grown, w)):
        k.put(x, y, "\u2571" if step % 3 == 0 else ("\u2502" if step % 3 == 1 else "\u2572"),
              _mix(_C.RED, 0.6 + 0.35 * (step / max(1, grown))))
        for i in range(3):                     # three candidate steps right, take the cheapest
            nx = x + 1
            ny = max(k.by0 + 1, min(k.by0 + h, y + (i - 1)))
            if i == 0 or cost(nx, ny) < cost(x + 1, y):
                y = ny
        x += 1
        if x > k.bx1 - 1:
            break
    k.put(k.bx0, k.by1, "\u88c2\u7eb9\u4e0d\u662f\u968f\u673a\u7684\uff0c\u662f\u6700\u4fbf\u5b9c"
                        "\u7684\u90a3\u6761\u8def", _ui(0.5))


def epicycles(k, t: float) -> None:
    """Fourier epicycles: circles on circles drawing a heart, and the coefficients that do it.

    The one motif in the list that is *both* the maths and the joke of this film: any curve is a sum of
    rotations, and this one is a sum of rotations that comes out as a heart. Each circle turns at its own
    harmonic, which is the parallel animation the pane inside a pane can show at its clearest.
    """
    k.section(k.by0, "\u5085\u91cc\u53f6\u672c\u8f6e \u00b7 \u5fc3\u5f62\u7684\u5206\u89e3", 0.28)
    # separate x and y scales: a terminal cell is about twice as tall as it is wide, so a curve drawn
    # with one radius per axis comes out as a horizontal smear - and the first version's was 6 cells
    # across in a 100-cell pane because it used the *height* for both
    sx = max(3, min(22, k.bw // 8))
    sy = max(2, min(9, (k.bh - 3) // 2))
    cx = k.bx0 + sx + 4
    cy = (k.by0 + k.by1) // 2 + 1
    # the heart, as a parametric sum of rotations: c_n ~ 1/|n| with a phase, which is what makes the
    # little circles worth drawing instead of a formula
    terms = [(1.0, 1, 0.0), (0.55, -2, 0.9), (0.32, 3, 1.7), (0.20, -4, 0.4), (0.12, 5, 2.2)]
    n_pts = 40
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
    """Nine heart curves: the six the textbooks use plus three that only exist as equations.

    `想法.md` lists five heart formulae under LOVE and asks for nine. They are drawn as a contact sheet -
    three rows of three - because the point is that they are *different shapes*, and a contact sheet is
    the only layout where that is visible at terminal resolution. Each cell is one equation, drawn on its
    own clock, so the sheet breathes rather than being a printed figure.
    """
    k.section(k.by0, "\u4e5d\u79cd\u5fc3\u5f62\u66f2\u7ebf", 0.28)
    # the sheet adapts: nine cells when the band is tall, three when it is short. The first version was
    # always 3x3, and in a ten-row band each cell got three rows - the hearts came out as dashes and the
    # nine equations printed on top of each other
    tall = (k.by1 - k.by0) >= 11
    cols, rows = (3, 3) if tall else (3, 1)
    cw = max(10, k.bw // cols)
    chh = max(3, (k.by1 - k.by0 - 1) // rows)
    if chh < 3:
        return
    eqs = ("r=1\u2212sin\u03b8", "r=1\u2212cos\u03b8", "(x\u00b2+y\u00b2\u22121)\u00b3=x\u00b2y\u00b3",
           "x\u00b2+(y\u2212|x|)\u00b2=1", "r=\u03b8", "16sin\u00b3t", "|x|^0.5", "r=sin\u00b2\u03b8", "e^{-|x|}")
    for ci in range(cols * rows):
        eq = eqs[ci]
        r0, c0 = divmod(ci, cols)
        ox = k.bx0 + c0 * cw + 2
        oy = k.by0 + 1 + r0 * chh
        k.put(ox, oy, eq[: max(0, cw - 3)], _ui(0.5))
        sx, sy = max(2, cw // 5), max(2, (chh - 1) // 2)
        spin = t * (0.4 + 0.1 * ci)
        for a in range(0, 360, 6):
            th = math.radians(a)
            if ci == 0:
                r = 1 - math.sin(th)
            elif ci == 1:
                r = 1 - math.cos(th)
            elif ci == 2:
                r = 0.8 + 0.2 * math.cos(2 * th)          # a stand-in for the implicit curve
            elif ci == 3:
                r = 0.7 + 0.3 * abs(math.cos(th))
            elif ci == 4:
                r = 0.3 + 0.7 * abs(math.sin(th))
            elif ci == 5:
                r = 0.6 + 0.4 * abs(math.sin(3 * th))
            elif ci == 6:
                r = 0.5 + 0.5 * abs(math.sin(th)) ** 0.5
            elif ci == 7:
                r = 0.4 + 0.6 * math.sin(th) ** 2
            else:
                r = 0.5 + 0.5 * math.exp(-abs(math.cos(th)) * 2)
            x = int(ox + 3 + sx * r * math.cos(th + spin) * 1.6)
            y = int(oy + 1 + sy * r * math.sin(th) * 0.9 + sy)
            k.put(x, y, "\u00b7", _mix(_C.RED if ci % 2 else _C.VIOLET, 0.85))
    k.put(k.bx0, k.by1, "\u540c\u4e00\u4e2a\u5f62\u72b6\uff0c\u4e5d\u4e2a\u65b9\u7a0b\uff1a\u6ca1\u6709"
                        "\u54ea\u4e2a\u662f\u201c\u5bf9\u201d\u7684", _ui(0.5))


def fork_bomb(k, t: float) -> None:
    """The fork bomb, drawn as the H-tree it actually is: one process, then two, then 4096.

    `想法.md` asks for `:(){ :|:& };:` growing into a three-dimensional H-tree under 处决, and the
    doubling is the whole drawing - what makes a fork bomb a fork bomb is not the code, it is that the
    ninth generation is five hundred times the eighth. The count is printed, and the counter is the
    thing that stops the frame: it is drawn to 4096 because 4096 processes is the joke.
    """
    k.section(k.by0, "fork \u70b8\u5f39 \u00b7 1 \u2192 4096", 0.28)
    depth = max(1, min(6, (k.by1 - k.by0 - 2) // 2))
    # the generation is the pane's own progress, not `t % 4`: the course panes live for 0.83 s and the
    # absolute clock put a different generation in each of them for no reason at all
    gen = int(min(depth, k.u * (depth + 1)))
    w = k.bw - 22
    if w < 12:
        return
    x0, y0 = k.bx0, k.by0 + 1
    for g in range(gen + 1):
        n = 2 ** g
        y = y0 + g * 2
        step = max(1, w // (n * 2))
        for i in range(n):
            x = x0 + 2 + i * step * 2
            if x > k.bx1 - 2:
                break
            k.put(x, y, "\u25cf", _mix(_C.GREEN if g == gen else _C.BLUE, 0.85))
            if g:
                for xx in range(x - step, x):        # the fork edge, back to the parent
                    k.put(xx, y - 1, BOX_H, _ui(0.2))
                k.put(x - step // 2, y - 1, "\u252c", _ui(0.3))
    k.put(k.bx1 - 18, k.by0 + 1, f"\u4ee3 {gen}", _mix(_C.AMBER, 0.9))
    k.put(k.bx1 - 18, k.by0 + 2, f"{2 ** gen:5d} \u8fdb\u7a0b", _mix(_C.RED, 0.9))
    k.put(k.bx0, k.by1, ":(){ :|:& };:  \u2014\u2014 \u4e5d\u4ee3\u4e4b\u540e\u5c31\u662f 4096", _ui(0.5))


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
    for i in range(n):                                   # only the stretch that is on screen
        dx = i - i0
        yy = math.sin(p) + math.cos(p) * (dx * (4 * math.pi / max(1, n - 1)))
        y = mid - int(amp * yy)
        if hi <= y <= lo:
            k.put(k.bx0 + i, y, "\u2500", _mix(_C.AMBER, 0.55))
    y0 = mid - int(amp * math.sin(p))
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
    for j in range(h):
        y = k.by0 + 1 + j
        fy = (j + 0.5) / h
        for i in range(w):
            x = k.bx0 + i
            fx = (i + 0.5) / w
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
    for j in range(h):
        y = k.by0 + 1 + j
        if j % 2:                                 # every other row: see below
            continue
        for i in range(w):
            x = k.bx0 + i
            a = 1 if int((i / pitch) % 2) == 0 else 0          # the horizontal grating
            u_ = (i - w / 2) * ca - (j - h / 2) * sa
            b = 1 if int((u_ / pitch) % 2) == 0 else 0
            # What the eye sees is where the *two* gratings are both open: that is the fringe. Drawing a
            # cell for "either grating open" instead fills half the pane with a half-tone and the fringes
            # disappear into it; drawing every row at full strength then made the panel the loudest thing
            # in the frame, which is the clutter the user's note is about. Every other row, and the
            # fringes read the same.
            if a and b:
                k.put(x, y, "\u2588", _mix(_C.VIOLET, 0.62))
            elif a or b:
                k.put(x, y, "\u00b7", _mix(_C.VIOLET, 0.14))
    k.put(k.bx0, k.by1, f"\u5939\u89d2 {math.degrees(ang):4.1f}\u00b0\uff1a"
                        f"\u6761\u7eb9\u95f4\u8ddd = \u5149\u6805\u95f4\u8ddd \u00f7 2sin(\u03b8/2)",
          _mix(_C.AMBER, 0.7))


def galaxy(k, t: float) -> None:
    """A three-armed spiral galaxy, winding on its own clock.

    `想法.md` asks for "三旋臂星系" under 标题, and the section it belongs to is the one that names the
    three arms of this school - 航空、航天、航海. A logarithmic spiral is `r = a e^{bθ}`; three of them a
    third of a turn apart, with the arms drawn as dots whose density falls off outward, is what a face-on
    galaxy looks like at terminal resolution.
    """
    k.section(k.by0, "\u4e09\u65cb\u81c2 \u00b7 \u822a\u7a7a / \u822a\u5929 / \u822a\u6d77", 0.28)
    cx = k.bx0 + min(26, k.bw // 2)
    cy = (k.by0 + k.by1) // 2
    rx = max(4, min(26, k.bw // 4))
    ry = max(2, min(14, (k.by1 - k.by0) // 2 - 1))
    if ry < 2:
        return
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
    k.put(k.bx0 + 2 * rx + 2, cy - 2, "\u822a\u7a7a \u00b7 \u822a\u5929 \u00b7 \u822a\u6d77", _ui(0.7))
    k.put(k.bx0 + 2 * rx + 2, cy - 1, r=0) if False else None
    k.put(k.bx0 + 2 * rx + 2, cy - 1, "r = a\u00b7e^{b\u03b8}\uff1a\u81c2\u4e0d\u662f\u76f4\u7684", _ui(0.5))


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


def pixelsort(k, t: float) -> None:
    """Pixel sorting: the frame's own rows, ordered by brightness, as a sort you can watch.

    `想法.md` puts "GPU 像素排序" under 崩溃, and the crash section is where the machine stops being able
    to hold its own picture together. Drawing it as an *almost sorted* field - a few passes of
    bubble/insertion over a brightness key - is both the algorithm and the collapse, and it is very
    legible: unsorted noise resolves into a gradient and then into bands.
    """
    k.section(k.by0, "GPU \u50cf\u7d20\u6392\u5e8f \u00b7 \u6309\u4eae\u5ea6", 0.28)
    w, h = k.bw, k.by1 - k.by0 - 1
    if w < 8 or h < 3:
        return
    passes = int(min(1.0, (t % 4.0) / 3.0) * 6)
    for j in range(h):
        y = k.by0 + 1 + j
        seed = [((i * 2654435761 + j * 40503) >> 11) % 100 for i in range(w)]
        seed.sort()
        # `passes` of an insertion sort, so the row is visibly *becoming* sorted rather than sorted
        srt = seed[:]
        for _ in range(passes):
            for i in range(1, len(srt)):
                if srt[i] < srt[i - 1]:
                    srt[i], srt[i - 1] = srt[i - 1], srt[i]
        if passes >= 4:
            srt = sorted(seed)
        for i, v in enumerate(srt):
            ch = " \u2591\u2592\u2593\u2588"[min(4, v // 22)]
            k.put(k.bx0 + i, y, ch, _mix(_C.AMBER, 0.25 + 0.7 * v / 100))
    k.put(k.bx0, k.by1, f"\u7b2c {passes} \u8d9f\uff1a\u989c\u8272\u8fd8\u5728\u5f80\u4e0a\u6d6e", _ui(0.5))


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
    for j in range(h):
        y = k.by0 + 1 + j
        fy = (j + 0.5) / h * 2 - 1
        for i in range(w):
            x = k.bx0 + i
            fx = (i + 0.5) / w * 2 - 1
            r = math.hypot(fx, fy * 2.0)
            if r > 1.0:
                continue
            th = math.atan2(fy * 2.0, fx)
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
    for j in range(h):
        y = k.by0 + 1 + j
        f = (j + 0.5) / h                                    # 0 at the horizon, 1 at the near edge
        z = 1.0 / max(0.06, f)                               # depth
        for i in range(-6, 7):                               # the verticals
            x = int(vpx + i * (w / 12.0) * (f ** 1.3))
            if k.bx0 <= x <= k.bx1:
                k.put(x, y, "\u2502" if abs(i) > 1 else "\u2551",
                      _mix(_C.BLUE, 0.15 + 0.5 * (1 - f)))
        # the horizontals: spaced by 1/z, and the `march` slides the whole set toward the viewer
        zz = z + march * 4
        if abs(zz - round(zz)) < 0.09:
            k.put(k.bx0, y, "\u2500" * w, _mix(_C.VIOLET, 0.15 + 0.5 * (1 - f)))
    k.put(vpx - 3, vpy, "\u25c6", _mix(_C.INK, 0.9))
    k.put(k.bx0, k.by1, "\u6d88\u5931\u70b9\u5728\u90a3\u91cc\uff1a\u7eb5\u7ebf\u6536\u655b\uff0c"
                        "\u6a2a\u7ebf\u6309 1/z \u53d8\u5bc6", _ui(0.5))


MOTIFS = {
    "he_init": ("He \u521d\u59cb\u5316", he_init),
    "rectifier": ("\u6574\u6d41\u4e0e\u6ee4\u6ce2", rectifier),
    "phyllotaxis": ("\u53f6\u5e8f", phyllotaxis),
    "byrne": ("Byrne \u56fe\u7248", byrne),
    "quantize": ("2\u2075\u00b3 \u91cf\u5316", quantize),
    "dijkstra": ("Dijkstra \u88c2\u7eb9", dijkstra_cracks),
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
    "hyperellipse": ("\u8d85\u692d\u5706", hyperellipse),
    "stardiff": ("\u884d\u5c04\u661f\u8292", stardiff),
    "en_limit": ("\u03b5\u2013N \u6781\u9650", en_limit),
    "binary": ("\u53cc\u661f\u65cb\u8fd1", binary),
    "lattice": ("\u6676\u683c\u5de8\u6784", lattice),
}


def draw_motif(name: str, k, t: float) -> bool:
    """Draw one motif into a sub-kit that already has the band the pane left free."""
    spec = MOTIFS.get(name)
    if spec is None:
        return False
    spec[1](k, t)
    return True
