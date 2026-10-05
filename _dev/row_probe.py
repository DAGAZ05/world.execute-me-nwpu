"""Do any right-column performances last too long, and do they still match the words?

The user's note: "确保不会出现占时过长的演出，比如右边panel的西红柿那个光谱界面占了过长时间，和左侧歌词
都不对应了". The film's own shots are 1.2-3.7 s each, so a school pane that holds for eight or twelve seconds
is sitting through four to eight lyric lines - the right column stops following the song. This measures
that directly rather than by eye:

  * every named row's span, and how many of the *film's own shots* it covers;
  * how many rows are over `LIMIT`;
  * what share of the song is covered by a row that outlasts `LIMIT`.

It is a check, not a report: rows over `LIMIT` fail unless they are in `LONG_OK` with a reason, the same
shape as `density_probe.KNOWN` and `clock_probe.STILL_OK`.

    python _dev/row_probe.py            every named row, longest first
    python _dev/row_probe.py --limit 6  a different ceiling
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

# The film's own shots run 1.2-3.7 s (`_dev/shots.py`), and the school's panes are its replacement, so a
# row that outlasts two of them is a row the song has moved past. Four seconds is the round number above
# the longest film shot; six is where it stops being a matter of taste.
LIMIT = 6.0

# Rows that are allowed to be long, with the reason. Three, and each had to be argued rather than
# assumed - the batch that added this check took the count from fourteen to three, and every one of the
# other eleven was split on a lyric line instead.
LONG_OK: dict[str, str] = {
    "pane_curriculum": "one subject - the four years, which is the answer to the question the gate just "
                       "asked - and it advances on its own clock: the lit year column walks every 1.4 s",
    "pane_landmark_sword": "the accusation runs from 'Challenging your God' to the college gate, and the "
                           "question panel covers this column for the last five seconds of the row",
    "pane_landmark_crest": "the words end at 02:13.5 (see the row's own times) and the film holds a "
                           "single 12 s shot there; this is the closing plate",
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=float, default=LIMIT)
    a = ap.parse_args()
    T.VAR[0] = "school"
    eng = T.Engine()
    shots = [(e["start"], e["end"]) for e in eng.table]
    rows = [r for r in SP.shot_rows() if r.get("name")]
    out = []
    for r in rows:
        span = r["end"] - r["at"]
        n = sum(1 for s, e in shots if e > r["at"] and s < r["end"])
        out.append((span, n, r["at"], r["name"], r.get("args")))
    out.sort(reverse=True)
    bad, total = [], 0.0
    for span, n, at, name, args in out:
        flag = ""
        if span > a.limit:
            total += span
            if name in LONG_OK:
                flag = f"   ({LONG_OK[name]})"
            else:
                flag = "   <-- TOO LONG"
                bad.append((name, at, span))
        print(f"  {at:7.2f} {span:6.2f}s  {n:2} film shot(s)  {name:24} {args or ''}{flag}")
    print(f"\n{len(rows)} named rows; {len(bad)} over {a.limit:.1f}s and unargued "
          f"({total:.1f}s of the song in long rows)")
    if bad:
        print("  FAIL: " + ", ".join(f"{n}@{at:.1f}s({sp:.1f}s)" for n, at, sp in bad))
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
