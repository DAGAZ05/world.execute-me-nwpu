"""How long a frame takes, which is the one thing none of the other probes measure.

`pane_probe` asks whether a pane can draw, `span_probe` whether it draws anything on its first frame,
`trans_probe` whether a transition keeps the buffer's invariants, and the two sweeps whether the whole
song runs. All four were green in the batch that shipped a five-second frame: the sprite keying had been
widened from "white paper" to "whatever colour the border is", which made it flood a 1536x1024 photograph
pixel by pixel in Python, and nothing that measures *correctness* can see a cost.

So this measures the cost, in the two ways it is actually paid:

  * **cold** - the first frame at a time, which is what happens when an effect appears for the first time
    (a sprite decoded, a cache filled). This is the number that decides whether the film hitches.
  * **warm** - the same times again. This is sustained playback, and it is the number that has to fit in
    the frame budget.

    python _dev/frame_probe.py                     the default 21 points, 197x52
    python _dev/frame_probe.py --sizes 197x52,120x34
    python _dev/frame_probe.py --budget 41.7       what a warm worst frame must stay under
    python _dev/frame_probe.py --reps 5            more warm passes, for a machine doing other things

Two things this had to learn, both of them measured:

  * **the collector is off in the player** (`tui_live.main`: "a gen-2 collection is a 20 ms hole in a
    33 ms frame"), so it is off here too. It was on, and the heaviest frame of the song - the torpedo
    shatter at t=163 - read 31 ms or 46 ms from one run to the next, with the difference being a
    collection that the player never performs. A probe that measures something the program does not do
    is not measuring the program.
  * **noise only ever adds time**, so the warm number reported is the *minimum over `--reps` passes* for
    each time, and the largest such minimum is the frame's cost. The biggest single observation is
    printed beside it as `peak`, so a machine that is genuinely too slow still shows up.
"""
from __future__ import annotations

import argparse
import gc
import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

# a spread over the whole song, chosen to land on every kind of moment: the opening, the aircraft, the
# gap, the point set, the first chorus, the fragments, the gate, the courses, the collapse, the closing
TIMES = [5.0, 11.5, 20.0, 35.0, 50.0, 63.0, 80.0, 100.0, 120.0, 133.0, 148.0, 152.5,
         155.0, 158.0, 163.0, 170.0, 176.5, 180.0, 190.0, 200.0, 210.0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="197x52", help="comma-separated, e.g. 197x52,120x34")
    ap.add_argument("--budget", type=float, default=41.7, help="ms per frame at 24 fps")
    ap.add_argument("--reps", type=int, default=3, help="warm passes; the per-time minimum is reported")
    ap.add_argument("--major", default="s", help="pre-answer the college gate")
    a = ap.parse_args()

    # exactly what the player does (`tui_live.main`), for the reason written there
    gc.disable()

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.reset(a.major)
    # ...and the same one-time sprite decode the player does on its first frame (`school_fx.warm`). Without
    # it the cold pass charges the probe for the basketball animation's 3 MB of JSON - 628 ms at t=63.00 -
    # which in the film is paid while the engine loads, with nobody watching.
    import school_fx as _FX
    _FX.warm(*[int(v) for v in a.sizes.split(",")[0].partition("x")[::2]])
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)

    bad = 0
    for spec in a.sizes.split(","):
        c, _, r = spec.partition("x")
        cols, rows = int(c), int(r)
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        cold = []
        for t in TIMES:
            t0 = time.perf_counter()
            T.draw(s, d, eng, t, True, 24.0)
            s.render_diff(sink)
            cold.append(((time.perf_counter() - t0) * 1000, t))
        best: dict[float, float] = {}
        peak: dict[float, float] = {}
        for _ in range(max(1, a.reps)):
            for t in TIMES:
                t0 = time.perf_counter()
                T.draw(s, d, eng, t, True, 24.0)
                s.render_diff(sink)
                ms = (time.perf_counter() - t0) * 1000
                best[t] = min(best.get(t, ms), ms)
                peak[t] = max(peak.get(t, ms), ms)
        warm = sorted(best.items(), key=lambda kv: kv[1])
        mean = sum(best.values()) / len(best)
        wt, worst = warm[-1]
        pk = peak[wt]
        flag = ""
        if worst > a.budget:
            flag = "  <-- OVER BUDGET"
            bad += 1
        print(f"{spec:9} cold  mean {sum(x for x, _ in cold) / len(cold):6.1f} ms   "
              f"worst {max(cold)[0]:6.1f} ms at t={max(cold)[1]:6.2f}")
        print(f"{spec:9} warm  mean {mean:6.1f} ms   worst {worst:6.1f} ms at t={wt:6.2f}   "
              f"peak {pk:6.1f} ms  ({a.reps} pass(es), min kept){flag}")
    print(f"\nbudget {a.budget:.1f} ms per frame (24 fps); {bad} size(s) over it")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
