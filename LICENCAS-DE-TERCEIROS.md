# Licenças de terceiros

Tudo que veio de fora e está dentro deste repositório, com a licença de cada coisa. O que não tem licença livre ficou
de fora (lista no fim).

## Código

| o quê | onde | licença |
|---|---|---|
| launch-video-clone (Pat Simmons) | `clonar/scripts/`: burst, compare, sheet, inkspan, inkspan_light, track, camtrack, round, round_mb, sbs | MIT |
| video-sharingan (Nikolas Faria) | `clonar/scripts/`: cuts, audio, common | MIT |
| Phosphor Icons | ícones da lista do Satellite, desenhados no `moldes/satellite/molde/index.html` | MIT |

O texto completo das duas licenças MIT do kit de clonagem, com o copyright de cada autor, está em
`clonar/LICENCAS-DE-TERCEIROS.md`. Cada arquivo copiado ou derivado mantém no topo a linha de copyright original.

O HyperFrames não vem dentro: roda por `npx` (versões 0.8.184 e 0.8.185) e baixa o próprio Chrome no primeiro render.

## Fontes

| fonte | onde | licença |
|---|---|---|
| Inter (The Inter Project Authors) | `moldes/satellite/molde/assets/fonts/Inter.ttf` | SIL Open Font License 1.1 |
| Archivo (The Archivo Project Authors) | `moldes/satellite/molde/assets/fonts/Archivo.ttf` | SIL Open Font License 1.1 |
| Instrument Serif Italic | `moldes/fala-destaque/assets/fonts/` | SIL Open Font License 1.1 |
| Playfair Display Italic | `moldes/fala-destaque/assets/fonts/` | SIL Open Font License 1.1 |
| DM Serif Display Italic | `moldes/fala-destaque/assets/fonts/` | SIL Open Font License 1.1 |

A SF Pro **não** vem dentro. Os moldes pedem `assets/fonts/SFNS.ttf`, e o montador copia a do teu Mac
(`/System/Library/Fonts/SFNS.ttf`) para a cópia de render, só na tua máquina. Sem ela, ou com `ASUI_FONTE_LIVRE=1`,
entra a Inter no lugar. Os emojis também vêm do sistema (Apple Color Emoji): nenhum arquivo de emoji vai no repositório.

## Sons

`sons/`: 20 sons, todos CC0 1.0. Dez são gerados por `sons/fazer_pacote.py`; dez vêm do Kenney Interface Sounds 1.0
(www.kenney.nl, CC0 1.0, baixados pelo soundcn). Detalhes som por som em `sons/CREDITOS.md`.

## Imagens e áudio dos moldes

- `moldes/joi/molde/assets/sprites/` e `moldes/voiceos/molde/assets/img/`: peças livres geradas por
  `moldes/pecas_livres.py` (formas simples, semente fixa). CC0. Ficam no lugar dos recortes do original.
- `moldes/*/molde/assets/silencio.m4a`: silêncio gerado pelo ffmpeg, no lugar do áudio do original. CC0.
- `moldes/voiceos/versoes/ceu-liso.png`: cor lisa gerada aqui. CC0.

## Vídeo de exemplo

`moldes/fala-destaque/exemplo/pessoa-pexels-8048492.mp4`: "A man explaining something", de Antoni Shkraba, no Pexels
(https://www.pexels.com/video/a-man-explaining-something-8048492/). Licença do Pexels (https://www.pexels.com/license/),
conferida em 22/10/2026: uso livre, edição permitida, atribuição não obrigatória. Não pode mostrar a pessoa de forma
negativa, dar a entender que ela endossa um produto, revender sem alteração nem redistribuir em outro banco. Detalhes e
sha256 em `moldes/fala-destaque/exemplo/ORIGEM.md`.

## Os vídeos de `exemplos/`

Renderizados por este repositório, com Inter, sem música e com os sons CC0 acima. Cada um tem o seu `ORIGEM.md`.

## O que ficou de fora, de propósito

- SF Pro e emojis da Apple (licença Apple, só no teu Mac).
- O áudio dos vídeos originais e a música de teste interna.
- Recortes de vídeos de terceiros: placas, fotos recortadas, ícones e memoji do VoiceOS, objetos do Joi.
- Os vídeos baixados da biblioteca e as miniaturas deles. As fichas trazem só o link do original, com crédito.
- A voz sintética do exemplo da pessoa falando (feita com o `say` do macOS): tu gera a tua na hora (ver o ORIGEM.md).
- Chaves e `.env`.

## A licença do próprio Apple Style UI

Ainda não decidida (repositório público ou privado é decisão do Júnior).
