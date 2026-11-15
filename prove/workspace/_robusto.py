# redacy 0.5.0 · prove/workspace/_robusto.py (lo lancia prova-workspace.sh)
"""crea-workspace.py e controlla-workspace.py davanti a nomi strani, file della memoria che non si leggono o non si scrivono.

Uso: python3 _robusto.py RADICE CARTELLA_DI_PROVA
 - nomi riservati da Windows (con, aux, com1, lpt9...): si rifiutano con una frase che dice di sceglierne un altro;
 - nomi con spazi, accenti, maiuscole, «..», barre, vuoto: una riga di errore, niente workspace, niente traceback;
 - memoria/INDICE.md o memoria/LOG.md non UTF-8: workspace creato, niente traceback, un avviso che dice quale riga
   non è riuscito a scrivere e perché; il rilancio con lo stesso nome aggiunge le righe che mancano senza toccare il workspace;
 - un file bloccato per un attimo (OneDrive, antivirus) si riprova; se resta bloccato lo si dice in una riga;
 - gli a capo del file dell'utente (CRLF) restano com'erano; i file nuovi vanno a capo con LF;
 - un workspace completo che esiste già: uscita 2, niente cambia;
 - controlla-workspace.py su una cartella senza AGENTS.md: si ferma subito con una riga, senza scandirla.
Una riga per controllo: «ok» o «FALLISCE». In fondo PASSA oppure FALLISCE <perché>. Niente rete, niente processi veri.
"""
import hashlib
import importlib.util
import os
import shutil
import subprocess
import sys
from unittest import mock

sys.dont_write_bytecode = True
RADICE, BASE = sys.argv[1], sys.argv[2]
os.makedirs(BASE, exist_ok=True)
CREA = os.path.join(RADICE, "skills", "crea-workspace", "scripts", "crea-workspace.py")
CONTROLLA = os.path.join(RADICE, "skills", "crea-workspace", "scripts", "controlla-workspace.py")
FALLITE = []


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)[:500]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def scrivi(percorso, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "wb") as f:
        f.write(dati if isinstance(dati, bytes) else dati.encode("utf-8"))


def leggi(percorso):
    with open(percorso, "rb") as f:
        return f.read()


_n = [0]


def studio(indice=None, log=None):
    """Una cartella dello studio finta, solo con ciò che serve a crea-workspace (AGENTS.md, grafi/, memoria/)."""
    _n[0] += 1
    d = os.path.join(BASE, "studio-%d" % _n[0])
    shutil.rmtree(d, ignore_errors=True)
    scrivi(os.path.join(d, "AGENTS.md"), "# Studio\n")
    os.makedirs(os.path.join(d, "grafi"))
    scrivi(os.path.join(d, "memoria", "INDICE.md"), "# Indice\n\n## Workspace\n" if indice is None else indice)
    scrivi(os.path.join(d, "memoria", "LOG.md"), "# Registro\n\n" if log is None else log)
    return d


