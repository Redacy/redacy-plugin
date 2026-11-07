---
name: impara
description: Salva ciò che il professionista insegna e ciò che si impara dal lavoro fatto, nella forma giusta: una pagina di memoria, una regola, una skill, uno script, un controllo automatico o un processo a passi fissi. Usala quando l'utente insegna ("ricordati che", "da noi si fa così", "ti spiego come lavoro"), quando ti corregge ("no, così non va", "questo lo faccio io"), oppure a fine lavoro ("abbiamo finito, cosa hai imparato?", "salva come si fa", "da ora in poi fallo sempre così").
---

# Impara

Obiettivo: ciò che l'utente sa e ciò che si è deciso nel lavoro restano nella cartella dello studio e cambiano il modo in cui decidi la prossima volta.

Hai due usi. Se l'utente ti sta insegnando o ti sta correggendo, vai a "Uso 1". Se il lavoro è finito e vuoi salvarne il metodo, vai a "Uso 2".

## Prima di scrivere

1. Leggi `memoria/INDICE.md`. Se una pagina c'entra, leggila.
2. Se la cosa riguarda cosa fai da solo e cosa chiedi, leggi `.agents/policy/cosa-faccio-da-solo.md`.
3. Decidi dove va ciò che hai imparato, con questa mappa:
   - Un fatto o un modo di ragionare: una pagina in `memoria/`. Come si fa: `references/pagina-di-memoria.md`.
   - Un limite o un permesso su una classe di azioni: una riga in `.agents/policy/cosa-faccio-da-solo.md`.
   - Una regola che vale per una cartella: un file in `.agents/regole/`.
   - Un modo di lavorare di un'area di lavoro sola: una procedura nella memoria di quell'area, `workspace/<nome>/memoria/`, o una skill in `workspace/<nome>/.agents/skills/`.
   - Prima di scrivere in `.agents/`, leggi "Se `.agents/` è in sola lettura".
4. Se non sai quale, applica il criterio di `references/forme.md`.

## Uso 1: l'utente insegna

Quando l'utente spiega una regola o un modo di lavorare:

1. Chiedi di cosa si tratta. Una domanda sola per volta.
2. Chiarisci finché la regola è completa: quando vale, chi la applica, le eccezioni, un esempio reale. Sempre una domanda per volta, con le sue parole.
3. Riassumi in 3-6 righe e chiedi: "È giusto così?".
4. Dopo il sì, cerca una pagina sullo stesso tema. Se c'è, aggiornala e mostra la differenza. Se no, creane una.
5. Aggiorna `memoria/INDICE.md`: una riga per pagina. Collega la nuova pagina a quelle vicine con `[[nome-pagina]]`, e aggiungi il collegamento di ritorno nelle pagine vicine.
6. Chiudi come in "Chiudere sempre".

Un fatto che contraddice una pagina: dillo e chiedi quale vale. Se l'utente ha corretto in modo esplicito, vince senza chiedere.

## Uso 1 bis: l'utente ti corregge

Una correzione vale già come sì. Non chiedere conferma: scrivi.

1. Dì in una riga che cosa avevi deciso e che cosa è sbagliato.
2. Cerca la pagina che c'entra in `memoria/`. Se c'è, aggiornala. Se no, creane una con la regola in positivo ("in questo caso si fa così"), il motivo e un esempio.
3. Se la correzione riguarda che cosa fai da solo e che cosa lasci all'utente, scrivi in `.agents/policy/` (vedi sotto).
4. Se riguarda una cartella precisa, scrivi in `.agents/regole/`. Se riguarda come lavora una sola area di lavoro, scrivi nella sua memoria o nelle sue skill.
5. Chiudi come in "Chiudere sempre".

## La policy: cosa fai da solo

Il file è `.agents/policy/cosa-faccio-da-solo.md`. Ha tre liste: "Faccio da solo", "Chiedo prima", "Non faccio mai". È un elenco puntato, mai una tabella.

