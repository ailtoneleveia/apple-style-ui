#!/usr/bin/env python3
"""qualidade.py: o medidor por peça do loop de qualidade. Pega o que um olho treinado pega e a média do quadro esconde.

  qualidade.py comparar <referencia.mp4> <candidato.mp4> [--pecas pecas.json] [--hf HF] [--saida DIR]
      clone contra o original, peça por peça (as da FICHA em pecas.json, ou detectadas no original)
  qualidade.py estilo <video.mp4> [--hf HF] [--saida DIR]
      sem referência (aplicar molde, vídeo novo): o vídeo contra o perfil de estilo calibrado (estilo.js)
  qualidade.py codigo <HF>
      movimento paramétrico: a composição anima por molas e curvas do estilo.js, não por tabela de pose

Peças: manchas que diferem do fundo da cena (nível 1: cartão, painel, ícone) e manchas de detalhe que diferem do
entorno (nível 2: texto, avatar, cursor, botão dentro do cartão), seguidas quadro a quadro com o detector do raio-x.
O fundo vem só do original e vale para os dois vídeos (mexer num trecho do clone não muda a nota de outro).
pecas.json (opcional) dá nome às peças da FICHA: [{"nome": "cursor", "quadros": [85, 103], "caixa": [x0, y0, x1, y1]}]
em px do vídeo; a caixa é a região onde a peça vive nesse trecho.

Para cada peça, medido do mesmo jeito nos dois vídeos, na região da peça no original:
  velocidade   por correlação de fase quadro a quadro (sub-pixel, não liga para esmaecimento): erro da velocidade
               contra o original e quebras de C1 (a velocidade salta num quadro, o tranco de uma chave linear)
  mola         cada movimento (sai de um repouso e assenta em outro) ajustado ao oscilador do estilo.js (o ajuste do
               raio-x): zeta, omega, passa do ponto e tempo de assentar, contra o mesmo movimento no original
  trajetória   erro RMS da posição (px) e correlação de x, y, escala e opacidade (centro e massa da máscara)
  escalonamento atraso de entrada contra a peça anterior que entra em sequência, e a sobreposição das entradas
  motion blur  obturador equivalente do vídeo (o ajuste do raio-x) e, por peça, o rastro: largura das bordas na
               direção do movimento menos a da perpendicular, nos quadros em que a peça anda, contra o original
  nitidez      energia do Laplaciano sobre a variância do recorte (não depende de contraste nem de alinhamento)
  cor          ΔE2000 médio no miolo da peça (pixels que são peça nos dois)
  forma        IoU da máscara da peça (e, no relatório, o erro do centro relativo ao tamanho, no pior trecho)
  percepção    SSIM no recorte da peça
  texto        quando o tesseract lê: conteúdo igual, altura-x e espessura do traço pela tinta

Saída: <saida>/qualidade.json e QUALIDADE.md (a PIOR peça primeiro, com o motivo técnico de cada reprovação e a
correção sugerida) e o JSON padrão {ok, resumo, proximo} no stdout, com "aprovada" e "piores".
Os limites (LIM e ESTILO) foram calibrados nos 3 clones bons (Satellite, Joi, VoiceOS: passam) contra o teste cego
B2 (reprova). Números e motivo de cada limite: CLONAR.md, "O loop de qualidade".
"""
from __future__ import annotations
import argparse, difflib, json, math, os, re, subprocess, sys, tempfile
from pathlib import Path
try:
    import numpy as np
    import cv2
except ImportError:  # chamado pelo python do sistema: troca pelo ambiente do kit (~/.apple-style-ui/venv)
    _py = os.environ.get("ASUI_PY") or str(Path.home() / ".apple-style-ui/venv/bin/python")
    if Path(_py).exists() and Path(_py).resolve() != Path(sys.executable).resolve():
        os.execv(_py, [_py] + sys.argv)
    raise

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.dont_write_bytecode = True
import raiox  # noqa: E402
import burst  # noqa: E402
import cuts as cortes_mod  # noqa: E402
from common import probe  # noqa: E402
from saida import ok, falha  # noqa: E402

LADO = 540          # lado maior da análise de peças (a fina, para nitidez, SSIM, cor e texto, vai até 1080)
LIMIAR = 24         # diferença do fundo (0-255, maior canal) que já é peça
AREA_MIN = 0.0004   # peça mínima: 0,04 % do quadro (cursor de ~22 px num quadro de 1080)
K_DETALHE = 31      # mediana espacial (px da análise) que separa o detalhe do entorno (nível 2)
MAX_PECAS = 60      # as mais importantes (área x duração); vídeo longo e cheio passa de 150 manchas
RESP = 0.3          # resposta mínima da correlação de fase para confiar na velocidade

# Limites do comparar. Calibração (3 clones bons contra o B2) no CLONAR.md, "O loop de qualidade".
LIM = dict(
    vel_erro=2.5,         # erro RMS da velocidade / velocidade RMS do original (bons: até 1,88; B2: 5,05 no cartão Recent)
    quebras=7,            # quebras de velocidade sem par no original, contadas como a 30 qps (bons: até 6,5; B2: 8)
    curva=0.75,           # diferença RMS da curva de progresso de um mesmo movimento (bons: até 0,71; B2: 1,08)
    sem_mola=0.35,        # resíduo do ajuste de mola do clone além do do original (bons: até 0,33; B2: 0,90)
    anda=(0.05, 0.15),    # movimento de 5 % do quadro ou mais que o clone faz em menos de 15 % (bons: nenhum; B2: 3)
    atraso_s=0.45,        # |Δ atraso de entrada| contra a peça anterior da sequência, em s (bons: até 0,42)
    obturador=(0.5, 2.0), # razão do obturador equivalente contra o original (bons: 0,99 a 1,53; B2: 0,84)
    nitidez=0.2,          # razão mínima da nitidez: abaixo disso a peça está borrada (bons: a partir de 0,23)
    delta_e=46.0,         # ΔE2000 da cor dominante: só pega cor trocada (texto sobre degradê engana; bons: até 44,7)
    iou=0.20,             # forma e lugar (bons: a partir de 0,23; B2: 0,07 a 0,18)
    ssim=0.50,            # percepção no recorte (bons: a partir de 0,53; B2: 0,40 a 0,50)
    texto=0.6,            # semelhança do texto lido, com o tesseract confiante (70+) nos dois
    altura_x=0.4,         # |razão - 1| da altura-x (bons: até 0,37; B2: 0,44)
    presente=0.6,         # fração dos quadros do original em que a peça também está no clone (peça de 10+ quadros)
    rastro_v=6.0,         # px/quadro (escala 1080): abaixo disso o rastro não aparece; o motion blur por peça só mede acima
    rastro=(4.0, 0.5),    # rastro a mais ou a menos que o original: 4 px (escala 1080) e meio quadro de obturador (180°)
                          # no pior trecho de 0,1 s (bons: até 0,29 quadro; B2 e B3: 0,83 a 0,90 na pílula preta)
)


def br(x, n=2):
    return f"{x:.{n}f}".replace(".", ",") if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


