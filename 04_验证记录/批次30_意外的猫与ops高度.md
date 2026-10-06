# 批次 30 验证记录：删掉闯进画面的一只猫、ops 面板的高度跟着右边那张图走

用户两条：

> shot 31 还是 32 出现了一只意外的猫，请删除它
>
> ops panel 的高度不要只固定为 1 行，根据右侧 panel 图像的高度进行动态调整

出图与日志在 `04_验证记录/批次30_意外的猫与ops高度/`。

---

## 1 那只猫是从哪来的

猫学长在这套演出里本来有**两处**：

| 位置 | 是什么 | 落在哪句歌词 |
| --- | --- | --- |
| `school_fx.GLYPH_EVENTS` 的 `(66.30, 68.20)` | 把 `猫学长_字符画.txt` 印在**整帧中央**的叠加层（1.9 s） | shot 31 `shot_happy` 66.159–68.005 = 副歌 "If I can make you happy / Then I can make you satisfied" |
| `school_scenes.pane_landmark_cat`（80.93） | 猫学长自己的 pane，逐行点亮 | "If I'm a tabby cat" |

用户看到的是第一处：它跟猫没有关系，落在**讲"让你开心"的副歌**上，而且正好叠在右侧图案列的左边（改前出图
`t0067_50_删猫前_猫学长叠在合唱上.png`，猫的耳朵、脸和尾巴压在画面正中；改后 `t0067_50_删猫后_画面上没有猫.png`）。

用户说"shot 31 **还是** 32"，这个不确定可以解释：叠加层的窗口是 66.30–68.20，而 shot 31 的边界是 68.005
（实测 `t=67.90 → shot_happy`、`t=68.10 → shot_execution`），所以它把 shot 31 整段和 shot 32 的前 0.2 s
都盖住了——两个数都对。

修法不是把它的窗口挪开或缩短，而是把**"把字符画印满整帧"这条路整个删掉**——它只剩猫一个用户了（何尊早就改走
`plate`：用户给了矢量稿 `何尊.html`，不再用字符画）：

- `school_fx.py` 删 `GLYPH_EVENTS`、`draw_glyphs`、`glyphs`、`_art`、`FILES["cat"]`、`FILES["hexun_art"]`；
- `tui_live.py` 删掉整屏层里那次 `_FX.draw_glyphs(s, cols, rows, t)`；
- 删完 `import school_fx` 后 `hasattr` 这四个名字全为 False（探针式的确认：没有半条路留下来）。

`pane_landmark_cat` **没有受影响**：它自己读那个 `.txt`（不经过 `_art`），所以猫学长仍然只在自己的 pane 里出现一次，
仍在 80.93、"If I'm a tabby cat" 那句上——这也是 `05_歌词会话对照_v2.md` 第 29 行要求的落点。

原因与结论都写进了代码里（`school_fx.py` 末尾注释 + `pane_landmark_cat` 的 docstring），免得下一次又有人"顺手把字符画印上去"。

---

## 2 ops 面板的高度：先量，再改

### 2.1 先量：新探针 `_dev/ops_probe.py`，以及它第一版量错了

第一版是**从成品屏幕上读**：找带 " ops" 的标题行，再往下找 `└`。这个量法有两处错，而且两处都让它**低报**：

1. 它假设框的左边界在第 1 列——136.90 之后图案列换到左边，第 1 列是**另一个框**的左边框，数到那个框的底就停了；
2. FX 叠加层（低空掠过、闪光、照片）偶尔会盖掉一个角。

它因此报出"137 个采样里 132 个只有 2 行"。**尺子错了，数出来的病也是错的**：修好之后用同一把尺子对旧代码复测，
真相是 **142/143 个可读采样 = 3 行 = 1 行字**（`┌` + 一行 + `└`）——这才是用户说的"固定为 1 行"。

现在的探针读的是 `draw_body` 自己发布的算术（`tui_live.GEOM`：`avail / pane_h / tick_rows / ops_top / ops_bottom`），
不再猜像素。

### 2.2 病根

```python
tick_min = 6 if (校园变体 and t >= MACHINE_FROM) else 3    # 一个常数
pane_h = min(max(need, avail - tick_min), avail - tick_min) # 图案把其余全吃掉
height = bottom - ops_top + 1                              # = tick_min
```

`tick_min` 是不变的，所以框的高度也不变：校园变体 3 行（一行字），专业段 6 行。

### 2.3 改法：高度是"右边那张图"的函数

```python
TICK_FLOOR, TICK_CAP = 3, 8
def tick_share(pane_h): return max(TICK_FLOOR, min(TICK_CAP, round(pane_h * 0.25)))

share  = tick_share(avail - TICK_FLOOR)     # 图案只被拿走 3 行时，它会有多高 → 取四分之一
pane_h = min(max(need, avail - share), avail - share)
```

