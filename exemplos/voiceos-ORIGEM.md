# Origem: voiceos.mp4

- **O que é:** o molde VoiceOS renderizado por este repositório, com motion blur (1920x1080, 60 qps, 11,7 s).
- **Como:** Inter no lugar da SF Pro (`ASUI_FONTE_LIVRE=1`), cor #E54A26, textos em português, céu, vinhedo, ícones e avatar trocados pelas peças livres. Sem áudio (silêncio): feito no voiceos-v1, antes dos sons por elemento (o voiceos-v2 já tem: `"sons": "suave"` ou `"marcado"`). Reencodado mais leve (CRF 24) para caber no repositório.
- **Referência do molde:** o vídeo original é de @creatoroly (https://www.instagram.com/p/DafsqUut4x1/). Aqui não entra nada dele: nem quadro, nem áudio, nem recorte.
- **Licença:** feito com fontes SIL OFL, sons CC0 e peças livres (ver `../LICENCAS-DE-TERCEIROS.md`).
- **Feito em:** 30/10/2026.

Para refazer, da raiz do produto:

```sh
ASUI_FONTE_LIVRE=1 python3 montar.py voiceos.json --video <pasta>/voiceos
```

com este `voiceos.json`:

```json
{
 "frase_ceu": "aaah cara",
 "frase_vinhedo": "Tenho muito trabalho pra fazer",
 "msg_nome": "Ana",
 "msg_hora": "00:02",
 "msg_texto": "Preciso mandar um roteiro novo pro cliente..",
 "botao_enviar": "Enviar",
 "pagina_vazia": "Nova página",
 "pagina_privado": "Privado",
 "pagina_titulo": "Roteiro do vídeo novo..",
 "pagina_dica": "Aperte “espaço” para IA ou “/” para comandos.",
 "linha1": "Uma página em branco.",
 "linha2": "Um cursor piscando.",
 "linha3": "É aqui que a maioria dos roteiros morre.",
 "linha4": "Tu sabe o que dizer. Digitar mata o ritmo.",
 "linha5": "Agora veja isso.",
 "linha6": "Sem teclado.",
 "linha7": "Só fale.",
 "linha8": "O app escuta. O app escreve.",
 "linha9": "Cada palavra vira texto, na hora.",
 "linha10": "Dez minutos digitando dão um parágrafo.",
 "linha11": "Dez minutos falando dão um roteiro inteiro.",
 "linha12": "Escrever nunca foi a parte difícil.",
 "linha13": "Digitar era.",
 "linha14_inicio": "Pare de",
 "linha14_destaque": "digitar",
 "linha14_fim": "seus roteiros.",
 "pilula_pronto": "Pronto!",
 "tecla": "fn",
 "frase_tecla": "e começa a falar",
 "legenda_logo": "conceito original de creatoroly",
 "cor_destaque": "#E54A26",
 "molde": "voiceos"
}
```
- **sha256:** `ea541d7b67457e30302376e11de96724a7023c76b278c84eb0d629e4d403f395`
