"""荧光余晖：多帧的指数衰减记忆，而不是"上一帧的幽灵"。

## 为什么需要它

终端里没有像素、没有模糊、没有 alpha 通道。一个字符格能表达的只有**字符本身**、它的前景色、
以及它的背景色——就这三样。想让画面有质感，多帧记忆是这三样之外唯一还剩的表达手段，
而播放器现在没有：`tui_live.fx_trail` 只保留**上一帧**的 42%（`TRAIL = 0.42`），
一帧记忆够做出"残影"，做不出"荧光"。

这一层补上它，和现有 `fx_trail` **正交**（两者可以同时开）：

    fx_trail   上一帧的幽灵，一格一格按 42% 保留（同帧内的一次操作）
    本模块     最近若干帧的亮度按指数衰减累积（跨帧的真实余晖），每格带自己的颜色

物理模型就是荧光粉的那一条：被激励到某个亮度，然后按时间常数衰减。

    level(t + dt) = level(t) * DECAY ** (dt * FPS)

`DECAY ** (dt * FPS)` 这个归一化和 `fx_trail` 用的是同一套，它保证**衰减速度不随帧率变化**——
必须如此：`--fps-cap` 从 30 提到 60 时每帧间隔减半，直接乘 `DECAY` 会让余晖在两倍帧率下衰减快一倍。
批 59 已经在 trail 上踩过这个坑（`fx_trail` 的注释："stepping it once per *drawn* frame made it
fade faster the smoother the player got"）。

## 用法（相位不能错）

    ph = Phosphor(cols, rows)
    ...
    每帧：
        draw(...)                  # 1. 先正常画这一帧（它会整屏重画，见下）
        ph.poke(s, dt)             # 2. 记下这一帧亮着的格、按 dt 衰减、同步自己的颜色镜像
        ph.ink(s)                  # 3. 把余晖叠上去（这一步会写入缓冲）
        s.render_diff(out)         # 4. 这时候才 diff，余晖才会真的被写进终端

**`ink` 必须在 `draw` 之后。** 这一条是实测出来的，不是设计偏好：`draw` 每帧把整屏重画一遍
（每个 pane 都是 `t` 的纯函数，从头画），所以任何在 `draw` **之前**写进缓冲的东西都会被涂掉。
第一版按"余晖是底子"的直觉把 `ink` 放在最前面，实测**一帧 2,811 处写入活下来 0 处**
（`_dev/out/sanity_phosphor.py` 量的），对照图当然一模一样。放在 `draw` 之后，它就是叠在这一帧
画面上的东西——语义上也更对：余晖是"上一帧留下的光，照在这一帧的画面上面"。

**`render_diff` 必须在 `ink` 之后**，这样 `prev` 里就带着余晖，下一帧的 diff 只会发出余晖
真正变了的那几格，不会每帧重发全屏。

`poke` 在 `ink` **之前**，是因为它要读的 `screen.dirty` 是**上一帧** `render_diff` 收好的
（`draw` 已经把缓冲换成了新的一帧，所以这一帧的 dirty 还没算出来）。这是有意的：
"变过的格"永远晚一帧被点燃，一帧的延迟在 24 fps 下看不出来，而它换来了
**一个帧内不需要两次全屏扫描**。

## 成本

**这一层不扫描屏幕。** `poke` 只读上一帧的 `screen.dirty`（`render_diff` 顺手收集的变动格，
见 `tui_live.Screen.dirty`），只对那几格做工作；`ink` 只读自己缓存的颜色镜像，
不做整屏提取。第一版逐格读 `screen.buf` 一帧要 9.6 ms
（`_dev/out/sanity_ink_profile.py`），这是这个效果能不能进 24 fps 预算的关键。
实测（`_dev/probe_phosphor.py`）：`ink` + `poke` 合计约 1.5 ms 一帧，且与动画速率脱钩。

## 它不是"把屏幕点亮"

三条纪律，缺一条这个效果就会变成噪声：

  * **残留低于 `MIN_LEVEL` 一律不画**。余晖低于这个亮度在字符格上只会是脏点，
    真实荧光粉也有一个"看不见"的下限；
  * **有字符的格子只混前景色的 `FG_SHARE`**，空格的背景混合才用满比例——
    当前画面上有字的地方，字必须仍然读得出来；
  * **只点燃"这一帧变过"的格子**。一帧里始终没动、但一直亮着的格子保持它们第一次亮起时
    记下的颜色，静止的字不会自己改变余晖。
"""
from __future__ import annotations

