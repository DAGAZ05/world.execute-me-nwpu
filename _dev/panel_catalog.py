"""Every panel in the schedule, as one table: when it runs, what the code *says* it draws, what text it
really prints, and what the audit concluded.

    python _dev/panel_catalog.py          writes _dev/out/audit/panel_catalog.md

The three middle columns come from three different places on purpose:

  * **when** - `school_panels.shot_rows()`, the schedule the player reads;
  * **what the code says** - the drawing function's own docstring, first sentence. This is the *claim*;
  * **what it prints** - rendered: the pane is drawn alone into a `Screen` at the size the schedule gives
    it (95x33 at 197x52) and the buffer's own characters are read back. This is the *evidence*;
  * **核验** - `_dev/out/audit/panes_verdict.tsv` (name, verdict), written from the batch's audits, so a
    claim and its check can never drift apart in this file.

The batch-31 audit is exactly the comparison of column 3 with column 4: a panel whose code says "sin x"
and whose drawing is a cosine is caught here, and so is a caption that says 4096 while the counter stops
at 64.
"""
from __future__ import annotations

import ast
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"
sys.path.insert(0, str(TOOLS))
os.environ.setdefault("PV_VARIANT", "school")

import tui_live as T            # noqa: E402
import school_panels as SP      # noqa: E402
import school_scenes as SC      # noqa: E402

OUT = Path(__file__).resolve().parent / "out" / "audit"
# the verdicts live next to the tools, not in `out/` (which is gitignored): they are the one
# hand-written input of this generator
VERDICT = Path(__file__).resolve().parent / "panes_verdict.tsv"
MODULES = ("school_scenes.py", "school_courses.py", "school_motifs.py", "school_sculpture.py")
W, H = 95, 33


def claims() -> dict[str, str]:
    """function name -> the first sentence of its docstring (the code's own claim about the drawing)."""
    out: dict[str, str] = {}
    for mod in MODULES:
        tree = ast.parse((TOOLS / mod).read_text(encoding="utf8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node) or ""
                first = doc.strip().split("\n\n")[0].replace("\n", " ").strip()
                out[node.name] = first
    return out


def verdicts() -> dict[str, str]:
    out: dict[str, str] = {}
    if VERDICT.exists():
        for ln in VERDICT.read_text(encoding="utf8").splitlines():
            if ln.strip() and not ln.startswith("#") and "\t" in ln:
                k, v = ln.split("\t", 1)
                out[k.strip()] = v.strip()
    return out


def text_of(pane: str, t: float) -> str:
    """The pane drawn alone at (W, H), read back as strings - the panel's own words.

    Drawn through `school_panels.draw_scene_pane`, which is the same route the frame takes: a course
    drawing, then a gauge, then the batch-1 scenes. Calling `school_scenes` directly would have reported
    the fourteen course panes and the six gauges as "not a pane".
    """
    s = T.Screen(W, H)
    if not SP.draw_scene_pane(pane, s, 0, 0, W - 1, H - 1, t, 0.5, 1.0, 1.0):
        return "(这张 pane 画不出来)"
    seen: list[str] = []
    for y in range(H):
        row = "".join(s.buf[y][x][0] for x in range(W)).strip()
        row = " ".join(row.split())
        if row and row not in seen:
            seen.append(row)
    return " ／ ".join(seen)


def claim_for(pane: str, claim: dict[str, str] | None = None) -> str:
    """The code's own claim about `pane` - the drawing function's first docstring sentence.

    The factory panes (`pane_motif_*`, `pane_ai_*`, the courses and gauges) carry the *factory's* name,
    so the claim has to be looked up on the function they dispatch to.
    """
    claim = claims() if claim is None else claim
    import school_courses as _CO
    fn = SC.PANE_BY_NAME.get(pane)
    for key in (getattr(fn, "__name__", pane), pane):
        if claim.get(key):
            return claim[key]
    if pane.startswith("pane_motif_") and claim.get(pane[len("pane_motif_"):]):
        return claim[pane[len("pane_motif_"):]]
    for table in (_CO.COURSES, _CO.AI):
        if pane in table:
            sub = getattr(table[pane][1], "__name__", "")
            if claim.get(sub):
                return claim[sub]
    return ""


def main() -> None:
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    claim, verdict = claims(), verdicts()
    rows = SP.shot_rows()
    times: dict[str, list[str]] = {}
    for r in rows:
        if r["name"]:
            times.setdefault(r["name"], []).append(f"{r['at']:.2f}")
    md = ["# panel 清单：日程 → 代码自己的说法 → 屏上真的写了什么 → 核验", "",
          "机器生成（`python _dev/panel_catalog.py`）。第四列是**渲染后从缓冲区读回**的文字（95×33，",
          "也就是 197×52 下面板的真实尺寸），所以它和第五列的核验是「声称 vs 实际」的两侧。", "",
          "| panel | 出现（秒） | 代码自己的说法（docstring 首句） | 屏上文字（渲染读回） | 核验 |",
          "| --- | --- | --- | --- | --- |"]
    for pane in sorted(times):
        c = claim_for(pane, claim)
        md.append("| `{}` | {} | {} | {} | {} |".format(
            pane, "、".join(times[pane]),
            c.replace("|", "\\|")[:220] or "—",
            text_of(pane, float(times[pane][0]) + 0.35).replace("|", "\\|")[:300] or "—",
            verdict.get(pane, "").replace("|", "\\|") or "—"))
    (OUT / "panel_catalog.md").write_text("\n".join(md) + "\n", encoding="utf8")
    missing = [p for p in times if p not in verdict]
    print(f"{len(times)} panes -> {OUT / 'panel_catalog.md'}")
    print(f"{len(missing)} without a verdict yet: {', '.join(missing) if missing else 'none'}")


if __name__ == "__main__":
    main()
