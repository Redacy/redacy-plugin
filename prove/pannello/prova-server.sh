#!/usr/bin/env bash
# prova-server.sh · redacy 0.3.1
# Prova il server del pannello su una cartella dello studio fatta da `inizia` (crea-cartella.py),
# con dati finti e una corsa per stato scritta da corsa.py:
#  - il server parte, la pagina e tutte le viste rispondono 200 e dicono cose giuste;
#  - la vista file dà il testo dei soli percorsi fissi (mai fonti/) e la sua firma cambia con i file;
#  - un secondo avvio riusa il primo (stesso pid, stessa porta, un solo processo);
#  - una richiesta con Host sbagliato, con Origin estraneo, senza gettone, con gettone sbagliato,
#    o senza Content-Type JSON è rifiutata;
#  - il POST di stop giusto ferma una corsa in corso, e una corsa già fermata o finita risponde 409;
#  - --spegni lo spegne e toglie pannello.json.
# Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/pannello/prova-server.sh
# Le cartelle di prova vanno in $REDACY_PROVE (default /home/ubuntu/lab/redacy-plugin-prove/D).
set -u

RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
PANNELLO="$RADICE/skills/pannello/scripts/pannello.py"
PREPARA="$RADICE/prove/pannello/_prepara.py"
BASE="${REDACY_PROVE:-/home/ubuntu/lab/redacy-plugin-prove/D}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
D="$BASE/server-$ORA/studio"
mkdir -p "$BASE/server-$ORA"

fallisce() { echo "FALLISCE $*"; python3 "$PANNELLO" --cartella "$D" --spegni >/dev/null 2>&1; exit 1; }
command -v python3 >/dev/null || { echo "FALLISCE manca python3"; exit 1; }
command -v curl >/dev/null || { echo "FALLISCE manca curl"; exit 1; }
[ -f "$PANNELLO" ] || { echo "FALLISCE manca $PANNELLO"; exit 1; }

# 1. La cartella finta, con una corsa per stato
python3 "$PREPARA" "$D" --corse > "$BASE/server-$ORA/ids.txt" 2> "$BASE/server-$ORA/prepara.err" \
  || fallisce "_prepara.py non riesce: $(cat "$BASE/server-$ORA/prepara.err")"
id_di() { sed -n "s/^$1=//p" "$BASE/server-$ORA/ids.txt"; }
IN_CORSO="$(id_di in-corso)"; PERSA="$(id_di persa)"; FINITA="$(id_di finita)"; FERMATA="$(id_di fermata)"
[ -n "$IN_CORSO" ] && [ -n "$PERSA" ] && [ -n "$FINITA" ] && [ -n "$FERMATA" ] || fallisce "mancano gli id delle corse di prova"

# 2. Accende il pannello
USCITA="$(python3 "$PANNELLO" --cartella "$D" 2>&1)" || fallisce "pannello.py non parte: $USCITA"
PORTA="$(echo "$USCITA" | sed -n 's#.*http://127.0.0.1:\([0-9]*\)/.*#\1#p')"
[ -n "$PORTA" ] || fallisce "non trovo la porta nell'uscita: $USCITA"
echo "$USCITA" | grep -q "acceso" || fallisce "l'uscita non dice che è acceso: $USCITA"
INFO="$D/interfaccia/pannello.json"
[ -f "$INFO" ] || fallisce "manca interfaccia/pannello.json"
python3 - "$INFO" "$D" "$PORTA" <<'EOF' || fallisce "pannello.json non ha porta, pid, ora, cartella e gettone giusti"
import json, os, sys
d = json.load(open(sys.argv[1]))
assert d["porta"] == int(sys.argv[3]), d
assert isinstance(d["pid"], int) and d["pid"] > 1
assert d["cartella"] == os.path.realpath(sys.argv[2])
assert len(d["gettone"]) >= 32 and d["ora"].endswith("Z")
assert oct(os.stat(sys.argv[1]).st_mode & 0o777) == "0o600", oct(os.stat(sys.argv[1]).st_mode)
EOF
GETTONE="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['gettone'])" "$INFO")"
PID1="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pid'])" "$INFO")"
URL="http://127.0.0.1:$PORTA"

