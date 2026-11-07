# Le domande di `inizia`

Le frasi sono una traccia. Lo studio d'esempio è inventato: uno studio di commercialista con le pratiche dei clienti in una cartella, una procedura scritta e un foglio delle scadenze. Al posto dei nomi d'esempio metti quelli dell'utente.

## L'apertura

> Ciao. Prepariamo insieme la cartella del tuo studio: qui un agente AI impara come lavori e ti aiuta a farlo. Ti faccio poche domande, una alla volta.
> Prima domanda: quali lavori ti piacerebbe affidare a un agente AI? Pensa a quelli che rifai ogni settimana, sempre uguali.

## Se i lavori sono vaghi

(«non so, un po' di tutto»)

> Va bene partire larghi. Dimmi l'ultima cosa che hai fatto ieri e che ti ha preso più di un'ora. Partiamo da quella.

## Dove stanno dati e procedure

> Dove stanno oggi i dati e le procedure di questi lavori? Mi basta il posto: una cartella sul computer, Drive o SharePoint, la posta, un foglio Excel, un gestionale.
> Non sposto niente. I tuoi dati restano dove sono: io segno solo dove trovarli.

## Se i dati sono in disordine

(«è tutto un disordine», «è tutto nella mia testa»)

> È normale: quasi nessuno ha tutto in ordine. Mi basta un punto da cui partire, anche la cartella dove salvi le pratiche così com'è.
> Se una procedura non è scritta, raccontamela come la spiegheresti a un collaboratore nuovo. La scrivo io e te la faccio rileggere.

## Il riepilogo delle fonti

> Ho guardato i posti che mi hai indicato. Ho trovato:
> - `Pratiche 2026/`: 214 cartelle, una per cliente.
> - `Procedura dichiarazioni.pdf`: come prepari una dichiarazione, in 12 passi.
> - `Scadenze.xlsx`: le scadenze di ogni cliente.
>
> La procedura diventa una pagina della memoria dello studio. Le pratiche e il foglio restano dove sono: ho segnato dove trovarli. Manca qualcosa?

I numeri li hai contati tu nella cartella. Se una fonte non l'hai potuta aprire, dillo in quella riga.

## La proposta del primo agente AI

> Ti propongo un primo agente AI per le dichiarazioni. Apre la pratica del cliente, controlla che ci siano tutti i documenti e ti prepara l'elenco di cosa manca. Ogni risultato lo vedi tu prima che esca.
> Partiamo da questo?

Un lavoro solo, detto coi suoi passi, con l'utente che controlla. Che dentro sia un'area di lavoro o un processo a passi fissi non serve dirlo.

## La conferma prima di creare

> Prima di scrivere ti dico cosa creo, tutto dentro questa cartella:
> - la memoria dello studio, con la procedura delle dichiarazioni;
> - un'area di lavoro «dichiarazioni» (la cartella `workspace/dichiarazioni/`), dove lavora il nuovo agente AI;
> - l'elenco di dove stanno i tuoi dati.
>
> Fuori da qui non tocco niente. Procedo?

È l'unico punto dove compare un nome di cartella tecnico, con la sua parola accanto.

## Il ritorno

(la cartella è già uno studio)

> Ciao di nuovo. Lo studio c'è già: due agenti AI (dichiarazioni e scadenze), 18 pagine di memoria, l'ultimo lavoro ieri alle 17:20.
> Non rifaccio le domande. Cosa c'è di nuovo: un lavoro in più, dati nuovi o qualcosa da correggere?

I numeri li conti nella cartella prima di dirli.

## La pagina dello studio

`memoria/studio.md`, scritta al passo 5, sotto le 400 parole:

```markdown
# Lo studio

Cos'è: chi è lo studio, cosa fa, per chi. Da: la conversazione di inizia del <AAAA-MM-GG>.

## Chi siamo
<mestiere, città, quante persone; una riga per persona che conta: nome e cosa fa>

## I lavori da affidare a un agente AI
- <lavoro, con le parole dell'utente> · <area di lavoro o processo creato, o «da fare»>

## Dove stanno dati e procedure
Le fonti sono in [[fonti-dati]]. Le procedure: [[<pagina della procedura>]].

## Cosa non si fa mai
<le regole che l'utente ha detto, una per riga; le stesse stanno in .agents/policy/cosa-faccio-da-solo.md, o in [[regole-in-attesa]] se .agents/ non si può scrivere>
```

Se un dato non lo sai, non inventarlo: scrivi «da chiedere».
