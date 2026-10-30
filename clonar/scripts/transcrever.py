#!/usr/bin/env python3
"""transcrever.py: as palavras de uma fala, com o início e o fim de cada uma.

  transcrever.py <audio ou video> [--saida palavras.json] [--idioma auto|pt|en|...] [--provedor auto|groq|local]
  transcrever.py --autoteste

Grava em --saida a lista no formato que os moldes já consomem (o mesmo do `hyperframes transcribe`):
  [{"text": "palavra", "start": 0.12, "end": 0.40}, ...]
e devolve no stdout o JSON padrão {ok, resumo, proximo}, com o provedor usado, o idioma e o arquivo.

Provedores, nesta ordem (--provedor auto):
1. Groq, whisper-large-v3 com timestamp_granularities[]=word (POST https://api.groq.com/openai/v1/audio/transcriptions,
   response_format verbose_json; plano gratuito, até 25 MB por arquivo). A fala vai como FLAC mono de 16 kHz.
   A chave vem de GROQ_API_KEY no ambiente ou num `.env` (o primeiro achado subindo da pasta atual e da pasta do kit).
   A chave nunca é impressa nem gravada.
2. Local: `npx hyperframes@0.8.184 transcribe` (whisper.cpp). Inglês usa o small.en (465 MB, rápido); qualquer outro
   idioma, ou auto, usa o large-v3 (~3 GB baixados na primeira vez). Sem chave da Groq, o JSON avisa com
   proximo.precisa_de_voce = true e o motivo, e a transcrição sai pelo local mesmo assim.
Não usa a ElevenLabs (créditos pagos).
"""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile, urllib.error, urllib.request, uuid
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from saida import falha, ok  # noqa: E402

GROQ_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GROQ_MODELO = "whisper-large-v3"
GROQ_LIMITE = 25 * 1024 * 1024
HF = ["npx", "--yes", "hyperframes@" + os.environ.get("HF_VERSAO", "0.8.184")]
AQUI = Path(__file__).resolve().parent


def chave_groq():
    """GROQ_API_KEY do ambiente ou do primeiro .env que tiver ela (subindo da pasta atual e da do kit)"""
    if os.environ.get("GROQ_API_KEY", "").strip():
        return os.environ["GROQ_API_KEY"].strip()
    vistos = set()
    for base in (Path.cwd(), AQUI):
        for d in [base, *base.parents]:
            env = d / ".env"
            if env in vistos or not env.is_file():
                continue
            vistos.add(env)
            for linha in env.read_text(errors="ignore").splitlines():
                k, _, v = linha.strip().removeprefix("export ").partition("=")
                if k.strip() == "GROQ_API_KEY" and v.strip().strip("'\""):
                    return v.strip().strip("'\"")
    return None


def audio_flac(fala, pasta, ext="flac"):
    """a fala em mono 16 kHz (FLAC para a Groq; WAV para o local, que recusa .aiff e outros)"""
    out = Path(pasta) / f"fala.{ext}"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(fala), "-vn", "-ac", "1", "-ar", "16000", str(out)],
                       capture_output=True, text=True)
    if r.returncode or not out.exists():
        falha(f"não consegui tirar o áudio de {fala}: {r.stderr.strip()[-300:]}", 1)
    return out