# 3. La pagina e tutte le viste rispondono 200
codice() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }
[ "$(codice "$URL/")" = "200" ] || fallisce "la pagina / non risponde 200"
curl -s "$URL/" | grep -q "$GETTONE" || fallisce "la pagina non porta il gettone"
for v in ciao stato periodo recenti grafi corse file-chiave memoria supporto file file-firma su-misura; do
  [ "$(codice "$URL/api/$v")" = "200" ] || fallisce "/api/$v non risponde 200"
  curl -s "$URL/api/$v" | python3 -c "import json,sys;json.load(sys.stdin)" 2>/dev/null || fallisce "/api/$v non è JSON"
done
[ "$(codice "$URL/api/inesistente")" = "404" ] || fallisce "una vista inesistente non dà 404"

# 4. Cosa dicono le viste
curl -s "$URL/api/stato" > "$BASE/server-$ORA/stato.json"
python3 - "$BASE/server-$ORA/stato.json" "$IN_CORSO" "$PERSA" "$FINITA" "$FERMATA" <<'EOF' || fallisce "una vista dice cose sbagliate (vedi sopra)"
import json, sys
s = json.load(open(sys.argv[1]))
vivo, persa, finita, fermata = sys.argv[2:6]
assert s["cartella"]["nome"] == "Studio Ferrante" or s["cartella"]["nome"], s["cartella"]
assert s["cartella"]["versione"].startswith("redacy "), s["cartella"]
assert s["periodo"]["obiettivo"].startswith("Chiudere le dichiarazioni"), s["periodo"]["obiettivo"]
assert len(s["periodo"]["todo"]["todo"]) == 4
assert s["conta"]["per_te"] == 2, s["conta"]
ritardo = {a["id"]: a["in_ritardo"] for a in s["periodo"]["aspettano_te"]}
assert ritardo == {"t1": True, "t2": False}, ritardo
assert len(s["log"]) == 4, s["log"]
assert s["log"][0].startswith("- 2026-11-06 12:40"), s["log"]   # l'ultima riga scritta in fondo al file è la prima
assert " · inizia · " in s["log"][3], s["log"]                   # la prima del file è l'ultima
assert s["log_righe"][0]["tipo"] == "impara" and s["log_righe"][0]["quando"] == "2026-11-06 12:40"
ids_in_corso = sorted(c["id"] for c in s["corse_in_corso"])
assert vivo in ids_in_corso and persa in ids_in_corso, ids_in_corso
per_id = {c["id"]: c for c in s["corse"]}
assert per_id[vivo]["stato_effettivo"] == "in-corso" and not per_id[vivo]["persa"]
assert per_id[persa]["stato_effettivo"] == "persa" and per_id[persa]["persa"]
assert per_id[finita]["stato_effettivo"] == "finita"
assert per_id[fermata]["stato_effettivo"] == "fermata" and per_id[fermata]["stop"]["chi"] == "pannello"
assert finita not in ids_in_corso and fermata not in ids_in_corso
assert [c["id"] for c in s["corse_ultime"]][:1] and all(c["id"] not in ids_in_corso for c in s["corse_ultime"])
g = {x["grafo"]: x for x in s["grafi"]}["giro-scadenze"]
assert len(g["passi"]) == 4 and ["leggi-foglio", "trova-scadenze"] in g["archi"], g["archi"]
assert g["acceso"] is False and g["innesco"]["tipo"] == "orario"
assert [w["nome"] for w in s["workspace"]] == ["dichiarazioni", "scadenze"]
assert s["workspace"][0]["titolo"] == "Dichiarazioni" and s["workspace"][0]["serve"].startswith("Prepara la pratica")
assert s["workspace"][0]["pagine_memoria"] == 2
assert {f["file"] for f in s["file_chiave"]["grafi"]} == {"grafi/giro-scadenze.yaml"}
assert any(f["nome"] == "pratiche" and f["cartella"] for f in s["file_chiave"]["fonti"])
m = s["memoria_grafo"]
assert m["conteggi"]["pagine"] == 9 and m["conteggi"]["mancanti"] == 2 and m["conteggi"]["collegamenti"] == 10, m["conteggi"]
mancanti = sorted(n["id"] for n in m["nodi"] if n["mancante"])
assert mancanti == ["modello-730", "scadenze-fiscali"], mancanti
assert not any(n["id"] == "non-contare-questo" for n in m["nodi"]), "un collegamento dentro il codice è stato contato"
assert not any(n["id"] == "LOG" for n in m["nodi"]), "LOG.md non è una pagina"
chiavi = {n["chiave"] for n in m["nodi"]}
assert "dichiarazioni/procedura-dichiarazioni" in chiavi and "studio/procedura-dichiarazioni" in chiavi
assert all(a["da"] in chiavi and a["a"] in chiavi for a in m["archi"])
assert "Cosa mi serve:" in s["supporto"]["testo"] and s["supporto"]["url"] == "https://redacy.com"
assert "Manca la colonna delle scadenze" in s["supporto"]["testo"]
EOF

