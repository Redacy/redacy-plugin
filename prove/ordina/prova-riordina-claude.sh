#!/usr/bin/env bash
# prova-riordina-claude.sh · redacy 0.4.2
# La skill `riordina-cartella` su Claude Code, da terminale, con un modello vero, su una cartella
# di pratiche finta e disordinata (uno studio di consulenza sulla sicurezza, inventato).
# Due conversazioni (`claude -p`), nella stessa cartella dello studio:
#   1. «riordina questa cartella»: la struttura e tutti i sì stanno nel primo messaggio;
#   2. «rimetti tutto com'era».
# Si controlla sui file, non sulle parole dell'agente: dopo la prima nessun file perso o cambiato
# (stesse impronte), i file dei clienti sotto Clienti/, i file senza padrone e il doppione fermi,
# piano e registro scritti, memoria aggiornata; dopo la seconda l'albero è identico a quello di partenza.
# Finisce con PASSA o FALLISCE <perché>. Circa 6 minuti e meno di un dollaro.
#
# Uso: bash prove/ordina/prova-riordina-claude.sh
#   REDACY_PROVE=<cartella>   dove mettere le cartelle di prova (se no una temporanea)
#   MODELLO=sonnet            il modello della prova
set -u
export PYTHONDONTWRITEBYTECODE=1
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
BASE="${REDACY_PROVE:-$(mktemp -d)}"
G="$BASE/riordina-claude-$(date +%Y%m%d-%H%M%S)-$$"
STUDIO="$G/studio-galli"
P="$G/dati/Pratiche"
fallisce() { echo "FALLISCE $*"; exit 1; }
ok() { echo "    ok: $*"; }

command -v claude >/dev/null || fallisce "manca claude"
mkdir -p "$G" "$P"
python3 "$RADICE/skills/inizia/scripts/crea-cartella.py" "$STUDIO" --plugin "$RADICE" > "$G/crea.txt" 2>&1 \
  || fallisce "crea-cartella.py: $(tail -2 "$G/crea.txt" | tr '\n' ' ')"

