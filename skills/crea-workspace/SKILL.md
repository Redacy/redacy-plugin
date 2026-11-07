---
name: crea-workspace
description: Crea un workspace, cioè un agente AI intero per un lavoro nuovo che l'utente non ha ancora fatto fare, dentro workspace/<nome>/ della sua cartella. Si usa quando dice "crea un agente per...", "ho un lavoro nuovo", "apri un workspace per...", "mi serve qualcuno che si occupi di...", "da oggi i preventivi li fai tu", oppure quando arriva un lavoro che nessun workspace esistente sa fare. Un lavoro che si ripete uguale non è un workspace: è un grafo, e serve la skill crea-grafo.
---

# Crea un workspace

Un workspace è un agente intero con un mestiere solo: ha il suo `AGENTS.md`, la sua memoria e le sue regole. Sta in `workspace/<nome>/` dentro la cartella dello studio.

## Quando serve

- Il lavoro è **nuovo**: l'utente non l'ha ancora fatto fare e nessun workspace lo conosce. Crea un workspace.
- Il lavoro si **ripete uguale** (ogni mattina, a ogni fattura): non è un workspace, è un grafo. Passa a `crea-grafo`.
- Il workspace **esiste già**: guarda `workspace/`. Se c'è, aprilo e lavora lì. Non ricrearlo e non sovrascriverlo.

Un grafo può chiamare un workspace nei suoi passi. Spesso si crea prima il workspace e poi il grafo che lo usa.

## Passo 1. Capire il lavoro

Fai **una domanda alla volta** e aspetta la risposta. Se l'utente ha già detto una cosa (anche nella richiesta), non richiederla. Se ti ha dato tutte le risposte in anticipo e ha detto di non fargli domande, non ne fare: usa ciò che ti ha dato.

Ti servono quattro cose:

1. **Cosa fa il lavoro.** Che cosa entra, che cosa deve uscire, per chi. Chiedi un caso concreto: "l'ultima volta che l'hai fatto, com'è andata?".
2. **Quali dati usa e dove stanno.** Il dato resta dov'è. Non lo copiare nel workspace: scrivi il percorso (`fonti/listini/`, una cartella condivisa, un file). Se l'utente non sa dove sta, scrivi "da indicare" e mettilo tra le cose da scoprire.
3. **Le regole del mestiere.** Cosa può fare da solo il workspace, cosa deve chiedere prima, cosa non fa mai. Quando una regola ha una soglia (un importo, un tipo di cliente), chiedi il numero.
4. **Il nome.** Kebab-case italiano, due o tre parole: `preventivi-officina`, `solleciti-clienti`. Solo minuscole, numeri e trattini. Proponilo tu, l'utente conferma.

