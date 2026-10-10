"""心形到底有没有空洞和凹陷？—— 用"封闭空洞计数"当判据，而不是看图。

用户对心形的两条意见来自参考仓库的提示词文档：

  * 第 21 条「这些❤️不要有这种空洞」；
  * 第 22/24 条「是这个部分，有三个」/「后面这里也有三个凹陷」。

"空洞"和"凹陷"在字符网格上是可以精确定义的，所以这个探针不靠眼睛：

  1. **封闭空洞**：一个空格的**四邻都是填充格**（或在同一行/列被填充格夹住），
     它就是填充内部的一个洞。实心图形里这种格应当为 0。
  2. **外圈连通性**：从图形包围盒外面做一次洪水填充，凡是**到不了**的空格且不是图形内部，
     就是被围住的洞。
  3. **顶部凹陷深度**：心形顶部两个圆瓣之间的凹口（cusp）。太深就是"凹陷"而不是心形的凹口。
     量法是"从包围盒顶行往下,每行最左与最右填充格之间有多少空格"——
     凹口越深，前几行的空白跨度越大。

三个判据都只依赖最终缓冲里的字符，所以对"图形怎么画出来的"完全无关。

    python _dev/probe_heart.py
    python _dev/probe_heart.py --sizes 14x6,20x9,28x12
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def analyse(rows: list) -> dict:
    """`rows` 是字符串列表（只看填充/空格）。返回三个判据的读数。"""
    h = len(rows)
    w = max((len(r) for r in rows), default=0)
    grid = [list(r.ljust(w)) for r in rows]

    def filled(x, y):
        return 0 <= x < w and 0 <= y < h and grid[y][x] != " "

    cells = [(x, y) for y in range(h) for x in range(w) if filled(x, y)]
    if not cells:
        return dict(n=0, bbox=None, enclosed_holes=-1, four_neighbour_holes=-1,
                    top_notch=0, holes=[])
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)

    # 1) 四邻皆填的空格 —— 填充内部的洞
    four = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)
            if not filled(x, y)
            and filled(x - 1, y) and filled(x + 1, y)
            and filled(x, y - 1) and filled(x, y + 1)]

    # 2) 从包围盒外做洪水填充，到不了的空格 = 被围住的洞
    pad = 2
    pw, ph = w + pad * 2, h + pad * 2
    outside = [[grid[y][x] == " " if (0 <= x < w and 0 <= y < h) else True
                for x in range(-pad, w + pad)] for y in range(-pad, h + pad)]
    seen = [[False] * pw for _ in range(ph)]
    stack = [(0, 0)]
    while stack:
        sx, sy = stack.pop()
        if not (0 <= sx < pw and 0 <= sy < ph) or seen[sy][sx] or not outside[sy][sx]:
            continue
        seen[sy][sx] = True
        stack.extend(((sx + 1, sy), (sx - 1, sy), (sx, sy + 1), (sx, sy - 1)))
    holes = []
    for y in range(ph):
        for x in range(pw):
            if outside[y][x] and not seen[y][x]:
                gx, gy = x - pad, y - pad
                if 0 <= gx < w and 0 <= gy < h:
                    holes.append((gx, gy))

    # 3) 顶部凹口：前几行"两端填充之间的空格跨度"
    notch = 0
    for y in range(y0, min(y1, y0 + 4) + 1):
        row = [x for x in range(x0, x1 + 1) if filled(x, y)]
        if len(row) >= 2:
            gap = 0
            for x in range(row[0], row[-1] + 1):
                if not filled(x, y):
                    gap += 1
            notch = max(notch, gap)
    return dict(n=len(cells), bbox=(x0, y0, x1, y1), enclosed_holes=len(holes),
                four_neighbour_holes=len(four), top_notch=notch, holes=holes)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", default="10x5,14x7,20x9,28x13,40x18")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    import school_motifs as M

    print(f"曲线自身范围：x ∈ [{-M.HEART_X_MAX:.1f}, {M.HEART_X_MAX:.1f}]，"
          f"y ∈ [{M.HEART_Y_MIN:.1f}, {M.HEART_Y_MAX:.1f}]（非对称：尖端只到 +12）")
    print(f"曲线比例 高:宽 = {M.HEART_RATIO:.4f}；格子的高宽比 _CA = {M._CA}")
    print(f"因此正确的格子框比例 h/w = HEART_RATIO/_CA = {M.HEART_RATIO / M._CA:.4f}")
    print()
    print(f"{'尺寸':>8} {'填充格':>7} {'封闭空洞':>9} {'四邻空洞':>9} {'顶部凹口':>9}")
    bad = 0
    for spec in a.sizes.split(","):
        w, h = (int(v) for v in spec.lower().split("x"))
        cells = M.heart_cells(w, h)
        rows = []
        for y in range(h):
            rows.append("".join("#" if (x, y) in cells else " " for x in range(w)))
        r = analyse(rows)
        flag = ""
        if r["enclosed_holes"] or r["four_neighbour_holes"]:
            flag = "  <== 有洞"
            bad += 1
        print(f"{spec:>8} {r['n']:7d} {r['enclosed_holes']:9d} "
              f"{r['four_neighbour_holes']:9d} {r['top_notch']:9d}{flag}")
        if r["holes"]:
            print(f"         洞的位置：{r['holes'][:12]}")
    print()
    # 打印最大的那个，肉眼看形状对不对（在终端里能直接看）
    # 用一个**高**的框（宽 26 格、高 22 格），因为格子高宽比 2.1，形状才不会被压扁
    cells = M.heart_cells(26, 22)
    print("26x22 的实际形状（宽 26 格、高 22 格 = 形状的真实比例）：")
    for y in range(22):
        print("   " + "".join("\u2588" if (x, y) in cells else "\u00b7" for x in range(26)))
    print()
    # 朝向判据：**第一个非空行**的填充格数应当明显小于最宽行（两个瓣），
    # 而最后一行应当很窄（尖头）。**不能用"第 0 行"**：图形在框里是居中摆放的，
    # 顶部本来就可能有一到几行空白（第一版就是这么误报 FAIL 的）。
    def nz(y):
        return sum(1 for x in range(26) if (x, y) in cells)

    counts = [nz(y) for y in range(22)]
    first_nz = next((y for y, c in enumerate(counts) if c), None)
    last_nz = next((y for y in range(21, -1, -1) if counts[y]), None)
    wmax = max(counts) if counts else 0
    print(f"第一个非空行 = 第 {first_nz} 行（{counts[first_nz]} 格），"
          f"最宽行 {wmax} 格，最后一行 = 第 {last_nz} 行（{counts[last_nz]} 格）")
    orient_ok = bool(
        first_nz is not None and last_nz is not None and wmax
        and counts[first_nz] < 0.75 * wmax      # 顶部不是圆冠：两个瓣各自窄
        and counts[last_nz] <= 0.35 * wmax      # 底部收成尖头
        and counts[first_nz] < counts[last_nz] * 3.5
    )
    print(f"  朝向（顶部两个瓣、底部尖头）：{'PASS' if orient_ok else 'FAIL'}")
    print()
    if bad:
        print(f"FAIL —— {bad} 个尺寸有空洞。")
        raise SystemExit(1)
    if not orient_ok:
        print("FAIL —— 心形朝向不对（凹口不在上面）。")
        raise SystemExit(1)
    print("PASS —— 所有尺寸都没有封闭空洞，也没有四邻皆填的空格；顶部两个瓣、底部尖头。")


if __name__ == "__main__":
    main()
