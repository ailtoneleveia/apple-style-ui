# Apple Style UI: o perfil de estilo

## Em uma página

**O que é.** Os três vídeos do @creatoroly que clonamos (Satellite, Joi e VoiceOS) foram medidos quadro a quadro.
Por caminhos diferentes, chegaram ao mesmo jeito de mexer. Esse jeito virou um arquivo só, o `estilo.js`: qualquer
molde ou peça nova do Apple Style UI carrega esse arquivo e já se mexe "como Apple", sem precisar de um vídeo
de referência do lado. Cor, fonte, logo e textos ficam no **kit de marca** de cada peça. O **perfil de estilo**
(este) cuida só do movimento, do tempo, da letra e do acabamento.

**As 8 regras, em português simples:**

1. **Nada para de repente.** Tudo chega como mola: sai rápido e vai freando. Nos três vídeos, uma caixa assenta em
   0,3 a 0,4 s e, no fim do caminho, perde cerca de um terço do que falta a cada 1/30 de segundo.
2. **Três molas para escolher.** *Suave* (a do Satellite: não passa do ponto, assenta em 0,41 s), *firme* (mais
   rápida, 0,30 s, também sem passar do ponto) e *elástica* (a do Joi: passa 8 % do caminho e volta, 0,31 s).
3. **Uma coisa vira a outra, sem corte.** Ícone vira cartão, cartão vira tile, tile vira pílula: é sempre a mesma
   **caixa que se transforma**. Corte seco, só num zoom de impacto ou numa troca de cena.
4. **Forma e cor andam em tempos diferentes.** Os cantos e a cor chegam antes da caixa (0,15 s). Escurecer é
   rápido. Clarear é devagar, quase meio segundo, passando por cinza.
5. **Tudo que entra nasce desfocado.** Texto e botão aparecem com 8 a 24 px de desfoque e ficam nítidos em 0,1 a
   0,3 s. Enquanto se transforma, a caixa desfoca mais quando corre mais.
6. **Motion blur de câmera, curto.** Exposição de 1/120 s (um quarto de quadro a 30 fps, meio quadro a 60 fps),
   feito com subquadros de verdade. Nada de borrão de CSS imitando velocidade.
7. **Ritmo.** Palavras entram uma a uma, a cada 40 ms; itens de lista, a cada 180 ms. A saída acelera, sai de
   cena, desfoca e some no fim.
8. **Letra.** SF Pro com peso por função (título 600, lista 620, botão 590, frase 450, número 900) e tamanho
   calculado pela largura da frase, não pela altura da letra.

**E a música?** Só o Joi encaixa os eventos na batida (colcheias de 136,9 BPM). O Satellite e o VoiceOS não seguem a
batida; o Satellite casa só a chegada da lista com os golpes da trilha. Por isso o encaixe na batida é opcional:
o `estilo.js` tem a função, e cada peça decide se usa.

**Como uma peça usa:**

```html
<script src="estilo.js"></script>
<script>
  const ES = window.ESTILO;
  const caixa = ES.caixa(palco, { estados: { icone: {...}, cartao: {...} },
    sequencia: [{ t: 0.2, estado: "icone", entrada: "escala" }, { t: 1.0, estado: "cartao" }], mola: "suave" });
  function draw(t) { const { F } = ES.quadro(t, 30, NF); caixa.desenha(F / 30); }
</script>
```

**A prova.** A demo (`demo/`) passa a mesma caixa por ícone, cartão, tile e pílula com as três molas lado a lado,
nos mesmos instantes do Satellite, usando só o `estilo.js`. A mola suave cai no mesmo quadro do Satellite na
passagem cartão→tile, e a firme cai no mesmo quadro na passagem ícone→cartão. Depois dos 4 primeiros quadros de
cada passagem, a largura fica a menos de 4 px da medida do Satellite. Detalhes no fim (seção 9).

