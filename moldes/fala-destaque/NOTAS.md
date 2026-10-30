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
| `altura` | number | a linha de base da palavra em destaque (px de cima) nas frases sem `alturas` (sem rosto). `--altura` no `montar.py` fixa esta para todas e desliga o rosto | 1108 (a do clone) |
| `alturas` | string (JSON) | uma linha de base por frase (px, ou `null`), também na cena escura; o `montar.py` tira do rosto (abaixo) | `[]` (vale `altura`, e 714 na cena escura) |
| `sombra` | enum | `nenhuma` (como a rodada final do clone) ou `medida` (60 %, σ 4 px, a do original: melhor em fundo claro) | `nenhuma` |
| `cenas` | string (JSON) | `{"<frase, a partir de 0>": "escura"}`: a frase vira a cena escura do neon (caixa alta em SF Pro 760 sobre o vídeo escurecido a 60 %, a última palavra antes do destaque maior e ao lado dele, na serifa; ver abaixo) | `{"2": "escura"}` (a frase do clone); frases transcritas recebem a da regra (abaixo) |

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

## A fonte da serifa (medida de novo em 30/10: a Instrument fica)

Testei mais 34 famílias itálicas OFL do Google Fonts (42 arquivos, mais pesos e larguras das variáveis), além das 9 do
clone: Alegreya, Amiri, Besley, Brygada 1918, Cardo, Castoro, Caudex, Cormorant Garamond, Crimson Pro, Crimson Text,
Fanwood, Faustina, Gelasio, Gentium Book Plus, Ibarra Real Nova, Libre Baskerville, Libre Bodoni, Libre Caslon Text,
Linden Hill, Literata, Lora, Mate, Merriweather, Noto Serif Display (também a 62,5 % de largura), Old Standard, Petrona,
Piazzolla, Rosarivo, Sedan, Sorts Mill Goudy, Source Serif 4, Spectral, STIX Two e Vollkorn. Medida pela tinta, como o
`ajusta_serifa.py` do clone: cada uma das 8 palavras em serifa desenhada sobre a placa no quadro assentado, contra a luz
do original (o recorte de `dentro.mp4`) na caixa + 24 px, com a proporção da fonte travada (uma razão largura/altura só
para as 8 palavras; escala e posição por palavra) e com espaço entre letras e negrito falso variando.

| fonte (melhor variante) | erro médio | reinvent | someone | new | works | right | along | magnified | now |
|---|---|---|---|---|---|---|---|---|---|
| **Instrument Serif (espaço -7, traço 1,3: a atual)** | **0,1125** | 0,126 | **0,079** | **0,111** | **0,149** | 0,066 | 0,088 | 0,104 | **0,179** |
| Playfair Display (espaço -10, traço 1,3) | 0,1161 | **0,120** | 0,083 | 0,134 | 0,166 | **0,062** | **0,087** | **0,075** | 0,202 |
| Crimson Text (espaço -10) | 0,1242 | | | | | | | | |
| Amiri (espaço -10) | 0,1247 | | | | | | | | |
| as outras 32 novas e a DM Serif | 0,128 a 0,168 | | | | | | | | |
| sem camada (não desenhar) | 0,1802 | | | | | | | | |

Nenhuma ganha da Instrument; a calibração dela (espaço -7, traço 1,3) também fica: traço 2, 2,6 e 3,5 e espaço -10 ou -4
pioram (0,1142 no melhor). A Playfair com espaço -10 chega perto e ganha em "magnified", "right" e "reinvent", mas
perde nas palavras curtas. O "t" alto e o traço grosso do original não estão em nenhuma das fontes livres testadas.
Script e resultados fora do repositório: `clones-novos/final-output/fase2/fontes/` (`avaliar.py`, `RESULTADO.json`).

### Qual frase vira a cena escura (resolvido em 30/10)

O `montar.py` escolhe sozinho, pela regra `escolhe_escura()`: no máximo uma cena escura por vídeo, e só com 3 frases ou
mais. Candidatas são as frases do meio (nem a primeira, que dá o padrão, nem a última, que borra no fim) que têm
destaque e pelo menos 2 palavras antes dele (a caixa alta precisa de uma linha em cima). Ganha a de maior pausa antes:
do início da última palavra da frase anterior até o início da frase, que é onde quem fala respira para dar ênfase.
Nas frases do clone a regra escolhe a frase 3 ("THAT'S NOT HOW SELF-DOUBT works"), a mesma do original; no exemplo do
Pexels escolhe a 4 ("repeated every single day", 0,92 s de pausa antes). O autoteste do `montar.py` confere os dois
limites (menos de 3 frases não tem cena; frase sem destaque ou com uma palavra só antes dele não entra).

Quem manda, nesta ordem: o campo `cenas` de uma `--versao` (inclusive `{}`, que desliga), a marca `escura:` no
`destaques.txt` (o `caso.py` grava em `cenas`) e a regra. Versão antiga com `frases` e sem `cenas` passa pela regra
(antes ela herdava o `{"2": "escura"}` do clone).

