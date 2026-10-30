#!/usr/bin/env python3
"""raiox.py <video> <pasta_saida> [--estilo estilo.js] [--sem-burst] [--legenda auto|sim|nao]

O raio-x: a medição do ciclo de clonagem, empacotada, sem clonar. Em poucos minutos devolve
  - duração, fps, cortes secos e cenas (trocas sem corte também, que quase sempre são morph);
  - as curvas de movimento dos elementos principais (posição e tamanho por quadro);
  - as molas estimadas em cada movimento, comparadas com suave, firme e elástica do estilo.js;
  - o obturador estimado (fração do quadro em que o motion blur fica exposto);
  - o BPM e se os eventos caem na batida ou nos golpes da trilha;
  - a paleta e a folha de quadros;
  - se o texto entra palavra a palavra (legenda cinética, ou interface com muito texto animado): aí cada palavra vira
    trilha própria (trilha_palavra.py), com entrada e saída medidas.
Saídas em <pasta_saida>: RAIOX.md (português simples), raiox.json, folha.jpg, curvas.png e analise/ (a análise
do burst.py, que o compare.py usa depois para dar a nota de cada rodada).

Como mede, em uma linha cada:
  elementos: fundo = mediana no tempo de cada cena; o que difere do fundo vira mancha; manchas seguidas de
    quadro em quadro (sobreposição com a posição prevista) viram trilhas; as que mais andam são as principais.
  palavras: traço fino de letra (black-hat/top-hat), letras juntadas em palavra e palavra seguida quadro a quadro;
    com 6 palavras ou mais nascendo em momentos diferentes, o texto entra palavra a palavra e as palavras que mexem
    entram nas molas e no obturador (as manchas de legenda são pequenas e curtas demais para a análise de manchas).
    O teste não separa legenda de interface com muito texto (Satellite, Joi e VoiceOS também passam); --legenda nao
    desliga, --legenda sim força.
  molas: cada trecho em que uma grandeza sai de um repouso e assenta em outro é ajustado (mínimos quadrados)
    ao oscilador amortecido do estilo.js (zeta, omega, impulso), e comparado com as três molas do estilo.
  obturador: cada peça rápida (ou pan) é comparada com um quadro parado dela mesmo, alinhado e borrado por uma
    linha de L px na direção do movimento; o L que mais se parece dá obturador = L / velocidade (px por quadro).
  batida: BPM e onsets pelo fluxo espectral (audio.py); acerto = evento a até max(1 quadro, 33 ms) da marca;
    acaso = a mesma lista deslocada no tempo 2.000 vezes.
"""
from __future__ import annotations
import argparse, json, math, os, re, subprocess, sys, time
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy.optimize import least_squares

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import burst  # noqa: E402
import cuts as cortes_mod  # noqa: E402
import audio as audio_mod  # noqa: E402
import trilha_palavra as tp  # noqa: E402
from common import probe  # noqa: E402
from saida import quadros  # noqa: E402

LADO = 480  # lado maior da análise de manchas
MOLAS_PADRAO = {"suave": (1.22, 20.0, 0.0), "firme": (1.57, 37.9, 0.0), "elastica": (0.62, 19.2, 0.0)}


def br(x, n=2):
    """número no jeito brasileiro"""
    return f"{x:.{n}f}".replace(".", ",")


# ------------------------------------------------------------------ molas (mesma forma fechada do estilo.js)
def mola_erro(t, e0, v0, z, w):
    t = np.maximum(np.asarray(t, float), 0)
    if z < 0.9999:
        a = z * w; wd = w * math.sqrt(1 - z * z); B = (v0 + a * e0) / wd
        return np.exp(-a * t) * (e0 * np.cos(wd * t) + B * np.sin(wd * t))
    if z <= 1.0001:
        c = v0 + w * e0
        return np.exp(-w * t) * (e0 + c * t)
    q = math.sqrt(z * z - 1); r1 = -w * (z - q); r2 = -w * (z + q)
    A = (v0 - r2 * e0) / (r1 - r2)
    return A * np.exp(r1 * t) + (e0 - A) * np.exp(r2 * t)


def mola(t, z, w, u0=0.0, t0=0.0):
    t = np.asarray(t, float) - t0
    return np.where(t <= 0, 0.0, 1 - mola_erro(t, 1.0, -u0, z, w))


def assenta(z, w, u0=0.0, tol=0.02):
    t = np.arange(0, 6, 0.001); e = np.abs(1 - mola(t, z, w, u0))
    fora = np.where(e > tol)[0]
    return float(t[fora[-1]]) if len(fora) else 0.0


def perda_q30(z, w):
    """quanto do que falta sobra a cada 1/30 s no fim do caminho"""
    k = z * w if z < 1 else w * (z - math.sqrt(z * z - 1))
    return math.exp(-k / 30)


def molas_do_estilo(caminho):
    try:
        s = open(caminho).read()
        m = {n: (float(z), float(w), float(u)) for n, z, w, u in
             re.findall(r"(suave|firme|elastica):\s*\{\s*zeta:\s*([\d.]+),\s*omega:\s*([\d.]+),\s*u0:\s*([\d.]+)", s)}
        if len(m) == 3:
            return m, caminho
    except OSError:
        pass
    return dict(MOLAS_PADRAO), "valores embutidos (estilo.js não encontrado)"


def ajusta_mola(t, p, fps):
    """mínimos quadrados de p(t) = mola(t - t0); devolve dict ou None"""
    best = None
    for z0 in (0.5, 0.9, 1.5):
        for w0 in (10.0, 22.0, 40.0):
            try:
                r = least_squares(lambda x: mola(t, x[0], x[1], x[2], x[3]) - p, [z0, w0, 1.0, 0.0],
                                  bounds=([0.15, 2.0, 0.0, -1.5 / fps], [4.0, 120.0, 40.0, 1.5 / fps]))
            except ValueError:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return None
    z, w, u0, t0 = best.x
    return dict(zeta=round(float(z), 2), omega=round(float(w), 1), u0=round(float(u0), 1), t0=float(t0),
                rms=round(float(np.sqrt(np.mean(best.fun ** 2))), 3))


