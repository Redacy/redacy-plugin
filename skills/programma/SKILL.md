---
name: programma
description: Guida a far partire da solo, a un orario o a un ritmo, un processo a passi fissi (un grafo in grafi/) o il giro del giorno, con l'attività programmata di Claude o la programmazione di Codex. Si usa quando l'utente dice "fallo ogni lunedì", "fallo partire da solo", "ricordamelo ogni mese", "ogni mattina alle 8 fammi il giro", "programma questo processo", "che giri tutte le notti".
---

# Programma

Il plugin non fa partire niente da solo e non ha un suo orologio. A far partire il lavoro è lo strumento del programma che l'utente usa: l'attività programmata di Claude o quella di Codex. Questa skill ti guida a crearla e a farlo con le regole giuste.

Quello che gira da solo è un lavoro senza nessuno davanti. Per questo la skill tratta con cura i limiti e le regole (sotto).

## Come parli con l'utente

Le parole di questa skill sono per te. All'utente dici "farlo partire da solo", "ogni lunedì alle 8", "il processo delle scadenze" (non grafo), "è partito da solo" (non corsa, non avviato_da), "l'attività programmata" con il nome che vede nell'app. Non dici cron, RRULE, prompt, token. Il prompt dell'attività glielo mostri com'è, dicendo che è il testo che lei userà ogni volta. Una domanda alla volta, niente lodi.

## Prima di cominciare

- Leggi `AGENTS.md` e, se c'è, `memoria/attivita-programmate.md`: potrebbe già esserci quella che l'utente chiede.
- Guarda i nomi in `grafi/`. Con l'utente parla di "processo" o "procedura", come lo chiama lui.
- Chiedi in una frase quale programma usa: Claude o Codex. Poi segui solo la sua strada.

## Passi

1. **Chiedi cosa deve girare.** Una domanda: "Quale processo vuoi far partire da solo? Oppure il giro del giorno?" Se il processo non esiste ancora, usa `crea-grafo` e poi torna qui.
2. **Chiedi quando.** Una domanda: giorno e ora, oppure ogni quanto. Dì subito un limite vero: nei moduli dell'app il ritmo minimo è un'ora (sotto, "Limiti").
3. **Controlla che sia adatto a girare da solo.** Leggi le righe in `.agents/policy/`.
   - Se il processo tocca un cliente, soldi, una firma o un invio, non lo programmare così com'è. Proponi che prepari la bozza e una voce in `periodo/todo.json` per l'utente.
   - Se il processo non è mai girato con l'utente davanti, fai prima una corsa a mano con lui. Poi si programma.
4. **Scrivi il prompt dell'attività** e mostralo. Aspetta il sì prima di andare avanti (sotto, "Il prompt").
5. **Guida alla creazione** nello strumento giusto (sotto, "Claude" o "Codex").
6. **Fai provare una volta, con lui presente.** Una prima esecuzione a mano, guardando insieme cosa succede e rispondendo ai permessi che chiede. Non è verificato che una sessione programmata carichi il plugin: se non trova la skill `crea-grafo` o `giro-del-giorno`, dillo all'utente e non dichiarare l'attività pronta.
7. **Segna l'attività** (sotto, "Cosa scrivi in memoria").

## Il prompt

Breve. Dice di leggere `AGENTS.md` della cartella e di eseguire il processo o il giro. Non spiega i passi: quelli stanno nel processo.

Per un processo a passi fissi, sostituisci il nome:

    Lavora nella cartella dello studio. Leggi AGENTS.md. Poi esegui il grafo grafi/<nome>.yaml come dice AGENTS.md. Apri la corsa con: python3 .agents/script/corsa.py apri <nome> --avviato-da <attivita-claude o automazione-codex>. Rispetta le regole in .agents/policy/. Non mandare niente a nessuno e non toccare clienti o soldi: se un passo lo richiede, fermati e scrivilo nella corsa.

Nel prompt scrivi il valore giusto al posto delle parentesi: `attivita-claude` se l'attività è di Claude, `automazione-codex` se è di Codex. Sono i due valori che il registro delle corse accetta per un avvio programmato (gli altri due sono `conversazione` e `utente`, per chi lancia a mano). Il prompt è per il modello: qui i nomi tecnici vanno bene.

Per il giro del giorno:

    Lavora nella cartella dello studio. Leggi AGENTS.md. Poi fai il giro del giorno con la skill giro-del-giorno e scrivi qui il risultato. Controlla la data di oggi: se è passato più di un giorno dall'orario previsto, dillo prima di tutto.

Se per Codex vuoi richiamare la skill con il suo modo (`$nome-skill`), puoi: la documentazione lo dice per l'app. Lascia comunque il nome in parole.

## Claude

Sono tre strade. Una sola va bene per una cartella con dati veri.

**L'app Claude (scheda Code).** È la strada giusta: gira sul computer dell'utente, vede la cartella e i collegamenti. I passi:

- Nella barra laterale della scheda Code, la voce Scheduled (in alcune versioni si chiama Routines). Poi New task.
- Se compare un menu con "Create with Claude" e "Set up manually", scegli "Set up manually".
- Un nome (minuscolo con i trattini, unico fra le sue attività), le istruzioni (il prompt), poi Advanced settings e l'interruttore "Only on this computer".
- "Local folder": la cartella dello studio.
- Il ritmo: Hourly, Daily, Weekdays, Weekly. Il ritmo Custom e quello Manual si scelgono dopo, da Edit. Un ritmo più fitto dell'ora il modulo lo rifiuta.
- Il modo dei permessi e il modello, poi Create.

