"""The college gate: `Illegal arguments` (02:10.74) asks the student what they study.

Why here, and why it is not a menu that appears from nowhere
-----------------------------------------------------------
`01_歌词分析.md` finds exactly one place in this song where a question can be asked without
interrupting it: 02:10.74, the line "Illegal arguments", after which the record goes quiet for 13.14
seconds (02:14.38 - 02:27.52). The lyrics before that point are all "I give you what you need" and
everything after it is "I execute". A user who has handed the machine a bad argument is about to find
out what it does with them, and the one thing it does not yet know is who is asking.

The gate is therefore the song's own hinge rather than a bolt-on, and the 13 seconds of instrumental
is the slot it sits in. That is why the audio **does not stop** here (the user's correction of
2026-10-03: the question is on screen for five seconds and the song keeps playing under it).

What the answer *decides* is `school_colleges`: the college whose content pack the reprise draws. Only
`s` is implemented, and the other options are **shown and rejected** rather than hidden. That is a
deliberate choice: the option list is a promise about the rest of the school, and a list that hides what
it cannot do is lying about the shape of the thing. `s` selects Software; anything else prints why it
does not work yet and waits for a valid key, so the gate cannot be escaped by accident - and when a
contributor's pack lands, adding their code to `school_colleges.IMPLEMENTED` is what makes their option
real (see that module: a college is *added*, never substituted).
"""
from __future__ import annotations

import school_colleges as _COL      # the option list, and which colleges have content behind them

# the moment the gate opens: just after the lyric line lands, so the question arrives *under* it
GATE_AT = 131.9                 # 02:11.9, one second after "Illegal arguments" at 02:10.74
GATE_UNTIL = 147.0              # the song comes back before "Execution" at 02:27.52
# The user's correction (2026-10-03): the music does **not** stop for the question. The question is on
# screen for five seconds, the first character of an option selects it, and if nothing is typed in that
# window the answer is Software - which is the student's own college, so the default is not a fallback,
# it is the answer the film was always going to give.
WINDOW = 5.0
DEFAULT_MAJOR = "s"             # what a seek past the gate assumes; see `major_at`

# The school's own list, from `02_叙事设计.md` §9: 24 专业学院, of which these are the ones a
# first-year would be asked to pick between. The list and which of them are implemented live in
# `school_colleges`, because they are also what decides *whose content the reprise draws*: the option
# list is a promise about the rest of the school, and a promise that hides half its options is not one.
# (`school_colleges.IMPLEMENTED` is the single place a contributor adds a college to.)
OPTIONS = [(code, zh, en) for code, zh, en in _COL.COLLEGES]
IMPLEMENTED = _COL.IMPLEMENTED

PROMPT = "\u5bf9\u4e86\uff0c\u4f60\u662f\u4ec0\u4e48\u5b66\u9662\u7684\uff1f"      # "对了，你是什么学院的？"
REJECT = "\u8be5\u65b9\u5411\u5c1a\u672a\u5f00\u8bbe\uff08\u672c\u9636\u6bb5\u53ea\u5b9e\u73b0\u4e86\u8f6f\u4ef6\u5b66\u9662\uff09"
HINT = "\u8bf7\u6309 s \u7ee7\u7eed"

# what the window shows while it waits: a dsh question block, in the film's own role vocabulary
# (`card` is the page's bullet line, `sub` its indented note, `err` its red system line)
BLOCK_HEAD = [("ai", PROMPT)]
BLOCK_TAIL = [("meta", GATE_AT and "\u7b49\u4f60\u56de\u7b54")]

