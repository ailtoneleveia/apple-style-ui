# Encaixe dos eventos dos 3 clones nas batidas e onsets da trilha original.
# Para refazer: copie assets/ref-audio.m4a de cada clone para <dir>/{sat,joi,vos}/assets/, rode
# 'npx hyperframes@0.8.184 beats --json .' em cada pasta (audio com data-timeline-role=music) e depois
# 'python3 batidas.py <dir>'. Saida registrada em batidas.txt.
# Mede se os eventos de cada clone caem nas batidas/onsets da trilha original.
# uso: python3 -I analisa.py <dir beats>
import json, subprocess, sys, numpy as np

B = sys.argv[1]
SR, HOP, N = 22050, 256, 1024

EV = {  # (fps, [(quadro, evento)]) tirados dos BREAKDOWN/LESSONS
    "sat": (30, [(10, "burst vira icone"), (24, "disco cresce"), (31, "icone->cartao"), (55, "zoom-out/terra"),
                 (68, "satelite no arco"), (88, "cartao->tile"), (112, "tile sai"), (123, "tile->pilula (corte)"),
                 (127, "pilula Fire"), (132, "Lost"), (138, "Crime"), (144, "Sickness"), (150, "Vehicle"),
                 (155, "titulo pousa"), (156, "botao End"), (161, "emojis"), (173, "mao do cursor"), (181, "clique/whip"),
                 (199, "rota desenha"), (206, "pico do whip"), (213, "ilha abre"), (229, "pico da ilha"),
                 (241, "relogio rola"), (242, "ambulancia"), (256, "relogio rola 2"), (260, "saida"), (278, "balao")]),
    "joi": (60, [(5, "icone entra"), (60, "flip comeca"), (80, "flip (1a nota)"), (132, "palavras da lista"),
                 (199, "menu escurece"), (209, "botoes"), (259, "risco"), (281, "Get"), (314, "linha encolhe"),
                 (329, "cartao formado"), (354, "punch-in")]),
    "joi6": (60, [(80, "flip"), (132, "lista"), (199, "menu escurece"), (281, "Get"), (329, "cartao"), (354, "punch-in")]),
    "sat_grandes": (30, [(10, "burst"), (31, "icone->cartao"), (88, "cartao->tile"), (123, "tile->pilula"), (127, "Fire"),
                 (155, "titulo"), (181, "clique/whip"), (213, "ilha"), (260, "saida"), (278, "balao")]),
    "vos": (60, [(3, "letras"), (13, "pilula sobe"), (63, "crossfade"), (70, "palavras"), (114, "clique"),
                 (136, "janela"), (150, "ditado"), (170, "icone rosa"), (184, "Slack"), (204, "caret->Send"),
                 (223, "clique Send"), (263, "corte"), (275, "HUD"), (306, "titulo digita"), (352, "Done!"),
                 (377, "placeholder"), (396, "scroll"), (437, "zoom"), (444, "caixa"), (462, "apaga"), (487, "corte fn"),
                 (514, "pan"), (520, "texto"), (566, "ponto solta"), (578, "triangulo"), (588, "legenda")]),
}


def onsets(path):
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(pcm, np.float32)
    nfr = 1 + (len(x) - N) // HOP
    win = np.hanning(N)
    S = np.abs(np.fft.rfft(np.stack([x[i * HOP:i * HOP + N] * win for i in range(nfr)]), axis=1))
    L = np.log1p(100 * S)
    flux = np.maximum(L[1:] - L[:-1], 0).sum(1)
    flux = np.concatenate([[0], flux])
    flux = (flux - np.median(flux)) / (np.percentile(flux, 99) + 1e-9)
    t = (np.arange(nfr) * HOP + N / 2) / SR
    k = 6  # pico local em +-6 hops (~70 ms) e acima de media movel + limiar
    pk = [i for i in range(k, nfr - k) if flux[i] == flux[i - k:i + k + 1].max()
          and flux[i] > flux[max(0, i - 40):i + 10].mean() + 0.08]
    return t[pk], flux[pk]


def nearest(ts, grid):
    g = np.asarray(grid)
    return np.array([t - g[np.argmin(np.abs(g - t))] for t in ts])


