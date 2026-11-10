#!/usr/bin/env bash
# redacy 0.4.0 · prove/ordina/prova-riordina.sh
# Prova riordina.py (controlla, applica, annulla) su cartelle finte: piano buono applicato e
# annullato con l'albero identico (per impronta), collisioni, uscite dalla cartella, file cambiato
# dopo il piano, interruzione a metà, nomi con spazi, accenti e apostrofi, fonti/ dello studio.
# Una riga per controllo, in fondo PASSA oppure FALLISCE <perché>.
# Cartelle di prova: $REDACY_PROVE (default ${TMPDIR:-/tmp}/redacy-plugin-prove). Nessun dato vero.
set -u
export PYTHONDONTWRITEBYTECODE=1
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
R="$RADICE/skills/riordina-cartella/scripts/riordina.py"
BASE="${REDACY_PROVE:-${TMPDIR:-/tmp}/redacy-plugin-prove}/ordina-riordina-$$"
rm -rf "$BASE"; mkdir -p "$BASE"
S="$BASE/studio"
ERRORI=()
controllo() { # controllo "descrizione" comando...
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $desc"; else echo "NO    $desc"; ERRORI+=("$desc"); fi
}
uguale() { if [ "$2" = "$3" ]; then echo "ok    $1"; else echo "NO    $1 (atteso '$2', trovato '$3')"; ERRORI+=("$1"); fi; }
impronte() { # ogni voce (cartelle comprese) con l'impronta del contenuto
  python3 -c 'import hashlib,os,sys
r=sys.argv[1]
for b,ds,fs in os.walk(r):
    ds.sort()
    for n in sorted(ds+fs):
        p=os.path.join(b,n)
        h=hashlib.sha256(open(p,"rb").read()).hexdigest() if os.path.isfile(p) else "cartella"
        print(os.path.relpath(p,r), h)' "$1"
}
rr() { # lancia riordina.py, stampa il codice d'uscita; l'uscita resta in $BASE/ultima.txt
  python3 "$R" "$@" > "$BASE/ultima.txt" 2>&1; local c=$?
  cat "$BASE/ultima.txt" >> "$BASE/uscite-tutte.txt"; echo "$c"
}
dice() { grep -qF -- "$1" "$BASE/ultima.txt"; }

[ -f "$R" ] || { echo "FALLISCE manca $R"; exit 1; }
python3 "$RADICE/skills/inizia/scripts/crea-cartella.py" "$S" --plugin "$RADICE" >/dev/null 2>&1 || { echo "FALLISCE crea-cartella.py"; exit 1; }

