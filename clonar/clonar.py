#!/usr/bin/env python3
"""clonar.py: o ciclo de clonagem do Apple Style UI (medir, montar, rodada, final). Roteiro em CLONAR.md.

  clonar.py novo   <pasta> <video> [--link URL] [--autor NOME]   cria o projeto com referencia/ e ORIGEM.md
  clonar.py medir  <pasta> [--eventos f1,f2,...] [--legenda auto|sim|nao]   raio-x do original: RAIOX.md + .apple-style-ui/medidas/
  clonar.py raiox  <video> [--saida DIR] [--eventos ...] [--legenda ...]     só o raio-x, sem projeto
  clonar.py montar <pasta>                                       cria hf/ a partir do modelo e do estilo.js
  clonar.py rodada <pasta> [--previa] [--o-que-mudou TEXTO] [--mascara M [--placa V] [--margem PX] [--elementos a,b]]
                                                                 renderiza, compara e grava rodadas/NN/nota.json; com
                                                                 máscara (placa de vídeo) a nota é a da camada recriada;
                                                                 raster de hf/assets/ sem declaração em RECORTES.md reprova
                                                                 a rodada (aprovada: false) e a nitidez vai na nota
  clonar.py final  <pasta> [--rodada NN] [--so-camada]           saidas/final.mp4 e saidas/lado-a-lado.mp4 (e so-camada.mp4)

Saída: JSON {ok, resumo, proximo: {comando, motivo, precisa_de_voce}} no stdout.
Erro: JSON {ok: false, erro, codigo} no stderr; código 1 = pedido inválido, 2 = falha ao rodar.
Variáveis: ASUI_PY (python com as dependências; padrão .venv/ do kit), ASUI_TMP (brutos de render, fora do
repositório), ASUI_ESTILO (estilo.js), HF_VERSAO (HyperFrames, padrão 0.8.184).
Só usa a biblioteca padrão: as medições rodam no python de ASUI_PY.
"""
import argparse, datetime, hashlib, json, os, re, shlex, shutil, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
SCR = KIT / "scripts"
sys.dont_write_bytecode = True
sys.path.append(str(KIT.parent))
from montar import NOME  # noqa: E402  o nome do produto mora numa constante só, no montador
BASTIDOR = "." + NOME   # a pasta de bastidor de cada clone
# o ambiente Python mora na máquina (~/.apple-style-ui/venv), não na pasta do plugin; .venv/ do kit ainda vale
PY = os.environ.get("ASUI_PY") or next((str(p) for p in (Path.home() / ".apple-style-ui/venv/bin/python", KIT / ".venv/bin/python") if p.exists()), sys.executable)
ESTILO = Path(os.environ.get("ASUI_ESTILO") or KIT.parent / "estilo" / "estilo.js")
ALVO = dict(distancia=0.012, correlacao=0.97, pico_quadros=1)
MAX_RODADAS = 6
EU = "python3 " + shlex.quote(str(KIT / "clonar.py"))  # com aspas: a pasta do plugin pode ter espaço


class Falha(Exception):
    def __init__(self, erro, codigo=2):
        super().__init__(erro); self.erro, self.codigo = erro, codigo


def agora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def guarda(p: Path):
    """nunca sobrescrever: antes de trocar um arquivo, guarda uma cópia com data ao lado"""
    if p.exists():
        d = p.with_name(f"{p.stem}.{datetime.datetime.now():%Y%m%d-%H%M%S}{p.suffix}")
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, d)


def roda(cmd, log=None, ok=(0,), env=None):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=env)
    if log:
        Path(log).parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a") as f:
            f.write(f"$ {' '.join(map(str, cmd))}\n{r.stdout}{r.stderr}\n")
    if r.returncode not in ok:
        raise Falha(f"{Path(str(cmd[1] if str(cmd[0]).endswith(('python', 'python3', 'zsh')) else cmd[0])).name} falhou "
                    f"(código {r.returncode}): {(r.stderr or r.stdout).strip()[-400:]}", 3 if r.returncode == 3 else 2)
    return r


def projeto(pasta, precisa=("referencia/original.mp4",)):
    P = Path(pasta).resolve()
    for x in precisa:
        if not (P / x).exists():
            raise Falha(f"falta {P / x}", 1)
    return P


