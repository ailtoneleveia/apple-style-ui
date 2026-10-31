#!/usr/bin/env python3
"""montar.py: o molde "final output" aplicado ao vídeo de uma pessoa falando.

  python3 moldes/fala-destaque/montar.py --pessoa video.mp4 --saida saidas/x.mp4 [--voz fala.wav] [--destaques "talent,habit"]
                          [--versao versao.json] [--cor-destaque "#ffffff"] [--fonte instrument|playfair|dmserif]
                          [--sombra nenhuma|medida] [--altura 1108] [--idioma auto|pt|en] [--transcricao palavras.json] [--previa]

1. A fala vem do próprio vídeo (ou de --voz, quando o vídeo não tem som). Transcrição palavra a palavra pelo kit:
   `clonar/scripts/transcrever.py` (Groq whisper-large-v3 com GROQ_API_KEY; sem chave, o `hyperframes transcribe`
   local: small.en para `--idioma en`, large-v3 para os outros e para auto). A lista fica no bastidor e é
   reaproveitada; `--transcricao palavras.json` usa uma lista pronta (o `caso.py aplicar` passa assim).
2. As palavras viram frases (campo `frases`): corta no ponto final, na vírgula de frase com 3 palavras ou mais, na pausa
   maior que 0,45 s e em 7 palavras. O tempo do whisper erra até ~0,5 s: cada frase com um trecho de fala (silencedetect)
   começando a menos de 0,7 s é esticada para dentro dele. Em cada frase, a palavra em destaque é a de --destaques (todas as que estiverem na
   lista) ou, sem lista, a regra do kit (`clonar/scripts/destaque.py`: a mais longa fora das palavras vazias).
3. Monta uma cópia do molde no bastidor (<pasta da saída>/.apple-style-ui/molde-<nome>/): o vídeo da pessoa em
   1080x1920 e 30 qps (corte central) como assets/pessoa.mp4, a duração certa e os campos gravados como padrões.
   A altura do texto de cada frase (campo `alturas`) sai do rosto (rosto.swift, Vision do macOS; ver alturas()).
   A versão resolvida fica em <nome>.versao.json ao lado da saída. O bastidor é o do projeto: se a saída está em
   <projeto>/saidas/, ele é <projeto>/.apple-style-ui/ (saidas/ pode ser apagada sem perder nada).
4. Renderiza com o motion blur do kit (`clonar/scripts/round_mb.sh`: 240 qps, tmix, um worker, H.264 -refs 4
   -level:v 5.1) e põe o áudio da fala. Para se faltar disco (menos de 5 GB livres antes do render).
Saída JSON {ok, resumo, proximo: {comando, motivo, precisa_de_voce}}; erro no stderr {ok: false, erro, codigo}.
"""
import argparse, hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
KIT = Path(os.environ.get("ASUI_KIT") or AQUI.parents[1] / "clonar")
sys.path.insert(0, str(KIT / "scripts"))
import destaque  # noqa: E402  a regra do destaque mora no kit (uma só para todos os moldes)


def ok(resumo, **extra):
    print(json.dumps(dict(ok=True, resumo=resumo, **extra), ensure_ascii=False, indent=1))


def falha(erro, codigo=1):
    print(json.dumps(dict(ok=False, erro=erro, codigo=codigo), ensure_ascii=False), file=sys.stderr); sys.exit(codigo)


def roda(cmd, **kw):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode:
        falha(f"{Path(str(cmd[0])).name} falhou: {(r.stderr or r.stdout).strip()[-500:]}", 2)
    return r


def probe(v):
    j = json.loads(roda(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries",
                         "format=duration", "-of", "json", v]).stdout)
    vs = [s for s in j["streams"] if s["codec_type"] == "video"]
    return dict(dur=float(j["format"]["duration"]), w=vs[0]["width"] if vs else 0, h=vs[0]["height"] if vs else 0,
                audio=any(s["codec_type"] == "audio" for s in j["streams"]))


