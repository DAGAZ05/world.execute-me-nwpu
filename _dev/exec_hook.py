"""钩出 `EXEC nn/nn` 到底是谁画的。

做法：把 `school_courses._Kit._header` 包一层，凡是这一帧的 tag 匹配 `EXEC \\d+/\\d+` 的，
就把**那一刻的时间、tag、标题、以及调用栈**打出来。这样不靠静态搜文本。
"""
from __future__ import annotations

import io
import os
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

import school_courses as C   # noqa: E402
import school_panels as SP   # noqa: E402
import tui_live as T         # noqa: E402

HITS: dict[str, list] = {}


def main() -> None:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    orig = C._Kit._header

    def hooked(self, title, n, total):  # noqa: ANN001
        if n:
            key = "%s | n=%d total=%d" % (title, n, total)
            if key not in HITS:
                # 调用栈里第一个非本文件的帧就是"谁传的"
                frames = [f for f in traceback.extract_stack()[:-1]
                          if "school_courses.py" not in f.filename]
                HITS[key] = frames[-3:]
        return orig(self, title, n, total)

    C._Kit._header = hooked

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    import school_gate as G
    G.assume()
    d, eng = T.Data(), T.Engine()
    s = T.Screen(197, 52)
    sink = io.StringIO()
    t = 100.0
    while t < 175.0:
        T.draw(s, d, eng, t, True, 24.0)
        s.render_diff(sink)
        t += 0.5

    print("=== 所有非零 n（也就是会画 EXEC nn/nn 的地方）===")
    for key, frames in HITS.items():
        print("  %s" % key)
        for f in frames:
            print("      %s:%d  %s" % (Path(f.filename).name, f.lineno, (f.line or "")[:96]))
    if not HITS:
        print("  （100-175 s 内没有非零 n）")


if __name__ == "__main__":
    main()
