# 组 B 审计 · 场景／地标面板（`project/player/_tools/school_scenes.py`）

范围：`school_scenes.py` 里除 `pane_everything_point`（属另一审计员）以外的全部 `def pane_*`，
以及它们各自挂靠的行（`school_panels.py` 的 `SHOT_ROWS` / `LANDMARK_ROWS` / `_exec_rows`）。

## 0. 审计基准与方法

**审计对象（sha256 前 16 位，写入本文时最后一次全量复核）：**

| 文件 | sha256(16) |
|---|---|
| `player/_tools/school_scenes.py` | `3d1b7d79b27130a9` |
| `player/_tools/school_panels.py` | `03d3d1a102956db8` |
| `player/_tools/school_courses.py` | `b618c7a09e2eba12` |
| `player/_tools/school_motifs.py` | `15b62800652ceddd` |
| `player/_tools/school_sculpture.py` | `27daae5790558c2c` |

> **注意：审计期间目标文件被并发修改。** 我第一次读 `school_panels.py` 时 17.00/21.00 两行校徽的 ops 是
> `"\u6821\u5fbe"`（校**徾**）与 `"\u516c\u8bda\u52c7\u6bc1"`（公诚勇**毁**），何尊行的 ops 是 `1980`，
> `school_scenes.py` 何尊注释是 `// 何尊铭文，公元前 1038`；最后一次复核（mtime `2026-10-06 11:07:36`，
> 距我复核仅 8 秒）时它们已变成 `校徽` / `公诚勇毅` / `1982` 与 `// 何尊铭文，约公元前 11 世纪（周成王五年）`。
> **本文所有结论都只对上面这组哈希负责**；文末「发现」里凡涉及这两个字符串的条目已按新内容重核（不再列为缺陷）。

**方法（不跑播放器：无音频、无 TTY）：**

1. **渲染取证**：`PV_VARIANT=school`，用桩 `Screen`（复刻 `tui_live.Screen.put` 的宽字符语义：字符写一格、宽字符再占一格）
   把面板画进 `197×52` 的**真实版面矩形**：`pane rect = x 99–195, y 10–39`（`draw_body`: `lx=98`，
   `pane_x0=99, pane_x1=195`；`sp_bottom=9`，`ops_top=10`，`pane_h=30`），并**经 `school_scenes.draw_pane`**
   调用——即带上 motif 分带（`MOTIF_IN`/`MOTIF_ALSO`），所以单带面板实际只拿到 `host_y1 = 10 + max(6, int(30*share)) - 1`
   （一带 `share=0.55` → 行 10–25；两带 `0.40` → 行 10–21）。
2. **越界扫描**：`cols ∈ {197,175,140,120,100,80} × rows ∈ {22..60 步长 2} × {未换边, 已换边} × u ∈ {0,0.1,0.5,0.9,1.0}`，
   逐格检查是否有写入落在 rect 之外（换边后 rect 为 `x 1–97`）。
3. **时钟探针**（复刻 `_dev/clock_probe.py` 的判据：**u 钉在 1.0**，取槽内 0.05/0.25/0.45/0.65/0.85/0.99 六帧比较字形＋颜色）。
4. **项目自带探针**：`_dev/pane_probe.py`、`_dev/clock_probe.py`、`_dev/repeat_probe.py`（headless，均不启动播放器）。

**项目自带探针的结论（用于对照）：**

```
python _dev/pane_probe.py    -> 0 problem(s) across 74 panes x 6 sizes
python _dev/clock_probe.py   -> 77 rows at 113x33: 0 still with no reason recorded
python _dev/repeat_probe.py  -> 77 row(s), 74 distinct drawing(s) - 0 repeat(s) to replace
```

三个探针都报「无问题」，而下面「发现」里的 S1/S2/S3/S4/S5 都是真的——原因是可指出的（见 F9）。

---

## 1. 面板清单

