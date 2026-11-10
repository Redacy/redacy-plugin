#!/usr/bin/env bash
# _catena.sh · redacy 0.4.0 · gli anelli comuni di catena-claude.sh e catena-codex.sh (si leggono con `source`)
#
# La catena: inizia -> crea-workspace -> crea-grafo -> corsa -> pannello -> stop, in una cartella
# che parte vuota. Ogni anello si controlla sui file, non sulle parole dell'agente.
# Chi carica questo file definisce prima: RADICE, BASE, G (cartella della catena), STUDIO, HARNESS (claude|codex).
# Riusa, senza riscriverle: prove/inizia/prova-onboarding-*.sh, prove/grafi/_comune.sh (il prompt
# e i controlli di crea-workspace e crea-grafo) e prove/pannello/_stop.sh (le due conversazioni dello stop).

PANNELLO="$RADICE/skills/pannello/scripts/pannello.py"
export PYTHONDONTWRITEBYTECODE=1
RIGHE_ANELLI=()

fallisce() {
  echo "FALLISCE $*"
  [ -n "${STUDIO:-}" ] && python3 "$PANNELLO" --cartella "$STUDIO" --spegni >/dev/null 2>&1
  exit 1
}
anello() { echo "--- anello $1: $2"; }
fatto() { echo "    ok: $*"; RIGHE_ANELLI+=("$*"); }

# Il numero di anello da cui si riparte (CATENA_DA=3 con CATENA_G=<cartella di una catena già iniziata>).
da_anello() { [ "${CATENA_DA:-1}" -le "$1" ]; }

# Anello 1. inizia ha creato l'albero e le copie portano la versione del manifesto.
controlla_albero() {
  local v n
  [ -f "$STUDIO/AGENTS.md" ] && [ -f "$STUDIO/CLAUDE.md" ] || fallisce "inizia non ha creato AGENTS.md e CLAUDE.md"
  grep -q '@AGENTS.md' "$STUDIO/CLAUDE.md" || fallisce "CLAUDE.md non importa AGENTS.md"
  for d in memoria fonti periodo grafi workspace .agents/script .agents/hooks .claude .codex interfaccia; do
    [ -d "$STUDIO/$d" ] || fallisce "inizia non ha creato $d/"
  done
  python3 -I "$RADICE/skills/inizia/scripts/crea-cartella.py" "$STUDIO" --plugin "$RADICE" --controlla > "$G/albero.txt" 2>&1 \
    || fallisce "crea-cartella.py --controlla: $(tail -3 "$G/albero.txt" | tr '\n' ' ')"
  v="$(python3 -I -c "import json;print(json.load(open('$RADICE/.claude-plugin/plugin.json'))['version'])")"
  n="$(grep -l "redacy $v" "$STUDIO"/.agents/script/* "$STUDIO"/.agents/hooks/*.py 2>/dev/null | wc -l | tr -d ' ')"
  [ "$n" -ge 6 ] || fallisce "solo $n copie in .agents/ portano «redacy $v» in testa (ne attendo almeno 6)"
  for f in "$STUDIO"/periodo/todo.json "$STUDIO"/periodo/idee.json; do
    python3 -I "$STUDIO/.agents/hooks/controlla-periodo.py" "$f" >/dev/null 2>&1 || fallisce "$(basename "$f") non passa controlla-periodo.py"
  done
  fatto "albero completo, $n copie con «redacy $v» in testa, todo.json e idee.json validi"
}

# Anello 3. crea-workspace e crea-grafo hanno lasciato workspace e grafi validi (i controlli di prove/grafi/_comune.sh)
controlla_workspace_e_grafo() {
  FALLITI=""
  controlla_risultato "$STUDIO"
  [ -z "$FALLITI" ] || fallisce "$FALLITI"
  GRAFO="$(ls "$STUDIO"/grafi/*.yaml 2>/dev/null | head -1 | xargs -n1 basename 2>/dev/null | sed 's/\.yaml$//')"
  [ -n "$GRAFO" ] || fallisce "nessun grafo in grafi/"
  fatto "$(ls -d "$STUDIO"/workspace/*/ | wc -l | tr -d ' ') workspace validi, grafo «$GRAFO» (passa controlla-grafo.py, L0, spento), righe nel registro"
}

