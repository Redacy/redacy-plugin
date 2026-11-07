# Esempio: il piano di uno studio finto

Studio Verdi, commercialista inventato, tre persone. Dati di fantasia. Oggi è il 2026-11-07.

## Prima

`periodo/obiettivo.md`, già scritto dall'utente e da non toccare:

    Chiudere le liquidazioni IVA di ottobre per tutti i clienti.
    Fatto quando: le tre liquidazioni sono inviate e le ricevute sono in fonti/.

`periodo/todo.json`:

    {"versione": "0.3.0", "periodo": "2026-11", "todo": [
      {"id": "t1", "cosa": "Riordinare le fatture di ottobre di Rossi Srl", "chi": "agente",
       "stato": "fatto", "scadenza": "2026-11-05", "dove": "workspace/contabilita",
       "da": "piano", "aggiornato": "2026-11-05"},
      {"id": "t2", "cosa": "Controllare i totali della liquidazione di Rossi Srl", "chi": "tu",
       "stato": "da fare", "scadenza": "2026-11-12", "dove": "", "da": "piano",
       "aggiornato": "2026-11-05"},
      {"id": "t3", "cosa": "Scegliere il gestionale per le fatture elettroniche", "chi": "tu",
       "stato": "ferma", "scadenza": "", "dove": "", "da": "piano",
       "aggiornato": "2026-10-01",
       "nota": "Aspetta la tua scelta fra i due preventivi, dal 2026-10-01"}
    ]}

`periodo/idee.json`:

    {"versione": "0.3.0", "periodo": "2026-11", "idee": [
      {"id": "i1", "idea": "Mandare un promemoria ai clienti prima di ogni scadenza",
       "da_dove": "conversazione", "arrivata": "2026-11-03"},
      {"id": "i2", "idea": "Riordinare tutto l'archivio del 2024",
       "da_dove": "utente", "arrivata": "2026-11-04"}
    ]}

## Cosa dice l'agente

Il quadro: l'obiettivo è in corso. Una voce fatta (t1). Una da fare entro il 12 (t2). Una decisione ferma da 37 giorni (t3). Due idee in attesa.

Poi, in prosa, due domande.

La prima: la decisione sul gestionale è ferma da oltre 30 giorni. Puoi decidere ora, parcheggiarla o dimenticarla. Decidere costa mezz'ora e sblocca le fatture di dicembre. Parcheggiarla la toglie dal quadro e non cambia niente fino a gennaio. Io ti consiglio di decidere questa settimana, perché dicembre è già pieno.

La seconda: il promemoria ai clienti (i1) aiuterebbe, ma l'obiettivo di questo periodo sono le liquidazioni. Portarlo ora vuol dire un'ora di lavoro dell'agente e un testo da farti approvare. Rimandarlo costa una settimana di ritardo. Ti consiglio di rimandarlo a dopo l'invio delle liquidazioni. L'archivio del 2024 (i2) lo scarterei: non c'entra con nessuna scadenza.

Poi l'agente si ferma. Non scrive niente.

## Dopo

L'utente risponde: "Il gestionale lo scelgo lunedì. Il promemoria portalo nel periodo, ma preparami solo la bozza. L'archivio scartalo."

`periodo/obiettivo.md`: identico a prima. L'utente non ha chiesto di cambiarlo.

`periodo/todo.json`, con due cose cambiate. La voce t3 passa a `da fare` con scadenza lunedì. In fondo c'è una voce nuova con id `t4`, il successivo a quello più alto:

    {"id": "t3", "cosa": "Scegliere il gestionale per le fatture elettroniche", "chi": "tu",
     "stato": "da fare", "scadenza": "2026-11-09", "dove": "", "da": "piano",
     "aggiornato": "2026-11-07"},
    {"id": "t4", "cosa": "Preparare la bozza del promemoria ai clienti", "chi": "agente",
     "stato": "da fare", "scadenza": "", "dove": "", "da": "piano",
     "aggiornato": "2026-11-07"}

L'invio ai clienti non è un todo dell'agente: resta all'utente.

`periodo/idee.json`, con l'esito sulle due idee:

    {"id": "i1", "idea": "Mandare un promemoria ai clienti prima di ogni scadenza",
     "da_dove": "conversazione", "arrivata": "2026-11-03",
     "esito": {"stato": "portata nel periodo", "data": "2026-11-07",
               "perche": "L'utente vuole la bozza ora, l'invio lo decide lui", "todo": "t4"}},
    {"id": "i2", "idea": "Riordinare tutto l'archivio del 2024",
     "da_dove": "utente", "arrivata": "2026-11-04",
     "esito": {"stato": "scartata", "data": "2026-11-07",
               "perche": "Non c'entra con nessuna scadenza del periodo"}}

Poi i due controlli escono 0, e in fondo a `memoria/LOG.md` arriva una riga:

    - 2026-11-07 10:30 · periodo · Piano aggiornato: 1 idea portata (t4), 1 scartata, decisione sul gestionale ripresa, obiettivo invariato.
