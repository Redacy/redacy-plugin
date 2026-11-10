<!-- redacy 0.4.0 · skills/crea-grafo/references/formato.md -->
# Il formato dei grafi e delle corse

Cos'è: il contratto di `grafi/<nome>.yaml` (il disegno di un lavoro che si ripete) e di `grafi/corse/<id>.json` (una volta che il lavoro è girato), più come l'agente esegue una corsa. Lo leggono `controlla-grafo.py`, `corsa.py`, il pannello e `AGENTS.md`.
Versione del formato: 1.

## 1. Il principio

Il yaml dice tutto ciò che il pannello disegna: i passi, il tipo e il nome di ciascuno, gli archi fra i passi, l'innesco, il passo che tocca all'utente, se il grafo è acceso. Niente di disegnato si ricava a mano. L'unica regola implicita è una sola, scritta qui e implementata in un solo punto (`archi_del_grafo` in `yaml_ridotto.py`): un passo senza `dopo` segue il passo scritto prima di lui.

Il formato è **ridotto**: niente utenti di sistema, niente permessi di accesso, niente ruoli da risolvere. Resta ciò che serve a un professionista sul suo computer.

## 2. Il sottoinsieme di yaml

Si legge con `yaml_ridotto.py`, solo libreria standard, senza PyYAML. Ammesso:

- mappe a blocchi (`chiave: valore`, rientro di 2 spazi) e liste a blocchi (`- voce`, anche `- id: x` seguito dalle altre chiavi della mappa);
- mappe e liste **in linea su una riga**: `{tipo: orario, quando: "..."}`, `[a, b]`, anche annidate;
- scalari: testo semplice o fra virgolette (`"..."` con `\"` e `\n`, oppure `'...'`), interi, decimali, `true` e `false`, `null` (o `~`, o il valore vuoto);
- testo a blocchi con `|` (e `|-`), per più righe;
- commenti con `#` (a inizio riga o dopo uno spazio, mai dentro le virgolette).

Non ammesso (il controllo dice riga e motivo): ancore e alias (`&x`, `*x`), tag (`!x`), documenti multipli, testo ripiegato `>`, mappe o liste in linea su più righe, chiavi non semplici (`? x`), tabulazioni nel rientro, chiavi ripetute, un testo semplice con `: ` dentro (va fra virgolette). Le date (`2026-11-07`) restano testo.

## 3. `grafi/<nome>.yaml`

Il nome del file senza `.yaml` è il nome del grafo. Nomi in kebab-case italiano (`^[a-z0-9]+(-[a-z0-9]+)*$`). Un campo che non è in tabella è un errore (il controllo dice quale e cosa fare).

### Il grafo

| Campo | Obbl. | Cosa vuol dire | Come si disegna |
|---|---|---|---|
| `grafo` | sì | il nome, uguale al file | il titolo |
| `versione` | sì | intero da 1; sale quando il grafo cambia | «v1» accanto al titolo |
| `obiettivo` | sì | una riga, al massimo 200 caratteri: a cosa serve | sotto il titolo |
| `descrizione` | no | testo a blocchi: cosa fa e come si controlla | pannello di contorno |
| `acceso` | sì | `true` se il grafo può partire da solo (attività programmata o automazione); `false` se parte solo quando lo chiedi | etichetta «acceso» o «spento» |
| `innesco` | sì | cosa lo fa partire (tabella sotto) | casella d'inizio |
| `passi` | sì | la lista dei passi, almeno uno e almeno uno di tipo `agente` | una casella per passo |
| `tetti` | sì | i limiti (tabella sotto) | pannello «Tetti» |
| `uscite` | sì | lista di testi: cosa produce fuori dalla corsa (può essere `[]`); un invio non è mai un'uscita | pannello «Uscite» |
| `autonomia` | sì | quanto può fare da solo (tabella sotto) | pannello «Autonomia» |
| `prove` | no | lista di prove a secco (tabella sotto) | pannello «Prove» |

### L'innesco

