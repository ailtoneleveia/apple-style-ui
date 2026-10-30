#!/usr/bin/env python3
"""conferir_pecas.py [pasta_saida]: confere as peças que o 4º clone trouxe para o kit, num vídeo sintético com resposta
conhecida (fundo com textura e câmera andando 3 px por quadro, uma palavra branca entrando por esmaecimento e
andando 4 px por quadro, e uma legenda de 8 palavras entrando uma a uma). Roda em menos de um minuto.

  trilha_palavra.py   caixa medida da palavra contra a verdade; palavras automáticas e o teste de legenda
  placa.py            placa larga com reprojeção baixa; placa curta (--janela) com alfa
  registra_cam.py     câmera com erro de 6 px (f25-35) corrigida contra a placa
  compara_mascara.py  original contra ele mesmo = 0; clone deslocado > 0; sem camada > clone
  placa_video.py      a palavra some da placa (o buraco é preenchido pelo entorno)
  aparicao.py         palavra parada entrando por esmaecimento em 4 quadros: a opacidade medida bate
  recortes.py         recorte do original sem declaração reprova; tipo interface reprova; declarado aprova; clone borrado acusado
  modelo/index.html   amostra() presa ao trecho medido (o elemento não nasce meio transparente), no node
Sai com código 1 se algo não bater."""
import json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import cv2

KIT = Path(__file__).resolve().parent.parent
SCR = KIT / "scripts"
sys.path.insert(0, str(SCR))
import trilha_palavra as tp  # noqa: E402

PY = sys.executable
W, H, N = 640, 360, 40
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="pecas-"))
OUT.mkdir(parents=True, exist_ok=True)
falhas = []


def confere(ok, o_que, detalhe=""):
    print(f"{'ok   ' if ok else 'FALHA'} {o_que}{': ' + detalhe if detalhe else ''}")
    if not ok:
        falhas.append(o_que)


def grava(caminho, quadros):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
                          "-c:v", "libx264", "-crf", "4", "-pix_fmt", "yuv444p", str(caminho)], stdin=subprocess.PIPE)
    for q in quadros:
        p.stdin.write(np.ascontiguousarray(q).tobytes())
    p.stdin.close(); p.wait()


