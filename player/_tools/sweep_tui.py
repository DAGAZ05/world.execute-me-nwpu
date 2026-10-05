"""Sweep the terminal player over the whole song at several window sizes.

In-process, so it can afford every frame at the reference size. Reports, per size:
  * any exception (with the frame that raised it)
  * cells the draw tried to put outside a screen that exists (Screen guards these, so the count
    stays 0; a nonzero count would mean the guard is what is hiding an overflow)
  * the slowest frame, against the 41.7 ms a 24 fps frame has
  * whether the left pane is holding what it should, sampled at the moments that decide it

Which of the two variants is swept is the environment's business, and it has to be decided *before*
`tui_live` is imported, because that is where the variant module is chosen:

    python _tools\\sweep_tui.py                    the film as shipped
    set PV_VARIANT=school && python _tools\\sweep_tui.py    the 西工大 adaptation

The report changes shape with the variant, because two of the four sections are about the film's own
story: the `--render auto` climax ranges and the "her pane" census describe 大肥鱼, and under the
school variant the left pane is the chat window on every shot and there is no figure to account for.
Printing them anyway would produce a screenful of numbers that are true of a film that is not being
drawn, which is worse than printing less. What the school variant reports instead is the thing that
can actually regress there: **every pane the schedule names must be drawn, and none of them may spill
out of the right-hand column**.
"""
from __future__ import annotations

import gc
import io
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_tools"))

os.environ.setdefault("PV_VARIANT", "original")
import tui_live as T  # noqa: E402

