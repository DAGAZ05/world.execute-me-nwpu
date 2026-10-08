"""The two places the machine still called itself by the film's names: the chapter bar and the log.

Everything else in this variant is the school's - the right-hand column, the left window, the
character. These two are the last of the film's own voice, and they are the loudest of them, because
they are the only text on screen that is *chrome*: the chapter label sits in the header next to the
clock, and the POST log fills the whole band under the chat window for the first five seconds.

    film:  00 / BOOT   01 / PRETRAIN   02 / SFT   03 / RLHF   04 / DEPLOY   ...   09 / WHALE_FALL
    school: 00 / 上电   01 / 初始化     02 / 定义   03 / 电与时间 04 / 副歌一   ...   09 / 关机

Both are pure data, which is why they live in one small file: a chapter is a `(start, label)` pair and
a log line is a `(time, status, text)` triple, exactly the shapes the player already reads, so the
player's two drawing routines did not have to change beyond asking this module instead of `film_panels`.

The chapter times are the *lyric* sections of `01_歌词分析.md` §1, not guessed: 00:29.28 is where
"If I'm a set of point" begins, 00:44.04 is "Switch my current", 00:58.65 is the first "If I can", and
so on. The one exception is 00:16.00, which is not a lyric but the first instrumental gap - the film's
own `01 / PRETRAIN` also starts at 16.0, because that is where the first real thing happens after the
boot lines and both versions need a boundary there.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- the chapter bar
#
# Ten labels in the film's own shape, `NN / 名字`. **The numbers are the film's** and this variant kept
# them: batch 49 first read the user's "改成 SW" as "stop numbering the bar" and renumbered nothing -
# the correction was "我让你改为 SW，不是让你把右上角章节序号改为 SW，而是就只是把中央图形改为 SW" - so the
# bar is as it always was and the *stamp over the flood* is what says `SW` (see `STAMP` below).
CHAPTERS: list[tuple[float, str]] = [
    (0.00, "00 / \u4e0a\u7535"),
    (16.00, "01 / \u521d\u59cb\u5316"),
    (29.28, "02 / \u5b9a\u4e49"),
    (44.04, "03 / \u7535\u4e0e\u65f6\u95f4"),
    (58.65, "04 / \u526f\u6b4c\u4e00"),
    (73.53, "05 / \u4e07\u7269\u7686\u70b9"),
    (103.03, "06 / \u4f60\u8d70\u4e86"),
    (125.33, "07 / \u975e\u6cd5\u53c2\u6570"),
    (147.52, "08 / \u6267\u884c"),
    (162.23, "09 / NPUer \u4e0e LOVE"),
]

# What the flood stamps in the middle of the screen at 02:26.2 (`tui_live.draw_flood`). The film stamps
# the *incoming chapter number* there - `07`, because `07 / EXECUTION` starts 1.16 s later - and for this
# variant the film's number is meaningless ("我的制作里开头就没有标章节号"). So the variant declares its
# own stamp instead, and `SW` is 软件学院: the same abbreviation the gate and the chat use for it.
STAMP = "SW"

# the labels the film's own code looks up by tag. `film_panels.chapter_start` is used by `her_style`
# to know when the climax has arrived; this variant answers from its own table so that a lookup cannot
# silently fall through to the film's numbers if the bar is ever moved.
CHAPTER_TAGS = {
    "EXECUTION": 147.52,
    "EVAL": 162.23,
}


# --------------------------------------------------------------------------- the POST log
#
# The band under the chat window prints a machine coming up, one line at a time, from 0.84 s. The film
# prints a GPU cluster's POST; the school prints the one this film is actually about - a board on a
# desk, with a sensor and an LCD on it. Same cadence, same status plates, same "WARN" line near the end
# (`attachment_to_user: not in policy` becomes the honesty line about the board not being wired yet).
#
# Times are the film's own (`data/timing`'s BOOT_LOG), because the lines land on the song's intro
# beats and the picture should not drift off them for the sake of different words.
BOOT_LOG: list[tuple[float, str, str]] = [
    (0.840, "OK", "power: USB 5V 0.48A"),
    (0.900, "OK", "board: UNO R3  (ATmega328P)"),
    (0.960, "OK", "clock: 16.000 MHz  crystal ok"),
    (1.020, "OK", "bootloader: optiboot 115200"),
    (1.080, "..", "mem test ........ 2048 B SRAM"),
    (1.140, "OK", "eeprom: 1024 B  clean"),
    (1.453, "OK", "i2c: LCD1602 at 0x27"),
    (1.643, "OK", "gpio: D2..D13 configured"),
    (1.833, "OK", "sensor: HC-SR04 trig/echo"),
    (2.023, "OK", "sensor: IR ranging on A0"),
    (2.213, "OK", "serial: 9600 8N1  ok"),
    (2.403, "OK", "watchdog: armed"),
    (2.593, "WARN", "hc-sr04: echo floating, wire D3"),
    (2.783, "OK", "protection: on"),
]

# the title the band's box takes once the protection line has been sung, as the film's does
PROT_START = 3.58
