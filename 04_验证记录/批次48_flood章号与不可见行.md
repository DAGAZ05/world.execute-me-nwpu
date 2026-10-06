# 批次 48 · `shot_flood` 上的「07」，以及一行排了却从没上屏的 pane

用户的提问是这一批的起点：

> 目前问题是 shot 64 附近屏幕中间有个 07 纹样，这是怎么回事？

查下去发现是**两个缺陷叠在同一段 3 秒上**：屏幕上那个数字**不是本变体的章号**，
而同一段里还有一行 pane **排了 3.02 s、一帧都没上过屏**。

---

## 1 shot 64 是什么，那个「07」是什么

```
shot 63   141.39 - 144.16  shot_hoard
shot 64   144.16 - 147.62  shot_flood      ← 整屏接管
shot 65   147.62 - 148.54  shot_exec_hit
```

`shot_flood` 是原片的"蓝色淹没机器"：`draw_flood` 在整屏铺一层噪声，
**在 `u > 0.6`（= 146.236 s）把一组方块字打在屏幕正中**。这是原片自己的装置
（`sec_chorus2.py:336-355`），而原片那一句是：

```python
# tui_live.py，改前
if u > 0.6:
    block_word(s, x0, y0 + max(0, (y1 - y0) // 2 - 4), "07", w, 9, mix(RED, 1.0))
```

`"07"` 是**写死的字面量**。它的含义是**即将到来的章号**——原片 146.24 打 `07`，
`07 / EXECUTION` 在 **147.40** 开始，正好是"下一章要来了"的预告。

问题在于两条时间轴的章号已经不一样了：

| | 章号 | 开始 |
|---|---|---|
| 原片 | `06 / REWARD_HACK` → **`07 / EXECUTION`** | 118.00 → **147.40** |
| 本变体 | `06 / 互换` → **`08 / 执行`** | 125.33 → **147.52** |

所以本变体的屏幕上印的是**原片的章号**，而它自己的顶部章节条写着 `07 / 非法参数`、
1.3 秒后变成 `08 / 执行`——**屏幕正中一个大 `07`，顶部条也是 `07`，下一章却是 `08`**。

### 1.1 修法：从当前生效的章节表里读"下一个章节"

`draw_flood` 拿不到 `Data`，而"哪张章节表生效"这件事在 `tui_live` 里本来就有答案
（`Data.chapter` 内联的那个三元式）。抽成一个模块级函数，两处共用：

```python
def panels():
    return SP if (SP is not None and VAR[0] == "school") else FP

def next_chapter_num(t: float) -> str:
    bar = panels().CHAPTERS
    after = [lab for s, lab in bar if s > t]
    lab = after[0] if after else (bar[-1][1] if bar else "")
    return lab.split("/")[0].strip()
```

`Data.chapter` 也改成走 `panels()`，于是"章节条"只有一个来源。
顺带处理了原代码里那句注释的过期说法（"the copy at line 144"——那份 `CHAPTERS = FP.CHAPTERS`
副本在模块加载时做、`--variant` 在之后才解析，所以它永远是影片的表）。

**两个变体各自正确**（实测）：

```
school    next chapter at 146.24s -> '08'   bar: [... '07 / 非法参数', '08 / 执行', '09 / 软工与爱']
original  next chapter at 146.24s -> '07'   bar: [... '07 / EXECUTION', '08 / EVAL: LOVE', ...]
```

渲染 t=146.50 的整帧，方块字的形状也跟着变（第二位数从闭合的 `8` 变回 `7`）。

---

## 2 顺着这 3 秒查出来的：`pane_motif_dijkstra` 一帧都没上过屏

批次 44 用户裁定"dijkstra 没被使用的话，需要在学院部分合适的地方加上"，落地方式是把
`pane_curriculum`（当时 136.90–147.52，全片最长的单个 pane）在 **144.50** 切开，
新行 `pane_motif_dijkstra` 拿 144.50–147.52。

而 144.50 **在 shot 64 里面**。`shot_flood` 走的是这条分支：

```python
elif ent is not None and ent["name"] == "shot_flood":
    draw_flood(s, 1, top, cols - 2, bottom, t, ent["u"])     # ← 没有 draw_body
```

