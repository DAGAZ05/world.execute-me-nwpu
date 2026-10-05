"""Which call leaves a wide character without its placeholder? Wraps the writers and prints a traceback.

    python _dev/_invariant_trace.py 0.04 197x52

One-shot diagnostic (the `_` prefix means scratch): `_dev/ansi_probe.py` says the *buffer* is inconsistent
- a double-width character at x whose x+1 is an ordinary space - and the terminal can only show what the
buffer says. This finds the writer by checking the invariant after every `Screen` method and printing the
Python stack of the first call that broke it.
"""
from __future__ import annotations

import os
import sys
import traceback
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402


def wide(ch: str) -> bool:
    return bool(ch) and unicodedata.east_asian_width(ch) in ("W", "F")


def broken(s: T.Screen):
    for y in range(s.rows):
        row, wrow = s.buf[y], s.wide[y]
        for x in range(s.cols - 1):
            if wide(row[x][0]) and (not wrow[x + 1] or row[x + 1][0] != ""):
                return f"y={y} x={x} {row[x][0]!r} then {row[x + 1][0]!r} wide={wrow[x + 1]}"
    for y in range(s.rows):
        row, wrow = s.buf[y], s.wide[y]
        for x in range(1, s.cols):
            if wrow[x] and row[x][0] == "" and not wide(row[x - 1][0]):
                return f"y={y} x={x} orphan placeholder, left={row[x - 1][0]!r}"
    return ""


def main() -> None:
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 0.04
    size = sys.argv[2] if len(sys.argv) > 2 else "197x52"
    c, _, r = size.partition("x")
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

    done = [False]

    def note(where: str, s: T.Screen) -> None:
        if done[0]:
            return
        why = broken(s)
        if why:
            done[0] = True
            print(f"after {where}: {why}")
            for line in traceback.format_stack()[-7:-1]:
                print("   ", line.strip().splitlines()[0])

    for name in ("fx_apply", "fx_reveal", "fx_trail", "fx_shake"):
        real = getattr(T, name)

        def wrap_fn(real=real, name=name):
            def call(s, *a, **kw):
                out = real(s, *a, **kw)
                note(name, s)
                return out
            return call
        setattr(T, name, wrap_fn())

    s = T.Screen(cols, rows)
    d_ = T.Data()
    eng_ = T.Engine()
    k = 0
    while k / 24.0 <= t + 0.05 and not done[0]:
        now = k / 24.0
        T.draw(s, d_, eng_, now, True, 24.0)
        why = broken(s)
        if why:
            done[0] = True
            print(f"the buffer is inconsistent after the frame at t={now:.3f}: {why}")
        k += 1
    if not done[0]:
        print(f"no invariant break found over {k} frame(s) ending at t={t}")


if __name__ == "__main__":
    main()
