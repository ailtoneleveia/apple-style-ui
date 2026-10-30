#!/usr/bin/env python3
"""aprender.py: o Apple Style UI aprende com o que a pessoa aprova, sem nunca andar para trás.

    python3 aprender.py aprovar <video.mp4> --tipo clone|versao|video-novo [--nota "..."] [--pendente]
                        [--versao <versao.json>] [--molde <pasta do molde>] [--quem <nome>] [--projeto <pasta>]
    python3 aprender.py travar [--quem <nome>]   # o ok humano na REVISAO.md: vira a versão nova do perfil
    python3 aprender.py perfil                   # o perfil de estilo em vigor (só leitura: nunca aprova nada)
    python3 aprender.py lista                    # o registro: o último estado de cada vídeo
    python3 aprender.py decisoes --projeto <pasta>   # as decisões de um vídeo, das antigas para as novas

Duas memórias:
  - no projeto, <projeto>/.apple-style-ui/decisoes.jsonl: cada decisão sobre aquele vídeo (aprovado, pendente,
    quarentena ou reprovado) com o motivo, uma por linha; o arquivo só cresce. O decisoes.json do formato antigo (uma
    lista reescrita a cada decisão) continua sendo lido, antes das linhas novas, e não é mais escrito;
  - na máquina, ~/.apple-style-ui/perfil/: aprovados.jsonl, as prévias de regressão e as versões travadas do
    perfil (perfil-v1, perfil-v2...), cada uma com a impressão digital (sha256) dos arquivos.

aprovar roda o portão (portao.py); se reprovar, só a decisão do projeto é escrita. Com --pendente, o item passou e
espera a pessoa. Sem --pendente é a aprovação humana do vídeo: cada versão já aprovada é re-renderizada em prévia com
o molde atual e tem que sair idêntica, senão o item fica em quarentena. Aprovado, o perfil ainda não muda: sai uma
REVISAO.md com o que mudaria e por quê, e só o `travar` (o ok humano, com a catraca de novo) cria a versão nova.

Saída: um JSON no stdout com ok, resumo e proximo; em erro, também uma linha JSON no stderr. Saída 0, 1 ou 2.
"""
import collections, datetime, getpass, glob, hashlib, json, os, re, shutil, sys, tempfile
import portao
from portao import Falha, comando, saida

REGISTRO = os.path.join(portao.PERFIL_DIR, "aprovados.jsonl")
PREVIAS = os.path.join(portao.PERFIL_DIR, "previas")
REVISAO = os.path.join(portao.PERFIL_DIR, "REVISAO.md")


def agora():
    return datetime.datetime.now().isoformat(timespec="seconds")


def atuais():
    """Último registro de cada vídeo: o registro só cresce e o mais novo vale."""
    if not os.path.exists(REGISTRO):
        return {}
    return {r["mp4"]: r for r in (json.loads(l) for l in open(REGISTRO, encoding="utf-8") if l.strip())}


def aprovados():
    return [r for r in atuais().values() if r["status"] == "aprovado"]


def ident(r):
    return portao.nome_do_molde(r["molde"]) + "-" + os.path.splitext(os.path.basename(r["mp4"]))[0]


def curto(caminho):
    return os.path.relpath(caminho, portao.RASCUNHO) if caminho.startswith(portao.RASCUNHO) else caminho


def decidir(projeto, decisao):
    """Acrescenta a decisão ao decisoes.jsonl do projeto (a memória daquele vídeo): uma linha, nada é reescrito."""
    caminho = os.path.join(projeto, "." + portao.NOME, "decisoes.jsonl")
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(json.dumps(decisao, ensure_ascii=False) + "\n")
    return caminho


def decisoes(projeto):
    """Todas as decisões do vídeo, das antigas para as novas: primeiro a lista do decisoes.json (o formato antigo), depois
    as linhas do decisoes.jsonl."""
    pasta = os.path.join(projeto, "." + portao.NOME)
    antigo, novo = os.path.join(pasta, "decisoes.json"), os.path.join(pasta, "decisoes.jsonl")
    lista = json.load(open(antigo, encoding="utf-8")) if os.path.exists(antigo) else []
    if os.path.exists(novo):
        lista += [json.loads(l) for l in open(novo, encoding="utf-8") if l.strip()]
    return lista


