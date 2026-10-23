"""开工前自检：这个内置环境是不是完整的、能不能跑这部片子。

为什么需要它：内置环境是 1100 个文件、78 MB 的二进制目录，**拷贝/解压时漏掉几个 `.pyd`
是很容易发生的**——而漏掉之后的表现往往不是"起不来"，而是某个功能悄悄降级
（比如 `_webp.pyd` 没了，Pillow 只是报 `WEBP support not installed`，鲸鱼那个 pane 被跳过，
片子继续跑）。那种失败最费时间。

这个脚本把"能不能跑"压缩成一次明确的 PASS/FAIL，并指出**缺了哪个文件**。

    player\\python\\python.exe player\\python\\check_env.py

`run.cmd` 会在启动前调它一次；也可以单独跑。
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAYER = HERE.parent

#: 少了任何一个，画面或功能会悄悄降级，所以逐个点名。
REQUIRED = [
    "python312.dll",
    "python312.zip",
    "python312._pth",
    "vcruntime140.dll",
    "Lib/site-packages/PIL/Image.py",
    "Lib/site-packages/PIL/_imaging.cp312-win_amd64.pyd",
    # ↑ Pillow 的核心；没有它 Pillow 根本 import 不了
    "Lib/site-packages/PIL/_imagingft.cp312-win_amd64.pyd",
    # ↑ 少了它：字体渲染（全片每一格文字）会失败
    "Lib/site-packages/numpy/__init__.py",
]
#: **`_webp.pyd` 不在这里**：仓库里的图已经全部转成 png（校徽、鲸鱼精灵都是），
#: png 的支持编译在 Pillow 核心里，不需要任何额外扩展模块。所以 `webp` 能力只作为
#: "信息"报出来，缺了不影响运行——这正是这一轮为兼容性做的事。


def main() -> int:
    bad: list[str] = []
    print("内置环境自检: %s" % HERE)

    # 1. 关键文件在不在
    for rel in REQUIRED:
        p = HERE / rel.replace("/", "\\")
        if not p.is_file():
            bad.append("缺少文件: %s" % rel)
    print("  文件检查: %s" % ("全部存在" if not bad else "%d 个有问题" % len(bad)))

    # 2. 能不能 import
    for mod in ("numpy", "PIL", "PIL.Image", "PIL.ImageFont"):
        try:
            __import__(mod)
            print("  import %-14s OK" % mod)
        except Exception as exc:                      # noqa: BLE001
            bad.append("import %s 失败: %s" % (mod, exc))
            print("  import %-14s **失败**  %s" % (mod, exc))

    # 3. Pillow 的可选能力（缺了只降级，不致命，但要看得见）
    try:
        from PIL import features
        for f in ("webp", "jpg", "zlib", "freetype2"):
            try:
                ok = features.check(f)
            except Exception:                          # noqa: BLE001
                ok = False
            print("  pillow 能力 %-10s %s%s"
                  % (f, "OK" if ok else "缺失",
                     "" if ok else "   （缺 webp 时鲸鱼那组精灵读不出来，该 pane 会被跳过）"
                     if f == "webp" else ""))
            if not ok and f in ("jpg", "freetype2"):
                bad.append("Pillow 缺少 %s 支持" % f)
    except Exception as exc:                          # noqa: BLE001
        bad.append("Pillow 的 features 模块不可用: %s" % exc)

    # 4. 片子本体
    for rel in ("_tools/tui_live.py", "film", "data"):
        if not (PLAYER / rel.replace("/", "\\")).exists():
            bad.append("缺少 %s" % rel)

    print()
    if bad:
        print("不完整 —— %d 个问题:" % len(bad))
        for b in bad:
            print("   * %s" % b)
        print("\n修法：这个目录应当有 %d 个文件、约 78 MB。最省事的是**重新拷一遍**"
              % 1100)
        print("（在源仓库里 `python _dev/build_portable_env.py --apply` 可以整个重建）。")
        print("**注意**：用资源管理器拷贝时如果中途取消/跳过，漏掉的往往是 `.pyd`。")
        return 1
    print("完整 —— 可以运行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
