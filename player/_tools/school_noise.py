"""噪声场：值噪声 / fbm 内核，以及它接在画面上的三种用法。

## 为什么是这一层

把两个参考仓库 grep 完的结论（见 `增强方向.md` §二）：`world.execute-me-ascii-main` 的 3,073 行
`scenes.py` 里**没有** plasma / fbm / 任何抖动（`plasma|fbm|perlin|dither|Bayer|metaball|voronoi|
mandel|raymarch` 只命中 5 处，且全是 `zbuf` 与 ramp）；本项目现在背景里的"纹理感"也全靠手写的
点阵与一次性 `_noise(i, r, c, n)` 函数。**噪声场是两个仓库共同的空白**，而终端里
`ramp × fbm` 的视觉冲击远大于它在像素渲染器里的样子。

## 三条纪律（都是这个项目already用过的，照搬）

  * **零 RNG、零状态**：随机性全部来自一个整数哈希（`hash16` 式，murmur 的 finalizer）。
    于是整个场是 `(x, y, t)` 的纯函数，可确定性重放、可 `--snapshot` 定格调试、可逐帧 diff 回归。
    `rehash()` 只在"想要另一个场"时改种子，不参与动画。
  * **整数运算做主循环**：值噪声的四个角和插值都在整数/定点上做，最后才转浮点。
  * **每帧一次整屏 numpy，不逐格 Python**：10,244 格的逐格循环在这个项目里就是 5–9 ms
    （见 `_dev/probe_frame_profile.py`）。这里的目标是**每帧 ≤ 2 ms**。

## 三种用法

    field(x, y, t)      环境底噪：ramp(值) → 字符，作为安静段落与转场时的"背景质感"
    warp(shape, t)      扰动量：给现有 pane 的坐标加一个 fbm 偏移（火在烧 / 水在流 / 信号在抖）
    threshold(x, y, p)  溶解/显影 mask：`fbm < p` 一个表达式同时得到数据填屏、溶解、显影

## 成本（`_dev/probe_noise_cost.py`，197×52，多轮中位数）

| 倍频数 | `tick`（整屏 numpy） | `field`（写进缓冲） | 合计 |
|---|---|---|---|
| 1 | 0.54 ms | 0.50 ms | **1.04 ms** |
| **2（默认）** | 1.08 ms | 0.45 ms | **1.53 ms** |
| 3 | 1.61 ms | 0.42 ms | 2.03 ms |

另加 `quantile_field`（等频化，只在场重算之后做一次）0.74 ms。

**倍频数是唯一影响成本的旋钮**（它线性决定哈希次数）；`scale` 只改变场的"块大小"，
可以按观感自由选。默认 2 倍频是为了留在 2 ms 预算内——3 倍频的细节更多，代价是刚好越线。

两处"想当然会更快、实测更慢"的记录，都写在 `field` 的 docstring 里：
把写缓冲的循环换成 numpy 向量化 + argsort 分组是 **3.48 → 7.98 ms**（更慢），
因为最后一步写 `list[list[tuple]]` 必然是 Python，而在它之上套 numpy 是净加开销。

## 用法

    nz = Noise(cols, rows, seed=7)
    ...
    nz.tick(t)                  # 每帧一次：算好这个时刻的场（整屏 numpy）
    nz.field(ramp, colour, s, box)      # 把场画成字符进缓冲
    m = nz.threshold(p)         # 或取一个布尔掩码交给调用方

它**不属于默认路径的任何一层**：默认关闭，由调用方按帧预算决定开不开。
"""
from __future__ import annotations

import numpy as np

#: `ramp` 的默认取值：10 档，两端各留一格空白，让场能"淡出到没有"。
RAMP = " .:-=+*#%@"

