"""Every frame in a range, worst first - the question `frame_probe`'s 99 samples cannot answer.

`frame_probe` samples a fixed grid plus the middle of every cut, and that grid has a hole in it that
this batch fell into: the 运-20 low pass is the film's largest sprite and its most expensive frame is
where its ink covers the whole screen, which is the *middle of the event* - and the middle of an event is
neither a grid point nor a cut middle. The gate read 40.2 ms for the whole song while the pass's own peak
was **47.8 ms at t=12.20**, i.e. over the 41.7 ms budget for about half a second (batch 56).

    python _dev/frame_sweep.py                     the whole song, 0.05 s, warm worst 10
    python _dev/frame_sweep.py --lo 10.5 --hi 17   one event's neighbourhood, where the questions are
    python _dev/frame_sweep.py --step 0.1 --reps 2 cheaper, for a first look
    python _dev/frame_sweep.py --dry               list the samples without drawing them

`0.05 s` is finer than the 24 fps frame time on purpose: at 0.0417 s a step of 0.1 s can miss the one
frame a sprite is at its largest. Each time is drawn `--reps` times and the **minimum** kept, the same
rule as `frame_probe` and for the same reason - noise only ever adds time. The collector is off, as it is
in the player. The default whole song is 4 300 frames x 4 passes: several minutes, so run it alone.
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--lo", type=float, default=0.0, help="first time sampled, seconds")
    ap.add_argument("--hi", type=float, default=215.0, help="last time sampled, seconds")
    ap.add_argument("--step", type=float, default=0.05, help="sampling step, seconds")
    ap.add_argument("--reps", type=int, default=4, help="warm passes; the per-time minimum is reported")
    ap.add_argument("--top", type=int, default=10, help="how many of the worst frames to list")
    ap.add_argument("--budget", type=float, default=41.7, help="ms per frame at 24 fps")
    ap.add_argument("--size", default="197x52", help="WxH")
    ap.add_argument("--dry", action="store_true", help="list the sample count and stop")
    a = ap.parse_args()

    cols, _, rows = a.size.partition("x")
    cols, rows = int(cols), int(rows)
    times = [round(a.lo + i * a.step, 4) for i in range(int((a.hi - a.lo) / a.step) + 1)]
    print(f"{len(times)} times from {a.lo} to {a.hi} every {a.step}s at {a.size}, "
          f"minimum of {a.reps} pass(es); budget {a.budget} ms")
    if a.dry:
        return

    import tui_live as T            # noqa: E402
    import school_panels as SP      # noqa: E402
    import school_fx as FX          # noqa: E402

    gc.disable()
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G         # noqa: E402
    G.reset("s")
    FX.warm(cols, rows)
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)
    s = T.Screen(cols, rows)
    sink = io.StringIO()

    for t in times:                 # one cold pass, so the warm numbers are warm
        T.draw(s, d, eng, t, True, 24.0)
        s.render_diff(sink)
    best: dict[float, float] = {}
    for _ in range(max(1, a.reps)):
        for t in times:
            t0 = time.perf_counter()
            T.draw(s, d, eng, t, True, 24.0)
            s.render_diff(sink)
            ms = (time.perf_counter() - t0) * 1000
            best[t] = min(best.get(t, ms), ms)

    mean = sum(best.values()) / len(best)
    over = [t for t, ms in best.items() if ms > a.budget]
    print(f"mean {mean:.1f} ms   warm worst {max(best.values()):.1f} ms   "
          f"{len(over)} frame(s) over budget")
    for ms, t in sorted(((v, k) for k, v in best.items()), reverse=True)[:a.top]:
        ev = [kw.get("name", fn.__name__) for start, end, fn, kw in FX.EVENTS if start <= t < end]
        cut = [f"{kind}@{start:.2f}" for start, (kind, dur) in FX._cuts().items()
               if start <= t <= start + dur]
        row = SP.row_at(t)
        print(f"  {ms:6.1f} ms at t={t:7.2f}   event={','.join(ev) or '-'}  cut={','.join(cut) or '-'}"
              f"  pane={row['name'] if row else '-'}")
    if over:
        spans = sorted(over)
        print(f"  over budget from {spans[0]:.2f} to {spans[-1]:.2f}")
    raise SystemExit(1 if over else 0)


if __name__ == "__main__":
    main()
