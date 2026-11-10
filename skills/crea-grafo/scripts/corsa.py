# redacy 0.4.0 - skills/crea-grafo/scripts/corsa.py
"""Tiene il registro delle corse di un grafo.

Una corsa e' una volta in cui un grafo (grafi/<nome>.yaml) e' stato eseguito.
Ogni corsa e' un file grafi/corse/<id>.json, scritto solo da questo script.
Una richiesta di stop e' un file a parte, grafi/corse/<id>.stop: la prossima volta che la corsa
fa un passo, un battito o si chiude, questo script la segna fermata ed esce con 3.

Comandi:
  apri     controlla il grafo, crea la corsa e stampa il suo id
  passo    segna l'inizio o la fine di un passo
  battito  dice che la corsa e' ancora viva
  chiudi   chiude la corsa (finita o fallita)
  ferma    chiede lo stop di una corsa: scrive grafi/corse/<id>.stop (lo usa il pannello)
  stato    mostra una corsa
  elenco   elenca le corse, le piu' recenti prima

Uscite: 0 ok; 1 uso sbagliato o grafo non valido; 2 corsa, grafo o cartella
che non c'e'; 3 la corsa non e' piu' in corso (fermata o chiusa): chi riceve 3
smette di lavorare a quella corsa.

Solo libreria standard. Funzioni importabili dal pannello:
trova_cartella(), leggi_corsa(percorso), e_persa(corsa, adesso=None).
"""

import argparse
import contextlib
import datetime
import importlib.util
import json
import os
import re
import sys
import tempfile
import time

QUI = os.path.dirname(os.path.abspath(__file__))
if QUI not in sys.path:
    sys.path.insert(0, QUI)

FORMATO = 1
PERSA_DOPO_DEFAULT = 20
AVVIATO_DA = ("conversazione", "attivita-claude", "automazione-codex", "utente")
NOME_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORMATO_ORA = "%Y-%m-%dT%H:%M:%SZ"


class ErroreCorsa(Exception):
    """Un errore che diventa un messaggio e un codice di uscita."""

    def __init__(self, codice, messaggio):
        super().__init__(messaggio)
        self.codice = codice
        self.messaggio = messaggio


# ---------------------------------------------------------------- tempo

def adesso_utc():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def scrivi_ora(dt):
    return dt.astimezone(datetime.timezone.utc).strftime(FORMATO_ORA)


def leggi_ora(testo):
    dt = datetime.datetime.strptime(testo, FORMATO_ORA)
    return dt.replace(tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------- cartelle

def _e_studio(cartella):
    return os.path.isfile(os.path.join(cartella, "AGENTS.md")) and os.path.isdir(
        os.path.join(cartella, "grafi")
    )


def trova_cartella(inizio=None, esplicita=None):
    """Restituisce la cartella dello studio (con AGENTS.md e grafi/).

    Ordine: `esplicita` (l'opzione --cartella), la variabile REDACY_CARTELLA,
    poi si risale da `inizio` (default: la cartella corrente).
    Solleva ErroreCorsa (codice 2) se non la trova.
    """
    scelta = esplicita or os.environ.get("REDACY_CARTELLA")
    if scelta:
        scelta = os.path.abspath(os.path.expanduser(scelta))
        if not _e_studio(scelta):
            raise ErroreCorsa(
                2,
                "La cartella %s non e' una cartella dello studio (servono AGENTS.md e grafi/)." % scelta,
            )
        return scelta
    corrente = os.path.abspath(inizio or os.getcwd())
    while True:
        if _e_studio(corrente):
            return corrente
        padre = os.path.dirname(corrente)
        if padre == corrente:
            raise ErroreCorsa(
                2,
                "Non trovo la cartella dello studio: risalendo da %s non c'e' nessuna cartella con AGENTS.md e grafi/. "
                "Spostati nella cartella dello studio, oppure usa --cartella." % (inizio or os.getcwd()),
            )
        corrente = padre


def cartella_corse(cartella):
    return os.path.join(cartella, "grafi", "corse")


def percorso_corsa(cartella, id_corsa):
    if not NOME_OK.match(id_corsa or ""):
        raise ErroreCorsa(2, "L'id di corsa '%s' non e' valido." % id_corsa)
    return os.path.join(cartella_corse(cartella), id_corsa + ".json")


def percorso_lucchetto(cartella, id_corsa):
    return os.path.join(cartella_corse(cartella), ".%s.lock" % id_corsa)


def percorso_stop(cartella, id_corsa):
    """La richiesta di stop e' un file a parte (<id>.stop): chi ferma scrive quello, la corsa la scrive solo corsa.py."""
    return os.path.join(cartella_corse(cartella), id_corsa + ".stop")


# ---------------------------------------------------------------- file

def su_windows():
    """Vero su Windows. I rami solo-Windows di questo file passano di qui (le prove lo forzano)."""
    return os.name == "nt"


def blocca_file(fd):
    """Lucchetto esclusivo su un file aperto, aspetta finche' lo ottiene. Unix: fcntl.flock. Windows: msvcrt.locking."""
    if su_windows():
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)   # riprova da solo per circa 10 secondi, poi OSError
                return
            except OSError:
                time.sleep(0.05)
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX)


