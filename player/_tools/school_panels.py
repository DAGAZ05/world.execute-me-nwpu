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
# Fourteen courses, twelve hits: 数据结构 and 算法设计 share a drawing because they share a *picture*
# (a red-black tree whose heights prove the O(log n)), and 工业模型 / 大型工业软件 take two of the
# three numbers in the countdown rather than being crammed into a hit that is already full.
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
    ("pane_exec_industrial", "\u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6"),
    ("pane_gauge_fem", "\u5de5\u4e1a\u6a21\u578b \u00b7 FEM"),
]

GAUGES = list(_CO.GAUGE_PANES)

# the three countdown numbers: each is a lyric line of its own, and each carries two instruments
GAUGE_SLOTS = [(148.79, 149.66, "ein, dos"), (149.66, 150.45, "trios, ne"),
               (150.45, 151.51, "fem, liu")]
EXEC_FROM, EXEC_TO = 147.52, 162.23      # the first "Execution" hit to the end of the reprise


def _exec_rows() -> list[dict]:
    """Fourteen courses and six instruments, laid out so that no two panes ever share a second.

    The song gives twelve "Execution" hits 0.87-1.07 s apart and three countdown numbers, and this
    variant has fourteen courses and six instruments. Fourteen plus six does not go into twelve plus
    three, and two earlier attempts at forcing it both failed in ways worth recording:

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
    """
    # 1. the instruments, disjoint by construction
    gauge_rows = []
    for g, (at, end, lyric) in enumerate(GAUGE_SLOTS):
        half = (end - at) / 2
        for side in (0, 1):
            j = g * 2 + side
            pane = GAUGES[j]
            gauge_rows.append(dict(at=at + side * half, end=at + (side + 1) * half, name=pane,
                                   lyric=lyric, course=_CO.COURSES.get(pane, (pane,))[0],
                                   ops=[pane], her=False, exec_n=0, gauge=g + 1))

    # 2. the free intervals the instruments left, and the courses spread evenly across them
    free = []
    cur = EXEC_FROM
    for at, end, _l in GAUGE_SLOTS:
        if at > cur:
            free.append((cur, at))
        cur = max(cur, end)
    if EXEC_TO > cur:
        free.append((cur, EXEC_TO))

    course_rows, i = [], 0
    for a, b in free:
        if i >= len(EXEC_PANES):
            break
        left = len(EXEC_PANES) - i
        # how many courses this gap carries: proportional to its length, at least one
        later = sum(bb - aa for aa, bb in free[free.index((a, b)) + 1:])
        share = max(1, int(round(left * (b - a) / max(1e-6, (b - a) + later))))
        take = min(left, share)
        step = (b - a) / take
        for j in range(take):
            pane, course = EXEC_PANES[i + j]
            course_rows.append(dict(at=a + j * step, end=a + (j + 1) * step, name=pane,
                                    lyric="Execution", course=course, ops=[course],
                                    her=False, exec_n=i + j + 1))
        i += take
    return course_rows + gauge_rows