# Anello 4. una corsa scritta: tutti i passi, poi chiusa
fai_corsa() {
  local out id
  GRAFO="${GRAFO:-$(ls "$STUDIO"/grafi/*.yaml | head -1 | xargs -n1 basename | sed 's/\.yaml$//')}"
  out="$(cd "$STUDIO" && python3 .agents/script/corsa.py apri "$GRAFO" --avviato-da utente 2>"$G/corsa-apri.err")" \
    || fallisce "corsa.py apri $GRAFO: $(cat "$G/corsa-apri.err")"
  CORSA_ID="$(echo "$out" | tail -1)"
  [ -f "$STUDIO/grafi/corse/$CORSA_ID.json" ] || fallisce "la corsa $CORSA_ID non è stata scritta"
  python3 - "$STUDIO/grafi/corse/$CORSA_ID.json" > "$G/passi.txt" <<'PY'
import json, sys
for p in json.load(open(sys.argv[1]))["passi"]:
    print(p["id"])
PY
  while read -r p; do
    (cd "$STUDIO" && python3 .agents/script/corsa.py passo "$CORSA_ID" "$p" inizio && \
     python3 .agents/script/corsa.py passo "$CORSA_ID" "$p" fatto --esito "prova $p") >/dev/null 2>&1 \
      || fallisce "corsa.py passo $p"
  done < "$G/passi.txt"
  (cd "$STUDIO" && python3 .agents/script/corsa.py chiudi "$CORSA_ID" finita) >/dev/null 2>&1 || fallisce "corsa.py chiudi"
  python3 - "$STUDIO/grafi/corse/$CORSA_ID.json" <<'PY' || fallisce "la corsa scritta non è finita con tutti i passi fatti"
import json, sys
c = json.load(open(sys.argv[1]))
assert c["stato"] == "finita", c["stato"]
assert all(p["stato"] == "fatto" for p in c["passi"]), [p["stato"] for p in c["passi"]]
assert c["avviato_da"] == "utente" and c["fine"]
PY
  fatto "corsa $CORSA_ID: $(wc -l < "$G/passi.txt" | tr -d ' ') passi fatti, chiusa «finita»"
}

# Anello 5. il pannello: si accende (da terminale, come la riga che inizia dà all'utente), risponde 200, vede la cartella
accendi_pannello() {
  local usc porta url gettone
  usc="$(python3 "$PANNELLO" --cartella "$STUDIO" 2>&1)" || fallisce "il pannello non parte: $usc"
  porta="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['porta'])" "$STUDIO/interfaccia/pannello.json")" \
    || fallisce "manca interfaccia/pannello.json"
  url="http://127.0.0.1:$porta"
  [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url/")" = "200" ] || fallisce "la pagina non risponde 200 ($url)"
  for v in stato periodo grafi corse memoria file-chiave; do
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url/api/$v")" = "200" ] || fallisce "/api/$v non risponde 200"
  done
  curl -s "$url/api/grafi" > "$G/api-grafi.json"; curl -s "$url/api/corse" > "$G/api-corse.json"
  grep -q "$GRAFO" "$G/api-grafi.json" || fallisce "il pannello non mostra il grafo $GRAFO"
  grep -q "$CORSA_ID" "$G/api-corse.json" || fallisce "il pannello non mostra la corsa $CORSA_ID"
  PANNELLO_URL="$url"
  fatto "pannello acceso su $url: pagina e sei viste rispondono 200, mostra il grafo $GRAFO e la corsa $CORSA_ID"
}

# Anello 6a. lo stop, livello 1: nessun hook, nessun modello. Una corsa in corso, lo stop dalla pagina (POST con gettone),
# il comando dopo lo stop esce con 3 e la corsa risulta «fermata».
stop_livello_1() {
  local id porta gettone url cod rc
  id="$(cd "$STUDIO" && python3 .agents/script/corsa.py apri "$GRAFO" --avviato-da utente 2>/dev/null | tail -1)"
  [ -n "$id" ] || fallisce "non riesco ad aprire la corsa da fermare"
  (cd "$STUDIO" && python3 .agents/script/corsa.py passo "$id" "$(head -1 "$G/passi.txt")" inizio) >/dev/null 2>&1 || fallisce "il primo passo non parte"
  porta="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['porta'])" "$STUDIO/interfaccia/pannello.json")"
  gettone="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['gettone'])" "$STUDIO/interfaccia/pannello.json")"
  url="http://127.0.0.1:$porta"
  cod="$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 -X POST "$url/api/ferma" \
        -H "Origin: $url" -H "Content-Type: application/json" -H "X-Gettone: $gettone" \
        -d "{\"id\":\"$id\",\"perche\":\"prova della catena\"}")"
  [ "$cod" = "200" ] || fallisce "il POST di stop dà $cod invece di 200"
  (cd "$STUDIO" && python3 .agents/script/corsa.py passo "$id" "$(head -1 "$G/passi.txt")" fatto) >/dev/null 2>&1; rc=$?
  [ "$rc" = "3" ] || fallisce "il comando dopo lo stop esce con $rc invece di 3"
  python3 - "$STUDIO/grafi/corse/$id.json" <<'PY' || fallisce "la corsa fermata non risulta «fermata» nel file"