**`draw_body` 根本不跑，右栏不画**，于是这一行在它整个生命里没有一帧落在一个会画 pane 的
镜头上。这不是推断而是分支结构本身：`shot_flood` 那 3.46 s 内 `draw_body` 的调用点只有 `else`
一个，而 `ent["name"] == "shot_flood"` 先命中了。改后渲染验证：142.40 / 143.20 / 144.00
三帧的右栏都能读到 `裂纹`，145.50（flood 中）读不到——判据就是"这一行的窗口里有没有一帧
落在会画 pane 的镜头上"。

### 2.1 为什么两个探针都看不见

- `row_probe` 量的是**行的跨度**与**压了几条歌词**：3.02 s，正常；
- `clock_probe` 量的是**画得动不动**：它直接调 `draw_scene_pane(name, s, ...)`，
  **自己造一个 Screen**，从不问这一行在真实帧里会不会被画。

同一个坑**批次 26 已经踩过一次**：`pane_ai_rl` 当时排在 175.31，落在 `shot_collapse`
（174.90–177.50）里，也是整屏接管。当时的修法只是**把行挪走**，没有留下判据——
于是批次 44 又照着同一个形状犯了一遍。**这才是本批真正要修的东西。**

### 2.2 修法一：切点改到歌词表自己的边界上

切点不需要发明，歌词表里本来就有这个位置：

```
131.90  [gap] 学院选择      ← 学院门在这里开
134.50  [gap] 进专业
138.00  [gap] 大一
142.00  [gap] 数据结构      ← 改成在这里切
147.52  Execution
```

`pane_curriculum` 136.90–**142.00**（5.10 s），`pane_motif_dijkstra` **142.00**–147.52。
可见生命 = 142.00–144.16 = **2.16 s**（144.16 起 flood 接管）。

三件事同时成立：

1. **可见**（2.16 s 都在 `shot_hoard` 里，`draw_body` 正常跑）；
2. **落在该落的词上**——最短路径正是「数据结构」图那一章的东西，而 `pane_exec_ds` 的 ops
   本来就写着「数据结构 · 树/图」，这个切点比 144.50（一次纯镜头切）更贴；
3. **代码表少一条具名例外**：`pane_curriculum` 5.10 s 掉到 `row_probe.LIMIT`（6.0 s）以下，
   `LONG_OK` 从三条减到两条。

行数仍是 81（只是改了 `at`/`end`），所以 `school_fx._cuts()` 的 `KINDS[i % len(KINDS)]`
**相位不变**——转场种类不会因为这次改排期而全部换一遍。`SHATTER_AT = (147.52,)` 也不受影响。

`pane_curriculum` 7.60 s → 5.10 s **不损失内容**：它的揭示是 `u = lt/dur` 的逐行打印，
**终态只取决于 `u = 1`**，所以两个时长下最后一帧的清单完全一样（大一 9/9、大二 10/13、
大三 9/10、大四 2/2，纵向空间才是上限），变化的只是打印速度（大二 13 门从每行 0.58 s 变成 0.39 s）。
实测：把同一行按两个跨度各画一次 `u = 1.0`，逐行比对**只差三行**——`▸` 巡读标记落在哪一列、
闪烁光标在哪一格（`█`），**24 行课程与两行页脚逐字相同**；墨量 291 vs 293。

### 2.3 修法二：把判据变成机检

`_dev/row_probe.py` 新增一项：**每一行有多少秒落在会画 pane 的镜头上**。

"不会画 pane"的窗口有两类，都写进常量：

```python
NO_PANE_SHOTS = {"shot_last_execution", "shot_black", "shot_flood", "shot_collapse"}
```

（本变体跳过了原片自己的 `shot_exec_hit`/`shot_count` 接管——`film_bleed` 为 False，
大肥鱼不会在倒数里回来——所以只剩这四个。）另一类是**学院门那 5 秒**：
`school_gate.overlay` 是整屏界面、在镜头分支**之前**`return`，它按**默认时间线**
（没人按键）计入，那正是无人值守播放时看到的样子。

窗口先合并再求差，`visible < 0.30 s` 即失败。修后 80 行全部有可见生命：

```
80 named rows; 0 over 6.0s and unargued (30.1s of the song in long rows)
0 row(s) with under 0.30s of visible life
```

最短的几条是六个数码管（0.39–0.44 s），与 `MIN_VISIBLE = 0.30` 之间留了余量。

### 2.4 修法三：`dijkstra` 的生长锚在自己的行上

