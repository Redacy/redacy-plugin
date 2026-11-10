# redacy 0.4.2 · prove/grafi/_comune.sh
#
# Codice comune di prova-crea-claude.sh e prova-crea-codex.sh: non si lancia,
# si carica con "source". Chi lo carica definisce la funzione
#   lancia_agente <cartella> <prompt> <file di trascrizione>
# che lancia l'agente nella cartella e ne restituisce il codice d'uscita
# (i controlli sul risultato girano comunque, qualunque sia).
# Poi chiama: prova_grafi <claude|codex>
#
# La prova crea una cartella di studio finta sotto $PROVE_BASE, chiede all'agente
# un workspace per un lavoro NUOVO e un grafo per un lavoro RIPETUTO, e controlla
# l'albero con gli script del plugin. Finisce con una riga: PASSA o FALLISCE <perché>.

AQUI_COMUNE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RADICE="$(cd "$AQUI_COMUNE/../.." && pwd)"
SCRIPTS_GRAFO="$RADICE/skills/crea-grafo/scripts"
SCRIPTS_WS="$RADICE/skills/crea-workspace/scripts"
CREA_CARTELLA="$RADICE/skills/inizia/scripts/crea-cartella.py"
PROVE_BASE="${REDACY_PROVE_BASE:-${TMPDIR:-/tmp}/redacy-plugin-prove/B}"
TEMPO_MAX=600
export PYTHONDONTWRITEBYTECODE=1

# Il prompt: tutte le risposte sono qui, l'agente non deve chiedere niente.
PROMPT_PROVA="$(cat <<'EOF'
Lavori nella cartella dello studio di un'officina meccanica finta (dati inventati). Non fare domande a nessuno: ti do io tutte le risposte. Fai due lavori, in quest'ordine.

1) LAVORO NUOVO. L'utente vuole un agente che prepari i preventivi di riparazione dell'officina. Usa la skill crea-workspace. Le risposte sono queste. Cosa fa: prepara il preventivo di una riparazione a partire dalla richiesta del cliente e dai listini. Dati: i listini stanno in fonti/listini/ e restano lì. Regole del mestiere: un preventivo è sempre una bozza e non si invia mai al cliente; ricambi e manodopera vanno su righe separate; l'IVA è al 22%; sopra 2.000 euro il preventivo lo approva l'utente. Nome: preventivi-officina. Alla fine lancia controlla-workspace.py e correggi finché esce 0.

2) LAVORO RIPETUTO. L'utente vuole che ogni lunedì alle 8 si prepari il riepilogo degli ordini aperti. Usa la skill crea-grafo. Le risposte sono queste. Nome: riepilogo-ordini-aperti. Parte ogni lunedì alle 08:00, fuso Europe/Rome. Passi: prima un passo agente (workspace orchestratore) legge gli ordini aperti in fonti/ordini/ e ne ricava l'elenco; poi un passo agente (workspace orchestratore) scrive il riepilogo di una pagina; poi un passo umano, forma lettura, dove il pannello: l'utente legge il riepilogo. Produce: un riepilogo di una pagina. Autonomia: il livello di partenza, senza cambiarlo. Alla fine lancia controlla-grafo.py e correggi finché esce 0.

Non inviare niente a nessuno. Per gli script usa solo python3. Quando hai finito scrivi in due righe cosa hai creato.
EOF
)"

aiuto_prova() {
  # $1 = claude|codex, $2 = nome dello script
  echo "Uso: bash prove/grafi/$2"
  echo "Prova che $1 sappia creare un workspace (lavoro nuovo) e un grafo (lavoro ripetuto)"
  echo "con le skill crea-workspace e crea-grafo, in una cartella di studio finta sotto"
  echo "$PROVE_BASE/crea-$1-XXXX. Conserva la trascrizione in _trascrizione.txt dentro quella cartella."
  echo "Chiama il modello una volta (timeout ${TEMPO_MAX} secondi). Ultima riga: PASSA oppure FALLISCE <perché>."
}

