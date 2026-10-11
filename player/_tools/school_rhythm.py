"""音游面板（批 98）：谱面、判定、计分、绘制。

用户的要求原话：

> 我希望加一个 音游 panel（music，显示当前得分，正确错误数），可以适当缩短 stdout panel 的高度
> （放在你认为合适的位置）用户需要操作的按键仅 D、J，这个放在学校部分；在学院部分歌词开始
> execution 后，操作键变为 S、D、J 三个，最后结束界面中央显示总得分，并根据得分区间写一句评价。
> 设计这个主要是为了增加区分度，当前的增强实在不明显。

所以这个模块要回答四件事，每一件都必须**可复现**（同一首歌同一时刻的谱面永远一样）：

1. **谱面从哪来**：不从随机数来，也不从"跟着歌词"来——从 `tui_live.beat()` 那张**拟合出来的
   节拍网格**来（0.458 s ≈ 131 BPM，451 个点）。那一句是这一版自己算的，所以谱面是这一版
   独有的东西，而不是"另一份拍点表"。
2. **按键**：`D` / `J` 两个；`执行` 段开始后加入 `S`（三个）。按键的所有权遵循 `school_gate`
   立下的规矩——**只在面板真的在舞台上时才吃键**，其余时间一律交回播放器。
3. **判定**：以**歌内时间**（`t`）为准，不用挂钟——暂停时 `t` 不走，于是暂停不会把谱面跑掉。
   `PERFECT ±0.09 s` / `GOOD ±0.20 s`，更远就是没按（`MISS` 在音符过期后结算）。
4. **计分与评价**：`score = 2*perfect + good`，满分 `2*N`，用**百分比**显示；
   结束界面的评语按区间给（见 `VERDICTS`）。

这个模块**不 import `tui_live`**（会成环）：需要播放器的 `ui`/`mix` 就自己接一套小的，
几何由调用方给（`draw` 的矩形来自 `tui_live`，那里才是布局的唯一副本）。
"""
from __future__ import annotations

import math
import os
from pathlib import Path

