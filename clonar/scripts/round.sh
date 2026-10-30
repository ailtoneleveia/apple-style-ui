#!/bin/zsh
# Copyright (c) 2026 Pat Simmons. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
# round.sh <hf_dir> <original.mp4> <saida.mp4> [FPS]: prévia sem motion blur (um subquadro por quadro).
# Mesmo caminho do round_mb.sh (um worker, ganho de luma, áudio sem -shortest, H.264 nível 5.1).
exec "${0:A:h}/round_mb.sh" "$1" "$2" "$3" 1 ${4:+"$4"}
