@echo off
REM ===================================================================
REM  world.execute(me); - NWPU school variant - terminal player
REM
REM  NOTE FOR WHOEVER EDITS THIS FILE: it is deliberately ASCII-only.
REM  cmd.exe reads a .cmd in the console's OEM codepage (GBK on a
REM  Chinese Windows), NOT as UTF-8, so Chinese comments in here arrive
REM  as byte soup and get executed as stray commands. That is exactly
REM  what happened to the first version of this launcher. Put the
REM  Chinese in the Python and keep this file in plain ASCII.
REM
REM  Needs: Windows, Python 3.10+ with pillow and numpy.
REM  Usage:  double-click, or  run.cmd --start 147  from a console.
REM ===================================================================
setlocal
cd /d "%~dp0"

set PV_VARIANT=school
set PYTHONUTF8=1

REM prefer the python bundled next to the original package, else PATH
if exist "python\python.exe" (
  set "PY=python\python.exe"
) else (
  set "PY=python"
)

REM a window of at least 175x52 columns is what the layout is drawn for
"%PY%" "_tools\tui_live.py" --variant school %*

if errorlevel 1 (
  echo.
  echo If it complained about pillow or numpy, run:
  echo     "%PY%" -m pip install pillow numpy
  pause
)
endlocal
