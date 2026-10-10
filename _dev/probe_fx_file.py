"""手改 `data/fx.json` 出错了会怎样？—— 逐种坏法验证它**不会把播放器带走**。

这个文件是给用户手改的，所以"写错了会怎样"必须比"写对了会怎样"更认真：
一个编辑器里改坏的文件不该让播放器起不来，也不该悄悄变成一个奇怪的状态。

判据（每一种坏法都要求）：
  * `_fx_load_file()` 返回 `None`（= 用默认值，三层全关），或者
  * 对**超范围**的数值，返回被**夹紧**到 0..1 的结果（`2` 当"全开"而不是报错）。

`_dev/probe_fx_file.py` 会临时改写 `player/data/fx.json`，跑完一定还原。

    python _dev/probe_fx_file.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "player" / "_tools"))
os.environ.setdefault("PV_VARIANT", "school")

CASES = [
    # (名字, 文件内容 或 None 表示删掉文件, 期望结果 None 或元组)
    ("文件不存在", None, None),
    ("空文件", "", None),
    ("坏 JSON", "{ this is not json", None),
    ("缺两个键", '{"phosphor": 0.5}', None),
    ("非数字", '{"phosphor": "many", "noise": 0, "dissolve": 0}', None),
    ("null 值", '{"phosphor": null, "noise": 1, "dissolve": 1}', None),
    ("超范围夹紧", '{"phosphor": 2, "noise": -1, "dissolve": 5}', (1.0, 0.0, 1.0)),
    ("顶层数组", "[0.5, 0.4, 0.6]", (0.5, 0.4, 0.6)),
    ("整数 0/1", '{"phosphor": 1, "noise": 1, "dissolve": 1}', (1.0, 1.0, 1.0)),
    ("带注释键", '{"_说明": "x", "phosphor": 0.6, "noise": 0.4, "dissolve": 1}', (0.6, 0.4, 1.0)),
    ("科学计数", '{"phosphor": 5e-1, "noise": 1e-1, "dissolve": 0}', (0.5, 0.1, 0.0)),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    path = ROOT / "player" / "data" / "fx.json"
    if not path.exists():
        raise SystemExit(f"missing: {path}（这个探针要改它，所以它必须已经存在）")
    original = path.read_text(encoding="utf-8")

    import importlib
    import tui_live as T
    importlib.reload(T)          # 确保读到的是当前文件

    print(f"文件：{path.relative_to(ROOT)}")
    print()
    print(f"{'坏法':>12} {'结果':>18} {'期望':>18}  判定")
    ok = True
    try:
        for name, body, want in CASES:
            if body is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(body, encoding="utf-8")
            got = T._fx_load_file()
            # 元组比较要用容差（浮点）
            if want is None:
                good = got is None
            elif got is None:
                good = False
            else:
                good = len(got) == 3 and all(abs(a - b) < 1e-9 for a, b in zip(got, want))
            ok &= good
            print(f"{name:>12} {str(got):>18} {str(want):>18}  {'PASS' if good else 'FAIL'}")
    finally:
        path.write_text(original, encoding="utf-8")
        print()
        print("（已还原 data/fx.json）")

    print()
    print("总体：", "PASS" if ok else "FAIL")
    print()
    print("另外还要确认一件事：文件是 0,0,0 时**画面一个字节都不变**——")
    print("  那是 `_dev/probe_diff_bytes.py` 与 `_dev/probe_scope_frames.py` 的活，不在这里重复。")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