def lancia(script, *args):
    r = subprocess.run([sys.executable, script] + list(args), capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return r.returncode, r.stdout, r.stderr


def crea(d, nome, descrizione="prepara i preventivi"):
    return lancia(CREA, nome, "-d", descrizione, "--cartella", d)


def albero(cartella):
    out = {}
    for base, _, nomi in os.walk(cartella):
        for n in nomi:
            p = os.path.join(base, n)
            out[os.path.relpath(p, cartella)] = hashlib.sha256(leggi(p)).hexdigest()
    return out


def senza_traceback(*testi):
    return all("Traceback" not in t for t in testi)


def workspace_di(d):
    return os.path.join(d, "workspace")


# ---- nomi riservati da Windows
for nome in ("con", "aux", "nul", "prn", "com1", "com9", "lpt1", "lpt9"):
    d = studio()
    rc, out, err = crea(d, nome)
    controllo("nome riservato «%s»: errore in una riga che dice di sceglierne un altro, niente creato" % nome,
              rc == 1 and "riservato" in err and "Scegli" in err and len(err.strip().splitlines()) == 1
              and not os.path.exists(workspace_di(d)) and senza_traceback(out, err), (rc, err))

# ---- nomi strani
for nome in ("Mio Lavoro", "perché", "UPPER", "..", "a/b", "a\\b", "x_y", " ", "con.txt"):
    d = studio()
    rc, out, err = crea(d, nome)
    controllo("nome strano %r: una riga di errore, niente creato, niente traceback" % nome,
              rc == 1 and err.startswith("errore:") and len(err.strip().splitlines()) == 1
              and not os.path.exists(workspace_di(d)) and senza_traceback(out, err), (rc, err))
d = studio()
rc, out, err = crea(d, "CON")
controllo("nome «CON» (maiuscolo): non propone un nome riservato", rc == 1 and "Prova con: con" not in err, err)
rc, out, err = lancia(CREA, "", "-d", "x", "--cartella", d)
controllo("nome vuoto: una riga di errore", rc == 1 and err.startswith("errore:") and senza_traceback(err), (rc, err))

# ---- INDICE.md non UTF-8: creato, avviso, rilancio che completa
d = studio(indice=b"# Indice\n\xe9\n## Workspace\n")
rc, out, err = crea(d, "mezzo")
ws = os.path.join(workspace_di(d), "mezzo")
controllo("INDICE non UTF-8: niente traceback, esce 0, il workspace c'è",
          rc == 0 and senza_traceback(out, err) and os.path.isfile(os.path.join(ws, "AGENTS.md")), (rc, err))
avvisi = [r for r in out.splitlines() if r.startswith("avviso:")]
controllo("INDICE non UTF-8: l'avviso nomina INDICE.md, dice il perché e che cosa fare",
          len(avvisi) == 1 and "INDICE.md" in avvisi[0] and "UTF-8" in avvisi[0] and "[[mezzo]]" in avvisi[0], out)
controllo("INDICE non UTF-8: il registro è stato aggiornato lo stesso",
          b"creato il workspace mezzo:" in leggi(os.path.join(d, "memoria", "LOG.md")))
controllo("INDICE non UTF-8: l'esito dice che il workspace è creato", "esito: workspace mezzo creato" in out, out)
prima_ws = albero(ws)
scrivi(os.path.join(d, "memoria", "INDICE.md"), "# Indice\n\n## Workspace\n")
rc, out, err = crea(d, "mezzo")
indice = leggi(os.path.join(d, "memoria", "INDICE.md")).decode("utf-8")
log = leggi(os.path.join(d, "memoria", "LOG.md")).decode("utf-8")
controllo("rilancio dopo aver sistemato l'INDICE: esce 0 e aggiunge la riga che mancava",
          rc == 0 and indice.count("[[mezzo]]") == 1 and "aggiornato:" in out and "INDICE.md" in out and senza_traceback(out, err),
          (rc, out, err, indice))
controllo("rilancio: il registro non prende una seconda riga", log.count("creato il workspace mezzo:") == 1, log)
controllo("rilancio: il workspace non è stato toccato", albero(ws) == prima_ws)
rc, out, err = crea(d, "mezzo")
controllo("terzo rilancio, tutto a posto: «esiste già», uscita 2", rc == 2 and "esiste già" in err, (rc, err))

# ---- LOG.md non UTF-8
d = studio(log=b"# Registro\n\xff\xfe\n")
rc, out, err = crea(d, "mezzo-log")
avvisi = [r for r in out.splitlines() if r.startswith("avviso:")]
controllo("LOG non UTF-8: niente traceback, avviso che nomina LOG.md e la riga da scrivere a mano",
          rc == 0 and senza_traceback(out, err) and len(avvisi) == 1 and "LOG.md" in avvisi[0] and "UTF-8" in avvisi[0]
          and "creato il workspace mezzo-log" in avvisi[0], (rc, out, err))
controllo("LOG non UTF-8: l'indice è stato aggiornato lo stesso", b"[[mezzo-log]]" in leggi(os.path.join(d, "memoria", "INDICE.md")))
controllo("LOG non UTF-8: il file dell'utente non è stato toccato", leggi(os.path.join(d, "memoria", "LOG.md")) == b"# Registro\n\xff\xfe\n")
scrivi(os.path.join(d, "memoria", "LOG.md"), "# Registro\n")
rc, out, err = crea(d, "mezzo-log")
controllo("LOG: il rilancio aggiunge la riga che mancava, l'indice non si duplica",
          rc == 0 and b"creato il workspace mezzo-log:" in leggi(os.path.join(d, "memoria", "LOG.md"))
          and leggi(os.path.join(d, "memoria", "INDICE.md")).count(b"[[mezzo-log]]") == 1, (rc, out, err))

# ---- tutti e due non leggibili
d = studio(indice=b"\xff", log=b"\xff")
rc, out, err = crea(d, "doppio")
controllo("INDICE e LOG non UTF-8: due avvisi, workspace creato, niente traceback",
          rc == 0 and out.count("avviso:") == 2 and senza_traceback(out, err)
          and os.path.isfile(os.path.join(workspace_di(d), "doppio", "AGENTS.md")), (rc, out, err))

# ---- file bloccato: si riprova, poi lo si dice (in-process, senza permessi veri)
spec = importlib.util.spec_from_file_location("crea_workspace_robusto", CREA)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)
if hasattr(M, "riprova"):
    M.ATTESA_RIPROVO = 0.6
    vera = M.scrivi_atomico
    chiamate = []

    def della_memoria_dello_studio(percorso):
        # INDICE.md e LOG.md dello studio, non i file del workspace nuovo (che stanno in workspace/<nome>/memoria/)
        return os.path.dirname(percorso) == os.path.join(d, "memoria")

    def bloccato_due_volte(percorso, testo):
        if della_memoria_dello_studio(percorso):
            chiamate.append(percorso)
            if len(chiamate) <= 2:
                raise PermissionError(13, "Permission denied")
        return vera(percorso, testo)

    d = studio()
    with mock.patch.object(M, "scrivi_atomico", bloccato_due_volte):
        try:
            _, _, aggiornati, avvisi, completato = M.crea("riprovo", "x", d, [])
            esito = (len(aggiornati), avvisi)
        except Exception as e:  # noqa
            esito = repr(e)
    controllo("un file bloccato per un attimo si riprova: nessun avviso, indice e registro scritti",
              isinstance(esito, tuple) and esito[0] == 2 and esito[1] == [], esito)

    def sempre_bloccato(percorso, testo):
        if della_memoria_dello_studio(percorso):
            raise PermissionError(13, "Permission denied")
        return vera(percorso, testo)

    d = studio()
    with mock.patch.object(M, "scrivi_atomico", sempre_bloccato):
        try:
            destinazione, creati, aggiornati, avvisi, completato = M.crea("bloccato", "x", d, [])
            esito = (aggiornati, avvisi)
        except Exception as e:  # noqa
            esito = repr(e)
    controllo("un file sempre bloccato: niente eccezione, due avvisi che dicono il permesso e la riga a mano",
              isinstance(esito, tuple) and len(esito[1]) == 2 and all("permesso" in a for a in esito[1])
              and os.path.isfile(os.path.join(workspace_di(d), "bloccato", "AGENTS.md")), esito)
    controllo("un file sempre bloccato: nessun file temporaneo lasciato in memoria/",
              not [n for n in os.listdir(os.path.join(d, "memoria")) if ".tmp-" in n], os.listdir(os.path.join(d, "memoria")))