#: 底噪的基色——**已经调暗过一次**（批 94）。
#:
#: 原值是 `(120, 150, 190)`，而它乘上场值之后**最亮的一格是 `(60, 75, 95)`、luma 73.3
#: = 正文的 34.5%**（`_dev/probe_noise_bright.py` 实测）。那个亮度正压在页脚
#: （`ui(0.55)`，34.9%）上、还比 chrome 元素（`ui(0.62–0.8)`，41–50%）亮，
#: 于是底纹读起来像"内容"——这就是"噪点太亮"的实质。
#:
#: 现在这个值比原值暗一档（`_dev/probe_palette_ladder.py` 的换算：要让最亮格落到正文的
#: 20%，基色约 `(69, 87, 110)`），而且这个是一个**可直接改的调色板事实**：
#: 想更暗就往下调，`tui_live.NOISE_GAIN` 是它的第二个旋钮。
BASE_COLOUR = (69, 87, 110)

#: 每帧算几个倍频。1 个是纯值噪声（平滑的云），3 个是 fbm（有细节的云）。
#: **默认 2**：它是"留在 2 ms/帧预算内"的那个值（3 倍频实测 2.03 ms，刚好越线）。
OCTAVES = 2

#: 倍频之间的频率与幅度比。
LACUNARITY = 2.0
GAIN = 0.5


def hash_field(x: np.ndarray, y: np.ndarray, seed: int) -> np.ndarray:
    """一个确定性的整数哈希 → [0, 1) 的浮点场。

    murmur3 的 finalizer：三次异或-乘法-移位，雪崩性质够好，纯整数运算、无查表，
    所以能直接跑在 numpy 数组上。**这是整层唯一的随机源**——没有 `random`、没有状态。
    """
    h = (x.astype(np.uint32) * np.uint32(0x27D4EB2D)
         ^ y.astype(np.uint32) * np.uint32(0x165667B1)
         ^ np.uint32(seed & 0xFFFFFFFF))
    h ^= h >> np.uint32(15)
    h *= np.uint32(0x2C1B3C6D)
    h ^= h >> np.uint32(12)
    h *= np.uint32(0x297A2D39)
    h ^= h >> np.uint32(15)
    return (h >> np.uint32(8)).astype(np.float32) / np.float32(1 << 24)


def value_noise(fx: np.ndarray, fy: np.ndarray, seed: int) -> np.ndarray:
    """值噪声：格点上取哈希值，格内双线性插值（带 smoothstep 缓和）。

    `fx`/`fy` 是浮点的格坐标（已经除以频率），返回同形状的 [0, 1] 场。
    """
    x0 = np.floor(fx).astype(np.int64)
    y0 = np.floor(fy).astype(np.int64)
    tx = (fx - x0).astype(np.float32)
    ty = (fy - y0).astype(np.float32)
    # smoothstep：3t²-2t³。比线性插值少一层"网格感"，代价是两次乘法
    tx = tx * tx * (np.float32(3.0) - np.float32(2.0) * tx)
    ty = ty * ty * (np.float32(3.0) - np.float32(2.0) * ty)

    c00 = hash_field(x0, y0, seed)
    c10 = hash_field(x0 + 1, y0, seed)
    c01 = hash_field(x0, y0 + 1, seed)
    c11 = hash_field(x0 + 1, y0 + 1, seed)
    top = c00 + (c10 - c00) * tx
    bot = c01 + (c11 - c01) * tx
    return top + (bot - top) * ty


def fbm(fx: np.ndarray, fy: np.ndarray, seed: int, octaves: int = OCTAVES,
        lacunarity: float = LACUNARITY, gain: float = GAIN) -> np.ndarray:
    """分数布朗运动：多个倍频的值噪声叠加，幅度按 `gain` 递减。返回值大致落在 [0, 1]。"""
    out = np.zeros(fx.shape, dtype=np.float32)
    amp = np.float32(1.0)
    total = np.float32(0.0)
    f = np.float32(1.0)
    for i in range(max(1, octaves)):
        out += amp * value_noise(fx * f, fy * f, seed + i * 1013)
        total += amp
        amp *= np.float32(gain)
        f *= np.float32(lacunarity)
    return out / total


#: fbm 的实际输出带。叠加多个倍频会把值往中间收（中心极限），所以它**不会**用满 [0,1]：
#: 实测 3 个倍频只到 0.118..0.801，1 个倍频到 0.005..0.967。这个常数是对 3 倍频量出来的，
#: 用途是把输出拉回满量程（见 `contrast`）。
FBM_BAND = (0.10, 0.85)