# una cartella di pratiche disordinata: nomi con spazi, accenti, apostrofi
pratiche() { # pratiche <cartella>
  python3 - "$1" <<'PY'
import os, sys
d = sys.argv[1]
for rel, testo in [
    ("disordine/DVR Rossi 2024.pdf", "dvr rossi"),
    ("disordine/fonometria Caffè Sant'Anna.pdf", "fonometria caffè"),
    ("disordine/vecchie/relazione dell'ingegnere è pronta.docx", "relazione"),
    ("disordine/vecchie/verbale Bianchi.pdf", "verbale"),
    ("Clienti/esistente.pdf", "c'era già"),
    ("sciolto.txt", "sciolto"),
]:
    p = os.path.join(d, *rel.split("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(testo)
PY
}
piano() { # piano <file> <cartella> <righe come JSON> [campi in più come JSON]
  mkdir -p "$(dirname "$1")"
  python3 -c 'import json,sys; p={"versione":1,"cartella":sys.argv[2],"regola":"Clienti/<cliente>/<file>","righe":json.loads(sys.argv[3])}; p.update(json.loads(sys.argv[4])); json.dump(p,open(sys.argv[1],"w",encoding="utf-8"),ensure_ascii=False,indent=1)' "$1" "$2" "$3" "${4:-{\}}"
}
BUONE='[
 {"da":"disordine/DVR Rossi 2024.pdf","a":"Clienti/Rossi/2024/DVR Rossi 2024.pdf","perche":"DVR del cliente Rossi"},
 {"da":"disordine/fonometria Caffè Sant'"'"'Anna.pdf","a":"Clienti/Caffè Sant'"'"'Anna/fonometria Caffè Sant'"'"'Anna.pdf","perche":"fonometria del Caffè"},
 {"da":"disordine/vecchie/relazione dell'"'"'ingegnere è pronta.docx","a":"Clienti/Bianchi/relazione dell'"'"'ingegnere è pronta.docx","perche":"relazione Bianchi"},
 {"da":"disordine/vecchie/verbale Bianchi.pdf","a":"Clienti/Bianchi/2023-05-02 verbale Bianchi.pdf","perche":"verbale, rinominato con la data"},
 {"da":"sciolto.txt","a":"sciolto.txt","perche":"resta dov'\''è"}
]'

# ================================================================ 1. piano buono, applicato e annullato
D="$BASE/uno/Pratiche"; pratiche "$D"
P1="$S/periodo/riordini/2026-11-10-pratiche/piano.json"
piano "$P1" "$D" "$BUONE"
PRIMA="$(impronte "$D")"
uguale "(1) controlla su un piano buono esce 0" 0 "$(rr controlla "$P1")"
controllo "(1) controlla dice quante righe e quante restano" dice "da spostare 4 · restano dove sono 1"
controllo "(1) controlla dà i numeri per cartella d'arrivo" dice "per cartella d'arrivo: Clienti/Bianchi · 2 file"
controllo "(1) controlla dà gli esempi" dice "esempio: riga 1 · disordine/DVR Rossi 2024.pdf → Clienti/Rossi/2024/DVR Rossi 2024.pdf"
controllo "(1) controlla segna dimensione e data nel piano" python3 -c 'import json,sys; p=json.load(open(sys.argv[1])); sys.exit(0 if all("byte" in r and "modificato" in r for r in p["righe"]) else 1)' "$P1"
uguale "(1) controlla non sposta niente" "$PRIMA" "$(impronte "$D")"
uguale "(1) applica esce 0" 0 "$(rr applica "$P1")"
controllo "(1) applica dice 4 spostati" dice "esito: 4 file spostati"
controllo "(1) il DVR è al suo posto" test -f "$D/Clienti/Rossi/2024/DVR Rossi 2024.pdf"
controllo "(1) il nome con accento e apostrofo è arrivato" test -f "$D/Clienti/Caffè Sant'Anna/fonometria Caffè Sant'Anna.pdf"
controllo "(1) il file rinominato è arrivato" test -f "$D/Clienti/Bianchi/2023-05-02 verbale Bianchi.pdf"
controllo "(1) il vecchio posto è vuoto" test ! -e "$D/disordine/DVR Rossi 2024.pdf"
controllo "(1) le cartelle rimaste vuote non si cancellano" test -d "$D/disordine/vecchie"
controllo "(1) il contenuto è lo stesso (stesse impronte, altri posti)" bash -c 'diff <(echo "$1" | awk "{print \$NF}" | grep -v cartella | sort) <(echo "$2" | awk "{print \$NF}" | grep -v cartella | sort)' _ "$PRIMA" "$(impronte "$D")"
REG1="$S/periodo/riordini/2026-11-10-pratiche/registro.jsonl"
controllo "(1) il registro c'è, con 4 mosse fatte" bash -c '[ "$(grep -c "\"evento\": \"spostato\"" "$1")" = 4 ]' _ "$REG1"
uguale "(1) rilanciare applica non rifà niente" 0 "$(rr applica "$P1")"
controllo "(1) e dice 4 già spostati" dice "0 file spostati, 0 lasciati dove sono perché cambiati dopo il piano, 4 già spostati prima"
uguale "(1) annulla esce 0" 0 "$(rr annulla "$REG1")"
controllo "(1) annulla toglie le cartelle che aveva creato" dice "cartelle create dal riordino tolte"
uguale "(1) dopo annulla l'albero è identico a prima (per impronta)" "$PRIMA" "$(impronte "$D")"
controllo "(1) Clienti/ c'era già e resta" test -f "$D/Clienti/esistente.pdf"
uguale "(1) dopo annulla, applica rifiuta" 1 "$(rr applica "$P1")"
uguale "(1) annulla rilanciato non fa danni" 0 "$(rr annulla "$P1")"
uguale "(1) ...e l'albero resta identico" "$PRIMA" "$(impronte "$D")"

# ================================================================ 2. piani che non vanno: niente si muove
D="$BASE/due/Pratiche"; pratiche "$D"; PRIMA="$(impronte "$D")"
mkdir -p "$BASE/due/fuori"; ln -s "$BASE/due/fuori" "$D/collegamento"
PRIMA="$(impronte "$D")"
k=0
rifiuta() { # rifiuta "descrizione" <righe JSON> <frase attesa> [campi in più]
  k=$((k + 1)); local p="$S/periodo/riordini/rotto-$k/piano.json"
  piano "$p" "$D" "$2" "${4:-{\}}"
  uguale "(2) $1: controlla esce 1" 1 "$(rr controlla "$p")"
  controllo "(2) $1: lo dice («$3»)" dice "$3"
  uguale "(2) $1: anche applica esce 1" 1 "$(rr applica "$p")"
}
UNA='"da":"disordine/DVR Rossi 2024.pdf","perche":"prova"'
rifiuta "due destinazioni uguali per maiuscole" '[{"da":"disordine/DVR Rossi 2024.pdf","a":"Clienti/Rossi.pdf","perche":"x"},{"da":"disordine/vecchie/verbale Bianchi.pdf","a":"clienti/ROSSI.pdf","perche":"y"}]' "è anche la destinazione della riga 1"
rifiuta "destinazione che c'è già" "[{$UNA,\"a\":\"Clienti/esistente.pdf\"}]" "c'è già: non sovrascrivo"
rifiuta "destinazione uguale a un file che c'è, per maiuscole" "[{$UNA,\"a\":\"Clienti/ESISTENTE.pdf\"}]" "si scontra con"
rifiuta "cartella con maiuscole diverse da una che c'è" "[{$UNA,\"a\":\"clienti/nuovo.pdf\"}]" "maiuscole diverse"
rifiuta "destinazione con .." "[{$UNA,\"a\":\"../fuori.pdf\"}]" "esce dalla cartella"
rifiuta "destinazione con .. in mezzo" "[{$UNA,\"a\":\"Clienti/../../fuori.pdf\"}]" "esce dalla cartella"
rifiuta "destinazione assoluta" "[{$UNA,\"a\":\"$BASE/due/fuori/x.pdf\"}]" "percorso intero"
rifiuta "destinazione con lettera di disco" "[{$UNA,\"a\":\"C:/Pratiche/x.pdf\"}]" "percorso intero"
rifiuta "destinazione attraverso un collegamento" "[{$UNA,\"a\":\"collegamento/x.pdf\"}]" "porta fuori dalla cartella"
rifiuta "sorgente con .." '[{"da":"../uno/Pratiche/sciolto.txt","a":"x.txt","perche":"x"}]' "esce dalla cartella"
rifiuta "sorgente che non c'è" '[{"da":"non-ce.pdf","a":"x.pdf","perche":"x"}]' "non c'è"
rifiuta "nome con i due punti" "[{$UNA,\"a\":\"Clienti/Rossi: DVR.pdf\"}]" "caratteri che Windows rifiuta"
rifiuta "nome riservato di Windows" "[{$UNA,\"a\":\"Clienti/CON.pdf\"}]" "nome riservato di Windows"
rifiuta "nome che finisce col punto" "[{$UNA,\"a\":\"Clienti/Rossi.\"}]" "finisce con uno spazio o un punto"
LUNGO="$(printf 'cartella-lunga-%.0s' $(seq 12))"
rifiuta "percorso troppo lungo per Windows" "[{$UNA,\"a\":\"$LUNGO/$LUNGO/x.pdf\"}]" "Windows ne regge 259"
rifiuta "riga senza perche" '[{"da":"sciolto.txt","a":"Clienti/sciolto.txt"}]' "manca «perche»"
rifiuta "lo stesso file in due righe" '[{"da":"sciolto.txt","a":"a/sciolto.txt","perche":"x"},{"da":"sciolto.txt","a":"b/sciolto.txt","perche":"y"}]' "un file, una riga"
rifiuta "un file dove un'altra riga vuole una cartella" '[{"da":"sciolto.txt","a":"Nuova/x","perche":"x"},{"da":"disordine/DVR Rossi 2024.pdf","a":"Nuova/x/DVR.pdf","perche":"y"}]' "è anche una cartella"
uguale "(2) dopo tutti i piani rifiutati la cartella è identica" "$PRIMA" "$(impronte "$D")"
# una cartella di sistema, e fonti/ dello studio senza permesso
p="$S/periodo/riordini/sistema/piano.json"; piano "$p" "/etc" '[{"da":"hosts","a":"x/hosts","perche":"x"}]'
uguale "(2) una cartella di sistema: esce 1" 1 "$(rr controlla "$p")"
controllo "(2) una cartella di sistema: lo dice" dice "cartella di sistema"
mkdir -p "$S/fonti/arrivati"; echo "materiale" > "$S/fonti/arrivati/doc.pdf"
p="$S/periodo/riordini/fonti/piano.json"; piano "$p" "$S/fonti" '[{"da":"arrivati/doc.pdf","a":"ordinati/doc.pdf","perche":"x"}]'
uguale "(2) fonti/ senza permesso: esce 1" 1 "$(rr controlla "$p")"
controllo "(2) fonti/ senza permesso: chiede il sì" dice "permesso_fonti"
piano "$p" "$S/fonti" '[{"da":"arrivati/doc.pdf","a":"ordinati/doc.pdf","perche":"x"}]' '{"permesso_fonti":"sì, detto in chat il 2026-11-10"}'
uguale "(2) fonti/ col permesso scritto: controlla esce 0" 0 "$(rr controlla "$p")"
p="$S/periodo/riordini/studio/piano.json"; piano "$p" "$S" '[{"da":"memoria/LOG.md","a":"altro/LOG.md","perche":"x"}]'
uguale "(2) le pagine dello studio non si toccano" 1 "$(rr controlla "$p")"
p="$S/periodo/riordini/senza-controlla/piano.json"; piano "$p" "$D" "[{$UNA,\"a\":\"Clienti/DVR.pdf\"}]"
uguale "(2) applica senza controlla prima: esce 1" 1 "$(rr applica "$p")"
controllo "(2) ...e dice di lanciare controlla" dice "lancia prima controlla"
controllo "(2) ...e non ha spostato niente" test -f "$D/disordine/DVR Rossi 2024.pdf"
echo "{ non json" > "$S/periodo/riordini/rotto-1/piano.json"
uguale "(2) un piano che non è JSON: esce 1" 1 "$(rr controlla "$S/periodo/riordini/rotto-1/piano.json")"
uguale "(2) un piano che non c'è: esce 2" 2 "$(rr controlla "$S/periodo/riordini/nessuno/piano.json")"

# ================================================================ 3. file cambiato dopo il piano
D="$BASE/tre/Pratiche"; pratiche "$D"
P3="$S/periodo/riordini/cambiato/piano.json"; piano "$P3" "$D" "$BUONE"
rr controlla "$P3" >/dev/null
echo " e una riga scritta dopo il piano" >> "$D/disordine/vecchie/verbale Bianchi.pdf"
CAMBIATO="$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$D/disordine/vecchie/verbale Bianchi.pdf")"
uguale "(3) controlla dopo il cambio: avviso, non errore" 0 "$(rr controlla "$P3")"
controllo "(3) ...dice che applica lo lascerà dov'è" dice "è cambiato dopo il piano"
uguale "(3) applica esce 0" 0 "$(rr applica "$P3")"
controllo "(3) applica dice che l'ha lasciato" dice "saltato: riga 4"
controllo "(3) il file cambiato è ancora al suo posto" test -f "$D/disordine/vecchie/verbale Bianchi.pdf"
uguale "(3) ...col contenuto nuovo" "$CAMBIATO" "$(python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$D/disordine/vecchie/verbale Bianchi.pdf")"
controllo "(3) gli altri sono spostati" test -f "$D/Clienti/Bianchi/relazione dell'ingegnere è pronta.docx"

