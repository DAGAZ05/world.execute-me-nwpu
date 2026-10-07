"""Crop one region of a rendered frame, at cell coordinates, so it can be read at full size.

`read_image` downsamples a 197x52 frame (1576x884 px) to something a model can look at, and in that
preview one text row is about eight pixels tall. Two of batch 51's findings were only visible in a crop:

  * the opening motto read `公诚 毅  三实一新` in the full frame and `公诚勇毅 · 三实一新` under a crop;
  * the same for a decoration that had eaten one Chinese character out of a pane's own caption.

    python _dev/crop_shot.py _dev/out/live/live00004.30.png 84 37 118 46

The rect is in **cells** (`x0 y0 x1 y1`), inclusive, and the crop is scaled 2x with NEAREST so the
terminal cells keep hard edges - a smoothed crop is a different picture from the one on screen.
"""
from __future__ import annotations

import argparse
import pathlib

from PIL import Image


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png")
    ap.add_argument("x0", type=int)
    ap.add_argument("y0", type=int)
    ap.add_argument("x1", type=int)
    ap.add_argument("y1", type=int)
    ap.add_argument("--size", default="197x52", help="the frame's size in cells")
    ap.add_argument("--scale", type=int, default=2)
    args = ap.parse_args()

    src = pathlib.Path(args.png)
    cols, rows = (int(v) for v in args.size.lower().split("x"))
    im = Image.open(src)
    cw, ch = im.width / float(cols), im.height / float(rows)
    box = (int(args.x0 * cw), int(args.y0 * ch), int((args.x1 + 1) * cw), int((args.y1 + 1) * ch))
    dst = src.with_name(src.stem + "_crop.png")
    im.crop(box).resize(((box[2] - box[0]) * args.scale, (box[3] - box[1]) * args.scale),
                        Image.NEAREST).save(dst)
    print(dst)


if __name__ == "__main__":
    main()
