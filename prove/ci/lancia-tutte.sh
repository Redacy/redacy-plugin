#!/usr/bin/env bash
# redacy 0.5.0 · prove/ci/lancia-tutte.sh
# Lancia prove/tutte.sh dalle macchine di GitHub. Su Windows (Git Bash) `python3` di solito non c'è: si
# mette sul PATH un `python3` che chiama `python`, solo per questa corsa, così le prove non cambiano.
set -eu
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
if [ "${RUNNER_OS:-}" = "Windows" ] && ! command -v python3 >/dev/null 2>&1; then
  BIN="${RUNNER_TEMP:-/tmp}/bin-python3"
  mkdir -p "$BIN"
  printf '#!/bin/sh\nexec python "$@"\n' > "$BIN/python3"
  chmod +x "$BIN/python3"
  export PATH="$BIN:$PATH"
fi

# Il Chromium per la prova della pagina: su Ubuntu `chromium` è un guscio snap che non parte, si usa il Chrome dei runner.
if [ -z "${REDACY_CHROMIUM:-}" ]; then
  for c in /usr/bin/google-chrome "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    if [ -x "$c" ]; then export REDACY_CHROMIUM="$c"; break; fi
  done
fi
echo "Chromium per la prova della pagina: ${REDACY_CHROMIUM:-nessuno}"
cd "$RADICE"
USCITA="${RUNNER_TEMP:-/tmp}/tutte-uscita.txt"
bash prove/tutte.sh 2>&1 | tee "$USCITA"
CODICE="${PIPESTATUS[0]}"
# Chrome sul runner a volte non si apre entro i 20 secondi della prova: se è l'unica prova rossa, si rilancia quella sola, una volta, e si vede nel registro.
if [ "$CODICE" -ne 0 ] && [ "$(tail -1 "$USCITA")" = "ESITO: FALLISCE pannello: la pagina vera nel browser" ]; then
  echo "Chrome non si è aperto: rilancio una volta la sola prova della pagina"
  bash prove/pannello/prova-pagina.sh
  exit $?
fi
exit "$CODICE"
