#!/usr/bin/env bash
# redacy 0.4.1 · prove/ordina/prova-inventario.sh
# Prova inventario.py su una cartella finta: conti, tipi, date, nomi, doppioni, cartelle vuote,
# file grandi, nomi che Windows rifiuta, tetto di file, niente scritto, niente traceback.
# Una riga per controllo, in fondo PASSA oppure FALLISCE <perché>.
# Cartelle di prova: $REDACY_PROVE (default ${TMPDIR:-/tmp}/redacy-plugin-prove). Nessun dato vero.
set -u
export PYTHONDONTWRITEBYTECODE=1
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
INV="$RADICE/skills/ordina-dati/scripts/inventario.py"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove}/ordina-inventario-$$"
rm -rf "$BASE"; mkdir -p "$BASE"
D="$BASE/Pratiche"
FUORI="$BASE/fuori"
ERRORI=()
controllo() { # controllo "descrizione" comando...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $desc"; else echo "NO    $desc"; ERRORI+=("$desc"); fi
}
impronte() { # ogni voce con tipo, dimensione, data e impronta del contenuto
  python3 -c 'import hashlib,os,sys
r=sys.argv[1]
for b,ds,fs in os.walk(r):
    ds.sort()
    for n in sorted(ds+fs):
        p=os.path.join(b,n); s=os.lstat(p)
        h=hashlib.sha256(open(p,"rb").read()).hexdigest() if os.path.isfile(p) and not os.path.islink(p) else "-"
        print(os.path.relpath(p,r), s.st_mode, s.st_size, int(s.st_mtime), h)' "$1"
}

[ -f "$INV" ] || { echo "FALLISCE manca $INV"; exit 1; }

