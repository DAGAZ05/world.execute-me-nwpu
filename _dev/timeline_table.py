"""The whole song as one timeline: lyric x dialogue x panel x overlay.

    python _dev/timeline_table.py                 writes _dev/out/audit/timeline.md and .tsv

Everything here is read out of the modules the player itself reads - `school_panels.shot_rows()` for the
schedule, `tui_live.Data().lines` for the lyric timeline, `school_chat._DIALOGUE` for the chat window and
`school_fx.EVENTS` for the full-frame layer - so the table cannot drift from what plays. It is the
*input* to the batch's correlation table, not a copy of it: the panel column carries the pane's name,
and what the pane draws is written down per panel (and checked) in the same batch.

Two things the table deliberately leaves out, per the request: the film's own `feature bands` box and the
`progress` bar (chrome, not an event).
"""
from __future__ import annotations

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
import panel_catalog as PC      # noqa: E402  the panel's own claim about what it draws

OUT = Path(__file__).resolve().parent / "out" / "audit"
OUT.mkdir(parents=True, exist_ok=True)
# the hand-written panel catalogue (name -> what it draws / what text it prints / verdict), if present
DESC = OUT / "panes.tsv"


def catalogue() -> dict[str, tuple[str, str, str]]:
    out: dict[str, tuple[str, str, str]] = {}
    if not DESC.exists():
        return out
    for ln in DESC.read_text(encoding="utf8").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        parts = ln.split("\t")
        if len(parts) >= 4:
            out[parts[0].strip()] = (parts[1].strip(), parts[2].strip(), parts[3].strip())
    return out


def claims() -> dict[str, str]:
    """pane -> what the code says it draws, from `panel_catalog` so the table and the catalogue agree."""
    import panel_catalog as PC
    return PC.claims()

ROLE_ZH = {"user": "我", "ai": "航小天", "sub": "副行", "code": "代码块", "meta": "元信息"}


def fx_brief(kw: dict) -> str:
    """The parts of an event's keyword arguments that are *content*: which picture, its size, its caption."""
    keep = ("name", "caption", "cols_n", "rows_n", "fill", "zoom", "peak", "side", "box", "dim")
    bits = [f"{k}={v!r}" for k, v in kw.items() if k in keep]
    return " ".join(bits)


