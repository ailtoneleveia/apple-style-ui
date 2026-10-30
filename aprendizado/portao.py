#!/usr/bin/env python3
"""portao.py: a catraca. Confere um vídeo antes da aprovação humana e diz PASSOU ou REPROVOU, com os motivos.

    python3 portao.py <clone>/final.mp4 --tipo clone
    python3 portao.py <video>/saidas/junior.mp4 --tipo versao [--versao moldes/satellite/versoes/junior.json] [--molde moldes/satellite/molde]
    python3 portao.py <video>/saidas/x-previa.mp4 --tipo versao --versao <video>/.apple-style-ui/versao-resolvida.json --previa

Clone: burst.py + compare.py contra a referência do próprio clone. Distância e correlação não podem ficar piores
que as do melhor clone aprovado (menos uma folga) e o pico de movimento de cada cena fica a no máximo 1 quadro.
Versão de molde (ou vídeo novo feito num molde): o molde com os padrões continua igual ao clone original, o check
do HyperFrames não acusa erro de código, quadros e duração batem, nenhum texto sai da caixa nem fica pequeno demais
(comparado com o molde nas mesmas peças e com os textos originais), o motion blur está lá e as cores estão na
paleta da versão. Com --previa, o vídeo é uma prévia: confere tudo menos o motion blur (o aprender.py sempre exige o
final). Também avisa se alguém editou à mão uma versão travada do perfil. Não registra nada.

A régua (o molde igual ao clone, e a regressão do aprender.py) compara quadro a quadro com tolerância: md5 igual passa
direto; senão, numa miniatura cinza de 64x64 (cada ponto é a média de um bloco de ~17 px), nenhum ponto pode diferir
mais que TOL_QUADRO. Assim o ruído do renderizador passa e uma mudança de verdade, mesmo de 4 px, não.

Saída: um JSON no stdout, {"ok", "resumo", "proximo": {"comando", "motivo", "precisa_de_voce"}, ...}. Em erro, também
uma linha {"ok": false, "erro", "codigo"} no stderr. Códigos de saída: 0 ok, 1 erro (inclui REPROVOU), 2 uso errado.
"""
import argparse, base64, hashlib, importlib.util, json, os, re, shlex, shutil, subprocess, sys, tempfile, zlib
from functools import lru_cache
import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)  # a raiz do produto
RASCUNHO = os.getcwd()  # o laudo mostra o vídeo relativo à pasta de trabalho


def _nome():
    """O nome do produto mora numa constante só, NOME no montador (montar.py na raiz do produto).
    Carregado com outro nome de módulo, para não ocupar o `import montar` do montar_de."""
    e = importlib.util.spec_from_file_location("montar_satellite", os.path.join(RAIZ, "montar.py"))
    m = importlib.util.module_from_spec(e)
    e.loader.exec_module(m)
    return m.NOME


NOME = _nome()  # dele saem ~/.<NOME>/perfil e <projeto>/.<NOME>/decisoes.json
PERFIL_DIR = os.environ.get("ASUI_PERFIL") or os.path.expanduser(f"~/.{NOME}/perfil")  # testes: ASUI_PERFIL=<pasta temporária>
SCRIPTS = os.path.join(RAIZ, "clonar", "scripts")
TRABALHO = os.environ.get("ASUI_TRABALHO") or os.path.join(tempfile.gettempdir(), NOME, "aprendizado")
# a prova é quadro a quadro contra a régua de cada molde (regressao/<molde>-original.txt), com a tolerância. A do
# Satellite saiu da prévia do clone; a do Joi e a do VoiceOS, do molde com as peças livres (os recortes do original não
# vão no repositório). Sem a régua, ela sai da prévia do projeto abaixo. Molde fora desta lista cai na versão travada
# (MOLDE.json, montar.py --travar)
ORIGINAL_DO_MOLDE = {m: os.path.join(RAIZ, "moldes", m, "molde") for m in ("satellite", "joi", "voiceos")}
# A régua por tolerância, calibrada em 22/10 com o mesmo render duas vezes neste Mac (prévias, miniatura 64x64): o maior
# ponto que muda é 0 no Satellite, 3 no Joi e 8 no VoiceOS (o vidro com backdrop-filter varia a cada render). TOL_QUADRO é
# o dobro do pior ruído. As mudanças de verdade dos testes passam longe: pílula 4 px mais larga (molde alterado) muda
# até 27 em 61 quadros; botão 20 % maior (teste da quarentena) até 63 em 56 quadros. A média do quadro inteiro não serve:
# a do ruído do VoiceOS (0,59) é maior que a da pílula alterada (0,30).
LADO, TOL_QUADRO = 64, 16
TOL_DIST, TOL_CORR, LAG_MAX = 0.008, 0.02, 1  # folga: Satellite (0,010 / 0,981) e Joi (0,004 / 0,997) passam um pelo outro
BLUR_MIN = 1.6  # com blur: Satellite 3,4x a 4,4x, VoiceOS 4,1x, Joi 2,4x (4 subquadros a 60 fps); sem blur: 1,0x
TEXTO = {"text_box_overflow": "texto saindo da caixa", "text_below_floor": "letra pequena demais para ler no celular"}


