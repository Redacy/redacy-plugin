# La spiegazione finale di `inizia`

L'ultimo messaggio di `inizia` spiega il sistema a chi non è un tecnico. Dice tre cose, in quest'ordine, e niente altro.

## 1. Cosa hai creato

Contalo nella cartella prima di dirlo, non a memoria:

- quante fonti sono segnate nell'elenco dei dati (`memoria/fonti-dati.md`) e quali restano dove sono;
- quali pagine di memoria sono nate (la pagina dello studio, le procedure);
- quali agenti AI sono nati, ognuno con il suo lavoro in una riga, e dove sta (`workspace/<nome>/` o `grafi/<nome>.yaml`).

## 2. Dove lo vede

- **Il pannello**: una pagina nel browser, solo sul suo computer, all'indirizzo che la skill `pannello` ha scritto in `interfaccia/pannello.json`. Dillo con l'indirizzo intero (`http://127.0.0.1:<porta>`).
- **La cartella**: il percorso della cartella dello studio. Tutto quello che l'agente sa e fa sta lì dentro.

Frase «Il pannello»:

> Ti ho aperto il pannello: una pagina nel browser, solo sul tuo computer. Lì vedi cosa sta girando, cosa aspetta te e cosa sa lo studio.
> Se un lavoro va fermato c'è il bottone Ferma. Per il resto il pannello mostra e basta: le richieste le fai qui, a me.

Su Claude Code, nell'app desktop, il pannello si apre anche nel pannello del browser dell'app (`.claude/launch.json`). Da terminale e su Codex, nel browser.

## 3. Cosa succederà

- La prossima volta basta scrivere cosa c'è da fare: l'agente parte da quello che sa.
- Quando l'utente corregge o insegna qualcosa, a fine lavoro l'agente propone di salvarlo (skill `impara`), così la volta dopo lo sa.
- La cartella cresce quando l'utente la guida: un lavoro nuovo diventa un nuovo agente AI dopo il suo sì.
- Niente parte da solo e niente esce dalla cartella senza di lui: mail e messaggi l'agente li prepara, li manda lui.
- I lavori detti e non ancora creati: uno per riga, come prossimi passi.

Frase «La chiusura»:

> Fatto. Lo studio adesso ha la sua memoria, un agente AI per le dichiarazioni e l'elenco dei tuoi dati.
> La prossima volta scrivimi cosa devi fare, anche solo «prepara la pratica di Rossi»: parto da quello che so. Se mi correggi, a fine lavoro ti propongo di salvarlo, così la volta dopo lo so.

## Su Codex

Su Codex la cartella si finisce con due gesti dell'utente, una volta sola. Diglieli in fondo, prima della chiusura, con il comando pronto da copiare.

1. **Una riga da lanciare nel terminale**, che finisce la cartella e accende il pannello. Si compone così, tutta su una riga: la riga `comando:` stampata da `crea-cartella.py` (solo se è uscito con 3), poi `&& cd <cartella dello studio> && python3 .agents/script/pannello.py`. Se la cartella era già completa, basta `cd <cartella dello studio> && python3 .agents/script/pannello.py`. Il pannello stampa il suo indirizzo: l'utente lo apre nel browser.
2. **I controlli automatici**: la prima volta che apre Codex in questa cartella, Codex chiede se si fida della cartella (sì); poi scrive `/hooks` e approva i due controlli. Va rifatto solo se un controllo cambia.

Frase «Su Codex»:

> Due cose le fai tu, una volta sola.
> Prima: apri il terminale e lancia questa riga. Finisce la cartella dello studio e accende il pannello, poi ti scrive l'indirizzo da aprire nel browser:
> `python3 …/crea-cartella.py … && cd … && python3 .agents/script/pannello.py`
> Poi: apri Codex in questa cartella, digli che ti fidi della cartella e scrivi `/hooks`. Approva i due controlli automatici: servono a fermare un lavoro dal pannello e a controllare le cose da fare.

## Cosa non dire

Niente lodi, niente frasi a effetto («il tuo studio prende forma»), niente numeri promessi. Niente nomi tecnici che l'utente non vedrà mai (skill, hook, sottoagente, JSON). Se qualcosa non è riuscito (il pannello, una fonte che non si apre), una riga, con cosa fare.
