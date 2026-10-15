"""批 174：按用户反馈修 6 处抬头。

用户报的：
  1. 两个时间线抬头没生效        -> `THEME_PINS` 覆盖了排期行的 sub（我上一批改错了地方）
  2. `2^53` 那处抬头仍是 MEMORY  -> 抬头 = pane 自己的标题 + 行的 sub，**标题**也要改
  3. 学院部分抬头重复（`特征图 · 特征图`）  -> 钉子的 sub 与排期行的 sub 都出镜
  4. `软件项目管理 / 软件开发综合训练` 重了 2 次
  5. 茄子 `消耗` -> `消化`
  6. 多余空格（`VCC` / `5V` / `class` / `444/472/503` 前）
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "player" / "_tools" / "school_panels.py"
S = ROOT / "player" / "_tools" / "school_scenes.py"


def esc(s: str) -> str:
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif o < 128:
            out.append(ch)
        elif o <= 0xFFFF:
            out.append("\\u%04x" % o)
        else:
            out.append("\\U%08x" % o)
    return "".join(out)


#: (文件, 正则, 替换, 说明)。正则用**源码里的 `\uXXXX` 转义形态**匹配，避免编码歧义。
JOBS = [
    # 1. 两个时间线的钉子 —— 抬头真正出镜的地方
    (P, r'\(50\.95, "pane_exchange", "timeline", "[^"]*"\)',
     '(50.95, "pane_exchange", "timeline", "%s")' % esc("\u5982\u679c\u80fd\u56de\u52301938"),
     "钉子 50.95 timeline 的 sub"),
    (P, r'\(52\.99, "pane_exchange", "timeline", "[^"]*"\)',
     '(52.99, "pane_exchange", "timeline", "%s")' % esc("\u4ece\u53e4\u90fd\u56de\u7738\u5f80\u4e8b\u6570\u5343\u5e74"),
     "钉子 52.99 timeline 的 sub"),
    # 5. 茄子：消耗 -> 消化
    (P, r'\\u6d88\\u8017', '\\u6d88\\u5316', "茄子：消耗 -> 消化"),
    # 6. 多余空格
    (P, r'\\u518d\\u901a  VCC \\u4e0e  5V', '\\u518d\\u901a VCC \\u4e0e 5V', "再通 VCC 与 5V 的重复空格"),
    (P, r'\\u5199\\u4e0b  class', '\\u5199\\u4e0b class', "写下 class 的重复空格"),
    (P, r'\\u756a\\u8304\\u5438\\u6536  444', '\\u756a\\u8304\\u5438\\u6536 444', "番茄吸收 444 的重复空格"),
]


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    cache: dict[Path, str] = {}
    for path, pat, new, why in JOBS:
        text = cache.get(path) or path.read_text(encoding="utf8")
        m = re.search(pat, text)
        if m is None:
            print("  未命中  %s" % why)
            continue
        text = text[:m.start()] + new + text[m.end():]
        cache[path] = text
        print("  命中    %s" % why)
    if "--apply" in sys.argv:
        for path, t in cache.items():
            path.write_text(t, encoding="utf8")
        print("已写入 %d 个文件" % len(cache))


if __name__ == "__main__":
    main()
