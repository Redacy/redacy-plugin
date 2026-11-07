#!/usr/bin/env bash
# redacy 0.3.1 · prove/grafi/prova-crea-claude.sh
#
# Prova che Claude Code sappia creare un workspace e un grafo con le skill del plugin.
# Si lancia da qualsiasi cartella: bash prove/grafi/prova-crea-claude.sh
# Chiama il modello una volta (sonnet, timeout 600 secondi).
# Finisce con una riga sola: PASSA oppure FALLISCE <perché>.

AQUI="$(cd "$(dirname "$0")" && pwd)"
source "$AQUI/_comune.sh"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  aiuto_prova claude prova-crea-claude.sh
  exit 0
fi

# Claude legge le skill dal plugin con --plugin-dir. Il prompt arriva da stdin perché
# --add-dir e --allowedTools prendono più valori e si mangerebbero un argomento finale.
lancia_agente() {
  local dir="$1" prompt="$2" trasc="$3"
  (
    cd "$dir" && printf '%s' "$prompt" | "${TIMEOUT[@]}" claude -p \
      --plugin-dir "$RADICE" \
      --model sonnet \
      --permission-mode acceptEdits \
      --add-dir "$RADICE" \
      --allowedTools "Bash(python3:*),Bash(ls:*),Skill,Read,Write,Edit,Glob,Grep"
  ) >"$trasc" 2>&1
}

prova_grafi claude
exit $?
