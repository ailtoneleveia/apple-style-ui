# rize.visualsx · DVgslvAjnuj

Referência: https://www.instagram.com/p/DVgslvAjnuj/

```text
Faça em HyperFrames um vídeo 16:9 de 5 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DVgslvAjnuj/

Visual: fundo claro e vazio (branco a cinza #f5f5f7); muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- pílula preta que cresce e mostra informação (Dynamic Island) (Dynamic Island): `modal-morph`, `spring-pop`
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`
- painel de vidro fosco ou líquido (frosted / liquid glass): `liquid-glass-widgets`, `liquid-glass-notification`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): música de ~174 BPM por baixo; um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
