# Apple Style UI

Vídeo com cara de lançamento da Apple, feito no Claude Code, pedindo em português.

O que separa um vídeo da Apple de um vídeo qualquer é o movimento: a peça que assenta sem tremer, o desfoque de
quem passa rápido, cada palavra entrando no seu tempo. A IA sozinha chuta esse movimento. Aqui ele vem medido: cada
molde saiu de um vídeo real, analisado quadro a quadro, e o que se aprendeu virou código e receita.

## O que dá para fazer

- **Pôr a tua marca num vídeo pronto.** São três vídeos de interface prontos (Satellite, Joi e VoiceOS). Tu diz o
  nome, a cor, a fonte, o logo e os textos, e sai o vídeo com a tua marca e o mesmo movimento do original.
- **Editar a tua gravação nesse estilo.** Manda o vídeo de tu falando: ele transcreve, escolhe a palavra de
  destaque de cada frase e põe a legenda fora do rosto, legível até em cima de tela gravada.
- **Copiar o estilo de um vídeo que tu viu.** Manda o link de um vídeo de interface. Ele recria a animação em código,
  sem recortar nada do original, e compara lado a lado, peça por peça, rodada após rodada.
- **Usar esse estilo nos teus vídeos.** O vídeo copiado vira um molde teu: troca marca, cores e textos e usa quantas
  vezes quiser.
- **Fazer um vídeo novo** a partir de uma referência da galeria, no mesmo padrão de movimento.
- **Achar referência.** Uma galeria com mais de 400 vídeos de interface escolhidos a dedo: filtra, assiste ali mesmo
  e copia o pedido pronto para o Claude.

## Como começar

No Claude Code:

```
/plugin marketplace add ailtoneleveia/apple-style-ui
/plugin install apple-style-ui@apple-style-ui
```

Depois é um comando só:

```
/apple-style-ui
```

Na primeira vez ele prepara a máquina sozinho: baixa o HyperFrames, o Chrome que faz o render e as bibliotecas de
Python, e confere o resto. Se faltar algum programa no Mac (ffmpeg, Node), ele mostra o comando e instala com o teu ok.
Depois mostra os exemplos e faz o teu primeiro vídeo com o teu nome e a tua cor. Se o comando não aparecer logo depois
de instalar, fecha e abre o Claude Code.

## No dia a dia

Digita `/apple-style-ui` e diz o que tu quer, do teu jeito. Nem precisa do comando: pedir um vídeo estilo Apple numa
frase normal já chama o plugin.

- "põe a minha marca no Joi, cor #E54A26, o app se chama Rotina"
- "edita a minha gravação nesse estilo" e o arquivo junto
- "quero um vídeo igual a esse" e o link
- "me mostra a galeria"

Ele pergunta só o que faltar e termina sempre dizendo o próximo passo. Na galeria, cada vídeo tem **Ver aqui**, para
assistir sem sair dela, e **Copiar para o Claude**, que copia o pedido pronto: é só colar no Claude Code.

Os teus vídeos ficam na pasta onde tu abriu o Claude Code, em `marcas/<tua marca>/videos/`. Cada vídeo que tu aprova
ensina o teu estilo, e o próximo não sai pior que o anterior.

Para receber as novidades: `/plugin marketplace update apple-style-ui` e depois `/plugin update apple-style-ui@apple-style-ui`.

## O que vem dentro

- **O perfil de estilo** (`estilo/`): as molas medidas, o desfoque de movimento de verdade, o ritmo de entrada e o
  peso da letra, em 8 regras numa página. E 24 receitas por sintoma, do tipo "a lista entra toda junta" ou "o texto
  entra nítido demais", cada uma com o que medir e o código que resolve.
- **Os moldes** (`moldes/`): Satellite, Joi, VoiceOS e o da pessoa falando, com as notas do que foi medido.
- **O kit de clonagem** (`clonar/`): mede cada peça do vídeo original e mostra onde a cópia ainda difere.
- **Os sons** (`sons/`): clique, tecla e chegada, de uso livre, encaixados no movimento.
- **A galeria** (`biblioteca/`): as referências com o link do original e o crédito de quem fez.

## O que ainda não faz

- Misturar peças de moldes diferentes num vídeo só.
- Comparar o vídeo novo com a referência peça por peça. Ele segue o padrão de movimento, e a comparação só existe
  quando tu copia a referência antes.
- Detalhe muito rápido na cópia: uma cascata de 4 quadros pode sair toda junta.
- Memoji e emoji da Apple não podem ir junto: a cópia desenha os seus, e eles ficam diferentes.
- Só roda no Mac, por enquanto.

## O que precisa ter

Mac e Claude Code. O resto o primeiro comando instala. Para transcrever fala mais rápido, uma `GROQ_API_KEY`
gratuita (console.groq.com) no `.env` da tua pasta. Sem ela, a transcrição roda no teu Mac, e a primeira vez baixa
uns 3 GB.

## Licenças

Código MIT. SF Pro e emojis da Apple não vêm no repositório: o render usa os do teu Mac. Para publicar, usa
`fonte: inter` ou `archivo` e uma música tua. Tudo de terceiros está em `LICENCAS-DE-TERCEIROS.md`; pastas e
comandos, em `ESTRUTURA.md`.
