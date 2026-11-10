# Il piano di un riordino

Il piano sta in `periodo/riordini/<AAAA-MM-GG>-<nome-cartella>/piano.json`, nella cartella dello studio. Accanto, `applica` scrive `registro.jsonl`. Un riordino, una cartella: un piano nuovo non va accanto al registro di un altro.

## La forma

```json
{
 "versione": 1,
 "cartella": "C:/Users/Studio/OneDrive/Pratiche",
 "regola": "Clienti/<cliente>/<anno>/, nome AAAA-MM-GG <tipo> <cliente>; da [[come-si-ordinano-le-pratiche]]",
 "righe": [
  {"da": "vecchie/DVR Rossi.pdf", "a": "Clienti/Rossi/2024/2024-03-01 DVR Rossi.pdf", "perche": "DVR di Rossi, marzo 2024"},
  {"da": "Copia di DVR Rossi.pdf", "a": "Copia di DVR Rossi.pdf", "perche": "doppione: decide l'utente"}
 ]
}
```

- `cartella`: il percorso intero della cartella da riordinare. Niente esce da lì.
- `righe`: una per file. `da` e `a` relativi alla cartella, con `/` (anche su Windows). `perche` in poche parole.
- Una riga con `a` uguale a `da` vuol dire «resta dov'è». Un file senza riga resta dov'è.
- Si spostano file, non cartelle intere: le cartelle d'arrivo le crea `applica`.
- `permesso_fonti`: solo per riordinare dentro `fonti/` dello studio, con le parole del sì dell'utente.
- `byte` e `modificato` li aggiunge `controlla` a ogni riga. Non scriverli a mano.

## Cosa controlla `controlla` (e rifà `applica` prima di muovere)

- La cartella c'è, non è di sistema, non è una parte dello studio; `fonti/` solo col permesso.
- Ogni `da` c'è, è un file vero (non un collegamento, non una cartella), sta dentro la cartella, non è in una cartella nascosta, compare in una riga sola.
- Ogni `a` resta dentro la cartella: niente `..`, niente percorsi interi o lettere di disco, niente collegamenti che portano fuori.
- Niente sovrascrive: un `a` che c'è già è un errore, anche se un'altra riga sposta quel file (niente catene). Cambiare solo le maiuscole dello stesso file va bene.
- Niente collisioni, contando maiuscole e minuscole uguali come su Windows e OneDrive: fra due `a`, fra un `a` e un file che c'è, fra due grafie della stessa cartella, fra un file e una cartella con lo stesso nome.
- Nomi validi su Windows e OneDrive: niente `< > : " / \ | ? *`, niente spazio o punto in fondo, niente nomi riservati (`CON`, `NUL`, `COM1`...), niente `~$` all'inizio, al più 255 caratteri per nome e 259 per il percorso intero.
- Ogni riga ha `perche`.

Un file cambiato dopo `controlla` (dimensione o data diverse) non è un errore: `applica` lo lascia dov'è e lo dice con una riga `saltato:`.

## Le uscite

- `0`: fatto; con `controlla`, il piano va bene.
- `1`: il piano non va, o il comando è sbagliato. Non è stato spostato niente.
- `2`: il piano o il registro non c'è.
- `3`: fermato a metà da un errore (un file aperto, un permesso). Il registro sa cosa è fatto: rilanciare `applica` riprende, `annulla` torna indietro.

Le righe dell'uscita cominciano con `problema:`, `avviso:`, `per cartella d'arrivo:`, `esempio:`, `spostato:`, `saltato:`, `riportato:`, `errore:`, `esito:`.

## Il registro

Una riga JSON per fatto, scritta e salvata sul disco prima e dopo ogni mossa: `inizio`, `cartella` (creata dal riordino), `sposto`, `spostato`, `saltato`, `errore`, `fine`, e per l'annullo `annullo`, `annullato`, `cartella-tolta`, `annullato-tutto`. Se un'interruzione arriva fra lo spostamento e la riga che lo segna, `applica` e `annulla` guardano dove sta il file e lo ritrovano.

Dopo un `annulla`, quel piano non si riapplica: per rifare il riordino si scrive un piano nuovo, in una cartella nuova.
