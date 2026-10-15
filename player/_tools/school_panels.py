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
    "pane_exec_embedded": "\u4e00\u6b21\u6267\u884c\uff1a\u4ece\u590d\u4f4d\u5411\u91cf\u5230\u4e2d\u65ad\u8fd4\u56de",
    "pane_exec_c": "\u4e00\u6b21\u6267\u884c\uff1a main \u91cc\u7684\u8bed\u53e5\u4e00\u6761\u6761\u8d70",
    "pane_exec_ds": "\u7ea2\u9ed1\u6811  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u63d2\u5165\u4e4b\u540e\u91cd\u65b0\u5e73\u8861",
    "pane_exec_algo": "\u5206\u6cbb /\u52a8\u89c4 /\u8d2a\u5fc3  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u4e09\u79cd\u8303\u5f0f\u6311\u4e00\u79cd",
    "pane_exec_se": "\u6570\u636e\u6d41\u56fe  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u6570\u636e\u6cbf  DFD \u7684\u7bad\u5934\u6d41\u4e00\u904d",
    "pane_exec_oop": "UML  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u6d88\u606f\u5728 UML \u5bf9\u8c61\u95f4\u4f20\u9012",
    "pane_exec_net": "\u4e09\u6b21\u63e1\u624b  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u63e1\u624b\u4e09\u6b21\uff0c\u8fde\u4e0a\u4e00\u6761\u7ebf",
    "pane_exec_os": "OpenEuler \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u8c03\u5ea6\u5668\u5207\u5230\u4e0b\u4e00\u4e2a\u8fdb\u7a0b",
    "pane_exec_co": "\u8865\u7801\u4e58\u6cd5  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u4e00\u4f4d\u4e00\u4f4d\u5730\u79fb\u52a0",
    "pane_exec_db": "EXPLAIN \u4e0e B+ \u6811 \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u6309 EXPLAIN \u8d70\u4e00\u904d\u7d22\u5f15",
    "pane_exec_pm": "\u5085\u91cc\u53f6 /\u51b2\u6fc0  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u51b2\u6fc0\u8fdb\u6765\uff0c\u54cd\u5e94\u51fa\u53bb",
    "pane_exec_test": "\u8986\u76d6\u7387  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u7528\u4f8b\u8dd1\u5b8c\uff0c\u8986\u76d6\u7387\u6da8\u4e00\u683c",
    "pane_exec_dl": "\u53cd\u5411\u4f20\u64ad  \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u524d\u5411\u4e00\u904d\u3001\u53cd\u5411\u4e00\u904d",
    "pane_exec_compiler": "\u4e94\u6b65\u7ba1\u9053 \u00b7 \u4e00\u6b21\u6267\u884c\uff1a\u6e90\u7801\u7a7f\u8fc7\u4e94\u6b65\u7ba1\u9053",
    "pane_exec_industrial": "\u4e00\u6b21\u6267\u884c\uff1a\u6574\u6761\u4ea7\u7ebf\u7684\u6c42\u89e3\u5668\u8dd1\u4e00\u904d",
    "pane_motif_powerdown": "十二次执行收束：N 一直数到 1",
}
GAUGE_SUB = {
    "pane_gauge_burndown": "\u71c3\u5c3d\u56fe  \xb7 \u71c3\u5c3d\u56fe\u8fd8\u5269\u51e0\u5929",
    "pane_gauge_pareto": "\u7f3a\u9677\u5e15\u7d2f\u6258  \xb7 \u4e24\u6210\u6a21\u5757\u80cc\u516b\u6210\u7f3a\u9677",
    "pane_gauge_attention": "\u6ce8\u610f\u529b  \xb7 \u6743\u91cd\u538b\u5728\u540c\u4e00\u4e2a\u8bcd\u4e0a",
    "pane_gauge_fem": "FEM \xb7 \u8fde\u7eed\u4f53\u88ab\u5207\u6210\u7f51\u683c",
    "pane_gauge_assembly": "\u88c5\u914d\u4f53 \xb7 \u96f6\u4ef6\u6309\u7ea6\u675f\u88c5\u6210\u6574\u673a",
    "pane_gauge_final": "\u7518\u7279\u56fe \xb7 \u6700\u540e\u4e00\u4e2a\u683c\u5b50\u662f\u6bd5\u8bbe",
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
         ops=["POWER_ON", "VCC", "GND", "5V"], mascot=False, sub="\u5148\u63a5\u5730\u7ebf\uff0c\u518d\u901a  VCC \u4e0e  5V"),
    dict(at=3.58, name="pane_protection", lyric="Lay down your pieces",
         ops=["ESD", "STRAP", "FUSE"], mascot=False, sub="\u8155\u5e26\u3001\u5730\u7ebf\u4e0e\u4fdd\u62a4\u4e1d\uff0c\u62a4\u4f4f\u81ea\u5df1"),
    dict(at=5.16, name="pane_class", lyric="And let's begin object creation",
         ops=["CLASS", "OBJECT", "INIT"], mascot=False, sub="\u5199\u4e0b  class\uff0c\u9020\u51fa\u7b2c\u4e00\u4e2a\u5bf9\u8c61"),
    dict(at=7.19, name="pane_parameters", lyric="Fill in my data parameters",
         ops=["PARAM", "SET", "COMMIT"], mascot=False, sub="\u4e00\u884c\u884c\u586b\u53c2\u6570\uff0c\u9f50\u4e86\u624d COMMIT"),
    dict(at=9.75, name="pane_motif_he_init", lyric="Initialization",
         ops=["He 初始化", "REPLACE"], mascot=False, sub="\u4e16\u754c\u7531\u65e0\u5e8f\u53d8\u6709\u5e8f"),
    # **13 s 附近那个倒计时删掉**（批 164，用户："13s附近，动画框有个倒计时，左下角 sim.start 框中
    # 也有倒计时，把动画框的这个倒计时删了吧"）。原来这里是一行 `pane_countdown`（12.47-13.20），
    # 而**左下角 `sim.start` 那个框本来就在倒数**——同一个倒计时画了两遍。
    # 处理办法是**把上一行（三旋臂）延长到 13.20 盖住这一段**，而不是删掉 `pane_countdown` 这个
    # pane：pane 留着（别处/以后可能要用），只是**不再有排期行引用它**。
    # 这样这一段时间里动画框演的还是三旋臂，倒计时只在左下角出现一次。
    dict(at=10.90, name="pane_three_arms", lyric="Set up our new world",
         ops=["AERO", "ASTRO", "MARINE"], mascot=True, end=13.20,
         sub="\u822a\u7a7a\u3001\u822a\u5929\u3001\u822a\u6d77\uff08\u4e09\u822a\u7279\u8272\uff09"),
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
    # **第一处间奏的中段：超椭圆**（批 137，清单第 11 条）。用户："第一处间奏的动画内容为
    # 校徽 + **超椭圆（替换一部分校徽动画）** + 刚才的傅里叶分析 两部分"、"超椭圆之前做过，
    # 可以改一下直接沿用"。所以这一行从"校徽"换成 `pane_hyper`——它直接调 `pane_exchange` 里
    # 那个现成的 `_ex_hyper`，没有重写。于是第一处间奏成了
    # **17.00 校徽 → 21.00 超椭圆 → 25.14 傅里叶** 三段。
    dict(at=21.00, name="pane_hyper", lyric="[gap]",
         ops=["\u8d85\u692d\u5706", "n"], mascot=False, end=25.14,
         sub="\u8bbe\u5b9a\u4e0d\u540c\uff0c\u80d6\u7626\u6709\u5f02 \xb7 |x|^n + |y|^n = r^n"),
    # **第一处间奏：叶序 → 傅里叶分解**（批 136，清单第 9 + 11 条）。
    # 用户："scene12动画框沿用之前场景的动画，不要使用叶序（这段是间奏），改用傅里叶分析的动态图示
    # （音乐分解）"、"第一处间奏的动画内容为校徽 + 超椭圆 + 刚才的傅里叶分析 两部分"。
    # 这一行（25.14-29.28，`[gap]`＝间奏）原来挂的是 `pane_motif_phyllotaxis`——**是这处间奏里
    # 唯一错的东西**；上一行（17.00-25.14，`pane_landmark_crest`）就是"校徽"那一半。
    dict(at=25.14, name="pane_fourier", lyric="[gap]",
         ops=["FFT", "\u8c10\u6ce2"], mascot=False,
         sub="\u97f3\u4e50\u62c6\u6210\u8c10\u6ce2\uff0c\u6790\u6784\u4e07\u7406"),
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
    # **抬头说明改对**（批 110，用户："if I'm a circle 动画框的抬头你依旧没改（不是超椭圆！）"）。
    # 这一屏画的是**正多边形在 n→∞ 时趋近圆**，和超椭圆是两件事：
    # 超椭圆是 `|x/a|^n + |y/b|^n = 1` 这一族曲线（n=2 是椭圆、n→∞ 是矩形），
    # 而这里是**内接正多边形**的周长趋近圆周长。文字与画面必须指同一件事。
    dict(at=33.01, name="pane_polyhedra", lyric="If I'm a circle",
         ops=["n \u2192 \u221e", "2\u03c0r", "CIRCLE"], mascot=False,
         sub="正多边形 n→∞ 趋近圆，周长趋近 2πr"),
    # **抬头与 ops 跟着画面改**（批 107）：这一行跨两条歌词——
    # `If I'm a sine wave`（36.77-40.36）与 **`If I approach infinity`（40.36-41.92）**。
    # 后半段画的是 `sin x / x`（用户："请改为函数 sin x / x…并在框内进行文字说明"），
    # 所以抬头不能再写"波与它的全部切线"，ops 也不能再写 ENVELOPE。
    #
    # **批 163（清单2 第 14 条点名）**：用户："**sin x 包络抬头去掉 sinx/x 的描述**"。
    # 框内实际画的是 `sin x 与切线包络`（`school_motifs.py` 的 `k.section`），
    # 而这一行的 `sub` 原来写的是 `sin x / x：振荡在衰减，极限是 0`——**那是另一个动画**
    # （sinc，见 `pane_motif_sinc`）。抬头和内容说的不是一件事，按批 98e 的规矩要一致。
    # `ops` 里的 `"sin x / x"` 与 `"趋近 0"` 同样是 sinc 的，一并换掉。
    dict(at=36.77, name="pane_motif_sine", lyric="If I'm a sine wave",
         ops=["\u6b63\u5f26", "\u5e45\u503c 1", "\u5207\u7ebf\u5305\u7edc"], mascot=False,
         sub="\u6b63\u5f26\u4e0e\u5b83\u7684\u5207\u7ebf\u5305\u7edc\uff0c\u6211\u4e0e\u4f60\u76f8\u5bb9"),
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
         ops=["NWPU", "1938", "1957"], mascot=False, sub="\u901a\u7535\uff0c\u6821\u5fbd\u70b9\u4eae"),
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
         ops=["XOR", "F\u2192M", "3 bits"], mascot=False, args=dict(panel="bits"), sub="\u8d8b\u4e8e\u65e0\u7a77\u5927\u65f6\u6781\u9650\u4e3a 0\uff08\u8fd9\u4e0d\u662f\u6d1b\u5fc5\u8fbe\uff01\uff09"),
    # AC/DC：用户批 119（清单第 25 条）"动画框内展出应当是直流、交流电示意" ⇒ `panel="acdc"`。
    dict(at=45.52, name="pane_exchange", lyric="To AC, to DC",
         ops=["AC", "DC", "RECTIFY"], mascot=False, args=dict(panel="acdc"),
         sub="\u6574\u6d41  \u2192 \u6ee4\u6ce2"),
    # 辫群（对应 `and then blind my vision`）。
    dict(at=47.27, name="pane_exchange", lyric="And then blind my vision",
         ops=["\u03c31", "BRAID"], mascot=False, args=dict(panel="braid"),
         sub="\u590d\u6742\u7684\u7f20\u7ed5\u8fc7\u7a0b\uff0c\u8ba9\u89c6\u7ebf\u8ff7\u79bb"),
    # **`so dizzy, so dizzy`（49.11）单独一行**（批 119，清单第 27 条）：它原来落在上面那一行里，
    # 于是同一行要演"辫群"和"向日葵叶序"两张**不同的画**——pane 的格子不会自己清，两段笔迹会叠。
    # 分成两行，各画各的。叶序**框内不留文字**（`phyllotaxis(titles=False)`）。
    dict(at=49.11, name="pane_exchange", lyric="So dizzy, so dizzy",
         ops=["PHYLLO", "137.5\u00b0"], mascot=False, args=dict(panel="phyllo"),
         sub="137.5\xb0 \u9ec4\u91d1\u89d2\uff0c\u91c7\u96c6\u70ab\u76ee\u9633\u5149"),
    # **`Oh, we can travel` 与 `To AD, to BC` 各占一行**（批 121，清单第 29 条）：它们是**两张
    # 不同的时间线**（西工大校史 / 西安的公元前后），而 pane 的格子不会自己清——批 119 的教训。
    # **原来是 `hyper`（超椭圆），已改成 `timeline`**：这份清单第 29 条就是"当前为超椭圆，改为
    # 时间线"。
    dict(at=50.95, name="pane_exchange", lyric="Oh, we can travel",
         ops=["1938", "1957", "1970", "2006"], mascot=False, args=dict(panel="timeline"),
         sub="\u5018\u82e5\u80fd\u56de\u5230 1938"),
    dict(at=52.99, name="pane_exchange", lyric="To AD, to BC",
         ops=["BC 202", "AD 618", "\u4eca"], mascot=False, args=dict(panel="timeline"),
         sub="\u4ece\u53e4\u90fd\u56de\u671b\u6570\u5343\u5e74"),
    # **`If I can, if I can`（58.65）起放双星旋进**（批 124，清单第 33 条："歌词第一次
    # if I can, if I can 开始就放双星旋进动画"）。
    # **这个 pane 本来就有**：`pane_motif_binary`（`school_motifs.binary`，抬头就是"双星旋进"），
    # 它原来排在 60.57（`Give you all the simulations`）——只是**晚了一句歌词**。
    # 我第一版另造了一个 `pane_binary_star` 插在 58.65，那是重复造轮子（已撤）。
    # 现在把 `pane_landmark_dialogue` 那一行截到 58.65，双星从这一句起、一路连到 64.29。
    dict(at=58.65, name="pane_motif_binary", lyric="If I can, if I can",
         ops=["GRAV", "MERGE"], mascot=False, sub="\u8f68\u9053\u8d8a\u8f6c\u8d8a\u8fd1"),
    # **GPU 像素排序挪到 `You have made some`（128.42）**（批 124，清单第 35 条：
    # "GPU 像素动画挪到后面"）。它原来在 64.29（`Be your only satisfaction`），
    # 那个位置现在给了 YOLO 打标。
    dict(at=128.42, name="pane_motif_pixelsort", lyric="You have made some",
         ops=["PIXELSORT", "\u6392\u5e8f"], mascot=False, end=130.74,
         sub="\u6211\u8bd5\u56fe\u6e32\u67d3\u5fc3\u7eea"),
    # **`Illegal arguments`（130.74）→ IEEE-754**（批 127，清单第 52 条："illegal arguments
    # 歌词处动画框内改为：IEEE-754 精度丢失 → Infinity → NaN 的动画演出"）。
    # 到 136.90（学院闸门）为止；批 124 为了不留空洞临时让像素排序顶到 136.90，
    # 并在 `_dev/row_probe.py` 的 `LONG_OK` 里留了一条写"暂时"的理由——**现在切开了，
    # 那条理由要删掉**。
    dict(at=130.74, name="pane_ieee754", lyric="Illegal arguments",
         ops=["IEEE-754", "Inf", "NaN"], mascot=False, end=136.90,
         sub="\u7cbe\u5ea6\u4e22\u5931  \u2192 Infinity \u2192 NaN"),
    # Acts 1 and 2 only (`max_phase=1`): `unite` shows the hands approaching and `deeply` the star
    # between them. **Act 3 - the star alone - is its own row at 84.60**, on the lyric `02b §3.3` pins
    # it to; it used to be the tail of this row, which put "只剩那颗星" under `If I can, if I can` at
    # ~57 s. See `pane_landmark_dialogue`.
    # **拆成两句**（批 148，清单2 第 5 条）：用户："目前歌词 And we can unite, so deeply so deeply
    # 对应的动画为对话雕塑。现在修改为：歌词 And we can unite 对应对话雕塑，so deeply so deeply
    # 对应动画调整为衍射星芒"。
    # 原来这一行 54.74-58.65 一句 `pane_landmark_dialogue` 盖住了两句歌词，现在在 56.79
    # （`So deeply, so deeply` 的时刻）切开：前一句留雕塑，后一句给星芒。
    dict(at=54.74, name="pane_landmark_dialogue", lyric="And we can unite",
         ops=["UNITE", "\u5bf9\u8bdd"], mascot=False, end=56.79,
         args=dict(max_phase=1), sub="\u4eba\u673a\u534f\u540c\uff0c\u8fd9\u662f\u300c\u5408\u300d"),
    dict(at=56.79, name="pane_motif_stardiff", lyric="So deeply, so deeply",
         ops=["DIFFRACT", "星芒"], mascot=False, end=58.65,
         sub="\u661f\u5149\u4e00\u70b9\uff0c\u644a\u6210\u4e00\u7247\uff0c\u6df1\u9083\u7470\u4e3d"),
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
    # **双星在 `simulations` 这一句合体、然后停住**（批 134，用户："双星旋进的动画也要改，
    # 其在 simulations 歌词时停止"）。原来这两行都叫 `pane_motif_binary`、一路连到 64.29，
    # 并合被推到很后面；现在**第二行只到 62.41**，`binary` 按"这一行自己的跨度"算相位
    # （`school_motifs._row_here`），所以并合正好落在 60.57——`Give you all the simulations`
    # 这一句上，之后画的是并合后的残骸（一颗亮星 + 一圈扩散的环，随拍脉动）。
    dict(at=60.57, name="pane_motif_binary", lyric="Give you all the simulations",
         ops=["0101", "模拟"], mascot=False, end=62.41, sub="\u5c06\u878d\u5408\u7684\u59ff\u6001\u6a21\u62df"),
    # 62.00-70.00 was the cat, held for eight seconds across five different lines - including "I will run
    # the execution", which is not a cat. The cat belongs on the two lines that *are* a cat (80.93,
    # below); here the hands carry "Then I can / satisfaction" and the conditional device carries
    # "If I can make you happy / I will run the execution", which is an `If ... then ...` like all the
    # others the device is for.
    # **`Be your only satisfaction`（64.29）→ YOLO + 打标**（批 124，清单第 35 条：
    # "动画改为 yolo 模型 + 打标（标签含 satisfaction 等满意程度）的动画图示，
    # GPU 像素动画挪到后面"）。原来这一行是 `pane_motif_pixelsort`（GPU 像素排序），
    # 按用户要求挪到后面——`You have made some`（128.42）那一处。
    # **YOLO 改成对应 `Then I can, then I can` + `Be your only satisfaction`**（批 134）：
    # 用户："yolo动画改为与歌词 then I can, then I can, be your only satisfaction 对应"。
    # `Then I can, then I can` 在 **62.41**，`Be your only satisfaction` 在 64.29、下一句
    # `If I can make you happy` 在 66.17——所以这一行从 64.29 **提前到 62.41**、**跨两句歌词**，
    # 到 66.17 为止（3.76 s，比原来的 1.88 s 宽裕，三拍因此重新配时）。
    dict(at=62.41, name="pane_yolo", lyric="Then I can, then I can",
         ops=["YOLO", "satisfaction"], mascot=False, end=66.17,
         sub="\u6ee1\u610f\u5177\u6709\u6700\u9ad8\u7f6e\u4fe1\u5ea6"),
    dict(at=66.17, name="pane_motif_galaxy", lyric="If I can make you happy",
         ops=["GALAXY", "星系"], mascot=False, sub="\u661f\u661f\u6309\u5f15\u529b\u6392\u961f"),
    dict(at=70.02, name="pane_motif_en_limit", lyric="Though we are trapped",
         ops=["存在n", "LIMIT"], mascot=False, sub="\u88ab\u56f0\u4f4f\u5728\u6536\u655b\u503c"),
    # 万物皆点 is three couplets - eggplant, tomato, cat - and the film cuts on each one. All three panels
    # held for 11.07 s was the user's example of a performance that outlasts its lyric ("右边panel的西红柿
    # 那个光谱界面占了过长时间，和左侧歌词都不对应了"): the spectrum was still on screen while the words
    # had moved on to the cat. Now each panel gets its own couplet, and the cat - which had the wrong row
    # entirely - gets the two lines about a tabby.
    # **抬头随内容一起改**（批 159，清单2 第 11 条）：这一格从"田间-加工-运输"的物流链改成了
    # "茄子在人体内分解的路径及产物"，而抬头原来还写着"茄子的营养：从土壤一路到餐桌"——
    # 那句话描述的是**已经不存在的那张图**（批 98e 的规矩：抬头必须和里面画的东西一致）。
    dict(at=73.53, name="pane_everything_point", lyric="If I'm an eggplant",
         ops=["\u53e3\u8154", "\u80c3", "\u5c0f\u80a0", "\u5927\u80a0"], mascot=False,
         args=dict(panel="food"),
         sub="\u4e00\u6839\u8304\u5b50\u7ecf\u4eba\u4f53\u6d88\u8017\uff0c\u80fd\u91cf\u9010\u7ea7\u51cf\u5c11"),
    dict(at=77.16, name="pane_everything_point", lyric="If I'm a tomato",
         ops=["444nm", "472nm", "503nm"], mascot=False, args=dict(panel="tomato"), sub="\u756a\u8304\u5438\u6536  444/472/503 nm"),
    dict(at=80.93, name="pane_landmark_cat", lyric="If I'm a tabby cat",
         ops=["\u732b\u5b66\u957f", "\u5b57\u7b26\u753b", "\u53e0\u52a0\u6001"], mascot=False, sub="\u53c8\u751f\u53c8\u6b7b\u7684\u53e0\u52a0\u6001"),
    # 84.6-110.4 is the last verse's "only God / switch my gender / trance" run: the switch lines belong to
    # the swap pane (a gender switch is the same three-bit flip as a current switch), the "if I can / feel
    # your vibrations" lines to the conditional device, and "finally be completion" to the Love class - the
    # expression completed. One pane per thought, instead of a hand and a crest held over all of it.
    # ...and the third act of the hands on the line `02b §3.3` pins it to: the star alone, hands gone.
    # The user's ruling on the placement question the audit raised ("02b §3.3 把它钉在 84.60"):
    # **84.60, on `If I'm the only God`**. `stardiff` follows on the next line, where a star as the
    # *proof of an existence* is the reading it was always meant to carry.
    #
    # **已换成斯宾诺莎的证明**（批 128，清单第 41 条）：用户："if I'm the only god 歌词对应的动画框
    # 一闪而过对话雕塑，请删除，这段歌词对应的动画改为 斯宾诺莎对于上帝为唯一实体（∃!）的证明"。
    # 那一闪而过的就是这条 `pane_landmark_dialogue` 的 `phase=2`（"手放下了，只剩那颗星"）。
    # `pane_landmark_dialogue` 本身没删——它还在 54.74 那一行演"两只手"。
    # **两句都归斯宾诺莎**（批 148，清单2 第 5 条）：用户："原来衍射星芒动画删除（当前对应歌词
    # then you're the proof of my existence），改为歌词 If I'm the only god, then you're the
    # proof of my existence **两句均对应斯宾诺莎证明的动画**（注意展示速度要调）"。
    # 所以 86.21 那一行的 `pane_motif_stardiff` 删掉，并进这一行（84.60-88.34，3.74 s）；
    # `pane_spinoza` 里的步长原本按 1.61 s 配的，也一并按行时长铺开（见 `pane_spinoza`）。
    dict(at=84.60, name="pane_spinoza", lyric="If I'm the only God",
         ops=["E!", "SUBSTANCE"], mascot=False, end=88.34,
         sub="E! 1 \xb7 \u795e\u662f\u552f\u4e00\u5b9e\u4f53"),
    # **`switch my gender` + `to F, to M` 两句 = 集合 F 与 M 的文氏图**（批 146，清单2 第 6 条）。
    # 用户："To F, to M的前一句是 switch my gender，我要求的是文氏图对应 switch my gender,
    # to F to M 两句，和 switch my current 没有任何关系"。
    #
    # 所以这一行**按 89.91 那一句的后边界 91.44 切**（`And then do whatever` 在 91.44，
    # 它属于 `from AM to PM` 那个钟面，归下一行），一行正好盖住这两句。
    # 原来这一行的 `pane_motif_quantize`（`2^53` 浮点量化）**没有别的行用它**——见下面那条记录。
    dict(at=88.34, name="pane_exchange", lyric="Switch my gender",
         ops=["F", "M", "\u96c6\u5408"], mascot=False, end=91.44,
         args=dict(panel="venn"), sub="\u76f8\u5f02\u53c8\u76f8\u4ea4"),
    # 钟面从 **91.44** 起（原来 92.00）：`And then do whatever, from AM to PM` 是两句，
    # 前一句 91.44 原来落在那条量化行里。`panel=clock` 由 93.52 的钉子钉上（见 `THEME_PINS`）。
    dict(at=91.44, name="pane_motif_chladni", lyric="From AM to PM",
         ops=["CHLADNI", "节点"], mascot=False, sub="\u4ece\u65e9\u5230\u665a\uff0c\u4e00\u5929\u88ab\u8986\u76d6\u4e24\u6b21"),
    # **两句都归监察博弈**（批 150，清单2 第 8 条）：用户："目前歌词 Oh, switch my role 对应
    # fork炸弹动画，去掉该动画，改为歌词 Oh, switch my role, to S to M **两句歌词均对应监察博弈
    # 动画**（相应播放速度、SM字符交替闪烁要调整）"。
    #
    # 所以原来这一行的 `pane_motif_fork_bomb` 撤掉、并进下一行，`pane_supervisory` 从 97.32
    # **提前到 95.28**，一行 95.28-98.93（**3.65 s**，原来它只有 1.61 s）。
    # fork 炸弹没有删代码，按用户要求**转移到学院部分**（见 167.75 那一行）。
    #
    # `pane_supervisory` 里的 S/M 交替闪烁与双方换选是写死 0.8 s / 1.6 s 的，行长了之后
    # 会显得碎——已改成按行时长铺开（见 `pane_supervisory`）。
    dict(at=95.28, name="pane_supervisory", lyric="Oh, switch my role",
         ops=["S", "M", "支付矩阵"], mascot=False, end=98.93,
         sub="\u59d4\u6258\u4eba  S / \u4ee3\u7406\u4eba  M"),
    dict(at=98.93, name="pane_motif_lattice", lyric="So we can enter",
         ops=["LATTICE", "TRANCE"], mascot=False, sub="向消失点收缩，入口在深处"),
    dict(at=101.13, name="pane_motif_moire", lyric="The trance, the trance",
         ops=["MOIRE", "TRANCE"], mascot=False, sub="\u4e24\u5c42\u6805\u683c\u9519\u5f00\uff0c\u4ee4\u4eba\u604d\u60da"),
    # The superellipse played twice (here and in the 互换 panel at 50.95). The user's rule is
    # once, so this slot is the resonance curve - the row covers "Feel your vibrations" (batch 34).
    dict(at=103.03, name="pane_motif_resonance", lyric="If I can, if I can",
         ops=["f0", "RESONANCE", "Q=6"], mascot=False, sub="\u6211\u4e0e\u4f60\u540c\u9891\u5171\u632f"),
    dict(at=106.84, name="pane_motif_epicycles", lyric="Then I can, then I can",
         ops=["EPICYCLE", "FOURIER"], mascot=False, sub="\u4e00\u4e2a\u5706\u5957\u4e00\u4e2a\u5706\uff0c\u753b\u51fa\u5b8c\u6574\u7684\u5fc3"),
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
    # **学院部分再拆一次**（批 150，清单2 第 8 条）：用户："fork炸弹动画转移到学院部分，
    # 当前动画 one path 对应歌词 then I can then I can, be your only execution，现在改为
    # 歌词 then I can then I can 对应动画 one path，歌词 be your only execution 对应 fork炸弹"。
    #
    # 原来这一行 166.05-169.61 是 `pane_motif_one_path`，但它一句盖住了两句歌词
    # （`Then I can, then I can` 在 166.05、`Be your only execution` 在 167.75）。
    # 在 **167.75** 切开：前半留给 one path，后半换成 fork 炸弹（从学校段 95.28 挪过来的那个）。
    dict(at=166.05, name="pane_motif_one_path", lyric="Then I can, then I can",
         ops=["ONE PATH", "唯一执行"], mascot=False, end=167.75,
         sub="十六个分支，只亮一条路"),
    dict(at=167.75, name="pane_motif_fork_bomb", lyric="Be your only execution",
         ops=["FORK", "角色"], mascot=False, end=169.61,
         sub="同一个函数调用自己：一次变两个、两个变四个"),
    dict(at=169.61, name="pane_backlog", lyric="If I can have you back",
         ops=["SCRUM", "TODO", "DOING", "DONE"], mascot=False, sub="\u628a\u4f60\u4ece  DONE \u632a\u56de  TODO"),
    # The four AI motifs. They are laid out around `shot_collapse` (174.90-177.50), which the TUI draws
    # full-bleed *in this variant too* - the film's picture collapses into a line and a dot, and there is
    # no chrome left to draw a pane in. The first version of this table put `pane_ai_rl` at 175.31, where
    # the column is empty for its whole life and the pane is simply not on screen. Two motifs before the
    # collapse and two after it also gives that moment something to divide.
    dict(at=171.31, name="pane_ai_cnn", lyric="If I can have you back",
         ops=["CONV", "KERNEL", "FEATURE MAP"], mascot=False, sub="\u7279\u5f81\u56fe  \xb7 \u5377\u79ef\u6838\u626b\u4e00\u904d\uff0c\u8ba4\u51fa\u8fd9\u6bb5\u56de\u5fc6"),
    dict(at=173.10, name="pane_ai_attention", lyric="Though we are trapped",
         ops=["Q", "K", "V", "SOFTMAX"], mascot=False, end=174.90, sub="\u6743\u91cd\u77e9\u9635  \xb7 Q \u5728  K \u91cc\u627e\u6700\u50cf\u7684\u90a3\u4e00\u6bb5"),
    # the film's own collapse, 174.90-177.50, with no pane behind it: `shot_collapse` is drawn
    # full-bleed in this variant too, so a name here would be a pane nobody can see
    dict(at=174.90, name=None, lyric="Though we are trapped", ops=["COLLAPSE"], mascot=False,
         end=177.50),
    dict(at=177.50, name="pane_ai_rl", lyric="I've studied, I've studied",
         ops=["POLICY", "ROLLOUT", "ADVANTAGE"], mascot=False, sub="\u5956\u52b1  \xb7 \u8bd5\u5f88\u591a\u904d\uff0c\u53d6\u4f18\u52bf\u6700\u5927\u7684\u90a3\u6761"),
    dict(at=179.30, name="pane_ai_diffusion", lyric="I've studied, I've studied",
         ops=["NOISE", "DENOISE", "\u6b65\u6570"], mascot=False, sub="\u53bb\u566a  \xb7 \u4ece\u566a\u58f0\u91cc\u4e00\u6b65\u6b65\u627e\u51fa\u4f60"),
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
         mascot=False, sub="\u81ea\u7531\u65f6\u5149\u4e5f\u5f97\u6392\u8fdb\u7518\u7279\u56fe"),
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
    # **这两行的前半段已经不是 MEMORY 了**（批 164，用户："113.75-114.75 和 114.75-115.90 原本
    # memory 处，现在是 2^53，把 pane_memory 改了，抬头写成
    # `2^53 · IEEE-754 double 的边界 · 你的记忆已超上限`"）。
    # 批 161 把 `pane_memory` 的后半段换成了 `2^53` 的量化（`MEMORY_FULL_AT = 113.75`），
    # 但这两行的抬头还写着 MEMORY 的那句——抬头和内容对不上了。现在改成用户给的那句。
    dict(at=113.75, name="pane_memory", lyric="You have left",
         ops=["2^53", "IEEE-754"], mascot=False, args=dict(layers=5),
         sub="\u4f60\u8d70\u4e00\u6b21\uff0c\u5c31\u591a\u53e0\u4e00\u5c42"),
    dict(at=114.75, name="pane_memory", lyric="You have left",
         ops=["2^53", "IEEE-754"], mascot=False, args=dict(layers=6),
         sub="\u4f60\u8d70\u4e00\u6b21\uff0c\u5c31\u591a\u53e0\u4e00\u5c42"),
    # "You have left me in isolation": the field emptying, one point left
    dict(at=115.90, name="pane_isolation", lyric="You have left me in isolation",
         ops=["ISOLATION", "\u4e00\u4e2a\u70b9"], mascot=False, sub="in isolation \xb7 \u53ea\u5269\u4e00\u4e2a\u70b9\uff0c\u5b64\u7acb\u4e8e\u8bb0\u5fc6\u7684\u89d2\u843d"),
    # ...and then the plate mode, in the slot the single-layer MEMORY used to hold. The count 2-3-4-5-6
    # is the sculpture's own idea and it is intact; `layers=1` was a callback on a different lyric
    # ("If I can, if I can"), so it is the row that costs the design least - and "memory 部分有点长了" is
    # the user's own reading of the same thing.
    dict(at=117.95, name="pane_motif_bessel", lyric="If I can, if I can",
         ops=["BESSEL", "\u5706\u677f\u6a21\u6001"], mascot=False, sub="\u8bbe\u60f3\u8282\u5f84\u5728\u8bb0\u5fc6\u6df1\u5904\u6446\u52a8"),
    # "Erase all the pointless fragments": the instruction carried out, cell by cell
    dict(at=119.81, name="pane_fragments", lyric="Erase all the pointless fragments",
         ops=["ERASE", "\u788e\u7247"], mascot=False, sub="\u6e38\u6807\u4e00\u884c\u884c\u5220\uff0c\u8bb0\u5fc6\u7684\u788e\u7247\u5c31\u6b64\u6d88\u5931"),
    # closing: the crest alone
    dict(at=193.46, name="pane_landmark_crest", lyric="[gap] \u5c3e\u58f0",
         ops=["NWPU", "\u516c\u8bda\u52c7\u6bc5"], mascot=False, ),
]

