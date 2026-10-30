#!/usr/bin/env python3
# Copyright (c) 2026 Pat Simmons. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
# Corrigido pelos 3 primeiros clones: resolução cheia, qualquer formato, sem -shortest, nível 5.1.
"""sbs.py <original.mp4> <clone.mp4> <saida.mp4>: lado a lado em resolução cheia.

ORIGINAL à esquerda, CLONE à direita, cada metade no tamanho do original (o clone é escalado se precisar),
rótulos numa plaquinha escura no canto de cima de cada metade (não somem em fundo branco nem caem em cima
da imagem em vídeo vertical), áudio do original, sem -shortest (cortava os últimos quadros). H.264 com
-refs 4 -level:v 5.1: sem nível fixo o x264 sobe para 6.0 e o QuickTime embaralha os blocos."""
import json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

ref, clone, out = sys.argv[1:4]
st = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height,r_frame_rate", "-of", "json", ref],
                               capture_output=True, text=True, check=True).stdout)["streams"][0]
W, H, fps = st["width"], st["height"], st["r_frame_rate"]
im = Image.new("RGBA", (2 * W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
fs = max(22, round(min(W, H) * 0.035))
f = None
for p in ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
    if os.path.exists(p):
        f = ImageFont.truetype(p, fs); break
f = f or ImageFont.load_default()
for x0, t, c in [(fs * 0.7, "ORIGINAL", (255, 255, 255)), (W + fs * 0.7, "CLONE", (255, 110, 110))]:
    b = d.textbbox((0, 0), t, font=f); m = fs * 0.45
    d.rounded_rectangle([x0, fs * 0.6, x0 + b[2] - b[0] + 2 * m, fs * 0.6 + b[3] - b[1] + 2 * m], radius=fs // 3, fill=(0, 0, 0, 170))
    d.text((x0 + m - b[0], fs * 0.6 + m - b[1]), t, font=f, fill=c)
lab = os.path.join(tempfile.mkdtemp(), "rotulos.png"); im.save(lab)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", ref, "-i", clone, "-i", lab, "-filter_complex",
                f"[0:v]setsar=1[a];[1:v]scale={W}:{H},setsar=1[b];[a][b]hstack=inputs=2[s];[s][2:v]overlay=0:0[v]",
                "-map", "[v]", "-map", "0:a?", "-c:v", "libx264", "-preset", "slow", "-tune", "animation", "-crf", "14",
                "-refs", "4", "-level:v", "5.1", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-r", fps,
                "-c:a", "aac", "-b:a", "192k", out], check=True)
print(out)
