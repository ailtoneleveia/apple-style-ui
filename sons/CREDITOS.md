# Créditos do pacote de sons (sons-v1)

Todos os 20 sons são **CC0**: dá para usar, vender e redistribuir sem pedir licença e sem atribuição obrigatória.
Nenhum som do pacote veio de licença com atribuição obrigatória, uso não comercial ou "sem obras derivadas".

## De onde vieram

- **Gerados aqui** (10 sons): síntese determinística em `fazer_pacote.py` (ruído moldado, senos e notas, com semente
  fixa). São sons nossos e ficam em CC0.
- **Kenney Interface Sounds 1.0** (10 sons), de Kenney (www.kenney.nl), criado em 11/02/2020. Licença
  **Creative Commons Zero (CC0 1.0)**, http://creativecommons.org/publicdomain/zero/1.0/. O próprio `License.txt` do
  pacote diz: "free to use in personal, educational and commercial projects" e que creditar a Kenney "is not
  mandatory". Baixado do soundcn (github.com/kapishdima/soundcn, pasta `assets/kenney_interface-sounds`, em
  22/10/2026). O código do soundcn é MIT; os arquivos do Kenney seguem CC0. Creditamos mesmo assim.
- **Fora de propósito:** a biblioteca embutida do media-use (Pixabay Content License) e a coleção World of Warcraft do
  soundcn (da Blizzard, não é livre) não foram usadas.

## Som por som

| nome nosso | tipo | o que é | origem | licença |
|---|---|---|---|---|
| aparecer-1 | aparecer | pop suave, gota que sobe | Kenney `drop_002.ogg` | CC0 1.0 |
| aparecer-2 | aparecer | pop suave, gota mais grave | Kenney `drop_003.ogg` | CC0 1.0 |
| aparecer-3 | aparecer | pop com cauda que sobe | Kenney `drop_004.ogg` | CC0 1.0 |
| clicar-1 | clicar | clique do cursor, com corpo curto | Kenney `click_001.ogg` + corpo gerado de 12 ms | CC0 1.0 |
| tocar-1 | tocar | toque curto e seco | Kenney `tick_002.ogg` | CC0 1.0 |
| tocar-2 | tocar | toque de seleção | Kenney `select_001.ogg` | CC0 1.0 |
| digitar-1 | digitar | tecla, grave | Kenney `click_002.ogg` | CC0 1.0 |
| digitar-2 | digitar | tecla, aguda | Kenney `click_003.ogg` | CC0 1.0 |
| numero-1 | numero | catraca de número rolando, 200 ms | Kenney `scroll_002.ogg` (200 ms, com o tique do meio mais forte) | CC0 1.0 |
| numero-2 | numero | catraca dupla, 200 ms | Kenney `scroll_003.ogg` (200 ms, idem) | CC0 1.0 |
| brilho-1 | brilho | seis toques agudos espalhados | gerado | CC0 (nosso) |
| brilho-2 | brilho | cinco toques agudos, mais graves | gerado | CC0 (nosso) |
| entrar-1 | entrar | whoosh que sobe e corta no pico | gerado | CC0 (nosso) |
| entrar-2 | entrar | whoosh que sobe, mais curto e grave | gerado | CC0 (nosso) |
| sair-1 | sair | whoosh que desce | gerado | CC0 (nosso) |
| sair-2 | sair | whoosh que desce, mais curto | gerado | CC0 (nosso) |
| morph-1 | morph | ar que cresce e assenta num baque grave | gerado | CC0 (nosso) |
| morph-2 | morph | ar que cresce, mais curto e claro | gerado | CC0 (nosso) |
| ilha-1 | ilha | "bloop" grave que abre, com sopro | gerado | CC0 (nosso) |
| sucesso-1 | sucesso | duas notas que sobem (dó 6, sol 6) | gerado | CC0 (nosso) |

Os 10 arquivos do Kenney foram cortados (silêncio), normalizados e, em três casos, recortados ou somados a um som
gerado. Isso é permitido pela CC0. Para refazer o pacote: `python3 fazer_pacote.py <pasta kenney_interface-sounds>`.
