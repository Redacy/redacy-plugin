# redacy

Plugin gratuito per Claude Code e per Codex che trasforma la cartella del tuo studio in un orchestratore in locale. Serve un tuo account del servizio AI che usi: il costo di quello è a parte.

*In English: a free plugin for Claude Code and Codex that turns a small professional firm's folder into a local orchestrator. It maps and tidies your files, creates AI agents and repeatable processes, keeps the work period, and shows everything in a dashboard on your own computer. The plugin and its skills are written in Italian.*

## Per chi è

Commercialisti, studi tecnici e piccole aziende con lavori che si ripetono e dati sparsi in cartelle, mail e fogli. Non serve saper programmare.

## Come si installa

Claude Code:

```
claude plugin marketplace add Redacy/redacy-plugin
claude plugin install redacy@redacy
```

Codex (0.164 o successivo):

```
codex plugin marketplace add Redacy/redacy-plugin
codex plugin add redacy@redacy
```

Il repo è privato: per ora installa solo chi ha accesso. Per provare da una cartella locale:

```
claude --plugin-dir /percorso/del/plugin
```

Su Codex: `codex plugin marketplace add /percorso/del/plugin`, poi `codex plugin add redacy@redacy`.

Dopo l'installazione apri una sessione nuova. Serve Python 3, solo libreria standard, niente pip. Funziona su macOS, Linux e Windows; su Windows, dove qui leggi `python3`, il comando di solito è `python` (o `py -3`).

## Come si parte

Apri Claude Code o Codex in una cartella vuota, o in quella del tuo studio, e scrivi `/redacy:inizia`. Su Codex scrivi: "usa la skill redacy:inizia".

`inizia` prepara questa cartella, senza toccare i tuoi file:

```
studio/
├── AGENTS.md, CLAUDE.md   le regole di lavoro dell'agente
├── memoria/               ciò che lo studio sa: pagine brevi, indice, registro
├── fonti/                 il materiale ricevuto, l'agente non lo modifica
├── periodo/               obiettivo, cose da fare, idee in attesa
├── grafi/                 i processi a passi fissi e le loro corse
├── workspace/             un agente per ogni lavoro
├── .agents/               regole, limiti e controlli automatici
└── interfaccia/           il pannello
```

Poi ti chiede quali lavori vuoi affidare a un agente AI e dove stanno già dati e procedure. Mappa le fonti, crea i primi agenti e apre il pannello. I tuoi dati restano dove sono.

## Le skill

Le prime tre sono quelle che usi di più. Le altre le chiama l'agente quando serve, o le chiedi tu.

| Comando | Cosa fa |
|---|---|
| `/redacy:inizia` | Prepara la cartella, ti intervista, mappa le fonti, crea i primi agenti, apre il pannello. |
| `/redacy:crea-workspace` | Crea un agente AI intero per un lavoro nuovo, con la sua memoria e i suoi limiti. |
| `/redacy:crea-grafo` | Trasforma un lavoro che si ripete uguale in un processo a passi fissi, con il passo che tocca a te. |
| `/redacy:ordina-dati` | Scrive in memoria dove stanno i tuoi dati e le tue procedure. I dati restano dove sono. |
| `/redacy:riordina-cartella` | Mette in ordine una cartella: conta cosa c'è, propone una struttura e un piano file per file, sposta solo dopo il tuo sì, non cancella niente e si può annullare. |
| `/redacy:pianifica-periodo` | Costruisce con te obiettivo e cose da fare, pesa le idee nuove, scrive il piano dopo il tuo sì. |
| `/redacy:giro-del-giorno` | Dice da dove partire, cosa aspetta te e cosa è fermo. |
| `/redacy:impara` | Salva ciò che insegni o correggi, nella forma giusta: pagina, regola, controllo o processo. |
| `/redacy:collega-sensore` | Ti guida a collegare posta, calendario, archivio, foglio o gestionale, in sola lettura. |
| `/redacy:programma` | Ti guida a far partire un processo da solo a un orario, con l'attività programmata di Claude o l'automazione di Codex. |
| `/redacy:pannello` | Accende il pannello e ti dà l'indirizzo. |

## Il pannello e lo stop

Il pannello è una pagina sola sul tuo computer (127.0.0.1). Ha cinque pannelli in una barra a sinistra (in basso sul telefono) e si apre su Oggi:
- Oggi: cosa tocca a te, cosa c'è da guardare, cosa sta lavorando, a che punto è il periodo;
- Processi: disegnati come un flusso, dal loro file;
- Periodo: obiettivo, cose da fare, idee;
- Memoria: un grafo delle pagine e dei loro collegamenti;
- Aree: chi si occupa di cosa.

