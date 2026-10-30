#!/usr/bin/env python3
"""registra_cam.py: registro absoluto da câmera, cada quadro direto contra a placa (sem acumular erro).

  registra_cam.py <video> <camera.json> <saida.json> --placa placa.jpg:A-B [--placa outra.png:C-D ...]
                  [--fora fora.json] [--claro 140] [--sat 105] [--sem-auto] [--escala 0.5]

A câmera encadeada (camtrack.py, quadro a quadro) acumula alguns px de erro. Aqui, para cada quadro f de cada
trecho, a placa do trecho (com o <placa>.json que o placa.py grava) é levada para a tela pela câmera atual e o
quadro do original é alinhado contra ela (ECC afim em cinza reduzido, sem o que está na frente e sem o buraco
transparente das placas .png). A correção vira escala e translação na câmera absoluta. Os quadros fora dos
trechos ficam como estavam. Grava a câmera corrigida (mesmo formato, com ref_cc = nota do ECC).
No 4º clone corrigiu até 17 px e baixou a reprojeção da placa de longe de 0,025-0,05 para 0,011-0,018.
"""
import argparse, json, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import LU, falha, ok, quadros  # noqa: E402
from placa import le_camera, le_fora, ruim  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("camera"); ap.add_argument("saida")
    ap.add_argument("--placa", action="append", required=True, help="arquivo:A-B (a placa e o trecho que ela cobre)")
    ap.add_argument("--fora"); ap.add_argument("--claro", type=float, default=140); ap.add_argument("--sat", type=float, default=105)
    ap.add_argument("--sem-auto", action="store_true"); ap.add_argument("--escala", type=float, default=0.5)
    a = ap.parse_args()
    cam = {f: dict(r) for f, r in le_camera(a.camera).items()}
    regras = le_fora(a.fora)
    trechos = []
    for p in a.placa:
        try:
            arq, faixa = p.rsplit(":", 1); A, B = map(int, faixa.split("-"))
            im = cv2.imread(arq, cv2.IMREAD_UNCHANGED); pj = json.load(open(os.path.splitext(arq)[0] + ".json"))
        except (ValueError, OSError) as e:
            falha(f"--placa {p}: {e}", 1)
        if im is None:
            falha(f"--placa {p}: imagem ilegível", 1)
        alfa = im[..., 3].astype(np.float32) if im.ndim == 3 and im.shape[2] == 4 else None
        trechos.append((A, B, im[..., :3][..., ::-1].astype(np.float32), alfa, pj))
    A0, B0 = min(t[0] for t in trechos), max(t[1] for t in trechos)
    crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 100, 1e-6)
    k = a.escala; feitos, correcao, notas = 0, [], []
    for f, q in quadros(a.video, A0, B0):
        t = next((t for t in trechos if t[0] <= f <= t[1]), None)
        if t is None or f not in cam:
            continue
        _, _, P, alfa, pj = t
        if pj["ancora"] not in cam:
            falha(f"a câmera não tem o quadro-âncora f{pj['ancora']} da placa", 1)
        H, W = q.shape[:2]
        ca, c = cam[pj["ancora"]], cam[f]
        s = c["s"] / ca["s"]; tx = c["tx"] - s * ca["tx"]; ty = c["ty"] - s * ca["ty"]
        M = np.float32([[s, 0, tx + s * pj["ox"]], [0, s, ty + s * pj["oy"]]])
        tela = cv2.warpAffine(P, M, (W, H))
        mk = ~ruim(q, f, regras, a.claro, a.sat, not a.sem_auto)
        mk &= cv2.warpAffine(np.ones(P.shape[:2], np.float32) if alfa is None else alfa / 255, M, (W, H)) > 0.99
        sz = (int(W * k), int(H * k))
        g1 = cv2.resize(q.astype(np.float32) @ LU, sz, interpolation=cv2.INTER_AREA)
        g2 = cv2.resize(tela @ LU, sz, interpolation=cv2.INTER_AREA)
        m2 = cv2.resize(mk.astype(np.uint8), sz, interpolation=cv2.INTER_NEAREST)
        if m2.mean() < 0.05:
            continue  # quase nada da placa à vista: fica a câmera encadeada
        Wm = np.eye(2, 3, dtype=np.float32)
        try:
            cc, Wm = cv2.findTransformECC(g1, g2, Wm, cv2.MOTION_AFFINE, crit, m2, 3)
        except cv2.error:
            continue
        esc = float(np.sqrt(abs(np.linalg.det(Wm[:, :2])))); e, g = float(Wm[0, 2]) / k, float(Wm[1, 2]) / k
        # tela_orig(x) ~ tela_placa(W x): s_novo = s / esc, t_novo = (t - (e, g)) / esc, na câmera absoluta
        antes = (c["s"], c["tx"], c["ty"])
        c["s"], c["tx"], c["ty"] = c["s"] / esc, (c["tx"] - e) / esc, (c["ty"] - g) / esc
        c["ref_cc"] = round(float(cc), 4)
        correcao.append(max(abs(c["tx"] - antes[1]), abs(c["ty"] - antes[2]), abs(c["s"] / antes[0] - 1) * max(W, H)))
        notas.append(float(cc)); feitos += 1
    json.dump([cam[f] for f in sorted(cam)], open(a.saida, "w"), indent=0)
    if not feitos:
        falha("nenhum quadro registrado (placa fora da tela, ou nada sem máscara)", 2)
    ok(f"{feitos} quadro(s) registrados contra a placa; correção máxima {max(correcao):.1f} px, nota ECC mediana {np.median(notas):.3f}",
       comando=None, motivo="refazer as placas (placa.py) com a câmera corrigida e conferir a reprojeção",
       saida=os.path.abspath(a.saida), quadros=feitos, correcao_max_px=round(max(correcao), 1),
       ecc_mediana=round(float(np.median(notas)), 4))


if __name__ == "__main__":
    main()
