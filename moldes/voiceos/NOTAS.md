# Molde do VoiceOS (clone dafsq)

> **No repositório.** A SF Pro não vem junto: na hora do render a cópia do molde recebe a do sistema (ou a Inter, com `ASUI_FONTE_LIVRE=1`). O áudio do original também não: o padrão é `assets/silencio.m4a`. O vídeo do clone (para o lado a lado) fica em `~/.apple-style-ui/originais/<molde>.mp4`, se tu tiver. As provas quadro a quadro citadas abaixo foram feitas com os arquivos do original, fora do repositório. Os recortes do original (objetos, fotos, ícones e memoji) também ficaram de fora: no lugar deles vão peças livres geradas por `moldes/pecas_livres.py`, com o mesmo nome e tamanho. Com elas, os padrões já não são o clone pixel a pixel; a régua do portão (`aprendizado/regressao/`) foi refeita com elas.

O clone "fastest concept for VoiceOS" virou um **molde**: o mesmo vídeo de 1920x1080,
60 fps e 11,67 s, com a mesma sequência, os mesmos tempos, os mesmos movimentos medidos e o mesmo áudio. Mudam os textos,
os ícones do dock, o avatar, a cor de destaque, a cor do anel da tecla e as duas fotos de fundo. Com os padrões, o molde
é o clone pixel a pixel (prova no fim).

```
voiceos/
  molde/          o projeto HyperFrames; as variáveis estão no <html> do index.html
  MOLDE.json      versão travada: versão (voiceos-v1) e impressão digital (sha256 de cada arquivo do molde)
  versoes/        uma versão = um JSON com os valores trocados
    original.json   {} = o clone, sem troca
    junior.json     a versão de teste (português, #E54A26)
    teste-campos.json + ceu-liso.png   prova dos campos de imagem e de emoji (céu liso amarelo, ícones e avatar emoji)
  montar.py       renderiza uma versão, trava e prova o molde
  saidas/         os vídeos prontos
```

Uso interno, só para estudo: SF Pro, emojis da Apple, os recortes do original (fotos, ícones, memoji) e o áudio do
original vêm de terceiros. Não publicar.

## Criar uma versão

1. Copie `versoes/junior.json` para `versoes/<nome>.json` e troque os valores. O que não estiver no arquivo fica igual
   ao original.
2. Rode, de dentro de `voiceos/`:
   ```
   python3 montar.py versoes/<nome>.json --previa   # 60 fps sem motion blur: vídeo e folha, ~1 min
   python3 montar.py versoes/<nome>.json            # final: 240 fps + tmix 4, lado a lado, lado a lado leve e folha
   ```
3. Saem em `saidas/`: `<nome>.mp4`, `<nome>-lado-a-lado.mp4` (original | versão, 3840x1080, crf 12),
   `<nome>-lado-a-lado-leve.mp4` (crf 20) e `<nome>-folha.jpg` (9 momentos: céu, dock, ditado, Send, título, linhas,
   caixa, tecla e logo; original em cima, versão embaixo). Confira a folha no olho antes de usar.

Antes de renderizar, o `montar.py` roda um autoteste (asserts) e confere a versão contra as variáveis declaradas:
variável que não existe, texto vazio, travessão, cor fora de `#rrggbb`, ícone ou avatar fora da lista e imagem que não
existe (ou não é jpg, png ou webp) viram uma mensagem clara e nada é renderizado. Render sempre com `--workers 1`;
para se o disco tiver menos de 2 GB livres; o bruto de 240 fps é apagado logo depois do tmix.

**Saída do montar.py.** O stdout traz um único JSON:
`{"ok": true, "resumo": "...", "proximo": {"comando": "...", "motivo": "...", "precisa_de_voce": true}, "arquivos": [...]}`.
O progresso vai para o stderr. Em erro, a última linha do stderr é `{"ok": false, "erro": "...", "codigo": "NOME_DO_ERRO"}`.
Códigos de saída: 0 ok, 1 erro, 2 uso errado.

**Versão travada.** `python3 montar.py --travar` grava o `MOLDE.json`. Se alguém editar o molde sem travar de novo, toda execução
avisa (campo `aviso` no JSON e linha no stderr) dizendo quais arquivos mudaram. Travar de novo depois de uma edição
sobe a versão (voiceos-v2, v3...). Antes de travar uma edição, rode `--provar`.

**No Studio do HyperFrames** as mesmas variáveis aparecem como campos (texto, cor, lista e imagem). Abra `molde/`
com `npx hyperframes@0.8.184 preview`.

## As variáveis

### Textos

