---
name: video
description: Porta de entrada do produto. Pergunta qual dos 4 caminhos a pessoa quer (começar, só clonar, vídeo igual a uma referência, achar uma referência), roda os comandos reais dos moldes, da clonagem e da catraca e termina sempre com o próximo passo. Use quando alguém quiser um vídeo estilo Apple, trocar a marca de um molde, clonar um vídeo ou escolher uma referência.
---

# Porta de entrada

Caminho de script é relativo à raiz do produto, `${CLAUDE_PLUGIN_ROOT}` (prefixe ao rodar, entre aspas).
Arquivo da pessoa fica no diretório atual, nunca na raiz.

## Regras
- Responda sempre no idioma do pedido, do começo ao fim, inclusive nos avisos de andamento e no resumo final.
  Pedido em português: português simples, "tu", sem travessão. Os scripts, os logs e este arquivo estarem em parte em
  inglês não muda isso. Toda resposta termina com **Próximo passo:** e um comando ou uma pergunta.
- Comando longo (render, `montar.py`, `clonar.py rodada` e `final`) roda em primeiro plano, com o tempo limite do
  comando no máximo (10 min). Se mandar algo para o segundo plano, espere no mesmo comando até acabar (`wait`, ou um
  laço que confere o arquivo). Nunca termine o turno com processo pendente: sem ninguém do outro lado, o aviso de fim
  nunca chega e o trabalho para.
- Sem o vídeo do clone original, não sai o lado a lado e a folha mostra só a versão. No repositório público isso é o
  esperado: o original não vai junto, por direito autoral. Não é falha; diga isso em uma frase e siga.
- Os scripts devolvem JSON `{ok, resumo, proximo}` no stdout. Leia o `resumo` para a pessoa e use o `proximo`.
  Erro vem no stderr com `codigo`: explique em uma frase e diga o conserto.
- Render sempre um por vez (o `montar.py` já usa `--workers 1`, e o `--lote` roda uma marca por vez). Nada é publicado nem enviado.
- Pergunte antes de instalar programa, gastar API, apagar ou mover arquivo da pessoa. Nunca sobrescreva:
  antes de trocar um arquivo dela, copie com a data no nome, ao lado.
- Não há comando separado para preparar a máquina ou ver em que pé está: se perguntarem, olhe a pasta do
  vídeo e `python3 aprendizado/aprender.py lista` e responda com o próximo passo.
- O que é da máquina mora em `~/.apple-style-ui/` (perfil de estilo, ambiente Python, biblioteca, vídeos dos clones).
  Nada é gravado dentro de `${CLAUDE_PLUGIN_ROOT}`: ela muda a cada atualização.