class Falha(Exception):
    """Erro com nome (codigo): vira o JSON de saída e o código de saída 1, ou 2 quando é uso errado."""
    def __init__(self, erro, codigo, comando="", motivo="", uso=False, **dados):
        super().__init__(erro)
        self.erro, self.codigo, self.comando, self.motivo, self.uso, self.dados = erro, codigo, comando, motivo, uso, dados


def saida(resumo, comando="", motivo="", precisa_de_voce=False, codigo=None, uso=False, **dados):
    """O contrato: um JSON no stdout; em erro, também {ok: false, erro, codigo} no stderr. Sai com 0, 1 ou 2."""
    print(json.dumps({"ok": codigo is None, "resumo": resumo,
                      "proximo": {"comando": comando, "motivo": motivo, "precisa_de_voce": precisa_de_voce}, **dados},
                     ensure_ascii=False, indent=1))
    if codigo:
        print(json.dumps({"ok": False, "erro": resumo, "codigo": codigo}, ensure_ascii=False), file=sys.stderr)
    sys.exit(0 if codigo is None else 2 if uso else 1)


def executar(fn):
    try:
        fn()
    except Falha as f:
        saida(f.erro, f.comando, f.motivo, bool(f.comando or f.motivo), f.codigo, f.uso, **f.dados)
    except SystemExit:
        raise
    except Exception as e:  # qualquer outra coisa é defeito do próprio aprendizado
        saida(f"defeito interno: {e!r}", "", "o erro não é do vídeo nem do comando; avise quem mantém o aprendizado", False, "DEFEITO_INTERNO")


class Args(argparse.ArgumentParser):
    def error(self, message):
        saida(f"uso errado: {message}", f"python3 {shlex.quote(self.prog)} --help", "veja as opções", False, "USO_ERRADO", uso=True)


def comando(script, *args):
    """Próximo comando pronto para rodar (com a pasta de perfil dos testes, se for o caso)."""
    env = f"ASUI_PERFIL={shlex.quote(PERFIL_DIR)} " if os.environ.get("ASUI_PERFIL") else ""
    return env + shlex.join(["python3", os.path.join(AQUI, script), *args])


def sh(cmd, **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        raise Falha(f"falta o programa {cmd[0]}", "FALTA_PROGRAMA", motivo="instale e rode de novo")
    if r.returncode:
        raise Falha(f"o comando falhou: {' '.join(map(str, cmd[:4]))} ... {(r.stderr or r.stdout)[-600:]}", "COMANDO_FALHOU")
    return r.stdout


def espaco():
    os.makedirs(TRABALHO, exist_ok=True)
    st = os.statvfs(TRABALHO)
    if st.f_bavail * st.f_frsize < 2e9:
        raise Falha(f"parei: menos de 2 GB livres no disco ({st.f_bavail * st.f_frsize / 1e9:.1f} GB)", "SEM_ESPACO",
                    motivo="libere espaço e rode de novo")


def montar_de(molde):
    """O montar.py que mora ao lado do molde: validar, render, HF, FPS e MOMENTOS vêm dele."""
    # shortcut: um montar por execução (o import fica em cache); dois motores no mesmo processo pedem importlib
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(molde)), "montar.py")):
        raise Falha(f"não achei o montar.py ao lado do molde {molde}", "FALTA_MONTAR")
    sys.path.insert(0, os.path.dirname(os.path.abspath(molde)))
    sys.dont_write_bytecode = True  # não deixa __pycache__ na pasta do molde
    import montar
    return montar


