"""One-shot: rewrite the left window's dialogue for coherence, and trim the rows the animation covers.

Two of the user's notes in one pass:

  * "对话问题：'我'的问题是根据歌词来的，但目前这样会显得上下文不连贯。你尝试在与歌词对照的情况下，让'我'与航小天的对话显得上下文连贯" - every question keeps the lyric it sits on and now *refers back* to what
    航小天 just said, and the answers that answered the wrong thing were fixed (1.33 asked about
    preparation and was told the school motto);
  * "航小天打篮球动图……位置放在左panel（覆盖会话框），时序位于歌词第一处 if I can if I can；其余受影响
    的内容删减或者与其他地方的融合一下" - the animation sits over the chat window from 58.65 for
    eleven and a half seconds, so the dialogue inside that window is *deleted*, and what was in it
    comes back as one merged line when the picture is gone.

Run once, from the project root:  python _dev/dialogue_patch.py
It prints every change and refuses to run if an anchor does not match what it expects, so a typo in this
table cannot silently rewrite a line the user wrote.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {"act1": ROOT / "player" / "_tools" / "school_lines.py",
         "act2": ROOT / "player" / "_tools" / "school_lines_act2.py"}
LINE = re.compile(r'^(\s*)\(([0-9.]+),\s*"((?:[^"\\]|\\.)*)",\s*"(\w+)",\s*"((?:[^"\\]|\\.)*)"\),\s*$')

# (time, role, the text that is there now, the text that should be) - the old text is checked.
PATCH: list[tuple[float, str, str, str]] = [
    # ---- P0: the opening. The question now says what it is looking at, and 1.33's answer answers the
    #      question that was asked instead of jumping to the motto (the motto moves to the `sub` line).
    (0.03, "user", "学长你好，我是西北工业大学的新生，请问……这里是从哪儿开始亮的？",
     "学长你好，我是今年刚入学的新生。这台机器……是从哪儿开始亮的？"),
    (1.33, "user", "那我需要提前准备什么吗？", "那我得先准备什么？"),
    (1.33, "ai", "三实一新。基础扎实、工作踏实、作风朴实、开拓创新。",
     "先做好防护 —— 静电手环、护目镜，一样都不能省。"),
    (1.33, "sub", "校训是公诚勇毅。这两句你会在每一面墙上看到。",
     "校训是公诚勇毅，作风是三实一新。两句话你会在每一面墙上看到。"),
    (3.58, "user", "这个是校徽吗？", "刚才亮起来的东西……是校徽吗？"),
    (5.16, "user", "那这所学校是怎么来的？", "1938 —— 那这所学校是怎么来的？"),
    (7.19, "user", "我要记住几个数？", "这所学校，我要记住几个数？"),
    # ---- "Initialization" now grows out of the four numbers instead of arriving from nowhere
    (9.75, "user", "「初始化」是什么意思？", "四个数我记住了。那 1938 年之前呢 —— 是空的吗？"),
    (9.75, "ai", "把一堆东西，变成「一个」东西。",
     "是空的。初始化就是把它填上 —— 把一堆东西，变成「一个」东西。"),
    (9.75, "sub", "数学上这件事先于学校。你迟早会遇到它。",
     "这四个数不是一开始就有的，是一年年填进来的。"),
    (10.90, "user", "那我们学校的世界是什么样子的？", "填上之后 —— 我们的世界是什么样子？"),
    (12.47, "user", "跑起来会怎么样？", "那让它跑起来，会怎么样？"),
    # ---- the campus half: each question picks the last answer up
    (33.01, "user", "启翔湖真的是圆的吗？", "那湖呢 —— 启翔湖真的是圆的吗？"),
    (36.77, "user", "飞机起飞是正弦吗？", "湖上是圆。那天上呢 —— 飞机起飞是正弦吗？"),
    (47.27, "user", "中间断过吗？", "那条线，中间断过吗？"),
    (54.74, "user", "「合」是什么意思？", "回到 1938 了。那「合」是什么意思？"),
    # ---- the chorus: 航小天 answers the four-year question with the animation, not with a sentence
    (58.65, "ai", "先给你每天要走的那些路。", "先给你看一段。看完你就知道了。"),
    (70.02, "user", "我们被困在哪儿？", "路也看完了。那我们被困在哪儿？"),
    (70.02, "ai", "秦岭和渭河之间。", "秦岭和渭河之间。你看到的那三条路、那只猫，都在这中间。"),
    (71.40, "user", "奇怪吗？", "四年都在这块地方 —— 奇怪吗？"),
    # ---- the "If I'm X" run is a *game* the student joins, which is what the song itself does
    (73.53, "user", "如果我是一根茄子呢？", "那我也学你 —— 如果我是一根茄子呢？"),
    (73.53, "ai", "那我就把营养给你。食堂的烧茄子，就是刚才那个。",
     "行，你学会了。那我把我有的都给你 —— 食堂的烧茄子，就是刚才那个。"),
    (84.60, "user", "「唯一」这件事，学校有吗？", "玩到这儿了 —— 「唯一」这件事，学校有吗？"),
    (88.34, "user", "学校改过名吗？", "那学校呢，改过名吗？"),
    (98.93, "user", "进哪儿？", "敲完那个字母 —— 进哪儿？"),
    (108.69, "user", "什么叫完整？", "你说要完整 —— 什么叫完整？"),
    # ---- act two
    (162.23, "user", "这些课到底在教什么？", "跑了这么多 —— 这些课到底在教什么？"),
    (169.61, "user", "那大三呢？", "那张图之后呢 —— 大三呢？"),
    (182.43, "user", "什么是依赖倒置？", "那我问一个真的 —— 什么是依赖倒置？"),
    (187.97, "user", "你是自由的吗？", "那你呢 —— 你是自由的吗？"),
]

# Rows whose whole block sits inside the animation's window (58.65-70.08) and is therefore covered by it.
# Everything else at those times - the `meta` rows - goes with them; the frame counter is not a message.
TRIM_BETWEEN = (58.66, 70.01)


def esc(text: str) -> str:
    """The file's own style: ASCII as itself, everything else as `\\uXXXX`."""
    return "".join(c if ord(c) < 128 else "\\u%04x" % ord(c) for c in text)


