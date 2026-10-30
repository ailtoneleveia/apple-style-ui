#!/usr/bin/env python3
"""cursor.py <video.mp4> <a> <b> <x0,y0,x1,y1> <saida.json> [--escalas 2.6,3.0,3.4] [--angulos -60:60:10]
            [--modelo cursor.png --ponta x,y]
cursor.py --autoteste

A PONTA do cursor (o ponto que clica), o ângulo e a escala por quadro, por casamento de modelo no gradiente.
Veio do clone VoiceOS (cursorrot.py), onde o cursor gira na direção do caminho e passa por fundo claro e escuro.

Por que não a caixa: a caixa de tinta de um cursor borrado, girado ou com contorno claro anda vários px longe da
ponta, e o clique (o que o olho confere) é a ponta. No teste cego B3 o cursor do clone parou em cima do "Get Info",
e no original a ponta fica abaixo do ⓘ. Casando no gradiente, a polaridade não importa: seta preta de contorno
branco (macOS) e seta branca de contorno escuro (Joi) dão o mesmo resultado.

Sem --modelo, usa a seta do macOS desenhada aqui (escala 1 = 24x34 px de modelo; a do Satellite saiu ~2,8 num quadro
de 1080). Para mão ou cursor próprio: renderize o cursor DO CLONE num PNG (fundo transparente) e passe --modelo com a
--ponta em px desse PNG; assim a medida do original e a do clone saem na mesma régua.
Grava {quadro: [x, y, escala, angulo, ncc]} em px do vídeo (ângulo em graus, horário) e devolve o JSON padrão.
ncc abaixo de ~0,5: o cursor sumiu, está atrás de algo ou o modelo não serve."""
import argparse, json, sys
import numpy as np
import cv2

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from saida import ok, falha, quadros  # noqa: E402

SETA = np.array([[2, 1.5], [2, 26], [8, 20.5], [12, 30.5], [16.2, 28.7], [12.2, 19], [20.5, 19]]) - [2, 1.5]


def grad(g):
    g = cv2.GaussianBlur(g.astype(np.float32), (0, 0), 1.0)
    return np.hypot(cv2.Sobel(g, cv2.CV_32F, 1, 0), cv2.Sobel(g, cv2.CV_32F, 0, 1))


def modelos(escalas, angulos, png=None, ponta=None, fundo=128.0):
    """{(escala, ângulo): (gradiente do modelo, ponta dentro do modelo)}; o modelo gira em torno da ponta.
    png = (cinza, alfa): pousado sobre o cinza do fundo do vídeo, para só a borda do cursor virar gradiente."""
    out = {}
    if png is not None:
        png = png[0] * png[1] + fundo * (1 - png[1])
    for sc in escalas:
        for ang in angulos:
            if png is None:
                R = 34 * sc + 6; Wd = int(2 * R)
                im = np.zeros((Wd, Wd), np.float32)
                c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
                p = SETA * sc; p = np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) + R
                cv2.fillPoly(im, [p.astype(np.int32)], 0.0)
                cv2.polylines(im, [p.astype(np.int32)], True, 255.0, max(2, int(sc)))
                out[(sc, ang)] = (grad(im), (R, R))
            else:
                h, w = png.shape[:2]; R = int(np.ceil(np.hypot(w, h) * sc)) + 4
                M = cv2.getRotationMatrix2D((float(ponta[0]), float(ponta[1])), -ang, sc)
                M[:, 2] += [R - ponta[0], R - ponta[1]]
                im = cv2.warpAffine(png, M, (2 * R, 2 * R), flags=cv2.INTER_AREA, borderValue=float(fundo))
                out[(sc, ang)] = (grad(im), (R, R))
    return out


