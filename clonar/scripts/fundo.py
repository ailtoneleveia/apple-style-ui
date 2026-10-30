#!/usr/bin/env python3
"""fundo.py <video> <saida.png> [--celula 20] [--mascaras mascaras.json] [--largura 540]

Campo de fundo de baixa frequência por quadro: a mediana de cada célula (celula px do original) sem o que está
na frente. Serve para fundos que são luz, vinheta, brilho e esmaecimento (o que um gradiente de CSS acerta
mal), e para a placa de um vídeo de pessoa. O que está na frente sai de duas formas:
  - mascaras.json: [{"de": f0, "ate": f1, "caixa": [x0, y0, x1, y1]}, ...] em px do original (as peças que a
    composição desenha por cima: elas não podem ficar borradas no fundo);
  - automático: segunda passada sem os pixels que diferem mais de 45 níveis da mediana da célula (texto fino).
Célula sem pixel bom é preenchida pelas vizinhas (inpaint).
Saída: um atlas PNG sem perda (linhas x colunas por quadro, 16 quadros por linha do atlas) e <saida>.json com o
tamanho da grade. Na composição: desenhe o retângulo do quadro num canvas do tamanho do vídeo com suavização alta."""
import argparse, json, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument("video"); ap.add_argument("saida")
ap.add_argument("--celula", type=int, default=20); ap.add_argument("--mascaras"); ap.add_argument("--largura", type=int, default=540)
a = ap.parse_args()
w, h = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                                "-of", "csv=p=0", a.video], capture_output=True, text=True, check=True).stdout.strip().split(","))
k = a.largura / w; W, H = a.largura, int(round(h * k))
cel = max(2, int(round(a.celula * k)))
gx, gy = W // cel, H // cel
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.video, "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                     capture_output=True, check=True).stdout
Q = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
masc = json.load(open(a.mascaras)) if a.mascaras else []
n = len(Q)
cols = 16; rows = (n + cols - 1) // cols
atlas = np.zeros((rows * gy, cols * gx, 3), np.uint8)


def celulas(img, ok):
    x = img[:gy * cel, :gx * cel].astype(np.float32).reshape(gy, cel, gx, cel, 3).transpose(0, 2, 1, 3, 4).reshape(gy, gx, cel * cel, 3)
    m = ok[:gy * cel, :gx * cel].reshape(gy, cel, gx, cel).transpose(0, 2, 1, 3).reshape(gy, gx, cel * cel)
    x = np.where(m[..., None], x, np.nan)
    with np.errstate(all="ignore"):
        med = np.nanmedian(x, axis=2)
    return med, m.mean(-1), x


for f in range(n):
    ok = np.ones((H, W), bool)
    for c in masc:
        if c["de"] <= f <= c["ate"]:
            x0, y0, x1, y1 = [int(round(v * k)) for v in c["caixa"]]
            ok[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = False
    med, frac, x = celulas(Q[f], ok)
    # segunda passada: tira o que foge da mediana da célula (texto e bordas finas)
    longe = np.nanmax(np.abs(x - med[:, :, None, :]), axis=-1) > 45
    with np.errstate(all="ignore"):
        med2 = np.nanmedian(np.where(longe[..., None], np.nan, x), axis=2)
    ruim = np.isnan(med2).any(-1) | (frac < 0.15)
    img = np.nan_to_num(med2).clip(0, 255).astype(np.uint8)
    if ruim.any() and not ruim.all():
        img = cv2.inpaint(img, ruim.astype(np.uint8), 3, cv2.INPAINT_TELEA)
    r, c_ = divmod(f, cols)
    atlas[r * gy:(r + 1) * gy, c_ * gx:(c_ + 1) * gx] = img
cv2.imwrite(a.saida, atlas[..., ::-1])
json.dump(dict(colunas_grade=gx, linhas_grade=gy, celula_px=w / gx, quadros=n, quadros_por_linha=cols), open(a.saida.rsplit(".", 1)[0] + ".json", "w"))
print(a.saida, f"grade {gx}x{gy} por quadro, {n} quadros")
