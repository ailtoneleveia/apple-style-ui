#!/usr/bin/env python3
"""aparicao.py: como cada peça entra e sai (opacidade, deslocamento, escala e desfoque por quadro), medida contra a placa.

  aparicao.py <original> <placa.mp4> <camada.json> <saida.js> [--nomes a,b] [--borda 8] [--json saida.json]

camada.json: [{"nome", "de", "ate", "caixa": [x0, y0, x1, y1], "tipo": "escuro"|"branco"|"opaco", "cor": [r, g, b]?,
               "assentado": f?}] em px do original (a caixa assentada; de/ate = primeiro e último quadro visível).
A peça assentada (quadro `assentado`, ou o de maior contraste com a placa) vira o molde: texto de uma cor só vira
alfa pela projeção (original - placa) na direção (cor - placa); peça opaca (caixa rosa com texto, cartão, emoji)
vira alfa 1 na caixa com a cor do próprio original. As outras peças da camada.json (vizinhas no recorte) ficam fora
da conta. Peça dentro de outra (texto no cartão) não serve: o fundo dela é a outra peça, não a placa. Em cada quadro das bordas da vida da peça (os `borda` primeiros e
últimos), procura o molde transformado que explica o original sobre a placa:
  original ≈ placa · (1 - a·A') + a·(L·A')',  com ' = desloca (dx, dy), escala k no centro e desfoca σ (gaussiana)
por descida coordenada (σ, dx, dy, k; a em forma fechada). Os quadros do meio ficam assentados (a = 1).
Saída: window.APARICAO = {nome: {de, ate, q: [[a, dx, dy, k, σ, resto], ...]}} (um por quadro de de-2 a ate+2;
resto = fração do sinal da peça que o ajuste não explica) e o resumo de cada entrada e saída.
Na composição: desenhe a peça na caixa assentada e aplique, no quadro contínuo F (interpolado), translate(dx, dy),
scale(k) no centro, filter blur(σ) e globalAlpha a. A placa tem de ser a limpa (placa_video.py).
"""
import argparse, json, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import falha, ok, quadros, tamanho  # noqa: E402

SIGMAS = [0, 0.7, 1.5, 2.5, 3.5, 5, 7, 9, 12, 16, 22]
MX, MY = 48, 24  # margem do recorte em volta da caixa: cabe o deslocamento e o desfoque da entrada


def transforma(img, dx, dy, k, sg, cx, cy):
    M = np.float32([[k, 0, cx - k * cx + dx], [0, k, cy - k * cy + dy]])
    out = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return cv2.GaussianBlur(out, (0, 0), sg) if sg > 0 else out


