#!/usr/bin/env python3
"""montar.py: o montador único dos moldes (Satellite, Joi e VoiceOS).

    python3 montar.py <versao.json> [--molde satellite|joi|voiceos] [--previa]
             [--marca <nome ou caminho>] [--video <pasta> | --saidas <pasta>]
    python3 montar.py <versao.json> --lote junior,padaria-exemplo [--video <pasta com {marca}>] [--previa]
    python3 montar.py --molde <molde> --travar [<molde>-vN]     # --registrar-molde é o mesmo comando
    python3 montar.py --molde voiceos --provar                   # os padrões do molde são o clone, pixel a pixel

O molde vem de --molde ou da chave "molde" da versão ("satellite", ou "satellite-v2" para dizer a versão do molde).
Final: alta taxa (240 fps) + tmix (motion blur real) + ganho de luma. Prévia: o fps do molde, sem motion blur.

Valores: vale a versão, depois a marca, depois o molde. A marca vem de --marca ou da chave "marca" da versão: um nome
(junior, padaria-exemplo) ou um caminho, relativo à pasta da versão, à pasta atual ou à raiz do produto. Os dois formatos de kit
valem: marcas/<cliente>/marca.json (novo) e marcas/<nome>.json (antigo).

Saídas:
  - sem --video, como sempre: em --saidas (padrão: saidas/ do molde), com o nome do arquivo de versão;
  - com --video <pasta>: em <pasta>/saidas/, com o nome do vídeo (<cliente>-<video> quando a pasta é
    marcas/<cliente>/videos/<video>/). O bastidor vai para <pasta>/.apple-style-ui/<data>-<tipo>-<sufixo>/ (um por render, dá para
    rodar dois clientes ao mesmo tempo) e nada é sobrescrito: o arquivo que já existe ganha a data dele no nome.
  Sempre: <nome>.mp4, <nome>-lado-a-lado.mp4 (original | versão, só com o vídeo do clone na máquina) e <nome>-folha.jpg.
  Com --previa os nomes ganham "-previa". A versão resolvida (sem "marca" nem "molde"), que é a que o portão lê, fica
  em <pasta>/.apple-style-ui/versao-resolvida.json (sem --video, no bastidor) e volta no JSON em "versao_resolvida".
  Lote: cada marca no seu vídeo; sem --video, marcas/{marca}/videos/<nome da versão>/ a partir da pasta atual.

Contrato: o stdout traz um único JSON {"ok": true, "resumo", "proximo": {"comando", "motivo", "precisa_de_voce"},
"arquivos", ...}; o log humano vai para o stderr. Em erro, o stderr termina com {"ok": false, "erro", "codigo"}.
Saída 0 = ok, 1 = erro, 2 = uso errado.
"""
import glob, hashlib, json, os, re, shlex, shutil, subprocess, sys, tempfile, time

