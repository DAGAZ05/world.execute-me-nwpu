"""Every string the school variant can print, decoded, with file:line - for reading, not for running.

    python _dev/text_inventory.py            writes _dev/out/audit/text_inventory.txt

The source writes Chinese as `\\uXXXX` escapes, which means a wrong-but-valid character (毅 U+6BC5 vs
毁 U+6BC1) is invisible when the file is read as bytes and invisible again in a terminal that renders it
as a glyph. This decodes every escape in the modules that draw text and lists it with its codepoints, so
the strings can be *read* - and the codepoints checked - in one pass.
"""
from __future__ import annotations

import ast
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"
OUT = Path(__file__).resolve().parent / "out" / "audit"
OUT.mkdir(parents=True, exist_ok=True)

MODULES = ["school_scenes.py", "school_courses.py", "school_motifs.py", "school_panels.py",
           "school_chat.py", "school_fx.py", "school_sculpture.py", "school_machine.py",
           "school_lines.py", "school_lines_act2.py"]

CJK = re.compile(r"[\u3400-\u9fff]")


def decode(node: ast.AST) -> str | None:
    try:
        v = ast.literal_eval(node)
    except Exception:
        return None
    return v if isinstance(v, str) else None


def main() -> None:
    lines: list[str] = []
    seen: dict[str, str] = {}
    for mod in MODULES:
        src = (TOOLS / mod).read_text(encoding="utf8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            s = node.value
            if not CJK.search(s) or len(s) > 200:
                continue
            first = s.splitlines()[0]
            key = f"{mod}:{node.lineno}"
            if key in seen:
                continue
            seen[key] = first
            cps = " ".join(f"{ch}=U+{ord(ch):04X}" for ch in first if CJK.match(ch))
            lines.append(f"{mod}:{node.lineno}\t{first}\t{cps}")
    lines.sort()
    (OUT / "text_inventory.txt").write_text("\n".join(lines) + "\n", encoding="utf8")
    print(f"{len(lines)} on-screen strings -> {OUT / 'text_inventory.txt'}")


if __name__ == "__main__":
    main()
