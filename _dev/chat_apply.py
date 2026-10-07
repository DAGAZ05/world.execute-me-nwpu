"""Batch 53: apply the user's hand-edited `05_歌词会话对照_v2.md` to `school_lines*.py`, literally.

    python _dev/_b53apply.py --dry      report every line that would change, change nothing
    python _dev/_b53apply.py            patch the two row files, then verify by re-reading them

The user's instruction is "严格按照现在的版本，修改对话，不允许擅自增删": the edited table is the
authority for the *text* of every dialogue row, and nothing may be added or dropped. So this is a
transcription, not a rewrite:

  * the block/role structure comes from the table, the times and tags stay as they are in the code;
  * the two are compared **row by row, in order** - a different number of lines in any block aborts the
    run instead of guessing;
  * only the text literal of a row is replaced (`ast` gives the node's exact span), so every comment in
    those files survives;
  * the patched modules are re-imported and the folded blocks are compared with the table's, so a
    mistranscription fails here rather than on screen.

The table's `meta` row joins the two halves of the window's right-aligned column with ` · `; the source
stores them as one string with a `|`, which is how `school_chat._blocks` splits them again.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")
sys.stdout.reconfigure(encoding="utf8", errors="replace")

DOC = ROOT / "05_\u6b4c\u8bcd\u4f1a\u8bdd\u5bf9\u7167_v2.md"
FILES = [ROOT / "player" / "_tools" / "school_lines.py",
         ROOT / "player" / "_tools" / "school_lines_act2.py"]
ZH2WHO = {"\u6211": "user", "\u5c0f\u5929": "ai", "\u526f\u884c": "sub", "\u4ee3\u7801": "code",
          "\u5361\u7247": "card", "\u7cfb\u7edf": "err", "\u5143\u4fe1\u606f": "meta"}


def cells(line: str) -> list[str]:
    """The table's cells, with **one** leading and trailing space removed - the delimiter padding only.

    `strip()` is wrong here and it took a dry run to see it: the `代码` rows carry their own leading
    spaces (the C-block's indentation inside the window), and stripping them would re-indent the film's
    code block. The table is transcribed, not tidied.
    """
    out = []
    for c in line.strip().strip("|").split("|"):
        out.append(c[1:-1] if len(c) >= 2 and c.startswith(" ") and c.endswith(" ") else c.strip())
    return out


def read_table() -> list[tuple[float, list[tuple[str, str]]]]:
    """[(time, [(who, text)])] in document order, from the user's edited table."""
    out: list[tuple[float, list[tuple[str, str]]]] = []
    for ln in DOC.read_text(encoding="utf8").splitlines():
        if not ln.startswith("|"):
            continue
        c = cells(ln)
        if len(c) >= 5 and c[3] == "\u53f3\u680f":                      # a block header
            t = float(c[1].split(":")[0]) * 60 + float(c[1].split(":")[1])
            out.append((t, []))
            continue
        if len(c) >= 5 and c[0] == "" and c[3] in ZH2WHO and out:
            text = c[4].replace("\\|", "|")
            if ZH2WHO[c[3]] == "meta" and "  \u00b7  " in text:
                text = "|".join(p.strip() for p in text.split("  \u00b7  ", 1))
            out[-1][1].append((ZH2WHO[c[3]], text))
    return out


def code_rows() -> list[tuple[pathlib.Path, int, int, str, str, str, str]]:
    """[(file, tuple index, text-node span start/end, t, tag, who, text)] for both row files."""
    rows = []
    for path in FILES:
        text = path.read_text(encoding="utf8")
        lines = text.splitlines(keepends=True)
        starts = []
        pos = 0
        for l in lines:
            starts.append(pos)
            pos += len(l)
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.AnnAssign):
                name, value = getattr(node.target, "id", ""), node.value
            elif isinstance(node, ast.Assign):
                name, value = getattr(node.targets[0], "id", ""), node.value
            else:
                continue
            if name not in ("ACT_ONE", "ACT_TWO") or value is None:
                continue
            for i, el in enumerate(value.elts):
                t, tag, who, txt = (ast.literal_eval(x) for x in el.elts)
                tn = el.elts[3]
                a = starts[tn.lineno - 1] + char_col(lines[tn.lineno - 1], tn.col_offset)
                b = starts[tn.end_lineno - 1] + char_col(lines[tn.end_lineno - 1], tn.end_col_offset)
                rows.append((path, i, a, b, t, tag, who, txt))
    return rows


