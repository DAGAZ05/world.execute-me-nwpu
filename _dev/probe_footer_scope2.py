"""footer 措辞改了之后，改动是不是只在 footer 那一行？—— 在**缓冲层**比，不碰转义流。

`_dev/probe_footer_scope.py` 想解码转义流来比，但它自己的解析器有 bug
（输出里出现 `\\x1b[3█`、`;195;217p` 这种破片），于是报出 33 行"差异"——那是解析器的形状。
**解码器写错比不写更糟**，所以换一条不需要解码的路。

`Screen.text_dump()` 本来就是稳定的屏幕快照（`_dev/probe_scope_frames.py` 用它做全曲回归），
而且这里要回答的问题不需要终端：**改动前后，第 1-51 行的文本是否逐行相同**。

做法：跑一帧，dump 全文；用 `--for` 指定一个数字只在**第几行**做一次人为标记，
从而定位差异行。更直接的办法是把两份 dump 存成文件用 diff 比——
这个脚本就输出两份 dump（当前 / 指定 git ref），并报告差异行号集合。

    python _dev/probe_footer_scope2.py --before HEAD~1
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"

SCRIPT = '''
import io, os, sys
sys.path.insert(0, r"{tools}")
os.environ.setdefault("PV_VARIANT", "school")
import tui_live as T
T.VAR[0] = "school"
import school_panels as SP
SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
T.SP = SP
import school_fx as FX
FX.warm(197, 52)
eng, data = T.Engine(), T.Data()
for t in {frames}:
    s = T.Screen(197, 52)
    sink = io.StringIO()
    T.draw(s, data, eng, t, True, T.FPS)
    s.render_diff(sink)
    print("===FRAME", t)
    for y in range(52):
        print("R%02d|" % y + "".join(c[0] for c in s.buf[y]))
'''


def collect(frames) -> dict:
    script = SCRIPT.format(tools=str(TOOLS), frames=repr(list(frames)))
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(f"run failed:\n{(p.stderr or '')[-2000:]}")
    out, cur = {}, None
    for line in (p.stdout or "").splitlines():
        if line.startswith("===FRAME"):
            cur = float(line.split()[1])
            out[cur] = {}
        elif line.startswith("R") and cur is not None:
            out[cur][int(line[1:3])] = line[4:]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="HEAD~1")
    ap.add_argument("--allow-rows", default="51", help="允许差异的行号（0-based，默认 51 = footer）")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    frames = [60.0 + k * 0.5 for k in range(4)] + [148.0, 184.5, 196.0, 0.5, 90.0]
    allow = {int(v) for v in a.allow_rows.split(",") if v.strip()}

    print("跑当前工作区...")
    now = collect(frames)
    cur = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                         text=True).stdout.strip()
    subprocess.run(["git", "checkout", a.before, "--", "player/_tools"], cwd=str(ROOT),
                   capture_output=True, text=True)
    print(f"跑 {a.before}...")
    try:
        old = collect(frames)
    finally:
        subprocess.run(["git", "checkout", cur, "--", "player/_tools"], cwd=str(ROOT),
                       capture_output=True, text=True)
        print(f"已恢复 {cur[:8]}")
    print()

    bad_rows = set()
    ncell = 0
    for t in frames:
        for y in range(52):
            b = (old.get(t) or {}).get(y, "")
            c = (now.get(t) or {}).get(y, "")
            if b != c:
                bad_rows.add(y)
                ncell += sum(1 for i in range(min(len(b), len(c))) if b[i] != c[i])
    print(f"取样 {len(frames)} 帧；不同的行（0-based）：{sorted(bad_rows) or '（无）'}")
    print(f"不同的格数合计：{ncell}")
    print(f"允许的行：{sorted(allow)}")
    print()
    outside = bad_rows - allow
    if outside:
        print(f"FAIL —— 差异落在允许集合之外：{sorted(outside)}")
        for y in sorted(outside)[:3]:
            t = frames[0]
            print(f"  row {y}:")
            print(f"    before {(old[t][y]).rstrip()[:110]!r}")
            print(f"    after  {(now[t][y]).rstrip()[:110]!r}")
        raise SystemExit(1)
    print("PASS —— 差异只在 footer 那一行。")
    y = sorted(bad_rows)[0]
    t = frames[0]
    print(f"  row {y} before …{(old[t][y])[-64:]!r}")
    print(f"  row {y} after  …{(now[t][y])[-64:]!r}")


if __name__ == "__main__":
    main()
