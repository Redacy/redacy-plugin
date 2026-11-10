#!/usr/bin/env bash
# prova-cartella.sh · redacy 0.4.2
# Crea una cartella vuota, lancia crea-cartella.py, controlla l'albero, rilancia e controlla
# che non sovrascriva nulla. Prova anche la copia degli script delle altre skill (con la
# versione e l'origine in testa) su un plugin finto, così il risultato non dipende da cosa
# c'è già nel plugin. Con _innesta.py prova anche --innesta e --aggiorna. Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/inizia/prova-cartella.sh
# Le cartelle di prova vanno in $REDACY_PROVE (se c'è), se no in una cartella temporanea.
set -u

RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
SCRIPT="$RADICE/skills/inizia/scripts/crea-cartella.py"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
mkdir -p "$BASE"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
D="$BASE/cartella-$ORA"
FINTO="$BASE/plugin-finto-$ORA"

fallisce() { echo "FALLISCE $*"; exit 1; }
impronte() { (cd "$1" && find . -type f -print0 | sort -z | xargs -0 sha256sum); }

command -v python3 >/dev/null || fallisce "manca python3"
[ -f "$SCRIPT" ] || fallisce "manca $SCRIPT"

# 1. Prima creazione in una cartella vuota
mkdir -p "$D"
python3 "$SCRIPT" "$D" > "$BASE/uscita-1-$ORA.txt" 2>&1 || fallisce "la prima creazione esce con errore (vedi $BASE/uscita-1-$ORA.txt)"

# 2. L'albero del contratto
for p in AGENTS.md CLAUDE.md .agents/hooks.json .agents/policy/cosa-faccio-da-solo.md \
         .agents/regole/memoria.md .agents/regole/testi-per-persone.md \
         .claude/settings.json .codex/config.toml .codex/hooks.json \
         memoria/INDICE.md memoria/LOG.md memoria/fonti-dati.md \
         periodo/obiettivo.md periodo/todo.json periodo/idee.json fonti/LEGGIMI.md interfaccia/.gitignore; do
  [ -f "$D/$p" ] || fallisce "manca il file $p"
done
for p in .agents/skills .agents/regole .agents/policy .agents/hooks .agents/script \
         .claude .codex memoria fonti periodo interfaccia grafi grafi/corse workspace; do
  [ -d "$D/$p" ] || fallisce "manca la cartella $p/"
done
[ -L "$D/.claude/skills" ] && [ "$(readlink "$D/.claude/skills")" = "../.agents/skills" ] || fallisce ".claude/skills non è il collegamento a ../.agents/skills"
[ -L "$D/.claude/rules" ] && [ "$(readlink "$D/.claude/rules")" = "../.agents/regole" ] || fallisce ".claude/rules non è il collegamento a ../.agents/regole"
find "$D" -name .tienimi | grep -q . && fallisce "un segnaposto .tienimi è finito nella cartella"

# 3. La forma dei file
[ "$(cat "$D/CLAUDE.md")" = "@AGENTS.md" ] || fallisce "CLAUDE.md non è @AGENTS.md"
grep -qx 'pannello.json' "$D/interfaccia/.gitignore" && grep -qx 'pannello.log' "$D/interfaccia/.gitignore" || fallisce "interfaccia/.gitignore non tiene fuori da git pannello.json e pannello.log"
PAROLE=$(wc -w < "$D/AGENTS.md")
[ "$PAROLE" -lt 1500 ] || fallisce "AGENTS.md ha $PAROLE parole, il tetto è 1500"
grep -q 'memoria/INDICE.md' "$D/AGENTS.md" || fallisce "AGENTS.md non dice di leggere memoria/INDICE.md"
python3 - "$D" <<'EOF' || fallisce "un file JSON non va o gli hook non coincidono (vedi sopra)"
import json, sys
try:
    import tomllib
except ImportError:  # python3 prima della 3.11 (il Mac di serie): il toml non si controlla
    tomllib = None
from pathlib import Path
d = Path(sys.argv[1])
for p in [".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json", "periodo/todo.json", "periodo/idee.json"]:
    json.loads((d / p).read_text(encoding="utf-8"))
if tomllib:
    tomllib.loads((d / ".codex/config.toml").read_text(encoding="utf-8"))
todo = json.loads((d / "periodo/todo.json").read_text())
idee = json.loads((d / "periodo/idee.json").read_text())
assert todo == {"versione": "0.3.0", "periodo": "", "todo": []}, f"todo.json: {todo}"
assert idee == {"versione": "0.3.0", "periodo": "", "idee": []}, f"idee.json: {idee}"
voci = [json.dumps(json.loads((d / p).read_text())["hooks"], sort_keys=True)
        for p in [".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json"]]