#: 三个键道，**顺序就是屏幕上的上下顺序**。批 99：用户要求学院段"三键顺序由上至下分别改为 SDJ"，
#: 所以学校段是 `D`(上) `J`(下)，学院段是 `S`(上) `D`(中) `J`(下)。
LANES = ("d", "j")
LANES3 = ("s", "d", "j")
LANE_LABEL = {"d": "D", "j": "J", "s": "S"}
#: 判定窗口，秒。用户要的是"音乐感"，所以两个窗口都取比较宽的值：
#: 严格到 ±0.05 在终端里会被键盘重复率影响，宽容到 ±0.25 又会让人觉得"怎么按都对"。
PERFECT = 0.09
GOOD = 0.20
#: 音符之间的最小间隔（秒）与全曲上限。
GAP = 0.45
MAX_NOTES = 520
#: **谱面的音乐参数**（批 100，见 `chart`）。第一版调出来 251/273 全是"重音"、长按只有 6 个——
#: 因为 `kick` 的中位数就有 0.42，等于没有筛选。现在改成**分层密度**：
#:
#:   * `loud < LOUD_LO`（安静）→ 16 分网格上**每 4 格**才可能落一个（约 0.458 s 一个）；
#:   * `LOUD_LO ≤ loud < LOUD_HI` → **每 2 格**（约 0.229 s）；
#:   * `loud ≥ LOUD_HI`（高潮）→ **每格**（0.114 s，最密）。
#:
#: 落点还要过 `TAP_KICK`（那一拍的 kick 够强）——所以安静段落自然稀疏、鼓点密集处自然密。
#: 这就是用户要的"根据音乐节奏变化"。
LOUD_LO, LOUD_HI = 0.38, 0.66
#: 三档的 kick 门槛（**越响要求越低**，见 `chart.kick_need`）。
KICK_LO, KICK_MID, KICK_HI = 0.34, 0.20, 0.10
BEAT_LOUD = 0.70
#: 长按：**落在稀疏的地方**（前后 0.80 s 没有别的音符），长度取到下一个音符之前，
#: 限制 0.35–1.20 s。这样"按住多久"跟音乐里那一段的留白一致，而不是随机数。
HOLD_GAP = 0.80
HOLD_MIN, HOLD_MAX = 0.35, 1.20
HOLD_LOUD = 0.42
#: 长按出现概率（只在符合条件的稀疏落点上，所以实际比例会低于它）。
HOLD_PCT = 0.55
#: 长按松手的容差（秒）：比尾巴早这么多松就算"断"。
HOLD_RELEASE = 0.18
#: 面板高度（行）：**按当前有几个键决定**。用户的要求："我让你学院部分增加music panel高度，
#: 容纳3个键位，你完全没改"——3 键那一段面板更高，并且每个键道有 **2 行**（音符是"厚块"，
#: 单行 1 格的点在滚动时读不出来）。
PANEL_H_BY_KEYS = {2: 6, 3: 8}
#: 每个键道占几行。
LANE_ROWS = {2: 2, 3: 2}
#: 面板的舞台窗口（见 `WINDOWS`）。
#: **它在哪两段舞台上**（批 98b，用户的口径）：
#:
#:   * 第一段（学校部分）：`3/2/2/RUN` 那段结束之后开始 —— 那是 `SIM_END = 16.082`；
#:     到**学院选择框出来之前**结束 —— 那是 `school_gate.GATE_AT = 131.9`（窗口 5 s，
#:     所以 131.9 起面板就退场，选择框是这一段的唯一焦点）。
#:   * 第二段（学院部分）：歌词 `Execution` 开始之后 —— `EXEC_AT = 147.52`；
#:     到**航小天全身跃动结束**（`WHALE_FALL_START` 之前的最后一拍，取 206.5），
#:     然后整屏变黑（`BLACK_START = 207.083`）。
#:
#: 中间 131.9–147.52 的十六秒面板**不在舞台上**：不画、不吃键、不记分（用户要求）。
#:
#: **批 99 又把学院段拆成两半**：
#:   * `174.90–177.50` 是原片的 `shot_collapse`（整屏收成一条线、再收成一点；
#:     `school_fx.emerge` 的注释写着这一段 "the school variant draws no pane behind it"）。
#:     屏幕上实测 ink 掉到 **841**（176.14–176.89）——用户："学院部分中间有一处全局变黑框，
#:     music panel在那里也要减除"。所以这一段面板退场。
#:   * 学院段的**终点 = 航小天跳跃结束**：`stand`（全身像）事件 193.60–199.00，
#:     取 199.40 作为落地余量（用户："学院部分应在航小天跳跃结束时结束"）。
COLLAPSE = (174.90, 177.50)
WINDOWS: list[tuple[float, float, int, tuple[str, ...]]] = [
    (16.082, 131.9, 2, LANES),          # 学校部分：D J
    (147.52, COLLAPSE[0], 3, LANES3),   # 学院部分（collapse 之前）
    (COLLAPSE[1], 199.40, 3, LANES3),   # 学院部分（collapse 之后）：到跳跃结束
]
EXEC_AT = 147.52
#: 面板从这一刻开始出现（前奏那 16 秒只有 logs，让人先看完开场）。
START_AT = WINDOWS[0][0]
#: **总分只在最后那一屏出现**（批 98d，用户："我让你仅显示在最后结尾包含'在铸剑吗'的画面"）。
#: 那一屏是 `draw_black`：`T_SLIDE = 208.3125`，滑动 0.5 s，打字 0.9 s
#: （`film_panels.SLIDE / TYPE_GAP / TYPE_DUR`），所以"在铸剑吗？"在 **209.86** 打完。
#: 总分从 210.2 起显示到全曲结束（`END = 211.9`）。
RESULT_AT = 210.2
FINISH_AT = 211.9


def panel_h(t: float) -> int:
    """面板这一刻的高度（行）：2 键 6 行、3 键 8 行。"""
    return PANEL_H_BY_KEYS.get(keys_at(t), PANEL_H_BY_KEYS[2])


def result_live(t: float) -> bool:
    """结算画面在不在（只有最后那一屏）。"""
    return RESULT_AT <= t <= FINISH_AT


