# Sons por elemento

"O mais pika desse estilo é o som: cada elemento que aparece tem som." Esta pasta é o pacote de sons do motor, e os
três moldes de interface (Satellite, Joi e VoiceOS) sabem usar.

## Como funciona

- **Pacote** (`sons/`): 20 sons curtos de interface, todos CC0 (origem e licença em `CREDITOS.md`), mono, 48 kHz,
  sem silêncio na frente e atrás, todos com a mesma loudness (-18 LUFS na janela de 100 ms, teto de -1 dBFS).
  `sons.json` guarda de cada som o tipo, a duração e o **ataque** (o instante do pico de energia dentro do arquivo).
  `fazer_pacote.py` refaz o pacote igual, byte a byte.
- **Mapa** (`moldes/<molde>/molde/sons.json`): a lista de eventos do molde, cada um com o quadro do pico do movimento
  no clone (no fps do molde: Satellite a 30, Joi e VoiceOS a 60), o tipo de som, o nível (`suave` ou `marcado`) e a
  entrada com mola que ele segue (só o Satellite tem mola firme).
- **Duas variáveis** no `index.html` do molde:
  - `sons`: `nenhum` (padrão), `suave` (só os eventos principais, 4 dB mais baixo) ou `marcado` (todo evento);
  - `musica_volume`: de 0 a 1, o volume da música quando há sons (padrão 0,7, uns 3 dB abaixo; no VoiceOS, 1, porque a
    trilha original tem locução). Com `nenhum` ela não é usada.
- **O montar.py** lê o mapa, põe o **ataque** de cada som em cima do quadro do evento (com precisão de amostra,
  inclusive em quadro fracionado), soma tudo à música com o volume pedido e passa num limitador em -1 dBFS (com
  compensação de atraso, para nada sair do lugar). Ele acompanha as outras variáveis:
  - `mola: firme` adianta o evento que está dentro de uma entrada (`b + 0,6 (f - b)`), como o `index.html`;
  - `ritmo: batidas` leva o evento para o quadro novo da saída (a mesma tabela do ritmo);
  - `ilha_texto` com mais palavras dá mais toques de tecla (um por palavra, com o passo desigual do `ritmo` do mapa).
- **Três cuidados ouvidos no Satellite (30/10), em todo molde:**
  - **teclas:** cada `digitar` muda um pouco de ganho e de altura (`TECLAS` no montar.py: 0, -2, -1, -3 e -1,5 dB, com
    velocidade 1, 1,06, 0,94, 1,03 e 0,97), além do rodízio entre os dois arquivos;
  - **golpes:** o montador acha os golpes da música (fluxo espectral menos a média local, corte em 3 vezes o percentil
    90) e o efeito que cai a até 40 ms de um golpe desce 6 dB (`BATIDA_DB`), para não somar com ele;
  - **volume:** com música de verdade, o final vai para -14,1 LUFS (`LUFS_ALVO`, a loudness integrada dos três
    originais, medida com o ebur128), em até 3 voltas de medir e corrigir depois do limitador. Com o silêncio do molde
    (o padrão no repositório), os efeitos ficam no nível deles: normalizar efeito sozinho a -14 LUFS deixaria cada pop
    alto como uma música inteira.
- **Sem repetir:** cada tipo roda entre as suas versões (aparecer 1, 2, 3, 1, ...), então o mesmo arquivo nunca toca
  em dois eventos seguidos. O autoteste do `montar.py` confere isso.
- **Padrão intacto:** com `sons: nenhum` nenhuma linha nova roda e a música segue copiada. A prévia de
  `versoes/original.json` do Satellite continua com o mesmo md5 (`61e3157750b0c70b88d0154dd33eabdf` com o silêncio do
  repositório; era `877170713ecc12ba4889e671dc0250f5` com o áudio do original), e o Joi e o VoiceOS com os padrões
  continuam passando na régua do portão (`aprendizado/testes/testes.sh`, caso 1).
- **No Studio** os dois campos aparecem, mas o som só entra pelo `montar.py` (como a música trocada e o ritmo).

```
python3 montar.py versoes/junior-suave.json      # junior com sons suaves
python3 montar.py versoes/junior-marcado.json    # junior com todo evento marcado
```

O `montar.py` grava a lista de eventos com o som escolhido em `<pasta de trabalho>/sons-eventos.json` e no log.

## Os sons

