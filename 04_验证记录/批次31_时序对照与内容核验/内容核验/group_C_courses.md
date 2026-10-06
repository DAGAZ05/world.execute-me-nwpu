# C 组审计：专业课 panel 与机器文本

审计对象：`player/_tools/school_courses.py`（`draw_course` / `draw_gauge` / `draw_ai`）、
`player/_tools/school_machine.py`（章节条 / boot log）、
`player/_tools/school_panels.py` 的课程·执行·章节表（`EXEC_PANES` / `GAUGE_SLOTS` / `EXEC_AT` /
`MACHINE_PROG` / `CHAPTERS` / `BOOT_LOG`）。

审计时的版本（本次审计期间 `school_panels.py` 被另一个 agent 于 11:05:45 改过，以下哈希是**当前**状态）：

| 文件 | SHA256(前16) | mtime |
|---|---|---|
| `school_courses.py` | `B618C7A09E2EBA12` | 2026-10-05 16:50:12 |
| `school_panels.py` | `6C36EEDDF8052D2C` | 2026-10-06 11:05:45（714 行） |
| `school_machine.py` | `ED1D52CB49C15FA4` | 2026-10-04 23:38:02 |

方法：不播放音频、不进 TTY。用 `python -` 短脚本导入 `tui_live` + `school_panels`（`PV_VARIANT=school`），
① 从 `player/input/lyrics.lrc` 取真实歌词时间；② 打印 `shot_rows()` / `ops_machine(t, ops)`；
③ 用 `T.Screen` + `SP.draw_scene_pane(...)` 渲染每个 pane 并逐行转写屏上文字；
④ 用 `T.Engine()` + `T.draw` 渲染整屏（197×52 真实窗口）包住 `draw_scene_pane` 量出 pane 的真实矩形。

**真实 pane 矩形（197×52，`--variant school`）＝ `(1,10)-(97,39)`，即 97×30 格**（门之后左右互换，门前在右侧 `(99,10)-(195,39)`，同为 97×30）。
下文凡写“真实尺寸”均指 97×30；`_dev/pane_probe.py:30-31` 里的 `(113,36)` 已与实况不符（见 F-32）。

---

## 1. pane 逐条

时间列＝该 pane 的排程区间（由 `shot_rows()` 算出）＋**区间内真实歌词**（LRC）；「行上标」＝该行 `lyric=` 字段
（`school_entry` 只把它塞进 `e["lyric"]`，播放器从不显示，仅排程/审计元数据）。

### 1.1 十四个 `pane_exec_*`

