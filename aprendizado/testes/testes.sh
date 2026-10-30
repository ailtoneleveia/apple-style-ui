#!/bin/zsh
# testes.sh: os testes da catraca (a régua do portão e o aprender.py).
#
#   zsh aprendizado/testes/testes.sh             uns 27 minutos; um render por vez (montador e portão usam --workers 1)
#   MANTER=1 zsh aprendizado/testes/testes.sh    guarda a pasta temporária mesmo quando tudo passa
#
# Tudo roda numa pasta temporária própria (mktemp -d), nunca na de uma sessão: os vídeos, os moldes alterados, o
# trabalho do portão (ASUI_TRABALHO) e um perfil de teste (ASUI_PERFIL). O perfil de verdade e os moldes não são tocados.
#
# Os quatro casos (COMO.md e ESTRUTURA.md, "O montador único e a régua do portão"):
#   1. padrões idênticos: a prévia de moldes/satellite/versoes/original.json pelo montador dá o md5 de sempre, e os três moldes
#      com os padrões passam na régua (Satellite idêntico; Joi e VoiceOS iguais dentro da tolerância);
#   2. pílula estourada: um item da lista longo demais REPROVA, e só por texto;
#   3. molde alterado: a pílula 4 px mais larga no molde REPROVA ("o molde mudou");
#   4. botão 20 % maior: com a junior aprovada, um molde que aumenta só o botão com texto trocado manda o próximo
#      aprovado para a QUARENTENA, porque a régua da junior mudou.
# Sai com 0 quando os quatro dão o esperado, 1 quando algum não dá.
#
# Nas versões dos casos 2 e 4 a cor principal é laranja: com o verde padrão, o portão acusa o matiz de 160° como cor
# fora da paleta (ver ESTRUTURA.md), e o motivo do teste ficaria misturado.

set -u
AQUI=${0:A:h}
PRODUTO=${AQUI:h:h}
M=$PRODUTO/moldes
APR=$PRODUTO/aprendizado
MONTAR=$PRODUTO/montar.py
MD5_ORIGINAL=61e3157750b0c70b88d0154dd33eabdf  # com o silencio.m4a do repositório (30/10); com o áudio do original era 877170713ecc12ba4889e671dc0250f5

T=$(mktemp -d -t asui-testes)
export ASUI_PERFIL=$T/perfil ASUI_TRABALHO=$T/trabalho
V=$T/videos
falhas=0
inicio=$SECONDS
print -r -- "pasta temporária: $T"

ok()  { print -r -- "  ok      $1"; }
nok() { print -r -- "  FALHOU  $1"; falhas=$((falhas + 1)); }
campo() { jq -r "$2" "$T/$1.json" 2>/dev/null; }   # campo <saída> <filtro jq>

# roda <saída> <comando...>: stdout em $T/<saída>.json, stderr em $T/<saída>.err; devolve o código de saída
roda() {
  local s=$1; shift
  "$@" > "$T/$s.json" 2> "$T/$s.err"
}

# molde <pasta>: cópia do Satellite com um montar.py ao lado (o portão importa o montar.py vizinho do molde)
molde() {
  mkdir -p "$1" && cp -R "$M/satellite/molde" "$1/satellite"
  cat > "$1/montar.py" <<EOF
import importlib.util as u, sys
sys.dont_write_bytecode = True
e = u.spec_from_file_location("montador", "$MONTAR")
m = u.module_from_spec(e)
e.loader.exec_module(m)
globals().update(m.api("satellite"))
EOF
}

# troca <arquivo> <de> <para>: troca exata, uma vez; falha se o trecho não estiver lá
troca() {
  python3 - "$@" <<'EOF'
import sys
f, a, b = sys.argv[1:]
s = open(f, encoding="utf-8").read()
assert s.count(a) == 1, f"trecho não encontrado em {f}: {a}"
open(f, "w", encoding="utf-8").write(s.replace(a, b))
EOF
}

# padroes <molde>: a régua do portão para o molde com os padrões, num processo por molde (o portão guarda um montar.py
# por processo). Imprime {"medida", "mudou"}.
padroes() {
  python3 -B -c 'import json, sys; sys.path.insert(0, sys.argv[1]); import portao
_, _, medida, mudou = portao.padroes(sys.argv[2])
print(json.dumps({"medida": medida, "mudou": mudou}, ensure_ascii=False))' "$APR" "$1"
}

print -r -- ""
print -r -- "1. padrões idênticos"
previa_original=""
if roda 1-montar python3 "$MONTAR" "$M/satellite/versoes/original.json" --molde satellite --previa --video "$V/original"; then
  previa_original=$(campo 1-montar '.arquivos[0]')
  md5=$(md5 -q "$previa_original")
  [[ $md5 == $MD5_ORIGINAL ]] && ok "md5 da prévia de original.json: $md5" || nok "md5 da prévia de original.json: $md5 (esperado $MD5_ORIGINAL)"
else
  nok "o montador não fez a prévia de original.json: $(tail -c 400 $T/1-montar.err)"
fi
for nome pasta in satellite "$M/satellite/molde" joi "$M/joi/molde" voiceos "$M/voiceos/molde"; do
  if roda 1-padroes-$nome padroes "$pasta"; then
    medida=$(campo 1-padroes-$nome '.medida')
    if [[ $(campo 1-padroes-$nome '.mudou') == null && ( $nome != satellite || $medida == idênticos ) ]]; then
      ok "$nome com os padrões passa na régua: $medida"
    else
      nok "$nome: $medida, $(campo 1-padroes-$nome '.mudou')"
    fi
  else
    nok "$nome: a régua não rodou: $(tail -c 400 $T/1-padroes-$nome.err)"
  fi