# ================================================================ 4. interruzione a metà, poi annulla
D="$BASE/quattro/Pratiche"; pratiche "$D"; PRIMA="$(impronte "$D")"
P4="$S/periodo/riordini/interrotto/piano.json"; piano "$P4" "$D" "$BUONE"
REG4="$S/periodo/riordini/interrotto/registro.jsonl"
rr controlla "$P4" >/dev/null
chmod 555 "$D/disordine/vecchie"          # la riga 3 non si può spostare: un errore a metà
uguale "(4) applica si ferma al primo errore: esce 3" 3 "$(rr applica "$P4")"
chmod 755 "$D/disordine/vecchie"
controllo "(4) dice l'errore in italiano" dice "errore: riga 3"
controllo "(4) dice cosa ha già fatto" dice "Spostati in questo giro: 2"
controllo "(4) le prime due mosse sono fatte" test -f "$D/Clienti/Rossi/2024/DVR Rossi 2024.pdf"
controllo "(4) la terza no" test -f "$D/disordine/vecchie/relazione dell'ingegnere è pronta.docx"
uguale "(4) annulla dopo l'interruzione esce 0" 0 "$(rr annulla "$REG4")"
uguale "(4) l'albero è identico a prima" "$PRIMA" "$(impronte "$D")"
# un'interruzione brusca: la mossa fatta ma non segnata finita nel registro
D="$BASE/cinque/Pratiche"; pratiche "$D"; PRIMA="$(impronte "$D")"
P5="$S/periodo/riordini/brusco/piano.json"; piano "$P5" "$D" "$BUONE"
REG5="$S/periodo/riordini/brusco/registro.jsonl"
rr controlla "$P5" >/dev/null; rr applica "$P5" >/dev/null
python3 - "$REG5" <<'PY'
import json, sys
p = sys.argv[1]
righe = open(p, encoding="utf-8").read().splitlines()
# si tiene tutto fino alla mossa della riga 3 (cominciata), e mezza riga scritta a metà
tenute = []
for r in righe:
    e = json.loads(r)
    if e.get("evento") == "spostato" and e.get("riga") == 3:
        break
    tenute.append(r)