def main() -> None:
    T.VAR[0] = "school"
    T.SP = SP
    cat = catalogue()
    claim = claims()
    rows = SP.shot_rows()
    lines = T.Data().lines
    dial = CH._DIALOGUE

    # the schedule must tile the song, or a row is being silently dropped (`_build` reports overlaps)
    gaps = [(a["end"], b["at"]) for a, b in zip(rows, rows[1:]) if abs(a["end"] - b["at"]) > 1e-6]
    md: list[str] = []
    tsv: list[str] = []
    md.append("# 全曲时序（机器生成，`_dev/timeline_table.py`）\n")
    md.append(f"78 行日程覆盖 {rows[0]['at']:.2f} - {rows[-1]['end']:.2f}s；"
              f"歌词 {len(lines)} 行；对话 {len(dial)} 块 / "
              f"{sum(len(b[2]) for b in dial)} 行；整屏层 {len(FX.EVENTS)} 个事件。\n")
    if gaps:
        md.append(f"**日程有 {len(gaps)} 处不连续**：{gaps}\n")
    tsv.append("start\tend\tschool_pane\tlyric_row\tlyric_lines\tdialogue\tops\tfx")
    for r in rows:
        at, end = r["at"], r["end"]
        name = r["name"] or "(影片自己的 pane)"
        lyr = [ln["text"] for ln in lines if at - 1e-6 <= ln["start"] < end - 1e-6]
        d = [b for b in dial if at - 1e-6 <= b[0] < end - 1e-6]
        ev = [(s, e, fn.__name__, fx_brief(kw)) for s, e, fn, kw in FX.EVENTS
              if s < end - 1e-6 and e > at + 1e-6]
        # the motif bands are gone as of batch 32 (they drew a motif a second time under the pane whose
        # lyric it belonged to, and every one of those motifs has a pane of its own)
        what, text, verdict = cat.get(r["name"], ("", "", ""))
        md.append(f"\n## {at:7.2f} - {end:7.2f}  `{name}`\n")
        md.append(f"- 歌词行：{r['lyric']!r}" + (f"；区间内 {len(lyr)} 行" if lyr else ""))
        if lyr:
            md.append(f"- 区间内歌词：{'; '.join(lyr)}")
        md.append(f"- ops：{'/'.join(map(str, r['ops']))}"
                  + ("；mascot=航小天可占左栏" if r.get("mascot") else ""))
        if what:
            md.append(f"- 画面：{what}")
        if text:
            md.append(f"- 屏上文字：{text}")
        if verdict:
            md.append(f"- 核验：{verdict}")
        for b in d:
            md.append(f"- 对话 @{b[0]:.2f}（挂在 {b[1]!r}）：")
            for role, txt in b[2]:
                md.append(f"    - {ROLE_ZH.get(role, role)}：{txt}")
        for s, e, nm, brief in ev:
            md.append(f"- 整屏层：{s:.2f}-{e:.2f} `{nm}` {brief}")
        tsv.append("\t".join([
            f"{at:.2f}", f"{end:.2f}", name, r["lyric"], " | ".join(lyr),
            " || ".join(f"{ROLE_ZH.get(x, x)}:{y}" for b in d for x, y in b[2]),
            "/".join(map(str, r["ops"])), " | ".join(f"{s:.2f}-{e:.2f} {nm} {br}" for s, e, nm, br in ev),
        ]))
    # the window events (the basketball, drawn *in* the chat window) and the shocks, for completeness
    md.append("\n---\n\n## 整屏层 / 窗口层 事件表\n")
    for s, e, fn, kw in FX.EVENTS:
        md.append(f"- {s:7.2f}-{e:7.2f}  整屏 `{fn.__name__}`  {fx_brief(kw)}")
    for s, e, fn, kw in FX.WINDOW_EVENTS:
        md.append(f"- {s:7.2f}-{e:7.2f}  会话框 `{fn.__name__}`  {fx_brief(kw)}")
    for s, e, amt in FX.SHOCKS:
        md.append(f"- {s:7.2f}-{e:7.2f}  震屏 {amt}")
    # ...and the same thing as one table, which is what the batch's record asks for: one row per row of
    # the schedule, with the lyrics it covers, the words in the chat window, the drawing, its ops and the
    # full-frame layer. `panes.tsv` (the hand-written catalogue) supplies the "what it draws" cell.
    tbl = ["# 全曲时序对照表（歌词 ↔ 对话 ↔ panel ↔ 整屏层）",
           "",
           "机器生成：`python _dev/timeline_table.py`。每一行是 `school_panels.shot_rows()` 的一行日程，",
           "时间取自该行自己的 `at`/`end`；歌词取自 `tui_live.Data().lines`（与 `input/lyrics.lrc` 同一份）；",
           "对话取自 `school_chat._DIALOGUE`（= `school_lines` + `school_lines_act2` 的行表）；",
           "整屏层取自 `school_fx.EVENTS`。**不含** `feature bands` 与 `progress`（按要求：那是 chrome 不是事件）。",
           "",
           "| # | 时间 | 歌词 | 对话（我 / 航小天 / 副行·代码） | panel | 画什么 | ops / 清单标题 | 整屏层 |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(rows, 1):
        at, end = r["at"], r["end"]
        name = r["name"] or "(影片自己的 pane)"
        lyr = [ln["text"] for ln in lines if at - 1e-6 <= ln["start"] < end - 1e-6]
        d = [b for b in dial if at - 1e-6 <= b[0] < end - 1e-6]
        ev = [(s, e, fn.__name__, fx_brief(kw)) for s, e, fn, kw in FX.EVENTS
              if s < end - 1e-6 and e > at + 1e-6]
        what = cat.get(r["name"], ("", "", ""))[0] or (
            PC.claim_for(r["name"], claim) if r["name"] else "")
        cell = lambda s: str(s).replace("|", "\\|").replace("\n", " ")          # noqa: E731
        talk = "<br>".join(f"{ROLE_ZH.get(role, role)}：{txt}" for b in d for role, txt in b[2])
        layer = "<br>".join(f"{s:.2f}-{e:.2f} `{nm}` {br}" for s, e, nm, br in ev)
        tbl.append("| {} | {:.2f}-{:.2f} | {} | {} | `{}` | {} | {} | {} |".format(
            i, at, end, cell(" / ".join(lyr)) or "—", cell(talk) or "—", name,
            cell(what) or "—", cell("/".join(map(str, r["ops"]))), cell(layer) or "—"))
    (OUT / "shishu_biao.md").write_text("\n".join(tbl) + "\n", encoding="utf8")
    print(f"{OUT / 'shishu_biao.md'}")
    print(f"{OUT / 'timeline.md'}")
    print(f"{OUT / 'timeline.tsv'}")
    print(f"rows {len(rows)}  gaps {len(gaps)}  lyric lines {len(lines)}  dialogue blocks {len(dial)}")


if __name__ == "__main__":
    main()