def declaracao(pasta):
    html = open(os.path.join(pasta, "index.html"), encoding="utf-8").read()
    m = re.search(r"data-composition-variables='(.*?)'", html, re.S)
    return html, m, json.loads(m.group(1))


def copia(origem, destino, valores=None):
    """Cópia do projeto. Com valores, injeta window.__hfVariables no começo do <head>, como o render faz: o check
    não lê --variables-file, e os padrões declarados ficam intactos porque os moldes medem "novo menos original"."""
    shutil.rmtree(destino, ignore_errors=True)
    shutil.copytree(origem, destino, ignore=shutil.ignore_patterns(".hyperframes", "renders"))
    if os.path.exists(os.path.join(os.path.dirname(origem), "montar.py")):
        montar_de(origem).fonte_do_sistema(destino)  # a SF Pro não vai no repositório: vem do sistema (ou a Inter)
    if valores:
        caminho = os.path.join(destino, "index.html")
        html = open(caminho, encoding="utf-8").read()
        script = "<script>window.__hfVariables = " + json.dumps(valores, ensure_ascii=False).replace("</", "<\\/") + ";</script>"
        novo, n = re.subn(r"<head[^>]*>", lambda m: m.group(0) + script, html, count=1)
        if not n:
            raise Falha(f"o index.html de {origem} não tem <head>", "MOLDE_SEM_HEAD")
        open(caminho, "w", encoding="utf-8").write(novo)
    return destino


def quadros_md5(mp4):
    out = sh(["ffmpeg", "-v", "error", "-i", mp4, "-map", "0:v", "-f", "framemd5", "-"])
    return [l.rsplit(",", 1)[-1].strip() for l in out.splitlines() if l.strip() and not l.startswith("#")]


def assinaturas(mp4):
    """Um item por quadro, "md5:miniatura": o md5 é o atalho exato; a miniatura (cinza LADOxLADO, média por área, em
    zlib + base64) é a régua com tolerância. Sem espaço, porque o aprender.py guarda um item por linha."""
    md5s = quadros_md5(mp4)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-map", "0:v", "-vf", f"scale={LADO}:{LADO}:flags=area", "-fps_mode", "passthrough",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    mini = np.frombuffer(raw, np.uint8).reshape(-1, LADO * LADO)
    if len(mini) != len(md5s):
        raise Falha(f"{mp4}: {len(md5s)} quadros no md5 e {len(mini)} na miniatura", "COMANDO_FALHOU")
    return [f"{h}:{base64.b64encode(zlib.compress(m.tobytes(), 9)).decode()}" for h, m in zip(md5s, mini)]


def igual(a, b):
    """Dois quadros da régua. md5 igual passa direto; senão, nenhum ponto da miniatura pode diferir mais que TOL_QUADRO.
    Régua antiga, só com md5: compara exato, como antes."""
    ha, _, ma = a.partition(":")
    hb, _, mb = b.partition(":")
    if ha == hb:
        return True
    if not (ma and mb):
        return False
    x, y = (np.frombuffer(zlib.decompress(base64.b64decode(m)), np.uint8).astype(np.int16) for m in (ma, mb))
    return x.shape == y.shape and int(np.abs(x - y).max()) <= TOL_QUADRO


def diferentes(a, b):
    return sum(not igual(x, y) for x, y in zip(a, b)) + abs(len(a) - len(b))


def exatos(a, b):
    """Quadros com o mesmo md5 (para dizer "idênticos" ou "iguais dentro da tolerância")."""
    return sum(x.partition(":")[0] == y.partition(":")[0] for x, y in zip(a, b))


def previa(mt, projeto, valores, nome):
    """Prévia (fps do molde, sem blur, --workers 1) numa cópia do projeto. Devolve (mp4, assinatura de cada quadro)."""
    espaco()
    pasta = os.path.join(TRABALHO, nome)
    proj = copia(projeto, os.path.join(pasta, "proj"))
    vj = os.path.join(pasta, "vars.json")
    json.dump(valores, open(vj, "w", encoding="utf-8"), ensure_ascii=False)
    mp4 = os.path.join(pasta, "previa.mp4")
    try:
        mt.render(proj, vj, mt.FPS, mp4)
    except (SystemExit, Exception) as e:  # cada montar.py falha do seu jeito (sys.exit ou exceção própria)
        raise Falha(f"o render da prévia {nome} falhou: {str(e)[-600:]}", "RENDER_FALHOU")
    shutil.rmtree(proj)
    return mp4, assinaturas(mp4)


