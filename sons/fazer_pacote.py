#!/usr/bin/env python3
"""fazer_pacote.py: monta o pacote de sons de interface do motor (sons/*.wav + sons/sons.json).

    python3 fazer_pacote.py <pasta do Kenney Interface Sounds>

Metade dos sons é gerada aqui (síntese determinística, sementes fixas); a outra metade vem do Kenney Interface Sounds
(CC0), que está no soundcn (github.com/kapishdima/soundcn, assets/kenney_interface-sounds). Cada som sai:
mono, 48 kHz, 16 bits, sem silêncio na frente e atrás (corte a -50 dB do pico), com fade de 1 ms na entrada e até 30 ms na saída, e com a mesma
loudness: -18 LUFS na janela de 100 ms mais alta (filtro K da BS.1770), com teto de -1 dBFS no pico.
A janela de 100 ms (e não os 400 ms do "momentâneo" da norma) é porque os sons duram de 10 a 700 ms.
O sons.json guarda, por som: arquivo, tipo, origem, licença, duração, "ataque" (o instante do pico de energia, que
o montar.py põe em cima do quadro do evento), loudness e pico finais.
"""
import json, os, subprocess, sys
import numpy as np
from scipy.signal import istft, lfilter, stft

AQUI = os.path.dirname(os.path.abspath(__file__))
SR = 48000
ALVO_LUFS, TETO_DB = -18.0, -1.0

# tipo -> ganho na mixagem (dB, sobre o som já normalizado) e a ordem de rodízio das versões
TIPOS = {
    "aparecer": -3, "clicar": 0, "tocar": -3, "digitar": -5, "numero": 2, "brilho": -3,
    "entrar": -2, "sair": -3, "morph": -2, "ilha": -2, "sucesso": -2,
}
KENNEY = "Kenney Interface Sounds 1.0 (kenney.nl), via soundcn (github.com/kapishdima/soundcn)"


# ---------------------------------------------------------------- síntese (tudo determinístico)
def t_(dur):
    return np.arange(int(dur * SR)) / SR


def banda(dur, fc, bw_oct, env, semente):
    """Ruído branco moldado no STFT: em cada instante, uma banda gaussiana (em oitavas) em volta de fc(t), vezes env(t)."""
    rng = np.random.default_rng(semente)
    x = rng.standard_normal(int(dur * SR) + 2048)
    f, tt, Z = stft(x, SR, nperseg=1024, noverlap=768)
    tt = tt - 512 / SR
    F = np.maximum(f[:, None], 1.0)
    G = np.exp(-0.5 * (np.log2(F / fc(tt)[None, :]) / bw_oct) ** 2) * env(tt)[None, :]
    _, y = istft(Z * G, SR, nperseg=1024, noverlap=768)
    return y[512:512 + int(dur * SR)]


def subida(tp, dur, ataque=2.2, queda=0.035):
    """Envelope que cresce até tp (curva de potência) e cai exponencial depois: o pico é o "ataque" do som."""
    return lambda t: np.where(t < tp, np.clip(t / tp, 0, 1) ** ataque, np.exp(-(t - tp) / queda)) * (t >= 0) * (t < dur)


def descida(tp, dur):
    """Sobe rápido até tp e desce suave até dur."""
    return lambda t: np.where(t < tp, np.clip(t / tp, 0, 1) ** 1.5, np.clip(1 - (t - tp) / (dur - tp), 0, 1) ** 2.2) * (t >= 0)


def varre(f0, f1, tp):
    """Frequência central em escala log de f0 a f1, chegando em f1 no instante tp."""
    return lambda t: f0 * (f1 / f0) ** np.clip(t / tp, 0, 1)


def seno(freq_t, amp_t):
    """Seno com frequência variável (fase integrada)."""
    fase = 2 * np.pi * np.cumsum(freq_t) / SR
    return np.sin(fase) * amp_t


def whoosh_entrar(dur, tp, f0, f1, bw, semente):
    return banda(dur, varre(f0, f1, tp), bw, subida(tp, dur), semente)


def whoosh_sair(dur, tp, f0, f1, bw, semente):
    return banda(dur, lambda t: f0 * (f1 / f0) ** np.clip(t / dur, 0, 1), bw, descida(tp, dur), semente)


def morph(dur, tp, f0, f1, grave0, grave1, semente):
    t = t_(dur)
    ar = banda(dur, varre(f0, f1, tp), 1.2, subida(tp, dur, 2.0, 0.05), semente)
    ar /= np.abs(ar).max()
    pos = np.clip(t - tp, 0, None)
    baque = seno(grave1 + (grave0 - grave1) * np.exp(-pos / 0.04), np.exp(-pos / 0.11) * (t >= tp) * np.clip(pos / 0.004, 0, 1))
    tom = seno(300 * 2 ** np.clip(t / tp, 0, 1), subida(tp, dur, 2.0, 0.03)(t)) * 0.15
    return ar * 0.55 + baque * 0.8 + tom


