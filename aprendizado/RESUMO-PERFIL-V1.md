# Perfil v1: o que entra e o que muda com o teu ok (22/10)

A revisão está em `~/.apple-style-ui/perfil/REVISAO.md`. Nada foi travado: o perfil só trava com o teu ok.

**O que entra.** Os 3 clones aprovados, cada um com as medidas do portão:

| clone | distância | correlação | pico | cortes |
|---|---|---|---|---|
| Satellite | 0,010 | 0,981 | 0 quadro | 2 de 2 |
| Joi | 0,004 | 0,997 | 0 quadro | 6 de 6 |
| VoiceOS | 0,010 | 0,999 | 1 quadro | 2 de 2 |

- A régua do próximo clone: distância até 0,012 (a melhor, 0,004, mais a folga), correlação a partir de 0,979
  (a melhor, 0,999, menos a folga) e pico de no máximo 1 quadro.
- Fontes: SF Pro nos 3, Inter em 1 e Apple Color Emoji em 1.
- As lições dos 3 `LESSONS.md` viram o `APRENDIZADOS.md`, com a origem de cada uma.
- Cores, molas e controles ficam vazios: eles vêm de versões de molde aprovadas, e ainda não há nenhuma.

**O que muda quando tu der o ok** (`python3 aprendizado/aprender.py travar`):
- nasce a pasta `perfil-v1/`, só de leitura e com a impressão digital de cada arquivo; se alguém mexer à mão, o
  portão avisa;
- `aprender.py perfil` passa a mostrar o perfil-v1 em vigor, e a próxima revisão compara com ele (o que mudar vira v2);
- a régua acima já vale desde a aprovação: um clone novo pior que ela é reprovado. O ok trava esse estado.
