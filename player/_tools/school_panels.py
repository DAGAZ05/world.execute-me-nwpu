"""The school variant's data layer - one import that `tui_live` reads instead of `film_panels`.

`tui_live.py` is written against `FP`: fifty-odd names, from the beat clock to the panel drawings.
This module answers the same names. Almost all of them are the film's own numbers and are forwarded
to `film_panels` untouched - the song, its timing, the lyric band, the word timeline and the maths
of the cuts do not change because the story moved to Xi'an. What is replaced is what the story
actually is:

    FP.dsh_window(t)      the whale's per-frame DOM   ->  school_chat.window(t), 航小天's dialogue
    FP.dsh_inside(t)      the film's COVER spans      ->  always on
    FP.shot_pane(name)    (new) which right-hand pane a shot wants
    FP.school_shots()     (new) shot -> pane / ops / full-bleed routing
    FP.ui_gain_at(...)    the film's drain curve      ->  1.0 (see below)

Why `ui_gain_at` is overridden rather than reused
-------------------------------------------------
The film's gain curve means one specific thing: *"The system colour is 'you'. It drains when you
leave and never fully comes back"* (engine.py:91-94), and it drains between 110.4 s and 179.5 s -
the stretch where the whale is alone. 航小天 is not alone in that stretch and has not been left; the
curve's cue does not exist in this variant. Reusing it would drain the window for a reason that is
no longer true, so this variant holds the gain at 1.0 and lets the *dialogue* carry that beat when
batch 6 gets there. That is a deliberate difference, not an oversight.

Forwarding is by module `__getattr__`, so every name this file does not define - `pulse`, `beat_t`,
`banner_fit`, `decode`, `FACTS`, `SCR`, `KERNELS`, the whole maths library the player leans on -
resolves to `film_panels` without being listed here. The list stays short on purpose: a name in this
file is a name the variant has *changed*.
"""
from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import film_panels as _FP            # noqa: E402  the film's own numbers, forwarded below
import school_chat as _CH            # noqa: E402
import school_scenes as _SC          # noqa: E402
import school_courses as _CO         # noqa: E402
import school_colleges as _COL       # noqa: E402  whose content the reprise draws
import school_machine as _MA         # noqa: E402

# ---------------------------------------------------------------- the chrome's two strings
#
# The chapter bar and the POST log are the only two pieces of the film's own *text* this variant had
# left, and they are the loudest: one sits next to the clock, the other fills the band under the chat
# window for the first five seconds. Both are pure data in the shapes the player already reads, so
# overriding them is two names here rather than a second drawing routine.
CHAPTERS = _MA.CHAPTERS
BOOT_LOG = _MA.BOOT_LOG
PROT_START = _MA.PROT_START
# ...and the one string that is not the bar's: what `draw_flood` stamps into the middle of the screen.
# `tui_live.flood_stamp` looks for this name on whichever module `panels()` returns, so re-exporting it
# here is what puts `SW` on screen instead of the film's chapter number.
STAMP = _MA.STAMP

# The film's last shot types `在吗？` into the prompt and nobody answers. This variant keeps the shot and
# changes the question, because what is being waited on here is not a person but the sword.
PROMPT_TEXT = "\u5728\u94f8\u5251\u5417\uff1f"
PROMPT_TOKS = ["\u5728\u94f8\u5251\u5417", "\uff1f"]


def chapter(t: float) -> str:
    """The chapter label at `t`, in this variant's own names."""
    return [lab for s, lab in CHAPTERS if s <= t][-1] if CHAPTERS else ""


def chapter_start(tag: str, default: float = 0.0) -> float:
    """When this variant's chapter bar reaches a chapter. See `school_machine.CHAPTER_TAGS`."""
    if tag in _MA.CHAPTER_TAGS:
        return _MA.CHAPTER_TAGS[tag]
    for s, lab in CHAPTERS:
        if tag in lab:
            return s
    return default

# ------------------------------------------------------------------ the twelve Execution hits
#
# 02:27.52-02:38.02 is the song's twelve "Execution" hits, and `02b_图像对位与可视化表达.md` §4.1
# reads them as twelve courses drawn in their own graphical language. The hits are NOT evenly spaced
# (0.87-1.07 s), and the shortest ones cannot carry a drawing: at 197x52 a course pane gets about
# eleven rows by a hundred-odd columns, and a data-flow diagram needs all of that just to be legible.
#
# So the table below gives each *hit* a pane and lets two short hits share one when a drawing would
# otherwise be on screen for under 1.3 s. The durations are the hits themselves - `_hit` computes them
# from the same lyric times the lyric band uses, so the picture changes exactly when the word is sung.
#
# Fifteen courses, twelve hits - and the count is not a detail, it is the whole reason `_exec_rows` has to
# spread the drawings evenly instead of putting one on each hit (see its docstring).
#
# This comment said "fourteen courses" and "数据结构 and 算法设计 share a drawing": both stopped being true
# in batch 12, when 算法设计 got its own pane and its own slot. The list below is what is real, and it is
# **sixteen** entries - fifteen courses plus `pane_motif_powerdown`, which is the machine's own shutdown
# counter rather than a sixteenth course. 工业模型 and 大型工业软件 are not in it at all: they are two of
# the six **instruments** on the countdown numbers (`GAUGE_SLOTS`), not course drawings on a hit.
# (Corrected by batch 38, whose subject was exactly this kind of drift between a comment and its code.)
EXEC_AT = [147.52, 148.59, 149.78, 150.64, 151.53, 152.43,
           153.32, 154.31, 155.20, 156.18, 157.12, 158.02, 161.51]

EXEC_PANES = [
    # (pane, the course)
    ("pane_exec_embedded", "\u5d4c\u5165\u5f0f\u7535\u5b50\u5fae\u7cfb\u7edf"),
    ("pane_exec_c", "\u7a0b\u5e8f\u8bbe\u8ba1\uff08C\uff09"),
    ("pane_exec_ds", "\u6570\u636e\u7ed3\u6784 \u00b7 \u7ea2\u9ed1\u6811"),
    # 算法设计 used to share `pane_exec_ds`; it is a different course with a different set of paradigms
    # (分治、动态规划、贪心) and it now has its own pane and its own slot inside the same twelve hits
    ("pane_exec_algo", "\u7b97\u6cd5\u8bbe\u8ba1 \u00b7 \u5206\u6cbb/\u52a8\u89c4/\u8d2a\u5fc3"),
    ("pane_exec_se", "\u8f6f\u4ef6\u5de5\u7a0b \u00b7 \u6570\u636e\u6d41\u56fe"),
    ("pane_exec_oop", "\u9762\u5411\u5bf9\u8c61 \u00b7 UML"),
    ("pane_exec_net", "\u8ba1\u7b97\u673a\u7f51\u7edc \u00b7 \u4e09\u6b21\u63e1\u624b"),
    ("pane_exec_os", "\u8ba1\u7b97\u673a\u64cd\u4f5c\u7cfb\u7edf \u00b7 OpenEuler"),
    ("pane_exec_co", "\u8ba1\u7b97\u673a\u7ec4\u6210\u539f\u7406 \u00b7 \u8865\u7801\u4e58\u6cd5"),
    ("pane_exec_db", "\u6570\u636e\u5e93 \u00b7 EXPLAIN \u4e0e B+ \u6811"),
    ("pane_exec_pm", "\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406 \u00b7 WBS/Gantt"),
    ("pane_exec_test", "\u8f6f\u4ef6\u6d4b\u8bd5 \u00b7 \u8986\u76d6\u7387"),
    ("pane_exec_dl", "\u6df1\u5ea6\u5b66\u4e60 \u00b7 \u53cd\u5411\u4f20\u64ad"),
    # \u7f16\u8bd1\u539f\u7406 is on the curriculum's spine and had no pane until batch 34
    ("pane_exec_compiler", "\u7f16\u8bd1\u539f\u7406 \u00b7 \u4e94\u6b65\u7ba1\u9053"),
    ("pane_exec_industrial", "\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6"),
    # ...and the last slot of the reprise is the machine's own shutdown counter rather than the FEM
    # instrument a second time: "除了校徽、铸剑雕塑外的演出禁止重复", and the countdown to one is what the
    # twelve hits are counting anyway. FEM keeps its place on the "fem, liu" number above.
    ("pane_motif_powerdown", "\u6267\u884c\u6536\u675f \u00b7 N \u2192 1"),
]

