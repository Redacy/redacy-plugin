# redacy 0.4.0 · skills/crea-workspace/scripts/crea-workspace.py
"""Crea un workspace (un agente intero) dentro la cartella dello studio.

Uso: python3 crea-workspace.py NOME --descrizione "..." [--cartella DIR] [--dati PERCORSO ...]
Solo libreria standard, Python 3.9 o più.
"""

import datetime
import os
import re
import shutil
import sys
import unicodedata

AIUTO = """Uso: python3 crea-workspace.py NOME --descrizione "TESTO" [opzioni]

Crea workspace/NOME/ nella cartella dello studio: un agente intero con
AGENTS.md, CLAUDE.md (che contiene solo "@AGENTS.md"), .agents/ (skills,
regole, policy) e memoria/ con INDICE.md e la scheda NOME.md. I file nascono
dal modello che sta accanto allo script, in modello/.

Poi aggiunge "- [[NOME]] · descrizione" nella memoria/INDICE.md dello studio,
sotto il titolo "## Workspace" (lo crea se manca), e una riga in
memoria/LOG.md dello studio.

Argomenti:
  NOME                    il nome del workspace, in kebab-case italiano
                          (solo minuscole, numeri e trattini: preventivi-officina)
  --descrizione, -d TESTO una frase: cosa fa il lavoro
  --cartella DIR          la cartella dello studio. Se manca la si trova
                          risalendo dalla cartella corrente fino a una che ha
                          AGENTS.md e grafi/ (o dalla variabile REDACY_CARTELLA)
  --dati PERCORSO         dove stanno i dati del lavoro. Si può ripetere.
                          Il dato resta dov'è: si scrive solo il percorso
  -h, --help              mostra questo aiuto

Un workspace che esiste già non si tocca: lo script esce con 2 e non scrive
niente. Aprilo e lavora lì.

Uscite: 0 fatto (stampa i percorsi creati) · 1 uso sbagliato o nome non valido
        · 2 il workspace esiste già.
"""

RE_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RADICE_SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELLO = os.path.join(RADICE_SKILL, "modello")
SCHEDA_MODELLO = os.path.join("memoria", "scheda.md")
CARTELLE_VUOTE = [
    os.path.join(".agents", "skills"),
    os.path.join(".agents", "regole"),
    os.path.join(".agents", "policy"),
    "memoria",
]


class Errore(Exception):
    def __init__(self, codice, testo):
        Exception.__init__(self, testo)
        self.codice = codice
        self.testo = testo


def suggerisci_nome(nome):
    """Il nome in kebab-case piu' vicino a quello scritto."""
    testo = unicodedata.normalize("NFKD", nome)
    testo = "".join(c for c in testo if not unicodedata.combining(c))
    testo = re.sub(r"[^a-z0-9]+", "-", testo.lower()).strip("-")
    return testo


def _e_studio(percorso):
    return os.path.isfile(os.path.join(percorso, "AGENTS.md")) and os.path.isdir(
        os.path.join(percorso, "grafi")
    )


def trova_cartella(esplicita=None):
    scelta = esplicita or os.environ.get("REDACY_CARTELLA")
    if scelta:
        scelta = os.path.abspath(os.path.expanduser(scelta))
        if not _e_studio(scelta):
            raise Errore(
                1,
                "La cartella %s non è una cartella dello studio (servono AGENTS.md e grafi/)."
                % scelta,
            )
        return scelta
    corrente = os.path.abspath(os.getcwd())
    while True:
        if _e_studio(corrente):
            return corrente
        padre = os.path.dirname(corrente)
        if padre == corrente:
            raise Errore(
                1,
                "Non trovo la cartella dello studio risalendo da %s (cerco AGENTS.md e grafi/). "
                "Entra nella cartella dello studio oppure usa --cartella." % os.getcwd(),
            )
        corrente = padre


