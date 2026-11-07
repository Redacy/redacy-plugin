---
name: pianifica-periodo
description: Costruisce il periodo di lavoro con l'utente. Legge obiettivo, todo e idee, mostra il quadro, pesa le idee arrivate fuori periodo e scrive il piano solo dopo la risposta. Si usa quando l'utente dice "pianifichiamo", "facciamo il piano", "cosa facciamo questo periodo", "rivediamo le idee", "cambiamo l'obiettivo", "ho deciso cosa fare".
---

# Pianifica il periodo

Un periodo buono fa avanzare un obiettivo. Non basta un elenco ordinato. L'obiettivo è dell'utente, non tuo.

Questa è l'unica skill in cui un'idea entra nel periodo. Fuori da qui le idee aspettano in `periodo/idee.json` e nessuno le insegue.

## Prima di cominciare

Leggi, in questo ordine:

- `memoria/INDICE.md`, e le pagine che c'entrano con ciò che trovi sotto.
- `periodo/obiettivo.md`.
- `periodo/todo.json`.
- `periodo/idee.json`.

Non rifare da zero. Porta avanti ciò che non è finito. Se un file è vuoto o manca, dillo e vai avanti col resto.

I campi dei due file sono in `references/campi.md`. Un esempio del prima e del dopo è in `examples/periodo-esempio.md`.

## Passi

1. **Mostra il quadro in breve.** L'obiettivo di oggi e la riga "Fatto quando:". Cosa è avanzato dall'ultima volta (voci `fatto`, per `aggiornato`). Cosa è fermo, e perché (voci `ferma`, con la nota). Cosa è in ritardo: scadenza passata e stato diverso da `fatto`. Quante idee aspettano.
2. **Pesa ogni idea senza esito.** Per ciascuna proponi uno di tre esiti, con una riga di perché: portata nel periodo, rimandata, scartata. Pesa anche le idee rimandate da tempo, se l'utente vuole riguardarle.
3. **Cerca le decisioni ferme.** Una voce `ferma` con nota che aspetta l'utente da oltre 30 giorni (la data è nella nota, "dal AAAA-MM-GG"; se manca, guarda `aggiornato`) si ripropone una volta sola: decidere, parcheggiare (rimandata) o dimenticare (scartata). Chiedi, non scegliere tu.
4. **Chiudi il messaggio con al massimo tre domande, in prosa.** Per ogni domanda scrivi: la domanda, le strade possibili con pro e costo, la tua raccomandazione. Niente elenchi di opzioni da scegliere. Non usare strumenti a scelta multipla.
5. **Fermati e aspetta.** Non scrivere niente prima della risposta. L'utente può rispondere in più messaggi o dettare il periodo: lascialo fare.
6. **Solo dopo la risposta, scrivi.** Segui la sezione sotto.
7. **Controlla i file** e chiudi con la riga di LOG.

## Cosa scrivi, e dove

**`periodo/todo.json`.** Ogni idea portata nel periodo diventa una voce:

- `id` nuovo: il numero più alto mai usato più uno. Non riusare mai un id vecchio, nemmeno di una voce `fatto`.
- `da`: `"piano"`. `aggiornato`: la data di oggi.
- `cosa` comincia con un verbo. `chi` è `tu`, `agente` o il nome di una persona.
- `dove` solo se il lavoro sta in un posto preciso della cartella.

Anche le voci già presenti cambiano se l'utente lo dice: stato, scadenza, chi. Aggiorna `aggiornato` di ogni voce che tocchi.

**`periodo/idee.json`.** A ogni idea pesata aggiungi `esito` con `stato`, `data` (oggi), `perche` e, se è portata nel periodo, `todo` con l'id della nuova voce. Non cancellare mai un'idea.

**`periodo/obiettivo.md`.** Si scrive o si riscrive solo se l'utente lo chiede, con parole sue o dettate. Poche righe di prosa e una riga `Fatto quando:` che si può verificare, senza todo. Se l'obiettivo c'è già e l'utente non ha chiesto di cambiarlo, non lo tocchi. Nemmeno per sistemarlo, accorciarlo o aggiornarlo. Se ti sembra superato, dillo in una domanda e basta.

## Una decisione che aspetta l'utente non è un todo con `chi: "tu"`

Un todo con `chi: "tu"` è un gesto: chiamare, firmare, mandare. Una decisione è un'altra cosa: finché l'utente non sceglie, nessuno può muoversi.

Scrivila come voce `ferma` con una `nota` che dice cosa aspetta e da quando (per esempio "Aspetta la tua scelta fra A e B, dal 2026-11-07"). Così resta visibile, non finisce fra le cose da fare e non si confonde con un gesto. Quando l'utente decide, la voce passa a `da fare` o a `fatto`, oppure se ne scrive una nuova col gesto che ne segue.

## Come parli con l'utente

Con lui usi le sue parole: "cose da fare" (non todo), "idee per dopo" (non idee.json), "l'obiettivo di queste settimane", "aspetta te" per ciò che tocca a lui. Le tre strade di un'idea le dici così: "la porto nelle cose da fare", "la rimando", "la lascio perdere". Le date come a voce ("giovedì", "ieri"), nei file `AAAA-MM-GG`. Niente lodi, niente punti esclamativi, una domanda alla volta.

## Cosa resta all'utente

Soldi, atti legali, invii a clienti. Puoi preparare una bozza e mettere la voce nei todo con `chi: "tu"`. Non li esegui e non li pianifichi come tuoi.

## Prima di dire "fatto"

Lancia il controllo su entrambi i file:

    python3 .agents/hooks/controlla-periodo.py periodo/todo.json
    python3 .agents/hooks/controlla-periodo.py periodo/idee.json

Nel plugin lo stesso script sta in `skills/pianifica-periodo/scripts/`. Se esce 1, leggi il messaggio, correggi il file e rilancia. Non dire "fatto" finché non esce 0.

Poi aggiungi in fondo a `memoria/LOG.md`, senza riscrivere le righe sopra, una riga come questa:

    - 2026-11-07 10:30 · periodo · Piano riscritto: 2 idee portate nel periodo, 1 rimandata, obiettivo invariato.

## Regole

- Mai scrivere prima della risposta dell'utente.
- Mai riscrivere `periodo/obiettivo.md` senza una richiesta.
- Un'idea entra nel periodo solo da qui, dopo averla pesata con l'utente.
- Mai riusare un id, mai cancellare una voce o un'idea.
- Una voce nuova ha sempre `da: "piano"` e `aggiornato` di oggi.
- Se manca un fatto, scrivi che manca. Non inventarlo.
