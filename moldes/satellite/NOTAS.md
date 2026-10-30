# O vídeo do Satellite como molde

> **No repositório.** A SF Pro não vem junto: na hora do render a cópia do molde recebe a do sistema (ou a Inter, com `ASUI_FONTE_LIVRE=1`). O áudio do original também não: o padrão é `assets/silencio.m4a`. O vídeo do clone (para o lado a lado) fica em `~/.apple-style-ui/originais/<molde>.mp4`, se tu tiver. As provas quadro a quadro citadas abaixo foram feitas com os arquivos do original, fora do repositório.

O clone do Satellite virou um **molde**: o mesmo vídeo, com a mesma sequência,
os mesmos tempos, os mesmos movimentos e o mesmo áudio. Mudam os textos, os ícones da lista, as cores e o nome no
balão final; para um "irmão" do Satellite, algumas peças e o jeito de entrar; e agora também a música e o ritmo,
a fonte, o formato (1:1 ou 9:16) e a marca inteira de um cliente. Sem nada trocado, o molde gera o clone
**quadro por quadro** (prova no fim).

```
moldes/satellite/
  molde/              o molde (projeto HyperFrames; as variáveis estão no <html> do index.html)
    MOLDE.json        versão do molde (satellite-v2, com a camada de som) e a impressão digital (sha256) de cada arquivo
    ritmo.js          vazio no molde; o montador preenche na cópia de render quando o ritmo é "batidas"
    sons.json         o mapa de eventos de som do molde (ver sons/SONS.md)
    assets/fonts/     Archivo e Inter (a SF Pro vem do sistema na hora do render)
    assets/silencio.m4a       o áudio padrão (o do original não vai no repositório)
  versoes/            uma versão = um arquivo JSON com os valores trocados
    original.json     {} = o clone, sem troca
    junior.json       a versão de teste (português, laranja #E54A26, juniorheusser)
    irmao.json        a junior com anel, radar, lista de baixo, título em desfoque e mola firme
    irmao-vertical.json   o irmão em 9:16, com a Inter (para o ritmo nas batidas, ponha a tua música em molde/assets/)
    junior-marca.json     a junior usando o kit marcas/junior/ (portanto com a Archivo)
    junior-suave.json, junior-marcado.json   a junior com sons por elemento
  MOLDE.json          versão do molde e impressão digital
  montar.py           invólucro de 3 linhas: chama o montador único (montar.py da raiz) com --molde satellite
  NOTAS.md            este arquivo
```

Na raiz do produto: `marcas/` (kits de exemplo), `sons/` (o pacote de sons, SONS.md e CREDITOS.md) e `montar.py`.
```
```

## O montador (um só para os três moldes)

O código mora no `montar.py` da raiz do produto e serve o Satellite, o Joi e o VoiceOS. O que é comum (validar, kit de marca,
render, motion blur, encode, lado a lado, folha, versão travada) está escrito uma vez; o que é de cada molde é um bloco
pequeno de configuração (fps, subquadros, momentos da folha, vídeo do clone, LUT) e, no Satellite, a parte de 9:16,
música, ritmo e sons. Os três `montar.py` antigos continuam funcionando: viraram invólucros que chamam o novo.

O molde vem de `--molde` ou da chave `"molde"` dentro da versão (`"satellite"`, ou `"satellite-v2"` para dizer a
versão do molde; se o molde já estiver em outra versão, sai um aviso).

## Criar uma versão nova