def live(t: float) -> bool:
    """这一时刻面板在舞台上吗？"""
    return any(a <= t <= b for a, b, _n, _l in WINDOWS)


def keys_at(t: float) -> int:
    """这一时刻有几个键（0 = 不在舞台上）。"""
    for a, b, n, _l in WINDOWS:
        if a <= t <= b:
            return n
    return 0


def lanes_at(t: float) -> tuple[str, ...]:
    """这一刻的键道，**顺序就是屏幕上的上下顺序**。

    学校段 `("d","j")`；学院段 `("s","d","j")`——用户批 99 的要求
    "学院部分三键顺序由上至下分别改为 SDJ"。
    """
    for a, b, _n, lanes in WINDOWS:
        if a <= t <= b:
            return tuple(lanes)
    return ()

#: 评语区间（百分比下限 -> 主句、副句）。主句写在中央大位置，副句在下一行。
VERDICTS: list[tuple[float, str, str]] = [
    (95.0, "全对。你把整个宇宙都执行了。",
     "机器没有出错，你也没有——这一遍可以拿去当基准。"),
    (85.0, "很准。节拍在你手上。",
     "该抓的重拍都抓住了，漏的那几个不影响它是一次完整的演出。"),
    (70.0, "稳。航小天在替你数拍子。",
     "有几处抢了一点、有几处晚了一点，但整首歌的骨架你撑住了。"),
    (50.0, "一半一半。像这台机器刚上电。",
     "意识是后来才到的，剩下的部分你已经知道该在哪儿使劲。"),
    (25.0, "没关系，第一次执行就是这样。",
     "点数不全也能跑，先把这一遍看完——机器不会因为你按错就停下。"),
    (0.0, "执行完成。",
     "分数只是这一遍的痕迹；真正的部分是你把它听完了。"),
]


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


# ---------------------------------------------------------------------- 谱面

def _beats() -> list[float]:
    """节拍网格（来自 `tui_live`，那里是唯一算它的地方）。

    `tui_live._beat_grid()` 需要 `tui_live.DATA[0]`（拟合周期与相位要读 `kick`）。播放器里它每帧
    都会被写，但在探针/单测里没有——所以这里补一次，**只在没装的时候**。

    **`Game()` 会在第一帧 `draw()` 之前构造**（批 98g 的真机 bug）：那时 `DATA[0]` 还是 `None`，
    第一版的 `_fit_beat_grid()` 拿到空网格又被缓存，于是整首谱面 0 个音符
    （真机 stderr 的 `music panel: 0 notes`；探针因为先设了 `DATA[0]` 看不到）。
    修法在 `tui_live._beat_grid`：空网格不缓存。这里再加一道保险——拿到空表就把数据装上重问一次。
    """
    try:
        import tui_live as T
        if T.DATA[0] is None:
            T.DATA[0] = T.Data()
        grid = list(T._beat_grid())
        if not grid:
            T._BEATS[0] = None
            grid = list(T._beat_grid())
        return grid
    except Exception:
        return []