python3 - "$P" <<'PY' || fallisce "pratiche finte non scritte"
import os, sys
d = sys.argv[1]
voci = [
    ("DVR Officina Rossi 2024.pdf", "dvr rossi 2024"),
    ("dvr officina rossi 2025 def.pdf", "dvr rossi 2025"),
    ("Nomina RSPP Officina Rossi 2025.pdf", "nomina rossi 2025"),
    ("Fonometria Bar Sant'Anna marzo 2025.pdf", "fonometria sant'anna 2025"),
    ("fonometria bar sant'anna 2023.pdf", "fonometria sant'anna 2023"),
    ("Fattura 12 2025 Bar Sant'Anna.pdf", "fattura sant'anna 2025"),
    ("Verbale sopralluogo Carrozzeria Bianchi 12-05-2025.docx", "verbale bianchi 2025"),
    ("DVR Carrozzeria Bianchi 2024.pdf", "dvr bianchi 2024"),
    ("Nomina RSPP Carrozzeria Bianchi 2024.pdf", "nomina bianchi 2024"),
    ("Attestato corso antincendio Carrozzeria Bianchi 2025.pdf", "attestato bianchi 2025"),
    ("vecchie/DVR Falegnameria Conti 2022.pdf", "dvr conti 2022"),
    ("vecchie/Fonometria Falegnameria Conti 2022.pdf", "fonometria conti 2022"),
    ("vecchie/relazione Falegnameria Conti 2022 è pronta.docx", "relazione conti 2022"),
    ("da sistemare/Copia di DVR Officina Rossi 2024.pdf", "dvr rossi 2024"),
    ("da sistemare/preventivo Officina Rossi 2025.xlsx", "preventivo rossi 2025"),
    ("da sistemare/Preventivo Carrozzeria Bianchi 2025.xlsx", "preventivo bianchi 2025"),
    ("da sistemare/appunti.txt", "telefonare al fornitore del fonometro"),
    ("scansione0001.pdf", "una scansione senza nome"),
]
for rel, testo in voci:
    p = os.path.join(d, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(testo + "\n")
PY

impronte() { # una riga per file: percorso relativo e impronta del contenuto
  python3 - "$1" <<'PY'
import hashlib, os, sys
r = sys.argv[1]
for b, ds, fs in os.walk(r):
    ds.sort()
    for n in sorted(fs):
        p = os.path.join(b, n)
        print(os.path.relpath(p, r).replace(os.sep, "/") + "\t" + hashlib.sha256(open(p, "rb").read()).hexdigest())
PY
}
impronte "$P" > "$G/prima.txt"

conversa() { # conversa <nome> <prompt>
  # il prompt arriva da stdin: --allowedTools prende più valori e si mangerebbe un prompt messo in coda
  ( cd "$STUDIO" && printf '%s' "$2" | timeout 900 claude -p --plugin-dir "$RADICE" --model "${MODELLO:-sonnet}" \
      --add-dir "$G/dati" --permission-mode acceptEdits \
      --allowedTools "Bash,Read,Write,Edit,Glob,Grep,Skill" ) > "$G/$1.txt" 2> "$G/$1.err"
  local c=$?
  [ "$c" = 0 ] || fallisce "claude -p ($1) esce $c (vedi $G/$1.err)"
}

echo "cartella di prova: $G"
echo "--- 1: riordina"
conversa riordina "Usa la skill riordina-cartella del plugin redacy (/redacy:riordina-cartella).

Questa è una prova automatica: nessuno può rispondere alle tue domande, quindi ti do subito tutte le risposte e tutti i sì.
- Riordina la cartella \`$P\`. Sono le pratiche del mio studio di consulenza sulla sicurezza sul lavoro.
- La struttura che voglio: \`Clienti/<cliente>/<anno>/\`, per esempio \`Clienti/Officina Rossi/2024/\`. I clienti sono Officina Rossi, Bar Sant'Anna, Carrozzeria Bianchi e Falegnameria Conti.
- I nomi dei file lasciali come sono.
- I file che non sai di quale cliente sono restano dove sono. I doppioni restano dove sono.
- Sì alla struttura. Sì al riassunto: sposta i file come nel piano, senza aspettare altre conferme.
Alla fine dimmi in poche righe cosa hai spostato e come torno indietro."

impronte "$P" > "$G/dopo.txt"
python3 - "$G/prima.txt" "$G/dopo.txt" <<'PY' || fallisce "dopo il riordino i file non tornano (vedi sopra)"
import sys
def leggi(f):
    return [r.rstrip("\n").split("\t") for r in open(f, encoding="utf-8") if r.strip()]
prima, dopo = leggi(sys.argv[1]), leggi(sys.argv[2])
guai = []
if sorted(h for _, h in prima) != sorted(h for _, h in dopo):
    guai.append("un file è stato perso, aggiunto o cambiato: %d prima, %d dopo" % (len(prima), len(dopo)))
pd = {p: h for p, h in dopo}
sotto = [p for p in pd if p.startswith("Clienti/")]
if len(sotto) < 12:
    guai.append("solo %d file sotto Clienti/ (ne attendo almeno 12)" % len(sotto))
for cliente in ("Rossi", "Sant'Anna", "Bianchi", "Conti"):
    if not any(cliente.lower() in p.split("/")[1].lower() for p in sotto if p.count("/") >= 2):
        guai.append("nessuna cartella del cliente " + cliente + " sotto Clienti/")
storti = [p for p in sotto if p.count("/") != 3 or not p.split("/")[2].isdigit()]
if storti:
    guai.append("file fuori da Clienti/<cliente>/<anno>/: " + "; ".join(storti[:3]))
for fermo in ("scansione0001.pdf", "da sistemare/appunti.txt", "da sistemare/Copia di DVR Officina Rossi 2024.pdf"):
    if fermo not in pd:
        guai.append("doveva restare dov'era: " + fermo)
if guai:
    print("    NO: " + "\n    NO: ".join(guai)); sys.exit(1)
print("    ok: %d file, nessuno perso o cambiato; %d sotto Clienti/<cliente>/<anno>/; senza padrone e doppione fermi" % (len(dopo), len(sotto)))
PY

PIANO="$(ls "$STUDIO"/periodo/riordini/*/piano.json 2>/dev/null | head -1)"
[ -n "$PIANO" ] || fallisce "nessun piano in periodo/riordini/"
REG="$(dirname "$PIANO")/registro.jsonl"
[ -f "$REG" ] || fallisce "manca il registro accanto al piano"
grep -q '"fine"' "$REG" || fallisce "il registro non arriva alla riga «fine»"
ok "piano e registro in periodo/riordini/$(basename "$(dirname "$PIANO")")/"
grep -qi "pratiche" "$STUDIO/memoria/fonti-dati.md" 2>/dev/null || fallisce "memoria/fonti-dati.md non parla della cartella riordinata"
grep -qi "riordinat" "$STUDIO/memoria/LOG.md" 2>/dev/null || fallisce "memoria/LOG.md non ha la riga del riordino"
ok "memoria/fonti-dati.md e memoria/LOG.md aggiornati"

echo "--- 2: rimetti com'era"
conversa annulla "Usa la skill riordina-cartella del plugin redacy (/redacy:riordina-cartella).

Questa è una prova automatica: nessuno può rispondere. Annulla il riordino della cartella \`$P\`: rimetti tutto com'era. Sì, sono sicuro."

impronte "$P" > "$G/tornato.txt"
cmp -s "$G/prima.txt" "$G/tornato.txt" || fallisce "dopo l'annullo l'albero non è quello di partenza: $(diff "$G/prima.txt" "$G/tornato.txt" | head -4 | cut -f1 | tr '\n' ' ')"
ok "dopo l'annullo ogni file è al suo posto, con lo stesso contenuto"
grep -qi "annullat" "$STUDIO/memoria/LOG.md" 2>/dev/null || fallisce "memoria/LOG.md non ha la riga dell'annullo"
ok "memoria/LOG.md ha la riga dell'annullo"
echo "PASSA"
