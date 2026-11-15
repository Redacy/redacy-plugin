# redacy 0.5.0 · skills/crea-workspace/scripts/crea-workspace.py
"""Crea un workspace (un agente intero) dentro la cartella dello studio.

Uso: python3 crea-workspace.py NOME --descrizione "..." [--cartella DIR] [--dati PERCORSO ...]
Solo libreria standard, Python 3.9 o più.
"""

import datetime
import os
import re
import shutil
import sys
import time
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
                          Il dato resta dov'è: si scrive solo il percorso.
                          Un percorso dello studio (fonti/listini) si scrive
                          dalla cartella del workspace (../../fonti/listini);
                          uno intero resta com'è
  -h, --help              mostra questo aiuto

Un workspace che esiste già non si tocca: lo script esce con 2 e non scrive
niente. Aprilo e lavora lì. Solo se il workspace è completo ma nell'indice o
nel registro manca la sua riga (una creazione finita a metà), rilanciando con
lo stesso nome lo script aggiunge quelle righe e non tocca il workspace.

Uscite: 0 fatto (stampa i percorsi creati; un "avviso:" dice una riga che non
        sono riuscito a scrivere) · 1 uso sbagliato o nome non valido
        · 2 il workspace esiste già.
"""

RE_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# Nomi che Windows non lascia usare per una cartella o un file, anche con un'estensione.
RISERVATI = {"con", "prn", "aux", "nul"} | {"com%d" % n for n in range(1, 10)} | {"lpt%d" % n for n in range(1, 10)}
ATTESA_RIPROVO = 1.0  # secondi: un file bloccato da OneDrive o dall'antivirus si libera quasi sempre in meno
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
        # Il workspace lavora dalla sua cartella (workspace/<nome>/): un percorso dello studio si scrive da lì.
        intero = os.path.isabs(d) or d.startswith(("~", "\\\\")) or re.match(r"^[A-Za-z]:[\\/]", d)
        dall_agente = d if intero else "../../" + d.replace("\\", "/")
        righe.append("- `%s`" % dall_agente)
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
    # in un solo passaggio: una descrizione che contiene "{{dati}}" non deve essere riempita a sua volta
    return re.sub(r"\{\{(\w+)\}\}", lambda m: valori.get(m.group(1), m.group(0)), testo)


def scrivi_atomico(percorso, testo):
    tmp = percorso + ".tmp-%d" % os.getpid()
    try:
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(testo)
        os.replace(tmp, percorso)
    except OSError:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def riprova(azione):
    """Esegue azione(); se il file e' bloccato (OSError) riprova per circa ATTESA_RIPROVO secondi, poi rilancia."""
    fine = time.time() + ATTESA_RIPROVO
    while True:
        try:
            return azione()
        except OSError:
            if time.time() >= fine:
                raise
            time.sleep(0.2)


def leggi_con_a_capo(percorso):
    """Ritorna (testo con a capo LF, a capo usato dal file): cosi' si riscrive con gli stessi a capo di prima."""
    with open(percorso, encoding="utf-8", newline="") as fh:
        testo = fh.read()
    a_capo = "\r\n" if "\r\n" in testo else "\n"
    return testo.replace("\r\n", "\n"), a_capo


def scrivi_con_a_capo(percorso, testo, a_capo):
    scrivi_atomico(percorso, testo.replace("\n", a_capo) if a_capo != "\n" else testo)


def aggiorna_indice(studio, nome, descrizione):
    """Aggiunge la riga sotto '## Workspace'. Ritorna 'aggiunta', 'gia' o None (nessun INDICE)."""
    percorso = os.path.join(studio, "memoria", "INDICE.md")
    if not os.path.isfile(percorso):
        return None
    testo, a_capo = leggi_con_a_capo(percorso)
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
    scrivi_con_a_capo(percorso, nuovo, a_capo)
    return "aggiunta"


def riga_di_log(nome, descrizione):
    ora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return "- %s · workspace · creato il workspace %s: %s\n" % (ora, nome, descrizione)


def aggiorna_log(studio, nome, descrizione, solo_se_manca=False):
    """Aggiunge la riga di LOG. Ritorna il percorso, o None se lo studio non ha memoria/
    (o, con solo_se_manca, se la riga di questo workspace c'e' gia')."""
    cartella = os.path.join(studio, "memoria")
    if not os.path.isdir(cartella):
        return None
    percorso = os.path.join(cartella, "LOG.md")
    riga = riga_di_log(nome, descrizione)
    if os.path.isfile(percorso):
        vecchio, a_capo = leggi_con_a_capo(percorso)
        if solo_se_manca and ("creato il workspace %s:" % nome) in vecchio:
            return None
        if vecchio and not vecchio.endswith("\n"):
            vecchio += "\n"
        scrivi_con_a_capo(percorso, vecchio + riga, a_capo)
    else:
        scrivi_atomico(percorso, "# Registro\n\nUna riga per fatto, in fondo, mai riscritta.\n\n" + riga)
    return percorso


def _perche(e):
    """Una frase corta sul motivo per cui una lettura o una scrittura non e' riuscita."""
    if isinstance(e, UnicodeDecodeError):
        return "non è scritto in UTF-8: aprilo e salvalo come UTF-8"
    if isinstance(e, PermissionError):
        return "non ho il permesso di scriverlo, oppure è aperto in un altro programma"
    return "errore del disco: %s" % (getattr(e, "strerror", None) or e)