**Versão travada.** Esta é a versão travada 1 do perfil de estilo. Os números da tabela abaixo são os que o
`teste.js` confere. Mudar um número muda todas as peças: rode `node teste.js` e refaça a demo (`./render.sh`).

```
estilo/
  ESTILO.md          este arquivo
  estilo.js          a biblioteca (window.ESTILO no navegador, require no Node)
  teste.js           autoteste: node teste.js
  demo/              composição HyperFrames da prova (index.html usa só o estilo.js)
  render.sh          ./render.sh previa | final (240 fps, tmix, H.264 que o QuickTime aceita)
  folha.py           folha de quadros e medida contra o Satellite
  saidas/            demo.mp4, demo-previa.mp4, demo-folha.jpg
  medidas/           molas.json (ajustes), batidas.py + batidas.txt, demo-contra-satellite.json
```

---

## Tabela técnica

Convenções: `f` = quadro do vídeo original de cada clone (Satellite e VoiceOS a 30/60 fps conforme indicado, Joi a
60 fps). `q@30` = quadros a 30 fps. Distâncias em px do quadro original (Satellite 1080x1080, Joi 1080x1920, VoiceOS
1920x1080). As trilhas vêm de `hf/tracks.js` de cada clone (fora do repositório). Ajustes por mínimos
quadrados em `medidas/molas.json`.

### 1. Molas

Forma fechada do oscilador amortecido (`molaErro`): erro `e(t)` com `e(0)=e0`, `e'(0)=v0`, parâmetros `zeta`
(amortecimento), `omega` (rad/s) e `u0` (impulso inicial em distâncias por segundo). Subamortecida, crítica e
superamortecida têm cada uma a sua fórmula; o `teste.js` confere contra integração numérica (RK4).

**Presets** (todos saem do repouso):

| preset | zeta | omega | assenta 2 % | overshoot | perda por quadro no fim (q@30 / q@60) | de onde veio | ajuste |
|---|---|---|---|---|---|---|---|
| `suave` | 1,22 | 20,0 | 0,405 s (12 q@30, 24 q@60) | 0 | 0,71 / 0,84 | Satellite, largura da caixa cartão→tile, f88-110 | rms 1,8 % |
| `firme` | 1,57 | 37,9 | 0,297 s (9 q@30, 18 q@60) | 0 | 0,64 / 0,80 | Satellite, largura da caixa ícone→cartão, f31-50 | rms 1,5 % |
| `elastica` | 0,62 | 19,2 | 0,311 s (9 q@30, 19 q@60) | 8,4 % do caminho | 0,67 / 0,82 | Joi, escala do botão Upgrade, f334-356 (0,45→1,05→0,99→1) | rms 1,8 % |
| `rapida` (interna) | 1,0 | 39 | 0,149 s | 0 | | Satellite, raio e cor no ícone→cartão, f31-35 | |
| `deslize` (interna) | 1,94 | 13,7 (u0 13,5) | 0,965 s | 0 | 0,88 / 0,94 | Satellite, pílula Vehicle subindo, f150-190 | rms 0,8 % |

**Curvas medidas** (de onde os presets saíram e o que confirma):

