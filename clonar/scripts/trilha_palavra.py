#!/usr/bin/env python3
"""trilha_palavra.py: a trilha de cada palavra (ou emoji, caixa, cartão) quadro a quadro, pela tinta.

  trilha_palavra.py <video> <elementos.json> <saida.js> [--json saida.json]
      mede os elementos pedidos e grava window.TRILHAS para a composição (amostra/encaixa do modelo do montar).
  trilha_palavra.py <video> --auto <saida.json> [--largura 540]
      acha as palavras sozinho (legenda cinética): é o que o raio-x usa.

elementos.json: {"nome": {"de": 43, "ate": 62, "teste": "claro", "limiar": 70, "regiao": [x0, y0, x1, y1],
                 "escolha": "uniao", "dilata": 25, "rgb": [r, g, b]}, ...}  (regiao e rgb opcionais)
  teste: escuro (luma < limiar) | claro (luma > limiar) | sat (max - min > limiar) | naobranco (255 - min > limiar)
         | azul (B - max(R, G) > limiar) | cor (distância até rgb < limiar)
  escolha: uniao | maior | topo | baixo | esq | dir | centro (o componente mais perto do centro da região)
  dilata: px para juntar as letras de uma palavra antes de escolher o componente.
Cada quadro vira [x0, y0, x1, y1, ângulo, R, G, B, tinta] em px do vídeo (ângulo do eixo longo pelos momentos,
cor do miolo da tinta, tinta = pixels que passam no teste) ou null.

Automático (como acha uma palavra, em uma linha cada):
  letras: traço fino escuro (black-hat) ou claro (top-hat) com núcleo de 3 % do lado menor, componente com altura
    de 1,5 a 12 % do lado menor; palavra: letras da mesma altura, na mesma linha, com vão menor que 1/4 da altura;
  trilha: a mesma palavra de quadro em quadro (sobreposição), com pelo menos 4 quadros e altura parecida com a
    das outras palavras do vídeo; legenda cinética = pelo menos 6 palavras (e 0,4 por segundo) que nascem em
    momentos diferentes.
Vem do 4º clone (legenda estilo Apple), onde 27 trilhas assim montaram 22 elementos sem nenhum ease à mão.
"""
import argparse, json, os, subprocess, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import LU, falha, ok, quadros, tamanho  # noqa: E402

CAMPOS = ("de", "ate", "teste", "limiar", "regiao", "escolha", "dilata")


# ------------------------------------------------------------------ elementos pedidos
def le_elementos(caminho, w, h):
    try:
        E = json.load(open(caminho))
    except (OSError, ValueError) as e:
        falha(f"elementos.json ilegível: {e}", 1)
    out = {}
    for nome, v in E.items():
        if isinstance(v, list):  # forma curta do 4º clone: [de, ate, teste, limiar, regiao, escolha, dilata]
            v = dict(zip(CAMPOS, v))
        v = dict(dict(regiao=[0, 0, w, h], escolha="maior", dilata=5), **v)
        if v["teste"] not in ("escuro", "claro", "sat", "naobranco", "azul", "cor") or (v["teste"] == "cor" and "rgb" not in v):
            falha(f"{nome}: teste inválido ({v['teste']}; 'cor' pede rgb)", 1)
        if not (0 <= v["de"] <= v["ate"]):
            falha(f"{nome}: de/ate inválidos", 1)
        out[nome] = v
    return out


def mascara(im, teste, lim, rgb=None):
    lu = im @ LU
    if teste == "cor":
        return (np.abs(im - np.float32(rgb)).max(-1) < lim).astype(np.uint8)
    return {"escuro": lu < lim, "claro": lu > lim, "sat": (im.max(-1) - im.min(-1)) > lim,
            "naobranco": (255 - im.min(-1)) > lim, "azul": (im[..., 2] - im[..., :2].max(-1)) > lim}[teste].astype(np.uint8)


