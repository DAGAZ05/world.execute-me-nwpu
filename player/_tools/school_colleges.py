"""The college packs: one entry per 学院, and which of them are implemented.

The film asks a question at 02:11.9 ("对了，你是什么学院的？") and the answer is supposed to decide what
the **last third of the film is about**. This module is that decision's single home:

* `COLLEGES` is the option list the question offers, in the order the question shows them.
  **The university has 20-odd 专业学院 and this list is not all of them** - it is the eight a first-year
  is most often asked to pick between, which is what the panel's ellipsis row says on screen. A college
  whose initial is missing adds itself here (the eight are a demo list, not the school);
* `IMPLEMENTED` is which of them have a **content pack** behind them. Today that is 软件学院 alone,
  because that is the author's own college;
* `active()` is the answer in force, and `school_panels.exec_rows_for()` reads it when it builds the
  reprise's rows. Before this module existed the answer decided nothing but its own panel: the reprise
  was always 软件学院's, whoever you said you were.

**A college is added, never substituted.** The whole point of a pack is that 软件学院's content is not a
template to be overwritten: it is one entry, and a new college is *another* entry. Concretely, a new
college contributes

1. its rows: one entry in `school_panels.PACKS` (its own course list, its own one-line explanations, its
   own gauge list - or `school_panels.PACKS["s"]` reused where the instruments are shared);
2. its drawings: pane functions *added* to `school_scenes.py` (one function per course, named in its
   course list), which is additive by construction - nothing existing is read;
3. its dialogue/curriculum lines if it wants its own (`school_chat.py`, `school_lines*.py` are separate
   tables for the same reason);
4. one line here: put its code in `IMPLEMENTED`, which is what turns the gate's "该方向尚未开设" into a
   real branch.

Nothing in another pack is imported or edited. `check.cmd` covers the rest: a pane that does not move, an
ink that leaves its box, a header with no explanation or a frame over the 24 fps budget all fail the
build, whoever's pack they came from.

Codes are the first character of the option in the question (`s` for 软件学院) so a contributor's key is
whatever initial their college has, and `--major <code>` pre-answers the gate for a scripted run.
"""

from __future__ import annotations

# (code, 中文名, English) - the order is the order the question shows them in
COLLEGES: list[tuple[str, str, str]] = [
    ("s", "软件学院", "Software"),
    ("a", "航空学院", "Aeronautics"),
    ("b", "航天学院", "Astronautics"),
    ("m", "航海学院", "Marine"),
    ("e", "电子信息学院", "Electronics"),
    ("o", "自动化学院", "Automation"),
    ("c", "计算机学院", "Computer Science"),
    ("l", "材料学院", "Materials"),
]

# ...and the ones with a content pack behind them. A code belongs here only when its pack exists.
IMPLEMENTED: set[str] = {"s"}

# what a viewer who never answered gets: the author's own college, which is the answer the film was
# always going to give (see `school_gate.DEFAULT_MAJOR`, which this replaced)
DEFAULT = "s"

# The answer in force. `school_gate` writes it when the question is answered, when the five seconds run
# out and when a seek drags the playhead past the question; everything that draws college content reads
# it through `active()`.
_ACTIVE = {"code": DEFAULT}


def codes() -> list[str]:
    """Every option the question offers, in the order it offers them."""
    return [c for c, _zh, _en in COLLEGES]


def name(code: str) -> str:
    """The Chinese name of a college code, or the code itself if it is not one of ours."""
    for c, zh, _en in COLLEGES:
        if c == code:
            return zh
    return code


def english(code: str) -> str:
    for c, _zh, en in COLLEGES:
        if c == code:
            return en
    return code


def implemented(code: str | None) -> bool:
    """Whether a college has content behind it. `None` (nobody answered) is not implemented."""
    return bool(code) and code in IMPLEMENTED


def active() -> str:
    """The college whose content is drawn: the answer, or the default when there is no pack for it.

    The fallback matters: `--major a` (or a contributor whose pack is half-landed) must not leave the
    reprise with no rows at all, so an unimplemented answer draws the default pack rather than nothing.
    """
    return _ACTIVE["code"] if implemented(_ACTIVE["code"]) else DEFAULT


def set_active(code: str | None) -> None:
    """Record the viewer's answer. Called by `school_gate`; the answer is clamped by `active()`."""
    _ACTIVE["code"] = code or DEFAULT
