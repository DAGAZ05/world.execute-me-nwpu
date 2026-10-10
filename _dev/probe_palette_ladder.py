"""噪点该调多暗？—— 用**项目自己的调色板步进**来定，不凭空挑一个数。

用户的诉求是"把噪点的颜色调暗"。`_dev/probe_noise_bright.py` 量出现状：

    背景 BG luma 6.9 · 正文 UI luma 212.5
    噪点最亮的一格 luma 73.3 = 正文的 34.5%

"34.5%"就是"太亮"的量化形式。而要挑一个更暗的值，最好别拍脑袋——
这个项目已经有一套自己的明暗层次（`UI` / `ME_TEXT` / `ME_MID` / `ME_HI` / `mix()`），
所以先把它列出来，再看"噪点应该落在哪一级"。

    python _dev/probe_palette_ladder.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")


def luma(c) -> float:
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import tui_live as T

    print("=== 项目自己的调色板（按亮度排序）===")
    seen = {}
    for n in dir(T):
        if not n.isupper() or n.startswith("_"):
            continue
        v = getattr(T, n)
        if isinstance(v, (list, tuple)) and len(v) == 3 and all(isinstance(x, int) for x in v):
            seen[n] = tuple(v)
    ui_l = luma(T.UI)
    for n, v in sorted(seen.items(), key=lambda kv: luma(kv[1])):
        print(f"  {n:<12} {str(v):<20} luma {luma(v):6.1f}   正文的 {100 * luma(v) / ui_l:5.1f}%")

    print()
    print("=== `mix(colour, k)` 给出的连续层次 ===")
    for src_name in ("UI", "ME_TEXT", "ME_HI"):
        src = getattr(T, src_name, None)
        if src is None:
            continue
        print(f"  mix({src_name}, k):")
        for k in (0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25, 0.30):
            c = T.mix(src, k)
            print(f"    k={k:4.2f}  {str(c):<18} luma {luma(c):6.1f}  正文的 {100 * luma(c) / ui_l:5.1f}%")

    print()
    print("=== 噪点基色换算 ===")
    base = (120, 150, 190)
    print(f"  当前基色 {base} luma {luma(base):.1f}；实测最亮格是基色的 0.5 倍"
          f"（(60,75,95)），因为 `k = v * level` 而 v 的峰值约 0.5。")
    print("  所以'最亮格'的亮度 ≈ 基色 × 0.5。要让最亮格落到某个目标，")
    print("  基色的目标 = 目标亮度 / 0.5。")
    for frac in (0.30, 0.25, 0.20, 0.15, 0.12):
        target = ui_l * frac
        need = target / 0.5
        # 按比例缩基色，保持色相
        scale = need / luma(base)
        c = tuple(int(v * scale) for v in base)
        print(f"  正文的 {frac * 100:4.1f}%  (luma {target:5.1f})  ->  基色 ≈ {str(c):<18} "
              f"（现基色的 {scale:.2f} 倍）")


if __name__ == "__main__":
    main()
