# redacy 0.4.1 · skills/riordina-cartella/scripts/riordina.py
"""Riordina una cartella seguendo un piano scritto, e sa tornare indietro.

Uso:
  python3 riordina.py controlla PIANO     verifica il piano senza spostare niente
  python3 riordina.py applica PIANO       sposta i file, una mossa alla volta, col registro
  python3 riordina.py annulla REGISTRO    riporta tutto com'era (va bene anche il PIANO)

Il piano è un JSON (il formato è in references/piano.md):
  {"versione": 1, "cartella": "<percorso intero>", "regola": "<testo>",
   "righe": [{"da": "vecchio/a.pdf", "a": "Clienti/Rossi/a.pdf", "perche": "..."}]}
I percorsi delle righe sono relativi alla cartella, con «/».

controlla non sposta niente. Segna nel piano dimensione e data di ogni file
(«byte» e «modificato»), così applica riconosce un file cambiato dopo e lo lascia
dov'è. applica rifà tutti i controlli, poi sposta senza cancellare e senza
sovrascrivere, e scrive ogni mossa nel registro (registro.jsonl accanto al
piano) prima e dopo averla fatta: un'interruzione si riprende rilanciando
applica, o si annulla. Si ferma al primo errore e dice cosa ha già fatto.
annulla fa le mosse al contrario, con le stesse garanzie, e toglie le cartelle
che applica ha creato solo se sono rimaste vuote.

Solo libreria standard, Python 3.9 o più. Gira su Windows, macOS e Linux.

Uscite: 0 fatto (o, con controlla, il piano va bene) · 1 il piano non va, o
uso sbagliato · 2 il piano o il registro non c'è o non si legge · 3 fermato a
metà da un errore: il registro dice cosa è già fatto.
"""

import datetime
import errno
import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import unicodedata
from collections import Counter

QUI = os.path.dirname(os.path.abspath(__file__))
INVENTARIO = os.path.join(os.path.dirname(os.path.dirname(QUI)), "ordina-dati", "scripts", "inventario.py")
NOME_REGISTRO = "registro.jsonl"
FORMATO_ORA = "%Y-%m-%dT%H:%M:%SZ"
TOLLERANZA_S = 2.0      # i dischi FAT e alcune sincronizzazioni tengono la data a 2 secondi
MAX_RIGHE_STAMPA = 10
MAX_PROBLEMI = 30


class Errore(Exception):
    def __init__(self, codice, testo):
        Exception.__init__(self, testo)
        self.codice = codice
        self.testo = testo