| clone | curva | quadros | zeta | omega | u0 | assenta 2 % | overshoot medido | perda/q@30 |
|---|---|---|---|---|---|---|---|---|
| Satellite | caixa, largura ícone→cartão | f31-50 | 1,57 | 37,9 | 0 | 0,30 s | 0,4 % | 0,63 |
| Satellite | caixa, altura ícone→cartão | f31-50 | 0,88 | 10,5 | 9,5 | 0,26 s | 1,3 % | 0,74 |
| Satellite | caixa, centro y ícone→cartão (afunda 14 px e volta) | f32-56 | 0,50 | 12,7 | 15,5 | 0,59 s | 36 % de 40 px | 0,81 |
| Satellite | caixa, largura cartão→tile | f88-110 | 1,24 | 20,3 | 0 | 0,41 s | 0 | 0,71 |
| Satellite | caixa, altura cartão→tile (atrasa) | f88-110 | 0,97 | 3,0 | 4 | 0,67 s | 0 | 0,91 |
| Satellite | balão, comprimento 200→439→391→400 | f278-300 | 0,58 | 15,1 | 12,5 | 0,33 s | 19 % | 0,75 |
| Satellite | balão, rotação 27°→−2°→0 | f278-300 | 0,94 | 17,0 | 27 | 0,29 s | 7 % | 0,59 |
| Satellite | Dynamic Island, largura 82→603→552 | f213-262 | 0,99 | 3,9 | 7,5 | 1,35 s | 11 % | 0,88 |
| Satellite | pílula Vehicle, y | f150-190 | 1,94 | 13,7 | 13,5 | 0,96 s | 0 | 0,88 |
| Satellite | pílula Fire, y | f127-135 | 2,18 | 59,6 | 38,5 | 0,26 s | 0 | 0,62 |
| Satellite | botão End, y | f156-199 | 2,64 | 14,7 | 5 | 1,34 s | 0 | 0,91 |
| Joi (60 fps) | botão Upgrade, escala | f334-356 | 0,61 | 19,4 | 0 | 0,31 s | 9 % (5 % do valor final) | 0,67 |
| Joi | ícone entrando, escala 0,29→0,94 | f5-15 | 0,66 | 17,1 | 6 | 0,33 s | 7 % (modelo) | 0,70 |
| Joi | escala da lista (largura do separador 750→714) | f145-186 | 0,85 | 6,0 | 4 | 0,52 s | 3 % | 0,84 |
| Joi | glifo "+" girando 17°→270° | f86-146 | 1,20 | 9,4 | 6 | 0,76 s | 0 | 0,84 |
| Joi | panorâmica final | f354-437 | 1,74 | 11,3 | 0,5 | 1,12 s | 0 | 0,89 |
| VoiceOS (60 fps) | janela, borda de cima | f141-200 | 0,95 | 9,1 | 10 | 0,31 s | 0,4 % | 0,75 |
| VoiceOS | janela, saindo do repouso em f136 | f136-200 | 0,94 | 13,5 | 0 | 0,38 s | 0 | 0,66 |
| VoiceOS | conteúdo dentro da janela (+27 → −10 → 0 px) | f146-200 | ajuste ruim (rms 11 %) | | | | 19 % | |

**Onde os três concordam.**
- A perda por quadro no fim do caminho das caixas fica entre 0,63 e 0,75 a 30 fps nos três (o VoiceOS anotou
  "0,6 a cada 3 quadros a 60 fps", que dá 0,71 a 30 fps).
- Caixa principal assenta em 0,30 a 0,41 s nos três.
- O que tem overshoot usa zeta entre 0,58 e 0,66: botão Upgrade e ícone do Joi, balão do Satellite.

**Onde discordam.**
- **Overshoot.** O Joi usa em botões e ícones (5 % do valor final). O Satellite usa em balão e ilha (11 a 19 %) e
  num afundar do cartão. O VoiceOS não usa no container, só no conteúdo (−10 px).
- **Assentamento longo** (0,9 a 1,3 s): só em lista, título e câmera, no Satellite e na panorâmica do Joi.
- **Firme e suave no Satellite.** O próprio Satellite usa a firme no ícone→cartão e a suave no cartão→tile. O
  VoiceOS, saindo do repouso, dá 0,38 s, igual à suave; com o impulso medido, dá 0,31 s, igual à firme.

### 2. Obturador e motion blur

