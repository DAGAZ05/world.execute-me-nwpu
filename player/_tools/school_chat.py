"""The school variant's dialogue: what the left window holds, minute by minute.

The film's window is `dsh_text.at(t)`, which reads the film's own per-frame DOM back out of a cache.
Nothing like that exists for this variant - the conversation was written for it - so this module is
the *authority* instead of a reader, and it has to answer the same question the film's cache does:

    dsh_window(t) -> (avatar, theme, [(role, text)])

`role` is the film's own vocabulary (see `film_panels`/`dsh_text._role_of` and `tui_live._dsh_rows`,
which is the layout that consumes it):

    name       the character's name, drawn next to the avatar
    state      the status line under it ("在线上")
    user       a right-aligned bubble: the student
    ai         a bare left-aligned line: 航小天
    sub        an indented line under an ai line
    meta       a right-aligned timestamp / elapsed time
    card       a "▸ ..." bullet
    err        a red system line
    code       monospace, no wrap

Two things this module owns that the film did not have to think about:

  * **The avatar is not a file.** The film names a PNG per frame (`avatars/b/01435.png`); here the
    field carries the *expression name* and `tui_live.draw_dsh` hands it to `mascot_glyphs`. The
    vocabulary is `mascot_glyphs.EXPRESSIONS`.
  * **The expression follows the lyrics, not the line being spoken.** `tui_live` is free to draw a
    line whose answer arrives a beat later; the expression is chosen per *shot* in `speed_plan`
    below, so the face never flickers between two lines of the same exchange.
"""
from __future__ import annotations

from bisect import bisect_right

# the school's own page theme: the film re-themes itself per chapter and the window follows
# (`dsh_text.theme_of` returns (bg-base, brand-primary, border-l1)). 航小天's palette: a cold navy
# page, the school-blue accent, a low-contrast border. The accent is *not* the film's 大肥鱼 blue -
# ME_TEXT stays the film's, and nothing in this variant pretends the two are the same character.
THEME = ("#070d1c", "#5a86d8", "#1d2c4a")

NAME = "航小天"
STATE = "在线上"


def _x(role: str, text: str) -> tuple[str, str]:
    return (role, text)


# --------------------------------------------------------------------------- the conversation
#
# Written against `03_批次设计/batch_01.md`, one entry per lyric line, in the order the lyrics
# arrive. `t` is the time the *answer* lands - the student's question is placed a little before it,
# so the line is being read when the word is sung. Times come from `input/lyrics.lrc`.
#
# The blank second element of the two-tuples below is the lyric line the exchange belongs to; it is
# kept beside the entry rather than in it because `dsh_window` must return the film's own two-tuple
# shape. It is there for whoever reads this file next, not for the layout.
#
# 00:00.03 - 00:30.89 is written here; the rest of the song is in `school_dialogue.SECOND_HALF`,
# chained below. The split is size, not structure: `DIALOGUE` is the whole song either way, and
# `_DIALOGUE` is what every function in this file reads.

