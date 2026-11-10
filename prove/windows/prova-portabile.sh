#!/usr/bin/env bash
# redacy 0.4.2 · prove/windows/prova-portabile.sh
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
command -v python3 >/dev/null || { echo "FALLISCE manca python3"; exit 1; }
export PYTHONDONTWRITEBYTECODE=1
timeout 120 python3 -I "$QUI/_portabile.py" "$RADICE" "$BASE/windows-$$"
