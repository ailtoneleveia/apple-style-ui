#!/usr/bin/env python3
"""conferir_qualidade.py [pasta_saida]: confere o medidor por peça (scripts/qualidade.py) em vídeos sintéticos com resposta
conhecida. Um cartão com um glifo dentro entra pela esquerda com a mola elástica do estilo.js (zeta 0,62, omega 19,2),
renderizado com motion blur de 8 subquadros. Roda em menos de um minuto.

  mola conhecida      o modo estilo acha a mola do cartão (zeta e omega perto dos verdadeiros, elástica) e aprova;
                      o original contra ele mesmo aprova todas as peças
  velocidade quebrada o mesmo caminho por pose lida à mão a cada quadro (erro de 6 a 14 px que troca de lado, interpolação linear):
                      reprova por quebras de velocidade ou movimento sem mola
  peça borrada        o mesmo vídeo com o cartão borrado (gaussiana de 6 px): reprova por nitidez
  código              tabela de chaves com 10 poses reprova; mola do estilo.js com mapa de tempo aprova
Sai com código 1 se algo não bater."""
import json, os, subprocess, sys, tempfile
from pathlib import Path
import numpy as np
import cv2

KIT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KIT / "scripts"))
import qualidade as q  # noqa: E402

W = H = 1080; N = 60; FPS = 30
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="qualidade-"))
OUT.mkdir(parents=True, exist_ok=True)
falhas = []


def confere(ok, o_que, detalhe=""):
    print(f"{'ok   ' if ok else 'FALHA'} {o_que}{': ' + detalhe if detalhe else ''}")
    if not ok:
        falhas.append(o_que)


def mola(t, z=0.62, w=19.2):
    """progresso 0→1 da mola que sai do repouso (a mesma forma fechada do estilo.js)"""
    t = np.maximum(t, 0)
    wd = w * np.sqrt(1 - z * z); a = z * w
    return 1 - np.exp(-a * t) * (np.cos(wd * t) + a / wd * np.sin(wd * t))


X0, X1, T0, FIM = 300, 640, 6, 30  # o cartão nasce no f6 em x 300, anda até 640 e some no f30


def x_mola(F):
    return X0 + (X1 - X0) * mola((F - T0) / FPS)


rng = np.random.default_rng(7)
CH = {f: X0 + (X1 - X0) * mola((f - T0) / FPS) + ((-1) ** f * rng.uniform(6, 14) if 0 < f - T0 < 20 else 0) for f in range(N + 1)}


def x_chaves(F):  # pose lida à mão quadro a quadro, interpolação linear (o jeito do B2: "centro por quadro")
    ks = sorted(CH)
    return float(np.interp(F, ks, [CH[k] for k in ks]))


def cartao(img, x, F, borrado=False):
    """cartão azul de 180 px com um glifo branco; vive de T0 a FIM (fora disso o fundo da cena não o engole)"""
    a = float(np.clip(F - T0 + 1, 0, 1) * np.clip((FIM - F) / 2, 0, 1))
    if a <= 0:
        return
    M = 24  # folga: o borrão leva a borda do cartão junto (recorte ampliado, não só o miolo)
    c = np.full((180 + 2 * M, 180 + 2 * M, 3), 243, np.uint8); c[M:M + 180, M:M + 180] = (40, 150, 245)
    cv2.circle(c, (M + 90, M + 90), 44, (255, 255, 255), -1); cv2.rectangle(c, (M + 60, M + 80), (M + 120, M + 100), (40, 150, 245), -1)
    if borrado:
        c = cv2.GaussianBlur(c, (0, 0), 6)
    x0, y0 = int(round(x)) - 90 - M, 400 - M
    if 0 <= x0 and x0 + 180 + 2 * M <= W:
        reg = img[y0:y0 + 180 + 2 * M, x0:x0 + 180 + 2 * M].astype(np.float32)
        img[y0:y0 + 180 + 2 * M, x0:x0 + 180 + 2 * M] = (reg * (1 - a) + c * a).round().astype(np.uint8)


def quadros(xf, borrado=False, sub=8):
    out = []
    for f in range(N):
        acc = np.zeros((H, W, 3), np.float32)
        for s in range(sub):  # motion blur de subquadro: obturador de 0,25 quadro (1/120 s a 30 qps)
            F = f + (s / (sub - 1) - 0.5) * 0.25
            img = np.full((H, W, 3), 243, np.uint8)
            cartao(img, xf(F), F, borrado)
            acc += img
        out.append((acc / sub).round().astype(np.uint8))
    return out


