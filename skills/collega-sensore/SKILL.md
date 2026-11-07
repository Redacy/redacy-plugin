---
name: collega-sensore
description: Guida a collegare una fonte viva (posta, calendario, archivio documenti, foglio di calcolo, gestionale) all'agente AI, in sola lettura, con gli strumenti nativi di Claude Code o di Codex. Si usa quando l'utente dice "collega la posta", "collega il calendario", "leggi anche il Drive", "leggi le mie mail", "guarda il foglio delle scadenze online", "collega il gestionale".
---

# Collega sensore

Un sensore è una fonte che cambia nel tempo e che l'agente può leggere: la posta, il calendario, un archivio di documenti, un foglio di calcolo, un gestionale. Questa skill lo collega con gli strumenti del programma che l'utente usa già. Non scrive codice e non installa niente di suo.

Le categorie (`~~posta`, `~~calendario`, `~~archivio documenti`, `~~foglio di calcolo`, `~~gestionale`) sono spiegate in `CONNECTORS.md`, nella radice del plugin.

## Come parli con l'utente

Le parole di questa skill sono per te. All'utente dici "collegamento" (non MCP, non server, non sensore), "la tua posta", "il tuo calendario". "Connettore" solo se lo vede scritto nell'app. Un comando lo mostri com'è, in un blocco, una volta, dicendo a cosa serve. Una domanda alla volta, niente lodi.

## Prima regola

L'utente decide cosa può leggere l'agente. Tutto ciò che l'agente legge resta dentro la cartella dello studio: non esce, non viene inviato a nessuno. Dillo all'inizio, in una riga.

## Passi

1. **Chiedi quale fonte.** Una domanda sola: "Quale fonte vuoi che legga? La posta, il calendario, un archivio di documenti, un foglio, un gestionale?" Se dice un prodotto (Outlook, Drive, Fatture in Cloud), prendi quello.
2. **Capisci la categoria.** Associa la fonte a una categoria di `CONNECTORS.md`. Se non è chiaro, chiedi cosa ci tiene dentro.
3. **Chiedi cosa serve leggere.** Una cartella di Drive, il calendario di lavoro, la casella di una sola persona: meno è meglio. Scrivi la risposta, ti servirà per il registro.
4. **Dì cosa serve all'utente.**
   - L'account della fonte, con il suo accesso.
   - La conferma sul sito del prodotto, nel browser, quando compare la richiesta di permessi. Se il prodotto lascia scegliere, preferisci i permessi di sola lettura.
   - Niente password in chat. Non chiederle mai e, se l'utente le scrive, digli di cambiarla. Una chiave di accesso (un token) la scrive lui nel terminale, dentro il comando, non nella conversazione.
5. **Capisci il suo programma.** Chiedi: "Stai usando Claude Code o Codex?" Poi segui solo la strada che lo riguarda (sotto).
6. **Fai provare con una lettura piccola.** Chiedi una cosa che non cambia niente: "elenca le ultime tre mail", "elenca gli eventi di domani", "elenca i primi cinque file della cartella X". Mostra l'esito all'utente. Se non funziona, vai a "Se qualcosa non va".
7. **Segna il collegamento** (sotto, "Cosa scrivi in memoria").
8. **Ricorda la regola.** Non crei regole nuove: in `.agents/policy/cosa-faccio-da-solo.md` c'è già "Collegare la posta, il calendario o un altro servizio" fra le cose che chiedi prima, e "Mandare qualcosa a qualcuno" fra quelle che non fai mai. Dì all'utente in una riga che sul collegamento leggi e basta, e che ogni scrittura, bozza o invio resta suo. Se l'utente vuole una regola in più, usa `impara`.

## Claude Code

Se l'utente ha già collegato il prodotto al suo account claude.ai (i "connettori"), Claude Code lo vede come un server MCP. Controlla così:

- Nella conversazione, il comando `/mcp` mostra i server e il loro stato.
- Dal terminale, `claude mcp list` li elenca.

Se non c'è, sono due strade.

**Dall'account claude.ai.** L'utente apre claude.ai/customize/connectors, aggiunge il prodotto e conferma i permessi. Poi riapre Claude Code e rifà il controllo.

**Un server a indirizzo.** Se il prodotto ha un server MCP con un indirizzo, il comando è questo, da lanciare nel terminale:

    claude mcp add --transport http <nome> <indirizzo>

Poi, nella conversazione, `/mcp` e il login nel browser. Dal terminale c'è anche `claude mcp login <nome>`, con `--no-browser` se il computer non ha un browser. L'indirizzo lo cerchi nella documentazione ufficiale del prodotto: non inventarlo.

Gli scope del collegamento:

- `local` è quello predefinito: vale per questa cartella, solo per l'utente, e le credenziali stanno fuori dalla cartella. Consiglialo.
- `project` scrive un file `.mcp.json` nella cartella, pensato per essere condiviso. Usalo solo se l'utente lo chiede, e mai con una chiave scritta dentro.
- `user` vale per tutte le sue cartelle.

Per toglierlo: `claude mcp remove <nome>`. Per i dettagli di un server: `claude mcp get <nome>`.

## Codex

Per un server a indirizzo, nel terminale:

    codex mcp add <nome> --url <indirizzo>
    codex mcp login <nome>

Il secondo comando apre il browser per il consenso; con `--no-browser` stampa un indirizzo da aprire a mano. Se il prodotto ha permessi di sola lettura con un nome noto, `codex mcp login <nome> --scopes <permessi>` chiede solo quelli: i nomi li cerchi nella documentazione del prodotto, non li inventi. `codex mcp list` elenca i server collegati; `/mcp`, dentro Codex, mostra quelli attivi. Per un programma locale al posto dell'indirizzo: `codex mcp add <nome> --env CHIAVE=valore -- <comando>`, ma la chiave la scrive l'utente, non tu.

La configurazione sta in `~/.codex/config.toml`, in una tabella `[mcp_servers.<nome>]`. Un file `.codex/config.toml` dentro la cartella vale solo se la cartella è fidata. Non modificare questi file di tuo: se serve un cambio a mano, dì all'utente quale riga e dove.

Per Codex dai solo questa strada. Non so se Codex veda anche i collegamenti fatti in altri programmi: non darlo per certo.

## Se qualcosa non va

- **Il collegamento chiede un permesso che non capisci.** Fermati, dillo con parole semplici e lascia scegliere a lui.
- **Il comando non è riconosciuto o il server non risponde.** Dì quale riga hai provato e cosa ha risposto. Non riprovare più di una volta con la stessa riga.
- **Il prodotto non ha un server MCP o un connettore.** Dillo: "Per questo non c'è un collegamento diretto che io sappia." Poi proponi la strada alternativa: l'utente esporta ogni tanto i dati (un file CSV o PDF, una copia del foglio) e li mette in `fonti/`. Poi usa `ordina-dati` per sistemarli e segnarli.
- **La lettura di prova mostra dati che l'utente non voleva far vedere.** Digli di restringere il permesso nel sito del prodotto o di togliere il collegamento (`claude mcp remove <nome>`, `codex mcp remove <nome>`), e non usare quei dati.

Se non sei certo di un passo o di un comando, dillo in una frase invece di darlo per sicuro. I comandi qui sopra vengono dalla documentazione ufficiale; i nomi dei menu nei siti dei prodotti cambiano spesso.

## Cosa scrivi in memoria

Dopo la lettura di prova riuscita, e solo dopo:

1. Aggiungi una riga in fondo a `memoria/fonti-dati.md`, nel formato: `- <fonte> · <categoria> · <nome del connettore> · <Claude Code o Codex> · sola lettura sì o no · AAAA-MM-GG`. "Sola lettura sì" vuol dire che hai chiesto solo permessi di lettura al prodotto. Se il prodotto non li offre, scrivi "no" e dillo all'utente: il collegamento può anche scrivere, e a trattenerti resta la regola "Non faccio mai".
2. Aggiungi una riga in fondo a `memoria/LOG.md`, mai riscrivendo le altre: `- AAAA-MM-GG HH:MM · fonte · collegata <fonte> (<categoria>) in <harness>, sola lettura <sì o no>`.
3. Se dell'utente hai saputo qualcosa che serve ricordare (il calendario di lavoro è il secondo della lista, la cartella dei clienti si chiama `Clienti 2026`), scrivila in una pagina di memoria con il collegamento `[[fonti-dati]]`: per questo usa `impara`.

## Cosa non fai

- Non chiedi password, codici di accesso o chiavi in chat.
- Non scrivi, non invii, non crei bozze o eventi nella fonte durante il collegamento. La lettura di prova non cambia niente.
- Non colleghi categorie di invio o firma (`~~firma e invio documenti`) in scrittura: dì che non lo fai.
- Non copi dati della fonte fuori dalla cartella dello studio.
- Non scegli tu cosa leggere: lo decide l'utente.

## Documentazione

- Claude Code, server MCP e connettori: https://code.claude.com/docs/en/mcp
- Codex, server MCP: https://learn.chatgpt.com/docs/extend/mcp?surface=cli (l'indirizzo vecchio, developers.openai.com/codex/mcp, rimanda qui)
- Codex, comandi `codex mcp`: https://learn.chatgpt.com/docs/cli/reference