1. Copie `versoes/junior.json` para `versoes/<nome>.json`.
2. Troque os valores. Pode apagar uma linha: o que não estiver no arquivo fica igual ao original.
3. Rode (`M` = o `montar.py` da raiz do produto; `python3 moldes/satellite/montar.py ...` faz o mesmo sem o `--molde`):
   ```
   python3 M versoes/<nome>.json --molde satellite --previa   # 30 fps, sem motion blur, ~1 a 2 min no total
   python3 M versoes/<nome>.json --molde satellite            # final: 240 fps + tmix 8 + ganho de luma (round_mb_fix.sh)
   python3 M versoes/<nome>.json --molde satellite --saidas <pasta>   # grava em outra pasta
   python3 M versoes/junior-marca.json --molde satellite --marca padaria-exemplo --video <pasta do vídeo>
   python3 M versoes/junior-marca.json --molde satellite --previa --lote junior,padaria-exemplo,salao-exemplo \
       --video "<trabalho>/marcas/{marca}/videos/lote-exemplo"
   ```
4. Sem `--video`, saem em `saidas/` (ou em `--saidas`) com o nome do arquivo de versão: `<nome>.mp4`,
   `<nome>-lado-a-lado.mp4` (original à esquerda, versão à direita; 2160x1080, ou 2160x1920 no 9:16) e
   `<nome>-folha.jpg` (os 9 momentos do Satellite, original em cima, versão embaixo). A prévia ganha `-previa` no nome.

**Com `--video <pasta>`** a saída segue `ORGANIZACAO-DE-PASTAS.md`:
- os vídeos vão para `<pasta>/saidas/` com o nome do vídeo: a pasta `marcas/padaria/videos/primeiro/` gera
  `padaria-primeiro.mp4`, `padaria-primeiro-lado-a-lado.mp4` e `padaria-primeiro-folha.jpg` (o cliente vai na frente
  porque a régua do aprendizado é guardada pelo nome do mp4, e dois clientes podem ter um vídeo com o mesmo nome);
  fora de `marcas/<cliente>/videos/`, o nome é o da própria pasta;
- o bastidor vai para `<pasta>/.apple-style-ui/<data>-<previa|final>-<sufixo>/`, um por render, então dá para rodar dois
  clientes ao mesmo tempo. Fica o `vars.json`, o `resultado.json` (o mesmo JSON do stdout), o render cru da prévia e,
  com sons, o `sons-eventos.json`; a cópia do molde sai no fim;
- nada é sobrescrito: o arquivo que já existe ganha a data dele no nome (`padaria-primeiro-20261022-153012.mp4`)
  antes de sair o novo;
- a versão resolvida (sem `"marca"` nem `"molde"`) fica em `<pasta>/.apple-style-ui/versao-resolvida.json`. É ela que o portão
  lê (`--versao`). Sem `--video`, ela fica no bastidor e o caminho volta no JSON (`versao_resolvida`).

**Lote.** `--lote marca1,marca2` faz a mesma versão para cada marca, uma por vez, cada uma no seu vídeo: `{marca}` no
`--video` vira o nome do kit. Sem `--video`, cada uma vai para `marcas/{marca}/videos/<nome da versão>/` a partir da
pasta atual.

**Lado a lado opcional.** O lado a lado e a linha de cima da folha usam o vídeo do clone original. Se ele não estiver
na máquina, sai só a versão (o vídeo e a folha com a linha da versão) e o resumo avisa. Nada quebra.

O montador confere o arquivo antes de renderizar: variável que não existe, cor fora do formato `#rrggbb`,
opção fora da lista, número fora da faixa, relógio fora de `M:SS`, texto vazio, travessão, música ou logo que não existe
dentro de `satellite/`, imagem que não existe (VoiceOS) e kit de marca com campo errado viram uma mensagem clara e nada é
renderizado. Ele também roda um autoteste (asserts) a cada execução, que inclui conferir que todas as versões guardadas
continuam válidas. Renderiza com `--workers 1` e para se o disco tiver menos de 2 GB livres.

### O que o montador devolve

- **stdout:** um único JSON, para outro programa ou agente ler:
  `{"ok": true, "resumo": "...", "proximo": {"comando": "...", "motivo": "...", "precisa_de_voce": true}, "arquivos": [...],
  "molde", "render_s", "total_s", "versao_resolvida", "bastidor"}`, mais `"avisos"`, `"marca"` e `"video"` quando houver.
  Depois de uma prévia, o próximo comando é o render final (com caminho absoluto, roda de qualquer pasta); depois do
  final, é abrir a folha de quadros. Os dois pedem alguém olhando (`precisa_de_voce: true`). No lote, `"lote"` traz o
  JSON de cada marca.
