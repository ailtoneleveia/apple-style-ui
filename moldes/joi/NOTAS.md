# Molde do Joi

> **No repositório.** A SF Pro não vem junto: na hora do render a cópia do molde recebe a do sistema (ou a Inter, com `ASUI_FONTE_LIVRE=1`). O áudio do original também não: o padrão é `assets/silencio.m4a`. O vídeo do clone (para o lado a lado) fica em `~/.apple-style-ui/originais/<molde>.mp4`, se tu tiver. As provas quadro a quadro citadas abaixo foram feitas com os arquivos do original, fora do repositório. Os recortes do original (objetos, fotos, ícones e memoji) também ficaram de fora: no lugar deles vão peças livres geradas por `moldes/pecas_livres.py`, com o mesmo nome e tamanho. Com elas, os padrões já não são o clone pixel a pixel; a régua do portão (`aprendizado/regressao/`) foi refeita com elas.

O clone do Joi virou um **molde**: o mesmo vídeo de 1080x1920, 60 fps e 7,52 s,
com a mesma sequência, os mesmos tempos medidos, os mesmos movimentos e o mesmo áudio. Mudam os textos, os dígitos,
os ícones da lista, os objetos 3D, as cores e os fundos. Sem nada trocado, o molde monta o clone (prova no fim).
Uso interno de estudo: SF Pro, emojis da Apple e o áudio do original não podem ser publicados.

```
joi/
  molde/          o projeto HyperFrames (as variáveis estão no <html> do index.html)
  MOLDE.json      a versão em vigor (joi-v2: kit de marca completo e sons) e a impressão digital (sha256 de cada arquivo)
  versoes-travadas/   uma pasta por versão travada (joi-v1, joi-v2), cópia do molde só leitura
  molde/sons.json o mapa evento -> som (ver ../../sons/SONS.md)
  versoes/        uma versão = um JSON só com o que muda
    original.json   {} = o clone
    junior.json     a versão de teste (português, laranja #E54A26)
    padaria-marca.json  o kit da padaria inteiro (cor, nome, Archivo e logo) com sons suaves
  montar.py       renderiza uma versão
  saidas/         vídeos, lado a lado e folhas de quadros
```

## Como usar

1. Copie `versoes/junior.json` para `versoes/<nome>.json` e troque os valores. O que não estiver no arquivo fica igual ao original.
2. Rode, de dentro de `joi/`:
   ```
   python3 montar.py versoes/<nome>.json --previa   # 60 fps, sem motion blur, ~1 a 1,5 min
   python3 montar.py versoes/<nome>.json            # final: 240 fps, motion blur com 4 subquadros, ganho e LUT de luma
   ```
3. Saem em `saidas/`: `<nome>.mp4`, `<nome>-lado-a-lado.mp4` (clone original à esquerda, versão à direita, 2160x1920)
   e `<nome>-folha.jpg` (10 momentos, original em cima, versão embaixo). A prévia ganha `-previa` no nome.
4. Confira a folha no olho antes de usar o vídeo.

**Saída do montar.py.** No stdout sai um único JSON:
`{"ok": true, "resumo": "...", "proximo": {"comando": "...", "motivo": "...", "precisa_de_voce": true}, "arquivos": [...]}`.
O `comando` já vem pronto para rodar, com caminho absoluto. Erro vai para o stderr como
`{"ok": false, "erro": "...", "codigo": "NOME_DO_ERRO"}`. Saída 0 = ok, 1 = erro, 2 = uso errado.
Códigos: `USO_ERRADO`, `VERSAO_ILEGIVEL`, `VERSAO_INVALIDA`, `FALTA_PROGRAMA`, `ORIGINAL_AUSENTE`, `DISCO_CHEIO`,
`COMANDO_FALHOU`, `AUTOTESTE_FALHOU`, `VERSAO_REPETIDA`, `ERRO_INTERNO`.

