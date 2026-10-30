# Apple Style UI

Motion design estilo Apple dentro do Claude Code. Não é uma lista de prompts: cada molde veio de um vídeo real,
clonado e medido quadro a quadro (mola, motion blur, tempo de cada peça, peso da letra), e o que se aprendeu nesses
clones virou código e receita. Tu pede em português e o vídeo sai com o movimento medido, não com uma mola inventada.

## O que tu consegue fazer

| Tu quer | Tu manda | Sai | Tempo | Prova (teste cego*) |
|---|---|---|---|---|
| **Vídeo com a tua marca** num molde provado (Satellite, Joi, VoiceOS) | nome, cor, fonte, logo, textos | o vídeo com as molas, o blur e o ritmo do original | ~4 min | ok |
| **Tua gravação editada** igual a uma referência de pessoa falando (molde fala-destaque) | o teu vídeo falando | legenda com palavra em destaque, transcrita e escolhida sozinha | ~4 min, US$ 0,62 | ok |
| **Clonar qualquer vídeo** de interface | o link | o clone em HTML (nada recortado do original), o lado a lado e a nota por peça | ~2 h, US$ 12 a 17 | ok, com limites abaixo |
| **Achar uma referência** | nada | a biblioteca: 1.323 vídeos classificados, com o texto pronto para colar | na hora | |

\* Teste cego: sessão nova do Claude Code numa pasta vazia, só com o plugin e o texto que a pessoa copia da biblioteca,
sem ninguém para responder perguntas. É o jeito que a gente prova que tu vai conseguir o mesmo que nós.

## Primeiro vídeo

No Claude Code:

```
/plugin marketplace add ailtoneleveia/apple-style-ui
/plugin install apple-style-ui@apple-style-ui
/apple-style-ui:video começar
```

Ele mostra os 3 exemplos (`exemplos/`), pergunta teu nome e tua cor e faz o vídeo no molde do Satellite. Na primeira
vez ele baixa o HyperFrames e um Chrome (uns 300 MB). Depois, `/apple-style-ui:video` sempre pergunta qual dos
caminhos acima tu quer e termina com o próximo passo.

## O que vem dentro (o saber de motion)

- **`estilo/estilo.js` e `estilo/ESTILO.md`: o perfil de estilo.** As 3 molas medidas (suave, firme, elástica, com ζ
  e ω), o obturador de 1/120 s com subquadros de verdade, o ritmo (palavra a cada 40 ms, item a cada 180 ms), a caixa
  que se transforma em vez de cortar, o nascer desfocado e o peso da letra por função. Tudo em 8 regras, numa página.
- **`estilo/RECEITAS.md`: 24 receitas por sintoma.** "A lista entra junta", "o cursor está no lugar errado",
  "o texto entra nítido demais", "o memoji vira mancha". Cada uma diz o que medir, o número de referência e o código.
- **`moldes/`**: Satellite, Joi, VoiceOS e fala-destaque, cada um com as notas do que foi medido e versões travadas.
- **`clonar/`**: o kit de clonagem. Raio-x do vídeo, ficha por cena e o medidor por peça (trajetória, mola, quebra de
  velocidade, rastro de motion blur, nitidez, forma, texto). Cada rodada gera imagens das manchas onde o clone ainda
  difere, e o clone só fecha depois que alguém olha cada uma.
- **`sons/`**: som por elemento (clique, tecla, chegada), todos CC0, encaixados no movimento.
- **`aprendizado/`**: a catraca. Um vídeo novo não pode sair pior que o anterior em nota, tempo nem custo, e o que tu
  aprova vira o teu perfil.
- **`biblioteca/site/index.html`**: a galeria. Filtra por nível, tipo e peça, clica em **Copiar para o Claude** e cola.
  Provada vai direto para o molde; clonável vai para o ciclo de clonagem; o resto vira vídeo novo no estilo calibrado.

## O que ainda não faz

- **Vídeo do zero sem referência nenhuma**: hoje sai pelo estilo calibrado com um prompt da biblioteca, sem medidor
  próprio. Um montador de cenas está em construção.
- **Misturar peças de moldes diferentes** e **clone que vira molde sozinho**: hoje virar molde pede o agente (~1h30).
- **Clone perfeito em detalhe rápido**: no último teste cego, os pontos de uma pílula caíram juntos quando no
  original caem em cascata, em 4 quadros. O medidor não pega eventos tão curtos; a receita 6 cobre o caso.
- **Memoji e emoji da Apple** não podem ser distribuídos: o clone desenha os seus, e eles ficam diferentes.
- **Só Mac**, por enquanto (render e fontes do sistema).

## O que precisa ter

Mac, Claude Code, ffmpeg, Node e Python 3 com numpy e pillow (`brew install ffmpeg node numpy pillow`). Para clonar,
um ambiente Python a mais, que o caminho de clonagem cria com o teu ok. Para transcrever fala, uma `GROQ_API_KEY`
gratuita no `.env` da tua pasta (sem ela, a transcrição roda local, mais lenta, e a 1ª vez baixa ~3 GB).

## Licenças

Código MIT. SF Pro e emojis da Apple não vêm no repositório: o render usa os do teu Mac. Para publicar, usa
`fonte: inter` ou `archivo` e uma música tua. Tudo de terceiros está em `LICENCAS-DE-TERCEIROS.md`; pastas e
comandos, em `ESTRUTURA.md`.