def mede_quadro(q, v):
    x0r, y0r, x1r, y1r = v["regiao"]
    im = q[y0r:y1r, x0r:x1r].astype(np.float32)
    m = mascara(im, v["teste"], v["limiar"], v.get("rgb"))
    dil = int(v["dilata"])
    n, lab, st, cen = cv2.connectedComponentsWithStats(cv2.dilate(m, np.ones((dil, dil), np.uint8)) if dil > 1 else m)
    comps = [j for j in range(1, n) if (m[lab == j] > 0).sum() >= 40]
    if not comps:
        return None
    if v["escolha"] == "uniao":
        sel = np.isin(lab, comps)
    else:
        cxr = (x1r - x0r) / 2
        chave = {"maior": lambda j: -st[j, 4], "topo": lambda j: st[j, 1], "baixo": lambda j: -(st[j, 1] + st[j, 3]),
                 "esq": lambda j: st[j, 0], "dir": lambda j: -(st[j, 0] + st[j, 2]),
                 "centro": lambda j: abs(cen[j][0] - cxr)}[v["escolha"]]
        sel = lab == min(comps, key=chave)
    ys, xs = np.nonzero(sel & (m > 0))
    cx, cy = xs.mean(), ys.mean()
    if len(xs) > 5:
        _, vec = np.linalg.eigh(np.cov(np.stack([xs - cx, ys - cy])))
        ang = float(np.degrees(np.arctan2(vec[1, 1], vec[0, 1])))
        ang = ang - 180 if ang > 90 else ang + 180 if ang <= -90 else ang
    else:
        ang = 0.0
    px = im[ys, xs]; l = px @ LU
    t = v["teste"]
    core = (px[l <= np.percentile(l, 15)] if t == "escuro" else px[l >= np.percentile(l, 85)] if t == "claro"
            else px[np.argsort(-(px.max(-1) - px.min(-1)))[:max(1, len(px) // 5)]])
    c = np.median(core, 0)
    return [int(xs.min() + x0r), int(ys.min() + y0r), int(xs.max() + x0r), int(ys.max() + y0r),
            round(ang, 1), int(c[0]), int(c[1]), int(c[2]), int(len(xs))]


def mede_pedidos(video, E):
    T = {k: dict(de=v["de"], ate=v["ate"], q=[None] * (v["ate"] - v["de"] + 1)) for k, v in E.items()}
    a, b = min(v["de"] for v in E.values()), max(v["ate"] for v in E.values())
    visto = a - 1
    for f, q in quadros(video, a, b):
        visto = f
        for k, v in E.items():
            if v["de"] <= f <= v["ate"]:
                T[k]["q"][f - v["de"]] = mede_quadro(q, v)
    if visto < b:
        falha(f"o vídeo acaba no quadro {visto}, antes do pedido ({b})", 1)
    return T


# ------------------------------------------------------------------ automático (legenda cinética)
def palavras_do_quadro(q):
    """caixas de palavra (x0, y0, x1, y1, polaridade, contraste, R, G, B, tinta) em px do quadro dado"""
    g = q.astype(np.float32) @ LU
    m = min(g.shape)
    k = max(5, int(round(0.03 * m)) | 1)
    ker = cv2.getStructuringElement(cv2.MORPH_RECT, (k, k))
    out = []
    for pol, resp in (("escuro", cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, ker)), ("claro", cv2.morphologyEx(g, cv2.MORPH_TOPHAT, ker))):
        tinta = (resp > 50).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(tinta, connectivity=8)
        # letra: altura de 2 a 12 % do lado menor; "I" e "l" são cheios (só o bloco largo e cheio não é letra)
        letras = [j for j in range(1, n) if 0.02 * m <= st[j, 3] <= 0.12 * m and st[j, 2] <= 12 * st[j, 3] and st[j, 4] >= 12
                  and 0.1 <= st[j, 4] / max(1, st[j, 2] * st[j, 3]) and (st[j, 4] / max(1, st[j, 2] * st[j, 3]) <= 0.85 or st[j, 2] <= 0.35 * st[j, 3])]
        letras.sort(key=lambda j: st[j, 0])
        pai = {j: j for j in letras}
        def raiz(j):
            while pai[j] != j:
                pai[j] = pai[pai[j]]; j = pai[j]
            return j
        for i, a in enumerate(letras):
            xa, ya, wa, ha = st[a, :4]
            for b in letras[i + 1:]:
                xb, yb, wb, hb = st[b, :4]
                if xb - (xa + wa) > 0.25 * max(ha, hb):
                    break  # ordenadas por x: as próximas estão ainda mais longe
                if max(ha, hb) / min(ha, hb) < 1.6 and min(ya + ha, yb + hb) - max(ya, yb) >= 0.5 * min(ha, hb):
                    pai[raiz(b)] = raiz(a)
        grupos = {}
        for j in letras:
            grupos.setdefault(raiz(j), []).append(j)
        for js in grupos.values():
            x0 = min(st[j, 0] for j in js); y0 = min(st[j, 1] for j in js)
            x1 = max(st[j, 0] + st[j, 2] for j in js); y1 = max(st[j, 1] + st[j, 3] for j in js)
            sel = np.isin(lab[y0:y1, x0:x1], js)
            r = resp[y0:y1, x0:x1][sel]
            px = q[y0:y1, x0:x1][sel]
            core = px[r >= np.median(r)]
            c = np.median(core, 0)
            if r.mean() < 90 or (len(js) == 1 and (y1 - y0 < 0.03 * m or r.mean() < 110)):
                continue  # pouco contraste, ou letra solta pequena: textura, cabelo, borda
            out.append((int(x0), int(y0), int(x1), int(y1), pol, float(r.mean()), int(c[0]), int(c[1]), int(c[2]), int(sel.sum())))
    # o vão claro entre letras escuras (e o contrário) também é "traço": fica a polaridade com mais tinta
    def dentro(a, b):
        i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
        return i / max(1, (a[2] - a[0]) * (a[3] - a[1]))
    return [a for a in out if not any(b[4] != a[4] and b[9] > a[9] and dentro(a, b) >= 0.6 for b in out)]


def iou(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return i / max(1e-9, (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i)


def acha_palavras(fonte, esc, fps=30.0, n_quadros=None):
    """fonte: (f, quadro) reduzidos; esc: px do original por px da análise. Devolve (trilhas, é_legenda, resumo)."""
    vivas, todas = [], []
    for f, q in fonte:
        cand = palavras_do_quadro(q)
        livres = set(range(len(cand)))
        pares = sorted(((iou(t["c"][-1], c[:4]), ti, ci) for ti, t in enumerate(vivas) for ci, c in enumerate(cand)
                        if c[4] == t["pol"]), reverse=True)
        usadas = set()
        for s, ti, ci in pares:
            if s < 0.3 or ti in usadas or ci not in livres:
                continue
            t = vivas[ti]; c = cand[ci]
            t["f"].append(f); t["c"].append(c[:4]); t["k"].append(c[5]); t["rgb"].append(c[6:9]); t["tinta"].append(c[9]); t["perdido"] = 0
            usadas.add(ti); livres.discard(ci)
        for ti, t in enumerate(vivas):
            if ti not in usadas:
                t["perdido"] += 1
        for ci in livres:
            c = cand[ci]
            vivas.append(dict(f=[f], c=[c[:4]], k=[c[5]], rgb=[c[6:9]], tinta=[c[9]], pol=c[4], perdido=0))
        todas += [t for t in vivas if t["perdido"] > 2]
        vivas = [t for t in vivas if t["perdido"] <= 2]
    todas += vivas
    tr = [t for t in todas if len(t["f"]) >= 4]
    for t in tr:
        h = np.array([c[3] - c[1] for c in t["c"]], float)
        t["altura"] = float(np.median(h)); t["firme"] = float(h.std() / max(1.0, t["altura"])) < 0.3
    tr = [t for t in tr if t["firme"]]
    if tr:  # palavras de legenda têm a mesma letra: fica quem está perto da altura mais comum (pesada pela duração)
        hs = np.repeat([t["altura"] for t in tr], [len(t["f"]) for t in tr])
        moda = float(np.median(hs))
        tr = [t for t in tr if 0.55 * moda <= t["altura"] <= 1.8 * moda]
    tr.sort(key=lambda t: t["f"][0])
    nascem = len({t["f"][0] // max(1, int(round(fps / 5))) for t in tr})  # momentos diferentes (janelas de 0,2 s)
    dur = (n_quadros or (max((t["f"][-1] for t in tr), default=0) + 1)) / fps
    legenda = len(tr) >= max(6, 0.4 * dur) and nascem >= 4
    out = []
    for i, t in enumerate(tr):
        f = np.array(t["f"]); c = np.array(t["c"], float) * esc; k = np.array(t["k"])
        plato = float(np.median(k)); acima = np.nonzero(k >= 0.9 * plato)[0]
        w = c[:, 2] - c[:, 0]; wf = float(np.median(w))
        out.append(dict(nome=f"P{i + 1}", f=f.tolist(), caixa=[[round(x, 1) for x in r] for r in c.tolist()],
                        polaridade=t["pol"], cor=[int(x) for x in np.median(np.array(t["rgb"]), 0)],
                        altura=round(t["altura"] * esc, 1), contraste=[round(float(x), 1) for x in k],
                        entra_q=int(acima[0]) if len(acima) else 0, sai_q=int(len(k) - 1 - acima[-1]) if len(acima) else 0,
                        cresce=round(float(w[0] / max(1.0, wf)), 2)))
    return out, legenda, dict(palavras=len(out), momentos=nascem, legenda=legenda)


def para_raiox(p):
    """trilha de palavra no formato das trilhas do raio-x (f, cx, cy, w, h em px do original, sem buraco)"""
    f = np.array(p["f"]); c = np.array(p["caixa"])
    fs = np.arange(f[0], f[-1] + 1)
    g = lambda v: np.interp(fs, f, v)
    return dict(f=fs.tolist(), cx=g((c[:, 0] + c[:, 2]) / 2), cy=g((c[:, 1] + c[:, 3]) / 2), w=g(c[:, 2] - c[:, 0]),
                h=g(c[:, 3] - c[:, 1]), nome=p["nome"], palavra=True)


# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("elementos", nargs="?"); ap.add_argument("saida", nargs="?")
    ap.add_argument("--auto", metavar="SAIDA_JSON"); ap.add_argument("--largura", type=int, default=540)
    ap.add_argument("--json", help="também grava as trilhas em JSON")
    a = ap.parse_args()
    if not os.path.exists(a.video):
        falha(f"vídeo não encontrado: {a.video}", 1)
    w, h = tamanho(a.video)
    if a.auto:
        larg = min(a.largura, w)
        r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                           "-of", "csv=p=0", a.video], capture_output=True, text=True).stdout.strip().split("/")
        fps = int(r[0]) / int(r[1]) if len(r) == 2 else 30.0
        P, legenda, res = acha_palavras(quadros(a.video, largura=larg), w / larg, fps)
        json.dump(dict(legenda=legenda, palavras=P), open(a.auto, "w"), ensure_ascii=False)
        ok(f"{res['palavras']} palavra(s) em {res['momentos']} momento(s): "
           + ("texto entra palavra a palavra (legenda cinética ou interface com muito texto)" if legenda else "não é texto palavra a palavra"),
           comando=None, motivo="use as caixas para escrever o elementos.json da ficha e medir cada palavra com precisão",
           saida=os.path.abspath(a.auto), legenda=legenda)
        return
    if not (a.elementos and a.saida):
        falha("uso: trilha_palavra.py <video> <elementos.json> <saida.js> | <video> --auto <saida.json>", 1)
    E = le_elementos(a.elementos, w, h)
    T = mede_pedidos(a.video, E)
    open(a.saida, "w").write("window.TRILHAS=" + json.dumps(T, separators=(",", ":")) + ";\n")
    if a.json:
        json.dump(T, open(a.json, "w"), separators=(",", ":"))
    resumo_el = {k: dict(quadros=f"f{v['de']}-f{v['ate']}", medidos=sum(x is not None for x in v["q"]), total=len(v["q"]),
                         primeiro=v["q"][0], ultimo=v["q"][-1]) for k, v in T.items()}
    falta = [k for k, v in resumo_el.items() if v["medidos"] < v["total"]]
    ok(f"{len(T)} trilha(s) em {os.path.basename(a.saida)}" + (f"; com buraco: {', '.join(falta)}" if falta else "; nenhuma com buraco"),
       comando=None, motivo="copiar para hf/trilhas.js e desenhar cada elemento com amostra() e encaixa() do modelo",
       saida=os.path.abspath(a.saida), elementos=resumo_el)


if __name__ == "__main__":
    main()
