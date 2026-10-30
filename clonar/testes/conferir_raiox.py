#!/usr/bin/env python3
"""conferir_raiox.py [pasta_saida]: roda o raio-x nos três originais já clonados e confere com o que os clones mediram
(ESTILO.md e LESSONS.md de cada clone). Sai com código 1 se algum número firme não bater."""
import json, os, subprocess, sys, tempfile
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
# os três originais são de terceiros e não vão no repositório: quem tem os clones aponta ASUI_ORIGINAIS para eles
R = Path(os.environ.get("ASUI_ORIGINAIS") or Path.home() / ".apple-style-ui" / "originais")
CASOS = [  # nome, original, eventos da ficha (None = automático), esperado
    ("Satellite", R / "satellite-ref.mp4", None,
     dict(fps=30, quadros=328, cortes=[], bpm=102.6, obturador=0.25, segue=False, mola=("largura", 30, 34, "firme"))),
    ("Joi", R / "joi-ref.mp4", "80,132,199,281,329,354",
     dict(fps=60, quadros=451, cortes=[354], bpm=136.9, obturador=0.4, segue=True, mola=None)),
    ("VoiceOS", R / "voiceos-ref.mp4", None,
     dict(fps=60, quadros=700, cortes=[263], bpm=119.9, obturador=0.5, segue=False, mola=None)),
]
saida = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(tempfile.mkdtemp(prefix="raiox-teste-"))
falhas = []
print("| vídeo | fps / quadros | cortes secos | BPM | obturador | batida | mola de referência | tempo |")
print("|---|---|---|---|---|---|---|---|")
for nome, video, eventos, e in CASOS:
    out = saida / nome
    cmd = [sys.executable, KIT / "scripts/raiox.py", video, out] + (["--eventos", eventos] if eventos else [])
    subprocess.run([str(c) for c in cmd], check=True, capture_output=True)
    r = json.load(open(out / "raiox.json"))
    ok_base = round(r["fps"]) == e["fps"] and r["quadros"] == e["quadros"]
    ok_cortes = len(r["cortes_secos"]) == len(e["cortes"]) and all(min((abs(c - x) for x in r["cortes_secos"]), default=99) <= 2 for c in e["cortes"])
    bpm = r["batida"].get("bpm") or 0
    ok_bpm = abs(bpm / e["bpm"] - 1) <= 0.03
    o = r["obturador"].get("obturador")
    ok_obt = o is None or abs(o - e["obturador"]) <= 0.15  # sem amostra boa não é erro; número longe é
    segue = r["batida"].get("leitura", "").startswith("segue a batida")
    ok_seg = segue == e["segue"]
    mola_txt = "não pedida"
    if e["mola"]:
        g, a0, a1, nm = e["mola"]
        achou = [m for m in r["molas"] if m["grandeza"] == g and a0 <= m["a"] <= a1]
        mola_txt = (f"{g} f{achou[0]['a']}: zeta {achou[0]['zeta']}, omega {achou[0]['omega']} → {achou[0]['mais_parecida']}"
                    if achou else f"{g} f{a0}-{a1} não achada")
        if not achou or achou[0]["mais_parecida"] != nm:
            falhas.append(f"{nome}: mola esperada {nm}")
    for ok, o_que in ((ok_base, "fps/quadros"), (ok_cortes, "cortes"), (ok_bpm, "BPM"), (ok_obt, "obturador"), (ok_seg, "batida")):
        if not ok:
            falhas.append(f"{nome}: {o_que}")
    print(f"| {nome} | {r['fps']:g} / {r['quadros']} | {r['cortes_secos']} (esperado {e['cortes']}) | {bpm} (esperado {e['bpm']}) | "
          f"{o} (esperado {e['obturador']}) | {r['batida'].get('leitura')} | {mola_txt} | {r['tempo_s']} s |")
print("\nOK" if not falhas else "\nFALHOU: " + "; ".join(falhas))
sys.exit(1 if falhas else 0)
