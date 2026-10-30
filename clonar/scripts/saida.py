"""saida.py: o que as ferramentas do kit escritas pelo Apple Style UI têm em comum.

- ok() e falha(): a saída JSON padrão {ok, resumo, proximo: {comando, motivo, precisa_de_voce}} no stdout;
  erro {ok: false, erro, codigo} no stderr (1 = pedido inválido, 2 = falha ao rodar).
- tamanho() e quadros(): leitura de quadros pelo número (select, a numeração do burst.py e do fdsum.py), um por vez,
  para vídeo vertical em resolução cheia não ocupar gigabytes de memória.
"""
import json, subprocess, sys



def __getattr__(nome):
    """LU (pesos do luma, float32) só carrega o numpy quando alguém pede: o caso.py roda com o python do sistema."""
    if nome == "LU":
        import numpy as np
        return np.array([0.299, 0.587, 0.114], np.float32)
    raise AttributeError(nome)


def ok(resumo, comando=None, motivo="", precisa_de_voce=False, **extra):
    print(json.dumps(dict(ok=True, resumo=resumo, **extra,
                          proximo=dict(comando=comando, motivo=motivo, precisa_de_voce=precisa_de_voce)),
                     ensure_ascii=False, indent=1))


def falha(erro, codigo=1):
    print(json.dumps(dict(ok=False, erro=erro, codigo=codigo), ensure_ascii=False), file=sys.stderr)
    sys.exit(codigo)


def tamanho(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(video)], capture_output=True, text=True)
    if r.returncode or not r.stdout.strip():
        falha(f"não consegui ler o vídeo {video}", 1)
    w, h = map(int, r.stdout.strip().split(",")[:2])
    return w, h


def quadros(video, a=0, b=None, largura=None):
    """gera (f, quadro RGB uint8) de a até b (inclusive), um por vez; largura reduz por área (altura par)"""
    import numpy as np
    w, h = tamanho(video)
    if largura and largura != w:
        h = max(2, int(round(h * largura / w / 2)) * 2); w = largura
    vf = f"select=between(n\\,{a}\\,{b if b is not None else 10 ** 9})" + (f",scale={w}:{h}:flags=area" if largura else "")
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(video), "-vf", vf, "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    n = w * h * 3; f = a
    try:
        while True:
            buf = p.stdout.read(n)
            if len(buf) < n:
                break
            yield f, np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            f += 1
    finally:
        p.stdout.close(); p.wait()