def carica_inventario():
    if not os.path.isfile(INVENTARIO):
        raise Errore(2, "Manca %s: il plugin è incompleto, aggiornalo." % INVENTARIO)
    spec = importlib.util.spec_from_file_location("inventario_redacy", INVENTARIO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


INV = None


# ---------------------------------------------------------------- tempo e file

def ora_utc(ts=None):
    if ts is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    else:
        dt = datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
    return dt.strftime(FORMATO_ORA)


def secondi(testo):
    dt = datetime.datetime.strptime(testo, FORMATO_ORA).replace(tzinfo=datetime.timezone.utc)
    return dt.timestamp()


def uguale(st, byte, modificato):
    try:
        return st.st_size == byte and abs(st.st_mtime - secondi(modificato)) <= TOLLERANZA_S
    except (TypeError, ValueError):
        return False


def spiega(e, cosa):
    """Un OSError in una frase italiana, senza traceback."""
    win = getattr(e, "winerror", None)
    if win in (32, 33) or e.errno in (errno.EBUSY, errno.ETXTBSY):
        return "%s: il file è aperto in un altro programma (Word, Excel, il lettore PDF). Chiudilo e rilancia." % cosa
    if isinstance(e, PermissionError) or e.errno in (errno.EACCES, errno.EPERM):
        return "%s: non ho il permesso, o il file è aperto in un altro programma. Chiudilo e rilancia." % cosa
    if win == 206 or e.errno == errno.ENAMETOOLONG:
        return "%s: il percorso è troppo lungo per il sistema." % cosa
    if e.errno == errno.EXDEV or win == 17:
        return "%s: i due posti stanno su dischi diversi, e fra dischi diversi non sposto (vorrebbe dire copiare e cancellare)." % cosa
    if e.errno == errno.ENOSPC:
        return "%s: il disco è pieno." % cosa
    if isinstance(e, FileNotFoundError):
        return "%s: il file non c'è più." % cosa
    if isinstance(e, FileExistsError):
        return "%s: c'è già un file con quel nome." % cosa
    return "%s: %s." % (cosa, e.strerror or e)


def scrivi_atomico(percorso, testo):
    tmp = percorso + ".tmp-%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, percorso)


def dentro(figlio, padre):
    figlio = os.path.normcase(figlio)
    padre = os.path.normcase(padre)
    return figlio == padre or figlio.startswith(padre.rstrip(os.sep) + os.sep)


def stesso_file(a, b):
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def chiave(rel):
    return unicodedata.normalize("NFC", rel).casefold()


# ---------------------------------------------------------------- cartelle di sistema

def di_sistema(cartella):
    """Il motivo per cui una cartella non si riordina mai, o None."""
    reale = os.path.realpath(cartella)
    if os.path.dirname(reale) == reale:
        return "è la radice del disco"
    casa = os.path.realpath(os.path.expanduser("~"))
    if os.path.normcase(reale) == os.path.normcase(casa):
        return "è la cartella dell'utente intera: scegli una sua sottocartella"
    vietate = []
    if os.name == "nt":
        for v in ("SystemRoot", "windir", "ProgramFiles", "ProgramFiles(x86)", "ProgramW6432",
                  "ProgramData", "APPDATA", "LOCALAPPDATA"):
            if os.environ.get(v):
                vietate.append(os.environ[v])
        vietate.append(os.path.join(casa, "AppData"))
    else:
        vietate += ["/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/proc", "/run", "/sbin",
                    "/snap", "/sys", "/usr", "/System", "/Library", "/Applications", "/private/etc",
                    "/var/lib", "/var/log", "/var/cache", "/var/db", "/var/spool", "/cores",
                    os.path.join(casa, "Library")]
    for v in vietate:
        rv = os.path.realpath(v)
        if dentro(reale, rv):
            return "è una cartella di sistema (%s)" % v
    return None


def trova_studio(da):
    corrente = os.path.realpath(da)
    while True:
        if INV.e_studio(corrente):
            return corrente
        padre = os.path.dirname(corrente)
        if padre == corrente:
            return None
        corrente = padre


def voce_studio(assoluto, studio):
    """Il primo pezzo del percorso dentro lo studio, se è una voce dello studio (memoria, fonti...)."""
    if not studio or not dentro(assoluto, studio) or os.path.normcase(assoluto) == os.path.normcase(studio):
        return None
    rel = os.path.relpath(assoluto, studio)
    primo = rel.split(os.sep)[0].lower()
    return primo if primo in INV.VOCI_STUDIO else None


# ---------------------------------------------------------------- il piano

def pezzi(testo):
    """I pezzi di un percorso del piano, o (None, motivo)."""
    if not isinstance(testo, str) or not testo.strip():
        return None, "è vuoto"
    t = testo.replace("\\", "/") if os.name == "nt" else testo
    if t.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", t):
        return None, "è un percorso intero: si scrive relativo alla cartella, per esempio `Clienti/Rossi/a.pdf`"
    p = [x for x in t.split("/") if x not in ("", ".")]
    if ".." in p:
        return None, "contiene `..` ed esce dalla cartella"
    if not p:
        return None, "è vuoto"
    return p, None


def leggi_piano(percorso):
    percorso = os.path.abspath(percorso)
    if not os.path.isfile(percorso):
        raise Errore(2, "Il piano %s non c'è." % percorso)
    try:
        with open(percorso, encoding="utf-8-sig") as f:
            piano = json.load(f)
    except ValueError as e:
        raise Errore(1, "Il piano %s non è un JSON valido (%s). Correggilo e rilancia." % (percorso, e))
    except OSError as e:
        raise Errore(2, spiega(e, "Non riesco a leggere il piano"))
    if not isinstance(piano, dict):
        raise Errore(1, "Il piano deve essere un oggetto con «cartella» e «righe».")
    if not isinstance(piano.get("cartella"), str) or not os.path.isabs(os.path.expanduser(piano["cartella"])):
        raise Errore(1, "Nel piano «cartella» deve essere il percorso intero della cartella da riordinare.")
    if not isinstance(piano.get("righe"), list) or not piano["righe"]:
        raise Errore(1, "Nel piano «righe» deve essere un elenco con almeno una riga.")
    for n, r in enumerate(piano["righe"], 1):
        if not isinstance(r, dict):
            raise Errore(1, "La riga %d del piano non è un oggetto con da, a, perche." % n)
    return percorso, piano


def impronta_righe(piano):
    coppie = [[r.get("da"), r.get("a")] for r in piano["righe"]]
    return hashlib.sha256(json.dumps(coppie, ensure_ascii=False).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- il registro

def leggi_registro(percorso):
    """Ricostruisce lo stato: {'inizio': {...}, 'righe': {n: {...}}, 'cartelle': [...], 'annullo': bool}."""
    stato = {"inizio": None, "righe": {}, "cartelle": [], "annullo": False, "ordine": []}
    if not os.path.isfile(percorso):
        return stato
    try:
        with open(percorso, encoding="utf-8") as f:
            linee = f.read().splitlines()
    except OSError as e:
        raise Errore(2, spiega(e, "Non riesco a leggere il registro"))
    for i, linea in enumerate(linee):
        if not linea.strip():
            continue
        try:
            ev = json.loads(linea)
        except ValueError:
            if i == len(linee) - 1:
                continue    # l'ultima riga scritta a metà da un'interruzione
            raise Errore(1, "Il registro %s ha una riga rotta (la %d). Non lo tocco." % (percorso, i + 1))
        tipo = ev.get("evento")
        n = ev.get("riga")
        if tipo == "inizio":
            if stato["inizio"] is None:
                stato["inizio"] = ev
        elif tipo == "cartella":
            stato["cartelle"].append(ev["creata"])
        elif tipo == "sposto":
            stato["righe"][n] = {"stato": "in corso", "da": ev["da"], "a": ev["a"],
                                 "byte": ev.get("byte"), "modificato": ev.get("modificato")}
            if n in stato["ordine"]:
                stato["ordine"].remove(n)
            stato["ordine"].append(n)
        elif tipo == "spostato" and n in stato["righe"]:
            stato["righe"][n]["stato"] = "fatta"
        elif tipo == "saltato":
            stato["righe"].setdefault(n, {})["stato"] = "saltata"
        elif tipo == "annullo" and n in stato["righe"]:
            stato["annullo"] = True
            stato["righe"][n]["stato"] = "in annullo"
        elif tipo == "annullato" and n in stato["righe"]:
            stato["annullo"] = True
            stato["righe"][n]["stato"] = "annullata"
        elif tipo in ("annullo-inizio", "annullato-tutto"):
            stato["annullo"] = True
    return stato


class Registro:
    def __init__(self, percorso):
        self.percorso = percorso
        self.f = None

    def scrivi(self, **ev):
        if self.f is None:
            self.f = open(self.percorso, "a", encoding="utf-8", newline="\n")
        ev["quando"] = ora_utc()
        self.f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        self.f.flush()
        try:
            os.fsync(self.f.fileno())
        except OSError:
            pass

    def chiudi(self):
        if self.f is not None:
            self.f.close()
            self.f = None


# ---------------------------------------------------------------- i controlli

class Esame:
    def __init__(self):
        self.problemi = []
        self.avvisi = []
        self.da_fare = []      # (n, riga, pezzi_da, pezzi_a)
        self.restano = 0
        self.gia_fatte = 0
        self.timbrate = 0


def esamina(piano_path, piano, stato, timbra):
    """Tutti i controlli. Non sposta niente. Con timbra=True segna byte e modificato nel piano."""
    es = Esame()
    radice = os.path.abspath(os.path.expanduser(piano["cartella"]))
    if not os.path.isdir(radice):
        es.problemi.append("la cartella %s non c'è" % radice)
        return es, radice
    reale = os.path.realpath(radice)
    motivo = di_sistema(radice)
    if motivo:
        es.problemi.append("la cartella %s non si riordina: %s" % (radice, motivo))
        return es, radice
    studio = trova_studio(os.path.dirname(piano_path))
    permesso_fonti = isinstance(piano.get("permesso_fonti"), str) and piano["permesso_fonti"].strip()
    voce = voce_studio(reale, studio)
    if voce == "fonti" and not permesso_fonti:
        es.problemi.append("la cartella sta in `fonti/`: serve il sì dell'utente, scritto nel piano come «permesso_fonti»")
        return es, radice
    if voce and voce != "fonti":
        es.problemi.append("la cartella è una parte dello studio (`%s`): non si riordina" % voce)
        return es, radice

    def problema(n, testo):
        es.problemi.append("riga %d: %s" % (n, testo))

    def tocca_studio(assoluto, n, campo):
        v = voce_studio(os.path.realpath(assoluto) if os.path.lexists(assoluto) else assoluto, studio)
        if v == "fonti" and permesso_fonti:
            return False
        if v:
            problema(n, "«%s» è dentro `%s` dello studio, che il riordino non tocca" % (campo, v))
            return True
        return False

    sorgenti = {}
    destinazioni = {}
    grafia_cartelle = {}
    cartelle_previste = set()
    elenchi = {}

    def nomi_in(cartella):
        if cartella not in elenchi:
            try:
                elenchi[cartella] = os.listdir(cartella)
            except OSError:
                elenchi[cartella] = []
        return elenchi[cartella]

    righe = piano["righe"]
    for n, r in enumerate(righe, 1):
        st_reg = stato["righe"].get(n, {}).get("stato")
        if st_reg == "fatta":
            es.gia_fatte += 1
            continue
        if not isinstance(r.get("perche"), str) or not r["perche"].strip():
            problema(n, "manca «perche»: una frase che dice perché il file va lì")
        pd, m = pezzi(r.get("da"))
        if pd is None:
            problema(n, "«da» %s" % m)
            continue
        pa, m = pezzi(r.get("a"))
        if pa is None:
            problema(n, "«a» %s" % m)
            continue
        da_rel, a_rel = "/".join(pd), "/".join(pa)
        da_abs = os.path.join(radice, *pd)
        a_abs = os.path.join(radice, *pa)
        k = chiave(da_rel)
        if k in sorgenti:
            problema(n, "il file `%s` è già nella riga %d: un file, una riga" % (da_rel, sorgenti[k]))
            continue
        sorgenti[k] = n
        # la sorgente
        if any(INV.e_nascosto(x) for x in pd):
            problema(n, "`%s` sta in una cartella nascosta o di sistema: non si tocca" % da_rel)
            continue
        if not os.path.lexists(da_abs):
            problema(n, "il file `%s` non c'è" % da_rel)
            continue
        try:
            st = os.lstat(da_abs)
        except OSError as e:
            problema(n, spiega(e, "non riesco a leggere `%s`" % da_rel))
            continue
        if stat.S_ISLNK(st.st_mode):
            problema(n, "`%s` è un collegamento: non lo sposto" % da_rel)
            continue
        if not stat.S_ISREG(st.st_mode):
            problema(n, "`%s` non è un file: le cartelle non si spostano intere, si scrive una riga per file" % da_rel)
            continue
        if not dentro(os.path.realpath(da_abs), reale):
            problema(n, "`%s` porta fuori dalla cartella (passa da un collegamento)" % da_rel)
            continue
        if tocca_studio(da_abs, n, "da"):
            continue
        if "byte" in r or "modificato" in r:
            if not uguale(st, r.get("byte"), r.get("modificato")):
                es.avvisi.append("riga %d: `%s` è cambiato dopo il piano: applica lo lascerà dov'è. Se va spostato "
                                 "lo stesso, togli «byte» e «modificato» da quella riga e rilancia controlla." % (n, da_rel))
        elif timbra:
            r["byte"] = st.st_size
            r["modificato"] = ora_utc(st.st_mtime)
            es.timbrate += 1
        if pd == pa:
            es.restano += 1
            continue
        # la destinazione
        brutto = False
        for x in pa:
            for motivo in INV.problemi_nome(x):
                problema(n, "«a» `%s`: %s" % (a_rel, motivo))
                brutto = True
            if INV.e_nascosto(x):
                problema(n, "«a» `%s` va in una cartella nascosta o di sistema" % a_rel)
                brutto = True
        lungo = len(os.path.abspath(a_abs))
        if lungo > INV.TETTO_PERCORSO:
            problema(n, "«a» `%s`: il percorso intero ha %d caratteri, Windows ne regge %d. Accorcia nomi o livelli"
                     % (a_rel, lungo, INV.TETTO_PERCORSO))
            brutto = True
        if brutto:
            continue
        # il primo antenato che c'è non deve portare fuori
        antenato = os.path.dirname(a_abs)
        while not os.path.lexists(antenato) and dentro(antenato, radice) and antenato != radice:
            antenato = os.path.dirname(antenato)
        if not dentro(os.path.realpath(antenato), reale):
            problema(n, "«a» `%s` porta fuori dalla cartella (passa da un collegamento)" % a_rel)
            continue
        if tocca_studio(a_abs, n, "a"):
            continue
        ka = chiave(a_rel)
        if ka in destinazioni:
            problema(n, "«a» `%s` è anche la destinazione della riga %d (su Windows e OneDrive maiuscole e "
                     "minuscole sono lo stesso nome)" % (a_rel, destinazioni[ka]))
            continue
        destinazioni[ka] = n
        # le cartelle lungo la strada: stessa grafia, e niente file al loro posto
        guasto = False
        for i in range(1, len(pa)):
            pref = "/".join(pa[:i])
            kp = chiave(pref)
            if kp in grafia_cartelle and grafia_cartelle[kp] != pref:
                problema(n, "la cartella `%s` è scritta anche `%s` in un'altra riga: usa una grafia sola"
                         % (pref, grafia_cartelle[kp]))
                guasto = True
                break
            grafia_cartelle[kp] = pref
            cartelle_previste.add(kp)
            padre = os.path.join(radice, *pa[:i - 1]) if i > 1 else radice
            if os.path.isdir(padre):
                for nome in nomi_in(padre):
                    if chiave(nome) == chiave(pa[i - 1]):
                        pieno = os.path.join(padre, nome)
                        if nome != pa[i - 1]:
                            problema(n, "c'è già `%s` con maiuscole diverse da `%s`: usa lo stesso nome"
                                     % (nome, pa[i - 1]))
                            guasto = True
                        elif not os.path.isdir(pieno) or os.path.islink(pieno):
                            problema(n, "`%s` c'è già e non è una cartella" % pref)
                            guasto = True
                        break
            if guasto:
                break
        if guasto:
            continue
        stesso = False
        if os.path.lexists(a_abs):
            try:
                stesso = os.path.samefile(da_abs, a_abs)
            except OSError:
                stesso = False
            if not stesso:
                problema(n, "«a» `%s` c'è già: non sovrascrivo. Scegli un altro nome (niente catene: un file "
                         "non va dove ne sta un altro, anche se quello si sposta)" % a_rel)
                continue
        else:
            padre = os.path.dirname(a_abs)
            if os.path.isdir(padre):
                for nome in nomi_in(padre):
                    if chiave(nome) == chiave(pa[-1]) and nome != pa[-1] \
                            and not stesso_file(os.path.join(padre, nome), da_abs):
                        problema(n, "«a» `%s` si scontra con `%s`, che c'è già (su Windows e OneDrive è lo stesso nome)"
                                 % (a_rel, nome))
                        stesso = None
                        break
            if stesso is None:
                continue
        es.da_fare.append((n, r, pd, pa))
    for n, r, pd, pa in es.da_fare:
        if chiave("/".join(pa)) in cartelle_previste:
            problema(n, "«a» `%s` è anche una cartella in un'altra riga" % "/".join(pa))
    return es, radice


def per_cartella(da_fare):
    gruppi = Counter("/".join(pa[:-1]) or "(in cima)" for _, _, _, pa in da_fare)
    if len(gruppi) > 20:
        gruppi = Counter("/".join(pa[:min(2, len(pa) - 1)]) or "(in cima)" for _, _, _, pa in da_fare)
    return sorted(gruppi.items())


def esempi(da_fare, quanti=MAX_RIGHE_STAMPA):
    if len(da_fare) <= quanti:
        return da_fare
    passo = len(da_fare) / quanti
    return [da_fare[int(i * passo)] for i in range(quanti)]


def stampa_problemi(es):
    for p in es.problemi[:MAX_PROBLEMI]:
        print("problema: %s" % p)
    if len(es.problemi) > MAX_PROBLEMI:
        print("problema: e altri %d, dello stesso tipo o di altri" % (len(es.problemi) - MAX_PROBLEMI))
    for a in es.avvisi[:MAX_PROBLEMI]:
        print("avviso: %s" % a)
    if len(es.avvisi) > MAX_PROBLEMI:
        print("avviso: e altri %d" % (len(es.avvisi) - MAX_PROBLEMI))


def registro_di(piano_path):
    return os.path.join(os.path.dirname(piano_path), NOME_REGISTRO)


def stato_del_piano(piano_path, piano):
    reg = registro_di(piano_path)
    stato = leggi_registro(reg)
    ini = stato["inizio"]
    if ini is not None:
        if ini.get("piano") != os.path.basename(piano_path):
            raise Errore(1, "Accanto al piano c'è il registro di un altro piano (%s). Metti il piano nuovo in una "
                            "cartella sua." % ini.get("piano"))
        if ini.get("impronta") != impronta_righe(piano):
            raise Errore(1, "Il piano è cambiato dopo che ho cominciato a spostare. Annulla prima "
                            "(annulla %s), poi fai un piano nuovo in una cartella nuova." % reg)
    return reg, stato


# ---------------------------------------------------------------- comandi

def cmd_controlla(piano_arg):
    piano_path, piano = leggi_piano(piano_arg)
    reg, stato = stato_del_piano(piano_path, piano)
    es, radice = esamina(piano_path, piano, stato, timbra=True)
    print("piano: %s" % piano_path)
    print("cartella: %s" % radice)
    if es.timbrate:
        try:
            scrivi_atomico(piano_path, json.dumps(piano, ensure_ascii=False, indent=1) + "\n")
            print("segnati: dimensione e data di %d file, nel piano" % es.timbrate)
        except OSError as e:
            raise Errore(2, spiega(e, "Non riesco a scrivere il piano"))
    stampa_problemi(es)
    righe = len(piano["righe"])
    if es.problemi:
        print("esito: il piano non va: %d problemi su %d righe. Non ho spostato niente." % (len(es.problemi), righe))
        return 1
    print("righe: %d · da spostare %d · restano dove sono %d · già spostate %d"
          % (righe, len(es.da_fare), es.restano, es.gia_fatte))
    for cartella, quanti in per_cartella(es.da_fare):
        print("per cartella d'arrivo: %s · %d file" % (cartella, quanti))
    for n, r, pd, pa in esempi(es.da_fare):
        print("esempio: riga %d · %s → %s · %s" % (n, "/".join(pd), "/".join(pa), r.get("perche", "")))
    print("esito: il piano va bene: %d file da spostare. Niente è stato spostato." % len(es.da_fare))
    return 0


def risolvi_in_corso(radice, stato, registro):
    """Le mosse cominciate e non segnate finite (un'interruzione): guarda dove sta il file."""
    for n, info in stato["righe"].items():
        if info.get("stato") != "in corso":
            continue
        da_abs = os.path.join(radice, *info["da"].split("/"))
        a_abs = os.path.join(radice, *info["a"].split("/"))
        if os.path.lexists(a_abs) and not os.path.lexists(da_abs):
            registro.scrivi(evento="spostato", riga=n, nota="ritrovato dopo un'interruzione")
            info["stato"] = "fatta"
        else:
            info["stato"] = None


def cmd_applica(piano_arg):
    piano_path, piano = leggi_piano(piano_arg)
    reg_path, stato = stato_del_piano(piano_path, piano)
    if stato["annullo"]:
        raise Errore(1, "Questo riordino è stato annullato (o si sta annullando). Per rifarlo, scrivi un piano nuovo "
                        "in una cartella nuova.")
    radice = os.path.abspath(os.path.expanduser(piano["cartella"]))
    registro = Registro(reg_path)
    try:
        if stato["inizio"] is not None:
            risolvi_in_corso(radice, stato, registro)
        es, radice = esamina(piano_path, piano, stato, timbra=False)
        print("piano: %s" % piano_path)
        print("cartella: %s" % radice)
        mancano = [n for n, r, _, _ in es.da_fare if "byte" not in r or "modificato" not in r]
        if mancano:
            es.problemi.append("le righe %s non hanno dimensione e data: lancia prima controlla, mostra il riassunto "
                               "e aspetta il sì" % ", ".join(str(n) for n in mancano[:10]))
        if es.problemi:
            stampa_problemi(es)
            print("esito: il piano non va: %d problemi. Non ho spostato niente." % len(es.problemi))
            return 1
        if stato["inizio"] is None:
            registro.scrivi(evento="inizio", piano=os.path.basename(piano_path), cartella=radice,
                            impronta=impronta_righe(piano), versione=1)
        print("registro: %s" % reg_path)
        spostati, saltati = 0, []
        for n, r, pd, pa in es.da_fare:
            da_rel, a_rel = "/".join(pd), "/".join(pa)
            da_abs = os.path.join(radice, *pd)
            a_abs = os.path.join(radice, *pa)
            try:
                st = os.lstat(da_abs)
            except OSError as e:
                registro.scrivi(evento="errore", riga=n, messaggio=str(e))
                return fermo(spiega(e, "riga %d, `%s`" % (n, da_rel)), spostati, es, reg_path)
            if not uguale(st, r["byte"], r["modificato"]):
                registro.scrivi(evento="saltato", riga=n, perche="cambiato dopo il piano")
                saltati.append((n, da_rel))
                continue
            if os.path.lexists(a_abs) and not os.path.samefile(da_abs, a_abs):
                registro.scrivi(evento="errore", riga=n, messaggio="destinazione occupata")
                return fermo("riga %d: `%s` è comparso nel frattempo, non sovrascrivo" % (n, a_rel), spostati, es, reg_path)
            try:
                for i in range(1, len(pa)):
                    c = os.path.join(radice, *pa[:i])
                    if not os.path.isdir(c):
                        registro.scrivi(evento="cartella", creata="/".join(pa[:i]))
                        os.mkdir(c)
                registro.scrivi(evento="sposto", riga=n, da=da_rel, a=a_rel, byte=st.st_size,
                                modificato=ora_utc(st.st_mtime))
                os.rename(da_abs, a_abs)
                registro.scrivi(evento="spostato", riga=n)
            except OSError as e:
                registro.scrivi(evento="errore", riga=n, messaggio=str(e))
                return fermo(spiega(e, "riga %d, `%s`" % (n, da_rel)), spostati, es, reg_path)
            spostati += 1
            if spostati <= MAX_RIGHE_STAMPA:
                print("spostato: %s → %s" % (da_rel, a_rel))
        if spostati > MAX_RIGHE_STAMPA:
            print("spostato: e altri %d (tutti nel registro)" % (spostati - MAX_RIGHE_STAMPA))
        for n, da_rel in saltati:
            print("saltato: riga %d · `%s` è cambiato dopo il piano: l'ho lasciato dov'è" % (n, da_rel))
        registro.scrivi(evento="fine", spostati=spostati, saltati=len(saltati))
        print("esito: %d file spostati, %d lasciati dove sono perché cambiati dopo il piano, %d già spostati prima. "
              "Niente cancellato, niente sovrascritto. Per tornare indietro: annulla %s"
              % (spostati, len(saltati), es.gia_fatte, reg_path))
        return 0
    finally:
        registro.chiudi()


def fermo(testo, spostati, es, reg_path):
    print("errore: %s" % testo)
    print("esito: fermato a metà. Spostati in questo giro: %d (più %d già prima). Il resto è dov'era. "
          "Si riprende rilanciando applica, o si torna indietro con: annulla %s" % (spostati, es.gia_fatte, reg_path))
    return 3


def cmd_annulla(arg):
    arg = os.path.abspath(arg)
    if arg.lower().endswith(".json") and not arg.lower().endswith(".jsonl"):
        arg = registro_di(arg)
    if not os.path.isfile(arg):
        raise Errore(2, "Il registro %s non c'è: forse il piano non è mai stato applicato." % arg)
    stato = leggi_registro(arg)
    ini = stato["inizio"]
    if ini is None or not ini.get("cartella"):
        raise Errore(1, "Il registro %s non dice quale cartella ha riordinato. Non tocco niente." % arg)
    radice = ini["cartella"]
    print("registro: %s" % arg)
    print("cartella: %s" % radice)
    if not os.path.isdir(radice):
        raise Errore(2, "La cartella %s non c'è più. Non tocco niente." % radice)
    registro = Registro(arg)
    riportati, saltati = 0, []
    try:
        registro.scrivi(evento="annullo-inizio")
        for n in reversed(stato["ordine"]):
            info = stato["righe"][n]
            s = info.get("stato")
            da_abs = os.path.join(radice, *info["da"].split("/"))
            a_abs = os.path.join(radice, *info["a"].split("/"))
            if s == "annullata":
                continue
            if s in ("in corso", "in annullo"):
                if os.path.lexists(da_abs) and not os.path.lexists(a_abs):
                    registro.scrivi(evento="annullato", riga=n, nota="era già al suo posto")
                    continue
                if not os.path.lexists(a_abs):
                    continue
            elif s != "fatta":
                continue
            try:
                st = os.lstat(a_abs)
            except OSError as e:
                return fermo_annulla(spiega(e, "riga %d, `%s`" % (n, info["a"])), riportati, arg)
            if not uguale(st, info["byte"], info["modificato"]):
                registro.scrivi(evento="saltato-annullo", riga=n, perche="cambiato dopo il riordino")
                saltati.append((n, info["a"]))
                continue
            if os.path.lexists(da_abs) and not os.path.samefile(da_abs, a_abs):
                return fermo_annulla("riga %d: al posto di `%s` c'è già un altro file, non sovrascrivo" % (n, info["da"]),
                                     riportati, arg)
            try:
                os.makedirs(os.path.dirname(da_abs), exist_ok=True)
                registro.scrivi(evento="annullo", riga=n)
                os.rename(a_abs, da_abs)
                registro.scrivi(evento="annullato", riga=n)
            except OSError as e:
                return fermo_annulla(spiega(e, "riga %d, `%s`" % (n, info["a"])), riportati, arg)
            riportati += 1
            if riportati <= MAX_RIGHE_STAMPA:
                print("riportato: %s → %s" % (info["a"], info["da"]))
        if riportati > MAX_RIGHE_STAMPA:
            print("riportato: e altri %d (tutti nel registro)" % (riportati - MAX_RIGHE_STAMPA))
        tolte, rimaste = 0, []
        for rel in reversed(stato["cartelle"]):
            c = os.path.join(radice, *rel.split("/"))
            if not os.path.isdir(c):
                continue
            try:
                os.rmdir(c)
                registro.scrivi(evento="cartella-tolta", cartella=rel)
                tolte += 1
            except OSError:
                rimaste.append(rel)
        for n, a_rel in saltati:
            print("saltato: riga %d · `%s` è cambiato dopo il riordino: l'ho lasciato dov'è" % (n, a_rel))
        for rel in rimaste:
            print("avviso: la cartella `%s` l'ho creata io ma non è vuota: la lascio" % rel)
        registro.scrivi(evento="annullato-tutto", riportati=riportati, saltati=len(saltati))
        print("esito: %d file riportati dov'erano, %d lasciati dove sono, %d cartelle create dal riordino tolte "
              "perché vuote. Niente cancellato, niente sovrascritto." % (riportati, len(saltati), tolte))
        return 0
    finally:
        registro.chiudi()


def fermo_annulla(testo, riportati, reg):
    print("errore: %s" % testo)
    print("esito: fermato a metà. Riportati in questo giro: %d. Si riprende rilanciando: annulla %s" % (riportati, reg))
    return 3


# ---------------------------------------------------------------- main

COMANDI = {"controlla": cmd_controlla, "applica": cmd_applica, "annulla": cmd_annulla}


def prepara_uscita():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv):
    global INV
    prepara_uscita()
    if not argv or argv[0] in ("-h", "--help"):
        sys.stdout.write(__doc__.split("\n\n", 1)[1])
        return 0 if argv else 1
    try:
        if argv[0] not in COMANDI:
            raise Errore(1, "Comando sconosciuto: %s. I comandi sono controlla, applica, annulla." % argv[0])
        if len(argv) != 2:
            raise Errore(1, "Serve un percorso dopo %s, uno solo. Esempio: riordina.py %s periodo/riordini/<...>/%s"
                         % (argv[0], argv[0], NOME_REGISTRO if argv[0] == "annulla" else "piano.json"))
        INV = carica_inventario()
        return COMANDI[argv[0]](argv[1])
    except Errore as e:
        print("errore: %s" % e.testo)
        return e.codice
    except KeyboardInterrupt:
        print("errore: fermato a metà da te. Il registro dice cosa è già fatto; rilancia lo stesso comando per riprendere.")
        return 3
    except Exception as e:  # mai un traceback all'utente
        print("errore: qualcosa non è andato (%s: %s). Il registro, se c'è, dice cosa è già fatto." % (type(e).__name__, e))
        return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
