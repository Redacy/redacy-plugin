#!/usr/bin/env bash
# redacy 0.3.0 · prove/periodo/prova-schemi.sh
# Il controllo accetta i file buoni e i vuoti, rifiuta un todo.json e un idee.json rotti col messaggio giusto.
# Cartelle di prova: $PROVE (default /home/ubuntu/lab/redacy-plugin-prove/C/schemi). Nessun dato vero.
set -u
QUI="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$(cd "$QUI/../.." && pwd)"
S="$PLUGIN/skills/pianifica-periodo"
C="$S/scripts/controlla-periodo.py"
P="${PROVE:-/home/ubuntu/lab/redacy-plugin-prove/C}/schemi"
rm -rf "$P"; mkdir -p "$P/buoni/periodo" "$P/vuoti/periodo" "$P/rotti/periodo"
fallisce() { echo "FALLISCE $1"; exit 1; }

# vuoti (quelli che copia inizia)
cp "$S/examples/todo.vuoto.json" "$P/vuoti/periodo/todo.json"
cp "$S/examples/idee.vuoto.json" "$P/vuoti/periodo/idee.json"
python3 "$C" "$P/vuoti/periodo/todo.json" "$P/vuoti/periodo/idee.json" >/dev/null || fallisce "i file vuoti non passano"

# buoni
cat > "$P/buoni/periodo/todo.json" <<'J'
{"versione":"0.3.0","periodo":"2026-11","todo":[
 {"id":"t1","cosa":"Riordinare le fatture di ottobre","chi":"agente","stato":"in corso","scadenza":"2026-11-14","dove":"workspace/contabilita","da":"piano","aggiornato":"2026-11-07"},
 {"id":"t2","cosa":"Firmare il preventivo per Rossi","chi":"tu","stato":"ferma","scadenza":"","dove":"fonti/preventivo-rossi.pdf","da":"utente","aggiornato":"2026-11-07","nota":"aspetta la risposta di Rossi"},
 {"id":"t3","cosa":"Chiamare il commercialista","chi":"Marta","stato":"da fare","scadenza":"2026-11-20","dove":"","da":"giro","aggiornato":"2026-11-07"}]}
J
cat > "$P/buoni/periodo/idee.json" <<'J'
{"versione":"0.3.0","periodo":"2026-11","idee":[
 {"id":"i1","idea":"Promemoria ai clienti prima delle scadenze","da_dove":"conversazione","arrivata":"2026-11-07"},
 {"id":"i2","idea":"Cartella condivisa per le ricevute","da_dove":"utente","arrivata":"2026-11-07","esito":{"stato":"portata nel periodo","data":"2026-11-08","perche":"serve alle fatture","todo":"t1"}},
 {"id":"i3","idea":"Newsletter mensile","da_dove":"fonti/appunti.md","arrivata":"2026-11-07","esito":{"stato":"scartata","data":"2026-11-08","perche":"non ora"}}]}
J
python3 "$C" "$P/buoni/periodo/todo.json" "$P/buoni/periodo/idee.json" >/dev/null || fallisce "i file buoni non passano"

# rotti: ogni caso = file, modifica, parola che il messaggio deve contenere
prova_rotto() { # nome file_base sostituzione_python messaggio_atteso
  local nome="$1" base="$2" py="$3" atteso="$4"
  local nomefile; nomefile="$(basename "$base")"
  mkdir -p "$P/rotti/$nome/periodo"
  python3 - "$base" "$P/rotti/$nome/periodo/$nomefile" "$py" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); exec(sys.argv[3])