| 面板 | 出现的歌词行／时间 | 画的是什么（一句话） | 屏上文字（标题／caption／说明／单位，逐字抄下） | 结论 |
|---|---|---|---|---|
| `pane_landmark_crest` | 0.03 `Switch on the power line`；17.00 `[gap]`；21.00 `[gap]`；193.46 `[gap] 尾声`（4 行，用户豁免重复） | 校徽 halfblock 字符化：一个实心椭圆（约占 23×11 格），下方接 `powerdown` 带 | 标题 `西北工业大学`；仅闭幕行有 caption `公诚勇毅 · 三实一新`；下带 `── 关机 · N → 1 ──`…`1 —— 只剩一件事没说`；ops：`NWPU 1938 1957`／`校徽 1938`／`校徽 1938 公诚勇毅`／`NWPU 公诚勇毅` | 图与题一致（确是校徽的半块字符化），但**只有轮廓、读不出徽记内部**；0.03／17.00／21.00 三次图形**逐格完全相同**（见 S8）；未按 `05` §P0 第 1 行画校门（校门是 `school_fx` 的全屏 flash，0.60–3.30） |
| `pane_power_on` | 1.33 `Remember to put on protection` | PCB 走线总线逐条点亮，一条亮格沿线走；最后一根常闪红；下方 `he_init` 带 | `VCC 5V` / `GND` / `UNO R3`；下带 `── He 初始化 N(0, 2/n) ──`、`±√(2/n) = 0.47   n = 9` | **主题与歌词错位一行**：它自己的 docstring 写的是 `Switch on the power line`(0.03) 的图（:89），却挂在「戴上防护」上；而 05 §P0 第 2 行要的是校训牌 `公诚勇毅`＋`三实一新` |
| `pane_protection` | 3.58 `Lay down your pieces` | 防静电手环（两排框线）＋两侧端点，压在暗色走线上；另有保险丝一行 | `⚠ ESD` / `fuse 0.5A`；下带 `── 向日葵叶序 θ = n · 137.508° ──`（含 `137.508° = 360° × (1 − 1/φ)`、`黄金角：最难近似的无理数`）、`── 双星旋近 a ∝ (t_c−t)^¼ ──` | **主题与歌词错位**：ESD／保险丝是「protection」的内容（docstring :139 也这么写），却挂在「放下你的零件」上；「pieces」这一行没有任何元件 |
| `pane_pieces` | **未排期，没有任何行** | 物料清单 7 行，逐件落位并打勾 | `UNO R3` `LCD1602` `HC-SR04` `IR` `breadboard` `9V` `jumpers` / `7/7` | **死代码**：全片唯一正对 `Lay down your pieces` 的图没有行（docstring :172 自认未排期）；`PANE_MIN` 里却留着 `(10,4)` |
| `pane_class` | 5.16 `And let's begin object creation` | 7 行类定义逐行打出，首行高亮 | `class World(UNO):` / `    name     = "NWPU"` / `    campus   = "CHANG'AN"` / `    sensors  = []` / `    display  = None` / `    def __init__(self):` / `        self.begin()` | 与「object creation」相符，但**只有类定义、没有实例化**；`class World(UNO):` 把开发板当基类；`CHANG'AN` 与参数表的 `长安校区` 用两套写法 |
| `pane_parameters` | 7.19 `Fill in my data parameters` | 7 行参数表，左键／中值／右来源；右下角**本应**叠一枚何尊 | `name "西北工业大学" 校史` / `campus "长安校区 东祥路1号" 官网` / `founded 1938 校史` / `renamed 1957 校史` / `colleges 24 官网` / `majors 72 官网` / `students 40000 官网` | 七个数值与 `02_叙事设计.md` §9 全部对得上；**何尊画不出来**：真实版面下给的框是 18×8，`glyph_cells` 在该尺寸非空墨点为 **0/144**（见 S7），docstring 的「旁边浮着何尊」实际不显示 |
| `pane_polyhedra` | 33.01 `If I'm a circle`（覆盖 33.01–36.77，含 34.54 `Then I will give you my circumference`） | **五列完全相同的菱形线框**，只有名字与 V−E+F 不同；下半还有 He 初始化的柱状图 | `Tetra` `Cube` `Octa` `Dodeca` `Icosa` / `4-6+4` `8-12+6` `6-12+8` `20-30+12` `12-30+20` / `N(0, 2/n)   n=1000` / `V-E+F = 2` | **双重问题**：(a) 主题错位——站在「我若是圆」（同帧台词在说启翔湖与周长）上画正多面体＋He 初始化，而它自己的 docstring 写的是 `Initialization`(9.75)，ops 却写 `abs(x)^n / n=2 / CIRCLE`；(b) 五个「多面体」几何逐格相同，与「按图论画顶点与边」的声明不符（见 S6） |
| `pane_three_arms` | 10.90 `Set up our new world` | 三条对数螺线旋臂，臂端挂标签 | `航空`+`ARJ21` / `航天`+`北斗` / `航海`+`蛟龙`；下带 `── 莫尔条纹 · 两层光栅 ──`、`── 三旋臂 · 航空 / 航天 / 航海 ──` | 三航＝三臂，点数对（不是两臂）；但臂端专名 `北斗`／`蛟龙` 不在 §9 的事实表里（该表给的是「第一型 50 kg 级水下无人智能航行器」），属未核实的专名 |
| `pane_countdown` | 12.47 `And let's begin the simulation` | 大块字符数字倒数，然后 `simulation: running`＋一个计时器 | 倒数态：`simulation starts in`；运行态：`simulation: running`、`t =   0.657 s`；下带 `── 克拉尼图形 · 沙在不动线上 ──`、`── 圆板模态 · J₄(j₄,₅r)cos4θ ──` | **会倒数**（3→2→1 方向正确），但第一个字形不是「3」（见 S4）；`running` 态只占 0.73 s 的最后约 0.15 s；**底边横线画在自己 rect 之外**（见 S2） |
| `pane_curriculum` | 136.90–147.52 `[after the gate]`（区间内无歌词；换边第一行） | 四列年级课表，每列一条年级头＋课程名；★ 标点名的课，走动高亮 | 列头 `大一` `大二 ▸` `大三` `大四`；大一 `★程序设计（C）` `★嵌入式微系统` `高等数学` `线性代数` `离散数学` `大学物理` `计算机导论` `程序设计实践`；大二 `★数据结构` `★算法设计` `★面向对象` `★计算机网络` `★计算机组成` `★操作系统` `★数据库` `概率统计`；大三 `★软件工程` `★软件项目管理` `★软件测试` `★深度学习` `★工业模型` `★大型工业软件` `软件体系结构` `需求工程` `人机交互`；大四 `毕业设计` `专业实习` `软件质量保证` `移动应用开发` `项目管理实训`；页脚 `★ = 你点名的重点，不是全部：同一学期还有别的课`、`这里只列到了每年的头几门` | 口径（★＝点名的，非培养方案）与 05 §「重点课」一致；但**课程名与 05 及同帧台词不一致**：`软件工程` 被排到大三（05 排大二）、`嵌入式微系统`（05／台词作「嵌入式微电子系统」、专业段 pane 作「嵌入式电子微系统」，一名三写）、`程序设计（C）`（05 作「程序设计基础（C 语言）」）、`计算机组成`（05 作「计算机组成原理」）；页脚「只列到每年的头几门」与实际列了 8/8/9/5 门不符 |
| `pane_point_set` | 29.28 `If I'm a set of point`（覆盖到 33.01，含 30.89 `Then I will give you my dimension`） | 上格 `IF`／右格 `THEN` 的双格装置，下方散点场 | 框上 `IF` / `THEN`；左格内 `a set of point`（歌词原文的语法错误照抄，正确）；无其他文字 | 与歌词相符（装置 + 点集）；THEN 格留空是设计；**边框上边比下边短 1 格**（95 vs 96，见 S10） |
| `pane_converge` | 162.23 `If I can, if I can`（区间含 164.07 `Give them all the execution`） | 六张小图（需求 / DFD / ER / 盒图 / 活动图 / 状态图）收敛成中间一个 UML 类框 | 小图题 ` 需求 ` / ` DFD ` / ` ER ` / ` 盒图 ` / ` 活动图 ` / ` 状态图 `；类框 ` class `、`+ giver`、`- taker`；下带 `── 光线步进 · 晶格巨构 ──` | **数量对不上**：docstring(:542) 与同帧台词都说是七张（含「时序图」），图里只有六张（见 S3）；收敛本身正确（`all`→`only`：六张 → 一个类） |
| `pane_backlog` | 169.61 `If I can have you back` | 三列 Scrum 看板；`完成` 列永远只剩一个破折号 | 列头 ` 待办 ` ` 进行中 ` ` 完成 `；卡片标 `▪ 需求`（每列同标）；`完成` 列是 `—`；页脚 `卡片一直被推回去` | **完全静止**：60 次采样（0–6.6 s）卡片数恒为 3（待办 1 张、进行中 2 张），没有任何卡片位移（见 S5）；且行只有 1.70 s（05 §P7c 的看板原意是 02:49.61–02:56.96 那 7.35 s 的「被困」） |
| `pane_knowledge` | 181.20–184.33（区间歌词 `I can answer all lo-o-ove`；行自带 lyric 写 `I've studied, I've studied`） | 一条自左下到右上的能力曲线，五点带小图形 | 左上 `大一 → 大三`；五点标 `C` `Java` `OpenEuler` `PGSQL` `反向传播`；点旁小图形 `{ }` `□` `>_` `≡` `∇` | 与 02b §4.5（C→Java→OpenEuler→PostgreSQL→反向传播）基本一致，但 `PGSQL` 是缩写；**u 钉在 1.0 时逐帧完全不变**（曲线只依赖 u，无 t／lt，见 S9 与时钟表）；02b 把这条曲线挂在 `I've studied how to properly love`（≈176.96），实际落在 `I can answer all lo-o-ove` 上 |
| `pane_love_class` | 184.33 `I know the algebraic expression of lo-o-ove` | 一个横向类框 + 一颗大心形曲线 | 框顶线 `Love`；`giver: Person` / `taker: Person` / `def give(self) -> None: ...`；下带 `── 心形曲线 r = 1 − sin θ ──`、`同一个形状，九个方程：没有哪个是“对”的` | **`class Love:` 这一行屏幕上根本不存在**（被自家 header 规则覆盖，见 S1）；心形曲线随 t 呼吸，所以「全片唯一静止」（02b §4.6 与 docstring :679）不成立；框只 46 格宽（栏宽 96），谈不上「放大铺满」；「九个方程」下面只画了一个心 |
| `pane_exchange`（`panel=bits`） | 41.92 `Switch my current` | F／M／XOR 三行二进制 + 走动的光标 | `F → M · 3 位`；`  F 01000110` / `  M 01001101` / `XOR 00001011 ← 3 位不同`；`改变一个字母，只动三位`；`0x46 ⊕ 0x4D = 0x0B` | 数值全对（0x46^0x4D=0x0B，三位）；**但内容属「换性别」**（F→M）却挂在「换电流」上；ops 同排期一致（`XOR / F→M / 3 bits`） |
| `pane_exchange`（`panel=clock`） | 45.52 `To AC, to DC` | 一个点阵椭圆表盘，两颗相距 π 的点＋中心 ⊕ | `12 小时 · 双重覆盖`；`两圈 = 一天` / `表盘不告诉你哪一圈` / `12h 是 24h 的二重覆盖`；`上午与下午是同一个位置` | 标签与图画相符（双覆盖讲得通）；表盘上没有 12/3/6/9 数字，只有点 — 说法靠文字承担 |
| `pane_exchange`（`panel=braid`） | 47.27 `And then blind my vision` | 三股辫：前两股交叉再交叉回去，第三股直行；交叉点随 t 下滑 | **`辩群 σ₁ · 可逆`**（错字，应为「辫群」）；`交叉一次再交叉回去，结果等于没动`；`σ₁ · σ₁⁻¹ = e` | σ₁ 画法对（B₃ 的第一、二股交叉）；**标题是错别字**：`\u8fa9`＝辩，应为 `\u8fab`＝辫（见 S12）；「看不见」这一行画辫群，属 想法.md 的五母题之一，勉强对应 |
| `pane_exchange`（`panel=hyper`） | 50.95 `Oh, we can travel` | 一个随 t 从菱形呼吸到圆角方框的超椭圆 | `超椭圆`；`n = 1.32`；`1 菱形 · 2 圆 · 6 方框` | 标签与图画相符；**docstring(:1199) 说这条线是 `Switch my current`**，与排期（`Oh, we can travel`）不符；模块 docstring(:1155) 说「Three panels（三个面板）」，实际画了四个（见 S11） |
| `pane_landmark_dialogue` | 54.74 `And we can unite`（覆盖 54.74–60.57，含 56.79 `So deeply, so deeply`、58.65 `If I can, if I can`） | 同一件「机器手与人的手」雕塑，三种裁切 | `对话 · we can unite` / `对话 · so deeply` / `对话 · the only God`；caption 依次 `两只手还没碰到` / `手指之间那颗星` / `只剩那颗星`；phase 2 另有 `不是接触，那颗星`；星在标题行上 | 一个 pane 里轮播三种标题：前两个各自落在对的行（unite 54.74、deeply 56.79），第三个 `the only God` 落在 58.65 `If I can, if I can` 上——02b §3.3 把「只剩那颗星」钉在 84.60 `If I'm the only God`（那行现在由 `pane_motif_stardiff` 画）；docstring(:875) 说 phase 2「两只手出画」，代码只是 `dim=0.35`（手还在，见 S13） |
| `pane_landmark_sword` | 125.33 `Challenging your God`（覆盖 125.33–136.90，含 `You have made some`、`Illegal arguments`） | **NWPU 字符画**（用户批准的替代品），一条白竖线扫过 | 标题 `为国铸剑`；caption `举剑的不是神`；下带 `── 2⁵³ 处的量化 ──` | **题／字幕与画面不符**：图上写的是 `NWPU` 四个字母，不是「为国铸剑」的雕塑（`school_sculpture.BANNER_FOR`，用户批注「用 NWPU 字符画代替」，见 S14）；docstring(:898) 说「全片用两次（含 Execution ×12）」，排期只有一次 |
| `pane_landmark_hezun` | 13.20 `[gap]`（器乐空隙） | 何尊字符画（`何尊_字符画.html` 路线），整屏字符块 | 标题 `何尊`；caption `“宅兹中国” · 铭文里最早的中国二字`；叠字 `origin = "宅兹中国"`、`// 何尊铭文，约公元前 11 世纪（周成王五年）` | **全片静止**（u 钉 1.0 时逐帧不变）：`phase=lt` 传了但没被用——HTML 路线优先（`:786`，见 S15）；docstring(:917) 说「两句歌词用它」，实际只有 13.20 一行、且在无词空隙上；两行叠字压在器身左侧笔画上 |
| `pane_landmark_cat` | 80.93 `If I'm a tabby cat` | 用户提供的 `猫学长_字符画.txt`，自上而下点亮 | 标题行**右端 `EXEC 14/00`**（见 S16）；段头 `猫学长`；`猫在不在里面，要打开才知道`；`|生⟩ + |死⟩) / √2 —— 叠加态不是不知道，是两个都在`（**左括号缺失**） | 叠加态公式少一个 `(`；标题行被 `_kit` 误当执行计数器，出现课程段的 `EXEC nn/00`；除了逐行点亮（u）之外不动（探针记为 by design 静止） |
| `pane_isolation` | 115.90 `You have left me in isolation` | 9 列点阵按到中心的距离逐个熄灭，只留中心一点在呼吸 | 标题 `孤立 · in isolation`；段头 `一个点留下`；`剩  0 / 98`；`你走了，剩下的都在灭` | **计数与画面自相矛盾**：caption 写「剩 0」，画面上中心那一点仍在（段头也写着「一个点留下」）——`- 1` 减掉了不该减的那个（见 S17）；其余（按距离熄灭、中心呼吸）正确 |
| `pane_fragments` | 119.81 `Erase all the pointless fragments`（覆盖到 125.33，含 `Then maybe, then maybe`、`You won't leave me so disheartened`） | 31×10 单元网格按阅读序擦除，一个红光标在网格上走 | 标题 `删除 · erase fragments`；段头 `无意义的碎片`；`306 / 310 已删`；`碎片不是痕迹，删了就没了` | 与歌词相符（擦除指令被执行）；故意留 4 格不删（docstring 有说明）；光标保证 u=1 时仍在动，是这一档里少数满足时钟要求的 pane |
| `pane_memory` | 110.40 `Though you have left`(2)／111.98(3)／112.89(4)／113.75(5)／114.75(6)／117.95 `If I can, if I can`(1) —— 6 行 | MEMORY 五行事块字母叠印 `layers` 层，逐层变暗并有一层走亮；下方 `dijkstra`＋`fragmentation` 带 | 标题 `MEMORY`；`layers 2`…`layers 6`、`layers 1`；下带 `── Dijkstra 裂纹 ──`、`── 内存碎片与整理 ──`、`碎片率 68% —— 整理不是删除` | **六次的图形各不相同**（六组签名互异，层数即参数），重复有理由（歌词同一句唱五遍）；但代码与注释相反：`layers > 3` 时水平错位被显式抵消（见 S18）；另注 `layers 1` 那一行挂在 `If I can, if I can` 上（05 P6 第 57 行）——与 `pane_isolation` 的切分逻辑一致 |