GAUGES = list(_CO.GAUGE_PANES)


def gauge_script(pane: str) -> str:
    """The number `pane` is counting, in the script its own language writes it in, or "".

    Read by the film's own overlay (`tui_live.draw_digit_word`) for the three countdown rows, and empty
    for every other pane - which is what makes the caller a two-liner.
    """
    return _CO.GAUGE_SCRIPTS.get(pane, "")

# One line each for the reprise rows, where the words are the twelve "Execution" hits and the three
# countdown numbers (batch 58, the user: "标题后加上' · '+简短说明文字…体现图案与当前歌词的照应"). The
# hits are the song's own count of executions, so each course drawing says what *one* run of it looks
# like, and each instrument answers the number being counted down. They live here rather than inside the
# rows because `_exec_rows` builds those rows from these two tables.
EXEC_SUB = {
    "pane_exec_embedded": "一次执行：从复位向量到中断返回",
    "pane_exec_c": "一次执行：main 里的语句一条条走",
    "pane_exec_ds": "一次执行：插入之后重新平衡",
    "pane_exec_algo": "一次执行：三种范式挑一种",
    "pane_exec_se": "一次执行：数据沿 DFD 的箭头流一遍",
    "pane_exec_oop": "一次执行：消息在 UML 对象间传递",
    "pane_exec_net": "一次执行：握手三次，连上一条线",
    "pane_exec_os": "一次执行：调度器切到下一个进程",
    "pane_exec_co": "一次执行：一位一位地移加",
    "pane_exec_db": "一次执行：按 EXPLAIN 走一遍索引",
    "pane_exec_pm": "一次执行：冲激进来，响应出去",
    "pane_exec_test": "一次执行：用例跑完，覆盖率涨一格",
    "pane_exec_dl": "一次执行：前向一遍、反向一遍",
    "pane_exec_compiler": "一次执行：源码穿过五步管道",
    "pane_exec_industrial": "一次执行：整条产线的求解器跑一遍",
    "pane_motif_powerdown": "十二次执行收束：N 一直数到 1",
}
GAUGE_SUB = {
    "pane_gauge_burndown": "数到 ein、dos：燃尽图还剩几天",
    "pane_gauge_pareto": "数到 ein、dos：两成模块背八成缺陷",
    "pane_gauge_attention": "数到 trois、ne：权重压在同一个词上",
    "pane_gauge_fem": "数到 trois、ne：连续体被切成网格",
    "pane_gauge_assembly": "数到 fem、liu：零件按约束装成整机",
    "pane_gauge_final": "数到 fem、liu：最后一个格子是毕设",
}

# the three countdown numbers: each is a lyric line of its own, and each carries two instruments.
#
# These three windows were 148.79 / 149.66 / 150.45 - exactly **10.00 s early** - which put the six
# instruments over the "Execution" hits and the three numbers (`Ein, dos` 159.20, `Trois, ne` 159.79,
# `Fem, liu` 160.66 in `input/lyrics.lrc`) on top of three *course* panes. `02b_图像对位与可视化表达.md`
# §4.2 pins them at 02:38.79-02:41.51, i.e. these numbers. Batch 31's timing audit found it by lining the
# schedule up with the lyric timeline (`_dev/timeline_table.py`); the old `EXEC_AT` below still holds the
# twelve hit times, and it is kept as the record of where the hits are.
GAUGE_SLOTS = [(158.79, 159.66, "ein, dos"), (159.66, 160.45, "trois, ne"),
               (160.45, 161.51, "fem, liu")]
EXEC_FROM, EXEC_TO = 147.52, 162.23      # the first "Execution" hit to the end of the reprise


def exec_rows_for(code: str) -> list[dict]:
    """One college's reprise rows: fifteen courses, one shutdown counter and six instruments.

    The song gives twelve "Execution" hits 0.87-1.07 s apart and three countdown numbers, and this
    variant has fifteen courses plus a counter and six instruments. Sixteen plus six does not go into
    twelve plus three, and two earlier attempts at forcing it both failed in ways worth recording:

      * **one course per hit and the instruments on the numbers** left four courses with 0.5 s each
        after the numbers, and
      * **interlacing the two lists** produced spans as short as 0.11 s - six frames at 24 fps, so a
        drawing would be replaced before its own reveal had finished. Both were caught by printing the
        resulting table, not by watching it.

    What works is to stop pretending the two lists interleave. **The instruments are anchored to the
    three numbers**, because that is what the brief says they are for, and they get their own
    non-overlapping window per number. **The courses then fill the gaps**: evenly across everything
    before the first number, evenly across each gap between two numbers, and evenly across the whole
    reprise after the last one. Nothing is squeezed to make the counts match, nothing overlaps, and
    the two sets are disjoint by construction rather than by a priority rule.

    The cost, stated plainly: the course on screen does not change on every "Execution" hit. It
    changes on a schedule of its own that is derived from the hits' own span. The alternative - a
    drawing that appears for six frames - would technically match the lyric and be unwatchable.

    **`code` is which college's pack to build** (see `school_colleges`): the algorithm is the school's,
    the lists are the college's, so a second college is one more entry in `PACKS` and no edit to the
    first one. An unknown code is not an error - it falls back to the default pack, which is what keeps
    `--major a` (a college whose pack has not landed yet) playing rather than empty.
    """
    pack = PACKS.get(code) or PACKS[_COL.DEFAULT]
    exec_panes = pack["exec_panes"]
    exec_sub, gauge_sub = pack["exec_sub"], pack["gauge_sub"]
    gauge_slots, gauges = pack["gauge_slots"], pack["gauges"]
    course_of = pack["course_of"]
    exec_from, exec_to = pack["exec_from"], pack["exec_to"]

    # 1. the instruments, disjoint by construction
    gauge_rows = []
    for g, (at, end, lyric) in enumerate(gauge_slots):
        half = (end - at) / 2
        for side in (0, 1):
            j = g * 2 + side
            pane = gauges[j]
            # the ticker reads the *course's* name, like every other row: `ops=[pane]` put the internal
            # identifier `pane_gauge_burndown` on screen for these six rows (found by the batch-31 audit)
            course = course_of(pane)
            gauge_rows.append(dict(at=at + side * half, end=at + (side + 1) * half, name=pane,
                                   lyric=lyric, course=course,
                                   ops=[course], mascot=False, exec_n=0, gauge=g + 1,
                                   sub=gauge_sub.get(pane, "")))

    # 2. the free intervals the instruments left, and the courses spread evenly across them
    free = []
    cur = exec_from
    for at, end, _l in gauge_slots:
        if at > cur:
            free.append((cur, at))
        cur = max(cur, end)
    if exec_to > cur:
        free.append((cur, exec_to))

    course_rows, i = [], 0
    for a, b in free:
        if i >= len(exec_panes):
            break
        left = len(exec_panes) - i
        # how many courses this gap carries: proportional to its length, at least one
        later = sum(bb - aa for aa, bb in free[free.index((a, b)) + 1:])
        share = max(1, int(round(left * (b - a) / max(1e-6, (b - a) + later))))
        take = min(left, share)
        step = (b - a) / take
        for j in range(take):
            pane, course = exec_panes[i + j]
            course_rows.append(dict(at=a + j * step, end=a + (j + 1) * step, name=pane,
                                    lyric="Execution", course=course, ops=[course],
                                    mascot=False, exec_n=i + j + 1,
                                    sub=exec_sub.get(pane, "")))
        i += take
    return course_rows + gauge_rows


