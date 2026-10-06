"""Does what plays match what was approved? The design table against the schedule.

    python _dev/design_check.py            a report; exit 1 when something needs a human look

`05_歌词会话对照_v2.md` is the approved design: one row per lyric line saying what "我" asks, what 航小天
answers, and what the right column draws. The schedule (`school_panels.shot_rows`) is what actually plays.
This lines the two up by time and reports:

  1. design rows whose time falls on no schedule row at all (the line has no panel of its own),
  2. design rows where the panel that is up does not obviously correspond to what the design says to draw
     - a *heuristic*, by keyword: 校门/gate, 校徽/crest, 何尊/hezun, 猫/cat, 铸剑/sword, 图书馆/library,
     对话的双手/dialogue, 运-20/y20, 歼-20/j20, 直-20/z20, 篮球/basket, 课程/exec, 母题/motif. A design row
     that names one of those and lands on a pane that names none of them is worth reading, not proof of a
     bug: the design allowed a panel to change when the later batches re-cut the song.
  3. schedule rows that no design row mentions (later inventions - fine, but list them so "approved" and
     "invented" can be told apart).
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_panels as SP      # noqa: E402

DESIGN = ROOT / "05_歌词会话对照_v2.md"
# the design's words -> what the schedule would call it
KEYWORDS = [
    (("\u6821\u95e8",), ("gate",)),
    (("\u6821\u5fbd",), ("crest",)),
    (("\u4f55\u5c0a",), ("hezun",)),
    (("\u732b",), ("cat",)),
    (("\u94f8\u5251", "\u5251"), ("sword",)),
    (("\u56fe\u4e66\u9986",), ("library",)),
    (("\u53cc\u624b", "\u5bf9\u8bdd"), ("dialogue",)),
    (("\u8fd0-20", "\u8fd020"), ("y20",)),
    (("\u6b7c-20", "\u6b7c20"), ("j20",)),
    (("\u76f4-20", "\u76f420"), ("z20",)),
    (("\u7bee\u7403",), ("basket", "dunk")),
    (("\u8bfe", "\u4e13\u4e1a"), ("exec", "gauge", "course")),
]


def secs(mmss: str) -> float | None:
    m = re.match(r"^(\d+):(\d+\.\d+)$", mmss)
    return int(m.group(1)) * 60 + float(m.group(2)) if m else None


def design_rows() -> list[tuple[int, float, str, str, str, str]]:
    out = []
    for ln in DESIGN.read_text(encoding="utf8").splitlines():
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 6 or not re.match(r"^\d+$", cells[0]):
            continue
        t = secs(cells[1])
        if t is None:
            continue
        out.append((int(cells[0]), t, cells[2], cells[3], cells[4], cells[5]))
    return out


def main() -> None:
    rows = SP.shot_rows()
    design = design_rows()
    print(f"design rows: {len(design)}   schedule rows: {len(rows)}")
    bad = 0
    print("\n== 1/2. every design row, and the panel that is up at its time ==")
    for idx, t, en, q, a, draw in design:
        row = next((r for r in rows if r["at"] - 1e-6 <= t < r["end"] - 1e-6), None)
        if row is None:
            print(f"   [{idx:2d}] {t:7.2f} {en[:38]:38s} -> NO SCHEDULE ROW   design draws: {draw[:40]}")
            bad += 1
            continue
        pane = row["name"] or "(film)"
        want = [want for words, want in KEYWORDS if any(w in draw for w in words)]
        if want and not any(w in pane for w in want[0]):
            print(f"   [{idx:2d}] {t:7.2f} {en[:30]:30s} -> {pane:26s} but design asks {draw[:46]}")
            bad += 1
    print("\n== 3. schedule rows no design row is anchored to ==")
    mentioned = {next((r["name"] for r in rows if r["at"] - 1e-6 <= t < r["end"] - 1e-6), None)
                 for _i, t, _e, _q, _a, _d in design}
    for r in rows:
        if r["name"] not in mentioned:
            print(f"   {r['at']:7.2f} {r['name'] or '(film)':26s} {r['lyric'][:40]}")
    print(f"\n== {bad} design row(s) needing a human look ==")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
