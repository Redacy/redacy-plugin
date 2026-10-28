# redacy-start

Plugin per Claude Code. Mette in ordine i dati dello studio e li prepara per un assistente gestito.

## Cosa fa

Otto skill, in italiano:

- `/redacy-start:ordina-dati` riordina le cartelle e scrive un indice. Sposta solo dopo un sì.
- `/redacy-start:impara-lo-studio` salva le regole dello studio come pagine brevi.
- `/redacy-start:chiedi-allo-studio` risponde dalla memoria, citando le fonti.
- `/redacy-start:prepara-bundle` scrive checklist e manifesto con impronte dei file.
- `/redacy-start:inizia` prepara cartelle, tre file del periodo e un CLAUDE.md breve.
- `/redacy-start:pianifica-periodo` costruisce obiettivo e todo con te.
- `/redacy-start:parcheggia-idea` mette le idee in coda senza dirottare il periodo.
- `/redacy-start:giro-del-giorno` dice cosa fare per primo e cosa è fermo.

## Come si prova in locale

```
claude --plugin-dir /percorso/di/plugin-redacy-v0
```

Poi digita `/redacy-start:` e scegli una skill.

Per provare anche il marketplace di prova:

```
claude plugin validate /percorso/di/plugin-redacy-v0
claude plugin marketplace add /percorso/di/plugin-redacy-v0
claude plugin install redacy-start@redacy-prova
```

## Cosa non fa

- Non contatta servizi esterni.
- Non installa software.
- Non legge né chiede chiavi e password.
- Non sposta né cancella file senza conferma.
- Non è l'assistente gestito: prepara i dati, niente altro.

Versione 0.2.0, provvisoria.