def ajusta(O, B, AL, cx, cy, ini, usa):
    """AL: canais [A, L·A (3)] do molde no recorte; usa: pixels que contam (as outras peças ficam de fora).
    Devolve (a, dx, dy, k, σ, resto)."""
    alvo = (O - B) * usa; sinal = float((alvo ** 2).sum()) + 1e-6
    memo = {}
    def erro(dx, dy, k, sg):
        ch = (dx, dy, round(k, 3), sg)
        if ch in memo:
            return memo[ch]
        T = transforma(AL, dx, dy, k, sg, cx, cy)
        D = (T[..., 1:] - B * T[..., :1]) * usa
        dd = float((D * D).sum())
        a = float(np.clip((alvo * D).sum() / dd, 0, 1.3)) if dd > 1e-6 else 0.0
        e = float(((alvo - a * D) ** 2).sum())
        memo[ch] = (e, a)
        return memo[ch]
    dx, dy, k, sg = ini
    for _ in range(3):
        sg = min(SIGMAS, key=lambda s: erro(dx, dy, k, s)[0])
        dx = min(range(-MX + 8, MX - 7), key=lambda x: erro(x, dy, k, sg)[0])
        dy = min(range(-MY + 6, MY - 5), key=lambda y: erro(dx, y, k, sg)[0])
        k = min((0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.2), key=lambda z: erro(dx, dy, z, sg)[0])
    e, a = erro(dx, dy, k, sg)
    if a < 0.02:
        dx, dy, k, sg = 0, 0, 1.0, 0
    return [round(a, 3), dx, dy, k, sg, round(e / sinal, 3)]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original"); ap.add_argument("placa"); ap.add_argument("camada"); ap.add_argument("saida")
    ap.add_argument("--nomes"); ap.add_argument("--borda", type=int, default=8); ap.add_argument("--json")
    a = ap.parse_args()
    for v in (a.original, a.placa, a.camada):
        if not os.path.exists(v):
            falha(f"não encontrado: {v}", 1)
    if tamanho(a.original) != tamanho(a.placa):
        falha("a placa não tem o tamanho do original", 1)
    W, H = tamanho(a.original)
    todos = json.load(open(a.camada))
    C = [e for e in todos if not a.nomes or e["nome"] in a.nomes.split(",")]
    if not C:
        falha("nenhuma peça para medir", 1)
    precisa = {}
    for e in C:
        e["r"] = [max(0, e["caixa"][0] - MX), max(0, e["caixa"][1] - MY), min(W, e["caixa"][2] + MX + 1), min(H, e["caixa"][3] + MY + 1)]
        fs = set(range(e["de"] - 2, e["de"] + a.borda)) | set(range(e["ate"] - a.borda + 1, e["ate"] + 3)) | set(range(e["de"], e["ate"] + 1, 4))
        for f in fs:
            precisa.setdefault(f, []).append(e["nome"])
    rec = {e["nome"]: {} for e in C}
    por_nome = {e["nome"]: e for e in C}
    for (f, o), (_, b) in zip(quadros(a.original), quadros(a.placa)):
        for nome in precisa.get(f, []):
            x0, y0, x1, y1 = por_nome[nome]["r"]
            rec[nome][f] = (o[y0:y1, x0:x1].astype(np.float32), b[y0:y1, x0:x1].astype(np.float32))
    res, txt = {}, []
    for e in C:
        R = rec[e["nome"]]
        vida = [f for f in range(e["de"], e["ate"] + 1) if f in R]
        if not vida:
            continue
        fs_ = e.get("assentado") or max(vida, key=lambda f: float(np.abs(R[f][0] - R[f][1]).sum()))
        O, B = R[fs_]
        x0, y0 = e["r"][:2]
        bx = [e["caixa"][0] - x0, e["caixa"][1] - y0, e["caixa"][2] - x0 + 1, e["caixa"][3] - y0 + 1]
        dentro = np.zeros(O.shape[:2], np.float32); dentro[bx[1]:bx[3], bx[0]:bx[2]] = 1
        if e.get("tipo") in ("escuro", "branco"):
            cor = np.float32(e.get("cor") or ([24, 20, 20] if e["tipo"] == "escuro" else [253, 252, 254]))
            d = cor - B
            A = np.clip(((O - B) * d).sum(-1) / np.maximum((d * d).sum(-1), 1.0), 0, 1) * cv2.dilate(dentro, np.ones((7, 7), np.uint8))
            L = np.broadcast_to(cor, O.shape)
        else:
            A, L = dentro, O
        AL = np.dstack([A, L * A[..., None]]).astype(np.float32)
        cx, cy = (bx[0] + bx[2]) / 2, (bx[1] + bx[3]) / 2
        # as outras peças no recorte (vizinhas de linha, caixa de cima) não entram na conta; a que contém esta não sai
        usa = np.ones(O.shape[:2], np.float32)
        for o_ in todos:
            c_ = o_["caixa"]
            if o_["nome"] == e["nome"] or (c_[0] <= e["caixa"][0] and c_[1] <= e["caixa"][1] and c_[2] >= e["caixa"][2] and c_[3] >= e["caixa"][3]):
                continue
            usa[max(0, c_[1] - 4 - y0):max(0, c_[3] + 5 - y0), max(0, c_[0] - 4 - x0):max(0, c_[2] + 5 - x0)] = 0
        usa[bx[1]:bx[3], bx[0]:bx[2]] = 1
        usa = usa[..., None]
        q, ini = [], (0, 0, 1.0, 0)
        borda = set(range(e["de"] - 2, e["de"] + a.borda)) | set(range(e["ate"] - a.borda + 1, e["ate"] + 3))
        for f in range(e["de"] - 2, e["ate"] + 3):
            if f not in R:
                q.append([0, 0, 0, 1.0, 0, 0] if (f < e["de"] or f > e["ate"]) else [1, 0, 0, 1.0, 0, 0]); continue
            if f not in borda and e["de"] + a.borda <= f <= e["ate"] - a.borda:
                q.append([1, 0, 0, 1.0, 0, 0]); continue
            r = ajusta(R[f][0], R[f][1], AL, cx, cy, ini if f < fs_ else (0, 0, 1.0, 0), usa)
            q.append(r); ini = tuple(r[1:5]) if r[0] > 0.05 else ini
        res[e["nome"]] = dict(de=e["de"] - 2, ate=e["ate"] + 2, assentado=fs_, q=q)
        ent = [x for x in q[:a.borda + 2] if 0.03 < x[0] < 0.97]
        sai = [x for x in q[-(a.borda + 2):] if 0.03 < x[0] < 0.97]
        txt.append(dict(nome=e["nome"], entrada_q=len(ent), entrada_1o=ent[0] if ent else None, saida_q=len(sai), saida_1o=sai[0] if sai else None))
    open(a.saida, "w").write("window.APARICAO=" + json.dumps(res, separators=(",", ":")) + ";\n")
    if a.json:
        json.dump(res, open(a.json, "w"), separators=(",", ":"))
    ok(f"{len(res)} peça(s) medidas; entrada média de {np.mean([t['entrada_q'] for t in txt]):.1f} quadros, saída de "
       f"{np.mean([t['saida_q'] for t in txt]):.1f}", comando=None,
       motivo="na composição, aplicar [a, dx, dy, k, σ] do quadro contínuo F em cada peça desenhada na caixa assentada",
       saida=os.path.abspath(a.saida), pecas=txt)


if __name__ == "__main__":
    main()
