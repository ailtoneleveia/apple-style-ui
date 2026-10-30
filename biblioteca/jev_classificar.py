"""Classifica reels no "estilo Apple" com o Jev (TypeSafe), olhando 4 quadros por vídeo.

Uso: python3 jev_classificar.py video1.mp4 [video2.mp4 ...] > saida.jsonl
Cada vídeo vira 4 quadros (15/40/65/90% da duração) e uma chamada só, com as perguntas do PLANO.md §4.
Chave: TYPESAFE_API_KEY no .env da raiz do projeto (nunca impressa). Preço: US$ 0,042 por milhão de tokens
de entrada (saída é grátis); imagem conta como token de entrada.
Perguntas em inglês porque o Jev acerta mais em inglês; rótulos em português, como no plano.
"""
import base64
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

RAIZ = pathlib.Path.cwd()  # o .env com a TYPESAFE_API_KEY fica na pasta de trabalho, nunca no repositório
MODELO = 'jev-1.14.0'
PRECO_MTOK = 0.042
PONTOS = (0.15, 0.40, 0.65, 0.90)
LADO = 1024  # lado maior do quadro; o Jev aceita de 280 a 1568
PAR = 0.2  # segundo quadro logo depois de cada ponto: movimento só aparece comparando quadros próximos

QUADROS = ('the frames of one short vertical video: four moments (`f15`, `f40`, `f65`, `f90`, at 15, 40, 65 and 90%'
           ' of its length), each followed 0.2 s later by `f15b`, `f40b`, `f65b`, `f90b`')
ESCOLHA = {
    'fundo': ('What is the background in ' + QUADROS + '?', {
        'claro_neutro': 'Plain light background: white, off-white or light gray, mostly empty.',
        'pastel_ou_gradiente_suave': 'Soft pastel color or a gentle gradient.',
        'wallpaper_ios_macos': 'An iOS or macOS style wallpaper behind the interface.',
        'escuro_com_glow': 'Dark or black background, often with neon or glowing light.',
        'foto_video_real': 'A real photo or filmed scene (people, places, objects).'}),
    'sujeito': ('What is the main subject in ' + QUADROS + '?', {
        'ui_isolada': 'A single interface element floating alone: a card, button, widget, notification or toggle.',
        'mockup_aparelho': 'A device or app window: iPhone, Mac, browser or Finder window.',
        'tipografia': 'Mostly words and type, the text itself is the subject.',
        'objeto_3d': 'A 3D object or product render.',
        'pessoa_camera': 'A person, usually talking to the camera.'}),
    'densidade': ('How crowded is the composition in ' + QUADROS + '?', {
        'um_heroi_muito_espaco': 'One hero element with lots of empty space around it.',
        'dois_tres_elementos': 'Two or three elements, still clean.',
        'poluido': 'Busy and cluttered, many elements competing.'}),
    'acabamento': ('How are the interface elements rendered in ' + QUADROS + '?', {
        'sombra_suave_1_2_cores_sistema': 'Soft, diffuse shadows and one or two Apple-like system colors (blue, gray).',
        'flat_sem_sombra': 'Flat, no shadows.',
        'neon_glow_saturado': 'Saturated neon colors and glow.',
        'contorno_ou_sombra_dura': 'Hard outlines or hard drop shadows.'}),
    'tipografia': ('What is the typography like in ' + QUADROS + '?', {
        'sans_limpa_poucas_palavras': 'Clean sans-serif like San Francisco, few words, one color.',
        'sans_com_palavra_destacada': 'Clean sans-serif with one word highlighted in another color (often blue).',
        'serifada_ou_display': 'Serif or decorative display font.',
        'legenda_estilo_capcut': 'CapCut-style captions: boxes, thick outlines, emoji, many colors.',
        'sem_texto': 'No text on screen.'}),
    'legenda': ('How does on-screen text appear in ' + QUADROS + '?', {
        'palavra_a_palavra_com_blur': 'Words appear one by one, some still blurred while entering.',
        'frase_estatica': 'A whole static line of text.',
        'karaoke_colorido': 'Karaoke captions where the spoken word changes color.',
        'icone_dentro_da_frase': 'An icon or small image sits inside the sentence, between words.',
        'nao_aplica': 'There is no on-screen text.'}),
    'morph': ('Comparing each frame with the one 0.2 s after it, in ' + QUADROS + ', how does one element change into the next?', {
        'mesmo_elemento_muda_de_forma': 'The same element smoothly changes shape or size into something else (a morph).',
        'troca_por_corte': 'Elements are replaced by cuts between different scenes.',
        'indefinido': 'Not possible to tell.'}),
    'ilha': ('Is there an iPhone Dynamic Island (a black pill at the top) in ' + QUADROS + '?', {
        'pilula_preta_muda_de_tamanho_ou_conteudo': 'Yes, the black pill grows, shrinks or shows content.',
        'pilula_estatica': 'Yes, but it stays the same.',
        'nao': 'No Dynamic Island.'}),
    'camera': ('How does the virtual camera behave across ' + QUADROS + '?', {
        'zoom_no_mesmo_elemento': 'It zooms in or out on the same element.',
        'inclinacao_3d': 'The interface tilts in 3D perspective.',
        'troca_de_cena': 'It jumps to a different scene.',
        'parada_so_a_ui_anima': 'The camera stays still and only the interface animates.'}),
}
DESFOQUE = {  # várias podem ser verdade ao mesmo tempo, então uma pergunta sim/não para cada
    'blur_rastro': 'Is there motion blur, an element leaving a blurred streak as it moves, in ' + QUADROS + '?',
    'blur_quadro': 'Is a whole frame blurred, as in a blur transition, in ' + QUADROS + '?',
    'blur_texto': 'Is text entering blurred and then becoming sharp in ' + QUADROS + '?',
    'blur_vidro': 'Is there frosted or liquid glass (blurred translucent panels) in ' + QUADROS + '?',
}