| clone | fps | obturador medido | usado no clone | exposição | onde mediu |
|---|---|---|---|---|---|
| Satellite | 30 | 0,25 quadro (rampa 24 px na horizontal contra 12 na vertical, botão End a 111 px/q) | 0,3 | 8,3 ms (10 usado) | f~206, pan rápido |
| Joi | 60 | 0,4 (rampa 24 px a 62 px/q contra 4 px parado) | 0,4; flip com desfoque extra de 10 px; saída da lista com 1,0 | 6,7 ms | cartão azul; flip f83; lista f188-200 |
| VoiceOS | 60 | 0,5 (ajuste `shutterfit.py`) | 0,5 | 8,3 ms | pans do vinhedo |

- **Concordam:** 6,7 a 10 ms de exposição. As duas medidas mais firmes (Satellite 0,25 a 30 fps, VoiceOS 0,5 a 60
  fps) dão exatamente 1/120 s. No `estilo.js`: `EXPOSICAO = 1/120`, `obturador(fps) = fps/120`.
- **Discordam:** o Joi exagera o arrasto em viradas e saídas (flip f83, lista f188-200: o pontilhado vira tracinhos
  de 20 px, mais do que o obturador explica).
- **Esquema (do Satellite, igual nos três):** render a 240 fps (8 subquadros a 30 fps, 4 a 60 fps), `tmix` de N e
  `select` do último. `Fi` (quadro inteiro) decide o que existe e os cortes; `F = Fi + (frac − MB_SHIFT·fps)·SHUTTER`
  move as coisas; `MB_SHIFT = (N−1)/2/(fps·N)` centra os subquadros. Em corte seco, os subquadros nunca misturam os
  dois lados (Joi f354). Borrão de CSS só para desfoque de profundidade, nunca para velocidade (Satellite: tirar o
  `vy*0,09` levou f144-151 de 0,0141 para 0,0113).

### 3. Tempo: os eventos caem na batida?

Medido com `npx hyperframes beats` (BPM) e onsets por fluxo espectral; a fase da grade vem dos onsets fortes.
Acerto = evento a até 33 ms (1 q@30, 2 q@60) da marca. "Acaso" = a mesma lista de eventos deslocada no tempo, 2.000
vezes. Script e saída: `medidas/batidas.py`, `medidas/batidas.txt`.

| clone | BPM (colcheia) | eventos | na colcheia | acaso | nos onsets | acaso | leitura |
|---|---|---|---|---|---|---|---|
| Joi | 136,9 (219 ms) | 6 grandes da LESSONS (f80, f132, f199, f281, f329, f354) | **4 de 6**, desvio médio 24 ms | 1,8; 55 ms | 4 de 6 | 2,2 | segue a colcheia (p≈0,09 com só 6 eventos); f281 (+3,5 q) e f354 (−2,4 q) escapam |
| Satellite | 102,6 (292 ms) | 27 | 2 de 27 | 6,1 | 11 de 27 | 7,4 | **não segue a batida**; as 5 pílulas f127, f132, f138, f144 e f150 caem em golpes da trilha (+0,9 / 0,0 / +0,1 / +0,5 / +0,6 q) |
| VoiceOS | 119,9 (250 ms) | 26 | 4 de 26 | 7,0 | 8 de 26 | 9,9 | **não segue**; a trilha tem locução, a ação segue a fala |

No `estilo.js`: `grade({bpm, primeiro, divisao})` ou `grade({batidas})` (aceita a saída do `hyperframes beats`) e
`encaixa(eventos, grade, {tolerancia, fps})`, que move cada evento para a marca mais perto e devolve o desvio.

### 4. Entradas, saídas e escalonamento

