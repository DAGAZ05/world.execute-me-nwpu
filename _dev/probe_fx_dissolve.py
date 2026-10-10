"""`--fx` 路径下的溶解：真的在改画面、不碰 CLEAR、而且**转场必须走完**。

`probe_dissolve.py` 验的是 `--dissolve` 那条老路。批 95 给 `--fx` 那条路加了
"强度也压缩出场顺序"（`_diss_aggr`），多了一个新的失败模式：
**压缩要是压过了头，转场结束时会有格子永远没切过去，屏幕上留下上一镜的半个画面。**
这个探针专门守它。

三条判据：
  1. 转场中段：改动格 > 0（开关接上了）；
  2. 落在 `CLEAR` 内的改动格 = 0（歌词条与左侧窗口不该被溶解）；
  3. **转场结束后**：画面与新镜头单独渲染的结果一致（残留 = 0）。

    python _dev/probe_fx_dissolve.py
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
    ap.add_argument("--at", type=float, default=66.0, help="一个真实转场的时刻")
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
    total = cols * rows
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()

    def set_triple(triple):
        T.FX_STRENGTH[0] = triple
        T.FX_BUNDLE[0] = T._fx_bundle(triple) if triple is not None else None
        T.FX_LEVEL[0] = 1.0
        T._fx_level_apply()

    def run(triple, frames, t0):
        """连跑 frames 帧（转场靠累积，必须同一块屏），返回 (逐帧快照, 逐帧的 CLEAR 列表)。"""
        set_triple(triple)
        T._CUT[0] = None                     # 强制从这一帧开始一次新转场
        s = T.Screen(cols, rows)
        sink = io.StringIO()
        snaps, clears = [], []
        for k in range(frames):
            t = t0 + k / T.FPS
            T.draw(s, data, eng, t, True, T.FPS)
            # **`CLEAR` 在 `draw` 开头就被清空、期间被填上，所以必须在这里读**
            # （第一版在 draw 之后才读，拿到的永远是空表，于是"落在 CLEAR 内"恒为 0，
            #  那条判据什么也没验）
            clears.append(list(T.CLEAR))
            s.render_diff(sink)
            snaps.append([row[:] for row in s.buf])
        return snaps, clears

    # 转场时长：CUT_DUR + CUT_CELL（见 draw 里 prog 的定义）
    dur = float(getattr(T, "CUT_DUR", 0.0)) + float(getattr(T, "CUT_CELL", 0.0))
    frames = int(dur * T.FPS) + 6
    print(f"转场 @{a.at}s，时长 {dur:.3f}s；跑 {frames} 帧（多跑几帧确保走完）")
    print()

    for label, triple in (("--fx 0.2,0.1,0.05", (0.2, 0.1, 0.05)),
                          ("--fx 1,1,1", (1.0, 1.0, 1.0)),
                          ("不给 --fx（对照：没有溶解）", None)):
        on, clears = run(triple, frames, a.at)
        off, _ = run(None, frames, a.at)
        mid = frames // 3
        d_mid = sum(1 for y in range(rows) for x in range(cols)
                    if on[mid][y][x] != off[mid][y][x])
        in_clear = 0
        rects = clears[mid]
        for (x0, y0, x1, y1) in rects:
            for y in range(max(0, y0), min(rows - 1, y1) + 1):
                for x in range(max(0, x0), min(cols - 1, x1) + 1):
                    if on[mid][y][x] != off[mid][y][x]:
                        in_clear += 1
        # 末帧：与**同一时刻**的关溶解帧比。两边都是同一帧号，所以时间一致——
        # 第一版拿"末帧"比"之后 0.5 秒"，那当然不同（画面本来就在动），判据是错的。
        last = on[-1]
        d_end = sum(1 for y in range(rows) for x in range(cols)
                    if last[y][x] != off[-1][y][x])
        print(f"=== {label} ===")
        print(f"  转场中段（第 {mid} 帧）改动格 {d_mid:5d}（{100 * d_mid / total:5.1f}%）"
              f"   CLEAR 矩形 {len(rects)} 个，落在 CLEAR 内 {in_clear}")
        print(f"  转场末帧（第 {frames - 1} 帧）与关溶解的**同一帧**不同 {d_end:5d} 格"
              f"（{100 * d_end / total:5.1f}%）  ← 应为 0：转场必须走完")
        print()

    print("读法：`落在 CLEAR 内` 必须为 0；`转场末帧不同` 必须为 0，")
    print("      否则说明压缩出场顺序压过了头，屏幕上会留下上一镜的半个画面。")


if __name__ == "__main__":
    main()