- Una riga per classe di azione, nella lista giusta, scritta come le altre: `- Preparare le bozze dei solleciti.` Se vuoi segnare quando l'utente l'ha detto, aggiungi la data in fondo alla riga: `(AAAA-MM-GG)`.
- Se la classe c'è già in una lista, correggi quella riga o spostala nell'altra lista. Non ne aggiungi una seconda.
- Il file resta sotto le 300 parole. Se cresce, raggruppa le classi simili in una riga.
- Una riga per voce: vai sempre a capo.
- Il file dice che cambiarlo si chiede prima. Basta la parola dell'utente: una correzione detta con le sue parole ("questo lo faccio io") è già il sì. Un permesso che deduci tu da un solo "vai" no: chiedi.
- Soldi, atti legali, invii a clienti restano in "Non faccio mai" finché l'utente non dice il contrario con le sue parole.

## Se `.agents/` è in sola lettura

Codex tiene `.agents/` e `.codex/` in sola lettura, anche quando può scrivere nel resto della cartella. Claude Code no. Se una scrittura in `.agents/` viene rifiutata, o sai di essere in Codex:

- Non cercare un altro modo di scrivere lì e non cambiare utente o strumento.
- Una regola o un permesso: scrivi la riga nella pagina `memoria/regole-in-attesa.md` (la crei tu, con la forma delle righe di policy) e aggiungila a `memoria/INDICE.md`. Dì all'utente, in una frase, che da Codex non puoi toccare le regole e che la riga aspetta: la passa nel file delle regole una sessione di Claude Code, oppure lui a mano. Finché non è passata, rispettala come se ci fosse.
- Una procedura che sarebbe una skill dello studio: scrivila come pagina in `memoria/`, con una riga sotto "Procedure" in `memoria/INDICE.md`. Funziona uguale: la leggi quando serve.
- Un controllo automatico (uno script in `.agents/hooks/`): non si può creare da Codex. Descrivilo in una pagina di memoria e dì all'utente che per attivarlo serve Claude Code.
- Le pagine in `memoria/` e le righe di `memoria/LOG.md` si scrivono sempre: lì non c'è limite.

## Uso 2: a fine lavoro

Quando l'utente chiude un lavoro e chiede di salvarlo:

