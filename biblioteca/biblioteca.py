"""Biblioteca de referências do estilo Apple: acha, baixa, classifica com o Jev e gera a ficha "como faz".

Uso (os dados ficam em $ASUI_DADOS; sem a variável, em ~/.apple-style-ui/biblioteca):
  python3 biblioteca.py atualizar [--fundo]       # tudo de uma vez; seguro rodar de novo
  python3 biblioteca.py descobrir [--fundo] [--desde <fonte>]   # perfis e buscas de fontes-salvas.json (ego-browser)
  python3 biblioteca.py awesome <pasta>           # põe na fila os vídeos do X de um data/library do awesome-opus
  python3 biblioteca.py baixar [N] [instagram|x]  # baixa, em versão leve, o que está em fontes.json e ainda não tem vídeo
  python3 biblioteca.py classificar <pasta_videos> <saida.jsonl>
  python3 biblioteca.py qualidade [N]             # ffprobe em tudo; rebaixa na melhor qualidade até N fichas da galeria
  python3 biblioteca.py apple|unidade <videos> <classes.jsonl>   # passadas extras (linhas novas já vêm com elas)
  python3 biblioteca.py montar <classes.jsonl> <pasta_audio> <pasta_repo>

`classificar` retoma de onde parou (pula id já presente na saída) e faz uma chamada só por vídeo, com as perguntas das
passadas apple e unidade junto. `montar` lê também o <id>.info.json do yt-dlp, o qualidade.json e o <id>.json do
`sharingan audio.py`, escreve fichas/<id>.json de todos os classificados e põe na galeria e no README só o que é
estilo Apple de verdade, por nível (provada, clonável, referência).
Ritmo: um pedido a cada 3 s por site; erro 429 pausa 15 min e, se repetir, para. Para no disco abaixo de 2,5 GB livres
ou com a pasta de vídeos acima de $ASUI_LIMITE_GB (padrão 4,1 GB).
"""
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from jev_classificar import MODELO, PRECO_MTOK, RAIZ, chave, quadros

AQUI = pathlib.Path(__file__).resolve().parent
DADOS = pathlib.Path(os.environ.get('ASUI_DADOS', '~/.apple-style-ui/biblioteca')).expanduser()
SALVAS = AQUI / 'fontes-salvas.json'
REPO = AQUI  # a pasta biblioteca/ do produto: README.md, fichas/, prompts/, site/
SHARINGAN = RAIZ / 'ferramentas/video-sharingan'
LIMITE_VIDEOS = float(os.environ.get('ASUI_LIMITE_GB', '4.1')) * 1e9

Q4 = 'the four frames `a`, `b`, `c`, `d` (taken at 15, 40, 65 and 90% of one short video)'
ESCOLHAS = {
    'tipo': ('What kind of video is shown in ' + Q4 + '?', {
        'ui_animacao': 'A pure interface or product animation: UI elements, cards, icons, no person on camera.',
        'pessoa_estilo_apple': 'A person talking, placed inside clean Apple-like design: rounded cards, phone frames, UI pop-ups.',
        'pessoa_legenda_comum': 'A person talking full screen with ordinary captions or overlays.',
        'bastidor_editor': 'A phone filming a computer screen with editing software open.',
        'tutorial_tela': 'A screen recording or tutorial of software.',
        'outro': 'Something else: photos, film footage, memes.'}),
    'fundo': ('What is the background in ' + Q4 + '?', {
        'claro_neutro': 'Plain light background: white, off-white or light gray, mostly empty.',
        'pastel_ou_gradiente_suave': 'Soft pastel color or a gentle gradient.',
        'wallpaper_ios_macos': 'An iOS or macOS style wallpaper.',
        'escuro_com_glow': 'Dark or black background, often with neon or glowing light.',
        'foto_video_real': 'A real photo or filmed scene fills the frame.'}),
    'densidade': ('How crowded is the composition in ' + Q4 + '?', {
        'um_heroi': 'One hero element with lots of empty space around it.',
        'dois_tres': 'Two or three elements, still clean.',
        'poluido': 'Busy and cluttered, many elements competing.'}),
    'acabamento': ('How are the interface elements rendered in ' + Q4 + '?', {
        'sombra_suave': 'Soft, diffuse shadows and one or two Apple-like system colors.',
        'flat': 'Flat, no shadows.',
        'neon': 'Saturated neon colors and glow.',
        'contorno_duro': 'Hard outlines or hard drop shadows.'}),
    'texto': ('How does text appear in ' + Q4 + '?', {
        'palavra_com_blur': 'Words appear one by one, some still blurred while entering.',
        'palavra_destacada': 'Clean sans-serif line with one word highlighted in another color.',
        'frase_limpa': 'A clean static line of sans-serif text.',
        'legenda_capcut': 'CapCut-style captions: boxes, thick outlines, emoji, many colors.',
        'sem_texto': 'No text on screen.'}),
    'ferramenta': ('Which tool does the post caption in `legenda` say was used to make the video?', {
        'after_effects': 'After Effects, Premiere or another Adobe tool.',
        'ia_codigo': 'Claude, an AI model or code (Remotion, HyperFrames).',
        'outra': 'Another named tool (Figma, Jitter, Rive, CapCut, Final Cut).',
        'nao_diz': 'The caption does not say.'}),
    'entrega': ('What does the post caption in `legenda` offer to people who comment or follow?', {
        'arquivo_projeto': 'Project files or templates.',
        'sons_musica': 'Sound effects or music.',
        'guia_prompt': 'A guide, prompt, storyboard or tutorial.',
        'curso_servico': 'A course, mentorship or paid service.',
        'nada': 'Nothing is offered.'}),
}
PECAS = {
    'dynamic_island': 'an iPhone Dynamic Island (black pill at the top of the screen) showing content',
    'notificacao': 'an iOS or macOS notification banner',
    'imessage': 'iMessage or chat bubbles',
    'cursor': 'a mouse cursor or hand pointer',
    'iphone': 'an iPhone frame or phone mockup',
    'janela': 'a laptop, browser or macOS window',
    'icone_app': 'a big app icon',
    'pessoa_no_cartao': 'a real person video placed inside a rounded card or phone frame over a designed background',
    'legenda_fala': 'captions of spoken words over a person',
    'numero_grande': 'a big number, price or counter',
    'grafico': 'a chart or graph',
    'botao_pilula': 'a pill-shaped button or toggle',
    'busca': 'a search bar or text input field',
    'teclado': 'an on-screen keyboard',
    'mapa': 'a map',
    'emoji_3d': 'large 3D emoji used as illustrations',
    'pilha_cartoes': 'a stack of overlapping cards',
    'print_site': 'a screenshot of a real website or app inside the design',
    'vidro': 'frosted or liquid glass panels (blurred, translucent)',
}

PERGUNTAS = {k: {'type': 'choice', 'instructions': q, 'criteria': c} for k, (q, c) in ESCOLHAS.items()}
PERGUNTAS['acabamento_pro'] = {'type': 'score', 'instructions': 'How polished and professional is the motion design in ' + Q4 + '?',
                               'criteria': ['Amateur', 'Decent', 'Good, clean and consistent', 'Top studio level, like an Apple keynote']}
