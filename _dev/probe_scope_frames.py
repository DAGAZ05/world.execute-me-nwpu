"""这一批只动了片尾那 13 秒吗？—— 逐帧比较"改之前"与"改之后"，给出差异的时间范围。

批 89 加了卡在 99% 的进度条（提示词文档第 06 条）。**它是刻意改画面**，所以
`_dev/probe_diff_bytes.py` 的 `DIFFERENT` 是预期的，不能当成回归。真正要守的是
"改动只落在该落的地方"：`shot_whale_fall`（193.54-205.54）与 `shot_last_execution`
（205.54-207.08）两个镜头，**其余 199 秒一帧都不该变**。

做法：同一份代码在**两个状态下**各跑一遍全曲，逐帧 dump 屏幕文本的 sha256 再比。
"改之前"的那一遍用 `git stash` 临时把改动收起来，跑完立刻 `stash pop` 恢复——
不用 `git archive`，因为那个取不出 `player/film` 与 `assets` 里的贴图，
`Engine()` 会直接起不来（踩过：FileNotFoundError: whale-cheerful.webp）。

    python _dev/probe_scope_frames.py --before HEAD
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "player" / "_tools"
#: 预期允许出现差异的窗口：`shot_whale_fall` 的第一帧到 `shot_last_execution` 的最后一帧。
#: **这些数字是逐帧扫出来的**（`_dev/probe_bar_rows.py`），不是从 shot 表抄的——
#: 表上的 193.54 / 205.54 / 207.083 与 `Engine.at()` 实际给的东西差 1-2 帧。
ALLOWED = (193.583, 207.042)
#: 容差 = 一帧（1/24 ≈ 0.0417 s）再放宽一点。**这不是放松判据，是承认量化**：
#: 采样点是 `i / FPS`，所以镜头边界 193.54 落在帧 193.583 上、207.083 落在 207.083~207.125 上，
#: 端点必然落在半个到一个帧步长之外。第一版写 0.06 就把一个完全正确的改动判成了 FAIL。
TOL = 0.12
FPS = 24.0

SCRIPT = '''
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
# **每一帧都用一个新的 Screen**：这样量到的只有"这一帧画了什么"，
# 不含上一帧的残留。复用同一个 Screen 连续 draw 而不 render_diff，
# 会让没被清掉的格子留在缓冲里——`_dev/probe_diff_at.py` 就是这样把进度条
# 误判成"延伸进黑屏"的。判据必须与播放器同序：draw 之后立刻 render_diff。
for i in range(n):
    t = i / FPS
    s = T.Screen(197, 52)
    sink = io.StringIO()
    T.draw(s, data, eng, t, True, FPS)
    s.render_diff(sink)
    print(i, hashlib.sha256(s.text_dump().encode("utf-8", "replace")).hexdigest()[:16])
'''


def run_frames() -> dict:
    """在当前工作区跑全曲，返回 {帧号: 文本摘要}。"""
    script = SCRIPT.format(tools=str(TOOLS))
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(ROOT))
    if p.returncode != 0:
        raise SystemExit(f"frame run failed:\n{(p.stderr or '')[-2500:]}")
    frames = {}
    for line in (p.stdout or "").splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[0].isdigit():
            frames[int(parts[0])] = parts[1]
    return frames


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--before", default="HEAD",
                    help="用来对比的 git ref（默认 HEAD）；改动所在的文件先在哪个 ref 上")
    ap.add_argument("--allow", metavar="LO,HI", default=None,
                    help="允许出现差异的时间窗口，秒。缺省用片尾进度条的窗口 "
                         "(193.583,207.042)；心形改动用 --allow 184.33,187.97。"
                         "**它是判据的一部分**：窗口写错就会把一个正确的改动判成 FAIL。")
    ap.add_argument("--keep-before", action="store_true",
                    help="不 stash（当工作区已经是'改之前'时用）")
    a = ap.parse_args()
    allowed = ALLOWED
    if a.allow:
        try:
            lo_s, hi_s = a.allow.split(",")
            allowed = (float(lo_s), float(hi_s))
        except ValueError:
            raise SystemExit(f"--allow 需要 LO,HI（秒），收到 {a.allow!r}")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print("跑'改之后'（当前工作区）...")
    after = run_frames()
    print(f"  {len(after)} 帧")

    # **"改之前"必须真的切到旧代码。** 第一版用 `git stash` 收改动，但如果改动已经 commit
    # （这一批的工作流就是先提交再验证），stash 是空的，于是两遍跑的都是同一份代码，
    # 结论变成"0 帧不同"——一个假阴性。改用 `git checkout <ref> -- player/_tools`
    # 显式取旧文件，跑完再 `git checkout HEAD -- player/_tools` 恢复。
    print(f"跑到'改之前'（checkout {a.before} 的 player/_tools）...")
    cur = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT), capture_output=True,
                         text=True).stdout.strip()
    co = subprocess.run(["git", "checkout", a.before, "--", "player/_tools"], cwd=str(ROOT),
                        capture_output=True, text=True)
    if co.returncode != 0:
        raise SystemExit(f"git checkout {a.before} failed: {co.stderr[:400]}")
    before = None
    try:
        before = run_frames()
        print(f"  {len(before)} 帧")
    finally:
        r = subprocess.run(["git", "checkout", cur, "--", "player/_tools"], cwd=str(ROOT),
                           capture_output=True, text=True)
        print(f"  已恢复当前代码（checkout {cur[:8]} rc={r.returncode}）")
        if r.returncode != 0:
            raise SystemExit(f"**恢复失败，请手动 git checkout HEAD -- player/_tools**\n"
                             f"{r.stderr[:400]}")
    print()

    common = sorted(set(before) & set(after))
    diff = [i for i in common if before[i] != after[i]]
    print(f"比较 {len(common)} 帧；不同的 {len(diff)} 帧")
    if not diff:
        print("两版逐帧完全相同 —— 这一批的改动没生效（或没落在 dump 得到的画面上）。")
        raise SystemExit(1)

    lo, hi = diff[0] / FPS, diff[-1] / FPS
    print(f"差异时间范围：{lo:.2f} - {hi:.2f} s")
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
        print(f"  {s0 / FPS:7.2f} - {s1 / FPS:7.2f} s   ({s1 - s0 + 1} 帧)")
    if len(runs) > 20:
        print(f"  ...（还有 {len(runs) - 20} 段）")
    print()
    outside = [(s0, s1) for s0, s1 in runs
               if not (allowed[0] - TOL <= s0 / FPS and s1 / FPS <= allowed[1] + TOL)]
    if outside:
        print(f"FAIL —— 有 {len(outside)} 段差异落在目标窗口 "
              f"{allowed[0]:.2f}-{allowed[1]:.2f} s 之外：")
        for s0, s1 in outside[:10]:
            print(f"  {s0 / FPS:.2f} - {s1 / FPS:.2f} s")
        raise SystemExit(1)
    print(f"PASS —— 全部差异都落在目标窗口 {allowed[0]:.2f}-{allowed[1]:.2f} s 内"
          f"（容差 {TOL} s，一帧 1/24≈0.042 s）")


if __name__ == "__main__":
    main()