| nome | o que faz (padrão do `estilo.js`) | medido em |
|---|---|---|
| `cima` | cai de 1,6x a própria altura, mola suave; desfoque 10→0 em 0,17 s; aparece em 0,06 s; cor de destaque vira tinta entre 0,10 e 0,25 s | Joi "Get your subscription" f281-292: 6 q a 22 px/q (132 px para letra de 82 px), opacidade em 2,5 q, desfoque 10→3 em 6 q e →0 em 10 q, vermelho→#171617 começa 5 q depois. Satellite título f155-188: cai 185 px (2,9x os 64 px) com cauda de 1,1 s, desfoque 10→0 em 9 q@30, verde→tinta f159-163,5 |
| `baixo` | sobe de 1,2x a altura, mola firme; desfoque 24→0 em 0,2 s | VoiceOS palavras f72-86: sobem 70-140 px (letra de 86 px), desfoque 24→0 em ~12 q@60; pílula f13-18: desfoque 14→0 |
| `lado` | entra pela direita de 62 % da largura do quadro, mola suave; desfoque 12→0 em 0,2 s | Joi estrela f315-329: x 1052→382 em 14 q@60 (0,23 s), desfocada; VoiceOS triângulo f578-590 gira 270°→0 |
| `escala` | 0,45→1 com a mola elástica (passa de 1 e volta); desfoque 16→0 em 0,3 s; aparece em 0,1 s | Joi Upgrade 0,45→1,05→1 (f334-356), ícone 0,29→0,94 em 10 q@60; Satellite ícone f5-14: 0,5→1 sem overshoot, desfoque 16→0, opacidade em 3 q@30 |
| `desfoque` | no lugar, 12 % maior e desfocado (12 px) até nítido em 0,12 s | Joi textos e botões 8-12 px→0 em 6-7 q@60; VoiceOS janela 24→0 f136-150 (0,23 s); Satellite conteúdo do tile 8→0 f89,5-97 (0,25 s); motor "desfoque" 12 % maior |

| saída | o que faz | medido em |
|---|---|---|
| `cima`, `baixo` | sai 12,4 % da altura do quadro acelerando (x1,25 por quadro a 30 fps, lambda 6,7/s) em 0,47 s; desfoque 0→9 px a partir de 41 % do tempo; opacidade 1→0,7→0 nos últimos 29 % | Satellite f259-276: câmera y 0→−134 px, desfoque da ilha 0→2→5→9 px (f266-276), opacidade 1→0,7→0 (f271-276) |
| `desfoque` | só desfoca e some, mesma curva | Satellite ilha; VoiceOS UI f254-262 |
| `lado`, `escala` | espelho da entrada com a mesma aceleração | sem medida própria |

- **Concordam:** saída acelera (nunca freia), desfoca e some no fim. Entrada sempre com desfoque que zera depressa.
- **Discordam:** direção da saída (Satellite sobe; Joi e VoiceOS deixam cair). O Satellite usa cauda longa no
  título; o Joi pousa seco em 0,1 s.
- **Escalonamento** (`PASSO`): palavras 40 ms (Joi f132/134/137 e f281/283/285,5: 33 a 50 ms), botões 33 ms (Joi
  f209/211/213), itens de lista 180 ms (Satellite f127/132/138/144/150: 170 a 200 ms), letras 100 ms (VoiceOS
  "ohhhh man" f3-58).

### 5. Transições e a caixa que se transforma

**Corte quase nunca.** Satellite: os dois "cortes" do `burst.py` (f10, f123) são morphs, o vídeo é um plano só.
Joi: 1 corte de verdade em 7 (punch-in f353→354). VoiceOS: 2 cortes (f263, f487) e 1 crossfade com máscara de
nuvem (f63-74).

**Regras da caixa** (`ES.caixa`), medidas no box do Satellite (`tracks.js`, `box`), no flip do Joi e na janela
do VoiceOS:

