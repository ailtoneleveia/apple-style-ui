#!/usr/bin/env python3
"""pecas_livres.py: gera as peças livres (CC0) que ocupam o lugar dos recortes do original nos moldes Joi e VoiceOS,
e o silêncio que ocupa o lugar do áudio do original nos três moldes de interface.

    python3 moldes/pecas_livres.py

Os recortes dos vídeos de referência (objetos 3D do Joi; céu, vinhedo, ícones e memoji do VoiceOS) e o áudio dos
originais não vão no repositório. Aqui eles viram desenhos simples, feitos só com código e semente fixa, com o mesmo
nome e o mesmo tamanho, para os moldes renderizarem igual sem mudar uma linha. Para ficar bonito, troque pelos teus:
no VoiceOS, os campos foto_ceu e foto_vinhedo aceitam qualquer imagem tua.
"""
import os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

AQUI = os.path.dirname(os.path.abspath(__file__))
JOI = os.path.join(AQUI, "joi", "molde", "assets", "sprites")
VOS = os.path.join(AQUI, "voiceos", "molde", "assets", "img")
rng = np.random.default_rng(7)


def ruido(w, h, escala, oitavas=4):
    """Ruído suave (nuvem) de 0 a 1, feito em baixa resolução e ampliado."""
    acc = np.zeros((h, w), np.float32)
    for o in range(oitavas):
        s = max(2, int(escala * 2 ** o))
        r = Image.fromarray((rng.random((s, max(2, s * w // h))) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
        acc += np.asarray(r, np.float32) / 255 / 2 ** o
    acc -= acc.min()
    return acc / acc.max()


def gradiente(w, h, cima, baixo):
    t = np.linspace(0, 1, h, dtype=np.float32)[:, None, None]
    return np.broadcast_to((1 - t) * np.array(cima, np.float32) + t * np.array(baixo, np.float32), (h, w, 3)).copy()


def ceu(w, h):
    """Céu azul com nuvens claras. Devolve (imagem, nuvem de 0 a 1)."""
    base = gradiente(w, h, (70, 128, 200), (176, 208, 236))
    n = ruido(w // 8, h // 8, 3)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255
    nuvem = np.clip((n - 0.45) * 2.4, 0, 1)[..., None]
    return Image.fromarray(np.uint8(base * (1 - nuvem) + 248 * nuvem)), nuvem[..., 0]


def vinhedo(w, h):
    """Campo verde em perspectiva, com fileiras."""
    img = gradiente(w, h, (150, 170, 120), (60, 92, 40))
    y = np.arange(h, dtype=np.float32)[:, None]
    x = np.arange(w, dtype=np.float32)[None, :]
    persp = (x - w / 2) / (0.15 + y / h)
    fileira = (np.sin(persp / 18) > 0.55)[..., None]
    img = np.where(fileira, img * 0.78, img)
    return Image.fromarray(np.uint8(np.clip(img, 0, 255)))


def caixa(w, h, fundo, cor, raio, desenho=None):
    im = Image.new("RGB", (w, h), fundo)
    d = ImageDraw.Draw(im)
    m = round(w * 0.06)
    d.rounded_rectangle((m, m, w - m, h - m), radius=raio, fill=cor)
    if desenho:
        desenho(d, w, h)
    return im


def objeto(w, h, forma, cor):
    """Objeto do menu do Joi: forma com luz de cima. Devolve (com fundo escuro, com alfa)."""
    esc = 4
    a = Image.new("L", (w * esc, h * esc), 0)
    d = ImageDraw.Draw(a)
    W, H = w * esc, h * esc
    if forma == "xicara":
        d.rounded_rectangle((W * .18, H * .22, W * .72, H * .86), radius=W * .08, fill=255)
        d.ellipse((W * .62, H * .38, W * .88, H * .66), outline=255, width=int(W * .06))
    elif forma == "controle":
        d.rounded_rectangle((W * .08, H * .3, W * .92, H * .74), radius=H * .2, fill=255)
    elif forma == "bola":
        d.ellipse((W * .1, H * .1, W * .9, H * .9), fill=255)
    else:  # monitor
        d.rounded_rectangle((W * .08, H * .1, W * .92, H * .66), radius=W * .04, fill=255)
        d.rectangle((W * .44, H * .66, W * .56, H * .82), fill=255)
        d.rounded_rectangle((W * .28, H * .82, W * .72, H * .88), radius=H * .02, fill=255)
    a = a.resize((w, h), Image.LANCZOS)
    luz = gradiente(w, h, [min(255, c * 1.35) for c in cor], [c * 0.55 for c in cor])
    rgba = Image.fromarray(np.uint8(np.dstack([luz, np.asarray(a)])), "RGBA")
    fundo = Image.new("RGBA", (w, h), (26, 26, 26, 255))
    return Image.alpha_composite(fundo, rgba).convert("RGB"), rgba


def silencio(caminho, segundos):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", f"{segundos}",
                    "-c:a", "aac", "-b:a", "64k", caminho], check=True)


def main():
    # Joi: os quatro objetos do menu escuro
    for nome, forma, (w, h), cor in [("cup", "xicara", (130, 120), (190, 180, 170)), ("pad", "controle", (140, 130), (120, 114, 100)),
                                     ("ball", "bola", (130, 130), (150, 150, 150)), ("screen", "monitor", (140, 150), (110, 112, 112))]:
        rgb, rgba = objeto(w, h, forma, cor)
        rgb.save(os.path.join(JOI, nome + ".png"))
        rgba.save(os.path.join(JOI, nome + "-a.png"))
    # VoiceOS: céu, faixa do céu, vinhedo e a máscara das nuvens
    c1, nuvem = ceu(4435, 2495)
    c1.save(os.path.join(VOS, "sky1.jpg"), quality=82)
    ceu(3696, 670)[0].save(os.path.join(VOS, "sky2.jpg"), quality=82)
    vinhedo(3696, 2080).save(os.path.join(VOS, "vine.jpg"), quality=82)
    alfa = Image.fromarray(np.uint8(nuvem * 255)).resize((2218, 1248), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6))
    Image.merge("RGBA", (*[Image.new("L", alfa.size, 255)] * 3, alfa)).save(os.path.join(VOS, "cloudmatte.png"))
    # VoiceOS: ícones de app (formas genéricas, sem imitar marca nenhuma; o nome do arquivo é só o do campo), o avatar e o ícone pequeno do HUD
    fundo = (147, 187, 226)
    branco = (255, 255, 255)
    formas = {
        "slack": ((92, 60, 140), lambda d, w, h: [d.ellipse((w * .3 + i % 2 * w * .22, h * .3 + i // 2 * h * .22, w * .48 + i % 2 * w * .22, h * .48 + i // 2 * h * .22), fill=branco) for i in range(4)]),
        "notion": ((245, 245, 245), lambda d, w, h: d.rounded_rectangle((w * .3, h * .28, w * .7, h * .72), radius=8, outline=(30, 30, 30), width=8)),
        "messages": ((70, 200, 90), lambda d, w, h: d.ellipse((w * .24, h * .26, w * .76, h * .68), fill=branco)),
        "docs": ((60, 120, 230), lambda d, w, h: [d.rectangle((w * .32, h * (.34 + .1 * i), w * .68, h * (.34 + .1 * i) + 7), fill=branco) for i in range(4)]),
        "gmail": ((235, 170, 60), lambda d, w, h: [d.rectangle((w * .26, h * .32, w * .74, h * .68), outline=branco, width=8), d.line([(w * .26, h * .32), (w * .5, h * .52), (w * .74, h * .32)], fill=branco, width=8)]),
        "figma": ((40, 40, 40), lambda d, w, h: [d.ellipse((w * .36, h * (.24 + .17 * i), w * .52, h * (.4 + .17 * i)), fill=c) for i, c in enumerate([branco] * 3)]),
        "cube": ((120, 120, 130), lambda d, w, h: d.polygon([(w * .5, h * .24), (w * .74, h * .38), (w * .74, h * .64), (w * .5, h * .78), (w * .26, h * .64), (w * .26, h * .38)], fill=(220, 220, 228))),
    }
    for nome, (cor, des) in formas.items():
        caixa(172, 172, fundo, cor, 38, des).save(os.path.join(VOS, f"ic_{nome}.png"))
    caixa(41, 41, (20, 20, 20), (245, 245, 245), 9, formas["notion"][1]).save(os.path.join(VOS, "notion_hud.png"))
    av = Image.new("RGB", (122, 120), (21, 22, 26))
    d = ImageDraw.Draw(av)
    d.ellipse((14, 10, 108, 104), fill=(214, 160, 120))
    d.ellipse((40, 44, 50, 56), fill=(40, 30, 30))
    d.ellipse((72, 44, 82, 56), fill=(40, 30, 30))
    d.arc((44, 58, 78, 84), 20, 160, fill=(120, 60, 50), width=4)
    av.save(os.path.join(VOS, "avatar.png"))
    # Satellite: um logo neutro para o balão final dos exemplos (no lugar do emoji)
    from PIL import ImageFont
    lg = Image.new("RGB", (200, 200), (24, 24, 28))
    d = ImageDraw.Draw(lg)
    d.ellipse((0, 0, 199, 199), fill=(229, 74, 38))
    f = ImageFont.truetype(os.path.join(AQUI, "satellite", "molde", "assets", "fonts", "Inter.ttf"), 120)
    d.text((100, 100), "A", font=f, fill=(255, 255, 255), anchor="mm")
    lg.save(os.path.join(AQUI, "satellite", "molde", "assets", "logo-exemplo.png"))
    # silêncio no lugar do áudio do original (a duração de cada molde)
    for pasta, seg in [("satellite/molde", 10.9333), ("joi/molde", 7.5167), ("voiceos/molde", 11.6667)]:
        silencio(os.path.join(AQUI, pasta, "assets", "silencio.m4a"), seg)
    print("peças livres geradas")


if __name__ == "__main__":
    main()