def main() -> None:
    changed = 0
    for tag, path in FILES.items():
        lines = path.read_text(encoding="utf8").splitlines(keepends=True)
        out, dropped = [], []
        for line in lines:
            m = LINE.match(line.rstrip("\n"))
            if not m:
                out.append(line)
                continue
            ind, t, lyric, role, text = m.groups()
            t = float(t)
            now = ast.literal_eval(f'"{text}"')
            if TRIM_BETWEEN[0] <= t <= TRIM_BETWEEN[1]:
                dropped.append(f"  - {t:7.2f} {role:5} {now[:44]}")
                changed += 1
                continue
            hit = [p for p in PATCH if abs(p[0] - t) < 1e-6 and p[1] == role]
            if not hit:
                out.append(line)
                continue
            _t, _role, old, new = hit[0]
            if now != old:
                print(f"ANCHOR MISMATCH in {tag} at {t} {role}:\n  file: {now!r}\n  table: {old!r}")
                raise SystemExit(1)
            print(f"  ~ {t:7.2f} {role:5} {old[:40]}\n            -> {new[:60]}")
            out.append(f'{ind}({t:g}, "{lyric}", "{role}", "{esc(new)}"),\n')
            changed += 1
            PATCH.remove(hit[0])
        path.write_text("".join(out), encoding="utf8")
        if dropped:
            print(f"{tag}: dropped {len(dropped)} row(s) inside the animation's window")
            print("\n".join(dropped))
    if PATCH:
        print("UNUSED PATCH ENTRIES:")
        for p in PATCH:
            print("  ", p[0], p[1], p[2][:40])
        raise SystemExit(1)
    print(f"\n{changed} row(s) changed")


if __name__ == "__main__":
    main()
