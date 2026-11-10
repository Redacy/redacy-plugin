# La pagina del pannello: com'è fatta e cosa deve reggere

Questo file è per chi cambia la pagina del pannello: una persona di Redacy o un agente. Non serve per usarla: le scelte di ogni utente stanno in `interfaccia/su-misura.json` (→ `../references/su-misura.md`).

## Per chi è

Chi usa il pannello è un libero professionista o il titolare di una piccola azienda, sui 40-50 anni. Usa il computer tutti i giorni, ma la tecnologia non è il suo lavoro e non è un appassionato di AI. Vuole che il lavoro sia fatto bene e poterlo controllare. È curioso: gli piace vedere come funzionano i sistemi.

Quindi la pagina sta nel mezzo. Non è roba da smanettoni e non è una scatola nera.
- **I primi 5 secondi.** Appena apre vede la scrivania: una frase che dice cosa aspetta lui e le cinque finestre in miniatura, vive. Capisce cosa aspetta lui, cosa sta lavorando e che il resto è sotto controllo. Niente da aprire prima, niente da imparare.
- **Il pannello mostra, il lavoro si chiede all'agente.** Dove una cosa manca, la pagina dice la frase da scrivere all'agente, e un tocco la copia.
- **Ogni cosa si apre fino al file da cui viene.**
- **Il file si mostra come interfaccia:**
  - il Markdown impaginato;
  - il JSON come schede;
  - lo YAML di un processo come un disegno.
  - Il testo grezzo resta a un clic: «Guarda il file com'è scritto».

## I pezzi

| Pezzo | Cosa fa |
|---|---|
| `guscio.html` | La struttura e la navigazione: una scrivania con finestre. Uno sfondo a tutta pagina (galassia, carta o tinta unita). In alto la sigla e il nome dello studio, l'ora dell'ultimo dato, «Aspetto» (sfondo e tema: automatico, chiaro, scuro) e «Supporto umano». Al centro la scrivania, con il saluto, la frase grande e le cinque finestre in miniatura; un clic su una miniatura la fa crescere fino a diventare la finestra. In basso il dock: «Scrivania» e i cinque pannelli. Su schermi larghi due finestre possono stare affiancate. Sotto i 760 px una finestra alla volta, a tutto schermo. In cima allo script c'è il blocco `SU MISURA`. |
| `contenuti/*.js`, `contenuti/contenuti.css` | L'interno dei cinque pannelli: Oggi, Processi, Periodo, Memoria, Aree, con il loro titolo e la barra «Indietro» quando si scende di un livello. Il guscio monta ogni pannello due volte: in modo `anteprima` nella miniatura sulla scrivania e in modo `pieno` nella finestra. |
| `fonte.js` | Nel plugin prende il posto di `dati.js`: i dati arrivano dal server locale. |
| `costruisci.py` | Unisce i pezzi in `../scripts/pagina.html`, un file solo senza risorse esterne. Va rilanciato dopo ogni modifica. La prova `prove/pannello/prova-pagina.sh` controlla che `pagina.html` sia quella che esce dai pezzi. |

## Il contratto fra guscio e contenuti

Il guscio carica, in quest'ordine:
1. `<link rel="stylesheet" href="contenuti.css">`
2. `<script src="dati.js"></script>`
3. `<script src="contenuti.js"></script>`

Poi viene il suo script. `costruisci.py` sostituisce queste tre righe esatte.

```js
window.DATI = { stato, file }       // stato = GET /api/stato; file = {percorso relativo: testo}
window.DATI_PRONTI                  // nel plugin: una Promise che si risolve quando i dati ci sono; il guscio parte lì
window.REDACY_PANNELLO              // true nel plugin
window.REDACY_MISURA                // le scelte di interfaccia/su-misura.json, già pulite dal server

Contenuti.pannelli                  // [{id, titolo, riga, icona}]: oggi, processi, periodo, memoria, aree
Contenuti.riassunto(id)             // {numero, etichetta, righe, stato: 'attenzione'|'corre'|'ok'|'calmo'}
const ist = Contenuti.monta(id, el, modo)   // modo 'anteprima' (da guardare) | 'pieno' (ci si lavora)
ist.aggiorna(modo); ist.vai(voce); ist.indietro(); ist.smonta();
Contenuti.carica(dati)              // dati nuovi: ridisegna le istanze montate solo se qualcosa è cambiato,
                                    // poi lancia 'contenuti:dati' su document
Contenuti.suFerma = function (id)   // la chiamata vera dello stop (nel plugin: POST /api/ferma col gettone)
```

**Eventi** lanciati dall'elemento montato, con `bubbles: true`:
- `contenuti:vai` con `{pannello, voce}`: un collegamento porta a un altro pannello. Il guscio lo apre e chiama `ist.vai(voce)`.
- `contenuti:profondita` con `{pannello, livelli}`: dice a che livello si è dentro il pannello. Il guscio non lo usa: per Esc chiama `ist.indietro()`, che dice se ha fatto un passo. Le briciole le disegnano i contenuti.

