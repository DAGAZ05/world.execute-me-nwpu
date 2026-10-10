"""字节级 A/B：这次 `render_diff` 的改动有没有动到任何一个输出字节？

`_dev/ansi_probe.py` 已经回答了"终端看到的画面是否等于缓冲"（425/425 帧无差异）。但那只证明
**画面**没变，不证明**字节流**没变——而这次的优化（整行相同时跳过、把变过的列收集到 `screen.dirty`）
如果哪里写错了，最可能的症状恰恰是"画面还对、但多写或少写了一些转义"，那在真终端上就是闪烁、
就是 SGR 状态不同步。

所以这个探针把一件事做绝：跑同一批帧，把每一帧的转义流**按字节**存下来。
用法上分两次跑，中间 `git stash` 切换实现：

    python _dev/probe_diff_bytes.py --out _dev/out/diffbytes/after.bin
    git stash push -- player/_tools/tui_live.py
    python _dev/probe_diff_bytes.py --out _dev/out/diffbytes/before.bin
    git stash pop
    python _dev/probe_diff_bytes.py --compare _dev/out/diffbytes/before.bin _dev/out/diffbytes/after.bin

`--compare` 用 sha256 比总长与内容，不一致时打印**第一处不同的偏移与上下文**，
而不是只说一句"不一样"。
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

# 一帧一帧地跨过整首歌：转场、字幕、飞行、结尾都在里面
SAMPLE = [round(v, 3) for v in
          [0.0 + k * 1.7 for k in range(30)] +
          [12.4 + k * 0.5 for k in range(8)] +        # 运-20 低空掠过（最贵的帧）
          [61.0 + k * 0.25 for k in range(12)] +      # 副歌，歌词逐字
          [147.0 + k * 0.5 for k in range(10)] +      # EXECUTION
          [184.4 + k * 0.4 for k in range(10)] +      # 心形（pane_love_class, 184.33-187.97）
          [190.0 + k * 0.4 for k in range(6)] +       # 结尾（几个 shot 的边界）
          [195.5 + k * 0.5 for k in range(8)] +       # 鲸落（底噪在这里最显眼）
          [206.0 + k * 0.35 for k in range(6)] +      # last_execution / black
          [210.0 + k * 0.4 for k in range(5)]]        # 末帧


class Recorder(io.StringIO):
    """A sink that keeps the bytes, so the whole run can be hashed."""

    def __init__(self) -> None:
        super().__init__()
        self.blob = bytearray()
        self.per_frame = []

    def write(self, text: str) -> int:
        data = text.encode("utf8")
        self.blob += data
        self.per_frame.append(len(data))
        return len(text)


def capture(cols, rows) -> tuple[bytes, list[int]]:
    import tui_live as T
    import school_panels as SP
    import school_fx as FX
    import school_gate as G

    T.VAR[0] = "school"
    T.SP = SP
    SP.init_palette(T.ui, T.mix, dict(ME_TEXT=T.ME_TEXT, ANOM=T.ANOM, RED=T.RED, BG=T.BG))
    G.reset("s")
    FX.warm(cols, rows)
    eng, data = T.Engine(), T.Data()
    s = T.Screen(cols, rows)
    sink = Recorder()
    for t in SAMPLE:
        sink.per_frame = []
        sink.blob = bytearray()
        T.draw(s, data, eng, t, True, 60.0)
        s.render_diff(sink)
        yield bytes(sink.blob), sink.per_frame[0] if sink.per_frame else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="write the whole stream here")
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("--size", default="197x52")
    a = ap.parse_args()

    if a.compare:
        b = Path(a.compare[0]).read_bytes()
        f = Path(a.compare[1]).read_bytes()
        hb, hf = hashlib.sha256(b).hexdigest(), hashlib.sha256(f).hexdigest()
        print(f"before  {len(b):9d} bytes  sha256 {hb}")
        print(f"after   {len(f):9d} bytes  sha256 {hf}")
        if b == f:
            print("\nIDENTICAL - the change altered no byte the terminal sees")
            return
        n = min(len(b), len(f))
        off = next((i for i in range(n) if b[i] != f[i]), n)
        print(f"\nDIFFERENT at offset {off}")
        print(f"  before ...{b[max(0, off - 40):off + 40]!r}")
        print(f"  after  ...{f[max(0, off - 40):off + 40]!r}")
        raise SystemExit(1)

    cols, rows = (int(v) for v in a.size.lower().split("x"))
    gc.disable()
    blob = bytearray()
    sizes = []
    for i, (frame, n) in enumerate(capture(cols, rows)):
        blob += frame
        sizes.append(len(frame))
    # sum the per-frame lengths; a running counter fed from the generator's second value silently
    # reported only the first frame, which is exactly the kind of "number that looks plausible" this
    # project's probes exist to not print (the file on disk was always right, the line about it was not)
    dest = Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(bytes(blob))
    print(f"{len(sizes)} frames, {sum(sizes)} bytes of escape stream -> {dest}")
    print(f"sha256 {hashlib.sha256(bytes(blob)).hexdigest()}")
    print(f"per-frame bytes: min {min(sizes)} median {sorted(sizes)[len(sizes) // 2]} "
          f"max {max(sizes)}  first five {sizes[:5]}")


if __name__ == "__main__":
    main()