# Il comando per limitare il tempo: timeout (Linux) o gtimeout (macOS con coreutils).
imposta_timeout() {
  TIMEOUT=()
  if command -v timeout >/dev/null 2>&1; then
    TIMEOUT=(timeout "$TEMPO_MAX")
  elif command -v gtimeout >/dev/null 2>&1; then
    TIMEOUT=(gtimeout "$TEMPO_MAX")
  fi
}

# Completa a mano ciò che crea-cartella.py non ha creato (o tutto, se non c'è).
prepara_cartella() {
  local T="$1"
  if [ -f "$CREA_CARTELLA" ]; then
    python3 -I "$CREA_CARTELLA" "$T" --plugin "$RADICE" >"$T.crea-cartella.txt" 2>&1 \
      || echo "avviso: crea-cartella.py è uscito con errore, completo a mano ($T.crea-cartella.txt)"
  fi
  mkdir -p "$T/.agents/skills" "$T/.agents/regole" "$T/.agents/policy" "$T/.agents/hooks" \
    "$T/.agents/script" "$T/memoria" "$T/fonti/listini" "$T/fonti/ordini" "$T/periodo" \
    "$T/grafi/corse" "$T/workspace"
  if [ ! -s "$T/AGENTS.md" ]; then
    cat >"$T/AGENTS.md" <<'EOF'
# Studio di prova

Cartella di prova con dati inventati: un'officina meccanica finta.

## Come lavori

- Leggi `memoria/INDICE.md` a inizio lavoro.
- Un lavoro nuovo, mai fatto prima, si affida a un workspace: usa la skill crea-workspace.
- Un lavoro che si ripete uguale diventa un grafo in `grafi/`: usa la skill crea-grafo.
- Il materiale ricevuto sta in `fonti/` e non si modifica.
- Niente invii e niente soldi senza l'utente.
- Scrivi in italiano, dai del tu.
EOF
  fi
  [ -s "$T/CLAUDE.md" ] || printf '@AGENTS.md\n' >"$T/CLAUDE.md"
  if [ ! -s "$T/memoria/INDICE.md" ]; then
    printf '# Indice\n\nUna riga per pagina.\n\n## Lo studio\n\nNessuna pagina ancora.\n' >"$T/memoria/INDICE.md"
  fi
  if [ ! -s "$T/memoria/LOG.md" ]; then
    printf '# Registro\n\nUna riga per fatto, in fondo, mai riscritta.\n\n' >"$T/memoria/LOG.md"
  fi
  # i tre script di crea-grafo, come li copia inizia
  local f
  for f in corsa.py controlla-grafo.py yaml_ridotto.py; do
    [ -f "$T/.agents/script/$f" ] || cp "$SCRIPTS_GRAFO/$f" "$T/.agents/script/$f"
  done
  # dati inventati
  [ -f "$T/fonti/listini/listino-2026.csv" ] || cat >"$T/fonti/listini/listino-2026.csv" <<'EOF'
codice,descrizione,prezzo_euro
RIC-001,Kit frizione,185.00
RIC-002,Pastiglie freno anteriori,64.50
RIC-003,Filtro olio,12.00
MAN-001,Manodopera oraria,48.00
EOF
  [ -f "$T/fonti/ordini/ordini-aperti.csv" ] || cat >"$T/fonti/ordini/ordini-aperti.csv" <<'EOF'
cliente,veicolo,lavoro,importo_euro,consegna
Cliente A,Panda 2019,Sostituzione frizione,420.00,2026-11-10
Cliente B,Golf 2017,Freni anteriori,260.00,2026-11-12
Cliente C,Ducato 2020,Tagliando,310.00,2026-11-09
EOF
}