- **stderr:** o log para gente (tempos, batidas, sons, avisos). Em caso de erro, a última linha é
  `{"ok": false, "erro": "...", "codigo": "NOME_DO_ERRO"}`. Códigos: `USO_ERRADO`, `VERSAO_INVALIDA`,
  `ARQUIVO_ILEGIVEL`, `MUSICA_ILEGIVEL`, `DISCO_CHEIO`, `FALTA_FERRAMENTA`, `FALTA_MODULO`, `COMANDO_FALHOU`,
  `RENDER_FALHOU`, `ENCODE_FALHOU`, `AUTOTESTE_FALHOU`, `MOLDE_SEM_9_16`, `VERSAO_DO_MOLDE_INVALIDA`,
  `VERSAO_DO_MOLDE_REPETIDA`, `LOTE_INCOMPLETO`, `FALTA_CLONE`, `SNAPSHOT_FALHOU`, `SNAPSHOT_INCOMPLETO`,
  `MOLDE_DIFERENTE_DO_CLONE` (os quatro últimos são do `--provar` do VoiceOS) e `FALHA_INTERNA`.
- **saída do processo:** 0 = ok, 1 = erro, 2 = uso errado.

## No Studio do HyperFrames: um campo por asset

As mesmas variáveis aparecem como campos no Studio. Abra o projeto `satellite/` no Studio
(`npx hyperframes preview` dentro da pasta, ou o app do HyperFrames): cada variável vira um campo, e trocar o
campo troca o asset no vídeo. Textos são caixas de texto, os ícones e as opções são listas, as cores têm seletor e os
fones do emoji são um liga/desliga. Três campos só ficam completos pelo `montar.py`: o **formato 9:16** (o
HyperFrames lê o tamanho do vídeo no arquivo, e quem troca para 1080x1920 é o montador), o **ritmo "batidas"** (as
batidas são calculadas pelo montador) e a **música** no vídeo final (o montador faz o corte e a mixagem). Os **sons**
(`sons` e `musica_volume`) também aparecem como campos, mas só entram no áudio pelo montador.

## O que dá para trocar

| variável | o que é | original |
|---|---|---|
| `rotulo_icone` | rótulo embaixo do ícone do app | Satellite |
| `cartao_titulo`, `cartao_tempo` | título e tempo do cartão escuro | ISS Flyover, in 14 min |
| `tile_rotulo` | rótulo do tile quadrado | Connected |
| `titulo` | título da lista (quebra sozinho em 2 linhas equilibradas, 3 se passar de 900 px) | What’s the emergency? |
| `item1` … `item5` | itens da lista, de cima para baixo. O 1 é o que o cursor clica; o 5 é o primeiro a chegar | Vehicle Issue … Fire |
| `icone1` … `icone5` | ícone de cada item: car, plus, shield, star, flame (os do original), heart, warning, lightning, house, phone, chat, user (Phosphor), ou um emoji da lista | car, plus, shield, star, flame |
| `botao` | botão vermelho do canto | End |
| `ilha_texto` | texto da Dynamic Island | Help is on the way |
| `relogio` | relógio inicial da ilha, `M:SS` (conta 2 segundos para baixo, como no original) | 1:40 |
| `balao_nome`, `balao_emoji`, `balao_fones` | nome e emoji do balão final; fones desenhados por cima do emoji | creatoroly, 🧑🏽, sim |
| `logo` | imagem redonda no lugar do emoji do balão (some com os fones). Caminho dentro de `satellite/` | vazio (emoji) |
| `cor_principal` | troca **todo o verde**: ícone, tile, pílulas, título chegando, rótulos, fundos medidos (field.js), Terra, halos e o começo da rota | #0cbc25 |
| `cor_ponto` | o ponto azul do ícone e do cartão, o ponto que voa e a ilha (abertura, timer, texto e relógio) | #0284f6 |
| `cor_rota` | a rota depois do começo (turquesa e azul) | #0067fc |
| `cor_botao` | o botão do canto | #f80207 |
| `fonte` | `sf` (SF Pro), `archivo` ou `inter` | sf |
| `formato` | `1:1` (1080x1080) ou `9:16` (1080x1920, Reels) | 1:1 |
| `musica` | arquivo de áudio dentro de `satellite/` (ex.: `assets/musica-teste.m4a`) | assets/ref-audio.m4a |
| `ritmo` | `original` (tempos medidos) ou `batidas` (cada momento começa numa batida da música) | original |
| `sons` | som por elemento: `nenhum` (só a música, como o original), `suave` (os eventos principais, 4 dB mais baixo) ou `marcado` (todo evento tem som). Ver `sons/SONS.md` | nenhum |
| `musica_volume` | volume da música quando há sons, de 0 a 1 (0,7 fica uns 3 dB abaixo). Com `sons: nenhum` não é usado | 0,7 |

