# Apple Style UI

Vídeo estilo Apple com a tua marca. Tu escolhe um molde (um vídeo clonado e provado quadro a quadro), troca nome, cor,
fonte e textos, e o vídeo sai com as molas, o motion blur e o ritmo do original. Uma catraca confere cada vídeo antes
do teu ok, então nada sai pior que o anterior.

## Primeiro vídeo em 5 minutos

No Claude Code:

```
/plugin marketplace add <dono>/apple-style-ui
/plugin install apple-style-ui@apple-style-ui
/apple-style-ui:video começar
```

Ele te mostra os 3 exemplos (`exemplos/`), pergunta o teu nome e a tua cor e faz o vídeo no molde do Satellite.
Com a máquina pronta, o render leva uns 2 minutos. Na primeira vez ele baixa o HyperFrames e um Chrome (uns 300 MB).

## Os 4 caminhos (`/apple-style-ui:video` pergunta qual)

| Tu diz | O que acontece |
|---|---|
| Quero começar | prepara a máquina, mostra os exemplos e faz um vídeo com o teu nome e a tua cor |
| Quero só clonar | tu manda o link; volta o raio-x, o clone, o lado a lado e a nota de fidelidade |
| Quero um vídeo igual a esta referência | se ela tem molde, troca marca, texto e cor; com pessoa falando, tu manda a tua gravação e ela sai editada igual |
| Quero uma referência | abre a galeria curada para tu escolher |

Todo caminho termina com o teu ok. Nos moldes de interface, a catraca confere antes, e o que tu aprova vira o teu
perfil de estilo.

## Como usar a biblioteca

Abre `biblioteca/site/index.html`, filtra (nível, tipo, peça), escolhe uma ficha, clica em **Copiar para o Claude** e
cola no Claude Code. O texto já sai no caminho certo: provada vai direto para o molde, clonável vai para o clone, e o
resto vira um vídeo novo no estilo calibrado. A diferença para as listas de prompts: lá ninguém reproduziu o prompt;
aqui as provadas têm clone com nota, e o resto passa pelo ciclo que mede.

## O que precisa ter

Mac, Claude Code, ffmpeg, Node e Python 3 com numpy e pillow (`brew install ffmpeg node numpy pillow`). Para clonar,
um ambiente Python a mais, que o caminho 2 cria com o teu ok. Para transcrever fala, uma `GROQ_API_KEY` gratuita no
`.env` da tua pasta (sem ela, a transcrição roda local, mais lenta).

## Licenças

SF Pro e emojis da Apple não vêm no repositório: o render usa os do teu Mac. Para publicar, usa `fonte: inter` ou
`archivo` e uma música tua. Tudo de terceiros está em `LICENCAS-DE-TERCEIROS.md`; pastas e comandos, em `ESTRUTURA.md`.
O formato de plugin com o repositório como marketplace segue o do get-brolls, do Bruno Moreira.
