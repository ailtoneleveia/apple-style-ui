# Estrutura do repositório

O nome é **Apple Style UI**; o identificador é `apple-style-ui`. Ele mora em `.claude-plugin/plugin.json`, e o
`marketplace.json` repete o `name` porque o Claude Code exige. O comando de entrada sai dele: `/apple-style-ui:video`.
No código, o nome é uma constante só: `NOME = "apple-style-ui"` no `montar.py`. Dela saem a pasta da máquina
(`~/.apple-style-ui/`) e a de bastidor (`.apple-style-ui/`, no vídeo e no clone). A sigla `ASUI_` fica só nas
variáveis de ambiente.

## O repositório (o próprio repositório é o marketplace)

```text
apple-style-ui/
├── .claude-plugin/        plugin.json e marketplace.json
├── SKILL.md               o comando de entrada, /apple-style-ui:video (os 4 caminhos)
├── README.md              uma tela
├── ESTRUTURA.md           este arquivo
├── LICENCAS-DE-TERCEIROS.md
├── montar.py              o montador único dos moldes de interface (Satellite, Joi e VoiceOS)
├── moldes/                só o formato de cada vídeo: estrutura, campos e padrões
│   ├── satellite/         molde/ (projeto HyperFrames, com o sons.json), montar.py (invólucro), NOTAS.md, versoes/,
│   │                      MOLDE.json (a versão em vigor) e versoes-travadas/<molde>-vN/ (uma pasta por versão, só leitura)
│   ├── joi/               idem
│   ├── voiceos/           idem
│   ├── fala-destaque/     pessoa falando com a palavra em destaque: index.html, montar.py, NOTAS.md, exemplo/ (Pexels)
│   └── pecas_livres.py    gera as peças livres que ocupam o lugar dos recortes e do áudio do original
├── estilo/                estilo.js, ESTILO.md, teste.js, render.sh, demo/ e medidas/: as molas e a caixa que se transforma
├── clonar/                o kit de clonagem com prova: clonar.py, caso.py, scripts/, modelo/, testes/, CLONAR.md
├── biblioteca/            a lista curada (README.md), fichas/, prompts/, site/ (a galeria), GLOSSARIO.md e o classificador
├── aprendizado/           portao.py, aprender.py, COMO.md, regressao/ e testes/ (a catraca)
├── sons/                  o pacote de sons CC0 (SONS.md, CREDITOS.md, sons.json, fazer_pacote.py)
├── marcas/                kits de exemplo: junior/, padaria-exemplo/ (com logo.png e ORIGEM.md), salao-exemplo/ (cada um com marca.json)
└── exemplos/              satellite.mp4, joi.mp4, voiceos.mp4 e o <molde>-ORIGEM.md de cada um
```

Fora do repositório:

```text
~/.apple-style-ui/         a máquina: perfil/ (o perfil de estilo), venv/ (o Python do kit de clonagem),
                           biblioteca/ (os vídeos baixados da biblioteca), originais/ (os vídeos dos clones, se tu tiver)
<pasta de trabalho>/       onde tu abre o Claude Code
├── marcas/<cliente>/      marca.json, logo + ORIGEM.md, videos/<video>/
│   └── videos/<video>/    PEDIDO.md, versao.json, saidas/, .apple-style-ui/ (bastidor: versão resolvida, decisoes.jsonl, logs)
└── clone-<nome>/          referencia/, RAIOX.md, FICHA.md, hf/, rodadas/, saidas/, LICOES.md, .apple-style-ui/
```

`marcas/` aparece nos dois lugares com o mesmo formato: no repositório ficam só os kits de exemplo; os kits de cliente
ficam na pasta de trabalho. O plugin nunca grava na própria raiz (ela muda a cada atualização).

## Comandos

- **Um de entrada:** `/apple-style-ui:video` (o `SKILL.md`). Pergunta o caminho e roda os scripts. Atalhos pelo
  argumento: `/apple-style-ui:video começar`, `clonar <link>`, `igual <link>`, `galeria`.