def roda(*args):
    r = subprocess.run([PY, *map(str, args)], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{Path(str(args[0])).name} falhou: {r.stderr.strip()[-300:]}")
    return json.loads(r.stdout)


# ------------------------------------------------------------------ vídeos sintéticos
rng = np.random.default_rng(3)
mundo = cv2.GaussianBlur(rng.uniform(0, 255, (H + 20, W + 3 * N + 20, 3)).astype(np.float32), (0, 0), 6)
mundo = (40 + (mundo - mundo.min()) / (mundo.max() - mundo.min()) * 90).astype(np.uint8)  # luma 40-130: sem branco no fundo
CAM = [dict(f=f, s=1.0, tx=-3.0 * f - 10, ty=-10.0) for f in range(N)]  # tela = mundo + t
PAL = dict(de=8, ate=33, x=(lambda f: 120 + 4 * (f - 8)), y=200)


def fundo(f):
    return mundo[10:10 + H, 10 + 3 * f:10 + 3 * f + W].copy()


def com_palavra(f, desvio=0):
    q = fundo(f)
    if PAL["de"] <= f <= PAL["ate"]:
        cam = np.zeros_like(q); cv2.putText(cam, "PALAVRA", (PAL["x"](f) + desvio, PAL["y"]), cv2.FONT_HERSHEY_DUPLEX, 1.6, (255, 255, 255), 4, cv2.LINE_AA)
        a = min(1.0, (f - PAL["de"] + 1) / 4) * (cam[..., :1] / 255.0)  # entra por esmaecimento em 4 quadros
        q = (q * (1 - a) + 255 * a).astype(np.uint8)
    return q


grava(OUT / "orig.mp4", [com_palavra(f) for f in range(N)])
grava(OUT / "clone.mp4", [com_palavra(f, 4) for f in range(N)])
grava(OUT / "placa.mp4", [fundo(f) for f in range(N)])
json.dump(CAM, open(OUT / "cam.json", "w"))

# verdade da caixa: a mesma palavra desenhada sozinha
v = np.zeros((H, W), np.uint8); cv2.putText(v, "PALAVRA", (PAL["x"](16), PAL["y"]), cv2.FONT_HERSHEY_DUPLEX, 1.6, 255, 4, cv2.LINE_AA)
ys, xs = np.nonzero(v > 127); verdade = [xs.min(), ys.min(), xs.max(), ys.max()]

# ------------------------------------------------------------------ trilha_palavra.py
json.dump({"palavra": dict(de=4, ate=36, teste="claro", limiar=200, escolha="uniao", dilata=15)}, open(OUT / "elementos.json", "w"))
r = roda(SCR / "trilha_palavra.py", OUT / "orig.mp4", OUT / "elementos.json", OUT / "trilhas.js", "--json", OUT / "trilhas.json")
T = json.load(open(OUT / "trilhas.json"))["palavra"]
q16 = T["q"][16 - 4]
confere(q16 is not None and max(abs(a - b) for a, b in zip(q16[:4], verdade)) <= 3, "trilha_palavra: caixa da palavra em f16",
        f"medida {q16[:4] if q16 else None}, verdade {verdade}")
confere(all(x is None for x in T["q"][:4]) and T["q"][8 - 4 + 3] is not None, "trilha_palavra: nada antes de f8, palavra em f11")
confere(r["ok"] and "proximo" in r, "trilha_palavra: saída JSON padrão")

# palavras automáticas: legenda de 8 palavras entrando uma a uma (texto escuro em fundo claro) e o vídeo da palavra só
claro = (255 - fundo(0) // 3)
pal8 = ["ELA", "VAI", "TOMAR", "AQUI", "O", "NOSSO", "CAFE", "HOJE"]
def legenda(f):
    q = claro.copy(); x, y = 30, 120
    for i, p in enumerate(pal8):
        if i == 4:
            x, y = 30, 200
        (tw, _), _ = cv2.getTextSize(p, cv2.FONT_HERSHEY_DUPLEX, 1.4, 3)
        if f >= 3 + 4 * i:
            cv2.putText(q, p, (x, y), cv2.FONT_HERSHEY_DUPLEX, 1.4, (25, 25, 25), 3, cv2.LINE_AA)
        x += tw + 22
    return q
P, leg, res = tp.acha_palavras(((f, legenda(f)) for f in range(N)), 1.0, 30.0, N)
inicios = sorted(p["f"][0] for p in P if p["polaridade"] == "escuro")
confere(leg and len(inicios) >= 7 and all(any(abs(i - (3 + 4 * k)) <= 1 for i in inicios) for k in range(8) if pal8[k] != "O"),
        "trilha_palavra --auto: 8 palavras uma a uma viram legenda", f"{res}, nascem em {inicios}")
_, leg1, res1 = tp.acha_palavras(((f, com_palavra(f)) for f in range(N)), 1.0, 30.0, N)
confere(not leg1, "trilha_palavra --auto: uma palavra só não é legenda", str(res1))

# ------------------------------------------------------------------ placa.py
r = roda(SCR / "placa.py", OUT / "orig.mp4", OUT / "cam.json", OUT / "placa.jpg", "--de", 0, "--ate", N - 1, "--ancora", 20)
pior = max(v for v in r["conferencia"].values() if v is not None)
confere(pior < 0.012, "placa: reprojeção da placa larga contra o original (sem a palavra)", f"pior {pior}")
r = roda(SCR / "placa.py", OUT / "orig.mp4", OUT / "cam.json", OUT / "janela.png", "--de", 10, "--ate", 16, "--ancora", 13, "--janela")
a = cv2.imread(str(OUT / "janela.png"), cv2.IMREAD_UNCHANGED)
confere(a is not None and a.shape[2] == 4 and 0 < (a[..., 3] == 0).mean() < 0.2, "placa --janela: PNG com alfa e buraco transparente",
        f"transparente {r['sem_dado']}")

# ------------------------------------------------------------------ registra_cam.py
errada = [dict(c, tx=c["tx"] + (6 if 25 <= c["f"] <= 35 else 0)) for c in CAM]  # a âncora (f20) fica certa: ela define o mundo
json.dump(errada, open(OUT / "cam_errada.json", "w"))
r = roda(SCR / "registra_cam.py", OUT / "orig.mp4", OUT / "cam_errada.json", OUT / "cam_certa.json", "--placa", f"{OUT / 'placa.jpg'}:0-{N - 1}")
certa = {c["f"]: c for c in json.load(open(OUT / "cam_certa.json"))}
erro = max(abs(certa[f]["tx"] - CAM[f]["tx"]) + abs(certa[f]["ty"] - CAM[f]["ty"]) for f in range(N))
confere(erro <= 1.0, "registra_cam: erro de 6 px em f25-35 corrigido contra a placa", f"erro que sobrou {erro:.2f} px; {r['resumo']}")

# ------------------------------------------------------------------ compara_mascara.py
igual = roda(SCR / "compara_mascara.py", OUT / "orig.mp4", OUT / "orig.mp4", OUT / "trilhas.js", "--placa", OUT / "placa.mp4")
desl = roda(SCR / "compara_mascara.py", OUT / "orig.mp4", OUT / "clone.mp4", OUT / "trilhas.js", "--placa", OUT / "placa.mp4")
confere(igual["distancia"] == 0 and igual["correlacao"] > 0.999 and igual["pico_quadros"] == 0, "compara_mascara: original contra ele mesmo",
        f"{igual['distancia']}, {igual['correlacao']}")
confere(desl["distancia_fina"] > 0.01 and desl["sem_camada"]["distancia_fina"] > desl["distancia_fina"],
        "compara_mascara: clone deslocado 4 px conta, e não desenhar nada conta mais",
        f"fina {desl['distancia_fina']}, sem camada {desl['sem_camada']['distancia_fina']}")

# ------------------------------------------------------------------ placa_video.py
roda(SCR / "placa_video.py", OUT / "orig.mp4", OUT / "trilhas.js", OUT / "placa_limpa", "--margem-x", 6, "--margem-y", 6)
pl = cv2.imread(str(OUT / "placa_limpa" / "0016.jpg"))[..., ::-1].astype(np.float32)
x0, y0, x1, y1 = verdade
antes = float(np.abs(com_palavra(16)[y0:y1, x0:x1].astype(np.float32) - fundo(16)[y0:y1, x0:x1]).mean())
depois = float(np.abs(pl[y0:y1, x0:x1] - fundo(16)[y0:y1, x0:x1]).mean())
confere(depois < 12 and antes > 3 * depois, "placa_video: a palavra some da placa", f"diferença para o fundo de {antes:.1f} para {depois:.1f} níveis")

# ------------------------------------------------------------------ aparicao.py
CX = [130, 180]  # palavra parada que aparece em f5-f8 (25 %, 50 %, 75 %, 100 %)
def parada(f, com=True):
    q = fundo(0)
    if com and f >= 5:
        cam = np.zeros_like(q); cv2.putText(cam, "ENTRA", tuple(CX), cv2.FONT_HERSHEY_DUPLEX, 1.6, (255, 255, 255), 4, cv2.LINE_AA)
        a = min(1.0, (f - 4) / 4) * (cam[..., :1] / 255.0)
        q = (q * (1 - a) + 255 * a).astype(np.uint8)
    return q
grava(OUT / "parada.mp4", [parada(f) for f in range(20)])
grava(OUT / "parada_placa.mp4", [parada(f, False) for f in range(20)])
v = np.zeros((H, W), np.uint8); cv2.putText(v, "ENTRA", tuple(CX), cv2.FONT_HERSHEY_DUPLEX, 1.6, 255, 4, cv2.LINE_AA)
ys, xs = np.nonzero(v > 127)
json.dump([dict(nome="entra", tipo="branco", cor=[255, 255, 255], de=5, ate=19, caixa=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())])],
          open(OUT / "camada.json", "w"))