# --------------------------------------------------------------------------- the state machine
#
# Four states, and the difference between the middle two is the whole reason this is a state machine
# rather than a flag:
#
#   waiting   the song is held at `GATE_AT`, the question is on screen, a key is expected
#   rejected  a key was pressed and it is not `s`: the reason is shown and we go back to waiting
#   answered  a key was pressed and it is `s`: the student is in Software and the song resumes
#   assumed   the playhead was *seeked* past the gate without a key. This has to be a separate state
#             from `answered`, because the two mean different things: one is the student having said
#             "software", the other is a viewer who dragged the bar and never answered. It resolves to
#             the same major - `DEFAULT_MAJOR` - because the alternative is a film that stops on a
#             question no one can see, which breaks seek-safety (skill § 1.1). What it does *not* do is
#             pretend the question was asked, so `asked` stays False and the window never claims to
#             have been answered.
STATE = {"phase": "waiting", "major": None, "asked": False, "rejected": "", "hold": 0.0,
         "held": False}


def reset(major: str | None = None) -> None:
    """Start over. `major` pre-answers the gate, which is what `--major` is for."""
    STATE.update(phase="answered" if major else "waiting", major=major,
                 asked=bool(major), rejected="", hold=0.0, held=False)
    # ...and the answer is what the reprise draws: `active()` clamps an unimplemented code to the
    # default pack, so `--major a` still plays (as 软件学院) rather than drawing nothing.
    _COL.set_active(major or _COL.DEFAULT)


def armed() -> bool:
    """Whether a key would be accepted right now.

    `rejected` counts as armed, and that is the whole point of the state existing: a wrong answer has
    to leave the question *up* and the next key readable, or the gate would be a single chance and a
    stray keypress would take the film past it silently. The first version returned True only for
    `waiting`, so pressing `a` printed the rejection and then swallowed the `s` that followed it -
    caught by driving the state machine directly (`_dev/_check_gate.py`) rather than by watching.
    """
    return STATE["phase"] in ("waiting", "rejected")


def key(ch: str) -> bool:
    """Take one keypress. True if it was ours (and so should not fall through to the player).

    Only `s` is accepted and the others are *shown and rejected* rather than hidden - see the module
    docstring. The rejection is not a dead end: the question stays up and the next key is read, so the
    gate cannot be walked past by pressing `a`.
    """
    if not armed():
        return False
    if ch.lower() in IMPLEMENTED:
        STATE.update(phase="answered", major=ch.lower(), asked=True, rejected="", held=False)
        # **the answer reaches the picture here**: from now on the reprise's rows are this college's
        _COL.set_active(ch.lower())
        return True
    if ch.lower() in {o[0] for o in OPTIONS} or ch.isprintable():
        STATE.update(phase="rejected", rejected=ch)
        return True
    return False


def tick(t: float, seeking: bool = False) -> float:
    """Advance the gate to `t` and return the time the player should use - which is always `t`.

    The gate used to pin the playhead at `GATE_AT` while it waited, which *was* the pause: the film's
    clock is the song's clock, so holding the clock held the song. The user's note is that the music
    must not stop ("音乐并不暂停，机制为显示 5s 内敲入选项前字符，若为输入则默认当前软件学院"), so
    nothing is pinned any more. The window opens at `GATE_AT`, a key inside it answers, and the window
    closing with no key answers with the default.

    `seeking` still means what it meant: a playhead that was *dragged* past the gate did not answer the
    question, and that is a different state from having typed `s`.
    """
    if STATE["phase"] in ("waiting", "rejected"):
        if t >= GATE_AT + WINDOW:
            # the five seconds are up and nothing was typed: Software, quietly, and the song never stopped
            STATE.update(phase="defaulted", major=DEFAULT_MAJOR, asked=False, held=False)
            _COL.set_active(DEFAULT_MAJOR)
        elif seeking:
            assume()
    return t


def window_open(t: float) -> bool:
    """Whether the question panel should be on screen, and whether a key would still count."""
    return STATE["phase"] in ("waiting", "rejected") and GATE_AT <= t < GATE_AT + WINDOW


def window_left(t: float) -> float:
    """Seconds left in the window, for the panel's own countdown."""
    return max(0.0, GATE_AT + WINDOW - t)


