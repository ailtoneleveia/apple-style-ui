"""Tria repositórios do GitHub com o Jev: o que é, para que plataforma e se serve para o estilo Apple.

Uso: python3 jev_repos.py repos.json pasta_readmes saida.jsonl
repos.json vem do `gh search repos --json fullName,description,stargazersCount,license,language,...`;
pasta_readmes tem <dono>_<repo>.md com o começo do README. Uma chamada por repositório, 8 em paralelo.
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from jev_classificar import MODELO, PRECO_MTOK, chave

PERGUNTAS = {
    'tipo': {'type': 'choice', 'instructions': 'What is the repository in `repo` mainly?', 'criteria': {
        'component_library': 'Reusable UI or animation components to drop into a web page or video.',
        'video_template': 'A ready video or composition project (Remotion, After Effects, Motion Canvas) to adapt.',
        'sound_assets': 'Sound effects or audio packs.',
        'design_assets': 'UI kits, device mockups, icons, wallpapers or fonts.',
        'tool_or_framework': 'An engine, framework, CLI or library to build animations or videos.',
        'agent_skill': 'Skills, prompts or instructions for AI coding agents such as Claude Code.',
        'curated_list': 'An awesome-list or collection of links.',
        'app_or_unrelated': 'An end-user app, a clone, a demo or something unrelated to making videos or UI motion.'}},
    'plataforma': {'type': 'choice', 'instructions': 'Which platform does `repo` target?', 'criteria': {
        'remotion': 'Remotion (React video).', 'hyperframes_or_html_gsap': 'HyperFrames, or HTML with GSAP.',
        'react_web': 'React web UI (Framer Motion, Motion, React Spring).', 'css_or_vanilla_js': 'Plain CSS or vanilla JavaScript.',
        'swift_native': 'Swift, SwiftUI or native iOS/macOS.', 'after_effects': 'After Effects or other desktop motion software.',
        'motion_canvas': 'Motion Canvas.', 'other': 'Something else or not specific.'}},
    'utilidade': {'type': 'score', 'instructions': 'How useful is `repo` to someone making short videos of clean Apple-style UI '
                  'motion (light backgrounds, iOS-like components, smooth spring motion, a sound for every element)?',
                  'criteria': ['Not useful', 'Loosely related', 'Useful as reference or inspiration', 'Directly reusable pieces for that']},
    'dynamic_island': {'type': 'noul', 'instructions': '`repo` includes an iPhone Dynamic Island component or animation.'},
    'liquid_glass': {'type': 'noul', 'instructions': '`repo` includes frosted or liquid glass (glassmorphism) effects.'},
    'spring_physics': {'type': 'noul', 'instructions': '`repo` provides spring physics or tuned easing presets for animation.'},
    'text_reveal': {'type': 'noul', 'instructions': '`repo` includes text animations such as blur-in, word-by-word or letter reveals.'},
    'ui_sfx': {'type': 'noul', 'instructions': '`repo` contains UI sound effects (clicks, pops, whooshes) or a sound library.'},
    'device_mockup': {'type': 'noul', 'instructions': '`repo` includes iPhone, Mac or browser window frames/mockups.'},
    'captions': {'type': 'noul', 'instructions': '`repo` makes animated captions or subtitles for videos.'},
    'cursor': {'type': 'noul', 'instructions': '`repo` includes an animated mouse cursor or click animation.'},
}


def perguntar(segredo, r, readme):
    estado = {'repo': {'name': r['fullName'], 'description': r.get('description') or '', 'stars': r['stargazersCount'],
                       'language': r.get('language') or '', 'license': (r.get('license') or {}).get('key', ''),
                       'readme_start': readme}}
    req = urllib.request.Request('https://api.typesafe.ai/v1/systemone', headers={
        'Authorization': f'Bearer {segredo}', 'Content-Type': 'application/json'},
        data=json.dumps({'model': MODELO, 'state': estado, 'questions': PERGUNTAS}).encode())
    for tentativa in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503) or tentativa == 4:
                return {'erro': f'{e.code}: {e.read()[:200].decode(errors="replace")}'}
            time.sleep(2 ** tentativa)


def main():
    repos = json.load(open(sys.argv[1]))
    pasta, saida = pathlib.Path(sys.argv[2]), open(sys.argv[3], 'w')
    segredo = chave()

    def um(r):
        p = pasta / (r['fullName'].replace('/', '_') + '.md')
        d = perguntar(segredo, r, p.read_text(errors='replace') if p.exists() else '')
        if 'erro' in d:
            return {'repo': r['fullName'], 'erro': d['erro']}
        a = d['answers']
        return {'repo': r['fullName'], 'url': r['url'], 'estrelas': r['stargazersCount'],
                'licenca': (r.get('license') or {}).get('key', ''), 'atualizado': r.get('updatedAt', '')[:10],
                'descricao': (r.get('description') or '')[:160], 'tipo': a['tipo']['choice'],
                'plataforma': a['plataforma']['choice'], 'utilidade': a['utilidade']['score'],
                **{k: round(a[k]['noul'], 2) for k in PERGUNTAS if a[k]['type'] == 'noul'},
                'tokens': d['usage']['input_tokens']}

    t0 = time.time()
    with ThreadPoolExecutor(8) as ex:
        for linha in ex.map(um, repos):
            saida.write(json.dumps(linha, ensure_ascii=False) + '\n')
    print(f'{len(repos)} repositórios em {time.time() - t0:.0f} s', file=sys.stderr)


if __name__ == '__main__':
    main()