roda(SCR / "aparicao.py", OUT / "parada.mp4", OUT / "parada_placa.mp4", OUT / "camada.json", OUT / "aparicao.js", "--json", OUT / "aparicao.json", "--borda", 6)
A = json.load(open(OUT / "aparicao.json"))["entra"]
med = [A["q"][f - A["de"]][0] for f in range(5, 9)]
confere(all(abs(m - e) < 0.12 for m, e in zip(med, (0.25, 0.5, 0.75, 1.0))), "aparicao: opacidade da entrada (25, 50, 75, 100 %)",
        ", ".join(f"{m:.2f}" for m in med))

# ------------------------------------------------------------------ recortes.py
RP = OUT / "recortes"; (RP / "referencia").mkdir(parents=True, exist_ok=True); (RP / "hf" / "assets" / "pecas").mkdir(parents=True, exist_ok=True)
shutil.copy2(OUT / "orig.mp4", RP / "referencia" / "original.mp4")
x0, y0 = PAL["x"](16) - 10, PAL["y"] - 45
cv2.imwrite(str(RP / "hf" / "assets" / "pecas" / "palavra.png"), cv2.cvtColor(com_palavra(16)[y0:y0 + 70, x0:x0 + 280], cv2.COLOR_RGB2BGR))
grava(OUT / "borrado.mp4", [cv2.GaussianBlur(com_palavra(f), (0, 0), 3) for f in range(N)])
md = RP / "hf" / "assets" / "RECORTES.md"
r = roda(SCR / "recortes.py", RP, "--clone", OUT / "borrado.mp4")
s = r["recortes"]["sem_declaracao"]
confere(not r["aprovada"] and s and s[0]["parece_do_original"], "recortes: recorte do original sem declaração reprova", r["resumo"])
confere(r["nitidez"]["borrado"], "recortes: clone borrado acusado na nitidez", f"razão {r['nitidez']['razao']}")
md.write_text("| arquivo | tipo | motivo |\n|---|---|---|\n| pecas/palavra.png | interface | recorte da palavra |\n")
confere(not roda(SCR / "recortes.py", RP, "--clone", OUT / "orig.mp4")["aprovada"], "recortes: tipo interface reprova")
md.write_text("| arquivo | tipo | motivo |\n|---|---|---|\n| pecas/*.png | foto | teste: foto filmada |\n")
r = roda(SCR / "recortes.py", RP, "--clone", OUT / "orig.mp4")
confere(r["aprovada"] and not r["nitidez"]["borrado"] and abs(r["nitidez"]["razao"] - 1) < 0.05, "recortes: declarado aprova; clone igual tem nitidez 1",
        f"razão {r['nitidez']['razao']}")