AQUI = os.path.dirname(os.path.abspath(__file__))
EU = os.path.join(AQUI, "montar.py")
NOME = "apple-style-ui"         # o nome do produto, uma constante só: dele saem ~/.apple-style-ui/ e o bastidor .apple-style-ui/
MOLDES_DIR = os.path.join(AQUI, "moldes")
MAQUINA = os.path.expanduser(f"~/.{NOME}")
# o vídeo do clone de cada molde não vai no repositório (é recorte de terceiro): quem tem o clone põe em
# ~/.apple-style-ui/originais/<molde>.mp4 e o lado a lado volta; sem ele, sai só a versão
ORIGINAIS = os.path.join(MAQUINA, "originais")
# SF Pro: a fonte não vai no repositório. Na hora do render, a cópia do molde recebe a do sistema (macOS); sem ela, ou
# com ASUI_FONTE_LIVRE=1, recebe a Inter (SIL OFL), que mora no molde do Satellite
SF_SISTEMA = "/System/Library/Fonts/SFNS.ttf"
INTER = os.path.join(MOLDES_DIR, "satellite", "molde", "assets", "fonts", "Inter.ttf")
SILENCIO = os.path.join("assets", "silencio.m4a")  # o áudio padrão dos moldes (o do original não vai no repositório)
X264 = ["-c:v", "libx264", "-preset", "veryslow", "-tune", "animation", "-crf", "12", "-refs", "4", "-level:v", "5.1",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart"]  # sem -refs 4 -level:v 5.1 o QuickTime embaralha os blocos
GAIN = 1.008                    # o encode do HyperFrames sai ~0,8 % escuro no luma (round_mb_fix.sh)
TRAVESSAO = re.compile("[—–]")
ARQUIVOS = ("musica", "logo")   # variáveis que são caminho de arquivo: a música mora no molde; o logo pode vir de fora (do kit)
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp")
REGRAS = {"relogio": (r"\d{1,2}:[0-5]\d", "tem que ser M:SS ou MM:SS"),
          "digitos": (r"\d{5}", "tem que ter exatamente 5 dígitos, um por casa do calendário")}
KIT_CAMPOS = ("cor_principal", "cor_destaque", "fonte", "nome", "logo", "creditos")
KIT_OBRIGATORIO = ("cor_principal", "fonte", "nome")

# Um bloco por molde: o que muda entre eles. Kit: campo do kit de marca -> variáveis do molde ("creditos" não vira variável).
MOLDES = {
    "satellite": dict(
        pasta=os.path.join(MOLDES_DIR, "satellite"), molde=os.path.join(MOLDES_DIR, "satellite", "molde"),
        trava=os.path.join(MOLDES_DIR, "satellite", "MOLDE.json"),
        original=os.path.join(ORIGINAIS, "satellite.mp4"), clone_hf=os.path.join(ORIGINAIS, "satellite-hf"), trabalho="satellite",
        hf="0.8.185", fps=30, n=8, nf=328, lut="", largura=1080, altura=1080, rotulo=30, quadro=(360, 360),
        momentos=[15, 40, 75, 100, 135, 175, 210, 250, 300],  # as 9 peças de hq/pecas-do-satellite.jpg
        lado_na_previa=True, leve=False, provar=False,
        kit={"cor_principal": ["cor_principal"], "cor_destaque": ["cor_ponto", "cor_rota"], "fonte": ["fonte"],
             "nome": ["balao_nome"], "logo": ["logo"]}),
    "joi": dict(
        pasta=os.path.join(MOLDES_DIR, "joi"), molde=os.path.join(MOLDES_DIR, "joi", "molde"), trava=os.path.join(MOLDES_DIR, "joi", "MOLDE.json"),
        original=os.path.join(ORIGINAIS, "joi.mp4"),  # o clone v6 (60 fps, 451 quadros)
        clone_hf=os.path.join(ORIGINAIS, "joi-hf"), trabalho="joi",
        hf="0.8.184", fps=60, n=4, nf=451, largura=1080, altura=1920, rotulo=40, quadro=(216, 384),
        # segunda LUT de luma do Joi (round_mb_fix.sh, v3+): Y cru medido em fundos lisos (27->29 no escuro, 233->234 no claro)
        lut="lutyuv=y='clip(val+0.5+if(lt(val\\,73)\\,2\\,if(lt(val\\,154)\\,2*(154-val)/81\\,if(lt(val\\,233)\\,0\\,1)))\\,0\\,255)'",
        momentos=[30, 88, 150, 178, 230, 262, 300, 340, 360, 450],  # ícone, pílula, lista, menu, risco, frase, cartão, fim
        # o nome da marca vai no rótulo do ícone, onde o original diz "Joi" (o padrão do molde continua "Joi")
        # o logo da marca entra no lugar da estrela do cartão azul
        lado_na_previa=True, leve=False, provar=False,
        kit={"cor_principal": ["cor_principal"], "nome": ["icone_texto"], "fonte": ["fonte"], "logo": ["logo"]}),
    "voiceos": dict(
        pasta=os.path.join(MOLDES_DIR, "voiceos"), molde=os.path.join(MOLDES_DIR, "voiceos", "molde"),
        trava=os.path.join(MOLDES_DIR, "voiceos", "MOLDE.json"), original=os.path.join(ORIGINAIS, "voiceos.mp4"),
        clone_hf=os.path.join(ORIGINAIS, "voiceos-hf"), trabalho="voiceos",
        hf="0.8.184", fps=60, n=4, nf=700, lut="", largura=1920, altura=1080, rotulo=34, quadro=(400, 225),
        momentos=[40, 110, 175, 228, 330, 430, 470, 555, 640],  # céu, dock, ditado, Send, título, linhas, caixa, tecla, logo
        # o nome vai na legenda do logo final e o logo da marca entra no lugar do triângulo do logo VO
        lado_na_previa=False, leve=True, provar=True,
        kit={"cor_principal": ["cor_destaque"], "nome": ["legenda_logo"], "fonte": ["fonte"], "logo": ["logo"]}),
}
for _n, _c in MOLDES.items():
    _c["nome"] = _n
    _c["travadas"] = os.path.join(_c["pasta"], "versoes-travadas")  # uma pasta por versão travada: <molde>-vN/

# Só do Satellite: ritmo pelas batidas, 9:16 e sons por elemento
SAT_FPS, SAT_NF = 30, 328
# os 8 momentos: (quadro em que começa no clone, quadros da entrada com mola, nome). São os mesmos inícios da mola firme
ENTRADAS = [(5, 19, "ícone"), (30, 21, "cartão"), (86, 22, "tile"), (127, 63, "lista"), (155, 35, "título"), (194, 19, "rota"), (213, 42, "ilha"), (277, 23, "balão")]
MEIO_MIN = 4                    # quadros mínimos do "meio" de um momento, no clone e na saída
# 9:16: o HyperFrames lê o tamanho do arquivo, então a cópia de render ganha 1080x1920 (o layout vem da variável formato)
VERTICAL = [('data-resolution="square"', 'data-resolution="portrait"'), ('content="width=1080, height=1080"', 'content="width=1080, height=1920"'),
            ("html, body { width: 1080px; height: 1080px;", "html, body { width: 1080px; height: 1920px;"),
            ('data-width="1080" data-height="1080"', 'data-width="1080" data-height="1920"')]
OY = 210                        # 9:16: deslocamento da cena quadrada (o mesmo do index.html)
SONS = os.path.join(AQUI, "sons")  # o pacote de sons (sons.json + .wav); o mapa evento -> som é satellite/sons.json
SONS_DB = {"suave": -4, "marcado": 0}   # nível dos efeitos, somado ao ganho de cada tipo
LUFS_ALVO = -14.1               # loudness integrada dos três originais (Satellite, Joi e VoiceOS, medida com ebur128)
BATIDA_DB = -6                  # efeito que cai em cima de um golpe da música desce 6 dB, para não somar com ele
# tecla a tecla: (ganho em dB, velocidade) em rodízio, para a digitação não soar como a mesma tecla repetida
TECLAS = [(0, 1.0), (-2, 1.06), (-1, 0.94), (-3, 1.03), (-1.5, 0.97)]
KM_FIRME = 0.6                  # a mola firme assenta em 60 % do tempo (o mesmo KM do index.html)


class Falha(Exception):
    """Erro com código para o JSON do stderr. saida: 1 = erro, 2 = uso errado."""
    def __init__(self, erro, codigo, saida=1):
        super().__init__(erro)
        self.erro, self.codigo, self.saida = erro, codigo, saida


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def hf(c):
    return ["npx", "--yes", f"hyperframes@{c['hf']}"]


def trabalho(c):
    """Bastidor sem --video: a pasta temporária do sistema."""
    p = os.path.join(tempfile.gettempdir(), NOME, c["trabalho"])
    os.makedirs(p, exist_ok=True)
    return p


# ---------------------------------------------------------------- variáveis, marca e validação
def declaradas(c):
    html = open(os.path.join(c["molde"], "index.html"), encoding="utf-8").read()
    m = re.search(r"data-composition-variables='(.*?)'", html, re.S)
    return {d["id"]: d for d in json.loads(m.group(1))}


def achar_imagem(v, c, base):
    """(caminho_no_disco, dentro_do_molde) ou (None, erro). data:image/ passa direto (None, None)."""
    if v.startswith("data:image/"):
        return None, None
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", v):
        return None, f"use um arquivo local ou data:image/ (veio {v[:60]!r})"
    if not v.lower().endswith(IMG_EXT):
        return None, f"a imagem tem que ser {', '.join(IMG_EXT)} (veio {v!r})"
    dentro = os.path.normpath(os.path.join(c["molde"], v))
    if not os.path.isabs(v) and dentro.startswith(c["molde"] + os.sep) and os.path.isfile(dentro):
        return dentro, True
    for p in ([v] if os.path.isabs(v) else [os.path.join(base, v), os.path.abspath(v)]):
        if os.path.isfile(p):
            return p, False
    return None, f"arquivo não encontrado: {v!r} (procurei no molde, ao lado do arquivo de versão e em {os.getcwd()})"


def validar(valores, decl, c, base=None):
    """Lista de erros (vazia = ok). Mesmas regras do --strict-variables do HyperFrames, mais as do projeto."""
    if not isinstance(valores, dict):
        return ["o arquivo de versão tem que ser um objeto JSON {\"variavel\": valor}"]
    erros = []
    for k, v in valores.items():
        d = decl.get(k)
        if d is None:
            erros.append(f"'{k}' não existe no molde. As variáveis são: {', '.join(decl)}")
            continue
        t = d["type"]
        if t == "string":
            if not isinstance(v, str) or (not v.strip() and k != "logo"):
                erros.append(f"'{k}' tem que ser um texto não vazio (veio {v!r})")
            elif TRAVESSAO.search(v):
                erros.append(f"'{k}' tem travessão: {v!r}. Troque por vírgula, ponto ou dois-pontos")
            elif k == "logo" and v:  # o logo pode morar fora do molde (marcas/<cliente>/logo.png): vai para a cópia de render
                erro = achar_imagem(v, c, base or c["pasta"])[1]
                if isinstance(erro, str):
                    erros.append(f"'logo': {erro}")
            elif k in ARQUIVOS and v:
                real = os.path.realpath(os.path.join(c["molde"], v))
                if not real.startswith(os.path.realpath(c["molde"]) + os.sep) or not os.path.isfile(real):
                    erros.append(f"'{k}' = {v!r}: o arquivo tem que existir dentro de {os.path.basename(c['molde'])}/ (ex.: assets/arquivo.m4a)")
        elif t == "color":
            if not (isinstance(v, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", v)):
                erros.append(f"'{k}' tem que ser uma cor no formato #rrggbb (veio {v!r})")
        elif t == "boolean":
            if not isinstance(v, bool):
                erros.append(f"'{k}' tem que ser true ou false (veio {v!r})")
        elif t == "number":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not d.get("min", v) <= v <= d.get("max", v):
                erros.append(f"'{k}' tem que ser um número de {d.get('min')} a {d.get('max')} (veio {v!r})")
        elif t == "enum":
            ok = [o["value"] for o in d["options"]]
            if v not in ok:
                erros.append(f"'{k}' = {v!r} não é uma opção. Opções: {' '.join(ok)}")
        elif t == "image":
            u = v.get("url") if isinstance(v, dict) else v
            if not isinstance(u, str) or not u.strip():
                erros.append(f"'{k}' tem que ser o caminho de uma imagem (ou {{\"url\": caminho}}) (veio {v!r})")
            else:
                erro = achar_imagem(u, c, base or c["pasta"])[1]
                if isinstance(erro, str):
                    erros.append(f"'{k}': {erro}")
    for k, (rx, msg) in REGRAS.items():
        if k in decl and isinstance(valores.get(k), str) and not re.fullmatch(rx, valores[k]):
            erros.append(f"'{k}' {msg} (veio {valores[k]!r})")
    return erros


def achar_marca(ref, base=None):
    """Caminho absoluto do kit, ou None. ref é um nome (junior, padaria-exemplo) ou um caminho (arquivo ou pasta do
    cliente). Procura a partir da pasta da versão, da pasta atual e da raiz do produto, nos dois formatos de kit."""
    if not isinstance(ref, str) or not ref.strip():
        return None
    nome = os.sep not in ref and not ref.endswith(".json")
    for raiz in [r for r in (base, os.getcwd(), AQUI) if r]:
        p = os.path.join(raiz, ref)
        cands = [p, os.path.join(p, "marca.json")]
        if nome:
            cands += [os.path.join(raiz, "marcas", ref, "marca.json"), os.path.join(raiz, "marcas", ref + ".json")]
        for x in cands:
            if os.path.isfile(x):
                return os.path.abspath(x)
    return None


def nome_da_marca(caminho):
    """padaria-exemplo para marcas/padaria-exemplo/marca.json; junior para marcas/junior.json."""
    b = os.path.basename(caminho)
    return os.path.basename(os.path.dirname(caminho)) if b == "marca.json" else os.path.splitext(b)[0]


def carregar(valores, decl, c, base=None, marca=None):
    """Resolve versão -> marca -> molde. --marca (marca=) vence a "marca" da versão; "molde" sai (não é variável).
    Devolve (valores, erros, info), com info = {"marca": caminho, "nome_marca", "kit_sem_uso": campos que o molde não usa}."""
    if not isinstance(valores, dict):
        return valores, validar(valores, decl, c, base), {}
    v = dict(valores)
    v.pop("molde", None)
    ref = v.pop("marca", None)
    if marca is not None:
        ref = marca  # --marca vence a "marca" da versão
    erros = validar(v, decl, c, base)
    if ref is None:
        return v, erros, {}
    caminho = achar_marca(ref, base)
    if not caminho:
        return v, erros + [f"não achei a marca {ref!r} (procurei ao lado da versão, na pasta atual e em {AQUI}, "
                           f"como marcas/<nome>/marca.json e marcas/<nome>.json)"], {}
    try:
        kit = json.load(open(caminho, encoding="utf-8"))
    except (OSError, ValueError) as e:
        return v, erros + [f"não consegui ler a marca {caminho}: {e}"], {}
    if not isinstance(kit, dict):
        return v, erros + [f"a marca {caminho} tem que ser um objeto JSON"], {}
    erros += [f"marca {caminho}: '{k}' não é campo de marca. Campos: {', '.join(KIT_CAMPOS)}" for k in kit if k not in KIT_CAMPOS]
    erros += [f"marca {caminho}: falta '{k}'" for k in KIT_OBRIGATORIO if k not in kit]
    cr = kit.get("creditos", {})
    if not (isinstance(cr, dict) and all(isinstance(t, str) and t.strip() for t in cr.values())):
        erros.append(f"marca {caminho}: 'creditos' tem que ser um objeto {{\"asset\": \"autor e licença\"}}")
    do_kit = {var: kit[k] for k, vs in c["kit"].items() if k in kit for var in vs}
    erros += [f"marca {caminho}: {e}" for e in validar(do_kit, decl, c, os.path.dirname(caminho))]
    if isinstance(do_kit.get("logo"), str) and do_kit["logo"]:  # o logo do kit é relativo à pasta do kit
        achado = achar_imagem(do_kit["logo"], c, os.path.dirname(caminho))[0]
        do_kit["logo"] = achado or do_kit["logo"]
    info = {"marca": caminho, "nome_marca": nome_da_marca(caminho),
            "kit_sem_uso": [k for k in kit if k in KIT_CAMPOS and k != "creditos" and k not in c["kit"]]}
    return {**do_kit, **v}, erros, info  # o que está escrito na versão vence


def preparar_imagens(valores, decl, c, base, proj):
    """Copia as imagens de fora do molde (as do VoiceOS e o logo) para proj/assets/var/ e troca o valor pelo caminho relativo."""
    for k, v in list(valores.items()):
        if decl[k]["type"] != "image" and not (k == "logo" and v):
            continue
        u = v.get("url") if isinstance(v, dict) else v
        caminho, dentro = achar_imagem(u, c, base)
        if caminho is None or dentro:
            valores[k] = u
            continue
        os.makedirs(os.path.join(proj, "assets", "var"), exist_ok=True)
        rel = f"assets/var/{k}{os.path.splitext(caminho)[1].lower()}"
        shutil.copyfile(caminho, os.path.join(proj, rel))
        valores[k] = rel
    return valores


# ---------------------------------------------------------------- versão travada do molde
def impressao_digital(c):
    """sha256 de cada arquivo do molde (sem o MOLDE.json, arquivos ocultos e caches do HyperFrames)."""
    out = {}
    for raiz, pastas, arqs in os.walk(c["molde"]):
        pastas[:] = sorted(p for p in pastas if not p.startswith(".") and p != "renders")
        for a in sorted(arqs):
            p = os.path.join(raiz, a)
            if a.startswith(".") or p == c["trava"]:
                continue
            out[os.path.relpath(p, c["molde"])] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def ler_trava(c):
    try:
        return json.load(open(c["trava"], encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def conferir_molde(c):
    """(versão, aviso ou None). O aviso não bloqueia: o molde foi editado sem virar versão nova."""
    reg = ler_trava(c)
    if not reg:
        return None, f"o molde não tem versão travada ({c['trava']}). Rode: python3 {EU} --molde {c['nome']} --travar"
    agora, antes = impressao_digital(c), reg.get("impressao_digital", {})
    mudou = sorted(k for k in set(agora) | set(antes) if agora.get(k) != antes.get(k))
    if not mudou:
        return reg.get("versao"), None
    return reg.get("versao"), (f"o molde {reg.get('versao')} foi editado sem virar versão nova ({', '.join(mudou[:6])}"
                               f"{' ...' if len(mudou) > 6 else ''}). Se a mudança fica, rode python3 {EU} --molde {c['nome']} --travar")


def congelar(c, reg):
    """Copia o molde para versoes-travadas/<versão>/ com o registro dela (MOLDE.json), arquivos só leitura. Uma pasta
    que já existe nunca é reescrita. Devolve True quando criou a pasta."""
    pasta = os.path.join(c["travadas"], reg["versao"])
    if os.path.exists(pasta):
        return False
    shutil.copytree(c["molde"], pasta, ignore=shutil.ignore_patterns(".*", "renders", "MOLDE.json"))
    json.dump(reg, open(os.path.join(pasta, "MOLDE.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    for raiz, _, arqs in os.walk(pasta):
        for a in arqs:
            os.chmod(os.path.join(raiz, a), 0o444)
    return True


def travar(c, nome=None):
    """Grava a versão e a impressão digital do molde (MOLDE.json, a versão em vigor) e congela uma cópia em
    versoes-travadas/<molde>-vN/. Sem nome: o próximo número. Mesmo nome com outro conteúdo, ou uma pasta de versão que já
    existe: recusa. A versão em vigor sem pasta (travada antes das pastas) ganha a sua. Devolve (versão, gravou)."""
    atual, reg = impressao_digital(c), ler_trava(c)
    if nome is None:
        if reg.get("impressao_digital") == atual:
            return reg["versao"], congelar(c, reg)
        ns = [int(m.group(1)) for x in [reg.get("versao") or ""] + (os.listdir(c["travadas"]) if os.path.isdir(c["travadas"]) else [])
              for m in [re.fullmatch(rf"{c['nome']}-v(\d+)", x)] if m]
        nome = f"{c['nome']}-v{max(ns, default=0) + 1}"
    if not re.fullmatch(rf"{c['nome']}-v\d+", nome):
        raise Falha(f"a versão do molde tem que ser {c['nome']}-v<número> (veio {nome!r})", "VERSAO_DO_MOLDE_INVALIDA", 2)
    if reg.get("versao") == nome:
        if reg.get("impressao_digital") == atual:
            return nome, congelar(c, reg)
        raise Falha(f"o molde mudou e {nome} já existe com outro conteúdo: use um número novo", "VERSAO_DO_MOLDE_REPETIDA", 2)
    if os.path.exists(os.path.join(c["travadas"], nome)):
        raise Falha(f"versoes-travadas/{nome} já existe e versão travada não se reescreve: use um número novo", "VERSAO_DO_MOLDE_REPETIDA", 2)
    reg = {"versao": nome, "travado_em": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "impressao_digital": atual}
    json.dump(reg, open(c["trava"], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    open(c["trava"], "a").write("\n")
    congelar(c, reg)
    return nome, True


def molde_pedido(c, pedido):
    """O molde de uma versão que pede outra versão do molde ("joi-v1"): a pasta congelada dela, ou None."""
    pasta = os.path.join(c["travadas"], pedido) if isinstance(pedido, str) and re.fullmatch(rf"{c['nome']}-v\d+", pedido) else None
    if pasta and os.path.isfile(os.path.join(pasta, "index.html")):
        return dict(c, molde=pasta, trava=os.path.join(pasta, "MOLDE.json"))
    return None


# ---------------------------------------------------------------- Satellite: ritmo e sons
def grade_de_sinal(x, sr, hop=256):
    """Grade regular de batidas (período s, fase s) de um sinal mono: onset por fluxo espectral e o pente (período
    entre 0,25 e 0,5 s, pulso de 120 a 240 por minuto) que soma mais onset, com tolerância de ±23 ms por batida.
    Sem a tolerância, música com swing puxa a fase para o contratempo (testado contra o hyperframes beats)."""
    import numpy as np
    n = 1024
    quadros = np.lib.stride_tricks.sliding_window_view(x, n)[::hop] * np.hanning(n)
    S = np.log1p(100 * np.abs(np.fft.rfft(quadros, axis=1)))
    o = np.maximum(0, np.diff(S, axis=0)).sum(1)
    o = np.maximum(0, o - np.convolve(o, np.ones(16) / 16, "same"))  # tira a média local (~0,19 s)
    o = np.lib.stride_tricks.sliding_window_view(np.pad(o, 2), 5).max(1)  # tolerância: ±2 passos de 11,6 ms
    t0, dt = hop / sr + n / 2 / sr, hop / sr                          # o fluxo i compara a janela i+1 com a i
    fim = t0 + (len(o) - 1) * dt
    melhor = (-1.0, 0.0, 0.0)
    for P in np.arange(0.25, 0.5, 0.0005):
        ph = np.arange(0, P, 0.005)
        k = np.arange(int((fim - P) / P) + 1)
        idx = np.rint((ph[:, None] + P * k[None, :] - t0) / dt).astype(int).clip(0, len(o) - 1)
        nota = o[idx].mean(1)
        i = int(np.argmax(nota))
        if nota[i] > melhor[0]:
            melhor = (float(nota[i]), float(P), float(ph[i]))
    return melhor[1], melhor[2]


def grade(audio):
    import numpy as np
    sr = 22050
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    if len(raw) < sr * 4 * 2:
        raise Falha(f"não consegui ler pelo menos 2 s de áudio de {audio}", "MUSICA_ILEGIVEL")
    return grade_de_sinal(np.frombuffer(raw, np.float32), sr)


def encaixar(batidas):
    """Quadro novo de cada momento: a batida (quadro inteiro) mais próxima, sem inverter a ordem nem colar dois momentos."""
    novos = []
    for i, (b, L, _) in enumerate(ENTRADAS):
        piso = 2 if i == 0 else novos[-1] + max(6, (b - ENTRADAS[i - 1][0]) // 2)
        cands = [q for q in batidas if piso <= q <= SAT_NF - 30]
        novos.append(min(cands, key=lambda q: (abs(q - b), -q)) if cands else max(piso, b))  # empate: a batida de depois (meio mais lento, não corrido)
    return novos


def curva(novos):
    """[[quadro de saída, quadro do clone], ...]: a entrada de cada momento anda a 1x (molas intactas), só o meio estica."""
    pts = [(0, 0)]
    for i, ((b, L, _), n) in enumerate(zip(ENTRADAS, novos)):
        b2, n2 = (ENTRADAS[i + 1][0], novos[i + 1]) if i + 1 < len(ENTRADAS) else (SAT_NF, SAT_NF)
        e = max(0, min(L, b2 - b - MEIO_MIN, n2 - n - MEIO_MIN))
        pts.append((n, b))
        if e:
            pts.append((n + e, b + e))
    pts.append((SAT_NF, SAT_NF))
    return pts


def eventos_de_som(V, mapa, pacote, saida=float):
    """Os eventos do nível V["sons"] no tempo da saída, em ordem: [(quadro, tipo, evento, som)].
    Mola firme: um evento dentro da entrada [b, b+L] cai em b + 0,6 (f - b), como no index.html. saida(): quadro do
    clone -> quadro da saída (ritmo "batidas"). Cada tipo roda entre as suas versões (rodízio), então o mesmo arquivo
    nunca toca duas vezes seguidas. por_palavra: um evento por palavra, a cada passo quadros, vezes o "ritmo" em rodízio
    (passos desiguais, como quem digita)."""
    km = KM_FIRME if V.get("mola") == "firme" else 1
    evs = []
    for e in mapa["eventos"]:
        if V["sons"] == "suave" and e["nivel"] != "suave":
            continue
        pp = e.get("por_palavra")
        rit = (pp or {}).get("ritmo", [1])
        for i in range(len(V[pp["variavel"]].split()) if pp else 1):
            f = e["quadro"] + (pp["passo"] * sum(rit[k % len(rit)] for k in range(i)) if pp else 0)
            b, L = e.get("mola", (0, 0))
            if b < f < b + L:
                f = b + km * (f - b)
            evs.append((saida(f), e["tipo"], e["evento"]))
    evs.sort(key=lambda x: x[0])
    vez = {}
    for i, (q, tipo, nome) in enumerate(evs):
        vs = pacote["tipos"][tipo]["versoes"]
        vez[tipo] = vez.get(tipo, -1) + 1
        evs[i] = (q, tipo, nome, vs[vez[tipo] % len(vs)])
    return evs


def lufs(caminho):
    """Loudness integrada (LUFS, ebur128 do ffmpeg) de um arquivo de áudio; None quando é silêncio."""
    r = subprocess.run(["ffmpeg", "-nostats", "-i", caminho, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m and float(m[-1]) > -70 else None


def golpes(m, sr, hop=256, n=1024):
    """Os golpes da música (mono): o fluxo espectral (como em grade_de_sinal) menos a média local, e o corte em 3 vezes o
    percentil 90. Devolve uma função t -> há golpe a até 40 ms de t. Efeito em cima de golpe soma com ele: as pílulas do
    Satellite caem em golpes de 7 a 13 vezes o percentil 90 da trilha original."""
    import numpy as np
    if len(m) < n + 2 * hop:
        return lambda t: False
    q = np.lib.stride_tricks.sliding_window_view(m, n)[::hop] * np.hanning(n)
    S = np.log1p(100 * np.abs(np.fft.rfft(q, axis=1)))
    o = np.maximum(0, np.diff(S, axis=0)).sum(1)
    o = np.maximum(0, o - np.convolve(o, np.ones(16) / 16, "same"))
    tt = hop / sr + n / 2 / sr + np.arange(len(o)) * hop / sr
    corte = max(3 * float(np.percentile(o, 90)), 1e-6)
    return lambda t: bool((o[(tt > t - 0.04) & (tt < t + 0.04)] > corte).any())


def mixar_sons(V, musica, saida, evs, pacote, fps=SAT_FPS, nf=SAT_NF):
    """Música vezes musica_volume, mais um som por evento com o "ataque" do som no instante do evento. Sai com a
    duração do vídeo (nf quadros a fps) e passa por um limitador em -1 dBFS (com compensação de atraso, para o encaixe
    não andar). Três cuidados ouvidos no Satellite: cada tecla muda um pouco de ganho e de altura (TECLAS); efeito em
    cima de um golpe da música desce BATIDA_DB; e, com música de verdade, o final vai para a loudness dos originais
    (LUFS_ALVO). Com o silêncio do molde, os efeitos ficam no nível deles. Devolve (saída, medidas)."""
    import numpy as np
    sr = 48000
    n = round(nf / fps * sr)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", musica, "-ac", "2", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
    m = np.frombuffer(raw, np.float32).reshape(-1, 2)[:n]
    mix = np.zeros((n, 2))
    mix[:len(m)] = m * V["musica_volume"]
    em_golpe, tecla, golpes_ = golpes(m.mean(1), sr), 0, []
    for q, tipo, nome, som in evs:
        info = pacote["sons"][som]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(SONS, info["arquivo"]), "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"], capture_output=True).stdout
        s = np.frombuffer(raw, np.float32).astype(np.float64)
        db, vel = pacote["tipos"][tipo]["ganho_db"] + SONS_DB[V["sons"]], 1.0
        if tipo == "digitar":
            d, vel = TECLAS[tecla % len(TECLAS)]
            db, tecla = db + d, tecla + 1
            s = np.interp(np.arange(0, len(s) - 1, vel), np.arange(len(s)), s)  # mais rápido = mais agudo
        if em_golpe(q / fps):
            db += BATIDA_DB
            golpes_.append(round(q, 2))
        s = s * 10 ** (db / 20)
        i0 = round((q / fps - info["ataque"] / vel) * sr)
        a, b = max(0, i0), min(n, i0 + len(s))
        if b > a:
            mix[a:b] += s[a - i0:b - i0, None]
    bruto = saida + ".f32"
    alvo = LUFS_ALVO if lufs(musica) is not None else None
    ganho, medido = 0.0, None
    for _ in range(3):  # o limitador come um pouco da loudness: mede o resultado e corrige (2 voltas bastam)
        (mix * 10 ** (ganho / 20)).astype("<f4").tofile(bruto)
        sh(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", bruto, "-af",
            "alimiter=limit=0.891:attack=2:release=40:level=false:latency=true", "-c:a", "aac", "-b:a", "256k", "-ar", str(sr), saida])
        medido = lufs(saida)
        if alvo is None or medido is None or abs(medido - alvo) <= 0.5:
            break
        ganho += alvo - medido
    os.remove(bruto)
    return saida, {"lufs": medido, "alvo_lufs": alvo, "ganho_db": round(ganho, 2), "em_golpe": golpes_}


def sons_por_elemento(c, V, audio, pasta, saida=float):
    """Sons por elemento (sons/SONS.md), em qualquer molde com sons.json. Com "nenhum" nada aqui roda e o áudio segue
    como antes (o padrão continua idêntico ao clone). saida(): quadro do clone -> quadro da saída (ritmo do Satellite).
    Devolve (áudio, texto para o resumo)."""
    if V.get("sons", "nenhum") == "nenhum":
        return audio, ""
    pacote = json.load(open(os.path.join(SONS, "sons.json"), encoding="utf-8"))
    evs = eventos_de_som(V, json.load(open(os.path.join(c["molde"], "sons.json"), encoding="utf-8")), pacote, saida)
    audio, med = mixar_sons(V, audio, os.path.join(pasta, "musica-sons.m4a"), evs, pacote, c["fps"], c["nf"])
    dur = c["nf"] / c["fps"]
    json.dump({"medidas": med, "eventos": [{"quadro": round(q, 3), "tipo": t, "evento": e, "som": s} for q, t, e, s in evs]},
              open(os.path.join(pasta, "sons-eventos.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"sons {V['sons']}: {len(evs)} eventos em {dur:.2f} s ({len(evs) / dur:.1f} por segundo), música a {V['musica_volume']:g}; "
        f"final {med['lufs'] if med['lufs'] is not None else '-'} LUFS (alvo {med['alvo_lufs'] or 'nenhum: sem música'}), "
        f"{len(med['em_golpe'])} efeito(s) em cima de golpe da música, -{-BATIDA_DB} dB")
    for q, t, e, s in evs:
        log(f"  quadro {q:6.2f}  {s:11s} {e}")
    return audio, f", sons {V['sons']}" + (f" ({med['lufs']:.1f} LUFS)" if med["lufs"] is not None else "")


def satellite(c, V, decl, proj, pasta):
    """O que só o Satellite faz antes do render: 9:16, música trocada, ritmo pelas batidas e sons por elemento.
    Devolve (áudio, quadros da folha ou None, altura da folha ou None, texto para o resumo)."""
    vert = V["formato"] == "9:16"
    if vert:
        ix = os.path.join(proj, "index.html")
        html = open(ix, encoding="utf-8").read()
        for a, b in VERTICAL:
            if html.count(a) != 1:
                raise Falha(f"o molde mudou: não achei {a!r} uma vez só para virar 9:16", "MOLDE_SEM_9_16")
            html = html.replace(a, b)
        open(ix, "w", encoding="utf-8").write(html)

    # música: a original vai copiada; outra música repete se for curta, corta na duração do vídeo e some em 0,5 s
    dur = SAT_NF / SAT_FPS
    if V["musica"] == decl["musica"]["default"]:
        audio = os.path.join(proj, V["musica"])
    else:
        audio = os.path.join(pasta, "musica.m4a")
        sh(["ffmpeg", "-v", "error", "-y", "-stream_loop", "-1", "-i", os.path.join(c["molde"], V["musica"]), "-t", f"{dur:.4f}",
            "-af", f"afade=t=out:st={dur - 0.5:.4f}:d=0.5", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", audio])

    inversa, para_saida = None, float
    if V["ritmo"] == "batidas":
        import numpy as np
        P, ph = grade(audio)
        batidas = [round((ph + k * P) * SAT_FPS) for k in range(int(dur / P) + 2)]
        novos = encaixar(batidas)
        pts = curva(novos)
        open(os.path.join(proj, "ritmo.js"), "w").write(f"window.RITMO = {json.dumps(pts)};\n")
        g, f = [p[0] for p in pts], [p[1] for p in pts]
        para_saida = lambda m: float(np.interp(m, f, g))
        inversa = lambda m: int(round(para_saida(m)))
        log(f"ritmo: {V['musica']}, pulso {P:.3f} s ({60 / P:.1f} por minuto), primeira batida {ph:.3f} s (quadro {ph * SAT_FPS:.1f})")
        log(f"  batidas (quadros): {' '.join(str(q) for q in batidas if q <= SAT_NF)}")
        for i, ((b, L, rot), n) in enumerate(zip(ENTRADAS, novos)):
            b2, n2 = (ENTRADAS[i + 1][0], novos[i + 1]) if i + 1 < len(ENTRADAS) else (SAT_NF, SAT_NF)
            e = max(0, min(L, b2 - b - MEIO_MIN, n2 - n - MEIO_MIN))
            log(f"  {rot:7s} clone {b:3d} -> saída {n:3d} ({n - b:+d}); entrada {e} quadros a 1x; meio a {(b2 - b - e) / (n2 - n - e):.2f}x")

    audio, extra = sons_por_elemento(c, V, audio, pasta, para_saida)
    quadros = [inversa(m) for m in c["momentos"]] if inversa else None
    return audio, quadros, 640 if vert else None, ("9:16" if vert else "1:1") + extra


# ---------------------------------------------------------------- render, encode, lado a lado e folha
def sh(cmd, codigo="COMANDO_FALHOU", **kw):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    except FileNotFoundError:
        raise Falha(f"falta o programa {cmd[0]} no PATH", "FALTA_FERRAMENTA")
    if r.returncode:
        raise Falha(f"falhou: {' '.join(cmd[:4])} ... {(r.stderr or r.stdout)[-1500:]}", codigo)
    return r.stdout


def espaco_livre(pasta):
    st = os.statvfs(pasta)
    gb = st.f_bavail * st.f_frsize / 1e9
    if gb < 2:
        raise Falha(f"parei: só {gb:.1f} GB livres no disco (mínimo 2 GB para renderizar)", "DISCO_CHEIO")
    return gb


def render(c, proj, vars_json, fps, saida):
    # Joi e VoiceOS: o Chrome deste Mac não repete o render bit a bit (vidro com backdrop-filter); ver NOTAS.md de cada um
    fonte_do_sistema(proj)
    t = time.time()
    sh(hf(c) + ["render", "--quality", "draft", "--fps", str(fps), "--workers", "1", "--strict-variables",
                "--variables-file", vars_json, "--output", saida], "RENDER_FALHOU", cwd=proj)
    return time.time() - t


def fonte_do_sistema(proj):
    """A SF Pro não vai no repositório: a cópia de render recebe a do sistema, ou a Inter (sem SF ou com ASUI_FONTE_LIVRE=1).
    Devolve o nome da fonte usada, ou None quando o molde não pede a SF."""
    alvo = os.path.join(proj, "assets", "fonts", "SFNS.ttf")
    html = open(os.path.join(proj, "index.html"), encoding="utf-8").read()
    for livre in ("Archivo.ttf", "Inter.ttf"):  # as fontes livres do kit de marca moram uma vez só, no molde do Satellite
        dest = os.path.join(proj, "assets", "fonts", livre)
        if f"assets/fonts/{livre}" in html and not os.path.isfile(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(os.path.join(os.path.dirname(INTER), livre), dest)
    if "assets/fonts/SFNS.ttf" not in html:
        return None
    livre = os.environ.get("ASUI_FONTE_LIVRE") == "1" or not os.path.isfile(SF_SISTEMA)
    os.makedirs(os.path.dirname(alvo), exist_ok=True)
    shutil.copyfile(INTER if livre else SF_SISTEMA, alvo)  # copyfile: sem as travas de arquivo do sistema
    if os.environ.get("ASUI_FONTE_LIVRE") == "1":  # modo livre (os exemplos do repositório): sem os emojis fixos do Satellite
        ix = os.path.join(proj, "index.html")
        html = open(ix, encoding="utf-8").read()
        open(ix, "w", encoding="utf-8").write(html.replace('world, "\u26a0\ufe0f")', 'world, "")').replace('world, "\U0001f691")', 'world, "")'))
    return "Inter" if livre else "SF Pro do sistema"


def guardar(caminho):
    """Nunca sobrescrever: o arquivo que já existe ganha a data dele no nome (<nome>-AAAAMMDD-HHMMSS.ext) antes de sair o
    novo. Devolve o nome novo, ou None quando não havia arquivo."""
    if not os.path.exists(caminho):
        return None
    raiz, ext = os.path.splitext(caminho)
    data = time.strftime("%Y%m%d-%H%M%S", time.localtime(os.path.getmtime(caminho)))
    destino, i = f"{raiz}-{data}{ext}", 1
    while os.path.exists(destino):
        i += 1
        destino = f"{raiz}-{data}-{i}{ext}"
    os.replace(caminho, destino)
    return destino


def nome_do_video(video):
    """Nome dos arquivos de saída: o da pasta do vídeo. Em marcas/<cliente>/videos/<video>/ o cliente vai na frente,
    porque a régua do aprendizado é guardada pelo nome do mp4 e dois clientes podem ter um vídeo com o mesmo nome."""
    p = os.path.normpath(os.path.abspath(video)).split(os.sep)
    return f"{p[-3]}-{p[-1]}" if len(p) >= 4 and p[-2] == "videos" and p[-4] == "marcas" else p[-1]


def rotulo_png(caminho, c, textos):
    from PIL import Image, ImageDraw, ImageFont
    im = Image.new("RGBA", (2 * c["largura"], c["altura"]), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", c["rotulo"])
    m, px, py = round(0.8 * c["rotulo"]), round(1.2 * c["rotulo"]), round(0.85 * c["rotulo"])
    for x0, txt in textos:  # pílula escura: rótulo branco sumia no fundo branco (LESSONS do Satellite)
        b = d.textbbox((0, 0), txt, font=f)
        d.rounded_rectangle((x0 + m, m, x0 + m + b[2] - b[0] + px, m + b[3] - b[1] + py), radius=round(0.65 * c["rotulo"]), fill=(20, 20, 20, 190))
        d.text((x0 + m + px // 2, m + py // 2 - b[1]), txt, font=f, fill=(255, 255, 255, 255))
    im.save(caminho)


def folha(c, original, novo, nome, caminho, alto=None, quadros=None):
    """Os momentos do molde lado a lado: o original em cima (quando o vídeo dele está na máquina) e a versão embaixo.
    alto: altura da versão (640 no 9:16 do Satellite); quadros: onde cada momento caiu na versão (ritmo)."""
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    W, H = c["quadro"]

    def quadro(v, n, h):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", v, "-vf", f"select=eq(n\\,{n}),scale={W}:{h}", "-fps_mode", "passthrough",
                              "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
        return Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, W, 3))
    f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 18)
    linhas = ([(original, "ORIGINAL", H, c["momentos"])] if original else []) + [(novo, nome.upper(), alto or H, quadros or c["momentos"])]
    im = Image.new("RGB", (len(c["momentos"]) * (W + 4) + 190, 40 + sum(h + 24 for _, _, h, _ in linhas)), (17, 17, 17))
    d = ImageDraw.Draw(im)
    y = 40
    for i, (v, txt, h, qs) in enumerate(linhas):
        d.multiline_text((10, y + h // 2 - 20), txt.replace("-", "-\n"), font=f, fill=(255, 220, 120))  # nome longo cabe nos 190 px
        for j, n in enumerate(qs):
            im.paste(quadro(v, n, h), (190 + j * (W + 4), y))
            if i == 0:
                d.text((190 + j * (W + 4) + 4, 12), f"quadro {n}", font=f, fill=(220, 220, 220))
            elif qs != c["momentos"]:
                d.text((190 + j * (W + 4) + 4, y - 22), f"saída {n}", font=f, fill=(255, 220, 120))
        y += h + 24
    im.save(caminho, quality=92)


def comando(versao, c, previa=False, marca=None, video=None, saidas=None):
    return shlex.join(["python3", EU, os.path.abspath(versao), "--molde", c["nome"], *(["--previa"] if previa else []),
                       *(["--marca", marca] if marca else []), *(["--video", video] if video else []), *(["--saidas", saidas] if saidas else [])])


def montar_um(c, versao, previa, marca=None, video=None, saidas=None):
    """Uma versão, um render. Devolve o JSON de resposta."""
    t0 = time.time()
    try:
        bruto_json = json.load(open(versao, encoding="utf-8"))
    except OSError as e:
        raise Falha(f"não consegui ler {versao}: {e}", "ARQUIVO_ILEGIVEL")
    except ValueError as e:
        raise Falha(f"{versao} não é JSON válido: {e}", "ARQUIVO_ILEGIVEL")
    pedido = bruto_json.get("molde") if isinstance(bruto_json, dict) else None
    avisos = []
    if isinstance(pedido, str) and "-v" in pedido and pedido != conferir_molde(c)[0]:
        congelado = molde_pedido(c, pedido)  # a versão pede uma versão antiga do molde: usa a pasta congelada dela
        if congelado:
            c = congelado
        else:
            avisos.append(f"a versão pede o molde {pedido}, que não está em {os.path.relpath(c['travadas'], AQUI)}/; "
                          f"saiu com o molde em vigor, {conferir_molde(c)[0]}")
    decl, base = declaradas(c), os.path.dirname(os.path.abspath(versao))
    valores, erros, info = carregar(bruto_json, decl, c, base, marca)
    if erros:
        raise Falha("versão inválida: " + " | ".join(erros), "VERSAO_INVALIDA")
    V = {**{k: d["default"] for k, d in decl.items()}, **valores}  # valores efetivos
    versao_molde, aviso = conferir_molde(c)
    avisos += [aviso] if aviso else []
    for a in avisos:
        log(f"aviso: {a}")

    pedida = saidas
    if video:
        video = os.path.abspath(video)
        nome = nome_do_video(video) + ("-previa" if previa else "")
        saidas = os.path.join(video, "saidas")
        os.makedirs(os.path.join(video, "." + NOME), exist_ok=True)
        pasta = tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-") + ("previa-" if previa else "final-"), dir=os.path.join(video, "." + NOME))
        resolvida = os.path.join(video, "." + NOME, "versao-resolvida.json")
    else:
        nome = os.path.splitext(os.path.basename(versao))[0] + ("-previa" if previa else "")
        saidas = os.path.abspath(saidas or os.path.join(c["pasta"], "saidas"))
        pasta = os.path.join(trabalho(c), nome)
        shutil.rmtree(pasta, ignore_errors=True)
        resolvida = os.path.join(pasta, "versao-resolvida.json")
    os.makedirs(saidas, exist_ok=True)
    proj = os.path.join(pasta, "proj")
    shutil.copytree(c["molde"], proj, ignore=shutil.ignore_patterns(".*", "renders"))

    # a versão resolvida é o que o portão lê: sem "marca" nem "molde", imagens de fora do molde com caminho absoluto
    para_portao = dict(valores)
    for k, v in valores.items():
        if decl[k]["type"] == "image" or (k == "logo" and v):
            caminho, dentro = achar_imagem(v.get("url") if isinstance(v, dict) else v, c, base)
            if caminho and not dentro:
                para_portao[k] = caminho
    texto = json.dumps(para_portao, ensure_ascii=False, indent=1) + "\n"
    if not (os.path.exists(resolvida) and open(resolvida, encoding="utf-8").read() == texto):
        guardar(resolvida)
        open(resolvida, "w", encoding="utf-8").write(texto)
    vars_json = os.path.join(pasta, "vars.json")
    json.dump(preparar_imagens(dict(valores), decl, c, base, proj), open(vars_json, "w", encoding="utf-8"), ensure_ascii=False)

    audio, quadros, alto, detalhe = os.path.join(proj, SILENCIO), None, None, ""
    if c["nome"] == "satellite":
        audio, quadros, alto, detalhe = satellite(c, V, decl, proj, pasta)
        detalhe = ", " + detalhe
    else:
        audio, detalhe = sons_por_elemento(c, V, audio, pasta)

    log(f"{nome} (molde {versao_molde}): {espaco_livre(pasta):.1f} GB livres")
    if previa:
        bruto = os.path.join(pasta, "previa.mp4")  # fica no bastidor: é o render cru, sem encode nosso
        tr = render(c, proj, vars_json, c["fps"], bruto)
        vf = []
    else:
        n, fps = c["n"], c["fps"]
        hi = fps * n
        open(os.path.join(proj, "mb.js"), "w").write(f"window.MB_SHIFT = {(n - 1) / 2 / hi};\n")
        bruto = os.path.join(pasta, f"bruto-{hi}.mp4")
        tr = render(c, proj, vars_json, hi, bruto)
        vf = ["-vf", f"tmix=frames={n},select='not(mod(n+1\\,{n}))',setpts=N/({fps}*TB),lutyuv=y='clip(16+(val-16)*{GAIN}\\,0\\,255)'"
                     + (f",{c['lut']}" if c["lut"] else ""), "-r", str(fps)]
    log(f"render: {tr:.0f} s")
    t = time.time()
    final = os.path.join(saidas, nome + ".mp4")
    trocados = [x for x in [guardar(final)] if x] if video else []
    # vídeo inteiro é o mestre de duração: sem -shortest (cortava os últimos quadros no Satellite)
    sh(["ffmpeg", "-v", "error", "-y", "-i", bruto, "-i", audio, "-map", "0:v", "-map", "1:a", *vf, *X264, "-c:a", "copy", final], "ENCODE_FALHOU")
    if not previa:
        os.remove(bruto)  # o bruto de alta taxa ocupa disco: sai logo depois do tmix
    log(f"encode: {time.time() - t:.0f} s -> {final}")

    arquivos = [final]
    tem_original = os.path.isfile(c["original"])
    if not tem_original:
        avisos.append(f"sem o vídeo do clone original ({c['original']}), saiu só a versão: sem lado a lado, e a folha mostra só a versão. "
                      "No repositório público isso é o esperado, não é falha: o original não vai junto, por direito autoral")
    elif not previa or c["lado_na_previa"]:
        lab = os.path.join(pasta, "rotulos.png")
        rotulo_png(lab, c, [(0, "ORIGINAL"), (c["largura"], f"VERSÃO {nome.upper()}")])
        # 9:16: original na mesma faixa (o #fdfdfd do molde sai #fbfbfb)
        base_f = f"[0:v]pad=1080:1920:0:{OY}:color=0xfbfbfb[o];[o][1:v]" if V.get("formato") == "9:16" else "[0:v][1:v]"
        for sufixo, crf in [("", "12")] + ([("-leve", "20")] if c["leve"] else []):
            lado = os.path.join(saidas, f"{nome}-lado-a-lado{sufixo}.mp4")
            trocados += [x for x in [guardar(lado) if video else None] if x]
            sh(["ffmpeg", "-v", "error", "-y", "-i", c["original"], "-i", final, "-i", lab, "-filter_complex",
                base_f + "hstack=inputs=2[s];[s][2:v]overlay=0:0[v]", "-map", "[v]", "-map", "1:a",
                *[crf if a == "12" else a for a in X264], "-c:a", "copy", lado], "ENCODE_FALHOU")
            arquivos.append(lado)
    fl = os.path.join(saidas, nome + "-folha.jpg")
    trocados += [x for x in [guardar(fl) if video else None] if x]
    folha(c, c["original"] if tem_original else None, final, nome, fl, alto, quadros)
    arquivos.append(fl)
    if video:
        shutil.rmtree(proj)  # a cópia do molde (~10 MB) sai; ficam vars.json, versão, sons e o render cru da prévia

    total = time.time() - t0
    if info.get("kit_sem_uso"):
        avisos.append(f"do kit {info['nome_marca']}, {' e '.join(info['kit_sem_uso'])} não entra(m) no {c['nome']} (o molde não tem esse campo)")
    if trocados:
        avisos.append(f"o que já existia foi guardado com a data no nome: {', '.join(os.path.basename(x) for x in trocados)}")
    marca_txt = f", marca {info['nome_marca']}" if info.get("nome_marca") else ""
    resumo = (f"{'Prévia' if previa else 'Final'} de {nome} (molde {versao_molde or c['nome']}{detalhe}{marca_txt}, "
              f"{'sem' if previa else 'com'} motion blur) pronta em {saidas}: {', '.join(os.path.basename(x) for x in arquivos)}. "
              f"Render {tr:.0f} s, total {total:.0f} s." + "".join(f" Atenção: {a}." for a in avisos))
    if previa:
        proximo = {"comando": comando(versao, c, False, marca, video, pedida and saidas),
                   "motivo": "conferir a folha da prévia no olho e, se estiver boa, renderizar o final com motion blur", "precisa_de_voce": True}
    else:
        proximo = {"comando": shlex.join(["open", fl]), "motivo": "conferir a folha de quadros no olho antes de usar o vídeo", "precisa_de_voce": True}
    saida = {"ok": True, "resumo": resumo, "proximo": proximo, "arquivos": arquivos, "molde": versao_molde,
             "render_s": round(tr), "total_s": round(total), "versao_resolvida": resolvida, "bastidor": pasta}
    if avisos:
        saida["avisos"] = avisos
    if info.get("marca"):
        saida["marca"] = info["marca"]
    if video:
        saida["video"] = video
        json.dump(saida, open(os.path.join(pasta, "resultado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return saida


def lote(c, versao, previa, marcas, video=None):
    """A mesma versão para várias marcas, uma por vez, cada uma no seu vídeo ({marca} no --video vira o nome do kit)."""
    base = os.path.dirname(os.path.abspath(versao))
    modelo = video or os.path.join("marcas", "{marca}", "videos", os.path.splitext(os.path.basename(versao))[0])
    if "{marca}" not in modelo:
        modelo = os.path.join(modelo, "{marca}")
    feitos, falhas = [], []
    for m in marcas:
        caminho = achar_marca(m, base)
        if not caminho:
            falhas.append(f"{m}: não achei a marca")
            continue
        log(f"--- lote: {m} ({len(feitos) + len(falhas) + 1} de {len(marcas)})")
        try:
            feitos.append(montar_um(c, versao, previa, caminho, modelo.replace("{marca}", nome_da_marca(caminho))))
        except Falha as f:
            falhas.append(f"{m}: {f.erro} ({f.codigo})")
            log(f"lote: {m} falhou: {f.erro}")
    if falhas:
        raise Falha(f"lote incompleto: {len(feitos)} de {len(marcas)} prontas"
                    f"{' (' + ', '.join(x['video'] for x in feitos) + ')' if feitos else ''}. Falharam: " + " | ".join(falhas), "LOTE_INCOMPLETO")
    folhas = [x["arquivos"][-1] for x in feitos]
    return {"ok": True, "resumo": f"Lote de {len(feitos)} marcas ({'prévia' if previa else 'final'}) pronto: "
                                  + "; ".join(f"{nome_da_marca(x['marca'])} em {x['video']}" for x in feitos) + ".",
            "proximo": {"comando": shlex.join(["open", *folhas]), "motivo": "conferir a folha de cada marca no olho", "precisa_de_voce": True},
            "arquivos": [a for x in feitos for a in x["arquivos"]], "lote": feitos}


# ---------------------------------------------------------------- prova pixel a pixel (VoiceOS)
def provar(c):
    """Snapshots PNG (sem encoder) de todos os quadros do clone e do molde com os padrões, comparados pixel a pixel."""
    import numpy as np
    from PIL import Image
    if not os.path.isfile(os.path.join(c["clone_hf"], "index.html")):
        raise Falha(f"falta o projeto do clone: {c['clone_hf']}", "FALTA_CLONE")
    t0 = time.time()
    pasta = os.path.join(trabalho(c), "prova")
    shutil.rmtree(pasta, ignore_errors=True)
    for lado, origem in (("clone", c["clone_hf"]), ("molde", c["molde"])):
        shutil.copytree(origem, os.path.join(pasta, lado), ignore=shutil.ignore_patterns(".*", "renders"))
        fonte_do_sistema(os.path.join(pasta, lado))
    log(f"prova: {espaco_livre(pasta):.1f} GB livres")

    def comparar(quadros):
        """Quadros (da lista) cujos PNGs do clone e do molde diferem."""
        at = ",".join("%.6f" % (f / c["fps"]) for f in quadros)
        png = {}
        for lado in ("clone", "molde"):
            png[lado] = os.path.join(pasta, "png-" + lado)
            shutil.rmtree(png[lado], ignore_errors=True)
            sh(hf(c) + ["snapshot", "--at", at, "--no-end", "--no-browser-gpu", "-o", png[lado]], "SNAPSHOT_FALHOU", cwd=os.path.join(pasta, lado))
        A, B = (sorted(glob.glob(os.path.join(png[x], "frame-*.png"))) for x in ("clone", "molde"))
        if len(A) != len(quadros) or len(B) != len(quadros):
            raise Falha(f"quadros {quadros[0]}-{quadros[-1]}: {len(A)} e {len(B)} PNGs para {len(quadros)} quadros", "SNAPSHOT_INCOMPLETO")
        out = []
        for f, a, b in zip(quadros, A, B):
            x, y = np.asarray(Image.open(a)), np.asarray(Image.open(b))
            if x.shape != y.shape or (x != y).any():
                out.append(f)
        for d in png.values():
            shutil.rmtree(d, ignore_errors=True)
        return out

    difs = []
    for b in range(0, c["nf"], 50):   # lotes de 50 quadros: os PNGs saem do disco a cada lote
        difs += comparar(list(range(b, min(b + 50, c["nf"]))))
        log(f"quadros {b}-{min(b + 50, c['nf']) - 1}: {len(difs)} diferentes até aqui")
    # o snapshot também erra de vez em quando (0 a 2 quadros em 700 por rodada; o quadro 142 sozinho bateu 6 de 6
    # vezes): cada quadro diferente é tirado de novo, sozinho, até 2 vezes
    refeitos = [f for f in difs if comparar([f]) and comparar([f])]
    shutil.rmtree(pasta, ignore_errors=True)
    if refeitos:
        raise Falha(f"{len(refeitos)} de {c['nf']} quadros diferem do clone mesmo refeitos (primeiros: {refeitos[:10]})", "MOLDE_DIFERENTE_DO_CLONE")
    nota = f"; {len(difs)} só {'bateu' if len(difs) == 1 else 'bateram'} no snapshot refeito (quadros {difs})" if difs else ""
    return {"ok": True, "resumo": f"{c['nf']} de {c['nf']} quadros do molde com os padrões têm os pixels idênticos aos do clone "
                                  f"(snapshot PNG{nota}, {time.time() - t0:.0f} s).",
            "proximo": {"comando": shlex.join(["python3", EU, "--molde", c["nome"], "--travar"]),
                        "motivo": "provado o molde, a trava registra a versão e a impressão digital dos arquivos", "precisa_de_voce": False},
            "arquivos": [], "molde": conferir_molde(c)[0], "refeitos": difs}


# ---------------------------------------------------------------- autoteste (roda a cada execução)
def autoteste(c):
    decl = declaradas(c)
    v = lambda x, base=None: validar(x, decl, c, base)
    # comum aos moldes
    assert v({}) == [] and len(v({"xyz": 1})) == 1 and len(v([1, 2])) == 1 and v("x")
    for k, d in decl.items():  # os padrões do molde passam nas próprias regras
        assert v({k: d["default"]}) == [], f"o padrão de '{k}' não valida"
    tipo = lambda t: next(k for k, d in decl.items() if d["type"] == t and k not in ARQUIVOS)
    assert len(v({tipo("color"): "laranja"})) == 1 and len(v({tipo("enum"): "foguete"})) == 1
    assert len(v({tipo("string"): "Carro — parado"})) == 1 and len(v({tipo("string"): "  "})) == 1
    imp = impressao_digital(c)
    assert "index.html" in imp and "MOLDE.json" not in imp and not any(k.startswith(".") for k in imp)
    # versão -> marca -> molde: "molde" sai; --marca vence a da versão; os dois formatos de kit; caminho relativo
    cor = c["kit"]["cor_principal"][0]
    x, e, info = carregar({"molde": c["nome"], "marca": "marcas/junior"}, decl, c)
    assert e == [] and "molde" not in x and "marca" not in x and x[cor] == "#E54A26" and info["nome_marca"] == "junior"
    x, e, info = carregar({"marca": "junior"}, decl, c, marca="padaria-exemplo")
    assert e == [] and x[cor] == "#D4860B" and info["nome_marca"] == "padaria-exemplo"
    assert set(info["kit_sem_uso"]) == {"fonte", "nome", "logo"} - set(c["kit"])
    kit = json.load(open(achar_marca("padaria-exemplo")))  # o kit da padaria chega às variáveis do molde (Joi: nome no ícone)
    assert all(x[var] == kit[k] for k, vs in c["kit"].items() if k in kit and k != "logo" for var in vs)
    # o logo mora fora do molde (marcas/<cliente>/logo.png): chega como caminho absoluto e vai para a cópia de render
    assert x["logo"] == os.path.join(AQUI, "marcas", "padaria-exemplo", kit["logo"]) and v({"logo": x["logo"]}) == []
    with tempfile.TemporaryDirectory() as tmp:
        proj = os.path.join(tmp, "proj")
        os.makedirs(proj)
        assert preparar_imagens({"logo": x["logo"]}, decl, c, tmp, proj)["logo"] == "assets/var/logo.png"
        assert os.path.isfile(os.path.join(proj, "assets", "var", "logo.png"))
    assert len(v({"logo": "nao-existe.png"})) == 1 and len(v({"logo": "../montar.py"})) == 1
    assert achar_marca(os.path.relpath(os.path.join(AQUI, "marcas", "salao-exemplo"))) == os.path.join(AQUI, "marcas", "salao-exemplo", "marca.json")
    assert carregar({"marca": "nao-existe"}, decl, c)[1] and carregar({cor: "#123456"}, decl, c, marca="junior")[0][cor] == "#123456"
    assert nome_do_video("/t/marcas/padaria/videos/primeiro") == "padaria-primeiro" and nome_do_video("/t/teste/padaria/") == "padaria"
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "a.mp4")
        open(a, "w").write("1")
        assert guardar(os.path.join(tmp, "b.mp4")) is None
        g1 = guardar(a)
        open(a, "w").write("2")
        os.utime(a, (os.path.getmtime(g1),) * 2)
        g2 = guardar(a)
        assert not os.path.exists(a) and g1 != g2 and open(g1).read() == "1" and open(g2).read() == "2"
        # travar: sem nome é o próximo número; mesmo nome com outro conteúdo é recusado
        falso = dict(c, pasta=tmp, molde=os.path.join(tmp, "m"), trava=os.path.join(tmp, "MOLDE.json"), travadas=os.path.join(tmp, "vt"))
        os.makedirs(falso["molde"])
        open(os.path.join(falso["molde"], "index.html"), "w").write("a")
        assert travar(falso) == (f"{c['nome']}-v1", True) and travar(falso) == (f"{c['nome']}-v1", False)
        open(os.path.join(falso["molde"], "index.html"), "w").write("b")
        assert conferir_molde(falso)[1] and travar(falso) == (f"{c['nome']}-v2", True)
        # cada versão tem a sua pasta, e a anterior não é reescrita
        v1, v2 = (os.path.join(falso["travadas"], f"{c['nome']}-v{i}") for i in (1, 2))
        assert open(os.path.join(v1, "index.html")).read() == "a" and open(os.path.join(v2, "index.html")).read() == "b"
        assert json.load(open(os.path.join(v1, "MOLDE.json")))["versao"] == f"{c['nome']}-v1" and conferir_molde(molde_pedido(falso, f"{c['nome']}-v1"))[1] is None
        assert molde_pedido(falso, f"{c['nome']}-v9") is None and molde_pedido(falso, "outro-v1") is None
        open(os.path.join(falso["molde"], "index.html"), "w").write("c")
        for nome in (f"{c['nome']}-v2", f"{c['nome']}-v1"):  # o registro em vigor e uma pasta que já existe
            try:
                travar(falso, nome)
                assert False, "travar aceitou um nome repetido"
            except Falha as f:
                assert f.codigo == "VERSAO_DO_MOLDE_REPETIDA"
        assert travar(falso) == (f"{c['nome']}-v3", True) and open(os.path.join(v1, "index.html")).read() == "a"
    # sons por elemento (todo molde com sons.json): opções e volume; o mapa só usa tipos do pacote; o suave é parte do
    # marcado; nunca o mesmo arquivo duas vezes seguidas; o padrão é "nenhum"
    pac, mapa = json.load(open(os.path.join(SONS, "sons.json"), encoding="utf-8")), json.load(open(os.path.join(c["molde"], "sons.json"), encoding="utf-8"))
    D = {k: d["default"] for k, d in decl.items()}
    assert D["sons"] == "nenhum" and v({"sons": "marcado", "musica_volume": 0.5}) == []
    assert len(v({"sons": "alto"})) == 1 and len(v({"musica_volume": 1.5})) == 1 and len(v({"musica_volume": True})) == 1
    assert all(e["tipo"] in pac["tipos"] for e in mapa["eventos"]) and all(os.path.isfile(os.path.join(SONS, s["arquivo"])) for s in pac["sons"].values())
    assert all(0 <= e["quadro"] < c["nf"] for e in mapa["eventos"])
    sv, mc = eventos_de_som({**D, "sons": "suave"}, mapa, pac), eventos_de_som({**D, "sons": "marcado"}, mapa, pac)
    assert 0 < len(sv) < len(mc) and {e[:3] for e in sv} <= {e[:3] for e in mc}
    assert all(a[3] != b[3] for a, b in zip(mc, mc[1:])) and all(a[0] <= b[0] for a, b in zip(mc, mc[1:]))
    # golpe da música: cliques a cada 0,4 s sobre um ruído baixo são golpes; entre eles, e no silêncio, não
    import numpy as np
    sr, rnd = 48000, np.random.default_rng(1)
    mus = (0.01 * rnd.standard_normal(sr * 3)).astype(np.float32)
    for t in np.arange(0.2, 3, 0.4):
        mus[int(t * sr):int(t * sr) + 960] += 0.5 * np.sin(np.arange(960) * 0.3) * np.exp(-np.arange(960) / 200)
    g = golpes(mus, sr)
    assert g(1.0) and g(1.4) and not g(1.2) and not g(0.8) and not golpes(np.zeros(sr * 3, np.float32), sr)(1.0)
    # cada molde
    if c["nome"] == "satellite":
        import numpy as np
        assert v({"titulo": "Qual é a emergência?", "icone1": "car", "cor_principal": "#E54A26", "balao_fones": True}) == []
        assert len(v({"relogio": "1:4"})) == 1 and len(v({"balao_fones": "sim"})) == 1 and len(v({"peca_mapa": "mapa"})) == 1
        assert v({"fonte": "inter", "formato": "9:16", "ritmo": "batidas", "musica": "assets/silencio.m4a", "logo": ""}) == []
        assert len(v({"fonte": "comic"})) == 1 and len(v({"formato": "4:5"})) == 1
        assert len(v({"musica": "assets/nao-existe.m4a"})) == 1 and len(v({"logo": "../montar.py"})) == 1
        x, e, _ = carregar({"marca": "marcas/junior", "balao_nome": "outro"}, decl, c)
        assert e == [] and x["balao_nome"] == "outro" and x["fonte"] == "archivo"
        assert "creditos" not in x and "cor_ponto" not in x  # sem cor_destaque, o ponto fica no padrão
        x = carregar({}, decl, c, marca="salao-exemplo")[0]
        assert x["cor_ponto"] == x["cor_rota"] == "#9B51E0" and x["fonte"] == "inter" and x["balao_nome"] == "salao.exemplo"
        # ritmo: cliques a cada 0,4 s a partir de 0,1 s -> a grade volta com erro menor que 1 quadro
        sr, s = 22050, np.zeros(22050 * 8, np.float32)
        for t in np.arange(0.1, 8, 0.4):
            i = int(t * sr)
            s[i:i + 256] += np.sin(np.arange(256) * 0.9) * np.exp(-np.arange(256) / 40)
        P, ph = grade_de_sinal(s, sr)
        assert abs(P - 0.4) < 0.004 and abs((ph - 0.1 + P / 2) % P - P / 2) < 1 / SAT_FPS, (P, ph)
        assert all(g == f for g, f in curva(encaixar([b for b, _, _ in ENTRADAS])))  # batidas nos inícios = tempo original
        pts = curva(encaixar(list(range(3, SAT_NF, 10))))
        assert all(g1 > g0 and f1 > f0 for (g0, f0), (g1, f1) in zip(pts, pts[1:])) and pts[-1] == (SAT_NF, SAT_NF)
        # a mola firme adianta só o que está dentro da entrada; um evento por palavra, com o passo desigual do ritmo
        fm = {e[2]: e[0] for e in eventos_de_som({**D, "sons": "marcado", "mola": "firme"}, mapa, pac)}
        assert abs(fm["ícone vira o cartão"] - 31.8) < 1e-9 and fm["satélite aparece no arco"] == 72
        ilha = [e[0] for e in eventos_de_som({**D, "sons": "marcado", "ilha_texto": "um dois três"}, mapa, pac) if e[2] == "texto da ilha, palavra a palavra"]
        assert len(ilha) == 3 and abs(ilha[1] - ilha[0] - 2.6) < 1e-9 and abs(ilha[2] - ilha[1] - 2.6 * 1.3) < 1e-9
        # a abertura do marcado ficou menos densa: no máximo 2 efeitos no primeiro meio segundo
        assert sum(e[0] < 15 for e in mc) <= 2
    elif c["nome"] == "joi":
        assert v({"item1": "Planejar o dia", "icone4": "sol", "objeto2": "🎮", "cor_principal": "#E54A26", "digitos": "01234"}) == []
        assert len(v({"objeto1": "carro"})) == 1 and len(v({"digitos": "5678"})) == 1 and len(v({"digitos": "5678a"})) == 1
    elif c["nome"] == "voiceos":
        assert D["musica_volume"] == 1 and not any(e["tipo"] in ("digitar", "numero") for e in mapa["eventos"])  # a trilha tem locução
        assert len(decl) == len(re.findall(r'\{"id": ', open(os.path.join(c["molde"], "index.html"), encoding="utf-8").read())), "variável repetida no molde"
        assert v({"frase_ceu": "aaah cara", "icone1": "💬", "avatar": "🙂", "cor_destaque": "#E54A26",
                  "foto_vinhedo": "assets/img/sky1.jpg", "foto_ceu": {"url": "assets/img/vine.jpg"}}) == []
        for ruim in ("nao-existe.jpg", "https://exemplo.com/ceu.jpg", "assets/fonts/SFNS.ttf", 3):
            assert len(v({"foto_ceu": ruim})) == 1, ruim
        assert v({"foto_ceu": "data:image/png;base64,AAAA"}) == []
    pasta = os.path.join(c["pasta"], "versoes")
    for f in sorted(os.listdir(pasta)):  # toda versão guardada tem que continuar válida
        if f.endswith(".json"):
            assert carregar(json.load(open(os.path.join(pasta, f), encoding="utf-8")), decl, c, pasta)[1] == [], f"versoes/{f} não valida"


# ---------------------------------------------------------------- invólucros e linha de comando
def api(nome):
    """O que os invólucros (moldes/<molde>/montar.py) expõem a quem os importa: o portão e o SKILL."""
    c = MOLDES[nome]
    return {"NOME": NOME, "MOLDE": c["molde"], "ORIGINAL": c["original"], "SAIDAS": os.path.join(c["pasta"], "saidas"), "HF": hf(c),
            "FPS": c["fps"], "N": c["n"], "NF": c["nf"], "MOMENTOS": c["momentos"], "Falha": Falha,
            "declaradas": lambda: declaradas(c),
            "validar": lambda valores, decl, base=None: validar(valores, decl, c, base),
            "carregar": lambda valores, decl, base=None, marca=None: carregar(valores, decl, c, base, marca)[:2],
            "render": lambda proj, vars_json, fps, saida: render(c, proj, vars_json, fps, saida),
            "conferir_versao": lambda: conferir_molde(c), "impressao_digital": lambda: impressao_digital(c),
            "autoteste": lambda: autoteste(c), "fonte_do_sistema": fonte_do_sistema}


USO = ("uso: python3 montar.py <versao.json> [--molde satellite|joi|voiceos] [--previa] [--marca <nome ou caminho>] "
       "[--video <pasta> | --saidas <pasta>] [--lote m1,m2,...]  |  --molde <molde> --travar [<molde>-vN]  |  --molde voiceos --provar")
COM_VALOR = ("--molde", "--marca", "--video", "--saidas", "--lote")
SEM_VALOR = ("--previa", "--provar", "--travar", "--registrar-molde")


def executar(argv):
    op, args, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in COM_VALOR:
            if i + 1 >= len(argv) or argv[i + 1].startswith("--"):
                raise Falha(f"{a} precisa de um valor. {USO}", "USO_ERRADO", 2)
            op[a], i = argv[i + 1], i + 2
        elif a in SEM_VALOR:
            op[a], i = True, i + 1
        elif a.startswith("--"):
            raise Falha(f"opção desconhecida: {a}. {USO}", "USO_ERRADO", 2)
        else:
            args.append(a)
            i += 1
    trava = op.get("--travar") or op.get("--registrar-molde")
    if ("--video" in op and "--saidas" in op) or ("--lote" in op and ("--marca" in op or "--saidas" in op)):
        raise Falha(f"--video e --saidas não vão juntos, nem --lote com --marca ou --saidas. {USO}", "USO_ERRADO", 2)
    if (trava and (len(args) > 1 or set(op) - {"--molde", "--travar", "--registrar-molde"})) or \
       ("--provar" in op and (args or set(op) - {"--molde", "--provar"})) or (not trava and "--provar" not in op and len(args) != 1):
        raise Falha(USO, "USO_ERRADO", 2)

    nome = op.get("--molde")
    if nome is not None and nome not in MOLDES:
        raise Falha(f"--molde {nome!r} não existe. Moldes: {', '.join(MOLDES)}", "USO_ERRADO", 2)
    if not trava and "--provar" not in op:
        try:
            pedido = json.load(open(args[0], encoding="utf-8")).get("molde")
        except (OSError, ValueError, AttributeError):
            pedido = None  # o erro de leitura sai depois, com o código certo
        if pedido is not None:
            m = re.fullmatch(r"([a-z]+)(-v\d+)?", pedido) if isinstance(pedido, str) else None
            if not m or m.group(1) not in MOLDES:
                raise Falha(f"'molde' = {pedido!r} não existe. Moldes: {', '.join(MOLDES)} (com ou sem -vN)", "VERSAO_INVALIDA")
            if nome and nome != m.group(1):
                raise Falha(f"a versão é do molde {m.group(1)} e o comando pediu --molde {nome}", "VERSAO_INVALIDA")
            nome = m.group(1)
    if nome is None:
        raise Falha(f"diga o molde: --molde {'|'.join(MOLDES)}, ou \"molde\": \"satellite\" na versão. {USO}", "USO_ERRADO", 2)
    c = MOLDES[nome]
    if not trava:
        for prog in ("ffmpeg", "npx"):
            if not shutil.which(prog):
                raise Falha(f"falta o programa {prog} no PATH", "FALTA_FERRAMENTA")
    try:
        autoteste(c)
    except AssertionError as e:
        raise Falha(f"o autoteste do montar.py falhou: {e or 'assert sem mensagem'}", "AUTOTESTE_FALHOU")

    if trava:
        versao, gravou = travar(c, args[0] if args else None)
        return {"ok": True, "resumo": f"Molde travado como {versao} em {c['trava']}." if gravou else f"O molde já está travado como {versao}; nada mudou.",
                "proximo": {"comando": shlex.join(["python3", EU, os.path.join(c["pasta"], "versoes", "original.json"), "--molde", nome, "--previa"]),
                            "motivo": "conferir que, com os padrões, o molde continua saindo igual ao clone", "precisa_de_voce": False},
                "arquivos": [c["trava"]], "molde": versao}
    if "--provar" in op:
        if not c["provar"]:
            raise Falha(f"--provar só existe no voiceos (o {nome} prova pelo portão)", "USO_ERRADO", 2)
        return provar(c)
    if "--lote" in op:
        marcas = [m.strip() for m in op["--lote"].split(",") if m.strip()]
        if not marcas:
            raise Falha(f"--lote precisa de pelo menos uma marca. {USO}", "USO_ERRADO", 2)
        return lote(c, args[0], "--previa" in op, marcas, op.get("--video"))
    return montar_um(c, args[0], "--previa" in op, op.get("--marca"), op.get("--video"), op.get("--saidas"))


def main(argv=None, molde=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if molde and "--molde" not in argv:
        argv = ["--molde", molde] + argv  # invólucro antigo: o molde vem da pasta dele
    try:
        saida = executar(argv)
    except Falha as f:
        print(json.dumps({"ok": False, "erro": f.erro, "codigo": f.codigo}, ensure_ascii=False), file=sys.stderr)
        sys.exit(f.saida)
    except ImportError as e:
        print(json.dumps({"ok": False, "erro": f"falta módulo Python: {e}", "codigo": "FALTA_MODULO"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    except Exception as e:  # bug: mesmo formato, para quem lê o stderr como JSON
        print(json.dumps({"ok": False, "erro": f"{type(e).__name__}: {e}", "codigo": "FALHA_INTERNA"}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    print(json.dumps(saida, ensure_ascii=False))


if __name__ == "__main__":
    main()
