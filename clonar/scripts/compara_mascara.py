#!/usr/bin/env python3
"""compara_mascara.py: a nota da camada recriada, medida só onde ela está (máscara por quadro).

  compara_mascara.py <original> <clone> <mascara> [--placa placa.mp4] [--margem 12] [--elementos a,b,...]
                     [--prev clone_anterior.mp4] [--json saida.json]

Para clone com placa de vídeo (a pessoa filmada é o próprio original, por baixo): a distância do quadro inteiro
fica artificialmente baixa, porque a placa é igual ao original. Aqui só contam os pixels da camada.
mascara: lista [{"de": f0, "ate": f1, "caixa": [x0, y0, x1, y1], "pegada": "x.png"?}] em px do original (o formato do
  fundo.py; com "pegada", só os pixels claros do PNG do tamanho da caixa contam: a tinta da palavra, não o vão), ou um
  trilhas.js / trilhas.json (trilha_palavra.py): a máscara de cada quadro é a união das caixas medidas naquele quadro
  (--elementos escolhe quais), alargada --margem px. Máscara justa por quadro: fundo parado fora da camada não dilui.
Números (pesados pelos pixels da máscara, quadros em que ela existe):
  distancia: |original - clone| / 255 na grade do compare.py (96 colunas, sem achatar a altura), o alvo do kit;
  distancia_fina: o mesmo em 540 colunas (borda de letra e meio px de desvio aparecem);
  com --placa, a máscara de cada quadro também soma onde o clone desenhou (|clone - placa| > 10, dentro das caixas das
  peças vivas): peça fora do lugar conta dos dois lados;
  correlacao e pico: energia de movimento da camada (|L_f - L_f-1| na máscara, com L = quadro - placa quando há
    --placa, para o movimento da pessoa por baixo não contar), correlação e atraso (janelas de 2 s, -6 a +6 quadros);
  sem_camada: com --placa, a distância entre o original e a placa sozinha (o que daria não desenhar nada);
  blocos: distância fina por trecho de 20 quadros (com a rodada anterior, se --prev).
"""
import argparse, json, os, re, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import falha, ok, quadros, tamanho  # noqa: E402

GRADE, FINA, BLOCO = 96, 540, 20


def le_mascara(caminho, elementos, margem):
    txt = open(caminho).read()
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    try:
        J = json.loads(m.group(1) if m else txt)
    except ValueError as e:
        falha(f"máscara ilegível: {e}", 1)
    caixas = {}  # f -> [[x0, y0, x1, y1] ou [x0, y0, x1, y1, pegada (bool HxW)], ...]
    if isinstance(J, list):
        base = os.path.dirname(os.path.abspath(caminho))
        for r in J:
            c = list(r["caixa"])
            if r.get("pegada"):
                pg = cv2.imread(os.path.join(base, r["pegada"]), cv2.IMREAD_GRAYSCALE)
                if pg is None:
                    falha(f"pegada ilegível: {r['pegada']}", 1)
                c.append(pg > 127)
            for f in range(int(r["de"]), int(r["ate"]) + 1):
                caixas.setdefault(f, []).append(c)
    else:
        for nome, t in J.items():
            if elementos and nome not in elementos:
                continue
            for i, q in enumerate(t["q"]):
                if q:
                    caixas.setdefault(t["de"] + i, []).append([q[0] - margem, q[1] - margem, q[2] + margem, q[3] + margem])
    if not caixas:
        falha("a máscara está vazia", 1)
    return caixas