def contrast(f: np.ndarray, band: tuple[float, float] = FBM_BAND) -> np.ndarray:
    """把 fbm 的输出拉回满量程 [0, 1]。

    **这不是美化，是功能性的**：`ramp` 的两端（`' '` 与 `'@'`）如果永远取不到，
    整个场就只剩中间几档，看起来是一层均匀的灰雾而不是"有亮有暗的纹理"；
    而且 `threshold(p)` 在小 p 时会返回空掩码（实测 p=0.2 覆盖 0%），
    那会让"溶解"这类用法在最该有反应的区间失效。

    拉伸是单调的，所以**不会改变形状**，只改变对比度——场的形态、可复现性、
    以及"t 变了场才变"这些性质都保持。
    """
    lo, hi = band
    out = (f - np.float32(lo)) / np.float32(hi - lo)
    return np.clip(out, 0.0, 1.0)


class Noise:
    """一个整屏的噪声场，按 `(x, y, t)` 求值。"""

    def __init__(self, cols: int, rows: int, seed: int = 7, scale: float = 14.0,
                 octaves: int = OCTAVES, drift: float = 0.35,
                 stretch: bool = True) -> None:
        self.cols, self.rows = cols, rows
        self.seed = int(seed)
        self.scale = float(scale)          # 一格屏幕坐标跨越多少个噪声格：越大越"大块"
        self.octaves = int(octaves)
        self.drift = float(drift)          # 每秒钟场往下漂多少格（让它"在流"）
        self.stretch = bool(stretch)       # 是否把输出拉回满量程（见 `contrast`）
        self.cur: np.ndarray | None = None
        self._quant: np.ndarray | None = None
        self._q_for: np.ndarray | None = None      # 分位表是为哪一帧的场算的
        #: 准静态图案的缓存（见 `field` 的 `period`）：[(y, x, 字符, 亮度), ...]
        self._pat: list | None = None
        self._pat_box: tuple | None = None
        self._pat_t = -1e9
        self._pat_checked = 0
        self.t = 0.0
        self._grid(0.0)

    def _grid(self, t: float) -> None:
        ys, xs = np.mgrid[0:self.rows, 0:self.cols]
        self._fx = xs.astype(np.float32) / np.float32(self.scale)
        # 纵向漂移：同一个场在往下走，读起来像"表面在流"而不是"整块在闪"
        self._fy = (ys.astype(np.float32) + np.float32(t * self.drift)) / np.float32(self.scale)
        self._t = t

    def resize(self, cols: int, rows: int) -> None:
        if (cols, rows) != (self.cols, self.rows):
            self.cols, self.rows = cols, rows
            self.cur = None
            self._grid(self.t)

    def tick(self, t: float, seed_offset: int = 0) -> np.ndarray:
        """算这个时刻的整屏场。返回 (rows, cols) 的 float32。

        **`t` 每帧都在变，所以场每帧都会重算**——这是有意的：`field` 的颜色强度要每帧连续。
        但**图案**不该跟着每帧重建，那由 `field` 的 `period` 单独控制（它的时间戳是
        `self._pat_t`，与这里无关）。第一版在这里把图案缓存清掉，于是 `period` 完全不起作用
        （每帧都判定为"需要重建"），实测成本一点没降——`_dev/probe_noise_ab.py` 把它抓了出来。
        """
        self.t = float(t)
        if (self.cur is None or abs(t - self._t) > 1e-9 or seed_offset):
            self._grid(t)
            f = fbm(self._fx, self._fy, self.seed + seed_offset * 7919, self.octaves)
            self.cur = contrast(f) if self.stretch else f
            self._q_for = None
        return self.cur

    # ------------------------------------------------------------------ 用法一：底噪

    def field(self, screen, ramp: str = RAMP, colour=None, box=None,
              level: float = 0.5, floor: float = 0.12, period: float = 0.0,
              stride: int = 1, gain: float = 1.0) -> int:
        """把场按 `ramp` 画成字符进缓冲。

        `floor` 是"低于这个亮度就不画"的门槛——终端里一格淡到看不见的字就是脏点，
        和 `fx_trail` 的 `TRAIL_MIN`、余晖层的 `MIN_LEVEL` 是同一个道理。

        **`colour` 不给就用 `BASE_COLOUR`，`gain` 再乘一次**（批 94）。两个旋钮分两层：
        基色是"噪点是什么颜色"（一个调色板事实，放在这里），`gain` 是"这次画多暗"
        （一个强度决定，由调用方给）。调用方改 `gain`，不需要知道基色是多少。

        **为什么"调暗"要用 `gain` 而不是 `level`**：实测量过，`level=0.5` 与 `level=1.0`
        的**峰值亮度完全一样**（都是 luma 73.3）——因为峰值那格 `v≈1`，`k = v * level`
        只在 `level<1` 时压它，而它本来就在顶端。真正决定"最亮那格有多亮"的是基色。

        **调多暗是按项目自己的调色板定的**（`_dev/probe_palette_ladder.py`）：正文 `UI`
        luma 212.5 记作 100%，页脚 `ui(0.55)` 是 **34.9%**、chrome 元素在 `0.62–0.8`
        （41–50%）。噪点原来最亮到 **34.5%**——正压在页脚上、还比 chrome 亮，
        所以它读起来像"内容"而不是"底纹"。底纹必须比所有文字都暗，于是取 **20%**
        （`NOISE_GAIN` 的默认值，见 `tui_live`）。

        **`stride` 是这一层真正的成本旋钮，`period` 只解决了一半。** 实测（真实画面，
        `draw + render_diff` 多轮中位数，`_dev/probe_noise_total.py`）：

            stride=1  period=0.25     +7.13 ms/帧   （其中 `render_diff` 只占很小一部分：
                                      终端流只多 12 KB/帧，所以钱花在画格子上）

        代价的来源是"每帧要重刷约 4,000 个格子"，而不是求值场（场只要 0.5-1.3 ms）。
        底噪是一层**纹理**，纹理不需要每格都有：`stride=2` 让一个字符代表 2×2 格，
        成本按 stride² 掉，而观感上只是纹理粗一点——对"pane 之间空隙里的暗部质感"这个用途
        完全够。`period` 控制图案多久重建一次（准静态），`stride` 控制图案有多密。

        **`period` 还顺手修了一个观感错误**：`period=0`（每帧按当前场重画）会让这 4,000 格
        每帧都变，读起来是噪点在闪，不是表面在流——一层"缓慢流动的底噪"不该每帧重写四成屏幕。
        这和 `tui_live.fx_trail` 那条"按 dt 步进而非按帧重画"是同一个道理。
        """
        f = self.cur
        if f is None:
            return 0
        if colour is None:
            colour = BASE_COLOUR
        _g = max(0.0, float(gain))
        if _g != 1.0:
            colour = (colour[0] * _g, colour[1] * _g, colour[2] * _g)
        n = len(ramp) - 1
        x0, y0, x1, y1 = box if box else (0, 0, self.cols - 1, self.rows - 1)
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(self.cols - 1, x1), min(self.rows - 1, y1)
        cr, cg, cb = int(colour[0]), int(colour[1]), int(colour[2])
        stride = max(1, int(stride))

        # ---- 图案：每隔 period 秒重建一次，其余帧直接用上一次的 ----
        fresh = (self._pat is None or self._pat_box != (x0, y0, x1, y1, stride)
                 or abs(self.t - self._pat_t) >= period or period <= 0.0)
        if fresh:
            cells = []
            for y in range(y0, y1 + 1, stride):
                frow = f[y]
                row = screen.buf[y]
                for x in range(x0, x1 + 1, stride):
                    if row[x][0] != " ":
                        continue             # 底噪是背景，不许盖掉任何内容
                    v = float(frow[x])
                    if v < floor:
                        continue
                    ch = ramp[int(v * n)]
                    if ch == " ":
                        continue
                    cells.append((y, x, ch, v))
            self._pat = cells
            self._pat_box = (x0, y0, x1, y1, stride)
            self._pat_t = self.t
        else:
            cells = self._pat
            # 复用图案时不再求值场、也不再逐格比较亮度；只确认这些格子现在还是空的
            # （中间可能有文字压上来），颜色按当前的 `level` 重刷——所以观感上仍然是
            # "亮度每帧连续变化、图案缓慢流动"。

        k = float(level)
        drawn = 0
        for y, x, ch, v in cells:
            cell = screen.buf[y][x]
            if cell[0] != " ":
                continue
            kk = v * k
            screen.buf[y][x] = (ch, (int(cr * kk), int(cg * kk), int(cb * kk)), cell[2])
            drawn += 1
        return drawn

    # ------------------------------------------------------------------ 用法二：扰动

    def warp(self, dx: float, dy: float, strength: float = 1.0):
        """返回一个 `(x, y) -> (dx, dy) 格` 的偏移查表，供调用方给自己的坐标加抖动。

        场的空间梯度就是"往哪边偏"：梯度大的地方偏得多，于是视觉上像被什么推着走，
        而不是整块平移。
        """
        f = self.cur
        if f is None:
            return None
        gy, gx = np.gradient(f)
        return (gx * np.float32(dx * strength), gy * np.float32(dy * strength))

    # ------------------------------------------------------------------ 用法三：阈值 mask

    def threshold(self, p: float) -> np.ndarray:
        """`fbm < p` 的布尔掩码：一个表达式同时得到数据填屏、溶解、显影。

        它是 `(x, y, t)` 的纯函数，所以同一个 `p` 画出来的形状可复现——
        这一点对"逐帧 diff 回归"很关键（`_dev/ansi_probe.py` 就是靠它）。

        **`stretch` 打开时先把场等频化，再比较。** 直接比较是错的：fbm 的值按中心极限分布
        堆在中间（实测 p=0.2 时覆盖 0%，因为场的最小值就有 0.25），于是"溶解"在它最该有反应的
        低区间完全没反应。等频化把值换成它在这一帧场里的**分位**，`p` 就等于覆盖率，
        一个阈值从 0% 均匀走到 100%。代价是一次 argsort（10,244 个 float32，约 0.6 ms），
        而且只在场重算时做一次。
        """
        f = self.cur
        if f is None:
            return np.zeros((self.rows, self.cols), dtype=bool)
        v = self.quantile_field() if self.stretch else f
        return v < np.float32(p)

    def order_key(self) -> np.ndarray:
        """一个整屏的"出场顺序"：每格的分位（0 = 最先出现，1 = 最后）。

        **溶解用它，而不是每帧调 `threshold`。** 转场需要的是"每一格有它自己的出场时刻"，
        有了这张表，`p` 从 0 走到 1 就是一次完整溶解，而且同一个 `p` 永远是同一批格子
        ——这正是逐帧 diff 回归需要的可复现性（`_dev/ansi_probe.py` 靠它）。

        与 `threshold` 共用同一张分位表，所以额外成本是零。

        **为什么不用 `threshold(t)`（把时间塞进场）**：场每帧重算，格子的出场顺序就会每帧变，
        转场会读成噪点在闪而不是"画面在一片片地换"。出场顺序必须**在一个转场里固定**。
        """
        return self.quantile_field()

    def quantile_field(self) -> np.ndarray:
        """把当前场换成它在自己内部的分位（等频化），使任意 `p` 的覆盖率都等于 `p`。

        分位是用**当前帧的场**算的，所以这是一个"经验 CDF"而不是理论分布——
        对溶解/显影这类"按比例露出"的用法，这正是想要的语义。
        """
        f = self.cur
        if f is None:
            return np.zeros((self.rows, self.cols), dtype=np.float32)
        if self._q_for is f:
            return self._quant
        flat = np.sort(f.reshape(-1))
        # 每个值在排序数组里的位置 / 总数 = 它的分位，用 searchsorted 一次算完
        rank = np.searchsorted(flat, f.reshape(-1), side="left")
        self._quant = (rank.astype(np.float32) / np.float32(flat.size)).reshape(f.shape)
        self._q_for = f
        return self._quant

    def stats(self) -> dict:
        f = self.cur
        if f is None:
            return dict(cells=self.cols * self.rows, mn=0.0, mx=0.0, mean=0.0)
        return dict(cells=int(f.size), mn=float(f.min()), mx=float(f.max()),
                    mean=float(f.mean()))