DIALOGUE: list[tuple[float, str, list[tuple[str, str]]]] = [
    (0.03, "Switch on the power line", [
        _x("user", "学长，软件学院大一，报到了。还没开学，我先给板子通上电。"),
        _x("ai", "欢迎来到西北工业大学。长安校区，东祥路 1 号。"),
        _x("ai", "你手上那块是 UNO，插上 USB 就能亮 —— 但你得先把电源线接对。"),
        _x("meta", "用时 0.4 秒"),
        _x("meta", "00:01"),
    ]),
    (1.33, "Remember to put on protection", [
        _x("user", "接线之前要注意什么吗？"),
        _x("ai", "防静电。手环接地，别摸金手指。"),
        _x("sub", "这条不是客套 —— 你上学期会亲手拆掉至少一块板子。"),
        _x("meta", "用时 1.1 秒"),
        _x("meta", "00:02"),
    ]),
    (3.58, "Lay down your pieces", [
        _x("user", "好。那我现在手上有哪些东西？"),
        _x("ai", "一块 UNO、一个超声波模块、一个红外测距、一块 LCD1602、一块面包板、若干杜邦线。"),
        _x("ai", "先把它们摆好，别急着插。"),
        _x("meta", "用时 1.6 秒"),
        _x("meta", "00:05"),
    ]),
    (5.16, "And let's begin object creation", [
        _x("user", "摆好了。然后呢？写代码？"),
        _x("ai", "先别写。想一想你要造的是什么。"),
        _x("sub", "软件工程的第一课不是敲键盘，是决定「世界上有哪些东西」。"),
        _x("code", "class World(UNO):"),
        _x("code", "    sensors = [Ultrasonic, Infrared]"),
        _x("code", "    display = LCD1602"),
        _x("meta", "用时 2.0 秒"),
        _x("meta", "00:07"),
    ]),
    (7.19, "Fill in my data parameters", [
        _x("user", "参数填什么？"),
        _x("ai", "填真的。别写 foo、bar。"),
        _x("sub", "你写进去的每一个数，将来都要能对上现实。"),
        _x("code", "name     = \"西北工业大学\""),
        _x("code", "campus   = \"长安校区 · 东祥路1号\""),
        _x("code", "founded  = 1938"),
        _x("code", "colleges = 24"),
        _x("meta", "用时 2.3 秒"),
        _x("meta", "00:09"),
    ]),
    (9.75, "Initialization", [
        _x("user", "初始化到底在做什么？"),
        _x("ai", "把刚才那堆东西，变成「一个」东西。"),
        _x("sub", "数学上这件事叫权重初始化。你大一会遇到它：He 初始化，方差 2/n。"),
        _x("meta", "用时 1.1 秒"),
        _x("meta", "00:10"),
    ]),
    (10.90, "Set up our new world", [
        _x("user", "那我们的世界是什么样子的？"),
        _x("ai", "三个旋臂。航空、航天、航海。"),
        _x("sub", "这不是比喻 —— 你走在校园里，抬头就是这三样东西。"),
        _x("meta", "用时 1.5 秒"),
        _x("meta", "00:12"),
    ]),
    (12.47, "And let's begin the simulation", [
        _x("user", "跑起来会怎么样？"),
        _x("ai", "会先跑很久什么都不发生。这很正常。"),
        _x("sub", "仿真最耗人的不是算，是等。"),
        _x("meta", "用时 0.8 秒"),
        _x("meta", "00:13"),
    ]),
    # ---------------------------------------------------------------- the gap (no lyrics)
    # 12.47 - 29.28 s is the film's first instrumental gap and this variant's first silence. Rule R2
    # of batch 1: a gap is 航小天 talking alone, and what he talks through is a *list* - here the
    # whole four years, printed a line at a time. It is the one place the audience is allowed to read
    # an entire curriculum before the lyrics start pushing the picture around.
    (14.00, "[gap] 四年课表", [
        _x("ai", "趁它跑，我说一下这四年的安排。"),
        _x("code", "大一   嵌入式电子微系统        程序设计（C）"),
        _x("code", "大二   软件工程               面向对象"),
        _x("code", "      计算机网络             计算机操作系统"),
        _x("code", "      计算机组成原理          数据库"),
        _x("code", "大三   软件项目管理            软件测试"),
        _x("code", "      深度学习               工业模型"),
        _x("code", "      大型工业软件"),
        _x("ai", "你会觉得它很长。它确实很长。"),
        _x("meta", "用时 2.3 秒"),
        _x("meta", "00:14"),
    ]),
    (29.28, "If I'm a set of point", [
        _x("user", "学长，我问个可能有点蠢的问题。"),
        _x("user", "这些数学，到底有什么用？"),
        _x("ai", "不蠢。这是这四年最该问的问题。"),
        _x("ai", "如果我是点集，我就把维数给你。"),
        _x("meta", "用时 1.9 秒"),
        _x("meta", "00:29"),
    ]),
    (30.89, "Then I will give you my dimension", [
        _x("ai", "维数。"),
        _x("ai", "一个点没有长度，但一堆点可以有一维、二维、三维。"),
        _x("sub", "你将来写图形程序，第一件事就是决定你有几维。"),
        _x("meta", "用时 1.2 秒"),
        _x("meta", "00:31"),
    ]),
]

# --------------------------------------------------------------------------- the whole song
#
# The two acts, chained here from the *flat* row files. The earlier `school_dialogue*` modules (with
# their `_x(..)` blocks) are superseded: stacking `_x(..)` calls one per line with a comma only on the
# first makes Python read `_x(a)(b)`, so the data silently became 4-tuples and the window raised on the
# first frame. `school_lines*` keeps time / lyric / who / text as four separate strings, which cannot be
# mis-parenthesised.
import school_lines as _L1                # noqa: E402
import school_lines_act2 as _L2           # noqa: E402


