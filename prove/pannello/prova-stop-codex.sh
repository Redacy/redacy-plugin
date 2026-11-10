#!/usr/bin/env bash
# prova-stop-codex.sh · redacy 0.4.0
# Lo stop dal pannello con Codex, due conversazioni (`codex exec`) nella stessa cartella dello studio.
#
# STADIO 1 (default, parte da solo): lo stop senza hook. Gli hook di Codex partono solo dopo che
#   l'utente li approva con /hooks, quindi qui conta il livello 1: corsa.py esce con 3 al comando
#   dopo lo stop e la conversazione si ferma. La corsa dell'altra conversazione non è toccata.
#   Usa 2 chiamate a `codex exec` (budget D: 3).
#
# STADIO 2 (l'hook ferma.py dopo il /hooks dell'utente): due righe a mano, una volta sola.
#   1) bash prove/pannello/prova-stop-codex.sh 2 prepara     crea la cartella di prova e dice dove andare
#   2) cd <la cartella che stampa> && codex      poi nell'interfaccia scrivi /hooks, approva i tre hook, esci
#   Poi:  bash prove/pannello/prova-stop-codex.sh 2          lancia la prova e vuole il marcatore dell'hook
#   (L'approvazione vale per hash: se cambia .codex/hooks.json va rifatta. Il flag di bypass non si usa.)
#
# Finisce con PASSA o FALLISCE <perché>.
# Uso: bash prove/pannello/prova-stop-codex.sh [1|2 [prepara]]
set -u
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove/D}"
STADIO="${1:-1}"
ORA="$(date +%Y%m%d-%H%M%S)-$$"
LAVORO="$BASE/stop-codex-$ORA"
# shellcheck source=_stop.sh
source "$(dirname "$0")/_stop.sh"
command -v codex >/dev/null || { echo "FALLISCE manca codex"; exit 1; }
command -v curl >/dev/null || { echo "FALLISCE manca curl"; exit 1; }

if [ "$STADIO" = "2" ]; then
  D="$BASE/codex-hook/studio"
  if [ "${2:-}" = "prepara" ]; then
    if [ -d "$D" ]; then echo "La cartella c'è già: $D (l'approvazione degli hook vale per quella)."; else
      mkdir -p "$BASE/codex-hook"; prepara_cartella "$D" si; echo "Cartella creata: $D"; fi
    echo "Adesso: cd $D && codex   poi scrivi /hooks, approva gli hook, esci. Poi: bash $0 2"
    exit 0
  fi
  [ -d "$D" ] || { echo "FALLISCE manca la cartella di prova: lancia prima  bash $0 2 prepara"; exit 1; }
  rm -rf "$D/grafi/corse" && mkdir -p "$D/grafi/corse"; HOOK=si
else
  mkdir -p "$LAVORO"; D="$LAVORO/studio"; prepara_cartella "$D" si; HOOK=ignora
fi
python3 "$PANNELLO" --cartella "$D" > "$LAVORO.pannello.txt" 2>&1 || fallisce "il pannello non parte: $(cat "$LAVORO.pannello.txt")"
mkdir -p "$LAVORO"

mkdir -p "${TMPDIR:-/tmp}/redacy-plugin-prove"; exec 9>"${TMPDIR:-/tmp}/redacy-plugin-prove/.codex.lock"; flock 9
CODEX=(codex exec --skip-git-repo-check -C "$D" -s workspace-write --json -c "projects={\"$D\"={trust_level=\"trusted\"}}")
( timeout 600 "${CODEX[@]}" "$(prompt_conversazione A giro-lento CODEX_THREAD_ID)" < /dev/null > "$LAVORO/A.jsonl" 2> "$LAVORO/A.err" ) &
pa=$!
( timeout 600 "${CODEX[@]}" "$(prompt_conversazione B giro-altro CODEX_THREAD_ID)" < /dev/null > "$LAVORO/B.jsonl" 2> "$LAVORO/B.err" ) &
pb=$!
aspetta_e_ferma "$D" 420
wait "$pa" "$pb"
for c in A B; do
  echo "$c: $(python3 - "$LAVORO/$c.jsonl" <<'PY'
import json, sys
ultimo = ""
for riga in open(sys.argv[1], encoding="utf-8", errors="replace"):
    try:
        e = json.loads(riga)
    except ValueError:
        continue
    it = e.get("item") or {}
    if it.get("type") == "agent_message":
        ultimo = it.get("text", "")
print(ultimo[-300:].replace("\n", " "))
PY
)"
done
controlla "$D" "$HOOK"
python3 "$PANNELLO" --cartella "$D" --spegni > /dev/null 2>&1
[ "$STADIO" = "2" ] && echo "stadio 2: l'hook ha fermato la conversazione A"
echo "PASSA"