# **The content packs** (see `school_colleges`): one entry per college, and a college is *added*, never
# substituted. `s` is 软件学院 - the author's own, the one whose courses this file was written for. A
# contributor's entry carries its own course list, its own one-line explanations, its own instruments
# (or borrows `PACKS["s"]`'s, since the twelve hits and three numbers are the school's, not the
# college's) and names pane functions that they *add* to `school_scenes.py`; then they put their code in
# `school_colleges.IMPLEMENTED` and the gate's "该方向尚未开设" turns into a real branch.
PACKS: dict[str, dict] = {
    "s": dict(
        college="软件学院",
        exec_panes=EXEC_PANES,
        exec_sub=EXEC_SUB,
        gauge_slots=GAUGE_SLOTS,
        gauges=GAUGES,
        gauge_sub=GAUGE_SUB,
        course_of=lambda pane: _CO.COURSES.get(pane, (pane,))[0],
        exec_from=EXEC_FROM,
        exec_to=EXEC_TO,
    ),
}


def _exec_rows() -> list[dict]:
    """The rows of the college the viewer answered with (`school_colleges.active()`)."""
    return exec_rows_for(_COL.active())

# ---------------------------------------------------------------- the school's own shot table
#
# The film has 97 shots. This variant does not need a different *cut* under every lyric line - it
# needs a different *panel* under the lines whose subject moved. So the shot table here is a sparse
# overlay: a row says "from this lyric line to the next, the right-hand column draws this pane".
# Between rows the film's own 97-shot table still runs, unchanged, which is what keeps the cuts,
# the lyric band, the word-level typing and the ops ticker working without being reimplemented.
#
# `at` is the *lyric* time (input/lyrics.lrc). `name` is the pane in school_scenes; `ops` is what
# the ticker scrolls under it; `mascot` is whether 航小天 (he) may take the left pane
# instead of the chat - see `school_keeps_pane`.
SHOT_ROWS: list[dict] = [
    # The opening, re-cut from six panes to four because two of them collided with the crest that
    # `LANDMARK_ROWS` pins to 0.03 s. Two rows at one timestamp is an overlap and the loser gets a
    # zero-length span, which is how the sweep found this: `pane_power_on` and `pane_protection` were
    # both being scheduled and neither was ever drawn. The board sequence now runs
    # crest(0.03) -> power_on(1.33) -> protection(3.58) -> class(5.16), which is also the order the
    # lyric puts them in: the protection line comes *before* "object creation", not after it.
    dict(at=1.33, name="pane_power_on", lyric="Remember to put on protection",
         ops=["POWER_ON", "VCC", "GND", "5V"], mascot=False, sub="先接地线，再通 VCC 与 5V"),
    dict(at=3.58, name="pane_protection", lyric="Lay down your pieces",
         ops=["ESD", "STRAP", "FUSE"], mascot=False, sub="腕带、地线与保险丝，护住自己"),
    dict(at=5.16, name="pane_class", lyric="And let's begin object creation",
         ops=["CLASS", "OBJECT", "INIT"], mascot=False, sub="写下 class，造出第一个对象"),
    dict(at=7.19, name="pane_parameters", lyric="Fill in my data parameters",
         ops=["PARAM", "SET", "COMMIT"], mascot=False, sub="一行行填参数，齐了才 COMMIT"),
    dict(at=9.75, name="pane_motif_he_init", lyric="Initialization",
         ops=["He 初始化", "REPLACE"], mascot=False, sub="格点先乱、再被替成有序"),
    dict(at=10.90, name="pane_three_arms", lyric="Set up our new world",
         ops=["AERO", "ASTRO", "MARINE"], mascot=True, sub="航空、航天、航海，各一条旋臂"),
    dict(at=12.47, name="pane_countdown", lyric="And let's begin the simulation",
         ops=["RUN", "SIM", "t=0"], mascot=False, sub="3-2-1 归零，模拟从 t=0 起跑"),
    # The gap is the campus, not the timetable. The user's audit (2026-10-03) found the four-year
    # curriculum list here, at 00:13-00:29, which is exactly the content the first act must not have:
    # the college is chosen at 02:11.9 and until then the film is about the *school*. The curriculum
    # moved to `pane_curriculum`'s new row after the gate, where it belongs (it is the answer to "so
    # what am I in for"), and the gap is now the bronze vessel's own character art and the crest.
    dict(at=13.20, name="pane_landmark_hezun", lyric="[gap]",
         ops=["\u4f55\u5c0a", "\u5b57\u7b26\u753b", "1982"], mascot=False, ),
    # The instrumental gap (13.2-29.3) has no words, so the two campus marks alternate over it rather than
    # one of them holding for sixteen seconds: the vessel, then the crest, then back. Nothing is asserted
    # by either, which is what a gap screen is for.
    dict(at=17.00, name="pane_landmark_crest", lyric="[gap]",
         ops=["\u6821\u5fbd", "1938"], mascot=False, ),
    dict(at=21.00, name="pane_landmark_crest", lyric="[gap]",
         ops=["\u6821\u5fbd", "1938", "\u516c\u8bda\u52c7\u6bc5"], mascot=False, ),
    dict(at=25.14, name="pane_motif_phyllotaxis", lyric="[gap]",
         ops=["叶序", "GROW"], mascot=False, ),
    # Batch 50 split this row for the matrix: 线性代数, 计算方法, 离散数学 and 深度学习 are all about the
    # same object and the film had none (the user: "增加矩阵的要素（线性代数、计算方法、离散数学、深度学习
    # 中均涉及矩阵）"). It belongs on this line rather than in the college section because a matrix *is* a
    # linear map of a point set - the drawing continues the sentence it is under.
    dict(at=29.28, name="pane_point_set", lyric="If I'm a set of point",
         ops=["IF", "SET", "DIM"], mascot=False, end=31.20, sub="每个点都带一个维度"),
    dict(at=31.20, name="pane_motif_matrix", lyric="If I'm a set of point",
         ops=["MATRIX", "A\u00b7x = b"], mascot=False, end=33.01, sub="点集乘一下，维度就换了"),
    # The IF/THEN passage is four couplets, not one: "a set of point / my dimension", "a circle / my
    # circumference", "a sine wave / all my tangents", "infinity / your limitations". One pane held for
    # all 12.6 s of it was the same fault the user found on the tomato pane - the right column stopped
    # following the song - so each couplet gets the pane that draws *it*: the conditional device, then the
    # superellipse (a circle is `n = 2` of it), then the sine and its envelope, which is also where the
    # pane's own third stage already was.
    dict(at=33.01, name="pane_polyhedra", lyric="If I'm a circle",
         ops=["n \u2192 \u221e", "2\u03c0r", "CIRCLE"], mascot=False, sub="圆是 n→∞ 的超椭圆"),
    dict(at=36.77, name="pane_motif_sine", lyric="If I'm a sine wave",
         ops=["正弦", "ENVELOPE"], mascot=False, sub="波与它的全部切线，都给你"),
    # The overlay stops at the end of P1 and the film's own 97-shot table takes the column back from
    # here to the end of the song. That is not a gap left by accident: a school pane only exists where
    # the school content exists, and the alternative - holding the last pane on screen for 166 seconds
    # - is what the film itself forbids ("a plate that *is* the lyric's text never bleeds past its own
    # line"; `references/visual-system.md`). The columns between 44 s and the end used to be the next
    # batch's work; `pane_exchange` has since taken 41.92-54.74 (see `LANDMARK_ROWS`), so the film's own
    # panels now only cover 44-54 s where nothing school-side is scheduled. **There is no `name=None`
    # row here any more**: it stood at exactly 41.92 and became a zero-length row the moment a real pane
    # started there, which the schedule check reported as a non-positive span.
]

