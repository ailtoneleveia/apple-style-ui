#!/usr/bin/env python3
"""caso.py: o caso central, "vídeo igual a esta referência", do link ao vídeo da pessoa editado.

  python3 caso.py referencia <link ou arquivo> [--pasta caso-<nome>] [--demonstrativo auto|sim|nao]
  python3 caso.py aplicar <molde> --video <gravação> [--saida <projeto>/saidas/<nome>.mp4] [--idioma auto|pt|en]
                          [--destaques destaques.txt] [--voz fala.wav] [--previa] [-- opções do molde]

Os cinco passos (CLONAR.md, "Caminho do comando de entrada"):
  1. baixar a referência ............ `referencia`
  2. tirar o vídeo de dentro ........ `referencia` (demonstrativo: cartão, tela ou celular; extrair_tela.py)
  3. clonar o trecho ................ trabalho de agente (clonar.py novo/medir/montar/rodada/final)
  4. virar molde .................... trabalho de agente (um projeto com campos e um montar.py ao lado)
  5. aplicar à pessoa ............... `aplicar`: transcreve, escolhe o destaque, monta e renderiza com motion blur
`referencia` termina dizendo o comando do passo 3; o passo 4 entrega a pasta do molde que `aplicar` recebe.

Contrato do molde (o que `aplicar` usa): uma pasta com `index.html` e `montar.py`, e o montar.py com
`--pessoa`, `--saida`, `--versao` (JSON com os campos), `--voz` e `--previa`, e as funções `le_palavras(arquivo)`,
`trechos_de_fala(fala)` e `frases(palavras, destaques, trechos)` (grupos de [texto, início, destaque 0/1]).

Pasta por projeto: `<projeto>/saidas/` (o que a pessoa abre), `<projeto>/destaques.txt` (a escolha do destaque, que ela
edita) e `<projeto>/.apple-style-ui/` (transcrição, versão, logs). Nada é sobrescrito: uma saída que já existe ganha
-2, -3. Cada passo é retomável: a referência baixada, o vídeo de dentro e a transcrição são reaproveitados.

O destaque: a regra do kit (`scripts/destaque.py`: a palavra mais longa da frase fora das palavras vazias de português
e inglês). O `destaques.txt` tem uma linha por frase com as palavras em destaque entre colchetes; mude os colchetes
(`escura:` no começo da linha marca a cena escura, nos moldes que têm o campo `cenas`; a primeira vez, a
`escolhe_escura()` do molde já marca uma) e rode o mesmo comando.
Saída JSON {ok, resumo, proximo: {comando, motivo, precisa_de_voce}}; erro no stderr {ok: false, erro, codigo}.
"""
import argparse, datetime, hashlib, importlib.util, json, os, re, shlex, shutil, subprocess, sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
SCR = KIT / "scripts"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCR))
from saida import falha, ok  # noqa: E402

BASTIDOR = ".apple-style-ui"
# o ambiente Python mora na máquina (~/.apple-style-ui/venv), não na pasta do plugin; .venv/ do kit ainda vale
PY = os.environ.get("ASUI_PY") or next((str(p) for p in (Path.home() / ".apple-style-ui/venv/bin/python", KIT / ".venv/bin/python") if p.exists()), sys.executable)
BIBLIOTECA = Path(os.environ.get("ASUI_DADOS") or Path.home() / ".apple-style-ui" / "biblioteca") / "videos"
EU = shlex.join(["python3", str(KIT / "caso.py")])


def roda(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


def json_de(r):
    """o JSON padrão de uma ferramenta do kit (stdout no ok, stderr na falha)"""
    for txt in (r.stdout, r.stderr):
        i = txt.find("{")
        if i >= 0:
            try:
                return json.loads(txt[i:])
            except json.JSONDecodeError:
                pass
    return {}


def sha(p, n=None):
    h = hashlib.sha256(Path(p).read_bytes()).hexdigest()
    return h[:n] if n else h


def probe(v):
    r = roda(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height", "-show_entries", "format=duration",
              "-of", "json", v])
    if r.returncode:
        falha(f"não consegui ler o vídeo {v}", 1)
    j = json.loads(r.stdout); vs = [s for s in j["streams"] if s["codec_type"] == "video"]
    return dict(dur=float(j["format"].get("duration", 0)), w=vs[0]["width"] if vs else 0, h=vs[0]["height"] if vs else 0,
                audio=any(s["codec_type"] == "audio" for s in j["streams"]))


def registra(projeto, comando, resumo):
    (projeto / BASTIDOR).mkdir(parents=True, exist_ok=True)
    with open(projeto / BASTIDOR / "log.jsonl", "a") as f:
        f.write(json.dumps(dict(quando=datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                                comando=comando, resumo=resumo), ensure_ascii=False) + "\n")