def groq(fala, idioma, chave, pasta):
    """devolve (palavras, idioma detectado) ou levanta RuntimeError com o motivo (sem a chave no texto)"""
    flac = audio_flac(fala, pasta)
    if flac.stat().st_size > GROQ_LIMITE:
        raise RuntimeError(f"a fala tem {flac.stat().st_size / 1e6:.0f} MB em FLAC, acima dos 25 MB do plano gratuito")
    campos = [("model", GROQ_MODELO), ("response_format", "verbose_json"), ("timestamp_granularities[]", "word"),
              ("temperature", "0")] + ([("language", idioma)] if idioma != "auto" else [])
    sep = uuid.uuid4().hex; corpo = b""
    for k, v in campos:
        corpo += f'--{sep}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    corpo += (f'--{sep}\r\nContent-Disposition: form-data; name="file"; filename="fala.flac"\r\n'
              "Content-Type: audio/flac\r\n\r\n").encode() + flac.read_bytes() + f"\r\n--{sep}--\r\n".encode()
    req = urllib.request.Request(GROQ_URL, data=corpo, method="POST", headers={
        "Authorization": f"Bearer {chave}", "Content-Type": f"multipart/form-data; boundary={sep}", "User-Agent": "apple-style-ui"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            j = json.load(r)
    except urllib.error.HTTPError as e:
        motivo = {401: "a Groq recusou a chave (GROQ_API_KEY inválida ou revogada)", 413: "arquivo grande demais para a Groq",
                  429: "limite do plano gratuito da Groq atingido; tente de novo mais tarde"}.get(e.code, f"a Groq respondeu {e.code}")
        raise RuntimeError(motivo) from None
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"sem conexão com a Groq ({getattr(e, 'reason', e)})") from None
    ws = [dict(text=w["word"].strip(), start=round(float(w["start"]), 3), end=round(float(w["end"]), 3))
          for w in j.get("words") or [] if w.get("word", "").strip()]
    for a, b in zip(ws, ws[1:]):  # o whisper às vezes dá a última palavra começando antes da anterior: anda só para a frente
        if b["start"] < a["start"]:
            b["start"] = a["start"]
            b["end"] = max(b["end"], b["start"])
    return ws, j.get("language") or idioma


def local(fala, idioma, pasta):
    modelo = "small.en" if idioma == "en" else "large-v3"
    fala = audio_flac(fala, pasta, "wav")
    cmd = HF + ["transcribe", str(fala), "--dir", str(pasta), "--json", "-m", modelo] + ([] if idioma == "en" else ["-l", idioma])
    r = subprocess.run(cmd, capture_output=True, text=True)
    tj = Path(pasta) / "transcript.json"
    if r.returncode or not tj.exists():
        falha(f"a transcrição local falhou: {(r.stderr or r.stdout).strip()[-400:]}", 2)
    j = json.load(open(tj)); ws = j if isinstance(j, list) else j.get("words", [])
    return [dict(text=w["text"].strip(), start=round(float(w["start"]), 3), end=round(float(w["end"]), 3))
            for w in ws if w.get("text", "").strip()], idioma


def livre(caminho):
    """não sobrescreve: devolve um nome que ainda não existe (x.json, x-2.json, ...)"""
    p, n = Path(caminho), 2
    while p.exists():
        p = Path(caminho).with_name(f"{Path(caminho).stem}-{n}{Path(caminho).suffix}"); n += 1
    return p


def transcreve(fala, idioma="auto", provedor="auto"):
    """(palavras, info) sem gravar nada fora de uma pasta temporária; info tem provedor, idioma e aviso"""
    aviso = None
    with tempfile.TemporaryDirectory(prefix="asui-transcricao-") as tmp:
        if provedor in ("auto", "groq"):
            chave = chave_groq()
            if not chave:
                aviso = "falta a GROQ_API_KEY no .env"
            else:
                try:
                    ws, idi = groq(fala, idioma, chave, tmp)
                    return ws, dict(provedor=f"groq ({GROQ_MODELO})", idioma=idi, aviso=None)
                except RuntimeError as e:
                    aviso = str(e)
            if provedor == "groq":
                falha(f"Groq pedida e indisponível: {aviso}", 2)
        ws, idi = local(fala, idioma, tmp)
        return ws, dict(provedor="local (hyperframes transcribe, " + ("small.en" if idioma == "en" else "large-v3") + ")",
                        idioma=idi, aviso=aviso)


def confere(ws, dur):
    """as palavras andam para a frente e cabem na fala"""
    assert ws, "nenhuma palavra"
    for a, b in zip(ws, ws[1:]):
        assert b["start"] >= a["start"] - 1e-3, f"fora de ordem: {a} {b}"
    for w in ws:
        assert 0 <= w["start"] <= w["end"] + 1e-3 <= dur + 0.5, f"tempo fora da fala: {w}"


def duracao(v):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def autoteste():
    """fala sintética do `say` (macOS) pelo provedor local em inglês; e o aviso quando falta a chave"""
    if not shutil.which("say"):
        falha("o autoteste usa o `say` do macOS", 1)
    with tempfile.TemporaryDirectory(prefix="asui-autoteste-") as tmp:
        fala = Path(tmp) / "fala.aiff"
        frase = "The quick brown fox jumps over the lazy dog. Then it rests for a while."
        subprocess.run(["say", "-v", "Samantha", "-r", "170", "-o", str(fala), frase], check=True)
        sem_chave = chave_groq() is None
        ws, info = transcreve(fala, "en", "auto" if sem_chave else "local")
        if sem_chave:  # o caminho de hoje: sem chave, avisa e cai no local
            assert info["aviso"] == "falta a GROQ_API_KEY no .env" and info["provedor"].startswith("local"), info
        confere(ws, duracao(fala))
        achou = sum(1 for w in ws if w["text"].strip(".,").lower() in frase.lower().replace(".", "").split())
        assert achou >= 0.8 * len(frase.split()), f"só {achou} de {len(frase.split())} palavras reconhecidas"
        assert ws[0]["start"] < 0.6, f"a primeira palavra começa tarde demais: {ws[0]}"
    ok(f"autoteste passou: {len(ws)} palavras pelo provedor local, {achou} batem com a frase, tempos em ordem"
       + ("; sem GROQ_API_KEY, o aviso saiu e caiu no local" if sem_chave else "; chave presente, Groq não testada aqui"),
       palavras=ws[:5])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fala", nargs="?"); ap.add_argument("--saida"); ap.add_argument("--idioma", default="auto")
    ap.add_argument("--provedor", default="auto", choices=("auto", "groq", "local")); ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args()
    if a.autoteste:
        return autoteste()
    if not a.fala or not Path(a.fala).exists():
        falha(f"fala não encontrada: {a.fala}", 1)
    fala = Path(a.fala).resolve()
    ws, info = transcreve(fala, a.idioma.lower(), a.provedor)
    if not ws:
        falha("a transcrição não achou nenhuma palavra (a fala tem voz?)", 2)
    confere(ws, duracao(fala))
    saida = livre(a.saida or fala.with_name(f"{fala.stem}.palavras.json"))
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(ws, ensure_ascii=False, indent=1))
    sha = hashlib.sha256(fala.read_bytes()).hexdigest()[:12]
    prec = info["aviso"] is not None
    ok(f"{len(ws)} palavras por {info['provedor']}, idioma {info['idioma']}" + (f"; aviso: {info['aviso']}" if prec else ""),
       comando=None if not prec else "acrescentar GROQ_API_KEY=<chave> ao .env (console.groq.com, plano gratuito)",
       motivo=info["aviso"] or "palavras prontas para o molde", precisa_de_voce=prec,
       arquivo=str(saida), provedor=info["provedor"], idioma=info["idioma"], sha_fala=sha)


if __name__ == "__main__":
    main()
