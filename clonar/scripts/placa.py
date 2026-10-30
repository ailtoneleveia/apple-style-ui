#!/usr/bin/env python3
"""placa.py: placa de fundo em coordenadas de mundo, a partir de um trecho do original e da câmera medida.

  placa.py <video> <camera.json> <saida.jpg|.png> --de A --ate B --ancora F [--janela] [--fora fora.json]
           [--claro 140] [--sat 105] [--sem-auto]

camera.json: [{"f": 0, "s": 1.0, "tx": 0, "ty": 0}, ...] com tela = s * mundo + (tx, ty) (camtrack.py, registra_cam.py).
A placa fica nas coordenadas do quadro-âncora: tela_f = s' * placa_mundo + t', com s' = s_f / s_âncora.
Cada quadro de A a B é levado para o mundo pela câmera e a placa é a mediana deles, sem o que está na frente:
  - automático: texto claro sem cor (luma > --claro e saturação < 60, dilatado 21 px) e cor forte (saturação > --sat,
    dilatado 31 px); --sem-auto desliga;
  - fora.json: [{"de": f0, "ate": f1, "caixa": [x0, y0, x1, y1]}] tira a caixa; {"de", "ate", "circulo": [cx, cy, r]}
    fica só com o que está dentro do círculo (máscara de abertura).
A mediana dos quadros sem zoom (s' perto de 1, nítidos) manda; a de todos só preenche o que eles não viram.
Placa larga (.jpg): o que nunca apareceu fica com a cor mediana da placa, e há conferência (placa levada de volta à
tela contra o original). --janela (.png): placa curta com alfa, buraco transparente, para ir por cima da larga em
trechos curtos (o mapa que se redesenha a cada nível de zoom pediu placas de 7 quadros no 4º clone).
Grava <saida>.json com a origem da placa no mundo (ox, oy), tamanho, âncora e a fração sem dado.
Memória: guarda o trecho inteiro levado para o mundo (float16); trechos longos em vídeo grande, divida.
Uso interno: a placa é recorte do vídeo original.
"""
import argparse, json, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import LU, falha, ok, quadros, tamanho  # noqa: E402


def le_camera(caminho):
    try:
        return {int(r["f"]): r for r in json.load(open(caminho))}
    except (OSError, ValueError, KeyError) as e:
        falha(f"camera.json ilegível: {e}", 1)


def relativa(cam, anc):
    """câmera relativa ao quadro-âncora: tela_f = s' * mundo_âncora + t'"""
    ca = cam[anc]
    return {f: dict(s=r["s"] / ca["s"], tx=r["tx"] - r["s"] / ca["s"] * ca["tx"], ty=r["ty"] - r["s"] / ca["s"] * ca["ty"])
            for f, r in cam.items()}