| nome | tipo | o que é | duração | ataque |
|---|---|---|---|---|
| aparecer-1 | aparecer | pop suave, gota que sobe | 188 ms | 5 ms |
| aparecer-2 | aparecer | pop suave, gota mais grave | 188 ms | 5 ms |
| aparecer-3 | aparecer | pop com cauda que sobe | 224 ms | 6 ms |
| clicar-1 | clicar | clique do cursor, com corpo curto | 94 ms | 6 ms |
| tocar-1 | tocar | toque curto e seco | 20 ms | 5 ms |
| tocar-2 | tocar | toque de seleção | 40 ms | 5 ms |
| digitar-1 | digitar | tecla, grave | 12 ms | 5 ms |
| digitar-2 | digitar | tecla, aguda | 7 ms | 4 ms |
| numero-1 | numero | catraca de número rolando | 200 ms | 100 ms |
| numero-2 | numero | catraca dupla de número rolando | 200 ms | 102 ms |
| brilho-1 | brilho | seis toques agudos espalhados | 598 ms | 8 ms |
| brilho-2 | brilho | cinco toques agudos, mais graves | 547 ms | 8 ms |
| entrar-1 | entrar | whoosh que sobe e corta no pico | 326 ms | 228 ms |
| entrar-2 | entrar | whoosh que sobe, mais curto e grave | 272 ms | 176 ms |
| sair-1 | sair | whoosh que desce | 310 ms | 42 ms |
| sair-2 | sair | whoosh que desce, mais curto (o Satellite não usa; fica para os outros moldes) | 247 ms | 33 ms |
| morph-1 | morph | ar que cresce e assenta num baque grave | 378 ms | 187 ms |
| morph-2 | morph | ar que cresce, mais curto e claro | 324 ms | 153 ms |
| ilha-1 | ilha | "bloop" grave que abre, com sopro | 700 ms | 9 ms |
| sucesso-1 | sucesso | duas notas que sobem (dó, sol) | 1200 ms | 8 ms |

Ganho de cada tipo na mixagem (em `sons.json`, `tipos`; vem do `fazer_pacote.py`): numero +2, clicar 0, entrar -2,
morph -2, ilha -2, sucesso -2, aparecer -3, tocar -3, brilho -3, sair -3, digitar -5 dB. O `suave` soma mais -4 dB.
Com isso, na versão junior, todo efeito do `marcado` fica de -5 a +2,6 dB em volta do nível típico da música (a
0,7), e no `suave` de -4,3 a -2,1 dB abaixo dele.

## Os eventos do Satellite

Quadro do clone a 30 fps (S = toca no suave e no marcado; M = só no marcado).

| quadro | som | nível | evento |
|---|---|---|---|
| 7 | aparecer | S | ícone entra |
| 13,5 | tocar | M | rótulo do ícone aparece |
| 33 | morph | S | ícone vira o cartão |
| 39,5 | digitar | M | texto do cartão aparece |
| 72 | brilho | S | satélite aparece no arco |
| 92 | morph | M | cartão encolhe e vira o tile |
| 97 | sucesso | S | tile conectado (a barra acende) |
| 122 | morph | M | tile vira a pílula cinza |
| 128, 132,5, 138,5, 144,5, 150,5 | aparecer | S | as cinco pílulas (caem nos golpes da trilha original) |
| 156 | entrar | S | título pousa, palavra a palavra |
| 158,5 | tocar | M | botão do canto assenta |
| 163, 169,5, 171,5 | aparecer | M | os três emojis de alerta |
| 181 | clicar | S | cursor clica no item 1 |
| 199 | entrar | S | câmera corre e a rota começa |
| 206 | entrar | M | ponto azul voa para a ilha |
| 216,5 | ilha | S | ilha abre |
| 217,8 + 2,6 por palavra (vezes 1; 1,3; 0,8; 1,15) | digitar | M | texto da ilha, palavra a palavra |
| 241,75 e 258,75 | numero | S | relógio vira (meio do rolamento) |
| 274,5 | sair | S | cena sobe e sai |
| 278,5 | aparecer | S | balão entra |
| 283 | brilho | M | brilho passa no balão |

O título não ganha um toque por palavra: no clone as palavras pousam todas em 53 ms (atraso de 0 a 1,6 quadro), e
toques tão juntos viram um só. Ele ganha um whoosh no pouso.

Saíram em 30/10 (satellite-v3, ouvido pelo Júnior): o whoosh do quadro 4 e o brilho do quadro 10 (a abertura do
marcado tinha 4 efeitos em 0,33 s, agora tem 2 no primeiro meio segundo) e o "relógio entra" do quadro 225 (embolava
com a última tecla).

## Medidas (versão junior, finais com motion blur, satellite-v2: antes dos ajustes de 30/10)

| | suave | marcado | creatoroly (medido no PLANO, seção 7) |
|---|---|---|---|
| efeitos pelo mapa | 17, **1,6 por segundo** | 35, **3,2 por segundo** | uns 3 por segundo fora da batida |
| efeitos com onset detectado a até 40 ms | 13 (1,2/s) | 24 (2,2/s) | |
| onsets no áudio final (música sozinha: 4,7/s) | 4,9/s | 4,9/s | 4,5 a 5,7/s no total |
| loudness integrada (original: -14,1 LUFS) | -17,3 LUFS | -16,4 LUFS | |
| pico | -1,6 dBFS | -1,1 dBFS | |

- O encaixe foi conferido no próprio mp4: o áudio final bate com o planejado (música vezes volume mais efeitos) com
  atraso de 0 amostra; vídeo e áudio começam em 0 e têm a mesma duração (10,933 s).
- Os efeitos que o detector de onset não acha são os que crescem devagar (whooshes, morph) e as teclas por baixo da
  música: é o esperado, não é atraso.
