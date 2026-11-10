#!/usr/bin/env bash
# dati-finti.sh · redacy 0.4.0
# Scrive in <cartella> i dati di uno studio di commercialista INVENTATO (nomi, clienti e numeri
# finti): una procedura in markdown, una cartella di pratiche, un foglio .csv delle scadenze.
# La posta non è un file: la prova la nomina nel messaggio («la posta è su Gmail»).
# Uso: bash prove/inizia/dati-finti.sh <cartella>
set -eu
D="${1:?serve la cartella dove scrivere i dati finti}"
mkdir -p "$D/Procedure" "$D/Pratiche 2026"

cat > "$D/Procedure/procedura-dichiarazioni.md" <<'EOF'
# Procedura: la dichiarazione dei redditi di un cliente

Studio Fabbri e Moretti, commercialisti (studio inventato per le prove). Ultima revisione: marzo 2026.

1. Apri la cartella del cliente in `Pratiche 2026/`.
2. Controlla che ci sia il modulo dei documenti ricevuti (`documenti-ricevuti.txt`).
3. Confronta i documenti ricevuti con l'elenco dell'anno prima.
4. Se manca un documento, scrivi al cliente l'elenco di cosa manca. La mail la manda Laura.
5. Segna nel foglio `Scadenze 2026.csv` lo stato «documenti completi».
6. Prepara la bozza della dichiarazione.
7. Fai controllare la bozza a Paolo, che firma.
8. Archivia la ricevuta di invio nella cartella del cliente.

Chi approva: Paolo Moretti. Chi scrive ai clienti: Laura Fabbri.
EOF

cliente() {
  local nome="$1"; shift
  mkdir -p "$D/Pratiche 2026/$nome"
  printf '%s\n' "$@" > "$D/Pratiche 2026/$nome/documenti-ricevuti.txt"
  printf 'Note su %s: cliente dal 2019, preferisce essere sentito per telefono.\n' "$nome" > "$D/Pratiche 2026/$nome/note.md"
}
cliente "Bassi Elena" "CU 2026" "spese mediche" "interessi mutuo"
cliente "Carta Giorgio" "CU 2026" "ricevute affitto"
cliente "Officina Ruggeri snc" "bilancio 2025" "registro IVA" "F24 versati"
cliente "Lodi Marta" "CU 2026"

cat > "$D/Scadenze 2026.csv" <<'EOF'
cliente;adempimento;scadenza;stato
Bassi Elena;dichiarazione dei redditi;2026-09-30;documenti completi
Carta Giorgio;dichiarazione dei redditi;2026-09-30;mancano documenti
Officina Ruggeri snc;bilancio;2026-04-30;fatto
Officina Ruggeri snc;liquidazione IVA;2026-11-16;da fare
Lodi Marta;dichiarazione dei redditi;2026-09-30;mancano documenti
EOF
echo "dati finti in $D"