PERGUNTAS['isca'] = {'type': 'noul', 'instructions': 'The post caption in `legenda` asks people to comment a word to receive something.'}
PERGUNTAS |= {k: {'type': 'noul', 'instructions': f'Is there {v} in any of {Q4}?'} for k, v in PECAS.items()}


def legenda(pasta, vid):
    info = pasta / f'{vid}.info.json'
    return (json.loads(info.read_text()).get('description') or '')[:1200] if info.exists() else ''


def valor(r):
    return round(r['noul'], 2) if r['type'] == 'noul' else round(r['score'], 2) if r['type'] == 'score' else r['choice']


def perguntar(perguntas, video, segredo):
    """Uma chamada ao Jev com 4 quadros do vídeo e a legenda do post. Devolve (duração, respostas, tokens de entrada)."""
    dur, imgs = quadros(video)
    corpo = {'model': MODELO, 'questions': perguntas,
             'state': {**{r: f'img-{r}' for r in 'abcd'}, 'legenda': legenda(video.parent, video.stem)},
             'assets': {f'img-{r}': {'type': 'image', 'format': 'jpg', 'data_base64': b} for r, b in zip('abcd', imgs[::2])}}
    req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=json.dumps(corpo).encode(), headers={
        'Authorization': f'Bearer {segredo}', 'Content-Type': 'application/json', 'TypeSafe-Danger-Zone-Images': 'true'})
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read())
            return dur, d['answers'], d.get('usage', {}).get('input_tokens', 0)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or tentativa == 4:
                raise RuntimeError(f'{e.code}: {e.read()[:200].decode(errors="replace")}')
        except Exception:  # rede caiu: tenta de novo
            if tentativa == 4:
                raise
        time.sleep(2 ** tentativa)


def classificar(pasta, saida):
    pasta, saida = pathlib.Path(pasta), pathlib.Path(saida)
    feitos = {json.loads(l)['id'] for l in saida.read_text().splitlines()} if saida.exists() else set()
    videos = [v for v in sorted(pasta.glob('*.mp4')) if v.stem not in feitos]
    segredo = chave()
    extras = APPLE | UNIDADE  # as passadas extras vão na mesma chamada: um vídeo, uma ida ao Jev

    def um(v):
        try:
            dur, a, tokens = perguntar(PERGUNTAS | extras, v, segredo)
        except Exception as e:
            return {'id': v.stem, 'erro': str(e)[:300]}
        return {'id': v.stem, 'duracao': round(dur, 1), **{k: a[k]['choice'] for k in ESCOLHAS},
                'confianca': {k: round(a[k]['confidence'], 2) for k in ESCOLHAS},
                'acabamento_pro': round(a['acabamento_pro']['score'], 2), 'isca': round(a['isca']['noul'], 2),
                'pecas': {k: round(a[k]['noul'], 2) for k in PECAS}, **{k: valor(a[k]) for k in extras}, 'tokens': tokens}

    with open(saida, 'a') as f, ThreadPoolExecutor(8) as ex:
        for linha in ex.map(um, videos):
            f.write(json.dumps(linha, ensure_ascii=False) + '\n')
            f.flush()
    return len(videos)


# Peça -> itens do catálogo do HyperFrames (`npx hyperframes add <nome>`), conferidos no catálogo v0.8.184.
CATALOGO = {
    'dynamic_island': (['modal-morph', 'spring-pop'], 'pílula preta que cresce e mostra informação (Dynamic Island)', 'Dynamic Island'),
    'notificacao': (['native-notification-pop', 'notification-stack', 'macos-notification'], 'aviso que desce do topo da tela', 'notification banner'),
    'imessage': (['chat-message', 'message-thread-reveal', 'typing-indicator'], 'balões de conversa aparecendo um a um', 'iMessage chat bubbles'),
    'cursor': (['oversized-cursor', 'press-ripple', 'cursor-zoom-follow'], 'seta ou mãozinha do Mac que entra e clica', 'macOS cursor click'),
    'iphone': (['device-frame-stage', 'vfx-iphone-device'], 'moldura de iPhone com a tela dentro', 'iPhone mockup'),
    'janela': (['browser-device-stage', 'macos-tahoe-liquid-glass', 'ui-focus-zoom'], 'janela do Mac ou do navegador', 'macOS window'),
    'icone_app': (['spring-pop', 'icon-swap'], 'ícone de app grande que surge com mola', 'app icon pop'),
    'pessoa_no_cartao': (['device-frame-stage', 'split-tilt-cards', 'focus-swap'], 'o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone', 'talking head in rounded card'),
    'legenda_fala': (['per-word-rise', 'blur-in'], 'legenda da fala entrando palavra a palavra', 'word-by-word captions'),
    'numero_grande': (['number-wheel', 'count-up', 'number-pop-in'], 'número ou preço que gira até o valor', 'rolling digits counter'),
    'grafico': (['count-up'], 'gráfico que se desenha', 'animated chart'),
    'botao_pilula': (['toggle-flip', 'spring-pop', 'press-ripple'], 'botão em forma de pílula que é tocado', 'pill button / toggle'),
    'busca': (['typewriter', 'ai-chat-reveal'], 'barra de busca sendo digitada', 'search bar typing'),
    'teclado': (['ai-chat-reveal'], 'teclado do iPhone subindo', 'iOS keyboard'),
    'mapa': (['nyc-paris-flight'], 'mapa com trajeto', 'map route'),
    'emoji_3d': (['spring-pop'], 'emoji 3D como ilustração', '3D emoji'),
    'pilha_cartoes': (['spring-stack-shuffle', 'notification-stack', 'focus-rack'], 'cartões empilhados que se reorganizam', 'card stack'),
    'print_site': (['browser-device-stage', 'ui-focus-zoom', 'cursor-zoom-follow'], 'print real do produto dentro do design', 'real product screenshot'),
    'vidro': (['liquid-glass-widgets', 'liquid-glass-notification'], 'painel de vidro fosco ou líquido', 'frosted / liquid glass'),
}
TEXTO = {'palavra_com_blur': (['blur-in', 'per-word-rise', 'soft-blur-in'], 'palavras entram uma a uma saindo do desfoque', 'word-by-word blur-in'),
         'palavra_destacada': (['soft-blur-in'], 'frase limpa com uma palavra em azul', 'one highlighted word')}
FUNDO = {'claro_neutro': 'fundo claro e vazio (branco a cinza #f5f5f7)', 'pastel_ou_gradiente_suave': 'fundo pastel ou gradiente suave',
         'wallpaper_ios_macos': 'wallpaper estilo iOS/macOS', 'escuro_com_glow': 'fundo escuro com brilho', 'foto_video_real': 'imagem real de fundo'}
DENS = {'um_heroi': 'um elemento por vez, com muito espaço vazio', 'dois_tres': 'dois ou três elementos por cena', 'poluido': 'muitos elementos'}


