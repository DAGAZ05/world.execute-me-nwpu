"""Audit the dialogue rows in the code: does each row's time match its own lyric line?

    python _dev/chat_audit.py

Three questions, all answerable from the sources the player reads:

  * **time vs lyric** - a row carries `(t, lyric, who, text)`; the lyric has its own time in
    `input/lyrics.lrc`, so `t` should be that time. This is how the Ein/dos row was found sitting
    9.00 s before its own lyric while its own timestamp cell said `02:38`;
  * **time vs its own timestamp** - `meta` rows carry `用时 X 秒|MM:SS`, and the `MM:SS` is the time the
    exchange is supposed to be landing at. A row whose meta says `02:38` and whose `t` is 149.79 is
    disagreeing with itself;
  * **coverage** - `school_chat.check_coverage()`, plus every line of `lyrics.lrc` accounted for.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")
sys.stdout.reconfigure(encoding="utf8", errors="replace")

import school_chat as CH          # noqa: E402
import school_lines as L1         # noqa: E402
import school_lines_act2 as L2    # noqa: E402

LRC = ROOT / "player" / "input" / "lyrics.lrc"


def lrc_rows() -> list[tuple[float, str]]:
    out = []
    for ln in LRC.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\[(\d+):(\d+\.\d+)\](.*)", ln)
        if m:
            t = int(m.group(1)) * 60 + float(m.group(2))
            if m.group(3).strip():
                out.append((t, m.group(3).strip()))
    return out


def main() -> int:
    lrc = lrc_rows()
    alltimes: dict[str, list[float]] = {}
    for t, text in lrc:
        alltimes.setdefault(text, []).append(t)

    def nearest(lyric: str, t: float) -> float | None:
        """The occurrence of `lyric` closest to `t` - the song repeats lines, so the first is wrong."""
        cand = alltimes.get(lyric)
        return min(cand, key=lambda x: abs(x - t)) if cand else None

    bad = 0
    print("rows whose time disagrees with their own lyric line (tolerance 0.05 s):")
    for rows, act in ((L1.ACT_ONE, 1), (L2.ACT_TWO, 2)):
        for t, lyric, who, text in rows:
            if lyric.startswith("[gap]"):
                continue
            want = nearest(lyric, t)
            if want is None:
                print(f"  act{act} {t:7.2f}  lyric {lyric!r} is not in lyrics.lrc")
                bad += 1
            elif abs(want - t) > 0.05:
                print(f"  act{act} {t:7.2f}  lyric {lyric!r} is at {want:7.2f}  ({want - t:+.2f} s)")
                bad += 1
    if not bad:
        print("  none")
    print()
    print("meta timestamp against its own row's time:")
    drift: list[tuple[float, float, str]] = []
    for rows, act in ((L1.ACT_ONE, 1), (L2.ACT_TWO, 2)):
        for t, lyric, who, text in rows:
            if who != "meta" or "|" not in text:
                continue
            stamp = text.split("|", 1)[1].strip()
            m = re.match(r"^(\d+):(\d+)$", stamp)
            if not m:
                print(f"  act{act} {t:7.2f}  meta {stamp!r} is not MM:SS")
                continue
            want = int(m.group(1)) * 60 + int(m.group(2))
            drift.append((t, want - t, stamp))
    # The cell is a hand-written decorative clock and its own style drifts by about a second (`用时 1.2 秒`
    # arriving next to `00:01`); what it may not do is disagree with its row by seconds, which is a screen
    # contradicting itself. 1.5 s is the "worth a look" line, 3.0 s is the failure line.
    for t, d, stamp in drift:
        if abs(d) > 1.5:
            print(f"  {t:7.2f}  meta says {stamp}  ({d:+.2f} s)"
                  + ("   <-- FAIL" if abs(d) > 3.0 else ""))
    ok = [d for _t, d, _s in drift if abs(d) <= 1.5]
    print(f"  {len(ok)} of {len(drift)} within 1.5 s; "
          f"median {sorted(d for _t, d, _s in drift)[len(drift) // 2]:+.2f} s")
    bad_clock = [x for x in drift if abs(x[1]) > 3.0]
    print()
    print("coverage:", CH.check_coverage() or "every lyric line is handled")
    print("blocks:", len(CH._DIALOGUE), " lines:", sum(len(b[2]) for b in CH._DIALOGUE))
    return 1 if (bad or bad_clock or CH.check_coverage()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
