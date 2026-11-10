#!/usr/bin/env bash
# catena-codex.sh · redacy 0.4.0
# La catena intera su Codex, da terminale, in una cartella vuota:
#   inizia -> crea-workspace -> crea-grafo -> corsa -> pannello -> stop
# Come catena-claude.sh, con le differenze che Codex impone (misurate, vedi README):
#   - nella sandbox di default .agents/ e .codex/ sono in sola lettura e la porta locale è negata:
#     inizia dà all'utente UNA riga da lanciare nel terminale (finisce la cartella e accende il pannello);
#     la lancia lo script di prova, come farebbe l'utente (lo fa prove/inizia/prova-onboarding-codex.sh);
#   - lo stop è provato al livello 1 (corsa.py esce con 3 dopo lo stop). Lo STADIO 2, l'hook ferma.py,
#     parte solo dopo che l'utente approva gli hook con /hooks: è un gesto dell'utente, non di questo
#     script (due righe a mano in testa a prove/pannello/prova-stop-codex.sh).
#
# Installa il plugin in ~/.codex da questa copia del repo, sotto flock, e lo toglie alla fine; prima
# copia ~/.codex/config.toml accanto al lucchetto. Mai ~/.codex/auth.json.
# Chiama `codex exec` 4 volte (inizia 1, crea-workspace e crea-grafo 1, stop 2). Finisce con PASSA o FALLISCE <perché>.
#
# Uso: bash prove/catena-codex.sh
#   REDACY_PROVE=<cartella>     dove mettere la cartella della catena (se no una temporanea)
#   CODEX_LOCK=<file>           il lucchetto per ~/.codex
#   CATENA_G=<cartella> CATENA_DA=<n>   riparte dall'anello n (come catena-claude.sh)
set -u
RADICE="$(cd "$(dirname "$0")/.." && pwd)"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
HARNESS=codex
LOCK="${CODEX_LOCK:-${TMPDIR:-/tmp}/redacy-plugin-prove/.codex.lock}"; mkdir -p "$(dirname "$LOCK")"
[ -d "$(dirname "$LOCK")" ] || LOCK="$BASE/.codex.lock"
if [ -n "${CATENA_G:-}" ]; then G="$CATENA_G"; else G="$BASE/catena-codex-$(date +%Y%m%d-%H%M%S)-$$"; fi
mkdir -p "$G"
# shellcheck source=_catena.sh
source "$RADICE/prove/_catena.sh"
# shellcheck source=grafi/_comune.sh
source "$RADICE/prove/grafi/_comune.sh"
command -v codex >/dev/null || fallisce "manca codex"
command -v curl >/dev/null || fallisce "manca curl"
imposta_timeout

# 1. inizia, con la prova di A (installa e toglie il plugin da sé, sotto lo stesso lucchetto)
if da_anello 1; then
  anello 1 "inizia (prove/inizia/prova-onboarding-codex.sh: la riga per il terminale la lancia lo script)"
  mkdir -p "$G/inizia"
  REDACY_PROVE="$G/inizia" CODEX_LOCK="$LOCK" bash "$RADICE/prove/inizia/prova-onboarding-codex.sh" > "$G/inizia.txt" 2>&1
  tail -1 "$G/inizia.txt" | grep -q '^PASSA' || fallisce "la prova di inizia non passa: $(tail -3 "$G/inizia.txt" | tr '\n' ' ')"
  STUDIO="$(ls -d "$G"/inizia/onboarding-codex-*/studio-fabbri-moretti | head -1)"
  echo "$STUDIO" > "$G/studio.txt"
  fatto "inizia su Codex: i controlli di A passati; cartella finita e pannello acceso dalla riga per il terminale"
fi
STUDIO="${STUDIO:-$(cat "$G/studio.txt" 2>/dev/null)}"
[ -d "${STUDIO:-/nonesiste}" ] || fallisce "non trovo la cartella dello studio (CATENA_G sbagliata?)"
python3 "$PANNELLO" --cartella "$STUDIO" --spegni >/dev/null 2>&1
controlla_albero

# Da qui Codex lavora col plugin installato dal worktree: il lucchetto sta preso finché lo script vive
if command -v flock >/dev/null 2>&1; then exec 9>"$LOCK"; flock 9; fi
COPIA="$(dirname "$LOCK")/_codex-config-catena-$(date +%Y%m%d-%H%M%S).toml"
[ -f "$HOME/.codex/config.toml" ] && cp "$HOME/.codex/config.toml" "$COPIA"
toglie_plugin() { codex plugin remove redacy@redacy >/dev/null 2>&1; codex plugin marketplace remove redacy >/dev/null 2>&1; }
trap toglie_plugin EXIT
codex plugin marketplace add "$RADICE" > "$G/installa.txt" 2>&1 || fallisce "codex plugin marketplace add: $(tail -2 "$G/installa.txt")"
codex plugin add redacy@redacy >> "$G/installa.txt" 2>&1 || fallisce "codex plugin add: $(tail -2 "$G/installa.txt")"
codex plugin list --json > "$G/plugin-list.json" 2>&1
grep -q '"redacy@redacy"\|redacy@redacy' "$G/plugin-list.json" || fallisce "codex plugin list non mostra redacy@redacy"
echo "plugin installato dal worktree: $(grep -o 'redacy@redacy[^,]*' "$G/plugin-list.json" | head -1)"
V="$(python3 -I -c "import json;print(json.load(open('$RADICE/.codex-plugin/plugin.json'))['version'])")"
[ -f "$HOME/.codex/plugins/cache/redacy/redacy/$V/.codex-plugin/plugin.json" ] || fallisce "la copia installata (versione $V) non c'è in ~/.codex/plugins/cache/redacy/redacy/"

# 3. crea-workspace e crea-grafo, col prompt e i controlli di prove/grafi/_comune.sh
if da_anello 3; then
  anello 3 "crea-workspace e crea-grafo (prompt e controlli di prove/grafi/_comune.sh)"
  prepara_cartella "$STUDIO"
  "${TIMEOUT[@]}" codex exec --skip-git-repo-check -C "$STUDIO" -s workspace-write \
    -c "projects={\"$STUDIO\"={trust_level=\"trusted\"}}" "$PROMPT_PROVA" < /dev/null > "$G/crea.txt" 2>&1
  echo "codex è uscito con $? (trascrizione: $G/crea.txt)"
  controlla_workspace_e_grafo
fi

if da_anello 4; then anello 4 "corsa"; fai_corsa; fi
anello 5 "pannello (acceso da terminale: dentro la sandbox di Codex la porta non si apre)"
GRAFO="${GRAFO:-$(ls "$STUDIO"/grafi/*.yaml | head -1 | xargs -n1 basename | sed 's/\.yaml$//')}"
[ -f "$G/passi.txt" ] || { fai_corsa; }
CORSA_ID="${CORSA_ID:-$(ls -1 "$STUDIO"/grafi/corse/*.json | head -1 | xargs -n1 basename | sed 's/\.json$//')}"
accendi_pannello
anello 6 "stop (livello 1 senza modello, poi due conversazioni su Codex, livello 1)"
stop_livello_1
stop_conversazioni codex
fine_catena