# ------------------------------------------------------------------ modelo: amostra() presa ao trecho
html = (KIT / "modelo" / "index.html").read_text()
m = re.search(r"// <encaixe>[^\n]*\n(.*?)// </encaixe>", html, re.S)
js = ("const H = 100; const T = {p: {de: 10, ate: 12, q: [[0,0,10,10,0,0,0,0,100],[2,0,12,10,0,0,0,0,100],[4,0,14,10,0,0,0,0,100]]}};\n"
      + (m.group(1) if m else "") + "\nconsole.log(JSON.stringify([amostra('p', 9.6), amostra('p', 10.5), amostra('p', 12.7), amostra('x', 5)]));")
r = subprocess.run(["node", "-e", js], capture_output=True, text=True)
try:
    a96, a105, a127, ax = json.loads(r.stdout)
    confere(a96 is not None and a96[0] == 0 and a105[0] == 1 and a127[0] == 4 and ax is None,
            "modelo: amostra() presa ao trecho (subquadro antes do 1º quadro usa o 1º)", f"{a96 and a96[0]}, {a105[0]}, {a127[0]}, {ax}")
except (ValueError, TypeError):
    confere(False, "modelo: trecho <encaixe> roda no node", r.stderr.strip()[-200:])
confere(all(k in html for k in ("function tinta(", "function encaixa(", "trilhas.js", "camada.js")), "modelo: tinta, encaixa, trilhas.js e camada.js")

print(f"\n{'OK' if not falhas else 'FALHOU: ' + '; '.join(falhas)}  (arquivos em {OUT})")
sys.exit(1 if falhas else 0)
