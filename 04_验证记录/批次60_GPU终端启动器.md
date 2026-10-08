# 批次 60 · `run_gpu.cmd`：把播放器交给 GPU 终端（不动一行业务代码）

> 用 GPU 终端写一版，基本不动当前代码（给我一个新的 run_gpu.cmd）

`player/run_gpu.cmd`（放在 `run.cmd` 旁边）。它只决定**在哪跑**，播放器一行没改：终端是流畅度的另一半
预算（`_dev/paint_probe.py` 量的就是它），而这一半完全不需要播放器知道。

## 1 它做什么

| 选择 | 命令行 |
|---|---|
| Windows Terminal（本机有） | `wt.exe -w -1 --size 197,52 new-tab -d "<player>" -- cmd /c <player>` |
| WezTerm（若有） | `wezterm.exe start --cwd "<player>" --config initial_cols=… --config initial_rows=… -- cmd /c <player>` |
| Alacritty（若有） | `alacritty.exe --working-directory "<player>" -o window.dimensions.columns=… -o window.dimensions.lines=… -e cmd /c <player>` |
| 都没有 | 在当前控制台跑，并打印 `winget install --id Microsoft.WindowsTerminal` |

播放器那一段与 `run.cmd` 完全一致（`python _tools\tui_live.py --variant school`），`run_gpu.cmd` 的**所有
参数原样转给播放器**（`--start 147`、`--fps-cap 30`、`--major s`…），`--dry-run` 只打印不启动，
`WEM_SIZE`（缺省 `197,52`）是初始窗口格数——影片就是为这个尺寸画的。

## 2 三条踩出来的坑（都写进文件头了）

| 现象 | 根因 |
|---|---|
| `'M' is not recognized` 之类一串报错 | **文件自己违反了 ASCII 规则**：注释里写了"运-20"，cmd 按 GBK 读 .cmd，UTF-8 字节成了乱码并按字节偏移续读，于是把注释的碎片当命令执行。改成 `the low-pass crossing` |
| `RUN` 只剩 `set PV_VARIANT=school`，播放器从**错误目录**启动 | `set "RUN=a&&b"` **不保留 `&&`**：cmd 在解析这一行时就把 `&&` 当命令分隔符，后半句被当场执行。改法不是转义，而是**不再串联**——`PV_VARIANT`/`PYTHONUTF8` 由 `run_gpu.cmd` 设好、子进程直接继承，内层命令只剩"一个程序 + 参数" |
| 窗口开了，但命令没跑 | Windows Terminal 的**顶层选项必须在子命令之前**：`wt --size 197,52 new-tab -d DIR -- cmd /c …` 有效，而 `wt new-tab -d DIR --size 197,52 …` 会开一个标签页并**静默丢掉**命令行 |

## 3 怎么确认它真的能用（不是"看起来对"）

1. `run_gpu.cmd --dry-run` 打印出完整的一行：
   `wt.exe -w -1 --size 197,52 new-tab -d "…\player" -- cmd /c python _tools\tui_live.py --variant school "--start" "147"`
2. **让标签页自己写证据**：用一个测试 .cmd 把 `cd`、`python --version` 写进 `%TEMP%`，再用两种 WT 写法各
   启动一次（参数不同以便区分）——只有"顶层选项在前"那一种写下了正确的工作目录，就是它把第三种坑抓出来的。
3. 再用**播放器本身**跑一遍同一个启动行：`python _tools\tui_live.py --variant school --once 12.0 --no-audio`
   → 标签页日志里有那一帧的转义流、`exit=0`、工作目录正确 ✓（重定向到文件时中文显示为乱码，那是控制台代码页
   的问题，不是启动器的问题）。

## 4 命令行设不了、但最影响帧率的四条（写在文件头）

* Windows Terminal 配置：`"useAcrylic": false` + 外观里关"透明度"——半透明窗口会让**每个重绘的格子**多走
  一次合成；
* 光标 `"blinking": "solid"`——闪烁光标每次闪都在重画自己那一行；
* atlas 引擎（GPU 渲染器）在 WT 1.18+ 是默认；更老的版本要 `"useAtlasEngine": true`；
* 窗口保持在 197×52 附近（拉满到 300×90 就是 2.4 倍格子），并且**别给播放器套管道**（`tee`、录制、
  捕获会话）——5 MB/s 穿管道就是几十 fps 与个位数的差别。

## 5 机检

| 项 | 结果 |
|---|---|
| `run_gpu.cmd --dry-run` | 打印的启动行正确（终端、工作目录、尺寸、参数转发） |
| WT 链路实测 | 标签页工作目录正确、`python 3.13.5`、播放器 `--once` 帧输出、`exit=0` |
| ASCII | `run_gpu.cmd` **0 个非 ASCII 字节**（这条规则就是它自己踩过的） |
| 业务代码 | 未改动播放器（本批只新增一个 .cmd） |