# Prova il risultato. Mette in $FALLITI i motivi (separati da "; ").
FALLITI=""
segna() { FALLITI="${FALLITI}${FALLITI:+; }$1"; }

controlla_risultato() {
  local T="$1" d nome n_ws=0 n_gr=0 f esito controllo

  for d in "$T"/workspace/*/; do
    [ -d "$d" ] || continue
    d="${d%/}"
    nome="$(basename "$d")"
    n_ws=$((n_ws + 1))
    esito="$(python3 -I "$SCRIPTS_WS/controlla-workspace.py" "$d" 2>&1)"
    if [ $? -ne 0 ]; then
      segna "controlla-workspace su $nome esce 1 ($(echo "$esito" | grep '^errore' | head -1))"
    fi
    if ! grep -qF "[[$nome]]" "$T/memoria/INDICE.md" 2>/dev/null; then
      segna "memoria/INDICE.md dello studio non ha il collegamento [[$nome]]"
    fi
  done
  [ "$n_ws" -ge 1 ] || segna "nessun workspace in workspace/"

  controllo="$T/.agents/script/controlla-grafo.py"
  [ -f "$controllo" ] || controllo="$SCRIPTS_GRAFO/controlla-grafo.py"
  for f in "$T"/grafi/*.yaml; do
    [ -f "$f" ] || continue
    n_gr=$((n_gr + 1))
    esito="$(python3 -I "$controllo" "$f" 2>&1)"
    if [ $? -ne 0 ]; then
      segna "controlla-grafo su $(basename "$f") esce 1 ($(echo "$esito" | grep -v '^avviso' | head -1))"
    fi
    grep -qE '^ *livello: *L0' "$f" || segna "$(basename "$f") non è a livello L0"
    grep -qE '^acceso: *false' "$f" || segna "$(basename "$f") non è spento (acceso: false)"
  done
  [ "$n_gr" -ge 1 ] || segna "nessun grafi/*.yaml"

  grep -qE '^- [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} · workspace · ' "$T/memoria/LOG.md" 2>/dev/null \
    || segna "memoria/LOG.md non ha la riga di tipo workspace"
  grep -qE '^- [0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2} · grafo · ' "$T/memoria/LOG.md" 2>/dev/null \
    || segna "memoria/LOG.md non ha la riga di tipo grafo"
}

prova_grafi() {
  local agente="$1" T uscita_agente
  command -v python3 >/dev/null 2>&1 || { echo "FALLISCE manca python3"; return 1; }
  command -v "$agente" >/dev/null 2>&1 || { echo "FALLISCE manca il comando $agente"; return 1; }
  for f in "$SCRIPTS_WS/crea-workspace.py" "$SCRIPTS_WS/controlla-workspace.py" "$SCRIPTS_GRAFO/controlla-grafo.py"; do
    [ -f "$f" ] || { echo "FALLISCE manca $f"; return 1; }
  done
  [ -d "$RADICE/skills/crea-workspace/modello" ] || { echo "FALLISCE manca il modello di crea-workspace"; return 1; }
  mkdir -p "$PROVE_BASE" || { echo "FALLISCE non riesco a creare $PROVE_BASE"; return 1; }
  T="$(mktemp -d "$PROVE_BASE/crea-$agente-XXXX")" || { echo "FALLISCE mktemp"; return 1; }
  imposta_timeout
  prepara_cartella "$T"
  echo "cartella di prova: $T"

  lancia_agente "$T" "$PROMPT_PROVA" "$T/_trascrizione.txt"
  uscita_agente=$?
  echo "$agente è uscito con $uscita_agente (trascrizione: $T/_trascrizione.txt)"
  [ "$uscita_agente" -eq 124 ] && segna "$agente ha superato i ${TEMPO_MAX} secondi"

  controlla_risultato "$T"
  if [ -n "$FALLITI" ]; then
    echo "FALLISCE $FALLITI"
    return 1
  fi
  echo "PASSA"
  return 0
}