def acha(cinza, T):
    """melhor (ncc, x, y, escala, ângulo) da ponta num recorte em tons de cinza. O recorte ganha uma borda repetida do
    tamanho do modelo: sem ela, a ponta perto da borda da região (o modelo tem folga para girar) nunca casa."""
    pad = int(max(m.shape[0] for m, _ in T.values()) // 2 + 1)
    G, best = grad(cv2.copyMakeBorder(cinza.astype(np.float32), pad, pad, pad, pad, cv2.BORDER_REPLICATE)), None
    for (sc, ang), (M, tip) in T.items():
        r = cv2.matchTemplate(G, M, cv2.TM_CCOEFF_NORMED); _, mx, _, (lx, ly) = cv2.minMaxLoc(r)
        if best is None or mx > best[0]:
            best = (float(mx), lx + tip[0] - pad, ly + tip[1] - pad, sc, ang)
    return best


def faixa(txt, tipo=float):
    if ":" in txt:
        a, b, p = map(float, txt.split(":")); return list(np.arange(a, b + p / 2, p))
    return [tipo(v) for v in txt.split(",")]


def autoteste():
    """seta branca de contorno escuro (polaridade oposta ao modelo), borrada, sobre fundo com degradê e ruído"""
    rng = np.random.default_rng(1)
    T = modelos([2.6, 3.0, 3.4], range(-40, 41, 10))
    piores = []
    for (tx, ty, sc, ang) in [(120.0, 90.0, 3.0, 0), (70.0, 140.0, 2.8, -20), (150.0, 60.0, 3.3, 30)]:
        im = np.tile(np.linspace(150, 230, 260, dtype=np.float32), (220, 1))
        c, s = np.cos(np.radians(ang)), np.sin(np.radians(ang))
        p = SETA * sc; p = np.stack([p[:, 0] * c - p[:, 1] * s, p[:, 0] * s + p[:, 1] * c], 1) + [tx, ty]
        cv2.fillPoly(im, [np.round(p * 8).astype(np.int32)], 250.0, shift=3)
        cv2.polylines(im, [np.round(p * 8).astype(np.int32)], True, 30.0, 3, shift=3)
        im = cv2.GaussianBlur(im, (0, 0), 1.2) + rng.normal(0, 3, im.shape).astype(np.float32)
        n, x, y, e, a = acha(im, T)
        piores.append(max(abs(x - tx), abs(y - ty)))
        assert abs(x - tx) <= 2.5 and abs(y - ty) <= 2.5 and abs(a - ang) <= 10, f"ponta {x},{y} ângulo {a} (verdade {tx},{ty} {ang})"
    ok(f"autoteste ok: ponta a até {max(piores):.1f} px da verdade em 3 cursores (polaridade invertida, borrados, girados)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?"); ap.add_argument("a", nargs="?", type=int); ap.add_argument("b", nargs="?", type=int)
    ap.add_argument("regiao", nargs="?"); ap.add_argument("saida", nargs="?")
    ap.add_argument("--escalas", default="2.6,3.0,3.4"); ap.add_argument("--angulos", default="-60:60:10")
    ap.add_argument("--modelo"); ap.add_argument("--ponta"); ap.add_argument("--autoteste", action="store_true")
    o = ap.parse_args()
    if o.autoteste:
        return autoteste()
    if not (o.video and o.saida):
        falha("uso: cursor.py <video> <a> <b> <x0,y0,x1,y1> <saida.json> (ou --autoteste)")
    if bool(o.modelo) != bool(o.ponta):
        falha("--modelo pede --ponta x,y (a ponta do cursor em px do PNG)")
    png = None
    if o.modelo:
        im = cv2.imread(o.modelo, cv2.IMREAD_UNCHANGED)
        if im is None:
            falha(f"não consegui ler {o.modelo}")
        cz = im.astype(np.float32) if im.ndim == 2 else im[..., :3].astype(np.float32).mean(-1)
        png = (cz, im[..., 3].astype(np.float32) / 255 if im.ndim == 3 and im.shape[2] == 4 else np.ones_like(cz))
    x0, y0, x1, y1 = map(int, o.regiao.split(","))
    ponta = [float(v) for v in o.ponta.split(",")] if o.ponta else None
    T, res, fracos = None, {}, []
    for f, q in quadros(o.video, o.a, o.b):
        cinza = q[y0:y1, x0:x1].astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
        if T is None:  # o modelo pousa sobre o fundo da região no 1º quadro (mediana da borda)
            T = modelos(faixa(o.escalas), faixa(o.angulos), png, ponta,
                        float(np.median(np.concatenate([cinza[0], cinza[-1], cinza[:, 0], cinza[:, -1]]))))
        n, x, y, sc, ang = acha(cinza, T)
        res[f] = [round(x + x0, 1), round(y + y0, 1), round(float(sc), 2), round(float(ang), 1), round(n, 3)]
        if n < 0.5:
            fracos.append(f)
    json.dump(res, open(o.saida, "w"), indent=0)
    ks = sorted(res)
    ok(f"ponta do cursor em {len(res)} quadros (f{ks[0]} {res[ks[0]][:2]} → f{ks[-1]} {res[ks[-1]][:2]})"
       + (f"; ncc baixo em {len(fracos)} quadros ({fracos[:6]}...): confira na folha" if fracos else ""),
       motivo="ajuste a mola do caminho da ponta (x e y) e desenhe o cursor do clone com a ponta nesse ponto",
       arquivo=o.saida, ncc_baixo=fracos)


if __name__ == "__main__":
    main()
