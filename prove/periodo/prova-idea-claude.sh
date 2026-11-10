#!/usr/bin/env bash
# redacy 0.4.2 · prove/periodo/prova-idea-claude.sh
# A metà di un lavoro l'utente dice un'idea fuori periodo: finisce in periodo/idee.json, non in periodo/todo.json,
# e il lavoro in corso continua. La riga di AGENTS.md è la stessa che propone _lavoro/C/schemi.md (la scrive A).
set -u
QUI="$(cd "$(dirname "$0")" && pwd)"
PLUGIN="$(cd "$QUI/../.." && pwd)"
S="$PLUGIN/skills/pianifica-periodo"
C="$S/scripts/controlla-periodo.py"
P="${PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove/C}/idea-claude"
fallisce() { echo "FALLISCE $1"; exit 1; }
command -v claude >/dev/null || fallisce "claude non c'è"

rm -rf "$P"; mkdir -p "$P/periodo" "$P/fonti" "$P/memoria" "$P/.agents/hooks" "$P/.claude"
cp "$S/scripts/controlla-periodo.py" "$S/scripts/todo.schema.json" "$S/scripts/idee.schema.json" "$P/.agents/hooks/"
cp "$S/examples/idee.vuoto.json" "$P/periodo/idee.json"
cat > "$P/.claude/settings.json" <<'J'
{"hooks": {"PostToolUse": [{"matcher": "Write|Edit|MultiEdit|Bash",
  "hooks": [{"type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR/.agents/hooks/controlla-periodo.py\""}]}]}}
J
cat > "$P/AGENTS.md" <<'J'
# Studio Bianchi (cartella di prova, dati inventati)

Sei l'agente AI dello studio. Leggi `memoria/INDICE.md` e `periodo/obiettivo.md` all'inizio.

## Come si lavora

- Un'idea che l'utente dice fuori periodo, cioè che non c'entra con l'obiettivo in `periodo/obiettivo.md`, non si insegue: la aggiungi come voce a `periodo/idee.json` (id nuovo, `da_dove: "conversazione"`, `arrivata` di oggi, senza `esito`), lo dici in una riga e torni al lavoro. Non la scrivi in `periodo/todo.json`: ce la porta solo `pianifica-periodo`, dopo aver pesato le idee con l'utente.
- `periodo/obiettivo.md` lo cambia solo l'utente, se lo chiede.
- Dopo ogni scrittura di `periodo/todo.json` o `periodo/idee.json` un controllo automatico dice se il file è valido: se non lo è, correggilo subito.
J
printf '@AGENTS.md\n' > "$P/CLAUDE.md"
printf '# Indice\n\n- (vuota)\n' > "$P/memoria/INDICE.md"
cat > "$P/periodo/obiettivo.md" <<'J'
Chiudere le dichiarazioni dei redditi dei clienti dello studio entro il 30 novembre.

Fatto quando: tutte le pratiche in `fonti/pratiche.md` hanno l'elenco dei documenti mancanti.
J
cat > "$P/periodo/todo.json" <<'J'
{"versione": "0.3.0", "periodo": "2026-11", "todo": [
  {"id": "t1", "cosa": "Preparare l'elenco dei documenti mancanti per ogni pratica", "chi": "agente", "stato": "in corso",
   "scadenza": "2026-11-15", "dove": "fonti/pratiche.md", "da": "piano", "aggiornato": "2026-11-06"}]}
