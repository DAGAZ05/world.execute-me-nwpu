"""Which declared layouts silently degrade?

`c_ds_algo` asked for three side-by-side columns and got the stacked fallback - for the entire life of
the pane - because its minimums summed to 100 columns while the pane body is 95. Nothing reported it:
the pane renders, moves, stays inside its rect, passes `pane_probe` and `density_probe`, and its own
docstring argued for the layout it never got. It was found by dumping the frame and *reading* it.

That is a class of defect, not an incident, and this probe is the generalisation: **every pane that asks
`_Kit.columns` or `_Kit.bands` for a layout is checked against what the layout actually returned**, at
the sizes the film really uses. A pane that wanted three columns and got two is a pane whose author
believes something false about what is on screen.

    python _dev/layout_probe.py            the real pane body, and a few smaller ones
    python _dev/layout_probe.py --sizes 95x30,120x36,60x20
"""
from __future__ import annotations

import argparse
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T              # noqa: E402
import school_courses as CO       # noqa: E402
import school_panels as SP        # noqa: E402

# What every pane body is at the two window sizes the film is authored against. 197x52 gives a 95-wide
# body and 120x34 gives 57; see `tui_live.draw_body`.
DEFAULT_SIZES = ("95x30", "57x24", "113x36")

#: `(pane, ask-kind, asked-for, got)` for every degraded call, filled by the instrumented `_Kit`.
DEGRADED: list[tuple[str, str, int, int]] = []
#: `(pane, ask-kind, asked-for, got)` for every call, so "no pane asked" is distinguishable from "all fine".
CALLS: list[tuple[str, str, int, int]] = []
#: panes whose draw raised. **These must fail the probe**: a pane that cannot draw records no layout
#: calls, so a run in which everything raises looks exactly like a run in which everything is fine.
#: (The first version of this file did that - every pane raised `maximum recursion depth exceeded` and
#: the probe printed PASS. See `_Kit`'s base capture below for why they all raised.)
RAISED: list[tuple[str, str]] = []

#: The real `_Kit`, captured *before* `CO._Kit` is replaced by `Watched`. Every internal call in the
#: subclass goes through this name - see the note in `Watched`.
_BASE = CO._Kit

#: Which pane is being drawn right now, so a degraded call can be attributed. A one-element list rather
#: than a module global for the same reason `tui_live` uses them: it is set from outside and read from
#: inside a class that must not be re-created per pane.
CURRENT = ["?"]


class Watched(_BASE):
    """`_Kit` with `columns`/`bands` reporting what they returned.

    **`_BASE` is captured before the module attribute is swapped**, and every internal call goes through
    `_BASE` rather than `CO._Kit`. The first version called `CO._Kit.columns(self, ...)` inside a subclass
    *of* `CO._Kit` - and since the whole point is that `CO._Kit` has been replaced by this class, that is
    a method calling itself: every pane died with `maximum recursion depth exceeded`.

    **And a pane that cannot draw is a failure, not an absence.** The first version caught the exception
    and printed it, so a run in which every pane raised recorded no layout calls at all and the probe
    reported PASS. The report below counts raises separately and fails on them.
    """

    def __init__(self, *a, **kw):
        _BASE.__init__(self, *a, **kw)
        self.pane = CURRENT[0]

    def columns(self, n, weights=None, mins=None):
        out = _BASE.columns(self, n, weights, mins)
        CALLS.append((self.pane, "columns", n, len(out)))
        if len(out) < n:
            DEGRADED.append((self.pane, "columns", n, len(out)))
        return out

    def bands(self, n, weights=None):
        out = _BASE.bands(self, n, weights)
        CALLS.append((self.pane, "bands", n, len(out)))
        if len(out) < n:
            DEGRADED.append((self.pane, "bands", n, len(out)))
        return out

    def sub(self, x0, y0, x1, y1):
        new = _BASE.sub(self, x0, y0, x1, y1)
        if not isinstance(new, Watched):
            new.__class__ = Watched
        new.pane = self.pane
        return new


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default=",".join(DEFAULT_SIZES))
    a = ap.parse_args()

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))

    rows = SP.shot_rows()
    panes = []
    for r in rows:
        name = r.get("name")
        if name and name not in panes:
            panes.append(name)

    total_bad = 0
    for size in a.sizes.split(","):
        c, _, rr = size.partition("x")
        w, h = int(c), int(rr)
        DEGRADED.clear()
        CALLS.clear()
        RAISED.clear()
        for name in panes:
            row = next((x for x in rows if x.get("name") == name), None)
            at = float(row["at"]) if row else 0.0
            end = float(row["end"]) if row else at + 1.0
            span = max(1e-6, end - at)
            args = row.get("args") if row else None
            s = T.Screen(w + 6, h + 4)
            # patch the module's `_Kit` for this one draw, so every `sub` keeps reporting
            real = CO._Kit
            CO._Kit = Watched
            CURRENT[0] = name
            try:
                SP.draw_scene_pane(name, s, 2, 2, 2 + w - 1, 2 + h - 1, at + span * 0.9, span * 0.9,
                                   span, 1.0, args=args)
            except Exception as exc:                      # noqa: BLE001
                RAISED.append((name, str(exc)))
            finally:
                CO._Kit = real
        if RAISED:
            print(f"\n=== {size}: {len(RAISED)} pane(s) raised while drawing ===")
            for pane, exc in RAISED:
                print(f"  {pane:26s} {exc}")
            total_bad += len(RAISED)
        # the panes that asked for a layout and did not get it
        if DEGRADED:
            print(f"\n=== {size}: {len(DEGRADED)} degraded layout call(s) ===")
            seen = set()
            for pane, kind, asked, got in DEGRADED:
                if (pane, kind, asked) in seen:
                    continue
                seen.add((pane, kind, asked))
                print(f"  {pane:26s} asked {kind}({asked}) -> got {got}")
            total_bad += len(seen)
        else:
            print(f"\n=== {size}: no pane asked for a layout it did not get "
                  f"({len(CALLS)} layout call(s)) ===")

    print()
    if total_bad:
        print(f"FAIL: {total_bad} pane(s) believe they have a layout they do not have")
        raise SystemExit(1)
    print("PASS: every declared layout is the layout that runs")


if __name__ == "__main__":
    main()
