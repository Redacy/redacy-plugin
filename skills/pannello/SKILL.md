---
name: pannello
description: Accende il pannello dello studio (una pagina nel browser, solo sul computer dell'utente) o riusa quello già acceso, e ne dà l'indirizzo. Si usa quando l'utente dice "apri il pannello", "fammi vedere", "cosa sta girando", "dov'è la pagina dello studio", "spegni il pannello", e alla fine di `inizia` per mostrare cosa è stato creato.
---

# Pannello

Il pannello è la pagina dello studio: vedi cosa sta girando, cosa aspetta te e cosa sa lo studio. La casa mostra cinque pannelli come cartelle (Oggi, Processi, Periodo, Memoria, Aree): l'utente ne tocca uno e si apre, con «Avvicina» lo porta quasi a tutto schermo, e il dock in basso lo porta da un pannello all'altro. Ogni cosa si apre fino al file da cui viene. Mostra e basta. Ha un solo gesto sulle esecuzioni, «Ferma», e un bottone «Richiedi supporto umano» che prepara un riepilogo e apre `https://redacy.com`: da lì non parte niente.

Gira sul computer dell'utente, su `127.0.0.1`, legge solo la cartella dello studio e non chiama né Claude né Codex. C'è un pannello solo per cartella: se è già acceso, questa skill dà l'indirizzo di quello.

## Come parli con l'utente

Dici «il pannello», «una pagina nel browser, solo sul tuo computer». Per le esecuzioni dici «sta girando», «fermato da te», «non dà notizie». Non dici server, porta, localhost né il nome degli script. L'indirizzo lo scrivi intero, perché l'utente lo apre: `http://127.0.0.1:47xxx/`.

## Passi

1. **Sii nella cartella dello studio** (quella con `AGENTS.md`). Se non lo sei, passa `--cartella <percorso>`.
2. **Accendi o riusa il pannello.** Lo script sta nella cartella di questa skill, in `scripts/pannello.py`. Su Claude il percorso è `${CLAUDE_SKILL_DIR}/scripts/pannello.py`; su Codex è `scripts/pannello.py` nella cartella della skill. Se esiste, vale anche la copia in `.agents/script/pannello.py` della cartella dello studio.
   ```
   python3 <percorso>/pannello.py
   ```
   Stampa «Il pannello è acceso: http://127.0.0.1:…/» oppure «già acceso» con lo stesso indirizzo.
3. **Dai l'indirizzo** e dici dove si apre:
   - Nell'app di Claude Code il pannello si apre da solo nel browser interno, dal menu dei server della cartella («pannello redacy», voce di `.claude/launch.json`). Se non c'è, apri l'indirizzo nel browser.
   - In Codex e nel terminale apri l'indirizzo nel browser.
4. **Spiega in tre frasi** (con le parole di `voce.md`), solo la prima volta:
   «Ti ho aperto il pannello: una pagina nel browser, solo sul tuo computer. Lì vedi cosa sta girando, cosa aspetta te e cosa sa lo studio. Se un lavoro va fermato c'è il bottone Ferma; per il resto il pannello mostra e basta.»
5. **La prima volta, le scelte su misura.** Se nella cartella non c'è `interfaccia/su-misura.json`, copialo da `modello/su-misura.json` di questa skill e adattalo all'utente: il nome dello studio, il pannello che vede per primo, l'ordine, lo sfondo, il colore. Come si sceglie e cosa non si tocca: `references/su-misura.md`.
6. **Se l'utente chiede di spegnerlo**: `python3 <percorso>/pannello.py --spegni`.

## Il pannello su misura

Se l'utente vuole il pannello diverso (prima i processi, il colore dello studio, uno sfondo più sobrio, niente frase in alto), cambi solo `interfaccia/su-misura.json` della sua cartella, come dice `references/su-misura.md`, e gli dici di ricaricare la pagina. Non tocchi mai `pagina.html`: è uguale per tutti e si aggiorna col plugin.

## Se non parte

- «Il sistema non mi lascia aprire una porta» (in Codex, dentro la sandbox): chiedi il permesso di lanciare lo stesso comando fuori dalla sandbox. Se l'utente preferisce, glielo dici in una riga da lanciare nel suo terminale, dalla cartella dello studio: `python3 .agents/script/pannello.py`.
- «Non trovo la cartella dello studio»: non sei nella cartella giusta. Chiedi all'utente dov'è.
- Una pagina che non si apre o resta vuota: guarda `interfaccia/pannello.log` e dì all'utente in una riga cosa c'è scritto.
- Il pannello si spegne da solo dopo otto ore senza che nessuno lo guardi. Riaccenderlo è lo stesso comando.

## Cosa legge il pannello (per te, non da dire)

`periodo/` (obiettivo, cose da fare), `memoria/LOG.md` (le cose fatte di recente), `grafi/*.yaml` e `grafi/corse/*.json` (i processi e le esecuzioni), `workspace/*/` (le aree di lavoro), `memoria/*.md` e `workspace/*/memoria/*.md` (la memoria, disegnata come un grafo dai `[[collegamenti]]`) e i nomi in `fonti/` (mai il contenuto). La pagina riceve anche il testo di questi file (mai di `fonti/`, mai delle cartelle nascoste) per mostrarli impaginati, e le scelte di `interfaccia/su-misura.json`. Se una cartella o un file non ci sono, la parte della pagina resta vuota, senza errori.

## Lo stop di una corsa

Il bottone «Ferma» scrive `grafi/corse/<id>.stop` (come `corsa.py ferma <id> --da pannello`). Chi sta eseguendo la corsa lo scopre al comando dopo: `corsa.py` esce con 3, oppure l'hook `.agents/hooks/ferma.py` nega lo strumento. Se ti succede, la corsa è stata fermata dall'utente: non riprovare, non cambiare strada, non chiuderla, scrivi una riga in `memoria/LOG.md` e dì all'utente che si è fermata e a quale passo.

In Codex l'hook parte solo dopo che l'utente lo approva con `/hooks` (una volta per cartella, e di nuovo se un hook cambia). Prima, lo stop funziona lo stesso grazie a `corsa.py`: ogni passo di una corsa passa da lì.