def ilha(dur):
    """Abrir a ilha: um "bloop" grave que sobe de 200 para 330 Hz em ~50 ms, com um sopro curto por cima."""
    t = t_(dur)
    a = np.clip(t / 0.004, 0, 1) * np.exp(-t / 0.12)
    f = 330 - 130 * np.exp(-t / 0.018)
    corpo = seno(f, a) + seno(2 * f, a * 0.22)
    sopro = banda(dur, lambda tt: np.full_like(tt, 1800.0), 1.2, lambda tt: np.clip(tt / 0.02, 0, 1) * np.exp(-np.clip(tt - 0.02, 0, None) / 0.05), 41)
    return corpo + sopro / np.abs(sopro).max() * 0.18


def nota(t, t0, f, amp, tau):
    u = t - t0
    a = np.where(u >= 0, np.clip(u / 0.003, 0, 1) * np.exp(-np.clip(u, 0, None) / tau), 0.0) * amp
    return np.sin(2 * np.pi * f * u) * a + np.sin(2 * np.pi * 2 * f * u) * a * 0.12


def sucesso(dur):
    """Duas notas que sobem (dó 6, sol 6), a primeira mais forte: o ataque é a primeira."""
    t = t_(dur)
    return nota(t, 0.0, 1046.5, 1.0, 0.16) + nota(t, 0.085, 1568.0, 0.7, 0.26)


BRILHO_1 = [(0, 5274, 1, .06), (.03, 6645, .7, .07), (.055, 4699, .6, .08), (.085, 7902, .45, .07), (.12, 5920, .35, .09), (.16, 8372, .25, .09)]
BRILHO_2 = [(0, 3951, 1, .07), (.025, 5920, .65, .06), (.05, 4978, .55, .08), (.08, 7040, .4, .07), (.11, 6272, .3, .09)]


def brilho(dur, toques, semente):
    """Toques agudos que se espalham em ~150 ms, decrescendo, com um chiado fino por cima."""
    t = t_(dur)
    x = sum(nota(t, t0, f, a, tau) for t0, f, a, tau in toques)
    ch = banda(dur, lambda tt: np.full_like(tt, 9000.0), 0.6, lambda tt: np.exp(-np.clip(tt, 0, None) / 0.12), semente)
    return x + ch / np.abs(ch).max() * 0.12


def clique(x):
    """O clique do Kenney com um corpo curto por baixo (900 para 600 Hz em 12 ms), para não sumir sob a música."""
    t = t_(len(x) / SR)
    corpo = seno(600 + 300 * np.exp(-t / 0.006), np.clip(t / 0.0005, 0, 1) * np.exp(-t / 0.012))
    return x / np.abs(x).max() + 0.6 * corpo


# ---------------------------------------------------------------- arquivos do Kenney
def ler(caminho):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", caminho, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)


def catraca(x, dur=0.2, pico=0.09):
    """Um pedaço de 200 ms da catraca, com o tique do meio mais forte: acompanha o rolamento do número (lento, rápido, lento)."""
    t = t_(dur)
    return x[: len(t)] * (0.35 + 0.65 * np.exp(-0.5 * ((t - pico) / 0.05) ** 2))


# ---------------------------------------------------------------- medida e acabamento
def kpond(x):
    """Filtro K da BS.1770 a 48 kHz (realce de agudos + passa-alta)."""
    y = lfilter([1.53512485958697, -2.69169618940638, 1.19839281085285], [1, -1.69065929318241, 0.73248077421585], x)
    return lfilter([1.0, -2.0, 1.0], [1, -1.99004745483398, 0.99007225036621], y)


def lufs_curto(x, janela=0.1):
    y = kpond(np.pad(x, (int(janela * SR), int(janela * SR))))
    n = int(janela * SR)
    ms = np.convolve(y * y, np.ones(n) / n, "valid")
    return -0.691 + 10 * np.log10(ms.max() + 1e-12)


def acabar(x):
    """Corta o silêncio (-50 dB do pico na frente e atrás), faz os fades e normaliza (LUFS curto, teto de pico)."""
    x = x - x.mean()
    a = np.abs(x)
    vivo = np.where(a > a.max() * 10 ** (-50 / 20))[0]
    ini, fim = max(0, vivo[0] - int(0.002 * SR)), min(len(x), vivo[-1] + int(0.002 * SR))
    x = x[ini:fim].copy()
    fi, fo = min(int(0.001 * SR), len(x) // 4), min(int(0.03 * SR), len(x) // 3)
    x[:fi] *= np.linspace(0, 1, fi)
    x[len(x) - fo:] *= np.linspace(1, 0, fo)
    g = 10 ** ((ALVO_LUFS - lufs_curto(x)) / 20)
    g = min(g, 10 ** (TETO_DB / 20) / np.abs(x).max())
    return x * g


def ataque(x):
    """Instante (s) do pico de energia em janela de 10 ms: é ele que cai no quadro do evento."""
    n = int(0.01 * SR)
    e = np.convolve(x * x, np.ones(n), "same")
    return float(np.argmax(e) / SR)


def salvar(nome, x):
    caminho = os.path.join(AQUI, nome + ".wav")
    pcm = np.round(np.clip(x, -1, 1) * 32767).astype("<i2")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s16le",
                    "-map_metadata", "-1", "-fflags", "+bitexact", "-flags:a", "+bitexact", caminho], input=pcm.tobytes(), check=True)
    return caminho