`dijkstra_cracks` 的相位原来是 `t % 6.0`（**绝对歌曲时钟**）——这对每个母题都是对的，
因为它们的槽位有五到十秒，一个周期能整落地。但这一行的可见生命只有 2.16 s：

| 时刻 | `t % 6` | 相位 | 画出来 |
|---|---|---|---|
| 142.00 | 4.00 | 已经长满 | 满 |
| 144.00 | 0.00 | **跳回 25%** | 只剩四分之一 |

即"一上来就已经长满、在消失前 4 帧缩回去"。改成从**行起点**算相位：

```python
@lru_cache(maxsize=1)
def _dijkstra_anchor() -> float:
    import school_panels as _SP
    for r in _SP.shot_rows():
        if r.get("name") == "pane_motif_dijkstra":
            return float(r["at"])
    return 0.0

ph = (t - _dijkstra_anchor()) % 6.0
grown = max(2, int(len(path) * min(1.0, 0.20 + ph / 2.0)))
```

行起点**从日程读**而不是写在母题里，所以以后改排期，相位跟着走。
效果（同一行、四个时刻的墨量）：`226 → 245 → 284 → 303`，裂纹在 1.6 s 内从 20% 开到满，
**在被 flood 吞掉之前画完**；循环保留，所以将来槽位变长也不会退化成静帧
（`clock_probe` 仍要求它动）。

---

## 3 机检

| 项 | 结果 |
|---|---|
| `check.cmd --full` | 退出码 0（十一个探针 + 两个变体 × 8 尺寸全片扫描） |
| `row_probe` | 80 行，0 超长、**0 不可见**（新判据） |
| `clock_probe` | 80 行 0 still |
| `pane_probe` | 77 个 (pane,参数) × 6 尺寸，0 异常 0 越界 |
| `timeline_doc --check` | up to date（重生成，63 处变化） |
| `sweep` school/original | 8 尺寸 0 崩溃 |
| `frame_probe`（门禁内） | `197x52` 热帧最差 **41.1 ms**（预算 41.7，0 尺寸超）、`120x34` 18.4 ms |
| 两个变体的章号 | school `08` / original `07`（都在 146.24 s 实测） |

### 3.1 性能：那个已知的最差帧，以及为什么它的判定会在同一份代码上翻面

`frame_probe` 的最差帧仍然是 **t=193.69**（193.46 那行的转场中点，同帧叠着图书馆背景、
航小天全身像与校徽 pane）——**与本次改动无关的帧**（本批只碰 142.0–147.6 s 与一个数字）。
同一份代码在同一台机器上连测三次：

```
43.5 ms   OVER BUDGET
41.1 ms   0 size(s) over it
39.9 ms   0 size(s) over it
```

预算 41.7 ms **正落在这份噪声里**。为了确认不是回归，`stage_probe` 拆了那一帧：

| 段 | 本批 | 批次 45 |
|---|---|---|
| `Screen.render_diff` | 15.04 | 15.74 |
| `tui_live.draw_body` | 9.84 | 9.32 |
| `school_fx.transition` | 3.56 | 3.09 |
| `school_fx.draw` | 3.14 | 2.26 |
| `tui_live.fx_apply` | 1.96 | 1.93 |

逐段都在噪声内 → 是机器负载（浏览器 + 动态壁纸），不是代码变慢。
这段测量与"**pass / fail / pass，同一份代码**"已经写进 `frame_probe` 的 docstring，
免得下一次审计把它当成回归重报一遍。

---

## 4 这一批的教训

**一个"挪走就完事"的修法会再生产同一个 bug。** 批次 26 把 `pane_ai_rl` 从
`shot_collapse` 里挪出来时，问题被当成"这一行排错了"；真正的形状是
"**有一类窗口不画 pane，而没有任何检查知道这件事**"。批次 44 在同一个形状上又排了一行，
两个探针都报绿。现在 `row_probe` 直接量"这一行有几秒真的在屏幕上"，
这一类错误是**算出来的**，不是看出来的。

**另一件**：屏幕上出现一个说不出来源的字符时，先问它属于哪条时间轴。
`07` 既不是排版错误也不是噪声，它是**原片的时间戳**留在了本变体的画面上——
和批次 47 处理的 `FILES` 兜底、`_cuts()` 的索引空间是同一类东西：
**两套词汇共存的接缝**。