out = {}
for k, (fps, ev) in EV.items():
    kk = k.split("_")[0].rstrip("6")
    beats = json.load(open(f"{B}/{kk}/beats/assets/ref-audio.m4a.json"))["beats"]
    bt = np.array([b["time"] for b in beats])
    per = np.median(np.diff(bt))
    # grade regular ajustada (fase por minimos quadrados nas batidas do detector)
    bt = bt[[b["strength"] > 0.1 for b in beats]]  # descarta batidas fracas de borda
    ph = bt[0] + per / (2 * np.pi) * np.angle(np.mean(np.exp(2j * np.pi * (bt - bt[0]) / per)))  # fase circular
    on_t, on_s = onsets(f"{B}/{kk}/assets/ref-audio.m4a")
    st = on_t[on_s > np.percentile(on_s, 50)]; h8 = per / 2
    best = max(((pp, abs(np.mean(np.exp(2j*np.pi*st/pp)))) for pp in np.linspace(h8*0.99, h8*1.01, 81)), key=lambda z: z[1])
    h8 = best[0]; per = 2 * h8
    ph = h8 / (2*np.pi) * np.angle(np.mean(np.exp(2j*np.pi*st/h8)))
    print(f"  grade: colcheia {h8*1000:.1f} ms, fase {ph*1000:.1f} ms, coerencia dos onsets {best[1]:.2f}")
    q = ph + per * np.arange(-2, 40)
    e8 = ph + per / 2 * np.arange(-4, 120)
    strong = on_t[on_s > np.percentile(on_s, 50)]
    ts = np.array([f / fps for f, _ in ev])
    dq, d8, do = nearest(ts, q), nearest(ts, e8), nearest(ts, strong)
    rng = np.random.default_rng(1)
    def hits(tt, grid, tol): return int((np.abs(nearest(tt, grid)) * fps <= tol).sum())
    tol = 1.0 if fps == 30 else 2.0  # 33 ms
    sh2 = rng.uniform(-1, 1, 2000)
    for nome, grid in (("colcheia", e8), ("onset", on_t), ("onset forte", strong)):
        h = hits(ts, grid, tol); nh = np.array([hits(ts + s, grid, tol) for s in sh2])
        print(f"  ACERTOS <=33ms {nome:12s}: {h}/{len(ts)}  acaso {nh.mean():.1f}  p={float((nh >= h).mean()):.3f}")
    # nulo: mesma lista deslocada por um offset aleatorio (preserva espacamento entre eventos)
    sh = rng.uniform(0, per, 4000)
    m8 = np.mean(np.abs(d8)); mo = np.mean(np.abs(do))
    null8 = np.array([np.mean(np.abs(nearest(ts + s, e8))) for s in sh])
    nullo = np.array([np.mean(np.abs(nearest(ts + s, strong))) for s in sh[:800]])
    out[k] = dict(bpm_detector=round(60 / per, 1), n_onsets=int(len(on_t)), n_fortes=int(len(strong)),
                  media_ms_colcheia=round(1000 * m8, 1), nulo_ms_colcheia=round(1000 * null8.mean(), 1),
                  p_colcheia=round(float((null8 <= m8).mean()), 3),
                  media_ms_onset=round(1000 * mo, 1), nulo_ms_onset=round(1000 * nullo.mean(), 1),
                  p_onset=round(float((nullo <= mo).mean()), 3),
                  dentro_1q_colcheia=int((np.abs(d8) * fps <= 1.0).sum()), n=len(ts))
    print(f"== {k} (fim)  {60/per:.1f} BPM  semínima {per*fps:.1f} q  colcheia {per*fps/2:.1f} q  onsets {len(on_t)} (fortes {len(strong)})")
    for (f, name), a, b, c in zip(ev, dq, d8, do):
        print(f"  f{f:4d} {f/fps:6.3f}s {name:22s} batida {a*fps:+5.1f}q  colcheia {b*fps:+5.1f}q  onset {c*fps:+5.1f}q")
    print("  resumo", out[k])
json.dump(out, open(f"{B}/resumo.json", "w"), indent=1)
