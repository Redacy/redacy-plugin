#!/usr/bin/env bash
# redacy 0.3.1 · prove/grafi/prova-crea-codex.sh
#
# Prova che Codex sappia creare un workspace e un grafo con le skill del plugin.
# Si lancia da qualsiasi cartella: bash prove/grafi/prova-crea-codex.sh
# Chiama il modello una volta (timeout 600 secondi). Non tocca ~/.codex/.
# Finisce con una riga sola: PASSA oppure FALLISCE <perché>.

AQUI="$(cd "$(dirname "$0")" && pwd)"
source "$AQUI/_comune.sh"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  aiuto_prova codex prova-crea-codex.sh
  exit 0
fi

# PROVVISORIO: per far vedere le skill a Codex le copio dentro la cartella di prova,
# in .agents/skills/. Va sostituito dal metodo che F scrive in verifiche.md quando c'è.
copia_skill_per_codex() {
  local dir="$1" s
  mkdir -p "$dir/.agents/skills"
  for s in crea-workspace crea-grafo; do
    rm -rf "$dir/.agents/skills/$s"
    cp -R "$RADICE/skills/$s" "$dir/.agents/skills/$s"
    find "$dir/.agents/skills/$s" -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null
  done
}

# Sandbox workspace-write: Codex scrive solo dentro la cartella di prova.
lancia_agente() {
  local dir="$1" prompt="$2" trasc="$3"
  copia_skill_per_codex "$dir"
  "${TIMEOUT[@]}" codex exec --skip-git-repo-check -C "$dir" --sandbox workspace-write "$prompt" >"$trasc" 2>&1
}

prova_grafi codex
exit $?
