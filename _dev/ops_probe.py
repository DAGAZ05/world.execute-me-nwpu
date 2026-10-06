"""How tall is the ops box, song-long? The user: "ops panel的高度不要只固定为1行，根据右侧panel图像的高度
进行动态调整".

    python _dev/ops_probe.py [--size 197x52] [--step 1.0]

The box is drawn last and gets whatever the drawing above it leaves, so its height is an *outcome* of the
pane's. This reads that split out of `tui_live.GEOM` - the arithmetic `draw_body` actually used - and
fails when a drawing of eight rows or more is answered with fewer than three rows of words, which is the
user's complaint coming back.

It used to read the height back off the finished screen by scanning for the box's corners, and that was
wrong in a way worth remembering: it looked for the closing corner in column 1 (another box's left edge
whenever the drawing column is on the right, which it is after 136.90) and an FX overlay sometimes paints
over a corner. It reported "two rows" for the box that was really three, i.e. it under-reported the very
thing being measured. A probe's ruler is as much a part of the result as its numbers.
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--step", type=float, default=1.0)
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    cols, rows = int(c), int(r)

    T.VAR[0] = "school"
    import school_panels as SP
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)

    # the ops box is the last framed box in the left/right drawing column, and its height is the split
    # `draw_body` made (published in `T.GEOM`). Reading it back off the screen was the first version of
    # this probe and it lied twice: it looked for the closing corner in column 1 - another box's left edge
    # whenever the drawing column is on the right - and an FX overlay paints over a corner now and then.
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    hist: dict[int, int] = {}
    by_time: list[tuple[float, int, int, int]] = []
    t = 0.0
    while t <= 212.0:
        T.draw(s, d, eng, t, True, 24.0)
        sink.seek(0)
        sink.truncate(0)
        s.render_diff(sink)
        if T.GEOM:
            h = int(T.GEOM.get("h") or 0)
            hist[h] = hist.get(h, 0) + 1
            by_time.append((t, h, int(T.GEOM.get("pane_h") or 0), int(T.GEOM.get("avail") or 0)))
        t += a.step
    print(f"{a.size}: ops box height over the song (sampled every {a.step}s)")
    for h in sorted(hist):
        print(f"   {h:2d} row(s): {hist[h]:4d} sample(s)")
    thin = sum(n for h, n in hist.items() if h <= 2)
    print(f"   {thin} sample(s) at two rows or fewer"
          f"{'  <- the user is looking at these' if thin else ''}")
    # ...and the point of the change: the box follows the drawing, so print the drawing's height beside
    # it. `avail` is the whole column; `pane_h` is what the drawing got; the box is what is left.
    tall = sorted({(p, h) for _t, h, p, _a in by_time})
    print("   drawing height -> box height (distinct pairs, pane rows / box rows):")
    for p, h in tall:
        n = sum(1 for _t, hh, pp, _a in by_time if (pp, hh) == (p, h))
        print(f"     pane {p:3d} -> ops {h:2d}   ({n} sample(s))")
    # The complaint was "the ops panel is fixed at one line". A drawing of eight rows or more that is
    # still answered with fewer than three rows of words is that bug coming back, so it fails the probe.
    bad = [t for t, h, p, _a in by_time if p >= 8 and h < 3]
    if bad:
        print(f"FAIL: {len(bad)} sample(s) with a {min(p for _t, _h, p, _a in by_time)}-row-or-taller "
              f"drawing and a box under three rows: {', '.join(f'{t:.1f}s' for t in bad[:8])}")
        sys.exit(1)
    print("PASS: no tall drawing is answered with a one-line ops box")


if __name__ == "__main__":
    main()
