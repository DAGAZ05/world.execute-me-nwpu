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

#: 三个键道。顺序就是屏幕上的左右顺序：`S` 在中间（它到"执行"段才出现）。
LANES = ("d", "j", "s")
LANE_LABEL = {"d": "D", "j": "J", "s": "S"}
#: 判定窗口，秒。用户要的是"音乐感"，所以两个窗口都取比较宽的值：
#: 严格到 ±0.05 在终端里会被键盘重复率影响，宽容到 ±0.25 又会让人觉得"怎么按都对"。
PERFECT = 0.09
GOOD = 0.20
#: 音符之间的最小间隔（秒）与全曲上限。0.45 s 略大于两个拍（0.229 s 一拍），
#: 于是"每两个拍一个音"是常态，重拍处可以连到"每拍一个"。
GAP = 0.45
MAX_NOTES = 520
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
WINDOWS: list[tuple[float, float, int]] = [
    (16.082, 131.9, 2),          # 学校部分：D J
    (147.52, 205.9, 3),          # 学院部分：S D J
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
    return any(a <= t <= b for a, b, _n in WINDOWS)


def keys_at(t: float) -> int:
    """这一时刻有几个键（0 = 不在舞台上）。"""
    for a, b, n in WINDOWS:
        if a <= t <= b:
            return n
    return 0


def lanes_at(t: float) -> tuple[str, ...]:
    n = keys_at(t)
    return LANES[:n] if n else ()

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

    `tui_live._beat_grid()` 需要 `tui_live.DATA[0]`（拟合周期与相位要读 `kick`）。
    播放器里它每帧都会被写，但在探针/单测里没有——所以这里补一次，**只在没装的时候**。
    """
    try:
        import tui_live as T
        if T.DATA[0] is None:
            T.DATA[0] = T.Data()
        return list(T._beat_grid())
    except Exception:
        return []


def chart() -> list[dict]:
    """全曲谱面：`[{t, lane}]`，按时间排序。

    规则（全部可复现）：
      * 只在 `WINDOWS` 的两段里取点（学校段 2 键、学院段 3 键），中间的选择框窗口**没有音符**；
      * 相邻两个音符至少隔 `GAP`（0.45 s）；
      * 键道按一个**确定性的哈希**分配（`lane = (i*7 + int(t*100)) % n`），并避免与上一个同键；
      * 每段的键数就是那一段的 `n`（2 或 3），不是"到某个时刻才解锁"。
    """
    grid = _beats()
    if not grid:
        return []
    out: list[dict] = []
    i = 0
    for at, end, n in WINDOWS:
        lanes = LANES[:n]
        last = -1e9
        for bt in grid:
            if bt < at or bt > end:
                continue
            if bt - last < GAP:
                continue
            k = (i * 7 + int(round(bt * 100))) % n
            lane = lanes[k]
            if out and lane == out[-1]["lane"] and n > 1:
                lane = lanes[(k + 1) % n]
            out.append(dict(t=round(bt, 4), lane=lane))
            last = bt
            i += 1
            if len(out) >= MAX_NOTES:
                return out
    return out


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
        self.combo = 0
        self.best = 0
        self.flash: tuple[float, str, str] | None = None   # (时刻, 判定, 键道)
        self.last_t = 0.0
        self.phase = 0                # 现在在第几段（0/1），以及这一段的命中
        self.phase_hit = 0

    # ---- 数值 ----------------------------------------------------------
    def score(self) -> int:
        return 2 * self.perfect + self.good

    def max_score(self) -> int:
        return max(1, 2 * self.total)

    def pct(self) -> float:
        return 100.0 * self.score() / self.max_score()

    def phase_of(self, t: float) -> int:
        for i, (a, b, _n) in enumerate(WINDOWS):
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
        """把已经过去、没人按的音符结算成 `MISS`。每帧调用。"""
        ph = self.phase_of(t)
        if ph != self.phase and ph >= 0:
            # 换段：连击归零（中间隔了十六秒的选择框），但分数累计
            self.combo = 0
            self.phase = ph
        if t < self.last_t - 0.5:                 # 回退/跳转：不追判，直接对齐
            self.used = sum(1 for n in self.notes if n["t"] < t - GOOD)
            self.combo = 0
        self.last_t = t
        while self.used < self.total and self.notes[self.used]["t"] < t - GOOD:
            note = self.notes[self.used]
            self.used += 1
            if note.get("done"):
                continue
            self.miss += 1
            self.combo = 0
            self.flash = (t, "MISS", note["lane"])

    def key(self, ch: str, t: float) -> bool:
        """吃下 `d`/`j`/`s` 吗？只有面板在舞台上、而且那个键道是活的才吃。"""
        if not live(t):
            return False
        k = ch.lower()
        if k not in LANES or not self.lane_is_live(k, t):
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
        # `used` 只在 `tick` 里推进（它管的是"过期结算"），所以这里不移动它
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
        if not (lane_x0 <= x <= lane_x1):
            continue
        yy0 = lane_y[ln]
        near = 1.0 - _clamp(abs(dt) / GOOD, 0.0, 1.0)
        #: 颜色：远 = 主题蓝 ×1.2（亮蓝），近 = 暖白。第一版从 `mix(me_text, 0.5)` 起，
        #: 实测最暗格 (58,71,121) 比正文还暗。
        far = tuple(min(255, int(v * 1.2)) for v in me_text)
        col = _grad(far, (255, 246, 190), near) if not note.get("done") else ui(0.30)
        ch = "\u2588" if not note.get("done") else "\u2591"
        for r in range(nrow):
            yy = yy0 + r
            if yy >= judge_y:
                break
            for k in range(3):
                if x + k <= lane_x1:
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
    big = f"{g.score()} / {g.max_score()}   {g.pct():.1f}%"
    cx = w // 2
    # **画在"在铸剑吗？"那一句下面**：`draw_black` 把那个问题打在屏幕下部的输入框里
    # （`py = y0 + h - 4`），光标与 token 号在它下面两行。总分放在问题**上方**两行，
    # 谁也不盖谁——第一版放在屏幕正中，用户说"总得分显示位置错误"。
    cy = max(2, y1 - 9)
    # **只用字体真的有的字符**：`—`（U+2014）在渲染器里是缺字方框，换成 ASCII 的 `-`。
    rows = [(cy, "WORLD.EXECUTE(ME) - complete", ui(0.8)),
            (cy + 1, big, (255, 246, 190)),
            (cy + 2, f"PERFECT {g.perfect}   GOOD {g.good}   MISS {g.miss}   "
                     f"best combo {g.best}", mix(me_text, 0.9)),
            (cy + 3, line, (180, 255, 200)),
            (cy + 4, sub, ui(0.62))]
    for yy, text, col in rows:
        if not (0 <= yy < getattr(s, "rows", 10 ** 6)):
            continue
        width = 0
        for ch in text:
            width += 2 if ord(ch) > 0x2E80 else 1
        s.put(max(0, cx - width // 2), yy, text, col)