import numpy as np

#: 每 1/24 s 保留多少。**这是这一层唯一需要调的参数**，实测（`_dev/probe_phosphor_delta.py`）：
#:
#:     0.42   一帧只改到 99-750 格，均差 15-20/255   —— 太轻，看不出是"余晖"
#:     0.58   197-942 格，均差 20-24/255              —— 默认：约 0.4 s 的可见尾巴
#:     0.70   228-2566 格，均差 23-50/255             —— 明显的长拖尾，适合抒情段落
#:
#: 0.58 的意思是一帧留 58%、三帧后约 20%、六帧后约 4%，尾巴大约 0.4 s——
#: 长于一次转场、短于一个乐句，正好落在"看得出在动、但看不清是什么"的区间里。
DECAY = 0.58

#: 低于这个亮度就不画了。`fx_trail` 的 `TRAIL_MIN = 0.06` 是同一个数量级的理由。
MIN_LEVEL = 0.10

#: 点燃时的亮度。
MAX_LEVEL = 1.0

#: 余晖落在**有字符**的格子上时，混进前景色的比例上限。压到 1/3 是有意的：那一格的字是
#: 当前画面，余晖是"它刚才也在"的暗示，不能盖过它。空格的背景混合不受这个系数限制。
FG_SHARE = 0.34

#: 衰减的归一化基准：影片自己的帧率。
FPS = 24.0