assert len(set(voci)) == 1, "le voci degli hook non sono uguali nei tre file"
h = json.loads(voci[0])
assert "ferma.py" in h["PreToolUse"][0]["hooks"][0]["command"], "PreToolUse non lancia ferma.py"
assert "controlla-periodo.py" in h["PostToolUse"][0]["hooks"][0]["command"], "PostToolUse non lancia controlla-periodo.py"
pol = (d / ".agents/policy/cosa-faccio-da-solo.md").read_text()
assert not any(r.lstrip().startswith("|") for r in pol.splitlines()), "la policy contiene una tabella"
EOF
[ "$(grep -c ' · inizia · ' "$D/memoria/LOG.md")" = 1 ] || fallisce "dopo la prima creazione LOG.md non ha una riga inizia"

# 4. Un hook con lo script che manca non blocca (esce 0)
for ev in PreToolUse PostToolUse; do
  CMD=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['hooks'][sys.argv[2]][0]['hooks'][0]['command'])" "$D/.agents/hooks.json" "$ev")
  T=$(mktemp -d)
  (cd "$T" && echo '{}' | CLAUDE_PROJECT_DIR="$T" bash -c "$CMD") || fallisce "l'hook $ev con lo script mancante non esce 0"
  rm -rf "$T"
done

# 5. --controlla su una cartella completa: niente manca
python3 "$SCRIPT" "$D" --controlla > "$BASE/uscita-controlla-$ORA.txt" 2>&1 || fallisce "--controlla su una cartella appena creata esce con errore"

# 6. Seconda passata: modifico un file, ne tolgo un altro; deve ricreare quello tolto e non toccare il resto
echo "riga dell'utente $ORA" >> "$D/memoria/INDICE.md"
rm "$D/periodo/idee.json"
PRIMA=$(impronte "$D" | grep -v -e ' ./periodo/idee.json$' -e ' ./memoria/LOG.md$')
python3 "$SCRIPT" "$D" > "$BASE/uscita-2-$ORA.txt" 2>&1 || fallisce "la seconda passata esce con errore"
grep -q "riga dell'utente $ORA" "$D/memoria/INDICE.md" || fallisce "la seconda passata ha sovrascritto memoria/INDICE.md"
grep -q '^saltato (c.è già): memoria/INDICE.md$' "$BASE/uscita-2-$ORA.txt" || fallisce "la seconda passata non dice di aver saltato memoria/INDICE.md"
[ -f "$D/periodo/idee.json" ] || fallisce "la seconda passata non ha ricreato periodo/idee.json"
DOPO=$(impronte "$D" | grep -v -e ' ./periodo/idee.json$' -e ' ./memoria/LOG.md$')
[ "$PRIMA" = "$DOPO" ] || fallisce "la seconda passata ha cambiato file che c'erano già"
[ "$(grep -c ' · inizia · ' "$D/memoria/LOG.md")" = 2 ] || fallisce "la seconda passata (un file creato) non ha aggiunto la sua riga a LOG.md"

# 7. Terza passata: niente da creare, niente cambia, LOG.md compreso
PRIMA=$(impronte "$D")
python3 "$SCRIPT" "$D" > "$BASE/uscita-3-$ORA.txt" 2>&1 || fallisce "la terza passata esce con errore"
grep -q '^esito: 0 creati' "$BASE/uscita-3-$ORA.txt" || fallisce "la terza passata ha creato qualcosa"
[ "$PRIMA" = "$(impronte "$D")" ] || fallisce "la terza passata ha cambiato qualcosa"

# 8. --controlla su una cartella vuota: dice cosa manca, esce 1, non scrive
V="$BASE/vuota-$ORA"; mkdir -p "$V"
python3 "$SCRIPT" "$V" --controlla > "$BASE/uscita-vuota-$ORA.txt" 2>&1 && fallisce "--controlla su una cartella vuota esce 0"
grep -q '^manca: AGENTS.md$' "$BASE/uscita-vuota-$ORA.txt" || fallisce "--controlla su una cartella vuota non dice che manca AGENTS.md"
[ -z "$(ls -A "$V")" ] || fallisce "--controlla ha scritto nella cartella vuota"

# 9. Le copie dalle altre skill, su un plugin finto con tutte le sorgenti
mkdir -p "$FINTO/.claude-plugin" "$FINTO/skills"
cp -R "$RADICE/skills/inizia" "$FINTO/skills/"
echo '{"name": "redacy", "version": "9.9.9"}' > "$FINTO/.claude-plugin/plugin.json"
for s in skills/crea-grafo/scripts/corsa.py skills/crea-grafo/scripts/controlla-grafo.py \
         skills/crea-grafo/scripts/yaml_ridotto.py skills/pianifica-periodo/scripts/controlla-periodo.py \
         skills/pannello/scripts/ferma.py skills/pannello/scripts/pannello.py; do
  mkdir -p "$FINTO/$(dirname "$s")"
  printf '#!/usr/bin/env python3\nprint("finto")\n' > "$FINTO/$s"
done
for s in skills/pianifica-periodo/scripts/todo.schema.json skills/pianifica-periodo/scripts/idee.schema.json; do
  echo '{"type": "object"}' > "$FINTO/$s"
