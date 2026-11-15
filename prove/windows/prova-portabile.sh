#!/usr/bin/env bash
# redacy 0.5.0 · prove/windows/prova-portabile.sh
# Prova, da macOS o Linux, i rami che servono su Windows: il lucchetto di file senza fcntl, la partenza
# del pannello senza fork, il controllo del processo senza os.kill, i comandi degli hook e del launch.json,
# i percorsi con la barra rovesciata, il collegamento di cartella. Il sistema non è Windows: si forza il
# ramo con le funzioni su_windows() e con moduli finti (msvcrt, kernel32). Non sostituisce una prova
# su un Windows vero: vedi l'elenco dei controlli da fare a mano nel rapporto di consegna.
# Finisce con PASSA o FALLISCE <perché>.
set -u
QUI="$(cd "$(dirname "$0")" && pwd)"
RADICE="$(cd "$QUI/../.." && pwd)"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
mkdir -p "$BASE"
# PYTHON può valere anche due parole (py -3): si espande senza virgolette, e si controlla la prima.
PYTHON="${PYTHON:-python3}"
command -v "${PYTHON%% *}" >/dev/null 2>&1 || { echo "FALLISCE manca ${PYTHON%% *}"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
# Il limite di tempo: timeout (Linux, Git Bash) o gtimeout (macOS con coreutils); se non c'è, nessun limite.
LIMITE=""
if command -v timeout >/dev/null 2>&1; then
  LIMITE="timeout 120"
elif command -v gtimeout >/dev/null 2>&1; then
  LIMITE="gtimeout 120"
fi
# shellcheck disable=SC2086
$LIMITE $PYTHON -I "$QUI/_portabile.py" "$RADICE" "$BASE/windows-$$"
