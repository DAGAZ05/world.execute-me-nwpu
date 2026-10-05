"""Does the basketball animation really reach the screen during the live loop?

    python _dev/dunk_live_probe.py 197x52           (or any COLSxROWS)

`_dev/dump_frame.py` showed the art fine, and so did the batch-24 renders - but the user reports it
"completely gone" when they play the film. The difference between the two is everything `main()` does
around a frame, and the biggest of those is the schedule walk it runs *before* the music: 36 frames of
`draw()` at row start times, into a throwaway screen, which is the only place in the program that
draws the animation outside the loop.

So this probe does not guess at the cause. It imports the player, replaces the dunk's entry in the
event table with one that reports what it drew and what `LEFT_BOX` was when it drew it, and then runs
the *real* `main()` - the warm-up, the schedule walk, the live loop - with the clock started just
before the window. Every frame of 58.6-70.1 s is logged with the ink inside the box, so "it is on
screen" and "it is not" are both answerable by reading a file.

`stdout` goes to a string: the live loop hides the cursor and switches to the alternate screen, and
none of that belongs in a terminal we are reading. Sound is off (the clock is wall-clock either way).
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402


def main() -> None:
    size = sys.argv[1] if len(sys.argv) > 1 else "197x52"
    c, _, r = size.partition("x")
    cols, rows = int(c), int(r)
    T.VAR[0] = "school"
    T.term_size = lambda default=(120, 34): (cols, rows)      # type: ignore[assignment]

    import school_fx as FX

    log: list[str] = []
    original = FX.dunk

    def traced(s, cc, rr, t, u, **kw):
        box = tuple(T.LEFT_BOX)
        before = sum(1 for y in range(box[1], box[3] + 1)
                     for x in range(box[0], box[2] + 1)
                     if 0 <= y < s.rows and 0 <= x < s.cols and s.buf[y][x][0] not in (" ", ""))
        err = ""
        try:
            original(s, cc, rr, t, u, **kw)
        except Exception as exc:                     # the player swallows this; here it must show
            err = f"{type(exc).__name__}: {exc}"
        after = sum(1 for y in range(box[1], box[3] + 1)
                    for x in range(box[0], box[2] + 1)
                    if 0 <= y < s.rows and 0 <= x < s.cols and s.buf[y][x][0] not in (" ", ""))
        log.append(f"t={t:7.2f}  box={box}  ink {before:5d} -> {after:5d}  "
                   f"kw={sorted(kw)}  {err}")
        return None

    for i, (a, b, fn, kw) in enumerate(FX.EVENTS):
        if fn is original:
            FX.EVENTS[i] = (a, b, traced, kw)

    # The live loop does not end when the song does - it holds the last frame until `q` - so the probe
    # stops itself a second past the window instead. It waits for the trace to have filled up first,
    # because the schedule walk (which runs before the music) also draws inside the window.
    class Stop(Exception):
        pass

    real_draw = T.draw

    def draw_stop(s, d, eng, t, playing, fps, audio=None):
        if t > 71.2 and len(log) >= 40:
            raise Stop
        return real_draw(s, d, eng, t, playing, fps, audio)

    T.draw = draw_stop                        # type: ignore[assignment]

    out, errf = io.StringIO(), io.StringIO()
    saved = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, errf
    sys.argv = ["tui_live.py", "--variant", "school", "--no-audio",
                "--start", "58.4", "--size", size]
    try:
        T.main()
    except (SystemExit, Stop):
        pass
    except BaseException as exc:                     # noqa: BLE001 - report, do not hide
        log.append(f"the loop ended early: {type(exc).__name__}: {exc}")
    finally:
        sys.stdout, sys.stderr = saved

    dest = Path(__file__).resolve().parent / "out" / "dunk_live.txt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    header = [f"{size}  {len(log)} frame(s) traced  (stderr follows)",
              errf.getvalue().strip() or "(no stderr)", ""]
    dest.write_text("\n".join(header + log) + "\n", encoding="utf8")
    hits = sum(1 for line in log if "->" in line and int(line.split("->")[1].split()[0]) > 100)
    print(f"{len(log)} frame(s), {hits} with the art on screen -> {dest}")


if __name__ == "__main__":
    main()