def regressao(itens, previa=None, digital=None):
    """Re-renderiza em prévia, com o molde atual, cada versão aprovada. Devolve o que mudou (vazio = nada piorou)."""
    previa = previa or (lambda r: portao.previa(portao.montar_de(r["molde"]), r["molde"], r["valores"], "regressao-" + ident(r))[1])
    digital = digital or portao.digital_do_molde
    mudou = []
    for r in itens:
        if r["tipo"] == "clone":
            continue  # clone é vídeo pronto: o molde não mexe nele
        if r.get("molde_digital") == digital(r["molde"]):
            continue  # mesmos arquivos de molde e mesmo HyperFrames: a saída não muda (Joi e VoiceOS nem repetem o render bit a bit)
        antes = open(r["previa"]).read().split()
        n = portao.diferentes(previa(r), antes)
        if n:  # "melhor" não dá para medir sem olho humano: se mudou, não entra
            mudou.append(f"{ident(r)}: {n} de {len(antes)} quadros da prévia mudaram com o molde atual")
    return mudou


def fontes(proj):
    txt = "".join(open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(proj, "index.html")) + glob.glob(os.path.join(proj, "compositions", "*.html")))
    return set(re.findall(r"""font-family\s*:\s*['"]?([A-Za-z][\w .-]*?)['",;]""", txt) + re.findall(r"""\d+(?:\.\d+)?px\s+['"]([^'"]+)['"]""", txt))


def perfil(itens):
    """O perfil de estilo, derivado só dos aprovados: cores, fontes, molas, controles e números dos clones."""
    grupos = {g: collections.defaultdict(collections.Counter) for g in ("cores", "molas", "controles")}
    fs, clones = collections.Counter(), {}
    for r in itens:
        fs.update(fontes(os.path.join(r["molde"], "hf") if r["tipo"] == "clone" else r["molde"]))
        if r["tipo"] == "clone":
            clones[ident(r)] = {k: r["compare"][k] for k in ("distancia", "correlacao", "movimento", "lag", "cortes")}
            continue
        for d in portao.declaracao(r["molde"])[2]:
            if d["type"] in ("enum", "boolean", "color"):  # textos são conteúdo, não estilo
                v = r["valores"].get(d["id"], d["default"])
                g = "cores" if d["type"] == "color" else "molas" if d["id"] == "mola" else "controles"
                grupos[g][d["id"]][v if isinstance(v, str) else json.dumps(v)] += 1
    p = {"aprovados": len(itens), "fontes": dict(fs.most_common())}
    p.update({g: {k: dict(c.most_common()) for k, c in sorted(v.items())} for g, v in grupos.items()})
    p["clones"] = clones
    if clones:
        bd, bc = min(c["distancia"] for c in clones.values()), max(c["correlacao"] for c in clones.values())
        p["regua_dos_clones"] = {"melhor_distancia": bd, "melhor_correlacao": bc, "distancia_maxima": round(bd + portao.TOL_DIST, 3),
                                 "correlacao_minima": round(bc - portao.TOL_CORR, 3), "pico_maximo_em_quadros": portao.LAG_MAX}
    return p


def aprendizados(itens):
    """APRENDIZADOS.md: a nota humana e o LESSONS.md de cada aprovado, com a origem, na ordem da aprovação."""
    partes, vistas = ["# Aprendizados do perfil\n\nO que cada item aprovado ensinou, com a origem. Gerado pelo aprender.py."], set()
    for r in sorted(itens, key=lambda r: r["data"]):
        bloco = [f"- Nota de {r['quem']}: {r['nota']}"] if r["nota"] else []
        lic = r.get("licoes")
        if lic and lic["md5"] not in vistas:  # a mesma lição não entra duas vezes
            vistas.add(lic["md5"])
            bloco += [f"Origem: `{lic['origem']}`", re.sub(r"(?m)^#", "###", lic["texto"]).strip()]
        if bloco:
            partes.append(f"## De {curto(r['mp4'])} ({r['tipo']}, aprovado por {r['quem']} em {r['data'][:10]})\n\n" + "\n\n".join(bloco))
    return "\n\n".join(partes) + "\n"