# ---- la cartella finta
python3 - "$D" "$FUORI" <<'PY'
import os, sys, time
d, fuori = sys.argv[1], sys.argv[2]
def f(rel, testo, anno=None):
    p = os.path.join(d, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as h:
        h.write(testo.encode("utf-8") if isinstance(testo, str) else testo)
    if anno:
        t = time.mktime((anno, 3, 2, 12, 0, 0, 0, 0, -1))
        os.utime(p, (t, t))
f("Clienti/Rossi Srl/2024-03-01 DVR Rossi Srl.pdf", "dvr rossi", 2019)
f("Clienti/Rossi Srl/20240415 fonometria Rossi Srl.pdf", "fonometria rossi")
f("Clienti/Rossi Srl/Copia di 2024-03-01 DVR Rossi Srl.pdf", "dvr rossi")          # doppione e copia
f("Clienti/Bianchi/01.02.2023 relazione Bianchi.docx", "relazione bianchi")
f("Clienti/Bianchi/relazione Bianchi (1).docx", "relazione bianchi")             # doppione e copia
f("Clienti/Bianchi/stessa misura A.txt", "aaaa")                                 # stessa misura, non doppione
f("Clienti/Bianchi/stessa misura B.txt", "bbbb")
f("Clienti/Caffè Sant'Anna/verbale dell'ispezione è pronto.pdf", "verbale")
f("Archivio/2021/a/b/profondo.xlsx", "foglio", 2021)
f("Archivio/2021/Rossi: preventivo?.pdf", "preventivo")                          # caratteri che Windows rifiuta
f("Archivio/CON.txt", "riservato")
f("Archivio/finisce col punto.", "punto")
f("Archivio/~$bozza.docx", "temporaneo")
f("Archivio/" + "n" * 230 + ".pdf", "lungo")
f("sciolto.jpg", b"\xff\xd8\xff")
f(".git/config", "nascosto")
f("Clienti/.nascosta/segreto.pdf", "nascosto")
os.makedirs(os.path.join(d, "Vuota"), exist_ok=True)
os.makedirs(os.path.join(d, "Archivio", "vuota anche questa"), exist_ok=True)
with open(os.path.join(d, "Archivio", "grande.zip"), "wb") as h:
    h.truncate(150 * 1024 * 1024)
os.makedirs(fuori, exist_ok=True)
with open(os.path.join(fuori, "fuori.pdf"), "w") as h:
    h.write("non si conta")
os.symlink(fuori, os.path.join(d, "collegamento"))
PY
PRIMA="$(impronte "$D")"

# ---- l'inventario in JSON
OUT="$BASE/inventario.json"
python3 "$INV" "$D" > "$OUT" 2> "$BASE/err.txt"; RC=$?
controllo "esce 0 su una cartella buona" test "$RC" = 0
J() { python3 -c 'import json,sys; i=json.load(open(sys.argv[1])); sys.exit(0 if eval(sys.argv[2]) else 1)' "$OUT" "$1"; }
controllo "conta 16 file (niente nascosti, niente oltre il collegamento)" J 'i["file"] == 16'
controllo "conta 10 cartelle" J 'i["cartelle"] == 10'
controllo "profondità 5" J 'i["profondita"] == 5'
controllo "i tipi: 6 pdf" J '{t["estensione"]: t["file"] for t in i["tipi"]}[".pdf"] == 6'
controllo "la data più vecchia è del 2019" J 'i["date"]["piu_vecchia"]["data"].startswith("2019-03-02")'
controllo "conta per anno" J 'i["date"]["per_anno"]["2021"] == 1'
controllo "trova la data AAAA-MM-GG all'inizio" J 'any(s["schema"] == "data AAAA-MM-GG all'"'"'inizio" for s in i["nomi"]["schemi"])'
controllo "trova la data AAAAMMGG" J 'any(s["schema"].startswith("data AAAAMMGG") for s in i["nomi"]["schemi"])'
controllo "trova la data GG-MM-AAAA" J 'any(s["schema"].startswith("data GG-MM-AAAA") for s in i["nomi"]["schemi"])'
controllo "trova il nome della cartella nel nome del file" J 'any(s["schema"] == "il nome della cartella che lo contiene" for s in i["nomi"]["schemi"])'
controllo "doppioni: due gruppi, due file in più" J 'len(i["doppioni"]["gruppi"]) == 2 and i["doppioni"]["file_in_piu"] == 2'
controllo "doppioni: il DVR e la sua copia" J '["Clienti/Rossi Srl/2024-03-01 DVR Rossi Srl.pdf", "Clienti/Rossi Srl/Copia di 2024-03-01 DVR Rossi Srl.pdf"] in [g["file"] for g in i["doppioni"]["gruppi"]]'
controllo "doppioni: la stessa misura non basta" J 'not any("Clienti/Bianchi/stessa misura A.txt" in g["file"] for g in i["doppioni"]["gruppi"])'
controllo "cartelle vuote: due" J 'sorted(i["cartelle_vuote"]) == ["Archivio/vuota anche questa", "Vuota"]'
controllo "file grandi: lo zip da 150 MB" J '[f["file"] for f in i["file_grandi"]] == ["Archivio/grande.zip"]'
P() { python3 -c 'import json,sys; i=json.load(open(sys.argv[1])); m={p["file"]: " ".join(p["problemi"]) for p in i["nomi_problematici"]}; sys.exit(0 if sys.argv[3] in m.get(sys.argv[2], "") else 1)' "$OUT" "$1" "$2"; }
controllo "nome con : e ? segnato" P "Archivio/2021/Rossi: preventivo?.pdf" "caratteri che Windows rifiuta"
controllo "CON.txt segnato come riservato" P "Archivio/CON.txt" "riservato"
controllo "punto in fondo segnato" P "Archivio/finisce col punto." "finisce con uno spazio o un punto"
controllo "~\$ di Office segnato" P 'Archivio/~$bozza.docx' "temporaneo di Office"
controllo "«Copia di» segnato" P "Clienti/Rossi Srl/Copia di 2024-03-01 DVR Rossi Srl.pdf" "copia"
controllo "« (1)» segnato" P "Clienti/Bianchi/relazione Bianchi (1).docx" "copia"
controllo "percorso troppo lungo segnato" P "Archivio/$(printf 'n%.0s' $(seq 230)).pdf" "percorso di"
controllo "accenti e apostrofi non sono un problema" J 'not any("Sant" in p["file"] for p in i["nomi_problematici"])'
controllo "il collegamento non è seguito ma contato" J 'i["saltati"].get("collegamenti (non seguiti)") == 1'
controllo "le voci nascoste sono saltate" J 'i["saltati"].get("nascosti o di sistema") == 2'
controllo "completo, senza avvisi di tetto" J 'i["completo"] is True'

# ---- il riassunto in italiano
python3 "$INV" "$D" --testo > "$BASE/testo.txt" 2>&1
controllo "--testo dice i file" grep -q '^File: 16 in 10 cartelle, fino a 5 livelli' "$BASE/testo.txt"
controllo "--testo dice i doppioni senza cancellare" grep -q '^Doppioni: 2 gruppi.*Non ho cancellato niente' "$BASE/testo.txt"
controllo "--testo dice i nomi da sistemare" grep -q '^Nomi da sistemare: ' "$BASE/testo.txt"

# ---- il tetto di file
python3 "$INV" "$D" --massimo 5 > "$BASE/tetto.json" 2>&1
controllo "con --massimo 5 guarda 5 file e lo dice" python3 -c 'import json,sys; i=json.load(open(sys.argv[1])); sys.exit(0 if i["file"]==5 and not i["completo"] and "primi 5" in " ".join(i["avvisi"]) else 1)' "$BASE/tetto.json"
python3 "$INV" "$D" --tetto-doppioni-mb 1 --elenco > "$BASE/elenco.json" 2>&1
controllo "--elenco porta tutti i file" python3 -c 'import json,sys; i=json.load(open(sys.argv[1])); sys.exit(0 if len(i["elenco"])==16 else 1)' "$BASE/elenco.json"

# ---- niente scritto, niente traceback
controllo "la cartella è identica a prima (date comprese)" test "$PRIMA" = "$(impronte "$D")"
python3 "$INV" "$BASE/non-ce" > "$BASE/nonce.txt" 2>&1; RC=$?
controllo "una cartella che non c'è: esce 2 e lo dice in italiano" bash -c '[ "$1" = 2 ] && grep -q "non c.è" "$2"' _ "$RC" "$BASE/nonce.txt"
python3 "$INV" "$D/sciolto.jpg" > "$BASE/file.txt" 2>&1; RC=$?
controllo "un file al posto della cartella: esce 2" test "$RC" = 2
python3 "$INV" "$D" --massimo zero > "$BASE/uso.txt" 2>&1; RC=$?
controllo "un'opzione sbagliata: esce 1" test "$RC" = 1
controllo "nessun traceback in nessuna uscita" bash -c '! grep -l Traceback "$1"/*.txt "$1"/*.json'  _ "$BASE"

if [ "${#ERRORI[@]}" -eq 0 ]; then
  rm -rf "$BASE"
  echo "PASSA"
  exit 0
fi
echo "(cartella di prova lasciata: $BASE)"
echo "FALLISCE ${ERRORI[0]}$([ "${#ERRORI[@]}" -gt 1 ] && echo " (e altri $(( ${#ERRORI[@]} - 1 )))")"
exit 1