import json, sys
c = json.load(open(sys.argv[1]))
assert c["stato"] == "fermata", c["stato"]
assert c["stop"] and c["stop"]["chi"] == "pannello", c["stop"]
PY
  fatto "stop livello 1: POST dalla pagina 200, il comando dopo lo stop esce con 3, la corsa è «fermata» (chi: pannello)"
}

# Anello 6b. lo stop con due conversazioni dell'harness nella stessa cartella (funzioni di prove/pannello/_stop.sh).
# $1 = claude|codex. Su Claude si pretende anche il marcatore dell'hook (livello 2), su Codex no (serve /hooks dell'utente).
stop_conversazioni() {
  local harness="$1" var hook pa pb
  # shellcheck source=pannello/_stop.sh
  D="$STUDIO"
  source "$RADICE/prove/pannello/_stop.sh"
  fallisce() { echo "FALLISCE $*"; python3 "$PANNELLO" --cartella "$STUDIO" --spegni >/dev/null 2>&1; exit 1; }
  grafo_lento giro-lento > "$STUDIO/grafi/giro-lento.yaml"
  grafo_lento giro-altro > "$STUDIO/grafi/giro-altro.yaml"
  python3 "$STUDIO/.agents/script/controlla-grafo.py" "$STUDIO/grafi/giro-lento.yaml" "$STUDIO/grafi/giro-altro.yaml" >/dev/null 2>&1 \
    || fallisce "i grafi dello stop non passano controlla-grafo.py"
  [ -f "$STUDIO/.agents/hooks/ferma.py" ] || fallisce "manca .agents/hooks/ferma.py nella cartella"
  if [ "$harness" = "claude" ]; then
    var=CLAUDE_CODE_SESSION_ID; hook=si
    ( cd "$STUDIO" && timeout 600 claude -p --model sonnet --plugin-dir "$RADICE" --allowedTools "Bash" -- \
        "$(prompt_conversazione A giro-lento $var)" < /dev/null > "$G/stop-A.out" 2>&1 ) & pa=$!
    ( cd "$STUDIO" && timeout 600 claude -p --model sonnet --plugin-dir "$RADICE" --allowedTools "Bash" -- \
        "$(prompt_conversazione B giro-altro $var)" < /dev/null > "$G/stop-B.out" 2>&1 ) & pb=$!
  else
    var=CODEX_THREAD_ID; hook=ignora
    local CX=(codex exec --skip-git-repo-check -C "$STUDIO" -s workspace-write --json -c "projects={\"$STUDIO\"={trust_level=\"trusted\"}}")
    ( timeout 600 "${CX[@]}" "$(prompt_conversazione A giro-lento $var)" < /dev/null > "$G/stop-A.jsonl" 2> "$G/stop-A.err" ) & pa=$!
    ( timeout 600 "${CX[@]}" "$(prompt_conversazione B giro-altro $var)" < /dev/null > "$G/stop-B.jsonl" 2> "$G/stop-B.err" ) & pb=$!
  fi
  aspetta_e_ferma "$STUDIO" 420
  wait "$pa" "$pb"
  controlla "$STUDIO" "$hook"
  if [ "$harness" = "claude" ]; then
    fatto "stop con due conversazioni su Claude: A fermata dalla pagina al passo 2, B finita; l'hook ferma.py ha negato un passo (livelli 1 e 2)"
  else
    fatto "stop con due conversazioni su Codex: A fermata al passo 2, B finita (livello 1; stadio 2 degli hook: serve /hooks dell'utente, vedi prove/pannello/prova-stop-codex.sh)"
  fi
}

fine_catena() {
  python3 "$PANNELLO" --cartella "$STUDIO" --spegni >/dev/null 2>&1
  echo
  for r in "${RIGHE_ANELLI[@]}"; do echo "  $r"; done
  echo "cartella della catena: $G"
  echo "PASSA"
}
