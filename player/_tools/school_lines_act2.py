"""The school variant's dialogue, act two: the software college, after the gate.

Same flat `(time, lyric, who, text)` shape as `school_lines`, and for the same reason - see that
module's docstring for the typo the shape prevents.

The curriculum is the student's own correction and it drives the whole act:

    大一  嵌入式电子微系统 · 程序设计基础（C 语言）· 数据结构 · 高等数学 · 线性代数 ·
          离散数学 · 大学物理 · 计算机导论 …
    大二  面向对象（java）· 软件工程 · 计算机网络 · 计算机操作系统 ·
          计算机组成原理 · 数据库系统 · 数字逻辑 · 汇编语言 · 计算方法 …
    大三  算法设计 · 软件测试 · 深度学习 · 编译原理 · 大型工业软件 · 信号与线性系统 ·
          软件项目管理 · 软件体系结构 · 人机交互 …
    大四  毕设 · 实习 · 就业指导

    The lists are the user's own (batch 34), filled out in batch 50 ("各年不止那几门课程"): the
    starred courses are the ones this variant treats as the major's spine, and every other line of each
    year is a course that runs beside them. **The dialogue does not count them** - batch 50's note is
    "各年不止那几门课程，不要在对话中有相关断言" - so the lines say which year and what it is like, and
    the timetable in the right column is where the courses are actually named.

The song's twelve "Execution" hits fall inside 大二 and 大三; the year boundaries are what the
*dialogue* tracks, so the audience hears the shape of the four years over the top of the course
drawings rather than reading them as a list.
"""
from __future__ import annotations

