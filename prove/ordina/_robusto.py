# redacy 0.5.0 · prove/ordina/_robusto.py (lo lanciano prova-inventario.sh e prova-riordina.sh)
"""inventario.py e riordina.py davanti alla radice del disco, a date prima del 1970 e a registri che non vanno.

Uso: python3 _robusto.py RADICE CARTELLA_DI_PROVA [inventario|riordina]
 - inventario.py rifiuta subito la radice del disco, la cartella dell'utente intera e una cartella di sistema, con
   «Scegli una sua sottocartella»; una sottocartella normale (anche di AppData o di Library) si guarda;
 - una data di modifica prima del 1970 (Windows: FILETIME 0, cioè il 1601) non ferma né inventario.py né riordina.py:
   si simula un Windows il cui fromtimestamp rifiuta i numeri negativi;
 - riordina.py annulla: un file ricomparso al posto originale e un registro con una riga rotta dicono che cosa fare, e
   seguire il consiglio funziona; niente cambia nel file dell'utente;
 - riordina.py: una riga di avanzamento ogni tanti file, in applica e in annulla.
Una riga per controllo: «ok» o «FALLISCE». In fondo PASSA oppure FALLISCE <perché>. Niente rete.
"""
import contextlib
import datetime
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import time
import types
from unittest import mock

sys.dont_write_bytecode = True
RADICE, BASE = sys.argv[1], sys.argv[2]
PARTE = sys.argv[3] if len(sys.argv) > 3 else "tutte"   # «inventario», «riordina» o tutte
INVENTARIO = os.path.join(RADICE, "skills", "ordina-dati", "scripts", "inventario.py")
RIORDINA = os.path.join(RADICE, "skills", "riordina-cartella", "scripts", "riordina.py")
FALLITE = []
shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(BASE)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)[:500]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def scrivi(percorso, testo):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


def leggi(percorso):
    with open(percorso, encoding="utf-8") as f:
        return f.read()


def lancia(script, *args, env=None, tempo=20):
    """Un rifiuto immediato non ha bisogno di tempo: se oltre `tempo` secondi lo script sta ancora scandendo, uscita 124."""
    e = dict(os.environ)
    e.update(env or {})
    t0 = time.time()
    try:
        r = subprocess.run([sys.executable, script] + list(args), capture_output=True, encoding="utf-8", errors="replace",
                           timeout=tempo, env=e)
    except subprocess.TimeoutExpired:
        return 124, "", "troppo lento: sta ancora scandendo", time.time() - t0
    return r.returncode, r.stdout, r.stderr, time.time() - t0


def pulito(*testi):
    return all("Traceback" not in t for t in testi)


def carica(percorso, nome):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


INV = carica(INVENTARIO, "inventario_robusto")
R = carica(RIORDINA, "riordina_robusto")
# ---- date prima del 1970: un Windows finto il cui fromtimestamp rifiuta i numeri negativi
class DatetimeWindows(datetime.datetime):
    @classmethod
    def fromtimestamp(cls, ts, tz=None):
        if ts < 0:
            raise OSError(22, "Invalid argument")
        return super().fromtimestamp(ts, tz)


def modulo_datetime_windows():
    m = types.SimpleNamespace(**{k: getattr(datetime, k) for k in dir(datetime) if not k.startswith("__")})
    m.datetime = DatetimeWindows
    return m


STORICO = -11644473600   # il 1601, la data zero di Windows