# how many rows of the right-hand column each pane wants, and the least it can be drawn in. The film
# carries the same pair per pane (`draw_body`'s `need`/`least`); a pane that cannot get `least` rows
# hands them back to the ops ticker rather than appearing as an empty box.
PANE_MIN = {
    # **`互换`这一屏要高一点**（批 122）：`gate` 面板现在画的是 CMOS 晶体管级电路
    # （VDD / PMOS / NMOS / GND 竖着叠），`_ex_gate` 在 `bh < 10` 时直接返回、一屏全空。
    "pane_exchange": (14, 8),
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


# ---------------------------------------------------------------- 学校自己的切点（批 97，E6）
#
# **这是"总体演出"这件事的关键**：整片的时间结构本来是上游的 97 shot 表
# （`tui_live._LAST_SHOT` 判定"换镜了"，学校排期只是在它上面稀疏地换右栏的 pane）。
# 也就是说，观众看到的"节奏"是原片导演的节奏。这一节让学校**自己也有刀**：
#
#   自一个 pane 出现起，只要遇到一个"学校自己的切点"，就触发一次转场——
#   于是右栏的每一次换图都变成一次**画面事件**，而不是"内容悄悄换了"。
#
# 候选怎么来的（Q3 = 效果至上，不预设数量）：取 **pane 行的边界**（每张图该换的时刻），
# 去掉上游 shot 表已经在那里切过的（那些本来就切了）、去掉间隔太近的（< 0.35 s 的两次切会
# 互相盖掉），剩下的吸到最近的拍上（`BEAT_SNAP` 之内）。候选**先量后用**：
# `_dev/school_cut_probe.py` 会报"切点落拍率、数量、最小间隔"，数量由那条曲线决定。
SCHOOL_CUT_MIN_GAP = 0.45
SCHOOL_CUT_SNAP = 0.23
#: 和上游的刀（或另一把学校刀）近到多少秒以内就**不算自己的一刀**——那是同一刀。
#: 实测教训（`_dev/school_cut_probe.py` 第一版）：吸拍会让一个"名义上离上游 0.1 s 远"的边界
#: **正好落到上游那一刀上**，合并后最小间隔 0.004 s，等于同一时刻排了两次转场。
SCHOOL_CUT_CLASH = 0.15


def school_cuts() -> list[float]:
    """学校自己的切点（秒），升序；每次调用都从表算，表小，代价可忽略。"""
    import tui_live as T
    rows = shot_rows()
    cuts: list[float] = []
    upstream: list[float] = []
    _prev: dict | None = None          # 上一行（判"是不是同一个 pane 被排成多行"）
    try:
        upstream = sorted(float(e["start"]) for e in T.Engine().table)
    except Exception:
        pass

    def _clash(t: float) -> bool:
        return any(abs(t - u) < SCHOOL_CUT_CLASH for u in upstream) or \
            any(abs(t - c) < SCHOOL_CUT_CLASH for c in cuts)

    for r in rows:
        at = float(r["at"])
        if at <= 1.0:
            continue
        # **同一张画被排成多行时，行边界不是切点**（批 126，用户："双星旋进动画内部有个
        # 切换特效，删掉"）。双星是 58.65 与 60.57 两行，都叫 `pane_motif_binary`——画的是
        # 同一张画在继续演，中间那次"切"就成了**动画内部的切换特效**。
        # 判据用 `T._pane_id`（**含 `panel`**）：`pane_exchange` 的五个面板同名但 `panel` 不同，
        # 那五处**是**切点；只用 `name` 会把它们也跳掉。
        if _prev is not None and T._pane_id(_prev) == T._pane_id(r):
            _prev = r
            continue
        _prev = r
        k, bt = T.beat(at)
        if k < 0:
            continue
        if abs(bt - at) > SCHOOL_CUT_SNAP:
            continue
        t = bt
        if _clash(t):
            continue                      # 上游已经（或几乎）在这里切了：那本来就是一次画面事件
        if cuts and t - cuts[-1] < SCHOOL_CUT_MIN_GAP:
            continue
        cuts.append(round(t, 4))
    return cuts


_PLAN: list = [None]


def cut_plan() -> list[float]:
    """缓存版（`fx_cut` 每帧问一次也不贵，但没理由每帧重算）。"""
    if _PLAN[0] is None:
        try:
            _PLAN[0] = school_cuts()
        except Exception:
            _PLAN[0] = []
    return _PLAN[0]


#: 最近一次学校切点的时刻（`tui_live.draw` 每次触发时写），与拉开时长。
#: 见 `draw_scene_pane` 的说明：切点必须有**学校自己的可视标记**，否则它在生产路径下是隐形的。
SCHOOL_WIPE_AT: list = [None]
SCHOOL_WIPE_S = 0.30


def cut_here(t: float, prev_t: float) -> float | None:
    """`(prev_t, t]` 之间有没有学校自己的切点？有就返回它的时刻（用于把这次转场的起点钉在拍上）。"""
    if t < prev_t:                        # 回退/跳转：这一帧不触发
        return None
    last = None
    for c in cut_plan():
        if prev_t < c <= t:
            last = c
    return last


#: **主题钉死**（批 98c）。用户点名的错配：*"时钟旋转动画没有对应到歌词 from am to pm，
#: FM切换动画也没有对应到 to f to m"*。原因是这些动画**已经在代码里**（`pane_exchange` 的
#: `panel=clock` 是 12 小时钟面、`panel=bits` 是 F→M 翻三位），但排期把它们放在了别的歌词行上：
#: 钟面在 "To AC, to DC"(45.52)，F→M 在 "Switch my current"(44.04)，
#: 而 "From AM to PM"(93.52) 给的是 chladni、"To F, to M"(89.91) 给的是 quantize。
#:
#: 这张表是**作者级**的裁决：`(歌词行时刻, 该行必须画的 pane/panel)`。`row_at` 之后由
#: `school_entry` 应用——所以它优先于通用排期，但只覆盖被点名的这几行，其余照旧。
#: 它同时是**可复现**的（常量表），并且 `_dev/lyric_pane_probe.py` 会把它列出来核对。
THEME_PINS: list[tuple[float, str, str, str]] = [
    # 12 小时钟面 = 一天的双覆盖 —— 只在字面讲时间的这一行
    (93.52, "pane_exchange", "clock", "12 小时钟面：一天被这半圈覆盖两次"),
    # F→M：**改成集合 F 与 M 的文氏图**（批 146，清单2 第 6 条：用户："F→M动画（对应歌词
    # switch my gender, to F to M），当前为数 F 和 M 的异或运算，感觉和歌词不搭。改为集合 F 和
    # 集合 M 相交的文氏图。集合 F 和 M 的圆框交替闪烁，下方写运算：F ∪ M = Human，F ∩ M = LOVE?"）。
    #
    # **这一格不再用钉子，改用排期行自己的 `args`**：用户随后澄清"文氏图对应 switch my gender,
    # to F to M **两句**"——而钉子只能钉它命中的那一行，89.91 那一句的后边界是 91.44，
    # 所以直接把 88.34-91.44 那一行改成 `pane_exchange` + `panel="venn"` 最直接
    # （钉在 89.91 也行，但两处说同一件事就多了一个会走样的地方）。
    #
    # **`panel="bits"`（`0x46 XOR 0x4D = 0x0B`）现在没有任何地方渲染它了**：排期里 41.92 那一行
    # 虽然写着 `panel="bits"`，但 41.92 被钉成了 `gate`（逻辑门，见下面那条），
    # 所以异或只在 89.91 出现过一次——那一次就是用户要换掉的那一次。
    # `_ex_bits` 的代码留着，它没有被删，只是暂时没有排期引用它。
    # 逻辑门 / 晶体管 —— **清单第 23 条**："歌词 switch my current 处改为逻辑门开关示例
    # （晶体管构成）"。原来这一处钉的是 `bits`（F→M 三位取反），而"三位取反"那件事对应的歌词是
    # 后面的 `To F, to M`（**清单第 21 条**：'F->M 三位取反应放在后面歌词 to f to m（实际上
    # 已经有了）'）——所以 `bits` 不该留在这里，它的行在 89.91，那里才是它的位置。
    (41.92, "pane_exchange", "gate", "PMOS 在上 · NMOS 在下 · 中间出 Y"),
    # AC/DC：电流的两个名字 —— **内容改成交流/直流示意**（批 119，清单第 25 条："scene18 歌词
    # to ac to dc，但动画框抬头你写的是超椭圆，动画框内展出应当是直流、交流电示意，请修改抬头
    # 及内容"）。原来钉的是 `hyper`（超椭圆），与歌词无关；现在换成 `acdc`
    # （`school_scenes._ex_acdc` = 全波整流 + RC 滤波，抬头"交流 → 直流"）。
    (45.52, "pane_exchange", "acdc", "交流变直流：整流 → 滤波"),
    # **时间线**（清单第 29 条）："scene 20 当前为超椭圆，改为时间线，歌词 if we can travel 展示
    # 时间线西工大校史，to ad to bc 展示西工大所在西安的公元前后历史"。两个 pane 行分别钉，
    # `_ex_timeline` 按时刻自己切两段内容——**不合并成一行**（批 119 的教训：一行演两张画会叠）。
    (50.95, "pane_exchange", "timeline", "一条路走到今天：1938 → 1957 → 1970 → 2006"),
    (52.99, "pane_exchange", "timeline", "同一块地方，换了三个名字：汉长安 → 唐长安 → 西安"),
    # 角色 S/M：字形互换 —— 与 F→M 是同一台机器上的另一次翻位。
    # **批 133 撤掉了这条钉子**（清单第 31 条）：`To S, to M`(97.32) 改成**监察博弈支付矩阵**
    # （新 pane `pane_supervisory`），不再是"一个字的两个身份"。钉子留着会把新 pane 顶掉。
    # 字形互换那件事本身还在 `pane_exchange` 的 `letters` 面板里，只是不再占这一句歌词。
]
# **注意：不要再给 47.27（辫群）加钉子**（批 119 我加过一次，立刻出错）：`pinned_row` 的匹配方式
# 是"哪一行的 `at..end` 覆盖这个时刻"，而它取的是**排期表里那一行的跨度**；47.27 那一行**自己
# 已经写着 `args=dict(panel="braid")`**，再钉一次只会把 `49.11` 那条 `so dizzy` 行**盖掉**
# （钉子记录的 `end` 是 47.27 那行的 end=49.11，于是 49.6 也落进钉子、`panel` 被改成 braid，
# 叶序就画不出来）。钉子只用来**纠正歌词与面板不对应**，不需要纠正的行不要钉。


_PINS: dict = {}


def pinned_row(at: float) -> tuple[float, dict] | None:
    """`at` 落在某一行里、而那一行被主题钉死了吗？返回 `(那一行的开始时刻, 替换后的行)`。

    **按"哪一行覆盖这个歌词"匹配，而不是"哪一行的 at 恰好等于歌词时刻"**：像 "To F, to M"(89.91)
    落在 88.34 那一行里（那一行是 `Switch my gender` 起的），它的 `at` 永远不等于 89.91。
    第一版按等值匹配，于是四个钉子里只有一个生效（`_dev/pin_debug.py` 量的）。

    解析一次存进 `_PINS`：**逐帧调用要便宜**（一个字典查表），而且表是常量。
    """
    if not _PINS:
        rows = shot_rows()
        for ts, pane, panel, sub in THEME_PINS:
            for r in rows:
                if r["at"] <= ts < r["end"]:
                    out = dict(r)
                    out["name"] = pane
                    out["args"] = dict(out.get("args") or {}, panel=panel)
                    out["sub"] = sub                      # 副标题也要换成这张图自己的说法
                    out["_pinned_for"] = ts
                    _PINS[round(float(r["at"]), 4)] = out
                    break
    # **取"不超过 `at` 的最大 key"**。第一版写了 `next(... for k in sorted(...) if k <= at)`，
    # 那取到的是**最小**的 key——于是 88/89/93 那三行全部拿到 45.52 那一行，
    # 表现就是"四个钉子里只有一个生效"（`_dev/pin_debug.py` 量出来的）。
    best = None
    for k in sorted(_PINS):
        if k <= at + 1e-6:
            best = k
        else:
            break
    return None if best is None else (best, _PINS[best])


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
    # **主题钉死优先**（批 98c）：用户点名的"时钟没对应到 from am to pm"那几行，在这里被换成
    # 字面对应的那张图（见 `THEME_PINS`）。它只覆盖被点名的行，其余排期不动。
    pin = pinned_row(row["at"])
    if pin is not None and abs(pin[0] - float(row["at"])) < 0.02:
        # 只有"当前这一行正是被钉死的那一行"才替换。`pinned_row` 返回的是"≤ 这个时刻的最近一条"，
        # 所以这里必须再比对开始时刻，否则那一行的图会一直延续到它后面的所有行上
        # （第一版就是这样：四个钉子里只有第一个行 45.52 生效，其余全落回通用排期）。
        pin_row = pin[1]
        need, _least = PANE_MIN.get(pin_row["name"], (10, 4))
        e.update(pane=pin_row["name"], pane_need=need, ops=pin_row["ops"],
                 pane_args=pin_row.get("args"), pane_sub=pin_row.get("sub", row.get("sub", "")))
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

    **学校自己的切点要看得见**（批 97c）。第一版把切点做成"重新揭示一次 `u`"，实测在生产路径下
    **完全看不出**（`_dev/school_cut_probe.py --at 30` = 0 格差异）：上游新镜头覆盖时
    `school_entry` 返回的是 `base`，右栏改由**上游自己**画，新旧内容一模一样。

    第二版把拉开标记写在这里，**也是错的**：那是同一条原因的另一种形式——只要当前不在学校的
    overlay 行上，这个函数根本不会被调用。所以拉开标记最后落在 `tui_live.fx_school_wipe`，
    它由播放器在"整帧画完之后"调用，**不管右栏是谁画的都生效**。
    """
    _CO.PANE_SUB[0] = sub
    drawn = False
    try:
        # **IF/THEN 框挂在最外层**（批 108）：这是右栏的入口，而下面两条快捷路径
        # （课程图 / 仪表）会提前 `return`、绕过 `school_scenes.draw_pane`——
        # 探针第一版量出"只有 5/10 对两格都亮"，缺的正是走那两条路径的 pane。
        if _CO.draw_course(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane),
                           total=len(EXEC_PANES)):
            drawn = True
        elif _CO.draw_gauge(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane)):
            drawn = True
        else:
            drawn = _SC.draw_pane(pane, s, x0, y0, x1, y1, t, lt, dur, u, args=args)
    finally:
        # **框已移到 `tui_live.draw`（批 110）**：`school_entry` 返回 base 的那些行右栏由**上游**
        # 自己画、这个函数根本不会被调用，于是 162-175 s 那几句 `If I can, if I have you back`
        # 上没有框（探针 SCOPE FAIL）。挂在"整帧画完之后"就与"谁画的右栏"无关——
        # 与 `fx_school_wipe` 同一个理由、同一处位置。
        # **这里不再画框**（批 114）：`_dev/pane_probe.py` 直接调这个函数（不走 `draw()`），
        # 需要框来做它的 `NO HEADER SUB` 判断，于是我在这里又画了一次——但这一份用的是
        # `y0+2`（与主路径的 `IFTHEN_TOP_ROW` 不同行），**而且从不擦**，于是主路径擦干净之后
        # 屏幕上还留着一份、`ifthen_scope_probe` 在 44.08 一直报"该无框却有框"。
        # 探针要的东西改由**探针自己**准备（它在 `draw_pane` 之外单独调 `_ifthen_frame`），
        # 生产路径只有一个画框的地方，擦与画就不会再错位。
        _CO.PANE_SUB[0] = ""
    return drawn


#: "IF/THEN 框画失败"只报一次的开关（见 `draw_scene_pane`）。
_IFTHEN_BROKEN = False


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
