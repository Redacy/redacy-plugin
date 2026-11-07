#!/usr/bin/env bash
# redacy 0.3.0 - prove/grafi/prova-corsa.sh
# Prova corsa.py su una cartella di studio finta. Una riga per controllo,
# in fondo una sola riga: PASSA oppure FALLISCE <perche'>.
# Uso: bash prove/grafi/prova-corsa.sh [--tieni]   (--tieni lascia la cartella di prova)
# La cartella di prova sta sotto $REDACY_PROVE (default /home/ubuntu/lab/redacy-plugin-prove/B).

set -u
if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'
  exit 0
fi
TIENI=0
[ "${1:-}" = "--tieni" ] && TIENI=1

QUI=$(cd "$(dirname "$0")" && pwd)
SCRIPT_DIR=$(cd "$QUI/../../skills/crea-grafo/scripts" && pwd)
CORSA="$SCRIPT_DIR/corsa.py"
BASE=${REDACY_PROVE:-/home/ubuntu/lab/redacy-plugin-prove/B}
mkdir -p "$BASE"
D=$(mktemp -d "$BASE/corsa-XXXX")
unset REDACY_CARTELLA

ERRORI=()
controllo() {  # controllo "descrizione" comando...
  local desc=$1
  shift
  if "$@" >/dev/null 2>&1; then
    echo "ok    $desc"
  else
    echo "NO    $desc"
    ERRORI+=("$desc")
  fi
}
uguale() {  # uguale "descrizione" atteso effettivo
  if [ "$2" = "$3" ]; then
    echo "ok    $1"
  else
    echo "NO    $1 (atteso '$2', trovato '$3')"
    ERRORI+=("$1")
  fi
}
C() { (cd "$D" && python3 "$CORSA" "$@"); }       # lancia corsa.py dalla cartella dello studio
rc() { "$@" >/dev/null 2>&1; echo $?; }            # restituisce solo il codice di uscita
J() {  # J file 'espressione su c'  -> stampa il valore
  python3 -c 'import json,sys
c=json.load(open(sys.argv[1]))
v=eval(sys.argv[2])
print("null" if v is None else v)' "$1" "$2"
}
F() { echo "$D/grafi/corse/$1.json"; }

# ---------------------------------------------------------------- lo studio finto
FUORI=$(mktemp -d "$BASE/fuori-XXXX")   # una cartella che non sta dentro lo studio
mkdir -p "$D/grafi" "$D/sotto/cartella/profonda"
echo "# Studio di prova (dati inventati)" > "$D/AGENTS.md"
cat > "$D/grafi/giro-prova.yaml" <<'YAML'
grafo: giro-prova
versione: 3
obiettivo: "Prova di una corsa con tre passi"
acceso: false
innesco: {tipo: parola}
passi:
  - id: leggi
    tipo: agente
    nome: Leggi
    workspace: orchestratore
    prompt: "Leggi il materiale di prova"
  - id: scrivi
    tipo: agente
    nome: Scrivi
    workspace: orchestratore
    prompt: "Scrivi una bozza di prova"
  - id: consegna
    tipo: umano
    nome: Consegna
    forma: lettura
    dove: "il pannello"
tetti:
  contemporanee: 1
uscite: []
autonomia:
  livello: L0
  da: 2026-11-07
  si: null
YAML
cat > "$D/grafi/rotto.yaml" <<'YAML'
grafo: rotto
versione: 1
passi: []
YAML