def chave():
    for linha in (RAIZ / '.env').read_text().splitlines():
        if linha.startswith('TYPESAFE_API_KEY='):
            return linha.split('=', 1)[1].strip()
    sys.exit('TYPESAFE_API_KEY não está no .env da raiz')


def quadros(video):
    dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                         '-of', 'csv=p=0', str(video)]))
    saida = []
    for t in [x for p in PONTOS for x in (dur * p, min(dur * p + PAR, dur - 0.05))]:
        jpg = subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-ss', f'{t:.2f}', '-i', str(video),
                              '-frames:v', '1', '-vf', f'scale={LADO}:{LADO}:force_original_aspect_ratio=decrease',
                              '-q:v', '4', '-f', 'mjpeg', '-'], capture_output=True, check=True).stdout
        saida.append(base64.b64encode(jpg).decode())
    return dur, saida


def veredito(r):
    """Regra do PLANO.md: apple_bom sem pergunta própria, a partir das respostas."""
    claro = r['fundo'] in ('claro_neutro', 'pastel_ou_gradiente_suave', 'wallpaper_ios_macos')
    limpo = r['densidade'] != 'poluido' and r['acabamento'] == 'sombra_suave_1_2_cores_sistema'
    tecnica = (r['morph'] == 'mesmo_elemento_muda_de_forma' or r['ilha'] == 'pilula_preta_muda_de_tamanho_ou_conteudo'
               or any(r[k] >= 0.5 for k in DESFOQUE))
    return claro and limpo and r['tipografia'] != 'legenda_estilo_capcut' and tecnica


def classificar(video, segredo):
    dur, imgs = quadros(video)
    refs = [f'f{int(p * 100)}{b}' for p in PONTOS for b in ('', 'b')]
    perguntas = {k: {'type': 'choice', 'instructions': q, 'criteria': c} for k, (q, c) in ESCOLHA.items()}
    perguntas |= {k: {'type': 'noul', 'instructions': q} for k, q in DESFOQUE.items()}
    corpo = {'model': MODELO, 'state': {r: f'img-{r}' for r in refs},
             'assets': {f'img-{r}': {'type': 'image', 'format': 'jpg', 'data_base64': b} for r, b in zip(refs, imgs)},
             'questions': perguntas}
    req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', data=json.dumps(corpo).encode(), headers={
        'Authorization': f'Bearer {segredo}', 'Content-Type': 'application/json',
        'TypeSafe-Danger-Zone-Images': 'true'})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            dados = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {'video': str(video), 'erro': f'{e.code}: {e.read()[:400].decode(errors="replace")}'}
    a = dados['answers']
    r = {k: a[k]['choice'] for k in ESCOLHA} | {k: a[k]['noul'] for k in DESFOQUE}
    tokens = dados['usage']['input_tokens']
    return {'video': str(video), 'duracao_s': round(dur, 1), 'apple_bom': veredito(r), 'respostas': r,
            'confianca': {k: a[k]['confidence'] for k in ESCOLHA}, 'tokens': tokens,
            'custo_usd': round(tokens * PRECO_MTOK / 1e6, 6), 'segundos': round(time.time() - t0, 1),
            'modelo': dados['model']}


if __name__ == '__main__':
    base = {'fundo': 'claro_neutro', 'densidade': 'um_heroi_muito_espaco', 'acabamento': 'sombra_suave_1_2_cores_sistema',
            'tipografia': 'sans_com_palavra_destacada', 'morph': 'mesmo_elemento_muda_de_forma', 'ilha': 'nao'} | dict.fromkeys(DESFOQUE, 0.1)
    assert veredito(base) and not veredito(base | {'fundo': 'escuro_com_glow'})
    assert not veredito(base | {'morph': 'troca_por_corte'}) and veredito(base | {'morph': 'indefinido', 'blur_vidro': 0.8})
    segredo = chave()
    for v in sys.argv[1:]:
        print(json.dumps(classificar(pathlib.Path(v), segredo), ensure_ascii=False), flush=True)
