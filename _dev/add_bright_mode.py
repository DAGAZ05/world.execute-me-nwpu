"""批：加一个 `--bright` 演示模式（大屏 / 投影时文字太淡）。

诊断（都是实测数值，不是感觉）：

* 界面"白"其实是 **UI = (200, 214, 234)** —— 只有 78% 亮度，而且偏蓝，投影下就读成浅灰；
* 副标题用 `ui(0.62)`，再乘一层 → 约 **(126, 133, 148)**，只剩一半亮度；
* 暗角把**角落压到 25%**（`VIG_FLOOR = 0.75`），扫描线再把每三行压到 **86%**；
* `UI_GAIN` 还会按镜头再乘一次（line 5228，每帧设）。

而且 `mix()` 把 level **夹在 [0,1]**，所以"加大增益"这条路走不通，只能**抬高源色**。

改法（不动美术，只动可读性）：

    TEXT_SRC = [UI]      ui() 从这个槽取源色；--bright 把它换成近白
    DIM_SCALE = [1.0]    暗角/扫描线的整体强度；--bright 把它调弱
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "player" / "_tools" / "tui_live.py"

JOBS = [
    # 1. 源色槽 + 压暗强度槽
    ('''UI_GAIN = [1.0]''',
     '''UI_GAIN = [1.0]

#: `ui()` 取源色的那个槽。**大屏/投影用的 `--bright` 只改这个槽**，不改 `UI` 常量本身
#: ——`UI` 还被别处直接引用（`s.put(..., UI)` 之类），改常量会牵动太多。
#: 为什么要有这个槽：`mix()` 把 level 夹在 [0, 1]（第 1749 行），所以"把增益加到 1 以上"
#: 是无效的，想让字更亮只有**抬高源色**这一条路。
TEXT_SRC = [UI]

#: 暗角与扫描线的整体强度倍数。`--bright` 把它压到 0.45：投影环境本身就有环境光，
#: 画面再自己压暗一层，边角的字就看不清了。
DIM_SCALE = [1.0]'''),

    # 2. ui() 改从槽里取源色
    ('''def ui(level: float):
    """`tuikit.amb(level)` - the film's plain UI colour through this frame's gain."""
    return mix(UI, level * UI_GAIN[0])''',
     '''def ui(level: float):
    """`tuikit.amb(level)` - the film's plain UI colour through this frame's gain.

    源色取自 `TEXT_SRC[0]`（默认就是 `UI`），`--bright` 会把它换成近白。
    """
    return mix(TEXT_SRC[0], level * UI_GAIN[0])'''),

    # 3. 暗角/扫描线乘上倍数
    ('''                out[y][x] = (1.0 - v * VIG_FLOOR * k) * scan''',
     '''                # `DIM_SCALE` 是 `--bright` 的旋钮：1.0 = 原样，0.45 = 投影模式
                _s = 1.0 - (1.0 - scan) * DIM_SCALE[0]
                out[y][x] = (1.0 - v * VIG_FLOOR * k * DIM_SCALE[0]) * _s'''),

    # 4. 命令行
    ('''    ap.add_argument("--no-fx", action="store_true",''',
     '''    ap.add_argument("--bright", action="store_true",
                    help="演示模式（大屏 / 投影）：界面文字换成近白，暗角与扫描线压到 45%，"
                         "并关掉余晖。起因是投影环境下 (200,214,234) 的\\"白\\"读起来发灰、"
                         "副标题只剩一半亮度。不改任何美术，只提可读性")
    ap.add_argument("--text-bright", type=float, default=None, metavar="K",
                    help="只调界面文字：K>1 把源色往纯白抬（1.0 = 原样，约 1.5 = 接近纯白）")
    ap.add_argument("--no-fx", action="store_true",'''),

    # 5. 生效
    ('''    if args.no_fx:
        FX.update(on=False, reveal=False, mech=False, trail=False, vig=False)''',
     '''    if args.bright:
        # 近白 + 压弱暗角/扫描线 + 关余晖（余晖会把上一帧的字又压暗一层）
        TEXT_SRC[0] = (247, 251, 255)
        DIM_SCALE[0] = 0.45
        FX.update(trail=False)
    if args.text_bright is not None:
        # 只动文字：把源色从 `UI` 朝纯白插值过去。`mix()` 夹 [0,1]，所以这里直接算颜色。
        k = max(1.0, min(3.0, float(args.text_bright)))
        f = min(1.0, (k - 1.0) / 0.7)
        TEXT_SRC[0] = tuple(int(c + (255 - c) * f) for c in UI)
    if args.no_fx:
        FX.update(on=False, reveal=False, mech=False, trail=False, vig=False)'''),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    t = P.read_text(encoding="utf8")
    apply = "--apply" in sys.argv
    ok = bad = 0
    for old, new in JOBS:
        if old in t:
            t = t.replace(old, new, 1)
            ok += 1
            print("  命中 %s…" % old.strip().split("\n")[0][:60])
        else:
            bad += 1
            print("  未命中 %s…" % old.strip().split("\n")[0][:60])
    print("\n命中 %d / 未命中 %d" % (ok, bad))
    if apply and bad == 0:
        P.write_text(t, encoding="utf8")
        print("已写入 %s" % P)


if __name__ == "__main__":
    main()