| variável | onde aparece | original |
|---|---|---|
| `frase_ceu` | cena 1, letra por letra no céu | ohhhh man |
| `frase_vinhedo` | cena 2, palavra por palavra | I got a lot work to do |
| `msg_nome`, `msg_hora` | janela de mensagem | Oly, 00:02 |
| `msg_texto` | a frase ditada (rosa, depois branca) | I need to send a new scirpt to client.. |
| `botao_enviar` | o botão que nasce do cursor | Send |
| `pagina_vazia` | título cinza da página antes de digitar | New page |
| `pagina_privado` | rótulo do cadeado | Private |
| `pagina_titulo` | título digitado | Script for new vid.. |
| `pagina_dica` | a linha vazia com dica | Press “space” for AI or “/” for commands. |
| `linha1` … `linha13` | as 13 linhas do texto da página | A blank page. … Typing was. |
| `linha14_inicio`, `linha14_destaque`, `linha14_fim` | a última linha; o destaque é a palavra que vira a caixa e depois a tecla | Stop / typing / your scripts. |
| `pilula_pronto` | texto embaixo da pílula preta | Done! |
| `tecla` | a tecla | fn |
| `frase_tecla` | a frase da cena 4, **sem ponto final** (o ponto é a bolinha que vira o logo; se vier com ponto, ele é tirado) | and start speaking |
| `legenda_logo` | legenda embaixo do logo | this is concept by creatoroly |

### Cores

| variável | o que troca | original |
|---|---|---|
| `cor_destaque` | **todo o rosa** por giro de matiz em OKLCH: ditado, cursor, brilho, botão, tom roxo da janela abrindo, ícone VO enchendo, lavado rosa da página, título digitado, cursores da página, brilho da linha 14 e o magenta da caixa | #d41ea2 (topo do botão) |
| `cor_anel` | o anel ondulado em volta da tecla (cor direta) | #c0e3fb |

O giro é o mesmo do molde do Satellite: a paleta medida gira de matiz em direção à cor nova; a cor de referência cai
exatamente na nova e as outras mantêm luminosidade e saturação relativas (o lavado claro continua claro, o roxo escuro
continua escuro). Só giram os rosas e magentas (matiz OKLCH entre 305° e 15°). O azul e o violeta da caixa e do texto
da linha 14, o vermelho final da caixa, o arco-íris da tecla e o azul de "and start speaking" ficam.

### Ícones, avatar e fotos

| variável | opções | original |
|---|---|---|
| `icone1` … `icone7` | os 7 recortes (slack, notion, messages, docs, gmail, figma, cube) ou 16 emojis da Apple (💬 📝 📧 📅 🎵 📷 🎨 📁 📊 🎬 💡 🚀 ⚙️ 🧠 🎙️ ✏️) num quadrado branco de app | slack … cube, da esquerda para a direita |
| `avatar` | `recorte` (o memoji) ou 8 emojis | recorte |
| `foto_ceu` | imagem: caminho de arquivo (relativo ao molde, ao arquivo de versão ou absoluto) | assets/img/sky1.jpg |
| `foto_vinhedo` | imagem, igual | assets/img/vine.jpg |

- `icone1` é o ícone que o cursor clica; a pílula de vidro troca o VO por ele. `icone2` também aparece na pílula preta
  da página (no original, o Notion).
- Uma foto nova cobre o retângulo da placa medida (`object-fit: cover`), com a mesma câmera, o mesmo desfoque e o
  mesmo escurecimento. A foto do céu cobre também a faixa de céu embaixo do vinhedo. Use foto 16:9 grande (as placas
  têm 4435 e 3696 px de largura, porque a câmera aproxima até 1,1x).

## Como o layout acompanha o texto

Tudo é medido pela fonte, sempre "novo menos original", e cada troca só roda quando o valor é diferente do padrão, por
isso o original nunca se mexe.

- **Céu e vinhedo:** a frase nova é montada com os avanços reais da SF Pro e centrada no mesmo centro de tinta. As letras
  (céu) e as palavras (vinhedo) pegam emprestadas as trilhas medidas do original, espalhadas por igual: no céu, a
  primeira metade das palavras usa as letras de "ohhhh" e o resto as de "man"; no vinhedo, a primeira palavra usa "I" e a
  última usa "do" (que entra varrendo da esquerda). Os quadros cinzas de carregamento ficam nas palavras que caem nas
  trilhas de "lot" e "work". Se não couber, a letra diminui (céu até 2400 px de mundo, vinhedo até 1800).
- **Mensagem:** o horário anda junto com o nome. O ditado (cabeça rosa e cunha branca) estica na largura da frase nova,
  no mesmo ritmo; o cursor que vira botão sai do fim da frase nova. Um rótulo maior alarga o botão para a esquerda e a
  mão clica no centro novo. A frase fica numa linha (até 670 px; acima disso a letra diminui).
- **Página:** título, dica e as 14 linhas são digitados pelas mesmas cabeças medidas, esticadas pela largura de cada
  linha nova. A caixa da dica cresce com o texto. As linhas usam um tamanho só: se a mais longa passar de 1350 px, todas
  diminuem juntas. Na linha 14, a caixa, a borracha, o brilho e o zoom final seguem a palavra de destaque, e o zoom ainda
  pousa a caixa no lugar onde a tecla aparece.
