---
name: giro-del-giorno
description: Il giro quotidiano sul periodo. Ordina i todo, mostra i primi tre con il motivo, dice cosa aspetta l'utente e cosa è fermo e chi lo sblocca. Si usa quando l'utente dice "cosa c'è oggi", "da dove parto", "cosa devo fare adesso", "giro del giorno", "a che punto siamo", "cosa è in ritardo".
---

# Giro del giorno

Una lettura veloce del periodo, per sapere da dove partire. Non è una pianificazione: l'obiettivo e le idee non si toccano qui.

## Cosa leggi

- `periodo/todo.json`: da qui viene l'ordine.
- `periodo/obiettivo.md`: per capire cosa pesa di più.
- `periodo/idee.json`: non lo usi per decidere l'ordine. Conti solo quante idee senza esito aspettano.

## Passi

1. **Calcola l'ordine.** Una scadenza vicina con un gesto dell'utente davanti pesa più di un todo vecchio. "In ritardo" si calcola: scadenza passata e stato diverso da `fatto`. Fra due voci simili vince quella più vicina all'obiettivo.
2. **Mostra i primi tre**, ciascuno con una riga di motivo. Per esempio: "t2, scade giovedì e il controllo è tuo."
3. **Dì cosa aspetta l'utente.** Le voci con `chi: "tu"` non fatte, e le voci `ferma` che aspettano una sua scelta, con la nota. Nessun elenco di opzioni: la decisione si prende con `pianifica-periodo`.
4. **Dì cosa è fermo e chi lo sblocca.** Per ogni voce `ferma` scrivi di chi è la mossa. Se non lo sai, scrivilo: "non so di chi è la mossa".
5. **Segna ciò che è cambiato**, dicendolo. Se l'utente ti dice che una cosa è fatta, passa la voce a `fatto`. Se è bloccata, passa a `ferma` con una `nota` che dice cosa aspetta. Aggiorna `aggiornato` di ogni voce che tocchi, con la data di oggi.
6. **Una voce nuova solo se l'utente la chiede**, con `da: "giro"`, un id che non riusa mai uno vecchio e `aggiornato` di oggi.

## Come parli con l'utente

Con lui usi le sue parole: "cose da fare" (non todo), "aspetta te", "fermo", "in ritardo". Date come a voce ("giovedì", "ieri"). Il giro è breve: i primi tre, poi cosa aspetta lui, poi cosa è fermo, al più cinque righe per blocco. Niente lodi, niente punti esclamativi.

## Cosa non fai

- Non tocchi `periodo/obiettivo.md` né `periodo/idee.json`.
- Non inventi compiti. Una lista corta non vuol dire niente da fare: può essere lavoro in salute. Dillo.
- Se un'idea ti sembra urgente, non la inserisci. Proponi di rivederla con `pianifica-periodo`.
- Non scegli per l'utente fra due strade. Le descrivi e rimandi a `pianifica-periodo`.

## Uno stato strano

Se una voce ha uno stato che non torna (per esempio `fatto` con una scadenza futura e una nota che parla di un blocco), non correggerla di tuo. Prima leggi `memoria/INDICE.md` e le pagine che c'entrano, poi dì all'utente se ti sembra un guasto oppure una scelta già presa. Se non lo capisci, chiedi.

## Soldi, clienti, atti ufficiali

Se un todo tocca un cliente, dei soldi o un atto ufficiale (un invio, un pagamento, una firma), preparalo: la bozza, il controllo, i numeri. Poi lascialo all'utente e dillo.

## Prima di dire "fatto"

Se hai scritto in `periodo/todo.json`, lancia:

    python3 .agents/hooks/controlla-periodo.py periodo/todo.json

Nel plugin lo script sta in `skills/pianifica-periodo/scripts/`. Se esce 1, correggi e rilancia. Se non hai scritto niente, il controllo non serve.

Se hai segnato qualcosa, aggiungi in fondo a `memoria/LOG.md` una riga, senza riscrivere le altre:

    - 2026-11-07 09:10 · periodo · Giro: t2 fatto, t5 ferma (aspetta il preventivo).
