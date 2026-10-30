# creatoroly · DMIZua2taax

Referência: https://www.instagram.com/p/DMIZua2taax/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DMIZua2taax/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo escuro com brilho; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- aviso que desce do topo da tela (notification banner): `native-notification-pop`, `notification-stack`, `macos-notification`
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- barra de busca sendo digitada (search bar typing): `typewriter`, `ai-chat-reveal`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`
- palavras entram uma a uma saindo do desfoque (word-by-word blur-in): `blur-in`, `per-word-rise`, `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~90 BPM por baixo; um efeito por evento de interface, uns 2 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