def nome_do_molde(molde):
    """satellite, joi ou voiceos: a pasta do molde, ou a de cima quando ela se chama molde/."""
    m = os.path.normpath(molde)
    return os.path.basename(os.path.dirname(m)) if os.path.basename(m) == "molde" else os.path.basename(m)


def digital_do_molde(molde):
    """sha256 dos arquivos do molde e da versão do HyperFrames: se não mudou, a saída do molde também não mudou."""
    h = hashlib.sha256(" ".join(montar_de(molde).HF).encode())
    for raiz, pastas, arqs in os.walk(molde):
        pastas[:] = sorted(p for p in pastas if not p.startswith(".") and p not in ("renders", "node_modules"))
        for a in sorted(arqs):
            if not a.startswith(".") and a != "MOLDE.json":
                h.update(os.path.relpath(os.path.join(raiz, a), molde).encode() + sha256(os.path.join(raiz, a)).encode())
    return h.hexdigest()


def quadros_e_fps(mp4):
    q = json.loads(sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                       "stream=nb_read_packets,r_frame_rate", "-of", "json", mp4]))["streams"][0]
    num, den = q["r_frame_rate"].split("/")
    return int(q["nb_read_packets"]), int(num) / int(den)


@lru_cache(None)
def padroes(molde):
    """A régua do molde: (vídeo de referência das cores, quadros esperados, medida, motivo de reprovação ou None)."""
    mt, nome = montar_de(molde), nome_do_molde(molde)
    if nome in ORIGINAL_DO_MOLDE:
        # shortcut: renderiza os padrões a cada execução (~40 s); cache por digital_do_molde se ficar lento
        base = os.path.join(AQUI, "regressao", nome + "-original.txt")
        if not os.path.exists(base):
            os.makedirs(os.path.dirname(base), exist_ok=True)
            open(base, "w").write("\n".join(previa(mt, ORIGINAL_DO_MOLDE[nome], {}, nome + "-clone-original")[1]) + "\n")
        mp4, md5s = previa(mt, molde, {}, f"{nome}-padroes-{hashlib.md5(molde.encode()).hexdigest()[:6]}")
        orig = open(base).read().split()
        dif, ruido = diferentes(md5s, orig), len(orig) - exatos(md5s, orig)
        medida = (f"{dif} quadros diferentes" if dif else "idênticos" if not ruido
                  else f"iguais dentro da tolerância ({ruido} quadros com ruído de render)")
        return (mp4, len(orig), medida,
                f"o molde mudou: com os padrões, a prévia não é mais igual ao clone original ({dif} de {len(orig)} quadros diferentes)" if dif else None)
    conferir = getattr(mt, "conferir_versao", None) or getattr(mt, "conferir_molde", None)
    if not conferir:
        raise Falha(f"não sei provar que o molde '{nome}' com os padrões é o clone original", "FALTA_ORIGINAL",
                    motivo="trave o molde (montar.py --travar) ou acrescente-o em ORIGINAL_DO_MOLDE no portao.py")
    versao, aviso = conferir()
    aviso = "; ".join(aviso) if isinstance(aviso, list) else aviso
    return (mt.ORIGINAL, quadros_e_fps(mt.ORIGINAL)[0], f"molde travado {versao}" if not aviso else "molde editado",
            f"o molde mudou: {aviso}" if aviso else None)


def check(mt, proj):
    momentos = ",".join(f"{n / mt.FPS:.3f}" for n in mt.MOMENTOS)  # as peças paradas e visíveis
    r = subprocess.run(mt.HF + ["check", "--json", "--no-contrast", "--at", momentos, "."], cwd=proj, capture_output=True, text=True)
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise Falha(f"o check do HyperFrames não rodou em {proj}: {r.stderr[-600:]}", "CHECK_FALHOU")


def achados(j):
    return [(f["code"], f.get("time") or 0, f.get("selector"), f.get("text") or "")
            for s in ("layout", "craft") for f in j.get(s, {}).get("findings", []) if f["code"] in TEXTO]  # 0.8.184 não tem craft


def novos(base, versao):
    """Achados de texto que só a versão tem. Bate por momento e (seletor ou texto): título com mais palavras desloca os seletores."""
    return [a for a in versao if not any(b[0] == a[0] and b[1] == a[1] and (b[2] == a[2] or b[3] == a[3]) for b in base)]