| regra | número | de onde |
|---|---|---|
| posição e tamanho seguem a mola da passagem, encadeada (a velocidade continua se um estado chega antes do outro assentar) | ver molas | Satellite f31-50, f88-110 |
| o raio chega antes da forma | raio/menor lado 0,50 → 0,40 → 0,31 → 0,27 → 0,229 em f31-35, enquanto a largura só assenta em f42; mola `rapida` | Satellite |
| a cor nova cobre a velha como opacidade, nunca brightness nem cinza no meio | fração medida 0,40 / 0,73 / 0,87 / 0,94 / 0,975 (f33-37); crossfade 0,0254, brightness 0,0205, mistura 0,0165 | Satellite LESSONS |
| escurecer é rápido | 0,17 s (Satellite f32-37), 0,12 s (Joi f198-204, frações 0,1→1 em 7 q@60) | Satellite, Joi |
| clarear é lento e passa por cinza | rampa em S de 0,47 s (Satellite tile→pílula f119-133: 20→246) e 0,53 s (Joi fundo escuro→branco f271-303); a cor velha perde o matiz | Satellite, Joi |
| desfoque de profundidade proporcional à velocidade da forma | picos 7,5 px (f33), 3 px (f92-93), 6 px (f127) | Satellite |
| conteúdo velho sai rápido, o novo entra logo depois e nasce desfocado | arte do ícone 1→0 em f30-33; arte do cartão 0→1 em f32,5-36; conteúdo do tile 8→0 px em f89,5-97 | Satellite |
| conteúdo escala com a caixa ou a caixa vira máscara | ícone e cartão escalam; no cartão→tile o conteúdo para de escalar em f88 (`encaixe: "mascara"`) | Satellite LESSONS |
| virar (flip) | rotateX 7°→85° (f60-82) e 109°→180° (f85-92), perspectiva 1200, a face troca aos 90°, pico de desfoque de 10 px de lado (f83) | Joi |
| desdobrar com a base fixa | borda de baixo parada em y 256 enquanto o topo sobe de 77 para −18 (f139-145); na caixa basta os dois estados terem a mesma base (a mola é linear, a base não se mexe) | VoiceOS |

Cada estado tem `x, y, w, h, raio, cor, fundo, sombra, brilho, conteudo, encaixe, atraso`; a sequência tem `t,
estado, mola, desfoque, virar` e, no primeiro item, `entrada`.

### 6. Tipografia

| função | peso | Satellite | Joi | VoiceOS |
|---|---|---|---|---|
| título | 600 | 550 com −1,5 px de espaço (64 px) | 620 (menu, 62 px) | 600 (título da página, 58,9 px) |
| lista | 620 | 500 (30 px) | 620 (58 px) | |
| botão, rótulo | 590 | semibold (rótulo do ícone) | 590 (29 px) | |
| frase, subtítulo | 450 | | 450 ("Get your subscription" 82 px, subtítulo 76,6 px) | |
| corpo, texto grande | 500 | 500 (cartão, tile) | 500 ("Joi Pro", Upgrade) | 500 (quase todo o texto, de 12,5 a 192 px) |
| número | 900 | | 900 (dígitos de 265 px) | |
| tecla | 700 | | | 700 ("fn" 156 px) |

- **Tamanho pela largura da frase:** o VoiceOS mostrou que pela altura erra 8 a 12 % ("I got a lot work to do":
  93 px pela altura, 86 px pela largura). Satellite (inkspan) e Joi (PIL na fonte real) também mediram pela tinta.
  `tamanhoPorLargura(texto, largura, {peso})` itera 4 vezes porque o SF Pro troca o tamanho óptico com o tamanho.
  Testada no render: acerta a largura pedida em 0,1 px; para "Get your subscription" a 729 px dá 80,6 px, contra 82 px
  medidos pela tinta no Joi (a largura de avanço é ~2 % maior que a tinta). Só chame depois de
  `document.fonts.load`: antes disso ela mede a fonte reserva e erra 6 a 10 %.
- **Concordam:** SF Pro do sistema (SFNS.ttf variável, opsz automático), texto colorido que escurece para a tinta
  depois de pousar. **Discordam:** o peso do texto grande (Joi 450 a 620, Satellite 550, VoiceOS 500).
- Texto que muda de papel encolhe em torno do começo de uma palavra, não do centro (Joi f314-330, x 317).