done

print -r -- ""
print -r -- "2. pílula estourada"
print -r -- '{"cor_principal": "#E54A26", "item1": "Problema no carro com o motor fundido no meio da estrada de terra, sem sinal de celular e sem ninguém por perto para ajudar"}' > "$T/pilula.json"
if roda 2-montar python3 "$MONTAR" "$T/pilula.json" --molde satellite --previa --video "$V/pilula"; then
  roda 2-portao python3 "$APR/portao.py" "$(campo 2-montar '.arquivos[0]')" --tipo versao --versao "$T/pilula.json" \
    --molde "$M/satellite/molde" --previa
  rc=$?
  textos=$(campo 2-portao '.portao.medidas["textos com problema"]')
  outros=$(campo 2-portao '[.portao.motivos[] | select(test("^(texto saindo da caixa|letra pequena demais)") | not)] | length')
  motivos=$(campo 2-portao '.portao.motivos | join(" | ")')
  [[ $rc == 1 && $(campo 2-portao '.portao.veredito') == REPROVOU && $textos -gt 0 && $outros == 0 ]] \
    && ok "portão REPROVOU só por texto ($textos): $motivos" || nok "portão: código $rc, $motivos"
else
  nok "o montador não fez a prévia da pílula: $(tail -c 400 $T/2-montar.err)"
fi

print -r -- ""
print -r -- "3. molde alterado"
molde "$T/molde-alterado"
troca "$T/molde-alterado/satellite/index.html" "p.W = Math.min(1040, Math.max(586, need));" "p.W = Math.min(1040, Math.max(590, need));"
if [[ -n $previa_original ]]; then
  roda 3-portao python3 "$APR/portao.py" "$previa_original" --tipo versao --versao "$M/satellite/versoes/original.json" \
    --molde "$T/molde-alterado/satellite" --previa
  rc=$?
  motivo=$(campo 3-portao '.portao.motivos[0]')
  [[ $rc == 1 && $(campo 3-portao '.portao.veredito') == REPROVOU && $motivo == "o molde mudou"* ]] \
    && ok "portão REPROVOU: $motivo" || nok "portão: código $rc, $(campo 3-portao '.resumo')"
else
  nok "sem a prévia de original.json do caso 1"
fi

print -r -- ""
print -r -- "4. botão 20 % maior"
molde "$T/molde-botao"
print -r -- '{"cor_principal": "#E54A26"}' > "$T/laranja.json"   # botão com o texto padrão: o molde alterado não mexe nele
if roda 4-final-junior python3 "$MONTAR" "$M/satellite/versoes/junior.json" --molde satellite --video "$V/junior" \
   && roda 4-final-laranja python3 "$MONTAR" "$T/laranja.json" --molde satellite --video "$V/laranja"; then
  roda 4-aprova-junior python3 "$APR/aprender.py" aprovar "$(campo 4-final-junior '.arquivos[0]')" --tipo versao \
    --versao "$M/satellite/versoes/junior.json" --molde "$T/molde-botao/satellite" --projeto "$V/junior" --quem teste --nota "teste da catraca"
  rc=$?
  [[ $rc == 0 && $(campo 4-aprova-junior '.resumo') == Aprovado* ]] \
    && ok "junior aprovada com o molde intacto" || nok "junior: código $rc, $(campo 4-aprova-junior '.resumo')"
  troca "$T/molde-botao/satellite/index.html" 'BW = 116 + grow(`590 27px ${FAM}`, 0, "botao");' \
    'BW = (116 + grow(`590 27px ${FAM}`, 0, "botao")) * (V.botao === DEF.botao ? 1 : 1.2);'
  roda 4-aprova-laranja python3 "$APR/aprender.py" aprovar "$(campo 4-final-laranja '.arquivos[0]')" --tipo versao \
    --versao "$T/laranja.json" --molde "$T/molde-botao/satellite" --projeto "$V/laranja" --quem teste --nota "teste da catraca"
  rc=$?
  codigo=$(grep '^{"ok": false' "$T/4-aprova-laranja.err" | tail -1 | jq -r '.codigo')
  mudou=$(campo 4-aprova-laranja '.mudancas[0]')
  [[ $rc == 1 && $codigo == QUARENTENA && $mudou == satellite-junior:* ]] \
    && ok "QUARENTENA: $mudou" || nok "laranja: código $rc ($codigo), $(campo 4-aprova-laranja '.resumo')"
else
  nok "o montador não fez os finais: $(tail -c 400 $T/4-final-*.err)"
fi

print -r -- ""
print -r -- "tempo: $(( (SECONDS - inicio) / 60 )) min $(( (SECONDS - inicio) % 60 )) s"
if (( falhas )); then
  print -r -- "RESULTADO: $falhas verificação(ões) falharam. A pasta fica para conferir: $T"
  exit 1
fi
if [[ -n ${MANTER:-} ]]; then
  print -r -- "RESULTADO: os quatro casos deram o esperado. Pasta guardada: $T"
else
  rm -rf "$T"   # só a pasta que este teste criou
  print -r -- "RESULTADO: os quatro casos deram o esperado."
fi