| Campo | Obbl. | Cosa vuol dire | Come si disegna |
|---|---|---|---|
| `tipo` | sì | `parola` (parte quando lo chiedi), `orario` o `evento` | l'icona dell'innesco |
| `quando` | solo `orario` | quando, come testo che si legge: `"ogni giorno alle 21:00 Europe/Rome"`, `"ogni lunedì alle 08:30 Europe/Rome"`. Il fuso va scritto: senza, il controllo avvisa. L'orario vero lo imposta la skill `programma` con gli strumenti nativi | la riga dell'orario |
| `fatto` | solo `evento` | il fatto che lo fa partire, in kebab-case (`nuova-fattura`, `file-arrivato`) | la riga dell'evento |
| `file` | solo `evento` | il percorso, relativo alla cartella dello studio, dove arriva il materiale (può avere `*`): `fonti/fatture/*.pdf` | la riga dell'evento |

### Un passo

Comuni a tutti: `id` (obbligatorio, kebab-case, unico nel grafo), `tipo` (obbligatorio: `cli`, `agente`, `umano`, `uscita`), `nome` (facoltativo, l'etichetta in italiano; se manca il pannello scrive l'`id` con gli spazi al posto dei trattini), `descrizione` (facoltativa, una riga o testo a blocchi: cosa succede qui), `dopo` (facoltativo, lista di `id` di passi **scritti prima**: gli archi che entrano; se manca, il passo segue quello scritto prima; il primo passo non ha `dopo`). Più passi con lo stesso `dopo` partono insieme; un passo con più voci in `dopo` aspetta tutti.

