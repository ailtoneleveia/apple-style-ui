# adrimotions · DKD43evtOxG

Referência: https://www.instagram.com/p/DKD43evtOxG/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DKD43evtOxG/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo escuro com brilho; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- barra de busca sendo digitada (search bar typing): `typewriter`, `ai-chat-reveal`
- cartões empilhados que se reorganizam (card stack): `spring-stack-shuffle`, `notification-stack`, `focus-rack`
- frase limpa com uma palavra em azul (one highlighted word): `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~110 BPM por baixo; um efeito por evento de interface, uns 4 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