### Desenho e movimento (para fazer um "irmão" do Satellite)

Mudam peças e o jeito de entrar, mas a música, os instantes em que cada momento começa e a sequência continuam os
mesmos. `versoes/irmao.json` usa todos os cinco.

| variável | original | opção nova: o que faz |
|---|---|---|
| `peca_cartao` | `arco` | `anel`: no mesmo cartão escuro, um anel de progresso que enche com o brilho e o ponto andando, com a porcentagem no centro. O enchimento segue o caminho medido do brilho do arco, então acelera e pausa nos mesmos lugares. No fim o anel encolhe e vira o ponto do tile, como o arco. |
| `peca_mapa` | `globo` | `radar`: no lugar e no tempo do globo, anéis concêntricos com uma varredura girando, no estilo do app Buscar, com pontos que acendem quando a varredura passa. Mantém o halo, a luz do cartão e o brilho que vira o tile. |
| `entrada_lista` | `cima` | `baixo`: as pílulas e o título sobem de baixo, com o mesmo escalonamento e as mesmas curvas espelhadas. A primeira pílula (a que sai da caixa cinza) termina no topo e é a que o cursor clica; as novas chegam por baixo saindo do desfoque de profundidade. |
| `entrada_titulo` | `pouso` | `desfoque`: cada palavra aparece no lugar, saindo desfocada e 12 % maior até ficar nítida, no mesmo ritmo palavra a palavra. |
| `mola` | `suave` | `firme`: cada entrada (ícone, cartão, tile, lista, título, botão, ilha e balão) começa no mesmo instante, chega mais rápido e assenta em 60 % do tempo. É o tempo do próprio movimento medido, comprimido. Câmera, rota, varredura, ponteiro e relógio continuam no tempo original. |

**Como a cor troca.** A paleta medida do clone gira de matiz no espaço OKLCH em direção à cor nova. A cor de
referência (`#0cbc25`, o disco do ícone) cai exatamente na cor nova; as outras guardam a luminosidade e a saturação
relativas, então os fundos claros continuam claros e os escuros continuam escuros. Só os verdes giram com
`cor_principal` (matiz OKLCH entre 115° e 185°); turquesa, azul, vermelho e cinza ficam.

**Como o layout acompanha o texto.** Tudo é medido pela fonte, sempre "novo menos original", por isso o original
nunca se mexe. Pílula, botão, ilha e balão crescem com o texto (o balão mantém o bico no centro). O título quebra
em linhas equilibradas e os emojis ⚠️ acompanham as bordas das linhas. Cartão, tile e rótulo do ícone diminuem a
letra se o texto não couber. Pílula passa de 1040 px só diminuindo a letra.

## Ritmo pela música

Com `"ritmo": "batidas"`, cada um dos **8 momentos** começa numa batida da música:

