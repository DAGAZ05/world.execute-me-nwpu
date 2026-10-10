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

#: 底噪亮度那个键（批 94）。它与三层强度是**互相独立**的，所以要单独验：
#: (名字, 文件内容, 期望的三层结果, 期望的 gain)
GAIN_CASES = [
    ("缺这个键 -> 默认", '{"phosphor":0.2,"noise":0.1,"dissolve":0.05}', (0.2, 0.1, 0.05), None),
    ("正常 0.8", '{"phosphor":0.2,"noise":0.1,"dissolve":0.05,"noise_gain":0.8}',
     (0.2, 0.1, 0.05), 0.8),
    ("超范围 5 -> 夹到 2.0", '{"phosphor":0.2,"noise":0.1,"dissolve":0.05,"noise_gain":5}',
     (0.2, 0.1, 0.05), 2.0),
    ("负值 -1 -> 夹到 0.1", '{"phosphor":0.2,"noise":0.1,"dissolve":0.05,"noise_gain":-1}',
     (0.2, 0.1, 0.05), 0.1),
    ("非数字 -> 默认", '{"phosphor":0.2,"noise":0.1,"dissolve":0.05,"noise_gain":"dark"}',
     (0.2, 0.1, 0.05), None),
    # **这条是重点**：三层写坏了，gain 必须**仍然生效**——两个不相干的失败不该绑在一起
    ("三层写坏 + gain 正常", '{"phosphor":"x","noise":0.1,"dissolve":0.05,"noise_gain":0.5}',
     None, 0.5),
    ("gain 写坏 + 三层正常", '{"phosphor":0.6,"noise":0.4,"dissolve":1,"noise_gain":null}',
     (0.6, 0.4, 1.0), None),
]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import importlib
    import tui_live as T
    importlib.reload(T)          # 确保读到的是当前文件

    # **绝不写用户真正在用的那个文件**（批 94 的教训）。这个探针要验"文件写坏了会怎样"，
    # 所以它必须写点什么；而写 `player/data/fx.json` 出过两次真事：
    #   1. `finally` 在进程被 Terminate 时不执行（我自己的冒烟测试就 Kill 过播放器），
    #      于是测试用的取值被留在用户文件里；
    #   2. 那个文件没有备份，第一版直接把用户的 `_readme` 与取值覆盖成了测试内容。
    # 现在探针把 `FX_FILE` 指到 `_dev/out/` 下的临时文件，用户的文件完全不参与。
    tmp = ROOT / "_dev" / "out" / "fx_probe_tmp.json"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    real = T.FX_FILE[0]
    T.FX_FILE[0] = tmp
    print(f"测试用的文件：{tmp.relative_to(ROOT)}（用户文件 {real.relative_to(ROOT)} 不参与）")
    print()

    def read_triple():
        return T._fx_load_file()

    def read_gain():
        return T._fx_read_gain()

    ok = True
    try:
        print(f"{'坏法':>12} {'结果':>18} {'期望':>18}  判定")
        for name, body, want in CASES:
            if body is None:
                tmp.unlink(missing_ok=True)
            else:
                tmp.write_text(body, encoding="utf-8")
            got = read_triple()
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
        tmp.unlink(missing_ok=True)
        T.FX_FILE[0] = real

    print()
    print("=== 底噪亮度键 `noise_gain`（批 94）===")
    print()
    print(f"{'坏法':>22} {'三层':>18} {'gain':>8} {'期望 gain':>10}  判定")
    T.FX_FILE[0] = tmp
    try:
        for name, body, want3, wantg in GAIN_CASES:
            tmp.write_text(body, encoding="utf-8")
            g3 = read_triple()
            g = read_gain()
            ok3 = (g3 is None and want3 is None) or (
                g3 is not None and want3 is not None
                and len(g3) == 3 and all(abs(a - b) < 1e-9 for a, b in zip(g3, want3)))
            okg = (g is None and wantg is None) or (
                g is not None and wantg is not None and abs(g - wantg) < 1e-9)
            good = ok3 and okg
            ok &= good
            print(f"{name:>22} {str(g3):>18} {str(g):>8} {str(wantg):>10}  "
                  f"{'PASS' if good else 'FAIL'}")
    finally:
        tmp.unlink(missing_ok=True)
        T.FX_FILE[0] = real
        print()
        print(f"（已还原指向：{T.FX_FILE[0].relative_to(ROOT)}；临时文件已删除）")

    print()
    print("总体：", "PASS" if ok else "FAIL")
    print()
    print("另外还要确认一件事：文件是 0,0,0 时**画面一个字节都不变**——")
    print("  那是 `_dev/probe_diff_bytes.py` 与 `_dev/probe_scope_frames.py` 的活，不在这里重复。")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
