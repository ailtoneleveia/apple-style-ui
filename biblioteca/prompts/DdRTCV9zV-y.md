# apexmotion.visuals · DdRTCV9zV-y

Referência: https://www.instagram.com/p/DdRTCV9zV-y/

```text
Monte em HyperFrames, como componentes reutilizáveis (um bloco por peça), os widgets da vitrine de https://www.instagram.com/p/DdRTCV9zV-y/.
Cada peça num quadro próprio, centralizada, em loop curto (2 a 4 s) que mostra o estado inicial, a interação e o estado final, para eu reaproveitar em outros vídeos.

Visual: fundo escuro com brilho; sombras suaves; cantos bem arredondados; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- pílula preta que cresce e mostra informação (Dynamic Island) (Dynamic Island): `modal-morph`, `spring-pop`
- ícone de app grande que surge com mola (app icon pop): `spring-pop`, `icon-swap`
- cartões empilhados que se reorganizam (card stack): `spring-stack-shuffle`, `notification-stack`, `focus-rack`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