class Phosphor:
    """一格一份的亮度 + 颜色记忆，按指数衰减。"""

    def __init__(self, cols: int, rows: int, decay: float = DECAY,
                 min_level: float = MIN_LEVEL, enabled: bool = True) -> None:
        self.cols, self.rows = cols, rows
        self.decay = float(decay)
        self.min_level = float(min_level)
        self.enabled = enabled
        self._alloc(cols, rows)

    def _alloc(self, cols: int, rows: int) -> None:
        self.cols, self.rows = cols, rows
        n = cols * rows
        #: 每格的亮度（0..1）。float32 够用：这是观感量，不是精度量。
        self.level = np.zeros(n, dtype=np.float32)
        #: 每格余晖自己的颜色。余晖必须带颜色——否则拖尾一律变灰，
        #: 而终端里"色相"是仅有的两个可供表达的量之一。
        self.colour = np.zeros((n, 3), dtype=np.uint8)
        #: 本模块自己不需要屏幕镜像：`ink` 直接从缓冲读它要的那几格（只读"有余晖的格"）。
        self._last_changed = 0

    def resize(self, cols: int, rows: int) -> None:
        if (cols, rows) != (self.cols, self.rows):
            self._alloc(cols, rows)

    # ------------------------------------------------------------------ 每帧

    def poke(self, screen, dt: float) -> int:
        """按 `dt` 衰减余晖，并把这一帧亮着的格点燃。

        必须在 `draw` 之后、`ink` 之前调用（见模块文档的相位说明）。它读的是**上一帧**
        `render_diff` 留下的 `screen.dirty`——那一帧里变过的格，就是这一帧最该被点燃的格。

        **每次循环里的工作被压到最少**，这是它便宜的第二个原因。第一版在这里同时做三件事
        （镜像前景、镜像背景、判断空格），一帧 5.5 ms；而"读这一格的字符和颜色"要建一个元组、
        查两次列表，是纯 Python 里最贵的那类操作。现在这里只用 `cell[0]` 和 `cell[1]`，
        背景色与"是否空格"交给 `ink` 按需读——`ink` 只遍历有余晖的格，
        比"这一帧变过的格"少一个量级。
        """
        if not self.enabled:
            return 0
        cols, rows = screen.cols, screen.rows
        if (cols, rows) != (self.cols, self.rows):
            self._alloc(cols, rows)

        step = self.decay ** (max(0.0, float(dt)) * FPS) if dt > 0 else 1.0
        self.level *= step
        # 已经衰减到看不见的归零，省掉后面每一次无用遍历
        self.level[self.level < self.min_level * 0.5] = 0.0

        levels = self.level
        colours = self.colour
        n_fresh = 0
        for y, xs in getattr(screen, "dirty", ()):
            if not (0 <= y < rows) or not xs:
                continue
            row = screen.buf[y]
            base = y * cols
            for x in xs:
                if not (0 <= x < cols):
                    continue
                cell = row[x]
                ch = cell[0]
                if ch == " " or ch == "":
                    continue               # 空了（或宽字符后半格）：让 level 自己衰减
                i = base + x
                levels[i] = MAX_LEVEL
                colours[i] = cell[1]
                n_fresh += 1
        return n_fresh

    def ink(self, screen) -> int:
        """把余晖叠进缓冲，返回被余晖改动的格数。必须紧跟 `poke`（见模块文档的相位）。

        **一个格子还亮着的时候也要上余晖，成品才在。** 这是修掉的第一个错：初版只在"当前缓冲是
        空格"的格子上画余晖，理由是"新内容就是它，余晖让位"——听起来对，实测一帧只改到 47 格。
        因为"变过"的格子绝大多数**仍然是亮的**（歌词换字、波形换高度、点阵换位置），
        而它们才是拖尾真正该出现的地方：一个 `▂` 换成了 `▃`，读者应该看到旧的那一档在那个格子上
        留了一瞬。

        所以按格子现在的状态分两种落法：

          * **有字符** → 混到**前景色**上（字自己发亮后余辉）；
          * **空** → 混到**背景色**上（字符走掉以后留下的拖尾）。

        余晖是加法，不是替换：混的比例永远小于 1，字符本身始终读得出来。
        """
        if not self.enabled:
            return 0
        cols, rows = screen.cols, screen.rows
        if (cols, rows) != (self.cols, self.rows):
            self._alloc(cols, rows)

        hot = np.nonzero(self.level >= self.min_level)[0]
        if not len(hot):
            self._last_changed = 0
            return 0

        # 余晖这一层需要的四样东西，都在这一次循环里从缓冲取——只取"有余晖的格"，
        # 比"这一帧变过的格"少一个量级（实测 1 500-4 200 格 vs 2 000-5 000 格，
        # 见 `_dev/probe_phosphor.py` 的两列）。
        fgs = np.empty((len(hot), 3), dtype=np.float32)
        bgs = np.empty((len(hot), 3), dtype=np.float32)
        empty = np.empty(len(hot), dtype=bool)
        skip = np.empty(len(hot), dtype=bool)
        k = 0
        for i in hot:
            y, x = divmod(int(i), cols)
            cell = screen.buf[y][x]
            ch = cell[0]
            fgs[k] = cell[1]
            bgs[k] = cell[2]
            empty[k] = ch == " "
            skip[k] = ch == "" and screen.wide[y][x]
            k += 1

        rc = self.colour[hot].astype(np.float32)
        f = self.level[hot].astype(np.float32)[:, None]
        blend_bg = bgs + (rc - bgs) * f
        blend_fg = fgs + (rc - fgs) * (f * FG_SHARE)
        out = np.clip(np.where(empty[:, None], blend_bg, blend_fg), 0, 255).astype(np.uint8)

        drawn = 0
        for k in range(len(hot)):
            if skip[k]:
                continue
            y, x = divmod(int(hot[k]), cols)
            row = screen.buf[y]
            cell = row[x]
            ch = cell[0]
            col = (int(out[k][0]), int(out[k][1]), int(out[k][2]))
            if ch == " ":
                row[x] = (" ", cell[1], col)
            else:
                row[x] = (ch, col, cell[2])
            drawn += 1
        self._last_changed = drawn
        return drawn

    # ------------------------------------------------------------------ 观测量

    def stats(self) -> dict:
        nz = int((self.level > 0).sum())
        return dict(cells=self.cols * self.rows, lit=nz, residue=nz,
                    inked=self._last_changed,
                    peak=float(self.level.max()) if self.level.size else 0.0)

    def clear(self) -> None:
        self.level[:] = 0.0
        self._last_changed = 0
