"""两个版本在某一时刻的**整屏差异**，逐格列出来。

`_dev/probe_scope_frames.py` 只给"哪些帧不同"，不给"差在哪"。当一帧被判为不同、
但某个特征（比如进度条）又查不到时，必须知道**到底哪一格变了**，否则只剩猜。

    python _dev/probe_diff_at.py --before 9496425 --at 207.46
    python _dev/probe_diff_at.py --before 9496425 --at 207.46 --rows 40-52
"""
from __future__ import annotations

import argparse
import io
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
t = {t}
s = T.Screen(197, 52); sink = io.StringIO()
# 先跑到这一帧之前，让状态（幽灵、转场）收敛到同一处
for i in range(max(0, int(t * T.FPS) - 40), int(t * T.FPS) + 1):
    T.draw(s, data, eng, i / T.FPS, True, T.FPS); s.render_diff(sink)
print("TEXTDUMP")
for y in range(52):
    print("R" + str(y).zfill(2) + "|" + "".join(c[0] for c in s.buf[y]))
print("COLORS")
for y in range(52):
    row = []
    for x in range(197):
        row.append("%02x%02x%02x" % tuple(s.buf[y][x][1]))
    print("C" + str(y).zfill(2) + "|" + "".join(row))
'''


def collect(tools: Path, t: float) -> dict:
    import subprocess as sp
    script = SCRIPT.format(tools=str(tools), t=repr(t))
    p = sp.run([sys.executable, "-c", script], capture_output=True, text=True,
               encoding="utf-8", errors="replace", cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(f"run failed:\n{(p.stderr or '')[-1800:]}")
    text, colors = {}, {}
    mode = None
    for line in (p.stdout or "").splitlines():
        if line == "TEXTDUMP":
            mode, = ("text",)
            continue
        if line == "COLORS":
            mode = "colors"
            continue
        if mode == "text" and line.startswith("R"):
            y = int(line[1:3])
            text[y] = line[4:]
        elif mode == "colors" and line.startswith("C"):
            y = int(line[1:3])
            colors[y] = line[4:]
    return dict(text=text, colors=colors)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", required=True)
    ap.add_argument("--at", type=float, required=True)
    ap.add_argument("--rows", help="e.g. 40-52")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    lo, hi = 0, 51
    if a.rows:
        x, y = a.rows.split("-")
        lo, hi = int(x), int(y)

    print(f"收集 t={a.at} （当前）...")
    after = collect(TOOLS, a.at)
    cur = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                         text=True).stdout.strip()
    subprocess.run(["git", "checkout", a.before, "--", "player/_tools"], cwd=str(ROOT),
                   capture_output=True, text=True)
    print(f"收集 t={a.at} （{a.before}）...")
    try:
        before = collect(TOOLS, a.at)
    finally:
        subprocess.run(["git", "checkout", cur, "--", "player/_tools"], cwd=str(ROOT),
                       capture_output=True, text=True)
    print(f"已恢复 {cur[:8]}")
    print()

    total = 0
    for y in range(lo, hi + 1):
        bt, ct = before["text"].get(y, ""), after["text"].get(y, "")
        bc, cc = before["colors"].get(y, ""), after["colors"].get(y, "")
        cdiffs = []
        for x in range(197):
            b = bc[x * 6:x * 6 + 6]
            c = cc[x * 6:x * 6 + 6]
            if b != c:
                cdiffs.append((x, b, c))
        if bt != ct or cdiffs:
            total += 1
            print(f"row {y:2d}")
            if bt != ct:
                for x in range(min(len(bt), len(ct))):
                    if bt[x] != ct[x]:
                        print(f"    x={x:3d} char: {bt[x]!r} -> {ct[x]!r}")
            for x, b, c in cdiffs[:8]:
                print(f"    x={x:3d} fg  : #{b} -> #{c}")
            if len(cdiffs) > 8:
                print(f"    ...还有 {len(cdiffs) - 8} 格颜色不同")
    print()
    if total == 0:
        print("这一帧两版完全相同（说明范围扫描的判定与这里不一致，需检查采样方式）。")
    else:
        print(f"共 {total} 行不同。")


if __name__ == "__main__":
    main()
