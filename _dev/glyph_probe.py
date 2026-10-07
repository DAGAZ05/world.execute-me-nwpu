"""Which sub-cell glyphs can this machine actually draw? Quadrants, braille, sextants, blocks.

    python _dev/glyph_probe.py

The film draws its pictures with `▀` plus a foreground and a background colour, which is one sub-cell
pair per cell. A quadrant (`▖▝▞▟`...) is 2x2 sub-cells with the same two colours, and a braille cell is
2x4 - four and eight times the detail for nothing but a different character. Whether they are *usable*
is a font question, not a taste question: the terminal's font has to have the glyph, and this project
already knows what a missing one costs (the waveform ramp rendered as `?` boxes until `tui_shot` sent
everything past ASCII to msyh). So this renders each family with the fonts the player and the renderer
use and reports whether the glyph came out empty or as a `.notdef` box.

**Three things had to be fixed before this probe could answer anything** (batch 39 - it had never been
run in this checkout, and `_dev/out/glyphs.png` did not exist to say so):

  * it printed the glyphs themselves to stdout, and a Windows console is GBK by default: the very first
    run died with `UnicodeEncodeError: 'gbk' codec can't encode character '\\u2580'`, i.e. the probe
    crashed on the family it exists to measure. Output is now ASCII-only and the glyphs go to the PNG;
  * `FONTS` was missing `consolab.ttf`, which is the monospace font the player itself names
    (`tui_live._F_MONO_B`); `consola.ttf` is the *renderer's* ASCII font (`tui_shot`), so the probe was
    measuring a different font from the one the film draws with;
  * a load failure returns `-1` from `glyph_ink`, and the blank count only counted `0` - so a font that
    could not be loaded at all was reported as "0 blank of N", i.e. perfect.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FAMILIES = {
    "blocks": [chr(c) for c in range(0x2580, 0x25A0)],
    "quadrants": [chr(c) for c in range(0x2596, 0x25A0)],
    "braille": [chr(c) for c in range(0x2800, 0x2900, 0x11)],
    "sextants": [chr(c) for c in range(0x1FB00, 0x1FB3C, 5)],
    "shade": [chr(c) for c in (0x2591, 0x2592, 0x2593)],
    "geometric": [chr(c) for c in (0x25A0, 0x25AA, 0x25CF, 0x25CB, 0x25B2)],
}
# `consolab.ttf` first because it is the one the player names for its own monospace output; `consola`
# is the renderer's ASCII face, and the CJK faces are what everything past ASCII falls back to.
FONTS = ["C:/Windows/Fonts/consolab.ttf", "C:/Windows/Fonts/consola.ttf",
         "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc",
         "C:/Windows/Fonts/simsun.ttc", "C:/Windows/Fonts/SimHei.ttf"]


def glyph_ink(font: ImageFont.FreeTypeFont, ch: str, size: int = 16) -> int:
    """How many pixels the glyph actually puts on the mask. 0 = blank, a full box = a fallback `.notdef`."""
    try:
        mask = font.getmask(ch)
    except Exception:
        return -1
    w, h = mask.size
    if not w or not h:
        return 0
    data = mask.tobytes() if hasattr(mask, "tobytes") else bytes(mask)
    return sum(1 for b in data if b > 40)


def verdict(inks: list[int]) -> str:
    """One family's reading, in words. `-1` (the font could not draw it at all) counts as a failure."""
    if any(i < 0 for i in inks):
        return "FAILED to measure"
    blank = sum(1 for i in inks if i == 0)
    if blank == len(inks):
        return "NO GLYPH (all blank)"
    if len(set(inks)) == 1:
        return "SAME INK for all (a fallback box)"
    if blank:
        return f"partial: {blank} blank of {len(inks)}"
    return f"ok ({min(inks)}-{max(inks)} px)"


def main() -> None:
    # ASCII only: a Windows console is GBK and the glyphs are not in it. See the module docstring.
    print("sub-cell glyph coverage, per font (ink pixels per glyph, 16px)")
    print("families: " + ", ".join(f"{k}={len(v)}" for k, v in FAMILIES.items()))
    print()
    summary: dict[str, dict[str, str]] = {}
    for path in FONTS:
        p = Path(path)
        if not p.exists():
            print(f"{p.name:14s} (not installed)")
            continue
        try:
            font = ImageFont.truetype(path, 16)
        except Exception as exc:                      # noqa: BLE001
            print(f"{p.name:14s} cannot be loaded: {exc}")
            continue
        print(f"{p.name}")
        summary[p.name] = {}
        for family, chars in FAMILIES.items():
            inks = [glyph_ink(font, c) for c in chars]
            v = verdict(inks)
            summary[p.name][family] = v
            lo = min(i for i in inks if i >= 0) if any(i >= 0 for i in inks) else -1
            hi = max(inks)
            print(f"   {family:10s} {v:34s} [{lo}..{hi}]")
        print()
    # ...and what the renderer would actually show, as one PNG: this is where the glyphs themselves go
    im = Image.new("RGB", (760, 40 * len(FAMILIES) + 10), (10, 12, 18))
    d = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 20)
    except Exception:
        f = ImageFont.load_default()
    y = 5
    for family, chars in FAMILIES.items():
        d.text((6, y), "".join(chars[:24]), font=f, fill=(230, 236, 248))
        d.text((640, y), family, font=f, fill=(120, 140, 180))
        y += 40
    out = Path(__file__).resolve().parent / "out" / "glyphs.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(f"sample sheet -> {out}")

    # a one-line answer to the question this was written for
    print()
    for family in ("quadrants", "braille", "sextants"):
        good = [name for name, fam in summary.items() if fam.get(family, "").startswith("ok")]
        print(f"{family:10s} usable in: {', '.join(good) if good else 'NONE'}")
    raise SystemExit(check_source() or 0)


