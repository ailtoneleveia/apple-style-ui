#!/usr/bin/env python3
"""maskfit.py <ref.png> <clone.png> [--hue blue|green|red] [--skip-top N]
Affine fit (cv2 ECC) between the same coloured shape in a reference frame and a clone frame:
prints clone = A * ref + t with scale x/y and rotation. Masks are blurred (sigma 10) so a stroke-width
difference does not bias the fit. Used on the route (v5): the clone line was 3.5 % short vertically,
invisible in the 96x54 compare grid but obvious as a doubled edge in diffview.
To correct world points p (screen = p + cam): ref_world = inv(A) @ (p + cam - t) - cam."""
import sys
import numpy as np, cv2
from PIL import Image

a, b = sys.argv[1], sys.argv[2]
hue = sys.argv[sys.argv.index("--hue") + 1] if "--hue" in sys.argv else "blue"
top = int(sys.argv[sys.argv.index("--skip-top") + 1]) if "--skip-top" in sys.argv else 0

def mask(p):
    im = np.asarray(Image.open(p).convert("RGB")).astype(int)
    R, G, B = im[..., 0], im[..., 1], im[..., 2]
    m = {"blue": (B > 180) & (R < 90) & (G < 160), "green": (G > 180) & (R < 120) & (B < 160),
         "red": (R > 200) & (G < 90) & (B < 90)}[hue].astype(np.float32)
    m[:top] = 0
    return cv2.GaussianBlur(m, (0, 0), 10)

A0, B0 = mask(a), mask(b)
warp = np.eye(2, 3, dtype=np.float32)
cc, warp = cv2.findTransformECC(A0 / A0.max(), B0 / B0.max(), warp, cv2.MOTION_AFFINE,
                                (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 300, 1e-6), None, 1)
A, t = warp[:, :2], warp[:, 2]
print(f"cc {cc:.3f}  clone = A*ref + t   sx {np.hypot(A[0,0], A[1,0]):.4f}  sy {np.hypot(A[0,1], A[1,1]):.4f}"
      f"  rot {np.degrees(np.arctan2(A[1,0], A[0,0])):.2f} deg  t {t.round(1).tolist()}  A {A.round(4).tolist()}")