def main():
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        sys.exit("uso: python3 fazer_pacote.py <pasta do Kenney Interface Sounds (kenney_interface-sounds do soundcn)>")
    K = lambda n: ler(os.path.join(sys.argv[1], n + ".ogg"))
    gerado = ("gerado aqui (fazer_pacote.py, síntese com semente fixa)", "CC0 (som nosso)")
    kenney = lambda n: (f"{KENNEY}, arquivo {n}.ogg", "CC0 1.0")
    # nome nosso: (tipo, o que é, sinal, (origem, licença))
    pacote = {
        "aparecer-1": ("aparecer", "pop suave, gota que sobe", K("drop_002"), kenney("drop_002")),
        "aparecer-2": ("aparecer", "pop suave, gota mais grave", K("drop_003"), kenney("drop_003")),
        "aparecer-3": ("aparecer", "pop com cauda que sobe", K("drop_004"), kenney("drop_004")),
        "clicar-1": ("clicar", "clique do cursor, com corpo curto", clique(K("click_001")), kenney("click_001, mais um corpo gerado de 12 ms")),
        "tocar-1": ("tocar", "toque curto e seco", K("tick_002"), kenney("tick_002")),
        "tocar-2": ("tocar", "toque de seleção", K("select_001"), kenney("select_001")),
        "digitar-1": ("digitar", "tecla, grave", K("click_002"), kenney("click_002")),
        "digitar-2": ("digitar", "tecla, aguda", K("click_003"), kenney("click_003")),
        "numero-1": ("numero", "catraca de número rolando, 200 ms", catraca(K("scroll_002")), kenney("scroll_002 (200 ms com envelope)")),
        "numero-2": ("numero", "catraca dupla de número rolando, 200 ms", catraca(K("scroll_003")), kenney("scroll_003 (200 ms com envelope)")),
        "brilho-1": ("brilho", "seis toques agudos espalhados", brilho(0.6, BRILHO_1, 77), gerado),
        "brilho-2": ("brilho", "cinco toques agudos, mais graves", brilho(0.6, BRILHO_2, 78), gerado),
        "entrar-1": ("entrar", "whoosh que sobe e corta no pico", whoosh_entrar(0.36, 0.26, 350, 3200, 0.9, 11), gerado),
        "entrar-2": ("entrar", "whoosh que sobe, mais curto e grave", whoosh_entrar(0.30, 0.21, 280, 2400, 1.1, 12), gerado),
        "sair-1": ("sair", "whoosh que desce", whoosh_sair(0.34, 0.04, 3000, 400, 1.0, 21), gerado),
        "sair-2": ("sair", "whoosh que desce, mais curto", whoosh_sair(0.28, 0.03, 2600, 350, 1.0, 22), gerado),
        "morph-1": ("morph", "ar que cresce e assenta num baque grave", morph(0.40, 0.20, 250, 1400, 140, 75, 31), gerado),
        "morph-2": ("morph", "ar que cresce, mais curto e claro", morph(0.34, 0.16, 300, 1700, 120, 70, 32), gerado),
        "ilha-1": ("ilha", "bloop grave que abre, com sopro", ilha(0.7), gerado),
        "sucesso-1": ("sucesso", "duas notas que sobem (dó, sol)", sucesso(1.2), gerado),
    }
    sons = {}
    for nome, (tipo, desc, x, (origem, lic)) in pacote.items():
        y = acabar(np.asarray(x, np.float64))
        salvar(nome, y)
        sons[nome] = {"arquivo": nome + ".wav", "tipo": tipo, "descricao": desc, "origem": origem, "licenca": lic,
                      "duracao": round(len(y) / SR, 4), "ataque": round(ataque(y), 4),
                      "lufs_100ms": round(lufs_curto(y), 1), "pico_db": round(20 * np.log10(np.abs(y).max()), 1)}
        s = sons[nome]
        assert s["pico_db"] <= TETO_DB + 0.05 and 0 <= s["ataque"] < s["duracao"], (nome, s)
        assert s["lufs_100ms"] <= ALVO_LUFS + 0.3, (nome, s)
    tipos = {t: {"ganho_db": g, "versoes": [n for n in sons if sons[n]["tipo"] == t]} for t, g in TIPOS.items()}
    assert all(v["versoes"] for v in tipos.values()) and len(sons) <= 20
    json.dump({"versao": "sons-v1", "taxa": SR, "alvo_lufs_100ms": ALVO_LUFS, "teto_db": TETO_DB, "tipos": tipos, "sons": sons},
              open(os.path.join(AQUI, "sons.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for n, s in sons.items():
        print(f"{n:11s} {s['duracao']:.3f} s  ataque {s['ataque']:.3f} s  {s['lufs_100ms']:6.1f} LUFS(100 ms)  pico {s['pico_db']:5.1f} dB")


if __name__ == "__main__":
    main()
