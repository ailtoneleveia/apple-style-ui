# creatoroly · CzRTmRAtCLd

Referência: https://www.instagram.com/p/CzRTmRAtCLd/

```text
Faça em HyperFrames um vídeo 9:16 de 27 s no estilo Apple, tomando como referência: https://www.instagram.com/p/CzRTmRAtCLd/

Visual: fundo escuro com brilho; muitos elementos; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- aviso que desce do topo da tela (notification banner): `native-notification-pop`, `notification-stack`, `macos-notification`
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- legenda da fala entrando palavra a palavra (word-by-word captions): `per-word-rise`, `blur-in`
- número ou preço que gira até o valor (rolling digits counter): `number-wheel`, `count-up`, `number-pop-in`
- emoji 3D como ilustração (3D emoji): `spring-pop`
- frase limpa com uma palavra em azul (one highlighted word): `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