---

## 发现（按严重度）

### 严重

**S1 `pane_love_class` 把自己的第一行擦掉了——屏幕上没有 `class Love:`**
- 证据：`school_scenes.py:710-716` 先把 4 行打在 `by+1+i`（`by = y0`），也就是行 `y0+1`；随后 `:721` 才构造 `_kit(...)`，而 `_kit` → `school_courses._Kit.__init__` → `_header` 会在**同一行 `y0+1`** 画满宽的进度规则（`school_courses.py:143-145`）。
- 取证（真实版面 99–195×10–39）：
  ```
  10|▏── Love ──────────────────────────────────────
  11| ───────────────────────────────────────────────────────────────  ← 整行规则，class Love: 已不在
  12|       giver: Person
  13|       taker: Person
  ```
  `class Love:` 只出现在左侧聊天窗的代码块里（`timeline.md:948`），右栏从来没有。
- 建议：把 `_kit(...)` 提到画类框之前（或改用 `k = SS._kit(...)` 但不画 header / 让 header 行不落在此处），使 `class Love:` 留在屏上。

**S2 `pane_countdown` 的「底部」横线画在自己的矩形之外**
- 证据：`school_scenes.py:408` `s.put(x0 + 1, y1 - y0 - 1, "─" * max(1, w - 2), _ui(0.35))`——注释说要画「the flat line at the bottom of the box」，但 `y1 - y0 - 1` 是**相对高度**被当成**绝对行号**用。
- 取证（越界扫描，288 次命中，全库只有这一个 pane 越界）：
  - `197×52`：host 行 10–21 → 线落在 **y=10（自己第一行）**，仍在 rect 内但位置完全错（本应 y=20）；
  - `197×44`：host 行 10–18 → 线落在 **y=7**，即画进了上方的 `feature bands` 框（rect 是 99–195×10–32）；
  - 同样的越界出现在 `rows ∈ {24,26,28,34,38,44}` × 全部被测宽度 × 换边前后。
