#!/usr/bin/env bash
# redacy 0.4.2 · prove/ci/lancia-tutte.sh
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
cd "$RADICE"
bash prove/tutte.sh