1. Rileggi il processo appena fatto: i passi, i dati usati, le decisioni dell'utente, le correzioni. Le correzioni sono la parte che vale di più: dicono dove l'utente decide lui.
2. Separa ciò che resta uguale (sequenza, fonti, formato dell'uscita, regole) da ciò che cambia (date, nomi, importi, quale file) e da ciò che decide l'utente.
3. Scegli la forma con `references/forme.md`. Le forme sono sei: pagina di memoria, regola, skill, script, controllo automatico (hook), processo a passi fissi (grafo).
4. Proponi UNA forma, con il motivo in una riga. Dì in una riga ciascuna le altre che hai scartato e perché. L'utente decide. Non scegliere per lui, non offrire un menu.
5. Dopo il sì, scrivi nella forma scelta (sotto). Poi chiudi come in "Chiudere sempre".

Non salvare tutto per principio. Se il lavoro è stato un caso unico, dillo e salva solo ciò che regge: spesso una pagina di tre righe.

### Se la forma è una pagina o una regola

Segui "Uso 1": una pagina secondo `references/pagina-di-memoria.md`, oppure una riga in `.agents/policy/cosa-faccio-da-solo.md`, oppure un file in `.agents/regole/`.

### Se la forma è una skill

- Una skill nata nello studio vive in `.agents/skills/<nome>/SKILL.md` nella cartella. Se serve a un'area di lavoro sola, in `workspace/<nome>/.agents/skills/<nome>/SKILL.md`. Da Codex non puoi scriverci: vedi "Se `.agents/` è in sola lettura".
- Ha la stessa struttura delle skill del plugin: cartella col nome in kebab-case, `SKILL.md` con `name` (uguale alla cartella) e `description` in italiano, in terza persona, con le frasi d'innesco come le dice l'utente.
- Il corpo è all'imperativo, sotto le 1.500 parole. Il resto va in `references/`.
- Scrivila con i termini dell'utente: se lui dice "il file del carrier", la skill dice così.
- Metti un punto di approvazione davanti a ogni passo che invia, spende, pubblica o cancella, e davanti a ogni passo dove l'utente ha esitato. Non chiedere il permesso a ogni passo: solo dove conta.
- Un dato che manca si dice che manca. Mai inventare un numero.
- Provala su un caso che l'utente conosce già, quello appena fatto, e mostra l'uscita accanto a ciò che aveva ottenuto a mano. Se non coincide, correggi e riprova.

### Se la forma è uno script

- Scrivilo in Python 3 con la sola libreria standard. Niente pip.
- Mettilo in una cartella `scripts/` accanto alla skill che lo usa.
- Primo commento: cosa fa, cosa legge, cosa scrive. Stessi ingressi, stesso esito. Esce 0 se va bene, 1 con un messaggio in italiano se no.
- Lo lanci una volta su un caso noto e mostri l'uscita prima di dire che è pronto.
- Nella skill che lo usa scrivi la riga con il comando.

### Se la forma è un controllo automatico

- Lo script va in `.agents/hooks/` della cartella (o dell'area di lavoro), sempre Python 3 con la sola libreria standard. Legge l'evento da stdin, se non ha niente da dire esce 0 in silenzio.
- Registrane la voce negli stessi file in cui sono già registrati i controlli della cartella (`.claude/settings.json` e `.codex/hooks.json`): copia la forma di una voce che c'è già.
- Provalo a mano con un file che deve passare e uno che deve fallire.

### Se la forma è un processo a passi fissi

- Usa la skill `crea-grafo` (in Claude Code `/redacy:crea-grafo`). Il file nasce in `grafi/<nome>.yaml`.
- Passale ciò che hai raccolto: i passi, i dati, i punti in cui decide l'utente.
- Il passaggio da area di lavoro a processo è uno degli esiti di questa skill. Non esiste un comando a parte.
- Dopo la creazione offri `programma` se deve partire da solo. Non programmarlo senza il sì.

## Come parli con l'utente

Le parole di questa skill sono per te. All'utente dici le sue:

- "area di lavoro" per workspace, "processo a passi fissi" per grafo, "le regole" per policy, "controllo automatico" per hook, "pagina" per pagina di memoria.
- Non dici "skill", "script", "hook", "grafo", "JSON". Se proponi di salvare una procedura, dici "una procedura che tengo qui nello studio". Un nome di cartella lo dici una volta, con la sua parola accanto.
- Una domanda alla volta, frasi corte, niente lodi, niente punti esclamativi.

## Regole

- Non toccare `periodo/obiettivo.md`. Una correzione sul modo di lavorare non cambia l'obiettivo: lo cambia solo l'utente, con `pianifica-periodo`.
- Non scrivere in `periodo/idee.json` né in `periodo/todo.json`. Se l'utente butta lì un'idea, diglielo e rimandala a `pianifica-periodo`.
- Scrivi solo ciò che l'utente ha detto. Non inventare.
- Niente dati di persone fisiche non necessari: chiedi prima. Per un cliente basta il ruolo o la sigla che usa l'utente.
- Frasi corte, parole del professionista, non le tue.
- Una regola nuova si scrive solo dopo il sì. Una correzione si scrive subito.
- Non cancellare una pagina o una riga di policy: se non vale più, aggiornala e scrivi la data e il motivo.

## Chiudere sempre

1. Aggiungi in fondo a `memoria/LOG.md`, senza riscrivere le righe sopra, una riga: `- AAAA-MM-GG HH:MM · impara · <frase>`. L'ora è quella della macchina. Se hai creato un processo a passi fissi, `crea-grafo` scrive la sua riga di tipo `grafo`: qui scrivi comunque la riga `impara`.
2. Dì all'utente in una riga che cosa hai cambiato e dove. Per esempio: "Ho aggiunto la pagina `memoria/scadenze-iva.md` e una riga nelle regole: i solleciti li lascio a te."
