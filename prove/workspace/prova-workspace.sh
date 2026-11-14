#!/usr/bin/env bash
# redacy 0.4.2 · prove/workspace/prova-workspace.sh
# crea-workspace.py e controlla-workspace.py: nomi riservati e strani, memoria che non si legge o non si scrive,
# rilancio che completa le righe mancanti, controlla-workspace su una cartella che non è un workspace.
# Tutta la logica sta in _robusto.py (gira anche su macOS e in Git Bash su Windows). Ultima riga: PASSA o FALLISCE <perché>.
# Cartelle di prova: $REDACY_PROVE (default ${TMPDIR:-/tmp}/redacy-plugin-prove). Nessun dato vero, niente rete.
set -u
export PYTHONDONTWRITEBYTECODE=1
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove}/workspace-$$"
rm -rf "$BASE"; mkdir -p "$BASE"
"${PYTHON:-python3}" "$RADICE/prove/workspace/_robusto.py" "$RADICE" "$BASE"
RC=$?
rm -rf "$BASE"
exit "$RC"
