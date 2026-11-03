#!/bin/sh
# Ao abrir o Claude Code: se a máquina ainda não foi preparada (o preparar.py grava o pronto.json), avisa o que digitar.
# Só olha um arquivo, para não atrasar a abertura; depois de preparada, não diz nada.
[ -f "$HOME/.apple-style-ui/pronto.json" ] && exit 0
cat <<'JSON'
{"systemMessage": "Apple Style UI instalado. Para preparar esta máquina (HyperFrames, Chrome e o resto) e fazer teu primeiro vídeo, digita: /apple-style-ui:video", "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "O plugin Apple Style UI está instalado, mas esta máquina ainda não foi preparada. Se a pessoa falar de vídeo, o /apple-style-ui:video começa pelo preparo."}}
JSON
