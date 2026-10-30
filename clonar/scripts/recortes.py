#!/usr/bin/env python3
"""recortes.py: confere se o clone recriou as peças ou só recortou o original, e se saiu mais borrado que ele.

  recortes.py <pasta do clone> [--clone video.mp4] [--json saida.json]

A regra (CLONAR.md, "Recriar, não recortar"): texto, ícone, cartão, pílula, botão e avatar desenhado são recriados
em HTML, CSS ou SVG. Recorte do original só para foto ou vídeo filmado de verdade, e cada raster de hf/assets/
(png, jpg, jpeg, webp, gif) é declarado em hf/assets/RECORTES.md, numa tabela:

  | arquivo | tipo | motivo |
  |---|---|---|
  | img/fundo.png | fundo | campo de luz do original, sem nenhuma peça por cima |
  | img/janelas/j*.png | foto | o mapa filmado, ... |

arquivo é relativo a hf/assets/ e aceita * e ?. tipo: foto, video ou fundo (TIPOS). Interface nunca é tipo válido.

Recortes (decide "aprovada"): raster sem declaração, ou declarado com tipo fora de TIPOS ou sem motivo, reprova.
Para cada raster sem declaração, diz se ele parece vir do original: template matching em escala 1/4 contra um
quadro a cada 3 do original (correlação normalizada, com o alfa como máscara); >= PARECE conta como recorte.

Nitidez (só registra, não reprova): energia do Laplaciano (média de L²) do clone e do original, nos pixels de borda
do original (Canny dilatado: as regiões dos elementos), um quadro a cada 3. razao = clone / original; abaixo de
BORRADO o clone saiu bem mais borrado. Sem --clone, usa saidas/final.mp4 ou a última rodada do bastidor.

Saída: JSON {ok, resumo, proximo, aprovada, motivo_reprovada, recortes, nitidez} no stdout (ok: true mesmo reprovada).
"""
import argparse, fnmatch, json, os, re, sys
from pathlib import Path
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import falha, ok, quadros  # noqa: E402

RASTER = (".png", ".jpg", ".jpeg", ".webp", ".gif")
TIPOS = ("foto", "video", "fundo")
PARECE, ESCALA, PASSO, BORRADO = 0.9, 4, 3, 0.6


def declaracoes(md):
    """{padrão: (tipo, motivo)} das linhas de tabela de RECORTES.md (a primeira coluna é o arquivo)"""
    d = {}
    if md.exists():
        for linha in md.read_text().splitlines():
            c = [x.strip().strip("`").strip() for x in linha.strip().strip("|").split("|")]
            if len(c) >= 2 and linha.lstrip().startswith("|") and c[0] and c[0].lower() != "arquivo" and not set(c[0]) <= set("-: "):
                d[c[0]] = (c[1].lower(), c[2] if len(c) > 2 else "")
    return d


def carrega(p):
    """(cinza float32, máscara uint8 ou None); gif pelo primeiro quadro"""
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    if im is None:
        cap = cv2.VideoCapture(str(p)); _, im = cap.read(); cap.release()
    if im is None:
        return None, None
    if im.ndim == 2:
        return im.astype(np.float32), None
    m = (im[..., 3] > 127).astype(np.uint8) if im.shape[2] == 4 else None
    return cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2GRAY).astype(np.float32), m


def parecido(tpl, msk, refs):
    """maior correlação normalizada de tpl (já na escala 1/ESCALA) contra os quadros reduzidos; (corr, quadro)"""
    h, w = refs[0][1].shape
    s = min(1.0, 0.95 * w / tpl.shape[1], 0.95 * h / tpl.shape[0])  # maior que o quadro: cabe inteiro
    tw, th = max(1, round(tpl.shape[1] * s)), max(1, round(tpl.shape[0] * s))
    if min(tw, th) < 6:
        return 0.0, None
    t = cv2.resize(tpl, (tw, th), interpolation=cv2.INTER_AREA)
    m = cv2.resize(msk, (tw, th), interpolation=cv2.INTER_NEAREST) if msk is not None else None
    if m is not None and m.sum() < 30:
        return 0.0, None
    if float(t[m > 0].std() if m is not None else t.std()) < 2:  # liso: correlação não diz nada
        return 0.0, None
    melhor = (0.0, None)
    for f, g in refs:
        r = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED, mask=m) if m is not None else cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
        v = float(np.nan_to_num(r, nan=0, posinf=0, neginf=0).clip(-1, 1).max())
        if v > melhor[0]:
            melhor = (v, f)
    return round(melhor[0], 3), melhor[1]


