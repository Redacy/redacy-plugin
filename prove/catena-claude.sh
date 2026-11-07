#!/usr/bin/env bash
# catena-claude.sh · redacy 0.3.1
# La catena intera su Claude Code, da terminale, in una cartella vuota:
#   inizia -> crea-workspace -> crea-grafo -> corsa -> pannello -> stop
# Ogni anello è controllato sui file (albero, workspace valido, grafo che passa controlla-grafo.py,
# corsa scritta, pannello che risponde 200, corsa «fermata» dopo lo stop, con i due livelli dello stop).
# Dati finti: uno studio di commercialista e un'officina, inventati. Nessun dato vero.
#
# Chiama `claude -p --model sonnet` 5 volte (inizia 1, crea-workspace e crea-grafo 1, stop 2 conversazioni:
# in tutto circa 15 minuti e 1,5 dollari). Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/catena-claude.sh
#   REDACY_PROVE=<cartella>     dove mettere la cartella della catena (se no una temporanea)
#   CATENA_G=<cartella> CATENA_DA=<n>   riparte dall'anello n (3 = crea-workspace/crea-grafo, 4 = corsa, 5 = pannello, 6 = stop)
set -u
RADICE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
HARNESS=claude
if [ -n "${CATENA_G:-}" ]; then G="$CATENA_G"; else G="$BASE/catena-claude-$(date +%Y%m%d-%H%M%S)-$$"; fi
mkdir -p "$G"
# shellcheck source=_catena.sh
source "$RADICE/prove/_catena.sh"
# shellcheck source=grafi/_comune.sh
source "$RADICE/prove/grafi/_comune.sh"
command -v claude >/dev/null || fallisce "manca claude"
command -v curl >/dev/null || fallisce "manca curl"
imposta_timeout

# 1. inizia, con la prova di A (cartella vuota, dati finti di uno studio, un solo claude -p con le risposte)
if da_anello 1; then
  anello 1 "inizia (prove/inizia/prova-onboarding-claude.sh)"
  mkdir -p "$G/inizia"
  REDACY_PROVE="$G/inizia" bash "$RADICE/prove/inizia/prova-onboarding-claude.sh" > "$G/inizia.txt" 2>&1
  tail -1 "$G/inizia.txt" | grep -q '^PASSA' || fallisce "la prova di inizia non passa: $(tail -3 "$G/inizia.txt" | tr '\n' ' ')"
  STUDIO="$(ls -d "$G"/inizia/onboarding-claude-*/studio-fabbri-moretti | head -1)"
  echo "$STUDIO" > "$G/studio.txt"
  fatto "inizia: $(grep -c '^ *ok' "$G/inizia.txt" | tr -d ' ') controlli di A passati (cartella, memoria, fonti, workspace, pannello)"
fi
STUDIO="${STUDIO:-$(cat "$G/studio.txt" 2>/dev/null)}"
[ -d "${STUDIO:-/nonesiste}" ] || fallisce "non trovo la cartella dello studio (CATENA_G sbagliata?)"
python3 "$PANNELLO" --cartella "$STUDIO" --spegni >/dev/null 2>&1
controlla_albero

# 2-3. crea-workspace e crea-grafo, col prompt e i controlli di prove/grafi/_comune.sh
if da_anello 3; then
  anello 3 "crea-workspace e crea-grafo (prompt e controlli di prove/grafi/_comune.sh)"
  prepara_cartella "$STUDIO"
  ( cd "$STUDIO" && printf '%s' "$PROMPT_PROVA" | "${TIMEOUT[@]}" claude -p --plugin-dir "$RADICE" --model sonnet \
      --permission-mode acceptEdits --add-dir "$RADICE" \
      --allowedTools "Bash(python3:*),Bash(ls:*),Skill,Read,Write,Edit,Glob,Grep" ) > "$G/crea.txt" 2>&1
  echo "claude è uscito con $? (trascrizione: $G/crea.txt)"
  controlla_workspace_e_grafo
fi

if da_anello 4; then anello 4 "corsa"; fai_corsa; fi
anello 5 "pannello"
GRAFO="${GRAFO:-$(ls "$STUDIO"/grafi/*.yaml | head -1 | xargs -n1 basename | sed 's/\.yaml$//')}"
[ -f "$G/passi.txt" ] || { fai_corsa; }
CORSA_ID="${CORSA_ID:-$(ls -1 "$STUDIO"/grafi/corse/*.json | head -1 | xargs -n1 basename | sed 's/\.json$//')}"
accendi_pannello
anello 6 "stop (livello 1 senza modello, poi due conversazioni su Claude con l'hook)"
stop_livello_1
stop_conversazioni claude
fine_catena