open(sys.argv[2], "w").write(json.dumps(d, ensure_ascii=False) if not d == "RAW" else "{ non json")
PY
  local uscita rc
  uscita="$(python3 "$C" "$P/rotti/$nome/periodo/$nomefile" 2>&1)"; rc=$?
  [ "$rc" = 1 ] || fallisce "$nome: attesa uscita 1, trovata $rc"
  echo "$uscita" | grep -qF "$atteso" || fallisce "$nome: manca «$atteso» nel messaggio: $uscita"
}
T="$P/buoni/periodo/todo.json"; I="$P/buoni/periodo/idee.json"
prova_rotto stato-strano "$T" 'd["todo"][0]["stato"]="boh"' "non è fra i valori ammessi"
prova_rotto manca-cosa "$T" 'del d["todo"][1]["cosa"]' "manca il campo «cosa»"
prova_rotto id-doppio "$T" 'd["todo"][1]["id"]="t1"' "gli id sono unici"
prova_rotto data-finta "$T" 'd["todo"][0]["scadenza"]="2026-02-30"' "non è una data che esiste"
prova_rotto data-storta "$T" 'd["todo"][0]["aggiornato"]="7/11/2026"' "non ha la forma giusta"
prova_rotto campo-extra "$T" 'd["todo"][0]["prio"]="alta"' "non previsto"
prova_rotto versione "$T" 'd["versione"]="0.2"' "deve valere"
prova_rotto non-elenco "$T" 'd["todo"]="niente"' "dovrebbe essere elenco"
prova_rotto da-strano "$T" 'd["todo"][2]["da"]="regia"' "non è fra i valori ammessi"
prova_rotto idea-vuota "$I" 'd["idee"][0]["idea"]=""' "non può essere vuoto"
prova_rotto esito-senza-perche "$I" 'del d["idee"][2]["esito"]["perche"]' "manca il campo «perche»"
prova_rotto esito-strano "$I" 'd["idee"][2]["esito"]["stato"]="forse"' "non è fra i valori ammessi"
prova_rotto id-idea-storto "$I" 'd["idee"][0]["id"]="x1"' "non ha la forma giusta"
# l'idea punta a un todo che non c'è: serve il todo.json accanto
mkdir -p "$P/rotti/todo-inesistente/periodo"; cp "$T" "$P/rotti/todo-inesistente/periodo/todo.json"
python3 - "$I" "$P/rotti/todo-inesistente/periodo/idee.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["idee"][1]["esito"]["todo"] = "t9"
open(sys.argv[2], "w").write(json.dumps(d, ensure_ascii=False))
PY
out="$(python3 "$C" "$P/rotti/todo-inesistente/periodo/idee.json" 2>&1)"; rc=$?
[ "$rc" = 1 ] && echo "$out" | grep -qF "non c'è in todo.json" || fallisce "todo-inesistente: rc=$rc $out"

# JSON rotto
mkdir -p "$P/rotti/json-rotto/periodo"; printf '{ "versione": "0.3.0", "todo": [ {' > "$P/rotti/json-rotto/periodo/todo.json"
out="$(python3 "$C" "$P/rotti/json-rotto/periodo/todo.json" 2>&1)"; rc=$?
[ "$rc" = 1 ] && echo "$out" | grep -qF "non è un JSON valido" || fallisce "json-rotto: $out"

# l'hook: silenzioso su ciò che non lo riguarda, parla su un file rotto
ev() { python3 -c "import json,sys;print(json.dumps({'cwd':sys.argv[1],'tool_name':'Write','tool_input':{'file_path':sys.argv[2]}}))" "$1" "$2"; }
out="$(ev "$P/buoni" "$P/buoni/periodo/todo.json" | python3 "$C" 2>&1)"; rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] || fallisce "hook su file buono: rc=$rc out=$out"
out="$(ev "$P/buoni" "$P/buoni/altro.md" | python3 "$C" 2>&1)"; rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] || fallisce "hook su altro file: rc=$rc out=$out"
out="$(ev "$P/rotti/id-doppio" "periodo/todo.json" | python3 "$C" 2>/dev/null)"; rc=$?
[ "$rc" = 2 ] && echo "$out" | grep -qF "gli id sono unici" || fallisce "hook su file rotto: rc=$rc out=$out"
out="$(echo 'non json' | python3 "$C" 2>&1)"; rc=$?
[ "$rc" = 0 ] && [ -z "$out" ] || fallisce "hook su stdin non JSON: rc=$rc"

echo PASSA