APPLE = {  # segunda passada: a primeira pôs no topo anúncio de gradiente vivo, bem-feito mas fora do estilo
    'apple_limpo': {'type': 'noul', 'instructions': 'Do ' + Q4 + ' look like Apple\'s own clean, minimal design language: light '
                    'neutral backgrounds, restrained colors, iOS/macOS-like interface elements, generous empty space?'},
    'paleta': {'type': 'choice', 'instructions': 'What is the overall color palette of ' + Q4 + '?', 'criteria': {
        'neutra_clara': 'Mostly white, light gray or soft pastel with one accent color.',
        'vivida_saturada': 'Bold, saturated, many strong colors or vivid gradients.',
        'escura': 'Mostly dark or black.'}},
}


UNIDADE = {  # o Júnior notou: post de vitrine (widgets + "comenta X") tem o componente como referência, não a edição
    'unidade': {'type': 'choice', 'instructions': 'What does the post in ' + Q4 + ' (caption in `legenda`) mainly show?', 'criteria': {
        'filme': 'A finished piece with several scenes and a beginning, middle and end: a launch film, an ad, an edited story.',
        'peca': 'A showcase of one or a few isolated UI widgets or components animating, often looping or in a grid, '
                'as a sample of something the author gives away or sells.',
        'processo': 'The making-of: the editing software, a tutorial or a before/after.'}},
    'entrega2': {'type': 'choice', 'instructions': 'What does the caption in `legenda` offer to people who comment or follow?', 'criteria': {
        'arquivo_projeto': 'Project files, templates or the widgets/components themselves.',
        'sons_musica': 'Sound effects or music.', 'guia_prompt': 'A guide, prompt, storyboard or tutorial.',
        'curso_servico': 'A course, mentorship or paid service.',
        'presente': 'A gift or freebie without saying what it is.', 'nada': 'Nothing is offered.'}},
}


def passada(pasta, classes, perguntas):
    """Acrescenta as respostas de `perguntas` a cada linha de classes.jsonl que ainda não tem."""
    pasta, classes = pathlib.Path(pasta), pathlib.Path(classes)
    linhas = [json.loads(l) for l in classes.read_text().splitlines()]
    segredo = chave()

    def um(c):
        if 'erro' in c or all(k in c for k in perguntas):
            return c
        try:
            _, a, _ = perguntar(perguntas, pasta / f"{c['id']}.mp4", segredo)
        except Exception:
            return c
        return c | {k: valor(a[k]) for k in perguntas}

    with ThreadPoolExecutor(8) as ex:
        novas = list(ex.map(um, linhas))
    classes.write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in novas))


# ---------- achar e baixar ----------

def ler_fontes():
    arq = DADOS / 'fontes.json'
    return json.loads(arq.read_text()) if arq.exists() else {}


def gravar_fontes(fontes):
    (DADOS / 'fontes.json').write_text(json.dumps(fontes, ensure_ascii=False, indent=0))


def falhas():
    arq = DADOS / 'falhou.txt'
    return {l.split('\t')[0] for l in arq.read_text().splitlines() if l.strip()} if arq.exists() else set()


def acrescentar(fontes, cod, origem):
    novo = cod not in fontes
    if origem not in fontes.setdefault(cod, []):
        fontes[cod].append(origem)
    return novo


JS_DESCOBRIR = r'''
const fontes = %s, conhecidos = new Set(%s), MAX = %d, SO_NOVOS = %s;
const dormir = ms => new Promise(r => setTimeout(r, ms));
const task = await taskSpace("apple-style-ui-biblioteca-ig");
const page = task.page("p1");
const fs = await import("node:fs/promises");
let vazias = 0;
for (const f of fontes) {
  const vistos = new Map();
  let parado = 0, bloqueio = "";
  const d = await fs.statfs("/System/Volumes/Data").catch(() => null);  // o vídeo do Instagram enche a memória e o swap come o disco
  if (d && d.bavail * d.bsize < 2.5e9) { console.log("ASUI " + JSON.stringify({ origem: f.origem, vistos: 0, achados: [], bloqueio: "disco abaixo de 2,5 GB livres" })); break; }
  try {
    try { await page.goto(f.url); } catch (e) { if (!/timed out/i.test(String(e))) throw e; }  // carga lenta não é bloqueio
    await dormir(6000);
    for (let i = 0; i <= MAX && parado < 2; i++) {
      const r = await page.evaluate(() => ({ url: location.href,
        itens: [...document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]')].map(a => [a.getAttribute("href"),
          [...a.querySelectorAll("svg[aria-label]")].map(s => s.getAttribute("aria-label")).join("|")]) }));
      if (/accounts\/login|challenge|suspended/.test(r.url)) { bloqueio = "o Instagram pediu login ou verificação: " + r.url; break; }
      const antes = vistos.size;
      let novos = 0;
      for (const [h, rotulo] of r.itens) {
        const m = h.match(/\/(?:p|reel)\/([A-Za-z0-9_-]{6,})/);
        if (!m || vistos.has(m[1])) continue;
        vistos.set(m[1], /\/reel\//.test(h) || /reel|clip|v[ií]deo/i.test(rotulo));
        if (!conhecidos.has(m[1])) novos++;
      }
      parado = (vistos.size === antes || (SO_NOVOS && !novos)) ? parado + 1 : 0;
      if (i < MAX && parado < 2) { await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); await dormir(4000); }
    }
  } catch (e) { bloqueio = String(e).slice(0, 200); }
  vazias = vistos.size ? 0 : vazias + 1;
  if (!bloqueio && vazias >= 2) bloqueio = "duas fontes seguidas sem nenhum post: pode ser bloqueio";
  console.log("ASUI " + JSON.stringify({ origem: f.origem, vistos: vistos.size, achados: [...vistos].filter(([, v]) => v).map(([k]) => k), bloqueio }));
  if (bloqueio) break;
  await page.goto("about:blank").catch(() => {});  // solta a memória da página antes da próxima fonte
  await dormir(8000);
}
await task.finish({ keep: [] });
'''


def descobrir(profundo=False, desde=''):
    """Rola os perfis (aba Reels) e as buscas salvas no navegador logado e põe em fontes.json os reels novos.
    Com profundo, rola até 10 vezes por fonte; sem, para quando uma rolagem não traz nada novo (uso diário).
    `desde` retoma uma rodada interrompida a partir da fonte cujo nome contém o texto."""
    salvas = json.loads(SALVAS.read_text())
    fontes = ler_fontes()
    lista = [{'origem': f'perfil:{p}', 'url': f'https://www.instagram.com/{p}/reels/'} for p in salvas['perfis']]
    lista += [{'origem': f'busca:{b}', 'url': 'https://www.instagram.com/explore/search/keyword/?q=' + urllib.parse.quote(b)}
              for b in salvas['buscas']]
    lista = lista[next((i for i, f in enumerate(lista) if desde in f['origem']), 0):]
    js = JS_DESCOBRIR % (json.dumps(lista), json.dumps(sorted(set(fontes) | falhas())), 10 if profundo else 3,
                         'false' if profundo else 'true')
    try:
        r = subprocess.run(['ego-browser', 'nodejs'], input=js, capture_output=True, text=True, timeout=4 * 3600)
        saida, erro = r.stdout + r.stderr, (r.stderr[-300:] if r.returncode else '')  # o console.log do ego-browser sai no stderr
        (DADOS / '_descoberta.log').write_text(saida)
    except (OSError, subprocess.TimeoutExpired) as e:
        saida, erro = '', str(e)[:300]
    novos, por_origem, bloqueio = [], {}, ''
    for linha in saida.splitlines():
        if linha.startswith('ASUI '):
            x = json.loads(linha[5:])
            bloqueio = bloqueio or x['bloqueio']
            n = [c for c in x['achados'] if acrescentar(fontes, c, x['origem'])]
            novos += n
            por_origem[x['origem']] = len(n)
    gravar_fontes(fontes)
    return novos, por_origem, bloqueio or (f'ego-browser: {erro}' if erro else '')


