# Molde "fala-destaque": a pessoa do usuário com as palavras em destaque do reel DaIOD8QSEAz

Projeto HyperFrames (`index.html`) com campos no `data-composition-variables`, lidos com
`window.__hyperframes.getVariables()` por cima dos padrões, como nos outros moldes (Joi, Satellite). O formato
vem do 6º clone (FICHA.md e LICOES.md, fora do repositório); aqui não entra gravação, só a estrutura, os campos e os padrões.

## Os campos

| campo | tipo | o que é | padrão |
|---|---|---|---|
| `video_pessoa` | string | o vídeo da pessoa falando (9:16); `data-var-src` no `<video>`. O `montar.py` copia para `assets/pessoa.mp4`, corta para 1080x1920 a 30 qps e acerta a duração | `assets/pessoa.mp4` |
| `frases` | string (JSON) | um grupo por frase; cada palavra `[texto, início em s, destaque 0/1]`. Sai da transcrição | as 5 frases do clone, com os tempos medidos |
| `cor_destaque` | color | a cor da palavra em destaque | `#fefaf7` (a medida) |
| `fonte_destaque` | enum | `instrument` (Instrument Serif Itálico com o espaço, o negrito e a proporção medidos), `playfair`, `dmserif` | `instrument` |
| `cor_apoio` | color | a cor das palavras pequenas | `#fffcf8` |
| `altura` | number | a linha de base da palavra em destaque (px de cima); suba se o texto cobrir a boca | 1108 (a do clone) |
| `sombra` | enum | `nenhuma` (como a rodada final do clone) ou `medida` (60 %, σ 4 px, a do original: melhor em fundo claro) | `nenhuma` |
| `cenas` | string (JSON) | `{"<frase, a partir de 0>": "escura"}`: a frase vira a cena escura do neon (caixa alta em SF Pro 760 sobre o vídeo escurecido a 60 %, a última palavra antes do destaque maior e ao lado dele, na serifa; ver abaixo) | `{"2": "escura"}` (a frase do clone); frases transcritas começam com `{}` |

As regras de diagramação e animação ficam no `MEDIDAS` do `index.html`, cada número com a origem no clone: três linhas
(pequenas em cima, destaque no meio, o resto embaixo à direita), entrada a ~85 % vindo 12 px da direita e escorregando
até parar em 20 quadros, troca de frase no corte, saída borrada do último grupo (σ 1,5 → 9 em 4 quadros).

## A cena escura (campo `cenas`, 22/10)

Medida nas caixas assentadas do clone (f106 do `camada.json`): linha de cima em caixa alta com 46 px de maiúscula
("THAT'S NOT HOW"), linha de baixo com a última palavra antes do destaque em caixa alta maior (62 px, "SELF-DOUBT") e o
destaque na serifa (tinta de "works" com 114 px), na mesma linha de base (y 714), 14 px de vão; as duas linhas
centradas em x 540, 28 px entre elas. As palavras nascem secas (sem clarear nem deslizar); a primeira nasce borrada no
corte (σ 8, 5, 2,5); a linha de cima desce 44 px entre a 2ª palavra e o destaque. Palavras depois do destaque vão
para uma terceira linha em caixa alta pequena. O clone corta para outra filmagem (o neon); o molde não tem outra, então
escurece o vídeo da pessoa a 60 % (`MEDIDAS.escura.escurece`).

Prova com os padrões sobre a placa do clone (`compara_mascara.py` na pegada, contra o original):

| render | distância | fina | correlação | janela f51-f100 | blocos f60-79 / f80-99 / f100-119 |
|---|---|---|---|---|---|
| antes (cena escura no padrão comum) | 0,191 | 0,231 | 0,04 | -0,03 (atraso -6) | 0,191 / 0,308 / 0,287 |
| com a cena escura  | 0,185 | 0,236 | 0,20 | 0,29 (atraso -2) | 0,283 / 0,286 / 0,292 |
| com a cena escura sem escurecer (só para a prova) | **0,172** | **0,223** | 0,16 | **0,35** (atraso -2) | **0,178** / **0,258** / 0,279 |
| sem camada (não desenhar nada) | 0,185 | 0,208 | | | |