Prima di creare, guarda `workspace/` (e l'indice di memoria dello studio): se un workspace fa già questo mestiere, dillo all'utente e apri quello.

## Passo 2. Creare la struttura

Lo script `scripts/crea-workspace.py` sta nella cartella di questa skill (`${CLAUDE_SKILL_DIR}` su Claude Code): lancialo con quel percorso assoluto, dalla cartella dello studio.

```
python3 ${CLAUDE_SKILL_DIR}/scripts/crea-workspace.py <nome> --descrizione "<una frase>" --dati "<percorso>"
```

- `--dati` si può ripetere, uno per ogni percorso. Se non ne hai, omettilo.
- `--cartella <dir>` serve solo se non lanci lo script da dentro lo studio.
- Lo script trova la cartella dello studio risalendo fino a una che ha `AGENTS.md` e `grafi/`.

Lo script crea `workspace/<nome>/` con `AGENTS.md`, `CLAUDE.md` (che contiene solo `@AGENTS.md`), `.agents/` (con `skills/`, `regole/`, `policy/`) e `memoria/` (con `INDICE.md` e la scheda `<nome>.md`). Poi aggiunge il collegamento nell'indice dello studio e una riga nel registro. Stampa i percorsi creati.

Se esce con 2, il workspace esiste già: non è un errore da aggirare. Apri quel workspace. Se esce con 1, leggi il messaggio: dice cosa correggere (di solito il nome).

## Passo 3. Scrivere il contenuto vero

Lo script lascia il modello con alcuni "(da completare)". Sostituiscili con ciò che hai capito.

**`workspace/<nome>/AGENTS.md`**: scrivi il dominio (di cosa si occupa, in due o tre righe) e quando lo usano (le richieste tipiche). Tieni il file sotto le 60 righe. Le regole lunghe vanno in `.agents/policy/`.

**`.agents/policy/`**: scrivi le regole del mestiere come **elenco di righe**, una voce per riga, sotto titoli come "Faccio da solo", "Chiedo prima", "Non faccio mai". **Mai tabelle**: un agente le legge male e il controllo le rifiuta. Una regola per riga, con il numero quando c'è: "i preventivi sopra 2.000 euro li approva l'utente".

**`memoria/<nome>.md`** (la scheda): cosa fa, quando si usa, dove stanno i dati. È la pagina che gli altri leggono per capire se questo workspace fa al caso loro. Una pagina breve.

Altre cose che l'utente ti racconta (un cliente difficile, un modo di fare, un errore da non ripetere) vanno in **una pagina a parte** in `memoria/`, collegata dalla scheda con `[[nome-pagina]]`. Una cosa, una pagina. Aggiungi la riga nell'`INDICE.md` del workspace.

Non inventare. Se non sai una cosa, scrivila tra le cose da scoprire nell'indice invece di indovinarla.

## Passo 4. L'indice e il registro dello studio

Lo script lo fa da sé quando lo studio ha `memoria/INDICE.md` e `memoria/`. Guarda l'output.

- Nell'indice dello studio ci deve essere, sotto `## Workspace`, la riga `- [[<nome>]] · <descrizione>`. Il collegamento punta alla scheda del workspace.
- In `memoria/LOG.md` ci deve essere una riga nel formato `- AAAA-MM-GG HH:MM · workspace · <frase>`, in fondo, senza riscrivere le altre.

Se lo script ha stampato un avviso perché mancava l'indice o il registro, aggiungi tu la riga, nello stesso formato.

## Passo 5. Controllare, poi dire fatto

Prima di dire che hai finito, lancia:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/controlla-workspace.py workspace/<nome>
```

(Su Codex `${CLAUDE_SKILL_DIR}` non si espande: usa il percorso assoluto della cartella di questa skill, che Codex ti ha dato quando ha caricato la skill.) Controlla l'albero: `AGENTS.md` non vuoto, `CLAUDE.md` uguale a `@AGENTS.md`, le tre cartelle di `.agents/`, indice e scheda, nessun segnaposto `{{...}}` rimasto, nessuna tabella nei file di policy. Se esce con 1, correggi e rilancia. Non dire "fatto" finché non esce con 0.

Gli avvisi non fermano, ma un "(da completare)" rimasto vuol dire che non hai finito il Passo 3.

## Passo 6. Dire all'utente cosa hai fatto

In poche righe:

- il nome e il percorso del workspace;
- cosa fa e dove prende i dati;
- le regole che hai scritto, in una riga ciascuna (così le può correggere subito);
- come lo usa: "chiedi un preventivo e lavoro in `workspace/<nome>/`";
- se il lavoro si ripete, proponi di farne anche un grafo con `crea-grafo`.

## Cosa non fare

- Non sovrascrivere un workspace che c'è.
- Non copiare i dati dell'utente dentro il workspace.
- Non scrivere policy in tabelle.
- Non dare al workspace il permesso di inviare mail, messaggi o documenti, né di muovere soldi. Questi passi restano all'utente: si scrivono nelle regole "Non faccio mai".
- Non usare nomi con spazi, accenti o maiuscole.
- Non lasciare segnaposto `{{...}}` nei file.