SCHOOL = T.VAR[0] == "school"
if SCHOOL:
    T.SP.init_palette(T.ui, T.mix,
                      dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    # the same one-time decode the player does on its first frame. Without it every size's first frame
    # carries the whole sprite warm-up - and now the basketball animation's 3 MB of JSON as well - and the
    # sweep's "SLOW" column is reporting the film's start-up rather than its playback.
    try:
        import school_fx as _FXw
        _FXw.warm(197, 52)
    except Exception:
        pass

# the live player turns the cyclic collector off (tui_live.main): a gen-2 pass is a 20-27 ms hole in
# a 33 ms frame, which without this would be charged to whichever frame happened to trigger it and
# read as a slow draw. Measure the renderer, not the collector.
gc.disable()

SIZES = [(197, 52), (240, 70), (160, 44), (120, 34), (100, 28), (96, 30), (80, 22), (60, 20)]
STEP = {197: 1, 240: 5, 160: 3, 120: 3, 100: 3, 96: 3, 80: 7, 60: 7}

d = T.Data()
print(f"variant: {'school (\u897f\u5de5\u5927\u7248)' if SCHOOL else 'original (大肥鱼)'}")
print("loading the film's shot table...")
t0 = time.time()
eng = T.Engine()
print(f"  {time.time() - t0:.1f} s")

# --render auto turns her into a solid portrait on the parts of the song that are about her, and
# wherever the system has gone red. The ranges are named by their first and last lyric, so a
# mistyped line is a silent no-match - and a *dropped* range slides every later one onto the wrong
# part of the song. Fail loudly instead of drawing the wrong thing.
unresolved = T.FP.figure_unresolved()
spans = T.FP.figure_spans()
bad_climax = False
if SCHOOL:
    print("\nthe figure story is the film's and is not drawn by this variant (skipped)")
else:
    if unresolved or len(spans) != len(T.FP.FIGURE_LINES):
        bad_climax = True
        print(f"\n!! figure ranges unresolved: {unresolved}")
    else:
        print("\nthe story `--render auto` tells (per shot):")
        for (first, last), (a, b) in zip(T.FP.FIGURE_LINES, spans):
            print(f"    {a:7.2f}-{b:7.2f}  {b - a:5.1f}s   solid blue: {first} ... {last}")
        print(f"    {T.FP.chapter_start('EXECUTION'):7.2f}            solid red: 07 EXECUTION, "
              f"alert_own=err")
        print(f"    {T.FP.chapter_start('EVAL'):7.2f}            red characters: 08 EVAL: LOVE onward")
        last_her = next((e for e in reversed(eng.table) if e["her"]), None)
        if last_her:
            print(f"    {last_her['start']:7.2f}-{last_her['end']:7.2f}  solid blue: the last shot she "
                  f"is in ({last_her['name']})")
        from collections import Counter
        tally = Counter(T.her_style(e) for e in eng.table if e["her"])
        tot = sum(e["end"] - e["start"] for e in eng.table)
        for (how, tint), n in sorted(tally.items()):
            secs = sum(e["end"] - e["start"] for e in eng.table
                       if e["her"] and T.her_style(e) == (how, tint))
            print(f"    -> {how}/{tint}: {n} shots, {secs:.1f} s of {tot:.1f} s ({100 * secs / tot:.0f} %)")

# what the film does with her pane, per shot, straight out of the table
her_shots = [e for e in eng.table if e["her"]]
noher = [e for e in eng.table if not e["her"]]
tot = sum(e["end"] - e["start"] for e in eng.table)

# ---------------------------------------------------------------- the school variant's own census
#
# The one thing that can silently regress in the school variant is the *schedule*: a row naming a pane
# nothing draws, a pane whose `args` no drawing accepts, or a row that overlaps the next one. All three
# are invisible on screen - a missing pane just leaves the film's own drawing in the column, which looks
# deliberate - so they are checked here, against the same table the player reads.
if SCHOOL:
    rows = T.SP.shot_rows()
    named = [r for r in rows if r.get("name")]
    # ask the dispatcher itself rather than re-deriving its table: whether a pane exists is its
    # question, and a second copy of the answer here is a second thing to keep in step
    undrawn = []
    for r in named:
        s_probe = T.Screen(80, 12)
        try:
            ok = T.SP.draw_scene_pane(r["name"], s_probe, 2, 2, 77, 9, 0.0, 0.0, 1.0, 0.5,
                                      args=r.get("args"))
        except Exception as exc:
            undrawn.append(f"{r['name']}: {type(exc).__name__}: {exc}")
            continue
        if not ok:
            undrawn.append(f"{r['name']}: no such pane")
    overlaps = sum(1 for a, b in zip(rows, rows[1:]) if b["at"] < a["end"] - 1e-9)
    gaps = [r for r in named if r["end"] - r["at"] <= 0]
    print(f"\nschool schedule: {len(rows)} rows, {len({r['name'] for r in named})} distinct panes")
    print(f"    undrawable rows: {undrawn or 'none'}")
    print(f"    overlapping rows: {overlaps}")
    print(f"    non-positive spans: {gaps or 'none'}")
    bad_climax = bad_climax or bool(undrawn) or overlaps > 0 or bool(gaps)
else:
    print(f"\nher pane drawn in {len(her_shots)}/{len(eng.table)} shots "
          f"= {sum(e['end'] - e['start'] for e in her_shots):.1f} s / {tot:.1f} s "
          f"({100 * sum(e['end'] - e['start'] for e in her_shots) / tot:.1f} %)")
    print("her absent: " + ", ".join(f"{e['name']}({e['start']:.1f})" for e in noher))

# What the left pane's upper box holds over the whole song, by the rule `draw_body` applies: the
# film's dsh window when it is on screen, the lone caret over GONE..BACK, her figure on the shots
# `her_style` gives a solid portrait, and nothing when the pane is too short for either.
from collections import Counter  # noqa: E402
P = T.SP if SCHOOL else T.FP
pane = Counter()
psec = Counter()
for e in eng.table:
    mid = (e["start"] + e["end"]) / 2
    dur = e["end"] - e["start"]
    if P.dsh_gone(mid):
        k = "caret  "
    elif P.dsh_inside(mid) and (SCHOOL or T.her_style(e)[0] != "half"):
        k = "window "
    elif e["her"]:
        k = "her    "
    else:
        k = "empty  "
    pane[k] += 1
    psec[k] += dur
print("\nleft pane, by what is in it (per shot, sampled at the shot's middle):")
for k, n in sorted(pane.items()):
    print(f"    {k} {n:3d} shots  {psec[k]:6.1f} s of {tot:.1f} s ({100 * psec[k] / tot:2.0f} %)")

print(f"\n{'size':>9} {'frames':>7} {'mean':>9} {'p95':>9} {'worst':>9} {'off':>5}  errors")
bad = 0
for cols, rows in SIZES:
    s = T.Screen(cols, rows)
    out = io.StringIO()
    step = STEP[cols]
    times = []
    n = 0
    off = 0
    err = None
    for k in range(0, round(T.END * 24), step):
        t = k / 24
        t1 = time.perf_counter()
        try:
            T.draw(s, d, eng, t, True, 24.0)
        except Exception:
            err = f"t={t:.3f}\n" + traceback.format_exc()
            break
        times.append((time.perf_counter() - t1) * 1000)
        # every cell the draw wrote must be printable; None would mean a missed blank
        off += sum(1 for row in s.buf for c in row if c is None or not isinstance(c[0], str))
        s.render_diff(out)
        n += 1
    if err:
        bad += 1
        print(f"{cols:>4}x{rows:<4} {n:>7}  FAILED\n{err}")
    else:
        ts = sorted(times)
        mean = sum(ts) / len(ts)
        p95 = ts[int(len(ts) * 0.95)]
        print(f"{cols:>4}x{rows:<4} {n:>7} {mean:>8.2f}ms {p95:>8.2f}ms {ts[-1]:>8.2f}ms {off:>5}  "
              f"{'ok' if ts[-1] < 41.7 else 'SLOW'}")

# the left pane's upper box, on the shots that decide it. Two things can be in it now: her figure
# (`/dev/me`), or the film's own dsh window (`dsh web`, or `hangxiaotian` under this variant - the
# title is `tui_live.WINDOW_TITLE`), which is what the film itself puts there from 5.0 s to the end -
# so a shot where the film draws her and the box holds the window is the film's answer, not a
# regression. What would be a regression is an *empty* box on a shot the film draws her.
#
# Under the school variant the window is in that box on **every** shot (`school_keeps_pane` returns
# False unconditionally), so the same table would report sixteen rows of "window, no mismatch" and
# nothing else. What is worth probing there instead is the pane the variant does *not* control the
# position of: the right-hand column. A school pane that drew into the left column, or one that failed
# to draw at all, is invisible in the film's own census and is the realistic regression, so the probes
# below check for it by drawing the last second up to each moment and looking for the pane's own
# header in the dump, on the right-hand side of the split.
print(f"\nleft pane presence (her '/dev/me', or the window '{T.WINDOW_TITLE}'), sampled per shot:")
FULL_BLEED = {"shot_exec_hit", "shot_count", "shot_last_execution", "shot_black",
              "shot_flood", "shot_collapse"}   # the last two take the whole screen, no pane at all
probes = [("shot_power", 0.5), ("shot_protection", 2.4), ("shot_pieces", 4.4), ("shot_infinity", 40.8),
          ("shot_unite", 55.4), ("shot_deeply", 57.6), ("shot_simulations", 61.5), ("shot_strange", 72.5),
          ("shot_erase", 120.7), ("shot_moe_dense", 136.3), ("shot_flood", 145.9),
          ("shot_collapse", 175.5), ("shot_whale_fall", 199.5), ("shot_have_you_back", 170.2),
          ("shot_grpo", 177.5), ("shot_me_trapped", 189.6)]
s = T.Screen(197, 52)
print(f"  {'shot':<22} {'t':>7}  film  hers  win")
wrong = 0
for name, t in probes:
    ent = eng.entry_at(t)
    # play the last second up to t: a jump *is* a cut, and the reveal the cut starts holds the old
    # picture in the box for half a second, so a probe drawn at a jump would read the previous
    # probe's pane.
    for k in range(24):
        T.draw(s, d, eng, max(0.0, t - 1 + k / 24), True, 24.0)
    dump = s.text_dump()
    box = T.WINDOW_TITLE in dump
    hers = "/dev/me" in dump
    film_her = bool(ent and ent["her"])
    film_win = P.dsh_inside(t) and not P.dsh_gone(t)
    if SCHOOL:
        flag = ""
        import school_gate as G
        if G.window_open(t):
            # The variant is asking its one question at this moment and the panel covers the left
            # column, so what the probe reads there is the question, not a missing pane. One probe
            # lands inside the five-second window (131.9-136.9): `shot_moe_dense`'s midpoint, 136.3.
            # This was read as a mismatch for as long as this tool's exit code was ignored - the sweep
            # printed PROBLEMS and every script that ran it carried on, which is why a check has to be
            # able to fail a script (see `project/check.cmd`).
            flag = "   n/a (the college question is on screen)"
        elif name not in FULL_BLEED and not box:
            flag = "   <-- MISMATCH: the school window should hold the pane here"
            wrong += 1
    elif name in FULL_BLEED:
        flag = "   n/a (TUI draws this shot full-bleed)"
    elif film_her and not (box or hers):
        flag = "   <-- MISMATCH: the film draws her and the box is empty"
        wrong += 1
    elif box and not (film_win or film_her or P.dsh_gone(t)):
        flag = "   <-- MISMATCH: the film has neither a window nor her here"
        wrong += 1
    else:
        flag = ""
    print(f"  {name:<22} {t:>7.2f}  {str(film_her):>5} {str(hers):>5} {str(box):>5}{flag}")

# The school variant's own check is the schedule, and it is done above. An earlier version of this
# section also measured "how much ink landed left of the split", to catch a pane drawing outside its
# rect - and it was not a usable signal: the chat window legitimately fills the left column with 400-
# 600 ink cells, so every sample read as a spill. The rect is handed to the pane by `draw_body` and the
# *clip* is `school_courses._Kit`, which is exactly what `_dev/pane_probe.py` already tests by drawing
# into a small screen and looking for ink outside it. Keeping a second, blunter copy of that check here
# would only produce six lines of false alarm per run.

print(f"\n{'OK' if bad == 0 and wrong == 0 and not bad_climax else 'PROBLEMS: %d crashes, %d pane mismatches, %s' % (bad, wrong, 'schedule problems' if bad_climax else 'none')}")
# and the exit code says the same thing as the line above, so `check.cmd` does not have to parse it
raise SystemExit(0 if (bad == 0 and wrong == 0 and not bad_climax) else 1)
