#!/bin/zsh
# Copyright (c) 2026 Pat Simmons. Licença MIT, texto completo em LICENCAS-DE-TERCEIROS.md.
# Adaptado para o Apple Style UI com as correções dos 3 primeiros clones.
#
# round_mb.sh <hf_dir> <original.mp4> <saida.mp4> [N] [FPS]
#   Renderiza a composição a FPS*N (N subquadros por quadro), tira a média de cada N (tmix) e devolve
#   um vídeo a FPS com motion blur de verdade. O obturador fica no draw() (estilo.js: quadro()), e o
#   MB_SHIFT do hf/mb.js centra os subquadros no quadro.
#   - FPS: o do original (padrão). N: 240/FPS (8 a 30 qps, 4 a 60 qps). N=1 é a prévia sem blur.
#   - Um worker só (com mais, o HyperFrames grava todos os quadros em disco antes de codificar).
#   - Recusa começar com menos de 2 GB livres (código 3). Apaga o bruto logo depois do tmix.
#   - Ganho de luma GANHO=1.008 só no Y (o encode do HyperFrames sai 0,8 % escuro; no croma piora).
#     LUMA_INSTAGRAM=1 soma a LUT dos níveis de um vídeo baixado do Instagram (escuros +2, brancos +1).
#   - Áudio do original sem -shortest (o vídeo manda no comprimento; -shortest comia quadros do fim).
#   - H.264 com -refs 4 -level:v 5.1 (sem nível fixo o QuickTime embaralha os blocos).
#   Brutos vão para ASUI_TMP (fora do repositório). HF_VERSAO fixa a versão do HyperFrames.
set -e
HF=${1:A}; ORIG=${2:A}; OUT=${3:A}
[ -d "$HF" ] && [ -f "$ORIG" ] || { echo "uso: round_mb.sh <hf_dir> <original.mp4> <saida.mp4> [N] [FPS]" >&2; exit 1; }
FPS=${5:-$(ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate -of csv=p=0 "$ORIG" | python3 -c "import sys; a,b=sys.stdin.read().strip().split('/'); print(round(int(a)/int(b)))")}
N=${4:-$((240 / FPS))}; [ "$N" -lt 1 ] && N=1
HI=$((FPS * N)); GANHO=${GANHO:-1.008}; HFV=${HF_VERSAO:-0.8.184}
TMP=${ASUI_TMP:-${TMPDIR:-/tmp}/apple-style-ui-render}; mkdir -p "$TMP" "${OUT:h}"
LIVRE=$(df -k "$TMP" | tail -1 | awk '{print $4}')
if [ "$LIVRE" -lt 2097152 ]; then echo "PARADO: só $((LIVRE / 1024)) MB livres (mínimo 2 GB)" >&2; exit 3; fi
# o cache de quadros de vídeo do HyperFrames também fica fora do repositório
export HYPERFRAMES_EXTRACT_CACHE_DIR=${HYPERFRAMES_EXTRACT_CACHE_DIR:-$TMP/hf-cache}
RAW="$TMP/${OUT:t:r}-$$-bruto.mp4"; V="$TMP/${OUT:t:r}-$$-v.mp4"
FILTRO="lutyuv=y='clip(16+(val-16)*$GANHO\,0\,255)'"
[ "${LUMA_INSTAGRAM:-0}" = 1 ] && FILTRO="$FILTRO,lutyuv=y='clip(val+0.5+if(lt(val\,73)\,2\,if(lt(val\,154)\,2*(154-val)/81\,if(lt(val\,233)\,0\,1)))\,0\,255)'"
echo "window.MB_SHIFT = $(python3 -c "print(($N-1)/2/$HI)");" > "$HF/mb.js"
trap 'echo "window.MB_SHIFT = 0;" > "$HF/mb.js"; rm -f "$RAW" "$V"' EXIT
T0=$(date +%s)
( cd "$HF" && npx --yes "hyperframes@$HFV" render --strict --quality ${HF_QUALIDADE:-draft} --workers 1 --fps $HI --output "$RAW" 2>&1 | grep -E "rendered in|rror" || true )
[ -s "$RAW" ] || { echo "o HyperFrames não gerou o bruto" >&2; exit 2; }
ffmpeg -v error -y -i "$RAW" -vf "tmix=frames=$N,select='not(mod(n+1\,$N))',setpts=N/($FPS*TB),$FILTRO" -r $FPS \
  -c:v libx264 -crf 16 -refs 4 -level:v 5.1 -pix_fmt yuv420p -an "$V"
rm -f "$RAW"
ffmpeg -v error -y -i "$V" -i "$ORIG" -map 0:v -map '1:a?' -c:v copy -c:a aac -b:a 192k "$OUT"
echo "render ${HI} qps + tmix $N: $(( $(date +%s) - T0 )) s; quadros $(ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=nb_read_frames -of csv=p=0 "$OUT")"