| panel | 出现的歌词行/时间 | 画的是什么（一句话） | 屏上文字（标题/字段/公式/数值/单位，逐字） | 结论 |
|---|---|---|---|---|
| `pane_exec_embedded` | 147.52–148.16（0.635 s）· 区间内 `Execution`（147.52）· 行上标 `Execution` | 蜂窝状板子：中间 UNO，周围六个外设格，串行总线上的电流点 | `▏嵌入式电子微系统`　`EXEC 01/15`　`6 路外设`　`串行总线上跑`　格内 `TRIG` `ECHO` `LCD` `SDA` `SCL` `GND` `UNO`　`实验课在实板子上，不在屏幕里`　底条 `5V 总线` | 主题对（嵌入式／测距接线）。但蜂窝**每个六边形的腰行左右斜杠反了**（F-20）；`6 路外设`把「HC-SR04 的 TRIG+ECHO」「LCD 的 SDA+SCL」「GND 电源」算成 6 个外设，实为 2 个器件＋电源；boot log 里的 `IR ranging on A0` 在图上没有 |
| `pane_exec_c` | 148.16–148.79（0.635 s）· 区间内 `Execution`（148.59）· 行上标 `Execution` | 指针在数组格上走，越界处标红 + 编译器警告 | `▏程序设计（C）`　`EXEC 02/15`　下标 `0 1 2 3 …13`　`*p++    2   addr 0x0009`　`warning: array subscript is above array bounds`　`[-Warray-bounds]`　术语 `pointer` `malloc / free` `struct` `buffer overflow` `segfault` `GDB` `compile / link` `Makefile` `valgrind` | 主题对（指针／越界）。但**越界红格永远画不出来**（F-21）；`addr` 由屏幕列算出（`0x0009` 随布局变）；格子框重叠成 `┌─┌─`；两位下标连成 `910111213` |
| `pane_exec_ds` | 151.51–152.33（0.825 s）· 区间内 `Execution`（151.53）· 行上标 `Execution` | 红黑树 + 黑高不变式（＋本该有的复杂度曲线与对照表） | `▏数据结构 · 红黑树`　`EXEC 03/15`　`── 红黑树 · 插入 ──`　键 `10 5 15 3 7 12 18`（真实尺寸下只有 7 个）　`插入   15/15  ·  黑高相等`　`① 根与叶为黑` `② 红节点之子必黑` `③ 各路径黑高相等`　`── 复杂度 ──`（**标题下空白**）　`── 对照 ──` `结构 平均 最坏`（**0 行数据**）　`二叉搜索树最坏退化成链。` `红黑树把最坏也做到 O(log n)，` `这就是它值得存的原因。`　底条 `search 8` | **真实尺寸下丢内容（F-6）**：复杂度曲线整段空白、对照表只有表头、树只画 7/15 个键却写 `插入 15/15`。三栏布局要求 `bw≥100`，实测 `bw=95`，永远回落到堆叠分支，而堆叠分支给曲线 6 行、给表 0 行 |
| `pane_exec_algo` | 152.33–153.16（0.825 s）· 区间内 `Execution`（152.43）· 行上标 `Execution` | 三栏：归并排序递归树 / LCS 动态规划表 / 区间调度贪心 | `▏算法设计 · 分治/动规/贪心`　`EXEC 04/15`　`── 分治 · 归并排序 ──` `── 动态规划 · LCS ──` `── 贪心 · 区间调度 ──`　`N W U N W P U !`（表头）／`N W P U S O F T`（行标）　`1 1 1 1 1 1 1 1` … DP 数值　`a[i]==b[j]: dp[i][j] = dp[i-1][j-1] + 1` / `否则 = max(dp[i-1][j], dp[i][j-1])`　`把重算的部分存起来，就是动态规划的全部`　`分到只剩一个，再合并上去`　`T(n) = 2T(n/2) + O(n) = O(n log n)`　`按结束时间排序，能接上就接：贪`（被列宽截断）　`A`…`H` + `← 选`　底条 `T(n)` | 主题对。但 **DP 表行列标签各错一格**（F-30）；**贪心三处自相矛盾**（未按结束时间排序、被选区间 C=[14,20] 与 F=[15,21] 重叠、题注被截断）（F-14） |
| `pane_exec_se` | 153.16–153.98（0.825 s）· 区间内 `Execution`（153.32）· 行上标 `Execution` | Youdon/DeMarco 数据流图：外部实体／加工／数据存储／带名数据流 | `▏软件工程 · 数据流图`　`EXEC 05/15`　`学生` `教师`　`1 提交` `2 编译运行` `3 自动判题` `4 反馈`　流名 `源代码` `编译日志` `测试用例` `通过率` `写入` `读取`　`D1──提交记录` `D2──测试用例`　`□ 外部实体   ╭─╮ 加工   ═ D1 数据存储   → 数据流`　`箭头上都有名字：没有名字的流向图叫流程图`　底条 `data` | 主题与记号对（加工是圆角框、存储是双线＋ID、流向都有名）。`源代码` 标签压在第一个加工框的左上角 `╭` 上；`教师` 外部实体画了两次（F-27） |
| `pane_exec_oop` | 153.98–154.81（0.825 s）· 区间内 `Execution`（154.31）· 行上标 `Execution` | 左：三层继承；右：接口＋vtable＋对象内存布局 | `▏面向对象 · UML`　`EXEC 06/15`　`── 继承 · is-a ──` `── 接口与多态 ──`　`Person`/`- name: str`　`Student`/`- sid: str`　`Teacher`/`- tno: str`　`GradStudent`/`- lab: str`　`TA`/`- course: str`　`<<interface>>` `Enrollable` `+ enroll(): void` `══▷ Student 实现`　`Person s = new Student();` `s.login();` `↓ 运行期查表`　`vtable @0x2f40`　`[0] Person.login()` `[1] Student.login()` `[2] Teacher.login()` `← 选中`　`Student s → 对象内存` `vptr  → 0x2f40` `字段  name · sid` `new 在堆上，引用在栈上`　`+ 公有` `- 私有` `# 保护`　`同一句调用，不同对象不同行为`　底条 `dispatch` | 主题对，继承三角在父类端（UML 正确），`vptr` 与 `vtable @0x2f40` 一致。小问题：实现关系画成实线 `══▷`，而自身注释（`:551`）说“UML draws it dashed”；调用点写 `Person s`、内存框写 `Student s`（同一变量两个类型） |
| `pane_exec_net` | 154.81–155.63（0.825 s）· 区间内 `Execution`（155.20）· 行上标 `Execution` | TCP 三次握手 → HTTP 两次请求 → 四次挥手时序图 | `▏计算机网络 · 三次握手`　`EXEC 07/15`　`CLIENT`（右侧**无** `SERVER`）　报文逐字：`SYN  seq=x`／`SYN+ACK  ack=x+1`／`ACK  ack=y+1`／`GET /student?id=41827`／`200 OK  application/json`／`GET /static/app.js`／`200 OK  1.2 KB  keep-alive`／`FIN  seq=u`／`ACK  ack=u+1`／`FIN+ACK  seq=w`／`ACK  ack=w+1`　阶段名 `三次握手` `HTTP` `四次挥手`　`握手 → 传数据 → 挥手：一条连接的一生`　底条 `seq` | **5/11 条报文在屏上没有字（F-3）**：`SYN+ACK ack=x+1`、`200 OK application/json`、`200 OK 1.2 KB`、`ACK ack=u+1`、`FIN+ACK seq=w` 全部丢失（`span = x_to-x_from` 对 `<` 方向为负 → `label[:0]`），标题写“三次握手”而 SYN+ACK 看不见；`SERVER` 是空串 |
| `pane_exec_os` | 155.63–156.46（0.825 s）· 区间内 `Execution`（156.18）· 行上标 `Execution` | OpenEuler 上的 `top`＋运行队列＋进程状态机＋地址翻译＋调度 | `▏计算机操作系统 · OpenEuler`　`EXEC 08/15`　`top - 03:11:24 up 41 days,  3:07,  1 user`　`Tasks: 214 total,   1 running, 213 sleeping`　`%Cpu(s):  6.2 us,  1.1 sy, 92.7 id`　表头 `  PID USER      PR  NI  %CPU  %MEM  STAT  COMMAND`；数据 ` 4100 root      20   0   4.0  0.3     kworker/0:1` … ` 5059 … systemd`　`run queue` `R:python3  S:sshd     S:postgres S:gcc`　`── 进程状态 ──` `new 新建` `ready 就绪` `running 运行` `blocked 阻塞` `exit 终止` + 转移词 `fork` `调度` `时间片到` `I/O 请求`　`阻塞不占 CPU`　`── 地址翻译 ──` `0x7ffd_1a3c 虚拟地址` `PGD  → 0x2f 页目录` `PTE  → 0x8c 页表项` `0x1a3_a3c 物理地址` `TLB 命中/未命中` `1 个周期`／`miss → 查表` `缓存命中率决定实际速度`　`── 调度 ──` `P1 P2 P3` `时间片 4 ms，就绪队列重排` `R:python3 在跑`　底条 `%CPU` | 主题对（最字面的“执行”）。三处内容错：**状态机转移标错**（`时间片到`→阻塞、`I/O 请求`→终止）、**%CPU 合计 ≈25% 与 `%Cpu(s)` 7.3% 矛盾**、STAT 列只有表头、COMMAND 画在 STAT 列下；高亮“运行”行与 `R:python3` 不一致（F-12） |
| `pane_exec_co` | 156.46–157.28（0.825 s）· 区间内 `Execution`（157.12）· 行上标 `Execution` | 4 位补码/移位加乘法器的 A、Q、M 寄存器轨迹 | `▏计算机组成原理 · 补码乘法`　`EXEC 09/15`　`M    00001011   =  11`　`A    00000010`　`Q    0000111▲`　`C    0   step 3/8`　`▸ 若 Q0=1：A ← A+M；否则跳过`　`▸ 算术右移 (C,A,Q) 一位`　`product   47   (13 × 11 = 143)`　术语 `ALU` `two's complement` `pipeline` `cache` `ISA` `Booth` `bus / DMA` `microprogram` `Verilog`　底条 `A/Q` | **数值自相矛盾（F-4）**：`product` 与括号里的 `13 × 11 = 143` 不等（真实时长内只到 step 2/8，显示 47/94；跑到 step 8/8 显示 **171**，唯一正确值是 step 5/8 的 143）；8 步对 4 位乘法多一倍；`C` 是 `(a+m)>255` 伪值；`Q` 最低位被 `▲` 覆盖；标题/Booth 说带符号，画的是无符号移位加 |
| `pane_exec_db` | 157.28–158.11（0.825 s）· 区间内 `Execution`（158.02）· 行上标 `Execution` | PostgreSQL `EXPLAIN` 计划树 + 其下的 B+ 树索引 | `▏数据库 · EXPLAIN 与 B+ 树`　`EXEC 10/15`　`Limit  (cost=0.29..8.31 rows=1 width=36)`　`└─ Index Scan using student_pkey on student`　`Index Cond: (id = 41827)`　`Filter: (college = 'software')`　`B+ root`　`internal  0  137  274  411`　`B+ leaf  0  137  274  411  548  685  822  959 1096 1233 1370 1507`　`三层树，一次查询三次 I/O`　底条 `scan` | 主题对（计划树＋B+ 树，三层=3 次 I/O 也对）。但**树里没有 41827**：内部键只到 411、叶键只到 1507，而查询条件是 `id = 41827`；内部键只是前 4 个叶键（0/137/274/411），12 个叶子里 8 个没有分隔键；扇出画成一排反斜杠（F-29）。计划文本用 `└─` 而非 PG 的 `->`，`Filter` 缺 `::text`（风格问题） |
| `pane_exec_pm` | 158.11–158.93（0.825 s）· **区间内真实歌词 `Ein, dos`（158.79）**· 行上标 `Execution` | WBS 甘特图：四条任务条＋关键路径变红＋周刻度 | `▏软件项目管理 · WBS/Gantt`　`EXEC 11/15`　`需求` `3d`／`设计` `2d`／`编码` `4d`／`测试` `3d`　`W1 W2 W3 W4`　`critical path`　术语 `WBS` `critical path` `burndown` `risk register` `Gantt` `milestone` `stakeholder` `scope creep` `retrospective`　底条 `sprint 3` | **单位/刻度错（F-13）**：横轴总量 12 天（条上写 `3d/2d/4d/3d`）却标 `W1–W4`（4 周）；串行链零浮时（3+2+4+3=12=项目总长）→ 四门全在关键路径上，却只把 `编码`/`测试` 标红 |
| `pane_exec_test` | 158.93–159.76（0.825 s）· **区间内真实歌词 `Trios, ne`（159.66）**· 行上标 `Execution` | 用例×路径覆盖矩阵＋缺陷分布 | `▏软件测试 · 覆盖率`　`EXEC 12/15`　`cases` `→ paths`　行号 `1`…`6`，格 `✓`/`×`　`defects` + 12 个 `░▒▓█` 柱　术语 `black box` `statement coverage` `branch coverage` `regression` `fuzzing` `unit test` `boundary value` `pytest` `CI`　底条 `cov %` | **`cov %` 与矩阵矛盾（F-5）**：底条 `cov %` 是 `|sin|` 波形（同一帧读到 `21.0`），矩阵实测 81✓/15× = **84.4%** 通过率；`defects` 柱高只由失败总数决定（`(nfail*(b+2)//(b+3))%4`），不含按列信息 |
| `pane_exec_dl` | 159.76–160.58（0.825 s）· **区间内真实歌词 `Fem, liu`（160.45）**· 行上标 `Execution` | loss 曲线＋反向传播（红）叠加 | `▏深度学习 · 反向传播`　`EXEC 13/15`　`loss 0.101`　`∇loss`　术语 `tensor` `forward / backward` `chain rule` `learning rate` `loss` `epoch / batch` `overfitting` `attention` `PyTorch`　底条 `loss` | 主题弱：**没有计算图/边**，“反向”只是沿曲线隔行贴 `/` 与 `\`（`:1050-1055`），docstring 说的“梯度沿边回流”没有画；绿点在 `sin` 轨迹上、不在曲线上 |
| `pane_exec_industrial` | 160.58–161.41（0.825 s）· 区间内无歌词（158.02 与 161.51 之间）· 行上标 `Execution` | 四格工业软件界面：特征树／BOM／等轴测视口／爆炸视图 | `▏大型工业软件`　`EXEC 14/15`　`feature tree` `▾ Part1` `▾ 拉伸1` `草图1` `▾ 拉伸2` `草图2` `▾ 圆角1` `▾ 阵列1`　`BOM 零件表` `件号名称       材料    数量`　`01  端盖       45 钢   1`／`02  深沟球轴承 GCr15   2`／`03  主体       ZL104   1`／`04  螺栓 M8    Q235    6`／`05  密封圈     丁腈    2`　`爆炸视图` `① 端盖` `② 轴承` `③ 主体` `④ 螺栓`　`isometric  ±X ±Y ±Z`　底条 `solver` | 主题对（特征树 拉伸 用字已正确 U+4F38）。真实尺寸下爆炸视图只有 4/5 个零件（BOM 5 行，`⑤密封圈` 不画，`:1137-1138` 的 `room` 截断）；等轴测视口只有 4 点＋4 斜线；BOM 表头 `件号名称` 无间隔（F-28） |

### 1.2 六个 `pane_gauge_*`（三句倒数各两个）

| panel | 出现的歌词行/时间 | 画的是什么（一句话） | 屏上文字 | 结论 |
|---|---|---|---|---|
| `pane_gauge_burndown` | 148.79–149.22（0.435 s）· 区间内无歌词 · 行上标 `ein, dos`（真实 `Ein, dos` 在 158.79） | 燃尽图：理想直线（灰点）＋实际折线（●，始终在理想线之上） | `▏软件项目管理 · 燃尽图`　`在跑不完的 Sprint`　`ideal ─  actual ●`　11 个日刻度 `┬`　实际序列 `100 96 88 85 74 70 66 61 58 52 50`（未标数值） | 图型对（向下、且始终高于理想线=做不完）。但**标题压在 day0 的 100% 数据点上**（`:1531` 后写在 `by0`）；图例写 `─` 而理想线画 `·`；无坐标数值/单位；`ideal = [(0,100),(10,0)]` 是死变量（F-19） |
| `pane_gauge_pareto` | 149.22–149.66（0.435 s）· 区间内无歌词 · 行上标 `ein, dos` | 缺陷帕累托柱（降序 6 根） | `▏软件测试 · 缺陷帕累托`　`defect pareto`　`cum 80% ──`　柱值 `42 27 15 9 5 2`（**未标**）　标签 `空指针 越界 竞态 内存 精度 其他` | 柱降序、标签用字正确（竞态=race condition）。但**没有累计百分比折线**（右侧整片空），只有一行静态文字 `cum 80% ──`，与自身 docstring“cumulative percentage rising, and the 80 % rule marked”矛盾；柱上无数值/百分比（F-15） |
| `pane_gauge_attention` | 149.66–150.06（0.395 s）· **区间内真实歌词 `Execution`（149.78）** · 行上标 `trios, ne` | 注意力热力图（对角线亮） | `▏深度学习 · 注意力`　`attention  head 3`　行标 `0 2 4 6 8 10 12 14 16`　`softmax focus 0.92` | **半张被覆盖＋标签与数据错位（F-16）**：`n=18` 但 `y = y0 + r//2` → r 与 r+1 写进同一格、后者覆盖前者，屏上每行显示的是**奇数** r 的数据而标签只写偶数（0,2,…,16）；实测带 `0` 标签的那一行对角线在第 1 列而非第 0 列（整幅对角线右移一格）。`n` 的上界写成 `(h-3)*2`，说明本意就是“每终端行两行”，但没有合并/错开而是直接覆盖。“`softmax focus`”不是 softmax（权重 `exp(-|r-c|*0.7)+0.08*exp(-|r-c-3|*0.5)` 阈值量化 + `hash()` 噪声） |
| `pane_gauge_fem` | 150.06–150.45（0.395 s）· 区间内无歌词 · 行上标 `trios, ne` | 翼型截面的有限元网格（应力区加密、红色集中） | `▏工业模型 · FEM`　`mesh  4820 nodes  9,318 elements`　`▲ 应力集中`　`网格只在零件上，零件外面什么都没有`　底条 `mesh`（blink） | **不是网格（F-17）**：整幅只有横线 `─` 和 `┼`，从不画竖线 `│`；节点/单元 4820/9318 ≈ 1:1.93 是三角网格的比例，画出来的却是四边形栅格 |
| `pane_gauge_assembly` | 150.45–150.98（0.530 s）· **区间内真实歌词 `Execution`（150.64）** · 行上标 `fem, liu` | 爆炸装配：零件沿轴分开 | `▏大型工业软件 · 装配体`　`assembly  BOM 41 parts`　`P1`…`P6`　`explode  ←──────→` | **画坏了（F-18）**：6 个方盒只有编号没有名称/材料/数量；`sep` 把零件推右并 `min(cx, bx1-6)` 截断 → P5 与 P6 重叠成一团（`└────│┘P6`）；所谓引线只是盒下一格的孤立 `│`；标题写 41 个零件、屏上 6 个 |
| `pane_gauge_final` | 150.98–151.51（0.530 s）· 区间内无歌词 · 行上标 `fem, liu` | 只有一条 `毕设` 的甘特图，条跑出右边缘 | `▏毕业设计 · 甘特图`　`Gantt  毕业设计`　`毕设` + 满条 + `???`　`它没有终点`　13 个刻度 `┬` | 图型与玩笑对（毕业设计·liu，设计 `02b §4.2` 就是这么定的）。刻度无月/单位数值（低） |

