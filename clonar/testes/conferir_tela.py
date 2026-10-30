#!/usr/bin/env python3
"""conferir_tela.py [pasta_saida]: confere o extrair_tela.py em dois vídeos sintéticos com resposta conhecida (menos de
um minuto): um "reel demonstrativo" com fundo claro parado, um painel vizinho escuro com miniatura que troca e um cartão
de cantos arredondados (raio 30) com conteúdo que corta a cada 5 quadros.
  parado:  cartão em x 300-659, y 200-839 (360x640): quad a menos de 1 px, dado como parado, troca em f20;
  andando: o mesmo cartão andando 1 px por quadro para a direita: dado em movimento, canto do último quadro a < 1,5 px.
Sai com código 1 se algo não bater."""
import json, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import cv2

KIT = Path(__file__).resolve().parent.parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="tela-"))
OUT.mkdir(parents=True, exist_ok=True)
W, H, N = 720, 1280, 40
falhas = []


def video(nome, anda):
    rng = np.random.default_rng(1)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30",
                          "-i", "-", "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(OUT / nome)], stdin=subprocess.PIPE)
    tex = [cv2.normalize(cv2.GaussianBlur(rng.integers(0, 255, (640, 360, 3)).astype(np.uint8), (0, 0), 6), None, 0, 255, cv2.NORM_MINMAX)
           for _ in range(N // 5)]
    for f in range(N):
        im = np.full((H, W, 3), 246, np.uint8)
        im[300:700, 60:285] = 70  # painel vizinho, a 15 px do cartão (borda do vizinho cruzando a do cartão: ver extrair_tela.py)
        im[360:460, 90:300] = 60 + 20 * ((f // 5) % 2)  # miniatura que troca
        x0 = 300 + (f if anda else 0)
        c = tex[f // 5]  # conteúdo que corta a cada 5 quadros
        m = np.zeros((640, 360), np.uint8); cv2.rectangle(m, (30, 0), (329, 639), 255, -1); cv2.rectangle(m, (0, 30), (359, 609), 255, -1)
        for cx, cy in ((30, 30), (329, 30), (329, 609), (30, 609)):
            cv2.circle(m, (cx, cy), 30, 255, -1)
        reg = im[200:840, x0:x0 + 360]; reg[m > 0] = c[m > 0]
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()


def roda(nome):
    r = subprocess.run([sys.executable, str(KIT / "scripts" / "extrair_tela.py"), str(OUT / nome), str(OUT / f"dentro-{nome}"),
                        "--json", str(OUT / f"{nome}.json"), "--sem-audio"], capture_output=True, text=True)
    if r.returncode:
        falhas.append(f"{nome}: extrair_tela falhou: {r.stderr[-300:]}"); return None
    return json.load(open(OUT / f"{nome}.json"))


video("parado.mp4", False); video("andando.mp4", True)
a = roda("parado.mp4")
if a:
    erro = np.abs(np.array(a["quad"]) - np.array([[299.5, 199.5], [659.5, 199.5], [659.5, 839.5], [299.5, 839.5]])).max()
    if erro > 1.0: falhas.append(f"parado: quad errado em {erro:.2f} px ({a['quad']})")
    if not a["parado"]: falhas.append("parado: dado como em movimento")
    if 20 not in a["cortes"]: falhas.append(f"parado: troca em f20 não achada ({a['cortes']})")
    if a["tamanho"] != [360, 640]: falhas.append(f"parado: tamanho {a['tamanho']} (esperado 360x640)")
    print(f"parado: quad a {erro:.2f} px, raio {a['raio_canto_px']} px, trocas {a['cortes']}")
b = roda("andando.mp4")
if b:
    if b["parado"]: falhas.append("andando: dado como parado")
    q = np.array(b["quads"][-1]) if b.get("quads") else None
    alvo = np.array([[338.5, 199.5], [698.5, 199.5], [698.5, 839.5], [338.5, 839.5]])
    erro = np.abs(q - alvo).max() if q is not None else 99
    if erro > 1.5: falhas.append(f"andando: canto do último quadro errado em {erro:.2f} px")
    print(f"andando: último quadro a {erro:.2f} px")
print("OK" if not falhas else "\n".join(falhas))
sys.exit(1 if falhas else 0)
