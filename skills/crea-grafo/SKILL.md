---
name: crea-grafo
description: Trasforma un lavoro che si ripete uguale in un grafo valido, cioè un file grafi/<nome>.yaml con i passi, l'innesco, il passo che tocca all'utente e i limiti. Si usa quando l'utente dice "fallo ogni mattina", "automatizza questo lavoro", "ogni volta che arriva una fattura...", "ogni lunedì prepara...", "trasforma questo in un grafo", "voglio che questo giri da solo". Un lavoro nuovo, mai fatto prima, non è un grafo: serve prima un workspace con crea-workspace.
---

# Crea un grafo

Un grafo è il disegno di un lavoro che si ripete uguale: quando parte, quali passi fa in ordine, quale passo tocca all'utente, cosa produce, quanto può fare da solo. Sta in `grafi/<nome>.yaml` nella cartella dello studio. Il pannello lo disegna, l'agente lo esegue passo per passo.

Il formato completo, campo per campo, sta in `references/formato.md` dentro la cartella di questa skill. Leggilo prima di scrivere il file.

## Quando serve

- Il lavoro si **ripete uguale** (ogni mattina, ogni lunedì, a ogni fattura che arriva): è un grafo.
- Il lavoro è **nuovo** o ogni volta diverso: non è un grafo. Si crea un workspace con `crea-workspace` e ci si lavora dentro.
- Esiste già un grafo per questo lavoro: guarda `grafi/`. Se c'è, aprilo e proponi di cambiare quello (sale la `versione`), non farne un secondo.

## Passo 1. Capire il lavoro

Fai **una domanda alla volta** e aspetta la risposta. Se l'utente ha già detto una cosa, non richiederla. Se ti ha dato tutte le risposte e ha detto di non fargli domande, non ne fare.

Ti servono sei cose:

1. **Cosa fa e a cosa serve.** Una riga (al massimo 200 caratteri): sarà l'`obiettivo`. Chiedi l'ultima volta che l'ha fatto a mano, passo per passo.
2. **Quando parte.** Tre casi: **a comando** (`parola`: parte quando lo chiede), **a un'ora** (`orario`: "ogni lunedì alle 8", serve anche il fuso, `Europe/Rome`), **a un fatto** (`evento`: "quando arriva una fattura", serve il fatto e la cartella dove arriva il materiale).
3. **I passi, nell'ordine.** Ogni passo è di un tipo: `cli` (un comando preciso), `agente` (lavoro da fare con giudizio, in un workspace), `umano` (tocca all'utente), `uscita` (ciò che il lavoro consegna).
4. **Quale passo tocca all'utente e in che forma.** `decisione` (sceglie), `lettura` (guarda), `invio` (spedisce lui), `fatto` (fa una cosa a mano). **Un invio non è mai dell'agente**: mail, messaggi e pagamenti li fa l'utente.
5. **Cosa produce.** Bozze, un file, un promemoria: finiscono in `uscite`.
6. **Quanto può fare da solo.** Il default è **L0**: prepara e basta. Non proporre di più al primo giro.

Dai un nome al grafo: kebab-case italiano, che dica il lavoro (`riepilogo-ordini-aperti`, `smista-fatture-in-arrivo`). Il nome del file senza `.yaml` è il nome del grafo.

## Passo 2. Controllare i workspace

Ogni passo `agente` ha un `workspace`: il nome di una cartella di `workspace/`, oppure `orchestratore` se il lavoro lo fa la cartella dello studio stessa.

Guarda `ls workspace/`. Se un passo nomina un workspace che non c'è, fermati e proponi `crea-workspace` per crearlo, poi torna qui. Non nominare workspace che non esistono: il controllo lo segnala come avviso, ma una corsa vera si bloccherebbe.

## Passo 3. Scrivere il file

Scrivi `grafi/<nome>.yaml` seguendo `references/formato.md`. Lo scheletro minimo:

```yaml
grafo: riepilogo-ordini-aperti
versione: 1
obiettivo: Preparare ogni lunedì il riepilogo degli ordini ancora aperti.
descrizione: |
  Legge gli ordini aperti e scrive un riepilogo di una pagina.
  Non spedisce niente: lo leggi tu nel pannello.
acceso: false
innesco: {tipo: orario, quando: "ogni lunedì alle 08:00 Europe/Rome"}
passi:
  - id: leggi-ordini
    tipo: agente
    nome: Leggi gli ordini aperti
    workspace: orchestratore
    prompt: Leggi gli ordini aperti in fonti/ordini/ e scrivi l'elenco con cliente, importo e data di consegna.
  - id: scrivi-riepilogo
    tipo: agente
    nome: Scrivi il riepilogo
    workspace: orchestratore
    prompt: Con l'elenco scrivi un riepilogo di una pagina, gli ordini in ritardo per primi.
  - id: leggi-riepilogo
    tipo: umano
    nome: Leggi il riepilogo
    forma: lettura
    dove: il pannello
tetti:
  contemporanee: 1
  corse_a_settimana: 2
uscite:
  - un riepilogo di una pagina
autonomia:
  livello: L0
  da: 2026-11-07
  si: null
```

