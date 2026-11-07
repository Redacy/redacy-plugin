#!/usr/bin/env bash
# tutte.sh · redacy 0.3.0
# Lancia tutte le prove che non chiamano nessun modello, una riga per prova, e in fondo
#   ESITO: PASSA     oppure     ESITO: FALLISCE <le prove che non passano>
# Non serve un account Claude o Codex. Serve Python 3, bash e curl. Dura un paio di minuti.
#
# Uso: bash prove/tutte.sh
#   REDACY_PROVE=<cartella>   dove mettere le cartelle di prova (se no una temporanea, tolta alla fine)
#   VERBOSO=1                 mostra anche l'uscita completa di ogni prova
#
# Le prove con un modello (catena e onboarding) sono a parte: prove/catena-claude.sh,
# prove/catena-codex.sh, prove/inizia/prova-onboarding-*.sh, prove/grafi/prova-crea-*.sh.
set -u
RADICE="$(cd "$(dirname "$0")/.." && pwd)"
if [ -n "${REDACY_PROVE:-}" ]; then BASE="$REDACY_PROVE"; TOGLI=""; else BASE="$(mktemp -d)"; TOGLI="$BASE"; fi
mkdir -p "$BASE"
export REDACY_PROVE="$BASE" REDACY_PROVE_BASE="$BASE" PROVE="$BASE" PYTHONDONTWRITEBYTECODE=1
for c in python3 curl; do
  command -v "$c" >/dev/null 2>&1 || { echo "ESITO: FALLISCE manca $c"; exit 1; }
done
FALLITE=""
N=0

prova() { # <nome> <comando...>
  local nome="$1"; shift
  local out="$BASE/uscita-$N.txt"; N=$((N + 1))
  local da; da=$(date +%s)
  "$@" > "$out" 2>&1
  local rc=$? t=$(( $(date +%s) - da ))
  local ultima; ultima="$(grep -v '^[[:space:]]*$' "$out" | tail -1)"
  if [ "$rc" -eq 0 ] && [[ "$ultima" == PASSA* || "$ultima" == *"Validation passed"* || "$ultima" == ok* ]]; then
    printf 'PASSA      %-46s %3ss\n' "$nome" "$t"
  else
    printf 'FALLISCE   %-46s %3ss  %s\n' "$nome" "$t" "${ultima:-nessuna uscita}"
    FALLITE="${FALLITE}${FALLITE:+, }$nome"
    [ -n "${VERBOSO:-}" ] || sed 's/^/             | /' "$out" | tail -8
  fi
  [ -z "${VERBOSO:-}" ] || sed 's/^/             | /' "$out"
}

# --- controlli di coerenza del pacchetto (nessuno script a parte) ---
coerenza() {
  cd "$RADICE" || { echo "FALLISCE non trovo $RADICE"; return 1; }
  python3 -I - <<'PY' || return 1
import json, sys
versioni = {}
for f, chiave in [(".claude-plugin/plugin.json", None), (".codex-plugin/plugin.json", None)]:
    versioni[f] = json.load(open(f, encoding="utf-8"))["version"]
mc = json.load(open(".claude-plugin/marketplace.json", encoding="utf-8"))
versioni[".claude-plugin/marketplace.json"] = mc["plugins"][0].get("version")
mx = json.load(open(".agents/plugins/marketplace.json", encoding="utf-8"))
versioni[".agents/plugins/marketplace.json"] = mx["plugins"][0].get("version")
if len(set(versioni.values())) != 1:
    print("FALLISCE le versioni non coincidono:", versioni); sys.exit(1)
cx = json.load(open(".codex-plugin/plugin.json", encoding="utf-8"))
if "interface" in cx:
    print("FALLISCE in .codex-plugin/plugin.json interface è in cima: va sotto extensions.com.openai"); sys.exit(1)
if "displayName" not in cx.get("extensions", {}).get("com.openai", {}).get("interface", {}):
    print("FALLISCE manca extensions.com.openai.interface.displayName"); sys.exit(1)
print("versione", list(versioni.values())[0], "nei quattro file; interface sotto extensions.com.openai")
PY
  # ogni skill ha SKILL.md con name uguale alla cartella
  local d n
  for d in skills/*/; do
    n="$(basename "$d")"
    [ -f "$d/SKILL.md" ] || { echo "FALLISCE $n non ha SKILL.md"; return 1; }
    grep -q "^name: $n\$" "$d/SKILL.md" || { echo "FALLISCE il name di $n non coincide con la cartella"; return 1; }
  done
  echo "$(ls -d skills/*/ | wc -l | tr -d ' ') skill, ognuna con SKILL.md e name giusto"
  # nessun nome di skill tolta, nessuna versione vecchia (la prova stessa è esclusa)
  local vecchi
  vecchi="$(grep -rnE "chiedi-allo-studio|parcheggia-idea|prepara-bundle|impara-lo-studio|0\.2\.0" . \
            --exclude-dir=.git --exclude-dir=__pycache__ --exclude=tutte.sh -I || true)"
  [ -z "$vecchi" ] || { echo "FALLISCE nomi tolti o versione vecchia ancora presenti:"; echo "$vecchi" | head -5; return 1; }
  echo "nessun nome tolto, nessuna versione 0.2.0"
  echo "ok"
}

# --- le copie nella cartella portano la versione del manifesto ---
copie_con_versione() {
  local T="$BASE/copie-versione/studio"
  mkdir -p "$T"
  python3 -I "$RADICE/skills/inizia/scripts/crea-cartella.py" "$T" --plugin "$RADICE" >/dev/null 2>&1 \
    || { echo "FALLISCE crea-cartella.py esce con errore"; return 1; }
  local v f n=0 manca=0
  v="$(python3 -I -c "import json;print(json.load(open('$RADICE/.claude-plugin/plugin.json'))['version'])")"
  for f in "$T"/.agents/script/*.py "$T"/.agents/hooks/*.py; do
    [ -f "$f" ] || continue
    n=$((n + 1))
    head -5 "$f" | grep -q "redacy $v" || { echo "senza «redacy $v» in testa: ${f#$T/}"; manca=$((manca + 1)); }
  done
  [ "$n" -gt 0 ] || { echo "FALLISCE nessuna copia trovata in .agents/"; return 1; }
  [ "$manca" -eq 0 ] || { echo "FALLISCE $manca copie su $n senza la versione"; return 1; }
  echo "$n copie in .agents/ con «redacy $v» in testa"
  echo "ok"
}

validate() {
  if ! command -v claude >/dev/null 2>&1; then echo "ok claude non c'è: validazione saltata"; return 0; fi
  claude plugin validate "$RADICE" 2>&1 | tee /dev/stderr | grep -q "Validation passed" && echo "Validation passed"
}

prova "coerenza dei manifesti e delle skill" coerenza
prova "le copie nella cartella portano la versione" copie_con_versione
prova "claude plugin validate" validate
prova "grafi: il controllo" bash "$RADICE/prove/grafi/prova-controllo.sh"
prova "grafi: le corse e lo stop" bash "$RADICE/prove/grafi/prova-corsa.sh"
prova "periodo: gli schemi e il controllo" bash "$RADICE/prove/periodo/prova-schemi.sh"
prova "inizia: la cartella" bash "$RADICE/prove/inizia/prova-cartella.sh"
prova "pannello: il server e lo stop" bash "$RADICE/prove/pannello/prova-server.sh"

[ -z "$TOGLI" ] || rm -rf "$TOGLI"
if [ -z "$FALLITE" ]; then echo "ESITO: PASSA"; exit 0; fi
echo "ESITO: FALLISCE $FALLITE"; exit 1
