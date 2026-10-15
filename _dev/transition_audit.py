"""审计：哪些动画行的**内部**（不是行的边界）会触发一次换场特效。

清单2 第 10 条：用户说三旋臂与 ε-N 各自中间都有换场特效、要删掉，并要求
「除此以外，你去检测所有动画中在自身内部存在换场特效的，我确认后进行删除」。

判据：换场特效是挂在**切换点**上的。如果一个切换点的时刻**严格落在某一行的 at 与 end 之间**
（既不是 at、也不是 end），那么观众看到的就是"这一行演到一半，画面自己换了一次场"。

    python _dev/transition_audit.py
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_panels as SP      # noqa: E402
import tui_live as T            # noqa: E402


def cut_times():
    """所有切换时刻，从几个可能的来源里收集。"""
    out = {}
    for name in ("CUTS", "CUT_AT", "SCHOOL_CUTS"):
        v = getattr(SP, name, None)
        if v:
            out[name] = list(v) if not callable(v) else list(v())
    for name in ("SCHOOL_CUTS", "CUTS"):
        v = getattr(T, name, None)
        if v:
            out["T." + name] = list(v) if not callable(v) else list(v())
    fn = getattr(SP, "school_cuts", None)
    if callable(fn):
        try:
            out["school_cuts()"] = list(fn())
        except Exception as e:
            out["school_cuts()"] = ["ERR: %s" % e]
    return out


def main() -> None:
    print("=== 切换点来源 ===")
    for k, v in cut_times().items():
        print("  %-18s len=%d  %s" % (k, len(v), str(v[:12])[:110]))
    print()

    rows = [(r["at"], r["end"], r.get("name") or "?", r.get("lyric") or "")
            for r in SP.shot_rows() if r.get("name")]
    print("排期行数 =", len(rows))

    cuts = []
    for k, v in cut_times().items():
        for c in v:
            if isinstance(c, (int, float)):
                cuts.append(float(c))
    cuts = sorted(set(cuts))
    print("切换点总数 =", len(cuts))
    print()

    inside = []
    for at, end, name, ly in rows:
        span = max(1e-6, end - at)
        # **只看"落在行中段"的切换**：行开头/结尾 0.35 之内的切换是**入场/出场**效果，
        # 本来就该在边界上发生。第一版用 0.02 的边界余量，于是 87 行里报了 38 行——
        # 其中绝大多数是 `at + 0.1~0.2` 的入场切换，把真问题淹掉了。
        hit = [(c, (c - at) / span) for c in cuts if at + 0.35 * span < c < end - 0.35 * span]
        if hit:
            inside.append((at, end, name, ly, span, hit))
    print("=== 切换点落在行**中段**（开头/结尾各让开 35%%）的行（%d 行）===" % len(inside))
    for at, end, name, ly, span, hit in inside:
        desc = " ".join("%.2f(%.0f%%)" % (c, f * 100) for c, f in hit)
        print("  %7.2f-%7.2f  %-24s %-26s 中段切换 %s"
              % (at, end, name, ly[:26], desc))


if __name__ == "__main__":
    main()
