#!/usr/bin/env python3
# redacy 0.4.1 · prove/pannello/_prepara.py
"""Prepara una cartella dello studio di prova per le prove del pannello.

Uso: python3 _prepara.py <cartella> [--plugin RADICE] [--corse]

Crea la cartella con crea-cartella.py (di `inizia`), poi ci mette dati inventati: lo studio di una
commercialista finta (Studio Ferrante), due aree di lavoro, pagine di memoria collegate (una citata
e non scritta), cose da fare, un obiettivo, il registro e un grafo. Con --corse scrive anche una
corsa per stato (finita, fallita, fermata, in corso, persa) usando corsa.py, e stampa gli id.
Nessun dato vero. Solo libreria standard.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
RADICE = os.path.normpath(os.path.join(QUI, "..", ".."))


def scrivi(cartella, rel, testo):
    p = os.path.join(cartella, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(testo)


def corsa(cartella, *args):
    script = os.path.join(cartella, ".agents", "script", "corsa.py")
    r = subprocess.run([sys.executable, script] + list(args) + ["--cartella", cartella], capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


GRAFO = """grafo: giro-scadenze
versione: 1
obiettivo: Ogni lunedì trova le scadenze dei clienti e prepara i promemoria in bozza.
descrizione: |
  Legge il foglio delle scadenze, trova chi scade entro due settimane e prepara una bozza per ogni cliente.
acceso: false
innesco: {tipo: orario, quando: "ogni lunedì alle 08:30 Europe/Rome"}
passi:
  - id: leggi-foglio
    tipo: cli
    nome: Legge il foglio delle scadenze
    comando: python3 .agents/script/leggi-foglio.py
  - id: trova-scadenze
    tipo: agente
    nome: Trova chi scade
    workspace: scadenze
    prompt: Trova i clienti con una scadenza entro due settimane
  - id: bozze
    tipo: uscita
    nome: Promemoria in bozza
    forma: bozza
    dove: la tua casella di posta, in bozze
  - id: spedisci
    tipo: umano
    nome: Rileggi e spedisci
    forma: invio
    dove: la tua casella di posta, in bozze
tetti:
  contemporanee: 1
  corse_al_giorno: 2
uscite: [promemoria in bozza]
autonomia: {livello: L0, da: "2026-11-07", si: null}
"""

WORKSPACE_AGENTS = {
    "dichiarazioni": ("# Dichiarazioni\n\nPrepara la pratica di ogni cliente e controlla che ci siano tutti i documenti.\n",
                      {"checklist-documenti": "# Checklist dei documenti\n\nCosa serve per una dichiarazione. Vedi [[procedura-dichiarazioni]] e [[modello-730]].\n",
                       "procedura-dichiarazioni": "# Procedura locale\n\nI passi dell'area. Vedi [[checklist-documenti]].\n"}),
    "scadenze": ("# Scadenze\n\nTiene il foglio delle scadenze e prepara i promemoria.\n",
                 {"calendario-fiscale": "# Calendario fiscale\n\nLe date che contano. Collegata a [[clienti]].\n"}),
}

MEMORIA = {
    "studio": "# Studio Ferrante\n\nLo studio di una commercialista: pratiche, scadenze, dichiarazioni.\n",
    "clienti": "# Clienti\n\nLe persone e le aziende seguite. Vedi [[procedura-dichiarazioni]] e [[scadenze-fiscali]].\n",
    "procedura-dichiarazioni": "# Come si prepara una dichiarazione\n\nDodici passi, dalla raccolta dei documenti alla firma. Usa [[clienti]] e [[stile-delle-mail]].\n\nEsempio di collegamento nel codice: `[[non-contare-questo]]`.\n",
    "stile-delle-mail": "# Come scriviamo ai clienti\n\nDel lei, frasi corte, la scadenza in fondo. Vedi [[clienti]].\n",
}

INDICE = """# Indice

La porta della memoria dello studio.

## Lo studio
- [[studio]] · chi siamo
- [[fonti-dati]] · dove stanno i dati

## Procedure
- [[procedura-dichiarazioni]]
- [[stile-delle-mail]]

## Persone e clienti
- [[clienti]]

