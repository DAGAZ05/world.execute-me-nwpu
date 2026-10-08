# world.execute(me); · 西工大改编版 · 终端实时 MV

一支**在真终端里逐帧跑出来**的 MV：画面里的每一格都是真的字符 + 真彩色，播放器每帧只重画变了的格子，
所以我们能在一个 197×52 的字符窗口里跑到 40 fps 上下。左边是 dsh（DeepSeek Harness）的对话窗口，
右边是"运行着她的那个世界"的可视化，歌词跟着歌走，底下是中文对照。

这是 **Mili《world.execute(me);》** 的非官方同人作品，基于 [MisakaZentai 的开源重建](https://github.com/MisakaZentai/world-execute-me-dsh-pv)（MIT）
做**西工大（NWPU）改编版**：把"她"换成了学院里的航小天，把模型的可视化换成了学校的专业与成果。
**仅供个人非商业分享：请勿商用。**

## 相关视频与仓库

| | |
|---|---|
| 上游原版 PV 与数据仓库 | <https://github.com/MisakaZentai/world-execute-me-dsh-pv>（MIT） |
| 视频（B 站） | `BV1oxam6kEVh`、`BV1xCai6aE9g`、`BV1SgaY64EG5` |

## 预览

都是本仓库的播放器真实渲染的一帧（197×52；渲染脚本在 `develop` 的 `_dev/live_replay.py`）。
前两张是**学校部分**，后两张是**学院部分**：

| 开场（学校部分） | 运-20 掠空（学校部分） |
|---|---|
| ![开场：校徽与第一句](preview/01-school-opening.png) | ![运-20 掠过何尊](preview/02-school-y20.png) |

| 航小天全身跃动（学院部分） | 软件项目管理 · 尾声（学院部分） |
|---|---|
| ![航小天在节拍上跃起](preview/03-college-mascot-hop.png) | ![软件项目管理与校徽](preview/04-college-project.png) |

两张学院部分的图都是**节拍上的那一帧**：后面三分之一里航小天全身图会随音乐上下跃动（`hop` 最高 5 格），
第三张取的正是一个正拍（`FP.pulse` 的峰值）。

## 跑起来

**1. 依赖**：Windows + Python 3.12 以上，`pillow>=10`、`numpy>=1.26`（见 `player/requirements.txt`）。

```
python -m pip install pillow numpy
```

**2. 自备歌曲与歌词（版权，仓库里没有）**：把 Mili 的 `world.execute(me);` 音频放到
`player/input/song.mp3`，歌词（可选）放到 `player/input/lyrics.lrc`。
`player/input/README.md` 写清了要什么（含音频的 sha256 与时长）——交换机的时钟就是对它解码出来的
第一个采样，所以文件不一样时起唱点可能整体偏移。

**3. 启动**：推荐用 GPU 终端，重画吞吐是这套东西的另一半预算（见下文）：

```bat
run_gpu.cmd              :: Windows Terminal / WezTerm / Alacritty，自动挑一个
run_gpu.cmd --dry-run    :: 只打印它准备执行的启动命令
run.cmd                  :: 在当前控制台里直接跑
run.cmd --start 147      :: 从 02:27 开始；任何播放器参数都能透传
```

两个启动器就在**仓库根目录**（执行接口），它们自己会 `cd` 到 `player\`。
`player\` 里那个中文名的启动器是给"自带 Python 的完整压缩包"用的（`player\python\python.exe`）。

**4. 按键**（播放时页脚一直写着）：`h` 换人物渲染 · `c` 切左右栏 · `x` 开关特效 · `空格` 暂停/继续 ·
`q` 退出；`python player\_tools\tui_live.py --help` 有全部参数（`--variant`、`--start`、`--no-audio`、
`--fps-cap` …）。

**5. 两个分支**（`main` 是可发布的部分，`develop` 是加上全部过程材料的版本）：

| 分支 | 内容 |
|---|---|
| **`main`** | 播放器、素材、预览、这份 README、`NOTICE.md`/`LICENSE`、两个启动器 |
| **`develop`** | 上面这些，加上过程材料：`03_批次设计/`、`04_验证记录/`、`01`–`06` 各篇文档、`CHANGELOG.md`、`参考-原始想法.md`、`check.cmd`，以及 `_dev/` 里的探针与生成器 |

`check.cmd` 在 `develop` 上：一次跑完十五个探针（约一分钟），`check.cmd --full` 再加两遍全曲扫描。
探针和它们的用途在 `04_验证记录/` 里有，`_dev/` 里是探针本身。

> 画面流畅度有两个预算，播放器两边都在意：Python 每帧约 22–24 ms，终端每帧要重画 30–170 KB 的转义流。
> 想更顺就用 GPU 终端（`run_gpu.cmd`）、关掉窗口的透明/亚克力、别再套一层管道；
> 想知道你机器上的真实帧率，看页脚那个 fps。

## 目录结构

```
├─ README.md              你正在读的这份
├─ NOTICE.md              第三方素材、许可与"哪些东西不在仓库里"
├─ LICENSE                本仓库的许可（改编部分的文字与图像：CC BY-NC-SA 4.0）
├─ run.cmd / run_gpu.cmd  执行接口：控制台 / GPU 终端（自足压缩包的启动器在 player\）
├─ preview/               README 里那几张帧（播放器真实渲染）
│
├─ player/                播放器本体
│   ├─ _tools/            播放循环与画面：tui_live.py + school_*.py（学院版）
│   ├─ film/              上游影片包（画面数据、角色帧、dsh 前端），见 NOTICE.md
│   ├─ data/              歌曲元数据与**不带文本**的歌词时间轴
│   ├─ docs/              上游包的说明（怎么工作、素材来源、字体）
│   ├─ input/             歌曲与歌词放这里（不进仓库，见其 README）
│   └─ LICENSES/          上游第三方许可全文
│
├─ assets/                改编用的参考图与素材（见其 README）
└─ （以下只在 develop 分支）
    ├─ CHANGELOG.md            开发记录：一批一批改了什么、为什么
    ├─ 参考-原始想法.md         最初的需求与想法
    ├─ 02_叙事设计.md           这部片子讲什么、怎么排
    ├─ 02b_图像对位与可视化表达.md  每张图对应哪句词、画的是什么
    ├─ 03_批次设计/             每一批改动的设计稿
    ├─ 04_验证记录/             每一批的验证记录与帧
    ├─ check.cmd               一键机检（十五个探针；--full 加两遍全曲扫描）
    └─ _dev/                   探针与生成器（机检用的那一套）
```

**不在任何分支里的三份文档**：`01_歌词分析.md`、`05_歌词会话对照_v2.md`、`06_时序对照表.md/.tsv`——
它们逐句印着整首歌的歌词，只在本地用 `_dev/chat_doc.py`、`_dev/timeline_doc.py` 生成（有 `lyrics.lrc`
就能生成，`check.cmd` 在没有歌词时会跳过这两项检查）。

## 这一版做了什么（和上游原版的不同）

* **人物**：dsh 的鲸鱼娘 → 学院里的航小天（窗口里的形象、表情与动作都是本仓库画的像素/字符画）；
* **右栏**：模型可视化 → 学校的专业与成果：运-20 / 直-20 / 歼-20 / ARJ21 / 魔鬼鱼 / 鱼雷、何尊、
  为国铸剑雕塑、校门、图书馆、校徽与校训，以及四年课表、软件工程与 AI 的课程图；
* **对话**：左边那段 dsh 对话整段重写成了校园线（报道、选课、社团、期末、毕设），
  与歌词逐句对照（对照表在本地生成，见上）；
* **数学与专业概念**：每条歌词配一张会动的图（点集与维度、互信息、双星并合、像素排序、超椭圆、
  布拉德盘、5³ 量化、克拉尼图形、卷积/注意力/强化学习/扩散模型…），每张都带一行"图在讲什么"的说明；
* **性能**：播放器按 `--fps-cap`（默认 60）重画，逐帧只写变化的格子；渲染器、精灵粘贴、
  图版绘制都按实测热点改过，记录在 `CHANGELOG.md`。

## 学院部分只做了一个学院：欢迎 PR 你的学院

后面约三分之一的**学院部分**，是按"学院四年课表"把专业内容画成会动的图（十六门课 + 六个倒计时仪表 +
收尾的毕业设计）。**目前只做了作者所在的软件学院**——民航、航空、航天、航海、材料、机电、力学、
电子信息、自动化、计算机、数学、物理……都还空着。

欢迎其他学院的同学 PR 自己学院的那一份。要动的地方不多：

| 你想做的 | 改哪里 |
|---|---|
| 换成本学院的课表与课程图 | `player/_tools/school_panels.py` 里 `_exec_rows` 那张表（行时间、课名、图案名、一句话说明）+ `EXEC_SUB`/`GAUGE_SUB` |
| 画一张新图（一门课的图案） | `player/_tools/school_scenes.py`（一个 pane 一个函数，pane 自己的时钟与 ops 都在里面） |
| 学院的选课线、对话线 | `player/_tools/school_gate.py`、`player/_tools/school_chat.py` |
| 校史/成果素材 | `assets/`（见 `assets/README.md`），像素化与出场由 `player/_tools/school_fx.py` 负责 |

机检会替你兜住底线：`check.cmd`（在 `develop` 分支）会检查图案是否越界、是否还会动、抬头有没有说明、
每帧是否还在 24 fps 预算内。加一门课要动哪些地方，`CHANGELOG.md` 最近几批里有完整例子。

## 版权与许可

* **歌曲与歌词不在本仓库里**，它们是 Mili 的作品；仓库里只有**逐帧对齐用的时间轴**（`player/data/timing/*_notext.json`，
  同样的时间、没有文本）。要看/要构建，自己放 `player/input/`。
* 代码与文档里会**引用**零散的歌词行（作为镜头名、行的标识与说明文字），这是引用，不是分发整首歌。
* **上游影片包**（`player/film/`，MisakaZentai 的开源重建）按 **MIT** 分发，许可全文在 `player/LICENSE`；
  其中鲸鱼娘立绘及其衍生画面是 **CC BY-NC-SA 4.0**，字体是 SIL OFL，dsh 前端是 MIT——
  完整的署名链与逐项许可见 `NOTICE.md` 与 `player/LICENSES/`。
* **本次西工大改编的文档与图像**（`preview/`、`assets/`、`03_批次设计/`、`04_验证记录/`、各篇 `.md`、
  学院版的 `school_*.py` 绘制的画面）按 **CC BY-NC-SA 4.0** 分发：署名、非商用、同样方式共享。
* `assets/` 里是改编用的参考图与素材，来源说明见 `assets/README.md`。

## 致谢

* **Mili** —— 《world.execute(me);》，这支片子的全部理由；
* **MisakaZentai** —— [上游原版](https://github.com/MisakaZentai/world-execute-me-dsh-pv)：影片结构、角色帧与 dsh 前端；
* **上善无形（溟月）、ZipZipPipe、Small-tailqwq / dsh-deep-whale、dsh-whale-galgame** —— 鲸鱼娘立绘与表情（CC BY-NC-SA 4.0）；
* **西北工业大学** —— 被改编的对象：校徽、校训、何尊、为国铸剑雕塑与那些校史里的第一。
