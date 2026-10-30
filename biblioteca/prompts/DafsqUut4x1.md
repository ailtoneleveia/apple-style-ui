# creatoroly · DafsqUut4x1

Referência: https://www.instagram.com/p/DafsqUut4x1/

```text
Faça em HyperFrames um vídeo 16:9 de 12 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DafsqUut4x1/

Visual: wallpaper estilo iOS/macOS; um elemento por vez, com muito espaço vazio; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- pílula preta que cresce e mostra informação (Dynamic Island) (Dynamic Island): `modal-morph`, `spring-pop`
- aviso que desce do topo da tela (notification banner): `native-notification-pop`, `notification-stack`, `macos-notification`
- balões de conversa aparecendo um a um (iMessage chat bubbles): `chat-message`, `message-thread-reveal`, `typing-indicator`
- seta ou mãozinha do Mac que entra e clica (macOS cursor click): `oversized-cursor`, `press-ripple`, `cursor-zoom-follow`
- janela do Mac ou do navegador (macOS window): `browser-device-stage`, `macos-tahoe-liquid-glass`, `ui-focus-zoom`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`
- palavras entram uma a uma saindo do desfoque (word-by-word blur-in): `blur-in`, `per-word-rise`, `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~120 BPM por baixo; um efeito por evento de interface, uns 3 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
