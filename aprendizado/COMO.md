# Como o Apple Style UI aprende, e por que ele nunca anda para trás

Cada vídeo que tu aprovas ensina o motor: as cores, as fontes, as molas, as peças que tu mais escolhes e os números
dos clones que ficaram bons. Isso vira o teu **perfil de estilo**. O perfil tem uma trava, a **catraca**: um vídeo
novo não entra se ficou pior que o anterior, e um aprendizado novo não entra se estragar o que já funcionava.

Tu não precisas pensar na forma. São dois comandos no dia a dia: `aprovar` e `travar`.

## O dia a dia

Rode de dentro de `aprendizado/` (na raiz do produto).

**1. Terminou um vídeo? Mande aprovar.** O portão confere tudo sozinho antes de qualquer registro.

```
python3 aprender.py aprovar ../saidas/cliente-x.mp4 --tipo versao --nota "Cliente aprovou na primeira"
python3 aprender.py aprovar <clone>/saidas/final.mp4 --tipo clone --nota "Clone fechado"
```

- `--tipo` é `clone`, `versao` (uma versão do molde) ou `video-novo` (um vídeo novo feito num molde).
- Numa versão, o arquivo de variáveis é achado pelo nome do vídeo (`saidas/cliente-x.mp4` usa `versoes/cliente-x.json`).
  Se não for assim, passe `--versao`. O molde padrão é o Satellite (`../satellite`); os outros dois vão em `--molde`:
  `--molde ../joi/molde` ou `--molde ../voiceos/molde`.
- Ainda não viu o vídeo, ou o cliente ainda não respondeu? Use `--pendente`: ele passa pelo portão e fica esperando.
  Quando for aprovar de verdade, rode o mesmo comando sem `--pendente`.

**2. Aprovou? Leia a revisão e dê o ok.** O perfil nunca muda sozinho. O `aprovar` escreve a `REVISAO.md` com o que
mudaria no perfil e por quê. Se estiver de acordo:

```
python3 aprender.py travar
```

Isso cria a próxima versão travada do perfil (`perfil-v1`, `perfil-v2`...). Antes de travar, a catraca roda de novo.

**3. Quer ver como está?**

```
python3 aprender.py perfil    # o perfil em vigor (só mostra: nunca aprova nada)
python3 aprender.py lista     # cada vídeo e o estado dele: aprovado, pendente ou quarentena
python3 portao.py ../saidas/cliente-x.mp4 --tipo versao   # só conferir, sem registrar nada
```

## O que a catraca bloqueia

Se qualquer item abaixo falhar, a resposta é **REPROVOU**, com os motivos em português, e nada entra no perfil.
A decisão fica anotada no projeto, com o motivo.

| em | o portão confere | por quê |
|---|---|---|
| clone | a distância visual e a correlação de movimento (do `compare.py`) não ficam piores que as do melhor clone aprovado, com uma folga de 0,008 e 0,02 | um clone novo não pode sair abaixo do melhor que já existe |
| clone | o pico de movimento de cada cena fica a no máximo 1 quadro da referência | o tempo é o que faz o movimento parecer Apple |
| versão | o molde, com os valores padrão, continua sendo o clone original. No Satellite, a prévia é comparada quadro a quadro com a do clone. No Joi e no VoiceOS, que não renderizam igual bit a bit duas vezes, vale a versão travada do molde (`MOLDE.json`, gravado pelo `montar.py --travar` depois da prova dele) | se isso quebrar, alguém mexeu no molde e todas as versões podem ter mudado |
| versão | o `check` do HyperFrames não acusa erro de código | render inválido não entra |
| versão | o vídeo tem a mesma quantidade de quadros e a mesma duração do molde | vídeo cortado ou esticado |
| versão | nenhum texto sai da própria caixa (pílula, botão, ilha, cartão) e nenhum fica pequeno demais para ler no celular | o texto é medido no navegador, com as variáveis entregues do mesmo jeito que o render entrega, nos momentos da folha de cada molde (9 no Satellite e no VoiceOS, 10 no Joi), e comparado com o molde nas mesmas peças com os textos originais. Só conta o que a versão piorou |
| versão | o motion blur está lá | um final sem blur parece barato; uma prévia mandada por engano é pega aqui |
| versão | as cores estão na paleta da versão (as do molde mais as escolhidas) | uma cor que não foi escolhida, ou um verde que devia ter virado laranja |
| perfil | ao aprovar e de novo ao travar, cada versão já aprovada cujo molde mudou (arquivos do molde ou versão do HyperFrames) é re-renderizada em prévia e tem que sair idêntica. Se o molde não mudou, a saída também não muda e nada é renderizado | um aprendizado novo não pode estragar o que já funcionava |
| perfil | as versões travadas conferem com a impressão digital (sha256) | se alguém editou um perfil travado à mão, o portão avisa que ele perdeu a integridade |

**Quarentena.** Quando um vídeo passa no portão mas o molde atual mudou alguma versão já aprovada, ele fica em
quarentena e o perfil não muda. Se a mudança no molde foi de propósito, aprove de novo as versões que mudaram (a
prévia nova vira a régua delas) e depois o vídeo que ficou em quarentena.

## Onde fica cada coisa

**No projeto** (a pasta do clone ou do motor, ou a que vier em `--projeto`):

- `.apple-style-ui/decisoes.jsonl`: cada decisão sobre aquele vídeo, uma por linha (o arquivo só cresce): aprovado,
  pendente, quarentena ou reprovado, com os motivos, as medidas, a nota e quem decidiu. O `decisoes.json` do formato
  antigo (uma lista reescrita) continua sendo lido antes das linhas novas. Para ver tudo:
  `python3 aprendizado/aprender.py decisoes --projeto <pasta>`.