def char_col(line: str, byte_col: int) -> int:
    """`ast` columns are UTF-8 byte offsets; these files carry Chinese in their comments."""
    if byte_col <= 0:
        return 0
    return len(line.encode("utf8")[:byte_col].decode("utf8", "replace"))


def literal(text: str, indent: str = "     ") -> str:
    """One string literal, escaped the way these files are written, wrapped like them if it is long.

    The wrapping splits the **text**, never the escaped string: cutting `\\u8304` in half turns one
    character into `\\u83` + `04`, which is a `SyntaxError` rather than a wrong glyph - and that is how
    the first run of this script found out.
    """
    def esc(s: str) -> str:
        return s.encode("unicode_escape").decode("ascii").replace('"', '\\"')

    if len(esc(text)) <= 76:
        return f'"{esc(text)}"'
    chunks: list[str] = []
    cur = ""
    for ch in text:
        cur += ch
        if len(esc(cur)) >= 56:
            chunks.append(cur)
            cur = ""
    if cur:
        chunks.append(cur)
    head, *rest = chunks
    return '"%s"' % esc(head) + "".join(f'\n{indent}"{esc(c)}"' for c in rest)


def main() -> None:
    dry = "--dry" in sys.argv
    table = read_table()
    rows = code_rows()
    # fold the code rows into blocks exactly the way `school_chat._blocks` does: consecutive rows with the
    # same `(time, lyric)` are one exchange, in order
    code_blocks: list[tuple[float, str, list[tuple[str, str]], list]] = []
    for r in rows:
        if code_blocks and code_blocks[-1][0] == r[4] and code_blocks[-1][1] == r[5]:
            code_blocks[-1][2].append((r[6], r[7]))
            code_blocks[-1][3].append(r)
        else:
            code_blocks.append((r[4], r[5], [(r[6], r[7])], [r]))
    print(f"table: {len(table)} blocks / {sum(len(b[1]) for b in table)} lines")
    print(f"code : {len(code_blocks)} blocks / "
          f"{sum(len(b[2]) for b in code_blocks)} lines")
    if len(table) != len(code_blocks):
        raise SystemExit("block count differs - not touching anything")
    edits = []
    for (tt, tlines), (ct, ctag, clines, crows) in zip(table, code_blocks):
        if abs(tt - ct) > 0.05:
            raise SystemExit(f"block time differs: table {tt} vs code {ct}")
        if len(tlines) != len(clines):
            raise SystemExit(f"block @{tt}: table has {len(tlines)} lines, code has {len(clines)}")
        for k, ((tw, tx), (cw, cx)) in enumerate(zip(tlines, clines)):
            if tw != cw:
                raise SystemExit(f"block @{tt} line {k}: role {tw!r} vs {cw!r}")
            if tx != cx:
                edits.append((crows[k], tx))
    print(f"rows to change: {len(edits)}")
    for (path, _i, _a, _b, t, _tag, who, old), new in edits:
        print(f"  {path.name} @{t:7.2f} {who:5s} {old[:34]!r}\n      -> {new[:60]!r}")
    if dry:
        return
    by_file: dict[pathlib.Path, list] = {}
    for (path, _i, a, b, t, tag, who, old), new in edits:
        by_file.setdefault(path, []).append((a, b, new))
    for path, items in by_file.items():
        text = path.read_text(encoding="utf8")
        for a, b, new in sorted(items, key=lambda x: -x[0]):
            text = text[:a] + literal(new) + text[b:]
        path.write_text(text, encoding="utf8")
        print(f"patched {path}")
    # ---- verify by re-reading the patched modules through the player's own folding
    for m in list(sys.modules):
        if m in ("school_lines", "school_lines_act2", "school_chat"):
            del sys.modules[m]
    import school_chat as CH
    got = CH._DIALOGUE

    def folded(block):
        """`_blocks` splits a `meta` row into its two cells; the table keeps them on one row."""
        out: list[tuple[str, str]] = []
        for role, text in block:
            if role == "meta" and out and out[-1][0] == "meta" and "|" not in out[-1][1]:
                out[-1] = ("meta", out[-1][1] + "|" + text)
            else:
                out.append((role, text))
        return out

    if len(got) != len(table):
        raise SystemExit(f"VERIFY FAILED: {len(got)} blocks vs {len(table)}")
    bad = 0
    for (tt, tlines), (ct, ctag, clines) in zip(table, got):
        if abs(tt - ct) > 0.05 or [(w, x) for w, x in tlines] != folded(clines):
            bad += 1
            print(f"  MISMATCH @{tt}: {tlines} vs {folded(clines)}")
    print("VERIFY:", "every row matches the table" if not bad else f"{bad} block(s) differ")
    raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