# ---------------------------------------------------------------- (a) corsa fermata
A=$(C apri giro-prova --avviato-da utente 2>"$D/apri-a.err")
uguale "(a) apri stampa un id" "giro-prova" "$(echo "$A" | sed -E 's/-[0-9]{8}-[0-9]{6}(-[0-9]+)?$//')"
controllo "(a) il file della corsa esiste" test -f "$(F "$A")"
uguale "(a) tre passi, tutti da-fare" "da-fare da-fare da-fare" "$(J "$(F "$A")" '" ".join(p["stato"] for p in c["passi"])')"
uguale "(a) ordine dei passi come nel grafo" "leggi scrivi consegna" "$(J "$(F "$A")" '" ".join(p["id"] for p in c["passi"])')"
uguale "(a) versione del grafo" "3" "$(J "$(F "$A")" 'c["versione"]')"
uguale "(a) passo 1 inizio" "0" "$(rc C passo "$A" leggi inizio)"
uguale "(a) passo 1 fatto con esito" "0" "$(rc C passo "$A" leggi fatto --esito "14 messaggi letti")"
uguale "(a) passo 2 inizio" "0" "$(rc C passo "$A" scrivi inizio)"
uguale "(a) ferma da pannello" "0" "$(rc C ferma "$A" --da pannello --perche "prova")"
SA=$(F "$A")
uguale "(a) stato fermata" "fermata" "$(J "$SA" 'c["stato"]')"
uguale "(a) stop.chi" "pannello" "$(J "$SA" 'c["stop"]["chi"]')"
uguale "(a) stop.perche" "prova" "$(J "$SA" 'c["stop"]["perche"]')"
controllo "(a) stop.quando e fine valorizzati" python3 -c 'import json,sys;c=json.load(open(sys.argv[1]));assert c["stop"]["quando"] and c["fine"]' "$SA"
uguale "(a) passo 1 fatto con esito" "fatto|14 messaggi letti" "$(J "$SA" 'c["passi"][0]["stato"]+"|"+c["passi"][0]["esito"]')"
uguale "(a) passo 2 fermato, con fine" "fermato|1" "$(J "$SA" 'c["passi"][1]["stato"]+"|"+str(int(c["passi"][1]["fine"] is not None))')"
uguale "(a) passo 3 resta da-fare" "da-fare" "$(J "$SA" 'c["passi"][2]["stato"]')"
uguale "(a) stato: ultima riga dice fermata" "fermata" "$(C stato "$A" | tail -n 1)"
uguale "(a) stato: il JSON stampato e' valido" "fermata" "$(C stato "$A" | sed '$d' | python3 -c 'import json,sys;print(json.load(sys.stdin)["stato"])')"
uguale "(a) passo su corsa fermata esce 3" "3" "$(rc C passo "$A" scrivi fatto)"
uguale "(a) chiudi su corsa fermata esce 3" "3" "$(rc C chiudi "$A" finita)"
uguale "(a) battito su corsa fermata esce 3" "3" "$(rc C battito "$A")"
uguale "(a) ferma su corsa fermata esce 3" "3" "$(rc C ferma "$A")"
uguale "(a) il passo 2 non e' cambiato dopo il 3" "fermato" "$(J "$SA" 'c["passi"][1]["stato"]')"

# ---------------------------------------------------------------- (b) corsa finita
B=$(C apri giro-prova --avviato-da attivita-claude --sessione abc 2>/dev/null)
SB=$(F "$B")
uguale "(b) avviato_da" "attivita-claude" "$(J "$SB" 'c["avviato_da"]')"
uguale "(b) sessione" "abc" "$(J "$SB" 'c["sessione"]')"
uguale "(b) persa_dopo_minuti 20" "20" "$(J "$SB" 'c["persa_dopo_minuti"]')"
C passo "$B" leggi inizio >/dev/null 2>&1
C passo "$B" leggi fatto --esito "ok" >/dev/null 2>&1
C passo "$B" scrivi inizio >/dev/null 2>&1
uguale "(b) chiudi con un passo in-corso e' rifiutata (1)" "1" "$(rc C chiudi "$B" finita)"
uguale "(b) dopo il rifiuto la corsa e' ancora in-corso" "in-corso" "$(J "$SB" 'c["stato"]')"
C passo "$B" scrivi fatto --esito "una bozza" >/dev/null 2>&1
C passo "$B" consegna inizio >/dev/null 2>&1
C passo "$B" consegna fatto --esito "aspetta la tua lettura" >/dev/null 2>&1
uguale "(b) chiudi finita" "0" "$(rc C chiudi "$B" finita)"
uguale "(b) stato finita" "finita" "$(C stato "$B" | tail -n 1)"
uguale "(b) tre passi fatti" "fatto fatto fatto" "$(J "$SB" '" ".join(p["stato"] for p in c["passi"])')"
controllo "(b) fine valorizzata" python3 -c 'import json,sys;assert json.load(open(sys.argv[1]))["fine"]' "$SB"

B2=$(C apri giro-prova 2>/dev/null)
C passo "$B2" leggi inizio >/dev/null 2>&1
C passo "$B2" leggi fatto >/dev/null 2>&1
uguale "(b) chiudi finita con passi da-fare" "0" "$(rc C chiudi "$B2" finita)"
uguale "(b) i da-fare diventano saltato" "fatto saltato saltato" "$(J "$(F "$B2")" '" ".join(p["stato"] for p in c["passi"])')"

