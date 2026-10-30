# Origem: joi.mp4

- **O que é:** o molde Joi renderizado por este repositório, com motion blur (1080x1920, 60 qps, 7,5 s).
- **Como:** Inter no lugar da SF Pro (`ASUI_FONTE_LIVRE=1`), cor #E54A26, textos em português, objetos do menu trocados pelas peças livres. Sem áudio (silêncio): o Joi ainda não tem sons por elemento.
- **Referência do molde:** o vídeo original é de @creatoroly (https://www.instagram.com/p/DPJJwcujV0X/). Aqui não entra nada dele: nem quadro, nem áudio, nem recorte.
- **Licença:** feito com fontes SIL OFL, sons CC0 e peças livres (ver `../LICENCAS-DE-TERCEIROS.md`).
- **Feito em:** 30/10/2026.

Para refazer, da raiz do produto:

```sh
ASUI_FONTE_LIVRE=1 python3 montar.py joi.json --video <pasta>/joi
```

com este `joi.json`:

```json
{
 "item1": "Planejar o dia",
 "item2": "Beber água",
 "item3": "Pegar sol",
 "item4": "Desacelerar",
 "botao1": "Concluir",
 "botao2": "Editar",
 "botao3": "Remover",
 "frase": "Assine o Joi Pro",
 "cartao_titulo": "Joi Pro",
 "cartao_botao": "Assinar",
 "cor_principal": "#E54A26",
 "molde": "joi"
}
```
- **sha256:** `8cf1414ccafae540a8b292931584b60e32e429b1da1c36555be8427ee426c261`