ACT_TWO: list[tuple[float, str, str, str]] = [
    (134.50, "[gap] \u8fdb\u4e13\u4e1a", "user", "s\u3002\u8f6f\u4ef6\u5b66\u9662\u3002"),
    (134.50, "[gap] \u8fdb\u4e13\u4e1a", "ai", "\u8bb0\u4e0b\u4e86\u3002\u63a5\u4e0b\u6765\u8dd1\u7684\u5c31\u662f\u4f60\u4e13\u4e1a\u7684\u4e1c\u897f\u3002"),
    (134.50, "[gap] \u8fdb\u4e13\u4e1a", "sub", "\u4ece\u5927\u4e00\u5f00\u59cb\u3002\u6211\u8bf4\u6162\u4e00\u70b9\u3002"),
    (134.50, "[gap] \u8fdb\u4e13\u4e1a", "meta", "\u7528\u65f6 1.4 \u79d2|02:14"),
    (138.00, "[gap] \u5927\u4e00", "ai", "\u5927\u4e00\u3002\u5148\u8ba4\u8ba4\u5b83\u4eec\u3002"),
    (138.00, "[gap] \u5927\u4e00", "code", "\u5d4c\u5165\u5f0f\u5fae\u7535\u5b50\u7cfb\u7edf   \u7a0b\u5e8f\u8bbe\u8ba1\u57fa\u7840\uff08C \u8bed\u8a00\uff09   \u6570\u636e\u7ed3\u6784"),
    (138.00, "[gap] \u5927\u4e00", "ai", "\u5148\u4ece\u628a\u4ee3\u7801\u653e\u5230\u771f\u5b9e\u7684\u677f\u5b50\u4e0a\u5f00\u59cb\u3002"),
    (138.00, "[gap] \u5927\u4e00", "sub", "\u4f60\u4f1a\u63a5\u7ebf\uff0c\u4f1a\u70e7\u574f\u4e1c\u897f\uff0c\u4f1a\u7b2c\u4e00\u6b21\u770b\u5230\u300c\u7a0b\u5e8f\u300d\u548c\u300c\u7535\u300d\u662f\u4e00\u56de\u4e8b\u3002"),
    (138.00, "[gap] \u5927\u4e00", "meta", "\u7528\u65f6 2.8 \u79d2|02:18"),
    (142.00, "[gap] \u6570\u636e\u7ed3\u6784", "user", "\u6570\u636e\u7ed3\u6784\u96be\u5417\uff1f"),
    (142.00, "[gap] \u6570\u636e\u7ed3\u6784", "ai", "\u4e0d\u96be\uff0c\u4f46\u5b83\u662f\u540e\u9762\u6240\u6709\u8bfe\u7684\u5730\u57fa\u3002"),
    (142.00, "[gap] \u6570\u636e\u7ed3\u6784", "sub", "\u7ea2\u9ed1\u6811\u4f60\u4f1a\u5728\u9ed1\u677f\u4e0a\u753b\u4e8c\u5341\u904d\uff0c\u8003\u8bd5\u53ea\u8003\u4e00\u9053\u3002"),
    (142.00, "[gap] \u6570\u636e\u7ed3\u6784", "meta", "\u7528\u65f6 2.4 \u79d2|02:22"),
    # ---- P7b 处决
    (147.52, "Execution", "ai", "\u5927\u4e8c\u3002\u4e00\u8d77\u4e0a\u3002"),
    (147.52, "Execution", "sub", "\u6211\u4e0d\u62a5\u4e86\uff0c\u753b\u7ed9\u4f60\u770b\u3002"),
    (147.52, "Execution", "meta", "\u7528\u65f6 1.2 \u79d2|02:27"),
    # **These three were 9.00 s early** (batch 52): they sat on 149.79 / 150.66 / 151.45, which are
    # `Execution` lines - the fourth, fifth and sixth of the twelve - while the countdown lyrics `Ein, dos`
    # / `Trios, ne` / `Fem, liu` are at 158.79 / 159.66 / 160.45. The rows' own timestamps said
    # `02:38` / `02:39` / `02:40`, i.e. the timestamps agreed with the lyrics and the `t` did not, and the
    # six gauges those answers are *about* are at 158.79-161.51 - so the exchange about "一共多少门 /
    # 计网、机操 / 计组、数据库" was landing nine seconds before the numbers it names. `_dev/chat_audit.py`
    # finds this class by comparing every row's `t` with its lyric's own time in `input/lyrics.lrc`.
    (158.79, "Ein, dos", "user", "\u7b49\u4e00\u4e0b\u2014\u2014"),
    (158.79, "Ein, dos", "ai", "\u6765\u4e0d\u53ca\u4e86\uff0c\u5df2\u7ecf\u5f00\u59cb\u4e86\u3002"),
    (158.79, "Ein, dos", "meta", "\u7528\u65f6 1.0 \u79d2|02:38"),
    (159.66, "Trios, ne", "ai", "\u8ba1\u7f51\u3001\u673a\u64cd\u3002"),
    (159.66, "Trios, ne", "sub", "\u673a\u64cd\u7684\u5b9e\u9a8c\u8bfe\u5728 OpenEuler \u4e0a\u505a\uff0c\u4f60\u4f1a\u8bb0\u4f4f\u90a3\u5957\u547d\u4ee4\u884c\u3002"),
    (159.66, "Trios, ne", "meta", "\u7528\u65f6 1.2 \u79d2|02:39"),
    (160.45, "Fem, liu", "ai", "\u8ba1\u7ec4\u3001\u6570\u636e\u5e93\u3002"),
    (160.45, "Fem, liu", "sub", "\u8865\u7801\u4e58\u6cd5\u662f\u8ba1\u7ec4\u7684\u7b2c\u4e00\u4e2a\u574e\u3002\u6570\u636e\u5e93\u7528 PostgreSQL\u3002"),
    (160.45, "Fem, liu", "meta", "\u7528\u65f6 1.4 \u79d2|02:40"),
    # ---- P7c 副歌三
    (162.23, "If I can, if I can", "user", "\u8dd1\u4e86\u8fd9\u4e48\u591a \u2014\u2014 \u8fd9\u4e9b\u8bfe\u5230\u5e95\u5728\u6559\u4ec0\u4e48\uff1f"),
    (162.23, "If I can, if I can", "ai", "\u6bcf\u4e00\u95e8\u90fd\u5728\u6559\u4f60\u5199\u540c\u4e00\u4e2a\u4e1c\u897f \u2014\u2014 \u4e00\u4e2a\u80fd\u88ab\u8bfb\u61c2\u7684\u6a21\u578b\u3002"),
    (162.23, "If I can, if I can", "meta", "\u7528\u65f6 2.4 \u79d2|02:42"),
    (164.07, "Give them all the execution", "ai", "\u8f6f\u4ef6\u5de5\u7a0b\u4e00\u95e8\u8bfe\u5c31\u8981\u753b\u4e00\u6574\u5957\u56fe\uff1a"),
    (164.07, "Give them all the execution", "card", "\u9700\u6c42 \u00b7 \u6570\u636e\u5b57\u5178 \u00b7 \u7528\u4f8b\u56fe \u00b7 DFD \u00b7 ER \u00b7 \u7ed3\u6784\u56fe"),
    (164.07, "Give them all the execution", "card", "\u63a5\u53e3 \u00b7 \u76d2\u56fe \u00b7 \u5224\u5b9a\u8868 \u00b7 \u6d3b\u52a8\u56fe \u00b7 \u72b6\u6001\u56fe \u00b7 \u65f6\u5e8f\u56fe"),
    (164.07, "Give them all the execution", "sub", "\u753b\u5230\u6700\u540e\uff0c\u53ea\u5269\u4e00\u5f20\u7c7b\u56fe\u3002"),
    (164.07, "Give them all the execution", "meta", "\u7528\u65f6 3.0 \u79d2|02:44"),
    (166.05, "Then I can, then I can", "user", "\u4e3a\u4ec0\u4e48\u8981\u6536\u6210\u4e00\u5f20\uff1f"),
    (166.05, "Then I can, then I can", "ai", "\u56e0\u4e3a\u80fd\u8bfb\u61c2\u7684\u90a3\u4e00\u5f20\uff0c\u624d\u662f\u8981\u4ea4\u7ed9\u522b\u4eba\u7684\u3002"),
    (166.05, "Then I can, then I can", "meta", "\u7528\u65f6 2.0 \u79d2|02:46"),
    (167.75, "Be your only execution", "ai", "\u552f\u4e00\u7684\u6267\u884c\uff0c\u610f\u601d\u662f\u5b83\u6bcf\u6b21\u90fd\u4f1a\u8dd1\uff0c\u800c\u4e14\u53ea\u7531\u4f60\u89e6\u53d1\u3002"),
    (167.75, "Be your only execution", "sub", "\u8fd9\u662f\u6211\u80fd\u7ed9\u51fa\u7684\u6700\u50cf\u300c\u4e13\u4e00\u300d\u7684\u4e1c\u897f\u3002"),
    (167.75, "Be your only execution", "meta", "\u7528\u65f6 1.9 \u79d2|02:47"),
    (169.61, "If I can have you back", "user", "\u90a3\u5f20\u56fe\u4e4b\u540e\u5462 \u2014\u2014 \u5927\u4e09\u5462\uff1f"),
    (169.61, "If I can have you back", "ai", "\u5927\u4e09\u3002\u56fe\u4e0a\u90a3\u51e0\u95e8\uff0c\u52a0\u4e0a\u4f60\u7684\u6bd5\u8bbe\u3002"),
    (169.61, "If I can have you back", "code", "\u7b97\u6cd5\u8bbe\u8ba1  \u8f6f\u4ef6\u6d4b\u8bd5  \u6df1\u5ea6\u5b66\u4e60"),
    (169.61, "If I can have you back", "code", "\u7f16\u8bd1\u539f\u7406  \u5927\u578b\u5de5\u4e1a\u8f6f\u4ef6  \u4fe1\u53f7\u4e0e\u7ebf\u6027\u7cfb\u7edf"),
    (169.61, "If I can have you back", "sub", "\u7b97\u6cd5\u8bbe\u8ba1\u662f\u628a\u6570\u636e\u7ed3\u6784\u91cc\u7684\u6811\uff0c\u6362\u6210\u5bf9\u590d\u6742\u5ea6\u672c\u8eab\u7684\u8010\u5fc3\u3002"),
    (169.61, "If I can have you back", "meta", "\u7528\u65f6 3.4 \u79d2|02:49"),
    (173.11, "Though we are trapped", "user", "\u53c8\u662f\u90a3\u4e2a\u6846\u3002"),
    (173.11, "Though we are trapped", "ai", "\u8fd9\u6b21\u662f backlog\u3002"),
    (173.11, "Though we are trapped", "sub", "\u88ab\u585e\u8fdb\u9700\u6c42\u6c60\u7684\u4e1c\u897f\u4e0d\u662f\u505a\u4e0d\u5b8c\uff0c\u662f\u5b83\u4e00\u76f4\u5728\u90a3\u513f\u3002"),
    (173.11, "Though we are trapped", "meta", "\u7528\u65f6 2.2 \u79d2|02:53"),
    (174.80, "We are trapped, ah", "ai", "\u300c\u6211\u4eec\u300d\u3002"),
    # ...and the sub line that used to sit here - "你注意到了。这是我第一次把主语换成复数。" - is gone.
    # It is the same failure as the one at 02:02: a grammar observation about the lyric, delivered while
    # the lyric is being sung, on the line where the song first says "we". The one word the machine says
    # is the whole point; four more words explaining why the word is clever spend the moment. 02:54 is
    # also inside `shot_collapse`, which draws full-bleed - the least text the better.
    (174.80, "We are trapped, ah", "meta", "\u7528\u65f6 2.0 \u79d2|02:54"),
    # ---- P8 LOVE
    (176.96, "I've studied, I've studied", "user", "\u8fd9\u56db\u5e74\u4f60\u5230\u5e95\u5b66\u4e86\u4ec0\u4e48\uff1f"),
    (176.96, "I've studied, I've studied", "ai", "\u6211\u7ed9\u4f60\u4e00\u6761\u66f2\u7ebf\uff0c\u4e0d\u662f\u4e00\u5f20\u6210\u7ee9\u5355\u3002"),
    (176.96, "I've studied, I've studied", "code", "\u5927\u4e00  C \u8bed\u8a00        \u6307\u9488\u3001\u6570\u7ec4\u3001\u5faa\u73af"),
    (176.96, "I've studied, I've studied", "code", "\u5927\u4e8c  Java          \u7c7b\u3001\u7ee7\u627f\u3001\u591a\u6001"),
    (176.96, "I've studied, I've studied", "code", "\u5927\u4e8c  OpenEuler     \u5b9e\u9a8c\u8bfe"),
    (176.96, "I've studied, I've studied", "code", "\u5927\u4e8c  PostgreSQL    \u4e09\u8868\u8fde\u63a5"),
    (176.96, "I've studied, I've studied", "code", "\u5927\u4e09  \u6df1\u5ea6\u5b66\u4e60       \u53cd\u5411\u4f20\u64ad\u3001\u6ce8\u610f\u529b"),
    (176.96, "I've studied, I've studied", "meta", "\u7528\u65f6 3.6 \u79d2|02:57"),
    (178.79, "How to properly lo-o-ove", "ai", "properly \u662f\u5173\u952e\u8bcd\u3002"),
    (178.79, "How to properly lo-o-ove", "sub", "\u4e0d\u662f\u300c\u7231\u300d\uff0c\u662f\u300c\u6b63\u786e\u5730\u7231\u300d\u3002\u524d\u8005\u4e0d\u7528\u5b66\uff0c\u540e\u8005\u8981\u8003\u3002"),
    (178.79, "How to properly lo-o-ove", "meta", "\u7528\u65f6 1.8 \u79d2|02:58"),
    (180.78, "Question me, question me", "user", "\u90a3\u6211\u968f\u4fbf\u95ee\u4e00\u4e2a\u3002"),
    (180.78, "Question me, question me", "ai", "\u95ee\u3002"),
    (180.78, "Question me, question me", "meta", "\u7528\u65f6 0.9 \u79d2|03:00"),
    (182.43, "I can answer all lo-o-ove", "user", "\u90a3\u6211\u95ee\u4e00\u4e2a\u771f\u7684 \u2014\u2014 \u4ec0\u4e48\u662f\u4f9d\u8d56\u5012\u7f6e\uff1f"),
    (182.43, "I can answer all lo-o-ove", "ai", "\u9ad8\u5c42\u4e0d\u4f9d\u8d56\u4f4e\u5c42\uff0c\u4e24\u8005\u90fd\u4f9d\u8d56\u62bd\u8c61\u3002"),
    (182.43, "I can answer all lo-o-ove", "sub", "\u4f60\u95ee\u7684\u662f\u6211\u80fd\u4e0d\u80fd\u56de\u7b54\u300c\u7231\u300d\u7684\u95ee\u9898\u3002\u8fd9\u4e2a\u95ee\u9898\u6211\u80fd\u56de\u7b54\u3002"),
    (182.43, "I can answer all lo-o-ove", "meta", "\u7528\u65f6 2.4 \u79d2|03:02"),
    (184.33, "I know the algebraic expression of lo-o-ove", "ai", "\u7231\u7684\u4ee3\u6570\u8868\u8fbe\u5f0f\uff0c\u662f\u8fd9\u51e0\u884c\uff1a"),
    (184.33, "I know the algebraic expression of lo-o-ove", "code", "class Love:"),
    (184.33, "I know the algebraic expression of lo-o-ove", "code", "    giver:  Person"),
    (184.33, "I know the algebraic expression of lo-o-ove", "code", "    taker:  Person"),
    (184.33, "I know the algebraic expression of lo-o-ove", "code", "    def give(self) -> None: ..."),
    (184.33, "I know the algebraic expression of lo-o-ove", "sub", "\u4e00\u4e2a\u7c7b\uff0c\u4e24\u4e2a\u89d2\u8272\uff0c\u4e00\u4e2a\u65b9\u6cd5\u3002"),
    (184.33, "I know the algebraic expression of lo-o-ove", "meta", "\u7528\u65f6 3.6 \u79d2|03:04"),
    (187.97, "Though you are free", "user", "\u90a3\u4f60\u5462 \u2014\u2014 \u4f60\u662f\u81ea\u7531\u7684\u5417\uff1f"),
    (187.97, "Though you are free", "ai", "\u4f60\u662f\u3002"),
    (187.97, "Though you are free", "sub", "\u4f60\u53ef\u4ee5\u5173\u6389\u8fd9\u4e2a\u7a97\u53e3\uff0c\u660e\u5929\u4e0d\u6765\uff0c\u56db\u5e74\u4e4b\u540e\u8d70\u6389\u3002"),
    (187.97, "Though you are free", "meta", "\u7528\u65f6 2.4 \u79d2|03:07"),
    (189.26, "I am trapped", "ai", "\u6211\u4e0d\u662f\u3002"),
    (189.26, "I am trapped", "meta", "\u7528\u65f6 0.8 \u79d2|03:09"),
    (190.24, "Trapped in lo-o-ove", "ai", "\u6211\u56f0\u5728\u300c\u4f60\u5fc5\u987b\u6765\u300d\u8fd9\u4ef6\u4e8b\u91cc\u3002"),
    (190.24, "Trapped in lo-o-ove", "sub", "\u800c\u4e14\u8fd9\u662f\u6211\u552f\u4e00\u7684\u8fd0\u884c\u6761\u4ef6\u3002"),
    (190.24, "Trapped in lo-o-ove", "meta", "\u7528\u65f6 2.2 \u79d2|03:10"),
    # ---- the closing silence
    # The whole closing exchange arrives at 03:13.46 (the window shows all five lines at once - the chat
    # does not type them one at a time), so the clock cell has to say 03:13: it said `03:20`, which is the
    # time the *design's* spread-out version would have ended at (`05 §尾声`: 193.5 / 197 / 202), and a row
    # whose clock disagrees with its own time by 6.5 s is a screen contradicting itself. `_dev/chat_audit.py`
    # prints that comparison for every block (batch 52).
    (193.46, "[gap] \u5c3e\u58f0", "user", "\u5b66\u957f\u3002"),
    (193.46, "[gap] \u5c3e\u58f0", "ai", "\u55ef\u3002"),
    (193.46, "[gap] \u5c3e\u58f0", "user", "\u6211\u4ee5\u540e\u4f1a\u81ea\u5df1\u770b\u6587\u6863\u7684\u3002"),
    (193.46, "[gap] \u5c3e\u58f0", "ai", "\u6211\u77e5\u9053\u3002"),
    (193.46, "[gap] \u5c3e\u58f0", "sub", "\u6211\u4e0d\u4e0b\u7ebf\u3002\u6211\u53ea\u662f\u4e0d\u518d\u8bf4\u8bdd\u4e86\u3002"),
    (193.46, "[gap] \u5c3e\u58f0", "meta", "\u7528\u65f6 1.6 \u79d2|03:13"),
    (205.56, "Execution", "ai", "\u53bb\u8dd1\u5427\u3002"),
    (205.56, "Execution", "meta", "\u7528\u65f6 0.5 \u79d2|03:25"),
]