- 为什么自家探针没抓到：`_dev/pane_probe.py:102` 固定 `s = T.Screen(w+6, h+4)` 并把 rect 放在 `(2,2)`，此时 `y1-y0-1` 恒等于 `h-1`，永远在框内。**探针的矩形原点固定是它的盲区。**
- 建议：改为 `y1 - 1`；并让 `pane_probe` 至少测一组 `y0 > 2` 的矩形（例如真实版面 `(99,10,195,39)`）。

**S3 `pane_converge` 只画六张图，而同帧台词与自己的 docstring 都说七张**
- 证据：`school_scenes.py:542` docstring「seven diagrams into one class」；`:555` `titles = ["需求", "DFD", "ER", "盒图", "活动图", "状态图"]`（六项）。同帧左窗台词（`timeline.md:819-821`）：「软件工程一门课就有七张图：需求 · DFD · ER · 盒图 · 活动图 · 状态图 · **时序图**」「七张图，最后收成一张类图」。
- 取证：u=0.10／0.45／0.70 三帧都数到 6 个 `┌`，`时序图` 从未出现。
- 建议：`titles` 补 `序图`/`时序图` 第七项（并把 `cw` 重算为 4 列 × 2 行的 3+3+1 或直接 7 格布局），或在台词与 docstring 里把「七张」改成「六张」。

