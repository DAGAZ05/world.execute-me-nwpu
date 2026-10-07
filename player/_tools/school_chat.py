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
    card       a "> ..." bullet
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


# --------------------------------------------------------------------------- the conversation
#
# The conversation is **not** here. It is `school_lines.ACT_ONE` + `school_lines_act2.ACT_TWO`, folded
# into blocks at the bottom of this file by `_blocks`.
#
# There used to be a second copy right here: a `DIALOGUE` list with the first thirty seconds typed out as
# `_x("user", ...)` calls, left over from the batch-1 design (the one that still had an Arduino board and
# a UML class inside the first ten seconds - the thing the act-one rule below forbids). It was superseded
# when the flat row files were written and **nothing read it**, so it was a second source of truth sitting
# in the same file as the first: the batch-51 regeneration of `05_歌词会话对照_v2.md` read it by mistake
# and produced a table whose first three exchanges do not exist in the player. It is deleted (batch 52).
#
# `dsh_window` must return the film's own two-tuple shape, so the lyric tag each exchange hangs on lives
# beside the entry rather than in it; see `_blocks`.

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


def lyric_lines() -> list[tuple[float, str]]:
    """`(time, text)` for every timed line of `input/lyrics.lrc` - the list `check_coverage` walks."""
    import re
    out: list[tuple[float, str]] = []
    if not ROOT_LRC.exists():
        return out
    for ln in ROOT_LRC.read_text(encoding="utf-8-sig").splitlines():
        m = re.match(r"^\[(\d+):(\d+\.\d+)\](.*)", ln)
        if m and m.group(3).strip():
            out.append((int(m.group(1)) * 60 + float(m.group(2)), m.group(3).strip()))
    return out


def why_no_exchange(t: float, text: str, lines: list[tuple[float, str]] | None = None,
                    depth: int = 0) -> str:
    """Why this lyric line has no exchange of its own, as a short phrase for a reader.

    `""` means it *has* one (or is the completion of a pair whose opener has one). `"UNEXPLAINED"` means
    nothing accounts for it, which is what `check_coverage` reports. The five reasons, in the order they
    are tried:

      1. **it has its own exchange** - a block in `_DIALOGUE` hangs on that line, at that time;
      2. **it completes a pair** - a `To`/`Then` line whose opener is itself handled. That is the IF/THEN
         device (`05_歌词会话对照_v2.md` §4): `To AC, to DC` finishes `Switch my current`;
      3. **a picture is covering the window** at that moment - measured from `school_fx.WINDOW_EVENTS`,
         the layer that draws *inside* the chat window. The basketball (58.65-70.08) covers four lines of
         the first chorus and nothing else does;
      4. **the previous exchange still holds the screen** - a block's own `用时 X 秒` cell says how long it
         stays, so `I will run the execution` (01:51.86) is inside the 3.4 s answer that opened at
         01:49.61 rather than being a line with nothing under it;
      5. **the stretch is declared silent** - `SILENT_SPANS`, a named list with a reason and a time range,
         for the one place where the film deliberately stops talking: the twelve `Execution` hits, which
         the right column's course drawings carry.

    **Why the old check could not fail (twice over).** It was `not ln.startswith(("To ", "Then "))` - a
    blanket exemption that made it return `[]` by construction (batch 38 fixed that half) - plus a *string*
    set, `COVERED_BY_PICTURE`, compared against a set of tags. Text-keyed exemptions exempt **every
    occurrence**: all twelve `Execution` lines were exempted by the one block that hangs on the first of
    them, and `I will run the execution` at 01:51.86 was exempted by the basketball that covers its
    01:08.20 occurrence. That is how a "what is said over which lyric" table can look complete while a
    line has no answer under it. Everything here is keyed by time instead (batch 52), so both of those
    have to be *declared* - the Execution run as a named silent span, the four chorus lines by the picture
    that really covers them - and this function is what `05_歌词会话对照_v2.md` prints as the reason.
    """
    if any(tag == text and abs(bt - t) <= 0.6 for bt, tag, _b in _DIALOGUE):
        return ""
    lines = lyric_lines() if lines is None else lines
    # ...then the three *measured* reasons, before the pair rule: a half-line inside the basketball
    # window is covered by the basketball, not by the line it completes (the opener of `Then I can, then I
    # can` at 01:02.41 is `Give you all the simulations` at 01:00.57, which is itself under the picture).
    import school_fx as _FX
    for s, e, fn, _kw in _FX.WINDOW_EVENTS:
        if s <= t < e:
            return f"**没有对话**：{s:.2f}-{e:.2f} 的 `{fn.__name__}` 画在会话窗里，把这一段盖住了"
    # ...the pair rule next, *before* rules 4 and 5, because "this is the second half of the line before
    # it" is the informative answer for a `To`/`Then` line and the design's own reason (§4). It has to come
    # after the picture rule, though: a half-line inside the basketball window is covered by the picture,
    # not by the line it completes.
    # The index is found with a loose tolerance on purpose: the film's own timeline
    # (`word_timeline.json`) and `lyrics.lrc` disagree by up to 0.64 s on a few lines, so a `To S, to M`
    # at 01:37.70 in one file is at 01:37.32 in the other and a 0.05 s match made this function report
    # the pair as unaccounted for.
    i = next((k for k, (lt, lx) in enumerate(lines) if lx == text and abs(lt - t) <= 0.75), None)
    if text.startswith(("To ", "Then ")) and depth < 4 and i is not None:
        j = i - 1
        while j >= 0 and lines[j][1].startswith(("To ", "Then ")):
            j -= 1
        if j >= 0:
            opener_t, opener = lines[j]
            if why_no_exchange(opener_t, opener, lines, depth + 1) == "":
                return f"**没有新对话**：这是半句，补完 `{opener}`（§4 IF/THEN 装置），画面承接上一句"
            return f"**没有对话**：这是半句，而它补完的 `{opener}` 也没有对话"
        return f"**没有对话**：这是半句，但表里找不到它补完的那一句"
    for bt, d in declared_spans():
        if 0.0 <= t - bt <= d + 0.3:
            return f"**没有新对话**：上一句的回答还在屏上（`{bt:.2f}` 那一块自称停留 {d:.1f} 秒）"
    for s, e, why in SILENT_SPANS:
        if s <= t < e:
            return f"**没有对话**：{why}"
    return "UNEXPLAINED"


