# madebyveduboi · DT8AH8kkwfh

Referência: https://www.instagram.com/p/DT8AH8kkwfh/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DT8AH8kkwfh/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo claro e vazio (branco a cinza #f5f5f7); sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- balões de conversa aparecendo um a um (iMessage chat bubbles): `chat-message`, `message-thread-reveal`, `typing-indicator`
- seta ou mãozinha do Mac que entra e clica (macOS cursor click): `oversized-cursor`, `press-ripple`, `cursor-zoom-follow`
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- janela do Mac ou do navegador (macOS window): `browser-device-stage`, `macos-tahoe-liquid-glass`, `ui-focus-zoom`
- ícone de app grande que surge com mola (app icon pop): `spring-pop`, `icon-swap`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- gráfico que se desenha (animated chart): `count-up`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- cartões empilhados que se reorganizam (card stack): `spring-stack-shuffle`, `notification-stack`, `focus-rack`
- palavras entram uma a uma saindo do desfoque (word-by-word blur-in): `blur-in`, `per-word-rise`, `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~124 BPM por baixo; um efeito por evento de interface, uns 3 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
