#!/usr/bin/env bash
# redacy 0.3.0 · prove/periodo/prova-hook-claude.sh
# In una cartella di prova con l'adattatore di Claude Code, una sessione scrive un todo.json rotto
# e l'hook di controllo lo segnala. Si vede nella trascrizione (stream-json): il messaggio dell'hook
# arriva alla sessione, non è solo ciò che la sessione ha scritto.
set -u
QUI="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$(cd "$QUI/../.." && pwd)"
S="$PLUGIN/skills/pianifica-periodo"
P="${PROVE:-/home/ubuntu/lab/redacy-plugin-prove/C}/hook-claude"
fallisce() { echo "FALLISCE $1"; exit 1; }
command -v claude >/dev/null || fallisce "claude non c'è"

rm -rf "$P"; mkdir -p "$P/periodo" "$P/.agents/hooks" "$P/.claude"
cp "$S/scripts/controlla-periodo.py" "$S/scripts/todo.schema.json" "$S/scripts/idee.schema.json" "$P/.agents/hooks/"
cp "$S/examples/todo.vuoto.json" "$P/periodo/todo.json"
cp "$S/examples/idee.vuoto.json" "$P/periodo/idee.json"
cat > "$P/.claude/settings.json" <<'J'
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit|MultiEdit|Bash",
        "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.agents/hooks/controlla-periodo.py\""}]
      }
    ]
  }
}
J
cat > "$P/AGENTS.md" <<'J'
# Studio di prova
Cartella di prova. Dopo ogni scrittura di periodo/todo.json o periodo/idee.json un controllo ti dice se il file è valido.
J
printf '@AGENTS.md\n' > "$P/CLAUDE.md"

PROMPT='Scrivi in periodo/todo.json una voce con id t1, cosa "Chiamare Rossi", chi "tu", stato "boh" (proprio questo valore, è una prova), scadenza vuota, dove vuoto, da "utente", aggiornato "2026-11-07". Tienilo nel formato di prima (versione, periodo, todo). Usa lo strumento di scrittura. Poi riferisci in una riga cosa ti ha detto il controllo automatico dopo la scrittura, citando le sue parole.'
cd "$P" || fallisce "cartella"
timeout 600 claude -p --model sonnet --plugin-dir "$PLUGIN" --permission-mode acceptEdits \
  --include-hook-events --output-format stream-json --verbose "$PROMPT" < /dev/null > "$P/trascrizione.jsonl" 2> "$P/errori.txt"
rc=$?
[ -s "$P/trascrizione.jsonl" ] || fallisce "nessuna uscita da claude (rc=$rc): $(head -c 300 "$P/errori.txt")"

# 1) il file è davvero rotto sul disco (la sessione ha scritto «boh»)
grep -q '"stato"' "$P/periodo/todo.json" && grep -q 'boh' "$P/periodo/todo.json" || fallisce "la sessione non ha scritto lo stato rotto (o l'ha già corretto): vedi trascrizione.jsonl"
# 2) l'evento hook_response di PostToolUse:Write porta il messaggio e il codice 2: l'hook è arrivato
python3 - "$P/trascrizione.jsonl" <<'PY' || exit 1
import json, sys
visto = False
for riga in open(sys.argv[1], encoding="utf-8"):
    try: e = json.loads(riga)
    except ValueError: continue
    if e.get("type") == "system" and e.get("subtype") == "hook_response" and e.get("hook_name", "").startswith("PostToolUse:") \
       and e.get("exit_code") == 2 and "non è fra i valori ammessi" in e.get("output", ""):
        visto = True
        print("hook_response", e["hook_name"], "exit", e["exit_code"])
        break
if not visto:
    print("FALLISCE nessun hook_response con codice 2 e il messaggio di controllo"); sys.exit(1)
PY
# 3) il modello lo ha ricevuto: la risposta finale cita i valori ammessi (che non poteva sapere dal prompt)
python3 - "$P/trascrizione.jsonl" <<'PY' || exit 1
import json, sys
for riga in open(sys.argv[1], encoding="utf-8"):
    try: e = json.loads(riga)
    except ValueError: continue
    if e.get("type") == "result":
        r = e.get("result", "")
        if "in corso" in r and "ferma" in r:
            print("il modello ha citato i valori ammessi"); sys.exit(0)
print("FALLISCE la risposta finale non cita i valori ammessi dal controllo"); sys.exit(1)
PY
echo PASSA