- **Por baixo:** `montar.py` (o montador dos três moldes de interface; os `moldes/<molde>/montar.py` são invólucros de
  3 linhas), `moldes/fala-destaque/montar.py` (chamado pelo `clonar/caso.py aplicar`), `aprendizado/portao.py`,
  `aprendizado/aprender.py` (`aprovar`, `travar`, `perfil`, `lista`, `decisoes`) e os de `clonar/` (`clonar.py`, `caso.py`).
  Todos respondem `{ok, resumo, proximo}` no stdout; erro no stderr com `codigo`. Saída 0 = ok, 1 = erro, 2 = uso errado.

## O que não vai no repositório, e o que entra no lugar

| fica fora | no lugar |
|---|---|
| SF Pro | o montador copia a do sistema (`/System/Library/Fonts/SFNS.ttf`) para a cópia de render; sem ela, ou com `ASUI_FONTE_LIVRE=1`, a Inter |
| emojis da Apple | os do sistema, na hora do render (nenhum arquivo de emoji vai junto) |
| áudio dos originais e a música de teste | `assets/silencio.m4a` em cada molde; o pacote de sons CC0 por cima (`"sons"`) |
| recortes do Joi e do VoiceOS (objetos, céu, vinhedo, ícones, memoji) | peças livres de `moldes/pecas_livres.py`, com o mesmo nome e tamanho |
| vídeos dos clones (lado a lado) | `~/.apple-style-ui/originais/<molde>.mp4`; sem ele, sai só a versão |
| vídeos e miniaturas da biblioteca | só o link do original, com crédito (`ASUI_MINIATURAS=1` gera as miniaturas na tua máquina) |
| vídeo da pessoa do nº 5 e a voz sintética | o vídeo do Pexels (`moldes/fala-destaque/exemplo/`) e a tua gravação |
| chaves e `.env` | o `.env` fica na pasta de trabalho (a `GROQ_API_KEY` da transcrição) |

## Limites conhecidos

- **A régua do portão é deste Mac.** `aprendizado/regressao/<molde>-original.txt` guarda o md5 e uma miniatura de cada
  quadro. A do Satellite saiu da prévia do clone; a do Joi e a do VoiceOS foram refeitas com as peças livres. A
  tolerância (16 em 255 na miniatura) foi calibrada só aqui: falta medir numa máquina de fora.
- **O verde padrão reprova por cor.** Com a `cor_principal` padrão do Satellite, o portão acusa matiz de 160° fora da
  paleta na própria versão original. Uma versão com outra cor não sofre disso. Conserto: igualar as duas faixas em
  `fora_da_paleta` (portao.py).
- **Portão de clone** procura `reference/analysis/` ao lado do mp4 (o formato antigo de clone); o desenho novo usa
  `referencia/`.
- **Resolvido (30/10): decisões em jsonl.** Cada decisão do vídeo é uma linha nova em `.apple-style-ui/decisoes.jsonl`
  (o arquivo só cresce). O `decisoes.json` antigo (a lista reescrita) continua sendo lido antes das linhas novas e não é
  mais escrito: `python3 aprendizado/aprender.py decisoes --projeto <pasta do vídeo>`.
- **Resolvido (30/10): versão travada em pasta numerada.** `montar.py --molde <molde> --travar` grava o `MOLDE.json` (a
  versão em vigor) e congela uma cópia do molde em `moldes/<molde>/versoes-travadas/<molde>-vN/`, com o registro dela e
  os arquivos só leitura. Uma pasta que já existe nunca é reescrita (o nome repetido é recusado). Uma versão que pede um
  molde antigo (`"molde": "joi-v1"`) sai com a pasta congelada dele. As versões anteriores às pastas (satellite-v2,
  joi-v1, voiceos-v1) foram congeladas do estado em que estavam travadas.
- **Resolvido (30/10): logo fora do molde.** O logo vem do kit (`marcas/<cliente>/logo.png`, relativo à pasta do kit),
  da versão ou de um caminho absoluto; o montador e o portão copiam para `assets/var/` da cópia de render.
- **Resolvido (30/10): Joi e VoiceOS** têm o kit de marca completo (cor, nome, fonte e logo) e sons por elemento
  (`sons/SONS.md`). Os dois não têm o campo `musica`: a trilha deles é o silêncio do molde, e a loudness alvo só vale
  quando há música de verdade.
- **O molde fala-destaque** ainda não passa pelo portão (`aprender.py`): termina com o vídeo e a pergunta de aprovação.