**S4 `pane_countdown` 的第一个数字不是「3」**
- 证据：`school_scenes.py:382-383` `digits[3] = ("████", "█   █", "█   █", "    █", "    █")`——第 2、3 行两侧都亮，既没有中横也没有底横，读起来是「Π／n」而不是 3（对照 `digits[2]` 是标准的 2：`████ / █ / ████ / █ / ████`）。
- 取证（u=0.10 → n=0 → 显示 `digits[3]`）：
  ```
  ████
  █   █
  █   █
      █
      █
  ```
- 建议：把 `digits[3]` 改成 `("████", "    █", "████", "    █", "████")`（与 2 同构、左竖换到第 4 行）。

**S5 `pane_backlog` 是死的：卡片永远不动，且这一行只有 1.70 s**
- 证据：`school_scenes.py:626` `n = 1 + int(fill * 4 * (0.6 + 0.4 * abs(math.sin(lt * 1.3 + i))))`——待办 `fill=0.18` 时 `int(0.432…0.72) = 0`，进行中 `fill=0.42` 时 `int(1.008…1.68) = 1`，两者都被取整抹平；没有别的位置／亮度随 `lt` 变。docstring(:605) 承诺「cards that are pushed from the right back to the left」。
- 取证：0–6.6 s 每 0.11 s 采样 60 次，`▪` 计数**恒为 3**；项目自带 `_dev/clock_probe.py` 也判 `pane_backlog() STILL`，理由写成「almost empty, not reported」。
- 行长度：`school_panels.py` 的 `SHOT_ROWS` 在 169.61 起、下一行 171.31 → 1.70 s（05 §P7c 的看板是 02:49.61–02:56.96 的 7.35 s 段）。
- 建议：让卡片数／位置真正随 `lt` 走（例如 `n = 1 + int(round(fill * 4 * abs(sin(lt * 0.9 + i))))`，并给每列一个随时间从右往左的 x 偏移）；同时考虑把这一段的 1.70 s 扩到跨 `Though we are trapped`。

**S6 `pane_polyhedra`：五个「正多面体」是同一个图形，且它站在「圆」的歌词上**
- 证据：`school_scenes.py:300-316` 的循环体里，几何只由 `cx`/`cy` 决定（`s.put(cx+2, cy-2+k, "│")`、四个 `dx,dy` 点、四条斜线），与 `i` 无关；只有 `:315-316` 的 `names[i]`／`vef[i]` 随列变化。docstring(:280) 声称「drawn as the graph they are - vertices and edges」——四面体的 4 顶点 6 边与正十二面体的 20 顶点 30 边不可能同形。
- 取证（真实版面）：行 14–18 五列**逐格相同**，只有行 19/20 的 `Tetra…Icosa` 与 `4-6+4…12-30+20` 不同。
- 主题：同帧台词（`timeline.md:178-188`）在讲「启翔湖真的是圆的吗」「把那个圆剪开拉直，就是周长」，ops 写 `abs(x)^n / n=2 / CIRCLE`，而 docstring 自认画的是 9.75 s 的 `Initialization`；05 §P1 第 11/12 行要的是启翔湖俯视图（圆环＋黑天鹅／斑头雁）与「圆环剪开拉直」。
- 取证（缺失）：`grep 启翔湖|黑天鹅|天鹅 player/_tools/*.py` → 0 命中。
- 建议：把该行换成启翔湖（圆环＋沿圆周移动的两只水鸟，`school_motifs` 已有现成曲线工具）；正多面体如要保留就按每个立体的顶点／边表分别画，或退回 9.75 的 `Initialization` 行。

