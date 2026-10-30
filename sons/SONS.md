# Sons por elemento

"O mais pika desse estilo é o som: cada elemento que aparece tem som." Esta pasta é o pacote de sons do motor, e o
molde do Satellite já sabe usar.

## Como funciona

- **Pacote** (`sons/`): 20 sons curtos de interface, todos CC0 (origem e licença em `CREDITOS.md`), mono, 48 kHz,
  sem silêncio na frente e atrás, todos com a mesma loudness (-18 LUFS na janela de 100 ms, teto de -1 dBFS).
  `sons.json` guarda de cada som o tipo, a duração e o **ataque** (o instante do pico de energia dentro do arquivo).
  `fazer_pacote.py` refaz o pacote igual, byte a byte.
- **Mapa** (`satellite/sons.json`): a lista de eventos do molde, cada um com o quadro do pico do movimento no clone,
  o tipo de som, o nível (`suave` ou `marcado`) e a entrada com mola que ele segue.
- **Duas variáveis** no `index.html` do molde:
  - `sons`: `nenhum` (padrão), `suave` (só os eventos principais, 4 dB mais baixo) ou `marcado` (todo evento);
  - `musica_volume`: de 0 a 1, o volume da música quando há sons (padrão 0,7, uns 3 dB abaixo). Com `nenhum` ela não
    é usada.
- **O montar.py** lê o mapa, põe o **ataque** de cada som em cima do quadro do evento (com precisão de amostra,
  inclusive em quadro fracionado), soma tudo à música com o volume pedido e passa num limitador em -1 dBFS (com
  compensação de atraso, para nada sair do lugar). Ele acompanha as outras variáveis:
  - `mola: firme` adianta o evento que está dentro de uma entrada (`b + 0,6 (f - b)`), como o `index.html`;
  - `ritmo: batidas` leva o evento para o quadro novo da saída (a mesma tabela do ritmo);
  - `ilha_texto` com mais palavras dá mais toques de tecla (um por palavra).
- **Sem repetir:** cada tipo roda entre as suas versões (aparecer 1, 2, 3, 1, ...), então o mesmo arquivo nunca toca
  em dois eventos seguidos. O autoteste do `montar.py` confere isso.
- **Padrão intacto:** com `sons: nenhum` nenhuma linha nova roda e a música segue copiada. A prévia de
  `versoes/original.json` continua com o mesmo md5 (`877170713ecc12ba4889e671dc0250f5`, antes e depois).
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
| 4 | entrar | M | faixas de luz cruzam a tela |
| 7 | aparecer | S | ícone entra |
| 10 | brilho | M | ponto azul acende no ícone |
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
| 217,8 + 1,6 por palavra | digitar | M | texto da ilha, palavra a palavra |
| 225 | numero | M | relógio entra |
| 241,75 e 258,75 | numero | S | relógio vira (meio do rolamento) |
| 274,5 | sair | S | cena sobe e sai |
| 278,5 | aparecer | S | balão entra |
| 283 | brilho | M | brilho passa no balão |

O título não ganha um toque por palavra: no clone as palavras pousam todas em 53 ms (atraso de 0 a 1,6 quadro), e
toques tão juntos viram um só. Ele ganha um whoosh no pouso.

## Medidas (versão junior, finais com motion blur)

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

## Como aplicar no Joi e no VoiceOS (não aplicado ainda)

Cada um tem o próprio `montar.py` e a própria trilha copiada (`audio = .../ref-audio.m4a`, depois `-c:a copy`).

1. **Declarar** `sons` e `musica_volume` no `data-composition-variables` do `index.html` do molde, com os mesmos
   valores e padrões daqui (`nenhum` e 0,7). Isso não muda o render.
2. **Escrever o mapa** `molde/sons.json` no mesmo formato. O quadro é no fps do molde (Joi e VoiceOS a 60 fps).
   Tirar os quadros das keyframes do `index.html` (o pico do movimento: maior velocidade, ou o quadro em que o
   elemento fica visível) e conferir numa folha com o quadro de cada som. Quem segue uma entrada com mola leva
   `"mola": [início, quadros]` só se o molde tiver a mola firme.
3. **No montar.py do molde**, logo depois de definir `audio` e antes do mux: se `V["sons"] != "nenhum"`, carregar
   `eventos_de_som` e `mixar_sons` do `montar.py` da raiz (por `importlib`, porque os dois arquivos se chamam
   `montar.py`) e chamar `mixar_sons(V, audio, <pasta>/musica-sons.m4a, eventos, pacote, fps=60, nf=<quadros>)`.
   O padrão continua idêntico porque nada roda com `nenhum`; refazer a prova de md5 da prévia.
4. **Cuidados por molde:**
   - **Joi:** os eventos grandes já caem nas colcheias da trilha (136,9 por minuto). Som em cima de nota soma com a
     nota: começar pelo `suave` e baixar o `aparecer` (uns -3 dB) para não dobrar o golpe.
   - **VoiceOS:** a trilha tem locução. Os sons têm de ficar abaixo da voz: `musica_volume` 1 (a voz não pode
     baixar) e o nível `suave`, e evitar `digitar` e `numero` em cima de palavra falada.

## O que ainda soa mal (medido, não ouvido)

- **Abertura do marcado:** quatro efeitos em 0,33 s (whoosh, pop, brilho, toque) com a música quase muda (ela entra
  em ~0,4 s). Ficam no nível da música, mas sozinhos: é o trecho mais exposto.
- **Ilha:** cinco teclas em 210 ms alternando só dois arquivos, e a catraca do relógio começa 50 ms antes da última
  tecla. Pode soar mecânico e embolado. Um terceiro `digitar` ou tirar o "relógio entra" resolve.
- **Pílulas:** os cinco pops caem em cima dos golpes da trilha original; somam com eles.
- **Catraca do relógio:** é o pico mais alto da onda (tiques curtos e secos), mesmo ficando abaixo da música na
  loudness. No `suave`, o primeiro "relógio vira" fica 7 dB abaixo da música naquele instante e pode sumir.
- **Volume geral:** com `musica_volume` 0,7 as versões saem 2 a 3 LUFS abaixo do original.