def grava(nome, qs):
    p = OUT / nome
    pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                           "-c:v", "libx264", "-crf", "6", "-pix_fmt", "yuv444p", str(p)], stdin=subprocess.PIPE)
    for x in qs:
        pr.stdin.write(np.ascontiguousarray(x).tobytes())
    pr.stdin.close(); pr.wait()
    return p


ref = grava("mola.mp4", quadros(x_mola))
quebrado = grava("chaves.mp4", quadros(x_chaves))
borrado = grava("borrado.mp4", quadros(x_mola, borrado=True))


def peca_do_cartao(res):
    """a peça que mais anda (o cartão)"""
    return max(res, key=lambda r: max((abs(m["caminho"]) for m in r["medidas"]["molas"]), default=0))


# 1. mola conhecida, sem referência
res, info, glob = q.estilo(ref)
c = peca_do_cartao(res)
mx = [m for m in c["medidas"]["molas"] if m["grandeza"] == "x" and m["mola"]]
achou = mx[0] if mx else None
confere(bool(achou) and abs(achou["zeta"] - 0.62) <= 0.2 and abs(achou["omega"] / 19.2 - 1) <= 0.2,
        "mola conhecida: zeta e omega do cartão", f"medido zeta {achou and achou['zeta']}, omega {achou and achou['omega']} (verdade 0,62 e 19,2)")
confere(bool(achou) and q.preset_perto(achou["zeta"], achou["omega"]) == "elastica", "mola conhecida: preset mais perto é a elástica")
confere(c["aprovada"], "mola conhecida: o cartão passa no perfil de estilo", json.dumps(c["reprovacoes"], ensure_ascii=False)[:300])

# 2. original contra ele mesmo
res, info, cen, g = q.compara(ref, ref, obturador=False)
for r in res:
    q.julga(r, FPS, W)
confere(all(r["aprovada"] for r in res), "original contra ele mesmo: todas as peças passam",
        "; ".join(f"{r['peca']}: {r['reprovacoes'][0]['motivo']}" for r in res if not r["aprovada"])[:300])

# 3. velocidade quebrada
res, info, cen, g = q.compara(ref, quebrado, obturador=False)
for r in res:
    q.julga(r, FPS, W)
c = peca_do_cartao(res)
med = {x["medida"] for x in c["reprovacoes"]}
qb = c["medidas"]["velocidade"]["quebras"]
confere(not c["aprovada"] and bool(med & {"quebras", "mola", "velocidade"}), "velocidade quebrada: o cartão reprova pelo movimento",
        f"medidas {sorted(med)}; quebras a mais {qb['a_mais']} (f{qb['quadros']}); erro de velocidade {c['medidas']['velocidade'].get('erro')}; "
        f"molas {[(m['grandeza'], m.get('curva_rms'), (m['clone'] or {}).get('rms'), (m['original'] or {}).get('rms')) for m in c['medidas']['molas']]}")

# 4. peça borrada
res, info, cen, g = q.compara(ref, borrado, obturador=False)
for r in res:
    q.julga(r, FPS, W)
c = peca_do_cartao(res)
confere(not c["aprovada"] and "nitidez" in {x["medida"] for x in c["reprovacoes"]}, "peça borrada: reprova por nitidez",
        f"nitidez {c['medidas']['nitidez']}x a do original")

# 5. código
hf = OUT / "hf"; hf.mkdir(exist_ok=True)
(hf / "cena.js").write_text("const CARTAO = [[0, 70], [2, 120], [4, 200], [6, 260], [8, 300], [10, 330], [12, 350], [14, 365], [16, 375], [18, 380]];\n"
                            "function x(F) { return K(F, CARTAO); }\n")
r = q.codigo(hf)
confere(not r["aprovado"] and r["tabelas_de_pose"] and r["tabelas_de_pose"][0]["chaves"] == 10, "código: tabela de 10 poses reprova")
(hf / "cena.js").write_text("const x = (t) => 70 + 310 * ES.mola(t - 0.2, 'elastica');\n"
                            "window.DADOS = {\"mapa\": [" + ", ".join(str(i) for i in list(range(20)) + [19] * 5 + list(range(20, 40))) + "]};\n")
r = q.codigo(hf)
confere(r["aprovado"] and r["molas_em_uso"] >= 1 and len(r["mapas_de_tempo"]) == 1, "código: mola do estilo.js com mapa de tempo aprova")

print("\nOK" if not falhas else "\nFALHOU: " + "; ".join(falhas))
sys.exit(1 if falhas else 0)
