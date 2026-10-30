#!/usr/bin/env python3
"""conferir_qualidade.py [pasta_saida]: confere o medidor por peça (scripts/qualidade.py) em vídeos sintéticos com resposta
conhecida. Um cartão com um glifo dentro entra pela esquerda com a mola elástica do estilo.js (zeta 0,62, omega 19,2),
renderizado com motion blur de 8 subquadros. Roda em cerca de três minutos.

  mola conhecida      o modo estilo acha a mola do cartão (zeta e omega perto dos verdadeiros, elástica) e aprova;
                      o original contra ele mesmo aprova todas as peças
  velocidade quebrada o mesmo caminho por pose lida à mão a cada quadro (erro de 6 a 14 px que troca de lado, interpolação linear):
                      reprova por quebras de velocidade ou movimento sem mola
  peça borrada        o mesmo vídeo com o cartão borrado (gaussiana de 6 px): reprova por nitidez
  rastro              disco escuro a 12 px/q, original com obturador de 1 quadro contra clone sem borrão: reprova por rastro
                      (falta); ao contrário, clone com rastro onde o original é nítido: reprova por rastro (sobra)
  peça pequena rápida um cursor de 36 px cruza a tela em 7 quadros (40 px/q); no clone passa 30 px abaixo: a peça é
                      detectada (trilha curta) e reprova por forma, com o erro do centro no motivo
  mancha              pílula preta com 3 pontos em onda que anda 5 px/q: uma pílula cinza a mais no fundo liso e os pontos
                      alinhados no lugar da onda reprovam por mancha; o vídeo deslocado 2 px ou atrasado 1 quadro não
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


def quadros_disco(obt):
    """disco escuro de 80 px que anda 12 px/q da esquerda para a direita; obt = obturador em quadros (0 = nítido)"""
    out = []
    for f in range(N):
        acc = np.zeros((H, W, 3), np.float32)
        for s in range(16):
            img = np.full((H, W, 3), 243, np.uint8)
            cv2.circle(img, (int(round(200 + 12 * (f + (s / 15 - 0.5) * obt))), 540), 40, (30, 30, 30), -1, cv2.LINE_AA)
            acc += img
        out.append((acc / 16).round().astype(np.uint8))
    return out


def quadros_cursor(dy=0):
    """cursor (disco escuro de 36 px) que entra no f20 em x 900 e anda 40 px/q para a esquerda até o f26"""
    out = []
    for f in range(N):
        img = np.full((H, W, 3), 243, np.uint8)
        cv2.putText(img, "Get Info", (560, 760), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (30, 30, 30), 3, cv2.LINE_AA)
        if 20 <= f <= 26:
            cv2.circle(img, (900 - 40 * (f - 20), 800 + dy), 18, (40, 40, 40), -1, cv2.LINE_AA)
        out.append(img)
    return out


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

# 5. rastro: obturador de 1 quadro no original, clone nítido (e o contrário)
longo, nitido = grava("obt1.mp4", quadros_disco(1.0)), grava("obt0.mp4", quadros_disco(0.0))
for o_, c_, quer in ((longo, nitido, "falta"), (nitido, longo, "sobra")):
    res, info, cen, g = q.compara(o_, c_, obturador=False)
    for r in res:
        q.julga(r, FPS, W)
    c = max(res, key=lambda r: len(r["medidas"].get("rastro") and r["medidas"]["rastro"]["quadros"] or []) + r["medidas"]["quadros"])
    ra = c["medidas"].get("rastro")
    rp = [x for x in c["reprovacoes"] if x["medida"] == "rastro"]
    confere(bool(rp) and quer in rp[0]["motivo"], f"rastro: {'clone sem o rastro do original' if quer == 'falta' else 'clone com rastro que o original não tem'} reprova ({quer})",
            f"rastro {ra}")

# 6. peça pequena e rápida (cursor): detectada e reprovada pelo lugar
cur, cur_errado = grava("cursor.mp4", quadros_cursor()), grava("cursor-baixo.mp4", quadros_cursor(30))
res, info, cen, g = q.compara(cur, cur, obturador=False)
for r in res:
    q.julga(r, FPS, W)
achou = [r for r in res if r["onde"].startswith("f20-26")]
confere(bool(achou) and all(r["aprovada"] for r in res), "cursor: a trilha curta e rápida vira peça e passa contra ela mesma",
        "; ".join(r["onde"] for r in res))
res, info, cen, g = q.compara(cur, cur_errado, obturador=False)
for r in res:
    q.julga(r, FPS, W)
c = next((r for r in res if r["onde"].startswith("f20-26")), None)
po = c and c["medidas"].get("posicao")
confere(bool(c) and "forma" in {x["medida"] for x in c["reprovacoes"]} and bool(po) and 20 <= po["erro_px"] <= 40,
        "cursor 30 px abaixo: reprova por forma, com o erro do centro", f"posicao {po}; iou {c and c['medidas']['iou']}")

# 7. mancha de diferença persistente: pílula preta que anda 5 px/q com 3 pontos verdes em onda
def quadros_pilula(onda=24, a_mais=False, dx=0, atraso=0):
    out = []
    for f in range(N):
        g = max(0, f - atraso)
        img = np.full((H, W, 3), 243, np.uint8)
        x = 200 + 5 * g
        cv2.rectangle(img, (x, 420), (x + 360, 560), (20, 20, 20), -1)
        for i in range(3):  # o do meio no centro, os de fora a ±onda px (a onda do B4)
            cv2.circle(img, (x + 90 + 90 * i, 490 + onda * (1 - i)), 24, (60, 180, 80), -1, cv2.LINE_AA)
        if a_mais and 10 <= f <= 50:  # pílula cinza (contraste 83) onde o original só tem fundo
            cv2.rectangle(img, (760, 200), (850, 236), (160, 160, 160), -1)
        out.append(np.roll(img, (dx, dx), (0, 1)) if dx else img)
    return out


pil = grava("pilula.mp4", quadros_pilula())
for nome, kw, quer in (("elemento a mais no fundo liso", dict(a_mais=True), "a mais"), ("pontos alinhados no lugar da onda", dict(onda=0), "detalhe"),
                       ("deslocamento de 2 px", dict(dx=2), None), ("atraso de 1 quadro", dict(atraso=1), None)):
    res, info, cen, g = q.compara(pil, grava("pilula-c.mp4", quadros_pilula(**kw)), obturador=False)
    ms = g["manchas"]
    mot = [q.julga_mancha(i, m, FPS)["reprovacoes"][0]["motivo"] for i, m in enumerate(ms)]
    if quer is None:
        confere(not ms, f"mancha: {nome} não reprova", "; ".join(f"{m['caixa']} {m['pico']}" for m in ms))
    else:
        ok_ = any(quer in t for t in mot) if quer == "a mais" else any("detalhe" in t and 260 <= (m["caixa"][1] + m["caixa"][3]) / 2 <= 720 for t, m in zip(mot, ms))
        confere(ok_, f"mancha: {nome} reprova ({quer})", "; ".join(f"{m['caixa']} {m['pico']}: {t[:60]}" for m, t in zip(ms, mot)) or "nenhuma mancha")

# 8. código
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