def _blocks(rows: list[tuple[float, str, str, str]]) -> list[tuple[float, str, list[tuple[str, str]]]]:
    """Fold flat rows into the `(time, lyric, [(role, text)])` shape the window reads.

    Consecutive rows with the same `(time, lyric)` are one exchange, in order; a `meta` row holds its
    two cells joined by `|` and is split back into two `meta` lines here, because they are two rows of
    the same right-aligned column and the layout draws them separately.
    """
    out: list[tuple[float, str, list[tuple[str, str]]]] = []
    for t, lyric, who, text in rows:
        if who == "meta":
            items = [("meta", p) for p in text.split("|")]
        else:
            items = [(who, text)]
        if out and out[-1][0] == t and out[-1][1] == lyric:
            out[-1][2].extend(items)
        else:
            out.append((t, lyric, items))
    return out


_DIALOGUE: list[tuple[float, str, list[tuple[str, str]]]] = (
    _blocks(list(_L1.ACT_ONE)) + _blocks(list(_L2.ACT_TWO))
)

# --------------------------------------------------------------------------- expression plan
#
# The face is driven by the *lyric's* emotional curve (`01_歌词分析.md` §4), not by the line being
# typed, and the plan changes on the beats that curve names, never mid-sentence. Each row is
# (from_seconds, expression); the last row at or before t wins, so the final row covers to the end.
#
# The mapping is deliberately coarse. The pane's portrait is 24x12 samples at best and the *chat
# avatar* is the same figure at 24x12 cells, so an expression is legible mainly through whether the
# eyes are open, closed or level - which is what this table varies, and why there are six changes in
# three and a half minutes rather than one per line.
EXPRESSION_PLAN: list[tuple[float, str]] = [
    (0.00, "normal"),      # P0 开机 - he is stating facts
    (10.90, "proud"),      # "Set up our new world" - the three arms
    (12.47, "normal"),     # the gap; he is describing the campus
    (29.28, "serious"),    # P1 定义 - "if I'm a set of point", the question that matters
    (47.27, "normal"),     # P2 电与时间 - the school's own history
    (49.11, "happy"),      # "So dizzy" - the library at night
    (58.65, "happy"),      # P3 副歌一 - campus life
    (73.53, "happy"),      # P4 万物皆点 - eggplant, tomato, tabby cat
    (84.60, "proud"),      # the firsts, 总师摇篮
    (88.34, "flat"),       # P5 互换 - the name changes, delivered deadpan
    (103.03, "normal"),    # P6 副歌二
    (110.40, "worried"),   # "You have left" x5 - the emotional floor of the song
    (115.60, "worried"),   # ...through "in isolation"
    (125.33, "serious"),   # P7a 控诉 - "Challenging your God"
    (130.74, "serious"),   # "Illegal arguments" - the error, and the gate
    (138.00, "normal"),    # act two: the four years
    (147.52, "serious"),   # P7b 处决 - the curriculum arrives whether he is ready or not
    (162.23, "serious"),   # P7c 副歌三 - the price has changed
    (176.96, "happy"),     # P8 LOVE - "I've studied how to properly love"
    (184.33, "proud"),     # "the algebraic expression of lo-o-ove"
    (187.97, "shy"),       # "you are free / I am trapped" - the one place he looks away
    (193.46, "normal"),    # the closing silence
]


def expression_at(t: float) -> str:
    keys = [k for k, _ in EXPRESSION_PLAN]
    return EXPRESSION_PLAN[max(0, bisect_right(keys, t) - 1)][1]


# --------------------------------------------------------------------------- the window at t

SPAN_FROM = 0.0                    # the window is on screen for the whole song in this variant
SPAN_TO = 211.9


def inside(t: float) -> bool:
    """Is the left pane holding the chat window at t.

    The film's own rule is a list of spans that dodge two moments (`GONE`/`BACK`, where the page is
    taken apart to a single caret). This variant has no such moment: the window is where the whole
    story is, so it is always on.
    """
    return SPAN_FROM <= t < SPAN_TO


