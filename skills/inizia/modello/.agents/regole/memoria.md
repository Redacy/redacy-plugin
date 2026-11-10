---
paths:
  - "memoria/**"
  - "workspace/*/memoria/**"
summary: una pagina breve per cosa, collegata con [[nome-pagina]] e scritta in INDICE.md; il registro LOG.md si scrive solo in fondo, una riga per fatto
---
<!-- redacy 0.4.0 · origine nel plugin: skills/inizia/modello/.agents/regole/memoria.md -->

# Come si scrive in memoria

Vale per `memoria/` e per la memoria di ogni area di lavoro (`workspace/<nome>/memoria/`).

1. **Una cosa per pagina**, sotto le 400 parole. Il nome del file in minuscolo, con i trattini: `procedura-dichiarazioni.md`.
2. **In testa alla pagina**: il titolo, una riga «cos'è», da dove viene (il file, la conversazione, la persona) e la data in cui l'hai saputo.
3. **Prima di scrivere una pagina nuova cerca se c'è già.** Se c'è, aggiorni quella: il sapere si integra, non si accumula.
4. **Collegamenti**: `[[nome-pagina]]`, il nome del file senza `.md`. Se colleghi A a B, aggiungi anche il collegamento da B ad A. Un collegamento a una pagina che non c'è ancora è una cosa da scoprire, non un errore.
5. **Ogni pagina nuova entra in `INDICE.md`** con una riga: `- [[nome-pagina]] · cosa dice in poche parole`.
6. **Una procedura** si scrive coi suoi passi numerati, chi fa cosa e cosa serve. Se l'utente l'ha raccontata a voce, gliela fai rileggere.
7. **Un dato non si copia in memoria.** Si segna dove sta, in `fonti-dati.md`.
8. **`LOG.md` si scrive solo in fondo**, una riga per fatto, mai riscritta: `- AAAA-MM-GG HH:MM · <tipo> · <frase>`. Tipi: `inizia`, `impara`, `workspace`, `grafo`, `corsa`, `periodo`, `fonte`.
9. **Dati personali di clienti e persone**: in memoria va il modo di lavorare, non il contenuto delle pratiche. Il nome di un cliente sì, i suoi dati no.
