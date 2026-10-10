"""收尾段（03:12 之后）现在是什么？—— 为提示词文档第 06 条（卡在 99% 的进度条）做现场勘查。

文档第 06 条：「03:12.5–03:31.9，加一个卡在99%的进度条动画，最后一句 execution 的时候
进度条变成一个同风格的红色 execution」。

要动这一段，先得知道三件事：这一段有哪些 shot、有哪些歌词、以及**现在画了什么**。
前两件在这里打印，第三件靠 `_dev/probe_dissolve.py` 那类对照图看（本机没有可用视觉模型）。

    python _dev/probe_finale.py
    python _dev/probe_finale.py --from 190 --to 212
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from", dest="lo", type=float, default=188.0)
    ap.add_argument("--to", dest="hi", type=float, default=212.0)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import tui_live as T
    import school_panels as SP

    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    T.SP = SP

    print(f"END = {T.END:.3f} s")
    print()
    rows = SP.shot_rows()
    print(f"片尾 shot 行（窗口 {a.lo:.1f}-{a.hi:.1f} 及最后 10 行）:")
    for r in rows:
        if a.lo <= r["at"] <= a.hi or r in rows[-10:]:
            print(f"  {r['at']:7.2f}  {r['name']}")
    print()
    print(f"{len(rows)} 行总计；最后一行 {rows[-1]['at']:.2f} {rows[-1]['name']}")
    print()

    import school_lines
    import school_lines_act2
    print(f"窗口 {a.lo:.1f}-{a.hi:.1f} 的歌词行:")
    seen = 0
    for mod in (school_lines, school_lines_act2):
        for e in getattr(mod, "LINES", []):
            if a.lo <= e[0] <= a.hi:
                kind = e[2] if len(e) > 2 else "?"
                zh = str(e[3])[:44] if len(e) > 3 else ""
                print(f"  {e[0]:7.2f}  [{kind:4s}] {e[1]!r}")
                if zh:
                    print(f"           {zh}")
                seen += 1
    if not seen:
        print("  （这一段没有歌词行）")
    print()
    print("提示词文档第 06 条要的是：这一段加一个**卡在 99%** 的进度条，")
    print("最后一句 execution 时它变成同风格的红色 EXECUTION 大字。")


if __name__ == "__main__":
    main()