def le_palavras(tj):
    j = json.load(open(tj)); ws = j if isinstance(j, list) else j.get("words", [])
    return [dict(t=w["text"].strip(), ini=float(w["start"]), fim=float(w["end"])) for w in ws if w["text"].strip()]


def transcreve(fala, bastidor, idioma):
    sha = hashlib.sha256(Path(fala).read_bytes()).hexdigest()[:12]
    tj = bastidor / f"transcricao-{sha}-{idioma}.json"
    if not tj.exists():
        roda([sys.executable, KIT / "scripts" / "transcrever.py", fala, "--idioma", idioma, "--saida", tj])
    return le_palavras(tj)


def trechos_de_fala(fala):
    """trechos com som (silencedetect a -35 dB, pausa de 0,12 s ou mais): [(início, fim), ...]"""
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(fala), "-af", "silencedetect=noise=-35dB:d=0.12", "-f", "null", "-"],
                       capture_output=True, text=True)
    marcas = re.findall(r"silence_(start|end): ([0-9.]+)", r.stderr)
    dur = probe(fala)["dur"]; out, ini = [], 0.0
    for tipo, v in marcas:
        v = float(v)
        if tipo == "start":
            if v - ini > 0.05:
                out.append((ini, v))
        else:
            ini = v
    if dur - ini > 0.05 and (not marcas or marcas[-1][0] == "end"):
        out.append((ini, dur))
    return out


def alinha(grupos_ws, trechos):
    """o whisper erra o tempo da palavra em até ~0,5 s (na voz de teste, a frase 4 vinha 0,58 s cedo). Cada frase que
    tem um trecho de fala começando a menos de 0,7 s dela, e de duração parecida, é esticada linearmente para dentro dele;
    o resto fica (na fala corrida da referência, sem pausa, nada muda)."""
    for g in grupos_ws:
        a, b = g[0]["ini"], g[-1]["fim"]
        cand = [t for t in trechos if abs(t[0] - a) < 0.7]
        if not cand or b - a < 0.05:
            continue
        s, e = min(cand, key=lambda t: abs(t[0] - a))
        if not 0.6 * (b - a) <= e - s <= 1.6 * (b - a) + 0.3:  # trecho que não é desta frase (fala corrida, música)
            continue
        for w in g:
            w["ini"] = s + (w["ini"] - a) * (e - s) / (b - a); w["fim"] = s + (w["fim"] - a) * (e - s) / (b - a)


def limpa(t):
    return re.sub(r"[.,!?;:\"“”]+", "", t)


def frases(palavras, destaques, trechos=None):
    grupos, g = [], []
    for i, w in enumerate(palavras):
        g.append(w)
        prox = palavras[i + 1] if i + 1 < len(palavras) else None
        fim_frase = re.search(r"[.!?]$", w["t"]) or (w["t"].endswith(",") and len(g) >= 3)
        if not prox or fim_frase or prox["ini"] - w["fim"] > 0.45 or len(g) >= 7:
            grupos.append(g); g = []
    if trechos:
        alinha(grupos, trechos)
    alvo = {limpa(d).lower() for d in destaques}
    out = []
    for g in grupos:
        txt = [limpa(w["t"]) for w in g]
        if alvo:
            dest = [t.lower() in alvo for t in txt]
        else:
            k = destaque.escolhe(txt)
            dest = [i == k for i in range(len(txt))]
        out.append([[t, round(w["ini"], 3), int(d)] for t, w, d in zip(txt, g, dest) if t])
    return out