Sul `document` arriva `contenuti:dati` dopo `Contenuti.carica`. Il guscio aggiorna le parti che disegna lui (la frase e il saluto della scrivania, il numero su Oggi nel dock, il pallino di chi sta lavorando, il titolo della scheda, l'ora dell'ultimo dato) e non rimonta le finestre.

`Contenuti.riassunto('oggi')` porta anche `guardare` (quante cose sono da guardare), quello di `processi` porta `corre` e quello di `periodo` porta `totale` (quante cose in tutto).

**Colori.** Il guscio passa i token `--pc-*` ai contenuti:
- testo: `--pc-testo`, `-2`, `-3`;
- superfici e linee: `--pc-superficie`, `-2`, `--pc-linea`;
- accento: `--pc-accento`, `--pc-su-accento`;
- stati: `--pc-attesa`, `--pc-corre`, `--pc-ok`, `--pc-errore`;
- forma e caratteri: `--pc-raggio`, `--pc-font`, `-titoli`, `-mono`.

## Cosa deve reggere la pagina

- **Niente risorse esterne.** Il server la serve con una Content-Security-Policy senza rete: niente Google Fonts, niente CDN, niente immagini da fuori. Caratteri di sistema. Nessun `<!--` né `<script` dentro il codice: `costruisci.py` li rifiuta.
- **Chiaro e scuro.** I colori sono token su `:root`, ridefiniti per il tema scuro. `body` ha uno sfondo esplicito.
- **Sfondi.** Galassia, carta o tinta unita, disegnati dentro la pagina. Le stelle della galassia si muovono piano. Le scelte della persona (`redacy-sfondo`, `redacy-tema` in `localStorage`) vincono su `su-misura.json`.
- **Telefono, 390×844.** Si naviga col dito, la pagina non scorre di lato, i bordi rispettano `env(safe-area-inset-*)`. Sotto i 760 px le miniature stanno in colonna, il dock è a tutta larghezza in basso e si vede una finestra alla volta, a tutto schermo, con il solo «Chiudi».
- **Movimento.**
  - Una mossa sola per ogni cambio (una miniatura che cresce in finestra, una finestra che si affianca), breve (circa 250 ms), in ease-out.
  - Bottoni e carte che si cliccano rispondono al puntatore e al tocco. Niente rimbalzi, niente che si muove da solo, tranne il pallino di chi sta lavorando e le stelle dello sfondo.
  - Con `prefers-reduced-motion` non si muove niente, nemmeno le stelle.
- **Indirizzi.** `#oggi` … `#aree` aprono quella finestra, `#supporto` il foglio del supporto. `#tutto` e ogni altro indirizzo aprono la scrivania, che è la vista di partenza. Il tasto Indietro del browser torna alla finestra di prima.
- **Due finestre affiancate** (solo su schermi larghi almeno 1180 px).
  - Un collegamento dentro una finestra che porta a un altro pannello (per esempio «Apri il processo» da Oggi) apre l'altra finestra accanto, così non si perde il punto.
  - «Affianca un'altra finestra» mette la finestra a sinistra e mostra a destra «Cosa tieni accanto?» con le altre da scegliere.
  - Si trascina una finestra dalla barra del titolo: ai lati si affianca, in alto si ingrandisce, al centro torna sola.
  - Il confine fra le due si trascina; il doppio clic lo rimette a metà. In due finestre il bottone dice «Tieni solo questa finestra».
- **Tastiera.**
  - I pannelli nel dock sono collegamenti: Tab li raggiunge, Invio apre; con le frecce ← → ci si sposta nel dock. Il primo Tab porta a «Vai al contenuto».
  - Esc fa un passo indietro alla volta: prima dentro la finestra (i livelli), poi da ingrandita a normale, poi chiude la finestra. Chiusa l'ultima si torna alla scrivania. Chiude anche il foglio del supporto.
  - Anche i tre bottoni della barra del titolo («Affianca un'altra finestra», «Ingrandisci» o «Riduci», «Chiudi») sono `<button>`.
  - Il focus si vede. Tutto ciò che si clicca è un `<button>` o un `<a>`.
- **Gesti.**
  - Un solo gesto sulle esecuzioni, «Ferma», con una conferma dentro la pagina (mai `confirm`).
  - Il supporto copia un riepilogo e apre `https://redacy.com/contatti`, la pagina dove si prenota un appuntamento. Da lì non parte niente.
- **Parole.**
  - Italiano semplice, scritto dalla parte di chi usa la pagina.
  - Le parole del prodotto sono processo, area, memoria e periodo.
  - «Corsa» e «grafo» stanno solo nella vista del file.
- **Finestre senza trucchi.** Le finestre sono quelle dei pannelli e basta: niente popup che nascondono altro e niente bottoni rossi per chiuderle. Si torna con «Indietro», con «Chiudi», con il dock o con Esc.
- **Niente viola nell'interfaccia.** Lo sfondo è un fondale, le finestre sono carte piene e leggibili, il colore solo per gli stati (attesa, lavora, fatto, errore). L'accento di partenza è un inchiostro scuro; il colore dello studio arriva da `su-misura.json`.
- **Bersagli comodi.** Su schermo a tocco ogni bottone è alto almeno 44 px.
