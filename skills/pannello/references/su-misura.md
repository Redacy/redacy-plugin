# Il pannello su misura

Questa guida è per te, non va letta all'utente.

Il pannello è la stessa pagina per tutti. Quello che cambia da un utente all'altro sta in un file solo della sua cartella, `interfaccia/su-misura.json`. Lo scrivi tu partendo dal modello di questa skill, `modello/su-misura.json`.

Il server legge il file a ogni apertura della pagina e tiene solo le chiavi qui sotto, con valori validi. Una chiave sbagliata o in più non rompe niente: viene ignorata.

## Quando lo scrivi

- **La prima volta**, alla fine di `inizia`, quando accendi il pannello. Se il file non c'è, copialo dal modello e adattalo a quello che hai capito dell'utente nell'intervista.
- **Quando l'utente lo chiede.** Per esempio:
  - «voglio vedere prima i processi»;
  - «mettici il colore dello studio»;
  - «lo voglio scuro»;
  - «lo sfondo è troppo vivace»;
  - «non mi serve la frase in alto».

## Le chiavi

| Chiave | Valori | Cosa cambia | Come scegli |
|---|---|---|---|
| `titolo` | testo, al massimo 60 caratteri | Il nome in alto a sinistra. Vuoto vuol dire il nome della cartella. | Il nome dello studio come lo dice l'utente: «Studio Ferrante», non «studio-ferrante». |
| `primo` | `oggi`, `processi`, `periodo`, `memoria`, `aree` | La finestra grande sulla scrivania, la prima che l'utente vede in grande. Le altre restano in miniatura. | Di solito `oggi`. `processi` se il suo lavoro con lo studio è soprattutto seguire processi che girano da soli. |
| `ordine` | i cinque nomi, in ordine | L'ordine nel dock in basso e sulla scrivania. | Quelli che usa di più vanno prima. Se ne manca uno, la pagina lo aggiunge in fondo. |
| `sfondo` | `galassia`, `carta`, `tinta` | Lo sfondo a tutta pagina: `galassia` è disegnata, con stelle che si muovono piano; `carta` è chiara e calma; `tinta` è un colore unito. Se l'utente ne sceglie un altro dal bottone «Aspetto» della pagina, vince la sua scelta. | `galassia`. `carta` o `tinta` se l'utente vuole una pagina più quieta. |
| `tema` | `auto`, `chiaro`, `scuro` | Il tema di partenza. Se l'utente ne sceglie un altro dal bottone «Aspetto» della pagina, vince la sua scelta. | `auto`: segue il computer. `chiaro` o `scuro` solo se l'utente lo chiede. |
| `frase` | `true`, `false` | La frase grande sulla scrivania e in cima a Oggi: cosa aspetta lui e cosa sta lavorando. | `true`. `false` solo se l'utente dice che non gli serve. |
| `accento` | `{"chiaro": "#rrggbb", "scuro": "#rrggbb"}` | Il colore della sigla dello studio, dei bottoni pieni e del contorno di ciò che è scelto, nel tema chiaro e in quello scuro. | Il colore dello studio, se lo conosci (logo, sito). `chiaro` deve leggersi su bianco con un contrasto di almeno 4.5:1. `scuro` deve leggersi su un fondo quasi nero, quindi è più chiaro. Se non sei sicuro, lascia quelli del modello. |

## Come lo controlli

```
python3 "<percorso>/pannello.py" --vista su-misura
```

Stampa le scelte che la pagina userà davvero. Se una chiave che hai scritto non c'è, il suo valore non era valido. Poi di' all'utente di ricaricare la pagina del pannello: le scelte si leggono quando la pagina si apre.

## Cosa non fai

- **Non tocchi `.agents/script/pagina.html` né gli script della skill.** Sono copie del plugin, uguali per tutti, e si rifanno con il plugin. Tutto quello che è di questo utente sta in `interfaccia/su-misura.json`.
- **Non aggiungi pannelli e non cambi le parole del prodotto.** Le parole sono processo, area, memoria e periodo.
- **Non ci metti dati dell'utente.** Il file dice solo come mostrare la pagina.
- **Se l'utente vuole qualcosa che le chiavi non coprono:**
  - segnalo come idea in `periodo/idee.json`, con le sue parole, come dice la skill `pianifica-periodo`;
  - digli che è una richiesta per Redacy, che può fare dal bottone «Supporto» del pannello.