def awesome(pasta):
    """Põe em fontes.json os posts do X com vídeo de um data/library do awesome-opus-5-5-video-prompts (chave = id do X)."""
    fontes, novos = ler_fontes(), []
    for f in sorted(pathlib.Path(pasta).glob('*.json')):
        m = (json.loads(f.read_text())['post'].get('media') or [{}])[0]  # a primeira mídia do post
        st = re.search(r'/status/(\d+)', m.get('url') or '')
        if m.get('type') == 'video' and st and acrescentar(fontes, st.group(1), 'repo:awesome-opus'):
            novos.append(st.group(1))
    gravar_fontes(fontes)
    return novos


def repositorios():
    """Atualiza (git pull) ou clona os repositórios salvos e põe na fila os vídeos novos deles."""
    novos = []
    for r in json.loads(SALVAS.read_text()).get('repositorios', []):
        destino = DADOS / r['pasta_local']
        if destino.exists():
            subprocess.run(['git', '-C', str(destino), 'pull', '-q'], capture_output=True, timeout=600)
        else:
            subprocess.run(['git', 'clone', '-q', '--depth', '1', '--filter=blob:none', '--sparse', r['git'], str(destino)],
                           capture_output=True, timeout=600)
            subprocess.run(['git', '-C', str(destino), 'sparse-checkout', 'set', 'data/library'], capture_output=True, timeout=600)
        novos += awesome(destino / 'data/library')
    return novos


def sonda(video):
    o = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                            'stream=codec_name,width,height,avg_frame_rate,bit_rate:format=duration,bit_rate',
                                            '-of', 'json', str(video)]))
    s, f = o['streams'][0], o['format']
    n, d = (s.get('avg_frame_rate') or '0/0').split('/')
    return {'largura': s['width'], 'altura': s['height'], 'fps': round(int(n) / int(d), 2) if int(d) else None,
            'codec': s['codec_name'], 'kbps': round(int(s.get('bit_rate') or f.get('bit_rate') or 0) / 1000),
            'duracao': round(float(f['duration']), 1)}


def melhor_disponivel(info):
    """O melhor formato de vídeo que o site oferece, até 1080 no lado menor (é o que o rebaixe pede).
    A lista é a mesma do `yt-dlp -F` e fica guardada no info.json do download."""
    vs = [f for f in info.get('formats') or [] if f.get('vcodec') not in (None, 'none') and f.get('width') and f.get('height')]
    vs = [f for f in vs if min(f['width'], f['height']) <= 1080] or vs
    if not vs:
        return None
    b = max(vs, key=lambda f: (min(f['width'], f['height']), f.get('tbr') or 0))
    return {'lado': min(b['width'], b['height']), 'kbps': round(b.get('vbr') or b.get('tbr') or 0)}


def tem_melhor(q):
    m, lado = q.get('melhor'), min(q['largura'], q['altura'])
    return bool(m) and (m['lado'] > lado or (m['lado'] == lado and m['kbps'] > 1.25 * q['kbps']))


MELHOR = ['-S', 'res:1080,fps,vcodec:h264,br']  # 1080 basta para clonar; o 4K do X só gasta disco
LEVE = ['-S', 'res:360']  # vídeo novo: só para o Jev decidir; o que entra na galeria é rebaixado depois em 1080
POR_RODADA = int(os.environ.get('ASUI_POR_RODADA', '200'))  # downloads por site em cada `atualizar`; o resto fica na fila


def url_de(vid):
    return f'https://x.com/i/status/{vid}' if vid.isdigit() else f'https://www.instagram.com/p/{vid}/'


def ytdlp(vid, fonte, ordem, filtro=()):
    """Baixa num _tmp e só troca o arquivo quando o novo abre no ffprobe. Devolve 'ok', '429' ou o motivo da falha."""
    tmp = DADOS / 'videos' / '_tmp'
    tmp.mkdir(parents=True, exist_ok=True)
    # -N 4: os pedaços do HLS do X vêm da CDN em paralelo; o pedido ao site continua um por vídeo
    r = subprocess.run(['yt-dlp', '-q', '--no-warnings', '--no-progress', '-N', '4', '--playlist-items', '1', '-f', 'bv*+ba/b', *ordem,
                        *filtro, '--merge-output-format', 'mp4', '--write-info-json', '-o', str(tmp / f'{vid}.%(ext)s'), *fonte],
                       capture_output=True, text=True, timeout=900)
    novo, msg = tmp / f'{vid}.mp4', ''
    if novo.exists():
        try:
            sonda(novo)
            novo.replace(DADOS / 'videos' / f'{vid}.mp4')
            if (tmp / f'{vid}.info.json').exists():
                (tmp / f'{vid}.info.json').replace(DADOS / 'videos' / f'{vid}.info.json')
            msg = 'ok'
        except Exception:
            msg = 'o arquivo novo não abre'
    for p in tmp.glob(f'{vid}.*'):  # sobra de download parcial
        p.unlink()
    if msg:
        return msg
    if re.search(r'\b429\b|Too Many Requests|wait a few minutes|rate.?limit', r.stderr, re.I):
        return '429'
    erro = [l for l in r.stderr.splitlines() if l.strip()]
    return erro[-1][:200] if erro else 'pulado: mais de 60 s ou sem vídeo'


def disco():
    """'' se pode seguir baixando; senão, o motivo da parada."""
    livre = shutil.disk_usage(DADOS).free
    usado = sum(p.stat().st_size for p in (DADOS / 'videos').glob('*.mp4'))
    if livre < 2.5e9:
        return f'disco: só {livre / 1e9:.1f} GB livres'.replace('.', ',')
    return f'disco: pasta de vídeos com {usado / 1e9:.2f}'.replace('.', ',') + ' GB, acima do limite' if usado > LIMITE_VIDEOS else ''


