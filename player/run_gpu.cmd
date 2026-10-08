@echo off
REM ===================================================================
REM  world.execute(me); - NWPU school variant - GPU terminal launcher
REM
REM  Same player, same Python: this file only chooses *where* it runs.
REM  The terminal is the second half of the smoothness budget - see
REM  _dev/paint_probe.py. A full-frame sprite (the low-pass crossing)
REM  writes ~170 KB of escape stream per frame, and the classic console
REM  host is the slowest thing in that chain; a GPU terminal (Windows
REM  Terminal's atlas engine, WezTerm, Alacritty) paints it several
REM  times faster, which is the difference between 30 and 45 fps on a
REM  machine where Python is not the wall.
REM
REM  ASCII-ONLY, for the reason player\run.cmd states at its top:
REM  cmd.exe reads a .cmd in the OEM codepage (GBK here), not UTF-8,
REM  and then runs fragments of the comments as commands. This file
REM  broke that rule once already, in the line about the aircraft.
REM
REM  AND NO SHELL CHAINING, which is the other thing this file learned:
REM  `set "RUN=a&&b"` does *not* keep the `&&` - cmd splits the line on
REM  it and runs the tail, which started the player from the wrong
REM  directory. So the inner command is one program plus arguments, and
REM  the two variables it needs (PV_VARIANT, PYTHONUTF8) are inherited
REM  by the child process instead of being re-set inside it.
REM
REM  Usage:  run_gpu.cmd                     school variant, new tab
REM          run_gpu.cmd --start 147         arguments go to the player
REM          run_gpu.cmd --fps-cap 30        any player flag works
REM          run_gpu.cmd --dry-run           print the command, run nothing
REM          set WEM_SIZE=197,52             initial window, in cells
REM
REM  Four settings this cannot change from a command line, and they are
REM  the ones that matter - make them permanent in the terminal's own
REM  settings, not per run:
REM    * Windows Terminal profile: "useAcrylic": false, and Appearance
REM      -> Transparency off. A translucent window makes every
REM      repainted cell a compositor pass.
REM    * "blinking": "solid" for the cursor: a blinking cursor repaints
REM      its own row on every blink.
REM    * The atlas engine is the default in Windows Terminal 1.18+ and
REM      is the GPU renderer this launcher is for; on older builds set
REM      "useAtlasEngine": true.
REM    * Keep the window near 197x52 cells: the film is drawn for that
REM      size, and a maximised 300x90 window is ~2.4x the cells to
REM      repaint every frame.
REM    * Do not pipe the player's output through anything - tee, a
REM      session recorder, a capture harness. 5 MB/s down a pipe is
REM      tens of fps against single digits, whatever the terminal.
REM ===================================================================
setlocal EnableExtensions
set "PLAYER=%~dp0"
if "%PLAYER:~-1%"=="\" set "PLAYER=%PLAYER:~0,-1%"
if not defined WEM_SIZE set "WEM_SIZE=197,52"
REM ...inherited by the player, not set inside it: see the note above
set "PV_VARIANT=school"
set "PYTHONUTF8=1"

REM ---- arguments: everything but --dry-run goes to the player --------
set "ARGS="
set "DRY="
:args
if "%~1"=="" goto args_done
if /i "%~1"=="--dry-run" set "DRY=1"
if /i not "%~1"=="--dry-run" set "ARGS=%ARGS% "%~1""
shift
goto args
:args_done

REM ---- the player, as run.cmd runs it -------------------------------
set "PY=python"
if exist "%PLAYER%\python\python.exe" set "PY=python\python.exe"
set "INNER=%PY% _tools\tui_live.py --variant school%ARGS%"

REM ---- which GPU terminal is here -----------------------------------
set "TERM="
where wt.exe >nul 2>nul && set "TERM=wt"
if not defined TERM where wezterm.exe >nul 2>nul && set "TERM=wezterm"
if not defined TERM where alacritty.exe >nul 2>nul && set "TERM=alacritty"

for /f "tokens=1,2 delims=," %%a in ("%WEM_SIZE%") do set "WEMC=%%a" & set "WEMR=%%b"

REM ---- the launch line, one branch per terminal ----------------------
REM  Windows Terminal's *top-level* options come before the subcommand:
REM  `wt --size 197,52 new-tab -d DIR -- cmd /c ...` works, and
REM  `wt new-tab -d DIR --size 197,52 ...` does not - it opens a tab
REM  and silently drops the command line. Measured, not guessed.
if not defined TERM goto no_terminal
if /i "%TERM%"=="wt" set "LAUNCH=wt.exe -w -1 --size %WEM_SIZE% new-tab -d "%PLAYER%" -- cmd /c %INNER%"
if /i "%TERM%"=="wezterm" set "LAUNCH=wezterm.exe start --cwd "%PLAYER%" --config initial_cols=%WEMC% --config initial_rows=%WEMR% -- cmd /c %INNER%"
if /i "%TERM%"=="alacritty" set "LAUNCH=alacritty.exe --working-directory "%PLAYER%" -o window.dimensions.columns=%WEMC% -o window.dimensions.lines=%WEMR% -e cmd /c %INNER%"

if defined DRY goto dry
goto launch

:dry
echo [run_gpu] terminal: %TERM%
echo [run_gpu] player:   %INNER%
echo [run_gpu] launch:   %LAUNCH%
endlocal
exit /b 0

:launch
echo [run_gpu] %TERM%  %WEM_SIZE% cells  ^(player: %INNER%^)
echo [run_gpu] if it names pillow or numpy:  %PY% -m pip install pillow numpy
%LAUNCH%
if errorlevel 1 goto launch_failed
endlocal
exit /b 0

:launch_failed
echo [run_gpu] %TERM% would not start; running in this console instead.
pushd "%PLAYER%"
%INNER%
popd
endlocal
exit /b 0

:no_terminal
echo [run_gpu] no GPU terminal found ^(wt.exe / wezterm.exe / alacritty.exe^).
echo [run_gpu] running in this console instead; for the GPU renderer:
echo [run_gpu]     winget install --id Microsoft.WindowsTerminal
pushd "%PLAYER%"
%INNER%
popd
endlocal
exit /b 0