Le finestre cambiano da una versione all'altra: se non vedi questi nomi, cerca gli stessi campi (nome, istruzioni, cartella, ritmo, solo su questo computer). In alternativa, in una sessione dell'app l'utente scrive la richiesta con le sue parole ("ogni lunedì alle 8 fammi il giro del giorno") e Claude crea l'attività.

**`/schedule` dal terminale.** Crea un'attività nel cloud di Anthropic: parte con una copia nuova di un repository GitHub e senza i file del computer. Per la cartella dello studio non va bene: lì stanno i file dell'utente e non devono uscire. Dillo, e non crearla.

**`/loop`.** Gira solo mentre la sessione è aperta, e quelle ricorrenti scadono dopo sette giorni. Va bene per provare, non per programmare.

Per cambiarla dopo: nella pagina dell'attività ci sono Run now, Status (Active o Paused), Edit, History, Delete.

## Codex

Nell'app, la voce si chiama Scheduled (la documentazione parla di attività programmate; in altre versioni si chiama automazione).

- L'utente apre una chat di Codex sulla cartella dello studio e chiede, con le sue parole, di creare un'attività con quel prompt, a quel ritmo, e che ogni esecuzione parta in una chat nuova.
- Un ritmo particolare lo dà in Custom o con una regola RRULE.
- Se la cartella è sotto Git, fai scegliere il progetto locale e non una copia nuova: in una copia, la memoria scritta finirebbe fuori dalla cartella. (Deduzione: la pagina dice solo che i worktree tengono separate le modifiche.)
- Le esecuzioni compaiono in Scheduled, con un segno per quelle da guardare.

La pagina non dà i clic uno per uno: se l'utente non trova il punto, può chiederlo a Codex in chat. Se non ha l'app ma solo il terminale, `codex exec` è il comando che esegue un prompt senza interfaccia; legarlo a un orario con l'orologio del computer non è uno strumento di Codex e non ti guido a farlo.

## Limiti, detti all'utente

- **Computer acceso e sveglio.** Claude: se il computer dorme all'ora prevista, l'esecuzione è saltata e al risveglio ne parte una sola, in ritardo. L'app ha un'opzione "Keep computer awake". Codex: computer acceso, app aperta, cartella sul disco.
- **La cartella deve essere raggiungibile.** Su un disco esterno scollegato o su una cartella non sincronizzata, l'esecuzione non parte. (Per Codex è una deduzione: la pagina dice "il progetto ancora sul disco".)
- **I permessi.** Un'attività senza nessuno davanti si ferma se Claude o Codex chiedono un permesso. In Codex, nel modo "workspace-write" falliscono le chiamate alla rete e ai collegamenti: un processo che legge la posta potrebbe non girare. Non ti consiglio l'accesso completo per un lavoro da solo. Alla prima prova, approva solo ciò che il processo serve davvero.
- **Niente clienti e niente soldi, da solo.** Una corsa non presidiata non scrive ai clienti, non manda niente, non paga e non firma. Usa le righe in `.agents/policy/`. Se il processo ne ha bisogno, prepara la bozza e lascia all'utente l'ultimo gesto.
- **Dove si vede.** Quando gira, l'agente scrive una corsa in `grafi/corse/`, e il pannello la mostra come "partito da solo". Se l'attività gira ma il pannello non mostra niente, la corsa non è stata registrata: guarda la cronologia dell'attività nello strumento e dillo all'utente.

## Cosa scrivi in memoria

Dopo la prima esecuzione riuscita:

1. Se `memoria/attivita-programmate.md` non c'è, la crei: titolo, una riga che dice cosa contiene, un collegamento `[[fonti-dati]]` se ci sono fonti collegate, e l'elenco. Poi aggiungi una riga a `memoria/INDICE.md`, nello stesso formato di quelle che ci sono, con `[[attivita-programmate]]`.
2. Una riga per attività: `- <cosa> · <quando> · <Claude o Codex> · AAAA-MM-GG`. Se l'utente cambia o toglie l'attività, aggiungi una riga che lo dice: non riscrivere le vecchie.
3. In fondo a `memoria/LOG.md`: `- AAAA-MM-GG HH:MM · corsa · programmato <cosa> <quando> con <Claude o Codex>`.

La pagina resta sotto le trecento parole. Se cresce, dividila per strumento.

## Cosa non fai

- Non crei un tuo orologio, uno script o una regola di sistema.
- Non programmi niente che spedisca, paghi o firmi.
- Non scrivi il prompt senza il sì dell'utente.
- Non crei attività nel cloud per la cartella dello studio.
- Non dai per certo ciò che non hai letto: se un passo dell'app non torna, dillo e chiedi all'utente cosa vede.

## Documentazione

- Claude, confronto fra i tipi di attività e `/loop`: https://code.claude.com/docs/en/scheduled-tasks
- Claude, attività programmate dell'app (sul computer): https://code.claude.com/docs/en/desktop-scheduled-tasks
- Claude, attività nel cloud e `/schedule`: https://code.claude.com/docs/en/routines
- Codex, attività programmate dell'app: https://learn.chatgpt.com/docs/automations?surface=app (l'indirizzo vecchio, developers.openai.com/codex/app/automations, rimanda qui)
- Codex, uso senza interfaccia (`codex exec`): https://learn.chatgpt.com/docs/non-interactive-mode (vecchio: developers.openai.com/codex/noninteractive)
