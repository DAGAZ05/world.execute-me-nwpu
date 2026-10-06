"""Do any right-column performances last too long, and do they still match the words?

The user's note: "确保不会出现占时过长的演出，比如右边panel的西红柿那个光谱界面占了过长时间，和左侧歌词
都不对应了". The film's own shots are 1.2-3.7 s each, so a school pane that holds for eight or twelve seconds
is sitting through four to eight lyric lines - the right column stops following the song. This measures
that directly rather than by eye:

  * every named row's span, and how many of the *film's own shots* it covers;
  * how many rows are over `LIMIT`;
  * what share of the song is covered by a row that outlasts `LIMIT`;
  * **how much of each row is actually on screen** - a row whose whole life falls inside a shot that
    draws no pane is a pane nobody ever sees, which has happened twice (`pane_ai_rl` at 175.31, inside
    `shot_collapse`; `pane_motif_dijkstra` at 144.50, inside `shot_flood`).

It is a check, not a report: rows over `LIMIT` fail unless they are in `LONG_OK` with a reason, and a row
with less than `MIN_VISIBLE` seconds of visible life always fails. The same shape as `density_probe.KNOWN`
and `clock_probe.STILL_OK`.

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

# Rows that are allowed to be long, with the reason. Two, and each had to be argued rather than assumed -
# the batch that added this check took the count from fourteen to two, and every one of the others was
# split on a lyric line instead. `pane_curriculum` was the third until batch 48, when the college
# section's tail was re-cut and its 10.62 s became 5.10 s.
LONG_OK: dict[str, str] = {
    "pane_landmark_sword": "the accusation runs from 'Challenging your God' to the college gate, and the "
                           "question panel covers this column for the last five seconds of the row",
    "pane_landmark_crest": "the words end at 02:13.5 (see the row's own times) and the film holds a "
                           "single 12 s shot there; this is the closing plate",
}

# Shots that take the whole frame, so `tui_live.draw` never reaches `draw_body` and the right-hand column
# is not drawn at all. The school variant skips the film's own takeovers (`film_bleed` is False for it) -
# 大肥鱼 does not come back for the countdown - which leaves these four.
NO_PANE_SHOTS = {"shot_last_execution", "shot_black", "shot_flood", "shot_collapse"}

# ...and one window that is not a shot: the college gate is a five-second full-screen interface over a
# dimmed terminal (`school_gate.GATE_AT` + `WINDOW`), drawn before the shot branch and returning, so the
# pane behind it is not drawn either. Measured on the default path - nobody typing - because that is what
# an unattended playthrough shows.
MIN_VISIBLE = 0.30              # seconds; the shortest row the schedule is allowed has 0.395 s


def _blocked_windows():
    """The spans of the song in which no pane is drawn, merged and sorted."""
    out = []
    for e in T.Engine().table:
        if e["name"] in NO_PANE_SHOTS:
            out.append((e["start"], e["end"]))
    try:
        import school_gate as _G
        out.append((_G.GATE_AT, _G.GATE_AT + _G.WINDOW))
    except Exception as exc:                                    # a missing gate must not fail the check
        print(f"  note: the gate window is not being counted ({exc})")
    merged: list[list[float]] = []
    for lo, hi in sorted(out):
        if merged and lo <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return merged


def visible_seconds(at: float, end: float, blocked) -> float:
    """How much of `[at, end)` is on a frame that draws the pane at all."""
    free, cur = 0.0, at
    for lo, hi in blocked:
        if hi <= cur or lo >= end:
            continue
        if lo > cur:
            free += min(lo, end) - cur
        cur = max(cur, hi)
        if cur >= end:
            break
    if cur < end:
        free += end - cur
    return free


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=float, default=LIMIT)
    a = ap.parse_args()
    T.VAR[0] = "school"
    eng = T.Engine()
    shots = [(e["start"], e["end"]) for e in eng.table]
    blocked = _blocked_windows()
    rows = [r for r in SP.shot_rows() if r.get("name")]
    out = []
    for r in rows:
        span = r["end"] - r["at"]
        n = sum(1 for s, e in shots if e > r["at"] and s < r["end"])
        out.append((span, n, r["at"], r["name"], r.get("args"),
                    visible_seconds(r["at"], r["end"], blocked)))
    out.sort(reverse=True)
    bad, hidden, total = [], [], 0.0
    for span, n, at, name, args, vis in out:
        flag = ""
        if vis < MIN_VISIBLE:
            flag = f"   <-- NEVER ON SCREEN ({vis:.2f}s of {span:.2f}s drawn)"
            hidden.append((name, at, span, vis))
        if span > a.limit:
            total += span
            if name in LONG_OK:
                flag += f"   ({LONG_OK[name]})"
            else:
                flag += "   <-- TOO LONG"
                bad.append((name, at, span))
        print(f"  {at:7.2f} {span:6.2f}s  visible {vis:6.2f}s  {n:2} film shot(s)  "
              f"{name:24} {args or ''}{flag}")
    print(f"\n{len(rows)} named rows; {len(bad)} over {a.limit:.1f}s and unargued "
          f"({total:.1f}s of the song in long rows)")
    if bad:
        print("  FAIL: " + ", ".join(f"{n}@{at:.1f}s({sp:.1f}s)" for n, at, sp in bad))
    print(f"{len(hidden)} row(s) with under {MIN_VISIBLE:.2f}s of visible life")
    if hidden:
        print("  FAIL: " + ", ".join(f"{n}@{at:.1f}s({v:.2f}s drawn)" for n, at, _s, v in hidden))
    raise SystemExit(1 if (bad or hidden) else 0)


if __name__ == "__main__":
    main()
