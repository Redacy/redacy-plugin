#!/usr/bin/env bash
# redacy 0.3.0 · prove/grafi/prova-controllo.sh
#
# Prova tecnica di controlla-grafo.py e yaml_ridotto.py.
# Accetta i grafi buoni, rifiuta quelli rotti e una serie di casi piccoli,
# controllando anche che il messaggio nomini il campo o la riga giusta.
# Si lancia da qualsiasi cartella: bash prove/grafi/prova-controllo.sh
# Finisce con una riga sola: PASSA oppure FALLISCE <perché>.

AQUI="$(cd "$(dirname "$0")" && pwd)"
RADICE="$(cd "$AQUI/../.." && pwd)"
SCRIPTS="$RADICE/skills/crea-grafo/scripts"
CONTROLLO="$SCRIPTS/controlla-grafo.py"
BUONI="$AQUI/buoni"
ROTTI="$AQUI/rotti"
PROVE_BASE="/home/ubuntu/lab/redacy-plugin-prove/B"

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  echo "Uso: bash prove/grafi/prova-controllo.sh"
  echo "Prova controlla-grafo.py sui grafi buoni, su quelli rotti e su casi piccoli."
  echo "Crea cartelle temporanee sotto $PROVE_BASE. Ultima riga: PASSA oppure FALLISCE <perché>."
  exit 0
fi

FALLITI=""
SEGNA() { FALLITI="${FALLITI}${FALLITI:+; }$1"; }

for f in "$CONTROLLO" "$SCRIPTS/yaml_ridotto.py"; do
  [ -f "$f" ] || { echo "FALLISCE manca $f"; exit 1; }
done

mkdir -p "$PROVE_BASE" || { echo "FALLISCE non riesco a creare $PROVE_BASE"; exit 1; }
T="$(mktemp -d "$PROVE_BASE/controllo-XXXXXX")" || { echo "FALLISCE mktemp"; exit 1; }

# controlla: lancia il controllo isolato (-I) su un file o cartella; mette in $USCITA e $TESTO
controlla() {
  TESTO="$(python3 -I "$CONTROLLO" "$@" 2>&1)"
  USCITA=$?
}

# deve_passare <etichetta> <percorso>
deve_passare() {
  controlla "$2"
  if [ "$USCITA" -eq 0 ]; then
    echo "ok   accettato: $1"
  else
    echo "KO   doveva essere accettato: $1"
    echo "$TESTO" | sed 's/^/       /'
    SEGNA "rifiutato un grafo buono ($1)"
  fi
}

# deve_fallire <etichetta> <percorso> <parola che deve comparire nel messaggio> [altra parola]
deve_fallire() {
  etichetta="$1"; percorso="$2"; shift 2
  controlla "$percorso"
  if [ "$USCITA" -ne 1 ]; then
    echo "KO   doveva essere rifiutato (uscita 1, trovata $USCITA): $etichetta"
    SEGNA "non rifiutato ($etichetta)"
    return
  fi
  for parola in "$@"; do
    if ! echo "$TESTO" | grep -qiF -- "$parola"; then
      echo "KO   rifiutato ma il messaggio non nomina \"$parola\": $etichetta"
      echo "$TESTO" | sed 's/^/       /'
      SEGNA "messaggio senza \"$parola\" ($etichetta)"
      return
    fi
  done
  echo "ok   rifiutato: $etichetta"
}