## A altura vem do rosto (30/10)

Com a gravação real em close (teste cego C), a altura do clone (1108) punha o texto na barba e na boca, e a cena
escura (714) caía nos olhos do exemplo do Pexels. Agora o `montar.py` acha o rosto em `assets/pessoa.mp4` a cada
0,2 s com o Vision do macOS (`rosto.swift`, rodado pelo `swift` do sistema: local, sem download, sem rede; o OpenCV
5 do ambiente não tem mais o Haar e o modelo do YuNet não está instalado) e grava uma linha de base por frase no campo
`alturas` (`alturas()` no `montar.py`):

- o bloco ocupa da linha de base -180 a +80 px (a linha de cima sobe nos picos da serifa, a cena escura desce 44 px) e
  fica entre y 220 e 1632 (o cabeçalho do Reels em cima e os 15 % de baixo da interface);
- ordem: logo abaixo do queixo (+30 px), acima da cabeça (a caixa do Vision sobe 40 % para o cabelo), abaixo da boca,
  acima dos olhos, o mais baixo da área segura, pelo rosto somado dos quadros da frase;
- se essa altura cobre de olhos a boca em algum quadro (um corte no meio da frase), vale a da área segura que deixa
  livres mais quadros, a mais perto dela; a amostra de logo antes do início conta, para pegar um corte em cima do
  início (no C, a frase 6 começa em f211 e o corte para a tela dividida é em f213);
- uma altura por frase (o texto não pula dentro dela); menos de 60 px de diferença da anterior fica a anterior; frase
  sem rosto em metade dos quadros fica `null` (vale `altura`).

`--altura` fixa uma altura para tudo e desliga o rosto; uma `--versao` com `alturas` manda. O detector soma ~5 s ao
`aplicar` (~17 s na primeira vez, quando o swift compila). Com isso, o `caso.py` passou a gravar no `destaques.txt` a
cena escura da regra (`escolhe_escura()`, com `escura:` na linha), que antes ficava fora do caminho do kit.

Prova (fora do repositório, `teste-cego/C-rosto/`): no C, frases 1 a 5 em 1335 (abaixo da barba), 6 em 427 (o corte),
7 a 9 em 877 (acima da cabeça na tela dividida, com a cena escura na 8); no Pexels, todas em 1274, a cena escura
também. Nenhum quadro das folhas antes e depois tem texto de olhos a boca. O autoteste confere close, tela dividida,
rosto enorme, sem rosto, o corte no início e a altura que não pula.

## O pingo do i encostado no "and" (resolvido em 30/10)

No primeiro grupo dos padrões, o pingo do i de "reinvent" sobe até a linha de cima e ficava colado no "d" do "and"
(a linha de cima subia só o bastante para não cobrir a serifa, 6 px, mas não andava de lado). No original o "and" fica
32 px à esquerda do pingo (f28). Agora a `tinta()` guarda o topo de cada coluna, a diagramação marca as colunas da
serifa que passam da altura de x (pingos e hastes) e um pedaço da linha de cima que fica a menos de `vaoPingo` (30 px)
de uma delas anda de lado, até `desviaMax` (40 px), para o lado mais perto que fique livre e dentro da tela. Sem lado
livre (como "It came" sobre "right"), vale a subida de antes. Nos padrões só o primeiro grupo muda: o "and" anda 33 px
para a esquerda e fica em x 316 (no original, 310). Os outros grupos saem iguais (prova em quadros, fora do
repositório: `clones-novos/final-output/fase2/pingo-antes-depois-1s.png` e `cmp-grupos.png`).

Sobre a placa do clone ainda aparece, nos quadros 0 a 2, a sobra do "and" original que o inpaint não apagou: isso é da
placa (só existe na prova com os padrões), não do molde.

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
- 30/10, com as mudanças desta data: o mesmo exemplo pelo `montar.py` (309 quadros, 5 frases, 6 destaques); a regra
  pôs a cena escura na frase 4 sem nenhuma marca (`exemplo/versao.json` é a versão resolvida dessa prova).
- Os padrões sobre a placa do clone: parecem o clone no olho, mas não no pixel (as provas ficaram fora do repositório).

## O que não faz

- A cena escura não corta para outra filmagem: escurece a da pessoa. A frase sai da regra acima; a pessoa troca no
  `destaques.txt` (`escura:`) ou no campo `cenas`.
- Não corta para outras filmagens nem borra o vídeo da pessoa na transição (só o texto).
- A altura do rosto precisa do macOS (o Vision pelo `swift`). Em outro sistema, ou se o swift falhar, vale a `altura`
  fixa e o resumo do `montar.py` avisa.
- Dentro de uma frase o texto não segue o rosto: se a pessoa se mexe muito, ganha a altura que deixa livres mais quadros.