| momento | começa no clone (quadro) | entrada que fica intacta |
|---|---|---|
| ícone | 5 | 19 quadros |
| cartão | 30 | 21 |
| tile | 86 | 22 |
| lista | 127 | até 63 (corta onde o título começa) |
| título | 155 | 35 |
| rota | 194 | 19 |
| ilha | 213 | 42 |
| balão | 277 | 23 |

Como funciona, em português simples:

1. O `montar.py` acha a **grade de batidas** da música: mede onde o som "ataca" (fluxo espectral) e procura a régua
   regular (pulso entre 0,25 e 0,5 s) que mais cai em cima desses ataques, com tolerância de 23 ms por batida.
2. Cada momento vai para a **batida mais próxima** da grade, sem trocar a ordem e sem colar dois momentos. No empate,
   vai para a batida de depois.
3. A **entrada** de cada momento (os quadros da mola) anda na velocidade original, então as molas não mudam.
   Só o **meio** do momento (o trecho parado ou lento até o próximo) estica ou encolhe. O vídeo continua com 10,93 s.
4. Isso vira uma tabela "quadro de saída → quadro do clone" (`ritmo.js` na cópia de render). O motion blur acompanha:
   onde o tempo anda mais rápido, o borrão fica maior.

O `npx hyperframes beats` não serviu aqui: ele acha as batidas da música inteira (118 s), mas não acha nenhuma em
trechos de 11, 20 ou 40 s. A análise em Python foi conferida contra ele na música inteira: diferença média de
0,4 quadro. Na trilha do Joi ela dá 135,9 por minuto (a medida do clone era 136).

**Música de teste:** a medição abaixo usou uma música de teste interna, de licença não verificada, que não vai no
repositório. Para usar o ritmo, ponha a tua música em `molde/assets/` e aponte o campo `musica` para ela.

**Onde caíram as batidas** (`versoes/irmao-vertical.json`): pulso de 0,326 s (184 por minuto, colcheias de ~92),
primeira batida em 0,175 s. Batidas nos quadros 5 15 25 35 44 54 64 74 83 93 103 113 123 132 142 152 162 172 181 191
201 211 220 230 240 250 260 269 279 289 299 308 318.

| momento | clone | saída | desvio | meio |
|---|---|---|---|---|
| ícone | 5 | 5 | 0 | 0,55x (mais lento) |
| cartão | 30 | 35 | +5 | 1,30x |
| tile | 86 | 83 | -3 | 1,06x |
| lista | 127 | 123 | -4 | 0,80x |
| título | 155 | 152 | -3 | 1,00x |
| rota | 194 | 191 | -3 | 0,80x |
| ilha | 213 | 211 | -2 | 0,85x |
| balão | 277 | 279 | +2 | 1,08x |

Música mais curta que o vídeo repete; mais longa é cortada em 10,93 s, sempre com 0,5 s de fade no fim. A música
original do Satellite segue copiada sem recodificar.

## Fonte

`"fonte"` troca a família de todos os textos: `sf` (SF Pro do sistema), `archivo` (a fonte da marca do Júnior) ou
`inter`. Os pesos por função continuam os medidos no clone: título 550, pílula 500, botão 590, texto da ilha 500,
relógio 400, cartão 500, rótulo 600. Archivo e Inter são fontes variáveis, então esses pesos saem exatos.

O layout é refeito pelo texto na fonte nova, comparado com o texto original em SF Pro: se a Archivo deixa
"juniorheusser" mais largo, o balão cresce; se a palavra cabe, nada muda. A linha de base de cada texto fica no
mesmo lugar do clone (cada fonte tem sua altura de ascendente e descendente, e o molde compensa a diferença).

Arquivos: `assets/fonts/Archivo.ttf` (Copyright 2020 The Archivo Project Authors, SIL Open Font License 1.1) e
`assets/fonts/Inter.ttf` (Copyright 2016 The Inter Project Authors, SIL Open Font License 1.1), as duas copiadas
de pastas locais.