def travada():
    """A última versão travada: (n, perfil, aprendizados, impressão digital). n = 0 quando ainda não há."""
    ns = [int(d[8:]) for d in os.listdir(portao.PERFIL_DIR) if re.fullmatch(r"perfil-v\d+", d)] if os.path.isdir(portao.PERFIL_DIR) else []
    if not ns:
        return 0, {}, "", {}
    pasta = os.path.join(portao.PERFIL_DIR, f"perfil-v{max(ns)}")
    ler = lambda f: open(os.path.join(pasta, f), encoding="utf-8").read()
    return max(ns), json.loads(ler("perfil.json")), ler("APRENDIZADOS.md"), json.loads(ler("impressao_digital.json"))


def plano(d, pre=""):
    out = {}
    for k, v in d.items():
        out.update(plano(v, f"{pre}{k}.") if isinstance(v, dict) and v else {pre + k: v})
    return out


def mudancas(antes, depois):
    a, b = plano(antes), plano(depois)
    return [f"- `{k}`: {json.dumps(a[k], ensure_ascii=False) if k in a else 'nada'} → {json.dumps(b[k], ensure_ascii=False) if k in b else 'sai'}"
            for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]


def revisao_texto():
    """O texto da REVISAO.md, ou None quando os aprovados não mudam nada no perfil travado."""
    itens = aprovados()
    novo, licoes = perfil(itens), aprendizados(itens)
    n, atual, atual_md, dig = travada()
    if novo == atual and licoes == atual_md:
        return None
    entram = [r for r in sorted(itens, key=lambda r: r["data"]) if ident(r) not in dig.get("itens", [])]
    porque = [f"- {r['tipo']} `{curto(r['mp4'])}`, aprovado por {r['quem']} em {r['data'][:10]}"
              + (f": \"{r['nota']}\"" if r["nota"] else "")
              + (f". Medidas: {json.dumps(r['medidas'], ensure_ascii=False)}" if r.get("medidas") else "") for r in entram]
    lic = [f"- {r['licoes']['origem']}" for r in entram if r.get("licoes") and r["licoes"]["md5"] not in atual_md]
    return "\n".join([
        f"# Revisão do perfil de estilo: perfil-v{n + 1}", "",
        f"Hoje vale: {'perfil-v' + str(n) if n else 'nenhuma versão travada ainda'}. Nada muda até alguém dar o ok com:", "",
        f"    {comando('aprender.py', 'travar')}", "",
        "Antes de travar, a catraca roda de novo: cada versão aprovada é re-renderizada em prévia e tem que sair idêntica.",
        "Para descartar a revisão, apague este arquivo. Ele volta no próximo aprovado.", "",
        "## Por quê: aprovados que ainda não estão no perfil", "", *(porque or ["- nenhum item novo: mudou o que já estava aprovado"]), "",
        "## O que muda no perfil.json", "", *(mudancas(atual, novo) or ["- nada"]), "",
        "## Lições que entram no APRENDIZADOS.md", "", *(lic or ["- nenhuma lição nova"]), ""])


def revisar():
    texto = revisao_texto()
    if texto is None:
        if os.path.exists(REVISAO):
            os.remove(REVISAO)
        return None
    open(REVISAO, "w", encoding="utf-8").write(texto)
    return REVISAO