def nome_livre(p):
    p, base, n = Path(p), Path(p), 2
    while p.exists():
        p = base.with_name(f"{base.stem}-{n}{base.suffix}"); n += 1
    return p


# ------------------------------------------------------------------ referencia
def autor_de(info_json):
    j = json.load(open(info_json))
    return j.get("channel") or j.get("uploader")  # channel é o @ no Instagram; uploader_id lá é número


def referencia(a):
    eh_link = re.match(r"https?://", a.fonte) is not None
    if eh_link:
        m = re.search(r"/(?:reels?|p|tv)/([\w-]+)", a.fonte)
        nome = m.group(1) if m else re.sub(r"\W+", "-", a.fonte.rstrip("/").rsplit("/", 1)[-1])[:40] or "referencia"
    else:
        if not Path(a.fonte).is_file():
            falha(f"arquivo não encontrado: {a.fonte}", 1)
        nome = Path(a.fonte).stem
    P = Path(a.pasta or f"caso-{nome}").resolve()
    ref = P / "referencia"; ref.mkdir(parents=True, exist_ok=True); (P / BASTIDOR / "medidas").mkdir(parents=True, exist_ok=True)
    reel = ref / "reel.mp4"; veio, autor, avisos = "já estava na pasta", None, []

    if not reel.exists():
        if eh_link:
            info = P / BASTIDOR / "reel"
            r = roda(["yt-dlp", "--playlist-items", "1", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "--write-info-json",
                      "-o", f"{info}.%(ext)s", a.fonte])
            baixado = Path(f"{info}.mp4")
            if r.returncode == 0 and baixado.exists():
                shutil.move(baixado, reel); veio = "yt-dlp"
                ij = Path(f"{info}.info.json")
                if ij.exists():
                    autor = autor_de(ij)
            else:
                copia = BIBLIOTECA / f"{nome}.mp4"
                if not copia.exists():
                    falha(f"não consegui baixar ({(r.stderr or r.stdout).strip()[-200:]}) e não há cópia na biblioteca. "
                          "Baixe o vídeo e rode de novo com o arquivo: caso.py referencia <arquivo.mp4>", 2)
                shutil.copy2(copia, reel); veio = f"biblioteca ({copia}), porque o download falhou"
                avisos.append("o download pediu login ou falhou; usei a cópia da biblioteca (sem cookies do navegador)")
                ij = copia.with_suffix(".info.json")
                if ij.exists():
                    autor = autor_de(ij)
        else:
            shutil.copy2(a.fonte, reel); veio = f"arquivo local {Path(a.fonte).resolve()}"
    origem = ref / "ORIGEM.md"
    pr = probe(reel)
    if not origem.exists():
        origem.write_text(f"# Origem da referência\n\n- Arquivo: `reel.mp4` ({reel.stat().st_size / 1e6:.1f} MB, {pr['w']}x{pr['h']}, "
                          f"{pr['dur']:.2f} s)\n- Link: {a.fonte if eh_link else '(arquivo local; preencher o link)'}\n"
                          f"- Autor: {autor or '(preencher)'}\n- Veio de: {veio}\n- Data: {datetime.date.today():%d/%m/%Y}\n"
                          f"- sha256: `{sha(reel)}`\n- Uso: estudo interno. Não publicar, não redistribuir.\n")

    # passo 2: o vídeo de dentro (demonstrativo)
    dentro = ref / "dentro.mp4"; demo = None
    if dentro.exists():
        demo = True
    elif a.demonstrativo != "nao":
        teste = P / BASTIDOR / "medidas" / "tela-dentro.mp4"; tj = P / BASTIDOR / "medidas" / "tela.json"
        if not teste.exists():
            r = roda([PY, SCR / "extrair_tela.py", reel, teste, "--json", tj])
            if r.returncode or not tj.exists():
                if a.demonstrativo == "sim":
                    falha(f"não achei a tela dentro da referência: {json_de(r).get('erro', r.stderr[-300:])}. "
                          "Passe os cantos com --quad no extrair_tela.py", 2)
                avisos.append("não achei cartão nem tela dentro da referência: ela já é o vídeo final")
        if tj.exists():
            Wn, Hn = json.load(open(tj))["tamanho"]
            frac = Wn * Hn / max(1, pr["w"] * pr["h"])
            # abaixo de 15% do quadro é um painel da própria animação, não uma tela ou cartão com vídeo (teste cego B: 8%)
            demo = a.demonstrativo == "sim" or 0.15 <= frac < 0.85
            if demo:
                shutil.copy2(teste, dentro)
            else:
                avisos.append(f"a 'tela' achada ocupa {frac:.0%} do quadro: a referência já é o vídeo final "
                              "(se for mesmo um demonstrativo, rode com --demonstrativo sim)")
    alvo = dentro if demo else reel
    pa = probe(alvo)
    resumo = (f"referência em {ref} ({veio}); " + (f"vídeo de dentro tirado: dentro.mp4, {pa['w']}x{pa['h']}, {pa['dur']:.1f} s"
              if demo else f"sem vídeo de dentro: o reel já é o vídeo final ({pa['w']}x{pa['h']}, {pa['dur']:.1f} s)")
              + ("; " + "; ".join(avisos) if avisos else ""))
    registra(P, "referencia", resumo)
    ok(resumo, comando=shlex.join(["python3", str(KIT / "clonar.py"), "novo", str(P), str(alvo)]
                                  + (["--link", a.fonte] if eh_link else []) + (["--autor", f"@{autor}"] if autor else [])),
       motivo="passos 3 e 4 são trabalho de agente (CLONAR.md, caminho demonstrativo): escolher um trecho que comece e "
              "termine num corte, clonar e virar molde (1h30 a 2h45 e US$ 28 a 33 de API; só com o ok). "
              f"Depois: {EU} aplicar <pasta do molde> --video <gravação da pessoa>",
       precisa_de_voce=True, pasta=str(P), referencia=str(reel), video_de_dentro=str(dentro) if demo else None,
       demonstrativo=bool(demo))


