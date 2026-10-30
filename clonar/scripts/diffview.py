#!/usr/bin/env python3
"""diffview.py <original.mp4> <clone.mp4> <saida.png> <f1,f2,...> [--tile 360] [--recorte x,y,w,h]

Uma linha por quadro: ORIGINAL | CLONE | diferença x4 (vermelho = clone mais escuro, azul = mais claro).
Mostra ONDE está o erro que sobrou, não só o tamanho. Imprime a distância de cada quadro.
Os quadros saem do próprio vídeo pelo número (select=eq(n,f)): é a numeração do burst.py e do fdsum.py."""
import argparse, subprocess
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument("original"); ap.add_argument("clone"); ap.add_argument("saida"); ap.add_argument("quadros")
ap.add_argument("--tile", type=int, default=360); ap.add_argument("--recorte")
a = ap.parse_args()
fl = [int(v) for v in a.quadros.split(",")]


def pega(v, fs):
    w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                    "-of", "csv=p=0", v], capture_output=True, text=True, check=True).stdout.strip().split(","))
    sel = "+".join(f"eq(n\\,{f})" for f in sorted(set(fs)))
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select={sel}", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    arr = np.frombuffer(raw, np.uint8).reshape(-1, h, w, 3)
    return dict(zip(sorted(set(fs)), arr)), w, h


R, w, h = pega(a.original, fl)
C, cw, ch = pega(a.clone, fl)
x0, y0, cw_, ch_ = [int(v) for v in a.recorte.split(",")] if a.recorte else (0, 0, w, h)
T = a.tile; th = int(T * ch_ / cw_)
folha = Image.new("RGB", (3 * T + 8, len(fl) * (th + 16)), (17, 17, 17)); d = ImageDraw.Draw(folha)
for k, f in enumerate(fl):
    r = R[f].astype(int)[y0:y0 + ch_, x0:x0 + cw_]
    c = np.asarray(Image.fromarray(C[f]).resize((w, h))).astype(int)[y0:y0 + ch_, x0:x0 + cw_]
    dl = c.mean(-1) - r.mean(-1)
    dv = np.zeros_like(r); dv[..., 0] = np.clip(-dl * 4, 0, 255); dv[..., 2] = np.clip(dl * 4, 0, 255)
    dv[..., 1] = np.clip(np.abs(c - r).max(-1) * 2, 0, 255) // 3
    y = k * (th + 16)
    for j, im in enumerate((r, c, dv)):
        folha.paste(Image.fromarray(im.astype(np.uint8)).resize((T, th)), (j * (T + 4), y + 14))
    md = np.abs(c - r).mean() / 255
    d.text((2, y + 1), f"f{f}  ORIGINAL | CLONE | diferença   dist {md:.4f}", fill=(255, 220, 120))
    print(f, round(md, 4))
folha.save(a.saida)