Punti che sbagliano più spesso:

- Un passo senza `dopo` segue quello scritto prima. Scrivi `dopo` solo per i rami in parallelo o per un passo che aspetta più passi.
- Il `prompt` di un passo `agente` è una skill (`/nome`), un testo breve (al massimo 300 caratteri) o `{file: percorso.md}`. Se il testo è più lungo, scrivilo in un file di `memoria/` e puntalo.
- Un testo semplice con due punti seguiti da spazio va fra virgolette.
- I tetti con un innesco `orario` o `evento` vogliono `corse_al_giorno` o `corse_a_settimana`.
- Le date restano testo (`2026-11-07`). Il rientro è di 2 spazi, mai tabulazioni.
- Un passo `cli` ha un comando senza shell: niente `;`, `|`, `&`, `$`, `<`, `>`.

### Le tre cose da non cambiare senza il sì dell'utente

Un grafo nuovo nasce con:

- `livello: L0`
- `si: null`
- `acceso: false`

Questo è il default. Non cambiarlo mai di tua iniziativa. Per salire a `L1` o `L2`, o per mettere `acceso: true`, serve il **sì scritto dell'utente**: chi lo dà e dove, in una riga, nel campo `si`. Se l'utente dice "fallo partire da solo", rispondi che prima si fa girare a `L0` e si guardano le bozze; poi, quando le ha viste e va bene, scriveremo il suo sì.

## Passo 4. Controllare, correggere, poi dire fatto

Lancia il controllo e **non dire fatto prima che esca con 0**. Lo script `scripts/controlla-grafo.py` sta nella cartella di questa skill (`${CLAUDE_SKILL_DIR}` su Claude Code; su Codex usa il percorso assoluto della cartella di questa skill, che Codex ti ha dato quando l'ha caricata). Lancialo con quel percorso assoluto, dalla cartella dello studio:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/controlla-grafo.py grafi/<nome>.yaml
```

Se non riesci a risolvere il percorso, la cartella dello studio ne ha una copia in `.agents/script/controlla-grafo.py`.

Ogni errore dice il file, la riga, il campo, cosa non va e cosa fare. Correggi e rilancia, finché esce con 0. Gli avvisi (un workspace che non c'è ancora, un orario senza fuso) non fermano, ma leggili: di solito hanno ragione.

## Passo 5. Il registro

In fondo a `memoria/LOG.md` aggiungi una riga, senza riscrivere le altre:

```
- AAAA-MM-GG HH:MM · grafo · creato il grafo <nome>: <una frase su cosa fa>
```

Ora e data sono quelle locali della macchina.

## Passo 6. Se parte da solo

Se l'innesco è `orario` o `evento`, il grafo resta spento (`acceso: false`) e non parte da solo. Proponi la skill `programma`: imposta l'orario vero con gli strumenti nativi di Claude Code o di Codex, ma solo dopo che l'utente ha guardato almeno una corsa a `L0` e ha dato il suo sì.

## Passo 7. Dire all'utente cosa hai fatto

In poche righe:

- il nome del grafo e dove sta (`grafi/<nome>.yaml`);
- i passi, in ordine, e quale tocca a lui;
- che nasce a `L0`, spento: prepara e basta, non spedisce niente;
- come si fa girare una volta (qui sotto);
- se l'innesco è a ora o a fatto, che per farlo partire da solo c'è `programma`.

## Come si esegue una corsa

Una corsa è una volta che il grafo gira. Le regole complete stanno nell'`AGENTS.md` della cartella dello studio e in `references/formato.md`, sezione 6: non ridefinirle. In breve:

1. Apri la corsa: `python3 .agents/script/corsa.py apri <grafo> --avviato-da conversazione`. Stampa l'id.
2. Per ogni passo, nell'ordine: `corsa.py passo <id> <passo> inizio`, fai il lavoro, `corsa.py passo <id> <passo> fatto --esito "<cosa hai prodotto>"`.
3. Alla fine `corsa.py chiudi <id> finita`, e racconta all'utente cosa è successo passo per passo.
4. Se un comando di `corsa.py` esce con 3, la corsa è stata fermata: ti fermi subito e lo dici all'utente, senza riprovare.

Per provarlo senza rischi, esegui una corsa a `L0` con dati inventati o con una copia del materiale.

## Cosa non fare

- Non mettere `acceso: true`, `L1` o `L2` senza il sì scritto dell'utente.
- Non mettere un invio fra le `uscite`, né un passo `agente` che spedisce: l'invio è un passo `umano` di forma `invio`.
- Non inventare workspace: se manca, `crea-workspace`.
- Non dire fatto con il controllo che esce con 1.
- Non cambiare il formato del file per farlo passare: correggi il file.