### 中

**S7 `pane_parameters` 里那枚何尊是 0 墨点（等于没画）**
- 证据：`school_scenes.py:255-270` 的框是 `(x0+w-18, y0+max(0,h-8), x1-1, y1-1)`；真实版面下该 pane（两带 → host 行 10–21）`w=96, h=11` → 框 `(177,13,194,20)` = 18×8；`SC.glyph_cells("he_zun",18,8)` 非空单元 **0/144**（`school_sculpture.glyph_cells` 的 `A[c,r] < 110 → None` 阈值在缩小后把笔画全丢掉；64×31 也只有 28/1984）。
- docstring(:229) 说「The right-hand column carries the *source* of each value, and that is the point of the shot」——正好是这块位置，重画也救不回那句承诺。
- 建议：删掉这段（或改用 `html_cells`／`stroke_cells` 路线，并把框放在表格下方 `y0+8` 起的整宽区域，至少 20 行高）。

**S8 校徽四次出现，三次图形逐格相同**
- 证据：`_landmark` 只在 `closing`（`t > 190`）时改 caption 与 `dim`（`school_scenes.py:1322-1327`），图形完全由 `u` 决定；去掉下方 motif 带后比较：`0.03 == 17.00 == 21.00`（逐格相同，仅 op 行文字不同）。
- 规则：用户只豁免「校徽、铸剑雕塑」的重复，所以这不算违规；但 17.00／21.00 两次是**同一张图连播 8 秒**，02b §3.6 的意图是「开机与关机」各一次。
- 建议：给 17.00／21.00 两次不同的裁切／尺寸（例如一次只留外环轮廓、一次满栏），或合并成一次并把 21.00 让给别的校园内容。
- 反向的一例：`pane_memory` 六次**图形互异**（六组签名互异），重复有理，与 docstring 的「一层一层数」一致——这一条是合格的。

**S9 时钟：面板实际依赖哪个钟**
- 判据：u 钉 1.0、取槽内六帧比较（项目自带 `clock_probe` 的判据）。
- 只依赖 `u`、**u=1 后凝固**的面板：`pane_class`、`pane_parameters`、`pane_polyhedra`、`pane_protection`、`pane_point_set`、`pane_converge`（它们 u=1 时仍在「动」，靠的是 `MOTIF_IN` 分给它们的 motif 带，不是自己的图）；`pane_landmark_hezun`、`pane_landmark_cat`（只有 u 的点亮／揭示）；`pane_knowledge`（曲线长度＝u，无 t／lt）；`pane_backlog`（连 u 都不影响——见 S5）。
- 真正用 t／lt 的：`pane_power_on`(u+lt 闪红)、`pane_three_arms`(u+lt 相位)、`pane_countdown`(u+lt 计时)、`pane_curriculum`(u+t 走动高亮)、`pane_isolation`(u+t 呼吸)、`pane_fragments`(u+t 光标)、`pane_memory`(t)、`pane_love_class`(u+t 心形)、`pane_landmark_dialogue`(u+lt 星)、`pane_landmark_sword`(u+lt 扫光)、`pane_landmark_crest`(u+lt 落幕／下带看 t)、`pane_exchange` 四支(t)。
- 项目自带的 `clock_probe.STILL_OK`（`_dev/clock_probe.py:51-57`）把 `hezun / dialogue / cat / crest / sword / class / knowledge / backlog / converge / love_class` 一律标为「by design 静止」，其中 `dialogue`、`love_class`、`crest`、`sword`、`class`、`converge` 实际都在动——豁免表两头都不准，等于把「有没有钟」这个问题从检查里删掉了。
- 建议：按面板逐个说明它用的钟，并把 `STILL_OK` 收窄到真正静止的 `hezun / cat / knowledge / backlog`（外加 `pieces` 这种未排期的），其余移出。

**S10 `pane_point_set` 的装置边框上边短 1 格**
- 证据：`school_scenes.py:507` 顶边 `"┌" + "─"*(half-2) + "┬" + "─"*(w-half-2) + "┐"` 共 `w-1` 格；`:514` 底边 `"└" + "─"*(w-2) + "┘"` 共 `w` 格（中间行 `:511` 也是 `w` 格）。
- 取证：三行长度 `[95, 96, 96]`（真实版面），右上角比右下角少一列。
- 建议：顶边把 `w - half - 2` 改成 `w - half - 1`。

**S11 `pane_exchange` 的文档与排期／数量不符**
- 证据：`:1155` docstring「Three panels」但 `:1166` 的 `one = {...}` 与 `:1179` 的循环都是四支（bits/clock/braid/hyper）；`:1199` `_ex_hyper` 的 docstring 说「the one the song's line is about: `Switch my current`」，而排期把 hyper 放在 50.95 `Oh, we can travel`（`school_panels.py:293`），bits（F→M）放在 `Switch my current`。
- 建议：docstring 改成四支并更正所属歌词；若坚持「换形」属于 `Switch my current`，则把 hyper 与 bits 的槽对调。