def registra(P, comando, ok):
    (P / BASTIDOR).mkdir(exist_ok=True)
    with open(P / BASTIDOR / "log.jsonl", "a") as f:
        f.write(json.dumps(dict(quando=agora(), comando=comando, ok=ok), ensure_ascii=False) + "\n")


def probe(v):
    r = roda(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
              "-show_entries", "format=duration", "-of", "json", v])
    j = json.loads(r.stdout); s = j["streams"][0]; a, b = s["r_frame_rate"].split("/")
    return dict(w=s["width"], h=s["height"], fps=round(int(a) / int(b), 3), dur=float(j["format"]["duration"]))


# ------------------------------------------------------------------ comandos
def novo(a):
    P = Path(a.pasta).resolve(); V = Path(a.video).resolve()
    if not V.exists():
        raise Falha(f"vídeo não encontrado: {V}", 1)
    dst = P / "referencia" / "original.mp4"
    sha = hashlib.sha256(V.read_bytes()).hexdigest()
    if dst.exists():
        if hashlib.sha256(dst.read_bytes()).hexdigest() != sha:
            raise Falha(f"{dst} já existe com outro conteúdo; não sobrescrevo", 1)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(V, dst)
    m = probe(dst)
    origem = P / "referencia" / "ORIGEM.md"
    if not origem.exists():
        origem.write_text(f"# Origem do original\n\n- Arquivo: `original.mp4` ({dst.stat().st_size / 1e6:.1f} MB, {m['w']}x{m['h']}, "
                          f"{m['fps']:g} qps, {m['dur']:.2f} s)\n- Link: {a.link or '(preencher)'}\n- Autor: {a.autor or '(preencher)'}\n"
                          f"- Baixado em: {datetime.date.today():%d/%m/%Y}\n- sha256: `{sha}`\n- Uso: estudo interno. Não publicar, "
                          "não redistribuir, não subir para repositório público.\n")
    (P / BASTIDOR).mkdir(exist_ok=True)
    registra(P, "novo", True)
    return dict(resumo=f"projeto criado em {P} com o original ({m['w']}x{m['h']}, {m['fps']:g} qps, {m['dur']:.2f} s)",
                proximo=dict(comando=f"{EU} medir {shlex.quote(str(P))}", motivo="medir o original antes de montar qualquer coisa", precisa_de_voce=False))


def raiox_cmd(video, saida, eventos=None, legenda="auto"):
    cmd = [PY, SCR / "raiox.py", video, saida, "--estilo", ESTILO, "--legenda", legenda]
    if eventos:
        cmd += ["--eventos", eventos]
    roda(cmd, log=Path(saida) / "raiox.log")
    return json.load(open(Path(saida) / "raiox.json"))


def resumo_raiox(r):
    o = r["obturador"].get("obturador")
    pref = sorted({m["mais_parecida"] for m in r["molas"]})
    return (f"{r['duracao_s']:.2f} s, {r['fps']:g} qps, {len(r['cortes_secos'])} corte(s) seco(s), {len(r['trocas_sem_corte'])} troca(s) sem corte, "
            f"{len(r['elementos'])} elemento(s) principal(is), {len(r['molas'])} mola(s) ({', '.join(pref) or 'nenhuma'}), "
            f"obturador {o if o is not None else 'sem medida'}, música: {r['batida'].get('leitura', 'sem áudio')}"
            + (f", texto palavra a palavra ({len(r['palavras'])} palavras com trilha própria)" if r.get("palavras") else ""))


def medir(a):
    P = projeto(a.pasta)
    M = P / BASTIDOR / "medidas"
    r = raiox_cmd(P / "referencia" / "original.mp4", M, a.eventos, a.legenda)
    guarda(P / "RAIOX.md")
    shutil.copy2(M / "RAIOX.md", P / "RAIOX.md")
    registra(P, "medir", True)
    return dict(resumo=f"RAIOX.md: {resumo_raiox(r)}", raiox=str(P / "RAIOX.md"),
                proximo=dict(comando=f"{EU} montar {shlex.quote(str(P))}",
                             motivo=f"antes, escrever FICHA.md cena por cena (folha em {BASTIDOR}/medidas/folha.jpg, quadros em "
                                    f"{BASTIDOR}/medidas/analise/shots/*/burst.png) e medir cada peça quadro a quadro (scripts/medir.py)",
                             precisa_de_voce=False))