# 4b. Il testo dei file per la pagina: solo percorsi fissi, mai fonti/ né le cartelle nascoste; la firma segue i file
curl -s "$URL/api/file" > "$BASE/server-$ORA/file.json"
FIRMA1="$(curl -s "$URL/api/file-firma" | python3 -c "import json,sys;print(json.load(sys.stdin)['firma'])")"
python3 - "$BASE/server-$ORA/file.json" "$FIRMA1" <<'EOF' || fallisce "la vista file dice cose sbagliate (vedi sopra)"
import json, sys
d = json.load(open(sys.argv[1]))
f = d["file"]
assert d["firma"] == sys.argv[2] and d["troncato"] is False, (d["firma"], sys.argv[2], d["troncato"])
for k in ("AGENTS.md", "periodo/obiettivo.md", "periodo/todo.json", "grafi/giro-scadenze.yaml", "workspace/dichiarazioni/AGENTS.md"):
    assert k in f, (k, sorted(f))
assert any(k.startswith("workspace/dichiarazioni/memoria/") for k in f), sorted(f)
assert any(k.startswith("grafi/corse/") and k.endswith(".json") for k in f), sorted(f)
assert not any(k.startswith(("fonti/", ".", "interfaccia/")) or "/." in k or k.endswith("CLAUDE.md") for k in f), sorted(f)
assert "Chiudere le dichiarazioni" in f["periodo/obiettivo.md"], f["periodo/obiettivo.md"][:200]
EOF
[ -f "$D/memoria/INDICE.md" ] || fallisce "manca memoria/INDICE.md nella cartella di prova"
printf '\n' >> "$D/memoria/INDICE.md"
FIRMA2="$(curl -s "$URL/api/file-firma" | python3 -c "import json,sys;print(json.load(sys.stdin)['firma'])")"
[ -n "$FIRMA1" ] && [ "$FIRMA1" != "$FIRMA2" ] || fallisce "la firma dei file non cambia quando cambia un file ($FIRMA1 -> $FIRMA2)"

# 4c. Le scelte su misura: senza file niente, col file solo le chiavi note e valide
[ "$(curl -s "$URL/api/su-misura")" = "{}" ] || fallisce "senza interfaccia/su-misura.json la vista su-misura non è vuota"
cat > "$D/interfaccia/su-misura.json" <<'EOF'
{"sfondo": "tinta", "primo": "processi", "ordine": ["memoria", "oggi", "boh", "oggi"], "frase": false,
 "accento": {"chiaro": "#0a7d5a", "scuro": "rosso"}, "titolo": "  Studio Prova  ", "script": "<script>"}
EOF
curl -s "$URL/api/su-misura" | python3 -c "
import json, sys
m = json.load(sys.stdin)
atteso = {'sfondo': 'tinta', 'primo': 'processi', 'ordine': ['memoria', 'oggi', 'processi', 'periodo', 'aree'], 'frase': False,
          'accento': {'chiaro': '#0a7d5a'}, 'titolo': 'Studio Prova'}
