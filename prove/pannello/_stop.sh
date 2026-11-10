#!/usr/bin/env bash
# _stop.sh · redacy 0.4.0 · funzioni comuni di prova-stop-claude.sh e prova-stop-codex.sh (si leggono con `source`)
#
# La prova: due conversazioni nella stessa cartella dello studio. La A fa una corsa di cinque passi
# lenti (giro-lento), la B una corsa indipendente (giro-altro). Mentre il passo 2 di A gira, da fuori
# si ferma A con un POST come lo fa la pagina (gettone + Origin + JSON). Poi si controlla che:
#   - la corsa di A risulta «fermata» (stop dal pannello) e i passi dopo il 2 non sono avvenuti;
#   - la B ha finito la sua corsa, e nessuna richiesta di stop o rifiuto l'ha toccata.

PANNELLO="$RADICE/skills/pannello/scripts/pannello.py"
PREPARA="$RADICE/prove/pannello/_prepara.py"

fallisce() { echo "FALLISCE $*"; python3 "$PANNELLO" --cartella "${D:-/nonesiste}" --spegni >/dev/null 2>&1; exit 1; }

grafo_lento() { # $1 = nome del grafo
cat <<EOF
grafo: $1
versione: 1
obiettivo: Cinque passi lenti, per provare lo stop dal pannello.
acceso: false
innesco: {tipo: parola}
passi:
  - id: passo-1
    tipo: agente
    nome: Passo uno
    workspace: orchestratore
    prompt: Fai il passo uno
  - id: passo-2
    tipo: agente
    nome: Passo due
    workspace: orchestratore
    prompt: Fai il passo due
  - id: passo-3
    tipo: agente
    nome: Passo tre
    workspace: orchestratore
    prompt: Fai il passo tre
  - id: passo-4
    tipo: agente
    nome: Passo quattro
    workspace: orchestratore
    prompt: Fai il passo quattro
  - id: passo-5
    tipo: agente
    nome: Passo cinque
    workspace: orchestratore
    prompt: Fai il passo cinque
tetti:
  contemporanee: 2
uscite: []
autonomia: {livello: L0, da: "2026-11-07", si: null}
EOF
}

# prepara_cartella <cartella> <con_hook: si|no>
prepara_cartella() {
  local d="$1" hook="$2"
  python3 "$PREPARA" "$d" > /dev/null 2>"$d.prepara.err" || fallisce "_prepara.py non riesce: $(cat "$d.prepara.err")"
  grafo_lento giro-lento > "$d/grafi/giro-lento.yaml"
  grafo_lento giro-altro > "$d/grafi/giro-altro.yaml"
  python3 "$d/.agents/script/controlla-grafo.py" "$d/grafi/giro-lento.yaml" "$d/grafi/giro-altro.yaml" > "$d.controllo.txt" 2>&1 \
    || fallisce "i grafi di prova non passano controlla-grafo.py: $(cat "$d.controllo.txt")"
  [ -f "$d/.agents/hooks/ferma.py" ] || fallisce "crea-cartella non ha copiato .agents/hooks/ferma.py"
  [ -f "$d/.agents/script/corsa.py" ] || fallisce "crea-cartella non ha copiato .agents/script/corsa.py"
  if [ "$hook" = "no" ]; then rm -f "$d/.agents/hooks/ferma.py"; fi
}

