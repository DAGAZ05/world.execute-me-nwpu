# NOTICE · 第三方素材、许可，以及"哪些东西不在仓库里"

本仓库 = **上游影片包**（MisakaZentai 的开源重建，`player/`）+ **本次西工大改编**（根目录的文档、
`preview/`、`assets/`、`03_批次设计/`、`04_验证记录/`、`_dev/` 与 `player/_tools/school_*.py` 的画面）。
两部分的第三方归属下面分开说；**上游影片包内部的逐项署名链在 [`player/NOTICE.md`](player/NOTICE.md)**，
这里不复述，只给结论与入口。

## 许可总览

| 部分 | 许可 |
|---|---|
| 上游影片包的代码、dsh 前端、React | **MIT**（`player/LICENSE`、`player/LICENSES/React-MIT.txt`） |
| 上游影片包里的鲸鱼娘立绘及其衍生画面 | **CC BY-NC-SA 4.0**（署名单见 `player/NOTICE.md`，全文在 `player/LICENSES/CC-BY-NC-SA-4.0.txt`） |
| 字体（Space Mono Bold、Anton Regular） | **SIL OFL 1.1**（`player/film/ai_mascot_mv_world_execute_20260926/fonts/OFL_*.txt`） |
| 本次西工大改编的文档与图像（根目录各篇 `.md`、`preview/`、`03_批次设计/`、`04_验证记录/`、`assets/`、学院版代码绘制的画面） | **CC BY-NC-SA 4.0**（见根目录 `LICENSE`） |
| 歌曲与歌词 | **不在本仓库**，权利归 Mili；本仓库不授予其再许可 |

## 不在仓库里的东西（`.gitignore` 里都写明了）

| 东西 | 权利人 | 说明 |
|---|---|---|
| 歌曲 `world.execute(me);` | Mili | 自备音频放到 `player/input/song.mp3`；要什么格式、怎么对齐见 [`player/input/README.md`](player/input/README.md) 与 `player/data/song.json`（时间零点是它的第一个采样） |
| 歌词 `.lrc` | Mili | 上游包用 `player/tools/lyrics.py fetch` 从 [LRCLIB](https://lrclib.net)（条目 36914646）取到本机，或自备；仓库里只保留**不带文字**的逐词/逐句时间轴 `player/data/timing/*_notext.json` |
| 逐字歌词时间轴 `word_timeline.json`（带文本的那份） | Mili | 构建期产物，不进仓库 |
| 逐句歌词对照表 `01_歌词分析.md`、`05_歌词会话对照_v2.md`、`06_时序对照表.md/.tsv` | Mili | 三份文档逐句印着整首歌，只在本机生成（`_dev/chat_doc.py`、`_dev/timeline_doc.py`）；有 `lyrics.lrc` 就能重新生成 |
| 原片舞者画面 | 见 `player/NOTICE.md` | 基于第三方 MMD 模型与动作生成，许可范围未确认，上游用立绘生成替身帧 |
| 音乐相关的一切 | Mili | 按 [Mili 官方使用指引](https://projectmili.com/copyright-guidelines) 处理：个人非商业二创可用；含 AI 的同人内容须明确标注；商用另行确认 |

**仓库里对歌词的使用**：代码与文档里会**引用**零散的歌词行——作为镜头名（`shot_*` 的标签）、
`school_panels.py` 里每一行的标识，以及说明这段画面在讲什么。这是**引用**，不是分发整首歌：
整首歌的文本与音频都不在仓库里，`player/data/timing/*_notext.json` 只留时间。

## `assets/`：改编用的参考图与素材

这些图是学院版画面的输入（`player/_tools/school_fx.py` 会把它们像素化成字符画），因此必须随仓库分发。
按类型分两批，**来源与权利归属按各自原样保留**：

* **本次改编自绘/自制的素材**：`航小天.png`、`航小天篮球.json`、`校园标识物/` 里的何尊系列
  （`何尊.svg`、`何尊_线稿.png`、`何尊_字符画.html`、`何尊_字符画.txt`、`何尊.png`）、
  `NWPU_字符画.txt`、`猫学长_字符画.txt`、`校徽.webp`、`为国铸剑雕塑_俯瞰.png`、
  `对话_机器手与人的手.png`。这些按本仓库的 CC BY-NC-SA 4.0 分享。
* **参考照片与图标**（校园建筑、飞机、元器件、界面图标等）：`校园与成果/*.png`（ARJ21、图书馆、校门、
  歼-20、直-20、运-20、魔鬼鱼、鱼雷）、`校园标识物/图标_*.jpg`、`校园标识物/memory_*.jpg`、
  `嵌入式-超声波红外测距.jpg`。它们是**非商业同人创作里的参考与输入**，出处见文件名；
  如果你是其权利人并希望它们不在这里，提一个 issue 就会被移除。

校园徽记、校训、雕塑与"何尊"等属于西北工业大学的标识与文化元素，此处仅作非商业性的校园题材表达，
不含任何官方认可或授权之意。

## 声明

* 这是**非官方同人作品**，与 DeepSeek、Mili、西北工业大学及上面列出的各位作者没有从属或合作关系，
  也未经他们认可；界面是对 DeepSeek Harness（dsh）前端的致敬。
* 转载、二次创作请保留上述署名链，并且**不要商用**。