else:
    controllo("crea-workspace.py sa riprovare un file bloccato (riprova)", False, "manca la funzione riprova")

# ---- a capo
d = studio(indice="# Indice\r\n\r\n## Workspace\r\n", log="# Registro\r\n\r\n")
rc, out, err = crea(d, "con-crlf")
ind = leggi(os.path.join(d, "memoria", "INDICE.md"))
lg = leggi(os.path.join(d, "memoria", "LOG.md"))
controllo("INDICE e LOG con a capo CRLF: restano CRLF (nessun a capo misto)",
          rc == 0 and ind.count(b"\n") == ind.count(b"\r\n") and lg.count(b"\n") == lg.count(b"\r\n") and b"[[con-crlf]]" in ind, (rc, ind, lg))
nuovi = [leggi(os.path.join(base, n)) for base, _, nomi in os.walk(os.path.join(workspace_di(d), "con-crlf")) for n in nomi]
controllo("i file nuovi del workspace vanno a capo con LF anche su Windows", nuovi and all(b"\r\n" not in n for n in nuovi))

# ---- una descrizione che contiene segnaposto non viene riempita due volte
d = studio()
rc, out, err = crea(d, "segnaposto", "usa {{dati}} e {{nome}} come esempio")
scheda = leggi(os.path.join(workspace_di(d), "segnaposto", "memoria", "segnaposto.md")).decode("utf-8")
controllo("una descrizione con {{dati}} dentro resta com'è (un solo passaggio di sostituzione)",
          rc == 0 and "usa {{dati}} e {{nome}} come esempio" in scheda, (rc, scheda[:300]))

# ---- esiste già, completo: non cambia niente
d = studio()
crea(d, "fatto")
prima = albero(d)
rc, out, err = crea(d, "fatto")
controllo("workspace completo e già in indice e registro: uscita 2, niente cambia", rc == 2 and albero(d) == prima, (rc, err))
shutil.rmtree(os.path.join(workspace_di(d), "fatto", "memoria"))
rc, out, err = crea(d, "fatto")
controllo("workspace incompleto (manca la scheda): uscita 2, non lo tocca", rc == 2 and not os.path.exists(os.path.join(workspace_di(d), "fatto", "memoria")), (rc, err))

# ---- controlla-workspace.py su una cartella che non è un workspace
estranea = os.path.join(BASE, "estranea")
shutil.rmtree(estranea, ignore_errors=True)
for i in range(30):
    scrivi(os.path.join(estranea, "cartella%d" % (i % 3), "file%d.md" % i), "ci sono dei {{segnaposto}} qui\n(da completare)\n")
rc, out, err = lancia(CONTROLLA, estranea)
righe = [r for r in out.splitlines() if r.startswith("errore:")]
controllo("controlla-workspace.py su una cartella senza AGENTS.md: un solo errore, nominato, senza scandirla",
          rc == 1 and len(righe) == 1 and "AGENTS.md" in righe[0] and "avviso:" not in out and senza_traceback(out, err), (rc, out))
d = studio()
crea(d, "buono")
rc, out, err = lancia(CONTROLLA, os.path.join(workspace_di(d), "buono"))
controllo("controlla-workspace.py su un workspace vero: ok, uscita 0", rc == 0 and "esito: ok" in out, (rc, out))
rc, out, err = lancia(CONTROLLA, os.path.join(BASE, "non-esiste"))
controllo("controlla-workspace.py su una cartella che non c'è: una riga", rc == 1 and "non esiste" in out and senza_traceback(out, err), (rc, out))

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
