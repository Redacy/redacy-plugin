# redacy

Plugin gratuito di Redacy per Claude Code e per Codex (serve un tuo account, il costo del servizio AI è a parte). Mette in ordine i dati dello studio e tiene il periodo di lavoro. È l'ingresso: quando i dati sono in ordine, Redacy può affiancarti con un agente AI gestito.

## Per chi è

Professionisti e piccole aziende con processi tecnici ripetuti, i cui dati sono sparsi in cartelle, mail e fogli.

## Cosa fa

Otto skill, in italiano:

- `ordina-dati` riordina le cartelle e scrive un indice. Sposta solo dopo un sì.
- `impara-lo-studio` salva le regole dello studio come pagine brevi e impara dalle correzioni.
- `chiedi-allo-studio` risponde dalla memoria, citando le fonti.
- `prepara-bundle` scrive checklist e manifesto con impronte dei file.
- `inizia` prepara cartelle, tre file del periodo e un CLAUDE.md breve.
- `pianifica-periodo` costruisce obiettivo e todo con te.
- `parcheggia-idea` mette le idee in coda senza dirottare il periodo.
- `giro-del-giorno` dice cosa fare per primo e cosa è fermo.

## Installazione

Il repo `Redacy/redacy-plugin` è privato: per ora installa solo chi ha accesso.

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

Apri poi una nuova sessione. In Claude Code le skill si chiamano `/redacy:<nome>`.

Per provare dalla cartella locale:

```
claude --plugin-dir /percorso/del/plugin
claude plugin validate /percorso/del/plugin
```

## Cosa fa e cosa non fa

- Lavora solo nella cartella che scegli.
- Non apre connessioni proprie, non installa software, non legge né chiede chiavi e password. I testi che legge passano dal servizio AI che usi (Claude Code o Codex), con le sue regole sui dati.
- Non sposta né cancella file senza un sì.
- Una persona rivede il risultato prima che esca: soldi, atti legali e invii restano tuoi.
- Non è l'agente gestito: prepara i dati, niente altro.

## Licenza

MIT, vedi `LICENSE`.

Versione 0.2.0-rc1, candidata al rilascio.