def prova_inventario():
    # ---- inventario.py: cartelle che non si guardano
    casa = os.path.join(BASE, "casa")
    os.makedirs(os.path.join(casa, "Pratiche"))
    scrivi(os.path.join(casa, "Pratiche", "a.txt"), "a")
    env_casa = {"HOME": casa, "USERPROFILE": casa}
    disco = os.path.splitdrive(os.path.abspath(os.sep))[0] + os.sep
    rc, out, err, t = lancia(INVENTARIO, disco, "--testo", env=env_casa)
    controllo("inventario sulla radice del disco: rifiutato subito, «Scegli una sua sottocartella»",
              rc == 1 and "radice del disco" in err and "Scegli una sua sottocartella" in err and t < 20 and pulito(out, err), (rc, err, t))
    rc, out, err, t = lancia(INVENTARIO, casa, "--testo", env=env_casa)
    controllo("inventario sulla cartella dell'utente intera: rifiutato, «Scegli una sua sottocartella»",
              rc == 1 and "cartella dell'utente" in err and "Scegli una sua sottocartella" in err and out == "", (rc, err))
    rc, out, err, t = lancia(INVENTARIO, os.path.join(casa, "Pratiche"), "--testo", env=env_casa)
    controllo("inventario su una sottocartella dell'utente: si guarda", rc == 0 and "File: 1" in out, (rc, err))
    sistema = os.environ.get("SystemRoot") if os.name == "nt" else "/etc"
    if sistema and os.path.isdir(sistema):
        rc, out, err, t = lancia(INVENTARIO, sistema, "--testo", env=env_casa)
        controllo("inventario su una cartella di sistema: rifiutato", rc == 1 and "cartella di sistema" in err and out == "", (rc, err))
    else:
        print("salto      inventario su una cartella di sistema (non trovo una cartella di sistema qui)")
    rc, out, err, t = lancia(INVENTARIO, BASE, "--testo", env=env_casa)
    controllo("inventario su una cartella temporanea (la usano le prove, e sta anche in AppData): si guarda", rc == 0, (rc, err))

    if hasattr(INV, "di_sistema"):
        controllo("riordina.py e inventario.py usano lo stesso controllo (di_sistema)",
                  INV.di_sistema(disco) == "è la radice del disco" and INV.di_sistema(BASE) is None, INV.di_sistema(disco))
    else:
        controllo("inventario.py ha di_sistema", False, "manca")


    cartella = os.path.join(BASE, "vecchi")
    scrivi(os.path.join(cartella, "antico.txt"), "x")
    scrivi(os.path.join(cartella, "normale.txt"), "y")
    try:
        os.utime(os.path.join(cartella, "antico.txt"), (-1000000000, -1000000000))
        utime_ok = True
    except (OSError, OverflowError, ValueError):
        utime_ok = False
    with mock.patch.object(INV, "datetime", modulo_datetime_windows()):
        try:
            if not hasattr(INV, "quando"):
                raise AttributeError("manca quando()")
            anno = INV.quando(STORICO).year
            esito = anno
        except Exception as e:  # noqa
            esito = repr(e)
        controllo("inventario.quando(): una data del 1601 su un Windows che rifiuta i numeri negativi dà l'anno 1601", esito == 1601, esito)
        if utime_ok:
            try:
                inv = INV.inventario(cartella, elenco=True)
                esito = (inv["date"]["piu_vecchia"]["data"], [f["modificato"][:4] for f in inv["elenco"] if f["file"] == "antico.txt"])
            except Exception as e:  # noqa
                esito = repr(e)
            controllo("inventario di una cartella con un file del 1938 su un Windows finto: nessun errore, la data è giusta",
                      esito == ("1938-04-24", ["1938"]), esito)
        else:
            print("salto      inventario con un file del 1938 (questo disco non ammette date prima del 1970)")