### 7. Acabamento

**Cantos** (`RAIO`, raio dividido pelo menor lado; nenhum dos três usou canto contínuo, só border-radius):

| peça | raio / menor lado | de onde |
|---|---|---|
| ícone, cartão | 0,229 | Satellite cartão 88,5 px em 388 (ajuste rms 0,3 px); Joi ícone 75/280 = 0,268 |
| tile | 0,235 | Satellite |
| menu | 0,246 | Joi 130/528 |
| cartão grande | 0,287 | Joi cartão azul ~150/522 (não está no `RAIO`) |
| tecla | 0,216 | VoiceOS 64/296 |
| janela | 0,15 | VoiceOS 46/307 |
| pílula | 0,345 | Satellite 40/116 |
| cápsula | 0,5 | Joi pílula 88/181 |

**Sombras quase não existem.** A profundidade vem de aro fino e brilho colorido (`SOMBRA`):
`pilula` 0 2,5px 0 #e3e3e3 + 0 1px 3px 3 % (Satellite lista); `flutuante` 0 10px 26px 16 % (Satellite ilha);
`tecla` aro 2,5 px + 0 8px 22px 7 % (VoiceOS); `aroEscuro` aro 2 px #2c2c2f (Joi menu); `aroClaro` aro 3 px branco
22 % (Joi pílula); `aroVidro` aro 1 px branco 7 % (VoiceOS janela).

**Brilhos** (`brilho(cor, raio, alfa)`): Satellite knob 16 px / 0,55, barra do tile 14 px / 0,6, halo atrás do
cartão no cartão→tile com desfoque de 50 px e pico de 0,75; Joi halo por objeto (+10 a +20 níveis) e campo largo
(+3); VoiceOS rosa 18 a 26 px / 0,55 a 0,8.

