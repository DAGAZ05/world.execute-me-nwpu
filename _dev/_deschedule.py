"""One-shot: replace every repeated drawing with one chosen for the lyric it sits on.

    python _dev/_deschedule.py

The user: "有些演出重复了很多次，除了校徽、铸剑雕塑外的演出禁止重复，请依据歌词给出合适的图案演出". The
audit is `_dev/repeat_probe.py` (8x the two hands, 3x the point set, 2x several others). Each row below is
a `(time, pane, ops)` triple; the pane at that time is replaced, and the ops ticker with it. The first
appearance of each drawing stays where it is - the ones below are the later ones.

`pane_motif_*` are `school_motifs`' twenty-two drawings promoted to panes (`school_scenes._motif`), each
picked here for what its own title means: He initialisation on "Initialization", phyllotaxis in the gap
after the campus opening, the sine on "If I'm a sine wave", binary and the pixel sort on "Give you all the
simulations", the galaxy on "If I can make you happy", `en_limit` on "Though we are trapped", the starburst
on "If I'm the only God", the quantiser / Chladni plate / fork bomb on the three "switch" lines, the
lattice on "So we can enter", moiré on "The trance", the superellipse on "If I can, if I can", the
epicycles on "Then I can, then I can", Byrne's plate at the second convergence, the Bessel curve on
"Though you are free", and the shutdown counter where the execution run ends.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PANELS = ROOT / "player" / "_tools" / "school_panels.py"

# (time, new pane, new ops)
PLAN = [
    (9.75, "pane_motif_he_init", ["He \u521d\u59cb\u5316", "REPLACE"]),
    (25.14, "pane_motif_phyllotaxis", ["\u53f6\u5e8f", "GROW"]),
    (36.77, "pane_motif_sine", ["\u6b63\u5f26", "ENVELOPE"]),
    (60.57, "pane_motif_binary", ["0101", "\u6a21\u62df"]),
    (62.00, "pane_motif_pixelsort", ["PIXELSORT", "\u6392\u5e8f"]),
    (66.17, "pane_motif_galaxy", ["GALAXY", "\u661f\u7cfb"]),
    (70.02, "pane_motif_en_limit", ["\u2203n", "LIMIT"]),
    (84.60, "pane_motif_stardiff", ["STAR", "\u884d\u5c04"]),
    (88.34, "pane_motif_quantize", ["QUANTIZE", "3 bits"]),
    (92.00, "pane_motif_chladni", ["CHLADNI", "\u8282\u70b9"]),
    (95.28, "pane_motif_fork_bomb", ["FORK", "\u89d2\u8272"]),
    (98.93, "pane_motif_lattice", ["LATTICE", "TRANCE"]),
    (101.13, "pane_motif_moire", ["MOIRE", "TRANCE"]),
    (103.03, "pane_motif_hyperellipse", ["|x|^n", "\u8d85\u692d\u5706"]),
    (106.84, "pane_motif_epicycles", ["EPICYCLE", "FOURIER"]),
    (161.41, "pane_motif_powerdown", ["POWERDOWN", "N \u2192 1"]),
    (166.05, "pane_motif_byrne", ["BYRNE", "PLATE"]),
    (187.97, "pane_motif_bessel", ["BESSEL", "\u632f\u52a8"]),
]


def main() -> None:
    s = PANELS.read_text(encoding="utf8")
    done = 0
    for at, name, ops in PLAN:
        # the row is `dict(at=9.75, name="pane_polyhedra", lyric=..., ops=[...], mascot=False)`
        pat = re.compile(r"dict\(at=" + re.escape(f"{at:.2f}") + r", name=\"([a-z_0-9]+)\"")
        m = pat.search(s)
        if not m:
            print(f"  {at:7.2f}  NOT FOUND")
            continue
        old = m.group(1)
        s = s[:m.start(1)] + name + s[m.end(1):]
        # ...and the ops list of the same row, which is the next `ops=[...]` after it
        o = re.compile(r"ops=\[[^\]]*\]")
        mo = o.search(s, m.end())
        if mo:
            new_ops = "ops=[" + ", ".join('"' + str(x).replace('"', '\\"') + '"' for x in ops) + "]"
            s = s[:mo.start()] + new_ops + s[mo.end():]
        print(f"  {at:7.2f}  {old:26s} -> {name}")
        done += 1
    PANELS.write_text(s, encoding="utf8")
    print(f"{done} row(s) reassigned")


if __name__ == "__main__":
    main()