assert m == atteso, m
" || fallisce "la vista su-misura non tiene solo le chiavi valide"
printf 'non è json' > "$D/interfaccia/su-misura.json"
[ "$(curl -s "$URL/api/su-misura")" = "{}" ] || fallisce "un su-misura.json rotto non dà {}"
rm -f "$D/interfaccia/su-misura.json"

# 5. Un secondo avvio riusa il primo
USCITA2="$(python3 "$PANNELLO" --cartella "$D" 2>&1)" || fallisce "il secondo avvio esce con errore: $USCITA2"
echo "$USCITA2" | grep -q "già acceso" || fallisce "il secondo avvio non dice «già acceso»: $USCITA2"
echo "$USCITA2" | grep -q ":$PORTA/" || fallisce "il secondo avvio dà un'altra porta: $USCITA2"
PID2="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pid'])" "$INFO")"
[ "$PID1" = "$PID2" ] || fallisce "il pid è cambiato ($PID1 -> $PID2): ha aperto un altro pannello"
# due avvii insieme: un solo pannello
python3 "$PANNELLO" --cartella "$D" >/dev/null 2>&1 &
python3 "$PANNELLO" --cartella "$D" >/dev/null 2>&1 &
wait
PID3="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pid'])" "$INFO")"
[ "$PID1" = "$PID3" ] || fallisce "due avvii insieme hanno cambiato il pid ($PID1 -> $PID3)"
N="$(pgrep -f -- "pannello.py --cartella $D" | wc -l)"
[ "$N" -le 1 ] || fallisce "ci sono $N processi del pannello per la stessa cartella"
# un'altra cartella ha il suo pannello
D2="$BASE/server-$ORA/altro"
python3 "$PREPARA" "$D2" >/dev/null 2>&1 || fallisce "_prepara.py non riesce sulla seconda cartella"
USCITA4="$(python3 "$PANNELLO" --cartella "$D2" 2>&1)" || fallisce "la seconda cartella non parte: $USCITA4"
echo "$USCITA4" | grep -q ":$PORTA/" && fallisce "due cartelle diverse hanno la stessa porta"
python3 "$PANNELLO" --cartella "$D2" --spegni >/dev/null 2>&1

