# haxmotionco · DZ-PwwTpwLS

Referência: https://www.instagram.com/p/DZ-PwwTpwLS/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DZ-PwwTpwLS/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo claro e vazio (branco a cinza #f5f5f7); sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- seta ou mãozinha do Mac que entra e clica (macOS cursor click): `oversized-cursor`, `press-ripple`, `cursor-zoom-follow`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- mapa com trajeto (map route): `nyc-paris-flight`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~129 BPM por baixo; um efeito por evento de interface, uns 2 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
