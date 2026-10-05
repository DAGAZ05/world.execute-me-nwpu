"""Ad-hoc: inspect the basketball animation JSON - structure, frames, and what one frame looks like.

    python _dev/dunk_probe.py                 summary
    python _dev/dunk_probe.py --frame 3       one frame as text
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "\u53c2\u8003\u53ca\u60f3\u6cd5" / "hangxiaotian.json"

ap = argparse.ArgumentParser()
ap.add_argument("--frame", type=int, default=-1)
ap.add_argument("--raw", action="store_true", help="also dump the keys of one frame")
a = ap.parse_args()

d = json.loads(SRC.read_text(encoding="utf8"))
frames = d["frames"]
print(f"canvas {d['canvas']}")
print(f"typography {d['typography']}")
print(f"animation {d['animation']}  frames={len(frames)}")
print(f"total duration {sum(float(f.get('duration') or 0) for f in frames):.2f}s")
print(f"frame keys: {sorted(frames[0].keys())}")
for i, fr in enumerate(frames[:4]):
    cs = fr.get("contentString", "")
    print(f"  {i}: title={fr.get('title')!r} duration={fr.get('duration')} "
          f"content={type(fr.get('content')).__name__} lines={len(cs.splitlines())} "
          f"colors={type(fr.get('colors')).__name__}"
          f"{len(fr['colors']) if hasattr(fr.get('colors'), '__len__') else ''}")
if a.raw:
    print(json.dumps({k: (v if not isinstance(v, (list, dict)) else f"<{type(v).__name__} len "
                          f"{len(v)}>") for k, v in frames[0].items()}, ensure_ascii=False, indent=1))
    c = frames[0].get("colors")
    if isinstance(c, list) and c:
        print("colors[0]", repr(c[0])[:200])
    ct = frames[0].get("content")
    if isinstance(ct, list) and ct:
        print("content[0]", repr(ct[0])[:300])
if a.frame >= 0:
    fr = frames[a.frame]
    print(f"\n--- frame {a.frame}  title={fr.get('title')!r} duration={fr.get('duration')}")
    for y, ln in enumerate(fr.get("contentString", "").splitlines()):
        print(f"{y:3}|{ln}")
