# stepan.straufvfx · DcJqUPhOO1N

Referência: https://www.instagram.com/p/DcJqUPhOO1N/

```text
Faça em HyperFrames um vídeo 1:1 de 12 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DcJqUPhOO1N/

Visual: fundo escuro com brilho; um elemento por vez, com muito espaço vazio; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- ícone de app grande que surge com mola (app icon pop): `spring-pop`, `icon-swap`
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- mapa com trajeto (map route): `nyc-paris-flight`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~138 BPM por baixo; um efeito por evento de interface, uns 3 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