# ---------------------------------------------------------------- the campus landmarks
#
# `02b_图像对位与可视化表达.md` §2-3 pins four campus works to particular lyric lines. Each row below
# is one of those pins, and each is deliberately *short*: a landmark is a punctuation mark, not a
# panel. Six occurrences of six works across three and a half minutes is the whole budget - the
# argument for that number is in the same file, §5, and it is the same argument as the meme-density
# rule in `02_叙事设计.md`: a screen full of campus landmarks is a promotional film, and this is a
# machine talking.
#
# MEMORY is the exception and appears repeatedly, because the sculpture is the song's own shape
# (one word printed twice) rather than a decoration.
LANDMARK_ROWS: list[dict] = [
    # Opening: the crest alone for the first second and a third, then the board lights up. The two were
    # briefly at the *same* timestamp - the brief wants the crest as a watermark *under* the traces -
    # and it does not work as a schedule: two rows at one instant is an overlap, and the second one gets
    # a zero-length span, so `pane_power_on` was never drawn at all. Caught by the sweep, which reports
    # non-positive spans rather than dropping them.
    dict(at=0.03, name="pane_landmark_crest", lyric="Switch on the power line",
         ops=["NWPU", "1938", "1957"], mascot=False, sub="通电，校徽先亮"),
    # `pane_power_on` is *not* repeated here: it is a `SHOT_ROWS` row. Listing it in both places is
    # what produced the collision this comment replaced - the crest and the board both wanted 0.03 s.
    # "unite" / "deeply" / "only God": the two hands - but at three *short* appearances, not three
    # enormous spans. The rows used to chain 54.74 -> 110.40 with no `end`, so `pane_landmark_dialogue`
    # covered fifty-six seconds of a two-hundred-second film and the user's note was exact ("对话这个图
    # 出现的有点久了"). Between its appearances are the supplied character art (`pane_landmark_cat`) and
    # the 万物皆点 pane, which is where `想法.md` puts the cat and the tomato anyway.
    # 互换: 41.92-54.74 had no school pane at all - the film's own panels drew it. This is the section
    # `想法.md` gives five motifs to (F→M as three flipped bits, the twelve-hour clock as a double cover
    # of a day, the braid group σ1), and it is drawn by `school_scenes.pane_exchange`. Four rows, one per
    # motif, on the line each belongs to rather than all four small at once for twelve seconds.
    dict(at=41.92, name="pane_exchange", lyric="Switch my current",
         ops=["XOR", "F\u2192M", "3 bits"], mascot=False, args=dict(panel="bits"), sub="三位取反：电流从 F 换向 M"),
    dict(at=45.52, name="pane_exchange", lyric="To AC, to DC",
         ops=["12h", "AM/PM"], mascot=False, args=dict(panel="clock"), sub="12 小时钟面：AC 与 DC 各半圈"),
    dict(at=47.27, name="pane_exchange", lyric="And then blind my vision",
         ops=["\u03c31", "BRAID"], mascot=False, args=dict(panel="braid"), sub="两股线一交叉，视线就断了"),
    dict(at=50.95, name="pane_exchange", lyric="Oh, we can travel",
         ops=["|x|^n", "SUPERELLIPSE"], mascot=False, args=dict(panel="hyper"), sub="换个 n，圆就走到更远"),
    # Acts 1 and 2 only (`max_phase=1`): `unite` shows the hands approaching and `deeply` the star
    # between them. **Act 3 - the star alone - is its own row at 84.60**, on the lyric `02b §3.3` pins
    # it to; it used to be the tail of this row, which put "只剩那颗星" under `If I can, if I can` at
    # ~57 s. See `pane_landmark_dialogue`.
    dict(at=54.74, name="pane_landmark_dialogue", lyric="And we can unite",
         ops=["UNITE", "\u5bf9\u8bdd"], mascot=False, args=dict(max_phase=1), sub="两只手将触未触：这就是「合」"),
    # **The binary stars had 1.43 s and that was not enough to watch** (batch 56, the user: "双星旋进的时间
    # 太短了，适当加点"). The row is what the drawing reads for its own clock (`school_motifs._row_span`),
    # so lengthening the row *is* lengthening the inspiral: 60.57-64.29 is 3.72 s, of which 0.45 s is the
    # transition, so the quarter-power law now has 3.27 s of visible life instead of 0.98. The time comes
    # from `pane_motif_pixelsort`, which had 4.17 s and keeps 1.88 - still over the 1.2 s floor the span
    # probe enforces, and the sorting sweep it draws is a loop, so it reads at any length.
    #
    # ...and it takes it from the *next lyric line*, not from a round number: `at` is a lyric time
    # (`input/lyrics.lrc`) everywhere in this table, and the first draft of this row used 64.00, which is
    # in the middle of "Then I can, then I can" and therefore a boundary the song does not have. 64.29 is
    # where "Be your only satisfaction" begins, which is also the line `pane_motif_pixelsort` now names.
    dict(at=60.57, name="pane_motif_binary", lyric="Give you all the simulations",
         ops=["0101", "模拟"], mascot=False, sub="两颗星越绕越近，直到并合"),
    # 62.00-70.00 was the cat, held for eight seconds across five different lines - including "I will run
    # the execution", which is not a cat. The cat belongs on the two lines that *are* a cat (80.93,
    # below); here the hands carry "Then I can / satisfaction" and the conditional device carries
    # "If I can make you happy / I will run the execution", which is an `If ... then ...` like all the
    # others the device is for.
    dict(at=64.29, name="pane_motif_pixelsort", lyric="Be your only satisfaction",
         ops=["PIXELSORT", "排序"], mascot=False, sub="杂色按亮度排成一列"),
    dict(at=66.17, name="pane_motif_galaxy", lyric="If I can make you happy",
         ops=["GALAXY", "星系"], mascot=False, sub="星星按引力排队，旋成三条臂"),
    dict(at=70.02, name="pane_motif_en_limit", lyric="Though we are trapped",
         ops=["存在n", "LIMIT"], mascot=False, sub="被困住，也收敛到一点"),
    # 万物皆点 is three couplets - eggplant, tomato, cat - and the film cuts on each one. All three panels
    # held for 11.07 s was the user's example of a performance that outlasts its lyric ("右边panel的西红柿
    # 那个光谱界面占了过长时间，和左侧歌词都不对应了"): the spectrum was still on screen while the words
    # had moved on to the cat. Now each panel gets its own couplet, and the cat - which had the wrong row
    # entirely - gets the two lines about a tabby.
    dict(at=73.53, name="pane_everything_point", lyric="If I'm an eggplant",
         ops=["USDA", "\u8425\u517b\u6d41\u5411"], mascot=False, args=dict(panel="food"), sub="茄子的营养：从土壤一路到餐桌"),
    dict(at=77.16, name="pane_everything_point", lyric="If I'm a tomato",
         ops=["444nm", "472nm", "503nm"], mascot=False, args=dict(panel="tomato"), sub="番茄吸收 444/472/503 nm"),
    dict(at=80.93, name="pane_landmark_cat", lyric="If I'm a tabby cat",
         ops=["\u732b\u5b66\u957f", "\u5b57\u7b26\u753b", "\u53e0\u52a0\u6001"], mascot=False, sub="猫学长：又生又死的叠加态"),
    # 84.6-110.4 is the last verse's "only God / switch my gender / trance" run: the switch lines belong to
    # the swap pane (a gender switch is the same three-bit flip as a current switch), the "if I can / feel
    # your vibrations" lines to the conditional device, and "finally be completion" to the Love class - the
    # expression completed. One pane per thought, instead of a hand and a crest held over all of it.
    # ...and the third act of the hands on the line `02b §3.3` pins it to: the star alone, hands gone.
    # The user's ruling on the placement question the audit raised ("02b §3.3 把它钉在 84.60"):
    # **84.60, on `If I'm the only God`**. `stardiff` follows on the next line, where a star as the
    # *proof of an existence* is the reading it was always meant to carry.
    dict(at=84.60, name="pane_landmark_dialogue", lyric="If I'm the only God",
         ops=["\u5bf9\u8bdd", "the only God"], mascot=False, args=dict(phase=2), sub="手放下了，只剩那颗星：唯一的存在"),
    dict(at=86.21, name="pane_motif_stardiff", lyric="Then you're the proof of my existence",
         ops=["STAR", "衍射"], mascot=False, sub="你在，就是我在的证据"),
    dict(at=88.34, name="pane_motif_quantize", lyric="Switch my gender",
         ops=["QUANTIZE", "3 bits"], mascot=False, sub="性别与电流是同一个开关"),
    dict(at=92.00, name="pane_motif_chladni", lyric="From AM to PM",
         ops=["CHLADNI", "节点"], mascot=False, sub="频率一换，节点就换一组"),
    dict(at=95.28, name="pane_motif_fork_bomb", lyric="Oh, switch my role",
         ops=["FORK", "角色"], mascot=False, sub="换个角色就指数膨胀"),
    dict(at=98.93, name="pane_motif_lattice", lyric="So we can enter",
         ops=["LATTICE", "TRANCE"], mascot=False, sub="向消失点收缩，入口在深处"),
    dict(at=101.13, name="pane_motif_moire", lyric="The trance, the trance",
         ops=["MOIRE", "TRANCE"], mascot=False, sub="两层栅格错开，就进入恍惚"),
    # The superellipse played twice (here and in the 互换 panel at 50.95). The user's rule is
    # once, so this slot is the resonance curve - the row covers "Feel your vibrations" (batch 34).
    dict(at=103.03, name="pane_motif_resonance", lyric="If I can, if I can",
         ops=["f0", "RESONANCE", "Q=6"], mascot=False, sub="f0 处最高：条件对上才响"),
    dict(at=106.84, name="pane_motif_epicycles", lyric="Then I can, then I can",
         ops=["EPICYCLE", "FOURIER"], mascot=False, sub="一个圆套一个圆，画出那颗心"),
    # "Challenging your God": the sword, as the accusation
    dict(at=125.33, name="pane_landmark_sword", lyric="Challenging your God",
         ops=["\u94f8\u5251", "CHALLENGE"], mascot=False, sub="把质问铸成一把剑"),
    # "Fill in my data parameters": the vessel is drawn *inside* `pane_parameters` rather than taking
    # the pane itself - the parameter table is what the lyric says, and 何尊 is the source annotation
    # on one of its rows. It has no row here for that reason: two rows at 7.19 would be two panes in
    # the same second, which is exactly the overlap this table exists to avoid.
    # ------------------------------------------------------------------ the closing three sections
    #
    # Without these the right-hand column fell back to the film's own panels for the last fifty seconds
    # (02:41.5 to the end), which is where the last two panes above stop. They are the four moments
    # `02b_图像对位与可视化表达.md` §4.3-4.6 names, and each is pinned to the lyric it belongs to rather
    # than to a share of the time.
    dict(at=162.23, name="pane_converge", lyric="If I can, if I can",         ops=["DFD", "ER", "\u6d3b\u52a8\u56fe", "\u72b6\u6001\u56fe", "\u2192", "CLASS"], mascot=False, sub="四张图收进一个类"),
    # Euclid I.47 was a plate about proof on a line about *selection*; this is the selection (batch 34)
    dict(at=166.05, name="pane_motif_one_path", lyric="Be your only execution",
         ops=["ONE PATH", "唯一执行"], mascot=False, sub="十六个分支，只亮一条路"),
    dict(at=169.61, name="pane_backlog", lyric="If I can have you back",
         ops=["SCRUM", "TODO", "DOING", "DONE"], mascot=False, sub="把你从 DONE 挪回 TODO"),
    # The four AI motifs. They are laid out around `shot_collapse` (174.90-177.50), which the TUI draws
    # full-bleed *in this variant too* - the film's picture collapses into a line and a dot, and there is
    # no chrome left to draw a pane in. The first version of this table put `pane_ai_rl` at 175.31, where
    # the column is empty for its whole life and the pane is simply not on screen. Two motifs before the
    # collapse and two after it also gives that moment something to divide.
    dict(at=171.31, name="pane_ai_cnn", lyric="If I can have you back",
         ops=["CONV", "KERNEL", "FEATURE MAP"], mascot=False, sub="卷积核扫一遍，认出这段回忆"),
    dict(at=173.10, name="pane_ai_attention", lyric="Though we are trapped",
         ops=["Q", "K", "V", "SOFTMAX"], mascot=False, end=174.90, sub="Q 在 K 里找最像的那一段"),
    # the film's own collapse, 174.90-177.50, with no pane behind it: `shot_collapse` is drawn
    # full-bleed in this variant too, so a name here would be a pane nobody can see
    dict(at=174.90, name=None, lyric="Though we are trapped", ops=["COLLAPSE"], mascot=False,
         end=177.50),
    dict(at=177.50, name="pane_ai_rl", lyric="I've studied, I've studied",
         ops=["POLICY", "ROLLOUT", "ADVANTAGE"], mascot=False, sub="试很多遍，取优势最大的那条"),
    dict(at=179.30, name="pane_ai_diffusion", lyric="I've studied, I've studied",
         ops=["NOISE", "DENOISE", "\u6b65\u6570"], mascot=False, sub="从噪声里一步步找出你"),
    dict(at=181.20, name="pane_knowledge", lyric="I've studied, I've studied",
         ops=["STUDIED", "\u77e5\u8bc6\u56fe\u8c31"], mascot=False, sub="学过的东西连成一张网"),
    # The curriculum, moved here from 00:13 where the audit found it: this is the answer to the college
    # the student just chose, so it belongs on the far side of the gate and not before it.
    #
    # **Split at 144.50** (batch 44): this row was the film's longest single drawing at 10.62 s, and the
    # stretch from the end of the 数据结构 exchange (~144.4) to the first "Execution" hit was carrying no
    # picture of its own. The tail now shows the algorithm one of these courses actually computes.
    #
    # **Moved to 142.00-147.52** (batch 48). The tail row was put at 144.50, which is *inside* shot 64
    # (`shot_flood`, 144.16-147.62) - and the film's flood shot takes the whole screen, panes and all, so
    # the pane was drawn zero times: scheduled for 3.0 s and never on screen. The lyric table has the
    # boundary this row wanted all along - the instrumental gap labelled 数据结构 at 02:22.0 - so the
    # curriculum ends there and the graph drawing owns the gap. `_dev/row_probe.py` now fails a row whose
    # whole life is inside a shot that draws no pane, which is the check that would have caught it.
    dict(at=136.90, name="pane_curriculum", lyric="[after the gate]",
         ops=["YEAR1", "YEAR2", "YEAR3", "YEAR4"], mascot=False, end=142.00, ),
    # `Dijkstra 裂纹` - a least-cost path through a material, as the last image before the twelve hits.
    # The user's note: the motif existed but **no row used it** ("dijkstra 没被使用的话，需要在学院部分
    # 合适的地方加上"). It belongs in the college section because shortest path is the fourth pillar of
    # 算法设计 - the pane next to this one in the schedule teaches 分治/动规/贪心, and this is the graph
    # algorithm that the other three build toward. It is a real Dijkstra now, not a greedy walk (batch 43),
    # so what it draws is the thing its caption claims.
    #
    # Its visible life is 142.00-144.16 (2.16 s): the row spans to 147.52 so that the schedule stays
    # gapless, but the last 3.36 s of it are behind `shot_flood`, which is where the "07" stamp lands.
    # The crack's growth is anchored on this row rather than on the song clock for that reason - see
    # `school_motifs._dijkstra_anchor`.
    dict(at=142.00, name="pane_motif_dijkstra", lyric="[after the gate]",
         ops=["\u7b97\u6cd5\u8bbe\u8ba1", "Dijkstra \u6700\u77ed\u8def"], mascot=False, end=147.52, ),
    dict(at=184.33, name="pane_love_class", lyric="I know the algebraic expression of lo-o-ove",
         ops=["LOVE", "CLASS", "UML"], mascot=False, sub="把心形写成一个类"),
    # The last verse is two thoughts, not one: "the algebraic expression of love", and then "though you
    # are free / I am trapped / trapped in lo-o-ove". The Love class draws the first; the hands - the
    # film's own work - draw the second, which is what the two hands not touching have always meant.
    # The disc, moved here from the closing chapter (batch 50): "把最后面的圆盘挪至学院部分前面的学校部分
    # （memory 部分有点长了，可以截取一部分换圆盘）". It is a *course* image - a circular plate mode, sand on
    # the lines that do not move - so it belongs in the school part before the college, and the time comes
    # out of the MEMORY run, which had six rows of the same word. What the closing chapter needed instead
    # was the subject the software-engineering chapter is for; see `pane_sw_project` at 187.97.
    dict(at=187.97, name="pane_sw_project", lyric="Though you are free",
         ops=["\u8f6f\u4ef6\u9879\u76ee\u7ba1\u7406", "\u8f6f\u4ef6\u5f00\u53d1\u7efc\u5408\u8bad\u7ec3"],
         mascot=False, sub="自由也得排进甘特图"),
    # MEMORY: one more layer on every "You have left", then down to one, then none.
    #
    # This is the one place in the film where a pane is drawn *differently* on lines that are otherwise
    # identical, and the difference is the whole idea: the sculpture is one word printed twice, the
    # lyric is one sentence sung five times, and the count is what ties them together. So the count
    # travels in `args` rather than being derived from the clock - `draw_scene_pane` hands it to the
    # drawing, and `pane_memory` takes a `layers` keyword.
    #
    # The *run* was fifteen seconds and the user's note is "memory 停留时间太长了，增加其他动画修改": the
    # climb is fine (the pane is redrawn on every line), but the last row - `layers=1` at 119.81 - then
    # sat there for five and a half seconds over "Erase all the pointless fragments" and "Then maybe,
    # then maybe", which are not about a graduation sculpture. So the run is cut twice: `pane_isolation`
    # takes "You have left me in isolation" (one point left, the field emptying), MEMORY comes back for
    # exactly one line at "If I can, if I can" as a single layer - the one word the point became - and
    # `pane_fragments` takes the erase. MEMORY is on screen for 7.4 s of the stretch instead of 15, and
    # no single row of it is longer than 3.2 s.
    dict(at=110.40, name="pane_memory", lyric="Though you have left",
         ops=["MEMORY", "x2"], mascot=False, args=dict(layers=2), sub="你走一次，就多叠一层"),
    dict(at=111.98, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x3"], mascot=False, args=dict(layers=3), sub="你走一次，就多叠一层"),
    dict(at=112.89, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x4"], mascot=False, args=dict(layers=4), sub="你走一次，就多叠一层"),
    dict(at=113.75, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x5"], mascot=False, args=dict(layers=5), sub="你走一次，就多叠一层"),
    dict(at=114.75, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x6"], mascot=False, args=dict(layers=6), sub="你走一次，就多叠一层"),
    # "You have left me in isolation": the field emptying, one point left
    dict(at=115.90, name="pane_isolation", lyric="You have left me in isolation",
         ops=["ISOLATION", "\u4e00\u4e2a\u70b9"], mascot=False, sub="只剩一个点：场里没人了"),
    # ...and then the plate mode, in the slot the single-layer MEMORY used to hold. The count 2-3-4-5-6
    # is the sculpture's own idea and it is intact; `layers=1` was a callback on a different lyric
    # ("If I can, if I can"), so it is the row that costs the design least - and "memory 部分有点长了" is
    # the user's own reading of the same thing.
    dict(at=117.95, name="pane_motif_bessel", lyric="If I can, if I can",
         ops=["BESSEL", "\u5706\u677f\u6a21\u6001"], mascot=False, sub="节线一圈圈，像一句「如果」"),
    # "Erase all the pointless fragments": the instruction carried out, cell by cell
    dict(at=119.81, name="pane_fragments", lyric="Erase all the pointless fragments",
         ops=["ERASE", "\u788e\u7247"], mascot=False, sub="游标一行行删，碎片就没了"),
    # closing: the crest alone
    dict(at=193.46, name="pane_landmark_crest", lyric="[gap] \u5c3e\u58f0",
         ops=["NWPU", "\u516c\u8bda\u52c7\u6bc5"], mascot=False, ),
]

# how many rows of the right-hand column each pane wants, and the least it can be drawn in. The film
# carries the same pair per pane (`draw_body`'s `need`/`least`); a pane that cannot get `least` rows
# hands them back to the ops ticker rather than appearing as an empty box.
PANE_MIN = {
    "pane_power_on": (12, 5),
    "pane_protection": (10, 4),
    "pane_pieces": (10, 4),
    "pane_class": (9, 4),
    "pane_parameters": (9, 4),
    "pane_polyhedra": (13, 6),
    "pane_three_arms": (16, 6),
    "pane_countdown": (8, 4),
    "pane_curriculum": (9, 4),
    "pane_point_set": (10, 5),
    # the two drawings that took the MEMORY run's tail. Both are legible in four rows and want nine:
    # `pane_isolation` is a grid of points (a short pane just shows fewer) and `pane_fragments` is a cell
    # grid that needs at least two rows of cells and its two captions.
    "pane_isolation": (11, 4),
    "pane_fragments": (11, 5),
}
# ...and the twenty-two `pane_motif_*` drawings (`school_scenes._motif`): they were written as bands and
# are now also panes, so they want about what a band wanted - eleven rows, legible in five.
for _m in ("he_init", "rectifier", "phyllotaxis", "byrne", "quantize", "dijkstra", "matrix", "epicycles",
           "hearts9",
           "fork_bomb", "sine", "chladni", "moire", "galaxy", "fragmentation", "pixelsort", "powerdown",
           "bessel", "hyperellipse", "stardiff", "en_limit", "binary", "lattice"):
    PANE_MIN["pane_motif_" + _m] = (11, 5)
# every course drawing wants the column's whole height: at 197x52 that is eleven rows, which is what
# a DFD, a sequence diagram or a register trace needs to be legible rather than merely present. The
# `least` of 5 is what keeps a short window from dropping to the ops ticker entirely.
for _p in _CO.COURSES:
    PANE_MIN[_p] = (11, 5)

# The last row of the table has no next row to take its end from, and it ends here: the song is
# 211.913 s long (`data/song.json`) and the player's clock *is* the audio, so past this point there is
# nothing left to draw over.
#
# It used to be `10 ** 9`, which reads as harmless - who cares what a duration is when the song has
# stopped - and was not: the closing plate's span became 999999806 s, so `u` sat at zero for the whole
# tail and every part of that pane that waits for `u` waited forever. `_dev/clock_probe.py` prints the
# span it measured, which is how it was found ("span 999999806.54s" between two rows of the table).
SONG_END = 212.0


def shot_rows() -> list[dict]:
    """`SHOT_ROWS` plus the fourteen course panes of the countdown, in time order.

    A row from `SHOT_ROWS` carries no `end` and takes the next row's `at`, because the batch-1 overlay
    is a list of "from this lyric line to the next". A row from `_exec_rows` carries its own `end`,
    because the course schedule is *not* a chain - the twelve hit spans, the three countdown spans and
    the six instruments are computed from the song's own lyric times and several of them sit inside
    spans that a chain would have cut short. Honouring a row's own `end` is what keeps the two
    schedules from overwriting each other.
    """
    rows = [dict(r) for r in SHOT_ROWS] + LANDMARK_ROWS + _exec_rows()
    rows.sort(key=lambda r: r["at"])
    for i, r in enumerate(rows):
        if "end" not in r:
            r["end"] = rows[i + 1]["at"] if i + 1 < len(rows) else SONG_END
    return rows


def school_shots() -> dict:
    """`{index: {name, pane, ops, figure, u}}` for the row covering each point in the song.

    The player asks this once per frame through `school_entry`; it is cheap because the table is
    ten rows long and sorted once.
    """
    rows = shot_rows()
    out = {}
    for i, r in enumerate(rows):
        out[i] = dict(index=i, total=len(rows), name=r["name"], pane=r["name"],
                      ops=r["ops"], figure=bool(r.get("mascot", False)), alert=None, alert_own=None,
                      start=r["at"], end=r["end"], run=0, last_figure=False, lyric=r["lyric"])
    return out


_ROWS = None


def row_at(t: float):
    """The overlay row covering t, or None before the first one."""
    global _ROWS
    if _ROWS is None:
        _ROWS = shot_rows()
    for r in _ROWS:
        if r["at"] <= t < r["end"]:
            return r
    return None


def school_entry(t: float, base: dict | None) -> dict | None:
    """The film's own entry for t, with the school overlay applied.

    Everything the player needs per frame lives on the film's entry (index, total, start, end, ops,
    alert, figure, u, the shot object). This keeps all of it and changes only what the variant owns -
    which pane the right column draws and what the ticker scrolls - so `draw_body`'s geometry, the
    cut machinery and the footer's shot label all keep working unchanged.
    """
    row = row_at(t)
    if row is None or base is None or row.get("name") is None:
        # no overlay here (before the song starts, or past the end of the batch's own rows): the film's
        # entry stands and its own panes draw. `row is None` and `name is None` are the same state.
        return dict(base, school=True) if base is not None else base
    e = dict(base)
    need, _least = PANE_MIN.get(row["name"], (10, 4))
    e.update(pane=row["name"], pane_need=need, ops=row["ops"],
             figure=bool(row.get("mascot", False)), school=True, lyric=row["lyric"],
             pane_args=row.get("args"), pane_sub=row.get("sub", ""))
    e["start"] = row["at"]
    # The row's own span, not `min(row end, film shot end)`: the film's shot under a school pane can be
    # shorter than the pane and can even *end before it starts* (the film's EXECUTION shots are cut on
    # the music while this variant's course panes are laid out end to end), and clamping to that gave a
    # negative duration - harmless in the drawing, because `_Kit` clamps `u`, but wrong in the footer
    # and wrong in anything that reasons about the pane's length.
    e["end"] = row["end"]
    dur = max(1e-6, e["end"] - e["start"])
    e["u"] = min(1.0, max(0.0, (t - e["start"]) / dur))
    return e


# ---------------------------------------------------------------- the left window

def dsh_window(t: float):
    """`(expression, theme, items)` - 航小天's window. Same shape as the film's own cache."""
    return _CH.window(t)


def school_window_fx(s, x0: int, y0: int, x1: int, y1: int, t: float) -> int:
    """What the score puts *inside* the chat window at `t` - the basketball animation, when it is due.

    A thin adapter for the same reason `SP_scene_pane` is one: `draw_body` should not have to know that
    the window's own events live in `school_fx`, and the one place that decides which module owns the
    full-frame layer is `tui_live.draw`. Returns how many events drew, which nothing waits on.
    """
    import school_fx as _FX
    return _FX.window_fx(s, s.cols, s.rows, t, (x0, y0, x1, y1))


def dsh_inside(t: float) -> bool:
    return _CH.inside(t)


def dsh_gone(t: float) -> bool:
    """Never: this variant has no moment where the page is taken apart to a caret."""
    return False


def dsh_gone_pair() -> tuple:
    return (1e9, 1e9)


def school_keeps_pane(_ent: dict | None) -> bool:
    """The chat window keeps the left pane on every school shot.

    The film lets the clear figure take the pane on a handful of shots. This variant's story is *in*
    the window - the student's questions and 航小天's answers are the narrative - so the window never
    gives the pane up. `mascot=True` on a row means the pane *may* show the figure, which the `c` key
    still toggles; the default is the window.
    """
    return False


def draw_scene_pane(pane: str, s, x0: int, y0: int, x1: int, y1: int,
                    t: float, lt: float, dur: float, u: float,
                    args: dict | None = None, sub: str = "") -> bool:
    """Draw `pane`: a course drawing first, then the batch-1 scenes, else False.

    `args` is the schedule's optional annotation for the drawing - see `school_scenes.draw_pane`.
    `sub` is the row's own one-line answer to "what has this drawing got to do with the words being
    sung" (batch 58); it is published for the header every pane draws through
    (`school_courses.PANE_SUB`, read by `_Kit._header`) and cleared again afterwards, so a caller that
    draws a pane without a schedule row gets a title and nothing else.
    """
    _CO.PANE_SUB[0] = sub
    try:
        if _CO.draw_course(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane),
                           total=len(EXEC_PANES)):
            return True
        if _CO.draw_gauge(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane)):
            return True
        return _SC.draw_pane(pane, s, x0, y0, x1, y1, t, lt, dur, u, args=args)
    finally:
        _CO.PANE_SUB[0] = ""


def _run_of(pane: str) -> int:
    """Which of the fourteen execution drawings this pane is, for its own counter."""
    for i, (p, _c) in enumerate(EXEC_PANES):
        if p == pane:
            return i + 1
    return 0


# ---------------------------------------------------------------- palette hand-off

def init_palette(ui_fn, mix_fn, colours: dict) -> None:
    """Hand `school_scenes` and `school_courses` the player's own helpers.

    Both draw through the same `ui`/`mix` the player uses, and neither may import `tui_live` (that
    would be a cycle), so the helpers are passed in rather than imported.
    """
    ctx = dict(colours)
    ctx["ui"] = ui_fn
    ctx["mix"] = mix_fn
    _SC.PANE_CTX.update(ctx)
    _SC._palette()
    _CO.CTX.update(ctx)
    _CO.resolve()


# ---------------------------------------------------------------- ui gain

def ui_gain_at(t: float, name: str, u: float) -> float:
    """1.0 for the whole song - see the module docstring for why the film's drain does not apply."""
    return 1.0


# ---------------------------------------------------------------- the ops box, per section

# The ops box is not one thing for the whole song. Up to the major section it is the film's ticker -
# the shot's own words, scrolling - and from the first "Execution" hit it becomes the machine doing
# the executing: instructions, a program counter and a register line. The user asked for exactly this
# ("ops 框没必要全局一致，可以按段落变化，比如专业段改成机器指令执行"), and it is also the one place
# in the layout where the *box* can say what section the song is in without a caption saying it.
MACHINE_FROM = EXEC_FROM          # 147.52, the first of the twelve hits
MACHINE_STEP = 0.30               # one instruction per 300 ms - fast enough to read as a machine

# ...and the machine's *last* act in the major section is a commit, not an instruction: the user asked for
# the panel to become a `git bash` window just before the sword sculpture lands (203.00), with the commit
# message as its content ("学院部分最后面 exec 框在铸剑雕塑出现前，将该 panel 抬头改为 git bash，下面内容
# 为：(hangxiaotian) git commit -m \"...\""). The window is the four seconds between the mascot leaving
# (199.00) and the sculpture arriving, and it is exact rather than approximate because both ends are
# events in `school_fx.EVENTS`.
GIT_FROM, GIT_TO = 199.00, 203.00
GIT_LINE = ("(hangxiaotian) git commit -m "
            "\"\u4eca\u5929\u53c8\u8ba4\u8bc6\u4e86\u4e00\u4f4d\u65b0\u540c\u5b66\uff0c"
            "\u671f\u5f85ta\u6bd5\u4e1a\u7684\u4e00\u5929\"")

# ---------------------------------------------------------------- the two columns change places
#
# "进入学院部分后可以将左右panel位置交换（相应的之前设计的图像的位置也需移动）". The gate is answered at
# 02:11.9 and the curriculum starts at 02:16.9, and that is where the film stops being about a student
# arriving and starts being about the machine's own work: the person moves to the right of the machine.
# It is one number, and `tui_live.draw_body` reads it through `getattr` so `--variant original` (which
# has no `school_panels`) simply never swaps.
SWAP_AT = 136.90                  # the curriculum row: the first frame on the far side of the gate

# eight instructions, because a program listing that fits without scrolling is a listing, not a ticker
MACHINE_PROG = (
    "LOAD  R1, [r0 + id]",
    "CMP   R1, #41827",
    "JNE   .lookup",
    "CALL  insert(R1)",
    "MOV   R2, [r1 + 0x04]",
    "ADD   R2, R2, #1",
    "STORE [r3 + 0x02], R2",
    "RET",
)
MACHINE_AT = 0x0040


def ops_machine(t: float, ops) -> dict | None:
    """What the ops box shows in the major section, or None to leave it as the film's ticker.

    The heading names the course the pane beside it is drawing, because the two boxes are about the
    same thing and one of them already knows its name. Everything here is a pure function of the
    playhead, like the panes: a seek lands on the same instruction, not on a different one.

    `title` is optional and the box uses it for its own heading - the one panel here that is not an
    `exec`: the `git bash` window just before the sword sculpture (see `GIT_FROM`).
    """
    if t < MACHINE_FROM:
        return None
    if GIT_FROM <= t < GIT_TO:
        # `tone` makes the box amber whatever the shot's alert colour is, and drops the inverted cursor
        # bar: this line is a sentence, not a listing's current instruction (the user: "这一行不要有红色框，
        # git bash 改为黄色").
        return {"title": "git bash", "rows": [GIT_LINE], "cur": 0, "head": "", "regs": "",
                "tone": "amber"}
    name = ""
    for op in (ops or ()):
        op = str(op)
        if op and op != "IDLE":
            name = op
            break
    head = name
    for i, (_pane, course) in enumerate(EXEC_PANES):
        if course and (course == name or course.split(" \u00b7 ")[0] == name.split(" \u00b7 ")[0]):
            head = f"EXEC {i + 1:02d}/{len(EXEC_PANES)}  {name}"
            break
    n = int((t - MACHINE_FROM) / MACHINE_STEP)
    cur = n % len(MACHINE_PROG)
    rows = [f"{MACHINE_AT + 4 * i:04X}  {ins}" for i, ins in enumerate(MACHINE_PROG)]
    flags = "Z" if n % 3 == 0 else ("C" if n % 3 == 1 else "N")
    return {"rows": rows, "cur": cur, "head": head,
            "regs": f"R1={(n * 7) & 0xFF:02X}  R2={(n * 13) & 0xFF:02X}  "
                    f"PC={MACHINE_AT + 4 * cur:04X}  FLAGS={flags}"}


# ---------------------------------------------------------------- forwarding

# the two drawing tables, re-exported by name rather than left to `__getattr__`: a sweep or a probe
# that wants to check "does this schedule row have a drawing" should be able to ask this module
# without importing the two drawing modules itself, and `__getattr__` cannot answer for them because
# they are attributes of the *other* modules, not of this one.
COURSES = _CO.COURSES
PANE_BY_NAME = _SC.PANE_BY_NAME


def __getattr__(name: str):
    """Everything not defined above is the film's: the song, its clock, its maths, its lyric band."""
    return getattr(_FP, name)