def holds(t: float) -> bool:
    """False, always: the gate no longer holds the song.

    Kept as a function rather than deleted because the player and the probes still ask, and the answer
    is now a property of the design rather than of the clock. The old body asked whether the playhead
    was *at* `GATE_AT` and armed; both of those are now the window's business (`window_open`), and
    nothing pauses.
    """
    return False


def reached(t: float, end: float) -> bool:
    """Whether a seek to `t` jumped over the gate without stopping on it.

    Landing *on* a time before the gate, or inside the hold, is not a jump past it: the gate opens
    normally when the playhead arrives. Only a destination beyond the gate's slot is one, and there the
    answer is assumed rather than the alternative of yanking the playhead backwards to 02:11.9, which
    would be a seek that ignores where the viewer asked to go.
    """
    return t >= GATE_UNTIL


def assume(major: str | None = None) -> None:
    """Answer the gate without a keypress, and remember that nobody pressed one."""
    STATE.update(phase="assumed", major=major or DEFAULT_MAJOR, held=False)
    _COL.set_active(major or DEFAULT_MAJOR)


# --------------------------------------------------------------------------- the scripted answer
#
# The gate has two ways to be answered, and which one is in charge depends on whether anybody is
# sitting in front of it:
#
#   * **a key**, when there is (`key()`); the song holds until one arrives;
#   * **the script**, when there is not - an exported frame, a `--once` render, a screenshot, or a
#     viewer who just wants to watch. The student types `s` himself, on the gate's own clock.
#
# The scripted path is not a fallback for the interactive one; it is the *primary* reading, because an
# MV is a film and a film cannot wait for a keypress. Since the gate no longer stops the song at all,
# the script is simply what happens when nobody types: the student's `s` types itself at
# SCRIPT_TYPE_AT of the window and that answer stands unless a real key beats it there - and the
# window's own default (`tick`, at five seconds) is the last resort.
#
# The stutter that was reported earlier came from exactly this: the gate pinned the clock at 02:11.9
# while the audio device ran on, so the tune kept playing under a frozen picture and jumped forward when
# the gate released. Holding a clock the audio never agreed to hold is now impossible, because nothing
# holds a clock.
SCRIPT_ASK = 0.30          # options on screen and the cursor starts walking
SCRIPT_STEP = 0.16         # per option, so the walk reads as a hand and not as a jump
SCRIPT_WALK_END = 1.35     # the walk reaches the bottom of the list about here
SCRIPT_TYPE_AT = 1.85      # the cursor is back on `s` and the student starts typing
SCRIPT_TYPE_DUR = 0.50     # the characters arrive over this long
SCRIPT_DONE = 2.60         # the gate is over and will not ask again
TYPED = "s\u3002"           # what the student types: `s` and a Chinese full stop


def scripted(u: float) -> dict:
    """The gate's progress `u` seconds after it opened, as `(phase, typed, cursor, selected)`.

    A pure function of `u`, so a frame at 02:13.2 is the same frame whether it was played into or
    seeked to. `u` is measured in *song* time, which is the only clock this module has.

    The walk is deliberately not a straight line down to option one. It goes down the list - which is
    how a hand reads a menu it did not expect - and then comes back up to `s`, and the highlight stays
    on `s` while the student types. The first version walked *to* `s` and left the highlight on the last
    option it had passed, so the picture said "材料学院" while the prompt said `s`; a rendered frame
    showed it and this is the fix.
    """
    n = len(OPTIONS)
    S = 1                                # the software option is first in the list
    if u < SCRIPT_ASK:
        return dict(phase="waiting", typed="", cursor=0, selected=0)
    if u < SCRIPT_WALK_END:
        walk = 1 + int((u - SCRIPT_ASK) / SCRIPT_STEP)
        return dict(phase="walking", typed="", cursor=min(n, walk), selected=0)
    if u < SCRIPT_TYPE_AT:
        # the cursor comes back to the option he is going to take
        return dict(phase="choosing", typed="", cursor=0, selected=S)
    if u < SCRIPT_TYPE_AT + SCRIPT_TYPE_DUR:
        k = (u - SCRIPT_TYPE_AT) / SCRIPT_TYPE_DUR
        return dict(phase="typing", typed=TYPED[: max(1, int(1 + k * (len(TYPED) - 1)))],
                    cursor=0, selected=S)
    if u < SCRIPT_DONE:
        return dict(phase="typed", typed=TYPED, cursor=0, selected=S)
    return dict(phase="answered", typed=TYPED, cursor=0, selected=S)


