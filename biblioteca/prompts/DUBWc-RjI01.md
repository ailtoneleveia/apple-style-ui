# dhruvinmotion · DUBWc-RjI01

Referência: https://www.instagram.com/p/DUBWc-RjI01/

```text
Faça em HyperFrames um vídeo 9:16 de 8 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DUBWc-RjI01/

Visual: fundo escuro com brilho; muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- balões de conversa aparecendo um a um (iMessage chat bubbles): `chat-message`, `message-thread-reveal`, `typing-indicator`
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- ícone de app grande que surge com mola (app icon pop): `spring-pop`, `icon-swap`
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- barra de busca sendo digitada (search bar typing): `typewriter`, `ai-chat-reveal`
- cartões empilhados que se reorganizam (card stack): `spring-stack-shuffle`, `notification-stack`, `focus-rack`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~98 BPM por baixo; um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