def fila(ids, args):
    """Um vídeo por vez, um pedido a cada ~3 s. 429: pausa de 15 min e tenta mais uma vez; se repetir, para a fila."""
    feitos, falhou, parada = [], [], ''
    for vid in ids:
        parada = disco()
        if parada:
            break
        for tentativa in range(2):
            r = ytdlp(vid, *args(vid))
            if r != '429' or tentativa:
                break
            time.sleep(900)
        if r == '429':
            parada = f'429 no {vid}: parei a fila'
            break
        if r == 'ok':
            feitos.append(vid)
        else:
            falhou.append((vid, r))
        time.sleep(3)
    return feitos, falhou, parada


def registrar_falhas(fal):
    with open(DADOS / 'falhou.txt', 'a') as f:
        f.writelines(f'{v}\t{m}\n' for v, m in fal)


def baixar(limite=None, so=''):
    """Baixa o que está em fontes.json e ainda não tem vídeo nem falhou. Instagram e X em paralelo, cada um no seu ritmo.
    `so` ('instagram' ou 'x') deixa rodar dois processos ao mesmo tempo sem que um baixe o que o outro está baixando."""
    tem = {v.stem for v in (DADOS / 'videos').glob('*.mp4')}
    pend = [i for i in ler_fontes() if i not in tem and i not in falhas() and so in ('', 'x' if i.isdigit() else 'instagram')]
    filtro = ['--match-filter', 'duration <=? 60']  # PLANO §4: mais de 60 s não é referência de estilo

    def lote(ids):  # em lotes de 25 para gravar as falhas no caminho: se o processo cair, o que falhou não volta para a fila
        feitos, falhou, parada = [], [], ''
        for i in range(0, len(ids), 25):
            f, fal, parada = fila(ids[i:i + 25], lambda vid: ([url_de(vid)], LEVE, filtro))
            registrar_falhas(fal)
            feitos, falhou = feitos + f, falhou + fal
            if parada:
                break
        return feitos, falhou, parada

    with ThreadPoolExecutor(2) as ex:
        res = list(ex.map(lambda ids: lote(ids[:limite]), [[i for i in pend if not i.isdigit()], [i for i in pend if i.isdigit()]]))
    return {'instagram': len(res[0][0]), 'x': len(res[1][0]), 'falhas': sum(len(r[1]) for r in res),
            'parada': '; '.join(r[2] for r in res if r[2])}


def qualidade(rebaixar=()):
    """Mede cada vídeo (resolução, fps, bitrate, codec, duração) e o melhor formato que o site oferece. Depois rebaixa,
    um por vez e na ordem dada, os ids de `rebaixar` que têm formato melhor. Cada id é rebaixado uma vez só."""
    arq = DADOS / 'qualidade.json'
    q = json.loads(arq.read_text()) if arq.exists() else {}

    def medir(v):
        tam = v.stat().st_size
        if q.get(v.stem, {}).get('bytes') == tam:
            return None
        info = DADOS / 'videos' / f'{v.stem}.info.json'
        return v.stem, {**sonda(v), 'bytes': tam, 'melhor': melhor_disponivel(json.loads(info.read_text())) if info.exists() else None}

    def medir_todos():
        with ThreadPoolExecutor(8) as ex:
            for r in ex.map(medir, sorted((DADOS / 'videos').glob('*.mp4'))):
                if r:
                    q[r[0]] = q.get(r[0], {}) | r[1]
        arq.write_text(json.dumps(q, ensure_ascii=False, indent=0))

    medir_todos()
    alvo = [v for v in dict.fromkeys(rebaixar) if v in q and 'rebaixe' not in q[v] and tem_melhor(q[v])]

    def via(cdn):  # primeiro pelo info.json guardado (só a CDN, sem pedido ao site); se o link venceu, pelo endereço do post
        return lambda vid: (['--load-info-json', str(DADOS / 'videos' / f'{vid}.info.json')] if cdn else [url_de(vid)], MELHOR)

    feitos, parada = [], ''
    for vid in alvo:
        um, fal, parada = fila([vid], via(True))
        if fal:
            um, fal, parada = fila([vid], via(False))
        q[vid]['rebaixe'] = f"ok {time.strftime('%Y-%m-%d')}" if um else f"falhou: {(fal or [('', parada)])[0][1]}"
        feitos += um
        if parada:
            break
    medir_todos()
    return {'medidos': len(q), 'com_formato_melhor': sum(tem_melhor(x) for x in q.values() if 'rebaixe' not in x),
            'rebaixados': len(feitos), 'parada': parada}


def medir_som(ids):
    """Mede o som (BPM, eventos por segundo) com o sharingan; pula o que já foi medido."""
    (DADOS / 'audio').mkdir(exist_ok=True)

    def um(vid):
        out = DADOS / 'audio' / f'{vid}.json'
        if not out.exists():
            subprocess.run([str(SHARINGAN / '.venv/bin/python3'), str(SHARINGAN / 'scripts/audio.py'),
                            str(DADOS / 'videos' / f'{vid}.mp4'), '-o', str(out)], capture_output=True)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(um, ids))


# ---------- a ficha ----------

def nota(c, meta):
    """0 a 100: quanto essa referência "fica boa" no estilo. Acabamento e cara de Apple pesam; curtidas desempatam."""
    regras = (c['fundo'] in ('claro_neutro', 'pastel_ou_gradiente_suave', 'wallpaper_ios_macos')) + (c['densidade'] != 'poluido') \
        + (c['acabamento'] == 'sombra_suave') + (c['texto'] != 'legenda_capcut')
    apple_ = 0.5 * regras / 4 + 0.35 * c.get('apple_limpo', 0.5) + 0.15 * (c.get('paleta', 'neutra_clara') == 'neutra_clara')
    curt = math.log10((meta.get('like_count') or 0) + 1) / 6  # 1 milhão de curtidas = 1
    return round(100 * (0.4 * c['acabamento_pro'] / 3 + 0.45 * apple_ + 0.15 * min(curt, 1)))


CLARO = ('claro_neutro', 'pastel_ou_gradiente_suave', 'wallpaper_ios_macos')


def apple(c):
    """Estilo Apple de verdade (PLANO §3: fundo claro e limpo, sombra suave; contraexemplo: escuro com neon).
    O apple_limpo do Jev sai baixo até em referência boa (o Satellite deu 0,42), então ele só corta o que está bem abaixo."""
    return (c['fundo'] in CLARO and c.get('paleta') != 'vivida_saturada' and c['acabamento'] != 'neon'
            and c['texto'] != 'legenda_capcut' and c['tipo'] not in ('outro', 'pessoa_legenda_comum')
            and c.get('apple_limpo', 0) >= 0.2 and (c['densidade'] != 'poluido' or c.get('apple_limpo', 0) >= 0.45))


PROVADAS = {  # clones com nota de fidelidade (PRODUTO.md): distância e correlação de movimento; caminho a partir da pasta do rascunho
    'DWWQEOmDfsf': ('Satellite', 0.010, 0.981, ''),
    'DPJJwcujV0X': ('Joi', 0.004, 0.997, ''),
    'DafsqUut4x1': ('VoiceOS', 0.010, 0.999, ''),
    'DaIOD8QSEAz': ('fala-destaque', None, None, ''),  # pessoa falando: a nota é por máscara (NOTAS.md do molde), sem número comparável
}
NIVEL = {'provada': 'Provada', 'clonavel': 'Clonável', 'referencia': 'Referência'}


