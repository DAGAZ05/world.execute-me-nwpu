"""Read every Chinese character this variant can print, against the project's own vocabulary.

    python _dev/text_check.py            exit 1 if anything is flagged

Two checks, both cheap and both aimed at one failure mode: the drawing modules write Chinese as `\\uXXXX`
escapes, so a *valid but wrong* character is invisible in the source (it reads as an escape), invisible in
a diff (two escapes differ by one hex digit) and invisible on screen (it renders as a glyph). The motto
`公诚勇毅` was written `公诚勇毁` in three places that way - U+6BC1 instead of U+6BC5 - and nobody could
see it. See `04_验证记录/批次31_时序对照与内容核验.md`.

1. **Vocabulary**: every CJK character used in an on-screen string of the school modules must also occur
   somewhere in the project's own prose (`*.md`). The prose is where these words were decided, so a
   character that only ever appears in a string literal is either a new word or a typo - and it is worth a
   human look either way. This is a *filter*, not a verdict: it cannot tell 毅 from 毁 if both are in the
   prose, which is exactly why check 2 exists.
2. **Required terms**: the school's own fixed vocabulary, spelled out, plus the wrong spellings it has
   actually been written with. Each expected term must occur at least once in the decoded strings and on
   screen; each known-wrong variant must not occur at all.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"
MODULES = ["school_scenes.py", "school_courses.py", "school_motifs.py", "school_panels.py",
           "school_chat.py", "school_fx.py", "school_sculpture.py", "school_machine.py",
           # the dialogue's two halves: `school_chat.DIALOGUE` is only the first thirty seconds, and the
           # rest of the song is the flat row files `school_lines` (act 1) and `school_lines_act2`
           "school_lines.py", "school_lines_act2.py"]
CJK = re.compile(r"[\u3400-\u9fff]")

# (term, why it is fixed) - a name the school owns, so the exact characters matter
REQUIRED = [
    ("\u897f\u5317\u5de5\u4e1a\u5927\u5b66", "the university's name"),
    ("\u516c\u8bda\u52c7\u6bc5", "the motto"),
    ("\u4e09\u5b9e\u4e00\u65b0", "the work style"),
    ("\u542f\u7fd4\u6e56", "the lake"),
    ("\u4f55\u5c0a", "the bronze vessel"),
    ("\u4e3a\u56fd\u94f8\u5251", "the sculpture"),
    ("\u4e09\u822a", "aviation / spaceflight / marine"),
]
# (wrong spelling, the right one) - written by mistake at least once, so it is checked by name
FORBIDDEN = [
    ("\u516c\u8bda\u52c7\u6bc1", "\u516c\u8bda\u52c7\u6bc5"),          # 毁 for 毅
    ("\u897f\u5de5\u5927\u5b66", "\u897f\u5317\u5de5\u4e1a\u5927\u5b66"),
]


def strings() -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    for mod in MODULES:
        src = (TOOLS / mod).read_text(encoding="utf8")
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if CJK.search(node.value):
                    out.append((mod, node.lineno, node.value))
    return out


def main() -> None:
    corpus = []
    for p in sorted(ROOT.rglob("*.md")):
        if "_dev" in p.parts and "out" in p.parts:
            continue
        corpus.append(p.read_text(encoding="utf8", errors="replace"))
    vocab = set("".join(corpus))
    bad = 0

    print("== 1. characters used on screen but nowhere in the project's prose ==")
    odd: dict[str, list[str]] = {}
    for mod, ln, s in strings():
        for ch in set(s):
            if CJK.match(ch) and ch not in vocab:
                odd.setdefault(ch, []).append(f"{mod}:{ln}")
    for ch, where in sorted(odd.items()):
        print(f"   {ch} U+{ord(ch):04X}  x{len(where)}  first {where[0]}")
        bad += 1
    if not odd:
        print("   none")

    print("== 2. the school's own vocabulary, spelled as it must be ==")
    joined = "\n".join(s for _m, _l, s in strings())
    for term, why in REQUIRED:
        n = joined.count(term)
        print(f"   {'ok  ' if n else 'MISS'} {term} ({why}) x{n}")
        bad += 0 if n else 1
    for wrong, right in FORBIDDEN:
        n = joined.count(wrong)
        print(f"   {'ok  ' if not n else 'BAD '} {wrong} must not occur (write {right}) x{n}")
        bad += 1 if n else 0
    print(f"== {bad} thing(s) to look at ==")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