def age(t: float) -> float:
    """How long the gate has been open at song time `t`, or a negative number before it opens."""
    return t - GATE_AT


def overlay(s, cols: int, rows: int, t: float) -> bool:
    """Draw the gate as a full-screen takeover; True while it is on screen.

    This is the gate's *primary* presentation and it exists because the first version put the question
    in the chat window, where two things went wrong and both were found by rendering a frame:

      * the window shows the tail of the conversation, so the option list was pushed off the bottom by
        the lines that followed it - the question was in the buffer and not on the screen, which is
        exactly what "选择学院完全没有体现" describes;
      * it was a list in a chat log, which is not what an interface asking you to choose looks like.

    So the gate takes the screen the way a real prompt does: the dimmed terminal behind it, a panel
    with the question, the eight colleges, a cursor that walks down to the software option and the
    student's own `s` typed into the input line. Everything is a function of the gate's age, so an
    exported frame carries the whole decision.

    It is on screen for `WINDOW` seconds and the song keeps playing underneath it - see `tick`. The
    panel says so: the countdown is on the title bar and the hint names both the mechanism and the
    default, because the five-second limit is only fair if the person reading it knows about it.

    Only the school variant calls this, and only while the gate is open.
    """
    if not window_open(t):
        return False
    u = age(t)
    if u < 0:
        return False
    # The panel stays for the whole window. It used to disappear as soon as `scripted(u)` said
    # "answered" - at 2.6 s - which left the last two and a half seconds of a five-second window with
    # the footer counting down over a screen that no longer showed the question. What the script
    # decides is the panel's *contents*: the cursor's walk and the characters in the input line.
    scr = scripted(u)

    import school_scenes as SC
    import school_courses as CO
    ME_TEXT, ANOM, _ui, _mix = SC.ME_TEXT, SC.ANOM, SC._ui, SC._mix
    AMBER, GREEN = CO.AMBER, CO.GREEN
    BG_ = SC.BG
    W = min(cols - 2, 78)
    H = min(rows - 2, 2 + len(OPTIONS) + 5)
    x0 = (cols - W) // 2
    y0 = max(1, (rows - H) // 2)
    x1, y1 = x0 + W - 1, y0 + H - 1

    # the terminal behind it, dimmed: the gate is a mode, not a new screen
    for y in range(1, rows - 1):
        s.put(1, y, " " * max(0, cols - 2), _ui(0.18), (2, 4, 9))
    # the window is 航小天's, so its box says his name (it said "dsh" - the film's page - until batch 34)
    s.box(x0, y0, x1, y1, " hangxiaotian  \u8bf7\u9009\u62e9\u5b66\u9662 ", 0.85, ANOM)
    left = window_left(t)
    s.put(x1 - 12, y0, f" {left:3.1f}s ",
          _mix(ANOM, 0.95) if left > 1.5 else _mix(CO.RED, 0.95))
    s.put(x0 + 2, y0 + 1, PROMPT, _mix(ME_TEXT, 1.0))
    if scr["cursor"]:
        s.put(x1 - 12, y0 + 1, f"cursor {scr['cursor']}/{len(OPTIONS)}", _ui(0.4))
    for i, (k, cn, en) in enumerate(OPTIONS):
        yy = y0 + 2 + i
        if yy > y1 - 4:
            break
        hot = scr["selected"] and i == scr["selected"] - 1
        passed = scr["cursor"] and i == scr["cursor"] - 1
        done = k in IMPLEMENTED and scr["phase"] in ("typing", "typed")
        bg = (26, 36, 66) if hot else None
        fg = _mix(ANOM, 1.0) if hot else (_mix(GREEN, 0.95) if done else _ui(0.8))
        # the highlight bar stops at the panel's inner edge: it used to start at x0+3 and run to the
        # end of the row, which painted over the right border and out of the box
        bar_w = max(0, x1 - (x0 + 3) - 2)
        if bg:
            s.put(x0 + 3, yy, " " * bar_w, fg, bg)
        s.put(x0 + 3, yy, ">" if passed else " ", _mix(ANOM, 1.0), bg or BG_)
        s.put(x0 + 5, yy, f"{k}", fg, bg or BG_)
        s.put(x0 + 8, yy, f"{cn:<12}", fg, bg or BG_)
        s.put(x0 + 22, yy, f"{en:<18}"[: max(0, x1 - (x0 + 22) - 3)], _ui(0.5), bg or BG_)
        if done:
            s.put(x1 - 3, yy, "\u221a", _mix(GREEN, 1.0), bg or BG_)
    # the input line: what the student types, and the caret while he has not finished
    iy = y1 - 2
    s.put(x0 + 2, iy, ">", _mix(ME_TEXT, 0.9))
    typed = scr["typed"]
    s.put(x0 + 4, iy, typed, _mix(ME_TEXT, 1.0))
    if scr["phase"] != "typed" and int(t * 2) % 2 == 0:
        s.put(x0 + 4 + len(typed), iy, "\u2588", _mix(ME_TEXT, 1.0))
    # The hint names the *mechanism*, not just the state: the gate is the one place the film stops and
    # waits for a person, and "请选择一个方向" told them that a choice existed without telling them how
    # to make one. The `s` planted at 01:36 is a sentence in the chat; this is the affordance. It now
    # also names the clock and the default, because the window closes on its own after five seconds and
    # a limit nobody was told about is not a limit, it is a trap.
    hint = ("\u6309 s\u3001\u6216\u7b49\u5b83\u81ea\u5df1\u9009" if scr["cursor"]
            else "\u6309\u5b66\u9662\u9996\u5b57\u6bcd\u9009\u62e9 \u00b7 5 \u79d2\u5185\u672a\u8f93\u5165"
                 "\u9ed8\u8ba4\u8f6f\u4ef6\u5b66\u9662")
    s.put(x0 + 2, y1 - 1, hint, _ui(0.55))
    return True


def lines() -> list[tuple[str, str]]:
    """The window's question block, as `(role, text)` in the film's own vocabulary.

    `u` is the gate's own age in seconds. When it is given, the *scripted* answer is drawn into the
    block - the cursor walking down to the software option, then `s` appearing in the prompt - and when
    it is None the block is the interactive one, waiting for a key. The two share this function because
    they are the same block read at two speeds; only the caller knows which is in charge.
    """
    if STATE["phase"] == "assumed":
        return []
    scr = scripted(u) if u is not None else dict(phase="waiting", typed="", cursor=0, selected=0)
    if scr["phase"] == "answered":
        # the gate is over: one line saying what was chosen, in the page's own bullet style
        return [("ai", PROMPT),
                ("card", f"\u221a s  {OPTIONS[0][1]}   {OPTIONS[0][2]}"),
                ("meta", "\u7b49\u4f60\u56de\u7b54")]
    out = list(BLOCK_HEAD)
    for i, (k, cn, en) in enumerate(OPTIONS):
        mark = "\u2022" if k in IMPLEMENTED else "\u00b7"
        lead = "> " if (scr["cursor"] and i == scr["cursor"] - 1) else "  "
        out.append(("card", f"{lead}{mark} {k}  {cn}   {en}"))
    if scr["typed"]:
        out.append(("user", scr["typed"]))
    if STATE["phase"] == "rejected":
        out.append(("err", f"\u00d7 {REJECT}"))
        out.append(("sub", HINT))
    elif not scr["typed"]:
        out.append(("sub", HINT))
    out.append(("meta", "\u7b49\u4f60\u56de\u7b54"))
    return out
