"""Which drawings repeat, and which lyrics they are on? The audit behind "除校徽、铸剑雕塑外禁止重复".

    python _dev/repeat_probe.py                every row, then every drawing by count
    python _dev/repeat_probe.py --from 130     only the rows after this time

The user's note is that "有些演出重复了很多次，除了校徽、铸剑雕塑外的演出禁止重复，请依据歌词给出合适的图案
演出". A drawing that comes back four times is four times the screen for one idea, and it also means three
lyrics are being illustrated by something aimed at a different one. This prints the schedule from the
variant's own table - so it cannot disagree with what plays - with the lyric each row is hung on, and then
the count per drawing, so the repeats and the spare vocabulary are both visible in one place.
"""
from __future__ import annotations

import argparse
import collections
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_panels as SP      # noqa: E402

# the two the user exempts by name
ALLOWED = {"pane_landmark_crest", "pane_landmark_sword"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="lo", type=float, default=0.0)
    a = ap.parse_args()

    rows = [r for r in SP.shot_rows() if r.get("name") and r["at"] >= a.lo]
    counts: collections.Counter = collections.Counter()
    for r in rows:
        args = r.get("args") or {}
        key = r["name"] + ("(" + ",".join(f"{k}={v}" for k, v in sorted(args.items())) + ")"
                           if args else "")
        counts[key] += 1
        print(f"{r['at']:8.2f}-{r['end']:8.2f}  {key:46s}  {r.get('lyric', '')}")
    print("\n--- by count (a drawing that appears once is not listed) ---")
    for key, n in counts.most_common():
        if n > 1:
            flag = "  (allowed: the user exempts it)" if key.split("(")[0] in ALLOWED else ""
            print(f"  {n:2d}x  {key}{flag}")
    print(f"\n{len(rows)} row(s), {len(counts)} distinct drawing(s) - "
          f"{sum(n - 1 for k, n in counts.items() if k.split('(')[0] not in ALLOWED)} repeat(s) to replace")


if __name__ == "__main__":
    main()