def gravar_versao(raiz, n, arquivos, quem, itens):
    """Cria perfil-vN com os arquivos e a impressão digital; tudo fica só leitura (versão travada é imutável)."""
    pasta = os.path.join(raiz, f"perfil-v{n}")
    if os.path.exists(pasta):
        raise Falha(f"{pasta} já existe e versão travada não se reescreve", "VERSAO_JA_EXISTE")
    os.makedirs(pasta)
    for nome, texto in arquivos.items():
        open(os.path.join(pasta, nome), "w", encoding="utf-8").write(texto)
    dig = {"versao": f"perfil-v{n}", "travada_em": agora(), "por": quem, "itens": itens,
           "sha256": {nome: portao.sha256(os.path.join(pasta, nome)) for nome in arquivos}}
    json.dump(dig, open(os.path.join(pasta, "impressao_digital.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for nome in [*arquivos, "impressao_digital.json"]:
        os.chmod(os.path.join(pasta, nome), 0o444)
    return pasta, dig


def aprovar(a):
    mp4 = os.path.abspath(a.mp4)
    if not os.path.exists(mp4):
        raise Falha(f"não achei o vídeo {mp4}", "VIDEO_NAO_ENCONTRADO", uso=True)
    clone = a.tipo == "clone"
    molde = os.path.dirname(mp4) if clone else os.path.abspath(a.molde)
    versao = None if clone else os.path.abspath(a.versao or portao.versao_padrao(mp4, molde))
    projeto = os.path.abspath(a.projeto or (molde if clone else os.path.dirname(molde)))
    args = [a.mp4, "--tipo", a.tipo] + (["--versao", versao, "--molde", molde] if versao else []) + ["--projeto", projeto]
    motivos, med, md5s = portao.rodar(mp4, a.tipo, versao, molde, [r["compare"] for r in aprovados() if r["tipo"] == "clone"])
    laudo = portao.laudo(mp4, a.tipo, motivos, med)
    base = {"data": agora(), "video": mp4, "tipo": a.tipo, "versao": versao, "molde": molde, "quem": a.quem, "nota": a.nota,
            "medidas": laudo["medidas"]}
    if motivos:
        dec = decidir(projeto, dict(base, decisao="reprovado", motivos=motivos))
        raise Falha(f"REPROVOU no portão: {laudo['video']}. {motivos[0]}. Nada entrou no perfil.", "REPROVADO_NO_PORTAO",
                    comando=comando("aprender.py", "aprovar", *args, "--nota", a.nota or "..."),
                    motivo="corrija os motivos e rode de novo", portao=laudo, decisoes=dec)
    fonte = os.path.join(os.path.dirname(mp4), "LESSONS.md")
    licoes = None
    if os.path.exists(fonte):
        txt = open(fonte, encoding="utf-8").read()
        licoes = {"origem": curto(fonte), "md5": hashlib.md5(txt.encode()).hexdigest(),
                  "texto": txt.replace(" \u2014 ", ", ").replace("\u2014", ", ").replace("\u2013", "-")}  # regra do projeto: sem travessão
    rec = {"tipo": a.tipo, "molde": molde, "versao": versao, "valores": None if clone else json.load(open(versao, encoding="utf-8")),
           "mp4": mp4, "projeto": projeto, "compare": med if clone else None, "medidas": laudo["medidas"], "nota": a.nota,
           "licoes": licoes, "data": base["data"], "quem": a.quem, "status": "pendente" if a.pendente else "aprovado", "motivo": []}
    if md5s:  # a prévia desta versão e a impressão digital do molde viram a régua dela nas próximas regressões
        rec["molde_digital"] = portao.digital_do_molde(molde)
        os.makedirs(PREVIAS, exist_ok=True)
        rec["previa"] = os.path.join(PREVIAS, ident(rec) + ".txt")
        open(rec["previa"], "w").write("\n".join(md5s) + "\n")
    if not a.pendente:
        rec["motivo"] = regressao([r for r in aprovados() if r["mp4"] != mp4])
        if rec["motivo"]:
            rec["status"] = "quarentena"
    with open(REGISTRO, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    dec = decidir(projeto, dict(base, decisao=rec["status"], motivos=rec["motivo"]))
    extra = {"portao": laudo, "decisoes": dec, "registro": REGISTRO}
    if rec["status"] == "pendente":
        saida(f"PASSOU no portão e ficou pendente de aprovação humana: {laudo['video']}.",
              comando("aprender.py", "aprovar", *[x for x in args], "--nota", a.nota or "..."),
              "quando a pessoa aprovar o vídeo, rode o mesmo comando sem --pendente", True, **extra)
    if rec["status"] == "quarentena":
        raise Falha(f"QUARENTENA: {laudo['video']} passou no portão, mas o molde atual mudou o que já estava aprovado. "
                    f"O perfil não mudou.", "QUARENTENA", motivo="; ".join(rec["motivo"]), mudancas=rec["motivo"], **extra)
    rev = revisar()
    if rev:
        saida(f"Aprovado: {laudo['video']}. O perfil não muda sozinho: a REVISAO.md diz o que mudaria e por quê.",
              comando("aprender.py", "travar"), f"leia {rev} e, se estiver de acordo, dê o ok travando a versão nova", True,
              revisao=rev, **extra)
    saida(f"Aprovado: {laudo['video']}. Nada muda no perfil de estilo.", "", "", False, **extra)


def travar(a):
    if not os.path.exists(REVISAO):
        saida("Não há revisão esperando: o perfil travado já tem tudo o que foi aprovado.", comando("aprender.py", "perfil"), "ver o perfil", False)
    texto = revisao_texto()
    if texto != open(REVISAO, encoding="utf-8").read():  # o ok vale para o texto que a pessoa leu
        revisar()
        raise Falha("A REVISAO.md estava desatualizada e foi refeita. Leia de novo antes de travar.", "REVISAO_DESATUALIZADA",
                    comando=comando("aprender.py", "travar"), motivo=f"leia {REVISAO}")
    itens = aprovados()
    mudou = regressao(itens)  # a catraca vale antes de travar
    if mudou:
        raise Falha("A catraca não deixou travar: o molde atual mudou versões já aprovadas.", "REGRESSAO",
                    motivo="; ".join(mudou), mudancas=mudou)
    n = travada()[0] + 1
    pasta, dig = gravar_versao(portao.PERFIL_DIR, n, {"perfil.json": json.dumps(perfil(itens), ensure_ascii=False, indent=2) + "\n",
                                                      "APRENDIZADOS.md": aprendizados(itens), "REVISAO.md": texto},
                               a.quem, [ident(r) for r in itens])
    os.remove(REVISAO)
    saida(f"Perfil travado em perfil-v{n}, com a impressão digital dos arquivos.", comando("aprender.py", "perfil"),
          "ver o perfil em vigor", False, pasta=pasta, impressao_digital=dig)


def ver_perfil(a):
    n, p, _, dig = travada()
    avisos = portao.integridade()
    espera = os.path.exists(REVISAO)
    resumo = (f"Perfil em vigor: perfil-v{n}, travado em {dig['travada_em'][:16]}." if n else "Ainda não há versão travada do perfil.") \
        + (" Há uma revisão esperando o ok." if espera else "") + (f" Atenção: {len(avisos)} aviso(s) de integridade." if avisos else "")
    saida(resumo, comando("aprender.py", "travar") if espera else "", f"leia {REVISAO}" if espera else "", espera,
          versao=f"perfil-v{n}" if n else None, perfil=p, avisos=avisos)


def lista(a):
    itens = list(atuais().values())
    conta = collections.Counter(r["status"] for r in itens)
    pend = [r for r in itens if r["status"] == "pendente"]
    prox = comando("aprender.py", "aprovar", pend[0]["mp4"], "--tipo", pend[0]["tipo"], *(["--versao", pend[0]["versao"], "--molde", pend[0]["molde"]] if pend[0]["versao"] else []),
                   "--projeto", pend[0]["projeto"], "--nota", "...") if pend else ""
    saida(f"{len(itens)} vídeo(s) no registro: " + ", ".join(f"{v} {k}" for k, v in sorted(conta.items())) + "." if itens else "O registro está vazio.",
          prox, "há vídeo esperando a aprovação humana" if pend else "", bool(pend),
          itens=[{"status": r["status"], "tipo": r["tipo"], "id": ident(r), "video": curto(r["mp4"]), "data": r["data"],
                  "quem": r["quem"], "nota": r["nota"], "motivo": r["motivo"]} for r in itens])


def ver_decisoes(a):
    projeto = os.path.abspath(a.projeto)
    ds = decisoes(projeto)
    ult = ds[-1] if ds else None
    saida(f"{len(ds)} decisão(ões) em {curto(projeto)}" + (f"; a última: {ult.get('decisao')} em {str(ult.get('data'))[:16]}." if ult else "."),
          "", "", False, decisoes=ds)


def autoteste():
    portao.autoteste()
    with tempfile.TemporaryDirectory() as tmp:  # decisões: o formato antigo é lido antes das linhas novas, e não é reescrito
        os.makedirs(os.path.join(tmp, "." + portao.NOME))
        antigo = os.path.join(tmp, "." + portao.NOME, "decisoes.json")
        json.dump([{"decisao": "reprovado"}], open(antigo, "w"))
        decidir(tmp, {"decisao": "pendente"})
        assert decidir(tmp, {"decisao": "aprovado"}).endswith("decisoes.jsonl")
        assert [d["decisao"] for d in decisoes(tmp)] == ["reprovado", "pendente", "aprovado"]
        assert json.load(open(antigo)) == [{"decisao": "reprovado"}] and decisoes(os.path.join(tmp, "vazio")) == []
    with tempfile.TemporaryDirectory() as tmp:
        ok, mudou = os.path.join(tmp, "ok.txt"), os.path.join(tmp, "mudou.txt")
        open(ok, "w").write("a\nb\n")
        open(mudou, "w").write("a\nb\n")
        itens = [{"tipo": "versao", "molde": "/m/satellite", "mp4": "/s/junior.mp4", "previa": ok},
                 {"tipo": "versao", "molde": "/m/satellite", "mp4": "/s/irmao.mp4", "previa": mudou},
                 {"tipo": "clone", "molde": "/r/joi", "mp4": "/r/joi/final.mp4"}]
        falsa = lambda r: ["a", "b"] if r["previa"] == ok else ["a", "c"]  # o molde novo mexeu na irmão
        mexido = lambda m: "depois"  # a impressão digital do molde mudou desde a aprovação
        assert regressao(itens, falsa, mexido) == ["satellite-irmao: 1 de 2 quadros da prévia mudaram com o molde atual"]
        assert regressao(itens[:1], falsa, mexido) == []
        assert regressao([dict(itens[1], molde_digital="antes")], falsa, lambda m: "antes") == []  # molde igual: nem renderiza
        gravar_versao(tmp, 1, {"perfil.json": "{}\n"}, "teste", [])
        assert portao.integridade(tmp) == []
        os.chmod(os.path.join(tmp, "perfil-v1", "perfil.json"), 0o644)
        open(os.path.join(tmp, "perfil-v1", "perfil.json"), "w").write('{"cores": "mexida"}\n')
        assert portao.integridade(tmp) == ["perfil-v1 perdeu a integridade: perfil.json foi editado à mão depois de travado"]
    c = {"distancia": 0.004, "correlacao": 0.997, "movimento": 1.0, "lag": 0, "cortes": "6/6"}
    p = perfil([{"tipo": "clone", "molde": "/r/joi", "mp4": "/r/joi/final.mp4", "compare": c},
                {"tipo": "clone", "molde": "/r/sat", "mp4": "/r/sat/final.mp4", "compare": dict(c, distancia=0.010, correlacao=0.981)}])
    assert p["regua_dos_clones"]["distancia_maxima"] == 0.012 and p["regua_dos_clones"]["correlacao_minima"] == 0.977
    assert mudancas({"a": {"x": 1}}, {"a": {"x": 2, "y": 3}}) == ["- `a.x`: 1 → 2", "- `a.y`: nada → 3"]


def main():
    autoteste()
    ap = portao.Args(prog="aprender.py", description="o Apple Style UI aprende com o que a pessoa aprova")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap_a = sub.add_parser("aprovar")
    ap_a.add_argument("mp4")
    ap_a.add_argument("--tipo", required=True, choices=["clone", "versao", "video-novo"])
    ap_a.add_argument("--nota", default="")
    ap_a.add_argument("--quem", default=getpass.getuser())
    ap_a.add_argument("--pendente", action="store_true", help="passou no portão, mas ainda espera a aprovação humana")
    ap_a.add_argument("--versao", help="JSON da versão (padrão: versoes/<nome do mp4>.json ao lado do molde)")
    ap_a.add_argument("--molde", default=os.path.join(portao.RAIZ, "moldes", "satellite", "molde"))
    ap_a.add_argument("--projeto", help="a pasta do vídeo ou do clone; as decisões ficam em .apple-style-ui/decisoes.jsonl dentro dela (padrão: a pasta do clone ou do motor)")
    ap_t = sub.add_parser("travar")
    ap_t.add_argument("--quem", default=getpass.getuser())
    sub.add_parser("perfil")
    sub.add_parser("lista")
    ap_d = sub.add_parser("decisoes")
    ap_d.add_argument("--projeto", required=True, help="a pasta do vídeo ou do clone")
    a = ap.parse_args()
    os.makedirs(portao.PERFIL_DIR, exist_ok=True)
    {"aprovar": aprovar, "travar": travar, "perfil": ver_perfil, "lista": lista, "decisoes": ver_decisoes}[a.cmd](a)


if __name__ == "__main__":
    portao.executar(main)
