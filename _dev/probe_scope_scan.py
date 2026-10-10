"""这一批只动了片尾那 13 秒吗？—— 逐帧比较"改之前"与"改之后"，给出差异的时间范围。

批 89 加了卡在 99% 的进度条（提示词文档第 06 条）。**它是刻意改画面**，所以
`_dev/probe_diff_bytes.py` 的 `DIFFERENT` 是预期的，不能当成回归。真正要守的是
"改动只落在该落的地方"：`shot_whale_fall`（193.54-205.54）与 `shot_last_execution`
（205.54-207.08）两个镜头，**其余 199 秒一帧都不该变**。

判据：对全曲逐帧 dump 屏幕文本的 sha256，比较两个版本，找出所有不同的帧并报告
它们的时间范围。这比"看一个字节偏移"强，因为它能证明没有别的地方被顺手改动。

    python _dev/probe_scope_scan.py --before <git-ref>
"""
from __future__ import annotations

import argparse
import hashlib
import os
import os.path as osp
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"

#: 预期允许出现差异的窗口（改动的目标）
ALLOWED = (193.54, 207.08)

SCRIPT = r'''
import io, os, sys, hashlib
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
FPS = T.FPS
n = int(T.END * FPS)
s = T.Screen(197, 52)
sink = io.StringIO()
for i in range(n):
    t = i / FPS
    T.draw(s, data, eng, t, True, FPS)
    s.render_diff(sink)
    print(i, hashlib.sha256(s.text_dump().encode("utf-8", "replace")).hexdigest()[:16])
'''.format(tools=str(TOOLS))


def run_frames(ref: str | None = None) -> list:
    """在当前工作区（或指定 git ref）跑全曲，返回每帧的文本摘要。"""
    if ref is None:
        env = dict(os.environ)
        p = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(ROOT), env=env)
        if p.returncode != 0:
            raise SystemExit(f"frame run failed:\n{p.stderr[-2000:]}")
        out = p.stdout
    else:
        # 用 git show 把该 ref 的 _tools 取到一个临时目录里跑
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="scope_"))
        p = subprocess.run(["git", "archive", ref, "player/_tools"], capture_output=True,
                           cwd=str(ROOT))
        if p.returncode != 0:
            raise SystemExit(f"git archive failed: {p.stderr[:400]}")
        subprocess.run(["tar", "-x", "-C", str(tmp)], input=p.stdout, check=True)
        tools = tmp / "player" / "_tools"
        script = SCRIPT.replace(str(TOOLS), str(tools))
        r = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", cwd=str(tmp))
        if r.returncode != 0:
            raise SystemExit(f"frame run (ref {ref}) failed:\n{r.stderr[-2000:]}")
        out = r.stdout
    frames = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit():
            frames[int(parts[0])] = parts[1]
    return frames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="HEAD", help="用来对比的 git ref（默认 HEAD）")
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("跑'改之后'（当前工作区）...")
    after = run_frames(None)
    print(f"  {len(after)} 帧")
    print(f"跑'改之前'（{a.before}）...")
    before = run_frames(a.before)
    print(f"  {len(before)} 帧")
    print()

    fps = 24.0
    common = sorted(set(before) & set(after))
    diff = [i for i in common if before[i] != after[i]]
    print(f"比较 {len(common)} 帧；不同的 {len(diff)} 帧")
    if diff:
        lo, hi = diff[0] / fps, diff[-1] / fps
        print(f"差异时间范围：{lo:.2f} - {hi:.2f} s")
        # 连续的段
        runs = []
        start = prev = diff[0]
        for i in diff[1:]:
            if i == prev + 1:
                prev = i
            else:
                runs.append((start, prev))
                start = prev = i
        runs.append((start, prev))
        print(f"共 {len(runs)} 段：")
        for s0, s1 in runs[:20]:
            print(f"  {s0 / fps:7.2f} - {s1 / fps:7.2f} s   ({s1 - s0 + 1} 帧)")
        if len(runs) > 20:
            print(f"  ...（还有 {len(runs) - 20} 段）")
        print()
        outside = [(s0, s1) for s0, s1 in runs
                   if not (ALLOWED[0] - 0.05 <= s0 / fps and s1 / fps <= ALLOWED[1] + 0.05)]
        if outside:
            print(f"FAIL —— 有 {len(outside)} 段差异落在目标窗口 {ALLOWED} 之外：")
            for s0, s1 in outside[:10]:
                print(f"  {s0 / fps:.2f} - {s1 / fps:.2f} s")
            raise SystemExit(1)
        print(f"PASS —— 全部差异都落在目标窗口 {ALLOWED[0]:.2f}-{ALLOWED[1]:.2f} s 内")
    else:
        print("两版逐帧完全相同（那说明这一批的改动没生效）。")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
