"""收尾段现在到底由什么在画？—— 为提示词文档第 06 条（卡在 99%）定位落点。

上一版 `probe_finale.py` 只看了 `school_panels.shot_rows()`，它的最后一行是 193.46。
但**学校变体的行表不等于影片的 shot 表**：`tui_live` 的主循环走的是影片自己的 shot 表
（`engine`），到 211.9 结束。所以"200 秒之后谁在画"必须问 engine，不能问行表。

这个探针同时打印两边的答案，并把"这一段有哪些歌词"再确认一遍。

    python _dev/probe_finale_who.py
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import tui_live as T
    import school_panels as SP

    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    T.SP = SP
    eng = T.Engine()

    print(f"END = {T.END:.3f}")
    # engine 的接口：找一下它怎么按时间取 shot
    cands = [n for n in dir(eng) if not n.startswith("__")]
    print(f"Engine 成员: {', '.join(cands)}")
    print()

    def shot_at(t):
        for name in ("at", "shot", "find", "row", "entry", "for_time"):
            fn = getattr(eng, name, None)
            if callable(fn):
                try:
                    r = fn(t)
                except Exception:
                    continue
                if r is not None:
                    return name, r
        return None, None

    print("t -> engine 给出的东西：")
    for t in (150.0, 180.0, 190.0, 195.0, 200.0, 203.0, 206.0, 209.0, 211.0, 211.8):
        which, r = shot_at(t)
        if isinstance(r, tuple) and r and isinstance(r[0], dict):
            d = r[0]
            print(f"  t={t:6.1f}  via {which}: name={d.get('name')} index={d.get('index')}")
        else:
            print(f"  t={t:6.1f}  via {which}: {type(r).__name__} {str(r)[:90]}")
    print()

    # 行表最后几行
    rows = SP.shot_rows()
    print("school 行表最后 5 行（用于对照）:")
    for r in rows[-5:]:
        print(f"  {r['at']:7.2f}  {r['name']}")
    print()

    # 收尾段画出来的画面里有什么（用文本 dump 看关键词，不依赖视觉模型）
    data = T.Data()
    print("收尾段几次取样：屏幕上是否出现这些关键词")
    keys = ("EXECUTION", "execution", "PROCESS", "LOOP", "99", "%", "\u6821\u5fbd", "\u8bda")
    for t in (190.0, 195.0, 200.0, 205.0, 209.0, 211.0):
        s = T.Screen(197, 52)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.normalise()
        dump = s.text_dump()
        hits = [k for k in keys if k in dump]
        print(f"  t={t:6.1f}  {hits if hits else '（以上关键词一个都没有）'}")


if __name__ == "__main__":
    main()
