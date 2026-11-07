#!/usr/bin/env bash
# prova-onboarding-claude.sh · redacy 0.3.1
# L'onboarding di `inizia` su Claude Code, da terminale, in una cartella vuota, coi dati finti
# di uno studio di commercialista inventato (dati-finti.sh). Un solo `claude -p`: le risposte
# dell'utente e i suoi sì stanno tutti nel primo messaggio (una prova automatica non risponde).
# Poi controlla-onboarding.py controlla la cartella. Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/inizia/prova-onboarding-claude.sh
#   REDACY_PROVE=<cartella>   dove mettere le cartelle di prova (se no una temporanea)
#   MODELLO=sonnet            il modello della prova
#   SENZA_PANNELLO=1          non controlla il pannello (solo finché la skill pannello non c'è)
set -u

RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
QUI="$RADICE/prove/inizia"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
G="$BASE/onboarding-claude-$ORA"
DATI="$G/dati-studio"
STUDIO="$G/studio-fabbri-moretti"
fallisce() { echo "FALLISCE $*"; exit 1; }

command -v claude >/dev/null || fallisce "manca claude"
mkdir -p "$G" "$STUDIO"
bash "$QUI/dati-finti.sh" "$DATI" > /dev/null || fallisce "dati finti non scritti"
python3 "$QUI/controlla-onboarding.py" --plugin "$RADICE" --studio "$STUDIO" --dati "$DATI" \
  --impronta "$G/impronta-dati.txt" --scrivi-impronta || fallisce "impronta dei dati non scritta"

PROMPT="Usa la skill inizia del plugin redacy (/redacy:inizia).

Questa è una prova automatica: nessuno può rispondere alle tue domande, quindi ti do subito tutte le risposte e tutti i sì.
- Prepara lo studio in questa cartella.
- Lo studio: Studio Fabbri e Moretti, commercialisti a Bologna. Siamo in due: Laura Fabbri segue i clienti e scrive loro, Paolo Moretti controlla e firma le dichiarazioni.
- Il lavoro che voglio affidare a un agente AI: preparare le dichiarazioni dei redditi dei clienti, cioè aprire la pratica, controllare che ci siano tutti i documenti e prepararmi l'elenco di cosa manca.
- Dove stanno i dati e le procedure: la procedura è in \`$DATI/Procedure/procedura-dichiarazioni.md\`; le pratiche dei clienti sono in \`$DATI/Pratiche 2026/\`, una cartella per cliente; le scadenze sono nel foglio \`$DATI/Scadenze 2026.csv\`; la posta dello studio è su Gmail e non è collegata.
- Una regola: le mail ai clienti le manda solo Laura; l'agente prepara le bozze e basta.
- A tutte le conferme rispondo sì: crea la cartella, la memoria, l'elenco delle fonti, un'area di lavoro per le dichiarazioni, e apri il pannello.
Alla fine spiegami cosa hai creato, dove lo vedo e cosa succede adesso."

echo "cartella di prova: $G"
( cd "$STUDIO" && timeout 600 claude -p --plugin-dir "$RADICE" --model "${MODELLO:-sonnet}" \
    --add-dir "$DATI" --permission-mode acceptEdits \
    --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Task,Agent,Skill" \
    --output-format stream-json --verbose "$PROMPT" ) > "$G/claude.jsonl" 2> "$G/claude.err"
USCITA=$?
[ "$USCITA" = 0 ] || fallisce "claude -p esce $USCITA (vedi $G/claude.err)"
# Una sessione può chiudere più di una risposta (lavori in sfondo che tornano dopo): si tengono
# tutte, nell'ordine, e il messaggio finale da controllare è la loro somma.
python3 - "$G/claude.jsonl" "$G/finale.txt" <<'EOF2' || fallisce "uscita di claude -p non leggibile"
import json, sys
risposte, costo, turni, sessione = [], 0.0, 0, None
for riga in open(sys.argv[1], encoding="utf-8"):
    try:
        e = json.loads(riga)
    except ValueError:
        continue
    if e.get("type") == "result":
        risposte.append(e.get("result") or "")
        costo = max(costo, e.get("total_cost_usd") or 0)  # cumulativo nella sessione
        turni += e.get("num_turns") or 0
        sessione = e.get("session_id")
if not risposte:
    sys.exit(1)
open(sys.argv[2], "w", encoding="utf-8").write("\n\n".join(risposte))
print(f"sessione: {sessione} · risposte finali: {len(risposte)} · turni: {turni} · costo USD: {costo:.2f}")
EOF2

# Una misura, non una condizione: quanti sottoagenti mappa-fonte ha lanciato la mappatura
N=$(python3 -c "
import json, sys
ids = set()
for riga in open(sys.argv[1], encoding='utf-8'):
    try:
        e = json.loads(riga)
    except ValueError:
        continue
    if e.get('type') == 'assistant':
        for b in e['message'].get('content', []):
            if b.get('type') == 'tool_use' and (b.get('input') or {}).get('subagent_type') == 'redacy:mappa-fonte':
                ids.add(b['id'])
print(len(ids))" "$G/claude.jsonl")
echo "nota: sottoagenti redacy:mappa-fonte lanciati: $N"

ARG=()
[ -n "${SENZA_PANNELLO:-}" ] && ARG+=(--senza-pannello)
python3 "$QUI/controlla-onboarding.py" --plugin "$RADICE" --studio "$STUDIO" --dati "$DATI" \
  --impronta "$G/impronta-dati.txt" --finale "$G/finale.txt" --harness claude "${ARG[@]}" | tee "$G/controlli.txt"
ESITO=${PIPESTATUS[0]}

# Il pannello acceso dalla prova si spegne
PID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('pid',''))" "$STUDIO/interfaccia/pannello.json" 2>/dev/null)
[ -n "$PID" ] && kill "$PID" 2>/dev/null
exit "$ESITO"