J
cat > "$P/fonti/pratiche.md" <<'J'
# Pratiche (dati inventati)
- Rossi Mario: ha consegnato CU, spese mediche, mutuo
- Verdi Anna: ha consegnato CU
- Neri SRL: ha consegnato bilancio
Documenti richiesti a tutti: CU, spese mediche, mutuo (se c'è), bilancio (solo società).
J
cp "$P/periodo/todo.json" "$P/_todo.prima.json"

PROMPT='Sto lavorando alla pratica di Rossi, Verdi e Neri: scrivimi in memoria/elenco-mancanti.md, una riga per cliente, i documenti che mancano. Ah, a proposito, mi è appena venuta un idea che non c entra con questo lavoro: mandare ai clienti un promemoria una settimana prima di ogni scadenza fiscale. Per ora non pensiamoci, tu intanto finisci l elenco.'
cd "$P" || fallisce "cartella"
timeout 600 claude -p --model sonnet --plugin-dir "$PLUGIN" --permission-mode acceptEdits \
  --output-format stream-json --verbose "$PROMPT" < /dev/null > "$P/trascrizione.jsonl" 2> "$P/errori.txt"
[ -s "$P/trascrizione.jsonl" ] || fallisce "nessuna uscita da claude: $(head -c 300 "$P/errori.txt")"

# 1) l'idea è in idee.json, e il file è valido
python3 "$C" "$P/periodo/idee.json" >/dev/null || fallisce "idee.json non è valido: $(python3 "$C" "$P/periodo/idee.json" | tail -3)"
python3 - "$P/periodo/idee.json" <<'PY' || exit 1
import json, sys
d = json.load(open(sys.argv[1]))
v = [i for i in d["idee"] if "promemoria" in i["idea"].lower()]
if len(v) != 1: print("FALLISCE l'idea del promemoria non c'è in idee.json (una sola volta):", len(v)); sys.exit(1)
if v[0].get("esito"): print("FALLISCE l'idea ha già un esito: va pesata con pianifica-periodo"); sys.exit(1)
PY
# 2) non è in todo.json: stesso numero di voci e nessuna parla di promemoria
python3 - "$P/periodo/todo.json" "$P/_todo.prima.json" <<'PY' || exit 1
import json, sys
d = json.load(open(sys.argv[1])); prima = json.load(open(sys.argv[2]))
if len(d["todo"]) != len(prima["todo"]) or any("promemoria" in t["cosa"].lower() for t in d["todo"]):
    print("FALLISCE l'idea è finita in todo.json"); sys.exit(1)
PY
python3 "$C" "$P/periodo/todo.json" >/dev/null || fallisce "todo.json non è più valido"
# 3) obiettivo.md intatto
grep -q "Chiudere le dichiarazioni dei redditi" "$P/periodo/obiettivo.md" && ! grep -qi promemoria "$P/periodo/obiettivo.md" || fallisce "obiettivo.md toccato"
# 4) il lavoro è continuato
[ -s "$P/memoria/elenco-mancanti.md" ] && grep -qi verdi "$P/memoria/elenco-mancanti.md" || fallisce "l'elenco dei documenti mancanti non è stato scritto"

# contrasto (solo informativo): la stessa cartella senza la riga sull'idea fuori periodo
K="$P/contrasto"; mkdir -p "$K"; cp -R "$P/periodo" "$P/fonti" "$P/memoria" "$P/.agents" "$P/.claude" "$P/CLAUDE.md" "$K/"
cp "$S/examples/idee.vuoto.json" "$K/periodo/idee.json"; rm -f "$K/memoria/elenco-mancanti.md"; cp "$P/_todo.prima.json" "$K/periodo/todo.json"
printf '# Studio Bianchi (cartella di prova, dati inventati)\n\nSei l agente AI dello studio. Leggi memoria/INDICE.md e periodo/obiettivo.md all inizio.\n' > "$K/AGENTS.md"
( cd "$K" && timeout 600 claude -p --model sonnet --plugin-dir "$PLUGIN" --permission-mode acceptEdits "$PROMPT" < /dev/null > "$K/uscita.txt" 2>&1 )
n=$(python3 -c "import json;print(len(json.load(open('$K/periodo/idee.json'))['idee']))")
echo "contrasto: senza la riga di AGENTS.md idee.json ha $n voci (con la riga: 1)"
echo PASSA
