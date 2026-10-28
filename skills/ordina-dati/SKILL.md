---
name: ordina-dati
description: Mette in ordine i documenti dello studio in cartelle chiare con un indice leggibile. Usala quando l'utente vuole riordinare cartelle di lavoro o cloud sincronizzati. Sposta i file solo dopo un sì.
---

# Ordina i dati dello studio

Obiettivo: cartelle chiare e un indice che un collega capisce in un minuto.

## Passi

1. Chiedi quale cartella ordinare. Lavora solo lì.
2. Elenca il contenuto in sola lettura. Non aprire file riservati più del necessario.
3. Proponi una struttura semplice, al massimo tre livelli. Esempio:
   - `01-clienti/<cliente>/<anno>/`
   - `02-modelli/`
   - `03-interno/`
   - `99-da-smistare/`
4. Mostra una tabella: file attuale, destinazione, motivo. Una riga per file.
5. Aspetta un sì esplicito. Se l'utente corregge, aggiorna la tabella e chiedi di nuovo.
6. Dopo il sì, sposta i file. Non cancellare nulla. Non sovrascrivere: se il nome esiste, aggiungi un suffisso.
7. Scrivi `INDICE.md` nella radice: una riga per cartella, cosa contiene e chi la usa.
8. Chiudi con un riepilogo: file spostati, file lasciati in `99-da-smistare/`, dubbi aperti.

## Regole

- Mai spostare senza conferma.
- Mai uscire dalla cartella scelta.
- Nomi file in minuscolo, con data ISO (2026-10-28) quando serve.
- Frasi corte nell'indice. Niente gergo.