def chart() -> list[dict]:
    """全曲谱面：`[{t, lane, kind, dur}]`，按时间排序。

    **批 100 按音游的做法重做**（用户："音符你都是固定的，这不符合音游的要求，正常来讲音游应该是
    根据音乐节奏等变化的，也分长按、短按"）。第一版是"在节拍网格上等间隔取点、全是最短单点"，
    于是读起来像节拍器而不是谱面。现在的三条规则：

    1. **基础密度跟 `kick` 走**：音符落在 **16 分网格**（一拍的四分之一，0.114 s）上，但
       **是否出现**由那一拍的 `kick` 决定（`TAP_KICK`）——安静段落自然稀疏、鼓点密集处自然密。
    2. **长按跟"持续的响"走**：`hold` 的出现要 `loud > 0.40`，长度由 `_hold_len` 从
       `loud` 的**连续段**量出来（0.30–1.40 s）。长按期间不再生成其它音符，所以谱面不重叠。
    3. **轻重区分**：`kind` 由 `loud` 给——`tap`（普通）与 `beat`（重音），判定相同、
       **画法不同**（重音更亮更厚），读谱时看得出"这一下要用力"。
    """
    grid = _beats()
    if not grid:
        return []
    try:
        import tui_live as T
        d = T.DATA[0]
    except Exception:
        d = None
    if d is None:
        return []
    iv = sorted(b - a for a, b in zip(grid, grid[1:]))
    beat = iv[len(iv) // 2] if iv else 0.458
    step = max(0.10, beat / 4.0)          # 16 分网格，从节拍网格推出来（与 E3 的切点同源）
    out: list[dict] = []

    def tap_at(t: float, lane: str, kind: str) -> None:
        out.append(dict(t=round(t, 4), lane=lane, kind=kind, dur=0.0))

    def kick_need(loud: float) -> float:
        """这一刻"多强才算一个音符"。**越响要求越低**——所以高潮段落会出现连打。

        第一版对三档用了同一个阈值，结果 232/307 的间隔都是 0.458 s（等于只有 L2 那一档真的在出音符）：
        `kick` 的强拍每两拍才来一次。响应度（`loud`）高的时候把门槛降下来，密度才真的分层。
        """
        if loud >= LOUD_HI:
            return KICK_HI
        if loud >= LOUD_LO:
            return KICK_MID
        return KICK_LO

    for at, end, n, lanes in WINDOWS:
        i = 0
        t = at
        while t <= end and len(out) < MAX_NOTES:
            loud = d.feat(t, "loud")
            kick = d.feat(t, "kick")
            slot = int(round(t / step))
            dens = 1 if loud >= LOUD_HI else (2 if loud >= LOUD_LO else 4)
            if slot % dens == 0 and kick >= kick_need(loud):
                h = (slot * 2654435761 + 7919) & 0xFFFF
                lane = lanes[(i * 5 + (h >> 3)) % n]
                if out and lane == out[-1]["lane"] and n > 1:
                    lane = lanes[(lanes.index(lane) + 1) % n]
                nxt = _next_gap(d, t, end, step, lanes, n)
                if (h % 100) < (HOLD_PCT * 100) and loud >= HOLD_LOUD and nxt >= HOLD_GAP:
                    # **长度取这一段空白的一半**，并限制在 0.35–1.20：太长会把下一拍压掉，
                    # 而且第一版取 `nxt - step` 时所有长按都顶到上限（实测中位=最大=1.20，没有变化）。
                    dur = min(HOLD_MAX, max(HOLD_MIN, 0.5 * nxt))
                    out.append(dict(t=round(t, 4), lane=lane, kind="hold", dur=round(dur, 4)))
                    i += 1
                    t = t + dur                     # 长按期间不出别的音符
                    continue
                tap_at(t, lane, "beat" if loud >= BEAT_LOUD else "tap")
                i += 1
            t += step
    return out


def _next_gap(d, t: float, end: float, step: float, lanes, n: int) -> float:
    """从 `t` 往后，下一个"可能落音符"的时刻离它多远（秒）。

    用它来决定长按能有多长：**长度是这一段留白的一半**，所以"按住多久"对应音乐里真实的空白。
    只看密度分层与 `kick` 阈值，不递归调用 `chart`。
    """
    t2 = t + step
    while t2 <= end:
        loud = d.feat(t2, "loud")
        dens = 1 if loud >= LOUD_HI else (2 if loud >= LOUD_LO else 4)
        need = KICK_HI if loud >= LOUD_HI else (KICK_MID if loud >= LOUD_LO else KICK_LO)
        if int(round(t2 / step)) % dens == 0 and d.feat(t2, "kick") >= need:
            return t2 - t
        t2 += step
    return end - t


# ---------------------------------------------------------------------- 状态

class Game:
    """一次播放的音游状态。**唯一的可变状态**，暂停/回退都不影响它的正确性：
    判定只读 `t`，而 `t` 是歌内时间。

    两段舞台（`WINDOWS`）合计成**一份**成绩单：每一段的满分是那一段的音符数，最终界面的总分与
    评价按两段合起来算（用户要的是"最后结束界面中央显示总得分"）。段与段之间（选择框那 16 秒）
    不画、不吃键、不记分。
    """

    def __init__(self) -> None:
        self.notes = chart()
        self.total = len(self.notes)
        self.used = 0                 # 已经结算过的音符下标
        self.perfect = 0
        self.good = 0
        self.miss = 0
        self.hp = 0                   # 长按尾巴**松早了**（丢了那 1 分）
        self.htail = 0                # 长按尾巴**按住了**（拿到那 1 分）
        self.combo = 0
        self.best = 0
        self.flash: tuple[float, str, str] | None = None   # (时刻, 判定, 键道)
        self.last_t = 0.0
        self.phase = 0                # 现在在第几段（0/1），以及这一段的命中
        self.phase_hit = 0
        self.held: dict[str, int] = {}   # 键道 -> 正在按着的长按下标

    # ---- 数值 ----------------------------------------------------------
    def score(self) -> int:
        """**一个音符最高 2 分**，但长按的 2 分是"头 1 + 尾 1"，而尾巴是**额外的记账项**。

        | 事件 | 分 | 计入 |
        |---|---|---|
        | `tap`/`beat` 接住（PERFECT / GOOD） | 2 / 1 | `perfect` / `good` |
        | `hold` 头接住（PERFECT / GOOD） | 2 / 1 | `perfect` / `good` |
        | `hold` 尾巴按住 | +1 | `htail` |
        | `hold` 尾巴松早了 | 0 | `hp` |

        所以 `max_score = 2 × (tap+beat 数) + 2 × hold 头数 + 1 × hold 数`，**每个音符最多 2 分**。

        这一段改了三次，每次都靠探针里的"准点自动玩家"抓到：第一版 `hp` 也当 2 分加
        （长按全断 = **102.1%**）；第二版尾巴记在 `good` 里，而 `good` 与 `perfect` 是**互斥**的
        两套记账，于是同一个长按变成"1 个音符位、2 分记账"（**101.2%**，`hit rate 401/385`）。
        现在三个计数互不重叠，`_dev/rhythm_score_debug.py` 会逐条印出每一分来自哪个事件。
        """
        return 2 * self.perfect + self.good + self.htail

    def hits(self) -> int:
        """**接住过**的音符个数（头那一分拿到了）。用于 `hit rate` 那一行。

        不能把"松早了的长按"算进来（它们头接住了、尾巴没有），那会让 `hit rate` 报出
        401/385（比音符总数还多）。所以这里只数 `perfect + good` 覆盖到的音符。
        """
        return min(self.total, self.perfect + self.good)

    def max_score(self) -> int:
        """满分：每个音符 2 分，长按的尾巴再多 1 分（所以 hold 一共 3 分）。"""
        holds = sum(1 for n in self.notes if n.get("kind") == "hold")
        return max(1, 2 * self.total + holds)

    def pct(self) -> float:
        return 100.0 * self.score() / self.max_score()

    def phase_of(self, t: float) -> int:
        for i, (a, b, _n, _l) in enumerate(WINDOWS):
            if a <= t <= b:
                return i
        return -1

    def verdict(self) -> tuple[str, str]:
        p = self.pct()
        for lo, line, sub in VERDICTS:
            if p >= lo:
                return line, sub
        return VERDICTS[-1][1], VERDICTS[-1][2]

    def lane_is_live(self, lane: str, t: float) -> bool:
        return lane in lanes_at(t)

    # ---- 判定 ----------------------------------------------------------
    def tick(self, t: float) -> None:
        """每帧调用：结算过期的音符，并检查正在按着的长按有没有被松早了。"""
        ph = self.phase_of(t)
        if ph != self.phase and ph >= 0:
            # 换段：连击归零（中间隔了十六秒的选择框），但分数累计
            self.combo = 0
            self.phase = ph
        if t < self.last_t - 0.5:                 # 回退/跳转：不追判，直接对齐
            self.used = sum(1 for n in self.notes if n["t"] < t - GOOD)
            self.combo = 0
            self.held.clear()
        self.last_t = t
        # **长按的尾巴**：按着不放，一直走到 `t + dur` 才算完整；松开由 `key` 处理（松早了）。
        # "按够了"也要结算一次（把尾巴那 1 分给上），走的是同一个 `release`，所以它自带去重。
        for lane, idx in list(self.held.items()):
            note = self.notes[idx]
            if t >= note["t"] + note["dur"]:
                self.release(lane, note["t"] + note["dur"])
        while self.used < self.total and self.notes[self.used]["t"] < t - GOOD:
            note = self.notes[self.used]
            self.used += 1
            if note.get("done"):
                continue
            self.miss += 1
            self.combo = 0
            self.flash = (t, "MISS", note["lane"])

    def key(self, ch: str, t: float) -> bool:
        """吃下 `d`/`j`/`s` 吗？只有面板在舞台上、而且那个键道**这一刻是活的**才吃。

        **校验必须问 `lanes_at(t)`，不能问 `LANES`**（批 100 的 bug）：`LANES` 是学校段那两道
        `("d","j")`，学院段多出来的 `s` 被 `k not in LANES` 挡在外面——表现是"s 道的音符
        （tap/beat/hold 都算）一个都不计分"，那个键按下去只有"空按"。
        `_dev/rhythm_s_lane_debug.py` 是把这一条钉出来的工具。
        """
        if not live(t):
            return False
        k = ch.lower()
        if k not in lanes_at(t):
            return False
        best_i, best_d = -1, 1e9
        # 只在"还没结算 + 在窗口内"的音符里找最近的，且键道要对得上
        for i in range(self.used, self.total):
            note = self.notes[i]
            if note.get("done"):
                continue
            dt = note["t"] - t
            if dt > GOOD:
                break
            if note["lane"] != k or abs(dt) > GOOD:
                continue
            if abs(dt) < best_d:
                best_i, best_d = i, abs(dt)
        if best_i < 0:
            # 窗口内没有这个键道的音符：记一次空按（不算错，但打断连击？——不打断，
            # 因为"多按"在音游里通常是中性行为，惩罚它会让新手很快放弃）
            self.flash = (t, "空按", k)
            return True
        note = self.notes[best_i]
        note["done"] = True
        if best_d <= PERFECT:
            self.perfect += 1
            self.flash = (t, "PERFECT", k)
        else:
            self.good += 1
            self.flash = (t, "GOOD", k)
        self.combo += 1
        self.best = max(self.best, self.combo)
        # **长按**：按下就算拿到头（分数已给），尾巴归 `release` / `tick` 管
        if note.get("kind") == "hold":
            self.held[k] = best_i
            self.flash = (t, "HOLD", k)
        # `used` 只在 `tick` 里推进（它管的是"过期结算"），所以这里不移动它
        return True

    def release(self, ch: str, t: float) -> bool:
        """松键。**只有长按需要它**：松早了扣掉半分并断连击；正常松手什么都不用做。"""
        k = ch.lower()
        idx = self.held.get(k)
        if idx is None:
            return False
        # **先摘掉**：`release` 会被调用两次（自动重复的松开、`tick` 的"按够了"），
        # 摘除必须在去重检查**之前**，否则第二次提前 return 时这一项永远留在 `held` 里，
        # 于是每一帧都重复结算（实测"准点"779→786，G 9→16）。
        del self.held[k]
        note = self.notes[idx]
        end = note["t"] + note["dur"]
        # **尾巴只结算一次**（`rel` 标记）。没有它，同一次长按会被记两遍——
        # 实测"准点"跑出 102.1%、hit rate 401/385（比音符数还多）。
        if note.get("rel"):
            return True
        note["rel"] = True
        if t < end - HOLD_RELEASE:
            # **松早了**：头那一分已经给了（在 `key` 里），尾巴这一分没有。
            self.hp += 1
            self.combo = 0
            self.flash = (t, "断", k)
        else:
            # 按到了尾巴：那 1 分记在 `htail`（**不能记进 `good`**——`good` 与 `perfect` 是互斥的
            # 两套记账，记进去就等于同一个长按拿了两份"音符分"，满分会爆）
            self.htail += 1
            self.combo += 1
            self.best = max(self.best, self.combo)
            self.flash = (t, "OK", k)
        return True


# ---------------------------------------------------------------------- 绘制

def _grad(c1, c2, k: float):
    return tuple(int(round(a + (b - a) * k)) for a, b in zip(c1, c2))


def draw(s, x0: int, y0: int, x1: int, y1: int, t: float, g: Game,
         ui, mix, me_text, bg, anom) -> int:
    """画面板。返回画了多少格（调用方只用于报告）。

    布局（宽 `w = x1-x0+1`，2 键 6 行 / 3 键 8 行）：

        ┌─ music ─────────────────────────────── 2 keys  D J ─┐
        │  D   ▏          ██            ██                     │   ← 每个键道 2 行
        │      ▏          ██            ██                     │
        │  J   ▏   ██                                          │
        │      ▏   ██                                          │
        │  ──────────────────────── 判定线 ──────────────────  │
        └──────────────────────────────────────────────────────┘

    **场上只有舞台，没有成绩单**（批 98d）：总分/命中/连击只在最后那一屏出现
    （`draw_final`，用户："我让你仅显示在最后结尾包含'在铸剑吗'的画面"）。
    场上保留的只有"最近一次判定"那一个词（PERFECT/GOOD/空按/MISS），它是玩法反馈不是成绩。
    """
    w = x1 - x0 + 1
    if w < 24 or y1 - y0 + 1 < 5 or not live(t):
        return 0
    nkeys = keys_at(t)
    labels = lanes_at(t)
    nrow = LANE_ROWS.get(nkeys, 1)
    title = "music"
    sub = f"{nkeys} keys  " + " ".join(LANE_LABEL[x] for x in labels)
    s.box(x0, y0, x1, y1, title, 0.62, me_text)
    s.put(max(x0 + 2, x1 - len(sub) - 1), y0, sub, ui(0.55))

    # 判定线画在**框的底边那一行**（`y1`），不占内部行。第一版放在 `y1-1`，
    # 而 3 键时 S 道的第二行正好也是 `y1-1`——`if yy >= judge_y: break` 把那行整行吃掉，
    # 实测"S 行 45 有 6 格、行 46 恒为 0"（`_dev/rhythm_lane_debug.py`）。
    judge_y = y1
    body_top = y0 + 1
    lane_y = {}
    for i, ln in enumerate(labels):
        lane_y[ln] = body_top + i * nrow
    for x in range(x0 + 1, x1):
        s.set_cell(x, judge_y, "\u2500", mix(me_text, 0.62), bg)
    # --- 键道
    lane_x0 = x0 + 5
    lane_x1 = x1 - 2
    span = max(1, lane_x1 - lane_x0)
    #: 屏幕上能看到多远的音符（秒）。**必须保证"随时都有音符在屏上"**：音符间隔 0.458 s，
    #: 窗口比间隔大不了多少时会出现整屏空档（第一版 `0.9 s` 就是这样，用户看到的"完全没有音符"）。
    look = GAP * 5.0
    for ln in labels:
        yy = lane_y[ln]
        s.put(x0 + 2, yy, LANE_LABEL[ln], mix(me_text, 0.85))
    drawn = 0
    for note in g.notes:
        dt = note["t"] - t
        if dt < -GOOD or dt > look:
            continue
        ln = note["lane"]
        if ln not in lane_y:
            continue
        x = lane_x1 - int(round(span * dt / look))
        yy0 = lane_y[ln]
        near = 1.0 - _clamp(abs(dt) / GOOD, 0.0, 1.0)
        #: 颜色：远 = 主题蓝 ×1.2（亮蓝），近 = 暖白。第一版从 `mix(me_text, 0.5)` 起，
        #: 实测最暗格 (58,71,121) 比正文还暗。
        far = tuple(min(255, int(v * 1.2)) for v in me_text)
        done = bool(note.get("done"))
        kind = note.get("kind", "tap")
        bright = (255, 246, 190) if kind == "beat" else (214, 235, 255)
        col = _grad(far, bright, near) if not done else ui(0.30)
        ch = "\u2588" if not done else "\u2591"
        # **长按 = 头 + 条**（批 100）：头是 3 格厚块，条沿"来向"（右边）铺到 `t + dur` 的位置。
        # 条用 `▄`（U+2584，半块）——**`glyph_probe` 抓到过 `▬`（U+25AC）在这个渲染器里是缺字方框**，
        # 半块是已经证明能画的那一类；读谱时"要按住多久"就是这条有多长。
        if kind == "hold" and not done and note.get("dur"):
            xe = lane_x1 - int(round(span * (dt + note["dur"]) / look))
            for xx in range(max(lane_x0, xe), min(lane_x1, x + 3) + 1):
                for r in range(nrow):
                    yy = yy0 + r
                    if yy >= judge_y:
                        break
                    s.set_cell(xx, yy, "\u2584", _grad(far, (150, 190, 255), near), bg)
                    drawn += 1
        thick = 3 if kind != "beat" else 4       # 重音更厚，读谱时看得出"这一下要用力"
        for r in range(nrow):
            yy = yy0 + r
            if yy >= judge_y:
                break
            for k in range(thick):
                if lane_x0 <= x + k <= lane_x1:
                    s.set_cell(x + k, yy, ch, col, bg)
                    drawn += 1
    # --- 面板上方（框内最后一行留给判定线，所以反馈写在键道与判定线之间那段空行的左侧）
    if g.flash is not None and t - g.flash[0] < 0.5:
        word, lane = g.flash[1], g.flash[2]
        col = {"PERFECT": (255, 246, 190), "GOOD": (180, 255, 200)}.get(word, anom)
        # 反馈写在最后一个键道那一块的最下一行（键名左边有 4 格空位，正好够一个词）
        yy = min(y1 - 1, body_top + len(labels) * nrow - 1)
        s.put(x0 + 2, yy, f"{word} {LANE_LABEL.get(lane, lane)}", col)
        drawn += len(word) + 4
    return drawn


def draw_final(s, x0: int, y0: int, x1: int, y1: int, t: float, g: Game,
               ui, mix, me_text, bg, anom) -> None:
    """结束界面：中央给总分与评语（用户要求"最后结束界面中央显示总得分，并根据得分区间写一句评价"）。

    **居中是相对整块屏幕，不是相对这个框**：框只占左列（1..98），而用户要的是"中央"——
    结尾那两分钟屏幕其余部分是空的，所以整屏中心 `s.cols // 2` 才是该对齐的地方。
    （第一版按框居中，文字落在 x≈113 而不是 98，肉眼看就是偏右。）
    """
    w = s.cols if getattr(s, "cols", 0) else (x1 - x0 + 1)
    line, sub = g.verdict()
    # **两个数字各自带单位**（批 100）：用户看到 `PERFECT+GOOD+MISS ≪ 720` 时合理地怀疑数字错了——
    # 720 是**分数**（每个音符 2 分），102+129+129=360 是**音符个数**。所以总分与命中率分行写，
    # 下面那行才是逐项计数，并且写明"每音符 2 分"。
    big = f"score {g.score()} / {g.max_score()}   ({g.pct():.1f}%)   each note = 2"
    cx = w // 2
    # **画在"在铸剑吗？"那一句下面**：`draw_black` 把那个问题打在屏幕下部的输入框里
    # （`py = y0 + h - 4`），光标与 token 号在它下面两行。总分放在问题**上方**两行，
    # 谁也不盖谁——第一版放在屏幕正中，用户说"总得分显示位置错误"。
    cy = max(2, y1 - 9)
    # **只用字体真的有的字符**：`—`（U+2014）在渲染器里是缺字方框，换成 ASCII 的 `-`。
    rows = [(cy, "WORLD.EXECUTE(ME) - complete", ui(0.8)),
            (cy + 1, big, (255, 246, 190)),
            (cy + 2, f"hit rate {g.hits()} / {g.total}   ({100.0*g.hits()/max(1,g.total):.1f}%)",
             mix(me_text, 0.85)),
            (cy + 3, f"PERFECT {g.perfect}   GOOD {g.good}   MISS {g.miss}   "
                     f"hold broken {g.hp}   best combo {g.best}", mix(me_text, 0.9)),
            (cy + 4, line, (180, 255, 200)),
            (cy + 5, sub, ui(0.62))]
    for yy, text, col in rows:
        if not (0 <= yy < getattr(s, "rows", 10 ** 6)):
            continue
        width = 0
        for ch in text:
            width += 2 if ord(ch) > 0x2E80 else 1
        s.put(max(0, cx - width // 2), yy, text, col)
