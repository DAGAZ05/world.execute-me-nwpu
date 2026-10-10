"""Is every `behind` photograph drawn *before* the words, and the words before everything else?

The rule a `behind` event is defined by - "this photograph is behind the words" - is an *order*, and an
order is the one thing a picture cannot be checked for. Batch 26 put the words on top of the backdrop by
re-drawing the band from outside the layer, after everything; batch 57 found what that costs: 航小天's
legs are inside the band's box, so for the library's four seconds (193.50-197.50) the redraw painted the
stdout box's top border straight across his body - 34-44 cells of him per frame, 3.9 s of it. The user:
"有一小段航小天全身图没有位于最上图层".

So the fix moved the redraw *into* the layer, between its two passes, and this is the check on that
order. It walks every frame in which a `behind` event and an ordinary event are both live - measured off
`school_fx.EVENTS`, not listed by hand - and wraps the layer and the callback to record the order they
were called in:

    python _dev/layer_probe.py             every overlapping window
    python _dev/layer_probe.py --step 0.25 frames per window

Two things it can fail on: a frame where an ordinary event was drawn before the words (the batch-57
bug), or a `behind` event drawn after them (which would make "behind" a lie). It also reports the
windows it found, so a schedule that no longer has any overlap says so instead of passing silently.
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


def windows() -> list[tuple[float, float]]:
    """Every span in which a `behind` event and an ordinary one are both live.

    **批 97 起用 `FX._snap` 之后的窗口**：整屏事件会被挪到最近的拍上（挪动 ±0.23 s），
    用名义窗口算出来的重叠区间会让取样点落到"其实已经不在窗口里"的时刻——
    这正是 193.60 那一刻从"活着"变成"死着"的原因（library 被挪到 193.69 起）。
    """
    import school_fx as FX
    behind = [FX._snap(a, b) for a, b, _fn, kw in FX.EVENTS if kw.get("behind")]
    other = [FX._snap(a, b) for a, b, _fn, kw in FX.EVENTS if not kw.get("behind")]
    out = []
    for a, b in behind:
        for c, d in other:
            lo, hi = max(a, c), min(b, d)
            if hi > lo:
                out.append((round(lo, 4), round(hi, 4)))
    return sorted(set(out))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--step", type=float, default=0.2, help="seconds between sampled frames")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    import tui_live as T
    import school_panels as SP
    import school_fx as FX

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    cols, rows = (int(v) for v in a.size.lower().split("x"))
    eng, data = T.Engine(), T.Data()
    s = T.Screen(cols, rows)
    sink = io.StringIO()

    spans = windows()
    print(f"{len(spans)} window(s) where a `behind` photograph and another event are both live:")
    for lo, hi in spans:
        print(f"  {lo:7.2f} - {hi:7.2f}  ({hi - lo:.2f} s)")
    if not spans:
        print("  (nothing to check: no `behind` event shares a frame with an ordinary one)")
        return

    order: list[str] = []
    real_run, real_words = FX._run, T._band_restore
    FX._run = lambda *ar, **kw: (order.append("behind" if ar[7].get("behind") else "other"),
                                 real_run(*ar, **kw))[1]
    T._band_restore = lambda *ar, **kw: (order.append("words"), real_words(*ar, **kw))[1]

    bad = 0
    frames = 0
    for lo, hi in spans:
        t = lo
        while t <= hi + 1e-6:
            order.clear()
            T.draw(s, data, eng, t, True, 24.0)
            s.render_diff(sink)
            frames += 1
            if order.count("words") != 1:
                print(f"  t={t:7.2f}  the words were drawn {order.count('words')} time(s): {order}")
                bad += 1
            else:
                i = order.index("words")
                late_behind = [x for x in order[i + 1:] if x == "behind"]
                early_other = [x for x in order[:i] if x == "other"]
                if late_behind or early_other:
                    print(f"  t={t:7.2f}  WRONG ORDER {order}  "
                          f"(behind after the words: {len(late_behind)}, "
                          f"other before them: {len(early_other)})")
                    bad += 1
            t = round(t + a.step, 4)
    print(f"\n{frames} frame(s) checked; {bad} with the wrong order")
    if bad:
        print("  FAIL: a `behind` photograph is behind the words, and the words are behind everything else")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