# ------------------------------------------------------------------ aplicar
def carrega_molde(molde):
    for x in ("index.html", "montar.py"):
        if not (molde / x).exists():
            falha(f"{molde} não é um molde: falta {x}", 1)
    spec = importlib.util.spec_from_file_location("montar_molde", molde / "montar.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    for f in ("le_palavras", "trechos_de_fala", "frases"):
        if not hasattr(m, f):
            falha(f"o montar.py do molde não tem {f}() (ver o contrato no topo do caso.py)", 1)
    return m


def le_destaques(arq, grupos):
    """aplica o destaques.txt: uma linha por frase, palavras em destaque entre colchetes, `escura:` marca a cena escura"""
    linhas = [l.strip() for l in Path(arq).read_text().splitlines() if l.strip() and not l.strip().startswith("#")]
    if len(linhas) != len(grupos):
        falha(f"{arq} tem {len(linhas)} frases e a transcrição tem {len(grupos)}: uma linha por frase (apague o arquivo "
              "para gerar de novo pela regra)", 1)
    escuras = []
    for i, (l, g) in enumerate(zip(linhas, grupos)):
        if l.lower().startswith("escura:"):
            escuras.append(i); l = l[7:].strip()
        toks = l.split()
        if len(toks) != len(g):
            falha(f"{arq}, frase {i + 1}: {len(toks)} palavras, a transcrição tem {len(g)} ({' '.join(p[0] for p in g)}). "
                  "Mude só os colchetes, não as palavras", 1)
        for p, t in zip(g, toks):
            p[2] = int(t.startswith("[") and t.endswith("]"))
    return escuras


def escreve_destaques(arq, grupos, escuras=()):
    txt = ["# Uma linha por frase. As palavras entre colchetes viram o destaque (pode ter mais de uma ou nenhuma).",
           "# Mude só os colchetes e rode o mesmo comando de novo. `escura:` no começo da linha põe a frase na cena escura",
           "# (caixa alta sobre o vídeo escurecido), nos moldes que têm o campo `cenas`.",
           "# Regra que escolheu: a palavra mais longa da frase fora das palavras vazias (clonar/scripts/destaque.py);",
           "# a cena escura, a escolhe_escura() do molde (tire o `escura:` para não ter)."]
    txt += [("escura: " if i in escuras else "") + " ".join(f"[{p[0]}]" if p[2] else p[0] for p in g) for i, g in enumerate(grupos)]
    Path(arq).write_text("\n".join(txt) + "\n")


def aplicar(a, extras):
    molde = Path(a.molde).resolve(); video = Path(a.video).resolve()
    if not video.is_file():
        falha(f"vídeo da pessoa não encontrado: {video}", 1)
    m = carrega_molde(molde)
    fala = Path(a.voz).resolve() if a.voz else video
    if not fala.is_file() or not probe(fala)["audio"]:
        falha("sem fala: o vídeo não tem áudio e não veio --voz (o destaque sai da transcrição da fala)", 1)
    saida = Path(a.saida).resolve() if a.saida else Path.cwd() / video.stem / "saidas" / f"{video.stem}.mp4"
    saida = nome_livre(saida)
    projeto = saida.parent.parent if saida.parent.name == "saidas" else saida.parent
    bast = projeto / BASTIDOR; bast.mkdir(parents=True, exist_ok=True)

    # 1. transcrever (retomável: a lista fica no bastidor, pelo sha da fala e o idioma)
    tj = bast / f"transcricao-{sha(fala, 12)}-{a.idioma}.json"; ti = tj.with_suffix(".info.json")
    if not tj.exists():
        r = roda([sys.executable, SCR / "transcrever.py", fala, "--idioma", a.idioma, "--saida", tj])
        j = json_de(r)
        if r.returncode or not j.get("ok"):
            falha(f"a transcrição falhou: {j.get('erro') or r.stderr[-300:]}", 2)
        ti.write_text(json.dumps(dict(provedor=j.get("provedor"), idioma=j.get("idioma"),
                                      aviso=j["proximo"]["motivo"] if j["proximo"]["precisa_de_voce"] else None), ensure_ascii=False))
    info = json.load(open(ti)) if ti.exists() else {}
    ws = m.le_palavras(tj)
    if not ws:
        falha("a transcrição não achou nenhuma palavra", 2)

    # 2. frases e destaque (regra do kit, ou o destaques.txt do projeto)
    grupos = m.frases(ws, [], m.trechos_de_fala(fala))
    arq = Path(a.destaques).resolve() if a.destaques else projeto / "destaques.txt"
    escuras = []
    if arq.exists():
        escuras = le_destaques(arq, grupos); origem_dest = f"o {arq.name}"
    elif a.destaques:
        falha(f"arquivo de destaques não encontrado: {arq}", 1)
    else:  # a cena escura da regra do molde (a altura do texto vem do rosto, então a caixa alta não cai nos olhos)
        i = m.escolhe_escura(grupos) if hasattr(m, "escolhe_escura") else None
        escuras = [] if i is None else [i]
        escreve_destaques(arq, grupos, escuras); origem_dest = "a regra do kit"
    # cenas sempre explícito: o padrão do molde marca a cena escura das frases do clone, não das da pessoa
    versao = dict(frases=json.dumps(grupos, ensure_ascii=False), cenas=json.dumps({str(i): "escura" for i in escuras}))
    vj = bast / f"{saida.stem}.caso-versao.json"
    vj.write_text(json.dumps(versao, ensure_ascii=False, indent=1))

    # 3. montar e renderizar (o montar.py do molde: cópia com os campos, motion blur, áudio da fala)
    cmd = [sys.executable, molde / "montar.py", "--pessoa", video, "--saida", saida, "--versao", vj]
    cmd += (["--voz", fala] if a.voz else []) + (["--previa"] if a.previa else []) + extras
    r = roda(cmd); j = json_de(r)
    (bast / f"{saida.stem}-montar.log").write_text(r.stdout + r.stderr)
    if r.returncode or not j.get("ok"):
        falha(f"o molde falhou: {j.get('erro') or (r.stderr or r.stdout)[-400:]}", j.get("codigo", 2))
    dest = [p[0] for g in grupos for p in g if p[2]]
    aviso = info.get("aviso")
    resumo = (f"{saida.name}: {len(grupos)} frase(s), destaques ({origem_dest}): {', '.join(dest) or 'nenhum'}"
              + (f"; cena escura nas frases {', '.join(str(i + 1) for i in escuras)}" if escuras else "")
              + f"; transcrição por {info.get('provedor', '?')}, idioma {info.get('idioma', '?')}"
              + (f"; aviso: {aviso}" if aviso else ""))
    registra(projeto, "aplicar " + " ".join(map(str, sys.argv[2:])), resumo)
    ok(resumo, comando=shlex.join(["open", str(saida)]),
       motivo=f"conferir no olho; para trocar o destaque, edite {arq} (colchetes) e rode o mesmo comando (sai um arquivo "
              "novo, nada é sobrescrito)" + (f". {aviso}: a transcrição saiu pelo local" if aviso else ""),
       precisa_de_voce=True, saida=str(saida), destaques=str(arq), transcricao=str(tj), versao=str(vj),
       aviso=aviso)


def main():
    argv = sys.argv[1:]; extras = []
    if "--" in argv:
        i = argv.index("--"); argv, extras = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("referencia"); s.add_argument("fonte"); s.add_argument("--pasta")
    s.add_argument("--demonstrativo", default="auto", choices=("auto", "sim", "nao"))
    s = sub.add_parser("aplicar"); s.add_argument("molde"); s.add_argument("--video", required=True); s.add_argument("--saida")
    s.add_argument("--idioma", default="auto"); s.add_argument("--destaques"); s.add_argument("--voz")
    s.add_argument("--previa", action="store_true")
    a = ap.parse_args(argv)
    referencia(a) if a.cmd == "referencia" else aplicar(a, extras)


if __name__ == "__main__":
    main()
