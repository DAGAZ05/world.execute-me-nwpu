"""复现：`--fx 0.2,0.1,0.05` 到底有没有生效？按 `x` 有没有变化？

用户的报告是"一个特效都没有，按 x 也没改变"。这条要**按用户的方式**验，
而不是按我认为的方式验：

  1. 走 `run.cmd` 同一条参数路径（`--variant school --fx ...`），看 `args.fx` 有没有被解析出来；
  2. 看三层在那个强度下**实际**落到什么参数、画出来多少格；
  3. 模拟按 `x`，看 footer 与三层是否变化；
  4. 特别验一个我之前没验的组合：**`fx.json` 是 0,0,0 + 命令行给 `--fx`**。

    python _dev/probe_fx_repro.py
"""
from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fx", default="0.2,0.1,0.05")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_fx as FX
    import school_gate as G
    import school_panels as SP
    import tui_live as T

    cols, rows = 197, 52
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    print("=" * 78)
    print("A. argparse 能不能解析 `--variant school --fx 0.2,0.1,0.05`（run.cmd 的原始路径）")
    print("=" * 78)
    ap2 = argparse.ArgumentParser()
    # 与 tui_live 里的定义保持一致（这里只关心这个参数能不能吃下 cmd 传过来的串）
    ap2.add_argument("--variant", default="school")
    ap2.add_argument("--fx", default=None)
    ap2.add_argument("--no-audio", action="store_true")
    try:
        ns = ap2.parse_args(["--variant", "school", "--fx", a.fx])
        print(f"  args.fx = {ns.fx!r}   解析成功")
        triple = tuple(float(p) for p in ns.fx.replace("\uff0c", ",").split(","))
        print(f"  -> 三元组 {triple}")
    except SystemExit as exc:
        print(f"  **argparse 退出：{exc}**")
        return

    print()
    print("=" * 78)
    print("B. 这三种强度映射到各层自己的参数是多少")
    print("=" * 78)
    p = T._fx_params(triple)
    print(f"  三元组 {triple}")
    print(f"  phosphor decay = {p['phosphor']}")
    print(f"  noise scale    = {p['noise']}   stride = {p['noise_stride']}")
    print(f"  dissolve       = {p['dissolve']}")

    print()
    print("=" * 78)
    print("C. 真正跑一遍：三层各画了多少格、画面与'全关'差多少格")
    print("=" * 78)

    def render(t, triple, level, path="--fx"):
        """返回 (屏幕, footer 行)"""
        if path == "--fx":
            T.FX_STRENGTH[0] = triple
            T.FX_BUNDLE[0] = T._fx_bundle(triple) if triple is not None else None
        T.FX_LEVEL[0] = level
        T._fx_level_apply()
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(sink)
        return s

    t = 61.5
    base = render(t, None, 1.0)          # 什么都关（FX_BUNDLE=None，但 FX["on"] 仍 True）
    # 真正"全关"的参照：先把 FX 也关掉
    T.FX_STRENGTH[0] = None
    T.FX_BUNDLE[0] = None
    T.FX_LEVEL[0] = 0.0
    T._fx_level_apply()
    s_off = T.Screen(cols, rows)
    T.draw(s_off, data, eng, t, True, T.FPS)
    s_off.render_diff(io.StringIO())

    for lv in T.FX_LEVELS:
        s = render(t, triple, lv)
        diff = sum(1 for y in range(rows) for x in range(cols)
                   if s.buf[y][x] != s_off.buf[y][x])
        foot = "".join(c[0] for c in s.buf[rows - 1])
        import re
        m = re.search(r"fx:[a-z]+(?:\(\d\))?", foot)
        nz = T.NOISE[0]
        print(f"  档位 {T._fx_level_name(lv):>4}  FX.on={str(T.FX['on']):>5}  "
              f"底噪={'on' if nz else 'off':>3}"
              f"{'(scale %s stride %s)' % (nz.scale, T._fx_params(triple)['noise_stride']) if nz else '':<22}"
              f"  与全关差 {diff:5d} 格   footer {m.group(0) if m else '(无)'}")

    print()
    print("=" * 78)
    print("D. 关键问题：`--fx` 给了、但 fx.json 是 0,0,0 时会怎样")
    print("=" * 78)
    real = T.FX_FILE[0]
    tmp = ROOT / "_dev" / "out" / "fx_repro_zero.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text('{"phosphor":0,"noise":0,"dissolve":0}', encoding="utf-8")
    T.FX_FILE[0] = tmp
    try:
        f = T._fx_load_file()
        print(f"  fx.json(0,0,0) 读到 {f}")
        print(f"  命令行 --fx    给出 {triple}")
        print("  按 tui_live 的优先级：命令行优先 -> 用命令行。")
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple)
        for lv in T.FX_LEVELS:
            T.FX_LEVEL[0] = lv
            T._fx_level_apply()
            nz = T.NOISE[0]
            print(f"    档位 {T._fx_level_name(lv):>4}  FX.on={str(T.FX['on']):>5}  "
                  f"底噪={'on' if nz else 'off'}")
    finally:
        tmp.unlink(missing_ok=True)
        T.FX_FILE[0] = real

    print()
    print("=" * 78)
    print("E. `x` 键的循环（模拟连按 4 次）")
    print("=" * 78)
    T.FX_STRENGTH[0] = triple
    T.FX_BUNDLE[0] = T._fx_bundle(triple)
    T.FX_LEVEL[0] = 1.0
    T._fx_level_apply()
    import re
    for i in range(5):
        T._fx_level_apply()
        s = T.Screen(cols, rows)
        T.draw(s, data, eng, t, True, T.FPS)
        s.render_diff(io.StringIO())
        foot = "".join(c[0] for c in s.buf[rows - 1])
        m = re.search(r"fx:[a-z]+(?:\(\d\))?", foot)
        nz = T.NOISE[0]
        mark = "   <== 按 x 之前" if i == 0 else ""
        print(f"  第 {i} 次  档位 {T._fx_level_name(T.FX_LEVEL[0]):>4}  "
              f"底噪={'on' if nz else 'off':>3}  footer {m.group(0) if m else '(无)':>12}{mark}")
        T._fx_cycle()


if __name__ == "__main__":
    main()