# ------------------------------------------------------------------ leitura
def le_video(video, lado=LADO):
    pm = probe(video)
    W, H, fps = pm["width"], pm["height"], pm["fps"]
    k = lado / max(W, H)
    aw, ah = max(2, int(round(W * k / 2)) * 2), max(2, int(round(H * k / 2)) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"scale={aw}:{ah}:flags=area", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    Q = np.frombuffer(raw, np.uint8).reshape(-1, ah, aw, 3)
    return Q, dict(w=W, h=H, fps=fps, esc=W / aw, n=len(Q), aw=aw, ah=ah)


def detalhe_de(Q):
    """nível 2: o que difere do entorno (mediana espacial), sem o fundo nem o miolo liso dos cartões"""
    return np.stack([cv2.absdiff(q, cv2.medianBlur(q, K_DETALHE)) for q in Q])


def cenas_de(video, n):
    """cortes secos (o mesmo teste do raio-x) → [(a, b)] com b exclusivo"""
    try:
        C = cortes_mod.detect(str(video))
        secos, _ = raiox.classifica_cortes(str(video), sorted(set(c["frame"] for c in C["cuts"])))
    except Exception:  # sem cortes legíveis: uma cena só
        secos = []
    lim = [0] + [s for s in secos if 0 < s < n] + [n]
    return [(lim[i], lim[i + 1]) for i in range(len(lim) - 1) if lim[i + 1] - lim[i] >= 2]


def fundos(Q, cenas):
    """fundo de cada cena = mediana no tempo (o do raio-x)"""
    return {(a, b): np.median(Q[a:b:max(1, (b - a) // 60)], axis=0).astype(np.int16) for a, b in cenas}


def fundo_de(F, f):
    return next((m for (a, b), m in F.items() if a <= f < b), next(iter(F.values())))


# ------------------------------------------------------------------ peças
def caixa(t, i):
    return (t["cx"][i] - t["w"][i] / 2, t["cy"][i] - t["h"][i] / 2, t["cx"][i] + t["w"][i] / 2, t["cy"][i] + t["h"][i] / 2)


def iou_caixa(a, b):
    i = max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def detecta(Q, D, info, cenas):
    tr = []
    for nivel, S in ((1, Q), (2, D)):
        for a, b in cenas:
            for t in raiox.trilhas_da_cena(S, a, b, info["esc"], area_min=AREA_MIN, limiar=LIMIAR):
                t = raiox.preenche(t); t["nivel"] = nivel; tr.append(t)
    W, H = info["w"], info["h"]
    # peça rápida e pequena (cursor que cruza a tela) só vira mancha enquanto o borrão a engrossa: 6 quadros bastam
    # quando ela anda metade do próprio tamanho por quadro
    rapida = lambda t: np.median(np.hypot(np.diff(t["cx"]), np.diff(t["cy"]))) >= 0.5 * np.sqrt(np.median(t["w"] * t["h"]))
    tr = [t for t in tr if (len(t["f"]) >= 8 or len(t["f"]) >= 6 and rapida(t)) and np.median(t["w"] * t["h"]) <= 0.35 * W * H]
    tr.sort(key=lambda t: -len(t["f"]) * float(np.median(t["w"] * t["h"])))
    fica = []
    for t in tr:  # a mesma peça vista nos dois níveis, ou perdida e achada de novo: fica a maior
        it = {f: i for i, f in enumerate(t["f"])}
        dup = False
        for u in fica:
            iu = {f: i for i, f in enumerate(u["f"])}
            comum = [f for f in t["f"] if f in iu]
            if len(comum) >= 0.7 * len(t["f"]) and \
                    sum(iou_caixa(caixa(t, it[f]), caixa(u, iu[f])) >= 0.6 for f in comum) >= 0.7 * len(comum):
                dup = True; break
        if not dup:
            fica.append(t)
    fica = sorted(fica[:MAX_PECAS], key=lambda t: (t["f"][0], t["cy"][0], t["cx"][0]))
    for i, t in enumerate(fica):
        k = int(np.argmax(t["w"] * t["h"]))
        t["nome"] = f"P{i + 1:02d}"
        t["onde"] = f"f{t['f'][0]}-{t['f'][-1]} em ({round(t['cx'][k])}, {round(t['cy'][k])}) {round(t['w'][k])}x{round(t['h'][k])}"
    return fica


def pecas_da_ficha(caminho):
    """pecas.json: [{nome, quadros: [a, b], caixa: [x0, y0, x1, y1], nivel?}] em px do vídeo → trilhas de caixa fixa"""
    out = []
    for p in json.load(open(caminho)):
        a, b = p["quadros"]; x0, y0, x1, y1 = p["caixa"]
        f = list(range(int(a), int(b) + 1)); n = len(f)
        out.append(dict(nome=p["nome"], onde=f"f{a}-{b} caixa {x0},{y0}-{x1},{y1} (FICHA)", f=f, ficha=True, nivel=int(p.get("nivel", 2)),
                        cx=np.full(n, (x0 + x1) / 2), cy=np.full(n, (y0 + y1) / 2), w=np.full(n, float(x1 - x0)), h=np.full(n, float(y1 - y0))))
    return out


def roi(t, i, info, margem=4):
    """caixa da peça no quadro i, em px da análise, com folga (a da FICHA já é a região inteira)"""
    esc = info["esc"]
    x0, y0, x1, y1 = (v / esc for v in caixa(t, i))
    mg = 0 if t.get("ficha") else margem + 0.12 * max(x1 - x0, y1 - y0)
    return (int(max(0, x0 - mg)), int(max(0, y0 - mg)), int(min(info["aw"], math.ceil(x1 + mg))), int(min(info["ah"], math.ceil(y1 + mg))))


K2 = np.ones((2, 2), np.uint8)
_HAN = {}


def momento(q, fundo):
    d = np.abs(q.astype(np.int16) - fundo).max(-1)
    m = cv2.morphologyEx((d > LIMIAR).astype(np.uint8), cv2.MORPH_OPEN, K2)
    a = int(m.sum())
    if a == 0:
        return m, dict(area=0, cx=np.nan, cy=np.nan, bw=0.0, bh=0.0, massa=0.0)
    ys, xs = np.nonzero(m)
    return m, dict(area=a, cx=float(xs.mean()), cy=float(ys.mean()), bw=float(np.ptp(xs) + 1), bh=float(np.ptp(ys) + 1),
                   massa=float(d[m > 0].sum()))


def fase(Q, f, r):
    """deslocamento de f-1 para f na região r (px da análise) por correlação de fase, e a resposta (confiança)"""
    x0, y0, x1, y1 = r
    if f < 1 or x1 - x0 < 16 or y1 - y0 < 16:
        return 0.0, 0.0, 0.0
    a = Q[f - 1, y0:y1, x0:x1].astype(np.float32).mean(-1); b = Q[f, y0:y1, x0:x1].astype(np.float32).mean(-1)
    if a.std() < 2 and b.std() < 2:
        return 0.0, 0.0, 0.0
    k = (x1 - x0, y1 - y0)
    if k not in _HAN:
        _HAN[k] = cv2.createHanningWindow(k, cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(a, b, _HAN[k])
    return dx, dy, resp


def series(t, Q, S, F, info):
    """a peça medida na região dela no ORIGINAL (a mesma região nos dois vídeos): posição, tamanho, massa, máscara
    (no nível da peça) e velocidade por correlação de fase (no quadro de verdade)"""
    esc = info["esc"]; out = []
    for i, f in enumerate(t["f"]):
        if f >= len(Q):
            break
        r = roi(t, i, info)
        x0, y0, x1, y1 = r
        m, s = momento(S[f, y0:y1, x0:x1], fundo_de(F, f)[y0:y1, x0:x1])
        r2 = r if i == 0 else tuple(fn(p, q) for fn, p, q in zip((min, min, max, max), r, roi(t, i - 1, info)))
        dx, dy, resp = fase(Q, f, r2)
        s.update(f=f, cx=(s["cx"] + x0 + 0.5) * esc, cy=(s["cy"] + y0 + 0.5) * esc, bw=s["bw"] * esc, bh=s["bh"] * esc,
                 area=s["area"] * esc * esc, mask=m, vx=dx * esc, vy=dy * esc, resp=resp)
        out.append(s)
    return out


def serie(S, k):
    return np.array([s[k] for s in S], float)


# ------------------------------------------------------------------ movimento
def corr(a, b, piso):
    v = np.isfinite(a) & np.isfinite(b)
    if v.sum() < 6 or np.std(a[v]) < piso:
        return None  # a grandeza não anda no original: a correlação não diz nada (o erro em px diz)
    if np.std(b[v]) < 1e-6:
        return 0.0
    return float(np.corrcoef(a[v], b[v])[0, 1])


def quebras(S, piso):
    """quadros em que a velocidade salta: |v(f) - v(f-1)| acima do ruído e de 45 % da velocidade (chave linear,
    pose lida à mão, parada seca). Só onde a correlação de fase confia nos dois quadros."""
    v = np.stack([serie(S, "vx"), serie(S, "vy")], 1); r = serie(S, "resp")
    out = []
    for k in range(2, len(v)):
        if r[k] < RESP or r[k - 1] < RESP:
            continue
        a, b = np.linalg.norm(v[k - 1]), np.linalg.norm(v[k])
        if max(a, b) >= 2 * piso and np.linalg.norm(v[k] - v[k - 1]) > max(piso, 0.45 * max(a, b)):
            out.append(S[k]["f"])
    return out


def deslocamento(S):
    """posição relativa integrada da velocidade confiável (onde não confia, interpola a velocidade)"""
    r = serie(S, "resp"); ok_ = r >= RESP
    if ok_.sum() < 4:
        return None, None
    idx = np.arange(len(S))
    vx = np.interp(idx, idx[ok_], serie(S, "vx")[ok_]); vy = np.interp(idx, idx[ok_], serie(S, "vy")[ok_])
    vx[0] = vy[0] = 0
    return np.cumsum(vx), np.cumsum(vy)


def grandezas(S, info):
    """x e y (deslocamento integrado da velocidade) e largura e altura (máscara), uma série por grandeza"""
    X, Y = deslocamento(S)
    g = {} if X is None else dict(x=(X, info["w"]), y=(Y, info["h"]))
    for nm, k, d in (("largura", "bw", info["w"]), ("altura", "bh", info["h"])):
        q = serie(S, k)
        if (q > 0).sum() >= 6:
            v = q > 0
            g[nm] = (np.interp(np.arange(len(q)), np.nonzero(v)[0], q[v]), d)
    return g


def mola_ok(aj):
    return bool(aj and aj["rms"] <= 0.08 and 2.5 < aj["omega"] < 115 and 0.16 < aj["zeta"] < 3.9)


def params(aj, p):
    return None if not aj else dict(zeta=aj["zeta"], omega=aj["omega"], impulso=aj["u0"], rms=aj["rms"], mola=mola_ok(aj),
                                    assenta_s=round(raiox.assenta(aj["zeta"], aj["omega"], aj["u0"]), 2),
                                    passa=round(max(0.0, float(np.max(p)) - 1), 3))


def molas_de(S, fps, info):
    """cada movimento (sai de um repouso e assenta em outro) ajustado à mola do estilo.js, sem referência"""
    f = np.array([s["f"] for s in S]); out = []
    for g, (q, d) in grandezas(S, info).items():
        for mv in raiox.movimentos(q, f, fps, d, g):
            tt = (np.array(mv["f_serie"]) - mv["a"]) / fps
            p = (np.array(mv["serie"]) - mv["q0"]) / (mv["q1"] - mv["q0"])
            aj = raiox.ajusta_mola(tt, p, fps)
            out.append(dict(grandeza=g, a=mv["a"], b=mv["b"], caminho=round(mv["q1"] - mv["q0"]), **(params(aj, p) or dict(mola=False))))
    return out


def curvas(SR, SC, fps, info):
    """cada movimento do original que é mola, e o clone medido NA MESMA JANELA (normalizado pelo próprio começo e
    fim): diferença da curva de progresso, mola ajustada nos dois e resíduo do ajuste (curva que não é mola)"""
    f = np.array([s["f"] for s in SR])
    GR, GC = grandezas(SR, info), grandezas(SC, info)
    k = max(2, int(round(0.1 * fps)))
    out = []
    for g, (qr, d) in GR.items():
        if g not in GC:
            continue
        qc = GC[g][0]
        for mv in raiox.movimentos(qr, f, fps, d, g):
            i = np.searchsorted(f, mv["f_serie"])
            if len(i) < 5:
                continue
            tt = (f[i] - mv["a"]) / fps
            pr = (qr[i] - mv["q0"]) / (mv["q1"] - mv["q0"])
            ajr = raiox.ajusta_mola(tt, pr, fps)
            if not mola_ok(ajr):
                continue  # o original não é mola aqui (degrau, deriva): não há o que comparar
            ib = int(np.searchsorted(f, mv["b"]))
            c0, c1 = qc[i[0]], float(np.median(qc[ib:ib + k])) if ib < len(qc) else qc[-1]
            item = dict(grandeza=g, a=mv["a"], b=mv["b"], caminho=round(mv["q1"] - mv["q0"]), caminho_clone=round(c1 - c0))
            if abs(c1 - c0) < 0.3 * abs(mv["q1"] - mv["q0"]):
                out.append(dict(item, anda=False, original=params(ajr, pr), clone=None)); continue
            pc = (qc[i] - c0) / (c1 - c0)
            ajc = raiox.ajusta_mola(tt, pc, fps)
            out.append(dict(item, anda=True, curva_rms=round(float(np.sqrt(np.mean((pc - pr) ** 2))), 3),
                            original=params(ajr, pr), clone=params(ajc, pc)))
    return out


def entrada(S):
    """quadro de entrada (massa passa de 50 % da sustentada) e o trecho da entrada (10 % a 90 %)"""
    m = serie(S, "massa"); f = [s["f"] for s in S]
    if m.max() <= 0:
        return None
    # 50 % da massa SUSTENTADA (percentil 75), não do pico: com a massa num platô perto de 50 % do pico, um pico de
    # tinta no fim da janela jogava o f50 dezenas de quadros para um lado ou outro sem nada mudar na entrada
    top = float(np.percentile(m, 75))
    i10, i50, i90 = (int(np.argmax(m >= k * top)) for k in (0.1, 0.5, 0.9))
    return dict(f10=f[i10], f50=f[i50], f90=f[max(i90, i10)])


def largura_borda(g, ux, uy, m=None, contraste=12.0):
    """largura equivalente (px) das bordas da peça ao longo de (ux, uy): gira o recorte para a direção virar o eixo x
    e, em cada linha, cada rampa monotônica vale Σ|d| / max|d| (borda nítida ~1-2 px; borrão em linha de L px ~L).
    Mediana ponderada pelo contraste, só nas rampas que tocam a máscara m da peça."""
    h, w = g.shape
    if w < 4 or h < 4:
        return None
    R = cv2.getRotationMatrix2D((w / 2, h / 2), math.degrees(math.atan2(uy, ux)), 1.0)
    r = cv2.warpAffine(g.astype(np.float32), R, (w, h), flags=cv2.INTER_LINEAR, borderValue=float("nan"))
    d = np.diff(r, axis=1)
    gy = np.zeros_like(r); gy[1:-1] = (r[2:] - r[:-2]) / 2
    gy = (gy[:, 1:] + gy[:, :-1]) / 2
    # só borda de frente para a direção (normal a até ~27°): numa borda oblíqua a largura ao longo da linha cresce
    # sem rastro nenhum (disco, pílula) e o borrão de um lado contaminava a medida do outro
    s = np.where(np.isfinite(d) & (np.abs(d) >= 1.0) & (np.abs(gy) <= 0.5 * np.abs(d)), np.sign(d), 0).ravel()
    novo = (np.arange(s.size) % (w - 1) == 0) | np.r_[True, s[1:] != s[:-1]]
    rid = np.cumsum(novo) - 1
    a = np.abs(np.nan_to_num(d)).ravel()
    soma = np.bincount(rid, a)
    mx = np.maximum.reduceat(a, np.flatnonzero(novo))
    ok_ = (s[novo] != 0) & (soma >= contraste)
    if m is not None:
        mk = cv2.warpAffine(m.astype(np.uint8), R, (w, h), flags=cv2.INTER_NEAREST)
        ok_ &= np.bincount(rid, (mk[:, 1:] | mk[:, :-1]).ravel().astype(float)) > 0
    if ok_.sum() < 4:
        return None
    L, P = soma[ok_] / mx[ok_], soma[ok_]
    o = np.argsort(L); c = np.cumsum(P[o])
    return float(L[o][np.searchsorted(c, 0.5 * c[-1])])


def rastro(t, SR, SC, QR, QC, info):
    """motion blur por peça: em cada quadro em que a peça anda (velocidade média de 7 quadros, pela trilha ou pela
    correlação de fase, o que for maior), o rastro de cada vídeo = largura das bordas na direção do movimento menos
    a largura na perpendicular (desfoque igual para todos os lados não é rastro), cada um na própria máscara. No pior
    trecho de ~0,1 s: a diferença em px (escala 1080) e em quadros de obturador (diferença / velocidade)."""
    n = len(SR)
    if n < 3:
        return None
    a1080 = 1080 / LADO  # px da análise -> px na escala 1080
    V = np.stack([np.gradient(np.asarray(t["cx"][:n], float)), np.gradient(np.asarray(t["cy"][:n], float))], 1) / info["esc"]
    for i, s in enumerate(SR):
        vf = np.array([s["vx"], s["vy"]]) / info["esc"]
        if s["resp"] >= RESP and np.hypot(*vf) > np.hypot(*V[i]):
            V[i] = vf
    Vm = np.array([V[max(0, i - 3):i + 4].mean(0) for i in range(n)])  # a peça que freia ainda carrega o rastro
    k3 = np.ones((3, 3), np.uint8)
    fs, vs, ro, rc = [], [], [], []
    for i, s in enumerate(SR):
        sp = float(np.hypot(*Vm[i]))
        if sp * a1080 < LIM["rastro_v"] or s["area"] <= 0 or SC[i]["area"] <= 0:
            continue
        ux, uy = Vm[i] / sp
        x0, y0, x1, y1 = roi(t, i, info)
        it = 1 + int(math.ceil(max(sp, float(np.hypot(*V[i]))) / 2))  # a borda borrada passa da máscara em até meio rastro
        w = []
        for Q, S in ((QR, SR), (QC, SC)):
            g = cv2.cvtColor(Q[s["f"], y0:y1, x0:x1], cv2.COLOR_RGB2GRAY)
            mk = cv2.dilate(S[i]["mask"], k3, iterations=it)
            w += [largura_borda(g, ux, uy, mk), largura_borda(g, -uy, ux, mk)]
        if None in w:
            continue
        fs.append(s["f"]); vs.append(sp); ro.append(w[0] - w[1]); rc.append(w[2] - w[3])
    k = max(3, int(round(0.1 * info["fps"])))
    pior = None
    for j in range(len(fs) - k + 1):
        if fs[j + k - 1] - fs[j] > 2 * k:
            continue
        d = float(np.median(np.subtract(ro[j:j + k], rc[j:j + k]))); v = float(np.median(vs[j:j + k]))
        nota = min(abs(d) * a1080 / LIM["rastro"][0], abs(d / v) / LIM["rastro"][1])  # >= 1: passa dos dois limites
        if pior is None or nota > pior[0]:
            pior = (nota, d, v, j)
    if pior is None:
        return None
    _, d, v, j = pior
    return dict(quadros=[fs[j], fs[j + k - 1]], velocidade=round(v * a1080, 1), original=round(float(np.median(ro[j:j + k])) * a1080, 1),
                clone=round(float(np.median(rc[j:j + k])) * a1080, 1), diferenca=round(d * a1080, 1), obturador=round(d / v, 2))


def posicao(SR, SC, fps):
    """erro do centro da máscara em relação ao tamanho da peça (raiz da área no original), no pior trecho de
    ~0,1 s (mediana da janela): uma peça pequena fora do lugar some no RMS da trilha inteira e no IoU médio"""
    ar, ac = serie(SR, "area"), serie(SC, "area")
    v = (ar > 0) & (ac > 0)
    if v.sum() < 3:
        return None
    e = np.hypot(serie(SR, "cx") - serie(SC, "cx"), serie(SR, "cy") - serie(SC, "cy"))[v]
    tam = np.sqrt(ar[v]); f = serie(SR, "f")[v]
    k = min(len(e), max(3, int(round(0.1 * fps))))
    rel = np.array([np.median(e[j:j + k] / tam[j:j + k]) for j in range(len(e) - k + 1)])
    j = int(np.argmax(rel))
    return dict(erro_rel=round(float(rel[j]), 2), quadros=[int(f[j]), int(f[j + k - 1])], erro_px=round(float(np.median(e[j:j + k])), 1),
                tamanho=round(float(np.median(tam[j:j + k])), 1))


# ------------------------------------------------------------------ medidas de detalhe (resolução fina)
def ssim(a, b):
    """SSIM (janela gaussiana 11, sigma 1,5) no recorte inteiro: só na tinta, texto bom com 1 px de deslize cai a 0,01"""
    a, b = a.astype(np.float32), b.astype(np.float32)
    C1, C2 = (0.01 * 255) ** 2, (0.03 * 255) ** 2
    g = lambda x: cv2.GaussianBlur(x, (11, 11), 1.5)
    ma, mb = g(a), g(b)
    va, vb, cab = g(a * a) - ma * ma, g(b * b) - mb * mb, g(a * b) - ma * mb
    mapa = ((2 * ma * mb + C1) * (2 * cab + C2)) / ((ma * ma + mb * mb + C1) * (va + vb + C2))
    return float(mapa.mean())


def lab(rgb):
    return cv2.cvtColor(rgb.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)


def ciede2000(L1, L2):
    """ΔE2000 entre dois arrays Lab (..., 3)"""
    L1, a1, b1 = L1[..., 0], L1[..., 1], L1[..., 2]
    L2, a2, b2 = L2[..., 0], L2[..., 1], L2[..., 2]
    Cm = (np.hypot(a1, b1) + np.hypot(a2, b2)) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25.0 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp, dh = L2 - L1, C2p - C1p, h2p - h1p
    dh = np.where(C1p * C2p == 0, 0, np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)))
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lpm, Cpm, hs = (L1 + L2) / 2, (C1p + C2p) / 2, h1p + h2p
    hpm = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) <= 180, hs / 2, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2)))
    T = 1 - 0.17 * np.cos(np.radians(hpm - 30)) + 0.24 * np.cos(np.radians(2 * hpm)) + 0.32 * np.cos(np.radians(3 * hpm + 6)) \
        - 0.20 * np.cos(np.radians(4 * hpm - 63))
    RC = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25.0 ** 7))
    SL = 1 + 0.015 * (Lpm - 50) ** 2 / np.sqrt(20 + (Lpm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cpm, 1 + 0.015 * Cpm * T
    RT = -np.sin(np.radians(2 * 30 * np.exp(-(((hpm - 275) / 25) ** 2)))) * RC
    return np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2 + RT * (dCp / SC) * (dHp / SH))


def tinta(crop):
    """máscara da peça no recorte fino: o que difere da cor da borda do recorte (o fundo local)"""
    borda = np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]]).astype(np.int16)
    return np.abs(crop.astype(np.int16) - np.median(borda, axis=0)).max(-1) > LIMIAR


