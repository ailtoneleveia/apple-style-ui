# shazyy.aep · DdZdKa4MnOd

Referência: https://www.instagram.com/p/DdZdKa4MnOd/

```text
Faça em HyperFrames um vídeo 9:16 de 35 s no estilo Apple, tomando como referência: https://www.instagram.com/p/DdZdKa4MnOd/

Visual: fundo escuro com brilho; muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- moldura de iPhone com a tela dentro (iPhone mockup): `device-frame-stage`, `vfx-iphone-device`
- janela do Mac ou do navegador (macOS window): `browser-device-stage`, `macos-tahoe-liquid-glass`, `ui-focus-zoom`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- gráfico que se desenha (animated chart): `count-up`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- barra de busca sendo digitada (search bar typing): `typewriter`, `ai-chat-reveal`
- print real do produto dentro do design (real product screenshot): `browser-device-stage`, `ui-focus-zoom`, `cursor-zoom-follow`
- frase limpa com uma palavra em azul (one highlighted word): `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