## Formato 9:16

Com `"formato": "9:16"` o vídeo sai em 1080x1920. Não é o quadrado esticado: a cena inteira (cartão, lista, rota,
ilha e balão) fica centralizada na faixa segura dos Reels, entre y 220 e y 1280 (os 220 px de cima e o terço de baixo
ficam livres de texto importante), e os fundos medidos (o verde da abertura, o lavado verde e o lavado azul do fim)
esticam a partir do centro da cena até ocupar a tela toda. O que antes saía do quadrado (pílulas entrando e saindo
desfocadas, cursor subindo, ilha subindo no fim) agora aparece nas faixas de cima e de baixo, sempre desfocado ou de
passagem. No lado a lado, o original é posto na mesma faixa para comparar.

## Kit de marca

Um kit é um arquivo `marcas/<cliente>/marca.json` (formato novo, com a pasta do cliente) ou `marcas/<nome>.json`
(formato antigo); os dois valem:

```json
{
  "cor_principal": "#E54A26",
  "cor_destaque": "#0284f6",
  "fonte": "archivo",
  "nome": "juniorheusser",
  "logo": "assets/logo-cliente.png",
  "creditos": {"fonte Archivo": "autor e licença", "logo": "autor e licença"}
}
```

- Obrigatórios: `cor_principal`, `fonte` e `nome` (o nome do balão final). Opcionais: `cor_destaque` (troca o ponto,
  a ilha e a rota; sem ela fica o azul do estilo), `logo` (imagem dentro de `satellite/`, entra no lugar do emoji) e
  `creditos` (autor e licença de cada asset da marca, no próprio arquivo).
- A versão aponta para o kit com `"marca": "marcas/junior.json"`, ou o comando escolhe com `--marca <nome ou caminho>`
  (`--marca` vence a `"marca"` da versão, então não é preciso um arquivo de versão por cliente). Um nome (`junior`,
  `padaria-exemplo`) é procurado em `marcas/` da pasta da versão, da pasta atual e da raiz do produto, nos dois formatos; um
  caminho pode ser relativo (à pasta da versão, à pasta atual ou à raiz do produto) ou absoluto, do arquivo ou da pasta do
  cliente. A ordem é **versão, depois marca, depois molde**: o que estiver escrito na versão vence o kit, e o que
  nenhum dos dois disser fica no padrão do molde.
- O kit também vale no Joi (`cor_principal`) e no VoiceOS (`cor_principal` vira `cor_destaque`). Fonte e nome não
  existem nesses moldes: o resumo avisa que ficaram de fora.
- Quem vende um estilo próprio troca só o kit do cliente e mantém o estilo inteiro.

`marcas/junior.json` tem #E54A26, Archivo, juniorheusser e o crédito da Archivo. Sem `cor_destaque`, o ponto e a ilha
continuam no azul do Satellite, como na `versoes/junior.json`.

## Versão do molde

`satellite/MOLDE.json` guarda `"versao": "satellite-v2"` (a v2 entrou com a camada de som) e a `"impressao_digital"`
(sha256 de cada arquivo do molde). A cada render o montador confere: se algum arquivo do molde mudou sem virar versão
nova, ele **avisa** no log e no resumo (não bloqueia) e diz quais arquivos mudaram. Quando a mudança é para ficar:

```
python3 montar.py --molde satellite --travar satellite-v3   # ou sem o nome: o próximo número
python3 montar.py --registrar-molde satellite-v3                    # o mesmo, pelo caminho antigo
```

Ele recusa registrar um conteúdo novo com o mesmo nome de versão. Joi e VoiceOS usam o mesmo comando
(`--molde joi --travar`), com o `MOLDE.json` ao lado da pasta `molde/`.

## O que ainda não dá para trocar, e por quê

- **Sequência e tempos de cada momento.** São as curvas medidas quadro a quadro da referência (`tracks.js`). As opções
  de desenho, movimento e ritmo variam em cima delas; uma sequência nova é um clone novo.
