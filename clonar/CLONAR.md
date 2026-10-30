# Clonar um vídeo, com prova

Clonar é refazer um vídeo de referência no HyperFrames até ele ficar igual quadro a quadro, com nota. O clone
serve para aprender o estilo de quem fez (molas, tempo, blur, letra) e vira molde depois. Uso interno de estudo:
o original e os recortes dele nunca saem daqui.

O ciclo: **medir, fichar, montar, rodar, comparar, corrigir**. No máximo 6 rodadas.
**Alvo (o que é "pronto"):** a nota global (distância ≤ 0,012, correlação de movimento ≥ 0,97 e pico de até 1 quadro
em todas as janelas) E todas as peças aprovadas no medidor por peça E o movimento paramétrico (seção "O loop de
qualidade"). A nota global sozinha não basta: o teste cego B2 fez 0,005 / 0,977 / 0 na rodada 3 e saiu bem inferior
aos clones bons (cursor e memoji errados, texto da chamada desalinhado, movimento por chaves lidas à mão). O fundo
liso dilui o erro de cada peça na média do quadro.

## Três regras que o teste cego cobrou

1. **Bateu o alvo, fecha na hora.** Quando a rodada bate o alvo inteiro, peças incluídas (o `proximo` diz "alvo
   batido: rode final"), roda `clonar.py final` e entrega. Nada de ajuste quadro a quadro depois disso: no teste, a rodada 2 já tinha distância
   0,005, correlação 0,977 e pico 0, e a sessão gastou mais 1 h polindo a uns 5 min por quadro. Polir só se o
   usuário pedir.
2. **Nada fica rodando sozinho.** Todo comando longo (render, rodada, final, ajuste) roda em primeiro plano, com o
   tempo limite do comando no máximo (10 min). Se precisar mandar para o segundo plano, espera no mesmo comando até
   acabar (`wait`, ou um laço que confere o arquivo de saída). Nunca termina o turno com processo pendente: no modo
   sem interação o aviso de fim nunca chega e a sessão fica parada.
3. **Recriar, não recortar.** Texto, ícone, cartão, pílula, botão e avatar desenhado são SEMPRE recriados em HTML,
   CSS ou SVG, com a fonte e as cores medidas. Recorte do original só vale para foto ou vídeo filmado de verdade
   (pessoa, paisagem, foto de produto) e para o campo de luz do fundo sem nenhuma peça por cima. Cada recorte entra
   em `hf/assets/RECORTES.md`, numa tabela `| arquivo | tipo | motivo |` (arquivo relativo a `hf/assets/`, aceita
   `*`; tipo `foto`, `video` ou `fundo`). No teste cego, um clone recortou 21 peças do próprio original e só animou
   os recortes: a nota ficou ótima porque o pixel era o original, mas o vídeo saiu borrado (nitidez 0,21 da do
   original), baixo em resolução e inútil como molde (não dá para trocar texto nem cor). Por isso a `rodada` roda
   `scripts/recortes.py`: raster sem declaração reprova a rodada (`"aprovada": false`, com o motivo), mesmo com a
   nota boa, e o `final` não fecha rodada reprovada. A nitidez do clone contra a do original vai na nota e no resumo.

## Instalar (uma vez)

```sh
python3 -m venv ~/.apple-style-ui/venv && ~/.apple-style-ui/venv/bin/pip install -r clonar/requirements.txt
```

Fora do pip: ffmpeg, node e o HyperFrames (roda por `npx`, versão fixa 0.8.184).
Os brutos de render vão para `ASUI_TMP` (padrão: pasta temporária do sistema), nunca para o projeto.

## A pasta de um clone

```text
clone-<nome>/
├── referencia/          original.mp4 + ORIGEM.md (link, autor, data, sha256)
├── RAIOX.md             as medidas em português simples
├── FICHA.md             cena por cena: o que aparece, de que quadro a que quadro, com os números
├── hf/                  a composição (index.html, estilo.js, assets/; recortes declarados em assets/RECORTES.md)
├── rodadas/01 … 06/     nota.json de cada rodada (distância, correlação, pico, fdsum, piores trechos, aprovada, nitidez)
├── saidas/              final.mp4 e lado-a-lado.mp4
├── LICOES.md            o que aprendeu, com evidência
└── .apple-style-ui/     bastidor: medidas, renders das rodadas, comparações, logs
```

- A pasta nasce quando precisa: `novo` cria só `referencia/` e `.apple-style-ui/`; o resto aparece no passo que usa.
- Nunca sobrescrever: antes de trocar um arquivo, o kit guarda uma cópia com data ao lado.
- Número de rodada não volta, nem se a pasta da rodada for apagada.

## O ciclo, passo a passo

Todos os comandos devolvem JSON `{ok, resumo, proximo: {comando, motivo, precisa_de_voce}}`.

1. **Criar.** `python3 clonar.py novo <pasta> <original.mp4> --link <url> --autor <@perfil>`
2. **Medir.** `python3 clonar.py medir <pasta>` roda o raio-x: duração, fps, cortes e cenas, curvas dos elementos,
   molas comparadas com as do `estilo.js`, obturador, BPM e batida, paleta e folha de quadros. Quando o texto entra
   palavra a palavra (legenda cinética), cada palavra vira trilha própria, com entrada e saída medidas (`--legenda
   nao` desliga, `--legenda sim` força). Ler o `RAIOX.md`
   inteiro e olhar `.apple-style-ui/medidas/folha.jpg` e `.apple-style-ui/medidas/analise/shots/*/burst.png`.
3. **Fichar.** Escrever `FICHA.md` cena por cena: quadros de início e fim, cada elemento, de onde vem, como entra,
   como sai, cor, fonte e peso. Cada número sai de uma medida (`scripts/trilha_palavra.py`, `medir.py`, `sheet.py`,
   `inkspan.py`, `track.py`, `camtrack.py`), nunca do olho. Toda peça que mexe (palavra, emoji, caixa, cartão) entra
   num `elementos.json` e vira trilha com `trilha_palavra.py <original> elementos.json .apple-style-ui/medidas/trilhas.js`. Os eventos grandes vão para `clonar.py medir <pasta> --eventos f1,f2,...`,
   que refaz o teste da batida com eles.
4. **Montar.** `python3 clonar.py montar <pasta>` cria `hf/` com o modelo, uma cópia do `estilo.js`, a SF Pro do
   sistema, o áudio do original e as trilhas medidas (`hf/trilhas.js`). Cada cena da ficha vira uma função de
   `draw(t)`, e cada peça de interface é desenhada nela (texto, forma, SVG), nunca um PNG recortado do original. O modelo já traz um canvas e o encaixe na tinta: `encaixa(txt, fonte, amostra(nome, F), opções)` desenha
   o texto ou emoji na caixa medida do original (escala, centro e ângulo), e `amostra()` prende o `F` ao trecho medido
   (sem isso o elemento nasce meio transparente). O `Fi` decide se o elemento existe. `{largura: true}` ajusta o
   espaço entre letras à proporção da caixa medida (a fonte do original quase nunca tem o mesmo espaçamento).
   **Movimento é mola, não pose.** A trilha medida serve para medir: cada movimento vira uma mola (`estilo.mola`,
   `estilo.cadeia`, `estilo.entrada`) com zeta, omega, impulso e começo ajustados nela (o `qualidade.py` dá a mola
   de cada movimento do original na correção). Tabela de pose por quadro em `hf/` reprova a rodada (veja "O loop
   de qualidade"). Onde não há trilha, comece pelas molas, entradas, saídas, passos e pesos do `estilo.js`. Placa de fundo (vídeo de pessoa, mapa) só quando
   `!SO_CAMADA`; sem ela, fundo neutro.
5. **Rodar.** `python3 clonar.py rodada <pasta> --o-que-mudou "..."` renderiza com motion blur de subquadros
   (240 qps: N=8 a 30 qps, N=4 a 60 qps; um worker; ganho de luma 1,008; H.264 nível 5.1), compara com o original
   e grava `rodadas/NN/nota.json`. `--previa` faz um render rápido sem blur para conferir a montagem. A rodada também
   confere os recortes e a nitidez (`scripts/recortes.py`, regra 3 lá em cima): `"aprovada": false` manda recriar as
   peças antes de qualquer outra correção. Roda em primeiro plano (uns 1,5 min num reel de 9 s).
   **Placa de vídeo** (a pessoa filmada é o próprio original, por baixo): o quadro inteiro fica artificialmente perto
   do original. O caminho do 5º clone: `placa_video.py` apaga a camada antiga do original na pegada dela (tinta da
   palavra assentada, caixa inteira na entrada, caixa rosa e cartão com a sombra, inclusive a passada do ponto das
   molas) → `hf/assets/placa/`; `aparicao.py` mede a entrada e a saída de cada peça contra essa placa; a mesma
   pegada vira a máscara da nota. Passe `--mascara <trilhas.js|caixas.json> --placa <placa.mp4>`: a nota que decide passa a ser a da
   camada recriada, só nos pixels da máscara de cada quadro (`compara_mascara.py`), com o movimento medido em
   quadro − placa e o número "sem camada" (não desenhar nada) ao lado para provar que a nota não engana. A máscara
   fica guardada em `.apple-style-ui/mascara.json` para as próximas rodadas e para o `final`.
6. **Comparar e corrigir.** A rodada roda o medidor por peça (`scripts/qualidade.py comparar`, com a checagem de
   código em `hf/`) e o `proximo` lista as 3 piores peças com o motivo técnico e a correção. Ataque essas 3, uma
   hipótese por peça. O `fdsum` por trecho (`.apple-style-ui/rodadas/NN/fdsum.txt`) e o `diffview.py` mostram onde
   está o erro no quadro. Detalhes na seção "O loop de qualidade".
7. **Fechar.** Ao bater o alvo (na mesma hora, sem polir), ou na 6ª rodada: `python3 clonar.py final <pasta>` gera
   `saidas/final.mp4` (a melhor rodada aprovada, de preferência uma em que todas as peças passaram) e `saidas/lado-a-lado.mp4` (resolução cheia, original à esquerda). `--so-camada` também renderiza
   `saidas/so-camada.mp4`: a mesma composição sem a placa (`camada.js`), o primeiro passo para virar molde.
   Escrever `LICOES.md`.

## O loop de qualidade (medir por peça, atacar as 3 piores)

A média do quadro não vê peça errada: num fundo liso, um cursor trocado ou um memoji diferente somem na conta. O
loop mede cada peça, critica com números de motion design, corrige as 3 piores e mede de novo.

**Medir por peça.** `scripts/qualidade.py comparar <original> <clone> [--pecas pecas.json] [--hf hf/]`. A `rodada`
já roda sozinha (com `--hf` e, se existir, o `pecas.json` da pasta do clone). As peças vêm do original em dois
níveis: o que difere do fundo da cena (cartão, painel, ícone) e o que difere do entorno (texto, avatar, cursor,
botão dentro do cartão). Para dar nome às peças da FICHA, escreva `pecas.json` (`[{"nome", "quadros": [a, b],
"caixa": [x0, y0, x1, y1]}]`). Cada peça é medida do mesmo jeito nos dois vídeos, na região dela no original:

| medida | como | reprova quando (limite) |
|---|---|---|
| velocidade | correlação de fase quadro a quadro, só onde ela confia nos dois vídeos | erro RMS acima de 2,5x a velocidade do original |
| quebras de C1 | a velocidade salta num quadro (chave linear, pose lida à mão, parada seca) | mais de 7 sem par no original (contadas como a 30 qps) |
| mola | cada movimento do original que é mola, e o clone na MESMA janela: curva de progresso, zeta, omega, passa do ponto, tempo de assentar | curva a mais de 0,75 (RMS), clone sem mola (resíduo 0,35 acima do original), ou movimento de 5 % do quadro que o clone não faz (menos de 15 %) |
| escalonamento | atraso de entrada contra a peça anterior da sequência, e a sobreposição | erro acima de 0,45 s |
| motion blur | obturador equivalente (o ajuste do raio-x) | fora de 0,5x a 2x o do original |
| nitidez | Laplaciano sobre a variância do recorte | abaixo de 0,2x a do original |
| cor | ΔE2000 da cor dominante da peça | acima de 46 (só pega cor trocada) |
| forma | IoU da máscara | abaixo de 0,2 |
| percepção | SSIM no recorte | abaixo de 0,5 |
| texto | tesseract confiante nos dois: conteúdo, altura-x; a espessura do traço só vai no relatório | conteúdo abaixo de 0,6; altura-x fora de 0,6x a 1,4x |

Sai `rodadas/NN/qualidade/QUALIDADE.md` (no bastidor) e `qualidade.json`, com a PIOR peça primeiro e o motivo
técnico de cada reprovação. O `proximo` da rodada lista as 3 piores com a correção. No B2: "y f146-151 (-94 px): o
clone não faz esse movimento (anda -11 px); animar com estilo.mola('suave') a partir do f146" e "largura f166-170:
curva diferente (rms 1,08): ζ 0,15 contra 0,90 medido, ω 8,2 contra 72,1; usar estilo.mola({zeta: 0.9, omega: 72.1,
u0: 0.0})".

**Atacar as 3 piores.** Uma hipótese por peça em cada rodada. A correção é sempre paramétrica: mola do `estilo.js`
quando ela explica a medida (o kit diz qual), ou mola com os parâmetros medidos. Proibido polir pose quadro a quadro:
a checagem de código reprova.

**Movimento paramétrico** (`qualidade.py codigo hf/`, também dentro de cada rodada). Reprova:
- tabela de chaves `[[quadro, valor], ...]` com mais de 4 chaves numa grandeza (início, fim, um passa-do-ponto e uma
  espera bastam para uma mola; mais que isso é pose copiada);
- trilha densa de pose (uma posição, escala ou caixa por quadro em `window.X = {...}`): a trilha medida mora no
  bastidor e serve para ajustar a mola, não para desenhar.

Passa: `estilo.mola`, `estilo.cadeia`, `estilo.entrada`, `estilo.saida`, `estilo.caixa`, `kf` e `cr` com até 4 chaves.
**Mapa de tempo é permitido** (o `mapL` do B2: inteiros que dizem qual quadro da 1ª volta mostrar em cada quadro da
2ª, quase sempre +1 ou 0). A diferença: o mapa de tempo só reparametriza o tempo e a pose continua saindo das molas;
a tabela de pose substitui a mola pelos números lidos do original, com velocidade quebrada em cada chave. Cor por
quadro (`bgL`) vai no relatório, sem reprovar. No B2 a checagem acusa 30 tabelas com 434 chaves (a maior, `PILULA`,
com 82) e nenhuma mola do `estilo.js`; o `mapL` e o `mapR` passam como mapa de tempo.

**Orçamento e pronto.** No máximo 6 rodadas. Pronto = nota global + todas as peças + código paramétrico. Na 6ª
rodada sem tudo passar, o `final` fecha com a melhor rodada (de preferência uma com as peças aprovadas) e o
`LICOES.md` anota o que ainda reprova, peça por peça.

**Calibração** (30/10, `rascunhos/.../qualidade-calibracao/`, peças detectadas sozinhas): os 3 clones bons passam e o
B2 reprova 16 de 57 peças. O pior de cada medida:

| medida | Satellite | Joi | VoiceOS | B2 | limite |
|---|---|---|---|---|---|
| peças reprovadas | 0 de 53 | 0 de 58 | 0 de 60 | **16 de 57** | 0 |
| erro de velocidade | 1,51 | 1,88 | 0,92 | **5,05** (cartão Recent com os memojis) | 2,5 |
| quebras a mais (30 qps) | 5 | 6,5 | 3 | **8** (grade de pastas, painel direito) | 7 |
| curva de mola (RMS) | 0,29 | 0,71 | 0,42 | **1,08** (pastas da 2ª volta) | 0,75 |
| clone sem mola (resíduo a mais) | 0,09 | 0,33 | 0,14 | **0,90** | 0,35 |
| movimento grande que o clone não faz | nenhum | nenhum | nenhum | **3** (anda 10 a 12 % do caminho) | 15 % |
| SSIM mínimo | 0,59 | 0,61 | 0,53 | **0,40** (ícone do Finder), 0,48 e 0,50 (rótulo Files) | 0,5 |
| IoU mínimo | 0,31 | 0,23 | 0,31 | **0,07** (rastro do WhatsApp), 0,18 (ⓘ e cursor do Get Info), 0,18 (aviso) | 0,2 |
| altura-x | 0,18 | 0,05 | 0,37 | **0,44** (Recent) | 0,4 |
| obturador (razão) | 1,53 | 0,99 | sem medida | 0,84 | 0,5 a 2 |

Com as peças da FICHA (`pecas.json` de cursor, avatar, texto da chamada, Get Info e botão), o B2 reprova o avatar
(SSIM 0,45: memoji diferente), o texto "Liam is calling" (IoU 0,15 e SSIM 0,46: desalinhado), o cursor da 2ª volta
(SSIM 0,49) e passa o botão verde (SSIM 0,83). O cursor da 1ª volta passa raspando (0,52).

O que a calibração mostrou e ainda limita:
- As margens são finas (velocidade 1,88 contra 5,05 é a folgada; quebras 6,5 contra 8 e SSIM 0,53 contra 0,50 não).
  Os limites saíram do pior clone bom, não de uma régua de percepção: clone novo que reprove raspando merece olho.
- Cor (ΔE), escalonamento, espessura do traço e conteúdo do texto quase não separam: em texto sobre degradê e em
  recorte com várias linhas o ruído dos bons é tão grande quanto o erro do B2. Ficaram com limite só para erro grosso.
- A checagem de código também acusa os 3 clones bons (eles usam trilha medida por quadro, `tracks.js`, e chaves com
  Catmull-Rom). A regra vale para o trabalho novo. A diferença do B2 para eles não é paramétrico contra trilha: é
  trilha densa medida por ferramenta e interpolada sem quebra, contra chaves esparsas lidas à mão e ligadas por reta.

**Sem referência** (aplicar molde, vídeo novo): `qualidade.py estilo <video.mp4> [--hf hf/]` compara contra o perfil
do `estilo.js`: molas dentro das faixas medidas (zeta 0,4 a 2,8, omega 2,5 a 65, assenta até 1,5 s, passa do ponto
até 40 %), metade ou mais dos movimentos de cada peça como mola, obturador entre 0,5x e 2x o do estilo (1/120 s),
nada parado por mais de 2 s, escalonamento (3 ou mais peças entrando no mesmo quadro reprova), velocidade
sem quebra, texto nítido e dentro da área segura (9:16: 8 % em cima, 18 % embaixo, 4 % dos lados; quadrado e 16:9:
3 %), fundo neutro, e pelo menos 30 % dos movimentos como mola.
Calibrado nos 3 originais, nos 3 clones bons e nos 3 exemplos dos moldes (`exemplos/`): os 9 passam (quebras por
peça até 14,5, obturador de 0,76x a 3x o do estilo, até 1,73 s parado, 31 a 65 % dos movimentos como mola). O B2
reprova por 55 quebras de velocidade no painel direito e pela checagem de código. Este modo só pega erro grosso:
sem o original ao lado, o espalhamento dos bons é largo (o Joi arrasta o borrão de propósito; as peças achadas
sozinhas incluem movimento que não é mola). Para nota fina, só o `comparar`.

## Caminho do comando de entrada: referência demonstrativa → vídeo com a pessoa do usuário

O caso mais pedido: a pessoa vê uma referência (muitas vezes um vídeo demonstrativo, com o vídeo editado dentro de um
cartão, de uma tela ou de um celular), cola o link, entrega a própria gravação e recebe o mesmo estilo com ela.
Provado no 6º clone (fora do repositório).

Os passos 1, 2 e 5 rodam sozinhos pelo `caso.py`; 3 e 4 continuam sendo trabalho de agente, com entrada e saída fixas.

1. **Baixar** e 2. **tirar o vídeo de dentro:** `python3 caso.py referencia <link ou arquivo> [--pasta caso-<nome>]`.
   Baixa com `yt-dlp` (sem cookies do navegador); post que pede login cai na cópia da biblioteca
   (`~/.apple-style-ui/biblioteca/videos/<código>.mp4`). Grava `referencia/reel.mp4` + `ORIGEM.md` (link, autor, de onde
   veio, sha256). Depois roda `scripts/extrair_tela.py` e decide sozinho (`--demonstrativo auto`): se a tela achada
   ocupa menos de 85 % do quadro, é demonstrativo e vira `referencia/dentro.mp4`; senão o reel já é o vídeo final
   (`--demonstrativo sim|nao` força). Cartão de borda indefinida: rode o `extrair_tela.py --quad` à mão.
   Saída: o `proximo.comando` já é o `clonar.py novo` do passo 3. No 6º clone: 41 s, dentro.mp4 de 594x1056.
3. **Clonar o vídeo de dentro (agente).** Entrada: `referencia/dentro.mp4` (ou o reel). Escolher um trecho que comece
   e termine num corte, ampliar para 1080x1920 se for menor (a nota do kit mede em 96 e 540 colunas, abaixo do nativo)
   e seguir o ciclo acima, com a pessoa como placa (`placa_video.py`, `aparicao.py`, `rodada --mascara --placa`).
   Saída: `saidas/final.mp4`, `lado-a-lado.mp4`, `so-camada.mp4` e `LICOES.md`. As ferramentas do 6º clone que juntam a
   camada (`camada.py`, `dados.py`) ficaram fora do kit: têm as
   palavras, os grupos e os quadros daquele trecho escritos no código e não servem para outro clone sem reescrever.
4. **Virar molde (agente).** Entrada: o clone. Saída: uma pasta com um projeto HyperFrames com campos
   (`data-composition-variables` + `getVariables()`: o vídeo da pessoa em `data-var-src`, as frases com o tempo de cada
   palavra, a cor e a fonte do destaque) e um `montar.py` ao lado. A diagramação e a animação viram regras com os
   números do clone (não as caixas medidas). Para o `caso.py aplicar` usar o molde, o montar.py segue o contrato escrito
   no topo do `caso.py` (`--pessoa --saida --versao --voz --previa` e as funções `le_palavras`, `trechos_de_fala`,
   `frases`). Exemplo: `moldes/fala-destaque/`.
5. **Aplicar à pessoa do usuário:** `python3 caso.py aplicar <molde> --video <gravação> [--saida <projeto>/saidas/x.mp4]
   [--idioma pt] [--destaques destaques.txt] [--voz fala.wav] [--previa] [-- opções do molde]`.
   - Transcreve com `scripts/transcrever.py`: Groq (whisper-large-v3, palavra a palavra, `GROQ_API_KEY` no ambiente ou
     no `.env`; plano gratuito); sem chave, avisa (`aviso: falta a GROQ_API_KEY no .env`) e usa o `hyperframes
     transcribe` local (small.en para inglês, large-v3 para o resto, ~3 GB na primeira vez). A lista fica no bastidor
     do projeto e é reaproveitada.
   - Agrupa em frases e alinha aos trechos de fala pelo `frases()` do molde.
   - Escolhe o destaque pela regra do kit (`scripts/destaque.py`): a palavra mais longa da frase fora das palavras
     vazias de português e inglês, sem advérbio em -mente/-ly se houver outra; empate, a mais perto do fim. Grava a
     escolha em `<projeto>/destaques.txt` (uma linha por frase, destaque entre colchetes). A pessoa muda os colchetes, ou
     põe `escura:` no começo da linha para a cena escura, e roda o mesmo comando: o arquivo é lido e respeitado.
   - Monta e renderiza pelo `montar.py` do molde (motion blur do `round_mb.sh`, um worker, para abaixo de 5 GB livres).
     Nada é sobrescrito: a saída que já existe ganha -2, -3.
   Prova em português (22/10), feita fora do repositório com uma fala real.

## Lista de verificação (o que os 5 primeiros clones ensinaram)

- [ ] **Medir cada peça quadro a quadro, animar por mola.** Toda peça que mexe vira trilha medida (`medir.py`,
      `track.py`) e a trilha vira mola ajustada (zeta, omega, impulso, começo). Ease no olho não chega lá; pose
      copiada quadro a quadro também não (o B2 tinha 434 chaves em 30 tabelas e saiu duro).
- [ ] **Só blur de subquadro.** Motion blur vem do render a 240 qps com obturador medido (1/120 s no estilo). Nada de
      `filter: blur()` proporcional à velocidade. Blur de CSS só para desfoque de entrada e profundidade, medido.
- [ ] **Corte seco não mistura lados.** `Fi` decide o que existe; os subquadros de um corte nunca juntam os dois planos.
- [ ] **Morph de cor é mistura.** A cor nova cobre a velha como opacidade (fração medida por quadro), nunca
      `brightness()` nem esmaecimento passando por cinza. Escurecer é rápido; clarear é lento.
- [ ] **Nada é estático.** Peça "parada" quase sempre ainda anda: brilho que varre, ponteiro que gira, conteúdo que
      treme dentro da janela. Amostre perfis de cor ao longo do tempo antes de congelar.
- [ ] **Peso de fonte medido.** Compare a quantidade de tinta da mesma palavra no mesmo tamanho (`inkspan.py`,
      `inkspan_light.py` para texto claro ou colorido) e ajuste o peso; depois o espaçamento.
- [ ] **Tamanho pela largura da frase.** Pela altura da letra erra 8 a 12 %. Use `ES.tamanhoPorLargura` (opsz = px).
- [ ] **Calibrar a luma.** Compare um fundo liso do clone com o do original em Y cru. O ganho 1,008 já vem no render;
      escuros e brancos de vídeo do Instagram pedem `LUMA_INSTAGRAM=1`. Nunca mexer no croma.
- [ ] **Conferir se há batida antes de supor.** O raio-x diz se os eventos caem na colcheia; só encaixe na batida
      quando ele (com os eventos da ficha) e o ouvido disserem que sim.
- [ ] **Container que encolhe:** o conteúdo escala ou a caixa vira máscara? Meça uma feição interna durante o encolhimento.
- [ ] **Geometria reconstruída é rascunho.** Ajuste de volta ao original com `maskfit.py` num quadro assentado.
- [ ] **Saída com tombo 3D:** ajuste por pontos internos e bordas ao mesmo tempo.
- [ ] **Recorte de objeto sobre brilho:** o alfa sai da luminância acima da borda do recorte; o brilho é camada à parte.
- [ ] **Cor e chave de tempo só de quadros numerados** (`select=eq(n,f)`), nunca de grade com rótulo nem de snapshot.
- [ ] **A tinta medida dá a caixa, a mola dá o caminho.** Texto e emoji: `trilha_palavra.py` no original, `encaixa()`
      na caixa assentada, e o caminho até ela por mola com os parâmetros medidos. Nenhum ease à mão.
- [ ] **Calibrar emoji e texto contra o próprio clone:** a mesma medida no original e no render, corrigir pela razão
      (escala pela raiz da razão de tinta, ângulo pela proporção da caixa). Espelhamento a caixa não vê: olhe.
- [ ] **Câmera encadeada acumula erro:** registre cada quadro direto contra a placa (`registra_cam.py`).
- [ ] **Fundo que se redesenha (mapa no zoom):** placa larga mais placas curtas com alfa por cima (`placa.py --janela`).
- [ ] **Placa de vídeo:** a nota que vale é a da máscara (`rodada --mascara --placa`), com "sem camada" ao lado.
- [ ] **Uma hipótese por região.** Mudou três regiões e duas pioraram: a média sobe e não se sabe por quê.
- [ ] **Placa de vídeo sem a camada antiga, e sem vazamento.** A pegada cobre a passada do ponto das molas (5º clone:
      o "S," da caixa rosa a 1,11 vazava pela placa e baixava a nota de graça).
- [ ] **Medir a entrada contra a placa, com as vizinhas fora da conta** (`aparicao.py`). Peça dentro de outra (texto
      no cartão) mede-se pelo contraste contra a peça de fora, não contra a placa.
- [ ] **"Ruído" que se repete quadro a quadro pode ser o movimento.** A borda da caixa rosa que "variava" era a mola
      (5º clone: correlação na máscara 0,81 → 0,91).
- [ ] **Peso por grupo.** Legenda e cartão do mesmo editor tinham pesos diferentes (720 e 590).
- [ ] **Referência demonstrativa: tire o vídeo de dentro primeiro** (`extrair_tela.py`) e meça tudo contra ele.
      ECC na faixa da borda deriva quando o conteúdo de dentro anda (6º clone: 24 px num cartão parado).
- [ ] **Nascimento pela tinta baixa.** A palavra pode nascer inteira e apagada (~85 %) e clarear depois; o limiar alto
      atrasa o nascimento em até 4 quadros.
- [ ] **Texto "parado" que escorrega.** Meça o x0 da trilha a vida toda (6º clone: 11 a 15 px em ~20 quadros).
- [ ] **Caixa com haste ou perna:** estenda a região só para onde a palavra tem haste (t, f, h) ou perna (g, y), sem as
      vizinhas, senão a caixa e a placa saem cortadas.
- [ ] **Fonte pela medida, não pelo olho:** desenhe as candidatas na caixa medida e compare na pegada.
- [ ] **Canvas não carrega @font-face sozinho:** `document.fonts.load()` e só guarde medida com `check()` verdadeiro.

## Ferramentas (`scripts/`)

| ferramenta | para quê |
|---|---|
| `raiox.py` | a medição inteira em minutos (o `medir` usa) |
| `burst.py` | folhas de quadros por cena, energia de movimento por quadro, análise que o `compare.py` usa |
| `cuts.py`, `audio.py` | cortes por continuidade de câmera; BPM, golpes e classe do áudio |
| `sheet.py` | todos os quadros de a até b numa folha (recorte opcional) |
| `fundo.py` | campo de fundo de baixa frequência por quadro (luz, vinheta, clarão), sem as peças desenhadas por cima |
| `trilha_palavra.py` | trilha de cada palavra, emoji ou caixa pela tinta (caixa, ângulo, cor, tinta por quadro) → `trilhas.js`; `--auto` acha as palavras sozinho |
| `placa.py` | placa de fundo em coordenadas de mundo pela câmera medida; `--janela`: placa curta com alfa |
| `registra_cam.py` | registro absoluto da câmera, cada quadro contra a placa (corrige o erro acumulado do `camtrack.py`) |
| `recortes.py` | todo raster de `hf/assets/` declarado em `RECORTES.md` (senão a rodada reprova, e diz qual veio do original por template matching); nitidez do clone contra a do original nas bordas dos elementos |
| `compara_mascara.py` | nota só na máscara (camada recriada sobre placa de vídeo), com o "sem camada" ao lado; aceita pegada PNG por peça |
| `placa_video.py` | placa de um vídeo de pessoa: o original com a camada antiga apagada (inpaint) na pegada de cada quadro |
| `aparicao.py` | entrada e saída de cada peça (opacidade, deslocamento, escala, desfoque por quadro) medidas contra a placa |
| `medir.py` | caixa ou momentos de uma peça por cor, quadro a quadro, direto do vídeo |
| `corner.py`, `maskfit.py` | raio de canto; ajuste afim de uma forma do clone contra o original |
| `inkspan.py`, `inkspan_light.py` | extensão e quantidade de tinta de um texto (escuro, claro ou colorido) |
| `track.py`, `camtrack.py` | pose de um objeto e câmera contínua por ECC encadeado |
| `round_mb.sh`, `round.sh` | render com motion blur de subquadros; prévia sem blur |
| `compare.py`, `fdsum.py`, `diffview.py` | nota global; distância por trecho com a rodada anterior; mapa da diferença |
| `qualidade.py` | o loop de qualidade: `comparar` (clone contra original, peça por peça), `estilo` (sem referência, contra o perfil calibrado) e `codigo` (movimento paramétrico em `hf/`) |
| `sbs.py` | lado a lado em resolução cheia |
| `saida.py` | o que as ferramentas novas têm em comum: saída JSON padrão e leitura de quadros um a um |
| `extrair_tela.py` | o vídeo de dentro de uma referência demonstrativa (cartão, tela, celular): acha, segue por homografia, endireita no tamanho nativo, lista trechos sem a tela e trocas de conteúdo |
| `transcrever.py` | as palavras de uma fala com início e fim (`[{text, start, end}]`, o formato dos moldes): Groq whisper-large-v3 com `GROQ_API_KEY`, ou o `hyperframes transcribe` local; `--autoteste` |
| `destaque.py` | a regra da palavra em destaque de cada frase (palavras vazias em português e inglês); roda sozinho como autoteste |

Todas as ferramentas novas devolvem o JSON padrão `{ok, resumo, proximo}`. Autotestes: `testes/conferir_raiox.py`
(o raio-x contra os 3 primeiros clones), `testes/conferir_pecas.py` (as peças acima num vídeo sintético, menos de
um minuto) e `testes/conferir_qualidade.py` (o medidor por peça: mola conhecida, velocidade quebrada, peça borrada
e a checagem de código, cerca de um minuto).

## Regras de render e disco

- `hyperframes render` sempre com `--workers 1` (com mais, ele grava todos os quadros em disco antes de codificar).
- O render para sozinho com menos de 2 GB livres e apaga o bruto logo depois do tmix.
- Vídeo dentro da composição (placa de fundo): o HyperFrames extrai os quadros a 240 qps para `ASUI_TMP/hf-cache`.
  Recorte a placa só no trecho e no tamanho que aparecem.
