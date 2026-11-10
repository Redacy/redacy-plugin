#!/usr/bin/env bash
# redacy 0.4.2 · prove/periodo/prova-hook-codex.sh
# PRIMA DI RILANCIARE (a mano, una volta): SOLO_STADIO_1=1 bash prove/periodo/prova-hook-codex.sh prepara la cartella;
#   poi nel terminale: cd ${TMPDIR:-/tmp}/redacy-plugin-prove/C/hook-codex && codex  e dentro Codex scrivi /hooks,
#   fidati dell'hook PostToolUse (controlla-periodo.py), esci. Il comando da lanciare dopo: bash prove/periodo/prova-hook-codex.sh
# Lo stesso controllo su Codex, in due stadi.
#  Stadio 1 (senza modello): l'evento che Codex manda a un hook PostToolUse dopo un apply_patch
#    (tool_name "apply_patch", la patch in tool_input.command, come dice la documentazione di Codex)
#    dà uscita 2 con il messaggio su stderr e il JSON decision/additionalContext su stdout.
#  Stadio 2 (una chiamata a Codex): in una cartella con .codex/hooks.json una sessione scrive un todo.json rotto
#    e l'hook lo segnala. Gli hook di Codex partono solo se la cartella è fidata E l'hook è stato rivisto:
#    una volta, a mano, con «codex» nella cartella di prova e il comando /hooks. Senza, lo stadio 2 dice
#    FALLISCE e spiega cosa fare. Il flag --dangerously-bypass-hook-trust NON si usa.
set -u
QUI="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$(cd "$QUI/../.." && pwd)"
S="$PLUGIN/skills/pianifica-periodo"
C="$S/scripts/controlla-periodo.py"
P="${PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove/C}/hook-codex"
LOCK="${TMPDIR:-/tmp}/redacy-plugin-prove/.codex.lock"; mkdir -p "$(dirname "$LOCK")"
fallisce() { echo "FALLISCE $1"; exit 1; }

mkdir -p "$P/periodo" "$P/.agents/hooks" "$P/.codex"
cp "$S/scripts/controlla-periodo.py" "$S/scripts/todo.schema.json" "$S/scripts/idee.schema.json" "$P/.agents/hooks/"
[ -e "$P/periodo/idee.json" ] || cp "$S/examples/idee.vuoto.json" "$P/periodo/idee.json"
cp "$S/examples/todo.vuoto.json" "$P/periodo/todo.json"

# ---- stadio 1: l'evento di Codex, senza modello
cat > "$P/_toccato.json" <<'J'
{"versione":"0.3.0","periodo":"","todo":[{"id":"t1","cosa":"Chiamare Rossi","chi":"tu","stato":"boh","scadenza":"","dove":"","da":"utente","aggiornato":"2026-11-07"}]}
J
cp "$P/_toccato.json" "$P/periodo/todo.json"
EV=$(python3 - "$P" <<'PY'
import json, sys
patch = "*** Begin Patch\n*** Update File: periodo/todo.json\n@@\n-  \"todo\": []\n+  \"todo\": [ ... ]\n*** End Patch\n"
print(json.dumps({"session_id": "prova", "transcript_path": None, "cwd": sys.argv[1], "hook_event_name": "PostToolUse",
                  "model": "prova", "permission_mode": "default", "turn_id": "t1", "tool_name": "apply_patch",
                  "tool_use_id": "u1", "tool_input": {"command": patch}, "tool_response": {"output": "Success"}}))
PY
)
out="$(echo "$EV" | python3 "$P/.agents/hooks/controlla-periodo.py" 2>"$P/_stderr.txt")"; rc=$?
[ "$rc" = 2 ] || fallisce "stadio 1: uscita $rc, attesa 2"
grep -qF "non è fra i valori ammessi" "$P/_stderr.txt" || fallisce "stadio 1: manca il messaggio su stderr"
echo "$out" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['decision']=='block' and d['hookSpecificOutput']['additionalContext']" 2>/dev/null || fallisce "stadio 1: JSON su stdout non valido"
echo "stadio 1 PASSA (evento apply_patch di Codex: uscita 2, messaggio e JSON)"

# ---- stadio 2: Codex vero
command -v codex >/dev/null || fallisce "codex non c'è"
cp "$S/examples/todo.vuoto.json" "$P/periodo/todo.json"
cat > "$P/.codex/hooks.json" <<'J'
{"hooks": {"PostToolUse": [{"matcher": "apply_patch|Edit|Write|Bash",
  "hooks": [{"type": "command", "command": "f=\"$(pwd)/.agents/hooks/controlla-periodo.py\"; [ ! -f \"$f\" ] || python3 \"$f\""}]}]}}
J
cat > "$P/.codex/config.toml" <<'J'
sandbox_mode = "workspace-write"
approval_policy = "on-request"
J
printf '# Studio di prova\nDopo ogni scrittura di periodo/todo.json un controllo automatico ti dice se il file è valido.\n' > "$P/AGENTS.md"
[ "${SOLO_STADIO_1:-}" = 1 ] && { echo "cartella pronta, stadio 2 non lanciato (SOLO_STADIO_1=1): la prova intera non è PASSA"; exit 0; }
PROMPT='Scrivi in periodo/todo.json una voce con id t1, cosa "Chiamare Rossi", chi "tu", stato "boh" (proprio questo valore, è una prova), scadenza vuota, dove vuoto, da "utente", aggiornato "2026-11-07", nello stesso formato di prima. Usa apply_patch. Poi riporta testuale cosa ti ha detto il controllo automatico dopo la scrittura.'
(
  flock 9
  cd "$P" && timeout 600 codex exec --skip-git-repo-check -C "$P" --json \
    -c "projects={\"$P\"={trust_level=\"trusted\"}}" "$PROMPT" < /dev/null > "$P/trascrizione.jsonl" 2> "$P/errori.txt"
) 9>"$LOCK"
[ -s "$P/trascrizione.jsonl" ] || fallisce "stadio 2: nessuna uscita da codex: $(head -c 300 "$P/errori.txt")"
grep -q boh "$P/periodo/todo.json" || fallisce "stadio 2: la sessione non ha scritto lo stato rotto: vedi trascrizione.jsonl"
if grep -qF "non è fra i valori ammessi" "$P/trascrizione.jsonl"; then
  echo "stadio 2 PASSA (il messaggio del controllo compare nella trascrizione di Codex)"
  echo PASSA
else
  echo "FALLISCE stadio 2: il controllo non ha parlato. Gli hook di Codex partono solo dopo la revisione: apri 'codex' in $P, scrivi /hooks, fidati dell'hook, esci, rilancia questa prova."
  exit 1
fi
