"""边界帧到底差在哪？—— `probe_scope_frames.py` 报告差异到 207.46 s，比窗口右端多了 0.38 s。

一个"超出预期"的差异有两种可能，必须分清：

  * **真的溢出了**（改动落到了不该落的时刻）——要修代码；
  * **窗口右端的定义不对**（`shot_last_execution` 的真正结束时刻不是我以为的 207.083）——要修探针。

这个脚本把边界上的几个帧的**文本与颜色**并排打出来，让差异看得见，而不是靠猜。
（"改之前"的一侧用 `git checkout <ref> -- player/_tools` 临时切过去拿。）

    python _dev/probe_boundary_frames.py --before HEAD~1 --from 207.0 --to 207.8
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
s = T.Screen(197, 52); sink = io.StringIO()
lo, hi = {lo}, {hi}
for i in range(int(lo * T.FPS), int(hi * T.FPS) + 1):
    t = i / T.FPS
    T.draw(s, data, eng, t, True, T.FPS); s.render_diff(sink)
    ent = eng.at(t)
    name = ent[0].fn.__name__ if ent and ent[0] and ent[0].fn else "?"
    row45 = "".join(c[0] for c in s.buf[45])
    nonblank = sum(1 for y in range(52) for c in s.buf[y] if c[0] not in (" ",))
    print("FRAME", round(t, 4), name, nonblank, "|" + row45.strip()[:90] + "|")
'''


def collect(tools: Path, lo: float, hi: float) -> dict:
    script = SCRIPT.format(tools=str(tools), lo=lo, hi=hi)
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(f"run failed:\n{(p.stderr or '')[-2000:]}")
    out = {}
    for line in (p.stdout or "").splitlines():
        if not line.startswith("FRAME "):
            continue
        parts = line.split(" ", 4)
        out[float(parts[1])] = line[6:]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="HEAD~1")
    ap.add_argument("--from", dest="lo", type=float, default=206.9)
    ap.add_argument("--to", dest="hi", type=float, default=207.8)
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("收集'改之后'...")
    after = collect(TOOLS, a.lo, a.hi)
    cur = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                         text=True).stdout.strip()
    subprocess.run(["git", "checkout", a.before, "--", "player/_tools"], cwd=str(ROOT),
                   capture_output=True, text=True)
    print("收集'改之前'...")
    try:
        before = collect(TOOLS, a.lo, a.hi)
    finally:
        subprocess.run(["git", "checkout", cur, "--", "player/_tools"], cwd=str(ROOT),
                       capture_output=True, text=True)
    print(f"已恢复 {cur[:8]}")
    print()

    keys = sorted(set(before) | set(after))
    for t in keys:
        b = before.get(t, "-")
        c = after.get(t, "-")
        mark = "  " if b == c else "**"
        print(f"{mark} t={t:7.3f}")
        print(f"     before: {b}")
        print(f"     after : {c}")
    print()
    print("'**' 标记的帧就是两版不同的帧；看它们落在 `shot` 的哪一段里。")


if __name__ == "__main__":
    main()
