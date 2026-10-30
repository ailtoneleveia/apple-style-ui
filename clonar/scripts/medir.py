#!/usr/bin/env python3
"""medir.py <video.mp4> <a> <b> <teste> [--regiao x0,y0,x1,y1] [--limiar L] [--forma caixa|momentos]

Mede uma peça quadro a quadro pela cor, direto do vídeo (quadros a..b, numeração do burst.py).
teste: escuro (luma<L) | naobranco (255-min>L) | claro (luma>fundo+L) | verde | azul | vermelho (canal - max dos
outros > L) | saturado (max-min > L).
--forma caixa (padrão): f x0 y0 x1 y1 w h cx cy area da caixa dos pixels que passam (linha/coluna precisa de 3).
--forma momentos: centro, lados do retângulo equivalente (sqrt(12*autovalor)) e ângulo do eixo longo. Aguenta
desfoque e motion blur, onde a caixa e o canto não aguentam (bom para morph que gira)."""
import argparse, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("a", type=int); ap.add_argument("b", type=int); ap.add_argument("teste")
ap.add_argument("--regiao"); ap.add_argument("--limiar", type=float, default=40); ap.add_argument("--forma", default="caixa")
a = ap.parse_args()
w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", a.video], capture_output=True, text=True, check=True).stdout.strip().split(","))
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"select=between(n\\,{a.a}\\,{a.b})", "-fps_mode",
                      "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
Q = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
reg = [int(v) for v in a.regiao.split(",")] if a.regiao else [0, 0, w, h]
L = a.limiar
for k, q in enumerate(Q):
    f = a.a + k
    im = q.astype(np.float32)
    fundo = np.median(im[:24, :24].reshape(-1, 3), 0) @ np.array([0.299, 0.587, 0.114])
    im = im[reg[1]:reg[3], reg[0]:reg[2]]
    r, g, b = im[..., 0], im[..., 1], im[..., 2]; lu = 0.299 * r + 0.587 * g + 0.114 * b
    m = {"escuro": lu < L, "naobranco": (255 - im.min(-1)) > L, "claro": lu > fundo + L,
         "verde": (g - np.maximum(r, b)) > L, "azul": (b - np.maximum(r, g)) > L,
         "vermelho": (r - np.maximum(g, b)) > L, "saturado": (im.max(-1) - im.min(-1)) > L}[a.teste]
    if a.forma == "momentos":
        ys, xs = np.nonzero(m)
        if len(xs) < 50:
            print(f, "-"); continue
        cx, cy = xs.mean(), ys.mean()
        ev, vec = np.linalg.eigh(np.cov(np.stack([xs - cx, ys - cy])))
        ang = np.degrees(np.arctan2(vec[1, 1], vec[0, 1]))
        ang = ang - 180 if ang > 90 else ang + 180 if ang <= -90 else ang
        print(f"{f} c {cx + reg[0]:.1f},{cy + reg[1]:.1f} W {np.sqrt(12 * ev[1]):.1f} H {np.sqrt(12 * ev[0]):.1f} ang {ang:.1f} area {len(xs)}")
        continue
    rows = np.where(m.sum(1) >= 3)[0]; cols = np.where(m.sum(0) >= 3)[0]
    if len(rows) == 0 or len(cols) == 0:
        print(f, "-"); continue
    x0, x1, y0, y1 = cols[0] + reg[0], cols[-1] + reg[0], rows[0] + reg[1], rows[-1] + reg[1]
    print(f, x0, y0, x1, y1, x1 - x0 + 1, y1 - y0 + 1, f"{(x0 + x1) / 2:.1f}", f"{(y0 + y1) / 2:.1f}", int(m.sum()))