# ------------------------------------------------------------------ manchas e trilhas
def decodifica(video, w, h, fps):
    k = LADO / max(w, h)
    aw, ah = max(2, int(round(w * k / 2)) * 2), max(2, int(round(h * k / 2)) * 2)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"scale={aw}:{ah}:flags=area", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, ah, aw, 3), w / aw


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1]); x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    return i / max(1e-9, a[2] * a[3] + b[2] * b[3] - i)


def trilhas_da_cena(Q, a, b, esc, area_min=0.0015, limiar=28):
    """manchas diferentes do fundo (mediana da cena), seguidas quadro a quadro. Coordenadas em px do original.
    area_min (fração do quadro) e limiar: o qualidade.py pede peças menores (cursor, avatar)."""
    n = b - a
    amostra = Q[a:b:max(1, n // 60)]
    fundo = np.median(amostra, axis=0).astype(np.int16)
    ah, aw = Q.shape[1:3]; area_q = aw * ah
    k1, k2 = np.ones((3, 3), np.uint8), np.ones((9, 9), np.uint8)
    vivas, todas = [], []
    for f in range(a, b):
        m = (np.abs(Q[f].astype(np.int16) - fundo).max(-1) > limiar).astype(np.uint8)
        m = cv2.morphologyEx(cv2.morphologyEx(m, cv2.MORPH_OPEN, k1), cv2.MORPH_CLOSE, k2)
        nc, _, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
        comps = [(float(st[i, 0]), float(st[i, 1]), float(st[i, 2]), float(st[i, 3]), float(st[i, 4]))
                 for i in range(1, nc) if area_min * area_q <= st[i, 4] <= 0.6 * area_q]
        livres = set(range(len(comps)))
        pares = []
        for ti, tr in enumerate(vivas):
            x, y, w, h = tr["caixa"][-1]
            vx, vy = tr.get("v", (0.0, 0.0))
            prev = (x + vx, y + vy, w, h)
            for ci, c in enumerate(comps):
                s = iou(prev, c[:4])
                if s < 0.15:
                    d = math.hypot(c[0] + c[2] / 2 - (prev[0] + w / 2), c[1] + c[3] / 2 - (prev[1] + h / 2))
                    r = (c[2] * c[3]) / max(1.0, w * h)
                    s = 0.1 * (1 - d / (0.12 * math.hypot(aw, ah))) if d < 0.12 * math.hypot(aw, ah) and 0.4 < r < 2.5 else 0
                if s > 0:
                    pares.append((s, ti, ci))
        usados_t = set()
        for s, ti, ci in sorted(pares, reverse=True):
            if ti in usados_t or ci not in livres:
                continue
            tr = vivas[ti]; c = comps[ci]; x, y, w, h = tr["caixa"][-1]
            tr["v"] = (c[0] + c[2] / 2 - x - w / 2, c[1] + c[3] / 2 - y - h / 2)
            tr["caixa"].append(c[:4]); tr["f"].append(f); tr["perdido"] = 0
            usados_t.add(ti); livres.discard(ci)
        for ti, tr in enumerate(vivas):
            if ti not in usados_t:
                tr["perdido"] = tr.get("perdido", 0) + 1
        for ci in livres:
            vivas.append(dict(f=[f], caixa=[comps[ci][:4]], perdido=0))
        for tr in [t for t in vivas if t["perdido"] > 2]:
            todas.append(tr)
        vivas = [t for t in vivas if t["perdido"] <= 2]
    todas += vivas
    out = []
    for tr in todas:
        if len(tr["f"]) < 6:
            continue
        cx = np.array([(x + w / 2) * esc for x, y, w, h in tr["caixa"]]); cy = np.array([(y + h / 2) * esc for x, y, w, h in tr["caixa"]])
        W = np.array([w * esc for x, y, w, h in tr["caixa"]]); H = np.array([h * esc for x, y, w, h in tr["caixa"]])
        out.append(dict(f=tr["f"], cx=cx, cy=cy, w=W, h=H))
    return out


def preenche(tr):
    """trilha com buraco vira contínua (interpolação): nunca deixar um null no meio da trilha"""
    f = np.array(tr["f"]); fs = np.arange(f[0], f[-1] + 1)
    return dict(f=fs.tolist(), **{k: np.interp(fs, f, tr[k]) for k in ("cx", "cy", "w", "h")})


def movimentos(q, f, fps, dim, nome):
    """trechos em que q sai de um repouso e assenta em outro"""
    q = np.asarray(q, float); n = len(q)
    if n < 6:
        return []
    passo = np.abs(np.diff(q))
    lim = max(0.6, 0.0025 * dim) * 30 / fps
    ativo = passo > lim
    k = max(2, int(round(0.1 * fps)))
    out, i = [], 0
    while i < len(ativo):
        if not ativo[i]:
            i += 1; continue
        j = i
        while j + 1 < len(ativo) and (ativo[j + 1] or (j + 2 < len(ativo) and ativo[j + 2])):
            j += 1
        # duas corcovas de velocidade (incha e depois transforma) são dois movimentos: corta no vale
        cortes = [i]
        sp = passo[i:j + 1]
        for m in range(2, len(sp) - 2):
            if sp[m] <= sp[m - 1] and sp[m] <= sp[m + 1] and sp[m] < 0.45 * min(sp[:m].max(), sp[m + 1:].max()):
                cortes.append(i + m)
        cortes.append(j + 1)
        for a0, b0 in zip(cortes[:-1], cortes[1:]):
            # a mola sai do repouso já quase na velocidade máxima: o começo lento antes disso é preparação
            a0 += int(np.argmax(passo[a0:b0] >= 0.25 * passo[a0:b0].max()))
            prox = cortes[cortes.index(b0) + 1] if b0 != cortes[-1] else None
            cauda = q[b0:b0 + k] if prox is None else q[b0:b0 + 1]
            if len(cauda) >= (1 if prox is not None else max(2, k // 2)):
                q0, q1 = q[a0], float(np.median(cauda))
                if abs(q1 - q0) >= max(0.03 * dim, 10) and b0 - a0 >= 3:
                    fim = min(n - 1, b0 + 2 * k) if prox is None else b0
                    out.append(dict(grandeza=nome, a=int(f[a0]), b=int(f[b0]), q0=float(q0), q1=q1,
                                    serie=q[a0:fim + 1].tolist(), f_serie=[int(x) for x in f[a0:fim + 1]]))
        i = j + 1
    return out


def classifica_cortes(video, cand):
    """Corte seco: as bordas do quadro anterior somem de repente (menos de 30 % sobrevivem e o par anterior
    mantinha 30 pontos a mais), ou a imagem inteira troca (mais de 90 % dos pixels) sem borda que fique.
    Em UI de fundo liso o teste de continuidade por pontos falha (pouca textura) e chama morph de corte."""
    if not cand:
        return [], []
    fr = {}
    need = set(x for c in cand for x in (c - 2, c - 1, c, c + 1) if x >= 0)
    for i, f in cortes_mod.iter_frames(video, width=320, gray=False):
        if i in need:
            fr[i] = f
    def sobrevive(a, b):
        ea = cv2.Canny(fr[a], 60, 150) > 0
        eb = cv2.dilate((cv2.Canny(fr[b], 60, 150) > 0).astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        return (ea & eb).sum() / max(1, ea.sum()), int(ea.sum())
    secos, trocas = [], []
    for c in cand:
        if c < 2 or c not in fr:
            continue
        s1, nb = sobrevive(c - 1, c); s0, _ = sobrevive(c - 2, c - 1)
        muda = lambda x, y: float((np.abs(fr[y].astype(int) - fr[x].astype(int)).max(-1) > 40).mean())
        chg, chg0 = muda(c - 1, c), muda(c - 2, c - 1)
        chg1 = muda(c, c + 1) if c + 1 in fr else 0.0
        # imagem inteira troca de uma vez (num esmaecimento a troca se espalha por vários quadros)
        seco = (nb >= 50 and s1 < 0.3 and s0 - s1 > 0.3) or (chg > 0.9 and s1 < 0.2 and chg0 < 0.3 and chg1 < 0.3)
        (secos if seco else trocas).append(c)
    return secos, trocas


# ------------------------------------------------------------------ obturador
def linha(L, ux, uy):
    """núcleo de borrão em linha (obturador): comprimento L px na direção (ux, uy)"""
    if L < 0.75:
        return None
    k = int(math.ceil(L)) | 1
    k += 2
    ker = np.zeros((k, k), np.float32); c = k // 2
    n = max(2, int(L * 4))
    for t in np.linspace(-L / 2, L / 2, n):
        x, y = c + t * ux, c + t * uy
        x0, y0 = int(math.floor(x)), int(math.floor(y)); fx, fy = x - x0, y - y0
        for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)), (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            if 0 <= x0 + dx < k and 0 <= y0 + dy < k:
                ker[y0 + dy, x0 + dx] += wgt
    return ker / ker.sum()


def obturador(video, fps, w, h, trilhas, cam, cenas):
    """Para cada peça rápida (ou pan do quadro inteiro), acha um quadro parado da mesma peça, alinha, borra esse
    quadro nítido com uma linha de comprimento L na direção do movimento e escolhe o L que mais se parece com o
    quadro em movimento. Obturador = L / velocidade. É o shutterfit do clone VoiceOS, generalizado."""
    cena_de = lambda f: next((c["cena"] for c in cenas if c["a"] <= f <= c["b"]), None)
    cand = []  # (v_aprox, f, g, caixa_f, caixa_g) caixas em px do original (x0, y0, x1, y1)
    for tr in trilhas:
        f = np.array(tr["f"]); cx, cy, W, H = tr["cx"], tr["cy"], tr["w"], tr["h"]
        vel = np.hypot(np.gradient(cx), np.gradient(cy))
        for k in range(1, len(f) - 1):
            if vel[k] < 8 or min(W[k], H[k]) < 40:
                continue
            for d in list(range(1, 41)):
                for kk in (k + d, k - d):
                    if 0 <= kk < len(f) and vel[kk] < 1.5 and abs(W[kk] / W[k] - 1) < 0.08 and abs(H[kk] / H[k] - 1) < 0.08 \
                            and cena_de(int(f[kk])) == cena_de(int(f[k])):
                        bx = lambda j: (cx[j] - W[j] / 2, cy[j] - H[j] / 2, cx[j] + W[j] / 2, cy[j] + H[j] / 2)
                        cand.append((float(vel[k]), int(f[k]), int(f[kk]), bx(k), bx(kk)))
                        break
                else:
                    continue
                break
    sp = np.hypot(cam[:, 0], cam[:, 1]) if len(cam) else np.zeros(0)
    for i in range(len(sp)):
        fi = i + 1
        if sp[i] < 8 or cam[i, 2] < 0.3:
            continue
        for d in range(1, 41):
            achou = False
            for g in (fi - d, fi + d):
                if 1 <= g < len(sp) + 1 and sp[g - 1] < 1.5 and cam[g - 1, 2] > 0.3 and cena_de(g) == cena_de(fi):
                    a, b = sorted((g, fi))
                    acum = np.abs(cam[a - 1:b - 1, :2].sum(0)) if b > a else np.zeros(2)
                    if max(acum) < 0.3 * min(w, h):
                        cand.append((float(sp[i]), fi, g, (0.1 * w, 0.1 * h, 0.9 * w, 0.9 * h), None))
                        achou = True; break
            if achou:
                break
    if not cand:
        return dict(amostras=0, obturador=None)
    cand.sort(key=lambda c: -c[0])
    escolhidos, janelas = [], {}
    for c in cand:  # no máximo 3 por trecho de 10 quadros
        j = c[1] // 10
        if janelas.get(j, 0) < 3:
            escolhidos.append(c); janelas[j] = janelas.get(j, 0) + 1
        if len(escolhidos) >= 20:
            break
    precisa = sorted(set(x for c in escolhidos for x in (c[1] - 1, c[1], c[1] + 1, c[2])))
    Qs = burst.grab(video, precisa, fps, w)
    cinza = lambda im: im.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    vals = []
    for v0, f, g, bf, bg in escolhidos:
        if any(x not in Qs for x in (f - 1, f, f + 1, g)):
            continue
        mg = 0.8 * v0 + 12
        x0, y0 = int(max(0, bf[0] - mg)), int(max(0, bf[1] - mg)); x1, y1 = int(min(w, bf[2] + mg)), int(min(h, bf[3] + mg))
        if x1 - x0 < 48 or y1 - y0 < 48:
            continue
        han = cv2.createHanningWindow((x1 - x0, y1 - y0), cv2.CV_32F)
        A, Bq = cinza(Qs[f - 1])[y0:y1, x0:x1], cinza(Qs[f + 1])[y0:y1, x0:x1]
        (dx, dy), r1 = cv2.phaseCorrelate(A, Bq, han)
        v = math.hypot(dx, dy) / 2
        if r1 < 0.05 or v < 6:
            continue
        ux, uy = dx / (2 * v), dy / (2 * v)
        F = cinza(Qs[f])[y0:y1, x0:x1]
        G = cinza(Qs[g])
        # região de busca no quadro parado: onde a peça está em g, com folga (a caixa da mancha é aproximada)
        if bg is not None:
            gx0, gy0, gx1, gy1 = bg[0] - mg, bg[1] - mg, bg[2] + mg, bg[3] + mg
        else:
            gx0, gy0, gx1, gy1 = x0, y0, x1, y1
        folga = 0.25 * max(x1 - x0, y1 - y0) + 24
        gx0, gy0 = int(max(0, gx0 - folga)), int(max(0, gy0 - folga)); gx1, gy1 = int(min(w, gx1 + folga)), int(min(h, gy1 + folga))
        # molde = miolo do quadro em movimento (tira a borda que o borrão contamina)
        corte = int(0.5 * v + 6)
        T = F[corte:-corte, corte:-corte] if F.shape[0] > 2 * corte + 24 and F.shape[1] > 2 * corte + 24 else None
        if T is None or T.std() < 4 or gx1 - gx0 <= T.shape[1] or gy1 - gy0 <= T.shape[0]:
            continue
        k = min(1.0, 640 / max(gx1 - gx0, gy1 - gy0))  # pan de quadro inteiro: trabalha menor
        Greg = cv2.resize(G[gy0:gy1, gx0:gx1], None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        Tk = cv2.resize(T, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
        # o máximo da correlação normalizada acontece quando o borrão do quadro parado iguala o do quadro em
        # movimento (Cauchy-Schwarz); com |diferença| o borrão sempre "ganharia" por suavizar o que não bate
        # o desfoque animado (entrada que nasce desfocada) é igual para todos os lados: entra como gaussiana à
        # parte, para não ser contado como obturador
        melhor = None
        for sg in (0, 1.5, 3, 5, 8):
            Gs = Greg if sg == 0 else cv2.GaussianBlur(Greg, (0, 0), sg * k)
            curva = []
            for Lb in np.arange(0, 1.6 * v + 0.01, max(0.5, v / 24)):
                ker = linha(Lb * k, ux, uy)
                Gb = Gs if ker is None else cv2.filter2D(Gs, -1, ker, borderType=cv2.BORDER_REPLICATE)
                curva.append((float(cv2.matchTemplate(Gb, Tk, cv2.TM_CCOEFF_NORMED).max()), float(Lb)))
            if melhor is None or max(curva)[0] > melhor[0][0]:
                melhor = (max(curva), curva, sg)
        (e_min, Lb), curva, sg = melhor
        e_zero = curva[0][0]
        if e_min < 0.93 or e_min - e_zero < 0.004:  # peça parada diferente, ou o borrão não explica nada
            continue
        i = [c[1] for c in curva].index(Lb)
        if 0 < i < len(curva) - 1:  # refino parabólico
            a_, b_, c_ = curva[i - 1][0], curva[i][0], curva[i + 1][0]
            den = a_ - 2 * b_ + c_
            if den < 0:
                Lb += 0.5 * (a_ - c_) / den * (curva[1][1] - curva[0][1])
        vals.append(Lb / v)
        if os.environ.get("RAIOX_DEBUG"):
            print("obt", f, "parado", g, "v", round(v, 1), "L", round(Lb, 1), "s", round(Lb / v, 2), "ncc", round(e_min, 3), "sem borrão", round(e_zero, 3), "gauss", sg, file=sys.stderr)
    if len(vals) < 2:
        return dict(amostras=len(vals), obturador=None)
    vals = np.array(vals)
    return dict(amostras=int(len(vals)), obturador=round(float(np.median(vals)), 2),
                faixa=[round(float(np.percentile(vals, 25)), 2), round(float(np.percentile(vals, 75)), 2)])


# ------------------------------------------------------------------ batida
def encaixe(eventos, grade_t, tol):
    if len(eventos) == 0 or len(grade_t) < 2:
        return 0
    g = np.asarray(grade_t)
    return int(sum(np.min(np.abs(g - t)) <= tol for t in eventos))


def eventos_visuais(energia, fps):
    """começos de movimento: picos da subida da energia por quadro (o "onset" da imagem)"""
    e = np.asarray(energia, float); k = max(1, int(round(fps / 30)))
    es = np.convolve(e, np.ones(k) / k, mode="same")
    sobe = np.maximum(0, np.diff(es, prepend=es[0]))
    lim = max(0.002, float(np.percentile(sobe, 90))); w = int(0.15 * fps)
    return [i for i in range(1, len(e) - 1) if sobe[i] > lim and sobe[i] == sobe[max(0, i - w):i + w + 1].max()]


def batida(video, fps, eventos_s, dur, bpm_burst=None):
    a = audio_mod.analyze(video)
    bpm = a.get("tempo_bpm")
    if bpm and bpm_burst and abs(bpm / bpm_burst - 1) > 0.04:
        bpm = bpm_burst  # os dois estimadores discordam (3:2 é o erro comum): fica o sem viés de 120 BPM
    out = dict(classe=a.get("class"), bpm=bpm, forca=a.get("beat_strength"),
               onsets_por_s=a.get("onsets_per_s"), eventos=len(eventos_s))
    if not a.get("has_audio") or not eventos_s:
        return out
    tol = max(1 / fps, 0.033)
    on = np.array(a.get("onsets_s") or [])
    rng = np.random.default_rng(7)
    ev = np.array(sorted(eventos_s))
    if on.size:
        hit = encaixe(ev, on, tol)
        acaso = [encaixe((ev + d) % dur, on, tol) for d in rng.uniform(-2, 2, 2000)]
        out["nos_onsets"] = dict(acertos=hit, acaso=round(float(np.mean(acaso)), 1),
                                 p=round(float(np.mean(np.array(acaso) >= hit)), 3))
    if bpm and on.size >= 4:
        per = 60 / bpm / 2  # colcheia; fase = média circular dos golpes
        ang = 2 * np.pi * (on % per) / per
        fase = (math.atan2(np.sin(ang).sum(), np.cos(ang).sum()) % (2 * np.pi)) / (2 * np.pi) * per
        grade_t = np.arange(fase, dur + per, per)
        hit = encaixe(ev, grade_t, tol)
        q = min(1.0, 2 * tol / per)  # chance de um evento solto cair a até tol de uma marca
        p_bin = sum(math.comb(len(ev), j) * q ** j * (1 - q) ** (len(ev) - j) for j in range(hit, len(ev) + 1))
        out["na_colcheia"] = dict(acertos=hit, acaso=round(q * len(ev), 1), p=round(p_bin, 3), colcheia_ms=round(per * 1000))
    seg = lambda k: k in out and out[k]["acertos"] >= max(3, 0.4 * len(ev)) and out[k]["p"] <= 0.1
    out["leitura"] = ("segue a batida (colcheias)" if seg("na_colcheia") else
                      "segue os golpes da trilha, não a grade" if seg("nos_onsets") else "não segue a batida")
    return out


# ------------------------------------------------------------------ desenhos
def curvas_png(caminho, principais, fps, nf, ajustes):
    L, A, M = 1400, 120, 30
    im = Image.new("RGB", (L, M + A * max(1, len(principais)) + 20), (18, 18, 18)); d = ImageDraw.Draw(im)
    fnt = burst.font(14)
    d.text((10, 8), "curvas por elemento (vermelho x, verde y, azul largura, amarelo altura; faixa = movimento com mola ajustada)",
           fill=(220, 220, 220), font=fnt)
    X = lambda f: 60 + (L - 80) * f / max(1, nf - 1)
    for r, el in enumerate(principais):
        y0 = M + r * A
        d.text((6, y0 + 4), el["nome"], fill=(255, 220, 120), font=fnt)
        for aj in ajustes:
            if aj["elemento"] == el["nome"]:
                d.rectangle([X(aj["a"]), y0 + 22, X(aj["b"]), y0 + A - 8], fill=(40, 48, 70))
        for k, cor in (("cx", (230, 90, 90)), ("cy", (110, 220, 120)), ("w", (110, 150, 240)), ("h", (230, 210, 90))):
            v = np.array(el[k]); lo, hi = v.min(), v.max()
            if hi - lo < 1e-6:
                continue
            pts = [(X(f), y0 + A - 10 - (A - 36) * (x - lo) / (hi - lo)) for f, x in zip(el["f"], v)]
            d.line(pts, fill=cor, width=2)
    for f in range(0, nf, max(1, int(fps))):
        d.text((X(f) - 8, im.height - 18), f"{f / fps:.0f}s", fill=(150, 150, 150), font=fnt)
    im.save(caminho)


def folha(video, caminho, meta, n, cortes):
    fps = meta["fps"]; w = 300 if meta["w"] >= meta["h"] else 200
    idx = sorted(set([int(round(i)) for i in np.linspace(0, n - 1, 24)] + [c for c in cortes] + [c - 1 for c in cortes if c > 0]))
    q = burst.grab(video, idx, fps, w)
    rot = [("CORTE " if i in cortes else "") + f"f{i} {i / fps:.2f}s" for i in idx if i in q]
    im = burst.sheet([q[i] for i in idx if i in q], rot, 6, f"{os.path.basename(video)}: {len(idx)} quadros")
    if im:
        im.convert("RGB").save(caminho, quality=88)


# ------------------------------------------------------------------ principal
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("saida")
    ap.add_argument("--estilo", default=os.environ.get("ASUI_ESTILO") or os.path.join(AQUI, "..", "..", "..", "motor", "estilo", "estilo.js"))
    ap.add_argument("--sem-burst", action="store_true", help="reaproveita saida/analise/ já feita")
    ap.add_argument("--eventos", help="quadros dos eventos grandes (da ficha), separados por vírgula, para o teste da batida")
    ap.add_argument("--legenda", choices=("auto", "sim", "nao"), default="auto", help="legenda cinética: decide sozinho, ou força")
    a = ap.parse_args()
    T0 = time.time()
    os.makedirs(a.saida, exist_ok=True)
    pm = probe(a.video)
    meta = dict(w=pm["width"], h=pm["height"], fps=pm["fps"], dur=pm["duration_s"])
    fps = meta["fps"]
    an = os.path.join(a.saida, "analise")
    if not (a.sem_burst and os.path.exists(os.path.join(an, "analysis.json"))):
        subprocess.run([sys.executable, os.path.join(AQUI, "burst.py"), a.video, an], check=True, capture_output=True)
    B = json.load(open(os.path.join(an, "analysis.json")))
    n = B["frames"]
    molas_est, origem_molas = molas_do_estilo(a.estilo)

    # cortes: o burst e o cuts.py acham toda troca grande; a sobrevivência das bordas separa corte seco de morph
    C = cortes_mod.detect(a.video)
    cand = sorted(set([c["frame"] for c in C["cuts"]] + [s["start_f"] for s in B["shots"][1:]]))
    secos, trocas = classifica_cortes(a.video, cand)
    lim = [0] + secos + [n]
    cenas = []
    for i in range(len(lim) - 1):
        s0, s1 = lim[i], lim[i + 1]
        pal = []
        for s in B["shots"]:
            if s["start_f"] < s1 and s["end_f"] >= s0:
                pal += [p["hex"] for p in s["palette"][:3]]
        cenas.append(dict(cena=i + 1, a=s0, b=s1 - 1, dur_s=round((s1 - s0) / fps, 2),
                          trocas_sem_corte=[t for t in trocas if s0 < t < s1], paleta=list(dict.fromkeys(pal))[:6]))

    # elementos
    Q, esc = decodifica(a.video, meta["w"], meta["h"], fps)
    Q = Q[:n]
    trilhas = []
    for c in cenas:
        trilhas += trilhas_da_cena(Q, c["a"], c["b"] + 1, esc)
    trilhas = [preenche(t) for t in trilhas]
    dim = max(meta["w"], meta["h"])
    for t in trilhas:
        t["anda"] = float(np.abs(np.diff(t["cx"])).sum() + np.abs(np.diff(t["cy"])).sum()
                          + np.abs(np.diff(t["w"])).sum() + np.abs(np.diff(t["h"])).sum())
    princ = [t for t in sorted(trilhas, key=lambda t: -t["anda"]) if t["anda"] > 0.15 * dim][:8]
    princ.sort(key=lambda t: t["f"][0])
    for i, t in enumerate(princ):
        k = int(np.argmax(t["w"] * t["h"]))
        t["nome"] = f"E{i + 1}"
        t["onde"] = dict(f=t["f"][k], x=round(t["cx"][k]), y=round(t["cy"][k]), w=round(t["w"][k]), h=round(t["h"][k]))

    # legenda cinética: cada palavra vira trilha (a análise de manchas só vê manchas pequenas e curtas)
    larg = min(540, meta["w"])
    pal, eh_leg, res_pal = tp.acha_palavras(quadros(a.video, largura=larg), meta["w"] / larg, fps, n)
    legenda = eh_leg if a.legenda == "auto" else a.legenda == "sim"
    pal_tr = [tp.para_raiox(p) for p in pal] if legenda else []
    for t in pal_tr:  # quanto anda = soma das faixas (máx - mín) de x, y, largura e altura; tremor de medida não soma
        t["anda"] = float(sum(np.ptp(t[k]) for k in ("cx", "cy", "w", "h")))
        t["dim"] = 10 * float(np.median(t["h"]))  # mexer 30 % da altura da letra já é movimento de palavra
    pal_mexe = sorted((t for t in pal_tr if t["anda"] > 0.03 * t["dim"]), key=lambda t: -t["anda"])[:12]
    for t in pal_mexe:
        k = int(np.argmax(t["w"] * t["h"]))
        t["onde"] = dict(f=t["f"][k], x=round(t["cx"][k]), y=round(t["cy"][k]), w=round(t["w"][k]), h=round(t["h"][k]))

    # molas
    ajustes = []
    for t in princ + pal_mexe:
        f = np.array(t["f"])
        for g, d_ in (("x", meta["w"]), ("y", meta["h"]), ("largura", meta["w"]), ("altura", meta["h"])):
            d_ = t.get("dim", d_)
            serie = {"x": t["cx"], "y": t["cy"], "largura": t["w"], "altura": t["h"]}[g]
            for mv in movimentos(serie, f, fps, d_, g):
                q = np.array(mv["serie"]); tt = (np.array(mv["f_serie"]) - mv["a"]) / fps
                p = (q - mv["q0"]) / (mv["q1"] - mv["q0"])
                aj = ajusta_mola(tt, p, fps)
                if not aj or aj["rms"] > 0.08 or not 2.5 < aj["omega"] < 115 or not 0.16 < aj["zeta"] < 3.9 or mv["b"] - mv["a"] < 4:
                    continue  # omega no limite = deriva lenta ou degrau, não mola
                dist = {nm: float(np.sqrt(np.mean((mola(tt, z, w_, u, aj["t0"]) - p) ** 2))) for nm, (z, w_, u) in molas_est.items()}
                perto = min(dist, key=dist.get)
                ajustes.append(dict(elemento=t["nome"], grandeza=g, a=mv["a"], b=mv["b"], de=round(mv["q0"]), para=round(mv["q1"]),
                                    zeta=aj["zeta"], omega=aj["omega"], impulso=aj["u0"], rms=aj["rms"],
                                    assenta_s=round(assenta(aj["zeta"], aj["omega"], aj["u0"]), 2),
                                    passa_do_ponto=round(max(0.0, float(p.max()) - 1), 3),
                                    perda_q30=round(perda_q30(aj["zeta"], aj["omega"]), 2),
                                    mais_parecida=perto, distancia_mola={k: round(v, 3) for k, v in dist.items()}))
    ajustes.sort(key=lambda x: x["a"])

    # câmera (quadro inteiro): só onde a correlação de fase confia
    cam = []
    G = Q.astype(np.float32).mean(-1)
    jan = cv2.createHanningWindow(G.shape[1:][::-1], cv2.CV_32F)
    for f in range(1, n):
        if any(f == c for c in secos):
            cam.append((0.0, 0.0, 0.0)); continue
        (dx, dy), r = cv2.phaseCorrelate(G[f - 1], G[f], jan)
        cam.append((dx * esc, dy * esc, r))
    cam = np.array(cam)
    pan = [(i + 1, float(math.hypot(dx, dy))) for i, (dx, dy, r) in enumerate(cam) if r > 0.25 and math.hypot(dx, dy) > 4]
    pico_pan = max(pan, key=lambda x: x[1]) if pan else None

    obt = obturador(a.video, fps, meta["w"], meta["h"], trilhas + pal_mexe, cam, cenas)

    # eventos para a batida: os da ficha (--eventos) ou os começos de movimento + cortes secos
    if a.eventos:
        ev = [int(x) for x in a.eventos.split(",") if x.strip()]
    else:
        ev = []
        for f in sorted(set(eventos_visuais(B["energy"], fps) + secos)):
            if not ev or f - ev[-1] > 2:
                ev.append(f)
    bat = batida(a.video, fps, [f / fps for f in ev], n / fps, (B.get("audio") or {}).get("bpm"))
    bat["eventos_de"] = "lista dada" if a.eventos else "começos de movimento e cortes (automático)"

    # paleta geral
    amostra = Q[::max(1, int(fps / 4))]
    mosaico = amostra.reshape(-1, amostra.shape[2], 3)
    paleta = burst.palette(np.ascontiguousarray(mosaico), k=8)

    folha(a.video, os.path.join(a.saida, "folha.jpg"), meta, n, secos)
    curvas_png(os.path.join(a.saida, "curvas.png"), princ + pal_mexe[:6], fps, n, ajustes)

    res = dict(video=os.path.abspath(a.video), largura=meta["w"], altura=meta["h"], fps=round(fps, 3), quadros=n,
               duracao_s=round(n / fps, 3), cortes_secos=secos, trocas_sem_corte=trocas, cenas=cenas,
               elementos=[dict(nome=t["nome"], quadros=[t["f"][0], t["f"][-1]], maior=t["onde"], anda_px=round(t["anda"]),
                               f=t["f"], x=[round(v, 1) for v in t["cx"]], y=[round(v, 1) for v in t["cy"]],
                               largura=[round(v, 1) for v in t["w"]], altura=[round(v, 1) for v in t["h"]]) for t in princ],
               legenda=dict(res_pal, usada=legenda, decidiu="sozinho" if a.legenda == "auto" else "pedido"),
               palavras=[dict(nome=p["nome"], quadros=[p["f"][0], p["f"][-1]], caixa=[round(x) for x in np.median(np.array(p["caixa"]), 0)],
                              altura=p["altura"], cor=p["cor"], polaridade=p["polaridade"], entra_q=p["entra_q"], sai_q=p["sai_q"],
                              cresce=p["cresce"], mexe=any(t["nome"] == p["nome"] for t in pal_mexe)) for p in pal] if legenda else [],
               molas=ajustes, molas_do_estilo={k: dict(zeta=v[0], omega=v[1], assenta_s=round(assenta(*v), 2)) for k, v in molas_est.items()},
               origem_molas=origem_molas,
               camera=dict(pico_px_por_quadro=round(pico_pan[1], 1) if pico_pan else 0, pico_quadro=pico_pan[0] if pico_pan else None,
                           quadros_com_pan=len(pan)),
               obturador=dict(obt, estilo=round(fps / 120, 2)), batida=bat, eventos_quadros=ev, paleta=paleta,
               tempo_s=round(time.time() - T0, 1))
    json.dump(res, open(os.path.join(a.saida, "raiox.json"), "w"), indent=1, ensure_ascii=False)
    open(os.path.join(a.saida, "RAIOX.md"), "w").write(texto(res, os.path.basename(a.video)))
    print(json.dumps({k: res[k] for k in ("quadros", "fps", "cortes_secos", "trocas_sem_corte", "tempo_s")}, ensure_ascii=False))


def texto(r, nome):
    fps = r["fps"]
    L = [f"# Raio-x: {nome}", ""]
    ns = len(r["cortes_secos"])
    obt = r["obturador"]
    bat = r["batida"]
    pref = {}
    for m in r["molas"]:
        pref[m["mais_parecida"]] = pref.get(m["mais_parecida"], 0) + 1
    molas_txt = ", ".join(f"{v} {k}" for k, v in sorted(pref.items(), key=lambda x: -x[1])) or "nenhuma medida"
    L += [f"**Em uma frase.** {br(r['duracao_s'])} s a {fps:g} quadros por segundo ({r['largura']}x{r['altura']}), "
          f"{'um plano só' if ns == 0 else f'{ns + 1} cenas separadas por {ns} corte(s) seco(s)'}"
          f"{f' e {len(r['trocas_sem_corte'])} troca(s) sem corte (morph ou troca no lugar)' if r['trocas_sem_corte'] else ''}; "
          f"molas mais parecidas com: {molas_txt}; "
          f"obturador {'de ' + br(obt['obturador']) + ' quadro' if obt.get('obturador') is not None else 'sem medida'}; "
          f"música: {bat.get('leitura', 'sem áudio')}"
          + (f"; texto palavra a palavra ({len(r['palavras'])} palavras)." if r.get("palavras") else "."), ""]
    L += ["## O básico", "",
          f"- Tamanho {r['largura']}x{r['altura']}, {fps:g} qps, {r['quadros']} quadros, {br(r['duracao_s'])} s.",
          f"- Medido em {br(r['tempo_s'], 0)} s. Arquivos: `raiox.json` (tudo em número), `folha.jpg`, `curvas.png`, `analise/`.", ""]
    L += ["## Cortes e cenas", "",
          "Corte seco é troca de plano de verdade (nada do quadro anterior continua). Troca sem corte é uma mudança grande",
          "de imagem em que a câmera continua: quase sempre um morph, um crossfade ou um elemento grande entrando.", "",
          "| cena | quadros | duração | trocas sem corte dentro | cores |", "|---|---|---|---|---|"]
    for c in r["cenas"]:
        L.append(f"| {c['cena']} | f{c['a']}-f{c['b']} | {br(c['dur_s'])} s | {', '.join('f' + str(t) for t in c['trocas_sem_corte']) or 'nenhuma'} | {' '.join(c['paleta'][:4])} |")
    L += ["", "## Elementos principais", "",
          "Manchas que diferem do fundo da cena, seguidas quadro a quadro; aqui só as que mais andam ou mudam de tamanho.",
          "Posição e tamanho em px do vídeo original, no quadro em que a mancha fica maior. Curvas em `curvas.png`.", "",
          "| elemento | quadros | maior em | centro | tamanho | quanto anda |", "|---|---|---|---|---|---|"]
    for e in r["elementos"]:
        m = e["maior"]
        L.append(f"| {e['nome']} | f{e['quadros'][0]}-f{e['quadros'][1]} | f{m['f']} | {m['x']}, {m['y']} | {m['w']}x{m['h']} | {e['anda_px']} px |")
    if not r["elementos"]:
        L.append("| nenhum | | | | | |")
    if r.get("palavras"):
        L += ["", "## Texto palavra a palavra (trilha por palavra)", "",
              f"{r['legenda']['palavras']} palavras nascendo em {r['legenda']['momentos']} momentos diferentes: o texto entra palavra a "
              f"palavra (legenda cinética, ou interface com muito texto; decidido {r['legenda']['decidiu']}). Cada palavra foi seguida",
              "pela tinta (traço fino de letra), não como mancha.",
              "Caixa = a caixa da tinta assentada, em px do original. Entra/sai = quadros até o contraste chegar a 90 % do",
              "patamar (esmaecimento) e depois dele. Cresce = largura no 1º quadro sobre a assentada (abaixo de 1 = nasce pequena).",
              "Ruído de cena (textura, cabelo, placa) também passa: confira na folha. Para clonar, meça cada palavra com",
              "`scripts/trilha_palavra.py` e um elementos.json com região e teste de cor.", "",
              "| palavra | quadros | caixa (x0, y0, x1, y1) | altura | tinta | cor | entra | sai | cresce | mexe |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for p in r["palavras"][:60]:
            L.append(f"| {p['nome']} | f{p['quadros'][0]}-f{p['quadros'][1]} | {', '.join(map(str, p['caixa']))} | {br(p['altura'], 0)} px | "
                     f"{p['polaridade']} | rgb({', '.join(map(str, p['cor']))}) | {p['entra_q']} q | {p['sai_q']} q | {br(p['cresce'])} | "
                     f"{'sim' if p['mexe'] else 'não'} |")
        if len(r["palavras"]) > 60:
            L.append(f"| ... mais {len(r['palavras']) - 60} em `raiox.json` | | | | | | | | | |")
    me = r["molas_do_estilo"]
    L += ["", "## Molas", "",
          "Cada linha é um movimento (uma grandeza saindo de um repouso e assentando noutro), ajustado ao oscilador",
          "amortecido do `estilo.js`. Zeta abaixo de 1 passa do ponto e volta; acima de 1 chega sem passar. Assenta =",
          "tempo até ficar a 2 % do fim. Perda = quanto do que falta sobra a cada 1/30 s no fim do caminho.",
          f"Molas do estilo: suave (zeta {br(me['suave']['zeta'])}, assenta {br(me['suave']['assenta_s'])} s), firme "
          f"(zeta {br(me['firme']['zeta'])}, {br(me['firme']['assenta_s'])} s), elástica (zeta {br(me['elastica']['zeta'])}, "
          f"{br(me['elastica']['assenta_s'])} s, passa 8 %).", "",
          "| elemento | grandeza | quadros | de → para (px) | zeta | omega | assenta | passa do ponto | perda/q30 | mais parecida | erro do ajuste |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for m in r["molas"]:
        L.append(f"| {m['elemento']} | {m['grandeza']} | f{m['a']}-f{m['b']} | {m['de']} → {m['para']} | {br(m['zeta'])} | {br(m['omega'], 1)} | "
                 f"{br(m['assenta_s'])} s | {br(100 * m['passa_do_ponto'], 0)} % | {br(m['perda_q30'])} | {m['mais_parecida']} "
                 f"({br(m['distancia_mola'][m['mais_parecida']], 3)}) | {br(m['rms'], 3)} |")
    if not r["molas"]:
        L.append("| nenhum movimento limpo o bastante para ajustar | | | | | | | | | | |")
    L += ["", "## Motion blur", ""]
    if obt.get("obturador") is not None:
        L.append(f"- Obturador estimado: **{br(obt['obturador'])} quadro** (faixa {br(obt['faixa'][0])} a {br(obt['faixa'][1])}, "
                 f"{obt['amostras']} amostras: peça em movimento contra ela mesma parada). Exposição de {br(1000 * obt['obturador'] / fps, 1)} ms.")
    else:
        L.append(f"- Sem amostras boas de borda em movimento ({obt.get('amostras', 0)}). Use o do estilo.")
    L.append(f"- O estilo usa 1/120 s, que a {fps:g} qps dá {br(obt['estilo'])} quadro. Render com subquadros (round_mb.sh), nunca blur de CSS.")
    cam = r["camera"]
    if cam["pico_quadro"]:
        L.append(f"- O quadro inteiro anda (pan) em {cam['quadros_com_pan']} quadros; pico de {br(cam['pico_px_por_quadro'], 0)} px por quadro em f{cam['pico_quadro']}.")
    L += ["", "## Música e batida", ""]
    if bat.get("classe") in (None, "silent"):
        L.append("- Sem áudio (ou silêncio).")
    else:
        L.append(f"- Áudio: {bat['classe']}, {br(bat['bpm'], 1) if bat.get('bpm') else '?'} BPM (força {br(bat.get('forca') or 0)}), "
                 f"{br(bat.get('onsets_por_s') or 0, 1)} golpes por segundo.")
        if "na_colcheia" in bat:
            x = bat["na_colcheia"]
            L.append(f"- Na colcheia ({x['colcheia_ms']} ms): {x['acertos']} de {bat['eventos']} eventos (o acaso daria {br(x['acaso'], 1)}; p = {br(x['p'], 3)}).")
        if "nos_onsets" in bat:
            x = bat["nos_onsets"]
            L.append(f"- Nos golpes da trilha: {x['acertos']} de {bat['eventos']} (acaso {br(x['acaso'], 1)}; p = {br(x['p'], 3)}).")
        L.append(f"- Eventos testados: {bat.get('eventos_de')} ({', '.join('f' + str(x) for x in r['eventos_quadros'][:30])}).")
        L.append(f"- **Leitura: {bat['leitura']}.** Conferir no ouvido; com os eventos grandes da ficha (`--eventos`) o teste fica mais justo.")
    L += ["", "## Paleta", "", " ".join(f"`{p['hex']}` {br(100 * p['share'], 0)} %" for p in r["paleta"]), "",
          "## Folha de quadros", "", "`folha.jpg`: 24 quadros espalhados pelo vídeo, mais os dois lados de cada corte seco.", "",
          "## O que conferir à mão", "",
          "- O raio-x mede manchas, não sabe o que elas são: confira na folha qual elemento é qual.",
          "- Molas saem da caixa da mancha. Desfoque, brilho e sombra engordam a caixa; meça a peça com `medir.py` antes de",
          "  copiar um número para a composição.",
          "- O obturador precisa de um quadro parado da mesma peça perto do movimento; peça que muda de forma enquanto anda engana.",
          "- Batida: o BPM pode sair dobrado ou pela metade; o que importa é a leitura (segue ou não) e conferir no ouvido."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