def ordem_rebaixe(linhas):
    """Ids da galeria na ordem de rebaixe: primeiro os que viram clonáveis com a fonte boa (até 15 s, filme ou peça)."""
    g = [c for c in linhas if 'erro' not in c and (apple(c) or c['id'] in PROVADAS)]
    return [c['id'] for c in sorted(g, key=lambda c: (not (c['duracao'] <= 15 and c.get('unidade') in ('filme', 'peca')),
                                                      -c.get('apple_limpo', 0)))]


def nivel(c, q):
    """provada: tem clone com nota. clonavel: fonte boa (1080 no lado menor), até 15 s, filme ou peça. referencia: o resto."""
    if c['id'] in PROVADAS:
        return 'provada'
    boa = bool(q) and min(q['largura'], q['altura']) >= 1000  # o Instagram entrega 1078 ou 992 em vez de 1080 em alguns posts
    return 'clonavel' if boa and c['duracao'] <= 15 and c.get('unidade') in ('filme', 'peca') else 'referencia'


def como_fazer(c, meta, audio):
    pecas = [k for k, p in c['pecas'].items() if p >= 0.6 and k in CATALOGO]
    usados = [(CATALOGO[k], k) for k in pecas] + ([(TEXTO[c['texto']], c['texto'])] if c['texto'] in TEXTO else [])
    formato = '9:16' if meta['height'] > meta['width'] * 1.2 else ('1:1' if abs(meta['height'] - meta['width']) < 50 else '16:9')
    if c.get('unidade') == 'peca':  # vitrine: a referência é o componente, não a edição do vídeo
        linhas = [f"Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de {meta['url']}.",
                  'Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o '
                  'estado final, para eu reaproveitar em outros vídeos.', '',
                  f"Visual: {FUNDO.get(c['fundo'], c['fundo'])}; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve)."]
    else:
        linhas = [f"Faça em HyperFrames um vídeo {formato} de {c['duracao']:.0f} s no estilo Apple, tomando como referência: {meta['url']}", '',
                  f"Visual: {FUNDO.get(c['fundo'], c['fundo'])}; {DENS[c['densidade']]}; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve)."]
    if usados:
        linhas += ['', 'Peças (instale com `npx hyperframes add <nome>`):']
        linhas += [f"- {pt} ({en}): {', '.join(f'`{n}`' for n in nomes)}" for (nomes, pt, en), _ in usados]
    linhas += ['', 'Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; '
               'um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.']
    if audio and audio.get('onsets_per_s'):
        bpm = audio.get('tempo_bpm')
        fora = len(audio.get('off_beat_onsets_s', [])) / (audio['onset_count'] / audio['onsets_per_s'])
        trilha = f"música de ~{bpm:.0f} BPM por baixo; " if bpm else ''
        linhas += ['', f"Som (medido na referência): {trilha}um efeito por evento de interface, uns {max(fora, 1):.0f} por segundo: "
                       "whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho."]
    linhas += ['', 'Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.']
    return '\n'.join(linhas), pecas


def palavra_isca(legenda_post):
    """A palavra do "comenta X" da legenda, se houver."""
    m = re.search(r'(?i)comment(?:\s+the\s+word)?\s*[:"“”\'*]*\s*([A-Za-z0-9]+)', legenda_post)
    return m.group(1).upper() if m else ''


def montar(classes, pasta_audio, repo):
    repo = pathlib.Path(repo)
    videos = pathlib.Path(classes).parent / 'videos'
    arq_q = pathlib.Path(classes).parent / 'qualidade.json'
    qual = json.loads(arq_q.read_text()) if arq_q.exists() else {}
    fontes = ler_fontes()
    for d in ('fichas', 'prompts'):
        (repo / d).mkdir(parents=True, exist_ok=True)
    todas = []
    for linha in pathlib.Path(classes).read_text().splitlines():
        c = json.loads(linha)
        if 'erro' in c or not (videos / f"{c['id']}.mp4").exists():
            continue
        info = videos / f"{c['id']}.info.json"
        meta = json.loads(info.read_text()) if info.exists() else {}
        # o info.json de carrossel não traz o tamanho: lê do próprio arquivo (o 9:16 errado do teste de 21/10 veio daí)
        q = qual.get(c['id']) or sonda(videos / f"{c['id']}.mp4")
        meta['width'], meta['height'] = q['largura'], q['altura']
        meta['url'] = url_de(c['id']) if not c['id'].isdigit() else (meta.get('webpage_url') or url_de(c['id']))
        a = pathlib.Path(pasta_audio) / f"{c['id']}.json"
        audio = json.loads(a.read_text()) if a.exists() else None
        prompt, pecas = como_fazer(c, meta, audio)
        galeria = apple(c) or c['id'] in PROVADAS
        e = {'id': c['id'], 'url': meta['url'], 'autor': meta.get('channel') or meta.get('uploader_id') or meta.get('uploader') or '',
             'data': time.strftime('%Y-%m-%d', time.gmtime(meta['timestamp'])) if meta.get('timestamp') else '',
             'curtidas': meta.get('like_count'), 'comentarios': meta.get('comment_count'),
             'legenda_post': (meta.get('description') or '')[:300], 'duracao_s': c['duracao'],
             'tipo': c['tipo'], 'fundo': c['fundo'], 'densidade': c['densidade'], 'acabamento': c['acabamento'],
             'texto': c['texto'], 'ferramenta': c['ferramenta'], 'unidade': c.get('unidade', 'filme'),
             'entrega': c.get('entrega2') or (c['entrega'] if c['isca'] >= 0.5 else 'nada'),
             'palavra': palavra_isca(meta.get('description') or ''),
             'acabamento_pro': c['acabamento_pro'], 'pecas': pecas, 'nota': nota(c, meta),
             'som': {k: audio.get(k) for k in ('class', 'tempo_bpm', 'onsets_per_s')} if audio else None,
             'qualidade': {k: q.get(k) for k in ('largura', 'altura', 'fps', 'kbps', 'codec')},
             'origem': fontes.get(c['id'], []), 'estilo_apple': galeria, 'nivel': nivel(c, q) if galeria else None,
             'prova': dict(zip(('clone', 'distancia', 'correlacao', 'lado_a_lado'), PROVADAS[c['id']])) if c['id'] in PROVADAS else None}
        (repo / 'fichas' / f"{c['id']}.json").write_text(json.dumps(e, ensure_ascii=False, indent=1))
        (repo / 'prompts' / f"{c['id']}.md").write_text(f"# {e['autor']} · {e['id']}\n\nReferência: {e['url']}\n\n```text\n{prompt}\n```\n")
        e['prompt'] = prompt
        todas.append(e)
    ordem = list(NIVEL)
    entradas = sorted((e for e in todas if e['estilo_apple']), key=lambda e: (ordem.index(e['nivel']), -e['nota']))
    json.dump(entradas, open(repo / 'data/biblioteca.json', 'w'), ensure_ascii=False)
    glos = glossario(entradas)
    escrever_readme(repo, entradas, glos, len(todas))
    site(repo, videos, entradas, glos, len(todas))
    return entradas