echo "-- i tre grafi buoni"
for f in "$BUONI"/*.yaml; do
  deve_passare "$(basename "$f")" "$f"
done
controlla "$BUONI"
if [ "$USCITA" -eq 0 ] && echo "$TESTO" | grep -q "3 grafi controllati, nessun errore"; then
  echo "ok   la cartella dei buoni: 3 grafi, nessun errore"
else
  echo "KO   la cartella dei buoni"; echo "$TESTO" | sed 's/^/       /'
  SEGNA "cartella dei buoni non pulita"
fi

echo "-- i tre grafi rotti"
deve_fallire "manca-autonomia.yaml" "$ROTTI/manca-autonomia.yaml" "autonomia" "manca"
RIGA_DOPO="$(grep -n '^    dopo: \[leggi-tutto\]' "$ROTTI/dopo-inesistente.yaml" | cut -d: -f1)"
deve_fallire "dopo-inesistente.yaml (riga $RIGA_DOPO)" "$ROTTI/dopo-inesistente.yaml" "dopo-inesistente.yaml:$RIGA_DOPO:" "dopo" "leggi-tutto"
RIGA_ANC="$(grep -n '^tetti: &base' "$ROTTI/yaml-con-ancora.yaml" | cut -d: -f1)"
deve_fallire "yaml-con-ancora.yaml (riga $RIGA_ANC)" "$ROTTI/yaml-con-ancora.yaml" "yaml-con-ancora.yaml:$RIGA_ANC:" "ancora"

echo "-- casi piccoli"
BASE="$T/prova-base.yaml"
cat > "$BASE" <<'EOF'
grafo: prova-base
versione: 1
obiettivo: Un grafo minimo per le prove.
acceso: false
innesco: {tipo: parola}
passi:
  - id: lavora
    tipo: agente
    workspace: orchestratore
    prompt: Fai la prova.
  - id: rivedi
    tipo: umano
    forma: lettura
    dove: il pannello
tetti: {contemporanee: 1}
uscite: []
autonomia: {livello: L0, da: 2026-11-07, si: null}
EOF
deve_passare "il grafo minimo di partenza" "$BASE"

# caso <nome-file senza .yaml> <etichetta> <parole attese...>  (il contenuto arriva da stdin)
caso() {
  nome="$1"; etichetta="$2"; shift 2
  cat > "$T/$nome.yaml"
  deve_fallire "$etichetta" "$T/$nome.yaml" "$@"
}

# 1. nome del file diverso dal nome del grafo
cp "$BASE" "$T/altro-nome.yaml"
deve_fallire "nome del file diverso dal nome del grafo" "$T/altro-nome.yaml" "grafo" "prova-base" "altro-nome"

# 2. ciclo fra i passi
caso ciclo "ciclo fra i passi" "ciclo" <<'EOF'
grafo: ciclo
versione: 1
obiettivo: Due passi che si aspettano a vicenda.
acceso: false
innesco: {tipo: parola}
passi:
  - id: uno
    tipo: agente
    workspace: orchestratore
    prompt: Fai uno.
  - id: due
    tipo: agente
    dopo: [tre]
    workspace: orchestratore
    prompt: Fai due.
  - id: tre
    tipo: agente
    dopo: [due]
    workspace: orchestratore
    prompt: Fai tre.
tetti: {contemporanee: 1}
uscite: []
autonomia: {livello: L0, da: 2026-11-07, si: null}
EOF

# 3. id ripetuto
caso id-ripetuto "id ripetuto fra i passi" "ripetuto" "lavora" <<'EOF'
grafo: id-ripetuto
versione: 1
obiettivo: Due passi con lo stesso id.
acceso: false
innesco: {tipo: parola}
passi:
  - id: lavora
    tipo: agente
    workspace: orchestratore
    prompt: Fai uno.
  - id: lavora
    tipo: agente
    workspace: orchestratore
    prompt: Fai due.
tetti: {contemporanee: 1}
uscite: []
autonomia: {livello: L0, da: 2026-11-07, si: null}
EOF

# 4. acceso true con si null
sed 's/^acceso: false/acceso: true/; s/^grafo: prova-base/grafo: acceso-senza-si/' "$BASE" > "$T/acceso-senza-si.yaml"
deve_fallire "acceso true con si null" "$T/acceso-senza-si.yaml" "acceso" "si"

# 5. livello L1 con si null
sed 's/livello: L0/livello: L1/; s/^grafo: prova-base/grafo: livello-senza-si/' "$BASE" > "$T/livello-senza-si.yaml"
deve_fallire "livello L1 con si null" "$T/livello-senza-si.yaml" "livello" "si"

# 6. innesco orario senza quando
sed 's/^innesco: {tipo: parola}/innesco: {tipo: orario}/; s/^tetti: .*/tetti: {contemporanee: 1, corse_al_giorno: 1}/; s/^grafo: prova-base/grafo: orario-senza-quando/' "$BASE" > "$T/orario-senza-quando.yaml"
deve_fallire "innesco orario senza quando" "$T/orario-senza-quando.yaml" "quando" "orario"

# 7. campo sconosciuto
sed 's/^versione: 1/versione: 1\ncolore: blu/; s/^grafo: prova-base/grafo: campo-sconosciuto/' "$BASE" > "$T/campo-sconosciuto.yaml"
deve_fallire "campo sconosciuto" "$T/campo-sconosciuto.yaml" "colore" "sconosciuto" "campo-sconosciuto.yaml:3:"