def raiox(a):
    saida = Path(a.saida or f"raiox-{Path(a.video).stem}").resolve()
    r = raiox_cmd(Path(a.video).resolve(), saida, a.eventos, a.legenda)
    return dict(resumo=resumo_raiox(r), raiox=str(saida / "RAIOX.md"),
                proximo=dict(comando=f"{EU} novo <pasta> {Path(a.video).resolve()}",
                             motivo="se for clonar, criar o projeto e medir dentro dele", precisa_de_voce=True))


def montar(a):
    P = projeto(a.pasta, ("referencia/original.mp4", f"{BASTIDOR}/medidas/raiox.json"))
    hf = P / "hf"
    if hf.exists():
        raise Falha(f"{hf} já existe; não sobrescrevo (edite a composição ou apague a pasta)", 1)
    if not ESTILO.exists():
        raise Falha(f"estilo.js não encontrado em {ESTILO} (defina ASUI_ESTILO)", 1)
    r = json.load(open(P / BASTIDOR / "medidas" / "raiox.json"))
    fundo = (r["cenas"][0]["paleta"] or ["#ffffff"])[0]
    pronto, hf = hf, P / BASTIDOR / "hf-montando"  # monta ao lado e só troca no fim: falha não deixa hf/ pela metade
    shutil.rmtree(hf, ignore_errors=True)
    shutil.copytree(KIT / "modelo", hf)
    html = (hf / "index.html").read_text()
    for k, v in dict(W=r["largura"], H=r["altura"], FPS=round(r["fps"]), NF=r["quadros"], DUR=round(r["quadros"] / r["fps"], 4),
                     FUNDO=fundo).items():
        html = html.replace("{{" + k + "}}", str(v))
    (hf / "index.html").write_text(html)
    shutil.copy2(ESTILO, hf / "estilo.js")
    tr = P / BASTIDOR / "medidas" / "trilhas.js"  # trilhas medidas antes do montar (trilha_palavra.py) já entram
    if tr.exists():
        shutil.copy2(tr, hf / "trilhas.js")
    (hf / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    sf = Path("/System/Library/Fonts/SFNS.ttf")
    if sf.exists():
        shutil.copyfile(sf, hf / "assets" / "fonts" / "SFNS.ttf")  # uso interno: fonte da Apple, não redistribuir (copyfile: sem as travas do sistema)
    roda(["ffmpeg", "-v", "error", "-y", "-i", P / "referencia" / "original.mp4", "-vn", "-c:a", "aac", "-b:a", "192k",
          hf / "assets" / "audio.m4a"], ok=(0, 1))
    hf.rename(pronto)
    registra(P, "montar", True)
    return dict(resumo=f"hf/ criado ({r['largura']}x{r['altura']}, {round(r['fps'])} qps, {r['quadros']} quadros) com estilo.js, "
                       f"SF Pro {'copiada' if sf.exists() else 'ausente'} e o áudio do original",
                proximo=dict(comando=f"{EU} rodada {P} --o-que-mudou \"montagem inteira a partir da FICHA\"",
                             motivo="montar as cenas da FICHA no draw(t) de hf/index.html (elementos medidos: trilha_palavra.py → "
                                    "hf/trilhas.js, desenhados com encaixa(txt, fonte, amostra(nome, F))) e renderizar a primeira rodada",
                             precisa_de_voce=False))


def le_compare(md):
    s = md.read_text()
    num = lambda pat: float(re.search(pat, s).group(1)) if re.search(pat, s) else None
    lags = [int(m) for m in re.findall(r"^\|[^|]+\|[^|]+\|[^|]+\|[^|]+\| (-?\d+) \|", s, re.M)]
    cortes = re.search(r"within 2 frames: (\d+)/(\d+)", s)
    return dict(distancia=num(r"Mean visual distance: ([\d.]+)"), correlacao=num(r"Motion-curve correlation: ([\d.\-na]+)"),
                movimento=num(r"Total motion vs reference: ([\d.]+)x"), pico_quadros=max((abs(x) for x in lags), default=0),
                cortes=f"{cortes.group(1)}/{cortes.group(2)}" if cortes else "sem cortes no original")


def mascara_cfg(P, a):
    """--mascara vale para esta rodada e fica guardada em .apple-style-ui/mascara.json para as próximas e para o final"""
    cfg = P / BASTIDOR / "mascara.json"
    if a.mascara:
        for x in [a.mascara] + ([a.placa] if a.placa else []):
            if not Path(x).exists():
                raise Falha(f"não encontrado: {x}", 1)
        c = dict(mascara=str(Path(a.mascara).resolve()), placa=str(Path(a.placa).resolve()) if a.placa else None,
                 margem=str(a.margem), elementos=a.elementos)
        guarda(cfg); cfg.write_text(json.dumps(c, ensure_ascii=False, indent=1))
        return c
    return json.load(open(cfg)) if cfg.exists() else None


def rodada(a):
    P = projeto(a.pasta, ("referencia/original.mp4", f"{BASTIDOR}/medidas/analise/analysis.json", "hf/index.html"))
    usados = [int(d.name) for base in (P / "rodadas", P / BASTIDOR / "rodadas") if base.exists() for d in base.iterdir() if d.name.isdigit()]
    nn = max(usados, default=0) + 1  # número de rodada não volta, nem se a pasta for apagada
    NN = f"{nn:02d}"
    B = P / BASTIDOR / "rodadas" / NN; B.mkdir(parents=True); (P / "rodadas" / NN).mkdir(parents=True)
    clone = B / "clone.mp4"; log = B / "render.log"
    orig = P / "referencia" / "original.mp4"
    try:
        roda(["zsh", SCR / ("round.sh" if a.previa else "round_mb.sh"), P / "hf", orig, clone], log=log)
        roda([PY, SCR / "burst.py", clone, B / "analise"], log=log)
        roda([PY, SCR / "compare.py", P / BASTIDOR / "medidas" / "analise", B / "analise", B / "comparacao"], log=log)
        ant = sorted((x for x in (P / BASTIDOR / "rodadas").glob("*/clone.mp4") if x.parent.name != NN), key=lambda x: x.parent.name)
        fd = roda([PY, SCR / "fdsum.py", orig, clone, "--json", B / "fdsum.json"] + (["--prev", ant[-1]] if ant else []), log=log)
        (B / "fdsum.txt").write_text(fd.stdout)
        roda([PY, SCR / "recortes.py", P, "--clone", clone, "--json", B / "recortes.json"], log=log)
        mc = mascara_cfg(P, a)
        if mc:
            roda([PY, SCR / "compara_mascara.py", orig, clone, mc["mascara"], "--margem", mc["margem"], "--json", B / "mascara.json"]
                 + (["--placa", mc["placa"]] if mc.get("placa") else []) + (["--elementos", mc["elementos"]] if mc.get("elementos") else [])
                 + (["--prev", ant[-1]] if ant else []), log=log)
    except Falha as e:
        (P / "rodadas" / NN / "nota.json").write_text(json.dumps(dict(rodada=nn, quando=agora(), erro=e.erro), ensure_ascii=False, indent=1))
        registra(P, f"rodada {NN}", False)
        raise
    n = le_compare(B / "comparacao" / "COMPARE.md")
    fdj = json.load(open(B / "fdsum.json"))
    piores = sorted(fdj["blocos"], key=lambda b: -b["dist"])[:3]
    mj = json.load(open(B / "mascara.json")) if mc else None
    alvo_n = mj or n  # com máscara, quem decide é a camada recriada (a placa de vídeo deixa o quadro inteiro baixo demais)
    atingiu = (alvo_n["distancia"] is not None and alvo_n["distancia"] <= ALVO["distancia"] and alvo_n["correlacao"] is not None
               and alvo_n["correlacao"] >= ALVO["correlacao"] and alvo_n["pico_quadros"] <= ALVO["pico_quadros"])
    if mj:
        mascara = {k: mj[k] for k in ("distancia", "distancia_fina", "correlacao", "movimento", "pico_quadros", "sem_camada", "como")}
        mascara["piores_trechos"] = [dict(quadros=f"f{b['a']}-f{b['b']}", dist=b["dist"], anterior=b.get("anterior"), pior_quadro=b["pior_quadro"])
                                     for b in sorted(mj["blocos"], key=lambda b: -b["dist"])[:3]]
    rc = json.load(open(B / "recortes.json"))  # recorte do original não declarado reprova, mesmo com a nota boa
    nota = dict(rodada=nn, quando=agora(), o_que_mudou=a.o_que_mudou or "", previa=bool(a.previa), **n,
                **(dict(mascara=mascara) if mj else {}),
                fdsum=fdj["media"], fdsum_anterior=fdj["anterior"], quadros=f"{fdj['quadros']}/{fdj['quadros_original']}",
                piores_trechos=[dict(quadros=f"f{b['a']}-f{b['b']}", dist=b["dist"], pior_quadro=b["pior_quadro"]) for b in piores],
                alvo=ALVO, atingiu=bool(atingiu and not a.previa), aprovada=rc["aprovada"],
                **(dict(motivo_reprovada=rc["motivo_reprovada"]) if not rc["aprovada"] else {}),
                nitidez=rc["nitidez"], video=str(clone))
    (P / "rodadas" / NN / "nota.json").write_text(json.dumps(nota, ensure_ascii=False, indent=1))
    for velha in (P / BASTIDOR / "rodadas").iterdir():  # bastidor: só as 2 últimas guardam análise e pares
        if velha.name.isdigit() and int(velha.name) <= nn - 2:
            shutil.rmtree(velha / "analise", ignore_errors=True)
            for png in (velha / "comparacao").glob("pairs_*.png"):
                png.unlink()
    registra(P, f"rodada {NN}", True)
    p0 = piores[0]
    res = (f"rodada {NN}{' (prévia)' if a.previa else ''}: distância {n['distancia']}, correlação {n['correlacao']}, "
           f"pico {n['pico_quadros']} q, movimento {n['movimento']}x, fdsum {fdj['media']}"
           + (f" (antes {fdj['anterior']})" if fdj["anterior"] is not None else "") + f"; pior trecho f{p0['a']}-f{p0['b']} ({p0['dist']})")
    if mj:
        pm = sorted(mj["blocos"], key=lambda b: -b["dist"])[0]
        p0 = dict(a=pm["a"], b=pm["b"], pior_quadro=pm["pior_quadro"])
        res += (f"; NA MÁSCARA (camada): distância {mj['distancia']} (fina {mj['distancia_fina']}), correlação {mj['correlacao']}, "
                f"pico {mj['pico_quadros']} q" + (f", sem camada {mj['sem_camada']['distancia']}" if mj.get("sem_camada") else "")
                + f"; pior trecho da camada f{pm['a']}-f{pm['b']} ({pm['dist']})")
    nt = rc["nitidez"]
    if nt:
        res += f"; nitidez {nt['razao']}x a do original" + (" (BEM MAIS BORRADO que o original)" if nt["borrado"] else "")
    if not rc["aprovada"]:
        res += f"; REPROVADA: {rc['motivo_reprovada']}"
        prox = dict(comando=f"{EU} rodada {shlex.quote(str(P))} --o-que-mudou \"peças recriadas em HTML, CSS ou SVG\"",
                    motivo="recriar em HTML, CSS ou SVG, com a fonte e as cores medidas, todo elemento de interface que hoje é "
                           "recorte do original; foto ou vídeo filmado de verdade se declara em hf/assets/RECORTES.md "
                           f"(tipo foto, video ou fundo, e o motivo). Detalhes em {BASTIDOR}/rodadas/{NN}/recortes.json",
                    precisa_de_voce=False)
    elif nota["atingiu"]:
        prox = dict(comando=f"{EU} final {shlex.quote(str(P))}",
                    motivo="alvo batido: rode final agora e entregue. Não polir depois do alvo: só se o usuário pedir",
                    precisa_de_voce=False)
    elif nn >= MAX_RODADAS and not a.previa:
        prox = dict(comando=f"{EU} final {P}", motivo=f"{MAX_RODADAS} rodadas: fechar com a melhor e anotar em LICOES.md o que ainda difere",
                    precisa_de_voce=False)
    else:
        prox = dict(comando=f"{EU} rodada {P} --o-que-mudou \"...\"",
                    motivo=f"corrigir primeiro f{p0['a']}-f{p0['b']} (pior quadro f{p0['pior_quadro']}): veja "
                           f"python3 scripts/diffview.py {orig} {clone} <saida.png> {p0['pior_quadro']} e {BASTIDOR}/rodadas/{NN}/fdsum.txt; "
                           "uma hipótese por região", precisa_de_voce=False)
    return dict(resumo=res, nota=str(P / "rodadas" / NN / "nota.json"), proximo=prox)


def final(a):
    P = projeto(a.pasta)
    notas = []
    for d in sorted((P / "rodadas").glob("*/nota.json")):
        n = json.load(open(d))
        if n.get("distancia") is not None and not n.get("previa") and n.get("aprovada", True):
            notas.append(n)
    if a.rodada:
        notas = [n for n in notas if n["rodada"] == int(a.rodada)]
    if not notas:
        raise Falha("nenhuma rodada aprovada com nota (rode clonar.py rodada; rodada com recorte não declarado não fecha)", 1)
    chave = (lambda n: (n["mascara"]["distancia_fina"], -n["rodada"])) if all("mascara" in n for n in notas) else (lambda n: (n["fdsum"], -n["rodada"]))
    best = min(notas, key=chave) if not a.rodada else notas[0]
    NN = f"{best['rodada']:02d}"
    S = P / "saidas"; S.mkdir(exist_ok=True)
    guarda(S / "final.mp4"); shutil.copy2(P / BASTIDOR / "rodadas" / NN / "clone.mp4", S / "final.mp4")
    guarda(S / "lado-a-lado.mp4")
    roda([PY, SCR / "sbs.py", P / "referencia" / "original.mp4", S / "final.mp4", S / "lado-a-lado.mp4"], log=P / BASTIDOR / "final.log")
    if a.so_camada:  # a mesma composição sem a placa de fundo (camada.js), num espelho de hf/ fora do projeto
        esp = Path(os.environ.get("ASUI_TMP") or Path(os.environ.get("TMPDIR", "/tmp")) / f"{NOME}-render") / f"hf-camada-{os.getpid()}"
        esp.mkdir(parents=True)
        try:
            for x in (P / "hf").iterdir():
                if x.name not in ("camada.js", "mb.js", "node_modules"):
                    (esp / x.name).symlink_to(x)
            (esp / "mb.js").write_text("window.MB_SHIFT = 0;\n")
            (esp / "camada.js").write_text("window.SO_CAMADA = true;\n")
            guarda(S / "so-camada.mp4")
            roda(["zsh", SCR / "round_mb.sh", esp, P / "referencia" / "original.mp4", S / "so-camada.mp4"], log=P / BASTIDOR / "final.log")
        finally:
            shutil.rmtree(esp, ignore_errors=True)
    registra(P, f"final {NN}", True)
    mb = best.get("mascara")
    return dict(resumo=f"saidas/final.mp4 e saidas/lado-a-lado.mp4{' e saidas/so-camada.mp4' if a.so_camada else ''} da rodada {NN} "
                       f"(distância {best['distancia']}, correlação {best['correlacao']}, pico {best['pico_quadros']} q, fdsum {best['fdsum']}"
                       + (f"; na máscara: distância {mb['distancia']}, fina {mb['distancia_fina']}, correlação {mb['correlacao']}" if mb else "") + ")",
                proximo=dict(comando=f"abrir {S / 'lado-a-lado.mp4'}",
                             motivo="conferir no olho e escrever LICOES.md (o que funcionou, o que ainda difere)", precisa_de_voce=True))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("novo"); s.add_argument("pasta"); s.add_argument("video"); s.add_argument("--link"); s.add_argument("--autor")
    s = sub.add_parser("medir"); s.add_argument("pasta"); s.add_argument("--eventos"); s.add_argument("--legenda", default="auto", choices=("auto", "sim", "nao"))
    s = sub.add_parser("raiox"); s.add_argument("video"); s.add_argument("--saida"); s.add_argument("--eventos")
    s.add_argument("--legenda", default="auto", choices=("auto", "sim", "nao"))
    s = sub.add_parser("montar"); s.add_argument("pasta")
    s = sub.add_parser("rodada"); s.add_argument("pasta"); s.add_argument("--previa", action="store_true"); s.add_argument("--o-que-mudou")
    s.add_argument("--mascara"); s.add_argument("--placa"); s.add_argument("--margem", type=float, default=12); s.add_argument("--elementos")
    s = sub.add_parser("final"); s.add_argument("pasta"); s.add_argument("--rodada"); s.add_argument("--so-camada", action="store_true")
    try:
        a = ap.parse_args()
    except SystemExit as e:
        if e.code:
            print(json.dumps(dict(ok=False, erro="argumentos inválidos (veja clonar.py -h)", codigo=1), ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        raise
    try:
        out = dict(novo=novo, medir=medir, raiox=raiox, montar=montar, rodada=rodada, final=final)[a.cmd](a)
    except Falha as e:
        print(json.dumps(dict(ok=False, erro=e.erro, codigo=1 if e.codigo == 1 else 2), ensure_ascii=False), file=sys.stderr)
        sys.exit(1 if e.codigo == 1 else 2)
    print(json.dumps(dict(ok=True, **out), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