- **Tecla:** o texto fica centrado na tecla (até 210 px). A frase da cena 4 começa no mesmo ponto à esquerda (a tecla
  fica à esquerda dela), estica a digitação e o ponto final sai do fim da frase nova e volta para o voo medido até o logo.
  Até 1830 px; acima disso a letra diminui.
- **Rótulos centrados** (Pronto!, legenda do logo): a caixa alarga em volta do mesmo centro.

## O que não dá para trocar, e por quê

- **Sequência, tempos e movimentos.** São as curvas medidas quadro a quadro do original (`tracks.js`, `tracks3.js`).
  Uma sequência nova é um clone novo.
- **Quantidade de coisas.** Sempre 7 ícones no dock e 14 linhas na página: cada uma tem sua trilha e o scroll medido
  conta com elas. Textos longos encolhem a letra, não quebram linha.
- **Desenhos fixos:** o logo VO (triângulo e círculo), a pílula de vidro e as barras de áudio, a janela, as bolinhas
  vermelha/amarela/verde, o cadeado, os cursores, a tecla com o arco-íris e o anel ondulado (só a cor do anel muda).
- **Cores que não giram:** azul e violeta da caixa e do texto da linha 14, o vermelho final da caixa, o azul de "and start
  speaking" e da bolinha, o arco-íris da tecla, o vidro e os cinzas.
- **Recorte de nuvem na transição.** Do céu para o vinhedo, o vinhedo aparece primeiro de dentro das nuvens, por uma
  máscara cortada da foto original do céu. Com outra foto de céu a máscara não serve, então a transição vira um
  crossfade simples (com a câmera e os tempos iguais).
- **Áudio.** Fixo, a trilha do original.
- **Formato.** Só 16:9 (1920x1080).
- **Corte da câmera na cena 4.** Entre os quadros 556 e 576 a câmera anda para a direita e a primeira letra da frase sai
  pela borda esquerda. É o movimento medido do original (o "a" de "and" sai do mesmo jeito), não um texto cortado pelo
  layout.
- **Fonte e emojis.** SF Pro e Apple Color Emoji do sistema, licença Apple, só neste Mac.

## Prova: com os padrões, o molde é o clone

- **Pixel a pixel, os 700 quadros:** `python3 montar.py --provar` tira snapshot PNG (sem encoder, Chrome em software)
  de cada quadro do clone e do molde e compara. Quadro que difere é tirado de novo, sozinho, até 2 vezes, porque o
  snapshot também erra de vez em quando. Resultado: **700 de 700 quadros com pixels idênticos**. Em três rodadas
  desta entrega, 700, 699 e 698 bateram de primeira; os que faltaram (quadros 25 e 142) bateram no snapshot refeito
  (o quadro 142 sozinho deu o mesmo PNG 6 de 6 vezes, 3 do clone e 3 do molde).
- **Estado de cada quadro** (conferido uma vez nesta entrega): num Chrome sem cabeça (o mesmo do HyperFrames), o DOM
  inteiro (elementos, atributos, estilos, SVG e texto) e o canvas do lavado rosa são iguais nos 700 quadros desenhados
  em sequência.
- **Por que não md5 do mp4:** o render do HyperFrames neste Mac não se repete bit a bit nem para o próprio clone. Dois
  renders do clone, sem nenhuma mudança, dão md5 diferentes (GPU: 2 de 2; software: 4 iguais e depois um diferente,
  conforme a carga da máquina). A variação fica no vidro com `backdrop-filter` do dock e da pílula e se espalha pelo
  resto do grupo de quadros no encode. Medido na mesma prévia de 60 fps: clone contra clone dá PSNR 40,77 dB e clone
  contra molde dá 40,78 dB, ou seja, o molde difere do clone exatamente o quanto o clone difere de si mesmo.
- **Campo de imagem:** `versoes/teste-campos.json` troca o céu por uma cor lisa (`ceu-liso.png`), três ícones e o avatar
  por emojis e o anel por um laranja claro. `saidas/teste-campos-previa-folha.jpg` mostra o céu amarelo na cena 1 e na
  faixa embaixo do vinhedo, o 💬 no dock e na pílula, o 📝 na pílula preta e o 🙂 no avatar.

## Tempo de render (este Mac, `--workers 1`)

- Prévia (60 fps, sem motion blur): 34 a 57 s de render, cerca de 1 min no total com o encode e a folha.
- Final da `junior.json` (240 fps + tmix 4): 129 s de render, 4 min 50 s no total (o encode veryslow dos dois lado a
  lado 3840x1080 pesa). O bruto de 240 fps fica na pasta temporária só até o tmix.
- `--provar` (1400 snapshots PNG em lotes de 50): cerca de 6 min (352 s).
