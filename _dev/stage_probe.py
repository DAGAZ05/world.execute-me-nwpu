"""Where does a frame's time actually go?

`_dev/frame_probe.py` says *how long* a frame takes and which time in the song is the worst. It cannot
say **which stage** spent it: the pipeline is seven steps deep (body -> footer -> the full-frame layer ->
the transition -> the lyric band put back -> `fx_apply`'s three post passes -> normalise + the write out)
and `fx_profile.py` only sees the first of the layer's two calls. Batch 36 deferred two whole effects -
a beat-driven brightness pulse and a scrolling scanline - because there was no way to price them:
"existing tooling cannot measure `fx_reveal` / `fx_trail` / `fx_shake` / `transition` separately", and a
frame budget with 2 ms of headroom cannot absorb an unmeasured effect.

This is that tool. It wraps every stage by name (the technique `_dev/_invariant_trace.py` uses) and
reports the breakdown per time, so the question becomes "the worst frame costs 39 ms - of which how much
is the transition, how much the reveal, how much the write".

    python _dev/stage_probe.py                  the default grid, 197x52
    python _dev/stage_probe.py --sizes 197x52,120x34
    python _dev/stage_probe.py --reps 3         warm: the per-stage minimum over passes

Same two rules as `frame_probe`, for the same reasons: the collector is off (the player turns it off),
and a stage's warm number is the **minimum over passes** because noise only ever adds time.
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

# the same spread `frame_probe` uses, so the two tools talk about the same frames
TIMES = [5.0, 11.5, 20.0, 35.0, 50.0, 63.0, 80.0, 100.0, 120.0, 133.0, 148.0, 152.5,
         155.0, 158.0, 163.0, 170.0, 176.5, 180.0, 190.0, 200.0, 210.0]

#: `label -> ms` for the frame currently being measured.
CUR: dict[str, float] = {}
#: every wrapped label, in pipeline order, for the report
ORDER: list[str] = []


def wrap(obj, name: str, label: str | None = None) -> None:
    """Time `obj.name` into `CUR` under `label`, keeping the call's own return value."""
    fn = getattr(obj, name, None)
    if fn is None:
        return
    tag = label or f"{getattr(obj, '__name__', obj)}.{name}"
    ORDER.append(tag)

    def timed(*a, **kw):
        t0 = time.perf_counter()
        try:
            return fn(*a, **kw)
        finally:
            CUR[tag] = CUR.get(tag, 0.0) + (time.perf_counter() - t0) * 1000.0

    timed.__name__ = getattr(fn, "__name__", name)
    setattr(obj, name, timed)


def instrument() -> None:
    """Wrap the seven stages. Nested stages stay nested on purpose: `fx_apply`'s total is useful *and*
    so is knowing which of its three passes owns it."""
    import school_fx as FX
    # the frame body: the full-bleed shots are their own paths, so time the three of them together
    for n in ("draw_body", "draw_flood", "draw_collapse", "draw_footer"):
        wrap(T, n)
    # the variant's full-frame layer, and the transitions after it
    wrap(FX, "draw", "school_fx.draw")
    wrap(FX, "transition", "school_fx.transition")
    # the band put back over a `behind` event
    wrap(T, "draw_lyrics")
    # the film's own post, and its three passes separately
    for n in ("fx_reveal", "fx_trail", "fx_shake"):
        wrap(T, n)
    wrap(T, "fx_apply")
    # the make-consistent pass and the write to the terminal
    wrap(T.Screen, "normalise")
    wrap(T.Screen, "render_diff")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="197x52", help="comma-separated, e.g. 197x52,120x34")
    ap.add_argument("--reps", type=int, default=3, help="warm passes; per-stage minimum is reported")
    ap.add_argument("--top", type=int, default=10, help="stages to list")
    ap.add_argument("--cuts", action="store_true", default=True,
                    help="also sample the middle of every cut transition (default on)")
    ap.add_argument("--no-cuts", dest="cuts", action="store_false")
    a = ap.parse_args()

    gc.disable()                            # what the player does; see `frame_probe`

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.reset("s")
    import school_fx as FX
    first = [int(v) for v in a.sizes.split(",")[0].partition("x")[::2]]
    FX.warm(*first)
    eng = T.Engine()
    d = T.Data()
    T.FX.update(on=True, reveal=True, mech=True, trail=True, vig=True, shake=True)

    instrument()

    # **The plain time grid misses every transition.** A transition lasts `TRANS_DUR` (one beat, 0.4615 s)
    # from a row's start, and the 21 spread-out times landed inside almost none of them - the first run of
    # this probe reported the transition stage as absent while a `page` turn was live at 5.16 s and the
    # grid sampled 5.00. Any tool that prices transitions has to sample *inside* them, so each cut
    # contributes its own point at the middle of its turn.
    times = list(TIMES)
    if a.cuts:
        import school_fx as _fxc
        for at, (_kind, dur) in sorted(_fxc._cuts().items()):
            times.append(round(at + dur * 0.5, 4))
        times = sorted(set(times))

    for spec in a.sizes.split(","):
        c, _, r = spec.partition("x")
        cols, rows = int(c), int(r)
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        # per-time, per-stage minima; and the totals
        best: dict[float, dict[str, float]] = {}
        total_best: dict[float, float] = {}
        peak: dict[float, float] = {}
        for rep in range(max(1, a.reps)):
            for t in times:
                CUR.clear()
                t0 = time.perf_counter()
                T.draw(s, d, eng, t, True, 24.0)
                s.render_diff(sink)
                ms = (time.perf_counter() - t0) * 1000.0
                slot = best.setdefault(t, {})
                for k, v in CUR.items():
                    slot[k] = min(slot.get(k, v), v)
                total_best[t] = min(total_best.get(t, ms), ms)
                peak[t] = max(peak.get(t, ms), ms)

        wt = max(total_best, key=lambda k: total_best[k])
        print(f"=== {spec}: {len(times)} times x {a.reps} pass(es)"
              f"{'  (incl. the middle of every cut)' if a.cuts else ''}")
        print(f"  frame total   mean {sum(total_best.values()) / len(total_best):6.1f} ms   "
              f"worst {total_best[wt]:6.1f} ms at t={wt:6.2f}   peak {peak[wt]:6.1f} ms")
        # the stage table, by worst-case cost across the measured times
        worst_of: dict[str, float] = {}
        mean_of: dict[str, float] = {}
        for tag in ORDER:
            vals = [best[t].get(tag, 0.0) for t in times]
            worst_of[tag] = max(vals)
            mean_of[tag] = sum(vals) / len(vals)
        table = sorted(worst_of.items(), key=lambda kv: -kv[1])[:a.top]
        print(f"  {'stage':26} {'mean ms':>8} {'worst ms':>9}  {'at t':>7}")
        for tag, w in table:
            at = max(times, key=lambda t: best[t].get(tag, 0.0))
            print(f"  {tag:26} {mean_of[tag]:8.2f} {w:9.2f}  {at:7.2f}")
        print(f"  --- breakdown of the worst frame (t={wt:.2f}, {total_best[wt]:.1f} ms total) ---")
        for tag, v in sorted(best[wt].items(), key=lambda kv: -kv[1]):
            if v >= 0.05:
                print(f"      {tag:26} {v:8.2f} ms")
        acc = sum(best[wt].values())
        print(f"      {'(accounted)':26} {acc:8.2f} ms   "
              f"unaccounted {total_best[wt] - acc:6.2f} ms")
        print()

    raise SystemExit(0)


if __name__ == "__main__":
    main()