| Campo | Tipo di passo | Obbl. | Cosa vuol dire | Come si disegna |
|---|---|---|---|---|
| `id` | tutti | sì | il nome interno | l'etichetta se manca `nome` |
| `tipo` | tutti | sì | `cli`, `agente`, `umano`, `uscita` | colore e icona della casella |
| `nome` | tutti | no | l'etichetta in italiano | il titolo della casella |
| `descrizione` | tutti | no | cosa succede nel passo | il testo sotto il titolo |
| `dopo` | tutti | no | da quali passi arriva | le frecce |
| `comando` | `cli` | sì | un comando senza shell (niente `;` `\|` `&` `` ` `` `$` `<` `>`), per esempio `python3 .agents/script/prepara-fatture.py` | `$ comando` nella casella |
| `minuti` | `cli`, `agente` | no | il tetto di durata, intero da 1 a 600 | `N′` nella casella |
| `workspace` | `agente` | sì | il nome di una cartella di `workspace/`, oppure `orchestratore` per il lavoro svolto dalla cartella stessa | `workspace <nome>` nella casella |
| `prompt` | `agente` | sì | una skill (`/nome`), un testo breve (al massimo 300 caratteri) oppure `{file: percorso.md}` | `/nome` o il testo |
| `modello` | `agente` | no | `forte`, `media` o `leggera`; se manca decide chi esegue | il nome nella casella |
| `forma` | `umano`, `uscita` | sì | per `umano`: `decisione`, `lettura`, `invio` o `fatto`; per `uscita`: testo libero (`bozza`, `promemoria`, `file`) | `forma <x>` |
| `dove` | `umano`, `uscita` | sì | dove l'utente trova o fa la cosa: «il pannello», «la tua casella di posta, in bozze» | `dove ...` |

Il passo `umano` è il passo che tocca a te: la corsa lo segna fatto quando l'agente ha consegnato e dice cosa aspetta. L'attesa non tiene aperta la corsa.

Regole di controllo sui passi: gli `id` sono unici; ogni voce di `dopo` è un `id` di un passo scritto prima e non il passo stesso; non ci sono cicli; il primo passo non ha `dopo`; c'è almeno un passo `agente`. Sono avvisi (non fermano): un `workspace` che non c'è ancora in `workspace/` quando il controllo gira dentro una cartella dello studio; un orario senza fuso.

### I tetti

| Campo | Obbl. | Cosa vuol dire |
|---|---|---|
| `contemporanee` | sì | quante corse insieme al massimo, intero da 1 |
| `corse_al_giorno` | con `orario` o `evento`, uno dei due | quante corse al giorno al massimo |
| `corse_a_settimana` | con `orario` o `evento`, uno dei due | quante corse a settimana al massimo |
| `finestra_minuti` | no | un orario si tratta solo entro questi minuti dalla scadenza, poi è saltato |

Un innesco `parola` non ha bisogno di `corse_al_giorno`.

### L'autonomia

| Campo | Obbl. | Cosa vuol dire |
|---|---|---|
| `livello` | sì | `L0` prepara e basta; `L1` consegna dopo il tuo sì; `L2` consegna da sé |
| `da` | sì | la data di questo livello, `AAAA-MM-GG` |
| `si` | sì | il tuo sì alla prima corsa vera: chi e dove (una riga, al massimo 120 caratteri), oppure `null` |

Un grafo nuovo nasce a `L0`, con `si: null` e `acceso: false`. Regole: un livello diverso da `L0` vuole `si` scritto; `acceso: true` vuole `si` scritto.

### Le prove

Ogni voce: `data` (obbligatoria, `AAAA-MM-GG`), `esito_atteso` (obbligatorio, testo), `input` (facoltativo, testo).

## 4. `grafi/corse/<id>.json`

Una corsa è un file JSON, scritto solo da `corsa.py`. L'`id` è `<grafo>-AAAAMMGG-HHMMSS` in UTC (con `-2`, `-3` se due corse partono nello stesso secondo). Le ore sono UTC con la `Z`: `2026-11-07T10:30:00Z`. I file che iniziano con il punto in `corse/` sono lucchetti: chi legge li salta.

| Campo | Cosa vuol dire |
|---|---|
| `formato` | `1` |
| `id` | l'id, uguale al nome del file senza `.json` |
| `grafo` | il nome del grafo |
| `versione` | la versione del grafo con cui è partita |
| `stato` | `in-corso`, `finita`, `fallita`, `fermata` |
| `avviato_da` | `conversazione` (l'utente in una conversazione), `attivita-claude` (un'attività programmata di Claude), `automazione-codex` (un'automazione di Codex), `utente` (un comando lanciato a mano) |
| `inizio` | quando è partita |
| `ultimo_segno` | l'ora dell'ultimo segno di vita: ogni `apri`, `passo`, `battito`, `chiudi` lo aggiorna |
| `persa_dopo_minuti` | dopo quanti minuti senza segno di vita il pannello mostra la corsa «persa» invece che «in corso»: 20, scritto nel file all'apertura (`apri --persa-dopo N` lo cambia) |
| `fine` | quando è finita, fallita o fermata; `null` finché è in corso |
| `sessione` | l'identificativo della conversazione che la esegue (testo), `null` se non c'è. `apri` lo legge da `--sessione`, altrimenti dall'ambiente: `CLAUDE_CODE_SESSION_ID` in Claude, `CODEX_THREAD_ID` in Codex. Lo stop lo confronta con la sessione che sta lavorando |
| `stop` | `null`, oppure `{"chi": "pannello", "quando": "...Z", "perche": "..."}`: la richiesta di stop copiata qui da `corsa.py` quando la vede (vedi «Lo stop») |
| `passi` | la lista dei passi, nell'ordine del grafo, creata all'apertura con tutti `da-fare` |

Ogni voce di `passi`:

| Campo | Cosa vuol dire |
|---|---|
| `id` | l'`id` del passo nel grafo |
| `stato` | `da-fare`, `in-corso`, `fatto`, `fallito`, `fermato`, `saltato` |
| `inizio` | quando è partito, `null` se non è partito |
| `fine` | quando è finito, `null` se non è finito |
| `esito` | una riga: cosa ha prodotto («3 bozze in bozze della posta»), `null` se non c'è |
| `nota` | una riga libera: perché è fallito, cosa aspetta, `null` se non c'è |

### Lo stop

La richiesta di stop è un **file a parte**, `grafi/corse/<id>.stop`: una riga JSON `{"chi": "pannello", "quando": "2026-11-07T10:00:00Z", "perche": "..."}`. Lo crea `corsa.py ferma <id> --da <chi>`, o il pannello nello stesso modo. Così il `.json` della corsa ha un solo scrittore, `corsa.py`. Quando c'è il `.stop`, `corsa.py` (a ogni `passo`, `battito`, `chiudi`, e a `stato` e `elenco`) segna la corsa `fermata` (`fine`, `stop` con chi e quando, i passi `in-corso` diventano `fermato`) ed esce con 3 stampando «Corsa fermata da <chi>: non fare altri passi, dillo all'utente.». Se il primo `passo` dopo la richiesta è un `inizio`, il passo non parte. Chi legge il `.json` senza passare da `corsa.py` tratta `in-corso` con un `.stop` accanto come `fermata`. Lo stop regge anche dove l'hook `ferma.py` non è approvato (Codex chiede l'approvazione di ogni hook, una volta per cartella): ciò che garantisce lo stop è il controllo di `corsa.py` prima di ogni passo, l'hook è una garanzia in più. I file `.stop` restano accanto alla corsa e non si cancellano.

Una corsa **persa** non è un valore di `stato`: lo decide chi legge. È persa se `stato` è `in-corso` e `ora - ultimo_segno > persa_dopo_minuti`.

Esempio:

```json
{
  "formato": 1,
  "id": "giro-posta-mattina-20261107-103000",
  "grafo": "giro-posta-mattina",
  "versione": 1,
  "stato": "in-corso",
  "avviato_da": "attivita-claude",
  "inizio": "2026-11-07T10:30:00Z",
  "ultimo_segno": "2026-11-07T10:31:12Z",
  "persa_dopo_minuti": 20,
  "fine": null,
  "sessione": "b3f1c2de",
  "stop": null,
  "passi": [
    {"id": "leggi-posta", "stato": "fatto", "inizio": "2026-11-07T10:30:01Z", "fine": "2026-11-07T10:31:10Z", "esito": "14 messaggi letti", "nota": null},
    {"id": "scrivi-bozze", "stato": "in-corso", "inizio": "2026-11-07T10:31:12Z", "fine": null, "esito": null, "nota": null},
    {"id": "controlla", "stato": "da-fare", "inizio": null, "fine": null, "esito": null, "nota": null}
  ]
}
```

## 5. `corsa.py`

Sta in `.agents/script/` (copiato da `inizia`) e nel plugin in `skills/crea-grafo/scripts/`. Solo libreria standard. Trova la cartella dello studio risalendo da `cwd` fino a una cartella con `AGENTS.md` e `grafi/` (o da `--cartella`, o dalla variabile `REDACY_CARTELLA`). Scritture atomiche (file temporaneo e `rename`), un lucchetto per corsa.

| Comando | Cosa fa |
|---|---|
| `apri <grafo> [--avviato-da conversazione\|attivita-claude\|automazione-codex\|utente] [--sessione ID] [--persa-dopo N]` | controlla il grafo (se ha errori non apre), crea il file, stampa l'id |
| `passo <id> <passo> inizio\|fatto\|fallito [--nota T] [--esito T]` | aggiorna il passo e `ultimo_segno` |
| `battito <id>` | aggiorna solo `ultimo_segno` |
| `chiudi <id> finita\|fallita` | chiude; i passi `da-fare` diventano `saltato`; con un passo `in-corso` rifiuta |
| `ferma <id> [--da CHI] [--perche T]` | scrive `grafi/corse/<id>.stop` e segna subito la corsa `fermata` (i passi `in-corso` diventano `fermato`); se la corsa non è in corso esce 3 e non scrive niente |
| `stato <id>` | applica un eventuale `.stop`, poi stampa il JSON della corsa e una riga «in corso», «persa» o lo stato |
| `elenco` | una riga per corsa, dalla più recente, con lo stato (persa compresa; applica gli eventuali `.stop`) |

Uscite: 0 ok; 1 uso sbagliato o grafo non valido; 2 corsa o grafo che non c'è; 3 la corsa non è più in corso (fermata o chiusa) o c'è una richiesta di stop: chi riceve 3 smette di lavorare.

## 6. Come si esegue una corsa (le cinque righe per `AGENTS.md`)

1. Prima di lavorare a un grafo: `python3 .agents/script/corsa.py apri <grafo> --avviato-da conversazione --sessione <id della sessione>`; stampa l'id, tienilo.
2. **Prima di ogni passo**, nell'ordine del grafo (per i passi con lo stesso `dopo`, uno alla volta): `corsa.py passo <id> <passo> inizio` (controlla anche se qualcuno ha chiesto lo stop), fai il lavoro del passo, poi `passo <id> <passo> fatto --esito "<cosa hai prodotto>"` (o `fallito --nota "<perché>"`). Un passo `umano` si segna `fatto` quando hai consegnato, scrivendo cosa aspetta l'utente.
3. Se un passo dura a lungo, lancia `corsa.py battito <id>` ogni pochi minuti: senza segni per 20 minuti il pannello mostra la corsa «persa».
4. Alla fine: `corsa.py chiudi <id> finita` (o `fallita` se un passo è fallito e non si recupera), e dici all'utente cosa è successo, passo per passo.
5. Se un comando di `corsa.py` esce con 3, o un hook nega un passo, la corsa è stata fermata: ti fermi subito, non riprovi, non cambi strada, non la chiudi; scrivi una riga in `memoria/LOG.md` e dici all'utente che si è fermata e a quale passo.