**S12 错别字：`辩群` 应为 `辫群`**
- 证据：`school_scenes.py:1278` `k.section(k.by0, "\u8fa9\u7fa4 \u03c3\u2081 ...")`；`\u8fa9`＝辩(U+8FA9)，辫＝U+8FAB。屏幕上就是「辩群 σ₁ · 可逆」。
- 建议：`\u8fa9` → `\u8fab`。
- 附注：审计首轮我在 `school_panels.py` 里读到的 `校徾`(U+5FBE)、`公诚勇毁`(U+6BC1) 两处 ops 错字，在最后一次复核时已被并发修改修成 `校徽`、`公诚勇毅`；本文不再列为缺陷，但**这两行的 ops 与同屏 `pane_landmark_crest` 的 caption 需要再对一次**（caption 用的是正确的 `公诚勇毅`）。

**S13 `pane_landmark_dialogue`：说「手出画」其实只是调暗；第三段标题落在错的行上**
- 证据：`school_scenes.py:884` `dim=1.0 if phase < 2 else 0.35`——`_landmark` 里没有任何「让两只手消失」的分支；docstring(:875) 说 phase 2「the hands gone」。
- 相位仅由 `lt` 分桶（`:878` `phase = 0 if lt < 1.2 else (1 if lt < 2.4 else 2)`），所以第三块标题 `对话 · the only God` / `只剩那颗星` 必然出现在 t≈57.1–60.57，而那一带的歌词是 `So deeply, so deeply`(56.79) 与 `If I can, if I can`(58.65)；02b §3.3 把「只剩那颗星」钉在 84.60 `If I'm the only God`。
- 建议：把 phase 2 从这一 pane 里删掉（或改成随行的三行排期），并让 `dim=0.35` 时同时不画两手（`_landmark` 加一个 crop 参数）；「only God」交给 84.60 那行。

**S14 `pane_landmark_sword`：题／字幕说「为国铸剑」，画的是 NWPU 字符画**
- 证据：`school_sculpture.py:481-482` `BANNER = {"NWPU": ...}`、`BANNER_FOR = {"sword": "NWPU"}`（用户批注「微缩的为国铸剑雕塑效果还是不太好，用NWPU字符画代替」）；`school_scenes.py:771-782` 走 `banner_cells` 分支，绘出的就是四个字母（取证渲染可读作 `N W P U`）。
- 于是 `:903-904` 的标题 `为国铸剑` 与 caption `举剑的不是神` 落在了字母画上——同一 caption 也是 `school_fx` 125.50–128.20 全屏 flash 的 caption（`school_fx.py:1718-1719`）。
- 另：docstring(:898) 说该 pane 全片用两次（含 Execution ×12），排期只有 125.33 一次。
- 建议：既然图形已是校名字母，标题／字幕改成与之相符的（例如标题 `NWPU`、caption 保留 `举剑的不是神` 作为引文），或把 docstring 与 02b §3.1 的「两次」改成一次——两者需按用户口径二选一（见「无法判定」）。

### 低

**S15 `pane_landmark_hezun` 的 `phase` 从未生效**
- 证据：`:923` 传 `phase=lt`，但 `_landmark` 的路由顺序是 `HTML_ART` 先于 `DIGITS`（`:786`），而 `he_zun` 同时在两个集合里（`school_sculpture.HTML_ART`、`SC.DIGITS`）；`inspect.signature(SC.html_cells)` 没有 `phase` 参数 → u=1 时逐帧不变。
- 建议：要么把 `he_zun` 从 `HTML_ART` 里移出（走 `digit_cells(..., phase=lt)`），要么删掉 `phase=lt` 与 docstring 里「binary digits settle」的说法。

**S16 `pane_landmark_cat`：标题行出现课程段的 `EXEC 14/00`**
- 证据：`school_scenes.py:964` `k = _kit(s, x0, y0, x1, y1, max(3, (y1 - y0) // 2))`——`_kit` 的第六个位置参数是 `run`（`_kit` 定义见 `:931`），被当成「执行序号」传进 `_Kit._header`（`school_courses.py:140-142`），于是标题行右端画出 `EXEC 14/00`（`14 = max(3, 29//2)`，`00` 是 total=0）。
- 取证：标题行 `▏ …                                    EXEC 14/00`。
- 建议：改成 `_kit(s, x0, y0, x1, y1, 0, "猫学长")`（并删掉紧随其后的 `k.section(k.by0, "猫学长")` 重复标题，或保留其一）。

**S17 `pane_isolation` 的计数把留下来的那一点减掉了**
- 证据：`:1377` `f"剩 {9 * len(rows) - gone - 1} / {9 * len(rows) - 1}"`；中心点 `far == 0` 被 `continue` 跳过、不计入 `gone`，所以 u=1 时 `gone = 全部-1`，显示 `9*11 - 98 - 1 = 0`。而同一 pane 的段头写着 `一个点留下`，画面上中心那一点仍在。
- 取证：`剩  0 / 98` 与屏上的 `○●` 同时存在。
- 建议：改为 `f"剩 {9*len(rows) - gone} / {9*len(rows)}"`（或把中心点算进 `gone` 的期望值），让数字与画面一致。

**S18 `pane_memory` 的代码与自己的注释相反**
- 证据：docstring(:1443-1444)「The offset grows with the layer index so that six layers read as a smear and two read as a doubled word」；`:1479` `ox = ... + (off // 2) - (off // 2 if layers > 3 else 0)`——`layers > 3` 时水平错位被**整项减掉**，恰好在「要读成 smear」的六层时归零，只有 ≤3 层才有 1 格水平错位（垂直错位 `off % 3` 仍在）。
- 建议：把 `- (off // 2 if layers > 3 else 0)` 删掉（或改成随层数增长的水平偏移），使六层真的散开。