CURTO = {'dynamic_island': 'Dynamic Island', 'notificacao': 'Notificação', 'imessage': 'iMessage', 'cursor': 'Cursor',
         'iphone': 'iPhone', 'janela': 'Janela', 'icone_app': 'Ícone de app', 'pessoa_no_cartao': 'Pessoa no cartão',
         'legenda_fala': 'Legenda da fala', 'numero_grande': 'Número girando', 'grafico': 'Gráfico', 'botao_pilula': 'Botão pílula',
         'busca': 'Busca', 'teclado': 'Teclado', 'mapa': 'Mapa', 'emoji_3d': 'Emoji 3D', 'pilha_cartoes': 'Pilha de cartões',
         'print_site': 'Print do produto', 'vidro': 'Vidro'}


def glossario(entradas):
    g = [{'id': k, 'pt_curto': CURTO[k], 'pt': pt, 'en': en, 'hf': nomes, 'n': sum(k in e['pecas'] for e in entradas)}
         for k, (nomes, pt, en) in CATALOGO.items()]
    g.append({'id': 'texto_blur', 'pt_curto': 'Texto com desfoque', 'pt': TEXTO['palavra_com_blur'][1], 'en': TEXTO['palavra_com_blur'][2],
              'hf': TEXTO['palavra_com_blur'][0], 'n': sum(e['texto'] == 'palavra_com_blur' for e in entradas)})
    return sorted(g, key=lambda x: -x['n'])


def fonte_txt(e):
    q = e['qualidade']
    return f"{min(q['largura'], q['altura'])}p" + (f" {q['fps']:.0f} fps" if q.get('fps') else '')


def escrever_readme(repo, entradas, glos, total):
    tipos = {'ui_animacao': 'Animação de interface', 'pessoa_estilo_apple': 'Pessoa falando no estilo Apple',
             'pessoa_legenda_comum': 'Pessoa com legenda comum', 'bastidor_editor': 'Bastidor no editor',
             'tutorial_tela': 'Tutorial de tela', 'outro': 'Outro'}
    por = {n: [e for e in entradas if e['nivel'] == n] for n in NIVEL}
    linha = lambda e: (f"| {e['nota']} | [@{e['autor']}]({e['url']}) | {', '.join(CURTO.get(p, p) for p in e['pecas'][:6])} | "
                       f"{fonte_txt(e)} | {e['duracao_s']:.0f} s | {e['curtidas'] or ''} | [ver](prompts/{e['id']}.md) |")
    cab = ['| nota | autor | peças | fonte | duração | ♥ | prompt |', '|---|---|---|---|---|---|---|']
    L = ['# Biblioteca do estilo Apple', '',
         f"{len(entradas)} referências do \"estilo Apple\" (animação de interface e edição com interface), escolhidas entre "
         f"{total} vídeos do Instagram e do X classificados pelo Jev (TypeSafe). Cada ficha diz quais peças o vídeo usa, como soa "
         "(medido com o video-sharingan) e traz um prompt para refazer no Claude com o HyperFrames.", '',
         f"- **Provada** ({len(por['provada'])}): já clonamos e medimos. Tem a nota de fidelidade (distância e correlação de "
         "movimento) e o lado a lado.",
         f"- **Clonável** ({len(por['clonavel'])}): estilo Apple, fonte em 1080 no lado menor, até 15 s, filme ou peça. "
         "É por onde começar um clone novo.",
         f"- **Referência** ({len(por['referencia'])}): o resto que passou no filtro de estilo Apple.",
         '- `fichas/<id>.json`: a ficha (fonte da verdade, inclusive dos vídeos que ficaram fora da galeria). '
         '`prompts/<id>.md`: o prompt gerado.',
         '- `GLOSSARIO.md`: o nome de cada peça, o termo para usar com o Claude e o item do catálogo do HyperFrames.',
         '- O vídeo é do autor: aqui só o link. Pedidos de remoção por issue.', '',
         f"## Provadas ({len(por['provada'])})", '', '| clone | autor | distância | correlação | lado a lado | prompt |',
         '|---|---|---|---|---|---|']
    virg = lambda x: 'por máscara (NOTAS.md do molde)' if x is None else f'{x:.3f}'.replace('.', ',')
    L += [f"| {e['prova']['clone']} | [@{e['autor']}]({e['url']}) | {virg(e['prova']['distancia'])} | {virg(e['prova']['correlacao'])} | "
          f"só local | [ver](prompts/{e['id']}.md) |" for e in por['provada']]
    L += ['', f"## Clonáveis ({len(por['clonavel'])})", ''] + cab + [linha(e) for e in por['clonavel']] + ['']
    L += [f"## Referências ({len(por['referencia'])})", '']
    for t, nome in tipos.items():
        xs = [e for e in por['referencia'] if e['tipo'] == t]
        if xs:
            L += [f'### {nome} ({len(xs)})', ''] + cab + [linha(e) for e in xs] + ['']
    (repo / 'README.md').write_text('\n'.join(L))
    G = ['# Glossário de peças', '', 'Nome em português, termo para o Claude, quantos vídeos da biblioteca usam e o item do '
         'catálogo do HyperFrames (`npx hyperframes add <nome>`).', '', '| peça | o que é | termo para o Claude | vídeos | HyperFrames |',
         '|---|---|---|---|---|']
    G += [f"| {g['pt_curto']} | {g['pt']} | {g['en']} | {g['n']} | {', '.join(f'`{n}`' for n in g['hf'])} |" for g in glos]
    (repo / 'GLOSSARIO.md').write_text('\n'.join(G) + '\n')


def miniatura(video):
    """4 quadros lado a lado (15/40/65/90%), 360x160, como data URI."""
    import base64
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video)]))
    ent = [x for p in (0.15, 0.40, 0.65, 0.90) for x in ('-ss', f'{dur * p:.2f}', '-i', str(video))]
    f = ';'.join(f'[{i}:v]scale=90:160:force_original_aspect_ratio=decrease,pad=90:160:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]' for i in range(4))
    jpg = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', *ent, '-filter_complex', f + ';[v0][v1][v2][v3]hstack=4',
                          '-frames:v', '1', '-q:v', '6', '-f', 'mjpeg', '-'], capture_output=True).stdout
    return 'data:image/jpeg;base64,' + base64.b64encode(jpg).decode()


