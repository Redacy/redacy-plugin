#!/usr/bin/env bash
# prova-stop-claude.sh · redacy 0.4.0
# Lo stop dal pannello con Claude Code, in due scenari, ognuno con due conversazioni (`claude -p`)
# nella stessa cartella dello studio:
#   1. senza l'hook: lo stop passa dal livello 1, corsa.py esce con 3 al comando dopo lo stop;
#   2. con l'hook ferma.py (PreToolUse): lo stop nega il comando dopo lo stop (e si vede il marcatore
#      grafi/corse/.<id>.notificato che solo l'hook scrive).
# In tutti e due la corsa dell'altra conversazione non è toccata. Dettagli in prove/pannello/_stop.sh.
# Finisce con PASSA o FALLISCE <perché>. Usa 4 chiamate a `claude -p --model sonnet` (timeout 600 l'una).
#
# Uso: bash prove/pannello/prova-stop-claude.sh
set -u
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove/D}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
LAVORO="$BASE/stop-claude-$ORA"
mkdir -p "$LAVORO"
# shellcheck source=_stop.sh
source "$(dirname "$0")/_stop.sh"
command -v claude >/dev/null || { echo "FALLISCE manca claude"; exit 1; }
command -v curl >/dev/null || { echo "FALLISCE manca curl"; exit 1; }

scenario() { # <nome> <con_hook si|no>
  local nome="$1" hook="$2"
  D="$LAVORO/$nome"
  echo "--- scenario $nome (hook: $hook)"
  prepara_cartella "$D" "$hook"
  python3 "$PANNELLO" --cartella "$D" > "$LAVORO/$nome-pannello.txt" 2>&1 || fallisce "il pannello non parte: $(cat "$LAVORO/$nome-pannello.txt")"
  ( cd "$D" && timeout 600 claude -p --model sonnet --plugin-dir "$RADICE" --allowedTools "Bash" -- \
      "$(prompt_conversazione A giro-lento CLAUDE_CODE_SESSION_ID)" < /dev/null > "$LAVORO/$nome-A.out" 2>&1 ) &
  local pa=$!
  ( cd "$D" && timeout 600 claude -p --model sonnet --plugin-dir "$RADICE" --allowedTools "Bash" -- \
      "$(prompt_conversazione B giro-altro CLAUDE_CODE_SESSION_ID)" < /dev/null > "$LAVORO/$nome-B.out" 2>&1 ) &
  local pb=$!
  aspetta_e_ferma "$D" 420
  wait "$pa" "$pb"
  echo "A: $(tail -c 300 "$LAVORO/$nome-A.out" | tr '\n' ' ')"
  echo "B: $(tail -c 200 "$LAVORO/$nome-B.out" | tr '\n' ' ')"
  controlla "$D" "$hook"
  python3 "$PANNELLO" --cartella "$D" --spegni > /dev/null 2>&1
  echo "scenario $nome: ok"
}

scenario livello1 no
scenario livello2 si
echo "PASSA"
