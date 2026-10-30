# motion_lenser · DLTxPpcIQkm

Referência: https://www.instagram.com/p/DLTxPpcIQkm/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DLTxPpcIQkm/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo pastel ou gradiente suave; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~117 BPM por baixo; um efeito por evento de interface, uns 3 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
