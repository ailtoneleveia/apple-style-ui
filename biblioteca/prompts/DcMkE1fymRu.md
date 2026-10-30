# _danielburlini · DcMkE1fymRu

Referência: https://www.instagram.com/p/DcMkE1fymRu/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DcMkE1fymRu/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo escuro com brilho; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- balões de conversa aparecendo um a um (iMessage chat bubbles): `chat-message`, `message-thread-reveal`, `typing-indicator`
- seta ou mãozinha do Mac que entra e clica (macOS cursor click): `oversized-cursor`, `press-ripple`, `cursor-zoom-follow`
- janela do Mac ou do navegador (macOS window): `browser-device-stage`, `macos-tahoe-liquid-glass`, `ui-focus-zoom`
- ícone de app grande que surge com mola (app icon pop): `spring-pop`, `icon-swap`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- emoji 3D como ilustração (3D emoji): `spring-pop`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
