# Origem: satellite.mp4

- **O que é:** o molde Satellite renderizado por este repositório, com motion blur (1080x1080, 30 qps, 10,9 s).
- **Como:** Inter (com `ASUI_FONTE_LIVRE=1`), cor #E54A26, nome `apple.style.ui` com um logo neutro (`assets/logo-exemplo.png`) no lugar do emoji do balão, textos em português. Áudio: silêncio + o pacote de sons CC0 (`"sons": "marcado"`). No modo livre, os emojis ⚠️ e 🚑 do mapa saem da cena.
- **Referência do molde:** o vídeo original é de @creatoroly (https://www.instagram.com/p/DWWQEOmDfsf/). Aqui não entra nada dele: nem quadro, nem áudio, nem recorte.
- **Licença:** feito com fontes SIL OFL, sons CC0 e peças livres (ver `../LICENCAS-DE-TERCEIROS.md`).
- **Feito em:** 30/10/2026.

Para refazer, da raiz do produto:

```sh
ASUI_FONTE_LIVRE=1 python3 montar.py satellite.json --video <pasta>/satellite
```

com este `satellite.json`:

```json
{
 "rotulo_icone": "Satélite",
 "cartao_titulo": "Passagem da ISS",
 "cartao_tempo": "em 14 min",
 "tile_rotulo": "Conectado",
 "titulo": "Qual é a emergência?",
 "item1": "Problema no carro",
 "icone1": "car",
 "item2": "Doença ou ferimento",
 "icone2": "plus",
 "item3": "Crime",
 "icone3": "shield",
 "item4": "Perdido ou preso",
 "icone4": "star",
 "item5": "Incêndio",
 "icone5": "flame",
 "botao": "Encerrar",
 "ilha_texto": "A ajuda está a caminho",
 "relogio": "1:40",
 "molde": "satellite",
 "fonte": "inter",
 "cor_principal": "#E54A26",
 "balao_nome": "apple.style.ui",
 "logo": "assets/logo-exemplo.png",
 "sons": "marcado"
}
```
- **sha256:** `e2f232dbaa59b497ceac9f60089dd32ec9e879aeca94ac64bfd5ceddcadcb198`