def check_coverage() -> list[str]:
    """Every lyric line must be handled; returns the ones that are not. See `why_no_exchange`."""
    lines = lyric_lines()
    if not lines:
        return ["(no lyrics.lrc to check against)"]
    bad: list[str] = []
    for t, text in lines:
        why = why_no_exchange(t, text, lines)
        if why == "UNEXPLAINED":
            bad.append(f"{text}  @{t:.2f}")
        elif "也没有对话" in why or "找不到它补完" in why:
            bad.append(f"{text}  @{t:.2f}  ({why.strip('*')})")
    return bad


# The one stretch where the film deliberately stops talking, with the reason. A lyric line inside one of
# these is handled by the *declaration*, not by a block - which is why it has to say why.
SILENT_SPANS: tuple[tuple[float, float, str], ...] = (
    (148.00, 161.51,
     "十二次 Execution：右栏的课图一张张出框，左窗只有开头那一句「大二。一起上。」（05 §6 第 8 条）"),
)


def declared_spans() -> list[tuple[float, float]]:
    """`(block time, how long it says it holds the screen)` - the `用时 X 秒` cell of each block.

    It is the block's own claim about its duration, and rule 4 of `check_coverage` reads it: a lyric line
    that arrives while the previous answer says it is still on screen is answered by that answer. Blocks
    without the cell contribute nothing, so a missing cell is never an exemption.
    """
    import re
    out: list[tuple[float, float]] = []
    for t, _tag, block in _DIALOGUE:
        for role, txt in block:
            if role != "meta":
                continue
            m = re.search(r"用时\s*([0-9.]+)\s*秒", txt)
            if m:
                out.append((t, float(m.group(1))))
    return out


from pathlib import Path as _P            # noqa: E402

# the song's own lyric file, for the coverage check below. `player/input/lyrics.lrc` - `parents[1]`
# is `player/`, which is where `input/` sits.
ROOT_LRC = _P(__file__).resolve().parents[1] / "input" / "lyrics.lrc"
