# La pagina del pannello: com'è fatta e cosa deve reggere

Questo file è per chi cambia la pagina del pannello: una persona di Redacy o un agente. Non serve per usarla: le scelte di ogni utente stanno in `interfaccia/su-misura.json` (→ `../references/su-misura.md`).

## Per chi è

Chi usa il pannello è un libero professionista o il titolare di una piccola azienda, sui 40-50 anni. Usa il computer tutti i giorni, ma la tecnologia non è il suo lavoro e non è un appassionato di AI. Vuole che il lavoro sia fatto bene e poterlo controllare. È curioso: gli piace vedere come funzionano i sistemi.

Quindi la pagina sta nel mezzo. Non è roba da smanettoni e non è una scatola nera.
- **I primi 5 secondi.** Appena apre è su Oggi e capisce cosa aspetta lui, cosa sta lavorando e che il resto è sotto controllo. Niente da aprire prima, niente da imparare: una barra di pannelli e la pagina.
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
| `guscio.html` | La struttura e la navigazione. Una barra a sinistra col nome dello studio, i cinque pannelli, l'ora dell'ultimo dato, «Supporto umano» e il tema (automatico, chiaro, scuro). A destra il pannello aperto, uno alla volta, a tutta altezza. Sotto gli 860 px di larghezza il nome va in alto e i pannelli in una barra in basso. In cima allo script c'è il blocco `SU MISURA`. |
| `contenuti/*.js`, `contenuti/contenuti.css` | L'interno dei cinque pannelli: Oggi, Processi, Periodo, Memoria, Aree, con il loro titolo e la barra «Indietro» quando si scende di un livello. Il guscio li monta in modo `pieno`; il modo `anteprima` resta per chi vuole un guscio diverso. |
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
- `contenuti:profondita` con `{pannello, livelli}`: dice a che livello si è dentro il pannello. Il guscio di oggi non lo usa, le briciole le disegnano i contenuti.

Sul `document` arriva `contenuti:dati` dopo `Contenuti.carica`. Il guscio aggiorna le parti che disegna lui (il numero accanto a Oggi, il pallino di chi sta lavorando, il titolo della scheda, l'ora dell'ultimo dato) e non rimonta i pannelli.

`Contenuti.riassunto('oggi')` porta anche `guardare` (quante cose sono da guardare) e quello di `processi` porta `corre`.

**Colori.** Il guscio passa i token `--pc-*` ai contenuti:
- testo: `--pc-testo`, `-2`, `-3`;
- superfici e linee: `--pc-superficie`, `-2`, `--pc-linea`;
- accento: `--pc-accento`, `--pc-su-accento`;
- stati: `--pc-attesa`, `--pc-corre`, `--pc-ok`, `--pc-errore`;
- forma e caratteri: `--pc-raggio`, `--pc-font`, `-titoli`, `-mono`.

## Cosa deve reggere la pagina

- **Niente risorse esterne.** Il server la serve con una Content-Security-Policy senza rete: niente Google Fonts, niente CDN, niente immagini da fuori. Caratteri di sistema. Nessun `<!--` né `<script` dentro il codice: `costruisci.py` li rifiuta.
- **Chiaro e scuro.** I colori sono token su `:root`, ridefiniti per il tema scuro. `body` ha uno sfondo esplicito.
- **Telefono, 390×844.** Si naviga col dito, la pagina non scorre di lato, i bordi rispettano `env(safe-area-inset-*)`.
- **Movimento.**
  - Una mossa sola per ogni cambio di pannello, breve (circa 250 ms), in ease-out.
  - Bottoni e carte che si cliccano rispondono al puntatore e al tocco. Niente rimbalzi, niente che si muove da solo, tranne il pallino di chi sta lavorando.
  - Con `prefers-reduced-motion` non si muove niente.
- **Indirizzi.** `#oggi` … `#aree` aprono quel pannello, `#supporto` il foglio del supporto. Ogni altro indirizzo (anche il vecchio `#tutto`) apre il primo pannello. Il tasto Indietro del browser torna al pannello di prima.
- **Tastiera.**
  - I pannelli nella barra sono collegamenti: Tab li raggiunge, Invio apre. Il primo Tab porta a «Vai al contenuto».
  - Esc fa un passo indietro dentro il pannello e chiude il foglio del supporto.
  - Il focus si vede. Tutto ciò che si clicca è un `<button>` o un `<a>`.
- **Gesti.**
  - Un solo gesto sulle esecuzioni, «Ferma», con una conferma dentro la pagina (mai `confirm`).
  - Il supporto copia un riepilogo e apre `https://redacy.com`. Da lì non parte niente.
- **Parole.**
  - Italiano semplice, scritto dalla parte di chi usa la pagina.
  - Le parole del prodotto sono processo, area, memoria e periodo.
  - «Corsa» e «grafo» stanno solo nella vista del file.
- **Niente finestre dentro la pagina** e niente bottoni rossi per chiuderle. Si torna con «Indietro», con la barra dei pannelli o con Esc.
- **Niente viola e niente sfondi decorativi.** Fondo neutro caldo, carte bianche, il colore solo per gli stati (attesa, lavora, fatto, errore). L'accento di partenza è un inchiostro scuro; il colore dello studio arriva da `su-misura.json`.
- **Bersagli comodi.** Su schermo a tocco ogni bottone è alto almeno 44 px.