B3=$(C apri giro-prova 2>/dev/null)
C passo "$B3" leggi inizio >/dev/null 2>&1
C passo "$B3" leggi fallito --nota "manca il file" >/dev/null 2>&1
C passo "$B3" scrivi inizio >/dev/null 2>&1
uguale "(b) chiudi fallita con un passo in-corso" "0" "$(rc C chiudi "$B3" fallita)"
uguale "(b) stato fallita" "fallita" "$(C stato "$B3" | tail -n 1)"
uguale "(b) in-corso diventa fallito, da-fare saltato, nota tenuta" "fallito fallito saltato manca il file" \
  "$(J "$(F "$B3")" '" ".join(p["stato"] for p in c["passi"])+" "+c["passi"][0]["nota"]')"
uguale "(b) passo inesistente esce 1" "1" "$(rc C passo "$(C apri giro-prova 2>/dev/null)" non-c-e inizio)"
uguale "(b) corsa inesistente esce 2" "2" "$(rc C passo giro-prova-20200101-000000 leggi inizio)"
uguale "(b) azione sbagliata esce 1" "1" "$(rc C passo "$B" leggi boh)"
uguale "(b) chiudi con parola sbagliata esce 1" "1" "$(rc C chiudi "$B" boh)"

# ---------------------------------------------------------------- (c) il JSON ha tutti i campi
cat > "$D/controlla-json.py" <<'PY'
import json, re, sys
ORA = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
CAMPI = ["formato", "id", "grafo", "versione", "stato", "avviato_da", "inizio", "ultimo_segno",
         "persa_dopo_minuti", "fine", "sessione", "stop", "passi"]
CAMPI_PASSO = ["id", "stato", "inizio", "fine", "esito", "nota"]
for percorso in sys.argv[1:]:
    c = json.load(open(percorso))
    assert list(c.keys()) == CAMPI, ("campi", list(c.keys()))
    assert c["formato"] == 1
    assert percorso.endswith("/" + c["id"] + ".json")
    assert isinstance(c["versione"], int) and not isinstance(c["versione"], bool)
    assert c["stato"] in ("in-corso", "finita", "fallita", "fermata")
    assert c["avviato_da"] in ("conversazione", "attivita-claude", "automazione-codex", "utente")
    assert ORA.match(c["inizio"]) and ORA.match(c["ultimo_segno"])
    assert isinstance(c["persa_dopo_minuti"], int)
    assert (c["fine"] is None) == (c["stato"] == "in-corso")
    assert c["fine"] is None or ORA.match(c["fine"])
    assert c["sessione"] is None or isinstance(c["sessione"], str)
    if c["stop"] is not None:
        assert list(c["stop"].keys()) == ["chi", "quando", "perche"] and ORA.match(c["stop"]["quando"])
    assert c["stato"] != "fermata" or c["stop"] is not None
    assert isinstance(c["passi"], list) and c["passi"]
    for p in c["passi"]:
        assert list(p.keys()) == CAMPI_PASSO, ("campi passo", list(p.keys()))
        assert p["stato"] in ("da-fare", "in-corso", "fatto", "fallito", "fermato", "saltato")
        for k in ("inizio", "fine"):
            assert p[k] is None or ORA.match(p[k]), (k, p[k])
        for k in ("esito", "nota"):
            assert p[k] is None or isinstance(p[k], str)
        assert (p["stato"] == "da-fare") == (p["inizio"] is None and p["fine"] is None) or p["stato"] == "saltato"
PY
controllo "(c) JSON valido con tutti i campi e i valori ammessi (corse A, B, B2, B3)" \
  python3 "$D/controlla-json.py" "$(F "$A")" "$SB" "$(F "$B2")" "$(F "$B3")"

# ---------------------------------------------------------------- (d) parallelo
FALLITI_D=0
for i in $(seq 1 20); do
  X=$(C apri giro-prova 2>/dev/null)
  C passo "$X" leggi inizio >/dev/null 2>&1 &
  C passo "$X" scrivi inizio --nota "n$i" >/dev/null 2>&1 &
  wait
  r=$(J "$(F "$X")" '" ".join(p["stato"] for p in c["passi"])+"|"+str(c["passi"][1]["nota"])')
  [ "$r" = "in-corso in-corso da-fare|n$i" ] || { FALLITI_D=$((FALLITI_D + 1)); echo "      corsa $X: $r"; }
done
uguale "(d) 20 coppie di passi in parallelo (corse diverse): nessuna scrittura persa" "0" "$FALLITI_D"

