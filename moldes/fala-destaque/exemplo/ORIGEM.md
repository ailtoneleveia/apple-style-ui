# Origem do exemplo

## A pessoa: `pessoa-pexels-8048492.mp4`

- Página: https://www.pexels.com/video/a-man-explaining-something-8048492/
- Arquivo: https://videos.pexels.com/video-files/8048492/8048492-hd_1080_1920_25fps.mp4 (6,4 MB, 1080x1920, 25 qps,
  14,12 s, 353 quadros, **sem trilha de áudio**)
- Autor: Antoni Shkraba (https://www.pexels.com/@shkrabaanthony/)
- Baixado em: 22/10/2026
- sha256: `e07fde6c86ee6e2f598c538b1c8bdfa63035533f5f05ca37a226f94fee0a427b`
- Licença, conferida em 22/10/2026: a página do vídeo marca "Free" com link para https://www.pexels.com/license/.
  A página da licença diz que a atribuição não é obrigatória ("Attribution is not required") e que dá para editar o
  vídeo. Não pode: mostrar a pessoa identificável de forma negativa, dar a entender que ela endossa um produto, vender
  cópia sem alteração, redistribuir em outro banco e usar como marca. O texto deste teste é neutro e não fala de produto.
- O que mostra: um homem de óculos e terno claro, em pé diante de um quadro branco, falando para a câmera e gesticulando.

## A fala (não vem no repositório)

- **O Pexels publica todos os vídeos sem áudio** (central de ajuda: https://help.pexels.com/hc/en-us/articles/43126081204505).
  Não existe fala dessa pessoa.
- Para o caminho da transcrição ter o que ler, a prova usou uma narração sintética feita com o `say` do macOS. Ela não
  vem no repositório (a voz é do sistema da Apple). Tu gera a tua na hora, na pasta de trabalho:

  ```sh
  say -v Daniel -r 150 -o fala.aiff "I used to think talent changed everything. It doesn't. What changes you is a small habit, repeated every single day, even when nobody is watching."
  ```

  Em português, troque a voz (`say -v '?'` lista as do teu Mac) e o texto. Com a tua gravação de verdade, nada disso é
  preciso: o vídeo já traz a fala.
- A boca dele não acompanha essa fala. O exemplo prova o molde (pessoa nova por baixo, texto e tempo tirados da
  transcrição, destaque, cor, fonte), não a sincronia com uma voz de verdade.

## A versão

`versao.json` é a versão resolvida que o `montar.py` gravou (campos do molde com as frases da transcrição). Comando:

```sh
python3 moldes/fala-destaque/montar.py --pessoa moldes/fala-destaque/exemplo/pessoa-pexels-8048492.mp4 --voz fala.aiff \
  --destaques "everything,doesn't,habit,single,day,watching" --sombra medida --saida saidas/com-outra-pessoa.mp4
```
