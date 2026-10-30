#!/usr/bin/env python3
"""fdsum.py <original.mp4> <clone.mp4> [--prev rodada_anterior.mp4] [--bloco 20] [--largura 480] [--json saida.json]

Distância quadro a quadro (média de |diferença| em RGB, 0 = igual), muito mais fina que a grade 96x54 do
compare.py, resumida por bloco de quadros, com a razão de movimento clone/original. Com --prev, cada bloco
mostra também a rodada anterior e um sinal (+ piorou, - melhorou, = igual): é por aqui que se decide o que
corrigir (mude uma hipótese por região e julgue pelos blocos, não pela média)."""
import argparse, json, subprocess
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("original"); ap.add_argument("clone")
ap.add_argument("--prev"); ap.add_argument("--bloco", type=int, default=20)
ap.add_argument("--largura", type=int, default=480); ap.add_argument("--json")
a = ap.parse_args()
w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", a.original], capture_output=True, text=True, check=True).stdout.strip().split(","))
W = a.largura; H = max(2, int(round(h * W / w / 2)) * 2)


def quadros(v):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3).astype(np.int16)


R = quadros(a.original); er = np.abs(np.diff(R, axis=0)).mean(axis=(1, 2, 3))


def dist(v):
    C = quadros(v)[:len(R)]
    return np.abs(C - R[:len(C)]).mean(axis=(1, 2, 3)) / 255, np.abs(np.diff(C, axis=0)).mean(axis=(1, 2, 3))


d, e = dist(a.clone)
dp = dist(a.prev)[0] if a.prev else None
print(f"distância média por quadro {d.mean():.4f}  quadros {len(d)}/{len(R)}" + (f"  (anterior {dp.mean():.4f})" if a.prev else ""))
blocos = []
for i in range(0, len(d), a.bloco):
    b = slice(i, i + a.bloco); pior = i + int(np.argmax(d[b])); eb = slice(max(i - 1, 0), i + a.bloco - 1)
    x = dict(a=i, b=min(i + a.bloco, len(d)) - 1, dist=round(float(d[b].mean()), 4), pior_quadro=pior,
             pior=round(float(d[pior]), 4), movimento=round(float(e[eb].sum() / max(er[eb].sum(), 1e-6)), 2))
    s = f"f{x['a']:3d}-{x['b']:3d}  dist {x['dist']:.4f}"
    if dp is not None and i < len(dp):
        x["anterior"] = round(float(dp[b].mean()), 4)
        s += f"  anterior {x['anterior']:.4f} {'+' if x['dist'] > x['anterior'] + 0.0005 else '-' if x['dist'] < x['anterior'] - 0.0005 else '='}"
    print(s + f"  pior f{pior} {x['pior']:.4f}  movimento {x['movimento']:.2f}")
    blocos.append(x)
if a.json:
    json.dump(dict(media=round(float(d.mean()), 4), quadros=len(d), quadros_original=len(R),
                   anterior=None if dp is None else round(float(dp.mean()), 4), blocos=blocos), open(a.json, "w"), indent=1)
