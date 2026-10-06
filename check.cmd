@echo off
rem Run every check this project has, in one command, and say whether any of them failed.
rem
rem Each probe exits non-zero when it has something to report, so this is a chain of `||` and one
rem verdict at the end. The probes print their own detail; this file only says which one spoke up.
rem
rem THIS FILE MUST STAY ASCII, and this is not a style note. cmd.exe reads a .cmd in the OEM codepage
rem (GBK here), not UTF-8, and it *seeks by byte offset* to the next line it wants - so a multi-byte
rem character shifts every offset after it and cmd resumes in the middle of an earlier line, running
rem fragments of comments as commands. That is how run.cmd failed once, and how this header did: the
rem line below quoting the actual error message had a Chinese character in it, and the run printed
rem "'Run' is not recognized", "'verdict' is not recognized", and so on, for four words out of the
rem comments above it. The checks all still ran; the noise was the tell. Everything user-facing that
rem is not ASCII lives in the Python tools this calls.
rem
rem   check.cmd          the fast set: eight probes, about a minute
rem   check.cmd --full   and the two whole-song sweeps (a few minutes more)
setlocal
set FAIL=0
pushd "%~dp0"

echo === pane_probe      every pane at six sizes: exceptions, ink outside the rect, colour shape
python _dev\pane_probe.py || set FAIL=1

echo.
echo === clock_probe     every pane at full reveal: does it still move, or is it a still frame
python _dev\clock_probe.py || set FAIL=1

echo.
echo === span_probe      the short panes: is there anything on screen in the frame they first appear
python _dev\span_probe.py || set FAIL=1

echo.
echo === trans_probe     the transitions: the buffer invariant they can break
python _dev\trans_probe.py shatter slide zoom skew page --cells || set FAIL=1

echo.
echo === row_probe       the schedule: does any pane outlast the lyric it belongs to
python _dev\row_probe.py || set FAIL=1

echo.
echo === density_probe   composition: all-ink walls and all-text panes fail, banding is reported
python _dev\density_probe.py || set FAIL=1

echo.
echo === ops_probe       the ops box: is a tall drawing answered with more than one line of words
python _dev\ops_probe.py --step 2.0 || set FAIL=1

echo.
echo === frame_probe     how long a frame takes, cold and warm, against the 24 fps budget
rem This one measures time, so it has to have the machine to itself: run next to another build and the
rem worst frame reads 48 ms instead of 37 and the check fails on somebody else's work.
python _dev\frame_probe.py --sizes 197x52,120x34 || set FAIL=1

if /i "%~1"=="--full" (
  echo.
  echo === sweep school    the whole song, in process, at eight window sizes
  pushd player
  set PV_VARIANT=school
  python _tools\sweep_tui.py || set FAIL=1
  echo.
  echo === sweep original  the same for the film's own variant
  set PV_VARIANT=original
  python _tools\sweep_tui.py || set FAIL=1
  popd
)

echo.
if "%FAIL%"=="1" (
  echo RESULT: at least one check FAILED - see the check that spoke up above
) else (
  echo RESULT: all checks passed
)
popd
exit /b %FAIL%