## Da scoprire
- [[scadenze-fiscali]]
"""

TODO = {
    "versione": "0.3.0", "periodo": "Novembre 2026",
    "todo": [
        {"id": "t1", "cosa": "Rileggere le bozze dei promemoria", "chi": "tu", "stato": "da fare", "scadenza": "2026-11-05",
         "dove": "grafi/giro-scadenze.yaml", "da": "giro", "aggiornato": "2026-11-05"},
        {"id": "t2", "cosa": "Caricare il foglio delle scadenze aggiornato", "chi": "tu", "stato": "da fare", "scadenza": "2099-01-01",
         "dove": "fonti", "da": "utente", "aggiornato": "2026-11-06"},
        {"id": "t3", "cosa": "Preparare la pratica di un cliente di prova", "chi": "agente", "stato": "in corso", "scadenza": "",
         "dove": "workspace/dichiarazioni", "da": "piano", "aggiornato": "2026-11-06"},
        {"id": "t4", "cosa": "Aggiornare il calendario fiscale", "chi": "agente", "stato": "fatto", "scadenza": "",
         "dove": "workspace/scadenze", "da": "piano", "aggiornato": "2026-11-04"},
    ],
}

IDEE = {"versione": "0.3.0", "periodo": "Novembre 2026",
        "idee": [{"id": "i1", "idea": "Un riepilogo mensile per ogni cliente", "da_dove": "conversazione",
                  "arrivata": "2026-11-04", "esito": None}]}

LOG = [
    "- 2026-11-04 09:05 · workspace · Creata l'area di lavoro scadenze",
    "- 2026-11-05 18:02 · periodo · Fatto: calendario fiscale aggiornato",
    "- 2026-11-06 12:40 · impara · Salvata la regola: i promemoria citano sempre la scadenza",
]


def prepara(cartella, plugin, con_corse):
    os.makedirs(cartella, exist_ok=True)
    r = subprocess.run([sys.executable, os.path.join(plugin, "skills", "inizia", "scripts", "crea-cartella.py"), cartella,
                        "--plugin", plugin], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("crea-cartella.py è uscito con %d: %s" % (r.returncode, r.stderr or r.stdout))
    script_b = os.environ.get("REDACY_SCRIPT_GRAFI")
    if script_b:  # prima della fusione di B: le sue copie di lavoro
        for n in ("corsa.py", "yaml_ridotto.py", "controlla-grafo.py"):
            if not os.path.isfile(os.path.join(cartella, ".agents", "script", n)) and os.path.isfile(os.path.join(script_b, n)):
                dest = os.path.join(cartella, ".agents", "script", n)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(os.path.join(script_b, n), "rb") as s, open(dest, "wb") as d:
                    d.write(s.read())
    scrivi(cartella, "memoria/INDICE.md", INDICE)
    for nome, testo in MEMORIA.items():
        scrivi(cartella, "memoria/%s.md" % nome, testo)
    for nome, (agents, pagine) in WORKSPACE_AGENTS.items():
        scrivi(cartella, "workspace/%s/AGENTS.md" % nome, agents)
        scrivi(cartella, "workspace/%s/CLAUDE.md" % nome, "@AGENTS.md\n")
        for pn, pt in pagine.items():
            scrivi(cartella, "workspace/%s/memoria/%s.md" % (nome, pn), pt)
    scrivi(cartella, "periodo/obiettivo.md", "# Obiettivo del periodo\n\nChiudere le dichiarazioni dei clienti entro il 30 novembre.\n")
    scrivi(cartella, "periodo/todo.json", json.dumps(TODO, ensure_ascii=False, indent=2) + "\n")
    scrivi(cartella, "periodo/idee.json", json.dumps(IDEE, ensure_ascii=False, indent=2) + "\n")
    scrivi(cartella, "fonti/scadenze.xlsx.txt", "foglio finto\n")
    scrivi(cartella, "fonti/pratiche/LEGGIMI.txt", "una cartella finta\n")
    scrivi(cartella, "grafi/giro-scadenze.yaml", GRAFO)
    with open(os.path.join(cartella, "memoria", "LOG.md"), "a", encoding="utf-8") as f:
        f.write("\n".join(LOG) + "\n")
    ids = {}
    if con_corse:
        ids = scrivi_corse(cartella)
    return ids


def scrivi_corse(cartella):
    ids = {}
    passi = ["leggi-foglio", "trova-scadenze", "bozze", "spedisci"]

    def apri(sessione):
        c, out, err = corsa(cartella, "apri", "giro-scadenze", "--avviato-da", "conversazione", "--sessione", sessione)
        if c != 0:
            raise SystemExit("corsa.py apri è uscito con %d: %s" % (c, err or out))
        return out.splitlines()[-1].strip()

    # una finita
    i = apri("sess-finita")
    for p in passi:
        corsa(cartella, "passo", i, p, "inizio")
        corsa(cartella, "passo", i, p, "fatto", "--esito", "ok %s" % p)
    corsa(cartella, "chiudi", i, "finita")
    ids["finita"] = i
    # una fallita
    i = apri("sess-fallita")
    corsa(cartella, "passo", i, passi[0], "inizio")
    corsa(cartella, "passo", i, passi[0], "fatto", "--esito", "foglio letto")
    corsa(cartella, "passo", i, passi[1], "inizio")
    corsa(cartella, "passo", i, passi[1], "fallito", "--nota", "Manca la colonna delle scadenze")
    corsa(cartella, "chiudi", i, "fallita")
    ids["fallita"] = i
    # una fermata dal pannello
    i = apri("sess-fermata")
    corsa(cartella, "passo", i, passi[0], "inizio")
    corsa(cartella, "passo", i, passi[0], "fatto", "--esito", "foglio letto")
    corsa(cartella, "passo", i, passi[1], "inizio")
    corsa(cartella, "ferma", i, "--da", "pannello", "--perche", "Lo faccio io oggi")
    ids["fermata"] = i
    # una persa: in corso, senza segni di vita da un'ora
    i = apri("sess-persa")
    corsa(cartella, "passo", i, passi[0], "inizio")
    p = os.path.join(cartella, "grafi", "corse", i + ".json")
    with open(p, encoding="utf-8") as f:
        dato = json.load(f)
    vecchio = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    dato["ultimo_segno"] = vecchio
    dato["inizio"] = vecchio
    with open(p, "w", encoding="utf-8") as f:
        json.dump(dato, f, ensure_ascii=False, indent=2)
    ids["persa"] = i
    # una in corso, viva
    i = apri("sess-viva")
    corsa(cartella, "passo", i, passi[0], "inizio")
    corsa(cartella, "passo", i, passi[0], "fatto", "--esito", "foglio letto")
    corsa(cartella, "passo", i, passi[1], "inizio")
    ids["in-corso"] = i
    return ids


def main():
    ap = argparse.ArgumentParser(description="Prepara una cartella dello studio di prova per il pannello.")
    ap.add_argument("cartella")
    ap.add_argument("--plugin", default=RADICE, help="la radice del plugin (default: questo repo)")
    ap.add_argument("--corse", action="store_true", help="scrive anche una corsa per stato e ne stampa gli id")
    a = ap.parse_args()
    ids = prepara(os.path.realpath(a.cartella), os.path.realpath(a.plugin), a.corse)
    for k in sorted(ids):
        print("%s=%s" % (k, ids[k]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