Sem o escurecimento, que na placa escurece de novo uma filmagem que já é escura, o padrão passa a ficar abaixo do "sem
camada" na grade pela primeira vez, e a janela da cena escura sai de -0,03 para 0,35 de correlação. Com o escurecimento
(o que vale para a pessoa), o bloco f60-79 piora (o fundo escurecido conta na máscara) e os outros dois melhoram. No
olho, as três linhas da cena ficam no lugar e no tamanho do clone . Continua longe no pixel:
a serifa não é a do original e o grupo troca ~2 quadros antes (a antecipação de 0,08 s).

## O tempo das palavras vem da transcrição

```sh
python3 clonar/scripts/transcrever.py <fala.mp4|.wav> --idioma pt --saida palavras.json
```

- Provedor: Groq (whisper-large-v3, palavra a palavra) com `GROQ_API_KEY` no ambiente ou no `.env`; sem chave, o
  `hyperframes transcribe` local (small.en para `--idioma en`, large-v3 para o resto, ~3 GB na primeira vez). O
  `montar.py` e o `caso.py aplicar` chamam ele sozinhos.
- No trecho clonado (fala real), o início que o whisper dá cai em média 0,067 s depois de a palavra aparecer na tela,
  com erro médio de 0,12 s: o molde antecipa 0,08 s.
- Na voz sintética, o whisper errou frases inteiras em até 0,58 s. O `montar.py` estica cada frase para dentro do
  trecho de fala que começa perto dela (silencedetect a -35 dB), quando a duração bate; na fala corrida não mexe.

## Como usar

Pelo kit (o caminho do produto): `python3 clonar/caso.py aplicar moldes/fala-destaque --video minha-fala.mp4
--saida <projeto>/saidas/minha-fala.mp4 [--idioma pt]`. Ele transcreve, escolhe o destaque, grava o
`<projeto>/destaques.txt` (a pessoa muda os colchetes e roda de novo) e chama o montar.py abaixo com `--versao`.

Direto:

```sh
python3 moldes/fala-destaque/montar.py --pessoa minha-fala.mp4 --saida saidas/minha-fala.mp4 \
  [--destaques "talento,hábito"] [--cor-destaque "#f2b544"] [--fonte playfair] [--sombra medida] [--altura 1000] \
  [--idioma pt] [--voz fala.wav] [--versao versao.json] [--previa]
```

1. transcreve a fala (do vídeo, ou de `--voz`), monta as frases e escolhe o destaque (os de `--destaques`, ou a regra do
   kit, `clonar/scripts/destaque.py`: a mais longa fora das palavras vazias de português e inglês);
2. grava a versão resolvida em `<saida>.versao.json` (edite e rode de novo com `--versao` para trocar palavra, tempo ou
   destaque sem transcrever de novo);
3. monta uma cópia do molde no bastidor (`<projeto>/.apple-style-ui/` quando a saída está em `<projeto>/saidas/`;
   senão `<pasta da saída>/.apple-style-ui/`), com os campos como padrões;
4. renderiza com o motion blur do kit (`clonar/scripts/round_mb.sh`: 240 qps, tmix, um worker, H.264
   `-refs 4 -level:v 5.1`) e põe o áudio da fala. Para se houver menos de 5 GB livres.

`npx hyperframes check` no molde puro acusa `missing_local_asset` (`assets/pessoa.mp4`): é esperado, o vídeo entra pelo
`montar.py`. Na cópia montada o check passa.

## O que já foi provado

- `exemplo/`: um homem em pé falando para a câmera (Pexels 8048492) com uma narração sintética (o Pexels não publica
  áudio): 424 quadros, 5 frases e 6 destaques tirados da transcrição.
- Os padrões sobre a placa do clone: parecem o clone no olho, mas não no pixel (as provas ficaram fora do repositório).

## O que não faz

- A cena escura não corta para outra filmagem: escurece a da pessoa. Não há regra que escolha sozinha qual frase vira
  cena escura; a pessoa marca no `destaques.txt` (`escura:`) ou no campo `cenas`.
- Não corta para outras filmagens nem borra o vídeo da pessoa na transição (só o texto).
- A diagramação não desvia do rosto: a `altura` é fixa por vídeo.
