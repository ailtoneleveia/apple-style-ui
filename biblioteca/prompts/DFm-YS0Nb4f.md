# creatoroly · DFm-YS0Nb4f

Referência: https://www.instagram.com/p/DFm-YS0Nb4f/

```text
Faça em HyperFrames um vídeo 9:16 de 21 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DFm-YS0Nb4f/

Visual: imagem real de fundo; muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- aviso que desce do topo da tela (notification banner): `native-notification-pop`, `notification-stack`, `macos-notification`
- seta ou mãozinha do Mac que entra e clica (macOS cursor click): `oversized-cursor`, `press-ripple`, `cursor-zoom-follow`
- legenda da fala entrando palavra a palavra (word-by-word captions): `per-word-rise`, `blur-in`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`
- palavras entram uma a uma saindo do desfoque (word-by-word blur-in): `blur-in`, `per-word-rise`, `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~120 BPM por baixo; um efeito por evento de interface, uns 3 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
