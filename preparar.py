#!/usr/bin/env python3
"""preparar.py: deixa a máquina pronta para o Apple Style UI e diz o que falta.

  python3 preparar.py              confere tudo e instala o que é do produto: o ambiente Python
                                   (~/.apple-style-ui/venv), o HyperFrames e o Chrome dele
  python3 preparar.py --conferir   só confere, sem instalar nada

Programas do sistema (ffmpeg, Node, Python 3.11+, whisper-cpp) não são instalados aqui: quando falta algum, a saída
traz o comando do brew para rodar com o ok da pessoa, e depois roda-se este de novo. Só usa a biblioteca padrão.

Saída: o JSON {ok, resumo, proximo, pronto, opcional} no stdout. Falta de programa: {ok: false, erro, codigo, conserto}
no stderr e saída 1. Pronta, grava ~/.apple-style-ui/pronto.json (o aviso de abertura do plugin para de aparecer).
"""
import argparse, datetime, json, os, platform, re, shutil, subprocess, sys, tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
HF = "0.8.184"  # a mesma versão fixa de montar.py e dos moldes
MAQUINA = Path.home() / ".apple-style-ui"
VENV = MAQUINA / "venv"
PRONTO = MAQUINA / "pronto.json"
LOG = MAQUINA / "preparar.log"


def roda(cmd, **kw):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, **kw)
    except OSError as e:
        return subprocess.CompletedProcess(cmd, 127, "", str(e))


def versao(cmd, padrao):
    r = roda(cmd)
    m = re.search(padrao, r.stdout + r.stderr) if r.returncode == 0 else None
    return tuple(int(x) for x in m.groups()) if m else None


def programas():
    """(o que está pronto, o que falta) entre os programas do sistema"""
    pronto, falta = [], []
    py = sys.version_info[:2]
    (pronto if py >= (3, 11) else falta).append(f"Python {py[0]}.{py[1]}" + ("" if py >= (3, 11) else " (precisa 3.11 ou mais novo)"))
    node = versao(["node", "--version"], r"v(\d+)")
    if node and node[0] >= 20 and shutil.which("npx"):
        pronto.append(f"Node {node[0]}")
    else:
        falta.append("Node 20 ou mais novo")
    for p in ("ffmpeg", "ffprobe"):
        (pronto if versao([p, "-version"], r"version n?(\d+)") else falta).append(p)
    # a transcrição local do HyperFrames usa o whisper-cpp; sem ele tenta compilar do código e falha num Mac novo
    (pronto if shutil.which("whisper-cli") else falta).append("whisper-cpp")
    return pronto, falta


def ambiente_ok():
    py = VENV / "bin" / "python"
    return py.exists() and roda([str(py), "-c", "import numpy, PIL, cv2, scipy"]).returncode == 0


def chave_groq():
    if os.environ.get("GROQ_API_KEY"):
        return True
    for d in [Path.cwd(), *Path.cwd().parents]:
        env = d / ".env"
        if env.is_file() and re.search(r"^\s*(export\s+)?GROQ_API_KEY\s*=\s*\S", env.read_text(errors="ignore"), re.M):
            return True
    return False


def passo(log, cmd, **kw):
    r = roda(cmd, **kw)
    log.write(f"$ {' '.join(map(str, cmd))}\n{r.stdout}{r.stderr}\n")
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="deixa a máquina pronta para o Apple Style UI")
    ap.add_argument("--conferir", action="store_true", help="só confere, sem instalar nada")
    a = ap.parse_args()

    def falha(erro, conserto, codigo=1):
        print(json.dumps(dict(ok=False, erro=erro, codigo=codigo, conserto=conserto), ensure_ascii=False), file=sys.stderr)
        sys.exit(codigo)

    if platform.system() != "Darwin":
        falha("o Apple Style UI por enquanto só roda no Mac (render e fontes do sistema)", None, 2)
    pronto, falta = programas()
    if falta:
        formula = {"Python": "python", "Node": "node", "ffmpeg": "ffmpeg", "ffprobe": "ffmpeg", "whisper-cpp": "whisper-cpp"}
        brew = "brew install " + " ".join(dict.fromkeys(formula[f.split()[0]] for f in falta))
        conserto = brew if shutil.which("brew") else "instalar o Homebrew em https://brew.sh (pede a senha do Mac), depois " + brew
        falha("falta no Mac: " + ", ".join(falta), conserto)

    MAQUINA.mkdir(parents=True, exist_ok=True)
    # o render usa o Chrome sem janela que o HyperFrames baixa para si (o "browser path" acha o Chrome comum e engana)
    hf_pronto = any((Path.home() / ".cache" / "hyperframes" / "chrome" / "chrome-headless-shell").glob("*"))
    if a.conferir:
        if not ambiente_ok():
            falta.append("ambiente Python do produto")
        if not hf_pronto:
            falta.append(f"HyperFrames {HF} e o Chrome dele")
        if falta:
            falha("falta preparar: " + ", ".join(falta), f"python3 {AQUI / 'preparar.py'}")
    else:
        with open(LOG, "a", encoding="utf-8") as log:
            log.write(f"\n== {datetime.datetime.now().isoformat(timespec='seconds')}\n")
            if not ambiente_ok():
                if not (VENV / "bin" / "python").exists() and not passo(log, [sys.executable, "-m", "venv", str(VENV)]):
                    falha(f"não consegui criar o ambiente Python em {VENV} (detalhes em {LOG})", f"python3 -m venv {VENV}", 2)
                if not passo(log, [str(VENV / "bin" / "pip"), "install", "-q", "-r", str(AQUI / "clonar" / "requirements.txt")]):
                    falha(f"não consegui instalar as bibliotecas Python (detalhes em {LOG}); confira a internet", f"python3 {AQUI / 'preparar.py'}", 2)
            if not passo(log, ["npx", "--yes", f"hyperframes@{HF}", "browser", "ensure"], cwd=tempfile.gettempdir(), timeout=900):
                falha(f"não consegui baixar o HyperFrames e o Chrome dele (detalhes em {LOG}); confira a internet", f"python3 {AQUI / 'preparar.py'}", 2)
    pronto += ["ambiente Python do produto", f"HyperFrames {HF} e o Chrome dele"]

    opcional = []
    if not chave_groq():
        opcional.append("sem GROQ_API_KEY no .env da pasta: a transcrição da tua gravação roda no Mac, e a 1ª vez baixa uns 3 GB")
    if not Path("/System/Library/Fonts/SFNS.ttf").exists():
        opcional.append("sem a SF Pro do sistema: os vídeos saem com a Inter")
    plugin = json.loads((AQUI / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]
    if not a.conferir:
        PRONTO.write_text(json.dumps(dict(versao=plugin, hyperframes=HF, data=datetime.date.today().isoformat()), indent=1) + "\n")
    print(json.dumps(dict(ok=True, resumo="Máquina pronta: " + ", ".join(pronto) + ".", pronto=pronto, opcional=opcional,
                          proximo=dict(comando="/apple-style-ui começar", motivo="o primeiro vídeo, com a tua marca",
                                       precisa_de_voce=True)), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