def nitidez(g):
    """energia do Laplaciano sobre a variância: borrar derruba, contraste e alinhamento não mexem"""
    g = g.astype(np.float32)
    return float(cv2.Laplacian(g, cv2.CV_32F, ksize=3).var() / (g.var() + 25.0))


def ocr(crop):
    """tesseract no recorte ampliado; devolve (texto, confiança média) ou (None, 0)"""
    g = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)
    if g.mean() < 128:
        g = 255 - g
    g = cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as fh:
        cv2.imwrite(fh.name, g)
    try:
        r = subprocess.run(["tesseract", fh.name, "-", "--psm", "6", "tsv"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None, 0
    finally:
        os.unlink(fh.name)
    pal, conf, cx = [], [], []
    for ln in r.stdout.splitlines()[1:]:
        c = ln.split("\t")
        if len(c) >= 12 and c[11].strip() and float(c[10]) >= 0:
            pal.append(c[11].strip()); conf.append(float(c[10]))
            if float(c[10]) >= 60 and sum(ch.isalnum() for ch in c[11]) >= 2:  # caixa da palavra no recorte (sem a ampliação)
                cx.append([int(c[6]) / 2, int(c[7]) / 2, (int(c[6]) + int(c[8])) / 2, (int(c[7]) + int(c[9])) / 2])
    txt = " ".join(pal)
    ocr.caixas = cx
    if sum(ch.isalnum() for ch in txt) < 3 or not conf:
        return None, 0
    return txt, float(np.mean(conf))


def traco(crop):
    """altura-x (mediana da altura das letras) e espessura do traço (2 x distância média à borda, na tinta)"""
    m = tinta(crop).astype(np.uint8)
    nc, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    hs = [st[i, 3] for i in range(1, nc) if st[i, 4] >= 6]
    if len(hs) < 3:
        return None, None
    return float(np.median(hs)), float(2 * cv2.distanceTransform(m, cv2.DIST_L2, 3)[m > 0].mean())


def quadros_de_detalhe(SR, dim, n=3):
    """até n quadros assentados (pouca velocidade e quase toda a massa) para as medidas de detalhe"""
    v = np.hypot(serie(SR, "vx"), serie(SR, "vy"))
    ar = serie(SR, "area")
    if ar.max() <= 0:
        return []
    idx = np.nonzero((v < max(1.0, 0.002 * dim)) & (ar >= 0.7 * ar.max()))[0]
    if not len(idx):
        idx = np.array([int(np.argmax(ar))])
    return [SR[i]["f"] for i in idx[np.linspace(0, len(idx) - 1, min(n, len(idx))).round().astype(int)]]


def caixa_fina(t, f, k, fw, fh):
    i = t["f"].index(f)
    x0, y0, x1, y1 = (v * k for v in caixa(t, i))
    mg = 0 if t.get("ficha") else 6 + 0.1 * max(x1 - x0, y1 - y0)
    return int(max(0, x0 - mg)), int(max(0, y0 - mg)), int(min(fw, x1 + mg)), int(min(fh, y1 + mg))


def detalhe(t, fr, GR, GC, k, fw, fh):
    acc = dict(ssim=[], nit=[], de=[])
    for f in fr:
        if f not in GR or f not in GC:
            continue
        x0, y0, x1, y1 = caixa_fina(t, f, k, fw, fh)
        if x1 - x0 < 8 or y1 - y0 < 8:
            continue
        a, b = GR[f][y0:y1, x0:x1], GC[f][y0:y1, x0:x1]
        ga, gb = cv2.cvtColor(a, cv2.COLOR_RGB2GRAY), cv2.cvtColor(b, cv2.COLOR_RGB2GRAY)
        ma, mb = tinta(a), tinta(b)
        acc["ssim"].append(ssim(ga, gb))
        if ga.std() >= 4:
            acc["nit"].append(nitidez(gb) / max(1e-6, nitidez(ga)))
        # cor da peça = mediana Lab da própria tinta (não depende do alinhamento)
        if ma.sum() >= 20 and mb.sum() >= 20:
            acc["de"].append(float(ciede2000(np.median(lab(a)[ma], 0), np.median(lab(b)[mb], 0))))
    r = dict(ssim=round(float(np.mean(acc["ssim"])), 3) if acc["ssim"] else None,
             nitidez=round(float(np.median(acc["nit"])), 2) if acc["nit"] else None,
             delta_e=round(float(np.mean(acc["de"])), 1) if acc["de"] else None)
    if fr and fr[0] in GR and fr[0] in GC:  # texto: no quadro mais assentado
        x0, y0, x1, y1 = caixa_fina(t, fr[0], k, fw, fh)
        a, b = GR[fr[0]][y0:y1, x0:x1], GC[fr[0]][y0:y1, x0:x1]
        ta, ca = ocr(a) if min(a.shape[:2]) >= 10 else (None, 0)
        if ta and ca >= 60:
            tb, cb = ocr(b)
            limpa = lambda s: re.sub(r"[^0-9a-z ]", "", (s or "").lower()).strip()
            xa, pa = traco(a); xb, pb = traco(b)
            r["texto"] = dict(original=ta, clone=tb, confianca=[round(ca), round(cb)], semelhanca=round(difflib.SequenceMatcher(None, limpa(ta), limpa(tb)).ratio(), 2),
                              altura_x=round(xb / xa, 2) if xa and xb else None, peso=round(pb / pa, 2) if pa and pb else None)
    return r


def obturador_de(video, P, info, cenas):
    """obturador equivalente do vídeo (o ajuste do raio-x) nas peças que andam rápido; None sem amostra boa"""
    tr = [dict(f=t["f"], cx=np.asarray(t["cx"]), cy=np.asarray(t["cy"]), w=np.asarray(t["w"]), h=np.asarray(t["h"])) for t in P]
    try:
        return raiox.obturador(str(video), info["fps"], info["w"], info["h"], tr, np.zeros((0, 3)),
                               [dict(cena=i, a=a, b=b - 1) for i, (a, b) in enumerate(cenas)])
    except Exception:
        return dict(amostras=0, obturador=None)


# ------------------------------------------------------------------ comparar: clone contra original
def velocidade(SR, SC, piso, fps):
    """erro da velocidade contra o original onde a correlação de fase confia nos DOIS (mudança de escala e
    esmaecimento derrubam a confiança), só em peça que anda de verdade (pico de 180 px/s)"""
    vr = np.stack([serie(SR, "vx"), serie(SR, "vy")], 1); vc = np.stack([serie(SC, "vx"), serie(SC, "vy")], 1)
    conf = np.minimum(serie(SR, "resp"), serie(SC, "resp")) >= RESP
    sr, sc = np.linalg.norm(vr, axis=1), np.linalg.norm(vc, axis=1)
    mov = conf & (np.maximum(sr, sc) >= piso)
    out = dict(quadros_em_movimento=int(mov.sum()))
    if mov.sum() >= 4 and sr[mov].max() * fps >= 180:
        out["erro"] = round(float(np.sqrt(np.mean(np.sum((vc - vr)[mov] ** 2, 1))) / max(3 * piso, np.sqrt(np.mean(sr[mov] ** 2)))), 2)
        out["pico_original"] = round(float(sr[mov].max()), 1)
        k = int(np.argmax(np.sum((vc - vr) ** 2, 1) * mov))
        out["pior_quadro"] = dict(f=SR[k]["f"], original=[round(x, 1) for x in vr[k]], clone=[round(x, 1) for x in vc[k]])
    qr, qc = quebras(SR, piso), quebras(SC, piso)
    sobra = [f for f in qc if not any(abs(f - g) <= 1 for g in qr)]
    out["quebras"] = dict(original=len(qr), clone=len(qc), a_mais=len(sobra), quadros=sobra[:8])
    return out


def mede_par(t, SR, SC, info, GR, GC, k, fw, fh):
    fps, W, H = info["fps"], info["w"], info["h"]
    dim = max(W, H)
    ar, ac = serie(SR, "area"), serie(SC, "area")
    vale = (ar > 0) & (ac > 0)
    m = dict(quadros=len(SR), presente=round(float(vale.sum() / max(1, (ar > 0).sum())), 2))
    xr, yr, xc, yc = serie(SR, "cx"), serie(SR, "cy"), serie(SC, "cx"), serie(SC, "cy")
    m["erro_px"] = round(float(np.sqrt(np.mean((xr[vale] - xc[vale]) ** 2 + (yr[vale] - yc[vale]) ** 2))), 1) if vale.sum() else None
    cs = dict(x=corr(xr, xc, 0.01 * dim), y=corr(yr, yc, 0.01 * dim), escala=corr(np.sqrt(ar), np.sqrt(ac), 0.03 * max(1, np.sqrt(ar).mean())),
              opacidade=corr(serie(SR, "massa"), serie(SC, "massa"), 0.1 * max(1, serie(SR, "massa").mean())))
    m["correlacao"] = {g: round(c, 3) for g, c in cs.items() if c is not None}
    ious = [(a["mask"] & b["mask"]).sum() / max(1, (a["mask"] | b["mask"]).sum()) for a, b in zip(SR, SC) if a["area"] > 0]
    m["iou"] = round(float(np.mean(ious)), 3) if ious else None
    m["posicao"] = posicao(SR, SC, fps)
    m["velocidade"] = velocidade(SR, SC, max(1.5, 0.0015 * dim) * 30 / fps, fps)
    m["molas"] = curvas(SR, SC, fps, info)
    m["entrada"] = dict(original=entrada(SR), clone=entrada(SC))
    fr = quadros_de_detalhe(SR, dim)
    m.update(detalhe(t, fr, GR, GC, k, fw, fh))
    m["quadros_detalhe"] = fr
    if os.environ.get("QUALIDADE_SERIES"):  # calibração: as séries cruas
        m["_series"] = {nm: {k_: [round(float(s[k_]), 2) for s in S] for k_ in ("f", "vx", "vy", "resp", "area", "massa")} for nm, S in (("o", SR), ("c", SC))}
    return m


def escalonamento(res, cenas, fps):
    """peças que entram em sequência (entradas a até 0,6 s uma da outra, na mesma cena): atraso contra a anterior"""
    for a, b in cenas:
        ent = [(r["medidas"]["entrada"]["original"], r) for r in res
               if r["medidas"]["entrada"]["original"] and a + 1 < r["medidas"]["entrada"]["original"]["f10"] < b]
        ent.sort(key=lambda x: x[0]["f50"])
        for (e0, r0), (e1, r1) in zip(ent, ent[1:]):
            c0, c1 = r0["medidas"]["entrada"]["clone"], r1["medidas"]["entrada"]["clone"]
            if e1["f50"] - e0["f50"] > 0.6 * fps or not c0 or not c1:
                continue
            sob = lambda x, y: max(0, min(x["f90"], y["f90"]) - max(x["f10"], y["f10"])) / max(1, x["f90"] - x["f10"])
            r1["medidas"]["escalonamento"] = dict(
                anterior=r0["peca"], atraso_original_q=e1["f50"] - e0["f50"], atraso_clone_q=c1["f50"] - c0["f50"],
                erro_s=round(abs((c1["f50"] - c0["f50"]) - (e1["f50"] - e0["f50"])) / fps, 3),
                sobreposicao_original=round(sob(e0, e1), 2), sobreposicao_clone=round(sob(c0, c1), 2))


def compara(ref, cand, pecas=None, obturador=True):
    QR, info = le_video(ref); QC, ic = le_video(cand)
    n = min(info["n"], ic["n"])
    if (ic["aw"], ic["ah"]) != (info["aw"], info["ah"]):
        QC = np.stack([cv2.resize(q, (info["aw"], info["ah"]), interpolation=cv2.INTER_AREA) for q in QC])
    QR, QC = QR[:n], QC[:n]; info["n"] = n
    cen = cenas_de(ref, n)
    DR, DC = detalhe_de(QR), detalhe_de(QC)
    # o fundo vem só do original e vale para os dois: o fundo do clone (mediana da cena inteira) mudava quando se
    # mexia num trecho, e a nota de peças de outro trecho ou do outro painel mudava junto
    fr1, fr2 = fundos(QR, cen), fundos(DR, cen)
    F = {1: (fr1, fr1), 2: (fr2, fr2)}
    P = pecas_da_ficha(pecas) if pecas else detecta(QR, DR, info, cen)
    W, H, fps = info["w"], info["h"], info["fps"]
    fw = W if max(W, H) <= 1080 else int(round(W * 1080 / max(W, H) / 2)) * 2
    fh = int(round(H * fw / W / 2)) * 2; k = fw / W
    SS = []
    for t in P:
        SR = series(t, QR, QR if t["nivel"] == 1 else DR, F[t["nivel"]][0], info)
        SC = series(t, QC, QC if t["nivel"] == 1 else DC, F[t["nivel"]][1], info)
        SS.append((t, SR, SC))
    del DR, DC
    fr = sorted({f for t, SR, _ in SS for f in quadros_de_detalhe(SR, max(W, H))})
    GR, GC = burst.grab(str(ref), fr, fps, fw), burst.grab(str(cand), fr, fps, fw)
    res = []
    for t, SR, SC in SS:
        m = mede_par(t, SR, SC, info, GR, GC, k, fw, fh)
        m["rastro"] = rastro(t, SR, SC, QR, QC, info)
        res.append(dict(peca=t["nome"], onde=t["onde"], nivel=t["nivel"], medidas=m))
    escalonamento(res, cen, fps)
    glob = {}
    if obturador:
        o_r, o_c = obturador_de(ref, P, info, cen), obturador_de(cand, P, info, cen)
        glob["obturador"] = dict(original=o_r.get("obturador"), clone=o_c.get("obturador"), estilo=round(fps / 120, 2),
                                 razao=round(o_c["obturador"] / o_r["obturador"], 2) if o_r.get("obturador") and o_c.get("obturador") else None)
    return res, info, cen, glob


# ------------------------------------------------------------------ código: movimento paramétrico
MAX_CHAVES = 4  # início, fim, um passa-do-ponto e uma espera: mais que isso numa grandeza é pose copiada
MOLA_RE = re.compile(r"\b(mola|molaVel|cadeia|cadeiaCor|entrada|saida|caixa|molaErro|escalona)\s*\(")


def _fecha(s, i):
    """índice depois do ']' que fecha o '[' em s[i]"""
    d = 0
    for j in range(i, len(s)):
        if s[j] == "[":
            d += 1
        elif s[j] == "]":
            d -= 1
            if d == 0:
                return j + 1
    return len(s)


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _plano(v):
    return all(_num(x) for x in v) if isinstance(v, list) else _num(v)


def _classifica_serie(v):
    """lista densa (uma entrada por quadro): mapa de tempo, cor por quadro ou pose"""
    if all(isinstance(x, int) and not isinstance(x, bool) and x >= 0 for x in v):
        d = np.diff(v)
        if np.mean(np.isin(d, (0, 1))) >= 0.8:
            return "mapa de tempo"
    if all(isinstance(x, list) and len(x) in (3, 4) and all(isinstance(c, int) and 0 <= c <= 255 for c in x) for x in v):
        return "cor por quadro"
    if all(_plano(x) for x in v):
        return "pose por quadro"
    return None


def _densas(obj, caminho, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _densas(v, f"{caminho}.{k}", out)
    elif isinstance(obj, list):
        if len(obj) >= 20 and (c := _classifica_serie(obj)):
            out.append((caminho, len(obj), c))
        elif obj and isinstance(obj[0], (list, dict)) and not all(_plano(x) for x in obj):
            for i, v in enumerate(obj[:50]):
                _densas(v, f"{caminho}[{i}]", out)


def codigo(hf):
    """procura tabela de pose (chaves [[quadro, valor], ...] com mais de MAX_CHAVES chaves, ou trilha densa, uma
    pose por quadro) e uso das molas do estilo.js nos .js e no <script> do index.html de hf/"""
    hf = Path(hf)
    fontes = []
    for p in sorted(hf.glob("*.js")) + sorted(hf.glob("compositions/*.html")) + [hf / "index.html"]:
        if p.exists() and p.name not in ("estilo.js",) and "node_modules" not in p.parts:
            fontes.append((p.name, p.read_text(errors="ignore")))
    tabelas, densas, mapas, cores, molas = [], [], [], [], 0
    for nome, s in fontes:
        molas += len(MOLA_RE.findall(s))
        i = 0
        while (mm := re.compile(r"\[\s*\[").search(s, i)):
            i = mm.start(); j = _fecha(s, i)
            try:
                T = json.loads(re.sub(r",\s*([\]}])", r"\1", re.sub(r"//[^\n]*", "", s[i:j])))  # JS: vírgula final e comentário
            except ValueError:
                i += 1; continue
            if isinstance(T, list) and len(T) >= 2 and all(isinstance(e, list) and len(e) >= 2 and _num(e[0]) for e in T) \
                    and all(T[k + 1][0] >= T[k][0] for k in range(len(T) - 1)) and all(_plano(e[1]) for e in T):
                if len(T) > MAX_CHAVES:
                    linha = s.count("\n", 0, i) + 1
                    rot = re.search(r"(?:const|let|var)\s+(\w+)\s*=\s*$", s[max(0, i - 80):i])
                    dim = len(T[0][1]) if isinstance(T[0][1], list) else 1
                    tabelas.append(dict(arquivo=nome, linha=linha, nome=rot.group(1) if rot else None, chaves=len(T),
                                        valores_por_chave=dim, quadros=[T[0][0], T[-1][0]]))
            i = j
        for m in re.finditer(r"window\.(\w+)\s*=\s*", s):  # dados gerados: window.X = {...} ou [...]
            a = m.end()
            if a < len(s) and s[a] in "{[":
                try:
                    obj, _ = json.JSONDecoder().raw_decode(s[a:])
                except ValueError:
                    continue
                achou = []
                _densas(obj, m.group(1), achou)
                for c, n_, tipo in achou:
                    item = dict(arquivo=nome, onde=c, quadros=n_)
                    (mapas if tipo == "mapa de tempo" else cores if tipo == "cor por quadro" else densas).append(item)
    aprovado = not tabelas and not densas
    motivos = []
    if tabelas:
        tot = sum(t["chaves"] for t in tabelas)
        motivos.append(f"{len(tabelas)} tabela(s) de chaves com mais de {MAX_CHAVES} chaves ({tot} chaves no total; a maior: "
                       + ", ".join(f"{t['nome'] or t['arquivo']}:{t['linha']} com {t['chaves']}" for t in sorted(tabelas, key=lambda t: -t["chaves"])[:3])
                       + "): pose copiada quadro a quadro ou à mão. Troque cada uma por uma mola (ES.mola, ES.cadeia, ES.entrada) "
                         "com zeta e omega medidos")
    if densas:
        motivos.append(f"{len(densas)} trilha(s) de pose por quadro (" + ", ".join(f"{d['arquivo']}:{d['onde']} ({d['quadros']} q)" for d in densas[:3])
                       + "): a trilha medida serve para ajustar a mola, não para desenhar")
    if not molas:
        motivos.append("nenhuma mola do estilo.js em uso (mola, cadeia, entrada, saida, caixa)")
        aprovado = False if (tabelas or densas) else aprovado
    return dict(aprovado=aprovado, molas_em_uso=molas, tabelas_de_pose=tabelas, trilhas_densas=densas,
                mapas_de_tempo=mapas, cores_por_quadro=cores, motivos=motivos)


# ------------------------------------------------------------------ veredito por peça
PRESETS = None


def preset_perto(z, w):
    """o preset do estilo.js mais perto de (zeta, omega), ou None se nenhum explica (|Δζ| ≤ 0,3 e ω até 1,5x)"""
    global PRESETS
    if PRESETS is None:
        PRESETS = raiox.molas_do_estilo(os.environ.get("ASUI_ESTILO") or os.path.join(AQUI, "..", "..", "estilo", "estilo.js"))[0]
    d = {n: abs(p[0] - z) + abs(math.log(p[1] / w)) for n, p in PRESETS.items()}
    n = min(d, key=d.get)
    return n if abs(PRESETS[n][0] - z) <= 0.3 and 1 / 1.5 <= PRESETS[n][1] / w <= 1.5 else None


def receita(o):
    """a correção da mola: o preset do estilo.js quando ele explica a mola medida, senão a mola medida"""
    n = preset_perto(o["zeta"], o["omega"])
    return f"estilo.mola('{n}')" if n else f"estilo.mola({{zeta: {o['zeta']}, omega: {o['omega']}, u0: {o['impulso']}}})"


def reprova(medida, valor, limite, motivo, correcao, excesso):
    return dict(medida=medida, valor=valor, limite=limite, motivo=motivo, correcao=correcao, peso=round(min(3.0, max(0.05, excesso)), 2))


def julga(r, fps, dim):
    m = r["medidas"]; f = []
    if m["quadros"] >= 10 and m["presente"] < LIM["presente"]:
        f.append(reprova("presente", m["presente"], LIM["presente"], f"a peça só aparece em {round(100 * m['presente'])} % dos quadros em que o original a mostra",
                         "conferir quando a peça nasce e some (Fi e a entrada medida)", (LIM["presente"] - m["presente"]) / LIM["presente"] * 3))
    v = m["velocidade"]
    if v.get("erro") is not None and v["erro"] > LIM["vel_erro"]:
        pq = v["pior_quadro"]
        f.append(reprova("velocidade", v["erro"], LIM["vel_erro"],
                         f"velocidade diferente da do original (erro {br(v['erro'])}x a velocidade; pior no f{pq['f']}: original "
                         f"{pq['original']} px/q, clone {pq['clone']} px/q)",
                         "refazer o movimento com mola de parâmetros medidos (abaixo), começando no quadro do original", v["erro"] / LIM["vel_erro"] - 1))
    q = v["quebras"]; qe = round(q["a_mais"] * 30 / fps, 1)
    if qe > LIM["quebras"]:
        f.append(reprova("quebras", qe, LIM["quebras"], f"{q['a_mais']} quebras de velocidade sem par no original (f{', f'.join(str(int(x)) for x in q['quadros'][:5])})",
                         "chave com interpolação linear ou pose lida à mão: trocar a tabela por estilo.mola/estilo.cadeia", (qe - LIM["quebras"]) / 3))
    for c in m["molas"]:
        o, k = c["original"], c["clone"]
        trecho = f"{c['grandeza']} f{c['a']}-{c['b']} ({c['caminho']:+d} px)"
        if not c["anda"]:  # o clone anda menos de 30 % do caminho: reprova se for quase nada num movimento grande
            if abs(c["caminho"]) >= LIM["anda"][0] * dim and c["caminho_clone"] * np.sign(c["caminho"]) < LIM["anda"][1] * abs(c["caminho"]):
                f.append(reprova("mola", c["caminho_clone"], "anda", f"{trecho}: o clone não faz esse movimento (anda {c['caminho_clone']:+d} px)",
                                 f"animar com {receita(o)} a partir do f{c['a']}", 2.0))
            continue
        if c["curva_rms"] > LIM["curva"]:
            dz = f"ζ {br(k['zeta'])} contra {br(o['zeta'])} medido, ω {br(k['omega'], 1)} contra {br(o['omega'], 1)}" if k else "sem ajuste"
            f.append(reprova("mola", c["curva_rms"], LIM["curva"], f"{trecho}: curva diferente (rms {br(c['curva_rms'])}): {dz}, "
                             f"passa do ponto {round(100 * (k or o)['passa'])} % contra {round(100 * o['passa'])} %, assenta em "
                             f"{br((k or o)['assenta_s'])} s contra {br(o['assenta_s'])} s", f"usar {receita(o)}", c["curva_rms"] / LIM["curva"] - 1))
        elif k and not k["mola"] and k["rms"] - o["rms"] > LIM["sem_mola"]:
            f.append(reprova("mola", k["rms"], LIM["sem_mola"], f"{trecho}: o movimento do clone não é mola (resíduo {br(k['rms'], 3)} contra "
                             f"{br(o['rms'], 3)} no original)", f"usar {receita(o)}", (k["rms"] - o["rms"]) / LIM["sem_mola"] - 1))
    e = m.get("escalonamento")
    if e and e["erro_s"] > LIM["atraso_s"]:
        f.append(reprova("escalonamento", e["erro_s"], LIM["atraso_s"], f"entra {e['atraso_clone_q']} q depois de {e['anterior']}, no original "
                         f"{e['atraso_original_q']} q (sobreposição {br(e['sobreposicao_clone'])} contra {br(e['sobreposicao_original'])})",
                         f"estilo.escalona(i, {round(e['atraso_original_q'] / fps, 3)}) a partir da entrada de {e['anterior']}", e["erro_s"] / LIM["atraso_s"] - 1))
    ra = m.get("rastro")
    if ra and abs(ra["diferenca"]) >= LIM["rastro"][0] and abs(ra["obturador"]) >= LIM["rastro"][1]:
        falta = ra["diferenca"] > 0
        f.append(reprova("rastro", ra["obturador"], LIM["rastro"][1],
                         f"f{ra['quadros'][0]}-{ra['quadros'][1]} a {br(ra['velocidade'], 1)} px/q: rastro de {br(ra['clone'], 1)} px no clone contra "
                         f"{br(ra['original'], 1)} px no original ({'falta' if falta else 'sobra'} {br(abs(ra['obturador']))} quadro de obturador)",
                         "obturador da peça como no original: borrão em linha na direção do movimento (round_mb.sh ou desfoque "
                         "direcional durante o trecho)" if falta else "tirar o borrão a mais da peça nesse trecho",
                         abs(ra["obturador"]) / LIM["rastro"][1] - 1 + 0.5))
    if m["nitidez"] is not None and m["nitidez"] < LIM["nitidez"]:
        f.append(reprova("nitidez", m["nitidez"], LIM["nitidez"], f"peça borrada: nitidez {br(m['nitidez'])}x a do original",
                         "tirar filter: blur fixo ou recorte ampliado; desenhar em vetor no tamanho final", (LIM["nitidez"] - m["nitidez"]) / LIM["nitidez"] * 3))
    if m["delta_e"] is not None and m["delta_e"] > LIM["delta_e"]:
        f.append(reprova("cor", m["delta_e"], LIM["delta_e"], f"cor da peça a ΔE2000 {br(m['delta_e'], 1)} do original",
                         "medir a cor num quadro numerado (select=eq(n,f)) e trocar", m["delta_e"] / LIM["delta_e"] - 1))
    if m["iou"] is not None and m["presente"] > 0 and m["iou"] < LIM["iou"]:
        po = m.get("posicao")
        onde_ = f" (centro a {br(po['erro_px'], 1)} px, {br(po['erro_rel'])}x o tamanho da peça, f{po['quadros'][0]}-{po['quadros'][1]})" if po else ""
        f.append(reprova("forma", m["iou"], LIM["iou"], f"forma ou lugar diferente: IoU da máscara {br(m['iou'])}{onde_}",
                         "ajustar a forma no quadro assentado (maskfit.py) e conferir o lugar", (LIM["iou"] - m["iou"]) / LIM["iou"] * 3))
    if m["ssim"] is not None and m["ssim"] < LIM["ssim"]:
        f.append(reprova("percepcao", m["ssim"], LIM["ssim"], f"o desenho da peça difere (SSIM {br(m['ssim'])} no recorte)",
                         "redesenhar a peça com o original ampliado ao lado (sheet.py no trecho): ícone, avatar, cursor", (LIM["ssim"] - m["ssim"]) / LIM["ssim"] * 3))
    t = m.get("texto")
    if t and min(t.get("confianca") or [0]) >= 70:
        if t["semelhanca"] < LIM["texto"]:
            f.append(reprova("texto", t["semelhanca"], LIM["texto"], f"texto lido \"{t['clone']}\" contra \"{t['original']}\" no original",
                             "conferir o texto, o corte da máscara e o letreiro no quadro", (LIM["texto"] - t["semelhanca"]) / LIM["texto"] * 3))
        for k_, nome in (("altura_x", "altura-x"),):  # a espessura do traço vai no relatório, sem reprovar (bons: até 1,52)
            if t.get(k_) is not None and abs(t[k_] - 1) > LIM[k_]:
                f.append(reprova("texto", t[k_], LIM[k_], f"{nome} {br(t[k_])}x a do original",
                                 "tamanho pela largura da frase (ES.tamanhoPorLargura) e peso pela tinta (inkspan.py)", abs(t[k_] - 1) / LIM[k_] - 1))
    r["reprovacoes"] = sorted(f, key=lambda x: -x["peso"])
    r["aprovada"] = not f
    r["peso"] = round(sum(x["peso"] for x in f), 2)
    return r


def linha_md(r):
    mot = "; ".join(f"**{x['medida']}**: {x['motivo']}. Correção: {x['correcao']}" for x in r["reprovacoes"]) or "passa"
    return f"| {r['peca']} | {r['onde']} | {'passa' if r['aprovada'] else 'REPROVA'} | {mot} |"


def relatorio(titulo, res, glob, extra=""):
    ruins = [r for r in res if not r["aprovada"]]
    L = [f"# {titulo}", "", extra, "", f"Peças: {len(res)}; reprovadas: {len(ruins)}.", ""]
    for k, g in glob.items():
        L.append(f"- **{k}**: {g.get('motivo') or json.dumps({a: b for a, b in g.items() if a != 'motivo'}, ensure_ascii=False)}")
    L += ["", "| peça | onde | veredito | motivo técnico e correção |", "|---|---|---|---|"]
    L += [linha_md(r) for r in sorted(res, key=lambda r: -r["peso"]) if not r["aprovada"]]
    L.append(f"| … | {len(res) - len(ruins)} peça(s) | passa | |")
    return "\n".join(L) + "\n"


def tres_piores(res, glob):
    out = [f"{g['nome']}: {g['motivo']}" for g in glob.values() if g.get("reprova")]
    for r in sorted((r for r in res if not r["aprovada"]), key=lambda r: -r["peso"])[:3]:
        x = r["reprovacoes"][0]
        out.append(f"{r['peca']} ({r['onde']}), {x['medida']}: {x['motivo']}; {x['correcao']}")
    return out[:3 + len([g for g in glob.values() if g.get("reprova")])]


def limpa_json(o):
    if isinstance(o, dict):
        return {k: limpa_json(v) for k, v in o.items() if k != "mask"}
    if isinstance(o, (list, tuple)):
        return [limpa_json(v) for v in o]
    if isinstance(o, np.generic):
        return o.item()
    return o


# ------------------------------------------------------------------ estilo: sem referência (aplicar molde, vídeo novo)
# Faixas do perfil de estilo, calibradas rodando este modo nos 3 originais, nos 3 clones bons e nos 3 exemplos dos
# moldes (todos passam). As molas medidas à mão no ESTILO.md vão de zeta 0,5 a 2,6 e omega 3 a 60; nas peças
# detectadas sozinhas o espalhamento é maior, então a faixa só pega o erro grosso (degrau, reta, mola mole demais).
ESTILO = dict(
    zeta=(0.2, 3.2), omega=(2.5, 110.0), assenta_s=3.7, passa=0.65,  # o pior dos bons, com folga pequena
    molas_min=0.3,         # fração mínima dos movimentos do vídeo que são mola (bons: 0,31 a 0,65)
    quebras=15,            # quebras de velocidade numa peça, contadas como a 30 qps (bons: até 14,5; B2: 55)
    obturador=(0.4, 3.2),  # razão contra o estilo (fps/120); bons: 0,76 a 3,0 (o Joi arrasta de propósito)
    estatico_s=2.0,        # maior trecho com o quadro inteiro parado (bons: até 1,73 s)
    junto_q=0.5,           # escalonamento: grupo de 3+ entradas com atraso mediano abaixo disso (quadros) entra tudo junto
    nitidez_texto=0.15,    # nitidez mínima de um texto (Laplaciano sobre variância; bons: a partir de 0,20)
    fundo_croma=12.0,      # o fundo dominante é neutro (croma Lab abaixo disso; bons: até 0,3)
)


def area_segura(W, H):
    """caixa onde texto pode ficar: no 9:16, 8 % em cima e 18 % embaixo (legenda e botões do Reels) e 4 % dos lados;
    no quadrado e no 16:9, 3 % em volta"""
    if H / W > 1.5:
        return 0.04 * W, 0.08 * H, 0.96 * W, 0.82 * H
    return 0.03 * W, 0.03 * H, 0.97 * W, 0.97 * H


def parado(Q, fps):
    """maior trecho (s) em que o quadro inteiro não muda (diferença média abaixo do ruído de compressão)"""
    d = np.array([float(np.abs(Q[f].astype(np.int16) - Q[f - 1]).mean()) for f in range(1, len(Q))])
    maior = atual = 0
    for x in d:
        atual = atual + 1 if x < 0.15 else 0
        maior = max(maior, atual)
    return round(maior / fps, 2)


def paleta_de(Q):
    amostra = Q[:: max(1, len(Q) // 24)].reshape(-1, 3)
    L = lab(amostra.reshape(1, -1, 3))[0]
    croma = np.hypot(L[:, 1], L[:, 2])
    viz = np.round(amostra / 16).astype(int)
    _, inv, cont = np.unique(viz, axis=0, return_inverse=True, return_counts=True)
    dom = amostra[inv.ravel() == int(np.argmax(cont))].mean(0)
    Ld = lab(dom.reshape(1, 1, 3))[0, 0]
    ac = croma > 20
    hues = np.degrees(np.arctan2(L[ac, 2], L[ac, 1])) % 360
    h, _ = np.histogram(hues, bins=12, range=(0, 360))
    fam = int((h / len(amostra) > 0.003).sum())
    return dict(fundo="#%02x%02x%02x" % tuple(int(round(x)) for x in dom), fundo_croma=round(float(np.hypot(Ld[1], Ld[2])), 1),
                familias_de_cor=fam, fracao_colorida=round(float(ac.mean()), 3))


def estilo(video, hf=None):
    Q, info = le_video(video); fps, W, H = info["fps"], info["w"], info["h"]
    cen = cenas_de(video, info["n"]); D = detalhe_de(Q)
    F = {1: fundos(Q, cen), 2: fundos(D, cen)}
    P = detecta(Q, D, info, cen)
    piso = max(1.5, 0.0015 * max(W, H)) * 30 / fps
    res, SS = [], []
    for t in P:
        S = series(t, Q, Q if t["nivel"] == 1 else D, F[t["nivel"]], info)
        SS.append((t, S))
        res.append(dict(peca=t["nome"], onde=t["onde"], nivel=t["nivel"],
                        medidas=dict(quadros=len(S), molas=molas_de(S, fps, info), quebras=quebras(S, piso), entrada=entrada(S))))
    del D
    fw = W if max(W, H) <= 1080 else int(round(W * 1080 / max(W, H) / 2)) * 2
    fh = int(round(H * fw / W / 2)) * 2; k = fw / W
    fr = {t["nome"]: quadros_de_detalhe(S, max(W, H), 1) for t, S in SS}
    G = burst.grab(str(video), sorted({f for v in fr.values() for f in v}), fps, fw)
    seg = area_segura(W, H)
    for (t, S), r in zip(SS, res):
        f0 = fr[t["nome"]][0] if fr[t["nome"]] else None
        if f0 is None or f0 not in G:
            continue
        x0, y0, x1, y1 = caixa_fina(t, f0, k, fw, fh)
        crop = G[f0][y0:y1, x0:x1]
        if min(crop.shape[:2]) < 10:
            continue
        txt, conf = ocr(crop)
        if txt and conf >= 70:
            # as palavras lidas (não a mancha inteira) contra a área segura, em px do vídeo
            pal = [[(x0 + a_) / k, (y0 + b_) / k, (x0 + c_) / k, (y0 + d_) / k] for a_, b_, c_, d_ in ocr.caixas]
            # palavra cortada pela borda do quadro é letreiro passando, não texto mal posto; folga de meia altura de letra
            fora = [p_ for p_ in pal if min(p_[0], p_[1], W - p_[2], H - p_[3]) > 2
                    and max(seg[0] - p_[0], seg[1] - p_[1], p_[2] - seg[2], p_[3] - seg[3]) > 0.5 * (p_[3] - p_[1])]
            r["medidas"]["texto"] = dict(texto=txt, confianca=round(conf), nitidez=round(nitidez(cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY)), 3),
                                         quadro=f0, caixa=[round(v) for v in (fora[0] if fora else caixa(t, t["f"].index(f0)))],
                                         dentro_da_area_segura=not fora)
    for r in res:
        julga_estilo(r, fps)
    glob = {}
    o = obturador_de(video, P, info, cen).get("obturador")
    est = fps / 120
    glob["obturador"] = dict(nome="obturador", medido=o, estilo=round(est, 2), razao=round(o / est, 2) if o else None)
    if o and not ESTILO["obturador"][0] <= o / est <= ESTILO["obturador"][1]:
        glob["obturador"].update(reprova=True, motivo=f"obturador {br(o)} quadro contra {br(est)} do estilo (1/120 s): "
                                 + ("motion blur de mais" if o > est else "sem motion blur de subquadro") + "; renderizar com round_mb.sh")
    p = parado(Q, fps)
    glob["estatico"] = dict(nome="nada estático", maior_trecho_parado_s=p, limite_s=ESTILO["estatico_s"])
    if p > ESTILO["estatico_s"]:
        glob["estatico"].update(reprova=True, motivo=f"{br(p)} s com o quadro inteiro parado: peça assentada ainda anda (brilho que varre, "
                                "ponteiro, conteúdo que respira)")
    ent = sorted(r["medidas"]["entrada"]["f50"] for r in res if r["medidas"]["entrada"] and r["medidas"]["entrada"]["f10"] > 1)
    grupos, g = [], ent[:1]
    for a, b in zip(ent, ent[1:]):
        if b - a <= 0.6 * fps:
            g.append(b)
        else:
            grupos.append(g); g = [b]
    grupos.append(g)
    juntos = [x for x in grupos if len(x) >= 3 and np.median(np.diff(x)) < ESTILO["junto_q"]]
    glob["escalonamento"] = dict(nome="escalonamento", grupos=[x for x in grupos if len(x) >= 3][:8],
                                 passo_estilo_s=dict(palavra=0.04, botao=0.033, item=0.18, letra=0.1))
    if juntos:
        glob["escalonamento"].update(reprova=True, motivo=f"{len(juntos)} grupo(s) de 3 ou mais peças entrando no mesmo quadro (f{juntos[0][0]}): "
                                     "escalonar com estilo.escalona(i, PASSO.palavra|botao|item)")
    mv = [x for r in res for x in r["medidas"]["molas"] if x["b"] - x["a"] >= 4]
    fm = round(sum(x["mola"] for x in mv) / len(mv), 2) if mv else None
    glob["molas"] = dict(nome="molas", movimentos=len(mv), fracao_mola=fm, minimo=ESTILO["molas_min"])
    if fm is not None and len(mv) >= 5 and fm < ESTILO["molas_min"]:
        glob["molas"].update(reprova=True, motivo=f"só {round(100 * fm)} % dos {len(mv)} movimentos são mola: o resto é reta, degrau ou chave; "
                             "animar pelas molas do estilo.js")
    pal = paleta_de(Q)
    glob["paleta"] = dict(nome="paleta", **pal)
    if pal["fundo_croma"] > ESTILO["fundo_croma"]:
        glob["paleta"].update(reprova=True, motivo=f"fundo dominante {pal['fundo']} colorido (croma {br(pal['fundo_croma'], 1)}): o estilo usa "
                              "fundo neutro (#fdfdfd, #f3f3f3, #0d0d0d) e a cor da marca nas peças")
    if hf:
        c = codigo(hf)
        glob["codigo"] = dict(nome="movimento paramétrico", aprovado=c["aprovado"], molas_em_uso=c["molas_em_uso"], tabelas=len(c["tabelas_de_pose"]),
                              trilhas=len(c["trilhas_densas"]))
        if not c["aprovado"]:
            glob["codigo"].update(reprova=True, motivo="; ".join(c["motivos"]))
    return res, info, glob


def julga_estilo(r, fps):
    m = r["medidas"]; f = []
    zmin, zmax = ESTILO["zeta"]; wmin, wmax = ESTILO["omega"]
    mv = [x for x in m["molas"] if x["b"] - x["a"] >= 4]
    for x in mv:
        if not x["mola"]:
            continue
        fora = []
        if not zmin <= x["zeta"] <= zmax:
            fora.append(f"ζ {br(x['zeta'])} (faixa {br(zmin)} a {br(zmax)})")
        if not wmin <= x["omega"] <= wmax:
            fora.append(f"ω {br(x['omega'], 1)} (faixa {br(wmin, 1)} a {br(wmax, 1)})")
        if x["assenta_s"] > ESTILO["assenta_s"]:
            fora.append(f"assenta em {br(x['assenta_s'])} s (até {br(ESTILO['assenta_s'])})")
        if x["passa"] > ESTILO["passa"]:
            fora.append(f"passa {round(100 * x['passa'])} % do ponto (até {round(100 * ESTILO['passa'])} %)")
        if fora:
            f.append(reprova("mola", x["zeta"], "faixa", f"{x['grandeza']} f{x['a']}-{x['b']}: mola fora do estilo: " + ", ".join(fora),
                             f"usar estilo.mola('{preset_perto(min(max(x['zeta'], zmin), zmax), min(max(x['omega'], wmin), wmax)) or 'suave'}')", 1.0))
    qe = round(len(m["quebras"]) * 30 / fps, 1)
    if qe > ESTILO["quebras"]:
        f.append(reprova("quebras", qe, ESTILO["quebras"], f"{len(m['quebras'])} quebras de velocidade (f{', f'.join(str(int(q)) for q in m['quebras'][:5])})",
                         "trocar chaves com interpolação linear por estilo.mola/estilo.cadeia", (qe - ESTILO["quebras"]) / 5))
    t = m.get("texto")
    if t:
        if t["nitidez"] < ESTILO["nitidez_texto"]:
            f.append(reprova("nitidez", t["nitidez"], ESTILO["nitidez_texto"], f"texto \"{t['texto']}\" borrado no f{t['quadro']} (nitidez {br(t['nitidez'], 3)})",
                             "texto em vetor no tamanho final, sem filter: blur depois de assentar", 1.5))
        if not t["dentro_da_area_segura"]:
            f.append(reprova("area_segura", t["caixa"], "área segura", f"texto \"{t['texto']}\" fora da área segura (caixa {t['caixa']})",
                             "subir ou encolher o texto para dentro da área segura", 1.0))
    r["reprovacoes"] = sorted(f, key=lambda x: -x["peso"])
    r["aprovada"] = not f
    r["peso"] = round(sum(x["peso"] for x in f), 2)
    return r


# ------------------------------------------------------------------ linha de comando
def saida_de(a, video):
    """--saida, ou o bastidor do vídeo (<video>/.apple-style-ui/qualidade-<nome>) quando ele está em <video>/saidas/"""
    if a.saida:
        return a.saida
    v = Path(video).resolve()
    if v.parent.name == "saidas":
        return str(v.parent.parent / ".apple-style-ui" / f"qualidade-{v.stem}")
    return str(v.with_suffix("")) + "-qualidade"


def grava(saida, nome, dados, md):
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    (saida / "qualidade.json").write_text(json.dumps(limpa_json(dados), ensure_ascii=False, indent=1, default=str))
    (saida / "QUALIDADE.md").write_text(md)
    return str(saida / "qualidade.json")


def cmd_comparar(a):
    res, info, cen, g = compara(a.referencia, a.candidato, a.pecas, obturador=not a.sem_obturador)
    for r in res:
        julga(r, info["fps"], max(info["w"], info["h"]))
    glob = {}
    o = g.get("obturador")
    if o:
        glob["obturador"] = dict(nome="obturador", **o)
        if o["razao"] is not None and not LIM["obturador"][0] <= o["razao"] <= LIM["obturador"][1]:
            glob["obturador"].update(reprova=True, motivo=f"obturador {br(o['clone'])} quadro contra {br(o['original'])} do original: "
                                     "renderizar com round_mb.sh e o obturador medido, sem blur de CSS por velocidade")
    if a.hf:
        c = codigo(a.hf)
        glob["codigo"] = dict(nome="movimento paramétrico", aprovado=c["aprovado"], molas_em_uso=c["molas_em_uso"],
                              tabelas=len(c["tabelas_de_pose"]), trilhas=len(c["trilhas_densas"]), mapas_de_tempo=len(c["mapas_de_tempo"]))
        if not c["aprovado"]:
            glob["codigo"].update(reprova=True, motivo="; ".join(c["motivos"]))
    ruins = [r for r in res if not r["aprovada"]]
    aprovada = not ruins and not any(x.get("reprova") for x in glob.values())
    piores = tres_piores(res, glob)
    saida = saida_de(a, a.candidato)
    arq = grava(saida, "comparar", dict(modo="comparar", referencia=str(a.referencia), candidato=str(a.candidato), aprovada=aprovada,
                                        limites=LIM, globais=glob, pecas=sorted(res, key=lambda r: -r["peso"])),
                relatorio("Qualidade por peça: clone contra o original", res, glob, f"Original `{a.referencia}`, clone `{a.candidato}`. "
                          f"{'APROVADA' if aprovada else 'REPROVADA'}: todas as peças precisam passar."))
    resumo = (f"{len(res)} peças, {len(ruins)} reprovada(s)" + "".join(f"; {x['nome']} reprova" for x in glob.values() if x.get("reprova"))
              + ("; APROVADA" if aprovada else f"; pior: {piores[0]}" if piores else ""))
    ok(resumo, None if aprovada else "corrigir as 3 piores e rodar de novo", "tudo passa: pode fechar" if aprovada else
       "atacar as 3 piores, uma hipótese por peça, com mola paramétrica (nada de pose quadro a quadro)",
       aprovada=aprovada, piores=piores, arquivo=arq)


def cmd_estilo(a):
    res, info, glob = estilo(a.video, a.hf)
    ruins = [r for r in res if not r["aprovada"]]
    aprovada = not ruins and not any(x.get("reprova") for x in glob.values())
    piores = tres_piores(res, glob)
    saida = saida_de(a, a.video)
    arq = grava(saida, "estilo", dict(modo="estilo", video=str(a.video), aprovada=aprovada, faixas=ESTILO, globais=glob,
                                      pecas=sorted(res, key=lambda r: -r["peso"])),
                relatorio("Qualidade contra o perfil de estilo", res, glob, f"Vídeo `{a.video}` contra o estilo.js calibrado, sem referência. "
                          f"{'APROVADO' if aprovada else 'REPROVADO'}."))
    resumo = (f"{len(res)} peças, {len(ruins)} fora do estilo" + "".join(f"; {x['nome']} reprova" for x in glob.values() if x.get("reprova"))
              + ("; APROVADO" if aprovada else f"; pior: {piores[0]}" if piores else ""))
    ok(resumo, None if aprovada else "corrigir as 3 piores e renderizar de novo", "pode entregar" if aprovada else
       "atacar as 3 piores com as molas e o escalonamento do estilo.js", aprovada=aprovada, piores=piores, arquivo=arq)


def cmd_codigo(a):
    c = codigo(a.hf)
    ok(("movimento paramétrico: passa" if c["aprovado"] else "REPROVA: " + "; ".join(c["motivos"]))
       + (f"; mapa de tempo permitido: {', '.join(m['onde'] for m in c['mapas_de_tempo'])}" if c["mapas_de_tempo"] else ""),
       None, "" if c["aprovado"] else "trocar as tabelas de pose por molas do estilo.js com parâmetros medidos",
       aprovada=c["aprovado"], **{k: v for k, v in c.items() if k != "aprovado"})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("comparar"); s.add_argument("referencia"); s.add_argument("candidato"); s.add_argument("--pecas")
    s.add_argument("--hf"); s.add_argument("--saida"); s.add_argument("--sem-obturador", action="store_true")
    s = sub.add_parser("estilo"); s.add_argument("video"); s.add_argument("--hf"); s.add_argument("--saida")
    s = sub.add_parser("codigo"); s.add_argument("hf")
    a = ap.parse_args()
    for x in [getattr(a, k, None) for k in ("referencia", "candidato", "video", "hf", "pecas")]:
        if x and not Path(x).exists():
            falha(f"não encontrado: {x}", 1)
    dict(comparar=cmd_comparar, estilo=cmd_estilo, codigo=cmd_codigo)[a.cmd](a)


if __name__ == "__main__":
    main()
