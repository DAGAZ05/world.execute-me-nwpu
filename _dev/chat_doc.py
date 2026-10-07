"""Generate `05_歌词会话对照_v2.md`: the whole conversation, one row per line of it.

    python _dev/chat_doc.py            rewrites the document
    python _dev/chat_doc.py --check    exit 1 if the file on disk is out of date

**Why it is generated rather than written.** The document is the surface the user edits ("我系统地改"),
and it was hand-maintained until batch 52 - at which point the user reported that *some of 航小天's
answers are not in it*. They were right, twice over: the code's dialogue had grown to 76 blocks / 371
lines (sub-lines, code blocks, error lines came later), and the table still had the first draft's first
three exchanges, which by then existed only in a dead `DIALOGUE` list inside `school_chat.py`. A table
whose completeness depends on somebody remembering to copy 371 lines is not a table.

So the rows are read out of the modules the player reads:

  * **dialogue** - `school_chat._DIALOGUE` (`school_lines.ACT_ONE` + `school_lines_act2.ACT_TWO`);
  * **lyrics** - `tui_live.Data().lines`, the film's own word-timed lines (what is typed on screen);
  * **panel + ops** - `school_panels.shot_rows()`, and what the pane draws from `panel_catalog`;
  * **why a lyric line has no exchange** - `school_chat.why_no_exchange`, which is the same five rules
    `check_coverage` gates on, printed instead of granted.

`check.cmd` runs `--check`, so a change to a line of dialogue fails the build until this is re-run.

Editing workflow: the user edits `05_歌词会话对照_v2 - 副本.md` (the copy), says what changed, and I apply
it to `school_lines*.py` and regenerate this file. Editing *this* file by hand is also fine - it is how a
change gets *requested* - but it makes `--check` red until the change lands in the code, which is the
point: a red check means "this sentence is in the table and not in the film yet".
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
import panel_catalog as PC      # noqa: E402

DOC = ROOT / "05_\u6b4c\u8bcd\u4f1a\u8bdd\u5bf9\u7167_v2.md"

ROLE_ZH = {"user": "\u6211", "ai": "\u5c0f\u5929", "sub": "\u526f\u884c", "code": "\u4ee3\u7801",
           "card": "\u5361\u7247", "err": "\u7cfb\u7edf", "meta": "\u5143\u4fe1\u606f"}

# The act structure, as sections of the table. A block belongs to the last section that starts at or
# before it. The titles are the design's own (they are what the old hand-written table used); the notes
# are one line of "what this stretch is", and they are checked by nothing - they are the prose half.
SECTIONS: list[tuple[float, str, str]] = [
    (0.00, "P0 \u5f00\u673a \u00b7 00:00.03 \u2013 00:12.47",
     "\u53f3\u680f\u8d2f\u7a7f\uff1a\u6821\u95e8\u4e0a\u7535\uff0c\u7535\u6d41\u6cbf\u6821\u95e8\u8f6e\u5ed3\u8d70\u3002"
     "\u5f00\u673a\u81ea\u68c0\u65e5\u5fd7\u5728\u5de6\u7a97\u4e0b\u65b9\u3002"),
    (12.47, "\u3010\u5668\u4e50\u7a7a\u9699\u3011\u6821\u56ed \u00b7 00:12.47 \u2013 00:29.28",
     "\u8fd9\u4e00\u6bb5\u4e0d\u7ed9\u8bfe\u8868\uff08v1 \u7684\u9519\uff09\uff1a\u53f3\u680f\u662f\u4f55\u5c0a\u4e0e"
     "\u6821\u5fbd\u4ea4\u66ff\uff0c\u5de6\u7a97\u822a\u5c0f\u5929\u81ea\u8ff0\u6821\u56ed\u7684\u4e09\u4e2a"
     "\u5730\u65b9\u3002"),
    (29.28, "P1 \u5b9a\u4e49 \u2014\u2014 \u6821\u56ed\u51e0\u4f55 \u00b7 00:29.28 \u2013 00:44.04",
     "\u8fd9\u4e00\u6bb5\u662f\u51e0\u4f55\uff0c\u4e0d\u662f\u4e13\u4e1a\u8bfe\uff1a\u70b9\u96c6\u3001\u7ef4\u5ea6\u3001"
     "\u542f\u7fd4\u6e56\u3001\u6b63\u5f26\u3001\u6781\u9650\u3002"),
    (44.04, "P2 \u7535\u4e0e\u65f6\u95f4 \u2014\u2014 \u6821\u53f2 \u00b7 00:44.04 \u2013 00:58.65",
     "\u6821\u53f2\u5728\u8fd9\u4e00\u6bb5\uff0c\u5168\u90e8\u5e26\u56fe\uff1a\u6362\u5411\u3001\u8fc1\u6821\u3001"
     "\u56db\u6821\u5408\u5e76\u3002"),
    (58.65, "P3 \u526f\u6b4c\u4e00 \u2014\u2014 \u6821\u56ed\u751f\u6d3b \u00b7 00:58.65 \u2013 01:13.53",
     "**\u7bee\u7403\u52a8\u56fe\u76d6\u4f4f\u4f1a\u8bdd\u7a97 58.65\u201370.08**\uff1a\u8fd9\u4e00\u6bb5"
     "\u56db\u6761\u6b4c\u8bcd\u7531\u753b\u9762\u627f\u62c5\uff08\u89c1 \u00a76\uff09\u3002"),
    (73.53, "P4 \u4e07\u7269\u7686\u70b9 \u2014\u2014 \u6821\u56ed\u7269\u4e0e\u603b\u5e08\u6587\u5316 \u00b7 "
            "01:13.53 \u2013 01:28.34",
     "\u8304\u5b50\u3001\u756a\u8304\u3001\u732b\u5b66\u957f\uff0c\u7136\u540e\u5728 `If I'm the only God` "
     "\u4e0a\u6536\u5230\u4e94\u4e2a\u300c\u7b2c\u4e00\u300d\u4e0e\u603b\u5e08\u6447\u7bee\u3002"),
    (88.34, "P5 \u4e92\u6362 \u00b7 01:28.34 \u2013 01:43.03",
     "\u6539\u540d\u3001\u6362\u7cfb\u3001\u6362\u89d2\u8272\uff0c\u90fd\u662f\u8fd9\u6240\u5b66\u6821\u81ea\u5df1"
     "\u505a\u8fc7\u7684\u4e8b\uff1b`To S, to M` \u57cb\u7684\u662f\u95e8\u90a3\u4e00\u4e2a\u5b57\u6bcd\u3002"),
    (103.03, "P6 \u526f\u6b4c\u4e8c \u2014\u2014 \u4f60\u8d70\u4e86 \u00b7 01:43.03 \u2013 02:05.33",
     "\u5168\u66f2\u60c5\u7eea\u6700\u4f4e\u70b9\u3002`You have left` \u4e94\u8fde\u5531\u5904\uff0c"
     "\u5de6\u7a97\u53ea\u6709\u7cfb\u7edf\u7684 `err:` \u884c\uff0c\u5bf9\u8bdd\u7f3a\u5e2d\u662f\u523b\u610f\u7684"
     "\uff08\u89c1 \u00a76\uff09\u3002"),
    (125.33, "P7a \u63a7\u8bc9 \u00b7 02:05.33 \u2013 02:10.74",
     "\u4e3a\u56fd\u94f8\u5251\u51fa\u73b0\uff0c\u7136\u540e\u662f\u771f\u5b9e\u62a5\u9519\u4e0e\u8c03\u7528\u6808\u3002"),
    (131.90, "\u8f6c\u8f74 \u00b7 \u5b66\u9662\u9009\u62e9\u95e8 \u00b7 02:10.74 \u2013 02:12.6",
     "\u5168\u5c4f\u6295\u7968\u9762\u677f\uff08`school_gate.overlay`\uff09\u3002\u8fd9\u4e00\u6bb5"
     "\u5de6\u7a97\u53ea\u6709\u4e24\u53e5\u57ab\u8bdd\uff0c\u95ee\u9898\u7531\u9762\u677f\u81ea\u5df1\u95ee\u3002"),
    (134.50, "\u7b2c\u4e8c\u5e55 \u00b7 \u8fdb\u4e13\u4e1a \u00b7 02:14 \u2013 02:27.52",
     "\u5927\u4e00\u3001\u6570\u636e\u7ed3\u6784\uff1a\u8bfe\u7a0b\u540d\u5728\u53f3\u680f\u7684\u8bfe\u8868\u91cc"
     "\uff0c\u5bf9\u8bdd\u53ea\u8bf4\u8fd9\u4e00\u5e74\u662f\u4ec0\u4e48\u6837\u5b50\uff08\u4e0d\u62a5\u6570\u91cf\uff09\u3002"),
    (147.52, "P7b \u5904\u51b3 \u2014\u2014 \u5341\u4e8c\u6b21 `Execution` \u4e0e\u516d\u4e2a\u5012\u6570 \u00b7 "
             "02:27.52 \u2013 02:42.23",
     "\u5341\u4e09\u6b21 `Execution` \u91cc\u53ea\u6709\u5f00\u5934\u4e00\u53e5\u5bf9\u8bdd\uff0c"
     "\u5176\u4f59\u7531\u53f3\u680f\u7684\u8bfe\u56fe\u4e00\u5f20\u5f20\u627f\u62c5\uff08\u89c1 \u00a76\uff09\u3002"),
    (162.23, "P7c \u526f\u6b4c\u4e09 \u2014\u2014 \u4ee3\u4ef7 \u00b7 02:42.23 \u2013 02:56.96",
     "\u4e00\u6574\u5957\u56fe\u6536\u6210\u4e00\u5f20\u7c7b\u56fe\uff1bAI \u6bcd\u9898\u5728"
     "`I will run the execution` \u4e0a\u653e\u7740\uff0c\u5de6\u7a97\u4e0d\u63d2\u8bdd\u3002"),
    (176.96, "P8 LOVE \u00b7 02:56.96 \u2013 03:13.46",
     "\u4e09\u5e74\u77e5\u8bc6\u7ebf\u3001\u4f9d\u8d56\u5012\u7f6e\u3001`class Love`\u3002"),
    (193.46, "\u3010\u5c3e\u58f0\u3011\u5bf9\u8bdd\u96d5\u5851\u4e0e\u6821\u5fbd \u00b7 03:13.46 \u2013 03:25.56",
     "\u6700\u540e\u4e00\u6bb5\u5bf9\u8bdd\u5728\u8fd9\u91cc\u4e00\u6b21\u51fa\u5b8c\uff08\u4e94\u884c\uff09\uff0c"
     "\u7136\u540e\u662f\u6821\u5fbd\u3002"),
    (205.56, "\u6700\u540e\u4e00\u58f0 `Execution` \u00b7 03:25.56 \u2013",
     "\u4e00\u53e5\u8bdd\uff0c\u7136\u540e\u5b89\u9759\u5230\u5e95\u3002"),
]

# the aircraft table, from the events themselves (`school_fx.EVENTS`); the columns are the four names,
# where each one is, and what the event is called.
PLANES = [
    ("\u8fd0-20", "y20", "\u4f4e\u7a7a\u63a0\u8fc7\uff0c\u6a2a\u8d2f\u5168\u5c4f\uff08`lowpass`\uff0c"
                        "\u53e6\u6709\u6574\u5c4f\u9707\u52a8\uff09"),
    ("ARJ21", "arj21", "\u8fdc\u5904\u5c0f\u56fe\uff0c\u6a2a\u5411\u6f02\u79fb\uff08`fly`\uff09"),
    ("\u76f4-20", "z20", "\u4ece\u4e0a\u5230\u4e0b\u964d\u843d\uff08`dive`\uff09"),
    ("\u6b7c-20", "j20", "\u659c\u5411\u722c\u5347\uff08`fly`\uff0cdy=-0.45\uff09"),
    ("\u9b54\u9b3c\u9c7c", "manta", "\u5728\u5b57\u7b26\u573a\u91cc\u6e38\u8fc7\uff0c\u5e26\u767d\u8272\u6d6a\u82b1"
                                  "\uff08`fly`\uff0cambient\uff09"),
]

DECISIONS = [
    ("1", "\u7b2c\u4e00\u5e55\u5bc6\u5ea6\uff08\u7ea6 25 \u4e2a\u753b\u9762\uff09", "\u4e0d\u780d\u3002"
     "\u7ea6\u675f\u6539\u6210\u4e0b\u9650\uff1a\u4efb\u4f55 pane \u4e0d\u5f97\u77ed\u4e8e 1.2 s\uff0c"
     "\u4e14\u6bcf\u53e5\u8bdd\u90fd\u5fc5\u987b\u6709\u56fe\u3002", "`span_probe`"),
    ("2", "`To S, to M` \u57cb\u7684 `s`", "\u753b\u9762\u4e0d\u95ea `s`\uff0c\u63d0\u793a\u653e\u5728\u53f0\u8bcd"
     "\u91cc\uff1b\u771f\u6b63\u8981\u663e\u773c\u7684\u662f\u95e8\u672c\u8eab\u3002", "`school_gate.overlay`"),
    ("3", "\u5bf9\u8bdd\u96d5\u5851\u653e\u54ea", "\u4e24\u5904\uff1a54.74 \u7684\u53f3\u680f pane"
     "\uff08\u5c0f\uff09\u4e0e 184.40 \u7684\u5168\u5c4f\u7834\u6846\uff08\u5927\uff0c\u5168\u7247\u53ea\u7834"
     "\u8fd9\u4e00\u6b21\uff09\u3002", "`pane_landmark_dialogue` + `EVENTS`"),
    ("4", "`\u673a\u64cd`", "\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf\uff08\u6807\u9898\u5c31\u5199"
     "\u300c\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf \u00b7 OpenEuler\u300d\uff09\u3002", "`pane_exec_os`"),
    ("5", "\u8981\u4e0d\u8981 CSV", "\u4e0d\u7528\u3002\u8fd9\u4efd Markdown \u5c31\u662f\u53ef\u9010\u884c\u6539\u7684"
     "\u8868\uff0c\u6539\u5b8c\u6211\u843d\u5230 `school_lines*.py`\u3002", "\u672c\u6587\u4ef6"),
    ("6", "`class Love` \u5168\u7247\u552f\u4e00\u5141\u8bb8\u9759\u6b62\uff0c\u800c `clock_probe` \u8981\u6c42"
          "\u6bcf\u5f20\u56fe\u90fd\u52a8", "\u4fdd\u63a2\u9488\u3002\u5fc3\u5f62\u7ee7\u7eed\u5fc3\u8df3\uff0c"
     "\u300c\u5141\u8bb8\u9759\u6b62\u300d\u8ba9\u4f4d\u4e8e\u673a\u5668\u4fdd\u8bc1\u3002", "\u4e0d\u6539\u4ee3\u7801"),
    ("7", "\u4e94\u8fde\u5531\u5904\u5bf9\u8bdd\u7f3a\u5e2d 8.55 s", "\u4fdd\u6301\u7559\u767d\u3002"
     "\u5de6\u7a97\u53ea\u6709 `err:`\uff0c\u90a3\u662f\u523b\u610f\u7684\u6c89\u9ed8\u3002", "\u4e0d\u6539\u4ee3\u7801"),
    ("8", "\u7bee\u7403\u7a97\u53e3 58.65\u201370.08 \u76d6\u4f4f\u4f1a\u8bdd\u7a97", "\u4e0d\u52a8\u3002"
     "\u88ab\u76d6\u4f4f\u7684\u56db\u6761\u6b4c\u8bcd\u5728\u672c\u8868\u91cc\u5c31\u5199\u7740"
     "\u300c\u753b\u9762\u76d6\u4f4f\u300d\u3002", "`school_chat.why_no_exchange` \u7b2c 3 \u6761"),
    ("9", "\u5bf9\u8bdd\u96d5\u5851\u7b2c\u4e09\u6bb5\u5f52\u5c5e", "\u6309 `02b \u00a73.3`\uff1a"
     "`unite` / `deeply` \u7559\u5728 54.74\uff0c\u7b2c\u4e09\u6bb5\u72ec\u7acb\u6210\u884c\u653e 84.60\uff0c"
     "`stardiff` \u987a\u5ef6\u5230 86.21\u3002", "\u5df2\u6539\u4ee3\u7801"),
    ("10", "`dijkstra` \u6ca1\u6709\u65e5\u7a0b\u884c\u7528\u5b83", "\u52a0\u8fdb\u5b66\u9662\u90e8\u5206\uff1a"
     "\u4ece `pane_curriculum` \u91cc\u5207\u51fa 142.00\u2013147.52\u3002", "`pane_motif_dijkstra`"),
    ("11", "\u90a3\u4e00\u884c\u753b\u7684\u662f\u88c2\u7eb9", "\u753b\u7b97\u6cd5\u672c\u8eab\uff08\u7528\u6237\uff1a"
     "\u300c\u6211\u8981\u6c42\u7684 dijkstra \u662f dijkstra \u7b97\u6cd5\uff0c\u4e0d\u662f\u88c2\u7eb9\u300d\uff09"
     "\u3002", "`school_motifs.dijkstra_route`"),
    ("12", "\u7ae0\u8282\u6761\u4e0a\u7684\u7ae0\u53f7", "\u53ea\u6539\u4e2d\u592e\u56fe\u5f62"
     "\uff08`SW`\uff09\uff0c\u7ae0\u8282\u6761**\u4e0d**\u52a8\u3002", "`school_machine.STAMP`"),
    ("13", "\u5706\u76d8\uff08\u8d1d\u585e\u5c14\uff09\u5728\u6536\u5c3e\u6bb5", "\u632a\u5230\u5b66\u9662\u6bb5"
     "\u4e4b\u524d\uff0c\u4ece `pane_memory(layers=1)` \u90a3\u4e00\u884c\u91cc\u622a\uff08\u5c42\u6570"
     "\u9012\u8fdb\u5b8c\u6574\u4fdd\u7559\uff09\u3002", "`pane_motif_bessel` @117.95"),
    ("14", "\u6536\u5c3e\u6bb5\u539f\u6765\u662f\u5706\u76d8", "\u6362\u6210\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406"
     "\uff08\u654f\u6377\u5ba3\u8a00 + \u51b2\u523a + \u4efb\u52a1\u770b\u677f\uff09\u3002", "`pane_sw_project`"),
    ("15", "\u5341\u516d\u6b21 `Execution` \u91cc\u7684\u300c\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406\u300d",
     "\u6539\u4e0a\u300c\u4fe1\u53f7\u4e0e\u7ebf\u6027\u7cfb\u7edf\u300d\uff08\u53d8\u6362\u5bf9 + "
     "`u(t)`/`\u03b4(t)`\uff09\uff0c\u8bfe\u8868\u91cc\u52a0 \u2605\u3002", "`c_pm`"),
    ("16", "\u56db\u5341\u516b\u5c0f\u65f6\u4ee5\u540e\u7684\u53d9\u4e8b\u53e3\u5f84", "\u8bfe\u7a0b\u6570"
     "\u4e0d\u5728\u5bf9\u8bdd\u91cc\u62a5\uff08\u7528\u6237\uff1a\u300c\u5404\u5e74\u4e0d\u6b62\u90a3\u51e0\u95e8"
     "\u8bfe\u7a0b\uff0c\u4e0d\u8981\u5728\u5bf9\u8bdd\u4e2d\u6709\u76f8\u5173\u65ad\u8a00\u300d\uff09\u3002",
     "\u5df2\u6539\u4ee3\u7801"),
]


def panes_at(t: float) -> tuple[str, str, str]:
    """(pane name, what it draws, ops) for the schedule row covering `t`."""
    rows = _ROWS[0]
    r = next((x for x in rows if x["at"] - 1e-6 <= t < x["end"] - 1e-6), None)
    if r is None:
        return "", "", ""
    name = r["name"] or ""
    what = PC.claim_for(name, _CLAIM[0]) if name else ""
    return name, what, "/".join(map(str, r["ops"]))


_ROWS: list = []
_CLAIM: list = []


def pane_label(pane: str, t: float) -> str:
    """The pane's own Chinese title, read back from a render - what the viewer sees, not the claim.

    `panel_catalog.claim_for` gives the code's *claim* (the drawing function's docstring, English); the
    pane also prints a title and a section line, and those are Chinese and are what is on screen. This
    reads them back out of the buffer and keeps the readable ones: a line is kept if, once its box
    drawing is stripped, half of what is left is a word character - which drops the rules (`── 敏捷 ·
    冲刺 · 看板 ─────`), the character art (a crest pane's first "text" line is 300 cells of `▀`) and the
    numeric readouts, and keeps `傅里叶本轮 · 心形的分解`.
    """
    key = (pane, round(t, 2))
    if key in _LABEL:
        return _LABEL[key]
    raw = PC.text_of(pane, t + 0.35)
    keep: list[str] = []
    for ln in raw.split(" \uff0f "):
        ln = ln.strip()
        if ln.count("\u2500") + ln.count("\u2502") > 2:
            ln = ln.strip("\u258f\u2502\u2500\u250c\u2510\u2514\u2518 ")
        else:
            ln = ln.lstrip("\u258f\u2502 ").rstrip()
        ln = " ".join(ln.split())
        if not ln or ln in keep:
            continue
        body = "".join(ch for ch in ln if ch not in "\u2500\u2502\u250c\u2510\u2514\u2518\u2588\u2580\u2584")
        good = sum(1 for ch in body if ch.isalnum() or "\u4e00" <= ch <= "\u9fff")
        if good < 2 or good / max(1, len(body)) < 0.5:
            continue
        keep.append(body[:44])
        if len(keep) == 2:
            break
    out = " \u00b7 ".join(keep)
    _LABEL[key] = out
    return out


_LABEL: dict[tuple[str, float], str] = {}

# Panes whose subject is character art or a photograph: they print no readable title, so the render has
# nothing to offer and the cell would fall back to the drawing function's English docstring. These are the
# design's own Chinese names (`02b_图像对位与可视化表达.md` §1/§3), written down here because a pane's
# *name* is not what is on screen.
PANE_ZH = {
    "pane_three_arms": "\u4e09\u65cb\u81c2\uff1a\u822a\u7a7a / \u822a\u5929 / \u822a\u6d77",
    "pane_landmark_dialogue": "\u5bf9\u8bdd\u96d5\u5851\uff1a\u673a\u5668\u624b\u4e0e\u4eba\u7684\u624b\u5c06\u89e6\u672a\u89e6",
    "pane_landmark_sword": "\u4e3a\u56fd\u94f8\u5251\u96d5\u5851\uff1a\u4e3e\u5251\u7684\u4e0d\u662f\u795e",
    "pane_landmark_cat": "\u732b\u5b66\u957f\uff1a\u53e0\u52a0\u6001",
    "pane_landmark_crest": "\u897f\u5317\u5de5\u4e1a\u5927\u5b66\u6821\u5fbd",
    "pane_landmark_hezun": "\u4f55\u5c0a\uff1a\u5b85\u5179\u4e2d\u56fd",
    "pane_sw_project": "\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406\uff1a\u654f\u6377\u5ba3\u8a00\u3001\u51b2\u523a\u3001\u770b\u677f",
    "pane_ai_cnn": "\u5377\u79ef\u795e\u7ecf\u7f51\u7edc\uff1a\u7279\u5f81\u56fe",
    "pane_ai_attention": "\u6ce8\u610f\u529b\uff1aQ\u00b7K\u1d40 \u7684\u70ed\u529b\u56fe",
    "pane_ai_rl": "\u5f3a\u5316\u5b66\u4e60\uff1a\u5956\u52b1\u66f2\u7ebf",
    "pane_ai_diffusion": "\u6269\u6563\u6a21\u578b\uff1a\u53bb\u566a\u8fc7\u7a0b",
    "pane_love_class": "\u7231\u7684\u4ee3\u6570\u8868\u8fbe\u5f0f\uff1a`class Love`",
}


def panel_cell(t: float) -> str:
    name, what, ops = panes_at(t)
    if not name:
        return "\u5f71\u7247\u81ea\u5df1\u7684\u753b\u9762\uff08\u8fd9\u4e00\u884c\u6ca1\u6709\u53f3\u680f pane\uff09"
    bits = [f"`{name}`"]
    label = pane_label(name, t) or PANE_ZH.get(name, "")
    if label:
        bits.append(f"\u300c{label}\u300d")
    elif what:
        bits.append(what.replace("|", "\\|")[:110])
    if ops:
        bits.append(f"ops\uff1a{ops}")
    return " \u2014\u2014 ".join(bits)


def film_line_near(t: float, tag: str) -> tuple[float, str] | None:
    """The film's own lyric line a block hangs on: same text and time, else the nearest within 2 s.

    A `[gap]` block (an instrumental stretch) hangs on no lyric line at all, and must not borrow the
    nearest one: the first version made the 14.00 s gap report itself as `And let's begin the simulation`,
    which is 1.5 s earlier and a completely different line.
    """
    if tag.startswith("[gap]"):
        return None
    lines = _LINES[0]
    exact = next((l for l in lines if l["text"] == tag and abs(l["start"] - t) <= 0.6), None)
    if exact is not None:
        return exact["start"], exact["text"]
    near = min(lines, key=lambda l: abs(l["start"] - t)) if lines else None
    if near is not None and abs(near["start"] - t) <= 2.0:
        return near["start"], near["text"]
    return None


def build() -> str:
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    _ROWS.append(SP.shot_rows())
    _CLAIM.append(PC.claims())
    lines = T.Data().lines
    _LINES.append(lines)
    blocks = sorted(CH._DIALOGUE, key=lambda b: b[0])
    why_of: dict[tuple[float, str], str] = {}
    for l in lines:
        why_of[(l["start"], l["text"])] = CH.why_no_exchange(l["start"], l["text"], CH.lyric_lines())

    out: list[str] = []
    w = out.append
    n_lines = sum(len(b[2]) for b in blocks)
    w("# \u6b4c\u8bcd \u2194 \u4f1a\u8bdd\u5bf9\u7167\u8868\uff08v3\uff0c\u673a\u5668\u751f\u6210\uff09")
    w("")
    w("> \u7528\u9014\uff1a**\u4f60\u636e\u6b64\u4fee\u6539**\u3002\u65f6\u95f4\u4e0e\u6b4c\u8bcd\u662f\u6743\u5a01"
      "\uff08\u4e0d\u6539\uff09\uff0c\u4e2d\u95f4\u4e24\u5217\u662f\u300c\u6211\u300d\u95ee\u4ec0\u4e48\u3001"
      "\u822a\u5c0f\u5929\u7b54\u4ec0\u4e48\uff0c\u53f3\u5217\u662f\u5f53\u65f6\u53f3\u680f\u5728\u753b\u4ec0\u4e48\u3002")
    w(">")
    w("> **\u672c\u6587\u4ef6\u7531 `_dev/chat_doc.py` \u751f\u6210**"
      "\uff08\u5bf9\u8bdd\u53d6\u81ea `school_chat._DIALOGUE`\uff0c\u6b4c\u8bcd\u53d6\u81ea\u5f71\u7247\u81ea\u5df1"
      "\u7684 `word_timeline.json`\uff0c\u53f3\u680f\u53d6\u81ea `school_panels.shot_rows()`\uff09\uff0c"
      "\u6240\u4ee5**\u6bcf\u4e00\u884c\u5bf9\u8bdd\u90fd\u5728\u8868\u91cc**\u2014\u2014\u5305\u62ec\u526f\u884c\u3001"
      "\u4ee3\u7801\u5757\u3001\u7cfb\u7edf\u884c\u4e0e\u5143\u4fe1\u606f\u3002")
    w("> \u6279\u6b21 52 \u4e4b\u524d\u5b83\u662f\u624b\u5199\u7684\uff0c\u7528\u6237\u62a5\u7684\u5c31\u662f"
      "\u300c\u6709\u4e9b\u822a\u5c0f\u5929\u7684\u56de\u7b54\u4e0d\u5728\u8868\u91cc\u300d\u3002")
    w(">")
    w("> \u6539\u6cd5\uff1a\u5728\u526f\u672c `05_\u6b4c\u8bcd\u4f1a\u8bdd\u5bf9\u7167_v2 - \u526f\u672c.md` "
      "\u91cc\u6539\uff0c\u544a\u8bc9\u6211\u6539\u4e86\u54ea\u91cc\uff0c\u6211\u843d\u5230 "
      "`school_lines*.py` \u5e76\u91cd\u65b0\u751f\u6210\uff1b\u76f4\u63a5\u6539\u672c\u6587\u4ef6\u4e5f\u884c"
      "\uff0c\u90a3\u6837 `chat_doc.py --check` \u4f1a\u53d8\u7ea2\uff0c\u76f4\u5230\u6539\u52a8\u843d\u5230"
      "\u4ee3\u7801\u91cc\u2014\u2014\u7ea2\u5c31\u662f\u300c\u8fd9\u53e5\u8bdd\u53ea\u5728\u8868\u91cc\u300d\u3002")
    w("")
    w(f"\u7edf\u8ba1\uff1a**{len(blocks)}** \u5757 / **{n_lines}** \u884c\u5bf9\u8bdd\uff0c"
      f"**{len(lines)}** \u884c\u6b4c\u8bcd\uff08\u5f71\u7247\u81ea\u5df1\u7684\u5b57\u5e55\u65f6\u95f4\u8f74\uff09\uff0c"
      f"**{len(SP.shot_rows())}** \u884c\u65e5\u7a0b\u3002")
    w("")
    w("### \u89d2\u8272\u56fe\u4f8b\uff08\u4e0e `school_lines*.py` \u7684 `who` \u5b57\u6bb5\u4e00\u4e00\u5bf9\u5e94\uff09")
    w("")
    w("| \u8868\u91cc | \u4ee3\u7801\u91cc | \u753b\u9762\u4e0a |")
    w("| --- | --- | --- |")
    for role, zh in (("user", "\u53f3\u5bf9\u9f50\u6c14\u6ce1\uff1a\u5b66\u751f"),
                     ("ai", "\u5de6\u5bf9\u9f50\u4e00\u884c\uff1a\u822a\u5c0f\u5929"),
                     ("sub", "\u7f29\u8fdb\u526f\u884c\uff08\u8ddf\u5728\u4e00\u6761 `ai` \u4e0b\u9762\uff09"),
                     ("code", "\u7b49\u5bbd\u4ee3\u7801\u5757"),
                     ("card", "\u300c> \u2026\u300d\u9879\u76ee\u7b26"),
                     ("err", "\u7ea2\u8272\u7cfb\u7edf\u884c"),
                     ("meta", "\u53f3\u5bf9\u9f50\u65f6\u95f4\u6233 / \u7528\u65f6")):
        w(f"| {ROLE_ZH[role]} | `{role}` | {zh} |")
    w("")
    w("---")
    w("")

    # ---- the per-line table, section by section
    w("## \u9010\u53e5\u5bf9\u7167\u8868")
    w("")
    w("\u6bcf\u4e00\u5757 = \u4e00\u53e5\u6b4c\u8bcd\u3002\u7b2c\u4e00\u884c\u662f\u300c\u53f3\u680f\u300d"
      "\uff08\u8fd9\u4e00\u53e5\u5728\u753b\u4ec0\u4e48\uff09\uff0c\u4e0b\u9762\u662f\u8fd9\u4e00\u53e5\u4e0a"
      "\u7684\u5bf9\u8bdd\uff0c\u9010\u884c\u3002\u6ca1\u6709\u5bf9\u8bdd\u7684\u6b4c\u8bcd\u4e5f\u5728\u8868\u91cc"
      "\uff0c\u5e76\u5199\u660e\u4e3a\u4ec0\u4e48\uff08\u534a\u53e5\u3001\u88ab\u753b\u9762\u76d6\u4f4f\u3001"
      "\u4e0a\u4e00\u53e5\u8fd8\u5728\u5c4f\u4e0a\u2026\uff09\u3002")
    idx = 0
    section = -1
    # One time-ordered stream of two kinds of item: a block (an exchange) and a lyric line nobody speaks
    # over. Emitting the second kind just before the *next* block put a line at 00:42.26 under the section
    # heading that starts at 00:44.04, so the section has to be chosen from each item's own time.
    items: list[tuple[str, float, object]] = [("block", b[0], b) for b in blocks]
    for l in lines:
        if why_of.get((l["start"], l["text"])):
            items.append(("line", l["start"], l))
    items.sort(key=lambda it: (it[1], 0 if it[0] == "line" else 1))
    emitted_lines: set[tuple[float, str]] = set()
    for kind, t, payload in items:
        while section + 1 < len(SECTIONS) and SECTIONS[section + 1][0] <= t + 1e-6:
            section += 1
            _, title, note = SECTIONS[section]
            if out and out[-1] != "":
                w("")
            w(f"### {title}")
            w("")
            if note:
                w(f"> {note}")
                w("")
            w("| # | \u65f6\u95f4 | \u6b4c\u8bcd | \u89d2\u8272 | \u53f0\u8bcd / \u53f3\u680f |")
            w("| --- | --- | --- | --- | --- |")
        if kind == "line":
            key = (payload["start"], payload["text"])
            if key in emitted_lines:
                continue
            emitted_lines.add(key)
            idx += 1
            w(f"| {idx} | {mmss(t)} | {cell(payload['text'])} | \u753b\u9762 | "
              f"{cell(why_of[key])} |")
            continue
        _t, tag, body = payload
        film = film_line_near(t, tag)
        idx += 1
        lyric_cell = cell(film[1]) if film else cell(tag)
        if film and film[1] != tag:
            lyric_cell += f" \u26a0 \u4ee3\u7801\u91cc\u6302\u7684\u662f \u300c{cell(tag)}\u300d"
        w(f"| {idx} | {mmss(t)} | {lyric_cell} | \u53f3\u680f | {cell(panel_cell(t))} |")
        # ...the dialogue, with the two halves of a `meta` cell (用时 / 时间戳) on one row: they are one
        # line of the window's right-aligned column and reading them as two rows doubles every block
        pending_meta: list[str] = []
        for role, text in body:
            if role == "meta":
                pending_meta.append(text)
                continue
            if pending_meta:
                w(f"|  |  |  | \u5143\u4fe1\u606f | {cell('  \u00b7  '.join(pending_meta))} |")
                pending_meta = []
            w(f"|  |  |  | {ROLE_ZH.get(role, role)} | {cell(text)} |")
        if pending_meta:
            w(f"|  |  |  | \u5143\u4fe1\u606f | {cell('  \u00b7  '.join(pending_meta))} |")
        if film:
            emitted_lines.add((film[0], film[1]))
    w("")

    # ---- the aircraft, from the events
    w("## \u98de\u673a\u4e0e\u9b54\u9b3c\u9c7c\uff08\u6309 `school_fx.EVENTS` \u751f\u6210\uff09")
    w("")
    w("| \u51fa\u573a | \u65f6\u95f4 | \u5728\u54ea\u4e00\u53e5\u6b4c\u8bcd\u4e0a | \u600e\u4e48\u98de |")
    w("| --- | --- | --- | --- |")
    for zh, key, how in PLANES:
        evs = [(s, e, kw) for s, e, fn, kw in FX.EVENTS if kw.get("name") == key]
        for s, e, kw in evs:
            lyric = next((l["text"] for l in lines if s - 1e-6 <= l["start"] < e), "")
            if not lyric:
                lyric = next((l["text"] for l in lines if s <= l["start"] < e + 1.0), "")
            w(f"| {zh} | {s:.2f}\u2013{e:.2f} | {cell(lyric) or '\u2014'} | {how} |")
    w("")

    # ---- the devices and the decisions
    w("## \u88c5\u7f6e\u4e0e\u7ea6\u5b9a")
    w("")
    w("- **IF/THEN**\uff1a`If` \u5f00\u53e5\u7684\u56de\u7b54\u843d\u5728\u5b83\u81ea\u5df1\u90a3\u4e00\u884c\uff0c"
      "`To` / `Then` \u534a\u53e5\u4e0d\u5360\u65b0\u7684\u4e00\u884c\u2014\u2014\u753b\u9762\u63a5\u7740"
      "\u4e0a\u4e00\u53e5\u8d70\u3002\u672c\u8868\u5728\u90a3\u4e9b\u884c\u91cc\u5199\u660e\u5b83\u8865\u5b8c"
      "\u7684\u662f\u54ea\u4e00\u53e5\u3002")
    w("- **\u4ee3\u7801\u5757 / \u5361\u7247 / \u7cfb\u7edf\u884c** \u90fd\u662f `school_lines*.py` "
      "\u91cc\u7684\u771f\u884c\uff0c\u4e0d\u662f\u672c\u8868\u7684\u63cf\u8ff0\u2014\u2014\u60f3\u6539"
      "\u5c31\u6539\u5b83\u4eec\u3002")
    w("- **\u65f6\u95f4** \u662f\u8fd9\u4e00\u5757\u5f00\u59cb\u51fa\u73b0\u7684\u65f6\u523b\uff08\u7b49\u4e8e"
      "\u53f3\u680f\u90a3\u4e00\u884c\u65e5\u7a0b\u7684 `at` \u9644\u8fd1\uff09\uff1b`word_timeline.json` "
      "\u91cc\u6bcf\u4e00\u884c\u6b4c\u8bcd\u7684\u5b57\u662f\u9010\u5b57\u6253\u51fa\u6765\u7684\uff0c\u6240\u4ee5"
      "\u7b54\u6848\u843d\u5728\u5b83\u90a3\u4e00\u53e5\u4e0a\u3002")
    w("")
    w("## \u5df2\u5b9a\u7684\u5730\u65b9\uff08\u7528\u6237\u88c1\u5b9a\uff0c\u4ee3\u7801\u6309\u7ed3\u8bba\u5b9e\u73b0\uff09")
    w("")
    w("| # | \u95ee\u9898 | \u7ed3\u8bba | \u843d\u5730 |")
    w("| --- | --- | --- | --- |")
    for n, q, verdict, land in DECISIONS:
        w(f"| {n} | {cell(q)} | {cell(verdict)} | {cell(land)} |")
    w("")
    w("\u5b8c\u6574\u7684\u88c1\u5b9a\u7406\u7531\u4e0e\u6bcf\u4e00\u6761\u7684\u5f53\u65f6\u8bc1\u636e\u5728 "
      "`06_\u65f6\u5e8f\u5bf9\u7167\u8868.md` \u4e0e `04_\u9a8c\u8bc1\u8bb0\u5f55/` \u91cc\uff1b\u8fd9\u91cc"
      "\u53ea\u5217\u7ed3\u8bba\uff0c\u56e0\u4e3a\u8fd9\u4efd\u6587\u4ef6\u7684\u4e3b\u4f53\u662f\u5bf9\u8bdd\u3002")
    w("")
    w("## \u8fd9\u4efd\u8868\u600e\u4e48\u4fdd\u6301\u771f\u7684")
    w("")
    w("| \u5de5\u5177 | \u7ba1\u4ec0\u4e48 |")
    w("| --- | --- |")
    w("| `_dev/chat_doc.py --check` | \u672c\u6587\u4ef6\u662f\u5426\u4e0e\u4ee3\u7801\u4e00\u81f4"
      "\uff08\u5728 `check.cmd` \u91cc\uff09 |")
    w("| `_dev/chat_audit.py` | \u6bcf\u4e00\u884c\u7684\u65f6\u95f4\u662f\u5426\u7b49\u4e8e\u5b83\u6302"
      "\u7684\u90a3\u53e5\u6b4c\u8bcd\u7684\u65f6\u95f4\uff1b\u5143\u4fe1\u606f\u91cc\u7684\u65f6\u949f\u662f"
      "\u5426\u4e0e\u81ea\u5df1\u7684\u65f6\u95f4\u4e00\u81f4 |")
    w("| `school_chat.check_coverage()` | \u6bcf\u4e00\u53e5\u6b4c\u8bcd\u90fd\u6709\u4ea4\u4ee3"
      "\uff08\u81ea\u5df1\u7684\u5bf9\u8bdd\u3001\u534a\u53e5\u3001\u88ab\u753b\u9762\u76d6\u4f4f\u3001"
      "\u4e0a\u4e00\u53e5\u8fd8\u5728\u5c4f\u4e0a\u3001\u6216\u5177\u540d\u7684\u6c89\u9ed8\u6bb5\uff09 |")
    w("")
    return "\n".join(out) + "\n"


def cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def mmss(t: float) -> str:
    return f"{int(t // 60):02d}:{t % 60:05.2f}"


_LINES: list = []


def main() -> None:
    text = build()
    if "--check" in sys.argv:
        old = DOC.read_text(encoding="utf8") if DOC.exists() else ""
        if old != text:
            print(f"05_\u6b4c\u8bcd\u4f1a\u8bdd\u5bf9\u7167_v2.md is out of date "
                  f"({len(old)} -> {len(text)} chars, sha "
                  f"{hashlib.sha256(old.encode()).hexdigest()[:8]} -> "
                  f"{hashlib.sha256(text.encode()).hexdigest()[:8]}); run:\n"
                  f"    python _dev/chat_doc.py")
            raise SystemExit(1)
        print("05_\u6b4c\u8bcd\u4f1a\u8bdd\u5bf9\u7167_v2.md is up to date")
        return
    DOC.write_text(text, encoding="utf8")
    print(f"{DOC}  ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    main()