def site(repo, videos, entradas, glos, total):
    # os quadros do vídeo são do autor: só entram com ASUI_MINIATURAS=1, para uso na tua máquina; no repositório, só o link
    if os.environ.get('ASUI_MINIATURAS') == '1':
        with ThreadPoolExecutor(8) as ex:
            thumbs = list(ex.map(lambda e: miniatura(videos / f"{e['id']}.mp4"), entradas))
    else:
        thumbs = [''] * len(entradas)
    campos = ('id', 'url', 'autor', 'data', 'curtidas', 'duracao_s', 'tipo', 'unidade', 'entrega', 'palavra', 'pecas', 'nota', 'som',
              'prompt', 'nivel')
    dados = {'gerado': time.strftime('%d/%m/%Y'), 'total': total, 'glossario': glos,
             'entradas': [{**{k: e[k] for k in campos}, 'fonte': fonte_txt(e), 'x': e['id'].isdigit(), 'thumb': t,
                           'prova': e['prova'] and {**e['prova'], 'lado_a_lado': ''}}
                          for e, t in zip(entradas, thumbs)],
             'rodape': 'Os vídeos são dos autores: aqui só o link, com crédito, e o botão leva ao original. Nota de 0 a 100 = '
                       'acabamento (Jev) + cara de Apple + curtidas. Fichas automáticas: conferir antes de usar.'}
    (repo / 'site').mkdir(exist_ok=True)
    (repo / 'site' / 'dados.js').write_text('window.BIBLIOTECA = ' + json.dumps(dados, ensure_ascii=False) + ';\n')


# ---------- o Jev alimentando sempre ----------

def atualizar(profundo=False):
    """Descobre, baixa, classifica, rebaixa na melhor qualidade o que entra na galeria, mede o som, monta e grava o resumo.
    Seguro rodar de novo: id já conhecido não volta para a fila, vídeo baixado não é baixado de novo, id classificado não
    é reclassificado e cada vídeo é rebaixado uma vez só."""
    t0, quando = time.time(), time.strftime('%Y-%m-%d %H:%M')
    classes = DADOS / 'classes.jsonl'
    antes = {json.loads(l)['id'] for l in classes.read_text().splitlines()} if classes.exists() else set()
    achados, por_origem, bloqueio = descobrir(profundo)
    do_repo = repositorios()
    baixados = baixar(POR_RODADA)
    classificar(DADOS / 'videos', classes)
    linhas = [json.loads(l) for l in classes.read_text().splitlines()]
    novos = [c for c in linhas if c['id'] not in antes]
    entram = ordem_rebaixe(novos)
    qual = qualidade(entram + ordem_rebaixe(linhas))  # os novos primeiro; o que sobrou de rodadas anteriores vem depois
    medir_som(ordem_rebaixe(linhas))
    entradas = montar(classes, DADOS / 'audio', REPO)
    custo = sum(c.get('tokens', 0) for c in novos) * PRECO_MTOK / 1e6
    galeria = {e['id']: e for e in entradas}
    plural = {'provada': 'provadas', 'clonavel': 'clonáveis', 'referencia': 'de referência'}
    contagem = ', '.join(f"{sum(e['nivel'] == n for e in entradas)} {plural[n]}" for n in NIVEL)
    R = [f'## {quando}', '',
         f"- Descobertos: {len(achados)} no Instagram ({', '.join(f'{o}: {n}' for o, n in por_origem.items() if n) or 'nada novo'}) "
         f"e {len(do_repo)} do repositório awesome-opus.",
         f"- Baixados: {baixados['instagram']} do Instagram e {baixados['x']} do X; {baixados['falhas']} falharam ou foram pulados.",
         f"- Classificados agora: {len(novos)} (custo do Jev: US$ {f'{custo:.4f}'.replace('.', ',')}). Total classificado: {len(linhas)}.",
         f"- Entraram na galeria: {sum(i in galeria for i in entram)}. Rebaixados em qualidade melhor: {qual['rebaixados']}.",
         f"- Galeria: {len(entradas)} referências ({contagem}).",
         f"- Tempo: {(time.time() - t0) / 60:.0f} min."]
    paradas = [p for p in (bloqueio, baixados['parada'], qual['parada']) if p]
    if paradas:
        R.append(f"- Parou antes do fim: {'; '.join(paradas)}.")
    R += [''] + [f"  - {NIVEL[galeria[i]['nivel']]}: [@{galeria[i]['autor']}]({galeria[i]['url']}), nota {galeria[i]['nota']}"
                 for i in entram if i in galeria] + ['']
    hist = AQUI / 'biblioteca' / 'historico.md'
    hist.write_text((hist.read_text() if hist.exists() else '# O que entrou na biblioteca a cada atualização\n\n') + '\n'.join(R) + '\n')
    print('\n'.join(R))


if __name__ == '__main__':
    assert nota({'fundo': 'claro_neutro', 'densidade': 'um_heroi', 'acabamento': 'sombra_suave', 'texto': 'frase_limpa',
                 'acabamento_pro': 3, 'apple_limpo': 1, 'paleta': 'neutra_clara'}, {'like_count': 999999}) == 100
    _c = {'id': 'x', 'fundo': 'claro_neutro', 'paleta': 'neutra_clara', 'acabamento': 'sombra_suave', 'texto': 'frase_limpa',
          'tipo': 'ui_animacao', 'densidade': 'dois_tres', 'apple_limpo': 0.42, 'duracao': 10.9, 'unidade': 'peca'}
    assert apple(_c) and not apple(_c | {'fundo': 'escuro_com_glow'}) and not apple(_c | {'densidade': 'poluido'})
    assert nivel(_c, {'largura': 1080, 'altura': 1920}) == 'clonavel' and nivel(_c, {'largura': 720, 'altura': 1280}) == 'referencia'
    assert nivel(_c | {'unidade': 'processo'}, {'largura': 1080, 'altura': 1920}) == 'referencia'
    assert tem_melhor({'largura': 720, 'altura': 1280, 'kbps': 500, 'melhor': {'lado': 1080, 'kbps': 900}})
    assert not tem_melhor({'largura': 1080, 'altura': 1920, 'kbps': 900, 'melhor': {'lado': 1080, 'kbps': 950}})
    cmd, arg = sys.argv[1], sys.argv[2:]
    if cmd == 'classificar':
        classificar(arg[0], arg[1])
    elif cmd in ('apple', 'unidade'):
        passada(arg[0], arg[1], APPLE if cmd == 'apple' else UNIDADE)
    elif cmd == 'montar':
        print(len(montar(arg[0], arg[1], arg[2])), 'entradas')
    elif cmd == 'descobrir':  # descobrir [--fundo] [--desde <perfil ou busca>]
        n, por, b = descobrir('--fundo' in arg, arg[arg.index('--desde') + 1] if '--desde' in arg else '')
        print(len(n), 'novos', por, b)
    elif cmd == 'awesome':
        print(len(awesome(arg[0])), 'novos')
    elif cmd == 'baixar':
        print(baixar(next((int(a) for a in arg if a.isdigit()), None), next((a for a in arg if a in ('instagram', 'x')), '')))
    elif cmd == 'qualidade':  # sem N: só mede; com N: rebaixa até N fichas da galeria, as que viram clonáveis primeiro
        linhas = [json.loads(l) for l in (DADOS / 'classes.jsonl').read_text().splitlines()]
        print(qualidade(ordem_rebaixe(linhas)[:int(arg[0])] if arg else ()))
    elif cmd == 'atualizar':
        atualizar('--fundo' in arg)