def sblocca_file(fd):
    if su_windows():
        import msvcrt
        with contextlib.suppress(OSError):
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        return
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)


@contextlib.contextmanager
def lucchetto(percorso):
    """Lucchetto esclusivo su un file nascosto. Si libera da solo."""
    fd = os.open(percorso, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        blocca_file(fd)
        yield
    finally:
        try:
            sblocca_file(fd)
        finally:
            os.close(fd)


def sostituisci(tmp, dest):
    """os.replace. Su Windows, se il pannello ha il file aperto in lettura in quell'istante, riprova per un secondo."""
    for tentativo in range(20):
        try:
            return os.replace(tmp, dest)
        except PermissionError:
            if not su_windows() or tentativo == 19:
                raise
            time.sleep(0.05)


def scrivi_atomico(percorso, dato):
    """Scrive il JSON in un file temporaneo nella stessa cartella e poi lo sostituisce."""
    cartella = os.path.dirname(percorso)
    nome = os.path.basename(percorso)
    fd, tmp = tempfile.mkstemp(prefix=".%s." % nome, suffix=".tmp", dir=cartella)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dato, f, ensure_ascii=False, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        sostituisci(tmp, percorso)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def scrivi_atomico_riga(percorso, dato):
    """Come scrivi_atomico, ma una sola riga JSON (il file .stop). Se c'e' gia', resta il primo."""
    cartella = os.path.dirname(percorso)
    fd, tmp = tempfile.mkstemp(prefix=".%s." % os.path.basename(percorso), suffix=".tmp", dir=cartella)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(dato, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        try:
            os.link(tmp, percorso)      # non sovrascrive: chi ha chiesto per primo resta
        except FileExistsError:
            pass
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp)


def leggi_corsa(percorso):
    """Legge il file di una corsa. Solleva OSError se non c'e', ErroreCorsa se e' illeggibile."""
    with open(percorso, encoding="utf-8") as f:
        try:
            dato = json.load(f)
        except ValueError as e:
            raise ErroreCorsa(1, "Il file %s non e' un JSON valido (%s)." % (percorso, e))
    if not isinstance(dato, dict) or "stato" not in dato:
        raise ErroreCorsa(1, "Il file %s non e' una corsa." % percorso)
    return dato


def e_persa(corsa, adesso=None):
    """True se la corsa e' in corso ma non da' segni di vita da piu' di persa_dopo_minuti."""
    if corsa.get("stato") != "in-corso":
        return False
    if adesso is None:
        adesso = adesso_utc()
    elif adesso.tzinfo is None:
        adesso = adesso.replace(tzinfo=datetime.timezone.utc)
    try:
        ultimo = leggi_ora(corsa["ultimo_segno"])
    except (KeyError, TypeError, ValueError):
        return True
    limite = corsa.get("persa_dopo_minuti") or PERSA_DOPO_DEFAULT
    return adesso - ultimo > datetime.timedelta(minutes=limite)


def _una_riga(testo):
    if testo is None:
        return None
    return " ".join(str(testo).split())


def leggi_stop(cartella, id_corsa):
    """La richiesta di stop di una corsa (dict con chi, quando, perche), o None se non c'e'."""
    try:
        with open(percorso_stop(cartella, id_corsa), encoding="utf-8") as f:
            testo = f.read().strip()
    except OSError:
        return None
    try:
        dato = json.loads(testo.splitlines()[0]) if testo else {}
    except (ValueError, IndexError):
        dato = {}
    if not isinstance(dato, dict):
        dato = {}
    return {
        "chi": _una_riga(dato.get("chi")) or "sconosciuto",
        "quando": dato.get("quando") or scrivi_ora(adesso_utc()),
        "perche": _una_riga(dato.get("perche")) or "",
    }


def _applica_stop(corsa, stop, ora):
    """Mette la corsa in stato fermata (in corso -> fermata, passi in corso -> fermato)."""
    adesso = scrivi_ora(ora)
    corsa["stop"] = stop
    corsa["stato"] = "fermata"
    corsa["fine"] = adesso
    corsa["ultimo_segno"] = adesso
    for p in corsa["passi"]:
        if p["stato"] == "in-corso":
            p["stato"] = "fermato"
            p["fine"] = adesso


def _messaggio_stop(stop):
    return "Corsa fermata da %s: non fare altri passi, dillo all'utente." % stop["chi"]


def stato_effettivo(corsa, cartella):
    """Lo stato che vede chi legge: una corsa in corso con un file .stop e' gia' 'fermata'."""
    if corsa.get("stato") == "in-corso" and leggi_stop(cartella, corsa.get("id", "")):
        return "fermata"
    return corsa.get("stato")


# ---------------------------------------------------------------- modifica di una corsa

def aggiorna(cartella, id_corsa, funzione):
    """Legge la corsa sotto lucchetto, applica `funzione(corsa, ora)`, scrive e restituisce.

    Se la corsa non c'e': ErroreCorsa 2. Se non e' piu' in corso, o se c'e' una richiesta di stop
    (la corsa diventa fermata): ErroreCorsa 3.
    Se `funzione` solleva un errore, il file non cambia.
    """
    percorso = percorso_corsa(cartella, id_corsa)
    if not os.path.isfile(percorso):
        raise ErroreCorsa(2, "La corsa %s non c'e'." % id_corsa)
    with lucchetto(percorso_lucchetto(cartella, id_corsa)):
        try:
            corsa = leggi_corsa(percorso)
        except FileNotFoundError:
            raise ErroreCorsa(2, "La corsa %s non c'e'." % id_corsa)
        if corsa["stato"] != "in-corso":
            raise ErroreCorsa(
                3,
                "La corsa %s non e' piu' in corso (%s). Smetti di lavorare a questa corsa: non riprovare e non chiuderla."
                % (id_corsa, corsa["stato"]),
            )
        ora = adesso_utc()
        stop = leggi_stop(cartella, id_corsa)
        if stop is not None:
            _applica_stop(corsa, stop, ora)
            scrivi_atomico(percorso, corsa)
            raise ErroreCorsa(3, _messaggio_stop(stop))
        funzione(corsa, ora)
        corsa["ultimo_segno"] = scrivi_ora(ora)
        scrivi_atomico(percorso, corsa)
    return corsa


def consolida_stop(cartella, id_corsa):
    """Se c'e' una richiesta di stop su una corsa in corso, la scrive nella corsa. Restituisce la corsa letta."""
    percorso = percorso_corsa(cartella, id_corsa)
    if not os.path.isfile(percorso):
        raise ErroreCorsa(2, "La corsa %s non c'e'." % id_corsa)
    with lucchetto(percorso_lucchetto(cartella, id_corsa)):
        corsa = leggi_corsa(percorso)
        stop = leggi_stop(cartella, id_corsa)
        if corsa["stato"] == "in-corso" and stop is not None:
            _applica_stop(corsa, stop, adesso_utc())
            scrivi_atomico(percorso, corsa)
    return corsa


def _trova_passo(corsa, id_passo):
    for p in corsa["passi"]:
        if p["id"] == id_passo:
            return p
    elenco = ", ".join(p["id"] for p in corsa["passi"])
    raise ErroreCorsa(1, "Il passo '%s' non e' in questa corsa. Passi: %s." % (id_passo, elenco))


# ---------------------------------------------------------------- comandi

def _carica_modulo(percorso, nome):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def cmd_apri(args):
    cartella = trova_cartella(esplicita=args.cartella)
    if not NOME_OK.match(args.grafo):
        raise ErroreCorsa(1, "Il nome del grafo '%s' non e' valido: usa lettere minuscole, numeri e trattini." % args.grafo)
    file_grafo = os.path.join(cartella, "grafi", args.grafo + ".yaml")
    if not os.path.isfile(file_grafo):
        raise ErroreCorsa(2, "Il grafo %s non c'e': manca il file %s." % (args.grafo, file_grafo))
    controllo = os.path.join(QUI, "controlla-grafo.py")
    if not os.path.isfile(controllo):
        raise ErroreCorsa(1, "Manca controlla-grafo.py accanto a corsa.py (%s): senza non apro nessuna corsa." % QUI)
    modulo = _carica_modulo(controllo, "controlla_grafo")
    errori, avvisi = modulo.controlla_file(file_grafo)
    for a in avvisi:
        print("avviso: %s" % a, file=sys.stderr)
    if errori:
        for e in errori:
            print(e, file=sys.stderr)
        raise ErroreCorsa(1, "Il grafo %s ha %d errori: non apro la corsa. Correggili e riprova." % (args.grafo, len(errori)))
    import yaml_ridotto

    grafo = yaml_ridotto.leggi_file(file_grafo)
    passi = [
        {"id": p["id"], "stato": "da-fare", "inizio": None, "fine": None, "esito": None, "nota": None}
        for p in grafo["passi"]
    ]
    os.makedirs(cartella_corse(cartella), exist_ok=True)
    ora = adesso_utc()
    with lucchetto(os.path.join(cartella_corse(cartella), ".apri.lock")):
        base = "%s-%s" % (args.grafo, ora.strftime("%Y%m%d-%H%M%S"))
        id_corsa = base
        n = 2
        while os.path.exists(os.path.join(cartella_corse(cartella), id_corsa + ".json")):
            id_corsa = "%s-%d" % (base, n)
            n += 1
        corsa = {
            "formato": FORMATO,
            "id": id_corsa,
            "grafo": args.grafo,
            "versione": grafo["versione"],
            "stato": "in-corso",
            "avviato_da": args.avviato_da,
            "inizio": scrivi_ora(ora),
            "ultimo_segno": scrivi_ora(ora),
            "persa_dopo_minuti": args.persa_dopo,
            "fine": None,
            "sessione": args.sessione or os.environ.get("CLAUDE_CODE_SESSION_ID") or os.environ.get("CODEX_THREAD_ID") or None,
            "stop": None,
            "passi": passi,
        }
        scrivi_atomico(percorso_corsa(cartella, id_corsa), corsa)
    print(id_corsa)
    return 0


def cmd_passo(args):
    cartella = trova_cartella(esplicita=args.cartella)

    def f(corsa, ora):
        p = _trova_passo(corsa, args.passo)
        adesso = scrivi_ora(ora)
        if args.azione == "inizio":
            p["stato"] = "in-corso"
            p["inizio"] = adesso
            p["fine"] = None
            p["esito"] = _una_riga(args.esito)
            p["nota"] = _una_riga(args.nota)
        else:
            p["stato"] = "fatto" if args.azione == "fatto" else "fallito"
            if p["inizio"] is None:
                p["inizio"] = adesso
            p["fine"] = adesso
            if args.esito is not None:
                p["esito"] = _una_riga(args.esito)
            if args.nota is not None:
                p["nota"] = _una_riga(args.nota)

    aggiorna(cartella, args.id, f)
    return 0


def cmd_battito(args):
    cartella = trova_cartella(esplicita=args.cartella)
    aggiorna(cartella, args.id, lambda corsa, ora: None)
    return 0


def cmd_chiudi(args):
    cartella = trova_cartella(esplicita=args.cartella)

    def f(corsa, ora):
        adesso = scrivi_ora(ora)
        in_corso = [p["id"] for p in corsa["passi"] if p["stato"] == "in-corso"]
        if in_corso and args.come == "finita":
            raise ErroreCorsa(
                1,
                "Non chiudo la corsa come finita: il passo %s e' ancora in corso. "
                "Segnalo 'fatto' o 'fallito', oppure chiudi la corsa come fallita." % ", ".join(in_corso),
            )
        for p in corsa["passi"]:
            if p["stato"] == "in-corso":
                p["stato"] = "fallito"
                p["fine"] = adesso
            elif p["stato"] == "da-fare":
                p["stato"] = "saltato"
        corsa["stato"] = args.come
        corsa["fine"] = adesso

    aggiorna(cartella, args.id, f)
    return 0


def cmd_ferma(args):
    cartella = trova_cartella(esplicita=args.cartella)
    percorso = percorso_corsa(cartella, args.id)
    if not os.path.isfile(percorso):
        raise ErroreCorsa(2, "La corsa %s non c'e'." % args.id)
    corsa = consolida_stop(cartella, args.id)
    if corsa["stato"] != "in-corso":
        raise ErroreCorsa(3, "La corsa %s non e' in corso (%s): non c'e' niente da fermare." % (args.id, corsa["stato"]))
    scrivi_atomico_riga(
        percorso_stop(cartella, args.id),
        {"chi": _una_riga(args.da) or "utente", "quando": scrivi_ora(adesso_utc()), "perche": _una_riga(args.perche) or ""},
    )
    consolida_stop(cartella, args.id)
    return 0


def etichetta_stato(corsa, adesso=None):
    if corsa["stato"] == "in-corso":
        return "persa" if e_persa(corsa, adesso) else "in corso"
    return corsa["stato"]


def cmd_stato(args):
    cartella = trova_cartella(esplicita=args.cartella)
    percorso = percorso_corsa(cartella, args.id)
    if not os.path.isfile(percorso):
        raise ErroreCorsa(2, "La corsa %s non c'e'." % args.id)
    corsa = consolida_stop(cartella, args.id)
    print(json.dumps(corsa, ensure_ascii=False, indent=2))
    print(etichetta_stato(corsa))
    return 0


def cmd_elenco(args):
    cartella = trova_cartella(esplicita=args.cartella)
    corse = []
    cartella_c = cartella_corse(cartella)
    nomi = sorted(os.listdir(cartella_c)) if os.path.isdir(cartella_c) else []
    for nome in nomi:
        if nome.startswith(".") or not nome.endswith(".json"):
            continue
        try:
            corse.append(consolida_stop(cartella, nome[:-5]))
        except (OSError, ErroreCorsa) as e:
            print("avviso: salto %s: %s" % (nome, getattr(e, "messaggio", e)), file=sys.stderr)
    if not corse:
        print("Nessuna corsa.")
        return 0
    corse.sort(key=lambda c: (c.get("inizio", ""), c.get("id", "")), reverse=True)
    adesso = adesso_utc()
    for c in corse:
        fatti = sum(1 for p in c["passi"] if p["stato"] == "fatto")
        print("%s\t%s\t%s\tpassi %d/%d" % (c["id"], etichetta_stato(c, adesso), c.get("inizio", ""), fatti, len(c["passi"])))
    return 0


# ---------------------------------------------------------------- riga di comando

class Formattatore(argparse.RawDescriptionHelpFormatter):
    def add_usage(self, usage, actions, groups, prefix=None):
        super().add_usage(usage, actions, groups, prefix or "Uso: ")

    def start_section(self, heading):
        titoli = {"options": "opzioni", "positional arguments": "argomenti"}
        super().start_section(titoli.get(heading, heading))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print("Uso sbagliato: %s" % message, file=sys.stderr)
        raise SystemExit(1)


def _intero_positivo(testo):
    try:
        n = int(testo)
    except ValueError:
        raise argparse.ArgumentTypeError("serve un numero intero, non '%s'" % testo)
    if n < 1:
        raise argparse.ArgumentTypeError("serve un numero da 1 in su")
    return n


def costruisci_parser():
    p = Parser(
        prog="corsa.py",
        description=__doc__.split("\n\n")[0] + "\n\nOgni comando ha il suo --help.",
        epilog="Uscite: 0 ok; 1 uso sbagliato o grafo non valido; 2 corsa, grafo o cartella che non c'e'; "
        "3 la corsa non e' piu' in corso (fermata o chiusa): smetti di lavorare.",
        formatter_class=Formattatore,
        add_help=False,
    )
    p.add_argument("-h", "--help", action="help", help="mostra questo aiuto ed esce")
    sub = p.add_subparsers(dest="comando", required=True, metavar="comando", parser_class=Parser)

    comune = Parser(add_help=False)
    comune.add_argument(
        "--cartella",
        metavar="PERCORSO",
        help="la cartella dello studio (con AGENTS.md e grafi/); se manca si usa REDACY_CARTELLA, poi si risale dalla cartella corrente",
    )

    def nuovo(nome, aiuto, descrizione):
        s = sub.add_parser(nome, parents=[comune], help=aiuto, description=descrizione, add_help=False, formatter_class=Formattatore)
        s.add_argument("-h", "--help", action="help", help="mostra questo aiuto ed esce")
        return s

    s = nuovo("apri", "controlla il grafo, crea la corsa, stampa l'id",
              "Controlla grafi/<grafo>.yaml. Se ha errori li stampa, esce con 1 e non crea nulla. "
              "Altrimenti crea la corsa con tutti i passi da fare e stampa il suo id: tienilo, serve agli altri comandi.")
    s.add_argument("grafo", help="il nome del grafo, cioe' il nome del file senza .yaml")
    s.add_argument("--avviato-da", choices=AVVIATO_DA, default="utente",
                   help="chi la fa partire (default: utente, un comando lanciato a mano)")
    s.add_argument("--sessione", metavar="ID", help="l'identificativo della conversazione o della sessione che la esegue")
    s.add_argument("--persa-dopo", type=_intero_positivo, default=PERSA_DOPO_DEFAULT, metavar="N",
                   help="dopo quanti minuti senza segni di vita la corsa risulta persa (default: %d)" % PERSA_DOPO_DEFAULT)
    s.set_defaults(fn=cmd_apri)

    s = nuovo("passo", "segna l'inizio o la fine di un passo",
              "Aggiorna un passo della corsa e il suo ultimo segno di vita. Esce con 3 se la corsa non e' piu' in corso.")
    s.add_argument("id", help="l'id della corsa")
    s.add_argument("passo", help="l'id del passo nel grafo")
    s.add_argument("azione", choices=("inizio", "fatto", "fallito"), help="cosa e' successo al passo")
    s.add_argument("--esito", metavar="TESTO", help="una riga: cosa ha prodotto il passo")
    s.add_argument("--nota", metavar="TESTO", help="una riga: perche' e' fallito, cosa aspetta")
    s.set_defaults(fn=cmd_passo)

    s = nuovo("battito", "dice che la corsa e' ancora viva",
              "Aggiorna solo l'ultimo segno di vita. Senza segni per piu' di 20 minuti (o --persa-dopo) la corsa risulta persa.")
    s.add_argument("id", help="l'id della corsa")
    s.set_defaults(fn=cmd_battito)

    s = nuovo("chiudi", "chiude la corsa come finita o fallita",
              "Con 'finita' i passi da fare diventano saltati; se un passo e' ancora in corso rifiuta (uscita 1). "
              "Con 'fallita' i passi in corso diventano falliti e quelli da fare saltati.")
    s.add_argument("id", help="l'id della corsa")
    s.add_argument("come", choices=("finita", "fallita"), help="come e' andata")
    s.set_defaults(fn=cmd_chiudi)

    s = nuovo("ferma", "ferma la corsa (lo usa il pannello)",
              "Scrive chi ha chiesto lo stop, mette la corsa in stato fermata e segna fermati i passi in corso. "
              "Chi sta eseguendo la corsa riceve 3 al comando successivo e smette.")
    s.add_argument("id", help="l'id della corsa")
    s.add_argument("--da", metavar="CHI", default="pannello", help="chi chiede lo stop (default: pannello)")
    s.add_argument("--perche", metavar="TESTO", help="il motivo, in una riga")
    s.set_defaults(fn=cmd_ferma)

    s = nuovo("stato", "mostra una corsa",
              "Stampa il JSON della corsa e poi una riga: 'in corso', 'persa' oppure lo stato (finita, fallita, fermata).")
    s.add_argument("id", help="l'id della corsa")
    s.set_defaults(fn=cmd_stato)

    s = nuovo("elenco", "elenca le corse, le piu' recenti prima",
              "Una riga per corsa: id, stato (persa compresa), inizio, passi fatti sul totale.")
    s.set_defaults(fn=cmd_elenco)
    return p


def main(argv=None):
    args = costruisci_parser().parse_args(argv)
    try:
        return args.fn(args)
    except ErroreCorsa as e:
        print(e.messaggio, file=sys.stderr)
        return e.codice
    except OSError as e:
        print("Errore sui file: %s" % e, file=sys.stderr)
        return 1


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
    sys.exit(main())
