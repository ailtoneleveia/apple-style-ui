# Receitas de motion: o que fazer quando uma peça reprova

O loop de qualidade (`clonar/scripts/qualidade.py`, seção "O loop de qualidade" do `clonar/CLONAR.md`) diz QUAL peça
reprovou e em qual medida. Este arquivo diz o que fazer com isso. Ache o sintoma no índice, meça o que a receita
manda, aplique a técnica com os números e meça de novo. Uma hipótese por peça em cada rodada: nos cinco clones, toda
rodada que mudou duas coisas na mesma região piorou uma delas e escondeu qual.

Os números vêm dos clones que fizemos antes de publicar o kit (os vídeos e as anotações ficam fora do repositório):
**Satellite** (1080x1080, 30 qps), **Joi** (1080x1920, 60 qps), **VoiceOS** (1920x1080, 60 qps), **legenda** (4º
clone, 30 qps), **salão** (5º, pessoa filmada, 25 qps), **final output** (6º, vídeo de dentro de um cartão, 30 qps) e
o teste cego **B3** (o reel DSCwCjGjR5R, clonado só com o plugin). `f` é o quadro do original de cada um. A tabela
completa das molas, do obturador e dos pesos está no `ESTILO.md`; aqui fica o caminho do sintoma até a correção.

A correção é sempre paramétrica (mola, entrada, saída, regra). Pose copiada quadro a quadro reprova na checagem de
código do loop, e com razão: ela trava a velocidade em cada chave.

## Índice por sintoma