**O que o montar.py confere antes de renderizar.** Variável que não existe, cor fora de `#rrggbb`, opção fora da lista
(ícones e objetos), dígitos que não sejam exatamente 5, texto vazio e travessão viram uma mensagem clara e nada é
renderizado. A cada execução ele roda um autoteste com asserts (validação, versão travada e todas as versões guardadas). Renderiza
com `--workers 1`, trabalha no rascunho da sessão e para se o disco tiver menos de 2 GB livres. O bruto de 240 fps é
apagado logo depois do tmix. Encode H.264 `veryslow`, `-tune animation`, crf 12, `-refs 4 -level:v 5.1` (sem isso o
x264 sobe para o nível 6.0 nessa resolução e o QuickTime embaralha os blocos).

**Versão travada.** `MOLDE.json` guarda a versão em vigor e o sha256 de cada arquivo de `molde/` (sem pastas ocultas de
cache), e `versoes-travadas/joi-vN/` guarda a cópia congelada de cada versão (arquivos só leitura, nunca reescrita).
Se alguém editar o molde sem travar uma versão nova, o `resumo` avisa quais arquivos mudaram e o `proximo` passa a ser o
comando de travar. Para travar: `python3 montar.py --travar` (o próximo número). Nome repetido, no registro ou numa pasta
que já existe, é recusado (`VERSAO_DO_MOLDE_REPETIDA`). Uma versão com `"molde": "joi-v1"` sai com a pasta congelada da v1.

**No Studio do HyperFrames.** As mesmas variáveis aparecem como campos (`npx hyperframes preview` dentro de `molde/`):
textos viram caixas, ícones e objetos viram listas e as cores têm seletor.

## O que dá para trocar

| variável | o que é | original |
|---|---|---|
| `icone_texto` | texto vermelho no topo do ícone de calendário. Com kit de marca, recebe o `nome` do `marca.json` (o valor escrito na versão vale mais); diminui acima de 220 px | Joi |
| `digitos` | os 5 dígitos que rolam no ícone, da esquerda para a direita; o 4º abre no centro e o 5º é o último a entrar | 56789 |
| `item1` … `item4` | itens da lista. O 1 vira o título do menu e é riscado; o 4 entra por último, do cinza ao preto | Plan a day, Drink water, Get Sunlight, Wind Down |
| `icone1` … `icone4` | ícone de cada item: `caixa` (tracejada), `lua`, `sol`, `gota`, `coracao`, `estrela`, `raio`, `feito`, ou um emoji 🌙 ☀️ 💧 🧘 ☕ 📚 🏃 ✅ 🍎 💤. O ícone do item 1 também vai para o menu | caixa, caixa, caixa, lua |
| `botao1` … `botao3` | rótulos dos botões do menu (o 3 é o vermelho) | Complete, Edit, Remove |
| `objeto1` … `objeto4` | os objetos 3D do menu, da esquerda para a direita: os recortes `xicara`, `controle`, `bola`, `monitor` (em qualquer posição) ou um emoji ☕ 🎮 ⚽ 🖥️ 💻 📱 🎧 📚 🏀 🪴 💡 ⏰ 🍎 📷 | xicara, controle, bola, monitor |
| `frase` | a frase que cai palavra por palavra e vira o subtítulo do cartão | Get your subscription |
| `cartao_titulo` | título do cartão | Joi Pro |
| `cartao_botao` | botão do cartão | Upgrade |
| `cor_principal` | gira **todo o azul**: gradiente, vidro e aro do cartão, estrela (marinho e clara), seta do botão, subtítulo e o fundo azulado de f324-336 | #4282f5 |
| `cor_vermelho` | gira o vermelho e os rosas: texto do ícone, disco rosa, fundo rosa de f79-95, botão Remove (fundo, rótulo, ícone e brilho) e a frase vermelha que escurece | #ee4f40 |
| `cor_icone` | cor dos ícones desenhados da lista (a lua roxa) | #5b35ef |
| `fonte` | `sf` (SF Pro, a do original), `archivo` ou `inter` (SIL OFL; os arquivos vêm do molde do Satellite na hora do render). Os textos originais continuam medidos em SF Pro e os novos na fonte escolhida, então o layout acompanha a largura real. Com kit de marca, vem do `fonte` do `marca.json` | sf |
| `logo` | imagem redonda no lugar da estrela do cartão (o mesmo voo). Caminho no molde, ao lado da versão, absoluto ou o `logo` do kit (`marcas/<cliente>/logo.png`): vai para `assets/var/` da cópia de render | vazio (estrela) |
| `sons` | som por elemento: `nenhum`, `suave` ou `marcado` (ver `sons/SONS.md`) | nenhum |
| `musica_volume` | volume da trilha quando há sons, de 0 a 1 | 0,7 |
| `fundo_claro`, `fundo_escuro` | os fundos lisos. Cada canal de cada fundo medido guarda o seu lugar entre o escuro e o claro, então o cinza do começo, as rampas e o cinza do botão "+" acompanham | #fdfdfd, #0d0d0d |