def prova_riordina():
    with mock.patch.object(R.datetime, "datetime", DatetimeWindows):
        try:
            esito = R.ora_utc(STORICO)
        except Exception as e:  # noqa
            esito = repr(e)
        controllo("riordina.ora_utc(): una data del 1601 su un Windows che rifiuta i numeri negativi non ferma lo script",
                  esito == "1601-01-01T00:00:00Z", esito)
        try:
            esito = R.secondi(R.ora_utc(STORICO))
        except Exception as e:  # noqa
            esito = repr(e)
        controllo("riordina: la data del 1601 scritta nel registro si rilegge uguale", esito == STORICO, esito)

    # ---- riordina.py: annulla e avanzamento (in-process: stesso Python, niente processi)
    R.di_sistema = lambda cartella: None    # la cartella di prova sta in una cartella temporanea, che su Windows è dell'utente
    _n = [0]


    def riordino(nomi, sposta_in="O"):
        """Una cartella con dei file, un piano che li sposta in una sottocartella, applicato. Ritorna (cartella, piano, registro)."""
        _n[0] += 1
        base = os.path.join(BASE, "r%d" % _n[0])
        c = os.path.join(base, "C")
        for n in nomi:
            scrivi(os.path.join(c, "s", n), "contenuto di " + n)
        piano = os.path.join(base, "piani", "piano.json")
        os.makedirs(os.path.dirname(piano))
        with open(piano, "w", encoding="utf-8") as f:
            json.dump({"versione": 1, "cartella": c, "regola": "tutto in %s" % sposta_in,
                       "righe": [{"da": "s/" + n, "a": sposta_in + "/" + n, "perche": "prova"} for n in nomi]}, f)
        for comando in ("controlla", "applica"):
            rc, out = riordina(comando, piano)
            assert rc == 0, (comando, out)
        return c, piano, os.path.join(os.path.dirname(piano), "registro.jsonl")


    def riordina(*argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                rc = R.main(list(argv))
            except Exception as e:  # noqa
                rc, _ = "ECCEZIONE %r" % e, None
        return rc, buf.getvalue()


    c, piano, registro = riordino(["a.txt", "b.txt"])
    scrivi(os.path.join(c, "s", "a.txt"), "NUOVO")
    rc, out = riordina("annulla", registro)
    controllo("annulla con un file ricomparso al posto originale: si ferma (3) e dice di spostarlo o rinominarlo e rilanciare",
              rc == 3 and "Spostalo o rinominalo" in out and "rilancia annulla" in out, (rc, out))
    rc2, out2 = riordina("annulla", registro)
    controllo("annulla rilanciato senza aver fatto niente: stesso esito, niente peggiora", rc2 == 3 and leggi(os.path.join(c, "s", "a.txt")) == "NUOVO", (rc2, out2))
    os.rename(os.path.join(c, "s", "a.txt"), os.path.join(c, "s", "a-nuovo.txt"))
    rc3, out3 = riordina("annulla", registro)
    controllo("seguito il consiglio (il file spostato altrove), annulla riporta tutto: uscita 0",
              rc3 == 0 and leggi(os.path.join(c, "s", "a.txt")) == "contenuto di a.txt" and leggi(os.path.join(c, "s", "b.txt")) == "contenuto di b.txt"
              and leggi(os.path.join(c, "s", "a-nuovo.txt")) == "NUOVO", (rc3, out3))

    c, piano, registro = riordino(["a.txt", "b.txt", "c.txt"])
    righe = leggi(registro).split("\n")
    punto = next(i for i, r in enumerate(righe) if '"riga": 2' in r and '"sposto"' in r)
    righe[punto] = "{rotto"
    scrivi(registro, "\n".join(righe))
    dopo_rotto = sorted(os.listdir(os.path.join(c, "O")))
    rc, out = riordina("annulla", registro)
    controllo("annulla con una riga rotta nel registro: uscita 1, nomina la riga, dice dove sono i file e come riportarli",
              rc == 1 and ("la %d" % (punto + 1)) in out and ("cancella la riga %d" % (punto + 1)) in out and "rilancia annulla" in out
              and "destinazione" in out, (rc, out))
    controllo("annulla con una riga rotta: non ha spostato niente", sorted(os.listdir(os.path.join(c, "O"))) == dopo_rotto)
    righe = [r for i, r in enumerate(leggi(registro).split("\n")) if i != punto]
    scrivi(registro, "\n".join(righe))
    rc, out = riordina("annulla", registro)
    controllo("seguito il consiglio (riga cancellata), annulla finisce senza traceback e riporta gli altri file",
              rc == 0 and os.path.isfile(os.path.join(c, "s", "a.txt")) and os.path.isfile(os.path.join(c, "s", "c.txt")), (rc, out))

    # ---- avanzamento
    nomi = ["f%02d.txt" % i for i in range(8)]
    R.MAX_RIGHE_STAMPA, R.AVANZAMENTO_OGNI = 2, 3
    base = os.path.join(BASE, "avanza")
    for n in nomi:
        scrivi(os.path.join(base, "C", "s", n), "x" + n)
    piano = os.path.join(base, "piani", "piano.json")
    os.makedirs(os.path.dirname(piano))
    with open(piano, "w", encoding="utf-8") as f:
        json.dump({"versione": 1, "cartella": os.path.join(base, "C"), "regola": "x",
                   "righe": [{"da": "s/" + n, "a": "O/" + n, "perche": "p"} for n in nomi]}, f)
    riordina("controlla", piano)
    rc, out = riordina("applica", piano)
    controllo("applica: una riga di avanzamento ogni tanti file, dopo le prime righe stampate",
              rc == 0 and "avanzamento: 3 file spostati" in out and "avanzamento: 6 file spostati" in out and "avanzamento: 4 " not in out, (rc, out))
    rc, out = riordina("annulla", os.path.join(os.path.dirname(piano), "registro.jsonl"))
    controllo("annulla: una riga di avanzamento ogni tanti file", rc == 0 and "avanzamento: 3 file riportati" in out and "avanzamento: 6 file riportati" in out, (rc, out))



if PARTE in ("tutte", "inventario"):
    prova_inventario()
if PARTE in ("tutte", "riordina"):
    prova_riordina()

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE[:5]) + (" … (%d in tutto)" % len(FALLITE) if len(FALLITE) > 5 else ""))
    sys.exit(1)
print("PASSA")