- **一次算完，不迭代**。写成 `t = round((avail - t) / 4)` 的不动点在 33 行上会在 6 和 7 之间来回跳，切分随"第几遍"
  变化比随图高变化更糟；现在的切分对图高单调。
- **不变量**：`pane_h + share == avail`，所以图案永远不会被画到列外（旧的 `tick_min` 起的就是这个作用，这一点不能丢）。
- **图案的最小可看行数优先**：`avail - share < least` 时图案整块让位（`pane_h = 0`），ops 回到"按内容要"
  （`len(tick)*2+1`，上限 8）——这与旧代码一致（120×34 下鲸鱼/KV 这类本来就放不下）。
- 专业段的 6 行下限保留（`if machine: n_tick = max(n_tick, 6)`：标题 + 寄存器 + 至少三条指令）。

### 2.4 量出来的结果

`python _dev/ops_probe.py`（全曲，1 秒一采样）：

| 窗口 | 图案高度 | ops 高度 | 改前 |
| --- | --- | --- | --- |
| 197×52 | 30 行 | **8 行**（213/213 采样） | 3 行（1 行字） |
| 120×34 | 16 行 | **4 行**（106/107） | 3 行 |
| 240×67 | 45 行 | 8 行（封顶） | 3 行 |

也就是说它**确实随"右边那张图"变**：197×52 给 8 行（6 行字，四五个词的列表整轮看得见），窗口小到 120×34 就是
4 行，再大也封在 8 行（影片自己的 ticker 是 32 行，因为影片右栏全是 ticker；这里上面还要留图案）。

探针自带失败判据：**图案 ≥ 8 行而 ops < 3 行即 exit 1**，现在是 PASS。`check.cmd` 也把它加进了快速集（八个探针）。

### 2.5 代价，说清楚

图案列少了 5 行（197×52：35 → 30）。大部分 pane 本来就没画满自己那块矩形（t=100 的"晶格重构"只用了上半部分，
下面的行本来就是空的），所以这 5 行原本是浪费的；真把自己撑满的 pane（鲸鱼、KV 缓存、采样、双管道）会按比例略小
——这是用户要的取舍：那一行字变成六行字。

---

## 3 机检

| 检查 | 结果 |
| --- | --- |
| `check.cmd --full` | **全部通过**（`check_full.txt`） |
| `ops_probe` 197×52 / 120×34 / 240×67 | PASS（0 个"高图配一行字"采样） |
| `frame_probe` 197×52 | 冷 35.8 ms（最差 125.1）；热均值 23.8、最差 33.3、峰值 40.7 ms |
| `frame_probe` 120×34 | 冷 22.6 ms；热均值 11.3、最差 15.2、峰值 16.1 ms |
| 预算 41.7 ms（24 fps） | **0 个尺寸超**（上一批热最差 31.8，这批发 33.3：ops 从 1 行字画到 6 行字，符合预期） |
| `ansi_probe` 全曲（24 fps 步长） | **5088 帧，0 处终端与缓冲区不一致**（`终端对照_全曲0.txt`） |
| `sweep_tui` 两种变体 | OK；校园 197×52 仍是 5086 帧、均值 14.06 ms |

---

## 4 改了哪些文件

| 文件 | 改动 |
| --- | --- |
| `player/_tools/school_fx.py` | 删掉整帧字符画那条路（`GLYPH_EVENTS`/`draw_glyphs`/`glyphs`/`_art`/两个 `FILES` 项），末尾注释写明原因 |
| `player/_tools/tui_live.py` | 新增 `TICK_FLOOR`/`TICK_CAP`/`tick_share`/`GEOM`；`draw_body` 的图案↔ops 切分改成随图高；删掉 `_FX.draw_glyphs` 调用 |
| `player/_tools/school_scenes.py` | `pane_landmark_cat` 的 docstring 改成"这是猫唯一一次演出" |
| `_dev/ops_probe.py` | 新增：量 ops 框高度（读 `GEOM`），自带失败判据 |
| `check.cmd` | 快速集加 `ops_probe`（七个探针 → 八个） |
| `README.md` | 状态表加一行 |

---

## 5 仍然如此 / 已知

- 校徽 4 次、铸剑雕塑的重复是**用户豁免**的（批次 28 的说明），本次没有动。
- 120×34 下 ops 是 4 行：窗口只有 20 行可切，四分之一就是 4 行；这不是"又固定回去了"，而是它本来就该跟着图高走。
- 专业段的 ops 是程序清单，下限 6 行（标题 + 寄存器 + 三条指令），这一条从批次 25 起就在。
- 那只猫的**本体**（`pane_landmark_cat`，80.93）没动；被删的是副歌上那次没有歌词依据的叠加。