open(p, "w", encoding="utf-8").write("\n".join(tenute) + '\n{"evento": "sposto", "ri')
PY
# la riga 4 è stata spostata ma il registro non lo sa: la si rimette a mano dov'era
mv "$D/Clienti/Bianchi/2023-05-02 verbale Bianchi.pdf" "$D/disordine/vecchie/verbale Bianchi.pdf"
uguale "(5) annulla dopo un'interruzione brusca esce 0" 0 "$(rr annulla "$REG5")"
uguale "(5) l'albero è identico a prima" "$PRIMA" "$(impronte "$D")"
# ripresa: dopo l'errore si rilancia applica e finisce
D="$BASE/sei/Pratiche"; pratiche "$D"
P6="$S/periodo/riordini/ripresa/piano.json"; piano "$P6" "$D" "$BUONE"
rr controlla "$P6" >/dev/null
chmod 555 "$D/disordine/vecchie"; rr applica "$P6" >/dev/null; chmod 755 "$D/disordine/vecchie"
uguale "(6) rilanciare applica dopo l'errore riprende ed esce 0" 0 "$(rr applica "$P6")"
controllo "(6) ...e fa solo le due che mancavano" dice "esito: 2 file spostati"
# annulla non tocca un file cambiato dopo il riordino
echo "cambiato dopo" >> "$D/Clienti/Bianchi/2023-05-02 verbale Bianchi.pdf"
uguale "(6) annulla esce 0" 0 "$(rr annulla "$S/periodo/riordini/ripresa/registro.jsonl")"
controllo "(6) annulla lascia dov'è il file cambiato dopo il riordino" dice "saltato: riga 4"
controllo "(6) ...che è ancora lì" test -f "$D/Clienti/Bianchi/2023-05-02 verbale Bianchi.pdf"
controllo "(6) ...e la sua cartella, non vuota, resta" dice "non è vuota: la lascio"
controllo "(6) gli altri sono tornati" test -f "$D/disordine/DVR Rossi 2024.pdf"

# ================================================================ niente traceback
controllo "nessun traceback in nessuna uscita" bash -c '! grep -l Traceback "$1"/uscite-tutte.txt' _ "$BASE"
controllo "nessun file temporaneo lasciato" bash -c '[ -z "$(find "$1" -name "*.tmp-*")" ]' _ "$BASE"

if [ "${#ERRORI[@]}" -eq 0 ]; then
  rm -rf "$BASE"
  echo "PASSA"
  exit 0
fi
echo "(cartella di prova lasciata: $BASE)"
echo "FALLISCE ${ERRORI[0]}$([ "${#ERRORI[@]}" -gt 1 ] && echo " (e altri $(( ${#ERRORI[@]} - 1 )))")"
exit 1
