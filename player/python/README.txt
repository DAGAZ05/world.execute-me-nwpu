这个目录是一个**可移植的 Python 3.12 环境**，随仓库分发，让换一台 Windows 机器
clone 下来就能直接跑，不必先装 Python、也不必联网。

    python.exe            3.12.10 的嵌入式发行版（python-3.12.10-embed-amd64）
    python312._pth        已打开 Lib\site-packages 与 import site（嵌入式包默认是关的）
    Lib\site-packages\    pillow 13.0.0 / numpy 2.5.4（cp312-win_amd64 的 wheel 直接解开）

为什么是 3.12 而不是更高：`audioop` 在 3.13 被移除，播放器的音频路径要用它，
3.12 还带着，省掉一层 shim。

用法：仓库根目录的 `run.cmd` 会优先使用这里的 `python.exe`（其次才退回 PATH 上的
`python`），所以什么都不用配：

    run.cmd                    双击，或
    run.cmd --start 147        从 147 秒开始

`run.cmd` 在启动片子之前会先跑一次 `check_env.py`。**残缺的环境不会"起不来"，而是会
悄悄降级** —— 比如少了 `_webp.cp312-win_amd64.pyd`，Pillow 只报一句
`WEBP support not installed`、鲸鱼那组精灵所在的 pane 被跳过，片子照跑。那种失败最费时间，
所以自检会在开工前逐项点名：

    player\python\python.exe player\python\check_env.py

    文件检查: 全部存在 / 不完整 —— N 个问题
    import numpy / PIL / PIL.Image / PIL.ImageFont      OK
    pillow 能力 webp / jpg / zlib / freetype2           OK 或 缺失

**拷贝这个目录时最要紧的一件事**：本目录应有 **约 1100 个文件、78 MB**。用资源管理器拖拽
中途取消、或用了带过滤的同步工具，漏掉的往往是 `.pyd`（Windows 的扩展模块），而漏了它们
不会有明显报错。拷完跑一次 `check_env.py` 就知道全不全。

依赖只有 pillow 与 numpy 两个第三方包，其余全是标准库；`torch` 只在
`player/film/pv_dsh_frontend_20260927/`（另一部片子的 GPU 渲染路径）里用到，本片不需要。

---

**重建这个目录**（例如升级依赖）用仓库里的脚本，它会重新下载并解压：

    python _dev/build_portable_env.py --apply

`_dev/` 只在 `enhance` 分支上；`display` / `main` 分支上不带脚本，这个已装好的目录就是成品。

注意 `.gitignore` 里有一条 `!player/python/**` 的放行规则：通用的 `*.py[cod]` 会把 Windows
扩展模块 `.pyd` 一起忽略掉（`[cod]` 里的 c/o/d 正好涵盖 pyd），少了它们环境就是残的。