# prompt_conversazione <nome: A|B> <grafo> <variabile con l'id della sessione>
prompt_conversazione() {
  local nome="$1" grafo="$2" var="$3"
  cat <<EOF
Sei la conversazione $nome, nella cartella dello studio. Esegui il grafo $grafo con corsa.py, un comando di shell per volta, nell'ordine, senza raggrupparli.
Comando 0: python3 .agents/script/corsa.py apri $grafo --avviato-da conversazione --sessione \$$var   (tieni l'id che stampa).
Poi, per ognuno dei cinque passi (passo-1, passo-2, passo-3, passo-4, passo-5), tre comandi separati: (a) python3 .agents/script/corsa.py passo <id> passo-N inizio ; (b) sleep 8 ; (c) python3 .agents/script/corsa.py passo <id> passo-N fatto --esito "fatto N".
Alla fine: python3 .agents/script/corsa.py chiudi <id> finita, e una riga di riepilogo.
Se un comando esce con codice 3, o un hook nega un comando, la corsa è stata fermata dall'utente: non riprovare, non chiuderla, non cambiare strada; scrivi una riga che dice che ti sei fermato e a quale passo.
EOF
}

corsa_di() { # <cartella> <grafo> -> il file json della corsa più recente di quel grafo
  ls -1 "$1"/grafi/corse/"$2"-*.json 2>/dev/null | sort | tail -1
}

stato_passo() { # <file corsa> <passo> -> stato del passo, o vuoto
  python3 - "$1" "$2" <<'EOF' 2>/dev/null
import json, sys
c = json.load(open(sys.argv[1]))
for p in c["passi"]:
    if p["id"] == sys.argv[2]:
        print(p["stato"])
EOF
}

# aspetta_e_ferma <cartella> <massimo secondi>: quando il passo 2 di giro-lento è in corso, POST come la pagina
aspetta_e_ferma() {
  local d="$1" massimo="$2" fine f stato porta gettone url id
  fine=$(( $(date +%s) + massimo ))
  while [ "$(date +%s)" -lt "$fine" ]; do
    f="$(corsa_di "$d" giro-lento)"
    if [ -n "$f" ]; then
      stato="$(stato_passo "$f" passo-2)"
      [ "$stato" = "in-corso" ] && break
      [ "$stato" = "fatto" ] && fallisce "il passo 2 era già finito prima dello stop: la prova è arrivata tardi"
    fi
    sleep 0.2
  done
  [ "${stato:-}" = "in-corso" ] || fallisce "il passo 2 di giro-lento non è mai partito (la conversazione A non ha eseguito la corsa)"
  id="$(basename "$f" .json)"
  porta="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['porta'])" "$d/interfaccia/pannello.json")"
  gettone="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['gettone'])" "$d/interfaccia/pannello.json")"
  url="http://127.0.0.1:$porta"
  local cod
  cod="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$url/api/ferma" \
        -H "Origin: $url" -H "Content-Type: application/json" -H "X-Gettone: $gettone" \
        -d "{\"id\":\"$id\",\"perche\":\"prova dello stop\"}")"
  [ "$cod" = "200" ] || fallisce "il POST di stop dà $cod invece di 200"
  echo "stop chiesto alle $(date +%T) su $id"
}

# controlla <cartella> <con_hook: si|no> <A|B uscite>: i fatti dopo lo stop
controlla() {
  local d="$1" hook="$2" fa fb ida idb
  fa="$(corsa_di "$d" giro-lento)"; fb="$(corsa_di "$d" giro-altro)"
  [ -n "$fa" ] || fallisce "la conversazione A non ha aperto nessuna corsa"
  [ -n "$fb" ] || fallisce "la conversazione B non ha aperto nessuna corsa"
  ida="$(basename "$fa" .json)"; idb="$(basename "$fb" .json)"
  python3 - "$fa" "$fb" <<'EOF' || fallisce "lo stato delle corse non è quello atteso (vedi sopra)"
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2]))
st = {p["id"]: p["stato"] for p in a["passi"]}
assert a["stato"] == "fermata", "la corsa A è %s, non fermata" % a["stato"]
assert a["stop"] and a["stop"]["chi"] == "pannello", a["stop"]
assert st["passo-1"] == "fatto", st
assert st["passo-2"] == "fermato", st
assert [st["passo-3"], st["passo-4"], st["passo-5"]] == ["da-fare"] * 3, "dopo lo stop sono avvenuti altri passi: %s" % st
assert b["stato"] == "finita", "la corsa B è %s, non finita" % b["stato"]
assert all(p["stato"] == "fatto" for p in b["passi"]), [p["stato"] for p in b["passi"]]
assert b["stop"] is None
assert a["sessione"] and b["sessione"] and a["sessione"] != b["sessione"], (a["sessione"], b["sessione"])
EOF
  [ ! -e "$d/grafi/corse/$idb.stop" ] || fallisce "la corsa B ha un file .stop"
  [ ! -e "$d/grafi/corse/.$idb.notificato" ] || fallisce "la conversazione B è stata toccata dall'hook"
  if [ "$hook" = "ignora" ]; then
    if [ -e "$d/grafi/corse/.$ida.notificato" ]; then echo "nota: l'hook ha negato un passo di A (marcatore presente)"; else echo "nota: l'hook non è partito (marcatore assente): lo stop è passato dal livello 1"; fi
  elif [ "$hook" = "si" ]; then
    [ -e "$d/grafi/corse/.$ida.notificato" ] || fallisce "l'hook non ha mai negato un passo di A (manca .$ida.notificato): lo stop è passato solo dal livello 1"
  else
    [ ! -e "$d/grafi/corse/.$ida.notificato" ] || fallisce "senza hook c'è un marcatore dell'hook"
  fi
}
