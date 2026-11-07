# Campi di periodo/todo.json e periodo/idee.json

Se divergono dagli schemi in `scripts/`, valgono gli schemi.

## periodo/todo.json

In testa, e nient'altro:

- `versione`: sempre `"0.3.0"`.
- `periodo`: un nome breve o un intervallo. Vuoto se non c'è un periodo.
- `todo`: l'elenco delle voci.

Ogni voce ha questi campi, tutti obbligatori salvo `nota`:

- `id`: `t1`, `t2`, ... Unico nel file. Non si riusa mai.
- `cosa`: l'azione in una frase, comincia con un verbo.
- `chi`: `tu`, `agente` o il nome di una persona.
- `stato`: `da fare`, `in corso`, `fatto` o `ferma`.
- `scadenza`: data `AAAA-MM-GG`, oppure vuoto (`""`).
- `dove`: `workspace/<nome>`, `grafi/<nome>.yaml` o un file della cartella. Vuoto se non c'è.
- `da`: `piano`, `giro` o `utente`.
- `aggiornato`: data `AAAA-MM-GG` dell'ultima modifica della voce.
- `nota`: facoltativa. Perché è ferma, cosa aspetta.

"In ritardo" non è un campo. Si calcola: scadenza piena, passata, stato diverso da `fatto`.

## periodo/idee.json

In testa:

- `versione`: sempre `"0.3.0"`.
- `periodo`: il periodo in corso quando le idee sono arrivate. Può essere vuoto.
- `idee`: l'elenco delle idee.

Ogni idea ha:

- `id`: `i1`, `i2`, ... Unico nel file. Non si riusa mai.
- `idea`: una o due frasi, con le parole dell'utente.
- `da_dove`: `conversazione`, `utente` o il percorso di un file.
- `arrivata`: data `AAAA-MM-GG`.
- `esito`: assente o `null` finché l'idea non è pesata.

Quando l'idea è pesata, `esito` ha:

- `stato`: `portata nel periodo`, `rimandata` o `scartata`.
- `data`: data `AAAA-MM-GG` in cui è stata pesata.
- `perche`: il motivo in una riga, non vuoto.
- `todo`: facoltativo, solo se portata nel periodo. L'id della voce.

## Chi scrive cosa

- `todo.json`: pianifica-periodo, giro-del-giorno e l'utente.
- `idee.json`: l'agente quando l'utente dice un'idea fuori periodo. pianifica-periodo aggiunge l'esito.
- `obiettivo.md`: solo se l'utente lo chiede.