# 8. tabulazione nel rientro
printf 'grafo: con-tabulazione\nversione: 1\nobiettivo: Prova.\nacceso: false\ninnesco: {tipo: parola}\npassi:\n\t- id: lavora\n\t  tipo: agente\ntetti: {contemporanee: 1}\nuscite: []\nautonomia: {livello: L0, da: 2026-11-07, si: null}\n' > "$T/con-tabulazione.yaml"
deve_fallire "tabulazione nel rientro" "$T/con-tabulazione.yaml" "tabulazion" "con-tabulazione.yaml:7:"

# 9. un passo agente che manca, e un orario senza fuso (avviso, non errore)
sed 's/^innesco: {tipo: parola}/innesco: {tipo: orario, quando: "ogni giorno alle 21:00"}/; s/^tetti: .*/tetti: {contemporanee: 1, corse_al_giorno: 1}/; s/^grafo: prova-base/grafo: orario-senza-fuso/' "$BASE" > "$T/orario-senza-fuso.yaml"
controlla "$T/orario-senza-fuso.yaml"
if [ "$USCITA" -eq 0 ] && echo "$TESTO" | grep -q "^avviso: .*fuso"; then
  echo "ok   orario senza fuso: solo un avviso, uscita 0"
else
  echo "KO   orario senza fuso"; echo "$TESTO" | sed 's/^/       /'
  SEGNA "orario senza fuso non dà un avviso"
fi

# 10. avviso per un workspace che non c'è, solo dentro una cartella dello studio
mkdir -p "$T/studio/grafi" "$T/studio/workspace/esiste"
: > "$T/studio/AGENTS.md"
sed 's/^    workspace: orchestratore/    workspace: non-esiste/; s/^grafo: prova-base/grafo: workspace-assente/' "$BASE" > "$T/studio/grafi/workspace-assente.yaml"
controlla "$T/studio/grafi/workspace-assente.yaml"
if [ "$USCITA" -eq 0 ] && echo "$TESTO" | grep -q "^avviso: .*non-esiste"; then
  echo "ok   workspace che non c'è: avviso, uscita 0"
else
  echo "KO   workspace che non c'è"; echo "$TESTO" | sed 's/^/       /'
  SEGNA "workspace assente non dà un avviso"
fi
sed 's/^    workspace: orchestratore/    workspace: esiste/; s/^grafo: prova-base/grafo: workspace-presente/' "$BASE" > "$T/studio/grafi/workspace-presente.yaml"
controlla "$T/studio/grafi/workspace-presente.yaml"
if [ "$USCITA" -eq 0 ] && ! echo "$TESTO" | grep -q "^avviso:"; then
  echo "ok   workspace che c'è: nessun avviso"
else
  echo "KO   workspace che c'è"; echo "$TESTO" | sed 's/^/       /'
  SEGNA "workspace presente dà un avviso"
fi

echo "-- niente PyYAML"
if grep -rnE '^[[:space:]]*(import|from)[[:space:]]+yaml([[:space:]]|\.|$)' "$SCRIPTS" >/dev/null 2>&1; then
  echo "KO   c'è un import di yaml negli script"
  SEGNA "import yaml negli script"
else
  echo "ok   nessun import di yaml negli script"
fi
if python3 -I -c "
import sys
sys.path.insert(0, '$SCRIPTS')
import yaml_ridotto
assert 'yaml' not in sys.modules
print('ok   il lettore si importa senza PyYAML')" ; then :; else
  echo "KO   il lettore non si importa in modalità isolata"
  SEGNA "yaml_ridotto non importabile"
fi

echo "-- il lettore da riga di comando"
JSON="$(python3 -I "$SCRIPTS/yaml_ridotto.py" "$BUONI/riepilogo-fatture-settimana.yaml" 2>&1)"
if echo "$JSON" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['passi'][1]['minuti']==20 and d['acceso'] is True and d['autonomia']['si'].startswith('Marta')"; then
  echo "ok   yaml_ridotto.py stampa il JSON giusto"
else
  echo "KO   yaml_ridotto.py non stampa il JSON atteso"
  SEGNA "JSON del lettore"
fi
python3 -I "$SCRIPTS/yaml_ridotto.py" "$ROTTI/yaml-con-ancora.yaml" >/dev/null 2>&1
if [ $? -eq 1 ]; then echo "ok   yaml_ridotto.py esce con 1 sul file rotto"; else
  echo "KO   yaml_ridotto.py non esce con 1 sul file rotto"; SEGNA "uscita del lettore sul rotto"; fi

rm -rf "$T"

if [ -z "$FALLITI" ]; then
  echo "PASSA"
else
  echo "FALLISCE $FALLITI"
  exit 1
fi