O "Get" do pedido é a primeira palavra da `frase`: no clone ele não é um elemento separado.

**Como a cor troca.** A paleta medida gira de matiz no espaço OKLCH em direção à cor nova (o mesmo método do molde do
Satellite). A cor de referência (`#4282f5`, o meio do gradiente do cartão; `#ee4f40`, o "Joi") cai exatamente na cor nova;
as outras guardam a luminosidade e a saturação relativas, então o vidro claro continua claro e a estrela marinho continua
escura. No fundo, o vermelho gira só os matizes de 335° a 55° e o azul só os de 215° a 300°, cada cor uma vez só
(a lua roxa, 282°, não é fundo e não gira). Cinzas não têm matiz e ficam.

**Como o layout acompanha o texto.** Tudo é medido na fonte, sempre "novo menos original", por isso o original não se
mexe (cada diferença é exatamente 0 nos padrões).
- Lista: cada palavra nova segue a trilha medida da palavra original na mesma posição (as que sobram entram 2,5 quadros
  depois da última), deslocada pela diferença de largura. Linha com mais de 540 px diminui a letra mantendo a linha de base.
- Título do menu: mesma escala do clone; diminui se não couber no cartão (o cartão mais estreito é o de f222).
- Botões do menu: crescem com o rótulo, com a mesma folga mínima do botão mais justo do clone, e o **cartão cresce** junto
  (até +245 px). Passando disso, os rótulos diminuem.
- Frase: continua centrada; acima de 960 px a letra diminui. Ela pousa no subtítulo do cartão palavra por palavra.
- Cartão: o botão segue o rótulo para os dois lados (borda esquerda fixa) e diminui a letra antes de passar do fim do
  cartão. Título e subtítulo novos têm que terminar antes do x 860 do cartão, que é a borda da tela no quadro parado do
  fim; se não couberem, a letra diminui.
- Texto do ícone: diminui acima de 220 px.

## O que não dá para trocar, e por quê

- **Sequência e tempos.** São curvas medidas quadro a quadro da referência (`tracks.js`). Uma sequência nova é um clone novo.
- **Quantidade de peças.** Sempre 4 itens na lista, 3 botões no menu e 4 objetos: cada um tem a sua trilha de entrada
  e saída. O número de palavras é livre.
- **Áudio.** A trilha é o `assets/silencio.m4a` (a do original não vai no repositório); não há campo `musica`. Os sons
  por elemento entram por cima pelo montador (`sons`).
- **Desenhos fixos:** a forma do ícone de calendário, a pílula "+" e o glifo que gira, o cursor, os ícones dos botões
  do menu (check, lápis, apagar), a estrela de 4 pontas, o ícone do botão do cartão e os pontinhos. O cartão escuro do
  menu e os botões cinza também ficam: só o botão vermelho segue `cor_vermelho`.
