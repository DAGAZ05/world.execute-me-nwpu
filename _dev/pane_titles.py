"""生成"每个动画框的抬头 / 副标题 / 对应歌词"对照表（清单2 第 14 条）。

**用整帧渲染读真实的抬头**，不做静态推断：抬头是 `_kit(...)` 的 title 或 `k.section(...)`，
两者都可能来自 pane 内部、`pane_exchange` 的 TITLE 表、或钉子替换过的行，
静态分析容易读到"代码里写了但那一行没跑到"的那个。渲染出来的是**观众真看到的那一行**。

    python _dev/pane_titles.py            # 写到 动画框抬头对照表.md
    python _dev/pane_titles.py --print    # 只打到标准输出
"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_panels as SP   # noqa: E402
import tui_live as T         # noqa: E402

OUT = ROOT / "动画框抬头对照表.md"


def boot():
    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    d, eng = T.Data(), T.Engine()
    return d, eng


def header_at(d, eng, t, row_at):
    """把这一行演到 `t`，读右侧动画框里"副标题"与"框内小标题"两行。

    **布局不写死行号**（不同 pane 的抬头行不一样，实测 `pane_protection` 就不在 10 行），
    改成在 2-26 行里按**形状**找：

      * 副标题 = 第一行含 `▏` 的（`draw_pane` 的抬头标记）；
      * 框内小标题 = 第一行形如 `─── 文字 ───` 的（`k.section` 画的那条带标题的横线）。

    第一版只扫 9-18 行、并且"以 `──` 开头就当小标题"，于是抓到了画面里的装饰横线
    （`pane_power_on` 那一行整行都是字符画）、也漏掉了抬头在别处的行。按形状找之后就稳了。
    """
    T.fx_clear(T.Screen(197, 52))
    s = T.Screen(197, 52)
    sink = io.StringIO()
    # 回看**不超过行首**：短行（0.6 s）按中点采样时 `t - 0.6` 已经退到**上一行**去了，
    # 读到的抬头是上一格的。这里把回看限制在这行已经演过的时长之内。
    back = min(0.6, max(0.05, t - row_at))
    for k in range(int(back * 24)):
        T.draw(s, d, eng, t - back + k / 24.0, True, 24.0)
        s.render_diff(sink)
    x0, _, x1, _ = T.PANE_BOX
    sub, sect = "", ""
    for y in range(2, 27):
        bare = "".join(s.buf[y][x][0] or " " for x in range(x0, x1 + 1)).strip()
        if not bare:
            continue
        if not sub and "\u258f" in bare:
            sub = bare.split("\u258f", 1)[1].strip()
        if not sect:
            # `── 标题 ──…`：两边是连续横线、中间夹着非横线的文字
            core = bare.strip("\u2500 ")
            if core and bare.startswith("\u2500\u2500") and core != bare:
                dash = sum(1 for c in bare if c == "\u2500")
                if dash >= 6 and dash > len(bare) * 0.4:
                    sect = core
    return sub, sect


def main() -> None:
    d, eng = boot()
    rows = [r for r in SP.shot_rows() if r.get("name")]
    out = ["# 动画框抬头对照表（清单2 第 14 条，当前状态）", "",
           "由 `_dev/pane_titles.py` **渲染**生成：把每一行演到它的中点，读出动画框里真实出现的",
           "**副标题**（第 10 行 `▏ …`）与**框内小标题**（`── … ──`）。表格按时间排。", "",
           "| 时刻 | 对应歌词 | 动画框 | 框内小标题 | 副标题（抬头） | ops |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        # **75% 处采样**（批 167）：中点常常正赶上转场（二进制雨 / 色块盖住抬头行），
        # 那时读到的"标题"其实是那一行上别的内容的碎片。
        t_s = r["at"] + (r["end"] - r["at"]) * 0.75
        sub, sect = header_at(d, eng, t_s, r["at"])
        args = r.get("args") or {}
        pane = r["name"] + (("(" + ",".join("%s=%s" % kv for kv in args.items()) + ")")
                            if args else "")
        ops = " · ".join(r.get("ops") or [])
        out.append("| %.2f–%.2f | %s | `%s` | %s | %s | %s |"
                   % (r["at"], r["end"], (r.get("lyric") or "").replace("|", "/"),
                      pane, sect or "—", sub or "—", ops))
    text = "\n".join(out) + "\n"
    if "--print" in sys.argv:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        print(text)
    else:
        OUT.write_text(text, encoding="utf8")
        print("wrote %s  (%d rows)" % (OUT, len(rows)))


if __name__ == "__main__":
    main()