def leggi_argomenti(argv):
    """Ritorna (nome, descrizione, cartella, dati). Solleva Errore(1) se l'uso e' sbagliato."""
    nome = None
    descrizione = None
    cartella = None
    dati = []
    i = 0
    valore_di = {"--descrizione": "descrizione", "-d": "descrizione", "--cartella": "cartella", "--dati": "dati"}
    while i < len(argv):
        a = argv[i]
        i += 1
        if a in ("-h", "--help"):
            sys.stdout.write(AIUTO)
            sys.exit(0)
        chiave = None
        valore = None
        if a.startswith("--") and "=" in a:
            chiave, valore = a.split("=", 1)
        elif a in valore_di:
            chiave = a
            if i >= len(argv):
                raise Errore(1, "Dopo %s serve un valore." % a)
            valore = argv[i]
            i += 1
        if chiave is not None:
            if chiave not in valore_di:
                raise Errore(1, "Opzione sconosciuta: %s. Guarda --help." % chiave)
            quale = valore_di[chiave]
            if quale == "descrizione":
                descrizione = valore
            elif quale == "cartella":
                cartella = valore
            else:
                dati.append(valore)
            continue
        if a.startswith("-") and len(a) > 1:
            raise Errore(1, "Opzione sconosciuta: %s. Guarda --help." % a)
        if nome is not None:
            raise Errore(1, "Il nome è uno solo: ho letto anche \"%s\". Guarda --help." % a)
        nome = a
    if not nome:
        raise Errore(1, "Manca il nome del workspace. Esempio: crea-workspace.py preventivi-officina --descrizione \"...\"")
    if descrizione is None or not descrizione.split():
        raise Errore(1, "Manca --descrizione: scrivi in una frase cosa fa il lavoro.")
    return nome, " ".join(descrizione.split()), cartella, dati


def testo_dati(dati, studio, avvisi):
    if not dati:
        return "- Nessun dato indicato ancora (da completare)."
    righe = []
    for d in dati:
        d = d.strip()
        if not d:
            continue
        righe.append("- `%s`" % d)
        assoluto = d if os.path.isabs(d) else os.path.join(studio, d)
        if not os.path.exists(os.path.expanduser(assoluto)):
            avvisi.append("il percorso dei dati \"%s\" non esiste ancora." % d)
    return "\n".join(righe) if righe else "- Nessun dato indicato ancora (da completare)."


def leggi_modello():
    """Elenco (percorso relativo, contenuto) dei file del modello."""
    if not os.path.isdir(MODELLO):
        raise Errore(1, "Manca il modello: %s. Il plugin è incompleto." % MODELLO)
    trovati = []
    for radice, cartelle, files in os.walk(MODELLO):
        cartelle[:] = sorted(c for c in cartelle if c != "__pycache__")
        for f in sorted(files):
            pieno = os.path.join(radice, f)
            rel = os.path.relpath(pieno, MODELLO)
            with open(pieno, encoding="utf-8") as fh:
                trovati.append((rel, fh.read()))
    if not trovati:
        raise Errore(1, "Il modello è vuoto: %s." % MODELLO)
    return trovati


def riempi(testo, valori):
    for chiave, valore in valori.items():
        testo = testo.replace("{{%s}}" % chiave, valore)
    return testo


def scrivi_atomico(percorso, testo):
    tmp = percorso + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(testo)
    os.replace(tmp, percorso)


def aggiorna_indice(studio, nome, descrizione):
    """Aggiunge la riga sotto '## Workspace'. Ritorna 'aggiunta', 'gia' o None (nessun INDICE)."""
    percorso = os.path.join(studio, "memoria", "INDICE.md")
    if not os.path.isfile(percorso):
        return None
    with open(percorso, encoding="utf-8") as fh:
        testo = fh.read()
    riga = "- [[%s]] · %s" % (nome, descrizione)
    righe = testo.split("\n")
    inizio = None
    for n, r in enumerate(righe):
        if r.strip() == "## Workspace":
            inizio = n
            break
    if inizio is None:
        if testo and not testo.endswith("\n"):
            testo += "\n"
        nuovo = testo + "\n## Workspace\n\n" + riga + "\n"
    else:
        fine = len(righe)
        for n in range(inizio + 1, len(righe)):
            if righe[n].startswith("## "):
                fine = n
                break
        if any(("[[%s]]" % nome) in r for r in righe[inizio + 1:fine]):
            return "gia"
        ultimo = inizio
        for n in range(inizio + 1, fine):
            if righe[n].strip():
                ultimo = n
        righe.insert(ultimo + 1, riga)
        nuovo = "\n".join(righe)
        if not nuovo.endswith("\n"):
            nuovo += "\n"
    scrivi_atomico(percorso, nuovo)
    return "aggiunta"