- **Objetos 3D.** Os recortes e os emojis entram parados, como no clone; nenhum gira em 3D (a referência gira um pouco).
- **Dígitos.** Exatamente 5, um por casa: o ícone tem a largura de um dígito.
- **Formato.** Só 9:16 (1080x1920).
- **Fonte e emojis.** SF Pro e Apple Color Emoji do sistema, licença Apple: só estudo, neste Mac. Para publicar, `fonte`
  `archivo` ou `inter` (ou `ASUI_FONTE_LIVRE=1`). Os dígitos do calendário e o glifo do "+" seguem a fonte do `#root`.
- **A frase original no fim.** "Get your subscription" fica cortada pela borda da tela no quadro parado do fim, como no
  clone e na referência. Ficou assim para o padrão sair igual; frase nova é ajustada para não cortar.
- **Textos muito longos.** Nada corta, mas a letra diminui. Com o teste extremo (item de 36 letras, botões de 21, frase
  de 48, título de 21) tudo coube, com rótulos dos botões e subtítulo pequenos. Conferir na folha.

## Prova: com os padrões, o molde é o clone

- **Diferença 0 no que o Chrome desenha.** O clone sem alteração e o molde com `versoes/original.json` (`{}`), abertos
  lado a lado no mesmo Chrome, dão o mesmo DOM inteiro (cada estilo, transform, texto e SVG de `#root`) em **452 de 452**
  quadros da prévia (60 fps) e em **1805 de 1805** instantes do final (240 fps, com o deslocamento de subquadro do motion
  blur). Rodado duas vezes. Controle: deslocar um dos dois em 1/4 de quadro já acusa diferença.
- **md5 do mp4: não dá igual, nem para o próprio clone.** O mesmo clone renderizado duas vezes com o mesmo comando sai
  com md5 diferente (`5f4bfa22…` e `470eada2…`): o Chrome deste Mac rasteriza as camadas que mudam de escala (ícone,
  pílula, cartão) de um jeito um pouco diferente a cada execução, tanto pela GPU quanto em software (`--no-browser-gpu`,
  testado duas vezes também). Medido nos quadros decodificados:
  - clone x clone: 298 de 452 quadros com alguma diferença, média 0,0283 por canal;
  - clone x molde padrão: 298 quadros, média 0,0284;
  - segundo render do clone x molde padrão: 84 quadros, média 0,0012.
  A diferença do molde é o ruído do próprio renderizador.

## Tempo de render (este Mac, `--workers 1`)

- Prévia: 25 a 35 s de render, 65 a 85 s no total com lado a lado e folha.
- Final com motion blur (junior): 82 s de render a 240 fps (1804 subquadros), 2 min 7 s no total (o encode veryslow do lado a lado 2160x1920 pesa).

## Kit de marca e sons (30/10, joi-v2)

- **Kit:** `cor_principal` -> `cor_principal`, `nome` -> `icone_texto`, `fonte` -> `fonte`, `logo` -> `logo`. Prova:
  `versoes/padaria-marca.json` (kit `marcas/padaria-exemplo/`: #D4860B, Archivo, "padaria.exemplo" no ícone e o logo
  no lugar da estrela). A Archivo é pedida com `document.fonts.load` logo no começo e o layout só confia na medida
  dela depois que ela chega (o `fonts.check` responde "sim" para uma fonte que ninguém pediu ainda, e a medida saía com
  a fonte reserva).
- **Sons:** 18 eventos em `molde/sons.json` (13 no suave, 1,7 por segundo; 18 no marcado, 2,4 por segundo), cada um
  no quadro do pico do movimento a 60 qps. Ver a tabela em `sons/SONS.md`.
- **Padrão intacto:** com os padrões (fonte `sf`, sem logo, `sons: nenhum`) a régua do portão continua passando
  ("iguais dentro da tolerância"), e nenhuma linha nova de som roda.