def window(t: float) -> tuple[str, tuple[str, str, str], list[tuple[str, str]]]:
    """`(expression, theme, items)` - the school window at t, exactly the film's own shape.

    Items accumulate: everything whose time has come is in the list, in order, and the layout shows
    the tail of it the way a chat does. That is `dsh_text`'s behaviour too (each frame carries the
    body forward), so `_dsh_rows` needs no special case for this variant.

    One thing is *not* accumulated: while the college gate is holding the song (02:11.9-02:27.5), the
    question and its option list are appended after the timeline, because the gate is a live dialogue
    with the viewer rather than a line the conversation already contained. `school_gate` owns that
    block; this module only places it.

    Only while it *holds*, though, and not merely once the gate's lyric has gone by: the gate answers
    itself on a seek (`school_gate.tick(seeking=True)`), and if this appended the block whenever the
    playhead was past 02:11.9 then every frame from there to the end of the song would carry a question
    that has already been answered. On a verified run the block is therefore never in the window, which
    is why `_dev/school_shot.py` resets the gate before rendering.
    """
    # everything whose time has come, then the last 40 entries of *that*: the window shows a chat's
    # tail, so there is no reason to wrap 300 rows every frame when `_dsh_rows` will throw all but the
    # last screenful away. Slicing before the filter instead of after is what made the window empty
    # for the first half of the song - the "last 40" were all still in the future.
    live = [e for e in _DIALOGUE if e[0] <= t]
    items: list[tuple[str, str]] = [("name", NAME), ("state", STATE)]
    for _when, _tag, block in live[-40:]:
        # the header is not part of a block: `_dsh_rows` skips `name`/`state` and `draw_dsh` places
        # them by hand, so a block that carried them would be describing the panel, not the chat
        items.extend((r, x) for r, x in block if r not in ("name", "state"))
    try:
        import school_gate as _G
        # The gate is **not** drawn here, and that is the fix for the last of its three bugs. It used to
        # be appended to this list, and this list is a chat: the window shows the tail of it, so the
        # option list was pushed off the bottom by the lines that followed (the question was in the
        # buffer and not on the screen), and when it did fit it stayed on screen after the gate had
        # closed, because the accumulated items never go away. The gate now owns its own full-screen
        # panel (`school_gate.overlay`) and this window only carries the dialogue around it.
        pass
    except Exception:
        pass
    return expression_at(t), THEME, items


def check_coverage() -> list[str]:
    """Every lyric line must be handled; returns the ones that are not.

    `01_歌词分析.md` counts 82 timed lyric lines and 3 instrumental gaps. A line is *handled* either
    by having its own exchange or by being the second half of a pair, and the second case is a rule
    rather than a list because the song makes the rule: **every** unhandled line in the whole record
    begins with `To ` or `Then ` - `To AC, to DC`, `Then I will give you my circumference`,
    `Then you can be my limitations`. These are the completions of `Switch my current` and of
    `If I'm a circle`, split across two lyric rows by the melody and by nothing else; giving each its
    own entry would print the answer before the question is finished. The window prints them under
    the entry that opened the pair, which is what the singer is doing too.

    The third case is `COVERED_BY_PICTURE`: lines whose window is filled by the basketball animation
    instead of by text (the user: "其余受影响的内容删减或者与其他地方的融合一下"). Those rows were
    *deleted*, not moved - the picture is over the window for all eleven seconds of them - and what they
    said comes back in one merged line when the picture is gone ("你看到的那三条路、那只猫，都在这中间").
    They are named here rather than dropped from the check, so the film still accounts for every line.
    """
    import re
    lrc = ROOT_LRC
    if not lrc.exists():
        return ["(no lyrics.lrc to check against)"]
    lines = [ln.split("]", 1)[1].strip() for ln in lrc.read_text(encoding="utf-8-sig").splitlines()
             if re.match(r"^\[\d+:\d+", ln)]
    lines = [ln for ln in lines if ln]
    have = {tag for _t, tag, _b in _DIALOGUE}
    return [ln for ln in lines
            if ln not in have and ln not in COVERED_BY_PICTURE
            and not ln.startswith(("To ", "Then "))]


# The four lines of the first chorus, which the animation covers: see `check_coverage`.
COVERED_BY_PICTURE = frozenset((
    "Give you all the simulations",
    "Be your only satisfaction",
    "If I can make you happy",
    "I will run the execution",
))


from pathlib import Path as _P            # noqa: E402

# the song's own lyric file, for the coverage check below. `player/input/lyrics.lrc` - `parents[1]`
# is `player/`, which is where `input/` sits.
ROOT_LRC = _P(__file__).resolve().parents[1] / "input" / "lyrics.lrc"
