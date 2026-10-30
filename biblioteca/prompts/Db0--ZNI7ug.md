# mohmd.visuals · Db0--ZNI7ug

Referência: https://www.instagram.com/p/Db0--ZNI7ug/

```text
Faça em HyperFrames um vídeo 9:16 de 10 s no estilo Apple, tomando como referência: https://www.instagram.com/p/Db0--ZNI7ug/

Visual: wallpaper estilo iOS/macOS; dois ou três elementos por cena; sombras suaves e uma ou duas cores de sistema; fonte sans tipo SF Pro (Inter serve).

Peças (instale com `npx hyperframes add <nome>`):
- o vídeo da pessoa dentro de um cartão arredondado ou de um iPhone (talking head in rounded card): `device-frame-stage`, `split-tilt-cards`, `focus-swap`
- botão em forma de pílula que é tocado (pill button / toggle): `toggle-flip`, `spring-pop`, `press-ripple`
- emoji 3D como ilustração (3D emoji): `spring-pop`
- cartões empilhados que se reorganizam (card stack): `spring-stack-shuffle`, `notification-stack`, `focus-rack`
- frase limpa com uma palavra em azul (one highlighted word): `soft-blur-in`

Movimento: cada elemento entra com mola curta (0,3 a 0,5 s), saída rápida e assentamento suave, sem quique exagerado; um elemento em foco por vez; troca de cena por desfoque ou por morph do mesmo elemento, sem corte seco.

Som (medido na referência): um efeito por evento de interface, uns 1 por segundo: whoosh curto nas entradas, pop no que surge, clique em cada toque, riser antes do fecho.

Antes de renderizar, compare 4 quadros-chave com a referência e ajuste posição, tamanho e tempo até bater.
```
