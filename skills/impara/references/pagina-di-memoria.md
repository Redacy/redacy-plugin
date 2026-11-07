# Una pagina di memoria

Una pagina dice una cosa sola. Sta in `memoria/<nome-pagina>.md`, o in `workspace/<nome>/memoria/` se serve a un'area di lavoro sola.

## Com'è fatta

- Titolo: la cosa, in poche parole, come la chiama l'utente.
- Regola: una o due frasi, in positivo ("in questo caso si fa così").
- Eccezioni: un elenco corto, o "nessuna detta finora".
- Esempio: un caso reale, con nomi di fantasia se serve.
- Data: `AAAA-MM-GG` in cui l'hai scritta o aggiornata.
- Fonte: chi l'ha detta e dove ("detto dall'utente in chat", "dalla procedura in `fonti/...`").
- Vedi anche: i `[[collegamenti]]` alle pagine vicine, col nome del file senza `.md`.

## Regole

- Sotto le 300 parole. Se cresce, dividila in due pagine e collegale.
- Un fatto per pagina. Se ne trovi due, sono due pagine.
- Prima di creare, cerca in `memoria/INDICE.md` una pagina sullo stesso tema: aggiorna quella.
- Se aggiorni, mostra la differenza e non cancellare la data vecchia: scrivi "aggiornata il ..." e perché.
- Una riga in `memoria/INDICE.md` per ogni pagina: `- [[nome-pagina]] · di cosa parla, in una riga`; le procedure stanno sotto la sezione "Procedure".
- Un collegamento da A a B vuole il collegamento di ritorno da B ad A, nello stesso giro.
- Una pagina che nomina una pagina non ancora scritta va bene: resta un collegamento da scrivere.
- Scrivi solo ciò che l'utente ha detto.

## Esempio

    # Solleciti di pagamento

    Regola: i solleciti ai clienti si preparano il primo del mese e li spedisce lo studio, mai l'agente.
    Eccezioni: i clienti con rateizzazione in corso non ricevono il sollecito.
    Esempio: la ditta di arredi con la rata di ottobre pagata non va nell'elenco.
    Data: 2026-11-07
    Fonte: detto dall'utente in chat.
    Vedi anche: [[scadenze-iva]], [[clienti-rateizzati]]