**Na máquina**, em `~/.apple-style-ui/perfil/` (vale para todos os vídeos):

- `aprovados.jsonl`: um item por linha, o mais novo de cada vídeo vale: tipo, molde, arquivo e valores da versão,
  mp4, notas do `compare.py`, nota humana, data, quem e status (aprovado, pendente ou quarentena);
- `previas/`: a impressão de cada quadro da prévia de cada versão aprovada (a régua da regressão). O registro guarda
  também a impressão digital do molde no dia da aprovação;
- `REVISAO.md`: a revisão esperando o ok, quando houver;
- `perfil-v1/`, `perfil-v2/`...: as versões travadas, só leitura. Cada uma tem `perfil.json`, `APRENDIZADOS.md`
  (a nota humana e o `LESSONS.md` de cada aprovado, com a origem), a `REVISAO.md` que recebeu o ok e
  `impressao_digital.json` (o sha256 de cada arquivo).

**Nesta pasta:** `portao.py`, `aprender.py`, este `COMO.md` e `regressao/satellite-original.txt` (a prévia do clone
original, quadro por quadro, que o molde tem que reproduzir com os padrões).

Para testar sem mexer no perfil de verdade, aponte para outra pasta: `ASUI_PERFIL=/outra/pasta python3 aprender.py ...`
(com `ASUI_TRABALHO=/outra/pasta`, os renders do portão também vão para lá).

**Os testes da catraca** moram em `apple-style-ui/aprendizado/testes/testes.sh` (uns 27 min, `zsh testes.sh`). Rodam numa
pasta temporária própria, com um perfil de teste, e conferem os quatro casos: padrões idênticos passam (e a prévia de
`original.json` dá o md5 de sempre), pílula estourada reprova por texto, molde alterado reprova ("o molde mudou") e o
botão 20 % maior manda o próximo aprovado para a quarentena.

## O que o perfil guarda

- **cores**: cada variável de cor e quantas versões aprovadas usaram cada valor;
- **fontes**: as famílias usadas nos moldes e clones aprovados;
- **molas**: a mola de cada versão aprovada (suave ou firme);
- **controles**: as peças, entradas, ícones e liga/desliga escolhidos, do mais usado para o menos usado;
- **clones** e **regua_dos_clones**: os números de cada clone aprovado e a régua que o próximo clone tem que bater.

Os textos das versões não entram: são conteúdo do cliente, não estilo.

## Para quem vende um estilo próprio

O editor que aplica o mesmo estilo (Apple, vidro, dadaísmo) à marca de cada cliente usa assim: cada cliente é uma
versão, aprovada quando o cliente aprova. O perfil acumula o que se repete nos aprovados, e a catraca garante que o
vídeo do próximo cliente não sai com texto cortado, sem blur, com cor errada ou com o molde quebrado.

## Saída para outros programas

Os dois comandos respondem com um único JSON no stdout:

```
{"ok": true, "resumo": "frase em português", "proximo": {"comando": "...", "motivo": "...", "precisa_de_voce": false}, ...}
```

Os campos seguintes trazem os detalhes (`portao`, `decisoes`, `revisao`, `perfil`, `itens`). Em erro, `ok` é `false`
e o stderr traz uma linha `{"ok": false, "erro": "...", "codigo": "NOME_DO_ERRO"}`. Os códigos de saída são três:
0 (ok), 1 (erro) e 2 (uso errado). Nomes de erro: `REPROVADO_NO_PORTAO`, `QUARENTENA`, `REGRESSAO`,
`REVISAO_DESATUALIZADA`, `VIDEO_NAO_ENCONTRADO`, `SEM_ESPACO`, `RENDER_FALHOU`, `CHECK_FALHOU`, `COMANDO_FALHOU`,
`FALTA_PROGRAMA`, `FALTA_MONTAR`, `FALTA_ORIGINAL`, `FALTA_ANALISE_DA_REFERENCIA`, `VERSAO_JA_EXISTE`, `USO_ERRADO`
e `DEFEITO_INTERNO`.

## Limites que já se sabe

- **"Melhor" não se mede sozinho numa versão.** Se o molde mudou uma versão aprovada, ela vai para quarentena mesmo
  que tenha ficado mais bonita. Quem decide é a pessoa.
- **Régua entre clones diferentes.** O clone novo é comparado com o melhor clone aprovado, mesmo de outra referência,
  por isso a folga existe. Uma rodada nova do mesmo clone não é comparada com a rodada anterior dele.
- **A conferência de cores conhece a faixa dos verdes que giram com `cor_principal`.** Um molde sem `cor_principal`
  só confere contra as cores do molde e as escolhidas.
- **Joi e VoiceOS não repetem o render bit a bit** (ver as NOTAS.md deles). Por isso, neles, a prova de que o molde
  ainda é o clone vem da versão travada do molde. Pelo mesmo motivo, se o molde deles mudar depois de uma versão
  aprovada, a regressão sempre acusa diferença e a versão vai para quarentena: alguém tem que olhar.
- **Fotos próprias no VoiceOS** (`foto_ceu`, `foto_vinhedo`) não foram testadas no portão: a prévia da versão é
  renderizada numa cópia do molde e o caminho da foto pode não chegar até ela.
- **Tempo.** Uma versão do Satellite leva cerca de 2 minutos no portão (duas prévias e dois checks). No Joi e no
  VoiceOS é uma prévia só (a régua é a versão travada do molde), mas a 60 fps. A regressão só renderiza quando o
  molde mudou.
- **Blur do Joi.** O final do Joi tem menos blur (4 subquadros a 60 fps): mede 2,4x contra o mínimo de 1,6x. Um final
  sem blur mede 1,0x.
- O portão usa do `montar.py` ao lado do molde: `validar`, `render`, `HF`, `FPS` e `MOMENTOS`.