# ---------------------------------------------------------------- every glyph the project prints
#
# **The check the film needed and did not have** (batch 50). `FAMILIES` above measures glyphs the project
# is *considering*; nothing measured the glyphs it already uses. The user's question about shot 8 ("stdout
# 中的字体是什么") led to the answer that a terminal has no font of its own to choose - and then to the
# question that does have an answer: which of the characters this project prints can the renderer draw?
# `tui_shot.Painter` sends ASCII to Consolas and *everything else* to 微软雅黑, so a non-ASCII codepoint is
# a `.notdef` box wherever msyh lacks it, and **eighteen of them were**: `▶ ◀ ▷ ▸ ▾ ✓ ✗ ⚠ ⇓ ∃ ∇ ⋯ ❓ ⟩`
# and the subscripts `₀₁₂₄₅`. They were visible in exported frames as boxes (`▸` beside 大二, `✓`/`✗` in the
# college gate, `▶`/`◀` on the deep-learning graph) and invisible to every other probe, because a box is
# still ink.
#
# **The test is a rendering, not a cmap**, and that is not pedantry: `msyh.ttc`'s `cmap` table claims
# `░` and `▒` are both absent, and the renderer draws `▒` correctly and `░` as a box. The reference is an
# unassigned codepoint, whose mask *is* the `.notdef` the reader sees.
RENDER_FONTS = {"ascii": "C:/Windows/Fonts/consola.ttf", "wide": "C:/Windows/Fonts/msyh.ttc"}
#: glyphs the Painter draws as a *pattern* instead of a character, so a missing glyph does not matter
PAINTED = set("\u2580\u2584\u2588\u2581\u2582\u2583\u2585\u2586\u2587\u2591\u2592\u2593\u258c\u2590")
REFERENCE = 0x0378                            # unassigned: whatever it renders is the fallback


def _mask(font, ch: str):
    try:
        m = font.getmask(ch, mode="L")
    except Exception:                         # noqa: BLE001
        return None
    return (m.size, m.tobytes() if hasattr(m, "tobytes") else bytes(m))


def check_source() -> int:
    import re
    sources = sorted((Path(__file__).resolve().parents[1] / "player" / "_tools").glob("*.py"))
    esc = re.compile(r"\\u([0-9a-fA-F]{4})")
    used: dict[int, set] = {}
    for p in sources:
        txt = p.read_text(encoding="utf8")
        chars = {ch for ch in txt if ord(ch) > 127}
        for m in esc.finditer(txt):
            chars.add(chr(int(m.group(1), 16)))
        for ch in chars:
            used.setdefault(ord(ch), set()).add(p.name)
    fonts, refs = {}, {}
    for name, path in RENDER_FONTS.items():
        try:
            fonts[name] = ImageFont.truetype(path, 16)
        except Exception:                     # noqa: BLE001
            print(f"note: {path} cannot be loaded")
            fonts[name] = ImageFont.load_default()
        refs[name] = _mask(fonts[name], chr(REFERENCE))
    bad, painted = [], []
    for cp, where in sorted(used.items()):
        if cp < 128:
            continue                          # ASCII is Consolas's whole job
        if chr(cp) in PAINTED:
            painted.append((cp, where))
            continue
        reading = _mask(fonts["wide"], chr(cp))
        if reading is None or not reading[1] or reading == refs["wide"]:
            bad.append((cp, where))
    print()
    print(f"glyphs the project prints, against the renderer's fonts "
          f"({len(used)} codepoints over {len(sources)} modules):")
    for cp, where in bad:
        print("  FAIL U+%04X renders as the fallback box  (%s)" % (cp, ",".join(sorted(where))[:70]))
    print(f"  {len(bad)} missing, {len(painted)} drawn as patterns by the painter "
          f"({len(painted)} of them)")
    return 1 if bad else 0


if __name__ == "__main__":
    main()