## Onde as coisas ficam (a pasta nasce quando precisa)
- Kit de marca: `marcas/<cliente>/marca.json` com `cor_principal` (#rrggbb), `fonte` (`inter`, `archivo` ou `sf`)
  e `nome`; opcionais `cor_destaque` e `creditos`. Modelo: `marcas/salao-exemplo/marca.json` (na raiz do produto).
- Um vídeo: `marcas/<cliente>/videos/<video>/` com `PEDIDO.md` (o pedido em texto e o molde usado),
  `versao.json` (os campos), `saidas/` (o que a pessoa abre) e `.apple-style-ui/` (bastidor: JSON, logs, decisões).
- **Som** (decisão do Júnior): todo vídeo novo no Satellite, o único molde com sons por elemento, leva no
  `versao.json` `"sons": "marcado"` quando o vídeo não tem fala, e `"sons": "suave"` quando tem narração ou pessoa
  falando. A pessoa troca com essa linha. Não mexa no padrão do molde (`"nenhum"`): é ele que mantém a prova de md5
  do original.

## Começo
Se a pessoa não disse o caminho nem mandou link ou arquivo junto do comando, pergunte:
"O que tu quer? 1. Quero começar 2. Quero só clonar 3. Quero um vídeo igual a esta referência 4. Quero uma referência".

**Texto que veio da galeria** (botão "Copiar para o Claude"). Reconheça pelo começo e vá direto ao caminho, sem perguntar:
- `igual <link>` + "Já existe molde para esta referência": caminho 3, ramo **Tem molde**. O molde sai do código do link:
  `DWWQEOmDfsf` = satellite, `DPJJwcujV0X` = joi, `DafsqUut4x1` = voiceos, `DaIOD8QSEAz` = fala-destaque (ramo da
  pessoa falando). Pergunte só a marca, os textos e a cor.
- `clonar <link>` + "Roda o ciclo de clonagem com nota": caminho 2 com esse link (o aviso de custo continua valendo).
- Começa com "Faça este vídeo usando o estilo calibrado" seguido do prompt da ficha: não há molde nem clone dessa
  referência. Leia o prompt, avise que sai um vídeo novo no estilo (não uma cópia medida) e monte em HyperFrames com
  as molas, as entradas, o obturador e o motion blur do `estilo/estilo.js` (veja `estilo/ESTILO.md`), render com
  `--workers 1`. Para ter nota de fidelidade, ofereça o caminho 2 com o link do prompt.

## 1. Quero começar (primeira vez, uns 5 minutos)
1. Máquina: `command -v ffmpeg node npx python3 && python3 -c "import numpy, PIL"`. Se faltar algo, ofereça
   `brew install ffmpeg node numpy pillow` e rode com o ok (leva alguns minutos). Sem `brew`: a própria pessoa
   instala pelo brew.sh, porque pede a senha do Mac. Avise: o 1º render baixa o HyperFrames e um Chrome (~300 MB).
2. Mostre os exemplos: `open exemplos/satellite.mp4 exemplos/joi.mp4 exemplos/voiceos.mp4` (feitos com a Inter,
   sem música e com o pacote de sons livre; o teu sai com a SF Pro do teu Mac se tu escolher `fonte: sf`).
   Diga que o primeiro vídeo sai no molde do Satellite (o único em que o kit troca cor, fonte e nome; no Joi ele troca
   a cor e o nome, que vai no rótulo do ícone; no VoiceOS, só a cor).
3. Pergunte o nome que aparece no balão final (ex.: @dela) e a cor da marca (#rrggbb). Fonte: `inter`, se ela não escolher.
   Avise que os textos continuam os do exemplo (o Satellite em português): trocar os textos é o caminho 3.
4. Na pasta atual, crie `marcas/<cliente>/marca.json` e a pasta `marcas/<cliente>/videos/primeiro/` com `PEDIDO.md`
   ("primeiro vídeo, molde satellite-v2") e `versao.json` = cópia de `moldes/satellite/versoes/junior-marca.json`
   com `"marca": "../../marca.json"` (o kit do cliente, relativo à pasta do vídeo), `"molde": "satellite-v2"` e
   `"sons": "marcado"` (o exemplo não tem fala; veja **Som**).
5. Final direto, sem prévia (o portão confere texto e layout):
   `python3 montar.py <video>/versao.json --video <video>`
   Uns 2 a 3 min. Enquanto roda, conte o que vem depois. O vídeo sai em `<video>/saidas/<cliente>-primeiro.mp4`
   (o caminho volta no JSON, em `arquivos`) e nada que já existia é sobrescrito. Depois, siga **Fechar**.

## 2. Quero só clonar
1. Peça o link ou o arquivo. Avise o custo antes: 1h30 a 2h45 e US$ 28 a 33 de API por clone. Só siga com o ok.
2. Ambiente Python do kit, uma vez (pergunte antes, instala uns 100 MB):
   `python3 -m venv ~/.apple-style-ui/venv && ~/.apple-style-ui/venv/bin/pip install -r clonar/requirements.txt`.
   Os scripts do kit acham esse ambiente sozinhos.
3. Referência da biblioteca ou link: `python3 clonar/caso.py referencia <link ou arquivo> --pasta clone-<nome>`
   (baixa, guarda o `ORIGEM.md` e diz se é demonstrativa). Depois siga `clonar/README.md` e `clonar/CLONAR.md` a partir
   do `proximo` (`clonar.py novo`, `medir`, que é o raio-x, e as rodadas).
   - **Recriar, não recortar.** Texto, ícone, cartão, pílula, botão e avatar desenhado são sempre recriados em HTML,
     CSS ou SVG, com a fonte e as cores medidas. Recorte do original só para foto ou vídeo filmado de verdade, e cada
     um declarado em `hf/assets/RECORTES.md` com o motivo. Recorte não declarado reprova a rodada, mesmo com a nota boa.
   - **Bateu o alvo, fecha.** Quando o `proximo` da rodada disser "alvo batido: rode final", rode `clonar.py final` na
     hora e entregue. Polir depois do alvo só se a pessoa pedir.
   A entrega é o lado a lado e a nota de fidelidade (distância e correlação de movimento).
4. Siga **Fechar** com `--tipo clone` (sem `--versao` e sem `--molde`).

## 3. Quero um vídeo igual a esta referência
- **Referência com pessoa falando e a pessoa manda a gravação dela** (o caso mais pedido; a referência pode ser
  demonstrativa, com o vídeo editado dentro de um cartão, de uma tela ou de um celular). Tudo pelo `clonar/caso.py`:
  1. `python3 clonar/caso.py referencia <link ou arquivo> --pasta clone-<nome>`: baixa, guarda a origem e tira o vídeo
     de dentro. Leia o `resumo`.
  2. Já existe molde para essa referência? Hoje há um: `moldes/fala-destaque/` (o reel DaIOD8QSEAz, palavra em
     destaque sobre a pessoa falando). Se sim, pule para o 4.
  3. Não existe: o `proximo` traz o `clonar.py novo` e o custo. Com o ok, faça o caminho 2 (clonar) e depois vire molde
     seguindo `clonar/CLONAR.md`, "Caminho do comando de entrada", passo 4 (o contrato do molde está no topo do caso.py).
  4. `python3 clonar/caso.py aplicar moldes/fala-destaque --video <gravação> --saida <video>/saidas/<nome>.mp4 [--idioma pt]`.
     Sem gravação ainda? O exemplo livre é `moldes/fala-destaque/exemplo/pessoa-pexels-8048492.mp4` (sem som: junte uma
     fala com `--voz fala.aiff`; o `exemplo/ORIGEM.md` mostra como gerar uma com o `say`).
     Uns 3 a 5 min para 15 s de fala. Se vier `aviso: falta a GROQ_API_KEY no .env`, a transcrição saiu pelo modelo
     local (mais lenta; a 1ª vez em português baixa ~3 GB): diga isso e siga. A chave é gratuita em console.groq.com e
     quem põe no `.env` é a pessoa.
  5. Mostre o vídeo e o `<video>/destaques.txt`: "As palavras em destaque estão entre colchetes. Quer trocar alguma?"
     Para trocar, edite os colchetes (ou `escura:` no começo da linha para a cena escura) e rode o mesmo comando; sai
     um arquivo novo, nada é sobrescrito. O portão do **Fechar** ainda não conhece este molde: termine mostrando o
     vídeo e perguntando "Aprovas este vídeo?".
- **Tem molde** (a referência é o Satellite, o Joi ou o VoiceOS do @creatoroly; veja `moldes/<molde>/NOTAS.md`):
  1. Copie `moldes/<molde>/versoes/junior.json` para `<video>/versao.json` e troque os valores pedidos.
     As tabelas de campos estão no NOTAS.md do molde. O que não estiver no arquivo fica igual ao original. No Satellite, ponha também o `"sons"` (veja **Som**).
     Com kit de marca (`"marca"` na versão), o `nome` do kit entra sozinho no Satellite (balão final) e no Joi (rótulo
     do ícone); um `icone_texto` na versão vale mais que o kit.
  2. Prévia: `python3 montar.py <video>/versao.json --molde <molde> --previa --video <video>` e `open` na folha de
     quadros (o último item de `arquivos` no JSON). Os três moldes gravam direto em `<video>/saidas/`.
  3. Com o ok da folha, o mesmo comando sem `--previa`. Depois, **Fechar**.
- **Não tem molde:** faça o caminho 2. Depois proponha transformar o clone em molde no padrão de
  `moldes/joi/NOTAS.md` (campos no `<html>`, montar.py, versão travada no MOLDE.json, prova de que com os padrões
  sai o clone). Uns 35 min e US$ 7 de agente: só com o ok.

## 4. Quero uma referência
1. `open biblioteca/site/index.html` (a galeria curada; abre direto no navegador, sem servidor).
2. Como escolher: em "O que é", fique em filme (o vídeo final); em "Tipo", interface ou pessoa falando; em "Peça",
   a peça que tu quer; ordem "Fica melhor". Ficha **verificada** já tem molde e sai em minutos; **classificada**
   precisa de clone antes. Cada ficha traz o link do original, com crédito, e um prompt.
3. Próximo passo: o caminho 3 com o link escolhido.

## Fechar (todo caminho termina aqui)
1. O portão lê a versão resolvida (sem `"marca"` nem `"molde"`), que o `montar.py` já gravou em
   `<video>/.apple-style-ui/versao-resolvida.json`.
2. Portão e registro pendente, num comando só (cerca de 1 min no Satellite):
   `python3 aprendizado/aprender.py aprovar <video>/saidas/<nome>.mp4 --tipo versao --versao <video>/.apple-style-ui/versao-resolvida.json --molde moldes/<molde>/molde --projeto <video> --pendente`
   (`moldes/<molde>/molde` é relativo à raiz do produto; o resto, à pasta atual)
   (`<nome>.mp4` é o primeiro item de `arquivos` no JSON do montar.py; as decisões ficam em
   `<video>/.apple-style-ui/decisoes.json`). REPROVOU: mostre os motivos, corrija e rode de
   novo. Nunca passe por cima.
3. Mostre o vídeo e a folha (`open`) e pergunte: "Aprovas este vídeo?".
4. Com o ok, o mesmo comando sem `--pendente`. Se a resposta citar a `REVISAO.md`, leia para a pessoa o que muda
   no perfil de estilo e só rode `python3 aprendizado/aprender.py travar` com um novo ok.
5. Próximo passo típico: outro cliente com o mesmo vídeo, sem copiar a versão:
   `python3 montar.py <video>/versao.json --marca <outro> --video marcas/<outro>/videos/<nome do vídeo>`, ou vários
   de uma vez: `python3 montar.py <video>/versao.json --lote <outro1>,<outro2> --video "marcas/{marca}/videos/<nome do vídeo>"`
   (uma marca por vez; `{marca}` vira o nome de cada kit).