def aggiorna_log(studio, nome, descrizione):
    """Aggiunge la riga di LOG. Ritorna il percorso, o None se lo studio non ha memoria/."""
    cartella = os.path.join(studio, "memoria")
    if not os.path.isdir(cartella):
        return None
    percorso = os.path.join(cartella, "LOG.md")
    ora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    riga = "- %s · workspace · creato il workspace %s: %s\n" % (ora, nome, descrizione)
    if os.path.isfile(percorso):
        with open(percorso, encoding="utf-8") as fh:
            vecchio = fh.read()
        if vecchio and not vecchio.endswith("\n"):
            vecchio += "\n"
        scrivi_atomico(percorso, vecchio + riga)
    else:
        scrivi_atomico(percorso, "# Registro\n\nUna riga per fatto, in fondo, mai riscritta.\n\n" + riga)
    return percorso


def crea(nome, descrizione, cartella, dati):
    if not RE_KEBAB.match(nome):
        giusto = suggerisci_nome(nome)
        dire = " Prova con: %s" % giusto if giusto and RE_KEBAB.match(giusto) else ""
        raise Errore(
            1,
            "Il nome \"%s\" non è in kebab-case (solo minuscole, numeri e trattini, per esempio preventivi-officina).%s"
            % (nome, dire),
        )
    studio = trova_cartella(cartella)
    destinazione = os.path.join(studio, "workspace", nome)
    if os.path.exists(destinazione):
        raise Errore(
            2,
            "Il workspace %s esiste già (%s). Non tocco niente: aprilo e lavora lì." % (nome, destinazione),
        )
    avvisi = []
    valori = {
        "nome": nome,
        "descrizione": descrizione,
        "dati": testo_dati(dati, studio, avvisi),
        "data": datetime.date.today().isoformat(),
    }
    file_pronti = []
    for rel, contenuto in leggi_modello():
        if rel == SCHEDA_MODELLO:
            rel = os.path.join("memoria", nome + ".md")
        file_pronti.append((rel, riempi(contenuto, valori)))

    creati = []
    cartella_workspace = os.path.join(studio, "workspace")
    prima = os.path.isdir(cartella_workspace)
    try:
        os.makedirs(destinazione)
        for sotto in CARTELLE_VUOTE:
            os.makedirs(os.path.join(destinazione, sotto), exist_ok=True)
        for rel, testo in file_pronti:
            pieno = os.path.join(destinazione, rel)
            os.makedirs(os.path.dirname(pieno), exist_ok=True)
            scrivi_atomico(pieno, testo)
            creati.append(pieno)
    except OSError as e:
        shutil.rmtree(destinazione, ignore_errors=True)
        if not prima:
            try:
                os.rmdir(cartella_workspace)
            except OSError:
                pass
        raise Errore(1, "Non riesco a scrivere il workspace (%s). Ho tolto ciò che avevo creato." % e)

    aggiornati = []
    indice = aggiorna_indice(studio, nome, descrizione)
    if indice == "aggiunta":
        aggiornati.append(os.path.join(studio, "memoria", "INDICE.md"))
    elif indice is None:
        avvisi.append(
            "lo studio non ha memoria/INDICE.md: aggiungi tu \"- [[%s]] · %s\" sotto \"## Workspace\"."
            % (nome, descrizione)
        )
    log = aggiorna_log(studio, nome, descrizione)
    if log:
        aggiornati.append(log)
    else:
        avvisi.append("lo studio non ha memoria/: scrivi tu la riga di registro (tipo workspace).")
    return destinazione, creati, aggiornati, avvisi


def main(argv):
    try:
        nome, descrizione, cartella, dati = leggi_argomenti(argv)
        destinazione, creati, aggiornati, avvisi = crea(nome, descrizione, cartella, dati)
    except Errore as e:
        sys.stderr.write("errore: %s\n" % e.testo)
        return e.codice
    for p in creati:
        print("creato: %s" % p)
    for p in aggiornati:
        print("aggiornato: %s" % p)
    for a in avvisi:
        print("avviso: %s" % a)
    print("esito: workspace %s creato in %s" % (nome, destinazione))
    print("Ora completa AGENTS.md e la scheda con il contenuto vero, poi lancia controlla-workspace.py.")
    return 0


def flussi_utf8():
    """Su Windows i flussi che non sono un terminale usano la tabella locale (cp1252): chi li legge vuole UTF-8."""
    for f in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if not f.isatty():
                f.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


if __name__ == "__main__":
    flussi_utf8()
    sys.exit(main(sys.argv[1:]))