### 1.3 四个 AI pane（`draw_ai`）

| panel | 出现的歌词行/时间 | 画的是什么（一句话） | 屏上文字 | 结论 |
|---|---|---|---|---|
| `pane_ai_cnn` | 171.31–173.10（1.79 s）· **区间内真实歌词 `I will run the execution`（171.77）** · 行上标 `If I can have you back` | 9×9 的字母 N，3×3 核滑动，7×7 特征图随之填色＋四层收缩条 | `▏卷积神经网络 · 特征图`　`EXEC 01/04`　`── 卷积 · 特征图 ──`　`输入 9×9`　`特征图 7×7`　`L1 · 边缘` `L2 · 纹理` `L3 · 部件` `L4 · 物体`　`卷积核在滑，滑到哪里就在哪里写一个数`　术语 `kernel / filter` `stride` `padding` `feature map` `pooling` `ReLU` `receptive field` `batch / channel` `backbone` | 主题对，7×7=9-3+1 也对，核框比窗口宽 1 格；**计数器显示 `EXEC 01/04`**（`draw_ai(..., run=1)`，四页全是 01，且分母 4 与课程页的 15 不同）（F-26）。行上标歌词与真实歌词不符（元数据，不上屏） |
| `pane_ai_attention` | 173.10–174.90（1.80 s）· 区间内 `Though we are trapped`（173.11）+ `We are trapped, ah`（174.80） | 7×7 注意力权重矩阵，对角线亮，选中行＋权重条 | `▏注意力 · 权重矩阵`　`EXEC 01/04`　`── 注意力 · QKᵀ → softmax ──`　`句子：西工大软件学院 · 每个字是一个 token`　tokens `西 工 大 软 件 学 院`（行列各一遍）　`第 2 行：“工”在看谁`　`每行加起来等于 1：分配注意力，不是平均分配`　`注意力就是一个权重矩阵，软化了的查找表`　术语 `query / key / value` `dot product` `softmax` `temperature` `multi-head` `causal mask` `context length` `self-attention` `flash attention` | 四页里画得最正确的一张：单元格 2 列宽×1 行 ≈ 正方形，行列标签齐全，`第 2 行`/`“工”` 与高亮行一致。小问题：权重条 7 段之间无间隔，读起来仍是一条实线（`:2300` 注释自称已修）；计数器同样是 `EXEC 01/04` |
| `pane_ai_rl` | 177.50–179.30（1.80 s）· **区间内真实歌词 `How to properly lo-o-ove`（178.79）** · 行上标 `I've studied, I've studied` | 策略环＋一组 rollout 相对组均值打分＋奖励曲线 | `▏强化学习 · 奖励`　`EXEC 01/04`　`── 强化学习 · 策略更新 ──`　`环境 state` `策略 π` `动作 a` `奖励 r`　`同一个问题，采样 G 次`　`r=0.90 A=+0.34`／`r=0.40 A=-0.16`／`r=0.75 A=+0.19`／`r=0.20 A=-0.36`　`基准 = 组内平均 0.56，比它好的加权、比它差的压低`　`奖励曲线（每次策略更新之后）`　`步长太大`　`曲线上升才说明更新有效，不是损失下降`　术语 `policy π` `rollout` `reward` `advantage` `baseline` `exploration` `value function` `GRPO` `PPO` | **算术全对**：均值 0.5625→`0.56`，四个优势 ±0.34/−0.16/+0.19/−0.36 与 `r-mean` 一致，柱长∝r（57/26/48/13 ≈ r×64）。轴无数值；计数器 `EXEC 01/04` |
| `pane_ai_diffusion` | 179.30–181.20（1.90 s）· **区间内真实歌词 `Question me, question me`（180.78）** · 行上标 `I've studied, I've studied` | 同一张图三个噪声级：t=2 纯噪声 → t=1 → t=0 干净，标记走位 | `▏扩散模型 · 去噪`　`EXEC 01/04`　`── 扩散 · 逐步去噪 ──`　`t=2`　`t=1`　`◀ 现在`　`t=0`　面板间 `←`　`每一步都是“预测噪声，然后把它减掉”`　`从纯噪声到一个形状：最后一步才看得出是什么`　术语 `forward process` `reverse process` `timestep t` `noise schedule` `U-Net` `latent space` `classifier-free` `sampler` `CFG scale` | 方向自相矛盾：t=2 在左、t=0 在右（去噪是左→右），面板间箭头却写 `←`（`:2438`）；`t=0` 面板在 11×11 下几乎是一整块实心矩形，心形的两瓣/缺口分辨不出（`(x²+y²-1)³-x²y³≤0` 在 |u|≤1 网格内几乎全真）；计数器 `EXEC 01/04` |

