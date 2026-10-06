"""The project's **global** timeline: one document, as detailed as the project can make it.

    python _dev/timeline_doc.py            rewrites `06_时序对照表.md` (and the TSV beside it)
    python _dev/timeline_doc.py --check    exit 1 if the file on disk is out of date

`06_时序对照表.md` is not a batch record: it is the standing answer to "what happens when", and every
batch has to keep it true. `check.cmd` runs `--check`, so a change to the schedule, the dialogue, a
panel's text or the overlay table fails the build until the document is regenerated.

Sections, in order:

  1. how to update it, and the counts it is built from
  2. 逐行日程 (78 rows): shot | lyric | dialogue | panel | ops | overlay | verdict
  3. 逐句歌词 (98 lines): which row each lyric line falls in, and what is on screen for it
  4. panel 清单 (65): the code's own claim, the text it really prints, the audit's verdict
  5. 整屏层 / 窗口层 / 转场 / 震屏
  6. 对话全文 (75 blocks / 365 lines) with the lyric and the pane each hangs on
  7. 变更历史: one line per batch, pointing at its record
  8. 已知未修与已接受的例外
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402
import school_chat as CH        # noqa: E402
import school_fx as FX          # noqa: E402
import school_scenes as SC      # noqa: E402
import panel_catalog as PC      # noqa: E402

DOC = ROOT / "06_\u65f6\u5e8f\u5bf9\u7167\u8868.md"
TSV = ROOT / "06_\u65f6\u5e8f\u5bf9\u7167\u8868.tsv"
OUT = ROOT / "_dev" / "out" / "audit"
ROLE_ZH = {"user": "\u6211", "ai": "\u822a\u5c0f\u5929", "sub": "\u526f\u884c",
           "code": "\u4ee3\u7801\u5757", "card": "\u5361\u7247", "meta": "\u5143\u4fe1\u606f"}

# one line per batch: what it changed, and where the record is. Kept here rather than derived, because
# "which batch did this" is history, not data - but it is part of the document, so it cannot rot.
HISTORY = [
    ("22", "\u822a\u5c0f\u5929\u6253\u7bee\u7403 + \u6f14\u51fa\u65f6\u957f", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2122_\u52a8\u56fe\u4e0e\u65f6\u957f.md"),
    ("23", "\u5f00\u5934\u753b\u9762\u4e0e\u97f3\u4e50\u540c\u6b65", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2123_\u542f\u52a8.md"),
    ("24", "\u5bf9\u8bdd\u8fde\u8d2f + \u7bee\u7403\u4e94\u6b21 + \u7528\u6237\u540d me", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2124_\u5bf9\u8bdd\u4e0eme.md"),
    ("25", "\u52a8\u56fe\u770b\u5f97\u89c1 + \u6821\u5fbd\u53bb\u7ebf + \u6821\u95e8\u653e\u5927", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2125_\u52a8\u56fe\u53ef\u89c1\u4e0e\u6821\u95e8\u653e\u5927.md"),
    ("26", "\u52a8\u56fe\u5c42\u7ea7 + MEMORY \u8282\u594f + \u767d\u6846", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2126_\u52a8\u56fe\u5c42\u7ea7\u4e0e\u8282\u594f.md"),
    ("27", "\u5b57\u7b26\u5bbd\u5ea6\u4fee\u6b63 + \u5b66\u9662\u6bb5\u6362\u8fb9 + \u5927\u5fc3\u5f62 + \u8fd0-20 \u8986\u76d6 2/3", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2127_\u5b57\u7b26\u4e0e\u89c6\u89c9.md"),
    ("28", "\u53bb\u91cd + \u4e13\u4e1a\u6bb5\u53ea\u7559\u4e13\u4e1a\u56fe\u6848 + \u6491\u767d\u6846", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2128_\u53bb\u91cd\u4e0e\u4e13\u4e1a.md"),
    ("29", "\u5168\u8eab\u56fe\u5f52\u4f4d + \u98de\u673a\u63d0\u4eae", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2129_\u63d0\u4eae\u4e0e\u5f52\u4f4d.md"),
    ("30", "\u5220\u6389\u9611\u8fdb\u753b\u9762\u7684\u732b + ops \u9ad8\u5ea6\u968f\u56fe\u9ad8", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2130_\u610f\u5916\u7684\u732b\u4e0eops\u9ad8\u5ea6.md"),
    ("31", "\u5168\u66f2\u65f6\u5e8f\u5bf9\u7167\u8868 + \u5185\u5bb9\u6838\u9a8c\uff08\u6293\u51fa\u4eea\u8868\u65e9 10 s\u3001\u540d\u5b9e\u4e0d\u7b26 12 \u5904\u3001\u6bcd\u9898\u91cd\u590d\uff09", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2131_\u65f6\u5e8f\u5bf9\u7167\u4e0e\u5185\u5bb9\u6838\u9a8c.md"),
    ("32", "\u4e0a\u6279\u672a\u6539\u9879\u6536\u5c3e + \u5934\u50cf 24\u00d712", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2132_\u672a\u6539\u9879\u6536\u5c3e\u4e0e\u5934\u50cf.md"),
    ("33", "\u4eba\u79f0\u4ee3\u8bcd\u6539\u4e3a\u7537\u6027\uff08figure/mascot\uff09+ \u65f6\u5e8f\u5bf9\u7167\u6539\u4e3a\u5168\u5c40\u6587\u6863", "04_\u9a8c\u8bc1\u8bb0\u5f55/\u6279\u6b2133_\u4eba\u79f0\u4e0e\u5168\u5c40\u65f6\u5e8f\u8868.md"),
]
# things deliberately left alone, so "not fixed" is a decision and not an oversight
ACCEPTED = [
    "\u6821\u5fbd\u56db\u6b21\u3001\u94f8\u5251\u96d5\u5851\u4e24\u6b21\u91cd\u590d\uff1a\u7528\u6237\u8c41\u514d\u3002",
    "\u4e13\u4e1a\u6bb5\u7684 ops \u662f\u7a0b\u5e8f\u6e05\u5355\uff08\u4e0d\u662f\u6eda\u6761\uff09\uff0c\u4ece 147.52 s \u5230\u7247\u5c3e\uff1b`ops=[...]` \u5728\u90a3\u4e4b\u540e\u8bfb\u4f5c\u6e05\u5355\u6807\u9898\u3002",
    "\u5267\u60c5\u4e0a\u65e0\u6cd5\u907f\u514d\u7684\u7a7a\u767d\uff1a58.65-70.08 \u7bee\u7403\u7a97\u53e3\u76d6\u4f4f\u4f1a\u8bdd\u7a97\uff08\u7ea6 11.4 s\uff09\u3002",
    "\u53d7\u6846\u5927\u5c0f\u9650\u5236\u7684\u7ed8\u5236\uff1astardiff \u661f\u8292\u3001powerdown \u5012\u8ba1\u65f6\u3001`pane_exec_ds` \u7684\u591a\u680f\u7248\u5f0f\uff08\u9608\u503c bw\u2265100\uff09\u3002",
    "boot log \u7684\u4e13\u4e1a\u5185\u5bb9\u51fa\u73b0\u5728 0.84-2.78 s\uff0c\u4e0e\u6279\u51c6\u7a3f\u201c02:10.74 \u524d\u7981\u4e13\u4e1a\u201d\u51b2\u7a81\uff1a\u90a3\u662f\u6279\u6b216 \u7684\u8bbe\u8ba1\u3002",
]


def build() -> str:
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    rows = SP.shot_rows()
    lines = T.Data().lines
    dial = CH._DIALOGUE
    claim = PC.claims()
    verdict = PC.verdicts()
    ev_all = list(FX.EVENTS)

    out: list[str] = []
    w = out.append
    w("# \u5168\u66f2\u65f6\u5e8f\u5bf9\u7167\u8868\uff08\u5168\u5c40\uff0c\u6bcf\u4e2a\u6279\u6b21\u90fd\u8981\u4fee\u6b63\uff09")
    w("")
    w("\u672c\u6587\u4ef6\u7531 `_dev/timeline_doc.py` **\u751f\u6210**\uff0c\u4e0d\u624b\u6539\uff1b"
      "\u6bcf\u4e2a\u6279\u6b21\u6539\u5b8c\u5fc5\u987b\u91cd\u8dd1\u4e00\u6b21\uff0c")
    w("`check.cmd` \u4f1a\u8dd1 `python _dev/timeline_doc.py --check`\uff0c"
      "\u6587\u4ef6\u8fc7\u671f\u76f4\u63a5\u5224\u5931\u8d25\u3002")
    w("")
    w(f"\u7edf\u8ba1\uff1a**{len(rows)}** \u884c\u65e5\u7a0b\uff08{rows[0]['at']:.2f}-{rows[-1]['end']:.2f} s\uff0c"
      f"\u65e0\u7a7a\u9699\uff09\u3001**{len(lines)}** \u884c\u6b4c\u8bcd\u3001**{len(dial)}** \u5757\u5bf9\u8bdd / "
      f"**{sum(len(b[2]) for b in dial)}** \u884c\u3001**{len(ev_all)}** \u4e2a\u6574\u5c4f\u4e8b\u4ef6\u3001"
      f"**{len(set(r['name'] for r in rows if r['name']))}** \u4e2a panel\u3002")
    w("")
    w("\u672c\u8868\u4e0d\u5217\uff1a`feature bands`\uff08chrome\uff09\u3001`progress`\uff08chrome\uff09\u3002")
    w("")
    w("\u5217\u7684\u610f\u601d\uff1a**\u65f6\u95f4** = \u65e5\u7a0b\u884c\u7684 `at`-`end`\uff1b**\u955c\u5934** = \u5f71\u7247\u81ea\u5df1\u7684"
      " 97 \u955c\u540d\uff1b**\u6b4c\u8bcd** = \u533a\u95f4\u5185\u7684\u5168\u90e8\u6b4c\u8bcd\u884c\uff1b**\u5bf9\u8bdd** = \u4f1a\u8bdd\u7a97\u91cc\u7684\u884c\uff1b")
    w("**panel** = \u53f3\u680f\uff08\u6216\u6362\u8fb9\u540e\u7684\u5de6\u680f\uff09\u753b\u7684 pane\uff1b"
      "**\u753b\u4ec0\u4e48** = \u4ee3\u7801\u81ea\u5df1\u7684\u8bf4\u6cd5\uff08docstring \u9996\u53e5\uff09\uff1b"
      "**ops** = \u6eda\u6761\u8bcd\uff08\u4e13\u4e1a\u6bb5\u662f\u6e05\u5355\u6807\u9898\uff09\uff1b**\u6574\u5c4f\u5c42** = \u56fe\u7247/\u98de\u673a/\u8f6c\u573a\u3002")
    w("")

    # 1. per row
    w("## 1 \u9010\u884c\u65e5\u7a0b")
    w("")
    w("| # | \u65f6\u95f4 | \u955c\u5934 | \u6b4c\u8bcd\uff08\u533a\u95f4\u5185\uff09 | \u5bf9\u8bdd | panel | \u753b\u4ec0\u4e48 | ops | \u6574\u5c4f\u5c42 | \u6838\u9a8c |")
    w("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    tsv = ["start\tend\tshot\tlyric\tpane\tops\tdialogue\toverlay\tverdict"]
    for i, r in enumerate(rows, 1):
        at, end = r["at"], r["end"]
        ent = SP.school_entry(end - 1e-3, None) or {}
        shot = ent.get("name") or "(none)"
        lyr = " / ".join(ln["text"] for ln in lines if at - 1e-6 <= ln["start"] < end - 1e-6)
        d = [b for b in dial if at - 1e-6 <= b[0] < end - 1e-6]
        ev = [e for e in ev_all if e[0] < end - 1e-6 and e[1] > at + 1e-6]
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")          # noqa: E731
        talk = "<br>".join(f"{ROLE_ZH.get(role, role)}\uff1a{txt}" for b in d for role, txt in b[2])
        layer = "<br>".join(f"{s:.2f}-{e:.2f} `{fn.__name__}` {fx_brief(kw)}" for s, e, fn, kw in ev)
        name = r["name"] or "(\u5f71\u7247\u81ea\u5df1)"
        what = PC.claim_for(r["name"], claim) if r["name"] else ""
        w("| {} | {:.2f}-{:.2f} | {} | {} | {} | `{}` | {} | {} | {} | {} |".format(
            i, at, end, shot, cell(lyr) or "\u2014", cell(talk) or "\u2014", name,
            cell(what) or "\u2014", cell("/".join(map(str, r["ops"]))), cell(layer) or "\u2014",
            cell(verdict.get(r["name"], "")) or "\u2014"))
        tsv.append("\t".join([f"{at:.2f}", f"{end:.2f}", shot, lyr.replace("\t", " "), name,
                              "/".join(map(str, r["ops"])), talk.replace("\t", " "),
                              layer, verdict.get(r["name"], "")]))
    w("")

    # 2. per lyric line
    w("## 2 \u9010\u53e5\u6b4c\u8bcd\uff08\u6bcf\u4e00\u53e5\u843d\u5728\u54ea\u4e00\u884c\uff09")
    w("")
    w("| \u65f6\u95f4 | \u6b4c\u8bcd | \u54ea\u4e00\u884c\u7684 panel | ops | \u8fd9\u4e00\u53e5\u7684\u5bf9\u8bdd |")
    w("| --- | --- | --- | --- | --- |")
    for ln in lines:
        r = next((x for x in rows if x["at"] - 1e-6 <= ln["start"] < x["end"] - 1e-6), None)
        d = [b for b in dial if abs(b[0] - ln["start"]) < 0.6]
        cell = lambda s: str(s).replace("|", "\\|")                               # noqa: E731
        talk = "<br>".join(f"{ROLE_ZH.get(role, role)}\uff1a{txt}" for b in d for role, txt in b[2])
        w(f"| {ln['start']:.2f} | {cell(ln['text'])} | `{(r['name'] if r and r['name'] else '(\u5f71\u7247)')}` | "
          f"{cell('/'.join(map(str, r['ops']))) if r else '\u2014'} | {cell(talk) or '\u2014'} |")
    w("")

    # 3. panel catalogue
    w("## 3 panel \u6e05\u5355\uff08\u4ee3\u7801\u81ea\u5df1\u7684\u8bf4\u6cd5 / \u5c4f\u4e0a\u771f\u5199\u4e86\u4ec0\u4e48 / \u6838\u9a8c\uff09")
    w("")
    times: dict[str, list[str]] = {}
    for r in rows:
        if r["name"]:
            times.setdefault(r["name"], []).append(f"{r['at']:.2f}")
    w("| panel | \u51fa\u73b0\uff08\u79d2\uff09 | \u4ee3\u7801\u81ea\u5df1\u7684\u8bf4\u6cd5 | \u5c4f\u4e0a\u6587\u5b57\uff08\u6e32\u67d3\u8bfb\u56de\uff09 | \u6838\u9a8c |")
    w("| --- | --- | --- | --- | --- |")
    for pane in sorted(times):
        c = PC.claim_for(pane, claim)
        txt = PC.text_of(pane, float(times[pane][0]) + 0.35)
        cell = lambda s: str(s).replace("|", "\\|")                               # noqa: E731
        w(f"| `{pane}` | {'\u3001'.join(times[pane])} | {cell(c)[:220] or '\u2014'} | "
          f"{cell(txt)[:320] or '\u2014'} | {cell(verdict.get(pane, '')) or '\u2014'} |")
    w("")

    # 4. the overlay layer
    w("## 4 \u6574\u5c4f\u5c42 / \u7a97\u53e3\u5c42 / \u8f6c\u573a / \u9707\u5c4f")
    w("")
    w("| \u65f6\u95f4 | \u5c42 | \u51fd\u6570 | \u53c2\u6570 |")
    w("| --- | --- | --- | --- |")
    for s_, e_, fn, kw in ev_all:
        w(f"| {s_:.2f}-{e_:.2f} | \u6574\u5c4f | `{fn.__name__}` | {fx_brief(kw).replace('|', chr(92) + '|')} |")
    for s_, e_, fn, kw in FX.WINDOW_EVENTS:
        w(f"| {s_:.2f}-{e_:.2f} | \u7a97\u53e3 | `{fn.__name__}` | {fx_brief(kw)} |")
    for s_, e_, amt in FX.SHOCKS:
        w(f"| {s_:.2f}-{e_:.2f} | \u9707\u5c4f | \u5e45\u5ea6 {amt} | \u2014 |")
    w("")

    # 5. the whole dialogue
    w("## 5 \u5bf9\u8bdd\u5168\u6587\uff08\u6309\u65f6\u95f4\uff0c"
      "\u6bcf\u5757\u6807\u51fa\u5b83\u6302\u5728\u54ea\u53e5\u6b4c\u8bcd\u4e0a\u3001\u5f53\u65f6\u54ea\u5f20 panel\uff09")
    w("")
    w("| \u65f6\u95f4 | \u6302\u5728 | panel | \u884c |")
    w("| --- | --- | --- | --- |")
    for t_, lyric, lines_ in dial:
        r = next((x for x in rows if x["at"] - 1e-6 <= t_ < x["end"] - 1e-6), None)
        pane = (r["name"] if r and r["name"] else "(\u5f71\u7247\u81ea\u5df1)")
        body = "<br>".join(f"{ROLE_ZH.get(role, role)}\uff1a{txt}" for role, txt in lines_)
        w(f"| {t_:.2f} | {lyric.replace('|', chr(92) + '|')} | `{pane}` | {body.replace('|', chr(92) + '|')} |")
    w("")

    # 6. history and the accepted list
    w("## 6 \u53d8\u66f4\u5386\u53f2\uff08\u6bcf\u4e2a\u6279\u6b21\u4e00\u884c\uff09")
    w("")
    w("| \u6279\u6b21 | \u6539\u4e86\u4ec0\u4e48 | \u8bb0\u5f55 |")
    w("| --- | --- | --- |")
    for b, what, path in HISTORY:
        w(f"| {b} | {what} | `{path}` |")
    w("")
    w("## 7 \u5df2\u63a5\u53d7\u7684\u4f8b\u5916\uff08\u4e0d\u662f\u6f0f\u6389\uff0c\u662f\u51b3\u5b9a\uff09")
    w("")
    for a in ACCEPTED:
        w(f"- {a}")
    w("")
    return "\n".join(out) + "\n"


def fx_brief(kw: dict) -> str:
    keep = ("name", "caption", "cols_n", "rows_n", "fill", "zoom", "peak", "side", "dim", "x", "y")
    return " ".join(f"{k}={v!r}" for k, v in kw.items() if k in keep)


def main() -> None:
    text = build()
    if "--check" in sys.argv:
        old = DOC.read_text(encoding="utf8") if DOC.exists() else ""
        if old != text:
            print(f"06_\u65f6\u5e8f\u5bf9\u7167\u8868.md is out of date "
                  f"({len(old)} -> {len(text)} chars, sha {hashlib.sha256(old.encode()).hexdigest()[:8]} -> "
                  f"{hashlib.sha256(text.encode()).hexdigest()[:8]}); run:\n"
                  f"    python _dev/timeline_doc.py")
            raise SystemExit(1)
        print("06_\u65f6\u5e8f\u5bf9\u7167\u8868.md is up to date")
        return
    DOC.write_text(text, encoding="utf8")
    # the machine-readable half of section 1
    rows = SP.shot_rows()
    lines = T.Data().lines
    dial = CH._DIALOGUE
    tsv = ["start\tend\tpane\tops\tlyric\tdialogue"]
    for r in rows:
        at, end = r["at"], r["end"]
        tsv.append("\t".join([
            f"{at:.2f}", f"{end:.2f}", r["name"] or "", "/".join(map(str, r["ops"])),
            " / ".join(ln["text"] for ln in lines if at - 1e-6 <= ln["start"] < end - 1e-6),
            " || ".join(f"{ROLE_ZH.get(role, role)}:{txt}" for b in dial if at - 1e-6 <= b[0] < end - 1e-6
                        for role, txt in b[2])]))
    TSV.write_text("\n".join(tsv) + "\n", encoding="utf8")
    print(f"{DOC}  ({len(text.splitlines())} lines)")
    print(f"{TSV}")


if __name__ == "__main__":
    main()
