#!/usr/bin/env bash
# prova-pagina.sh · redacy 0.4.0
# La pagina del pannello in un browser vero, contro il server vero, su una cartella fatta da `inizia`
# con dati finti e una corsa per stato:
#  - pagina.html è quella che esce dai pezzi in skills/pannello/sorgenti (costruisci.py --controlla);
#  - la pagina prende i dati dal server e non scrive errori in console, nemmeno di Content-Security-Policy;
#  - niente bottoni rossi; «Ferma» da Oggi, con la conferma, ferma la corsa in corso.
# Senza Node 22+ o senza un Chromium la parte nel browser dice SALTA (e la prova PASSA lo stesso,
# dicendolo). Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/pannello/prova-pagina.sh
# Le cartelle di prova vanno in $REDACY_PROVE (default ${TMPDIR:-/tmp}/redacy-plugin-prove/D).
set -u

RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
PANNELLO="$RADICE/skills/pannello/scripts/pannello.py"
PREPARA="$RADICE/prove/pannello/_prepara.py"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove/D}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
G="$BASE/pagina-$ORA"
D="$G/studio"
mkdir -p "$G"

fallisce() { echo "FALLISCE $*"; python3 "$PANNELLO" --cartella "$D" --spegni >/dev/null 2>&1; exit 1; }

# 1. pagina.html viene dai pezzi
python3 "$RADICE/skills/pannello/sorgenti/costruisci.py" --controlla >/dev/null \
  || fallisce "pagina.html non è quella dei pezzi: rilancia skills/pannello/sorgenti/costruisci.py"

# 2. la cartella finta e il pannello acceso
python3 "$PREPARA" "$D" --corse > "$G/ids.txt" 2> "$G/prepara.err" || fallisce "_prepara.py non riesce: $(cat "$G/prepara.err")"
IN_CORSO="$(sed -n 's/^in-corso=//p' "$G/ids.txt")"
[ -n "$IN_CORSO" ] || fallisce "manca l'id della corsa in corso"
USCITA="$(python3 "$PANNELLO" --cartella "$D" 2>&1)" || fallisce "pannello.py non parte: $USCITA"
URL="$(echo "$USCITA" | grep -o 'http://127.0.0.1:[0-9]*/' | head -1)"
[ -n "$URL" ] || fallisce "non trovo l'indirizzo nell'uscita: $USCITA"

# 3. la pagina nel browser
if ! command -v node >/dev/null; then
  python3 "$PANNELLO" --cartella "$D" --spegni >/dev/null 2>&1
  echo "PASSA (la parte nel browser SALTA: manca node)"; exit 0
fi
ESITO="$(node "$RADICE/prove/pannello/prova-pagina.mjs" "$URL" "$IN_CORSO" "$G/foto" 2>&1)"
CODICE=$?
python3 "$PANNELLO" --cartella "$D" --spegni >/dev/null 2>&1
ULTIMA="$(echo "$ESITO" | tail -1)"
[ $CODICE -eq 0 ] || { echo "FALLISCE ${ULTIMA#FALLISCE }"; exit 1; }
case "$ULTIMA" in
  SALTA*) echo "PASSA (la parte nel browser $ULTIMA)";;
  PASSA*) echo "PASSA ${ULTIMA#PASSA } · foto in $G/foto";;
  *) echo "FALLISCE uscita inattesa: $ULTIMA"; exit 1;;
esac
