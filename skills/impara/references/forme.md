# Le sei forme

I nomi tecnici di questa pagina sono per te: all'utente dici le sue parole (vedi "Come parli con l'utente" in `SKILL.md`). Dopo un lavoro, ciò che hai imparato ha una forma sola, quella che costa meno e regge di più. Parti dalla prima domanda e scendi. Ti fermi alla prima forma che calza.

## Il criterio

1. È un fatto, o un modo di decidere? Pagina di memoria.
2. È un limite o un permesso (cosa fai da solo, cosa lasci all'utente, cosa vale in una cartella)? Regola.
3. È una procedura che rifarai con la guida di un modello, con passi che cambiano da caso a caso? Skill.
4. È deterministica: stessi passi, stesso esito ogni volta, senza giudizio? Script.
5. È un controllo da fare dopo ogni scrittura o prima di un'azione? Controllo automatico (hook).
6. È ripetuta, a passi fissi, e potrebbe girare senza l'utente? Processo a passi fissi (grafo).

Se due forme calzano, prendi la più piccola. Una pagina oggi, un processo quando la pagina è stata applicata tre volte uguale.

## Le forme, con un esempio

Gli esempi sono di uno studio di commercialista inventato.

- Pagina di memoria, in `memoria/`. Un fatto: "i clienti in forfettario non ricevono la fattura elettronica con IVA". Un modo di decidere: "se un cliente non risponde entro dieci giorni, si manda un secondo avviso e basta".
- Regola, in `.agents/policy/cosa-faccio-da-solo.md` o in `.agents/regole/`. Un permesso: "preparare le bozze delle lettere ai clienti: da solo". Un limite: "spedire le lettere: lascio a te". Una regola per cartella: "in `Pratiche 2026/` i file si chiamano cliente-anno-tipo".
- Skill, in `.agents/skills/<nome>/`. "Preparare la pratica di una dichiarazione": apri la cartella del cliente, guarda quali documenti ci sono, decidi cosa manca. I passi cambiano col cliente e serve giudizio. Se serve a un'area di lavoro sola, va in `workspace/<nome>/.agents/skills/`.
- Script, accanto alla skill che lo usa, in `scripts/`. "Sommare le ritenute di un elenco di fatture esportato in CSV": sempre gli stessi conti, nessun giudizio. Python 3 con la sola libreria standard.
- Controllo automatico (hook), in `.agents/hooks/`. "Dopo ogni scrittura in `periodo/todo.json`, controlla che il file sia valido." Oppure: "prima di scrivere in `Pratiche 2026/`, controlla che il nome del file segua la regola".
- Processo a passi fissi, in `grafi/<nome>.yaml`, con la skill `crea-grafo`. "Ogni lunedì alle 8 leggi il foglio delle scadenze, prepara l'elenco della settimana, e lascia all'utente il passo di invio." È ripetuto, ha passi fissi e gira anche senza l'utente. Il passaggio da area di lavoro a processo è uno degli esiti di `impara`: nasce quando un lavoro fatto più volte in un'area ha sempre la stessa forma.

## Come proporre

- Una forma sola, con il motivo in una riga: "Ti propongo una procedura che tengo qui nello studio, perché i passi cambiano con ogni cliente e li decidi tu."
- Le altre scartate, una riga ciascuna: "Non un calcolo fisso: c'è giudizio a metà. Non un processo a passi fissi: non gira senza di te."
- Poi aspetti. Decide l'utente.

## Dove si sbaglia

- Uno script per un lavoro con giudizio: si rompe al primo caso strano.
- Una skill per un fatto: basta una pagina.
- Un processo a passi fissi per un lavoro fatto una volta: aspetta la seconda e la terza.
- Una regola scritta dove Codex non arriva: in Codex `.agents/` è in sola lettura, la riga va in `memoria/regole-in-attesa.md` (vedi `SKILL.md`).
- Una regola di permesso che nasce da un solo "vai": serve la parola esplicita dell'utente.