### 1.4 机器文本

| 对象 | 位置/时间 | 内容（逐字） | 结论 |
|---|---|---|---|
| 章节条 `CHAPTERS`（`school_machine.py:28-39`） | 0.00／16.00／29.28／44.04／58.65／73.53／103.03／125.33／147.52／162.23 | `00 / 上电` `01 / 初始化` `02 / 定义` `03 / 电与时间` `04 / 副歌一` `05 / 万物皆点` `06 / 你走了` `07 / 非法参数` `08 / 处决` `09 / 软工与爱` | 名字与曲式大体对（P1/P2/P3/P4/P7a/P7b/P7c 的起点逐一对齐 `01_歌词分析.md §1`）。两处结构缺口：**P5 互换（88.34–103.03，14.7 s）没有章节**，条上仍是 `05 / 万物皆点`；`09 / 软工与爱` 一格里塞了 P7c+P8+P9（49.8 s），`P9 关机`（205.56）无章节。`school_machine.py:9` 的 docstring 写 `09 / 关机`，与 `:38` 的数据不符（F-25） |
| boot log `BOOT_LOG`（`school_machine.py:59-74`） | 0.840–2.783 s，逐行＋`[OK]/[..]/[WARN]` 状态牌，盒题在 `PROT_START` 后变 `init --protection`，右下角 `post n/14` | `power: USB 5V 0.48A`／`board: UNO R3  (ATmega328P)`／`clock: 16.000 MHz  crystal ok`／`bootloader: optiboot 115200`／`mem test ........ 2048 B SRAM`／`eeprom: 1024 B  clean`／`i2c: LCD1602 at 0x27`／`gpio: D2..D13 configured`／`sensor: HC-SR04 trig/echo`／`sensor: IR ranging on A0`／`serial: 9600 8N1  ok`／`watchdog: armed`／`[WARN] hc-sr04: echo floating, wire D3`／`protection: on` | **数字全对**（Uno R3=ATmega328P、16 MHz、optiboot@115200、2 KB SRAM、1 KB EEPROM、PCF8574@0x27、USB 5V/0.48A<0.5A、D3 在 D2..D13 内），与台词一致（`school_chat.py:67/73/80` 同样说 UNO、超声波、红外、LCD1602、杜邦线、防静电）。两点问题：① 这 14 行**是嵌入式专业课内容**，出现在 0.84–2.78 s，与 `05_歌词会话对照_v2.md:13/39`“02:10.74 之前一句专业课都不许出现 / 第一幕 完全禁止”直接冲突（批次 4 是刻意改的 → 是规则冲突，不是疏忽）（F-24）；② `PROT_START = 3.58`（盒题切换点）比“protection 那一句”（歌词 1.33、原片自己的 `film_panels.PROT_START = 1.313`）晚 2.25 s（F-24） |
| 程序清单 `MACHINE_PROG`＋`ops_machine`（`school_panels.py:660-699`） | 147.52 起（`MACHINE_FROM`，**无上界**），每 0.30 s 一条指令；盒题 `exec` | 地址与指令：`0040  LOAD  R1, [r0 + id]`／`0044  CMP   R1, #41827`／`0048  JNE   .lookup`／`004C  CALL  insert(R1)`／`0050  MOV   R2, [r1 + 0x04]`／`0054  ADD   R2, R2, #1`／`0058  STORE [r3 + 0x02], R2`／`005C  RET`；寄存器行例：`R1=00  R2=00  PC=0040  FLAGS=Z`、`R1=15  R2=27  PC=004C  FLAGS=Z`、`R1=2A  R2=4E  PC=0058  FLAGS=Z` | **PC 对**（`PC=0x40+4*cur` 正好是 `cur` 高亮行的地址，`MACHINE_AT + 4*i` 与实际行一致）。**R1/R2/FLAGS 与高亮指令无关**（F-10）：`R1=(n*7)&0xFF` 最大 0xFF，永远不等于 `#41827`(0xA363) → `JNE` 必跳、`CALL insert` 不可达，而 `FLAGS` 每三拍还打印一次 `Z`；`add R2,R2,#1` 的相邻帧 R2 却 +13；`.lookup` 与 `insert` 在清单里都没有定义（无法汇编）；`[r0 + id]`、`CALL insert(R1)` 也不是任何真实 ISA 的写法（boot log 说是 ATmega328P＝AVR）。**同一段“插入 41827”挂在 15 个课程标题下**（F-11）；仪表槽的标题直接泄漏内部 pane id（F-9） |

---

## 发现（按严重度）

### 高

