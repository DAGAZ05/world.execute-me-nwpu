"""Every panel's on-screen *text*, read out of the buffer - one pane at a time, at two sizes.

    python _dev/pane_text.py                    writes _dev/out/audit/pane_text.txt
    python _dev/pane_text.py pane_motif_sine    one pane, printed

For the batch's correlation table the interesting column is "what words does this drawing print": the
title, the labels, the caption. Reading them from the drawing's own buffer (rather than from the source)
is also the cross-check on the audits: a claim about a caption can be compared with the caption the
player really writes, character for character.

Each pane is drawn alone in a box (95x33 - the real size at 197x52 - and 95x11, the size `PANE_MIN`
allows on a small window), at three points of its own reveal, and the union of the text rows is printed.
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
import school_panels as SP      # noqa: E402
import school_scenes as SC      # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "audit"
OUT.mkdir(parents=True, exist_ok=True)
SIZES = ((95, 33), (95, 11))
# a time inside each pane's own schedule row, so `u` is high and the drawing is complete
MID = {r["name"]: (r["at"] + r["end"]) / 2 for r in SP.shot_rows() if r["name"]}


def text_of(pane: str, w: int, h: int, t: float) -> list[str]:
    s = T.Screen(w, h)
    sig = SC.PANE_BY_NAME.get(pane)
    if sig is None:
        return ["<no such pane>"]
    u = 1.0
    for args in (None,):
        try:
            sig(s, 0, 0, w - 1, h - 1, t, 0.5, 1.0, u, args) if pane.startswith("pane_motif_") \
                else sig(s, 0, 0, w - 1, h - 1, t, 0.5, 1.0, u)
        except TypeError:
            sig(s, 0, 0, w - 1, h - 1, t, 0.5, 1.0, u)
    out = []
    for y in range(h):
        row = "".join(s.buf[y][x][0] for x in range(w)).rstrip()
        if row.strip():
            out.append(f"{y:2d}|{row}")
    return out


def main() -> None:
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    names = [n for n in dict.fromkeys(r["name"] for r in SP.shot_rows()) if n]
    names += [n for n in sorted(SC.PANE_BY_NAME) if n not in names]
    if len(sys.argv) > 1:
        names = sys.argv[1:]
    lines: list[str] = []
    for pane in names:
        t = MID.get(pane, 30.0)
        lines.append(f"\n===== {pane}  (schedule mid t={t:.2f}) =====")
        for w, h in SIZES:
            rows = text_of(pane, w, h, t)
            lines.append(f"-- {w}x{h}")
            lines.extend("   " + r for r in rows)
    (OUT / "pane_text.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    if len(sys.argv) > 1:
        print("\n".join(lines))
    else:
        print(f"{len(names)} panes -> {OUT / 'pane_text.txt'}")


if __name__ == "__main__":
    main()