# 6. Richieste rifiutate
[ "$(codice -H 'Host: evil.example.com' "$URL/api/stato")" = "403" ] || fallisce "Host sbagliato non rifiutato (GET)"
[ "$(codice -H 'Host: evil.example.com:'$PORTA "$URL/")" = "403" ] || fallisce "Host sbagliato non rifiutato (pagina)"
[ "$(codice -H 'Origin: http://evil.example.com' "$URL/api/stato")" = "403" ] || fallisce "Origin estraneo non rifiutato (GET)"
POST() { # POST <id> [intestazioni...]
  local id="$1"; shift
  curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$URL/api/ferma" -d "{\"id\":\"$id\"}" "$@"
}
OK_ORIGIN="Origin: $URL"; OK_JSON="Content-Type: application/json"
[ "$(POST "$IN_CORSO" -H "$OK_ORIGIN" -H "$OK_JSON")" = "403" ] || fallisce "POST senza gettone non rifiutato"
[ "$(POST "$IN_CORSO" -H "$OK_ORIGIN" -H "$OK_JSON" -H 'X-Gettone: sbagliato')" = "403" ] || fallisce "POST col gettone sbagliato non rifiutato"
[ "$(POST "$IN_CORSO" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "403" ] || fallisce "POST senza Origin non rifiutato"
[ "$(POST "$IN_CORSO" -H 'Origin: http://evil.example.com' -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "403" ] || fallisce "POST con Origin estraneo non rifiutato"
[ "$(POST "$IN_CORSO" -H "$OK_ORIGIN" -H 'Content-Type: text/plain' -H "X-Gettone: $GETTONE")" = "415" ] || fallisce "POST senza Content-Type JSON non rifiutato"
[ "$(POST "$IN_CORSO" -H 'Host: evil.example.com' -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "403" ] || fallisce "POST con Host sbagliato non rifiutato"
[ "$(codice -X OPTIONS -H "$OK_ORIGIN" "$URL/api/ferma")" = "405" ] || fallisce "OPTIONS (preflight) non rifiutato"
[ "$(codice -X DELETE "$URL/api/stato")" = "405" ] || fallisce "DELETE non rifiutato"
python3 - "$D/grafi/corse/$IN_CORSO.json" <<'EOF' || fallisce "una richiesta rifiutata ha comunque toccato la corsa"
import json, sys
c = json.load(open(sys.argv[1]))
assert c["stato"] == "in-corso" and c["stop"] is None, c["stato"]
EOF
[ ! -e "$D/grafi/corse/$IN_CORSO.stop" ] || fallisce "una richiesta rifiutata ha scritto il file .stop"

# 7. Lo stop giusto
[ "$(POST "$IN_CORSO" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "200" ] || fallisce "lo stop giusto non risponde 200"
[ -f "$D/grafi/corse/$IN_CORSO.stop" ] || fallisce "lo stop non ha scritto <id>.stop"
python3 - "$D/grafi/corse/$IN_CORSO.json" <<'EOF' || fallisce "dopo lo stop la corsa non risulta fermata dal pannello"
import json, sys
c = json.load(open(sys.argv[1]))
assert c["stato"] == "fermata", c["stato"]
assert c["stop"]["chi"] == "pannello", c["stop"]
assert any(p["stato"] == "fermato" for p in c["passi"]), c["passi"]
EOF
curl -s "$URL/api/corse" | python3 -c "
import json,sys
d=json.load(sys.stdin)
assert '$IN_CORSO' not in [c['id'] for c in d['in_corso']]
u={c['id']:c for c in d['ultime']}
assert u['$IN_CORSO']['stato_effettivo']=='fermata'
" || fallisce "la vista corse non mostra la corsa fermata"
[ "$(POST "$IN_CORSO" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "409" ] || fallisce "fermare due volte non dà 409"
[ "$(POST "$FINITA" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "409" ] || fallisce "fermare una corsa finita non dà 409"
[ "$(POST "non-esiste-20260101-000000" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "404" ] || fallisce "una corsa che non c'è non dà 404"
[ "$(POST "../../AGENTS" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "400" ] || fallisce "un id con percorso non dà 400"
# la corsa persa si può fermare (è ancora «in corso» nel file)
[ "$(POST "$PERSA" -H "$OK_ORIGIN" -H "$OK_JSON" -H "X-Gettone: $GETTONE")" = "200" ] || fallisce "una corsa persa non si ferma"

# 8. Spegne
python3 "$PANNELLO" --cartella "$D" --spegni > /dev/null 2>&1
sleep 0.5
kill -0 "$PID1" 2>/dev/null && fallisce "dopo --spegni il processo $PID1 è ancora vivo"
[ ! -f "$INFO" ] || fallisce "dopo --spegni pannello.json c'è ancora"
[ "$(codice "$URL/api/ciao")" != "200" ] || fallisce "dopo --spegni la porta risponde ancora"
# riaccende (dopo uno spegnimento pulito) e tiene pannello.json d'accordo con launch.json
python3 "$PANNELLO" --cartella "$D" > /dev/null 2>&1 || fallisce "non riparte dopo --spegni"
python3 - "$D" <<'EOF' || fallisce ".claude/launch.json non è d'accordo con pannello.json"
import json, sys
d = sys.argv[1]
porta = json.load(open(d + "/interfaccia/pannello.json"))["porta"]
voci = [v for v in json.load(open(d + "/.claude/launch.json"))["configurations"] if v["name"] == "pannello redacy"]
assert len(voci) == 1 and voci[0]["port"] == porta and str(porta) in voci[0]["runtimeArgs"], voci
EOF
python3 "$PANNELLO" --cartella "$D" --spegni > /dev/null 2>&1

echo "PASSA"