**F-1｜六个仪表的三个倒数时间整体早 10.00 s；课程 pane 因此被挤到 0.635/0.825 s。**
`school_panels.py:118-119` `GAUGE_SLOTS = [(148.79,149.66,"ein, dos"),(149.66,150.45,"trios, ne"),(150.45,151.51,"fem, liu")]`；
LRC 实测三句倒数是 `158.79 Ein, dos`／`159.66 Trios, ne`／`160.45 Fem, liu`，末位 `161.51 Execution` —— **每一项恰好差 10.00 s**（158→148、159→149、160→150、161→151）。
后果（渲染实测）：`pane_gauge_attention`（149.66–150.06）区间内是 `Execution`(149.78)、`pane_gauge_assembly`（150.45–150.98）区间内是 `Execution`(150.64)，而三个倒数数字分别落在 `pane_exec_pm`(158.79)、`pane_exec_test`(159.66)、`pane_exec_dl`(160.45) 上 —— 与设计 `02b_图像对位与可视化表达.md §4.2`（“02:38.79–02:41.51，每个数字配一个仪表”，ein→燃尽图/dos→帕累托/trios→注意力/ne→FEM/fem→装配/liu→甘特）正好相反。
修法：`GAUGE_SLOTS = [(158.79,159.66,"ein, dos"),(159.66,160.45,"trios, ne"),(160.45,161.51,"fem, liu")]`（一行）。

**F-2｜`EXEC_AT` 是死表，而它恰好是正确的那份击点时间。**
`school_panels.py:88-89` 定义后全仓库无引用（`grep EXEC_AT` 只命中定义）；实际排程由 `_exec_rows()`（`:123-184`）从 `GAUGE_SLOTS` 推导；`:82-83` 注释里的 `_hit` 函数并不存在。
修法：删掉 `EXEC_AT`，或让 `_exec_rows` 用它做断言（`assert` 12 个击点与推导区间一致）。

**F-3｜网络 pane 里 5/11 条报文没有标签，三次握手的 SYN+ACK 看不见。**
`school_courses.py:688` `span = x_to - x_from`；`:702` `lab = label[: max(0, span - 3)]`；对 `d == "<"` 方向 `x_from, x_to = bx, ax` → `span = ax-bx = -94` → `label[:0] = ""`。
实测：`SYN+ACK  ack=x+1`、`200 OK  application/json`、`200 OK  1.2 KB  keep-alive`、`ACK  ack=u+1`、`FIN+ACK  seq=w` 均不在屏上；`SERVER`（`:656`）是空串。
修法：`span = abs(x_to - x_from)`。

**F-4｜组成原理 pane 的乘积与括号里的算式矛盾，8 步对 4 位乘法多一倍。**
`school_courses.py:841-842` `steps = 8; step = min(steps, int(lt*2.2)+1)`，`:846` `for i in range(step-1)`，`:867` `f"product  {(a<<4)|q:3d}   (13 × 11 = 143)"`。
计算实测：step=1→13、step=2→94、step=3→47、step=5（4 次迭代）→**143**、step=8（7 次迭代）→**171**；pane 只活 0.825 s（`lt≤0.83`）→ 只到 step 2/8（94），末帧若真到 8/8 会显示 `product  171   (13 × 11 = 143)`。
修法：`steps = 4`（4 位乘法 4 次），并把 `product` 只在 `step>=steps` 时显示。

**F-5｜软件测试 pane 的 `cov %` 与它自己的矩阵矛盾；缺陷“直方图”不含每列信息。**
`school_courses.py:1017-1020` `nfail = max(1, len([i for i in fail if i < done]))`；`h = (nfail*(b+2)//(b+3)) % 4`（只用总数）；`DETAIL` 之外底条 `LIVE["pane_exec_test"] = ("count","cov %",0)` → `_live` 的 `count` 分支 `v = abs(math.sin(t*1.3))*99`（`:2025-2027`）。
实测同一帧：底条 `cov %  21.0`，矩阵 81✓/15× = 84.4%。
修法：`cov = 100*(done - 已失败)/done` 直接传给 `_live`；直方图改成按列统计。

**F-6｜`pane_exec_ds` 在真实尺寸（97×30）丢掉两张图的内容，计数却写 15/15。**
`school_courses.py:1482-1490` 三栏要求 `k.columns(3,[10,7,9],mins=[40,26,30])`，`_Kit.columns`（`:252`）`if sum(need)+2*(n-1) > self.bw: return []` → 需 `bw≥100`；整屏实测 pane `(1,10)-(97,39)` → `bw=95` → 永远返回 `[]` → 走 `bands` 堆叠分支（`:1492-1499`）。
实测渲染：`── 复杂度 ──` 标题下**空白**（`_ds_curves` 的 `:1256-1257` 守卫 `y1-y0<4` 直接 return），`── 对照 ──` 只有 `结构 平均 最坏` 表头、**0 行数据**（`_ds_table:1334` 的 `yy > k.by1-6` 全部 break），树只画 7 个键（`depth` 从 3 降到 2）却写 `插入   15/15`。
修法：把 `mins` 降到 `[34,24,26]`（`bw=95` 可容纳 92），或给堆叠分支的表单列高度。

**F-7｜两个课程母题（ds 的像素排序、os 的 fork 炸弹）在真实尺寸永不出现。**
`school_courses.py:2074` `if motif and k.bh >= 26`；真实 pane 高 30 → `draw_y1=28`、`k.by1=27`、`k.by0=12` → `bh=25 < 26`。
实测：97×30 下 `pane_exec_ds` 无 `GPU 像素排序`、`pane_exec_os` 无 `fork 炸弹`（113×36 下两者都在）。
修法：把阈值改成 `k.bh >= 24`。

**F-8｜fork 炸弹文案的算术错，而且永远画不到那个代数（画在 `pane_exec_os` 内）。**
`school_motifs.py:387` `":(){ :|:& };:  —— 九代之后就是 4096"`：2⁹ = **512**，4096 = 2¹²（第 12 代）；同文件 `:352-357` 的 docstring 还写“the ninth generation is five hundred times the eighth”（实为 2 倍）。
而且 `:360` `depth = max(1, min(6, …))`、`:386` `f"{2 ** gen:5d} 进程"` → 最多 `代 6` / `64 进程`，标题 `fork 炸弹 · 1 → 4096` 不可达。
修法：文案改 `十二代之后就是 4096`，或把 `depth` 上限提到 12（并配合 F-7 的阈值）。

### 中

**F-9｜ops 框标题泄漏内部 pane id（六个仪表），末尾段泄漏 ticker 词。**
`shot_rows()` 里仪表行的 `ops=[pane]`（`school_panels.py:156` `ops=[pane]`，pane 是 `"pane_gauge_burndown"`），`ops_machine`（`:688-692`）匹配不到 `EXEC_PANES` 就原样输出。
实测：148.79–151.51 六槽的标题依次是 `pane_gauge_burndown`、`pane_gauge_pareto`、`pane_gauge_attention`、`pane_gauge_fem`、`pane_gauge_assembly`、`pane_gauge_final`；162.23 之后是 `DFD`、`SCRUM`、`CONV`、`Q`、`POLICY`、`NOISE`、`STUDIED`、`LOVE`、`BESSEL`。
修法：查不到课程时用 `_CO.COURSES.get(pane, (pane,))[0]` 兜底，并给末尾段一个 `MACHINE_TO`。