| sintoma | o loop costuma acusar | receita |
|---|---|---|
| a peça rápida sai nítida demais, sem rastro | obturador, nitidez (clone mais nítido) | [1](#1-a-peça-rápida-sai-nítida-demais) |
| a peça sai dobrada, com fantasma ou nasce meio transparente | SSIM, IoU, quebras | [2](#2-a-peça-sai-dobrada-com-fantasma-ou-nasce-meio-transparente) |
| o movimento sai duro, de chave, sem fluidez | mola (curva, clone sem mola), quebras de C1, velocidade | [3](#3-o-movimento-sai-duro-sem-fluidez) |
| o cartão estica como líquido e o clone só escala | mola (movimento que o clone não faz), IoU | [4](#4-o-cartão-estica-como-líquido) |
| a caixa que se transforma parece crossfade ou passa por cinza | ΔE, SSIM no morph | [5](#5-o-morph-parece-crossfade-ou-passa-por-cinza) |
| a lista entra junta, as linhas andam todas iguais | escalonamento, IoU das linhas | [6](#6-a-lista-entra-junta) |
| texto pequeno com peso ou desenho errado | altura-x, SSIM do texto | [7](#7-texto-pequeno-com-peso-ou-desenho-errado) |
| texto com peso, largura ou espaçamento errados | SSIM, IoU, altura-x | [8](#8-texto-com-peso-largura-ou-espaçamento-errados) |
| texto desalinhado, pulando ou fora do lugar | IoU, trajetória | [9](#9-texto-desalinhado-ou-pulando) |
| o cursor está no lugar errado | IoU e SSIM do cursor, trajetória | [10](#10-o-cursor-está-no-lugar-errado) |
| memoji, avatar ou emoji vira mancha | SSIM do avatar | [11](#11-memoji-avatar-ou-emoji-vira-mancha) |
| a entrada parece seca: a peça nasce nítida e inteira | nitidez no 1º quadro, escalonamento | [12](#12-a-entrada-parece-seca) |
| a peça parada parece morta | velocidade (original anda, clone não) | [13](#13-a-peça-parada-parece-morta) |
| a lista de baixo sai nítida demais | nitidez, SSIM das peças de baixo | [14](#14-a-parte-de-trás-sai-nítida-demais) |
| cor ou nível errados, branco que vira cinza | ΔE, distância em trecho parado | [15](#15-cor-ou-nível-errados) |
| sombra ou brilho errado, halo cinza em volta do objeto | SSIM, distância | [16](#16-sombra-e-brilho) |
| o tempo não bate (adiantado, atrasado, fora da música) | pico, correlação, escalonamento | [17](#17-o-tempo-não-bate) |
| texto digitado ou ditado que aparece de uma vez | trajetória da tinta, ΔE | [18](#18-digitação-e-ditado) |
| palavra em destaque sem graça | mola da caixa de destaque, entrada | [19](#19-palavra-em-destaque) |
| saída ou troca de cena errada | mola, correlação no trecho | [20](#20-saída-e-troca-de-cena) |
| câmera ou fundo escorregando | velocidade do quadro inteiro, distância | [21](#21-câmera-e-fundo) |
| som, render e encode | (fora do medidor) | [22](#22-som-render-e-encode) |
| referência é um vídeo dentro de uma tela | (antes de medir) | [23](#23-vídeo-dentro-de-uma-tela) |
| a medida parece mentir | qualquer uma | [24](#24-quando-a-medida-engana) |

---

## 1. A peça rápida sai nítida demais

O original tem rastro (borrão na direção do movimento) e o clone sai seco. No B3, as bolinhas do f200 saíram nítidas
sem rastro e o ícone do WhatsApp subia sem o rastro verde.

**Medir.** No quadro mais rápido da peça, no original e no clone, na mesma região:

```sh
python3 clonar/scripts/medir.py original.mp4 200 200 escuro --forma rampa --regiao x0,y0,x1,y1
python3 clonar/scripts/medir.py original.mp4 199 201 escuro --regiao x0,y0,x1,y1    # caixa: a velocidade v sai do cx
```

`rx` é a rampa 10-90 % da borda na horizontal, `ry` na vertical. Andando v px/quadro em x, o borrão é
`L = sqrt(rx² - ry²) / 0,8` e o obturador da peça é `L / v`. Satellite: botão End a 111 px/q, rx 24, ry 12, L 26 px,
obturador 0,23 (o estilo usa 1/120 s: 0,25 q a 30 qps, 0,5 q a 60 qps). Joi: borda do cartão a 62 px/q, 24 contra 4
parada, ~0,4.

**Técnica, na ordem em que o erro costuma estar:**

1. **A peça não anda pelo `F`.** Tudo que se move é função do `F` contínuo de `ES.quadro(t, FPS, NF)`, nunca do `Fi`.
   Pose calculada com o `Fi`, ou guardada por quadro, faz os 8 subquadros verem a mesma pose: a peça sai nítida em
   qualquer obturador. Procure `Fi` em posição, escala e ângulo.
2. **A rodada foi prévia.** `rodada --previa` e `round.sh` não têm subquadros. O blur só existe no `round_mb.sh`.
3. **A peça arrasta mais que o global.** O obturador não é um número só: no Joi o flip do ícone chega a 10 px de
   borrão (f83) e na saída da lista o pontilhado vira tracinhos verticais de ~20 px, mais do que 0,4 explica. Dê à
   camada o obturador medido dela, com subquadros de verdade (blur isotrópico no lugar disso deixou o erro igual):

   ```js
   // obturador próprio de uma camada: s = obturador medido da peça, em quadros (até ~1)
   const Fcam = (Fi, F, s) => Fi + (F - Fi) * s / ES.obturador(FPS);
   desenhaBolinhas(Fcam(Fi, F, 0.9) / FPS);
   ```
4. **O rastro é maior que um quadro de caminho** (rastro desenhado pelo criador, não obturador): acumule a peça em
   n tempos para trás dentro do próprio quadro. Cada amostra vai para um canvas à parte e soma com peso 1/n, para as
   formas de uma mesma amostra continuarem se cobrindo normalmente:

   ```js
   const acc = new OffscreenCanvas(W, H), ag = acc.getContext("2d");
   const uma = new OffscreenCanvas(W, H), ug = uma.getContext("2d");
   // desenha(g, F) desenha só a peça no tempo F; janela em quadros, para trás; pesos opcionais (rastro que some)
   function rastro(desenha, F, janela, n = 6, pesos = null) {
     const p = pesos || Array(n).fill(1), soma = p.reduce((a, b) => a + b, 0);
     ag.clearRect(0, 0, W, H);
     for (let i = 0; i < n; i++) {
       ug.clearRect(0, 0, W, H); desenha(ug, F - janela * i / Math.max(1, n - 1));
       ag.globalCompositeOperation = "lighter"; ag.globalAlpha = p[i] / soma; ag.drawImage(uma, 0, 0);
     }
     ag.globalCompositeOperation = "source-over"; ag.globalAlpha = 1;
     ctx.drawImage(acc, 0, 0);
   }
   ```
5. **Rastro colorido** (o verde atrás do ícone do WhatsApp no B3) é uma peça: meça o comprimento dele por quadro pela
   cor (`medir.py ... verde --regiao ...`) e desenhe como forma própria, com o comprimento preso à velocidade da peça.

**Nunca** borrão de CSS proporcional à velocidade por cima dos subquadros. No Satellite, um `vy*0,09` esquecido
deixava as pílulas 2 a 4 vezes mais moles que o original (gradiente máximo de borda 44 contra 184 em f148); tirar levou
f144-151 de 0,0141 para 0,0113. Blur de CSS só para desfoque de entrada e de profundidade, medidos.

## 2. A peça sai dobrada, com fantasma ou nasce meio transparente

São erros do motion blur de subquadros, não da peça.

- **Buraco na trilha.** Um quadro sem medida no meio faz os subquadros de um quadro alternarem entre medida e
  estimativa: no Joi a linha 3 da lista saiu dobrada em f146 (25 px entre os dois ramos). Preencha os buracos
  internos por interpolação antes de desenhar; f144-151 foi de 0,0107 para 0,0060.
- **Corte seco.** O `Fi` decide o enquadramento; os subquadros nunca misturam os dois lados (Joi f354: 0,033 só
  nesse quadro até ramificar pelo `Fi`).
- **Primeiro quadro meio transparente.** Metade dos subquadros do 1º quadro cai antes da trilha. O `amostra()` do
  modelo já prende o `F` ao trecho medido; o `Fi` de quem chama decide se a peça existe (legenda, f120: 0,0392 →
  0,0170).
- **Duas cópias trocando.** Peça que muda de container (o glifo da ISS que vira o ícone do tile, no Satellite) tem
  trilha própria e é desenhada no espaço do palco durante a passagem. Nunca uma cópia sumindo enquanto a outra
  aparece: f88-95 foi de 0,0301 para 0,0243.

## 3. O movimento sai duro, sem fluidez

**Medir.** O loop já ajusta a mola de cada movimento do original (zeta, omega, passa do ponto, tempo de assentar) e
diz qual usar. Com uma trilha tua (`medir.py`, `cursor.py`, `trilha_palavra.py`), ajuste por mínimos quadrados:

```js
// node: ajuste de mola numa trilha y[i] (um valor por quadro, do começo até assentar)
const ES = require("./estilo/estilo.js");
function ajusta(y, fps) {
  const y0 = y[0], y1 = y[y.length - 1]; let b = null;
  for (let z = 0.3; z <= 3; z += 0.02) for (let w = 3; w <= 70; w += 0.5) for (let u = 0; u <= 40; u += 2) {
    let e = 0;
    for (let i = 0; i < y.length; i++) e += (y0 + (y1 - y0) * ES.mola(i / fps, { zeta: z, omega: w, u0: u }) - y[i]) ** 2;
    if (!b || e < b[0]) b = [e, z, w, u];
  }
  return { rms: Math.sqrt(b[0] / y.length), zeta: +b[1].toFixed(2), omega: b[2], u0: b[3] };
}
```

No B3, o ícone do WhatsApp fechou com rms 0,9 px e a pílula com 2,6 a 4,4 px.

**Técnica.**
- `ES.mola(t, preset)` para um movimento, `ES.cadeia(t, [[t0, v0], [t1, v1, mola], ...])` quando um alvo novo chega
  antes do anterior assentar: a velocidade continua, sem tranco. Mola sem `u0` sai do repouso.
- **Nada para entre chaves** (Joi): o ícone entra 0,29 → 0,94 em 10 q a 60 qps, recua a 0,80 e cresce devagar até 1,0
  em 25 q. Overshoot pequeno (3 a 5 %) e assentamento longo (10 a 25 q a 60 qps).
- **Onde fica o overshoot.** VoiceOS: o container assenta sem passar (perde ~0,6 do que falta a cada 3 q a 60 qps); quem
  passa do ponto é o conteúdo (−10 px) e os ícones. Joi: botões e ícones passam 5 % do valor final. Satellite: balão
  (19 %), ilha (11 %) e o cartão que afunda 14 px e volta.
- **Assentamento longo** (0,9 a 1,3 s) só em lista, título e câmera.
- **Pan assimétrico** (VoiceOS): acelera em ~20 q e freia em ~25 q a 60 qps, com cauda longa; pico de −114 px/q. Zoom
  final quase linear: +0,02 de escala por quadro durante 50 q. Whip pan do Satellite: ease-in a partir do f181, pico
  de 111 px/q no f206, ease-out até −1043 px no f233.
- Perda por quadro no fim do caminho: 0,63 a 0,75 a 30 qps nos três primeiros clones. Fora disso, desconfie da medida.

## 4. O cartão estica como líquido

O original deforma (estica mais num lugar que no outro, cisalha o texto, a borda de um lado fica parada) e o clone
aplica uma escala só. No B3, a saída do cartão "Recent" (f45-50) é um esticão horizontal de até 2x que some, e o loop
acusava "y +66 px que o clone não faz".

**Medir.** Corte a peça em faixas horizontais e veja a largura de cada uma por quadro:

```sh
python3 clonar/scripts/medir.py original.mp4 44 52 naobranco --forma faixas --faixas 8 --regiao x0,y0,x1,y1
```

- todas as faixas crescem na mesma razão: é escala, com a origem onde a borda fica parada;
- o meio cresce mais que as pontas: barriga (deformação de verdade);
- as faixas andam em x de forma diferente: cisalhamento (o topo vai, a base fica);
- uma borda não muda entre quadros: é a âncora (a origem da transformação);
- meça também o conteúdo (texto, avatares) à parte: no B3 o conteúdo esticava menos que o corpo, e descia e girava.

Confira os cantos durante o esticão (`corner.py`): canto que continua redondo é largura animada (o `ES.caixa` faz);
canto que vira elipse é escala.

**Números medidos.**
- B3, "Recent": o corpo estica em x em torno da borda direita e o conteúdo estica menos, com descida e giro. Corpo e
  conteúdo separados passaram as peças P02 e P32 sem malha (rodada 08).
- Joi, menu escuro saindo (f270-286, 60 qps): estica na largura até passar da tela, mantém a altura em ~680 e só
  tomba no fim (rotateX 8° → 74° em f278-284). Título, checkbox, risco e cursor viajam presos a ele.
- VoiceOS, janela que "cai": na verdade desdobra. A borda de baixo fica parada em y 256 enquanto o topo sobe de 77 a
  −18 (f139-145). Movendo a janela inteira, ela cobria a pílula.
- Joi, bolha de vidro virando cartão: paredes laterais assimétricas (40 px à esquerda, 80 à direita em f326) que somem
  até f330, e a cor muda com o tamanho (receita 15).

**Técnica, do mais simples ao mais caro.**

1. Escala não uniforme com a origem na borda que fica, corpo e conteúdo em camadas separadas, cada um com a sua mola:

   ```js
   const sx = ES.cadeia(tc, [[T0, 1], [T0 + 0.05, 2.0, { zeta: 0.9, omega: 18, u0: 8 }]]);   // números do teu ajuste
   corpo.style.transformOrigin = "100% 50%";                                                    // a borda direita fica
   corpo.style.transform = `scaleX(${sx})`;
   conteudo.style.transformOrigin = "100% 50%";
   conteudo.style.transform = `translateY(${dy}px) rotate(${giro}deg) scaleX(${1 + (sx - 1) * 0.5})`;  // estica menos
   ```
   Cisalhamento: acrescente `skewX(k)` com k numa mola própria. Canto redondo no esticão: anime `width` (ou use o
   `ES.caixa`) em vez de `scaleX`.
2. Barriga ou deformação por faixa: desenhe o cartão parado uma vez num canvas à parte e copie em faixas, cada uma com
   a escala do perfil medido:

   ```js
   // src: canvas com o cartão em repouso (w x h). perfil(v) = escala x da faixa v (0 = topo, 1 = base).
   function liquido(src, x, y, w, h, perfil, desloca = () => 0, n = 24) {
     const fh = h / n;
     for (let i = 0; i < n; i++) {
       const v = (i + 0.5) / n, dw = w * perfil(v);
       ctx.drawImage(src, 0, i * fh, w, fh, x + w - dw + desloca(v), y + i * fh, dw, fh + 0.5); // +0,5 px tapa a costura
     }
   }
   // barriga: perfil = v => 1 + A * Math.sin(Math.PI * v); cisalhamento: desloca = v => C * (v - 0.5)
   // A e C saem de molas (ES.cadeia) ajustadas nas larguras das faixas medidas
   ```
3. Tombo 3D na saída: ajuste por pontos internos E pelas bordas ao mesmo tempo. Dois pontos internos aceitam uma
   família inteira de (escala, inclinação, centro); no Joi o ajuste só por título e botão virou tombo cedo e piorou
   f272-279 (0,0131 → 0,0148); com as bordas, 0,0091.

## 5. O morph parece crossfade ou passa por cinza

A regra está no `ESTILO.md` §5 e o `ES.caixa` já faz quase tudo. O que conferir quando reprova:

- **A cor nova cobre a velha como opacidade** sobre a cor-alvo, nunca `brightness()` nem crossfade. Satellite, ícone →
  cartão (f32-39): crossfade 0,0254, brightness 0,0205, mistura na fração medida 0,0165. As frações saem de 5 ou 6
  pontos fixos amostrados em cada quadro do morph (o canal G 120/63/39/26 deu 0,40/0,73/0,87/0,94). `ES.cadeiaCor` para
  cor que muda mais de uma vez.
- **Escurecer é rápido** (0,12 a 0,17 s), **clarear é lento** (rampa em S de 0,47 a 0,53 s, passando por cinza).
- **O raio chega antes da forma**: raio/menor lado 0,50 → 0,229 em 4 q (f31-35) com a mola `rapida`, enquanto a
  largura só assenta em f42.
- **Conteúdo escala ou a caixa vira máscara?** Meça uma feição de dentro durante o encolhimento. No cartão → tile do
  Satellite a caixa foi de 614 para 302 px e o destaque do arco ficou em y 516-555, só estreitando (197 → 27 px):
  `encaixe: "mascara"`.
- **Conteúdo velho sai em 0,08 s, o novo entra logo depois desfocado** (8 px → 0 em 0,25 s).
- **A altura pode atrasar** (Satellite cartão → tile: largura a 54 % quando a altura está a 36 %, f92). A caixa usa a
  mesma mola nos dois eixos; se o loop acusar, anime a altura com a mola medida dela por fora.
- **Atraso por elemento**: o texto do cartão do Satellite entra 0,23 s depois do arco.

## 6. A lista entra junta

**Medir.** Cada linha é uma peça. Ponha uma entrada por linha no `elementos.json` e rode
`trilha_palavra.py <original> elementos.json .apple-style-ui/medidas/trilhas.js`. Da trilha saem o nascimento de cada
linha (pela tinta baixa, receita 9) e o espaço entre linhas ao longo do tempo.

**Números medidos.**
- B3, lista do Files: linhas em escada de **1,5 q** (o valor da ficha). Com 1,3 q a tinta se concentrava no f33 e a
  "entrada" (50 % da massa máxima) andava 22 q para a frente. A escala do conteúdo começa em 0,67 no f29, tirada da
  largura medida de "Ae Editz", não das posições x. O título "Files" fica 7 % maior que a lista entre l36 e l59: mudar
  a curva do conteúdo inteiro quebrou seis peças, o pulso só no título resolveu. Avatares em escada de 2 q com a mola
  elástica.
- Satellite, pílulas: uma a cada 170 a 200 ms (f127, f132, f138, f144, f150), entrando por cima e empurrando a pilha.
  A pílula nova nasce branca, apagada e desfocada; ícone e texto chegam verdes e o texto vira #1d1d1f ~6 q depois.
- Joi, lista de tarefas: as linhas nascem juntas e se afastam (linha 2 − linha 1: 85 px em f140 → 160 px em f165, a
  60 qps); as palavras entram uma a uma a cada 33 a 50 ms e o espaço entre palavras fecha (linha 1: 315 → 259 px).
- `ES.PASSO`: palavra 40 ms, botão 33 ms, item de lista 180 ms, letra 100 ms.

**Técnica.** Uma entrada e uma mola por linha, com o começo em escada, e o espaço entre linhas como mola à parte:

```js
LINHAS.forEach((txt, i) => {
  const t0 = T_LISTA + ES.escalona(i, 1.5 / FPS);           // escada medida (aqui 1,5 q)
  if (tc < t0) return;
  const e = ES.entrada("baixo", tc - t0, { altura: 40 });
  const gap = G0 + (G1 - G0) * ES.mola(tc - T_ABRE, { zeta: 0.65, omega: 17.2 }); // espaço entre linhas (B3: 41 → 47 px)
  desenhaLinha(txt, X, Y0 + i * gap + e.dy, e);
});
```

Nunca um transform só na lista inteira: o original reorganiza as linhas de forma desigual enquanto o cartão cresce
(B3, P12, P15, P16, P43, P48).

**Armadilha do medidor.** O escalonamento compara o f50 da massa de tinta com o da peça vizinha. Um pico de tinta no
fim da janela da peça (texto ficando mais nítido, outra linha entrando) atrasa esse f50 sem mudar nada visível na
entrada. Olhe a folha (`sheet.py`) antes de mexer no tempo.

## 7. Texto pequeno com peso ou desenho errado

O SF Pro muda o desenho com o tamanho (eixo `opsz`; no SFNS, opsz = px): em tamanho pequeno a letra é mais larga e mais
aberta. Medir ou desenhar a 100 px e escalar põe a letra de título num texto de 15 px. No B3, medir a 100 px e escalar
errou o texto pequeno. Medido no navegador (Chrome, SFNS do sistema): "Get Info" peso 500 a 15 px tem a tinta **12,8 %
mais larga** que a mesma frase a 100 px reduzida; no DOM, 57,4 px contra 50,5.

**Técnica.**
- **Canvas:** `encaixa(txt, fonte, q, { real: true })` (modelo do clone) refaz a medida e o desenho no tamanho final,
  arredondado em meio px. Use em texto até ~60 px.
- **DOM:** `font-size` no tamanho final e escala só perto de 1 (entradas 0,45 → 1). Se a peça precisa ser escalada de
  verdade, trave o desenho no tamanho em que ela aparece: `font-variation-settings: "opsz" 15` com `font-size: 100px` e
  `scale(0.15)` dá exatamente a largura do texto a 15 px (382,5 px a 100 px contra 57,4 x 100/15).
- **Tamanho pela largura**, nunca pela altura: `ES.tamanhoPorLargura(texto, largura, {peso})` itera porque o opsz muda
  com o tamanho. Só depois de `document.fonts.load`.

## 8. Texto com peso, largura ou espaçamento errados

**Medir.** A mesma palavra, no mesmo tamanho, no original e no clone: quantidade de tinta (peso) e extensão (largura).
`inkspan.py ref.png clone.png nome:x0,y0,x1,y1` para texto escuro, `inkspan_light.py` para texto claro ou colorido.
Quadros só de `ffmpeg -vf select=eq(n\,f)`, nunca de snapshot (saiu um quadro adiantado no Satellite).

**Técnica e números.**
- **Peso pela tinta.** Satellite, título: 10546 px escuros a 500, 12928 a 590, 11832 no original: 550 com −1,5 px de
  espaço. `ES.PESOS` traz o peso por função (título 600, lista 620, botão 590, frase 450, número 900, tecla 700).
- **Peso por grupo.** O mesmo editor usa pesos diferentes: salão, legenda 720 e cartão 590; final output, sem-serifa
  470 (500 dava 7 % de tinta a mais) e caixa alta 760 (700 dava 10 % a menos).
- **Tamanho pela largura de tinta**, com os eixos da fonte: VoiceOS, "I got a lot work to do" deu 93 px pela altura e
  86 px pela largura (8 a 12 % de erro); com a fonte grande o ditado parecia atrasado.
- **Espaço entre letras pela proporção da caixa**: `encaixa(..., { largura: true })`. A fonte do original quase nunca
  tem o mesmo espaçamento (salão 0,060 → 0,053).
- **Serifa de destaque** (final output): Instrument Serif Itálico, espaço −7 e negrito falso de 1,3 px (na fonte de
  100), medidos contra o original em 7 palavras. Fonte candidata se escolhe desenhando cada uma na caixa medida e
  comparando o erro por palavra, não no olho (o olho pediu "mais condensada"; a medida mostrou o original 13 % mais
  largo).
- **Fonte carregada antes de medir**: canvas não dispara a @font-face sozinho. `document.fonts.load()` e só guarde a
  medida com `document.fonts.check()` verdadeiro (a 1ª prévia do final output saiu 22 % menor).
- **Meça a ferramenta antes de confiar nela.** No B3 um script de caixa dilatava 4 px e o título saía grande e pesado.

## 9. Texto desalinhado ou pulando

- **Linha de base, não topo da tinta.** No Joi, o "a" de "Plan a day" subia porque cada palavra era alinhada pelo topo
  da tinta. Texto montado por regra (molde, legenda) se alinha pela linha de base; `tinta()` dá o deslocamento (`t`) da
  tinta em relação à linha de base.
- **Encolher em torno do começo de uma palavra**, não do centro: Joi, "Get your subscription" encolhe em torno de x 317
  (início de "your"): 667 → 471 → 397 → 353 px em f314-330.
- **Texto "parado" que escorrega.** Final output: toda palavra anda 11 a 15 px para a esquerda em ~20 q; a caixa pela
  mediana errava ~10 px.
- **Nascimento pela tinta baixa** (10 %), não pela alta: com 30 %, "now" nascia no f185 e era f181. A palavra pode
  nascer inteira a ~85 % e clarear em 14 q.
- **Caixa de palavra com haste** (t, f, h, d, l) **ou perna** (g, y): estenda a região só para o lado da haste e tire
  as vizinhas da conta, senão a caixa sai cortada.
- **Peça que ganha "pai"** no meio (título que passa a viajar com o cartão): projete pelo mesmo transform do pai a
  partir de um quadro de âncora, em vez de trilha própria. Joi, f266 em diante: o trecho foi de 0,027 para 0,009.
- **Tempo da fala.** O whisper dá o início da palavra ~0,067 s depois do nascimento medido (erro médio 0,12 s); em voz
  sintética errou frases inteiras em até 0,58 s, e o alinhamento pelos trechos de fala (`silencedetect`) corrigiu.

## 10. O cursor está no lugar errado

O que o olho confere é a **ponta** (o ponto que clica), e a caixa de tinta de um cursor borrado ou girado anda longe
dela. No B3 o cursor do clone parou em cima do "Get Info"; no original a mão aponta de baixo para o ⓘ.

**Medir.**

```sh
python3 clonar/scripts/cursor.py original.mp4 86 100 x0,y0,x1,y1 .apple-style-ui/medidas/cursor.json
# mão ou cursor próprio: renderize o cursor DO CLONE num PNG transparente e diga onde fica a ponta
python3 clonar/scripts/cursor.py original.mp4 86 100 x0,y0,x1,y1 cursor.json --modelo mao.png --ponta 38,11 --escalas 0.9,1,1.1 --angulos -20:20:10
```

Sai `{quadro: [x, y, escala, ângulo, ncc]}` da ponta. ncc abaixo de ~0,5 é cursor borrado, escondido ou modelo
errado: confira esses quadros na folha. Casando no gradiente, seta preta de contorno branco e seta branca de contorno
escuro dão o mesmo resultado. Ajuste a mola do caminho da ponta (receita 3) em x e y.

**Números medidos.**
- Satellite: seta sobe de (662, 809) no f157 a (658, 624) no f172 com ease-out; vira mão no f173; aperta em f181-187
  (escala ≈ 0,7) e o item clicado fica verde em f182-189. A seta do clone tinha de ser 1,32x a do primeiro chute.
- Joi: seta macOS **branca de contorno escuro o tempo todo** (no fundo branco ela parecia escura só por causa do
  borrão), entra pela direita deitada (−60°) em f193-200, e a da referência é ~1,3x a do clone. De f266 em diante viaja
  presa ao cartão (receita 9, "pai").
- VoiceOS: a seta gira na direção do caminho e muda de escala (`cursor.py` mede os dois); clique em f114-121.

**Técnica.** Desenhe o cursor com a ponta na origem: posição, giro e escala acontecem em volta dela.

```js
// seta macOS na mesma régua do cursor.py (escala 1 = 24x34; ponta em 0,0)
const cursor = el(`<svg width="24" height="34" viewBox="0 0 24 34" style="overflow:visible">
  <path d="M0 0 L0 24.5 L6 19 L10 29 L14.2 27.2 L10.2 17.5 L18.5 17.5 Z" fill="#000" stroke="#fff"
        stroke-width="1.6" stroke-linejoin="round"/></svg>`);
cursor.style.transformOrigin = "0 0";
const x = ES.cadeia(tc, [[T0, X0], [T1, X1, { zeta: 1, omega: 14 }]]), y = ES.cadeia(tc, [[T0, Y0], [T1, Y1, { zeta: 1, omega: 14 }]]);
const aperta = ES.cadeia(tc, [[T0, 1], [T_CLIQUE, 0.7, "rapida"], [T_CLIQUE + 0.1, 1, "suave"]]);
cursor.style.transform = `translate(${x}px, ${y}px) rotate(${ANG}deg) scale(${ESCALA * aperta})`;
```

Seta ou mão: a troca é seca, no quadro medido, pelo `Fi`.

## 11. Memoji, avatar ou emoji vira mancha

No B2 o memoji saiu com SSIM 0,45 (o limite é 0,5); no B3 os avatares viraram manchas coloridas no f50.

**Técnica, por ordem de preferência.**
1. **O avatar é da pessoa** (o memoji dela, a foto dela): é o asset dela, entra como `foto` no `hf/assets/RECORTES.md`.
2. **Recriar em SVG ou CSS** com as cores medidas: disco de fundo, rosto, cabelo, roupa e o acessório que dá a leitura
   (o fone do memoji do Satellite foi desenhado em CSS). Meça as cores em quadros ampliados (`sheet.py` com recorte);
   o SSIM pede a silhueta e as massas de cor, não o detalhe.
3. **Emoji do sistema** (`EMO(px)` no modelo) encaixado na caixa medida e **calibrado contra o próprio render**: a mesma
   medida (tinta saturada) no original e no clone, escala pela raiz da razão de tinta, ângulo pela proporção da caixa.
   Legenda: bicicleta 1,8x/−35° → tinta 16311 contra 15462; 1,72x/−25° fechou f200-219 em 0,0307. O espelhamento a caixa
   não vê: olhe (o 🚴 do original estava espelhado).

Emoji da Apple e memoji são material de terceiros: valem para estudo neste Mac, nunca no molde publicado (os moldes
usam as peças livres de `moldes/pecas_livres.py`). Entrada de avatar: escada de 2 q com a mola elástica (B3).

## 12. A entrada parece seca

A peça nasce nítida e inteira, e no original ela nasce desfocada, apagada ou deslizando.

**Medir.** `aparicao.py` mede opacidade, deslocamento, escala e desfoque por quadro de cada peça contra a placa (ou o
fundo), com as vizinhas fora da conta.

**Números medidos** (o `ES.entrada` traz os padrões; troque pelos medidos):
- desfoque de entrada 8 a 24 px → 0 em 0,1 a 0,3 s; opacidade em 0,05 a 0,1 s; cor de destaque vira tinta entre 0,10
  e 0,25 s;
- Joi, "Get your subscription": cai 132 px (1,6x a altura da letra) em 6 q a 60 qps, desfoque 10 → 3 em 6 q e → 0 em
  10 q, vermelho → #171617 começando 5 q depois;
- salão, palavra da legenda: em 5 q sobe de 15 px abaixo, cresce de 0,85 a 1 e vai de 25 % a 100 % (25, 52, 75, 92,
  99 %), sem desfoque. Saída do grupo: só opacidade, em 4 a 5 q (98, 95, 86, 76, 58 % e some);
- final output: nasce inteira a ~85 %, vindo 9 a 12 px da direita, clareia até 100 % em ~14 q e escorrega até parar em
  ~20 q, sem desfoque nem escala;
- legenda (4º clone): o original nasce desfocado (YOO, apart, when, bike); o clone ficou nítido porque o raio não foi
  medido. Meça o desfoque também.

```js
const e = ES.entrada("cima", tc - T_PALAVRA, { altura: 82, blur: 10, tBlur: 0.17 });
el.style.transform = `translate(${e.dx}px, ${e.dy}px) scale(${e.s})`;
el.style.filter = ES.blurf(e.blur); el.style.opacity = e.op;
el.style.color = ES.rgb(ES.mixc(ES.hex(DESTAQUE), ES.hex(TINTA), e.tinta));
```

## 13. A peça parada parece morta

O que parece parado no original quase sempre anda. Amostre um perfil de cor horizontal da peça ao longo do tempo
(`medir.py ... --forma faixas`, `fundo.py`) e o ângulo de ponteiros (`medir.py ... --forma momentos`) antes de congelar.

- Satellite, Dynamic Island: um brilho varre da esquerda para a direita (centro a 20 % → 56 % → 92 % da largura em
  f224/232/240, #252525 sobre #080808) e o ponteiro do timer gira (−61° no f220 → 0° no f234 → 46° no f272). O clone
  com a ilha parada: f216-223 de 0,0207 para 0,0143 depois de animar.
- VoiceOS: o conteúdo treme dentro da janela parada (+27 → −10 → 0 px em f146-200); meça o conteúdo contra o próprio
  container (NCC do avatar), não contra a tela.
- Joi: o ícone "respira", crescendo devagar de 0,80 a 1,0 em 25 q.
- B3: a grade já aparece borrada no quadro 1; o clone começava invisível e o ajuste de mola não achava o movimento.

## 14. A parte de trás sai nítida demais

**Medir.** Para cada item abaixo da zona nítida: tinta mínima (o quão escuro fica o texto) e gradiente máximo de borda.

Satellite, lista: pílulas abaixo de y ≈ 760 desfocam aos poucos (Crime ~1,5 px, Lost ~3 px no f192). Original em y 837:
tinta mínima 86, borda 85; em y 975: 137 e 17. O clone, antes do modelo: 22/110 e 65/45. Com desfoque e névoa
ajustados por y, f160-175 foi de 0,0261/0,0248 para 0,0205/0,0177.

```js
// profundidade por y: [y, desfoque px, névoa 0..1 em direção ao fundo]; os números aqui são de exemplo
const DOF = [[760, 0, 0], [837, 1.5, 0.2], [975, 3, 0.45]];
const dof = (y) => [1, 2].map((k) => ES.kf(y, DOF.map((p) => [p[0], p[k]]), ES.E.lin));
const [b, nevoa] = dof(yItem);
item.style.filter = ES.blurf(b);
item.style.color = ES.rgb(ES.mixc(ES.hex(TINTA), ES.hex(FUNDO), nevoa));
```

No morph, o desfoque de profundidade segue a velocidade da forma (picos de 7,5 / 3 / 6 px no Satellite); o
`ES.caixa` já faz.

## 15. Cor ou nível errados

- **Cor só de quadro numerado** (`select=eq(n\,f)`), nunca de grade com rótulo (deslocou 20 px no Joi) nem de snapshot.
- **Nível do encode**: o HyperFrames sai ~0,8 % escuro. O ganho 1,008 só no luma já vem no `round_mb.sh` (Satellite,
  quadros parados: 0,0100 → 0,0062). Ganho no croma piorou os verdes claros (0,0097 → 0,0109). Vídeo baixado do
  Instagram tem escuros 2 níveis acima: `LUMA_INSTAGRAM=1` (Joi: Y 27 contra 29 num trecho escuro de 66 q custava
  ~0,008 por quadro). Calibre nos dois extremos e no meio, com o Y cru dos fundos lisos.
- **Branco que não chega**: no B3 o #fdfdfd saía #fcfcfc; para bater 253 no vídeo foi preciso pintar 254. Corrija a
  cor pintada pela diferença medida no render, não a curva toda.
- **Fundo é campo medido**, não gradiente de CSS: `fundo.py` dá o campo de baixa frequência por quadro (brilho,
  vinheta, clarão). Na legenda, os trechos só de fundo ficaram em 0,005 a 0,010 desde a 1ª rodada.
- **Clarões por quadro** (B3): o peso de cada clarão de cor medido do canto do painel, com a forma da subida e da
  descida (seno ou linear) e onde ele corta seco.
- **Vidro muda de cor com o tamanho** (Joi): bolha pequena é mais saturada (#9ebbf9 no f318 → #b9d1fc → #cadbfc ao
  esticar → #6496fa quando vira cartão), com aro saturado de ~14 px na tela em qualquer escala.
- O ΔE do loop só pega cor trocada (limite 46). Erro fino de cor aparece no `fdsum.py` por trecho e no `diffview.py`.

## 16. Sombra e brilho

- **Sombra quase não existe** nos três primeiros clones: a profundidade vem de aro fino e brilho colorido
  (`ES.SOMBRA`: `pilula`, `flutuante`, `tecla`, `aroEscuro`, `aroClaro`, `aroVidro`; `ES.brilho(cor, raio, alfa)`).
- **Brilho é camada à parte.** Joi: objeto recortado com o brilho embutido carregava um disco cinza; separar o recorte
  (alfa pela luminância acima da borda do próprio recorte) do brilho (halo por objeto de +10 a +20 níveis e campo largo
  de +3) levou f216-247 de ~0,017 para ~0,008. Para recorte permitido (foto, produto):

  ```python
  # numpy: A = recorte RGB (float), bg = mediana da borda de 4 px do recorte
  a = np.clip((A.mean(2) - bg.mean() - 5) / 38, 0, 1) ** 0.8          # alfa: luminância acima da borda
  c = np.clip((A - (1 - a[..., None]) * bg) / np.maximum(a[..., None], 1e-3), 0, 255)  # cor sem o fundo
  ```
- **Halo que um objeto joga no outro**: Satellite, o cartão joga azul no oceano (medido a 30, 90 e 170 px fora,
  f86-98). Brilho atrás do cartão no cartão → tile com desfoque de 50 px e pico de 0,75.
- **Sombra de texto** (final output): existe (−8 a −20 níveis a 4 px da letra: σ ~4 px, 60 %), mas ligada derrubou a
  correlação na máscara. Teste como uma hipótese só e decida pelos blocos.

## 17. O tempo não bate

- **Batida, só se existir.** O raio-x diz se os eventos caem na colcheia. Joi: 4 de 6 eventos grandes numa colcheia de
  136,9 BPM. Satellite e VoiceOS não seguem a batida (o VoiceOS segue a fala). `ES.grade` e `ES.encaixa`; no molde, a
  entrada de cada momento anda na velocidade original e só o meio estica ou encolhe.
- **Mapa de tempo por painel** (B3): o reel tinha dois painéis com relógios próprios; a 2ª volta do direito é a 1ª
  atrasada 132 q exatos e a do esquerdo 141,5 q. Achado por correspondência de quadros (erro mínimo por deslocamento
  fracionário), cortou o trabalho pela metade: `l = Fi >= 142 ? F - 141.5 : F`. Mapa de tempo é permitido pelo loop.
- **Energia de movimento por janela e por região** mostra onde o tempo diverge: no B3, janelas de 12 q por painel
  acharam um clarão que corta seco no f85, um rosa que salta no f96 e um botão que já anda no f88 (correlação 0,932 →
  0,947). Para o trecho que ainda difere, janelas de 6 q.
- **Leitura de faixa de vídeo**: `format=gray` antes do `crop`. Em yuv420 um crop de 67 linhas sai com 66 e o atraso
  medido derivava de −0,08 para −0,23 s em 10 s.
- **Fala**: receita 9 (o whisper atrasa ~0,067 s; alinhe por trechos de fala).

## 18. Digitação e ditado

VoiceOS: o texto entra em blocos de 2 a 6 caracteres por quadro, com os ~90 px mais novos ainda clareando. Primeiro
aparece colorido (roxo, azul, rosa) e só escurece 10 a 30 q depois, atrás de uma cunha: a troca para a tinta é um
degradê de ~160 px passando por azul-marinho, não uma troca seca (com a troca seca, "start" ficou meio azul no f551,
onde o original já estava quase preto).

```js
// g: canvas só do texto (OffscreenCanvas), copiado para o quadro no fim; cpq = caracteres por quadro medidos
function digitado(g, txt, x0, yb, F, F0, cpq, atraso, COR, MARINHO, TINTA) {
  const n = Math.max(0, Math.min(txt.length, Math.floor((F - F0) * cpq)));
  const s = txt.slice(0, n), xh = x0 + g.measureText(s).width;                          // cabeça
  const xw = x0 + g.measureText(txt.slice(0, Math.max(0, Math.floor((F - F0 - atraso) * cpq)))).width; // cunha
  const gr = g.createLinearGradient(xw - 80, 0, xw + 80, 0);
  gr.addColorStop(0, TINTA); gr.addColorStop(0.5, MARINHO); gr.addColorStop(1, COR);
  g.fillStyle = gr; g.fillText(s, x0, yb);
  const fade = g.createLinearGradient(xh - 90, 0, xh, 0);                               // os ~90 px mais novos
  fade.addColorStop(0, "rgba(0,0,0,0)"); fade.addColorStop(1, "rgba(0,0,0,0.8)");
  g.globalCompositeOperation = "destination-out"; g.fillStyle = fade; g.fillRect(xh - 90, yb - 300, 90, 400);
  g.globalCompositeOperation = "source-over";
}
```

A ponta direita da tinta colorida e da tinta escura por linha, quadro a quadro, dá `cpq` e `atraso`
(`medir.py ... vermelho|azul|saturado` e `escuro` na faixa da linha).

## 19. Palavra em destaque

- **Caixa de destaque com mola** (salão, 25 qps): cresce da esquerda (x e centro vertical fixos) com escala 0,45 (30 %,
  desfoque 8), 0,72, 0,99, 1,07, 1,11, 1,11, 1,09, 1,02, 0,99, 0,98, 0,97, 0,97, 0,99, 1,00. O texto vai junto. Ajuste
  por mínimos quadrados: `{ zeta: 0.51, omega: 16.25, u0: 13 }` (rms 0,014 na escala). No clone, essa mola levou a
  correlação na máscara de 0,81 para 0,91. Antes ela tinha sido descartada como "ruído": ruído que se repete quadro a
  quadro pode ser o movimento.
- **Placa sem a camada antiga**: a pegada cobre a passada do ponto da mola (o "S," da caixa a 1,11 vazava pela placa).
- **Destaque em serifa** (final output, molde `moldes/fala-destaque/`): três linhas por frase (pequenas em cima, a
  palavra grande no meio, o resto embaixo à direita), entrada da receita 12, serifa da receita 8. A palavra sai do
  `clonar/scripts/destaque.py` (a mais longa fora das palavras vazias).

## 20. Saída e troca de cena

- **Saída acelera, nunca freia**: Satellite f259-276, sobe 134 px acelerando 1,25x por quadro a 30 qps, desfoque 0 → 9 px
  a partir de 41 % do tempo, opacidade 1 → 0,7 → 0 nos últimos 29 %. `ES.saida(tipo, t, o)`. A direção muda por criador
  (Satellite sobe, Joi e VoiceOS deixam cair). B3: "tudo sai acelerando para baixo (137 px)".
- **Corte quase nunca**: o Satellite é um plano só (os dois "cortes" do raio-x são morphs). Troca de cena é a caixa que
  se transforma (receita 5).
- **Transição por dentro de uma forma** (VoiceOS, céu → vinhedo): a placa nova aparece primeiro DENTRO das nuvens da
  velha. Máscara de "nuvem" (pouca saturação, muito valor) da própria placa que sai, com a força ajustada por quadro por
  mínimos quadrados em cima do alfa global (0,07 no f65 → 0,6 no f71): resíduo de 10-14 níveis para 7-8.
- **Transição com o quadro inteiro borrando** (final output): desfoque por palavra σ 1,5 → 9 em 4 q.
- **Tombo 3D**: receita 4, item 3.

## 21. Câmera e fundo

- **Cena esparsa** (texto sobre branco): ECC só de translação ou similaridade, ou o template de uma palavra única com
  busca de escala (NCC > 0,98). O ECC afim jogou +60 px de y falsos no VoiceOS (f516-540).
- **Conteúdo periódico** (linhas de texto, listas, grades) num scroll rápido: o registro escorrega um período (VoiceOS
  travou em −51 px/q, o espaço das linhas). Registre pela assinatura "ponta direita da tinta por linha", que não se
  repete (deu −321 px, conferido com casamento direto f411 → f418).
- **Câmera encadeada acumula erro**: `registra_cam.py` registra cada quadro direto contra a placa (legenda: até 17 px;
  f160-179 de 0,0258 para 0,0206).
- **Mapa que dá zoom se redesenha**: placa larga mais placas curtas com alfa (`placa.py --janela`).
- **NaN no `warpAffine`**: o `borderValue` tem de ter os 3 canais (com `np.nan` só o R virava NaN e a borda saiu
  vermelha).
- **Ver o que anda sozinho**: leve cada quadro para as coordenadas de mundo (a câmera desfeita); o que ainda se mexe é
  entrada de interface, digitação ou cursor, e pode ser medido sem a câmera.

## 22. Som, render e encode

- **Som por elemento**: `sons/SONS.md` (pacote livre, `sons.json` por molde). Padrão: `"marcado"` em vídeo sem fala,
  `"suave"` com fala. No Joi nenhum efeito foi preciso: cada evento já caía numa nota da trilha.
- **Render**: `--workers 1` (com mais, ele grava todos os quadros em disco antes de codificar); 240 qps, `tmix` de N e o
  `MB_SHIFT` do `mb.js` centrando os subquadros; para com menos de 2 GB livres.
- **Encode**: H.264 com `-refs 4 -level:v 5.1` (sem nível fixo, um lado a lado de 3840x1080 subiu para 6.0 e o QuickTime
  embaralhou os blocos). Nunca `-shortest` quando o vídeo é o mais longo: cortou 4 quadros no Satellite e desalinhou
  toda comparação depois deles.

## 23. Vídeo dentro de uma tela

Referência demonstrativa (o vídeo editado dentro de um cartão, de um celular, de uma tela): tire o vídeo de dentro
antes de qualquer medida, com `clonar/scripts/extrair_tela.py` (o `caso.py referencia` já roda). O que fez diferença:
achar a tela pelo desvio de cada pixel no tempo, não pela borda do quadro (328,52 contra 328,5 de verdade); miolo pela
distância à borda com o corte de Otsu; a cada quadro o degrau mais perto da posição prevista (posição + velocidade), não
o mais forte; nada de ECC na faixa da borda quando o conteúdo de dentro anda (derivou 24 px num cartão parado).

## 24. Quando a medida engana

- **O fundo do medidor é a mediana da cena**: mexer num trecho muda a máscara de outros trechos e até do outro painel
  (B3, P32 reprovou depois de uma mudança só no outro painel). Escreva `pecas.json` com as peças da FICHA para o
  medidor não achar "peça" no fundo liso (B3, P25).
- **Trilha com caixa a mais**: antes de usar uma trilha, confira se a contagem e a cor das caixas batem. No Joi a
  estrela entrava como 4ª palavra e o ramo de reserva desenhava "your" gigante; filtro por cor (B−R da estrela ~63)
  resolveu, filtro por posição quebrou outro trecho.
- **Posição só de medida numérica**: ler posição a olho numa grade com rótulo errou 20 px e custou uma rodada (Joi v4).
- **Placa de vídeo**: a nota do quadro inteiro não vale (a pessoa é o próprio original); vale a da máscara, com o "sem
  camada" ao lado (`rodada --mascara --placa`).
- **Média empatada esconde troca**: no VoiceOS v2 duas mudanças pioraram os seus blocos, três melhoraram e a média
  ficou igual. Julgue pelos blocos do `fdsum.py --prev` e pelo `diffview.py`, não pela média.