- **Duração.** Sempre 10,93 s, mesmo no ritmo "batidas" (o fim é fixo; o meio do balão estica ou encolhe).
- **Rota, ilha e balão** não têm peça alternativa ainda (só a mola firme muda a entrada da ilha e do balão).
- **Quantidade de itens.** Sempre 5: cada pílula tem a sua trilha medida de chegada.
- **Desenhos fixos:** o ícone do app (disco com o cone azul), o satélite da ISS e do tile, o mapa das Américas,
  a forma da rota, os ⚠️ do título e a ambulância 🚑. Só a cor deles segue as variáveis.
- **Azuis que não são o "ponto":** o balão do iMessage, o arco e o texto azul do cartão, o oceano e o lavado azul do
  fim. E o vermelho da trilha da ambulância.
- **SF Pro e emojis** são do sistema, licença Apple, só para estudo. Não publicar fora deste Mac com `fonte: sf` nem
  com emojis (a Archivo e a Inter são livres).
- **Formatos.** Só 1:1 e 9:16 (4:5 e 16:9 não).
- **Relógio.** Conta só dois segundos (1:40 → 1:39 → 1:38) como no original, e a dezena troca no meio do rolamento no
  quadro 243 (vem do clone; ficou para o padrão sair idêntico).
- **Textos muito longos.** Pílula, botão, ilha e balão crescem; acima de ~3 linhas de título ou de uma pílula com mais de
  ~45 letras o texto fica pequeno ou aperta. Conferir na folha de quadros.
- **Música com tempo que muda muito.** A grade é regular; uma música que acelera ou desacelera no trecho fica com os
  últimos momentos fora da batida.

## Prova: com os padrões, o molde é o clone

- Prévia (30 fps, sem motion blur): o molde com `versoes/original.json` e o clone sem alteração renderizados com o
  mesmo comando dão **o mesmo arquivo mp4 (md5 igual)**. Refeito depois de entrarem fonte, formato, ritmo, música e
  logo: os dois dão `83f2d7b8c193a28cd645e527cec62c0b`. Cada controle novo, no padrão, toma o mesmo caminho de código do
  clone.
- A saída `original-previa.mp4` do montador (vídeo encodado com a música) dá `877170713ecc12ba4889e671dc0250f5` antes e
  depois da camada de som, e de novo depois da junção dos três montadores (22/10), tanto pelo `montar.py --molde satellite` da
  raiz quanto pelo invólucro `montar.py`.
- Final (240 fps + tmix): `saidas/original.mp4` contra o render v6 do clone (fora do repositório) dá diferença
  média de 0,17 em 255 por pixel (PSNR 50,9 dB), que é ruído de encode (crf 12 aqui, crf 16 lá). Para comparar: os
  dois encodes do próprio clone (`final.mp4` e `hq/satellite-replica-1080.mp4`) diferem 0,37 entre si.
- Todas as versões guardadas (`versoes/*.json`) passam no autoteste do `montar.py`.

## Tempo de render (este Mac, `--workers 1`)

- Prévia 1:1: ~25 a 40 s de render, ~1,5 a 2 min no total com lado a lado e folha.
- Prévia 9:16: 38 s de render, 3 min no total (o lado a lado 2160x1920 em veryslow pesa).
- Final 1:1 com motion blur: 2 min 20 s a 2 min 40 s de render a 240 fps, 3 a 4,5 min no total
  (`junior-marca`: 140 s de render, 3 min 32 s no total).
- Final 9:16 com motion blur (`irmao-vertical`): 170 s de render, 4 min 15 s no total.
- Pelo montador único (22/10): prévia 1:1 de `original.json`, 23 s de render e 36 s no total; final 1:1 da
  `junior-marca` com `--marca padaria-exemplo --video`, 113 s de render e 2 min 7 s no total; lote de 3 marcas em prévia,
  1 min 33 s.
