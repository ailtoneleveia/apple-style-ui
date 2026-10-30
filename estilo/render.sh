#!/bin/zsh
# render.sh [previa|final]: renderiza a demo do estilo.js.
#   previa: 30 fps, sem motion blur.
#   final: 240 fps (8 subquadros), tmix 8 -> 30 fps, luma calibrada (ESTILO.LUMA), H.264 que o QuickTime aceita.
# Brutos vão para a pasta temporária e são apagados logo depois do tmix. Para se o disco tiver menos de 2 GB livres.
set -e
MODO=${1:-final}
E="${0:A:h}"; D="$E/demo"; OUT="$E/saidas"
TMP=${ESTILO_TMP:-${TMPDIR:-/tmp}/apple-style-ui-estilo}
# a SF Pro não vai no repositório: a demo usa a do sistema (macOS) ou, sem ela ou com ASUI_FONTE_LIVRE=1, a Inter
mkdir -p "$D/assets/fonts"
if [ "${ASUI_FONTE_LIVRE:-0}" = 1 ] || [ ! -f /System/Library/Fonts/SFNS.ttf ]; then cp "$E/../moldes/satellite/molde/assets/fonts/Inter.ttf" "$D/assets/fonts/SFNS.ttf"
else cp /System/Library/Fonts/SFNS.ttf "$D/assets/fonts/SFNS.ttf"; fi
mkdir -p "$TMP" "$OUT"
LIVRE=$(df -g "$TMP" | tail -1 | awk '{print $4}')
if [ "$LIVRE" -lt 2 ]; then echo "PARADO: só $LIVRE GB livres (mínimo 2)"; exit 1; fi
FPS=30; N=8; HI=$((FPS * N))
X264=(-c:v libx264 -preset veryslow -tune animation -crf 12 -refs 4 -level:v 5.1 -pix_fmt yuv420p -movflags +faststart)
# luma: ganho do Satellite + LUT dos escuros do Joi (estilo.js, LUMA.filtro)
LUMA=$(cd "$E" && node -e 'process.stdout.write(require("./estilo.js").LUMA.filtro)')
T0=$(date +%s)
if [ "$MODO" = previa ]; then
  echo "window.MB_SHIFT = 0;" > "$D/mb.js"
  ( cd "$D" && npx --yes hyperframes@0.8.184 render --workers 1 --fps $FPS --crf 10 --output "$TMP/previa-raw.mp4" 2>&1 | grep -E "rendered in|rror" || true )
  ffmpeg -v error -y -i "$TMP/previa-raw.mp4" -vf "$LUMA" -r $FPS "${X264[@]}" -an "$OUT/demo-previa.mp4"
  rm -f "$TMP/previa-raw.mp4"
else
  echo "window.MB_SHIFT = $(python3 -c "print(($N-1)/2/$HI)");" > "$D/mb.js"
  ( cd "$D" && npx --yes hyperframes@0.8.184 render --workers 1 --fps $HI --crf 10 --output "$TMP/demo-raw.mp4" 2>&1 | grep -E "rendered in|rror" || true )
  echo "window.MB_SHIFT = 0;" > "$D/mb.js"
  T1=$(date +%s); echo "render 240 fps: $((T1 - T0)) s; bruto $(du -h "$TMP/demo-raw.mp4" | cut -f1)"
  ffmpeg -v error -y -i "$TMP/demo-raw.mp4" -vf "tmix=frames=$N,select='not(mod(n+1\,$N))',setpts=N/($FPS*TB),$LUMA" -r $FPS "${X264[@]}" -an "$OUT/demo.mp4"
  rm -f "$TMP/demo-raw.mp4"
fi
echo "pronto em $(( $(date +%s) - T0 )) s: $(ls "$OUT"/demo*.mp4 | tr '\n' ' ')"
ffprobe -v error -count_frames -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_read_frames -of csv=p=0 "$OUT/demo$([ "$MODO" = previa ] && echo -previa).mp4"
