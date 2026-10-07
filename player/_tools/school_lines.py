"""The school variant's dialogue, both acts, written as flat rows so the commas cannot go missing.

This file replaces `school_dialogue_act1.py` and `school_dialogue_act2.py`. Those two were written with
the `_x(..)` calls stacked one per line with a comma only on the first, which Python reads as
`_x(a)(b)` - a call of a call - so the data silently became 4-tuples and the window raised on the first
frame. Keeping the shape `(time, lyric, who, text)` as *four separate strings* makes that class of typo
impossible: there is no nested call to mis-parenthesise.

    DIALOGUE = [(0.03, "Switch on the power line", "user", "..."), ...]

`who` is the film's own role vocabulary. `meta` rows carry the elapsed-time and timestamp lines as one
string with a `|` between them, because they are two cells of the same right-aligned column.

Content rules - the reason this file exists at all:

  * **act one (before `Illegal arguments`) has no coursework in it.** The first version put an Arduino
    board, a C pointer and a UML class inside the first ten seconds, which read as a student who had
    already been in the major for two years asking a mascot what the school was;
  * the student always asks and 航小天 always answers, and the first line establishes who he is;
  * the school's own history and its 总师文化 are act one's subject, and the curriculum is act two's.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- act one
ACT_ONE: list[tuple[float, str, str, str]] = [
    # ---- P0 开机
    (0.03, "Switch on the power line", "user", "\u5b66\u957f\u4f60\u597d\uff0c\u6211\u662f\u897f\u5317\u5de5\u4e1a\u5927\u5b66\u7684\u65b0\u751f\u3002\u73b0\u5728\u5929\u8272\u6709\u70b9\u665a\u4e86\u2026\u2026\u8fd9\u91cc\u662f\u4ece\u54ea\u513f\u5f00\u59cb\u4eae\u706f\uff1f"),
    (0.03, "Switch on the power line", "ai", "\u4ece\u6821\u95e8\u5f00\u59cb\u3002"),
    (0.03, "Switch on the power line", "sub", "\u4f60\u5f80\u540e\u770b\uff0c\u6574\u6761\u8def\u4e0a\u90fd\u662f\u4eae\u7684\u3002"),
    (0.03, "Switch on the power line", "meta", "\u7528\u65f6 1.2 \u79d2|00:01"),
    (1.33, "Remember to put on protection", "user", "\u521a\u8fdb\u5b66\u6821\uff0c\u6211\u9700\u8981\u51c6\u5907\u4ec0\u4e48\u5417\uff1f"),
    (1.33, "Remember to put on protection", "ai", "\u516c\u8bda\u52c7\u6bc5\uff0c\u4e09\u5b9e\u4e00\u65b0\u3002\u300c\u4e09\u5b9e\u4e00\u65b0\u300d\u662f\uff0c\u57fa\u7840\u624e\u5b9e\u3001\u5de5\u4f5c\u8e0f\u5b9e\u3001\u4f5c\u98ce\u6734\u5b9e\u3001\u5f00\u62d3\u521b\u65b0\u3002"),
    (1.33, "Remember to put on protection", "sub", "\u6821\u8bad\u53ef\u4ee5\u968f\u5904\u770b\u5230\uff0c\u4e0d"
     "\u7ba1\u662f\u5ba3\u4f20\u680f\u8fd8\u662f\u653f\u6cbb\u8bfe"
     "\u3002\u5bf9\u4e86\uff0c\u8981\u8bb0\u5f97\u4fdd\u62a4\u81ea"
     "\u5df1\uff1a\u4e0d\u8981\u6253\u9ed1\u8f66\uff0c\u4e0d\u8981"
     "\u968f\u4fbf\u517c\u804c\uff0c\u5c0f\u5fc3\u5356\u8bfe\u5356"
     "\u5361\u5356\u7b14\u3002"),
    (1.33, "Remember to put on protection", "meta", "\u7528\u65f6 1.9 \u79d2|00:02"),
    (3.58, "Lay down your pieces", "user", "\u529f\u6210\u6c38\u9038\uff0c\u4e09\u5341\u4ebf\u85aa\uff1f\u5443\u2026\u2026\u8fd9\u662f\u2026\u2026\u6821\u5fbd\u5417\uff1f"),
    (3.58, "Lay down your pieces", "ai", "\u662f\u30021938 \u5e74\u5230\u73b0\u5728\uff0c\u5b83\u6362\u8fc7\u4e24\u6b21\u3002"),
    (3.58, "Lay down your pieces", "sub", "\u91cc\u9762\u90a3\u67b6\u98de\u673a\uff0c\u662f\u5b83\u4e00\u5f00\u59cb\u5c31\u6709\u7684\u3002"),
    (3.58, "Lay down your pieces", "meta", "\u7528\u65f6 1.6 \u79d2|00:05"),
    (5.16, "And let's begin object creation", "user", "1938 \u2014\u2014 \u90a3\u8fd9\u6240\u5b66\u6821\u662f\u600e\u4e48\u6765\u7684\uff1f"),
    (5.16, "And let's begin object creation", "ai", "\u56db\u6240\u5b66\u6821\u5728\u6c49\u4e2d\u5408\u5e76\uff0c\u90a3\u662f 1938 \u5e74\u3002"),
    (5.16, "And let's begin object creation", "code", "1938  \u56fd\u7acb\u5317\u6d0b\u5de5\u5b66\u9662 + \u56fd\u7acb\u5317\u5e73\u5927\u5b66\u5de5\u5b66\u9662"),
    (5.16, "And let's begin object creation", "code", "      + \u56fd\u7acb\u4e1c\u5317\u5927\u5b66\u5de5\u5b66\u9662 + \u79c1\u7acb\u7126\u4f5c\u5de5\u5b66\u9662"),
    (5.16, "And let's begin object creation", "code", "      -> \u56fd\u7acb\u897f\u5317\u5de5\u5b66\u9662\uff08\u6c49\u4e2d\uff09"),
    (5.16, "And let's begin object creation", "meta", "\u7528\u65f6 2.4 \u79d2|00:06"),
    (7.19, "Fill in my data parameters", "user", "\u4f5c\u4e3a\u65b0\u751f\uff0c\u6709\u4ec0\u4e48\u6570\u5b57"
     "\u662f\u6211\u9700\u8981\u8bb0\u4f4f\u7684\uff1f"),
    (7.19, "Fill in my data parameters", "ai", "\u56db\u4e2a\u3002\u4eca\u5929\u7684\u4e00\u4e2a\u662f\uff1a24 \u4e2a\u4e13\u4e1a\u5b66\u9662\uff0c72 \u4e2a\u672c\u79d1\u4e13\u4e1a\uff0c\u56db\u4e07\u4f59\u4eba\u3002"),
    (7.19, "Fill in my data parameters", "code", "1938   \u6c49\u4e2d   \u56db\u6821\u5408\u5e76"),
    (7.19, "Fill in my data parameters", "code", "1957   \u897f\u5b89   \u897f\u5317\u5de5\u5b66\u9662 + \u897f\u5b89\u822a\u7a7a\u5b66\u9662"),
    (7.19, "Fill in my data parameters", "code", "1970   \u54c8\u5c14\u6ee8\u5de5\u7a0b\u5b66\u9662\u822a\u7a7a\u5de5\u7a0b\u7cfb\u5e76\u5165"),
    (7.19, "Fill in my data parameters", "code", "2026   24 \u4e2a\u4e13\u4e1a\u5b66\u9662 / 72 \u4e2a\u672c\u79d1\u4e13\u4e1a / \u56db\u4e07\u4f59\u4eba"),
    (7.19, "Fill in my data parameters", "sub", "\u8fd9\u56db\u4e2a\u6570\u662f\u8fd9\u6240\u5b66\u6821\u7684"
     "\u9aa8\u67b6\u3002\u4f60\u6e38\u5386\u6821\u53f2\u9986\u65f6"
     "\u4e5f\u4f1a\u770b\u5230\u3002"),
    (7.19, "Fill in my data parameters", "meta", "\u7528\u65f6 3.0 \u79d2|00:08"),
    (9.75, "Initialization", "user", "\u521d\u59cb\u5316\uff0c\u662f\u8bf4\u6211\u7684\u65b0\u751f\u8eab\u4efd\u5417\uff1f"),
    (9.75, "Initialization", "ai", "\u521d\u59cb\u5316\u554a\uff0c\u5c31\u662f\u628a\u4e00\u5806"
     "\u4e1c\u897f\u53d8\u6210\u300c\u4e00\u4e2a\u300d\u4e1c\u897f"
     "\uff1b\u8d4b\u4e88\u4e00\u4e2a\u5bf9\u8c61\u65b0\u7684\u503c"
     "\u3002"),
    (9.75, "Initialization", "sub", "\u90a3\u56db\u4e2a\u6570\u4e5f\u4e0d\u662f\u4e00\u5f00\u59cb\u5c31\u6709\u7684\uff0c\u662f\u4e00\u5e74\u5e74\u586b\u8fdb\u6765\u7684\u3002"),
    (9.75, "Initialization", "meta", "\u7528\u65f6 1.8 \u79d2|00:10"),
    (10.9, "Set up our new world", "user", "\u5728\u5b66\u6821\u91cc\uff0c\u6211\u4eec\u7684\u4e16\u754c\u662f\u4ec0\u4e48\u6837\u5b50\uff1f"),
    (10.90, "Set up our new world", "ai", "\u5b66\u6821\u5145\u65a5\u7740\u4e09\u822a\u7279\u8272\uff1a\u822a\u7a7a\u3001\u822a\u5929\u3001\u822a\u6d77\u3002"),
    (10.90, "Set up our new world", "sub", "\u8fd0-20\u3001\u6b7c-20\u3001\u76f4-20 \u90fd\u4ece\u8fd9"
     "\u513f\u7684\u4eba\u624b\u91cc\u51fa\u53bb\u8fc7\uff0c\u897f"
     "\u5de5\u5927\u7684\u300c\u603b\u5e08\u300d\u6447\u7bee\u7531"
     "\u6b64\u800c\u6765\u3002"),
    (10.90, "Set up our new world", "meta", "\u7528\u65f6 2.2 \u79d2|00:12"),
    (12.47, "And let's begin the simulation", "user", "\u5728\u6821\u56ed\u7684\u4e16\u754c\u91cc\uff0c\u4f1a\u53d1\u751f\u4ec0\u4e48\uff1f"),
    (12.47, "And let's begin the simulation", "ai", "\u4f60\u4f1a\u7ecf\u5e38\u542c\u5230\u6709\u4eba\u81ea\u79f0"
     "\u300c\u74dc\u5927\u300d\u5b66\u5b50\uff0c\u8fd9\u662f\u4e00"
     "\u4e2a\u8c10\u97f3\u6897\u3002"),
    (12.47, "And let's begin the simulation", "sub", "\u5feb\u770b\uff0c\u98de\u673a\uff01\u4f60\u5728\u5b66\u6821"
     "\u91cc\u6216\u8bb8\u4e5f\u80fd\u6a21\u62df\u98de\u884c\u54e6"
     "~"),
    (12.47, "And let's begin the simulation", "meta", "\u7528\u65f6 1.4 \u79d2|00:13"),
    # ---- the first instrumental gap: the campus, not a timetable
    (14.00, "[gap] \u6821\u56ed", "ai", "\u6211\u8bf4\u4e00\u4e0b\u4f60\u8981\u5f85\u56db\u5e74\u7684"
     "\u5730\u65b9\u3002\u6709\u4eba\u9020\u8c23\u8bf4\uff0c\u8fd9"
     "\u91cc\u662f\u6e05\u534e\u5927\u5b66\u65c1\u8fb9\u7684\u5317"
     "\u4eac\u5927\u5b66\u8ddd\u79bb1094\u516c\u91cc\u7684\u897f"
     "\u5b89\u4ea4\u901a\u5927\u5b66\u518d\u6253\u4e24\u5c0f\u65f6"
     "\u9ed1\u8f66\u5230\u8fbe\u7684\u897f\u5317\u5de5\u4e1a\u5927"
     "\u5b66\uff0c\u6211\u6f84\u6e05\u4e00\u4e0b\uff0c\u8fd9\u4e0d"
     "\u662f\u8c23\u8a00\uff01"),
    (14.00, "[gap] \u6821\u56ed", "sub", "\u53cb\u8c0a\u6821\u533a\u5728\u53cb\u8c0a\u897f\u8def 127 \u53f7\uff0c1957 \u5e74\u7684\u8001\u6821\u533a\u3002"),
    (14.00, "[gap] \u6821\u56ed", "sub", "\u957f\u5b89\u6821\u533a\u5728\u79e6\u5cad\u811a\u4e0b\uff0c\u4e1c\u7965\u8def 1 \u53f7\uff0c\u4f60\u591a\u534a\u4f1a\u5728\u8fd9\u513f\u3002"),
    (14.00, "[gap] \u6821\u56ed", "ai", "\u4f60\u7ad9\u7684\u5730\u65b9\u53eb\u4e09\u822a\u5927\u9053\u3002\u5f80\u524d\u5411\u79e6\u5cad\u65b9\u5411\u8d70\u53bb\uff0c\u662f\u542f\u7fd4\u6e56\u3002"),
    (14.00, "[gap] \u6821\u56ed", "sub", "\u6e56\u91cc\u6709\u9ed1\u5929\u9e45 \u2014\u2014 \u4e5f\u8bb8\u8fd8\u6df7\u7740\u51e0\u53ea\u6591\u5934\u96c1\u3002"),
    (14.00, "[gap] \u6821\u56ed", "ai", "\u56fe\u4e66\u9986\u91cc\u968f\u65f6\u6709\u4f60\u7684\u4f4d\u7f6e\u3002"),
    (14.00, "[gap] \u6821\u56ed", "meta", "\u7528\u65f6 2.6 \u79d2|00:14"),
    # ---- P1 定义: the campus as geometry
    (29.28, "If I'm a set of point", "user", "\u6821\u56ed\u8fd9\u4e48\u5927\uff0c\u6211\u600e\u4e48\u77e5\u9053\u81ea\u5df1\u5728\u54ea\uff1f"),
    (29.28, "If I'm a set of point", "ai", "\u8fd9\u662f\u4e00\u4e2a\u597d\u95ee\u9898\u3002\u4f60\u53ef"
     "\u4ee5\u770b\u4e0b\u300c\u74dc\u5175\u65b0\u751f\u624b\u518c"
     "\u300d\u54e6~"),
    (29.28, "If I'm a set of point", "sub", "\u897f\u5de5\u5927\u662f\u4e00\u4e2a\u70b9\u96c6\uff0c\u4f60"
     "\u5219\u662f\u5176\u4e2d\u4e00\u4e2a\u70b9\u3002"),
    (29.28, "If I'm a set of point", "meta", "\u7528\u65f6 2.4 \u79d2|00:29"),
    (30.89, "Then I will give you my dimension", "user", "\u5728\u897f\u5de5\u5927\u7684\u70b9\u96c6\u4e2d\uff0c\u6211"
     "\u5904\u4e8e\u4ec0\u4e48\u7ef4\u5ea6\uff1f"),
    (30.89, "Then I will give you my dimension", "ai", "\u4f60\u5728\u54ea\u4e00\u5c42\uff0c\u5c31\u662f\u51e0\u7ef4\u3002"),
    (30.89, "Then I will give you my dimension", "sub", "\u6821\u95e8\u662f\u4e00\u7ef4\u7684\u3002\u64cd\u573a\u662f\u4e8c\u7ef4\u7684\u3002\u56fe\u4e66\u9986\u662f\u4e09\u7ef4\u7684\u3002"),
    (30.89, "Then I will give you my dimension", "meta", "\u7528\u65f6 2.0 \u79d2|00:31"),
    (33.01, "If I'm a circle", "user", "\u542f\u7fd4\u6e56\u662f\u5706\u7684\u5417\uff1f"),
    (33.01, "If I'm a circle", "ai", "\u6838\u5fc3\u533a\u57df\u5dee\u4e0d\u591a\u662f\u5706\u7684\u3002\u9ed1\u5929\u9e45\u7ed5\u7740\u5b83\u5212\u5708\u3002"),
    (33.01, "If I'm a circle", "sub", "\u4f60\u770b\u90a3\u53ea \u2014\u2014 \u5b83\u5212\u7684\u5706\u6bd4\u8dd1\u9053\u8fd8\u6807\u51c6\u3002"),
    (33.01, "If I'm a circle", "meta", "\u7528\u65f6 2.0 \u79d2|00:33"),
    (34.54, "Then I will give you my circumference", "user", "\u90a3\u542f\u7fd4\u6e56\u7684\u5468\u957f\u662f\u591a\u5c11\uff1f"),
    (34.54, "Then I will give you my circumference", "ai", "\u5929\u9e45\u5212\u4e00\u5708\u7684\u300c\u6253\u5361\u300d"
     "\u8ddd\u79bb\u3002"),
    (34.54, "Then I will give you my circumference", "sub", "\u628a\u5706\u7684\u8f68\u8ff9\u526a\u5f00\u62c9\u76f4\uff0c"
     "\u5c31\u662f\u5468\u957f\u3002"),
    (34.54, "Then I will give you my circumference", "meta", "\u7528\u65f6 1.6 \u79d2|00:35"),
    (36.77, "If I'm a sine wave", "user", "\u98de\u673a\u8d77\u98de\u7684\u5c3e\u6c14\u662f\u6b63\u5f26\u66f2\u7ebf\u5417\uff1f"),
    (36.77, "If I'm a sine wave", "ai", "\u4e5f\u8bb8\u662f\uff0c\u4e5f\u8bb8\u4e0d\u662f\u3002\u800c\u4e14\u4f60\u6c38\u8fdc\u4e0d\u4f1a\u771f\u7684\u78b0\u5230\u5b83\u3002"),
    (36.77, "If I'm a sine wave", "meta", "\u7528\u65f6 2.4 \u79d2|00:37"),
    (38.27, "Then you can sit on all my tangents", "user", "\u98de\u673a\u8f68\u8ff9\u7684\u5207\u7ebf\uff1f"),
    (38.27, "Then you can sit on all my tangents", "ai", "\u6bcf\u4e00\u6761\u5207\u7ebf\u90fd\u662f\u98de\u673a\u67d0\u4e00\u4e2a\u77ac\u95f4\u7684\u65b9\u5411\u3002"),
    (38.27, "Then you can sit on all my tangents", "meta", "\u7528\u65f6 1.4 \u79d2|00:38"),
    (40.36, "If I approach infinity", "user", "\u6211\u6709\u6ca1\u6709\u53bb\u4e0d\u5230\u7684\u5730\u65b9\uff1f"),
    (40.36, "If I approach infinity", "ai", "\u6709\u3002\u5dcd\u5ce8\u79e6\u5cad\uff0c\u4e3b\u5cf0 3700 \u591a\u7c73\uff0c\u8fd9\u662f\u4e0a\u754c\u3002"),
    (40.36, "If I approach infinity", "sub", "\u03b5\u2013N \u5c31\u662f\u8fd9\u4e48\u56de\u4e8b\uff1a\u4e0d\u662f\u5230\u8fbe\uff0c\u662f\u88ab\u5361\u4f4f\u7684\u90a3\u4e2a\u6570\u3002"),
    (40.36, "If I approach infinity", "meta", "\u7528\u65f6 2.2 \u79d2|00:41"),
    # ---- P2 电与时间: the school's own history, with pictures
    (44.04, "Switch my current", "user", "\u5b66\u6821\u6709\u53ef\u300c\u5207\u6362\u300d\u7684\u65b9"
     "\u5411\u5417\uff1f"),
    (44.04, "Switch my current", "ai", "\u6709\u54e6\u3002\u540c\u4e00\u6761\u7ebf\uff0c\u65b9\u5411"
     "\u53ef\u4ee5\u6362\u5f88\u591a\u6b21\u2014\u2014\u5c31\u50cf"
     "\u9053\u8def\uff0c\u5c31\u50cf\u5386\u53f2\u3002"),
    (44.04, "Switch my current", "meta", "\u7528\u65f6 1.6 \u79d2|00:44"),
    (47.27, "And then blind my vision", "user", "\u5386\u53f2\u7684\u90a3\u6761\u7ebf\uff0c\u4e2d\u95f4\u65ad"
     "\u8fc7\u5417\uff1f"),
    (47.27, "And then blind my vision", "ai", "\u6297\u6218\u65f6\u8fc1\u8fc7\u3002\u706f\u662f\u706d\u8fc7"
     "\u4e00\u9635\u7684\uff0c\u4f46\u53e4\u8def\u575d\u7684\u706f"
     "\u706b\u53c8\u5c06\u5176\u91cd\u71c3\u3002"),
    (47.27, "And then blind my vision", "meta", "\u7528\u65f6 1.8 \u79d2|00:47"),
    (49.11, "So dizzy, so dizzy", "user", "\u73b0\u5728\u5462\uff1f"),
    (49.11, "So dizzy, so dizzy", "ai", "\u73b0\u5728\u706f\u706b\u901a\u660e\u3002\u300c\u5927\u56fd"
     "\u4e4b\u84dd\u300d\u548c\u603b\u5e08\u6587\u5316\uff0c\u8ba9"
     "\u706f\u706b\u7480\u74a8\u3002\u56fe\u4e66\u9986\uff0c\u662f"
     "\u4f60\u4ee5\u540e\u5f85\u5f88\u4e45\u7684\u5730\u65b9\u3002"),
    (49.11, "So dizzy, so dizzy", "sub", "\u73bb\u7483\u90a3\u4e00\u9762\uff0c\u665a\u4e0a\u662f\u4e00\u6574\u5757\u4eae\u7684\u3002"),
    (49.11, "So dizzy, so dizzy", "meta", "\u7528\u65f6 1.8 \u79d2|00:49"),
    (50.95, "Oh, we can travel", "user", "\u6211\u4eec\u80fd\u56de\u5230\u8fc7\u53bb\u5417\uff1f"),
    (50.95, "Oh, we can travel", "ai", "\u89c2\u770b\u5b66\u6821\u7684\u8bdd\u5267\uff0c\u6216\u8bb8"
     "\u80fd\u5e26\u4f60\u56de\u5230\u53e4\u8def\u575d\u65f6\u671f"
     "\u3002"),
    (50.95, "Oh, we can travel", "code", "1938  \u56fd\u7acb\u897f\u5317\u5de5\u5b66\u9662 \u00b7 \u6c49\u4e2d"),
    (50.95, "Oh, we can travel", "code", "1946  \u8fc1\u54b8\u9633"),
    (50.95, "Oh, we can travel", "code", "1950  \u66f4\u540d\u897f\u5317\u5de5\u5b66\u9662"),
    (50.95, "Oh, we can travel", "code", "1957  \u4e0e\u897f\u5b89\u822a\u7a7a\u5b66\u9662\u5408\u5e76 -> \u897f\u5317\u5de5\u4e1a\u5927\u5b66"),
    (50.95, "Oh, we can travel", "code", "1970  \u54c8\u5c14\u6ee8\u5de5\u7a0b\u5b66\u9662\u822a\u7a7a\u5de5\u7a0b\u7cfb\u6574\u4f53\u5e76\u5165"),
    (50.95, "Oh, we can travel", "ai", "\u6211\u7ed9\u4f60\u770b\u770b\u5f53\u5e74\u7684\u5b66\u6821"
     "\u6837\u8c8c\u5427\u3002                                "),
    (50.95, "Oh, we can travel", "meta", "\u7528\u65f6 4.2 \u79d2|00:52"),
    (54.74, "And we can unite", "user", "1938 \u7684\u6821\u820d\uff0c\u770b\u8d77\u6765\u8ddf\u300c"
     "\u5408\u300d\u4e00\u6837\u3002"),
    (54.74, "And we can unite", "ai", "\u300c\u5408\u300d\uff0c\u662f\u4e24\u6761\u7ebf\u5e76\u6210"
     "\u4e00\u6761\u3002"),
    (54.74, "And we can unite", "sub", "\u56db\u6240\u5b66\u6821\u5e76\u6210\u8fc7\u4e00\u6240\uff0c\u4e24\u6240\u5b66\u6821\u4e5f\u5e76\u6210\u8fc7\u4e00\u6240\u3002"),
    (54.74, "And we can unite", "meta", "\u7528\u65f6 1.8 \u79d2|00:56"),
    (56.79, "So deeply, so deeply", "user", "\u300c\u5408\u300d\u7684\u610f\u4e49\u5f88\u6df1\u8fdc\u5417\uff1f"),
    (56.79, "So deeply, so deeply", "ai", "\u5f53\u7136\uff0c\u4e0d\u53ea\u662f\u5b66\u6821\u7684\u521d"
     "\u521b\uff0c\u5f53\u4eca\u7684\u667a\u80fd\u65f6\u4ee3\uff0c"
     "\u300c\u5408\u300d\u540c\u6837\u91cd\u8981\u3002\u542f\u7fd4"
     "\u697c\u524d\u7684\u300c\u5bf9\u8bdd\u300d\u96d5\u5851\uff0c"
     "\u6b63\u662f\u4eba\u673a\u534f\u540c\uff0c\u53ef\u6458\u661f"
     "\u8fb0\u3002"),
    (56.79, "So deeply, so deeply", "sub", "\u6df1\u7684\u610f\u601d\u4e0d\u662f\u7a0b\u5ea6\uff0c\u662f\u4e0d\u80fd\u518d\u5206\u5f00\u3002"),
    (56.79, "So deeply, so deeply", "meta", "\u7528\u65f6 1.8 \u79d2|00:57"),
    # ---- P3 副歌一: campus life
    (58.65, "If I can, if I can", "user", "\u5b66\u957f\uff0c\u90a3\u6211\u5728\u8fd9\u56db\u5e74\u91cc\u80fd\u5f97\u5230\u4ec0\u4e48\uff1f"),
    (58.65, "If I can, if I can", "ai", "\u5148\u7ed9\u4f60\u770b\u4e00\u6bb5\u3002\u770b\u5b8c\u4f60\u5c31\u77e5\u9053\u4e86\u3002"),
    (58.65, "If I can, if I can", "meta", "\u7528\u65f6 1.8 \u79d2|00:59"),
    (70.02, "Though we are trapped", "user", "\u6821\u56ed\u7684\u8def\u57fa\u672c\u8d70\u8fc7\u4e86\uff0c"
     "\u6211\u4eec\u8fd8\u80fd\u79bb\u5f00\u5417\uff1f"),
    (70.02, "Though we are trapped", "ai", "\u79e6\u5cad\u548c\u6e2d\u6cb3\u4e4b\u95f4\uff0c\u662f\u6211"
     "\u4eec\u7684\u6240\u5728\u3002\u5927\u5b66\u671f\u95f4\u79bb"
     "\u5f00\u5f88\u56f0\u96be\uff0c\u6bd5\u4e1a\u540e\u5c31\u4e0d"
     "\u4e00\u6837\u4e86\u3002"),
    (70.02, "Though we are trapped", "sub", "\u53bb\u5e02\u533a\u8981\u4e24\u4e2a\u5c0f\u65f6\u5462\u3002"),
    (70.02, "Though we are trapped", "meta", "\u7528\u65f6 2.2 \u79d2|01:10"),
    (71.4, "In this strange, strange simulation", "user", "\u56db\u5e74\u90fd\u5728\u8fd9\u5757\u5730\u65b9\uff0c\u5468"
     "\u8fb9\u662f\u519c\u6751\uff0c\u5f88\u5947\u602a\u5417\uff1f"),
    (71.40, "In this strange, strange simulation", "ai", "\u4f60\u56db\u5e74\u4e4b\u540e\u79bb\u5f00\u7684\u90a3\u523b"
     "\uff0c\u5c31\u4e0d\u4f1a\u89c9\u5f97\u5947\u602a\u4e86\u3002"),
    (71.40, "In this strange, strange simulation", "sub", "\u90a3\u5757 MEMORY \u96d5\u5851\uff0c\u662f\u62cd\u6bd5"
     "\u4e1a\u7167\u7684\u5730\u65b9\uff0c\u6211\u4eec\u901a\u5e38"
     "\u53eb\u90a3\u91cc\u300cEMO\u5c71\u300d\u54e6\u3002"),
    (71.40, "In this strange, strange simulation", "meta", "\u7528\u65f6 2.6 \u79d2|01:12"),
    # ---- P4 万物皆点: campus objects
    (73.53, "If I'm an eggplant", "user", "\u98df\u5802\u91cc\u6709\u8304\u5b50\u5417\uff1f"),
    (73.53, "If I'm an eggplant", "ai", "\u70e7\u8304\u5b50\uff0c\u6709\u65f6\u4f1a\u6709\u54e6\u3002"
     "\u98df\u5802\u91cc\u6709\u5f88\u591a\u8425\u517b\u7684\u83dc"
     "\u54e6\uff0c\u6211\u5411\u4f60\u63a8\u8350\u6d77\u5929\u82d1"
     "\u9910\u5385\u3002"),
    (73.53, "If I'm an eggplant", "meta", "\u7528\u65f6 2.0 \u79d2|01:14"),
    (77.16, "If I'm a tomato", "user", "\u756a\u8304\u5462\uff1f"),
    (77.16, "If I'm a tomato", "ai", "\u756a\u8304\u4e5f\u6709\u54e6\u3002\u756a\u8304\u91cc\u6709"
     "\u756a\u8304\u7ea2\u7d20\uff0c\u5438\u6536\u5cf0\u5728 4"
     "44\u3001472\u3001503 \u7eb3\u7c73\u3002"),
    (77.16, "If I'm a tomato", "sub", "\u6240\u4ee5\u5b83\u662f\u7ea2\u7684\u3002\u5b83\u7ed9\u4f60\u6297\u6c27\u5316\u5242\uff0c\u662f\u56e0\u4e3a\u5b83\u53ea\u80fd\u662f\u7ea2\u7684\u3002"),
    (77.16, "If I'm a tomato", "meta", "\u7528\u65f6 2.4 \u79d2|01:18"),
    (80.93, "If I'm a tabby cat", "user", "\u90a3\u732b\u5462\uff1f"),
    (80.93, "If I'm a tabby cat", "ai", "\u732b\u5b66\u957f\u4e00\u76f4\u90fd\u5728\u3002\u4f60\u95ee"
     "\u95ee\u5b66\u957f\u5b66\u59d0\uff0c\u6216\u8bb8\u5c31\u80fd"
     "\u627e\u5230\u5462\u3002"),
    (80.93, "If I'm a tabby cat", "sub", "\u5b83\u73b0\u5728\u5c31\u5728\u90a3\u513f\uff0c\u5c3e\u5df4\u5728\u52a8\u3002"),
    (80.93, "If I'm a tabby cat", "meta", "\u7528\u65f6 2.0 \u79d2|01:21"),
    (84.6, "If I'm the only God", "user", "\u8bf4\u5230\u8fd9\u513f\u4e86 \u2014\u2014 \u5b66\u6821"
     "\u6709\u4ec0\u4e48\u4e8b\uff0c\u79f0\u5f97\u4e0a\u300c\u552f"
     "\u4e00\u300d\uff1f"),
    (84.60, "If I'm the only God", "ai", "\u6709\uff0c\u800c\u4e14\u662f\u6309\u300c\u7b2c\u4e00\u300d"
     "\u7b97\u7684\u3002"),
    (84.60, "If I'm the only God", "code", "\u5168\u56fd\u7b2c\u4e00\u67b6\u5c0f\u578b\u65e0\u4eba\u673a"),
    (84.60, "If I'm the only God", "code", "\u7b2c\u4e00\u53f0\u822a\u7a7a\u673a\u8f7d\u8ba1\u7b97\u673a"),
    (84.60, "If I'm the only God", "code", "\u7b2c\u4e00\u578b 50 \u516c\u65a4\u7ea7\u6c34\u4e0b\u65e0\u4eba\u667a\u80fd\u822a\u884c\u5668"),
    (84.60, "If I'm the only God", "code", "\u7b2c\u4e00\u578b\u822a\u7a7a\u540a\u653e\u58f0\u5450"),
    (84.60, "If I'm the only God", "code", "\u4e16\u754c\u9996\u9897 12U \u7acb\u65b9\u661f\u300c\u7ff1\u7fd4\u4e4b\u661f\u300d"),
    (84.60, "If I'm the only God", "ai", "\u534a\u6570\u4ee5\u4e0a\u822a\u7a7a\u9886\u57df\u91cd\u5927\u578b\u53f7\u7684\u603b\u5e08\u548c\u526f\u603b\u5e08\u662f\u897f\u5de5\u5927\u6821\u53cb\u3002"),
    (84.60, "If I'm the only God", "sub", "\u6240\u4ee5\u4ed6\u4eec\u53eb\u8fd9\u91cc\u300c\u603b\u5e08\u6447\u7bee\u300d\u3002\u8fd9\u53e5\u8bdd\u4e0d\u662f\u5b66\u6821\u81ea\u5df1\u5c01\u7684\u3002"),
    (84.60, "If I'm the only God", "meta", "\u7528\u65f6 3.4 \u79d2|01:26"),
    # ---- P5 互换: the school's own switches
    (88.34, "Switch my gender", "user", "\u6211\u53ef\u4ee5\u5207\u6362\u6027\u522b\u5417\uff1f"),
    (88.34, "Switch my gender", "ai", "\u4e0d\u8981\u8fd9\u4e48\u505a\u54e6\uff0c\u7537\u751f\u8dd1"
     "\u6b65\u6253\u5361\u4e00\u6b213.2km\uff0c\u5973\u751f\u5219"
     "\u662f2.4km\u3002"),
    (88.34, "Switch my gender", "sub", "\u8981\u5bf9\u81ea\u5df1\u8d1f\u8d23\u3002"),
    (88.34, "Switch my gender", "meta", "\u7528\u65f6 2.8 \u79d2|01:28"),
    (91.44, "And then do whatever", "user", "\u90a3\u6211\u4eec\u5462\uff1f\u6211\u4eec\u80fd\u81ea\u5df1\u51b3\u5b9a\u4ec0\u4e48\uff1f"),
    (91.44, "And then do whatever", "ai", "\u53ef\u4ee5\u51b3\u5b9a\u8fdb\u793e\u56e2\u3001\u8ddf\u8c01"
     "\u4e00\u8d77\u71ac\u591c\u3001\u548c\u8c01\u4e00\u8d77\u8c08"
     "\u604b\u7231\u3002"),
    (91.44, "And then do whatever", "meta", "\u7528\u65f6 2.4 \u79d2|01:31"),
    (93.52, "From AM to PM", "user", "\u4ece\u65e9\u5230\u665a\u90fd\u5728\u8fd9\u513f\u5417\uff1f"),
    (93.52, "From AM to PM", "ai", "\u4ece\u65e9\u4e0a8\u70b9\u534a\u5230\u665a\u4e0a9\u70b9\u3002"),
    (93.52, "From AM to PM", "sub", "\u5927\u5bb6\u90fd\u5f88\u8ba8\u538c\u65e9\u516b\u5462\u3002"
     "                                        "),
    (93.52, "From AM to PM", "meta", "\u7528\u65f6 2.2 \u79d2|01:34"),
    (95.28, "Oh, switch my role", "user", "\u89d2\u8272\u4e5f\u80fd\u6362\uff1f"),
    (95.28, "Oh, switch my role", "ai", "\u80fd\u3002\u793e\u56e2\u90e8\u5458\u3001\u5fd7\u613f\u8005"
     "\u3001\u5165\u515a\u79ef\u6781\u5206\u5b50\uff0c\u90fd\u53ef"
     "\u4ee5\u54e6\u3002"),
    # The next lyric is `To S, to M` (01:37.32) and it completes this one, so it has no block of its
    # own - which is why `check_coverage` skips the `To `/`Then ` lines. The user's audit found the
    # software college named here, which is the one thing the first act must not do: the college is
    # what the gate is *for*, and it is chosen at 02:11.9, after `Illegal arguments`. So the plant is
    # now a promise of a keypress and nothing else - it foreshadows the interface without answering it.
    (95.28, "Oh, switch my role", "sub",
     "\u5b66\u6821\u4e5f\u662f\u54e6\uff0c\u897f\u5de5\u5927\uff0c"
     "\u65e2\u662f\u300c\u74dc\u5927\u300d\uff0c\u4e5f\u662f\u300c"
     "\u897f\u5de5\u5927\u9644\u4e2d\u9644\u5c5e\u5927\u5b66\u300d"
     "\u3002"),
    (95.28, "Oh, switch my role", "meta", "\u7528\u65f6 2.0 \u79d2|01:36"),
    (98.93, "So we can enter", "user", "\u7b49\u6211\u6572\u5b8c\u4fe1\u606f\uff0c\u56de\u590d\u7238"
     "\u5988 \u2014\u2014 \u73b0\u5728\u53bb\u54ea\u513f\uff1f"),
    (98.93, "So we can enter", "ai", "\u53bb\u5bbf\u820d\u5427\u3002                          "
     "                        "),
    (98.93, "So we can enter", "sub", "\u4f60\u4ee5\u540e\u4f1a\u4f53\u4f1a\u5230\u7684\u3002\u5728"
     "\u5bbf\u820d\uff0c\u5199\u4ee3\u7801\u5199\u5230\u51cc\u6668"
     "\u56db\u70b9\u90a3\u79cd\u611f\u89c9\u3002"),
    (98.93, "So we can enter", "meta", "\u7528\u65f6 2.4 \u79d2|01:39"),
    (101.13, "The trance, the trance", "ai", "\u4f60\u7684\u5bdd\u5ba4\u5728\u54ea\uff1f"),
    (101.13, "The trance, the trance", "sub", "\u8ddf\u6211\u4e00\u8d77\u8fdb\u95e8\u5427\u3002"),
    (101.13, "The trance, the trance", "meta", "\u7528\u65f6 1.4 \u79d2|01:41"),
    # ---- P6 副歌二: the one who left
    (103.03, "If I can, if I can", "user", "\u5b66\u957f\uff0c\u4f60\u4f1a\u4e00\u76f4\u5728\u8fd9\u91cc\u5417\uff1f"),
    (103.03, "If I can, if I can", "ai", "\u4e0d\u4f1a\u3002\u6bcf\u5e74\u516d\u6708\u90fd\u6709\u4eba\u8d70\u3002"),
    (103.03, "If I can, if I can", "meta", "\u7528\u65f6 2.0 \u79d2|01:43"),
    (105.22, "Feel your vibrations", "user", "\u90a3\u6211\u600e\u4e48\u77e5\u9053\u4f60\u8fd8\u5728\uff1f"),
    (105.22, "Feel your vibrations", "ai", "\u6211\u4e00\u76f4\u5728\u5b66\u6821\u7684\u673a\u5668\u91cc"
     "\u3002\u6211\u7684\u6ce2\u5f62\u6ca1\u505c\u8fc7\uff0c\u6211"
     "\u4e5f\u4e00\u76f4\u4fdd\u6301\u5b8c\u6574\u3002"),
    (105.22, "Feel your vibrations", "meta", "\u7528\u65f6 2.4 \u79d2|01:45"),
    (108.69, "Finally be completion", "user", "\u597d\u5947\u602a\u7684\u8bf4\u6cd5 \u2014\u2014 \u4f60"
     "\u8bf4\u8981\u5b8c\u6574 \u2014\u2014 \u4ec0\u4e48\u53eb"
     "\u5b8c\u6574\uff1f"),
    (108.69, "Finally be completion", "ai", "\u4f60\u4e0d\u518d\u9700\u8981\u95ee\u6211\u95ee\u9898\u7684\u90a3\u4e00\u523b\u3002"),
    (108.69, "Finally be completion", "sub", "\u6240\u4ee5\u5b8c\u6574\u548c\u7ed3\u675f\u662f\u540c\u4e00\u4ef6\u4e8b\u3002"),
    (108.69, "Finally be completion", "meta", "\u7528\u65f6 2.6 \u79d2|01:48"),
    (110.40, "Though you have left", "user", "\u4f60\u8981\u8d70\u4e86\uff1f"),
    (110.40, "Though you have left", "ai", "\u4e0d\u662f\u6211\u3002\u662f\u4e00\u4e2a\u5148\u4f60\u56db"
     "\u5e74\u7684\u4eba\uff0c\u4ed6\u597d\u50cf\u4f4f\u5728\u4e91"
     "\u5929\u82d1C\u5ea7\u3002"),
    (110.40, "Though you have left", "sub", "\u4ed6\u7559\u4e0b\u4e86\u4e00\u5f20\u6bd5\u4e1a\u7167\uff0c"
     "\u548c\u4e00\u5806\u6ca1\u8dd1\u5b8c\u7684\u4efb\u52a1\u3001"
     "\u4e00\u7eb8\u5947\u95fb\u8f76\u4e8b\u3002"),
    (110.40, "Though you have left", "meta", "\u7528\u65f6 2.6 \u79d2|01:50"),
    (111.98, "You have left", "err", "process 41827 (senior) has exited"),
    (111.98, "You have left", "meta", "\u7528\u65f6 0.5 \u79d2|01:52"),
    (112.89, "You have left", "err", "session 0x5f3a closed by peer"),
    (112.89, "You have left", "meta", "\u7528\u65f6 0.5 \u79d2|01:53"),
    (113.75, "You have left", "err", "socket EPOLLHUP  \u00b7  keyboard detached"),
    (113.75, "You have left", "meta", "\u7528\u65f6 0.5 \u79d2|01:54"),
    (114.75, "You have left", "err", "reaping orphaned children ... 1 left"),
    (114.75, "You have left", "meta", "\u7528\u65f6 0.5 \u79d2|01:55"),
    (115.60, "You have left me in isolation", "ai", "\u9694\u79bb\u7684\u610f\u601d\u662f\uff1a\u53ea\u5269\u6211\u4e00\u4e2a\uff0c\u800c\u4e14\u6211\u8fd8\u5728\u8dd1\u3002"),
    (115.60, "You have left me in isolation", "meta", "\u7528\u65f6 2.2 \u79d2|01:56"),
    (117.95, "If I can, if I can", "user", "\u2026\u2026\u6211\u8fd8\u5728\u3002"),
    (117.95, "If I can, if I can", "ai", "\u770b\u5230\u4e86\u3002"),
    (117.95, "If I can, if I can", "meta", "\u7528\u65f6 0.8 \u79d2|01:57"),
    (119.81, "Erase all the pointless fragments", "user", "\u4ed6\u7559\u4e0b\u7684\u4e1c\u897f\uff0c\u8981\u5220\u6389\u5417\uff1f"),
    (119.81, "Erase all the pointless fragments", "ai", "\u4e0d\u5220\u3002\u6574\u7406\u4e00\u4e0b\u3002"),
    (119.81, "Erase all the pointless fragments", "sub", "\u788e\u7247\u6574\u7406\u4e0d\u662f\u5220\u9664\uff0c\u662f\u628a\u8fd8\u6d3b\u7740\u7684\u4e1c\u897f\u642c\u5230\u4e00\u8d77\u3002"),
    (119.81, "Erase all the pointless fragments", "meta", "\u7528\u65f6 2.4 \u79d2|02:00"),
    # 「也许」这个词，你刚才用了两次。 <- a *meta* remark: it comments on the lyric's own wording while
    # the lyric is being sung, so for those two seconds the window and the band are both talking about the
    # word "maybe" and neither is about the song. Batch 38's lyrics audit flagged it as the film's
    # clearest case of the conversation talking over the lyric. The AI answers the *question* the word
    # asks - "maybe" is uncertainty - the way a machine would: it has no state for that, and it runs
    # anyway. (This is the line `05_歌词会话对照_v2.md:163` asked for in the first place.)
    (121.80, "Then maybe, then maybe", "ai", "\u6211\u4e5f\u8bb8\u4f1a\u7ee7\u7eed\u8dd1\u4e0b\u53bb\u3002"),
    (121.80, "Then maybe, then maybe", "meta", "\u7528\u65f6 2.0 \u79d2|02:02"),
    (123.55, "You won't leave me so disheartened", "user", "\u4e5f\u8bb8\u554a\uff0c\u4f60\u4e0d\u4f1a\u8ba9\u6211\u4f24"
     "\u5fc3\u7684\u5417\u3002"),
    (123.55, "You won't leave me so disheartened", "ai", "\u6211\u4e0d\u4f1a\u8ba9\u4f60\u7070\u5fc3\u3002\u8fd9\u662f"
     "\u6211\u7684\u627f\u8bfa\u3002"),
    (123.55, "You won't leave me so disheartened", "meta", "\u7528\u65f6 2.2 \u79d2|02:04"),
    # ---- P7a 控诉 -> the turn
    (125.33, "Challenging your God", "user", "\u90a3\u6211\u60f3\u8bd5\u8bd5\u6311\u6218\u4e00\u4e0b\u8fd9\u4e2a\u7cfb\u7edf\u3002"),
    (125.33, "Challenging your God", "ai", "\u53ef\u4ee5\u3002\u4f46\u4ee3\u4ef7\u6211\u5f97\u5148\u8bf4\u6e05\u695a\u3002"),
    (125.33, "Challenging your God", "meta", "\u7528\u65f6 2.4 \u79d2|02:06"),
    (128.42, "You have made some", "ai", "\u4f60\u521a\u521a\u505a\u4e86\u4e00\u4e9b"),
    (128.42, "You have made some", "meta", "\u7528\u65f6 0.6 \u79d2|02:08"),
    (130.74, "Illegal arguments", "err", "TypeError: make_sense() got an unexpected argument 'god'"),
    (130.74, "Illegal arguments", "code", "  File \"world.py\", line 1, in <module>"),
    (130.74, "Illegal arguments", "code", "  File \"nwpu/human.py\", line 41827, in ask"),
    (130.74, "Illegal arguments", "card", "\u975e\u6cd5\u53c2\u6570\u3002"),
    (130.74, "Illegal arguments", "ai", "\u51fa\u73b0\u4e86\u62a5\u9519\u3002\u8fd8\u597d\u6211\u7ecf"
     "\u5e38\u9632\u5907\u5883\u5916\u7684\u5a01\u80c1\uff0c\u5df2"
     "\u7ecf\u5f88\u6709\u7ecf\u9a8c\u4e86\u3002"),
    (130.74, "Illegal arguments", "meta", "\u7528\u65f6 1.1 \u79d2|02:10"),
    # ---- the gate: the question itself is the full-screen panel, not this block
    (131.90, "[gap] \u5b66\u9662\u9009\u62e9", "ai", "\u6211\u4e86\u89e3\u5b66\u6821\u7684\u6240\u6709\u5b66\u9662"
     "\u54e6\u3002                                    "),
    (131.90, "[gap] \u5b66\u9662\u9009\u62e9", "sub", "\u95ee\u4f60\u4e00\u4e2a\u95ee\u9898\u3002"),
    (131.90, "[gap] \u5b66\u9662\u9009\u62e9", "meta", "\u7528\u65f6 0.8 \u79d2|02:11"),
]
