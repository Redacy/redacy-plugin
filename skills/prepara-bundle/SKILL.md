---
name: prepara-bundle
description: Prepara la checklist di fonti, permessi e chiavi e un manifesto con impronte dei file, per consegnare i dati dello studio a una macchina gestita. Non installa nulla e non contatta nessuno.
---

# Prepara il bundle

Obiettivo: sapere con precisione cosa si consegna, da dove, con quali permessi.

## Passi

1. Chiedi la cartella radice dei dati dello studio.
2. Chiedi le fonti: cartelle condivise, cloud, posta, gestionale. Una riga per fonte: nome, dove sta, chi la gestisce.
3. Per ogni fonte chiedi il permesso necessario: sola lettura o lettura e scrittura, e chi lo concede.
4. Per le chiavi e gli accessi scrivi solo il nome e chi li custodisce. Non chiedere mai il valore. Non leggere file di segreti.
5. Scrivi `bundle/CHECKLIST.md` con tre tabelle: fonti, permessi, chiavi. Aggiungi una colonna "Stato" (da fare, fatto).
6. Genera il manifesto `bundle/MANIFESTO.md`: una tabella con percorso relativo, byte, sha256. Usa `find` e `sha256sum` in sola lettura, con percorsi relativi alla radice.
7. Mostra il totale: numero di file, byte, file esclusi.
8. Chiedi di rivedere la checklist. Segna cosa manca.

## Regole

- Percorsi sempre relativi. Niente nomi di utenti o di macchine.
- Escludi file di sistema, temporanei e segreti. Elencali come esclusi.
- Non copiare, non inviare, non installare. Il bundle è solo un elenco.
- Se un file è molto grande o riservato, segnalalo e chiedi.