Ogni cosa si apre fino al file da cui viene, impaginato. Il pannello mostra, il lavoro si chiede all'agente: dove serve, la pagina ti dice la frase da scrivergli e un tocco la copia. Il primo giorno, a cartella vuota, Oggi mostra quattro passi per cominciare. L'unico gesto è il bottone di stop su una corsa. "Richiedi supporto umano" ti porta a https://redacy.com e non fa partire niente.

Il nome in alto, il pannello che vedi per primo, l'ordine, il tema (chiaro, scuro o come il computer) e il colore si scelgono per ogni studio in `interfaccia/su-misura.json`. Li scrive l'agente; basta chiedergli «metti prima i processi» o «usa il colore dello studio».

Per accenderlo chiedi all'agente: "apri il pannello". Oppure usa il comando che `inizia` ti dà.

Lo stop ha due livelli. Ogni passo di una corsa controlla se è stata fermata: regge su Claude Code e su Codex. Dove gli hook sono approvati, un controllo in più blocca anche i comandi.

## Su Codex, tre cose da sapere

Sono state misurate.

1. Nella sandbox di default `.agents/` e `.codex/` della cartella sono in sola lettura. `inizia` ti dà una riga da lanciare nel terminale, che finisce la cartella e accende il pannello.
2. Il pannello su Codex si accende da quella riga, perché la sandbox nega la porta locale.
3. Gli hook della cartella partono solo dopo che scrivi `/hooks` in Codex e li approvi, una volta per cartella. Installare il plugin non basta. Senza, la cartella funziona lo stesso: manca solo il controllo in più.

## Su Windows, tre cose da sapere

1. Serve Python 3 installato davvero: `python --version` deve rispondere `3.x`. Se si apre il Microsoft Store, Python non c'è ancora.
2. `inizia` scrive i controlli automatici e il comando del pannello con il Python che trova su quella macchina. Una cartella nata su un Mac e poi spostata su Windows tiene i comandi vecchi: si cancellano i tre file dei controlli e si rilancia `inizia`.
3. Le parti scritte per Windows (il pannello che resta acceso, i lucchetti dei file, i controlli automatici) sono provate per ora solo in simulazione, con `prove/windows/prova-portabile.sh`. La prima installazione su una macchina vera va seguita passo passo.

## Cosa fa e cosa non fa

- Lavora solo nella cartella che scegli.
- Non apre connessioni proprie fuori da localhost, non installa software, non chiede chiavi né password.
- I testi che legge passano dal servizio AI che usi.
- Non sposta file senza un tuo sì e non ne cancella mai. Un riordino si può annullare.
- Non raccoglie dati e non ha telemetria: vedi `PRIVACY.md`.
- Una persona rivede il risultato prima che esca. Soldi, atti legali e invii restano tuoi.
- Gli agenti nascono al livello più prudente e non cambiano da soli.

Cosa resta fuori:

- Non è l'agente gestito di Redacy: quello gira su una macchina nostra e cresce da solo.
- Non c'è un campo unico di comando.
- Non ha uno scheduler proprio. Per far partire un processo da solo, la skill `programma` ti guida a un'attività programmata di Claude o a un'automazione di Codex.

## Per chi sviluppa

```
bash prove/tutte.sh
claude plugin validate .
```

`prove/tutte.sh` lancia le prove senza modello: una riga per prova, in fondo `ESITO: PASSA` o `ESITO: FALLISCE`. Dura meno di un minuto. Servono Python 3, bash e curl. La prova della pagina vera nel browser (`prove/pannello/prova-pagina.sh`) usa anche Node 22 e un Chromium; se mancano, quella parte salta e lo dice.

La pagina del pannello si fa in pezzi in `skills/pannello/sorgenti/` (il guscio con la barra e la navigazione, i contenuti dei cinque pannelli, la fonte dei dati) e si monta in `skills/pannello/scripts/pagina.html` con `python3 skills/pannello/sorgenti/costruisci.py`. Cosa deve reggere sta in `skills/pannello/sorgenti/CONTRATTO.md`.

Le prove con un modello chiamano Claude Code o Codex con il tuo account: `prove/catena-claude.sh` e `prove/catena-codex.sh` seguono la catena inizia, crea-workspace, crea-grafo, corsa, pannello, stop; le prove di un solo pezzo stanno in `prove/inizia/prova-onboarding-*.sh` e `prove/grafi/prova-crea-*.sh`.

## Licenza

MIT, vedi `LICENSE`. Versione 0.4.0.