# ---------------------------------------------------------------- the school's own shot table
#
# The film has 97 shots. This variant does not need a different *cut* under every lyric line - it
# needs a different *panel* under the lines whose subject moved. So the shot table here is a sparse
# overlay: a row says "from this lyric line to the next, the right-hand column draws this pane".
# Between rows the film's own 97-shot table still runs, unchanged, which is what keeps the cuts,
# the lyric band, the word-level typing and the ops ticker working without being reimplemented.
#
# `at` is the *lyric* time (input/lyrics.lrc). `name` is the pane in school_scenes; `ops` is what
# the ticker scrolls under it; `her` is whether the left pane may show 航小天 instead of the chat.
SHOT_ROWS: list[dict] = [
    # The opening, re-cut from six panes to four because two of them collided with the crest that
    # `LANDMARK_ROWS` pins to 0.03 s. Two rows at one timestamp is an overlap and the loser gets a
    # zero-length span, which is how the sweep found this: `pane_power_on` and `pane_protection` were
    # both being scheduled and neither was ever drawn. The board sequence now runs
    # crest(0.03) -> power_on(1.33) -> protection(3.58) -> class(5.16), which is also the order the
    # lyric puts them in: the protection line comes *before* "object creation", not after it.
    dict(at=1.33, name="pane_power_on", lyric="Remember to put on protection",
         ops=["POWER_ON", "VCC", "GND", "5V"], her=False),
    dict(at=3.58, name="pane_protection", lyric="Lay down your pieces",
         ops=["ESD", "STRAP", "FUSE"], her=False),
    dict(at=5.16, name="pane_class", lyric="And let's begin object creation",
         ops=["CLASS", "OBJECT", "INIT"], her=False),
    dict(at=7.19, name="pane_parameters", lyric="Fill in my data parameters",
         ops=["PARAM", "SET", "COMMIT"], her=False),
    dict(at=9.75, name="pane_polyhedra", lyric="Initialization",
         ops=["V-E+F", "HE_INIT", "N(0,2/n)"], her=False),
    dict(at=10.90, name="pane_three_arms", lyric="Set up our new world",
         ops=["AERO", "ASTRO", "MARINE"], her=True),
    dict(at=12.47, name="pane_countdown", lyric="And let's begin the simulation",
         ops=["RUN", "SIM", "t=0"], her=False),
    # The gap is the campus, not the timetable. The user's audit (2026-10-03) found the four-year
    # curriculum list here, at 00:13-00:29, which is exactly the content the first act must not have:
    # the college is chosen at 02:11.9 and until then the film is about the *school*. The curriculum
    # moved to `pane_curriculum`'s new row after the gate, where it belongs (it is the answer to "so
    # what am I in for"), and the gap is now the bronze vessel's own character art and the crest.
    dict(at=13.20, name="pane_landmark_hezun", lyric="[gap]",
         ops=["\u4f55\u5c0a", "\u5b57\u7b26\u753b", "1980"], her=False),
    # The instrumental gap (13.2-29.3) has no words, so the two campus marks alternate over it rather than
    # one of them holding for sixteen seconds: the vessel, then the crest, then back. Nothing is asserted
    # by either, which is what a gap screen is for.
    dict(at=17.00, name="pane_landmark_crest", lyric="[gap]",
         ops=["\u6821\u5fbe", "1938"], her=False),
    dict(at=21.00, name="pane_landmark_crest", lyric="[gap]",
         ops=["\u6821\u5fbd", "1938", "\u516c\u8bda\u52c7\u6bc1"], her=False),
    dict(at=25.14, name="pane_landmark_hezun", lyric="[gap]",
         ops=["\u4f55\u5c0a", "\u5b57\u7b26\u753b"], her=False),
    dict(at=29.28, name="pane_point_set", lyric="If I'm a set of point",
         ops=["IF", "SET", "DIM"], her=False),
    # The IF/THEN passage is four couplets, not one: "a set of point / my dimension", "a circle / my
    # circumference", "a sine wave / all my tangents", "infinity / your limitations". One pane held for
    # all 12.6 s of it was the same fault the user found on the tomato pane - the right column stopped
    # following the song - so each couplet gets the pane that draws *it*: the conditional device, then the
    # superellipse (a circle is `n = 2` of it), then the sine and its envelope, which is also where the
    # pane's own third stage already was.
    dict(at=33.01, name="pane_polyhedra", lyric="If I'm a circle",
         ops=["|x|^n", "n=2", "CIRCLE"], her=False),
    dict(at=36.77, name="pane_class", lyric="If I'm a sine wave",
         ops=["sin", "ENVELOPE", "TANGENT"], her=False),
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
         ops=["NWPU", "1938", "1957"], her=False),
    # `pane_power_on` is *not* repeated here: it is a `SHOT_ROWS` row. Listing it in both places is
    # what produced the collision this comment replaced - the crest and the board both wanted 0.03 s.
    # "unite" / "deeply" / "only God": the two hands - but at three *short* appearances, not three
    # enormous spans. The rows used to chain 54.74 -> 110.40 with no `end`, so `pane_landmark_dialogue`
    # covered fifty-six seconds of a two-hundred-second film and the user's note was exact ("对话这个图
    # 出现的有点久了"). Between its appearances are the supplied character art (`pane_landmark_cat`) and
    # the 万物皆点 pane, which is where `想法.md` puts the cat and the tomato anyway.
    # 互换: 41.92-54.74 had no school pane at all - the film's own panels drew it. This is the section
    # `想法.md` gives five motifs to (F→M as three flipped bits, the twelve-hour clock as a double cover
    # of a day, the braid group σ₁), and it is drawn by `school_scenes.pane_exchange`. Four rows, one per
    # motif, on the line each belongs to rather than all four small at once for twelve seconds.
    dict(at=41.92, name="pane_exchange", lyric="Switch my current",
         ops=["XOR", "F\u2192M", "3 bits"], her=False, args=dict(panel="bits")),
    dict(at=45.52, name="pane_exchange", lyric="To AC, to DC",
         ops=["12h", "AM/PM"], her=False, args=dict(panel="clock")),
    dict(at=47.27, name="pane_exchange", lyric="And then blind my vision",
         ops=["\u03c3\u2081", "BRAID"], her=False, args=dict(panel="braid")),
    dict(at=50.95, name="pane_exchange", lyric="Oh, we can travel",
         ops=["|x|^n", "SUPERELLIPSE"], her=False, args=dict(panel="hyper")),
    dict(at=54.74, name="pane_landmark_dialogue", lyric="And we can unite",
         ops=["UNITE", "\u5bf9\u8bdd"], her=False),
    dict(at=60.57, name="pane_landmark_dialogue", lyric="Give you all the simulations",
         ops=["SIM", "\u5bf9\u8bdd"], her=False),
    # 62.00-70.00 was the cat, held for eight seconds across five different lines - including "I will run
    # the execution", which is not a cat. The cat belongs on the two lines that *are* a cat (80.93,
    # below); here the hands carry "Then I can / satisfaction" and the conditional device carries
    # "If I can make you happy / I will run the execution", which is an `If ... then ...` like all the
    # others the device is for.
    dict(at=62.00, name="pane_landmark_dialogue", lyric="Then I can, then I can",
         ops=["DEEPLY", "\u5bf9\u8bdd"], her=False),
    dict(at=66.17, name="pane_point_set", lyric="If I can make you happy",
         ops=["IF", "THEN", "RUN"], her=False),
    dict(at=70.02, name="pane_landmark_dialogue", lyric="Though we are trapped",
         ops=["TRAPPED", "\u5bf9\u8bdd"], her=False),
    # 万物皆点 is three couplets - eggplant, tomato, cat - and the film cuts on each one. All three panels
    # held for 11.07 s was the user's example of a performance that outlasts its lyric ("右边panel的西红柿
    # 那个光谱界面占了过长时间，和左侧歌词都不对应了"): the spectrum was still on screen while the words
    # had moved on to the cat. Now each panel gets its own couplet, and the cat - which had the wrong row
    # entirely - gets the two lines about a tabby.
    dict(at=73.53, name="pane_everything_point", lyric="If I'm an eggplant",
         ops=["USDA", "\u8425\u517b\u6d41\u5411"], her=False, args=dict(panel="food")),
    dict(at=77.16, name="pane_everything_point", lyric="If I'm a tomato",
         ops=["444nm", "472nm", "503nm"], her=False, args=dict(panel="tomato")),
    dict(at=80.93, name="pane_landmark_cat", lyric="If I'm a tabby cat",
         ops=["\u732b\u5b66\u957f", "\u5b57\u7b26\u753b", "\u53e0\u52a0\u6001"], her=False),
    # 84.6-110.4 is the last verse's "only God / switch my gender / trance" run: the switch lines belong to
    # the swap pane (a gender switch is the same three-bit flip as a current switch), the "if I can / feel
    # your vibrations" lines to the conditional device, and "finally be completion" to the Love class - the
    # expression completed. One pane per thought, instead of a hand and a crest held over all of it.
    dict(at=84.60, name="pane_landmark_dialogue", lyric="If I'm the only God",
         ops=["ONLY_GOD", "\u5bf9\u8bdd"], her=False),
    dict(at=88.34, name="pane_exchange", lyric="Switch my gender",
         ops=["F\u2192M", "3 bits"], her=False, args=dict(panel="bits")),
    dict(at=92.00, name="pane_exchange", lyric="From AM to PM",
         ops=["12h", "AM/PM"], her=False, args=dict(panel="clock")),
    dict(at=95.28, name="pane_exchange", lyric="Oh, my switch role",
         ops=["S/M", "ROLE"], her=False, args=dict(panel="braid")),
    dict(at=98.93, name="pane_landmark_dialogue", lyric="So we can enter",
         ops=["TRANCE", "\u5bf9\u8bdd"], her=False),
    dict(at=101.13, name="pane_landmark_dialogue", lyric="The trance, the trance",
         ops=["TRANCE", "\u5bf9\u8bdd"], her=False),
    dict(at=103.03, name="pane_point_set", lyric="If I can, if I can",
         ops=["IF", "THEN", "VIBRATION"], her=False),
    dict(at=106.84, name="pane_love_class", lyric="Then I can, then I can",
         ops=["CLASS", "Love", "COMPLETE"], her=False),
    # "Challenging your God": the sword, as the accusation
    dict(at=125.33, name="pane_landmark_sword", lyric="Challenging your God",
         ops=["\u94f8\u5251", "CHALLENGE"], her=False),
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
    dict(at=162.23, name="pane_converge", lyric="If I can, if I can",         ops=["DFD", "ER", "\u6d3b\u52a8\u56fe", "\u72b6\u6001\u56fe", "\u2192", "CLASS"], her=False),
    dict(at=166.05, name="pane_converge", lyric="Be your only execution",
         ops=["CONVERGE", "CLASS"], her=False),
    dict(at=169.61, name="pane_backlog", lyric="If I can have you back",
         ops=["SCRUM", "TODO", "DOING", "DONE"], her=False),
    # The four AI motifs. They are laid out around `shot_collapse` (174.90-177.50), which the TUI draws
    # full-bleed *in this variant too* - the film's picture collapses into a line and a dot, and there is
    # no chrome left to draw a pane in. The first version of this table put `pane_ai_rl` at 175.31, where
    # the column is empty for its whole life and the pane is simply not on screen. Two motifs before the
    # collapse and two after it also gives that moment something to divide.
    dict(at=171.31, name="pane_ai_cnn", lyric="If I can have you back",
         ops=["CONV", "KERNEL", "FEATURE MAP"], her=False),
    dict(at=173.10, name="pane_ai_attention", lyric="Though we are trapped",
         ops=["Q", "K", "V", "SOFTMAX"], her=False, end=174.90),
    # the film's own collapse, 174.90-177.50, with no pane behind it: `shot_collapse` is drawn
    # full-bleed in this variant too, so a name here would be a pane nobody can see
    dict(at=174.90, name=None, lyric="Though we are trapped", ops=["COLLAPSE"], her=False,
         end=177.50),
    dict(at=177.50, name="pane_ai_rl", lyric="I've studied, I've studied",
         ops=["POLICY", "ROLLOUT", "ADVANTAGE"], her=False),
    dict(at=179.30, name="pane_ai_diffusion", lyric="I've studied, I've studied",
         ops=["NOISE", "DENOISE", "\u6b65\u6570"], her=False),
    dict(at=181.20, name="pane_knowledge", lyric="I've studied, I've studied",
         ops=["STUDIED", "\u77e5\u8bc6\u56fe\u8c31"], her=False),
    # The curriculum, moved here from 00:13 where the audit found it: this is the answer to the college
    # the student just chose, so it belongs on the far side of the gate and not before it.
    dict(at=136.90, name="pane_curriculum", lyric="[after the gate]",
         ops=["YEAR1", "YEAR2", "YEAR3", "YEAR4"], her=False, end=147.52),
    dict(at=184.33, name="pane_love_class", lyric="I know the algebraic expression of lo-o-ove",
         ops=["LOVE", "CLASS", "UML"], her=False),
    # The last verse is two thoughts, not one: "the algebraic expression of love", and then "though you
    # are free / I am trapped / trapped in lo-o-ove". The Love class draws the first; the hands - the
    # film's own work - draw the second, which is what the two hands not touching have always meant.
    dict(at=187.97, name="pane_landmark_dialogue", lyric="Though you are free",
         ops=["FREE", "TRAPPED", "\u5bf9\u8bdd"], her=False),
    # MEMORY: one more layer on every "You have left", then down to one, then none.
    #
    # This is the one place in the film where a pane is drawn *differently* on lines that are otherwise
    # identical, and the difference is the whole idea: the sculpture is one word printed twice, the
    # lyric is one sentence sung five times, and the count is what ties them together. So the count
    # travels in `args` rather than being derived from the clock - `draw_scene_pane` hands it to the
    # drawing, and `pane_memory` takes a `layers` keyword.
    dict(at=110.40, name="pane_memory", lyric="Though you have left",
         ops=["MEMORY", "x2"], her=False, args=dict(layers=2)),
    dict(at=111.98, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x3"], her=False, args=dict(layers=3)),
    dict(at=112.89, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x4"], her=False, args=dict(layers=4)),
    dict(at=113.75, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x5"], her=False, args=dict(layers=5)),
    dict(at=114.75, name="pane_memory", lyric="You have left",
         ops=["MEMORY", "x6"], her=False, args=dict(layers=6)),
    # "Erase all the pointless fragments": the layers going the other way - four, then one
    dict(at=117.95, name="pane_memory", lyric="If I can, if I can",
         ops=["MEMORY", "x4"], her=False, args=dict(layers=4)),
    dict(at=119.81, name="pane_memory", lyric="Erase all the pointless fragments",
         ops=["MEMORY", "x1"], her=False, args=dict(layers=1)),
    # closing: the crest alone
    dict(at=193.46, name="pane_landmark_crest", lyric="[gap] \u5c3e\u58f0",
         ops=["NWPU", "\u516c\u8bda\u52c7\u6bc5"], her=False),
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
}
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
    """`{index: {name, pane, ops, her, u}}` for the row covering each point in the song.

    The player asks this once per frame through `school_entry`; it is cheap because the table is
    ten rows long and sorted once.
    """
    rows = shot_rows()
    out = {}
    for i, r in enumerate(rows):
        out[i] = dict(index=i, total=len(rows), name=r["name"], pane=r["name"],
                      ops=r["ops"], her=r.get("her", False), alert=None, alert_own=None,
                      start=r["at"], end=r["end"], run=0, last_her=False, lyric=r["lyric"])
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
    alert, her, u, the shot object). This keeps all of it and changes only what the variant owns -
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
             her=bool(row.get("her", False)), school=True, lyric=row["lyric"],
             pane_args=row.get("args"))
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
    gives the pane up. `her=True` on a row means the pane *may* show the figure, which the `c` key
    still toggles; the default is the window.
    """
    return False


def draw_scene_pane(pane: str, s, x0: int, y0: int, x1: int, y1: int,
                    t: float, lt: float, dur: float, u: float,
                    args: dict | None = None) -> bool:
    """Draw `pane`: a course drawing first, then the batch-1 scenes, else False.

    `args` is the schedule's optional annotation for the drawing - see `school_scenes.draw_pane`.
    """
    if _CO.draw_course(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane),
                       total=len(EXEC_PANES)):
        return True
    if _CO.draw_gauge(pane, s, x0, y0, x1, y1, t, lt, dur, u, run=_run_of(pane)):
        return True
    return _SC.draw_pane(pane, s, x0, y0, x1, y1, t, lt, dur, u, args=args)


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
    """
    if t < MACHINE_FROM:
        return None
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
