#!/usr/bin/env python3
"""corner.py <frame.png> <mode> <thr> x0,y0,x1,y1
Corner radius of a rounded rectangle: inside the region, take the mask (same colour tests as
measure.py), find the shape's bbox, read how far the left edge is pulled in on each of the top
rows and fit a circular radius r to it (inset(d) = r - sqrt(r^2 - (r - d)^2)). Prints bbox and r."""
import sys
import numpy as np
from PIL import Image

p, mode, thr = sys.argv[1], sys.argv[2], float(sys.argv[3])
x0, y0, x1, y1 = [int(v) for v in sys.argv[4].split(",")]
im = np.asarray(Image.open(p).convert("RGB")).astype(np.int16)[y0:y1, x0:x1]
r_, g, b = im[..., 0], im[..., 1], im[..., 2]
m = {"dark": (0.299 * r_ + 0.587 * g + 0.114 * b) < thr, "nonwhite": (255 - im.min(-1)) > thr,
     "green": (g - np.maximum(r_, b)) > thr, "blue": (b - np.maximum(r_, g)) > thr,
     "sat": (im.max(-1) - im.min(-1)) > thr}[mode]
rows = np.where(m.sum(1) >= 3)[0]; cols = np.where(m.sum(0) >= 3)[0]
top, bot, left, right = rows[0], rows[-1], cols[0], cols[-1]
H = bot - top + 1
ins = []
for d in range(0, H // 2):
    xs = np.where(m[top + d])[0]
    ins.append((xs[0] - left) if len(xs) else np.nan)
ins = np.array(ins, float)
best = None
for r in np.arange(4, H / 2 + 0.5, 0.5):
    d = np.arange(len(ins)) + 0.5
    pred = np.where(d < r, r - np.sqrt(np.maximum(r * r - (r - d) ** 2, 0)), 0)
    e = np.nanmean((pred - ins) ** 2)
    if best is None or e < best[0]:
        best = (e, r)
print(f"bbox x{left + x0}-{right + x0} y{top + y0}-{bot + y0} w{right - left + 1} h{H}  radius {best[1]:.1f} (rms {np.sqrt(best[0]):.2f})")
print("inset by row:", " ".join(f"{v:.0f}" for v in ins[:40]))
