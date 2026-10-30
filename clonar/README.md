# Apple Style UI: kit de clonagem

Refaz um vídeo de referência no HyperFrames até ficar igual quadro a quadro, com nota de fidelidade, e mede
qualquer vídeo em minutos (raio-x) sem clonar. O roteiro do ciclo está em [`CLONAR.md`](CLONAR.md).

```sh
python3 -m venv ~/.apple-style-ui/venv && ~/.apple-style-ui/venv/bin/pip install -r requirements.txt   # uma vez, fora do plugin

python3 clonar.py raiox  video.mp4 --saida raiox-video     # só medir: RAIOX.md + raiox.json + folha + curvas
python3 clonar.py novo   clone-x video.mp4 --link URL --autor @perfil
python3 clonar.py medir  clone-x                           # raio-x dentro do projeto
python3 clonar.py montar clone-x                           # hf/ com o modelo e o estilo.js
python3 clonar.py rodada clone-x --o-que-mudou "..."       # render com motion blur + nota
python3 clonar.py rodada clone-x --mascara M --placa V     # placa de vídeo: a nota é a da camada, só na máscara
python3 clonar.py final  clone-x [--so-camada]             # saidas/final.mp4, lado-a-lado.mp4 (e so-camada.mp4)

# o loop de qualidade (a rodada já roda o comparar): peça por peça, as 3 piores com a correção
python3 scripts/qualidade.py comparar original.mp4 clone.mp4 [--pecas pecas.json] [--hf hf/]
python3 scripts/qualidade.py estilo saida.mp4 [--hf hf/]    # molde ou vídeo novo, contra o perfil do estilo.js
python3 scripts/qualidade.py codigo hf/                     # movimento paramétrico: tabela de pose reprova

# referência demonstrativa (o vídeo editado dentro de um cartão, tela ou celular): tire o vídeo de dentro antes
python3 scripts/extrair_tela.py reel.mp4 dentro.mp4 --json tela.json   # tamanho nativo, trechos sem a tela, trocas

# o caso central: referência → (clone e molde, trabalho de agente) → o vídeo da pessoa editado igual
python3 caso.py referencia <link ou arquivo>                # baixa, tira o vídeo de dentro, diz o comando do clone
python3 caso.py aplicar <molde> --video gravacao.mp4        # transcreve, escolhe o destaque, monta, renderiza
python3 scripts/transcrever.py fala.mp4 --idioma pt         # só as palavras com tempo (Groq; sem chave, local)
```

Cada comando devolve JSON `{ok, resumo, proximo: {comando, motivo, precisa_de_voce}}`; erro vai no stderr como
`{ok: false, erro, codigo}`.

Dependências: Python 3.11+ com numpy, opencv-python-headless, pillow e scipy (`requirements.txt`); ffmpeg; node; HyperFrames
0.8.184 por `npx`; tesseract (opcional: sem ele, o medidor por peça pula a leitura de texto). O perfil de estilo vem de `estilo/estilo.js` na raiz do produto (ou `ASUI_ESTILO`).

Autotestes: `~/.apple-style-ui/venv/bin/python testes/conferir_raiox.py` roda o raio-x nos três originais já clonados (só com eles em `ASUI_ORIGINAIS`) e confere com
o que os clones mediram; `~/.apple-style-ui/venv/bin/python testes/conferir_pecas.py` confere trilha por palavra, placas (de câmera e
de vídeo), registro de câmera, nota na máscara, aparição e o encaixe do modelo num vídeo sintético (menos de 10 s);
`~/.apple-style-ui/venv/bin/python testes/conferir_tela.py` confere o `extrair_tela.py` num cartão parado e num que anda (menos de 15 s);
`~/.apple-style-ui/venv/bin/python testes/conferir_qualidade.py` confere o medidor por peça em vídeos sintéticos (mola conhecida,
velocidade quebrada, peça borrada) e a checagem de código (cerca de 1 min);
`python3 scripts/transcrever.py --autoteste` transcreve uma fala do `say` pelo provedor local e confere o aviso da
chave da Groq (uns 5 s); `python3 scripts/destaque.py` confere a regra do destaque.

Partes do código vêm de projetos com licença MIT: avisos em [`LICENCAS-DE-TERCEIROS.md`](LICENCAS-DE-TERCEIROS.md).
