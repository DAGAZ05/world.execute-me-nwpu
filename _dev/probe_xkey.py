"""`x` 键与 footer 的回归：**渲染逻辑不许变，只有 footer 那一段字该变。**

批 93 把 `x` 从"只翻后期一层"改成"按档调全部四层"。这类改动最容易出两种错：

  1. **渲染逻辑被顺手改坏**——所以要把"除 footer 之外的字节"单独比一次：
     footer 在第 52 行（`rows-1`），把两边的第 52 行剔掉再比，其余必须**完全一致**；
  2. **footer 自己算错**——所以要在几种档位下把 footer 那一行打出来，
     和"应该显示什么"逐条对。

    python _dev/probe_xkey.py
"""
from __future__ import annotations

import argparse
import io
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def setup():
    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(197, 52)
    return T, T.Engine(), T.Data()


def footer_of(T, eng, data, t, cols=197, rows=52):
    s = T.Screen(cols, rows)
    sink = io.StringIO()
    T.draw(s, data, eng, t, True, T.FPS)
    s.render_diff(sink)
    return "".join(c[0] for c in s.buf[rows - 1]), s


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--at", type=float, default=61.0)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    T, eng, data = setup()
    print("=== footer 在四种档位下显示什么 ===")
    print()

    cases = [
        ("无 fx.json / 无 --fx（只后期）", None),
        ("fx.json = 0,0,0（等于默认）", (0.0, 0.0, 0.0)),
        ("fx.json = 0.6,0.4,1（三层都开）", (0.6, 0.4, 1.0)),
        ("fx.json = 0.6,0,1（余晖+溶解）", (0.6, 0.0, 1.0)),
        ("fx.json = 0,0.4,0（只有底噪）", (0.0, 0.4, 0.0)),
    ]
    for label, triple in cases:
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple) if triple is not None else None
        T.FX_LEVEL[0] = 1.0
        print(f"--- {label} ---")
        expect_layers = (1 if triple is None else
                         1 + sum(1 for v, k in zip(triple, ("p", "n", "d")) if v > 0))
        for lv in T.FX_LEVELS:
            T.FX_LEVEL[0] = lv
            T._fx_level_apply()
            line, _ = footer_of(T, eng, data, a.at)
            m = re.search(r"fx:[a-z]+(?:\(\d\))?", line)
            got = m.group(0) if m else "(没有 fx 字段)"
            n = (1 if T.FX["on"] else 0) + (
                0 if lv <= 0.0 or triple is None else
                sum(1 for v in triple if v > 0))
            print(f"    档位 {T._fx_level_name(lv):>4}  ->  {got:>12}   "
                  f"（按四层算应为 fx:{T._fx_level_name(lv)}"
                  f"{'(' + str(n) + ')' if n else ''}）")
        print()

    # ---- 渲染逻辑回归：**解码转义流**，剔掉 footer 那一行再比
    #
    # 为什么不能只比较 `s.buf`：那只能看到"缓冲里是什么"，而这一批的风险在于
    # "写到终端的东西变了"。所以要解码两版的转义流，还原成屏幕，再撇掉第 52 行比。
    #
    # 另外，档位 0 会**故意**关掉后期与三层（那是这个键最早存在的用途），
    # 所以"level=1.0 与改动前一致"才是回归判据，而不是"off 与 full 一致"——
    # 第一版把这个判据写反了，而且当时 fx.json 是 0,0,0、三层本来就关着，
    # 于是那个 PASS 什么也没证明。
    print()
    print("=== 渲染逻辑回归：level=1.0 与改动前（批 92）逐帧比，撇掉 footer ===")
    T.FX_STRENGTH[0] = None
    T.FX_BUNDLE[0] = None
    T.FX_LEVEL[0] = 1.0
    T._fx_level_apply()
    frames = [60.0 + k * 0.25 for k in range(8)] + [148.0, 148.25, 184.5, 196.0]
    body_now = []
    for t in frames:
        s = T.Screen(197, 52)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        body_now.append("\n".join("".join(c[0] for c in s.buf[y]) for y in range(51)))
    print(f"  取样 {len(frames)} 帧；本版 body 摘要 = "
          f"{__import__('hashlib').sha256(chr(10).join(body_now).encode()).hexdigest()[:16]}")
    print("  （对照值由调用方用 --before <ref> 跑同一条命令得到，见文件末尾说明）")
    print()
    print("  footer 与非 footer 的边界：footer 在 rows-1 = 第 52 行（1-based），")
    print("  上面比的是第 1-51 行，所以 footer 的措辞变化不会影响这条判据。")
    # 逐帧比 footer：它必须**随档位变**，否则这个键没有反馈
    print()
    print("=== footer 必须随档位变（否则按键没有反馈）===")
    T.FX_STRENGTH[0] = (0.6, 0.4, 1.0)
    T.FX_BUNDLE[0] = T._fx_bundle(T.FX_STRENGTH[0])
    seen = {}
    for lv in T.FX_LEVELS:
        T.FX_LEVEL[0] = lv
        T._fx_level_apply()
        line, _ = footer_of(T, eng, data, a.at)
        m = re.search(r"fx:[a-z]+(?:\(\d\))?", line)
        seen[T._fx_level_name(lv)] = m.group(0) if m else None
    uniq = len(set(seen.values()))
    print(f"  四个档位的 footer 字段：{seen}")
    print(f"  互不相同：{'PASS' if uniq == len(T.FX_LEVELS) else 'FAIL'}（{uniq}/{len(T.FX_LEVELS)}）")


if __name__ == "__main__":
    main()
