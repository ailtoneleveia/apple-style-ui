#!/usr/bin/env python3
"""extrair_tela.py: tira o vídeo de dentro de uma referência demonstrativa (a tela, o cartão "Final output", o celular
filmado) e devolve esse vídeo endireitado, no tamanho nativo, com os trechos em que ele some ou troca de conteúdo.

  extrair_tela.py <video> <saida.mp4> [--json tela.json] [--quad "x,y x,y x,y x,y"] [--a A] [--b B]
                  [--tamanho LxA] [--sem-audio] [--crf 10]

1. Acha o cartão sozinho (ou usa --quad, cantos em sentido horário a partir do alto à esquerda, px do vídeo): é a
   maior região que muda ao longo do vídeo. O desvio de cada pixel no tempo separa o cartão do que é fixo; o miolo
   pela distância à borda separa o cartão de um painel vizinho que também muda (o "Storyboard"); cada lado vira uma
   reta ajustada na borda que persiste no tempo (mediana do gradiente), então canto arredondado e leve
   perspectiva não atrapalham.
2. Segue o cartão quadro a quadro: as 4 bordas são achadas de novo perto de onde devem estar (posição + velocidade do
   quadro anterior; degrau de luz na normal de cada lado, reta por RANSAC) e os 4 cantos dão a homografia do quadro; se ele se mexe, gira ou
   inclina, cada quadro tem a sua. (ECC na faixa da borda, o caminho do registra_cam.py, deriva aqui: o conteúdo que
   anda dentro do cartão puxa o ajuste.) Se 95 % dos quadros com as 4 bordas firmes ficam a menos de 2 px do quad
   achado no tempo, o cartão é dado como parado e usa um quad só (o recorte não treme por ruído).
3. Recorta e endireita cada quadro (warpPerspective, Lanczos) no tamanho nativo: a média dos lados opostos em px do
   vídeo (o que o vídeo de dentro tinha de resolução, de fato, nesta gravação). Áudio copiado do original.
4. Mede o raio do canto (na diagonal da fração de quadros diferentes do fundo) e marca os trechos:
   "fora": nenhuma borda reta em 3 ou 4 lados (o cartão não está lá); com 1 ou 2, conta como "borda fraca";
   "corte": o conteúdo de dentro troca de um quadro para o outro (diferença média alta no miolo).
Saída JSON padrão; com --json grava os cantos por quadro, o tamanho, o raio e os trechos.
"""
import argparse, json, os, subprocess, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import LU, falha, ok, quadros, tamanho  # noqa: E402

PASSO_AMOSTRA = 10   # quadros entre amostras para achar o cartão
ESCALA = 0.5         # o rastreio roda em meia resolução
cheio = lambda q: (np.asarray(q) + 0.5) / ESCALA - 0.5   # noqa: E731  meia -> cheia (centro de pixel)
meio = lambda q: (np.asarray(q) + 0.5) * ESCALA - 0.5    # noqa: E731  cheia -> meia


def pico(p):
    """posição do máximo com meio-pixel de parábola"""
    i = int(np.argmax(p))
    if 0 < i < len(p) - 1:
        d = p[i - 1] - 2 * p[i] + p[i + 1]
        if d < 0:
            return i + 0.5 * (p[i - 1] - p[i + 1]) / d
    return float(i)


def fps_de(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate",
                        "-of", "csv=p=0", video], capture_output=True, text=True).stdout.strip()
    n, d = (r.split("/") + ["1"])[:2]
    return float(n) / float(d or 1), r


def gradiente(L):
    gx = cv2.Sobel(L, cv2.CV_32F, 1, 0, ksize=3); gy = cv2.Sobel(L, cv2.CV_32F, 0, 1, ksize=3)
    return cv2.magnitude(gx, gy)