def mascara_do_quadro(caixas, w, h):
    m = np.zeros((h, w), np.float32)
    for c in caixas:
        x0, y0, x1, y1 = (int(v) for v in c[:4])
        if len(c) > 4:  # pegada: PNG do tamanho da caixa
            pg = c[4]; ya, xa = max(0, -y0), max(0, -x0)
            yb, xb = min(pg.shape[0], h - y0), min(pg.shape[1], w - x0)
            m[y0 + ya:y0 + yb, x0 + xa:x0 + xb] = np.maximum(m[y0 + ya:y0 + yb, x0 + xa:x0 + xb], pg[ya:yb, xa:xb])
        else:
            m[max(0, y0):min(h, int(np.ceil(c[3])) + 1), max(0, x0):min(w, int(np.ceil(c[2])) + 1)] = 1
    return m


def reduz(im, largura):
    h, w = im.shape[:2]
    return cv2.resize(im, (largura, max(1, int(round(h * largura / w)))), interpolation=cv2.INTER_AREA)


def corr(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 and x.std() > 1e-9 and y.std() > 1e-9 else float("nan")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original"); ap.add_argument("clone"); ap.add_argument("mascara")
    ap.add_argument("--placa"); ap.add_argument("--margem", type=float, default=12); ap.add_argument("--elementos")
    ap.add_argument("--prev"); ap.add_argument("--json")
    a = ap.parse_args()
    for v in (a.original, a.clone, a.placa, a.prev):
        if v and not os.path.exists(v):
            falha(f"não encontrado: {v}", 1)
    W, H = tamanho(a.original)
    if tamanho(a.clone) != (W, H):
        falha(f"o clone não tem o tamanho do original ({W}x{H})", 1)
    caixas = le_mascara(a.mascara, set(a.elementos.split(",")) if a.elementos else None, a.margem)
    fluxos = [quadros(a.original), quadros(a.clone)] + [quadros(v) for v in (a.placa, a.prev) if v]
    tem_p, tem_prev = bool(a.placa), bool(a.prev)
    S = dict(g=[0.0, 0.0], f=[0.0, 0.0], gb=[0.0, 0.0], fb=[0.0, 0.0])  # soma das diferenças e dos pesos
    eo, ec, por_q, ant = [], [], [], None
    for itens in zip(*fluxos):
        f = itens[0][0]
        o, c = itens[0][1].astype(np.float32), itens[1][1].astype(np.float32)
        p = itens[2][1].astype(np.float32) if tem_p else None
        pv = itens[-1][1].astype(np.float32) if tem_prev else None
        mk = mascara_do_quadro(caixas.get(f, []), W, H)
        if tem_p:  # onde o clone desenhou também conta (peça fora da pegada do original), dentro das caixas das peças vivas
            zona = mascara_do_quadro([c_[:4] for c_ in caixas.get(f, [])], W, H)
            mk = np.maximum(mk, zona * cv2.dilate((np.abs(c - p).max(-1) > 10).astype(np.uint8), np.ones((5, 5), np.uint8)))
        mg, mf = reduz(mk, GRADE) >= 0.5, reduz(mk, FINA) > 0.5
        og, cg, of_, cf = reduz(o, GRADE), reduz(c, GRADE), reduz(o, FINA), reduz(c, FINA)
        lo, lc = (of_ - reduz(p, FINA), cf - reduz(p, FINA)) if tem_p else (of_, cf)
        linha = dict(f=f, px=int(mf.sum()))
        if mf.any():
            dg = np.abs(og - cg)[mg].sum() / 255 / 3 if mg.any() else 0.0
            df = np.abs(of_ - cf)[mf].sum() / 255 / 3
            S["g"][0] += dg; S["g"][1] += mg.sum(); S["f"][0] += df; S["f"][1] += mf.sum()
            linha.update(fina=df / mf.sum())
            if tem_p:
                pg, pf = reduz(p, GRADE), reduz(p, FINA)
                S["gb"][0] += np.abs(og - pg)[mg].sum() / 255 / 3 if mg.any() else 0.0; S["gb"][1] += mg.sum()
                S["fb"][0] += np.abs(of_ - pf)[mf].sum() / 255 / 3; S["fb"][1] += mf.sum()
            if tem_prev:
                linha.update(prev=float(np.abs(of_ - reduz(pv, FINA))[mf].mean() / 255))
        if ant is not None:
            u = mf | ant[0]
            if u.any():
                eo.append((f, float(np.abs(lo - ant[1])[u].mean()), float(np.abs(lc - ant[2])[u].mean())))
        ant = (mf, lo, lc)
        por_q.append(linha)
    n = len(por_q)
    if n == 0:
        falha("não li nenhum quadro", 2)
    fs_e = np.array([x[0] for x in eo]); e_o = np.array([x[1] for x in eo]); e_c = np.array([x[2] for x in eo])
    # atraso por janela de 2 s (como o compare.py): o deslocamento que mais correlaciona, de -6 a +6 quadros
    pico, janelas = 0, []
    for j0 in range(0, len(e_o), 50):
        x, y = e_o[j0:j0 + 50], e_c[j0:j0 + 50]
        if len(x) < 9 or x.max() < 1.0 or x.std() < 1e-6:
            continue
        melhor, lag = -2.0, 0
        for L in range(-6, 7):
            xa = x[max(0, -L):len(x) - max(0, L)]; ya = y[max(0, L):len(y) - max(0, -L)]
            cc = corr(xa, ya)
            if cc == cc and cc > melhor:
                melhor, lag = cc, L
        janelas.append(dict(quadros=f"f{int(fs_e[j0])}-f{int(fs_e[min(len(fs_e), j0 + 50) - 1])}", atraso=lag,
                            correlacao=round(corr(x, y), 3)))
        pico = max(pico, abs(lag))
    blocos = []
    for b0 in range(0, n, BLOCO):
        tr = [x for x in por_q[b0:b0 + BLOCO] if "fina" in x]
        if not tr:
            continue
        pw = np.array([x["px"] for x in tr], float)
        bl = dict(a=por_q[b0]["f"], b=por_q[min(n, b0 + BLOCO) - 1]["f"],
                  dist=round(float(np.average([x["fina"] for x in tr], weights=pw)), 4),
                  pior_quadro=max(tr, key=lambda x: x["fina"])["f"])
        if tem_prev:
            bl["anterior"] = round(float(np.average([x["prev"] for x in tr], weights=pw)), 4)
        blocos.append(bl)
    r = lambda k: round(S[k][0] / S[k][1], 4) if S[k][1] else None
    res = dict(distancia=r("g"), distancia_fina=r("f"), correlacao=round(corr(e_o, e_c), 3),
               movimento=round(float(e_c.sum() / max(1e-9, e_o.sum())), 2), pico_quadros=pico, janelas=janelas,
               quadros=n, quadros_com_mascara=sum(1 for x in por_q if "fina" in x),
               mascara_media=round(float(np.mean([x["px"] for x in por_q]) / ((FINA * H / W) * FINA)), 4),
               sem_camada=dict(distancia=r("gb"), distancia_fina=r("fb")) if tem_p else None,
               blocos=blocos, como=f"grade {GRADE} colunas e fina {FINA} colunas, só nos pixels da máscara"
               + ("; movimento da camada = quadro - placa" if tem_p else ""))
    if a.json:
        json.dump(res, open(a.json, "w"), ensure_ascii=False, indent=1)
    piores = sorted(blocos, key=lambda b: -b["dist"])[:3]
    ok(f"na máscara: distância {res['distancia']} (fina {res['distancia_fina']}), correlação {res['correlacao']}, pico {pico} q"
       + (f"; sem camada daria {res['sem_camada']['distancia']} (fina {res['sem_camada']['distancia_fina']})" if tem_p else ""),
       comando=None, motivo=("corrigir primeiro " + ", ".join(f"f{b['a']}-f{b['b']} ({b['dist']})" for b in piores)) if piores else "",
       **{k: v for k, v in res.items() if k != "blocos"}, piores=piores)


if __name__ == "__main__":
    main()