X=$(C apri giro-prova 2>/dev/null)
C passo "$X" leggi fatto --esito "uno" >/dev/null 2>&1 &
C passo "$X" scrivi fatto --esito "due" >/dev/null 2>&1 &
C battito "$X" >/dev/null 2>&1 &
wait
uguale "(d) due passo e un battito in parallelo sulla stessa corsa" "fatto fatto|uno|due" \
  "$(J "$(F "$X")" '" ".join(p["stato"] for p in c["passi"][:2])+"|"+c["passi"][0]["esito"]+"|"+c["passi"][1]["esito"]')"

# cinque apri insieme: id tutti diversi e file tutti presenti
PRIMA=$(ls "$D/grafi/corse" | grep -c '\.json$')
for i in 1 2 3 4 5; do (C apri giro-prova >"$D/apri-par-$i.out" 2>/dev/null) & done
wait
uguale "(d) cinque apri insieme: cinque id diversi" "5" "$(cat "$D"/apri-par-*.out | sort -u | grep -c .)"
uguale "(d) cinque apri insieme: cinque file in piu'" "$((PRIMA + 5))" "$(ls "$D/grafi/corse" | grep -c '\.json$')"
controllo "(d) i file delle cinque corse sono JSON validi" python3 "$D/controlla-json.py" $(for f in "$D"/apri-par-*.out; do F "$(cat "$f")"; done)