**S19 版面一致性：一半面板没有 kit 的标题行／规则**
- 走 `_Kit`（有 `▏` 标题行＋进度规则）的：`pane_landmark_*`(经 `_landmark`)、`pane_landmark_cat`、`pane_isolation`、`pane_fragments`、`pane_exchange`、`pane_memory`、`pane_love_class`。
- 直接 `s.put` 的：`pane_power_on/protection/pieces/class/parameters/polyhedra/three_arms/countdown/point_set/curriculum/knowledge/converge`——它们的首行就是内容（`pane_class` 行首是 `class World(UNO):`，`pane_knowledge` 行首是 `大一 → 大三`），没有标题行也没有规则。
- `pane_backlog` 更特别：`_kit` 的 header 行（`y0`）随后被自己的列盖线覆盖（`:619-625`），于是它有三条「只有上盖、没有下框」的列（底边在 `y1` 只是一条断开的横线，无 `└/┘` 角）。
- 与模块 docstring(:5-7)「the same three bands, the same border weight… one machine the whole way through」不完全相符。
- 建议：给这些 pane 统一补一个 `k.section(k.by0, 标题)`（或用 `_kit`），`pane_backlog` 补下框角。

**S20 小疵**
- `pane_knowledge` 的标签居中用 `len(name)` 而非 `_cells(name)`（`:672`，与 `school_courses._cells` 的宽字符口径不一致）；`PGSQL` 是 `PostgreSQL` 的缩写（02b §4.5 写全名）。
- `pane_curriculum` 的四列只用掉行 10–20，行 21–37 全空（30 行的面板只用 11 行）；★ 分布 2/7/6/0。
- `pane_landmark_hezun` 的两行叠字（`origin = …`、`// 何尊铭文…`）画在器身左侧笔画上（`:924-928` 在 `_landmark` 之后写），取证渲染里可见文字把字符画挖掉一块。
- `pane_three_arms` 的臂端专名 `北斗`／`蛟龙` 不在 `02_叙事设计.md` §9 的事实表内（该表用「第一型 50 kg 级水下无人智能航行器」），属未核实专名。

**S21 重复：motif 带把「只演一次」的图案又演了一遍（14 处）**
- 规则：用户「除了校徽、铸剑雕塑外的演出禁止重复」。`MOTIF_IN`／`MOTIF_ALSO`（`school_scenes.py:1645-1679`）让一个 host pane 的下半栏再画一遍某个 motif，而这个 motif 往往**自己也有排期**：
  `he_init`(带@pane_power_on 1.33 与 pane 9.75)、`phyllotaxis`(3.58 与 25.14)、`binary`(3.58 与 60.57)、`sine`(5.16 与 36.77)、`galaxy`(10.90 与 66.17)、`moire`(10.90 与 101.13)、`chladni`(12.47 与 92.00)、`bessel`(12.47 与 187.97)、`stardiff`(33.01 与 84.60)、`quantize`(125.33 与 88.34)、`powerdown`(0.03/17/21/193 每一次与 161.41)、`lattice`(162.23 与 98.93)、`byrne`(29.28 与 166.05)、`en_limit`(29.28 与 70.02)、`hyperellipse`(7.19 与 103.03)、`rectifier`(7.19)、`dijkstra`/`fragmentation`(110.40 起)、`fork_bomb`(pane_exec_os 与 95.28)。
- 为什么自家探针没报：`_dev/repeat_probe.py` 只按 `name(args)` 统计**排期行**，带不是行，所以 74 个 drawing 全算「不同」，输出 `0 repeat(s) to replace`。
- 建议：明确「带」是否算第二次演出；若算，就为每个 host pane 换用未排期的 motif，或把 motif 只留给它自己的行。

---

## 无法判定

1. **校门 vs 校徽谁是 0.03 的主图**：`05_歌词会话对照_v2.md` §P0 第 1 行要「校门上电（电流沿轮廓走）」，`02b` §3.6 要「校徽 半透明水印，走线从徽记里穿出」，代码是「校徽 pane + `school_fx` 校门全屏 flash(0.60–3.30)」。两份设计互相冲突，需要用户指定以哪一份为准（或确认「全屏 flash 算数」）。
2. **`软件工程` 属大二还是大三**：`05` §「重点课」把它列在大二 ★，`school_scenes.py:422-435` 把它排在大三；`03_批次设计/` 若有一份更晚的、用户批准的课表即可定案（我没查批次设计文件），否则需用户一句话。
3. **`pane_landmark_sword` 的标题／caption 要不要跟图一起换成 NWPU**：用户只批注了「图」换成字符画（`school_sculpture.py:476`），没说标题也换；同理 02b §3.1 的「Execution ×12 也用铸剑」是否作废，需要用户确认。
4. **`pane_backlog` 的归属歌词**：`05` §P7c 把看板挂在 `If I can have you back`（169.61，代码这么排），`02b` §4.4 挂在 `Though we are trapped`；而 169.61 那一行的台词（`timeline.md:850-856`）讲的是「大三六门＋毕设」。三者需要设计口径统一。
5. **`pane_knowledge` 的能力曲线该挂哪句**：02b §4.5 写 `I've studied how to properly love`(≈176.96)，代码挂在 181.20（区间只有 `I can answer all lo-o-ove`）——但 02b/05 又说四个 AI pane 要占 03:00 前后，可能是有意的取舍，需用户确认。
6. **「带」是否计入重复**（S21）：属于规则解释，不是代码事实。
7. **真机观感**：我没有跑播放器（无音频、TTY）。S1/S2/S13 这类「覆盖／越界在动起来之后是否更明显」只能靠 `_dev/live_screen_probe.py` 或实际播放确认；`_dev/pane_probe.py --shots` 可以出 PNG 逐帧看一眼（我未生成图片文件，以免在仓库里留下非审计产物）。
