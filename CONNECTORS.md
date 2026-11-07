# Connettori

## Come si leggono i riferimenti

Nelle skill di questo plugin, `~~categoria` sta per qualunque prodotto l'utente colleghi in quella categoria. `~~posta` può essere Outlook, Gmail o un'altra casella. Le skill parlano di categorie, non di prodotti: funzionano con quello che hai.

Il plugin non porta con sé nessun collegamento già pronto. Si collega ciò che serve, una fonte alla volta, con la skill `collega-sensore` (in Claude Code `/redacy:collega-sensore`). Funziona con gli strumenti nativi di Claude Code e di Codex.

## Le categorie

| Categoria | Segnaposto | Cosa vuol dire | Cosa ci fa l'agente | Esempi | Skill |
|---|---|---|---|---|---|
| Posta | `~~posta` | le caselle di posta di lavoro | legge e cerca messaggi, allegati compresi | Outlook, Gmail | `collega-sensore` |
| Calendario | `~~calendario` | gli appuntamenti e le scadenze fissate | legge gli eventi | Outlook Calendar, Google Calendar | `collega-sensore` |
| Archivio documenti | `~~archivio documenti` | dove stanno file e cartelle in rete | legge e cerca file | SharePoint, OneDrive, Google Drive | `collega-sensore` |
| Foglio di calcolo | `~~foglio di calcolo` | tabelle online | legge celle e fogli | Excel online, Fogli Google | `collega-sensore` |
| Gestionale | `~~gestionale` | il programma dove stanno clienti, fatture, contabilità | legge anagrafiche, documenti e scadenze | Fatture in Cloud, TeamSystem | `collega-sensore` |
| Messaggistica | `~~messaggistica` | le chat di lavoro | legge i canali che l'utente indica | Teams, Slack | `collega-sensore` |
| Firma e invio documenti | `~~firma e invio documenti` | firma digitale, PEC, invio di atti | niente: non si collega in scrittura | DocuSign, Adobe Acrobat Sign, PEC | nessuna: gesto dell'utente |

## Il principio

- **Sola lettura.** L'agente legge. Non scrive, non cancella, non sposta, non crea eventi e non manda messaggi. Molti collegamenti includono anche gli strumenti per scrivere: per questo la regola sta scritta nella cartella, in `.agents/policy/cosa-faccio-da-solo.md` («Non faccio mai: mandare qualcosa a qualcuno»), e l'agente chiede prima di ogni scrittura.
- **Cosa vede l'agente lo decide l'utente.** Una cartella, un calendario, una casella: meno è meglio. Con i dati veri dei clienti decide lui, caso per caso.
- **Nulla esce dalla cartella.** Ciò che l'agente legge da una fonte resta nella cartella dello studio.
- **Gli invii restano all'utente.** Una mail, un messaggio, una firma, una PEC: l'agente prepara la bozza, la spedisce l'utente. Per questo la categoria `~~firma e invio documenti` non si collega in scrittura.
- **Se un collegamento non c'è.** Si propone l'esportazione periodica nella cartella `fonti/`, e `ordina-dati` la mette in ordine.
- **Niente password in chat.** L'accesso si conferma nel sito del prodotto, nel browser.