def righe_della_memoria(studio, nome, descrizione, solo_se_manca=False):
    """Aggiunge la riga all'indice e al registro dello studio. Non solleva mai.

    Ritorna (aggiornati, avvisi): i file scritti e una frase per ogni riga che non e' riuscita
    (il workspace resta valido: la riga si aggiunge a mano, o rilanciando lo script)."""
    aggiornati = []
    avvisi = []
    percorso_indice = os.path.join(studio, "memoria", "INDICE.md")
    try:
        indice = riprova(lambda: aggiorna_indice(studio, nome, descrizione))
        if indice == "aggiunta":
            aggiornati.append(percorso_indice)
        elif indice is None and not solo_se_manca:
            avvisi.append(
                "lo studio non ha memoria/INDICE.md: aggiungi tu \"- [[%s]] · %s\" sotto \"## Workspace\"."
                % (nome, descrizione)
            )
    except (OSError, UnicodeDecodeError) as e:
        avvisi.append(
            "non sono riuscito ad aggiungere la riga all'indice (%s: %s). Aggiungi tu \"- [[%s]] · %s\" sotto "
            "\"## Workspace\"; oppure sistema il file e rilancia lo stesso comando: aggiunge le righe che mancano."
            % (percorso_indice, _perche(e), nome, descrizione)
        )
    percorso_log = os.path.join(studio, "memoria", "LOG.md")
    try:
        log = riprova(lambda: aggiorna_log(studio, nome, descrizione, solo_se_manca))
        if log:
            aggiornati.append(log)
        elif not solo_se_manca:
            avvisi.append("lo studio non ha memoria/: scrivi tu la riga di registro (tipo workspace).")
    except (OSError, UnicodeDecodeError) as e:
        avvisi.append(
            "non sono riuscito ad aggiungere la riga al registro (%s: %s). Aggiungi tu in fondo la riga «%s» "
            "oppure sistema il file e rilancia lo stesso comando: aggiunge le righe che mancano."
            % (percorso_log, _perche(e), riga_di_log(nome, descrizione).strip())
        )
    return aggiornati, avvisi


def e_completo(destinazione, nome):
    """Un workspace con i tre file che lo reggono: lo si puo' considerare finito (mancano al piu' le righe in memoria/)."""
    return all(
        os.path.isfile(os.path.join(destinazione, *parti))
        for parti in (("AGENTS.md",), ("CLAUDE.md",), ("memoria", nome + ".md"))
    )


def crea(nome, descrizione, cartella, dati):
    """Ritorna (destinazione, creati, aggiornati, avvisi, completato): completato e' True se il workspace
    c'era gia' e lo script ha solo aggiunto le righe che mancavano in memoria/."""
    if nome in RISERVATI:
        raise Errore(
            1,
            "Il nome \"%s\" è riservato da Windows (come con, aux, nul, prn, com1-com9, lpt1-lpt9): "
            "una cartella con quel nome non si crea. Scegline un altro, per esempio %s-lavoro." % (nome, nome),
        )
    if not RE_KEBAB.match(nome):
        giusto = suggerisci_nome(nome)
        dire = " Prova con: %s" % giusto if giusto and RE_KEBAB.match(giusto) and giusto not in RISERVATI else ""
        raise Errore(
            1,
            "Il nome \"%s\" non è in kebab-case (solo minuscole, numeri e trattini, per esempio preventivi-officina).%s"
            % (nome, dire),
        )
    studio = trova_cartella(cartella)
    destinazione = os.path.join(studio, "workspace", nome)
    if os.path.exists(destinazione):
        esiste = Errore(
            2,
            "Il workspace %s esiste già (%s). Non tocco niente: aprilo e lavora lì." % (nome, destinazione),
        )
        if not e_completo(destinazione, nome):
            raise esiste
        # Una creazione finita a meta' (indice o registro non scritti): si aggiungono solo le righe che mancano.
        aggiornati, avvisi = righe_della_memoria(studio, nome, descrizione, solo_se_manca=True)
        if not aggiornati and not avvisi:
            raise esiste
        return destinazione, [], aggiornati, avvisi, True
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
        raise Errore(1, "Non riesco a scrivere il workspace (%s). Ho tolto ciò che avevo creato. "
                              "Controlla che workspace/ sia una cartella e che si possa scrivere, poi rilancia." % e)

    aggiornati, altri = righe_della_memoria(studio, nome, descrizione)
    return destinazione, creati, aggiornati, avvisi + altri, False


def main(argv):
    try:
        nome, descrizione, cartella, dati = leggi_argomenti(argv)
        destinazione, creati, aggiornati, avvisi, completato = crea(nome, descrizione, cartella, dati)
    except Errore as e:
        sys.stderr.write("errore: %s\n" % e.testo)
        return e.codice
    for p in creati:
        print("creato: %s" % p)
    for p in aggiornati:
        print("aggiornato: %s" % p)
    for a in avvisi:
        print("avviso: %s" % a)
    if completato:
        print("esito: il workspace %s esisteva già in %s: non l'ho toccato, ho solo provato ad aggiungere le righe che mancavano"
              % (nome, destinazione))
        return 0
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