# ---------------------------------------------------------------- (e) persa
E=$(C apri giro-prova 2>/dev/null)
C passo "$E" leggi inizio >/dev/null 2>&1
uguale "(e) appena aperta: in corso" "in corso" "$(C stato "$E" | tail -n 1)"
python3 - "$(F "$E")" <<'PY'
import datetime, json, sys
p = sys.argv[1]
c = json.load(open(p))
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)
c["ultimo_segno"] = t.strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(c, open(p, "w"), indent=2)
PY
uguale "(e) 30 minuti senza segni: stato dice persa" "persa" "$(C stato "$E" | tail -n 1)"
uguale "(e) il file dice ancora in-corso (persa non e' uno stato)" "in-corso" "$(J "$(F "$E")" 'c["stato"]')"
controllo "(e) elenco la mostra persa" bash -c "cd '$D' && python3 '$CORSA' elenco | grep -F '$E' | grep -q 'persa'"
uguale "(e) battito esce 0" "0" "$(rc C battito "$E")"
uguale "(e) dopo il battito: in corso" "in corso" "$(C stato "$E" | tail -n 1)"
controllo "(e) elenco la mostra di nuovo in corso" bash -c "cd '$D' && python3 '$CORSA' elenco | grep -F '$E' | grep -q 'in corso'"
# persa-dopo personalizzato: 30 minuti fa ma soglia 60 = non persa
E2=$(C apri giro-prova --persa-dopo 60 2>/dev/null)
python3 - "$(F "$E2")" <<'PY'
import datetime, json, sys
p = sys.argv[1]
c = json.load(open(p))
c["ultimo_segno"] = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
json.dump(c, open(p, "w"), indent=2)
PY
uguale "(e) --persa-dopo 60 e 30 minuti: in corso" "60 in corso" "$(J "$(F "$E2")" 'c["persa_dopo_minuti"]') $(C stato "$E2" | tail -n 1)"
uguale "(e) una corsa persa accetta ancora un passo (e torna viva)" "0 in corso" "$(rc C passo "$E" scrivi inizio) $(C stato "$E" | tail -n 1)"
controllo "(e) e_persa importabile" python3 -c '
import importlib.util, datetime, sys
s = importlib.util.spec_from_file_location("corsa", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
c = {"stato": "in-corso", "ultimo_segno": "2026-11-07T10:00:00Z", "persa_dopo_minuti": 20}
u = datetime.datetime(2026, 11, 7, 10, 0, 0, tzinfo=datetime.timezone.utc)
assert not m.e_persa(c, u + datetime.timedelta(minutes=20))
assert m.e_persa(c, u + datetime.timedelta(minutes=21))
assert not m.e_persa(dict(c, stato="finita"), u + datetime.timedelta(days=1))
' "$CORSA"
controllo "(e) trova_cartella e leggi_corsa importabili" python3 -c '
import importlib.util, sys
s = importlib.util.spec_from_file_location("corsa", sys.argv[1]); m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
assert m.trova_cartella(sys.argv[2] + "/sotto/cartella/profonda") == sys.argv[2]
assert m.leggi_corsa(sys.argv[3])["id"]
' "$CORSA" "$D" "$(F "$E")"

# ---------------------------------------------------------------- (f) grafo rotto o inesistente
PRIMA=$(ls -A "$D/grafi/corse" | sort | md5sum)
uguale "(f) apri su grafo rotto esce 1" "1" "$(rc C apri rotto)"
uguale "(f) apri su grafo inesistente esce 2" "2" "$(rc C apri non-esiste)"
uguale "(f) apri con nome non valido esce 1" "1" "$(rc C apri ../x)"
uguale "(f) apri senza grafo esce 1" "1" "$(rc C apri)"
uguale "(f) apri su grafo rotto stampa errori" "si" "$(C apri rotto 2>&1 >/dev/null | grep -q 'rotto.yaml' && echo si || echo no)"
uguale "(f) nessun file creato dai rifiuti" "$PRIMA" "$(ls -A "$D/grafi/corse" | sort | md5sum)"

# ---------------------------------------------------------------- (h) la cartella dello studio
uguale "(h) da una sottocartella risale e trova lo studio" "0" "$(cd "$D/sotto/cartella/profonda" && rc python3 "$CORSA" elenco)"
uguale "(h) fuori da uno studio esce 2" "2" "$(cd "$FUORI" && rc python3 "$CORSA" elenco)"
uguale "(h) con --cartella da fuori" "0" "$(cd "$FUORI" && rc python3 "$CORSA" elenco --cartella "$D")"
uguale "(h) con REDACY_CARTELLA da fuori" "0" "$(cd "$FUORI" && REDACY_CARTELLA="$D" rc python3 "$CORSA" elenco)"
uguale "(h) --cartella sbagliata esce 2" "2" "$(cd "$D" && rc python3 "$CORSA" elenco --cartella "$FUORI")"
controllo "(h) elenco: piu' recenti prima e una riga per corsa" python3 - "$D" "$CORSA" <<'PY'
import subprocess, sys
d, corsa = sys.argv[1:3]
out = subprocess.run([sys.executable, corsa, "elenco"], cwd=d, capture_output=True, text=True).stdout.strip().splitlines()
import os
n = len([f for f in os.listdir(d + "/grafi/corse") if f.endswith(".json") and not f.startswith(".")])
assert len(out) == n, (len(out), n)
inizi = [l.split("\t")[2] for l in out]
assert inizi == sorted(inizi, reverse=True)
PY
controllo "(h) --help in italiano, per il programma e per ogni comando" bash -c "
  python3 '$CORSA' --help | grep -q 'Uso:' &&
  for c in apri passo battito chiudi ferma stato elenco; do python3 '$CORSA' \$c --help | grep -q 'Uso:' || exit 1; done"

# ---------------------------------------------------------------- (i) fixture buone, se ci sono
BUONI="$QUI/buoni"
if ls "$BUONI"/*.yaml >/dev/null 2>&1; then
  for f in "$BUONI"/*.yaml; do
    n=$(basename "$f" .yaml)
    cp "$f" "$D/grafi/$n.yaml"
    uguale "(i) apri sul grafo buono $n" "0" "$(rc C apri "$n")"
  done
fi

# ---------------------------------------------------------------- (g) niente file in giro
RESTI=$(find "$D/grafi/corse" -type f ! -name '*.json' ! -name '.*.lock' | wc -l | tr -d ' ')
uguale "(g) nessun file temporaneo o estraneo in grafi/corse" "0" "$RESTI"
uguale "(g) i soli file nascosti sono lucchetti" "0" "$(find "$D/grafi/corse" -type f -name '.*' ! -name '.*.lock' | wc -l | tr -d ' ')"
uguale "(g) nessun .tmp in tutto lo studio" "0" "$(find "$D" -name '*.tmp' | wc -l | tr -d ' ')"

# ---------------------------------------------------------------- esito
if [ "${#ERRORI[@]}" -eq 0 ]; then
  [ "$TIENI" -eq 1 ] || rm -rf "$D" "$FUORI"
  echo "PASSA"
  exit 0
else
  echo "(cartelle di prova lasciate: $D e $FUORI)"
  echo "FALLISCE ${ERRORI[0]}$([ "${#ERRORI[@]}" -gt 1 ] && echo " (e altri $(( ${#ERRORI[@]} - 1 )))")"
  exit 1
fi
