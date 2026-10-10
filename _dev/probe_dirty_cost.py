"""How much does the batch-81 `dirty` collection cost the frame it belongs to?

`render_diff` now builds `[(row, [cols]), ...]` so the phosphor layer does not have to walk the screen
itself. That collection is work the frame did not do before, and it sits inside the player's hottest
function - so it has to be measured, not assumed to be free.

    python _dev/probe_dirty_cost.py --window 56.8,58.0 --rounds 7

It swaps in a variant of `tui_live.py` with the one line removed, measures both, and restores the
original from a backup it takes first. Anything else in the file is left alone.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TUI = ROOT / "player" / "_tools" / "tui_live.py"
ANCHOR = "            self.dirty.append((y, [x for x in range(self.cols) if row[x] != old[x]]))"


def measure(window: str, rounds: int) -> float:
    out = subprocess.run(
        [sys.executable, str(ROOT / "_dev" / "probe_ab_frame.py"), "--window", window,
         "--rounds", str(rounds)],
        capture_output=True, text=True, cwd=str(ROOT), encoding="utf-8", errors="replace",
    )
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 6 and "-" in parts[0] and parts[0][0].isdigit():
            return float(parts[2])
    raise SystemExit(f"could not read the median from:\n{out.stdout}\n{out.stderr}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--window", default="56.8,58.0")
    ap.add_argument("--rounds", type=int, default=7)
    a = ap.parse_args()

    src = TUI.read_text(encoding="utf-8")
    if ANCHOR not in src:
        raise SystemExit("the dirty-collection line is not where this probe expects it")
    before_sha = hashlib.sha256(TUI.read_bytes()).hexdigest()

    backup = Path(tempfile.mkdtemp(prefix="dirtycost")) / "tui_live.py"
    shutil.copy2(TUI, backup)
    try:
        with_collect = measure(a.window, a.rounds)

        TUI.write_text(src.replace(ANCHOR, "            pass"), encoding="utf-8")
        without = measure(a.window, a.rounds)
    finally:
        shutil.copy2(backup, TUI)

    after_sha = hashlib.sha256(TUI.read_bytes()).hexdigest()
    print(f"\nwindow {a.window}, {a.rounds} rounds, median ms")
    print(f"  with the dirty collection   {with_collect:7.1f}")
    print(f"  without it                  {without:7.1f}")
    print(f"  the collection costs        {with_collect - without:+7.1f} ms "
          f"({100 * (with_collect - without) / without:+.1f} %)")
    print(f"  file restored: {'yes, sha unchanged' if after_sha == before_sha else 'NO - CHECK IT'}")


if __name__ == "__main__":
    main()