**F-10｜寄存器行与高亮指令无关，`JNE`/`CALL` 的符号在清单里不存在。**
`school_panels.py:693-699` `R1=(n*7)&0xFF`、`R2=(n*13)&0xFF`、`flags = "Z" if n%3==0 else …`。
实测连续三帧：`PC=0040 R1=00 R2=00 FLAGS=Z` → `PC=0044 R1=07 R2=0D FLAGS=C`（`CMP` 不写 R1，R1 却从 00 变 07）；`PC=0054`(ADD R2,R2,#1) 前后 R2 由 41→4E（+13）。
`CMP R1,#41827` 的立即数 41827 > R1 上界 255 → Z 永不可能成立，而 `FLAGS` 每三拍打印一次 `Z`；`JNE .lookup`、`CALL insert(R1)` 引用的 `.lookup`/`insert` 在 8 行清单里都没有定义。
修法：让 `R1/R2` 由被高亮的指令推演出（LOAD 值=41827&0xFF、ADD 时 +1），`FLAGS` 由 `CMP` 结果决定，或改成不带寄存器语义的“机器忙”指示。

**F-11｜同一段“插入学生 41827”清单挂在 15 个课程标题下；且清单一直画到片尾。**
`:688-692` 的 `head` 只换标题不换程序；`MACHINE_FROM = EXEC_FROM`（`:647`）没有上界 → 147.52–212.0 s（64.5 s）都是 `exec` 盒。
实测标题：`EXEC 09/15  计算机组成原理 · 补码乘法` 旁仍是 `LOAD/CMP/JNE/CALL/…` 插入程序；`EXEC 07/15  计算机网络 · 三次握手` 同理；末尾 `head=DFD`/`SCRUM`/`LOVE`。
批次 8 记录（`04_验证记录/批次8_专业段.md:112-113`）已承认“固定八条、没随章节换程序”。
修法：按 `EXEC_PANES` 的课程换 2–3 套清单，或把 `head` 改成不宣称“同一件事”的中性标题，并加 `MACHINE_TO=162.23`。

**F-12｜OS pane 三处自相矛盾：状态机转移、%CPU 合计、STAT/COMMAND 列。**
`school_courses.py:771-784` `states` 与 `trans = ("fork","调度","时间片到","I/O 请求")` 按相邻两两连线 → 画出 `running --时间片到--> blocked`、`blocked --I/O 请求--> exit`（正确：`running --时间片到--> ready`、`running --I/O 请求--> blocked`、`blocked --I/O 完成--> ready`、`running --结束--> exit`）。
`:735` 固定 `%Cpu(s):  6.2 us,  1.1 sy, 92.7 id`（繁忙 7.3%），而 `:744-746` 的 8 行 `%CPU = 0.4+4.0*|sin(lt*1.1+i)|` 实测 4.0+3.9+0.6+3.7+4.1+1.1+3.3+4.3 = **25.0%**。
`:737` 表头有 `STAT`，`:745` 数据行没有 STAT 字段、`:747` 进程名写在 `bx0+38`（落在 STAT 列下，COMMAND 列空）；`:750` 的 `◀` 行与 `:745` 高亮的 `i==0` 行不是同一行，而底栏永远写 `R:python3 在跑`。
修法：把 `%Cpu(s)` 改成按表算、补 STAT 字段并把进程名移到 `bx0+40`、转移词改成三元组 `(from,to,label)`。

**F-13｜项目管理 pane 的横轴单位错（12 天标成 4 周），关键路径标错。**
`school_courses.py:940` `tasks = [("需求",…,3,0),("设计",…,2,3),("编码",…,4,5),("测试",…,3,9)]`、`:943` `total = 12`（条上写 `3d/2d/4d/3d`），`:965-966` 却写 `W1..W4`（每个间隔 3 天≈一周）。
`:953` `critical = i in (2, 3)`：四段首尾相接、总时长 12 = 项目总长（零浮时）→ 四段全在关键路径上。
修法：刻度改 `D1..D4`/`第1周`，`critical` 改为按最晚完成时间算（此处应为全部）。

**F-14｜贪心栏三处自相矛盾。**
`school_courses.py:1433` `st, en = (i*7)%20, (i*7)%20 + 4 + (i%3)` → 8 行的结束时间是 `4,12,20,5,13,21,6,14`（升序 `4,5,6,12,13,14,20,21`），屏上行序并非按结束时间排序，而题注（`:1441`）写“按结束时间排序”。
`:1428` `picks = [0,2,5,7]` → 被标 `← 选` 的区间是 A=[0,4]、C=[14,20]、F=[15,21]、H=[9,14]，其中 **C 与 F 重叠**（15<20），贪心解不可能含两者。
题注被列宽截断成 `按结束时间排序，能接上就接：贪`（`:1441` 的 20 个汉字 = 40 格 > 该列 31 格）。
修法：先按 `en` 排序再画；`picks` 改成真正的活动选择结果；题注缩短到列宽内。

**F-15｜帕累托没有累计线。**
`school_courses.py:1535-1564` 只画柱与轴；累计百分比仅有一行文字 `cum 80% ──`（`:1564`，且 `k.u>0.75` 才亮）。
自身 docstring（`:1538-1539`）称“Bars descending, cumulative percentage rising, and the 80 % rule marked”。
修法：加一条按 `cumsum(bars)/100` 折线 + 80% 水平参考线（用第二纵轴或百分比刻度）。

**F-16｜注意力热力图半张被覆盖、标签与数据错位、`softmax` 名不副实。**
`school_courses.py:1576-1584`：`n = max(6, min(18, min(w-8, (h-3)*2)))` 实测 `n=18`，而 `y = y0 + r//2` → r 与 r+1 写同一终端行（后者覆盖前者），行标只在 `r%2==0` 时画（0,2,…,16）。
实测 97×30：带 `0` 标签的一行对角线在第 1 列（`x0+1`），不是第 0 列 —— 每个可见行显示的是奇数 r 的数据，标签指的是偶数 r，对角线整体右移一格；`(h-3)*2` 的上界说明本意是每终端行放两行，但代码是覆盖而非合并/错开。
`focus = min(0.92, k.u*1.1)` 与 `hash((r,c,int(lt*2)))%7` 都不是 softmax。
修法：`n = 9`（或按 `ai_attention` 的写法一格 2 列宽、一行一个 token），让行标与 `r` 一一对应，`focus` 改成真的按行归一。

**F-17｜FEM “网格”没有竖线，单元数与画法不符。**
`school_courses.py:1630-1638` 只在 `inside` 的列上写 `"┼"` 或 `"─"`，全图无 `│`；`mesh  4820 nodes  9,318 elements`（`:1615`）比值 1.93 是三角网格（E≈2N）的比例，而画的是四边形栅格。
修法：按固定列距画 `│`（或把单元数改成四边形网格的 ≈4.8k）。

**F-18｜装配体 pane 画坏了。**
`school_courses.py:1655-1667`：`n=6` 只有 `P1..P6` 无名称；`sep = int(k.u*(w//4))` 后 `cx = min(cx+sep, k.bx1-6)` → i=4、5 都被截到 `bx1-6`，P5 与 P6 完全重叠（渲染为 `└────│┘P6`）；“引线”只是盒下一格的孤立 `│`（`:1665`）；标题 `assembly  BOM 41 parts` 与屏上 6 个零件不符。
修法：`sep` 按零件数均分且不截断、用 `_ind_explode` 的等距写法、给零件补名称/数量。

**F-19｜燃尽图的标题覆盖 day0 数据点／图例与画法不符。**
`school_courses.py:1523-1531`：`actual[0]=100` 与 `ideal` 的第一个点都落在 `k.by0`，而标题 `在跑不完的 Sprint` 在画完之后写在 `k.by0`（`:1531`）→ 覆盖前 19 格（含 x=bx0+2 的 ●）；图例写 `ideal ─ actual ●`（`:1532`）而理想线画的是 `·`（`:1520`）。
`:1516` `ideal = [(0,100),(10,0)]` 是死变量。
修法：标题写到 `k.by0` 之前先画数据，或把数据区下移一行；图例字符改 `·`。

**F-20｜嵌入式 pane 的六边形腰行左右斜杠被下半部分覆盖（几何 bug）。**
`school_courses.py:321-328`：`for i in range(1, r+1)` 同时写上半行 `top+i = cy-r+i` 与下半行 `bot-i = cy+r-i`；当 `i == r` 时两者都是 `cy` —— 最宽那一行先按上半部写（左 `/` 右 `\`），随即被下半部覆盖成（左 `\` 右 `/`）。
实测（`r=2, cy=10` 隔离渲染）：

```
       ___
      /   \
     \ TRIG/     <- 腰行左右反了
      \   /
       ___
```

后果：`c_embedded` 蜂窝每一格的腰行斜杠方向都反，相邻格连起来读成 `\ TRIG●─\ ECHO●──  LCD/`（该 pane 的 docstring 自称这处几何“第一版就修过”）。
修法：上半部循环只写到 `i < r`（或把最宽行单独写一次）。

**F-21｜C 语言 pane：越界红格永不出现；`addr` 由屏幕列推出；格子框重叠。**
`school_courses.py:395-404` `for i in range(n): col = RED if (over and i == step)`，而 `over = step >= n` → `i == step` 永不成立；实测 step∈{14,15,16} 的 25 帧里整屏 RED 格数 = **0**（该 pane 的 docstring 卖点正是“the red cell past the end”）。
`:406` `addr 0x{k.bx0 + step*4:04X}`：地址 = 屏幕列（渲染得 `0x0009`），换布局/窗口即变。
`:401-403` 三宽格框以 2 格步距画 → `┌─┌─┌─`、`└─└─└─`；两位下标连成 `910111213`。
修法：`(over and i == 0)` 之外再画一个越界格；地址用固定基址（如 `0x7FFC`）+ 索引；格距改 3 或用 `┬` 连成一条带。

**F-22｜红黑树 pane 的计数/形状自相矛盾（窄窗或堆叠分支时）。**
`school_courses.py:1202-1205` `depth` 会从 3 降到 2（真实尺寸即如此）→ 只画 `keys[:7]`，而 `:1233` 的计数写 `插入 {done:2d}/15`（`done` 最大 15）；`:1289-1309` `_ds_shapes` 声称“同一组键，两种形状”，实际链画 6 个点、平衡树画 7 个点（`xs` 有 7 项）；`:1207` `lit = set((0,1,4)[:…])` 是“search 8”的路径，但 8 的节点下标是 11，未包含。
修法：计数改成 `len(keys[:n_nodes])`，平衡树去掉第 7 个点，`lit` 补 11。

**F-23｜深度学习 pane 没有计算图。**
`school_courses.py:1050-1056` 反向只是 `k.put(..., y + (1 if c % 3 else -1), "\\" if c % 2 else "/")`；docstring（`:1024-1028`）称“the red edges are the gradient flowing back through the same graph the blue edges carried activations forward”，而图中没有边/节点。
`:1047-1049` 的绿点是 `sin` 轨迹，不在 loss 曲线上。
修法：画出 3–5 个节点与边（前向蓝、反向红），或把 docstring 改成“loss 曲线 + 梯度符号”。

**F-24｜boot log 与设计规则冲突；`PROT_START` 晚 2.25 s。**
`05_歌词会话对照_v2.md:13` “02:10.74 的 `Illegal arguments` 之前，一句专业课都不许出现”、`:39` 第一幕“完全禁止”，并且把 v1 的“Arduino 接线”列为违规样例；而 `school_machine.BOOT_LOG`（`school_machine.py:59-74`）在 0.84–2.78 s 打了 14 行 UNO/ATmega/HC-SR04/LCD1602/I2C/GPIO。
`school_machine.py:77` `PROT_START = 3.58` 声称是“protection 那一句唱完之后”，但 `Remember to put on protection` 在 1.33（`01_歌词分析.md:57`），3.58 是 `Lay down your pieces`；原片自己的 `film_panels.py:264 PROT_START = 1.313`。
修法：把 boot log 的器件行改成不点课程名的自检（或按规则移到 02:10.74 之后）；`PROT_START = 1.33`。

**F-25｜章节条漏掉 P5 互换，末段合并 P7c+P8+P9；docstring 写 09/关机。**
`school_machine.py:28-39` 的 10 项按 `01_歌词分析.md §1` 对：P1 29.28 ✓、P2 44.04 ✓、P3 58.65 ✓、P4 73.53 ✓，但 P4 在 88.34 结束、`P5 互换`（88.34–103.03）没有条目，条上仍显示 `05 / 万物皆点`（这 14.7 s 的 pane 是 switch 母题：quantize/chladni/fork_bomb/lattice/moire）；`09 / 软工与爱` 从 162.23 一路到片尾（49.8 s），`P9 关机`（205.56）无章节。
`school_machine.py:9` 的 docstring 示例写 `09 / 关机`，与 `:38` 数据不符（批次 4 记录 `04_验证记录/批次4_机器身份与全曲右栏.md:16` 定的就是 `09 / 软工与爱`）。
修法：docstring 同步；若要贴曲式，补一条 `88.34 / 互换`。

### 低

**F-26｜计数器口径不一：课程页 `EXEC nn/15`（14 门课 + 1 个非课程 pane）vs docstring/批次 8 记录的 `/14`；四张 AI 页全是 `EXEC 01/04`。**
`school_panels.py:597-598` 传 `total=len(EXEC_PANES)`（15），`school_courses.py:2184` 注释写“the `EXEC n/14` counter”，`04_验证记录/批次8_专业段.md:20` 的例子是 `EXEC 06/14`；`school_courses.py:2504` `draw_ai(..., run: int = 1)` → 四页都 `01`（`ll.2503-2511` 未接收 `run`）。
修法：`total=14`（或把 powerdown 排除在分母外）；`draw_ai` 由 `school_scenes` 传 `run`。

**F-27｜数据流图：流名压掉加工框左上角；`教师` 外部实体画了两次。**
`school_courses.py:463` `k.put(k.bx0+ew+2, y, flow, …)` 的 6 格 `源代码` 正好覆盖 `:454` 画在 `px` 的 `╭`（渲染行 3 为 `┌─ 学生 ───┐ 源代码────╮`，缺 `╭`）；`:444` 与 `:484` 各画一个 `教师`。
修法：标签移到流线下方一行；右侧的教师框去掉或改成“教务系统”。

**F-28｜工业软件 pane：真实尺寸下爆炸视图少一个零件；视口几乎空白；BOM 表头粘连。**
`school_courses.py:1137-1138` `room = max(0,(k.bh-2)//3)` 在右侧栏高 15 时 = 4 → `parts[:4]`，而 BOM（`:1103-1107`）有 5 行、`⑤密封圈` 不画；`:1082-1097` 视口只有 4 个 `·` 与 4 个斜线；`:1114` `_pad("件号",4)+_pad("名称",11)` 无间隔 → 表头读作 `件号名称`。
修法：`room` 至少 5（或缩到每件 2 行）；视口画真实棱边；表头加 1 格间距。

**F-29｜B+ 树的键域与查询条件矛盾。**
`school_courses.py:894-928`：内部键 `i*137`（i=0..3 → 0/137/274/411）与叶键 `i*137`（i=0..leaves-1 → …1507），而计划里的条件是 `id = 41827`（`:881`）→ 树里没有这个键；内部键只复用了前 4 个叶键，12 个叶子中 8 个没有路由键；`:919-922` 的扇出插值渲染成一排反斜杠。
修法：键域覆盖 41827（如按 `41827//n` 生成分隔键），并把内部键改成叶块首键。

**F-30｜LCS 表行列标签各错一格。**
`school_courses.py:1399` 表头写在 `bx0+4`，`:1408` 单元格写在 `bx0+4+j*2` → 第 j 列的值落在第 j 个字母（`b[j]`）下面；`:1401` 行标 `a[j]` 在 `by0+3+j`，`:1408` 数据行 `i` 在 `by0+3+i` → i=1 的数据画在 `a[1]` 那一行（渲染可见 `W  1 1 1…`，首行 `N` 无数据、末行无标签）。
修法：单元格改 `bx0+2+j*2`，数据行改 `by0+2+i`。

**F-31｜`draw_gauge` / `_gauge_live` 不可达 → 倒数词与采样游标永不上屏。**
`school_panels.py:597` 先调 `draw_course`，而 `_CO.COURSES`（`school_courses.py:1751-1756`）**包含六个 `pane_gauge_*`** → `draw_course` 直接返回 True，`:600` 的 `draw_gauge` 永不执行。
后果：`draw_gauge` 的 `digit`/`lang`（`:2149-2150`）从未被传参 → 屏上没有 `ein/dos/trios/ne/fem/liu`；`_gauge_live` 的“采样游标”也没有；六个仪表拿到底条 `_activity`（`seed=run=0`，六者同相），只有 `pane_gauge_fem` 因在 `LIVE` 里拿到 blink。
修法：把六个 gauge 从 `COURSES` 移除，或在 `draw_course` 前先试 `draw_gauge`，并把 `digit/lang` 从 `GAUGE_SLOTS` 传下去。

**F-32｜`_dev/pane_probe.py` 的尺寸已与实况不符（113×36 vs 97×30），这正是 F-6/F-7 没被发现的原因。**
`pane_probe.py:30-31` `(113,36)` 注释为“the pane as the layout now gives it”；实测 197×52 下 pane 为 97×30。
修法：把 197×52 真实矩形加进 `SIZES`（或由 `T.draw` 量出后写回）。

**F-33｜若把 F-1 修正，课程 pane 之间仍不足 1.3 s，而源码注释声称不会。**
`school_panels.py:80-83` 与 `school_courses.py:10-12` 称“让两个短击点共用一个 pane，避免 <1.3 s”；实测（当前排程）每个 `pane_exec_*` 只有 0.635 s 或 0.825 s，`_split` 已无调用者（`grep _split` 只有定义）。
修法：改注释（或真的合并到 12 个 pane）。

**F-34｜AI 扩散 pane 的箭头方向与去噪方向相反。**
`school_courses.py:2437-2438` `k.put(x0+size*cell+2, …, "\u2190", …)`，而面板顺序是 t=2（纯噪声，左）→ t=0（干净，右）。
修法：改成 `\u2192`。

**F-35｜若干 docstring/注释与数据不符（不影响画面，但会被后续审计当依据）。**
`school_courses.py:1-21`（“fourteen drawings”/“one course per hit”）、`:835`（“two's-complement multiplication”，实为无符号）、`:551`（“dashed”，实为实线）、`:1505-1509`（burndown “ideal line is straight and grey”）、`:1538-1539`（pareto 有累计线）；`school_panels.py:124`（“Fourteen courses and six instruments” 与 `_exec_rows` 实测 15 门+6）、`:2184`（`/14`）。
修法：逐条改注释。

**F-36｜`school_fx.py` 的校徽字幕仍是错字（不在我的模块内，父级已列，此处仅确认它确实上屏）。**
`_dev/out/audit/timeline.md:45` `整屏层：3.60-5.10 flash name='crest' caption='公诚勇毁'`、`:900` `emerge name='crest' caption='公诚勇毁'`（正确为 `公诚勇毅`，U+6BC5）。我核到 `school_panels.py` 的两处**已在本轮 11:05 被改对**（见下）。
修法：`school_fx.py:1691/1755` 的 `\u6bc1` → `\u6bc5`（父级负责）。

---

## 字符核对（承接父级清单）

`school_panels.py` / `school_machine.py` 用“屏上字符 − 全项目 md 正文”筛出的集合为空；
`school_courses.py` 筛出的 20 余字逐条核对如下，**全部是语境中的真词**（给出完整字符串）：

| 字符 | 位置 | 屏上完整字符串 | 判定 |
|---|---|---|---|
| 钢 | `school_courses.py:1103` | `("01", "端盖", "45 钢", "1")` | 真词（45 钢） |
| 沟 / 栓 | `:1104` `:1106` | `("02", "深沟球轴承", "GCr15", "2")` / `("04", "螺栓 M8", "Q235", "6")` | 真词 |
| 腈 | `:1107` | `("05", "密封圈", "丁腈", "2")` | 真词（丁腈橡胶） |
| 竞 | `:1544` | `labels = ["空指针", "越界", "竞态", "内存", "精度", "其他"]` | 真词（竞态=race condition） |
| 申 | `:1785` | `("malloc / free", "堆内存，谁申请谁释放")` | 真词 |
| 泄 | `:1792` | `("valgrind", "内存泄漏检查器")` | 真词 |
| 耦 | `:1821` `:1830` | `("coupling / cohesion", "低耦合，高内聚")` / `("inheritance", "继承：复用，也制造耦合")` | 真词 |
| 瀑/捷/敏 | `:1823` | `("waterfall / agile", "瀑布与敏捷，顺序与迭代")` | 真词 |
| 踩 | `:1833` | `("design pattern", "设计模式：别人踩过的坑")` | 真词（踩过的坑） |
| 斥 | `:1855` | `("semaphore", "信号量：同步与互斥")` | 真词 |
| 斯 | `:1866` | `("Booth", "布斯算法：带符号乘法")` | 真词（Booth=布斯） |
| 冗 | `:1876` | `("normal form", "范式：拆表消除冗余")` | 真词 |
| 碑 | `:1888` | `("milestone", "里程碑：可交付的检查点")` | 真词 |
| 蔓 | `:1890` | `("scope creep", "范围蔓延：需求慢慢长大")` | 真词 |
| 孪 | `:1919` | `("digital twin", "数字孪生：先算后造")` | 真词 |
| 温/锐 | `:2471` | `("temperature", "温度：调权重的锐度")` | 真词 |
| 涂 | `:2490` | `("forward process", "加噪：一步一步涂黑")` | 真词 |
| 听 | `:2498` | `("CFG scale", "提示词强度：听话到什么程度")` | 真词 |
| 闲 | `school_motifs.py:567`（画在我 scope 的 pane 内） | `"← 整理后：空闲连成一整块"` | 真词 |
| 碗 | `school_scenes.py:1064`（父级给的是 :1062，行号已漂移） | `"从地里到碗里只剩一半"` | 真词 |

**本轮已修复（无需再动）**：`school_panels.py` 校徽 ops 与校训 ops —— 当前 `:231` `ops=["\u6821\u5fbd","1938"]`（校徽，U+5FBD ✓）、`:233` `["\u6821\u5fbd","1938","\u516c\u8bda\u52c7\u6bc5"]`（公诚勇毅，U+6BC5 ✓）。
我在 10:5x 读到的旧版确实是 `\u5fbe`（徾）与 `\u6bc1`（毁），11:05:45 的编辑已改对；父级清单里的 `school_panels.py:228/230` 行号是旧版的，现为 `:231/:233`。
（`school_panels.py` 之外我未做字符全量扫描；`school_fx.py` 不在我的模块内。）

---

## 无法判定

1. **F-1 的 10.00 s 是否曾经是有意为之**：全部设计文件（`02b §4.2`、`04_验证记录/批次2_课图与仪表.md:60-62`、`批次28_去重与专业.md:61`）都把仪表锚在“三个数字”上，没有找到“把仪表提前到 Execution 段”的记录；但也无法排除某个未入库的口头决定，故按缺陷报。
2. **pane 真实尺寸只量了 197×52**（`批次8` 记录的参考窗口）：F-6/F-7/F-28 是“97×30 下如此”。更宽的窗口（如左右不互换或加大窗口）下 `columns()` 可能通过，内容会回来；我没有逐尺寸复算。
3. **章节条里 `05 / 万物皆点` 覆盖 P5 互换**：`批次4` 记录的十条标签里本来就没有“互换”，所以这是设计层的取舍还是漏项，我按曲式缺口报告，无法判断是否已被接受。
4. **`FLAGS`/`R1`/`R2` 是否有意当作“机器在动的假寄存器”**：`批次8` 记录的示例（`R1=AB R2=52`）与该公式吻合，说明是有意做成会动的；但“与高亮指令无关”这一点没有任何文件说明，故仍记为缺陷。
5. **`fork_bomb` 的“九代”是否另有计数口径**（例如按“分裂轮次”从 8 代起算）：按 `2**gen` 的代码口径，4096 只能是第 12 代。
6. **`school_fx.py` 的 `公诚勇毁` 是否也已在 11:05 那一轮被改**：该文件不在我的模块内，我只确认 `timeline.md:45/900` 的字幕是错的（timeline 是旧版生成物，可能已过期）。
7. **两张图（ds 的像素排序、os 的 fork 炸弹）在 `bh≥26` 时是否真的画对**：我在 113×36 下看到它们出现，但只做了“是否出现”的检查，没有逐格核对母题自身的不变量。