def cinza(mp4, lado=360):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", f"scale={lado}:{lado}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(-1, lado, lado).astype(np.int16)


def razao_blur(final, previa_mp4):
    """Diferença final x prévia onde a prévia se mexe, dividida pela diferença onde ela está parada. Sem blur dá ~1."""
    a, b = cinza(final), cinza(previa_mp4)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    mov = np.zeros(b.shape, bool)
    mov[1:] = np.abs(np.diff(b, axis=0)) > 12
    d = np.abs(a - b)
    return float(d[mov].mean() / max(d[~mov].mean(), 0.05)) if mov.any() else 0.0


def matiz(rgb):
    """Matiz HSV em graus de uma lista N x 3 de cores em 0..1."""
    r, g, b = rgb.T
    mx = rgb.max(1)
    c = mx - rgb.min(1) + 1e-9
    return np.where(mx == r, (g - b) / c % 6, np.where(mx == g, (b - r) / c + 2, (r - g) / c + 4)) * 60


def matiz_hex(h):
    return float(matiz(np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]]))[0])


def matizes(mp4):
    """Histograma de matiz (36 faixas de 10°) dos pixels saturados, a 10 quadros por segundo."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-vf", "fps=10,scale=270:270", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, 3).astype(np.float32) / 255
    mx, mn = f.max(1), f.min(1)
    ok = (mx - mn > 0.25) & (mx > 0.3)
    return np.bincount((matiz(f[ok]) // 10).astype(int) % 36, minlength=36) / max(int(ok.sum()), 1)


def fora_da_paleta(hist_padrao, hist_versao, cores, principal_padrao=None):
    """Faixas de matiz (graus) da versão que não estão no molde nem perto (±40°) das cores da versão.
    Os verdes do molde giram com cor_principal, então saem da lista do molde (±40° da cor padrão)."""
    verde = matiz_hex(principal_padrao) if principal_padrao else None
    ok = {i for i, v in enumerate(hist_padrao)
          if v > 0.003 and (verde is None or abs((i * 10 + 5 - verde + 180) % 360 - 180) > 40)}
    for c in cores:
        h = matiz_hex(c)
        ok |= {int((h + d) // 10) % 36 for d in range(-40, 41, 5)}  # mesma janela da exclusão acima, senão a borda do verde padrão reprova o original
    return [i * 10 for i, v in enumerate(hist_versao) if v > 0.005 and i not in ok]


def ler_compare(txt):
    num = lambda rot: float(re.search(rot + r":\s*([\d.]+)", txt).group(1))
    lags = [(c[1].strip(), int(c[5])) for c in (l.split("|") for l in txt.splitlines())
            if len(c) == 8 and c[2].strip().startswith("f") and c[5].strip().lstrip("-").isdigit()]
    cena, lag = max(lags, key=lambda x: abs(x[1]), default=("", 0))
    cortes = re.search(r"within 2 frames:\s*(\d+/\d+)", txt)
    return {"distancia": num("Mean visual distance"), "correlacao": num("Motion-curve correlation"),
            "movimento": num("Total motion vs reference"), "lag": lag, "cena_lag": cena, "cortes": cortes.group(1) if cortes else ""}


def portao_clone(mp4, clones):
    pasta = os.path.dirname(mp4)
    ref = os.path.join(pasta, "reference", "analysis")
    if not os.path.exists(os.path.join(ref, "analysis.json")):
        raise Falha(f"não achei a análise da referência em {ref}", "FALTA_ANALISE_DA_REFERENCIA",
                    comando=shlex.join(["python3", os.path.join(SCRIPTS, "burst.py"), os.path.join(pasta, "reference", "ref.mp4"), ref]),
                    motivo="o portão compara o clone com a análise da referência")
    espaco()
    out = os.path.join(TRABALHO, "compare-" + os.path.basename(pasta))
    sh([sys.executable, os.path.join(SCRIPTS, "burst.py"), mp4, out + "-analise"])
    sh([sys.executable, os.path.join(SCRIPTS, "compare.py"), ref, out + "-analise", out])
    n = ler_compare(open(os.path.join(out, "COMPARE.md"), encoding="utf-8").read())
    motivos = []
    if clones:
        bd, bc = min(c["distancia"] for c in clones), max(c["correlacao"] for c in clones)
        if n["distancia"] > bd + TOL_DIST:
            motivos.append(f"a imagem ficou mais longe da referência (distância {n['distancia']:.3f}) do que o melhor clone "
                           f"aprovado permite ({bd:.3f} mais {TOL_DIST} de folga)")
        if n["correlacao"] < bc - TOL_CORR:
            motivos.append(f"o ritmo dos movimentos bate menos com a referência (correlação {n['correlacao']:.3f}) do que o "
                           f"melhor clone aprovado permite ({bc:.3f} menos {TOL_CORR} de folga)")
    if abs(n["lag"]) > LAG_MAX:
        motivos.append(f"o pico de movimento da cena {n['cena_lag']} está {abs(n['lag'])} quadros "
                       f"{'atrasado' if n['lag'] > 0 else 'adiantado'} (o máximo é {LAG_MAX})")
    return motivos, n


def portao_versao(mp4, versao, molde, so_previa=False):
    mt = montar_de(molde)
    try:
        valores = json.load(open(versao, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"não consegui ler a versão {versao}: {e}"], {}, None
    lista = declaracao(molde)[2]
    decl = {d["id"]: d for d in lista}
    erros = mt.validar(valores, decl)
    if erros:
        return ["a versão não vale: " + e for e in erros], {}, None
    motivos, med = [], {}
    nome = os.path.splitext(os.path.basename(mp4))[0]

    # 1. regressão: o molde com os padrões tem que continuar sendo o clone
    ref_mp4, esperados, med["padrões x original"], mudou = padroes(molde)
    if mudou:
        motivos.append(mudou)

    # 2. check do HyperFrames: erro de código, e texto que só a versão corta ou encolhe
    pasta = os.path.join(TRABALHO, "check-" + nome)
    estrutura = {k: v for k, v in valores.items() if decl[k]["type"] in ("enum", "boolean")}  # mesmas peças, textos originais
    jv = check(mt, copia(molde, pasta + "-versao", valores))
    jb = check(mt, copia(molde, pasta + "-base", estrutura))
    erros = [f["message"][:140] for s in ("lint", "runtime") for f in jv.get(s, {}).get("findings", []) if f["severity"] == "error"]
    if erros:
        motivos.append(f"o check do HyperFrames acusou {len(erros)} erro(s) de código: " + "; ".join(erros))
    textos = novos(achados(jb), achados(jv))
    med["textos com problema"] = len(textos)
    for c, t, _, txt in textos:
        motivos.append(f"{TEXTO[c]}: \"{txt[:60]}\" aos {t:.1f} s")
    shutil.rmtree(pasta + "-versao")
    shutil.rmtree(pasta + "-base")

    # 3. quadros e duração iguais aos do molde. A régua é uma prévia; o final pode ter um quadro a menos, porque o
    # último grupo de subquadros do motion blur fica incompleto (Joi: prévia 452, final 451)
    nq, fps = quadros_e_fps(mp4)
    med["quadros"] = f"{nq} de {esperados} a {fps:g} fps"
    if nq not in ((esperados,) if so_previa else (esperados, esperados - 1)) or abs(fps - mt.FPS) > 0.01:
        motivos.append(f"o vídeo tem {nq} quadros a {fps:g} fps ({nq / fps:.2f} s); o molde tem {esperados} quadros "
                       f"a {mt.FPS} fps ({esperados / mt.FPS:.2f} s)")

    # 4. motion blur: o final tem que diferir da prévia da mesma versão justamente onde há movimento
    vmd5 = None
    if so_previa:
        med["motion blur"] = "não se aplica (prévia)"
    else:
        vp, vmd5 = previa(mt, molde, valores, "versao-" + nome)
        rb = razao_blur(mp4, vp)
        med["motion blur"] = f"{rb:.1f}x"
        if rb < BLUR_MIN:
            motivos.append(f"sem motion blur: nos trechos de movimento o vídeo está igual à prévia ({rb:.1f}x, o mínimo é "
                           f"{BLUR_MIN}x). Renderize o final, não a prévia")

    # 5. cores: só as do molde e as escolhidas na versão
    cores = [valores.get(d["id"], d["default"]) for d in lista if d["type"] == "color"]
    fora = fora_da_paleta(matizes(ref_mp4), matizes(mp4), cores, decl.get("cor_principal", {}).get("default"))
    med["cores fora da paleta"] = len(fora)
    if fora:
        motivos.append("cores fora da paleta da versão, matiz em graus: " + ", ".join(f"{h}°" for h in fora))
    return motivos, med, vmd5


def sha256(caminho):
    return hashlib.sha256(open(caminho, "rb").read()).hexdigest()


def integridade(raiz=None):
    """Avisos para cada versão travada do perfil (perfil-v1, perfil-v2...) cujos arquivos não batem com a impressão digital."""
    raiz, avisos = raiz or PERFIL_DIR, []
    for pasta in sorted(d for d in os.listdir(raiz) if re.fullmatch(r"perfil-v\d+", d)) if os.path.isdir(raiz) else []:
        try:
            digital = json.load(open(os.path.join(raiz, pasta, "impressao_digital.json"), encoding="utf-8"))["sha256"]
        except (OSError, ValueError, KeyError):
            avisos.append(f"{pasta} perdeu a integridade: a impressao_digital.json sumiu ou foi estragada")
            continue
        for nome, h in digital.items():
            f = os.path.join(raiz, pasta, nome)
            if not os.path.exists(f) or sha256(f) != h:
                avisos.append(f"{pasta} perdeu a integridade: {nome} foi editado à mão depois de travado")
    return avisos


def versao_padrao(mp4, molde):
    nome = os.path.splitext(os.path.basename(mp4))[0].removesuffix("-previa")
    return os.path.join(os.path.dirname(os.path.abspath(molde)), "versoes", nome + ".json")


def rodar(mp4, tipo, versao, molde, clones, so_previa=False):
    """(motivos, medidas, assinaturas da prévia da versão ou None). Motivos vazios = PASSOU."""
    if tipo == "clone":
        return (*portao_clone(mp4, clones), None)
    return portao_versao(mp4, versao, molde, so_previa)  # versao e video-novo: os dois saem de um molde


def laudo(mp4, tipo, motivos, med):
    """O resultado do portão como dados: veredito, motivos, medidas e avisos de integridade."""
    if "distancia" in med:  # números do compare.py
        med = {"distância": f"{med['distancia']:.3f}", "correlação": f"{med['correlacao']:.3f}", "movimento": f"{med['movimento']:.2f}x",
               "pico de movimento": f"{abs(med['lag'])} quadro(s) na pior cena ({med['cena_lag']})", "cortes": med["cortes"]}
    return {"video": os.path.relpath(mp4, RASCUNHO) if mp4.startswith(RASCUNHO) else mp4, "tipo": tipo,
            "veredito": "REPROVOU" if motivos else "PASSOU", "motivos": motivos, "medidas": med, "avisos": integridade()}


def autoteste():
    cmp = ("Mean visual distance: 0.010 (0 identical)\nMotion-curve correlation: 0.981 (1.0)\nTotal motion vs reference: 0.94x\n"
           "Reference cuts matched within 2 frames: 2/2\n| shot | frames | distance | motion corr | lag | ratio |\n|---|---|---|---|---|---|\n"
           "| 1 | f0-9 | 0.007 | 0.99 | 0 | 0.87 |\n| 2.2 | f70-122 | 0.013 | 0.97 | -2 | 1.01 |\n| 3.4 (static) | f303-327 | 0.005 | nan |  | nan |\n")
    n = ler_compare(cmp)
    assert (n["distancia"], n["correlacao"], n["movimento"], n["lag"], n["cena_lag"], n["cortes"]) == (0.010, 0.981, 0.94, -2, "2.2", "2/2")
    base = [("text_box_overflow", 5.8, "#a > div:nth-of-type(2)", "Fire"), ("text_box_overflow", 8.3, "#a > div:nth-of-type(14)", "🚑")]
    versao = [("text_box_overflow", 5.8, "#a > div:nth-of-type(2)", "Incêndio"),  # mesmo seletor: já era assim no molde
              ("text_box_overflow", 8.3, "#a > div:nth-of-type(15)", "🚑"),       # seletor deslocado, mesmo texto
              ("text_box_overflow", 7.0, "#a > div:nth-of-type(6)", "Problema no carro com o motor")]
    assert novos(base, versao) == versao[2:]
    assert achados({"layout": {"findings": [{"code": "text_box_overflow", "time": 1, "selector": "x", "text": "a"}]}}) == [("text_box_overflow", 1, "x", "a")]
    padrao = np.zeros(36)
    padrao[[12, 21, 4]] = 0.3  # verde, azul e amarelo do molde
    assert fora_da_paleta(padrao, padrao, ["#0cbc25"], "#0cbc25") == []
    borda = padrao.copy()
    borda[16] = 0.01  # 165°: borda do verde padrão no Satellite original
    assert fora_da_paleta(borda, borda, ["#0cbc25"], "#0cbc25") == []
    laranja = padrao.copy()
    laranja[12], laranja[1] = 0, 0.3
    assert fora_da_paleta(padrao, laranja, ["#E54A26"], "#0cbc25") == []
    assert fora_da_paleta(padrao, padrao, ["#E54A26"], "#0cbc25") == [120]  # pediu laranja e o verde ficou
    assert diferentes(["a", "b", "c"], ["a", "x", "c", "d"]) == 2  # régua antiga, só md5: exata
    q = lambda h, m: f"{h}:{base64.b64encode(zlib.compress(np.asarray(m, np.uint8).tobytes())).decode()}"
    z = np.full(LADO * LADO, 200)
    ruido, mudou = z.copy(), z.copy()
    ruido[:50] += TOL_QUADRO
    mudou[7] -= TOL_QUADRO + 1
    assert igual(q("a", z), q("a", mudou)) and igual(q("a", z), q("b", ruido)) and not igual(q("a", z), q("b", mudou))
    assert not igual(q("a", z), "b") and diferentes([q("a", z), q("x", z)], [q("b", ruido), q("y", mudou)]) == 1
    assert exatos([q("a", z), q("x", z)], [q("a", ruido), "y"]) == 1
    assert round(matiz_hex("#0cbc25")) == 129 and round(matiz_hex("#E54A26")) == 11
    assert [nome_do_molde(m) for m in ("/r/moldes/satellite", "/r/moldes/joi/molde", "/r/moldes/voiceos/molde/")] == ["satellite", "joi", "voiceos"]


def main():
    autoteste()
    ap = Args(prog="portao.py", description="a catraca: PASSOU ou REPROVOU")
    ap.add_argument("mp4")
    ap.add_argument("--tipo", required=True, choices=["clone", "versao", "video-novo"])
    ap.add_argument("--versao", help="JSON da versão (padrão: versoes/<nome do mp4>.json ao lado do molde)")
    ap.add_argument("--molde", default=os.path.join(RAIZ, "moldes", "satellite", "molde"))
    ap.add_argument("--previa", action="store_true", help="o vídeo é uma prévia: confere tudo menos o motion blur")
    a = ap.parse_args()
    import aprender  # a régua dos clones vem do perfil de estilo
    mp4, molde = os.path.abspath(a.mp4), os.path.abspath(a.molde)
    if not os.path.exists(mp4):
        raise Falha(f"não achei o vídeo {mp4}", "VIDEO_NAO_ENCONTRADO", uso=True)
    if a.previa and a.tipo == "clone":
        raise Falha("--previa vale para versão e vídeo novo, não para clone", "USO_ERRADO", uso=True)
    versao = None if a.tipo == "clone" else os.path.abspath(a.versao or versao_padrao(mp4, molde))
    motivos, med, _ = rodar(mp4, a.tipo, versao, molde, [r["compare"] for r in aprender.aprovados() if r["tipo"] == "clone"], a.previa)
    r = laudo(mp4, a.tipo, motivos, med)
    aviso = f" Atenção: {len(r['avisos'])} aviso(s) de integridade do perfil." if r["avisos"] else ""
    args = [a.mp4, "--tipo", a.tipo] + (["--versao", versao, "--molde", molde] if versao else [])
    if motivos:
        saida(f"REPROVOU no portão: {r['video']}. {motivos[0]}.{aviso}", comando("portao.py", *args, *(["--previa"] if a.previa else [])),
              "corrija os motivos e rode o portão de novo", True, "REPROVADO_NO_PORTAO", portao=r)
    if a.previa:
        saida(f"PASSOU no portão (prévia, sem conferir o motion blur): {r['video']}.{aviso}", "",
              "a prévia passou; o registro no perfil é com o final, pelo aprender.py aprovar", True, portao=r)
    saida(f"PASSOU no portão: {r['video']}.{aviso}", comando("aprender.py", "aprovar", *args, "--nota", "..."),
          "o portão não aprova nada: a aprovação é humana", True, portao=r)


if __name__ == "__main__":
    executar(main)
