"""Where does `school_fx.warm` spend its time? One line per event, in the order the song plays them.

    python _dev/warm_profile.py [197x52]

`warm` is the wait before the music starts, so what it costs is what the user stares at ("decoding the
variant's sprites... 4.6 s"). This is the measurement behind the size of that wait: it plays every event
exactly as `warm` does - both ends and twelve points across - and reports each one's share, plus the
count of *distinct* sprite sizes, which is what actually costs (the cache answers the repeats).
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

size = sys.argv[1] if len(sys.argv) > 1 else "197x52"
c, _, r = size.partition("x")
cols, rows = int(c), int(r)
s = T.Screen(cols, rows)

a0 = time.perf_counter()
FX.basket_frames()
print(f"{'basket_frames()':52s} {(time.perf_counter() - a0) * 1000:8.1f} ms")

total = 0.0
for start, end, fn, kw in FX.EVENTS:
    a = time.perf_counter()
    for f in (0.0, 1.0) + tuple((k + 0.5) / 12.0 for k in range(12)):
        try:
            fn(s, cols, rows, start + (end - start) * f, f, **kw)
        except Exception:
            pass
    d = (time.perf_counter() - a) * 1000
    total += d
    name = getattr(fn, "__name__", str(fn))
    print(f"{start:7.2f} {name:10s} {str(kw)[:36]:38s} {d:8.1f} ms")
print(f"{'total':52s} {total:8.1f} ms")
print(f"{'distinct sprite sizes cached':52s} {FX.sprite.cache_info().currsize:8d}")