- A medida de onsets é uma heurística: com o detector daqui a música sozinha já dá 4,7 por segundo, então o número
  de efeitos que conta é o do mapa.

## Os eventos do Joi (joi-v2, 60 qps)

Tirados das trilhas medidas (`tracks.js`: ícone, faixa dos dígitos, palavras da lista, cursor, objetos, frase) e das
chaves do `index.html`, conferidos numa folha de quadros. Sem mola firme no Joi.

| quadro | som | nível | evento |
|---|---|---|---|
| 8 | aparecer | S | ícone entra |
| 22 | numero | M | dígitos rolam no ícone |
| 82 | morph | S | ícone gira de lado e vira a pílula |
| 100 | tocar | M | o + gira e vira x |
| 141 | aparecer | S | item 1 entra |
| 147 | aparecer | M | itens 2 e 3 entram |
| 160 | aparecer | S | item 4 entra (do cinza ao preto) |
| 198 | entrar | S | a lista sai e o menu escuro se forma |
| 216 | aparecer | S | botões e objetos do menu aparecem |
| 247 | sair | M | objetos do menu somem |
| 260 | clicar | S | cursor clica no item (o risco começa) |
| 276 | sair | S | menu sai |
| 285 | aparecer | S | frase cai palavra a palavra (um som só: as palavras pousam a 2,5 quadros uma da outra) |
| 318 | brilho | M | estrela voa para o cartão |
| 326 | morph | S | frase vira o cartão |
| 346 | aparecer | S | título e botão do cartão entram |
| 354 | entrar | S | corte para perto do cartão |
| 380 | sucesso | S | cartão assenta |

Suave: 13 efeitos em 7,52 s (1,7 por segundo); marcado: 18 (2,4 por segundo).

## Os eventos do VoiceOS (voiceos-v2, 60 qps)

A trilha original tem locução: nada de `digitar` nem `numero` (ficariam em cima da fala) e `musica_volume` 1.

| quadro | som | nível | evento |
|---|---|---|---|
| 16 | aparecer | S | frase do céu começa a aparecer |
| 26 | aparecer | M | dock aparece embaixo |
| 70 | entrar | S | céu vira o vinhedo |
| 100 | entrar | M | dock cresce |
| 118 | clicar | S | cursor clica no ícone do dock |
| 141 | morph | S | janela da mensagem abre |
| 165 | brilho | M | ditado rosa corre |
| 212 | aparecer | S | botão Enviar nasce do cursor |
| 226 | clicar | S | mão clica em Enviar |
| 263 | entrar | S | corte para a página |
| 312 | tocar | M | título começa a ser digitado |
| 412 | entrar | M | o texto da página rola |
| 452 | aparecer | S | a caixa cobre a palavra destaque |
| 478 | morph | S | caixa cresce e vira a tecla |
| 494 | brilho | S | tecla acende |
| 578 | entrar | M | triângulo (ou o logo do kit) voa para o logo |
| 598 | sucesso | S | o logo se forma |

Suave: 11 efeitos em 11,67 s (0,9 por segundo); marcado: 17 (1,5 por segundo).

## Medidas depois dos ajustes (30/10)

Com a trilha original por baixo (fora do repositório, só para ouvir: `fase2-provas/ouvir/` no rascunho), loudness
integrada pelo ebur128 do ffmpeg. As três trilhas originais medem -14,1 LUFS.

| | efeitos | em cima de golpe (-6 dB) | ganho para o alvo | final |
|---|---|---|---|---|
| Satellite suave (junior) | 17 | 9 (as pílulas 132,5 a 150,5 entre eles) | +3,3 dB | -14,1 LUFS |
| Satellite marcado (junior) | 32 | 18 | +2,8 dB | -14,2 LUFS |
| Joi suave (padaria) | 13 | 8 | +3,0 dB | -14,1 LUFS |
| Joi marcado (padaria) | 18 | 11 | +2,6 dB | -14,1 LUFS |
| VoiceOS suave (padaria) | 11 | 5 | 0 | -14,1 LUFS |
| VoiceOS marcado (padaria) | 17 | 7 | 0 | -14,0 LUFS |

Antes dos ajustes, o Satellite saía 2 a 3 LUFS abaixo do original (-17,3 no suave, -16,4 no marcado). Com o silêncio do
repositório (sem normalizar), os efeitos sozinhos medem -22,1 LUFS no Satellite marcado, -26,5 no Joi suave e -27,2 no
VoiceOS suave.

## O que ainda soa mal (medido, não ouvido depois dos ajustes)

- O corte de golpe pega muito evento nas trilhas cheias (9 de 17 no Satellite suave): 6 dB é um meio-termo, ainda não
  ouvido. Se os efeitos sumirem, baixar `BATIDA_DB` para -3.
- A catraca do relógio do Satellite continua sendo o pico mais alto da onda (tiques curtos e secos).
- Joi e VoiceOS não têm o campo `musica`: no repositório a trilha deles é o silêncio, então a loudness alvo só vale
  para quem trocar o `assets/silencio.m4a` da cópia (ou levar o `musica` do Satellite para eles).