**Luma** (`LUMA`): o encode do HyperFrames sai 0,8 % escuro (#fdfdfd → #fbfbfb). `LUMA.filtro` é o ganho 1,008 só
no Y (Satellite; ganho no croma piorou os verdes claros f120-135 de 0,0097 para 0,0109). `LUMA.instagram` soma a LUT
do Joi (escuros +2 até Y 73, rampa até 154, brancos +1 a partir de 233), que copia os níveis do vídeo postado. Na
demo as duas juntas levaram #fdfdfd a #ffffff e fizeram um anel de 1 nível em volta do brilho, por isso a LUT ficou
só para comparar com um original baixado.

**Fundos:** #fdfdfd (Satellite e Joi), #f3f3f3 (Joi abertura), escuros #0d0d0d (Joi), #101010 (Satellite cartão),
#111113 (Joi menu).

### 8. O que o `estilo.js` exporta

| grupo | nomes |
|---|---|
| utilitários (do Satellite) | `clamp, lerp, E, prog, kf, cr, hex, mixc, rgb, blurf, luma` |
| obturador | `EXPOSICAO, obturador(fps), mbShift(n, fps), quadro(t, fps, nf) → {Fi, F}` |
| molas | `molaErro, MOLAS, mola(t, preset), molaVel, assenta(preset), overshoot(preset), velMax, cadeia(t, chaves), cadeiaCor` |
| entradas e saídas | `ENTRADAS, entrada(tipo, t, opções) → {dx, dy, s, rot, blur, op, tinta}, SAIDAS, saida, PASSO, escalona` |
| tempo | `grade, encaixa` |
| tipografia | `PESOS, tamanhoPorLargura` |
| acabamento | `RAIO, raio, SOMBRA, brilho, LUMA` |
| caixa que se transforma | `caixa(pai, {estados, sequencia, mola, desfoque}) → {raiz, desenha(t), geometria(t)}` |

`t` sempre em segundos. Numa composição, `const {Fi, F} = ES.quadro(t, FPS, NF)` e desenhe com `F / FPS`.

### 9. Prova: a demo

`demo/index.html` (1920x1080, 30 fps, 150 quadros) usa só o `estilo.js`. A mesma caixa, em escala 0,75, passa por
ícone (f5, entrada `escala`), cartão (f31), tile (f88) e pílula (f119), nos instantes do Satellite, uma vez com cada
mola: suave, firme e elástica, lado a lado. Os desfoques dos picos são os medidos (7,5 / 3 / 6 px).

- Vídeo: `saidas/demo.mp4` (240 fps → tmix 8 → 30 fps, luma calibrada, H.264 veryslow crf 12, refs 4, nível 5.1).
  Prévia sem motion blur: `saidas/demo-previa.mp4`.
- Folha de quadros: `saidas/demo-folha.jpg`, com o Satellite (o clone, fora do repositório) em cima e as três molas
  embaixo, nos quadros f24 a f128, na mesma escala.
- Render (este Mac, `--workers 1`): 1.200 quadros a 240 fps em 73 a 103 s (três rodadas), 81 a 140 s no total com
  tmix e encode. Prévia: 19 s de render, 42 s no total.

**Números** (`folha.py`, `medidas/demo-contra-satellite.json`; larguras em px do Satellite):

| mola | passagem | meio do caminho (Satellite / demo) | erro médio de largura | depois dos 4 primeiros quadros |
|---|---|---|---|---|
| suave | cartão→tile | f92 / **f92** | 15,8 | **3,5** |
| suave | ícone→cartão | f34 / f35 | 36,9 | 21,2 |
| firme | ícone→cartão | f34 / **f34** | 9,9 | **3,7** |
| firme | cartão→tile | f92 / f91 | 28,7 | 16,5 |
| elástica | ícone→cartão | f34 / f34 | 34,2 | 28,4 (passa 8 % de propósito) |
| elástica | cartão→tile | f92 / f91 | 46,4 | 36,0 |

- O render bate com o modelo da caixa em 1 a 2 px (f86-100): o caminho estilo.js → HyperFrames → tmix é exato.
- Os erros dos primeiros quadros vêm da cena, não da mola: o Satellite incha o disco de 208 para 318 px em f24-31 e
  afasta a câmera de 768 para 614 px em f55-88 antes de cada passagem; a demo sai do tamanho do estado.
- **No olho:** forma, cantos, cor, desfoque e tempo da caixa batem com o Satellite em ícone→cartão e cartão→tile. A
  passagem tile→pílula sai escura, cinza e clara nos mesmos quadros (f121 a f128). O que falta é o que não é caixa:
  o knob azul, a Terra, o halo azul do cartão→tile e os lavados verdes do fundo.

### 10. O que ainda não está no perfil de estilo

- **Tile→pílula do Satellite** é um ease-in de 8 quadros seguido da cauda da pílula, não uma mola. A mola sai do
  repouso andando mais cedo (em f121 está em 34 % do caminho, o Satellite em 16 %) e chega ao meio do caminho cerca
  de 1 quadro antes (Satellite entre f122 e f123).
- **Altura que atrasa** no cartão→tile (largura a 54 % quando a altura está a 36 %, f92): a caixa usa a mesma mola
  nos dois eixos.
- **Atraso por elemento do conteúdo:** no Satellite o texto do cartão entra 0,23 s depois do arco (f38-40,5); a
  caixa tem um atraso só por estado.
- **Vidro do Joi** (bolha mais saturada quando pequena, aro de 14 px, paredes assimétricas) e **conteúdo que treme
  dentro da janela** do VoiceOS (+27 → −10 → 0 px) ficaram fora.
- **Saídas `lado` e `escala`** não têm medida própria (espelham a entrada).
- **Encaixe na batida** confirmado só no Joi, e com 6 eventos (p≈0,09): é tendência forte, não prova.
- Uso interno de estudo: SF Pro e emojis da Apple são do sistema; a trilha original não entra na demo.
