# Le prove

Per chi sviluppa il plugin. Chi lo usa non ha bisogno di questa cartella.

```
bash prove/tutte.sh
claude plugin validate --strict .
```

`prove/tutte.sh` lancia le prove senza modello: una riga per prova, in fondo `ESITO: PASSA` o `ESITO: FALLISCE`. Dura meno di un minuto. Servono Python 3, bash e curl. La prova della pagina vera nel browser (`prove/pannello/prova-pagina.sh`) usa anche Node 22 e un Chromium; se mancano, quella parte salta e lo dice.

La pagina del pannello si fa in pezzi in `skills/pannello/sorgenti/` (il guscio con la scrivania, le finestre e il dock, i contenuti dei cinque pannelli, la fonte dei dati) e si monta in `skills/pannello/scripts/pagina.html` con `python3 skills/pannello/sorgenti/costruisci.py`. Cosa deve reggere sta in `skills/pannello/sorgenti/CONTRATTO.md`.

Le prove con un modello chiamano Claude Code o Codex con il tuo account: `prove/catena-claude.sh` e `prove/catena-codex.sh` seguono la catena inizia, crea-workspace, crea-grafo, corsa, pannello, stop; le prove di un solo pezzo stanno in `prove/inizia/prova-onboarding-*.sh`, `prove/grafi/prova-crea-*.sh` e `prove/ordina/prova-riordina-claude.sh`.

Per provare il plugin da una cartella locale, senza installarlo: `claude --plugin-dir /percorso/del/plugin`. Su Codex: `codex plugin marketplace add /percorso/del/plugin`, poi `codex plugin add redacy@redacy`.

Le parti scritte per Windows (il pannello che resta acceso, i lucchetti dei file, i controlli automatici) sono provate in simulazione con `prove/windows/prova-portabile.sh`. Una cartella nata su un Mac e poi spostata su Windows tiene i comandi vecchi: si cancellano i tre file dei controlli e si rilancia `inizia`.
