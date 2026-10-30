# stoedly · DcaO8HnsgpU

Referência: https://www.instagram.com/p/DcaO8HnsgpU/

```text
Faça em HyperFrames um vídeo 9:16 de 104 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DcaO8HnsgpU/

Visual: imagem real de fundo; muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- barra de busca sendo digitada (search bar typing): `typewriter`, `ai-chat-reveal`
- teclado do iPhone subindo (iOS keyboard): `ai-chat-reveal`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
