"""Which event is costing what, frame by frame, over the low pass.

    python _dev/fx_profile.py 11.2 13.1
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_fx as FX          # noqa: E402

lo = float(sys.argv[1]) if len(sys.argv) > 1 else 11.2
hi = float(sys.argv[2]) if len(sys.argv) > 2 else 13.1
cols, rows = 197, 52
T.VAR[0] = "school"
t0 = time.perf_counter()
n = FX.warm(cols, rows)
print(f"warm {n} in {time.perf_counter() - t0:.2f} s")

s = T.Screen(cols, rows)
out = []
t = lo
while t < hi:
    live = [(st, en, fn.__name__, kw) for st, en, fn, kw in FX.EVENTS if st <= t < en]
    t1 = time.perf_counter()
    FX.draw(s, cols, rows, t)
    out.append(((time.perf_counter() - t1) * 1000, t, live))
    t += 1 / 24.0
out.sort(reverse=True)
print("slowest frames of `school_fx.draw` alone:")
for ms, tt, live in out[:8]:
    print(f"  {ms:7.1f} ms at t={tt:5.2f}  {[f'{n}@{st:.1f}' for st, _e, n, _k in live]}")
print(f"mean {sum(x for x, _, _ in out) / len(out):.1f} ms over {len(out)} frames")
