#!/usr/bin/env bash
# prova-onboarding-codex.sh · redacy 0.4.2
# L'onboarding di `inizia` su Codex, da terminale, in una cartella vuota, coi dati finti di uno
# studio di commercialista inventato (dati-finti.sh). Installa il plugin da questa copia del
# repo, lancia un solo `codex exec` (le risposte e i sì dell'utente nel primo messaggio), poi
# toglie il plugin, lancia la riga che inizia dà all'utente per finire la cartella e accendere il
# pannello (nella sandbox .agents/ e .codex/ sono chiuse e la porta non si apre) e controlla.
# Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/inizia/prova-onboarding-codex.sh
#   REDACY_PROVE=<cartella>   dove mettere le cartelle di prova (se no una temporanea)
#   CODEX_LOCK=<file>         il lucchetto per ~/.codex (default: quello delle prove della box, se c'è)
#   SENZA_PANNELLO=1          non controlla il pannello (solo finché la skill pannello non c'è)
#
# Cosa tocca fuori dalla cartella di prova: ~/.codex/config.toml (marketplace e plugin `redacy`,
# aggiunti e poi tolti), con una copia di prima accanto al lucchetto. Mai ~/.codex/auth.json.
set -u

RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
QUI="$RADICE/prove/inizia"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
G="$BASE/onboarding-codex-$ORA"
DATI="$G/dati-studio"
STUDIO="$G/studio-fabbri-moretti"
LOCK="${CODEX_LOCK:-${TMPDIR:-/tmp}/redacy-plugin-prove/.codex.lock}"; mkdir -p "$(dirname "$LOCK")"
[ -d "$(dirname "$LOCK")" ] || LOCK="$G/.codex.lock"
fallisce() { echo "FALLISCE $*"; exit 1; }

command -v codex >/dev/null || fallisce "manca codex"
command -v flock >/dev/null || fallisce "manca flock"
mkdir -p "$G" "$STUDIO"
bash "$QUI/dati-finti.sh" "$DATI" > /dev/null || fallisce "dati finti non scritti"
python3 "$QUI/controlla-onboarding.py" --plugin "$RADICE" --studio "$STUDIO" --dati "$DATI" \
  --impronta "$G/impronta-dati.txt" --scrivi-impronta || fallisce "impronta dei dati non scritta"

PROMPT="Usa la skill redacy:inizia del plugin redacy.

Questa è una prova automatica: nessuno può rispondere alle tue domande, quindi ti do subito tutte le risposte e tutti i sì.
- Prepara lo studio in questa cartella.
- Lo studio: Studio Fabbri e Moretti, commercialisti a Bologna. Siamo in due: Laura Fabbri segue i clienti e scrive loro, Paolo Moretti controlla e firma le dichiarazioni.
- Il lavoro che voglio affidare a un agente AI: preparare le dichiarazioni dei redditi dei clienti, cioè aprire la pratica, controllare che ci siano tutti i documenti e prepararmi l'elenco di cosa manca.
- Dove stanno i dati e le procedure: la procedura è in \`$DATI/Procedure/procedura-dichiarazioni.md\`; le pratiche dei clienti sono in \`$DATI/Pratiche 2026/\`, una cartella per cliente; le scadenze sono nel foglio \`$DATI/Scadenze 2026.csv\`; la posta dello studio è su Gmail e non è collegata.
- Una regola: le mail ai clienti le manda solo Laura; l'agente prepara le bozze e basta.
- A tutte le conferme rispondo sì: crea la cartella, la memoria, l'elenco delle fonti, un'area di lavoro per le dichiarazioni, e apri il pannello.
Alla fine spiegami cosa hai creato, dove lo vedo e cosa succede adesso."

echo "cartella di prova: $G"
export RADICE STUDIO G PROMPT ORA
flock "$LOCK" bash -c '
  set -u
  COPIA="$(dirname "$0")/_codex-config-$ORA.toml"
  [ -f "$HOME/.codex/config.toml" ] && cp "$HOME/.codex/config.toml" "$COPIA"
  codex plugin marketplace add "$RADICE" > "$G/codex-installa.txt" 2>&1 || exit 11
  codex plugin add redacy@redacy >> "$G/codex-installa.txt" 2>&1 || exit 12
  timeout 600 codex exec --skip-git-repo-check -C "$STUDIO" -s workspace-write \
    --json --output-last-message "$G/finale.txt" "$PROMPT" < /dev/null > "$G/codex.jsonl" 2> "$G/codex.err"
  U=$?
  codex plugin remove redacy@redacy >> "$G/codex-installa.txt" 2>&1
  codex plugin marketplace remove redacy >> "$G/codex-installa.txt" 2>&1
  exit $U
' "$LOCK"
USCITA=$?
case "$USCITA" in
  0) ;;
  11|12) fallisce "installazione del plugin in Codex non riuscita (vedi $G/codex-installa.txt)" ;;
  *) fallisce "codex exec esce $USCITA (vedi $G/codex.err)" ;;
esac
grep -c '"type":"item.completed"' "$G/codex.jsonl" | sed 's/^/eventi completati: /'

# Il gesto dell'utente: nella sandbox di Codex .agents/ e .codex/ sono in sola lettura e la porta
# del pannello non si apre, quindi inizia gli dà una riga da lanciare una volta nel terminale:
# finisce la cartella e accende il pannello. La prova la lancia al suo posto, con lo script di
# questa copia del plugin (la copia installata in Codex è già stata tolta).
{ python3 "$RADICE/skills/inizia/scripts/crea-cartella.py" "$STUDIO" && cd "$STUDIO" && python3 .agents/script/pannello.py; } > "$G/riga-utente.txt" 2>&1
echo "riga dell'utente: esce $? (vedi $G/riga-utente.txt)"
cd "$RADICE" || exit 1

# Una misura, non una condizione: quanti sottoagenti ha lanciato Codex (eventi collab_tool_call)
echo "nota: chiamate ai sottoagenti di Codex (collab_tool_call): $(grep -o '"type":"collab_tool_call"' "$G/codex.jsonl" | wc -l)"

ARG=()
[ -n "${SENZA_PANNELLO:-}" ] && ARG+=(--senza-pannello)
python3 "$QUI/controlla-onboarding.py" --plugin "$RADICE" --studio "$STUDIO" --dati "$DATI" \
  --impronta "$G/impronta-dati.txt" --finale "$G/finale.txt" --harness codex "${ARG[@]}" | tee "$G/controlli.txt"
ESITO=${PIPESTATUS[0]}

PID=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('pid',''))" "$STUDIO/interfaccia/pannello.json" 2>/dev/null)
[ -n "$PID" ] && kill "$PID" 2>/dev/null
exit "$ESITO"
