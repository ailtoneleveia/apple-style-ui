#!/usr/bin/env python3
"""placa_video.py: a placa de fundo de um vídeo de pessoa (ou de qualquer filmagem), sem a camada desenhada por cima.

  placa_video.py <original> <mascara> <pasta_saida> [--margem-x 30] [--margem-y 16] [--folga 1] [--qualidade 90]
                 [--mp4 placa.mp4]

A pessoa filmada não se recria: vira placa, quadro a quadro. Mas o original já traz a legenda, o cartão e os emojis
queimados na imagem; se a placa for o original cru, a camada antiga aparece por baixo da nova e a nota engana.
Aqui, em cada quadro, as caixas da máscara (as peças da camada, com margem para o deslocamento e o desfoque da
entrada, e `folga` quadros antes e depois) são apagadas e preenchidas pelo entorno (inpaint Telea): buraco pequeno
(texto) em resolução cheia, buraco grande (cartão) em 1/4 e ampliado, porque o vidro vai borrá-lo de qualquer jeito.
mascara: [{"de": f0, "ate": f1, "caixa": [x0, y0, x1, y1], "pegada": "x.png"?}] em px do original (com pegada, só a
tinta da peça vira buraco: o vão entre as letras fica com o fundo de verdade), ou trilhas.js/trilhas.json.
Saída: <pasta_saida>/NNNN.jpg (um por quadro, para a composição desenhar o quadro Fi) e, com --mp4, o mesmo em vídeo
(para o compara_mascara.py --placa). Uso interno: a placa é o vídeo original.
"""
import argparse, os, subprocess, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import falha, ok, quadros, tamanho  # noqa: E402
from compara_mascara import le_mascara, mascara_do_quadro  # noqa: E402

GRANDE = 60000  # px: acima disso o buraco é preenchido em 1/4


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("original"); ap.add_argument("mascara"); ap.add_argument("saida")
    ap.add_argument("--margem-x", type=int, default=30); ap.add_argument("--margem-y", type=int, default=16)
    ap.add_argument("--folga", type=int, default=1); ap.add_argument("--qualidade", type=int, default=90)
    ap.add_argument("--mp4")
    a = ap.parse_args()
    if not os.path.exists(a.original):
        falha(f"não encontrado: {a.original}", 1)
    W, H = tamanho(a.original)
    cx = le_mascara(a.mascara, None, 0)
    por_q = {}
    for f, cs in cx.items():  # folga: a peça que entra desfocada já borra o quadro antes do medido
        for g in range(f - a.folga, f + a.folga + 1):
            por_q.setdefault(g, []).extend(cs)
    os.makedirs(a.saida, exist_ok=True)
    n, area = 0, []
    for f, q in quadros(a.original):
        bgr = np.ascontiguousarray(q[..., ::-1])
        m = (mascara_do_quadro(por_q.get(f, []), W, H) > 0).astype(np.uint8) * 255
        if m.any() and (a.margem_x or a.margem_y):
            m = cv2.dilate(m, np.ones((2 * a.margem_y + 1, 2 * a.margem_x + 1), np.uint8))
        if m.any():
            nc, lab, st, _ = cv2.connectedComponentsWithStats(m)
            grande = np.isin(lab, [j for j in range(1, nc) if st[j, 4] > GRANDE]).astype(np.uint8) * 255
            pequeno = cv2.subtract(m, grande)
            if grande.any():
                k = 4
                lo = cv2.inpaint(cv2.resize(bgr, (W // k, H // k), interpolation=cv2.INTER_AREA),
                                 cv2.dilate(cv2.resize(grande, (W // k, H // k), interpolation=cv2.INTER_NEAREST), np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)
                hi = cv2.resize(lo, (W, H), interpolation=cv2.INTER_CUBIC)
                bgr = np.where(grande[..., None] > 0, hi, bgr)
            if pequeno.any():
                bgr = cv2.inpaint(bgr, pequeno, 5, cv2.INPAINT_TELEA)
            area.append(float((m > 0).mean()))
        cv2.imwrite(os.path.join(a.saida, f"{f:04d}.jpg"), bgr, [cv2.IMWRITE_JPEG_QUALITY, a.qualidade])
        n += 1
    if not n:
        falha("não li nenhum quadro do original", 2)
    if a.mp4:
        fps = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0",
                              a.original], capture_output=True, text=True).stdout.strip()
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", fps, "-i", os.path.join(a.saida, "%04d.jpg"), "-c:v", "libx264",
                            "-crf", "10", "-pix_fmt", "yuv420p", "-refs", "4", "-level:v", "5.1", a.mp4], capture_output=True, text=True)
        if r.returncode:
            falha(f"ffmpeg falhou ao gravar {a.mp4}: {r.stderr.strip()[-300:]}", 2)
    ok(f"{n} quadros de placa em {a.saida}; {len(area)} com buraco preenchido (em média {100 * np.mean(area or [0]):.1f} % do quadro)",
       comando=None, motivo="desenhar o quadro Fi da placa embaixo da camada (só quando !SO_CAMADA) e comparar com --placa",
       saida=os.path.abspath(a.saida), quadros=n, mp4=os.path.abspath(a.mp4) if a.mp4 else None)


if __name__ == "__main__":
    main()