def escolhe_escura(grupos):
    """A frase da cena escura, ou None: no máximo uma por vídeo, só com 3 frases ou mais. Candidatas: as do meio (nem a
    primeira, que dá o padrão, nem a última, que borra no fim), com destaque e pelo menos 2 palavras antes dele (a caixa
    alta precisa de uma linha em cima). Ganha a de maior pausa antes: do início da última palavra da frase anterior ao
    início da frase (é onde quem fala respira para dar ênfase). No clone, escolhe a frase 3, a mesma do original."""
    cands = [(g[0][1] - grupos[i - 1][-1][1], -i, i) for i, g in enumerate(grupos)
             if 0 < i < len(grupos) - 1 and g and grupos[i - 1] and any(p[2] for p in g) and [p[2] for p in g].index(1) >= 2]
    return max(cands)[2] if cands else None


SEGURO = (220, 1632)  # o bloco fica entre o cabeçalho do Reels (~11 % de cima) e a legenda e os botões (15 % de baixo)
BLOCO = (180, 80)     # o bloco acima e abaixo da linha de base do destaque (a linha de cima sobe nos picos da serifa e,
                      # na cena escura, desce 44 px; a de baixo tem descendentes)
MARGEM = 30


def rostos(video):
    """os rostos do vídeo a cada 0,2 s, pelo Vision do macOS (rosto.swift, local); [] sem o swift"""
    if not shutil.which("swift"):
        return []
    r = subprocess.run(["swift", str(AQUI / "rosto.swift"), str(video), "0.2"], capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        return []


def alturas(grupos, amostras, dur):
    """A linha de base do destaque em cada frase, pelo rosto: o bloco nunca cobre de olhos a boca. Ordem: logo abaixo do
    queixo, acima da cabeça, abaixo da boca, acima dos olhos, o mais baixo da área segura, pelo rosto somado dos quadros
    da frase. Uma altura por frase (o texto não pula dentro dela). Se essa altura cobre o rosto em algum quadro (um corte
    no meio da frase), vale a altura da área segura que deixa livres mais quadros, a mais perto dela. Frase com rosto em
    menos da metade dos quadros: None (vale a `altura`). Diferença menor que 60 px da frase anterior: fica a anterior."""
    def regra(fs):
        cab = min(r["caixa"][1] - 0.4 * (r["caixa"][3] - r["caixa"][1]) for r in fs)  # o cabelo passa da caixa do Vision
        olhos, boca, queixo = min(r["olhos"] for r in fs), max(r["boca"] for r in fs), max(r["queixo"] for r in fs)
        for y in (queixo + MARGEM + BLOCO[0], cab - MARGEM - BLOCO[1], boca + MARGEM + BLOCO[0], olhos - MARGEM - BLOCO[1]):
            if cabe(y):
                return round(y)
        return SEGURO[1] - BLOCO[1]
    cabe = lambda y: SEGURO[0] <= y - BLOCO[0] and y + BLOCO[1] <= SEGURO[1]
    livre = lambda y, r: y + BLOCO[1] + 10 < r["olhos"] or y - BLOCO[0] - 10 > r["boca"]
    out, ant = [], None
    for gi, g in enumerate(grupos):
        a = min(p[1] for p in g) - 0.08
        b = min(p[1] for p in grupos[gi + 1]) - 0.08 if gi + 1 < len(grupos) else dur
        # a amostra de antes do início conta (passo de 0,2 s): um corte logo antes da frase não passa sem ser visto
        am = [s for s in amostras if a - 0.2 < s["t"] < b] or sorted(amostras, key=lambda s: abs(s["t"] - (a + b) / 2))[:1]
        fs = [max(s["rostos"], key=lambda r: (r["caixa"][2] - r["caixa"][0]) * (r["caixa"][3] - r["caixa"][1]))
              for s in am if s["rostos"]]
        if not fs or len(fs) < len(am) / 2:
            out.append(None); ant = None; continue
        geral = regra(fs)
        nota = lambda y: sum(livre(y, f) for f in fs)
        y = max([geral, *range(SEGURO[0] + BLOCO[0], SEGURO[1] - BLOCO[1] + 1, 10)], key=lambda y: (nota(y), -abs(y - geral)))
        if ant is not None and abs(y - ant) < 60 and cabe(ant) and nota(ant) >= nota(y):
            y = ant
        out.append(y); ant = y
    return out


CARREGADO = 3.3  # média de bordas (edgedetect 0,15/0,35) na faixa do texto: fundo da pessoa 1,0 a 2,7 (teste cego C e
                 # Pexels), tela gravada com código 3,9 a 10,8 (tela dividida do C). Acima disso a frase ganha a faixa escura


def faixas(entrada, grupos, alts, altura, dur, cenas):
    """1 na frase cujo fundo atrás do texto é carregado (tela gravada, código, letreiro): ali o texto branco some e o
    molde põe a faixa escura suave atrás dele. `entrada`: os argumentos de entrada do ffmpeg (o vídeo, ou um lavfi no teste)."""
    out = []
    for gi, g in enumerate(grupos):
        a = min(p[1] for p in g); b = min(p[1] for p in grupos[gi + 1]) if gi + 1 < len(grupos) else dur
        if cenas.get(str(gi)) == "escura":
            out.append(0); continue
        y = (alts[gi] if gi < len(alts) and alts[gi] else altura)
        y0 = max(0, int(y - BLOCO[0] - 30)); h = min(1920 - y0, BLOCO[0] + BLOCO[1] + 60)
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, a):.2f}", "-t", f"{max(0.25, b - a):.2f}", *entrada, "-vf",
                            f"fps=4,crop=840:{h}:120:{y0},edgedetect=low=0.15:high=0.35,signalstats,metadata=print:file=-",
                            "-f", "null", "-"], capture_output=True, text=True).stdout
        e = sorted(float(x) for x in re.findall(r"YAVG=([\d.]+)", r))
        out.append(int(bool(e) and e[len(e) // 2] > CARREGADO))
    return out


def autoteste():
    clone = json.loads(json.loads(re.search(r'"id": "frases".*?"default": ("(?:[^"\\]|\\.)*")', (AQUI / "index.html").read_text())
                                  .group(1)).replace("&apos;", "'"))
    assert escolhe_escura(clone) == 2, escolhe_escura(clone)  # a frase do neon no original
    assert escolhe_escura(clone[:2]) is None  # menos de 3 frases: sem cena escura
    sem = [[["a", 0, 0], ["b", .1, 1]], [["c", 1, 0], ["d", 1.1, 0], ["e", 1.2, 1]], [["f", 3, 0], ["g", 3.1, 0]], [["h", 4, 1]]]
    assert escolhe_escura(sem) == 1  # a frase 2 não tem destaque; a 1 tem só 1 palavra antes dele e é a primeira
    # altura pelo rosto (rostos sintéticos nas medidas do Vision no teste cego C): close, tela dividida, rosto enorme, nenhum
    R = lambda y0, y1, olhos, boca, queixo: dict(caixa=[300, y0, 800, y1], olhos=olhos, boca=boca, queixo=queixo)
    close, baixo, enorme = R(470, 1000, 520, 870, 1000), R(1150, 1550, 1180, 1450, 1560), R(200, 1500, 400, 1200, 1500)
    um = lambda rs: alturas([[["a", 0.08, 1]]], [dict(t=k / 5, rostos=rs(k)) for k in range(6)], 1.2)[0]
    al = [um(lambda k: [r]) for r in (close, baixo, enorme)] + [um(lambda k: [])]
    assert al == [1210, 880, 1410, None], al  # abaixo do queixo, acima da cabeça, abaixo da boca, sem rosto
    corte = um(lambda k: [close] if k == 0 else [baixo])  # corte logo depois do início (teste cego C, f211-f213)
    for y, rs in zip(al[:3] + [corte, corte], ([close], [baixo], [enorme], [close], [baixo])):
        assert all(y + BLOCO[1] < r["olhos"] or y - BLOCO[0] > r["boca"] for r in rs), (y, rs)  # nunca de olhos a boca
    gs = [[["a", 0, 1]], [["b", 1, 1]]]  # duas frases com o mesmo rosto mexendo 40 px: a altura não pula
    assert len(set(alturas(gs, [dict(t=k / 5, rostos=[R(470 + 4 * k, 1000 + 4 * k, 520, 870, 1000 + 4 * k)]) for k in range(10)], 2))) == 1
    # faixa: fundo liso não liga, fundo carregado (ruído) liga, cena escura nunca
    lav = lambda f: ["-f", "lavfi", "-i", f"color=c=0x404850:size=1080x1920:rate=30:duration=1{f}"]
    assert faixas(lav(""), [[["a", 0, 1]]], [1108], 1108, 1, {}) == [0]
    assert faixas(lav(",noise=alls=60:allf=t"), [[["a", 0, 1]], [["b", 0.5, 1]]], [], 1108, 1, {"1": "escura"}) == [1, 0]


def main():
    autoteste()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pessoa", required=True); ap.add_argument("--saida", required=True); ap.add_argument("--voz")
    ap.add_argument("--destaques", default=""); ap.add_argument("--versao"); ap.add_argument("--cor-destaque")
    ap.add_argument("--fonte", choices=("instrument", "playfair", "dmserif")); ap.add_argument("--sombra", choices=("nenhuma", "medida"))
    ap.add_argument("--altura", type=float)
    ap.add_argument("--idioma", default="auto"); ap.add_argument("--previa", action="store_true")
    ap.add_argument("--transcricao", help="lista de palavras pronta ([{text, start, end}]), no lugar de transcrever")
    a = ap.parse_args()
    pessoa, saida = Path(a.pessoa).resolve(), Path(a.saida).resolve()
    if not pessoa.exists():
        falha(f"vídeo da pessoa não encontrado: {pessoa}")
    pp = probe(pessoa)
    fala = Path(a.voz).resolve() if a.voz else pessoa
    if not fala.exists() or not probe(fala)["audio"]:
        falha("sem fala: o vídeo não tem áudio e não veio --voz (o texto em destaque sai da transcrição da fala)")
    nome = saida.stem
    bastidor = (saida.parent.parent if saida.parent.name == "saidas" else saida.parent) / ".apple-style-ui"
    bastidor.mkdir(parents=True, exist_ok=True); saida.parent.mkdir(parents=True, exist_ok=True)
    dur = min(pp["dur"], probe(fala)["dur"])

    decl = json.loads(re.search(r"data-composition-variables='(.*?)'", (AQUI / "index.html").read_text(), re.S).group(1)
                      .replace("&apos;", "'"))
    valores = {d["id"]: d["default"] for d in decl}
    regra = not a.versao  # frases novas: a cena escura sai da regra (escolhe_escura); a versão que traz `cenas` manda
    if a.versao:
        vv = json.load(open(a.versao)); valores.update(vv)
        regra = "frases" in vv and "cenas" not in vv  # versão antiga, sem o campo: as frases dela não são as do clone
    else:
        ws = le_palavras(a.transcricao) if a.transcricao else transcreve(fala, bastidor, a.idioma)
        if not ws:
            falha("a transcrição não achou nenhuma palavra", 2)
        valores["frases"] = json.dumps(frases(ws, [d for d in a.destaques.split(",") if d.strip()], trechos_de_fala(fala)),
                                       ensure_ascii=False)
    if regra:
        i = escolhe_escura(json.loads(valores["frases"]))
        valores["cenas"] = json.dumps({} if i is None else {str(i): "escura"})
    for k, v in (("cor_destaque", a.cor_destaque), ("fonte_destaque", a.fonte), ("sombra", a.sombra), ("altura", a.altura)):
        if v is not None:
            valores[k] = v
    valores["video_pessoa"] = "assets/pessoa.mp4"

    # cópia do molde com a pessoa, a duração e os campos como padrões
    w = bastidor / f"molde-{nome}"; shutil.rmtree(w, ignore_errors=True)
    shutil.copytree(AQUI, w, ignore=shutil.ignore_patterns("exemplo", "versoes", "montar*.py", "*.md", ".hyperframes", "renders",
                                                       "*.20[0-9][0-9][0-9][0-9][0-9][0-9]-*"))  # cópias com data
    sf = Path("/System/Library/Fonts/SFNS.ttf")
    if sf.exists():
        shutil.copyfile(sf, w / "assets" / "fonts" / "SFNS.ttf")  # uso interno: fonte da Apple, não redistribuir
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"
    roda(["ffmpeg", "-v", "error", "-y", "-i", pessoa, "-t", f"{dur:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-crf", "14",
          "-pix_fmt", "yuv420p", w / "assets" / "pessoa.mp4"])
    orig = bastidor / f"{nome}-pessoa-com-fala.mp4"  # o que o round_mb.sh usa para o qps e o áudio
    roda(["ffmpeg", "-v", "error", "-y", "-i", w / "assets" / "pessoa.mp4", "-i", fala, "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", orig])
    nf = int(round(dur * 30)); d_ = f"{nf / 30:.4f}"
    # a altura de cada frase vem do rosto, salvo `--altura` (fixa) ou `alturas` numa --versao
    aviso = None
    if a.altura is not None:
        valores["alturas"] = "[]"
    elif not (a.versao and "alturas" in vv):
        am = rostos(w / "assets" / "pessoa.mp4")
        valores["alturas"] = json.dumps(alturas(json.loads(valores["frases"]), am, nf / 30))
        aviso = None if am else "sem detector de rosto (o swift do macOS): a altura ficou a fixa"
    if not (a.versao and "faixas" in vv):
        valores["faixas"] = json.dumps(faixas(["-i", str(w / "assets" / "pessoa.mp4")], json.loads(valores["frases"]),
                                              json.loads(valores["alturas"] or "[]"), float(valores["altura"]), nf / 30,
                                              json.loads(valores["cenas"] or "{}")))
    (saida.parent / f"{nome}.versao.json").write_text(json.dumps(valores, ensure_ascii=False, indent=1))
    html = (w / "index.html").read_text()
    html = re.sub(r'data-duration="[0-9.]+"', f'data-duration="{d_}"', html)
    for d in decl:
        d["default"] = valores[d["id"]]
    html = re.sub(r"data-composition-variables='.*?'", "data-composition-variables='" +
                  json.dumps(decl, ensure_ascii=False).replace("'", "&apos;") + "'", html, count=1, flags=re.S)
    (w / "index.html").write_text(html)

    livre = shutil.disk_usage(w).free / 1e9
    if livre < 5:
        falha(f"parei antes do render: só {livre:.1f} GB livres (mínimo 5 GB)", 3)
    saida.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["zsh", KIT / "scripts" / "round_mb.sh", w, orig, saida] + (["1"] if a.previa else [])
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    (bastidor / f"{nome}-render.log").write_text(r.stdout + r.stderr)
    if r.returncode or not saida.exists():
        falha(f"o render falhou (log em {bastidor / (nome + '-render.log')}): {(r.stderr or r.stdout).strip()[-400:]}", 2)
    fr = json.loads(valores["frases"])
    ok(f"{saida.name}: {nf} quadros, {len(fr)} frase(s), destaques: {', '.join(p[0] for g in fr for p in g if p[2]) or 'nenhum'}"
       f"; alturas pelo rosto: {valores.get('alturas', '[]')}" + (f"; aviso: {aviso}" if aviso else ""),
       saida=str(saida), versao=str(saida.parent / f"{nome}.versao.json"),
       proximo=dict(comando=f"abrir {saida}", motivo="conferir no olho; para trocar palavra, tempo ou destaque, edite a versão "
                    "e rode de novo com --versao", precisa_de_voce=True))


if __name__ == "__main__":
    main()