done
printf '<!doctype html>\n<html><body>finta</body></html>\n' > "$FINTO/skills/pannello/scripts/pagina.html"
mkdir -p "$FINTO/skills/pannello/modello"
echo '{"version": "0.0.1", "configurations": []}' > "$FINTO/skills/pannello/modello/launch.json"
D2="$BASE/cartella-finta-$ORA"
python3 "$FINTO/skills/inizia/scripts/crea-cartella.py" "$D2" > "$BASE/uscita-finta-$ORA.txt" 2>&1 || fallisce "la creazione col plugin finto esce con errore"
grep -q '^avviso' "$BASE/uscita-finta-$ORA.txt" && fallisce "col plugin finto completo ci sono avvisi"
for p in .agents/script/corsa.py .agents/script/controlla-grafo.py .agents/script/yaml_ridotto.py \
         .agents/hooks/controlla-periodo.py .agents/hooks/ferma.py .agents/script/pannello.py; do
  [ -f "$D2/$p" ] || fallisce "col plugin finto manca $p"
  [ "$(head -1 "$D2/$p")" = '#!/usr/bin/env python3' ] || fallisce "$p ha perso la prima riga #!"
  sed -n 2p "$D2/$p" | grep -q 'redacy 9.9.9 · copiato da skills/' || fallisce "$p non porta versione e origine nelle prime righe"
  python3 "$D2/$p" | grep -q finto || fallisce "$p copiato non gira più"
done
for p in .agents/hooks/todo.schema.json .agents/hooks/idee.schema.json; do
  python3 -c "import json,sys; d=json.load(open(sys.argv[1])); assert d['\$comment'].startswith('redacy 9.9.9 · copiato da skills/pianifica-periodo/scripts/'); assert d['type']=='object'" "$D2/$p" || fallisce "$p non porta versione e origine nel \$comment"
done
[ "$(head -1 "$D2/.agents/script/pagina.html")" = '<!doctype html>' ] || fallisce "pagina.html ha perso il doctype in prima riga"
sed -n 2p "$D2/.agents/script/pagina.html" | grep -q '^<!-- redacy 9.9.9 · copiato da skills/pannello/scripts/pagina.html' || fallisce "pagina.html non porta versione e origine dopo il doctype"
cmp -s "$D2/.claude/launch.json" "$FINTO/skills/pannello/modello/launch.json" || fallisce ".claude/launch.json non è la copia esatta del modello del pannello"
python3 "$FINTO/skills/inizia/scripts/crea-cartella.py" "$D2" --controlla > /dev/null 2>&1 || fallisce "--controlla sulla cartella del plugin finto non è pulito"

# 10. Cartelle protette (come la sandbox di Codex): fa il resto, esce 3, stampa la riga per finire
P="$BASE/protetta-$ORA"; mkdir -p "$P/.agents" "$P/.codex"; chmod 555 "$P/.agents" "$P/.codex"
python3 "$SCRIPT" "$P" > "$BASE/uscita-protetta-$ORA.txt" 2>&1; U=$?
chmod 755 "$P/.agents" "$P/.codex"
[ "$U" = 3 ] || fallisce "con .agents/ e .codex/ protette lo script esce $U, non 3"
grep -q '^non scritto: .agents/' "$BASE/uscita-protetta-$ORA.txt" || fallisce "con .agents/ protetta non dice cosa non ha scritto"
[ -f "$P/memoria/INDICE.md" ] && [ -f "$P/periodo/todo.json" ] && [ -f "$P/AGENTS.md" ] || fallisce "con .agents/ protetta non ha creato il resto"
grep -q 'da finire con una riga nel terminale' "$P/memoria/LOG.md" || fallisce "la riga di LOG.md non dice che la cartella è da finire"
CMD=$(sed -n 's/^comando: //p' "$BASE/uscita-protetta-$ORA.txt")
[ -n "$CMD" ] || fallisce "con .agents/ protetta non stampa la riga comando:"
bash -c "$CMD" > "$BASE/uscita-ripresa-$ORA.txt" 2>&1 || fallisce "la riga stampata non finisce la cartella"
python3 "$SCRIPT" "$P" --controlla > /dev/null 2>&1 || fallisce "dopo la riga stampata --controlla non è pulito"

# 11. Ciò che c'era già (--innesta) e le copie vecchie (--aggiorna): una riga ok/NO per controllo
python3 -I "$RADICE/prove/inizia/_innesta.py" "$RADICE" "$BASE/innesta-$ORA" > "$BASE/uscita-innesta-$ORA.txt" 2>&1 \
  || { grep -v '^ok' "$BASE/uscita-innesta-$ORA.txt" | head -5; fallisce "_innesta.py: vedi sopra"; }

# 12. crea-workspace.py: i percorsi dei dati scritti dal punto di vista del workspace
python3 -I "$RADICE/prove/inizia/_workspace.py" "$RADICE" "$BASE/workspace-$ORA" > "$BASE/uscita-workspace-$ORA.txt" 2>&1 \
  || { grep -v '^ok' "$BASE/uscita-workspace-$ORA.txt" | head -5; fallisce "_workspace.py: vedi sopra"; }

echo "cartella di prova: $D"
echo "PASSA"
