"""How long does one frame of the film take to build, and how big is its escape stream?

    python _dev/frame_budget.py [--variant school] [--size 197x52] [--samples 40]

The player's smoothness has two budgets and this prints both, per frame:

  * **build** - `draw()` in Python, millisecond-resolution, warm (the first frame of each pane is
    cold and the real player pays for it before the music starts);
  * **paint** - `render_diff()`'s escape bytes for that frame, which is what the terminal has to
    parse and rasterise. Bytes are not milliseconds, but they are the half of the budget the
    launcher's advice is about, and they are comparable between frames.

Sampling every 2 s across the whole song is enough to see which shots are the expensive ones.
"""
from __future__ import annotations

import argparse
import io
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAYER = ROOT / "player"
sys.path.insert(0, str(PLAYER / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--variant", default="school", choices=["original", "school"])
    ap.add_argument("--size", default="197x52")
    ap.add_argument("--from", dest="t0", type=float, default=0.0)
    ap.add_argument("--to", dest="t1", type=float, default=211.9)
    ap.add_argument("--step", type=float, default=2.0)
    ap.add_argument("--top", type=int, default=15, help="print this many slowest frames")
    args = ap.parse_args()

    c, _, r = args.size.partition("x")
    cols, rows = int(c), int(r)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    T.VAR[0] = args.variant
    if args.variant == "school":
        import school_panels as SP
        T.SP = SP
        # the school panes draw through the film's palette helpers, and they are handed to the
        # variant module rather than imported (see tui_live.main) - a probe has to do the same.
        SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
        try:
            import school_gate as _G
            _G.reset("s")
        except Exception as exc:
            print(f"# no gate: {exc}", file=sys.stderr)
        import school_fx
        t0 = time.perf_counter()
        n = school_fx.warm(cols, rows)
        print(f"# sprites warmed: {n} in {time.perf_counter() - t0:.1f} s", file=sys.stderr)
    T.enable_vt()

    d = T.Data()
    eng = None
    try:
        eng = T.Engine()
    except Exception as exc:
        print(f"# no engine: {exc}", file=sys.stderr)

    s = T.Screen(cols, rows)
    sink = io.StringIO()

    # one pass to fill the caches, exactly like the player's own warm-up
    t0 = time.perf_counter()
    T.draw(s, d, eng, 1.0, True, 0.0)
    s.render_diff(sink)
    print(f"# first frame (cold): {(time.perf_counter() - t0) * 1000:.0f} ms, "
          f"{len(sink.getvalue()) / 1024:.0f} KB")

    rowsout = []
    t = args.t0
    while t <= args.t1:
        sink.seek(0)
        sink.truncate(0)
        a = time.perf_counter()
        T.draw(s, d, eng, t, True, 0.0)
        b = time.perf_counter()
        s.render_diff(sink)
        c2 = time.perf_counter()
        rowsout.append((t, (b - a) * 1000.0, len(sink.getvalue()), (c2 - b) * 1000.0))
        t += args.step

    ms = [x[1] for x in rowsout]
    kb = [x[2] / 1024.0 for x in rowsout]
    print()
    print(f"frames sampled   {len(rowsout)}  ({args.t0:.0f}-{args.t1:.0f} s, every {args.step:g} s)")
    print(f"build ms         min {min(ms):6.1f}   median {statistics.median(ms):6.1f}   "
          f"mean {statistics.fmean(ms):6.1f}   max {max(ms):6.1f}   p90 {sorted(ms)[int(len(ms) * .9)]:6.1f}")
    print(f"paint KB         min {min(kb):6.1f}   median {statistics.median(kb):6.1f}   "
          f"mean {statistics.fmean(kb):6.1f}   max {max(kb):6.1f}")
    budget = 1000.0 / 60
    over = [x for x in rowsout if x[1] > budget]
    print(f"over {budget:.1f} ms    {len(over)}/{len(rowsout)} frames "
          f"({100.0 * len(over) / len(rowsout):.0f} %) would miss a 60 fps cap")
    print(f"implied fps cap  build-only {1000.0 / statistics.fmean(ms):.1f} fps "
          f"(median {1000.0 / statistics.median(ms):.1f})")
    print()
    print("slowest frames:")
    for t, b, n, p in sorted(rowsout, key=lambda x: -x[1])[:args.top]:
        ent = eng.entry_at(t) if eng else None
        name = (ent or {}).get("name", "?")
        print(f"  t={t:7.2f}  build {b:7.1f} ms   paint {n / 1024:6.1f} KB   {name}")
    print()
    print("largest paint streams:")
    for t, b, n, p in sorted(rowsout, key=lambda x: -x[2])[:args.top]:
        ent = eng.entry_at(t) if eng else None
        name = (ent or {}).get("name", "?")
        print(f"  t={t:7.2f}  paint {n / 1024:6.1f} KB   build {b:7.1f} ms   {name}")


if __name__ == "__main__":
    main()