def ruim(q, f, regras, claro=140, sat=105, auto=True):
    """máscara (bool) do que está na frente da placa no quadro f, em px do vídeo"""
    h, w = q.shape[:2]
    m = np.zeros((h, w), bool)
    if auto:
        qf = q.astype(np.float32); lu = qf @ LU; st = qf.max(-1) - qf.min(-1)
        m |= cv2.dilate(((lu > claro) & (st < 60)).astype(np.uint8), np.ones((21, 21), np.uint8)) > 0
        m |= cv2.dilate((st > sat).astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
    for r in regras:
        if not r["de"] <= f <= r["ate"]:
            continue
        if "caixa" in r:
            x0, y0, x1, y1 = map(int, r["caixa"]); m[max(0, y0):y1, max(0, x0):x1] = True
        if "circulo" in r:
            cx, cy, rr = r["circulo"]; yy, xx = np.ogrid[:h, :w]
            m |= (xx - cx) ** 2 + (yy - cy) ** 2 > rr ** 2
    return m


def le_fora(caminho):
    if not caminho:
        return []
    try:
        return json.load(open(caminho))
    except (OSError, ValueError) as e:
        falha(f"fora.json ilegível: {e}", 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("camera"); ap.add_argument("saida")
    ap.add_argument("--de", type=int, required=True); ap.add_argument("--ate", type=int, required=True)
    ap.add_argument("--ancora", type=int, required=True); ap.add_argument("--janela", action="store_true")
    ap.add_argument("--fora"); ap.add_argument("--claro", type=float, default=140); ap.add_argument("--sat", type=float, default=105)
    ap.add_argument("--sem-auto", action="store_true")
    a = ap.parse_args()
    A, B = a.de, a.ate
    cam0 = le_camera(a.camera)
    falta_cam = [f for f in list(range(A, B + 1)) + [a.ancora] if f not in cam0]
    if falta_cam:
        falha(f"a câmera não tem os quadros {falta_cam[:5]}{'...' if len(falta_cam) > 5 else ''}", 1)
    regras = le_fora(a.fora)
    cam = relativa(cam0, a.ancora)
    W, H = tamanho(a.video)
    xs, ys = [], []
    for f in range(A, B + 1):
        c = cam[f]; s = c["s"]
        xs += [-c["tx"] / s, (W - c["tx"]) / s]; ys += [-c["ty"] / s, (H - c["ty"]) / s]
    ox, oy = int(np.floor(min(xs))), int(np.floor(min(ys)))
    PW, PH = int(np.ceil(max(xs))) - ox, int(np.ceil(max(ys))) - oy
    pilha, fs, guarda = [], [], {}
    for f, q in quadros(a.video, A, B):
        c = cam[f]; s = c["s"]
        qf = q.astype(np.float32)
        qf[ruim(q, f, regras, a.claro, a.sat, not a.sem_auto)] = np.nan
        M = np.float32([[s, 0, c["tx"] + s * ox], [0, s, c["ty"] + s * oy]])  # tela = s * (placa + o) + t
        w_ = cv2.warpAffine(qf, M, (PW, PH), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderMode=cv2.BORDER_CONSTANT,
                            borderValue=(np.nan, np.nan, np.nan))  # escalar só valeria para o canal R
        pilha.append(w_.astype(np.float16)); fs.append(f)
        if not a.janela and (f - A) % 4 == 0:
            guarda[f] = q
    if len(fs) != B - A + 1:
        falha(f"o vídeo acaba antes do quadro {B}", 1)
    nitidos = [w_ for f, w_ in zip(fs, pilha) if abs(cam[f]["s"] - 1) < 0.03] or pilha
    with np.errstate(all="ignore"):
        P = np.nanmedian(np.stack(nitidos).astype(np.float32), axis=0)
        P2 = np.nanmedian(np.stack(pilha).astype(np.float32), axis=0)
    P = np.where(np.isnan(P), P2, P)
    falta = np.isnan(P).any(-1)
    P = np.nan_to_num(P).clip(0, 255).astype(np.uint8)
    info = dict(ox=ox, oy=oy, largura=PW, altura=PH, ancora=a.ancora, de=A, ate=B, sem_dado=round(float(falta.mean()), 4))
    lado = os.path.splitext(a.saida)[0] + ".json"
    if a.janela:
        rgba = np.dstack([P, np.where(falta, 0, 255).astype(np.uint8)])
        cv2.imwrite(a.saida, cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA), [cv2.IMWRITE_PNG_COMPRESSION, 6])
        json.dump(info, open(lado, "w"))
        ok(f"placa curta {PW}x{PH} com alfa, f{A}-f{B}, {100 * info['sem_dado']:.1f} % transparente", comando=None,
           motivo="desenhar por cima da placa larga só nesse trecho, com a mesma câmera", saida=os.path.abspath(a.saida), **info)
        return
    if falta.any():  # o que nunca apareceu fica com a cor mediana (o inpaint inventava borda colorida)
        P[falta] = np.median(P[~falta], 0).astype(np.uint8)
    cv2.imwrite(a.saida, P[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 95])
    conf = {}
    for f, q in guarda.items():  # placa levada de volta à tela contra o original, sem o que está na frente
        c = cam[f]; s_ = c["s"]
        M = np.float32([[s_, 0, c["tx"] + s_ * ox], [0, s_, c["ty"] + s_ * oy]])
        tela = cv2.warpAffine(P.astype(np.float32), M, (W, H), flags=cv2.INTER_LINEAR)
        bom = ~ruim(q, f, regras, a.claro, a.sat, not a.sem_auto)
        conf[f"f{f}"] = round(float(np.abs(tela - q.astype(np.float32))[bom].mean() / 255), 4) if bom.any() else None
    info["conferencia"] = conf
    json.dump(info, open(lado, "w"))
    pior = max((v for v in conf.values() if v is not None), default=None)
    ok(f"placa {PW}x{PH}, f{A}-f{B}, âncora f{a.ancora}, {100 * info['sem_dado']:.1f} % sem dado; reprojeção pior {pior}",
       comando=None, motivo="reprojeção acima de ~0,02 longe da âncora pede registro absoluto (registra_cam.py) ou placas curtas (--janela)",
       saida=os.path.abspath(a.saida), **info)


if __name__ == "__main__":
    main()