def reta(pts, tol=1.5, devolve_frac=False):
    """reta por RANSAC (um selo ou sombra encostado no lado não entorta a borda) e ajuste fino nos que concordam"""
    pts = pts.astype(np.float32); rng = np.random.default_rng(0); melhor = None
    for _ in range(300):
        a, b = pts[rng.choice(len(pts), 2, replace=False)]
        d = b - a; n = np.hypot(*d)
        if n < 1e-6:
            continue
        dist = np.abs((pts[:, 0] - a[0]) * d[1] - (pts[:, 1] - a[1]) * d[0]) / n
        dentro = dist < tol
        if melhor is None or dentro.sum() > melhor.sum():
            melhor = dentro
    vx, vy, x0, y0 = cv2.fitLine(pts[melhor], cv2.DIST_L2, 0, 0.01, 0.01).ravel()
    r = (np.array([vx, vy]), np.array([x0, y0]))
    return (r, float(melhor.mean())) if devolve_frac else r


def cruza(r1, r2):
    (d1, p1), (d2, p2) = r1, r2
    A = np.array([d1, -d2]).T
    t = np.linalg.solve(A, p2 - p1)
    return p1 + t[0] * d1


def acha_quad(amostras, w, h):
    """cantos (4x2, px de meia resolução) do maior retângulo que muda; e a fração 'diferente do fundo' por pixel"""
    Ls = np.array([q.astype(np.float32) @ LU for q in amostras])
    sd = Ls.std(0)
    v = np.clip(sd[sd > 6], 0, 255).astype(np.uint8).reshape(-1, 1)
    t_otsu = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[0] if v.size else 6
    for corte in (t_otsu, 0.5 * t_otsu):  # Otsu separa o miolo do painel vizinho; cartão que anda deixa a faixa da
        m = (sd > max(6.0, corte)).astype(np.uint8)  # passada no topo do Otsu, e aí meio Otsu acha o miolo
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        ff = m.copy(); cv2.floodFill(ff, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 1); m |= 1 - ff  # tapa os furos
        dt = cv2.distanceTransform(m, cv2.DIST_L2, 5)
        r = float(dt.max())
        if r >= 0.08 * min(w, h):
            break
    if r < 10:
        falha("não achei nenhuma região grande que muda no vídeo (o cartão está parado o tempo todo?): use --quad", 2)
    n, lab = cv2.connectedComponents((dt > 0.6 * r).astype(np.uint8))
    yx = np.unravel_index(np.argmax(dt), dt.shape)
    nucleo = (lab == lab[yx]).astype(np.uint8)
    t = int(0.6 * r)  # o miolo é o cartão encolhido t px de cada lado (sem o painel vizinho, mais estreito)
    x, y, bw, bh = cv2.boundingRect(nucleo)
    x, y, bw, bh = max(0, x - t), max(0, y - t), min(w - x + t, bw + 2 * t), min(h - y + t, bh + 2 * t)
    # Um lado com pouca mudança perto da borda (fundo escuro fixo, marca d'água) faz o miolo parar antes: cada lado
    # anda para fora enquanto o desvio no tempo ainda é de cartão (cai a menos de 40 % do de dentro = saiu do cartão)
    cols = slice(x + int(0.15 * bw), x + int(0.85 * bw)); rows = slice(y + int(0.15 * bh), y + int(0.85 * bh))
    liso = lambda p: np.convolve(p, np.ones(5) / 5, mode="same")  # noqa: E731
    sd_y, sd_x = liso(sd[:, cols].mean(1)), liso(sd[rows, :].mean(0))
    def borda(perfil, est, passo):
        est = int(np.clip(est - passo * 6, 0, len(perfil) - 1))
        ref = float(np.median(perfil[min(est, est - passo * 30):max(est, est - passo * 30) + 1]))
        i = est
        while 0 < i < len(perfil) - 1 and perfil[i] > 0.4 * ref:
            i += passo
        return i
    y0, x1 = borda(sd_y, y, -1), borda(sd_x, x + bw - 1, 1)
    y1, x0 = borda(sd_y, y + bh - 1, 1), borda(sd_x, x, -1)
    # as retas saem da borda do desvio no tempo (selo ou sombra parados encostados no lado não contam: ali o desvio é 0
    # dos dois lados); G, a borda que persiste no quadro, fica para o rastreio
    Gsd = gradiente(sd)
    G = np.median(np.array([gradiente(L) for L in Ls[:: max(1, len(Ls) // 40)]]), 0)
    x, y, bw, bh = x0, y0, x1 - x0 + 1, y1 - y0 + 1
    lados = []
    busca = max(4, int(0.015 * max(bw, bh)))
    for lado in ("topo", "dir", "base", "esq"):
        pts = []
        horiz = lado in ("topo", "base")
        comp = bw if horiz else bh
        for i in range(int(0.15 * comp), int(0.85 * comp)):  # longe dos cantos arredondados
            if horiz:
                cx = x + i; c0 = y if lado == "topo" else y + bh - 1
                lo, hi = max(0, c0 - busca), min(h - 1, c0 + busca)
                pts.append((cx, lo + pico(Gsd[lo:hi + 1, cx])))
            else:
                cy = y + i; c0 = x if lado == "esq" else x + bw - 1
                lo, hi = max(0, c0 - busca), min(w - 1, c0 + busca)
                pts.append((lo + pico(Gsd[cy, lo:hi + 1]), cy))
        lados.append(reta(np.array(pts)))
    topo, dir_, base, esq = lados
    quad = np.array([cruza(topo, esq), cruza(topo, dir_), cruza(base, dir_), cruza(base, esq)], np.float32)
    return quad, sd.astype(np.float32), G


BUSCA_RASTREIO = 6   # px (meia resolução) que cada borda pode andar de um quadro para o outro


def lados_no_quadro(L, quad, busca, n=60):
    """acha de novo os 4 lados perto do quad: em n pontos de cada lado (15 a 85 %, longe dos cantos), o maior degrau
    de luz na normal; reta por RANSAC. Devolve (quad novo, quantos lados falharam: poucos pontos concordam ou degrau
    fraco)"""
    from scipy.ndimage import map_coordinates
    retas, ruins = [], 0
    ks = np.arange(-busca, busca + 1, dtype=np.float32)
    for i in range(4):
        p0, p1 = quad[i], quad[(i + 1) % 4]
        d = (p1 - p0) / max(1e-6, np.linalg.norm(p1 - p0)); nrm = np.array([-d[1], d[0]], np.float32)
        ss = np.linspace(0.15, 0.85, n, dtype=np.float32)
        base = p0[None] + ss[:, None] * (p1 - p0)[None]
        pts = base[:, None, :] + ks[None, :, None] * nrm[None, None, :]
        perf = map_coordinates(L, [pts[..., 1].ravel(), pts[..., 0].ravel()], order=1, mode="nearest").reshape(n, -1)
        deg = np.abs(np.diff(perf, axis=1))
        off, forca = np.zeros(n), np.zeros(n)
        for j, r in enumerate(deg):  # o degrau mais perto de onde a borda estava (não o mais forte: o conteúdo de
            lim = max(4.0, 0.3 * r.max())  # dentro do cartão também tem bordas retas e puxaria o lado)
            mx = [k for k in range(len(r)) if r[k] >= lim and (k == 0 or r[k] >= r[k - 1]) and (k == len(r) - 1 or r[k] >= r[k + 1])]
            if mx:
                k = min(mx, key=lambda k: abs(k + 0.5 - busca))
                lo, hi = max(0, k - 1), min(len(r), k + 2)
                off[j] = lo + pico(r[lo:hi]) + 0.5 - busca; forca[j] = r[k]
        cand = base + off[:, None] * nrm[None]
        ok_pts = cand[forca > 4]
        if len(ok_pts) < n // 2:
            retas.append(None); ruins += 1; continue
        r, frac = reta(ok_pts, devolve_frac=True)
        if frac < 0.5:
            retas.append(None); ruins += 1; continue
        retas.append(r)
    if ruins:
        return quad, ruins
    topo, dir_, base_, esq = retas
    return np.array([cruza(topo, esq), cruza(topo, dir_), cruza(base_, dir_), cruza(base_, esq)], np.float32), 0


def raio_do_canto(sd, quad, Wn, Hn):
    """raio do canto pela diagonal do desvio no tempo (fora do arco não muda nada, nem a sombra): o arco cruza a
    diagonal a r(raiz2 - 1) do canto"""
    Hm = cv2.getPerspectiveTransform(quad, np.float32([[0, 0], [Wn, 0], [Wn, Hn], [0, Hn]]))
    f = cv2.warpPerspective(sd, Hm, (Wn, Hn), flags=cv2.INTER_LINEAR)
    f = f / max(1e-6, float(np.median(f[Hn // 4:3 * Hn // 4, Wn // 4:3 * Wn // 4])))
    rs = []
    for cx, cy, sx, sy in ((0, 0, 1, 1), (Wn - 1, 0, -1, 1), (Wn - 1, Hn - 1, -1, -1), (0, Hn - 1, 1, -1)):
        d = next((k for k in range(min(Wn, Hn) // 3) if f[cy + sy * k, cx + sx * k] > 0.5), None)
        if d is not None:
            rs.append(d * np.sqrt(2) / (np.sqrt(2) - 1))
    return float(np.median(rs)) if rs else 0.0


def trechos(marca):
    out, ini = [], None
    for i, v in enumerate(list(marca) + [False]):
        if v and ini is None:
            ini = i
        if not v and ini is not None:
            out.append([ini, i - 1]); ini = None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("saida")
    ap.add_argument("--json"); ap.add_argument("--quad"); ap.add_argument("--a", type=int, default=0)
    ap.add_argument("--b", type=int); ap.add_argument("--tamanho"); ap.add_argument("--sem-audio", action="store_true")
    ap.add_argument("--crf", type=int, default=10)
    ap.add_argument("--corte", type=float, default=0.06, help="diferença média (0-1) no miolo que conta como troca")
    a = ap.parse_args()
    if not os.path.exists(a.video):
        falha(f"não encontrado: {a.video}", 1)
    W, H = tamanho(a.video)
    w, h = int(W * ESCALA) // 2 * 2, int(H * ESCALA) // 2 * 2
    fps, fps_txt = fps_de(a.video)

    amostras = [q for f, q in quadros(a.video, a.a, a.b, largura=w) if (f - a.a) % PASSO_AMOSTRA == 0]
    if len(amostras) < 3:
        falha("vídeo curto demais para achar o cartão (menos de 3 amostras)", 1)
    quad_auto, sd, G = acha_quad(amostras, w, h)
    if a.quad:
        try:
            quad = meio(np.float32([[float(v) for v in p.split(",")] for p in a.quad.split()]).reshape(4, 2)).astype(np.float32)
        except ValueError:
            falha("--quad: quatro pares x,y separados por espaço", 1)
    else:
        quad = quad_auto
    lado = lambda q, i, j: float(np.linalg.norm(q[i] - q[j]))  # noqa: E731
    if a.tamanho:
        Wn, Hn = map(int, a.tamanho.lower().split("x"))
    else:
        Wn = int(round((lado(quad, 0, 1) + lado(quad, 3, 2)) / 2 / ESCALA / 2)) * 2
        Hn = int(round((lado(quad, 0, 3) + lado(quad, 1, 2)) / 2 / ESCALA / 2)) * 2
    raio = raio_do_canto(sd, quad, Wn, Hn) if not a.quad else None

    # rastreio: em cada quadro, as 4 bordas são achadas de novo perto das do quadro anterior (degrau de luz na normal
    # de cada lado + RANSAC) e os cantos dão a homografia do quadro. ECC na faixa da borda (o caminho do
    # registra_cam.py) foi tentado e deriva: o conteúdo que anda dentro do cartão puxa o ajuste (24 px neste reel).
    atual = quad.copy()
    por_q, falhos, difs = [], [], []
    ant = None
    for f, q in quadros(a.video, a.a, a.b, largura=w):
        L = cv2.GaussianBlur(q.astype(np.float32) @ LU, (0, 0), 1.0)
        # no 1º quadro a borda pode estar longe do quad achado no tempo (cartão que anda: o desvio pega a área toda que
        # ele percorre); procura mais longe e depois só perto
        busca = BUSCA_RASTREIO if por_q else max(BUSCA_RASTREIO, int(0.12 * min(np.ptp(quad[:, 0]), np.ptp(quad[:, 1]))))
        # procura perto de onde o cartão deve estar (posição + velocidade do quadro anterior): sem isso, um lado que passa
        # por uma borda parada do vizinho (o painel ao lado) fica preso nela e o cartão "encolhe"
        # shortcut: se a borda do cartão passa exatamente por cima de uma borda parada (menos de 1 px de meia resolução),
        # o degrau parado ainda pode capturar o lado; se aparecer, rastrear em resolução cheia perto da borda
        prev = atual + (atual - por_q[-2]) if len(por_q) >= 2 and falhos[-1] == 0 else atual
        novo_q, ruins = lados_no_quadro(L, prev.astype(np.float32), busca)
        if ruins == 0:
            atual = novo_q
        por_q.append(atual.copy()); falhos.append(ruins)
        Hm = cv2.getPerspectiveTransform(atual, np.float32([[0, 0], [96, 0], [96, 170], [0, 170]]))
        mi = cv2.warpPerspective(L, Hm, (96, 170))[20:150, 10:86]
        difs.append(0.0 if ant is None else float(np.abs(mi - ant).mean() / 255)); ant = mi
    por_q = np.array(por_q); falhos = np.array(falhos)
    bons = falhos == 0
    dv = np.abs(por_q - quad).max((1, 2)) / ESCALA
    desvio = float(np.percentile(dv[bons], 95)) if bons.any() else 0.0
    parado = desvio < 2.0  # a borda achada num quadro só, em meia resolução, oscila até ~2 px (conteúdo claro, selo)
    if parado:
        por_q[:] = quad  # cartão parado: um quad só (o da borda no tempo, mais preciso), o recorte não treme
    fora = falhos >= 3  # nenhuma borda reta: o cartão não está lá (com 1 ou 2, é borda sem contraste naquele quadro)
    cortes = [i + a.a for i, d in enumerate(difs) if d > a.corte]

    # recorte e endireitamento em resolução cheia
    os.makedirs(os.path.dirname(os.path.abspath(a.saida)), exist_ok=True)
    dst = np.float32([[-.5, -.5], [Wn - .5, -.5], [Wn - .5, Hn - .5], [-.5, Hn - .5]])  # o quad é a borda da tinta
    b_real = a.a + len(por_q) - 1
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{Wn}x{Hn}", "-r", fps_txt,
           "-i", "-"]
    if not a.sem_audio:
        cmd += ["-ss", f"{a.a / fps:.6f}", "-t", f"{len(por_q) / fps:.6f}", "-i", a.video, "-map", "0:v", "-map", "1:a?",
                "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-c:v", "libx264", "-crf", str(a.crf), "-preset", "slow", "-pix_fmt", "yuv420p", "-refs", "4",
            "-level:v", "5.1", "-movflags", "+faststart", a.saida]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f, q in quadros(a.video, a.a, b_real):
        Hm = cv2.getPerspectiveTransform(cheio(por_q[f - a.a]).astype(np.float32), dst)
        p.stdin.write(cv2.warpPerspective(q, Hm, (Wn, Hn), flags=cv2.INTER_LANCZOS4,
                                          borderMode=cv2.BORDER_REPLICATE).tobytes())
    p.stdin.close()
    if p.wait():
        falha("o ffmpeg falhou ao gravar a saída", 2)

    info = dict(video=a.video, quadros_borda_fraca=int((falhos > 0).sum()), saida=a.saida, de=a.a, ate=b_real, fps=fps, tamanho=[Wn, Hn],
                quad=cheio(quad).round(2).tolist(), parado=parado, desvio_max_px=round(desvio, 2),
                raio_canto_px=None if raio is None else round(raio, 1),
                fora=[[x + a.a, y + a.a] for x, y in trechos(fora)], cortes=cortes,
                )
    if a.json:
        json.dump(dict(info, quads=None if parado else cheio(por_q).round(2).tolist(),
                       diferenca_miolo=[round(d, 4) for d in difs]), open(a.json, "w"), ensure_ascii=False, indent=1)
    ok(f"vídeo de dentro {Wn}x{Hn} ({b_real - a.a + 1} quadros, cartão {'parado' if parado else 'em movimento'}, "
       f"desvio máx {desvio:.2f} px, raio do canto {info['raio_canto_px']} px); {len(info['fora'])} trecho(s) sem o "
       f"cartão, {len(cortes)} troca(s) de conteúdo", comando="python3 clonar.py raiox " + a.saida,
       motivo="medir o vídeo de dentro como um original qualquer", **info)


if __name__ == "__main__":
    main()
