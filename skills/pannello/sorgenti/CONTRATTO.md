# La pagina del pannello: com'è fatta e cosa deve reggere

Questo file è per chi cambia la pagina del pannello: una persona di Redacy o un agente. Non serve per usarla: le scelte di ogni utente stanno in `interfaccia/su-misura.json` (→ `../references/su-misura.md`).

## Per chi è

Chi usa il pannello è un libero professionista o il titolare di una piccola azienda, sui 40-50 anni. Usa il computer tutti i giorni, ma la tecnologia non è il suo lavoro e non è un appassionato di AI. Vuole che il lavoro sia fatto bene e poterlo controllare. È curioso: gli piace vedere come funzionano i sistemi.

Quindi la pagina sta nel mezzo. Non è roba da smanettoni e non è una scatola nera.
- **I primi 5 secondi.** Appena apre, capisce cosa aspetta lui, cosa sta lavorando e che il resto è sotto controllo.
- **Ogni cosa si apre fino al file da cui viene.**
- **Il file si mostra come interfaccia:**
  - il Markdown impaginato;
  - il JSON come schede;
  - lo YAML di un processo come un disegno.
  - Il testo grezzo resta a un clic: «Guarda il file com'è scritto».

## I pezzi

| Pezzo | Cosa fa |
|---|---|
| `guscio.html` | Lo spazio e la navigazione. La casa mostra i pannelli come cartelle, con il primo grande. Un pannello si apre con lo zoom. «Avvicina» e «Allontana» portano la vista avanti e indietro. Il dock in basso porta da un pannello all'altro. C'è anche lo sfondo che la persona sceglie (galassia, scrivania, tinta unita) e il foglio «Supporto umano». In cima allo script c'è il blocco `SU MISURA`. |
| `contenuti/*.js`, `contenuti/contenuti.css` | L'interno dei cinque pannelli: Oggi, Processi, Periodo, Memoria, Aree. Il guscio disegna la cornice, i contenuti disegnano dentro. |
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
- `contenuti:vai` con `{pannello, voce}`: un collegamento porta a un altro pannello. Il guscio lo porta davanti e chiama `ist.vai(voce)`.
- `contenuti:profondita` con `{pannello, livelli}`: serve per le briciole.

Sul `document` arriva `contenuti:dati` dopo `Contenuti.carica`. Il guscio aggiorna le parti che disegna lui (la frase, i numeri, il dock) e non rimonta i pannelli.

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
  - Una mossa sola per ogni spostamento, da 350 a 600 ms, in ease-out.
  - Niente rimbalzi.
  - Con `prefers-reduced-motion` le mosse diventano dissolvenze e la galassia sta ferma.
  - La galassia si ferma anche quando la scheda è nascosta.
- **Indirizzi.** `#oggi` … `#aree` aprono quel pannello, `#tutto` apre la casa e `#supporto` il foglio del supporto.
- **Tastiera.**
  - ← e → spostano nel dock, Invio apre.
  - Esc fa un passo indietro alla volta: prima dentro il pannello, poi esce dall'avvicinamento, poi torna alla casa.
  - Il focus si vede. Tutto ciò che si clicca è un `<button>` o un `<a>`.
- **Gesti.**
  - Un solo gesto sulle esecuzioni, «Ferma», con una conferma dentro la pagina (mai `confirm`).
  - Il supporto copia un riepilogo e apre `https://redacy.com`. Da lì non parte niente.
- **Parole.**
  - Italiano semplice, scritto dalla parte di chi usa la pagina.
  - Le parole del prodotto sono processo, area, memoria e periodo.
  - «Corsa» e «grafo» stanno solo nella vista del file.
- **Niente bottoni rossi** per chiudere le finestre. Si torna con le briciole, con «Tutto» nel dock, con Esc o con un tocco sullo sfondo.
