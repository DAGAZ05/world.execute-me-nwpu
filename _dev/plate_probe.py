"""One pane, at the size the player really gives it, as a PNG - for art that is judged by looking.

`pane_probe.py` renders every pane at six sizes to catch *faults* (exceptions, ink outside the rect, a
bad colour tuple) and its shots are of its first size, 118x11. This does the opposite: a named pane, at
the production pane size, so a change to a landmark's characterisation can be compared with the last
one rather than described.

    python _dev/plate_probe.py                      the landmark panes, 95x33
    python _dev/plate_probe.py pane_landmark_sword
    python _dev/plate_probe.py pane_landmark_sword --size 118x33 --u 1.0
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402

DEFAULT = ["pane_landmark_hezun", "pane_landmark_sword", "pane_landmark_dialogue",
           "pane_landmark_cat", "pane_landmark_crest", "pane_memory"]
OUT = Path(__file__).resolve().parent / "out" / "plates"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("panes", nargs="*", default=None)
    ap.add_argument("--size", default="95x33")
    ap.add_argument("--u", type=float, default=1.0, help="reveal at which to draw")
    ap.add_argument("--tag", default="", help="suffix for the filenames")
    a = ap.parse_args()
    c, _, r = a.size.partition("x")
    w, h = int(c), int(r)

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    OUT.mkdir(parents=True, exist_ok=True)
    from tui_shot import Painter
    painter = Painter()

    for pane in (a.panes or DEFAULT):
        s = T.Screen(w + 6, h + 4)
        SP.draw_scene_pane(pane, s, 2, 2, 2 + w - 1, 2 + h - 1, 100.0, 2.0, 2.0, a.u)
        p = OUT / f"{pane}{('_' + a.tag) if a.tag else ''}.png"
        print(painter.paint(s, p, f"{pane}  {w}x{h}  u={a.u:.2f}"))


if __name__ == "__main__":
    main()