def confere_recortes(P, orig):
    A = P / "hf" / "assets"
    rasters = sorted(x for x in A.rglob("*") if x.suffix.lower() in RASTER and "node_modules" not in x.parts) if A.exists() else []
    dec = declaracoes(A / "RECORTES.md")
    refs = None
    sem, invalidos, declarados = [], [], []
    for x in rasters:
        rel = x.relative_to(A).as_posix()
        chave = next((k for k in dec if fnmatch.fnmatch(rel, k)), None)
        if chave is not None:
            tipo, motivo = dec[chave]
            if tipo not in TIPOS or not motivo:
                invalidos.append(dict(arquivo=rel, tipo=tipo, motivo=motivo))
            else:
                declarados.append(dict(arquivo=rel, tipo=tipo))
            continue
        if refs is None:
            refs = [(f, cv2.cvtColor(q, cv2.COLOR_RGB2GRAY).astype(np.float32)) for f, q in quadros(orig, largura=None)
                    if f % PASSO == 0] if orig.exists() else []
            refs = [(f, cv2.resize(g, (g.shape[1] // ESCALA, g.shape[0] // ESCALA), interpolation=cv2.INTER_AREA)) for f, g in refs]
        g, m = carrega(x)
        if g is None:
            sem.append(dict(arquivo=rel, parece_do_original=None, corr=None, quadro=None)); continue
        g = cv2.resize(g, (max(1, g.shape[1] // ESCALA), max(1, g.shape[0] // ESCALA)), interpolation=cv2.INTER_AREA)
        m = cv2.resize(m, (g.shape[1], g.shape[0]), interpolation=cv2.INTER_NEAREST) if m is not None else None
        corr, f = parecido(g, m, refs) if refs else (0.0, None)
        sem.append(dict(arquivo=rel, parece_do_original=corr >= PARECE, corr=corr, quadro=f))
    return dict(rasters=len(rasters), declarados=declarados, sem_declaracao=sem, tipo_invalido=invalidos,
                do_original_sem_declaracao=sum(1 for s in sem if s["parece_do_original"]))


def energia(g, regiao):
    lap = cv2.Laplacian(g, cv2.CV_32F, ksize=3)
    return float((lap[regiao] ** 2).mean()) if regiao.any() else None


def confere_nitidez(orig, clone):
    if not clone or not Path(clone).exists():
        return None
    eo, ec = [], []
    for (f, a), (_, b) in zip(quadros(orig), quadros(clone)):
        if f % PASSO:
            continue
        ga = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY)
        gb = cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
        if gb.shape != ga.shape:
            gb = cv2.resize(gb, (ga.shape[1], ga.shape[0]), interpolation=cv2.INTER_AREA)
        reg = cv2.dilate(cv2.Canny(ga, 60, 150), np.ones((7, 7), np.uint8)) > 0
        x, y = energia(ga.astype(np.float32), reg), energia(gb.astype(np.float32), reg)
        if x is not None:
            eo.append(x); ec.append(y)
    if not eo:
        return None
    o, c = float(np.mean(eo)), float(np.mean(ec))
    r = round(c / o, 3) if o else None
    return dict(original=round(o, 1), clone=round(c, 1), razao=r, borrado=bool(r is not None and r < BORRADO),
                quadros=len(eo), clone_video=str(clone))


def ultimo_clone(P):
    f = P / "saidas" / "final.mp4"
    if f.exists():
        return f
    rs = sorted((P / ".apple-style-ui" / "rodadas").glob("*/clone.mp4"))
    return rs[-1] if rs else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pasta"); ap.add_argument("--clone"); ap.add_argument("--json")
    a = ap.parse_args()
    P = Path(a.pasta).resolve()
    orig = P / "referencia" / "original.mp4"
    if not (P / "hf").exists():
        falha(f"falta {P / 'hf'}", 1)
    rec = confere_recortes(P, orig)
    nit = confere_nitidez(orig, a.clone or ultimo_clone(P)) if orig.exists() else None
    motivos = []
    if rec["sem_declaracao"]:
        do = [s["arquivo"] for s in rec["sem_declaracao"] if s["parece_do_original"]]
        motivos.append(f"{len(rec['sem_declaracao'])} raster(s) sem declaração em hf/assets/RECORTES.md"
                       + (f", {len(do)} recortado(s) do original ({', '.join(do[:6])}{'...' if len(do) > 6 else ''})" if do else ""))
    if rec["tipo_invalido"]:
        motivos.append(f"{len(rec['tipo_invalido'])} declarado(s) com tipo fora de {'/'.join(TIPOS)} ou sem motivo "
                       f"({', '.join(x['arquivo'] for x in rec['tipo_invalido'][:6])})")
    aprovada = not motivos
    motivo = "; ".join(motivos)
    res = (f"recortes: {rec['rasters']} raster(s), {len(rec['declarados'])} declarado(s); "
           + ("aprovada" if aprovada else f"REPROVADA: {motivo}"))
    if nit:
        res += (f"; nitidez do clone {nit['razao']}x a do original" + (" (BEM MAIS BORRADO: peças recortadas e reescaladas?)" if nit["borrado"] else ""))
    out = dict(aprovada=aprovada, motivo_reprovada=motivo, recortes=rec, nitidez=nit)
    if a.json:
        Path(a.json).write_text(json.dumps(out, ensure_ascii=False, indent=1))
    ok(res, None if aprovada else f"recriar as peças e declarar o resto em {P / 'hf/assets/RECORTES.md'}",
       "" if aprovada else "interface (texto, ícone, cartão, pílula, botão, avatar desenhado) se recria em HTML, CSS ou SVG; "
       "foto ou vídeo filmado se declara com tipo e motivo", **out)


if __name__ == "__main__":
    main()
