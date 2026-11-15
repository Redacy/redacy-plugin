# redacy 0.5.0 · prove/pannello/_apri.py (lo lancia prova-server.sh)
"""Prova `pannello.py --apri` e le due letture dei file di Windows (BOM, file di sistema).

Uso: python3 _apri.py RADICE CARTELLA_DI_PROVA
Le cartelle di prova vanno sotto CARTELLA_DI_PROVA. Il browser non si apre mai davvero: xdg-open è uno
script finto che scrive il suo argomento in un file; per Windows e macOS si forzano il ramo e il comando.
"""
import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import time
import urllib.request
from unittest import mock

RADICE, BASE = sys.argv[1], sys.argv[2]
os.makedirs(BASE, exist_ok=True)
PANNELLO = os.path.join(RADICE, "skills/pannello/scripts/pannello.py")
PREPARA = os.path.join(RADICE, "prove/pannello/_prepara.py")
FALLITE = []
DUE_RIGHE = ("Pagina aperta nel browser.", "Non ho potuto aprire il browser: apri tu l'indirizzo.")


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


spec = importlib.util.spec_from_file_location("pannello_apri", PANNELLO)
pannello = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pannello)
if not hasattr(pannello, "apri_browser"):  # codice senza --apri: ogni controllo che segue fallisce, senza interrompere la prova
    controllo("pannello.py ha apri_browser", False)
    pannello.apri_browser = lambda url: None
URL = "http://127.0.0.1:47123/"
SENZA_SCHERMO = {k: v for k, v in os.environ.items() if k not in ("DISPLAY", "WAYLAND_DISPLAY")}


def sistema(nome):
    return mock.patch.object(pannello, "su_windows", lambda: nome == "windows"), \
        mock.patch.object(sys, "platform", {"windows": "win32", "macos": "darwin", "linux": "linux"}[nome])


@contextlib.contextmanager
def finto(nome, ambiente=None):
    a, b = sistema(nome)
    with a, b, mock.patch.dict(os.environ, ambiente if ambiente is not None else {}, clear=ambiente is not None):
        yield


# 1. Windows: os.startfile con l'indirizzo, nessun processo
chiamate = []
with finto("windows"), mock.patch.object(os, "startfile", lambda u: chiamate.append(u), create=True), \
        mock.patch.object(subprocess, "Popen", side_effect=AssertionError("niente processi su Windows")):
    esito = pannello.apri_browser(URL)
controllo("Windows: os.startfile è chiamato con l'indirizzo", esito is True and chiamate == [URL], (esito, chiamate))


def startfile_rotto(u):
    raise OSError("nessun programma associato")


with finto("windows"), mock.patch.object(os, "startfile", startfile_rotto, create=True):
    controllo("Windows: se startfile fallisce, non apre e non lancia eccezioni", pannello.apri_browser(URL) is False)


# 2. macOS: `open <indirizzo>`, staccato e muto
class Figlio:
    def __init__(self, codice=0):
        self.codice = codice

    def wait(self, timeout=None):
        return self.codice


lanci = []


def popen_finto(codice):
    def f(cmd, **kw):
        lanci.append((cmd, kw))
        return Figlio(codice)
    return f


with finto("macos", {}), mock.patch.object(subprocess, "Popen", popen_finto(0)):
    esito = pannello.apri_browser(URL)
controllo("macOS: lancia `open` con l'indirizzo", esito is True and lanci and lanci[0][0] == ["open", URL], lanci)
kw = lanci[0][1] if lanci else {}
controllo("macOS: il figlio è staccato e senza terminale",
          kw.get("stdin") == kw.get("stdout") == kw.get("stderr") == subprocess.DEVNULL and kw.get("start_new_session") is True, kw)
with finto("macos", {}), mock.patch.object(subprocess, "Popen", popen_finto(1)):
    controllo("macOS: se `open` esce con errore, non è aperto", pannello.apri_browser(URL) is False)


def popen_rotto(cmd, **kw):
    raise OSError("non trovato")


with finto("macos", {}), mock.patch.object(subprocess, "Popen", popen_rotto):
    controllo("macOS: se il comando non parte, non apre e non lancia eccezioni", pannello.apri_browser(URL) is False)

# 3. Linux: serve uno schermo e xdg-open; il modulo webbrowser non si usa
finti = os.path.join(BASE, "bin")
os.makedirs(finti, exist_ok=True)
marcatore = os.path.join(BASE, "aperto.txt")


def xdg_open_finto(corpo):
    p = os.path.join(finti, "xdg-open")
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("#!/bin/sh\n" + corpo + "\n")
    os.chmod(p, os.stat(p).st_mode | stat.S_IXUSR)


xdg_open_finto('printf "%s" "$1" > "$MARCATORE"')
PERCORSO = finti + os.pathsep + os.environ.get("PATH", "")
with finto("linux", {"PATH": PERCORSO, "MARCATORE": marcatore}), mock.patch.object(subprocess, "Popen", side_effect=AssertionError("senza schermo non si lancia niente")):
    controllo("Linux senza DISPLAY: non apre, e non lancia nessun processo", pannello.apri_browser(URL) is False)
with finto("linux", {"PATH": os.path.join(BASE, "vuota"), "DISPLAY": ":99"}):
    controllo("Linux con DISPLAY ma senza xdg-open: non apre", pannello.apri_browser(URL) is False)
for nome_var, valore in (("DISPLAY", ":99"), ("WAYLAND_DISPLAY", "wayland-0")):
    if os.path.exists(marcatore):
        if os.path.exists(marcatore):
            os.unlink(marcatore)
    with finto("linux", {"PATH": PERCORSO, "MARCATORE": marcatore, nome_var: valore}):
        esito = pannello.apri_browser(URL)
    letto = open(marcatore, encoding="utf-8").read() if os.path.exists(marcatore) else None
    controllo("Linux con %s e xdg-open: lo chiama con l'indirizzo" % nome_var, esito is True and letto == URL, (esito, letto))

xdg_open_finto("exit 3")
with finto("linux", {"PATH": PERCORSO, "DISPLAY": ":99"}):
    controllo("Linux: xdg-open che esce con errore = non aperto", pannello.apri_browser(URL) is False)
xdg_open_finto("sleep 6")
with finto("linux", {"PATH": PERCORSO, "DISPLAY": ":99"}):
    t0 = time.time()
    esito = pannello.apri_browser(URL)
    durata = time.time() - t0
controllo("Linux: un xdg-open che non finisce non blocca oltre 3 secondi", durata < 4.5 and esito is True, (esito, round(durata, 1)))
xdg_open_finto('printf "%s" "$1" > "$MARCATORE"')

# 4. main(): su Windows apre dal genitore, dopo la riga «acceso», con l'indirizzo giusto
registro = []
info = {"porta": 47123, "pid": 1}
for nome_arg, args, attesa in (("--apri", ["--cartella", BASE, "--apri"], True), ("senza --apri", ["--cartella", BASE], False)):
    registro.clear()
    fuori = io.StringIO()
    with finto("windows"), mock.patch.object(pannello, "trova_cartella", lambda c: BASE), \
            mock.patch.object(pannello, "accendi", lambda *a: (info, True)), \
            mock.patch.object(os, "startfile", lambda u: registro.append((u, fuori.getvalue())), create=True), \
            contextlib.redirect_stdout(fuori):
        try:
            codice = pannello.main(args)
        except SystemExit as e:  # argparse non conosce --apri
            codice = e.code
    righe = fuori.getvalue().splitlines()
    if attesa:
        controllo("main %s su Windows: esce 0, due righe, apre dopo aver scritto l'indirizzo" % nome_arg,
                  codice == 0 and righe == ["Il pannello è acceso: " + URL, DUE_RIGHE[0]] and len(registro) == 1
                  and registro[0][0] == URL and URL in registro[0][1], (codice, righe, registro))
    else:
        controllo("main %s su Windows: una riga sola e il browser non si tocca" % nome_arg,
                  codice == 0 and righe == ["Il pannello è acceso: " + URL] and not registro, (codice, righe, registro))
fuori = io.StringIO()
with finto("linux", {}), mock.patch.object(pannello, "trova_cartella", lambda c: BASE), \
        mock.patch.object(pannello, "accendi", lambda *a: (info, False)), contextlib.redirect_stdout(fuori):
    try:
        codice = pannello.main(["--cartella", BASE, "--apri"])
    except SystemExit as e:
        codice = e.code
controllo("main --apri su Linux senza schermo: esce 0 e dice di aprire l'indirizzo a mano",
          codice == 0 and fuori.getvalue().splitlines() == ["Il pannello è già acceso: " + URL, DUE_RIGHE[1]], fuori.getvalue())

# 5. Il pannello vero, da riga di comando (solo su Linux)
if sys.platform != "linux":
    print("SALTA     le prove da riga di comando: servono Linux e il suo xdg-open finto")
else:
    D = os.path.join(BASE, "studio")
    r = subprocess.run([sys.executable, PREPARA, D], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        controllo("preparo la cartella di prova", False, r.stderr)
        print("FALLISCE preparazione")
        sys.exit(1)

    def lancia(*args, **ambiente):
        env = dict(SENZA_SCHERMO, PATH=PERCORSO, MARCATORE=marcatore, **ambiente)
        return subprocess.run([sys.executable, PANNELLO, "--cartella", D] + list(args), capture_output=True,
                              text=True, encoding="utf-8", timeout=60, env=env)

    if os.path.exists(marcatore):
        if os.path.exists(marcatore):
            os.unlink(marcatore)
    try:
        # senza --apri: l'uscita è quella di sempre, una riga
        r = lancia()
        righe = r.stdout.splitlines()
        controllo("senza --apri: una riga sola, «acceso», niente browser",
                  r.returncode == 0 and len(righe) == 1 and righe[0].startswith("Il pannello è acceso: http://127.0.0.1:")
                  and not os.path.exists(marcatore), (r.returncode, r.stdout, r.stderr))
        indirizzo = righe[0].split(": ", 1)[1] if righe else ""
        # senza DISPLAY (già acceso): la seconda riga dice di aprire a mano, esce 0, xdg-open non è toccato
        r = lancia("--apri")
        controllo("--apri senza DISPLAY: esce 0 e la seconda riga è «Non ho potuto aprire il browser…»",
                  r.returncode == 0 and r.stdout.splitlines() == ["Il pannello è già acceso: " + indirizzo, DUE_RIGHE[1]]
                  and not os.path.exists(marcatore), (r.returncode, r.stdout, r.stderr))
        # con DISPLAY e un xdg-open finto: «Pagina aperta» e l'indirizzo arriva a xdg-open
        r = lancia("--apri", DISPLAY=":99")
        letto = open(marcatore, encoding="utf-8").read() if os.path.exists(marcatore) else None
        controllo("--apri con DISPLAY=:99 e xdg-open finto: «Pagina aperta nel browser.» e l'indirizzo giusto",
                  r.returncode == 0 and r.stdout.splitlines() == ["Il pannello è già acceso: " + indirizzo, DUE_RIGHE[0]]
                  and letto == indirizzo, (r.returncode, r.stdout, letto, indirizzo))
        lancia("--spegni")
        # pannello spento: --apri lo accende e poi apre (il server risponde prima che il browser parta)
        if os.path.exists(marcatore):
            os.unlink(marcatore)
        r = lancia("--apri", DISPLAY=":99")
        letto = open(marcatore, encoding="utf-8").read() if os.path.exists(marcatore) else None
        righe = r.stdout.splitlines()
        controllo("--apri su un pannello spento: lo accende, poi apre l'indirizzo che risponde",
                  r.returncode == 0 and len(righe) == 2 and righe[0].startswith("Il pannello è acceso: ") and righe[1] == DUE_RIGHE[0]
                  and letto == righe[0].split(": ", 1)[1], (r.returncode, r.stdout, letto))
        lancia("--spegni")
        # --primo-piano: l'opzione non fa niente
        if os.path.exists(marcatore):
            os.unlink(marcatore)
        porta = 47000 + (os.getpid() % 900)
        env = dict(SENZA_SCHERMO, PATH=PERCORSO, MARCATORE=marcatore, DISPLAY=":99")
        figlio = subprocess.Popen([sys.executable, PANNELLO, "--cartella", D, "--apri", "--primo-piano", "--porta", str(porta)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env)
        sveglio = False
        for _ in range(60):
            try:
                urllib.request.urlopen("http://127.0.0.1:%d/api/ciao" % porta, timeout=1).read()
                sveglio = True
                break
            except Exception:
                time.sleep(0.2)
        time.sleep(0.5)
        controllo("--apri con --primo-piano: il pannello gira e il browser non viene aperto",
                  sveglio and not os.path.exists(marcatore) and figlio.poll() is None, (sveglio, os.path.exists(marcatore)))
        lancia("--spegni")
        try:
            uscita, errori = figlio.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            figlio.kill()
            uscita, errori = figlio.communicate()
        controllo("--apri con --primo-piano: non stampa niente", uscita == "", uscita)
    finally:
        lancia("--spegni")

# 6. Audit #6: un file con BOM si legge come uno senza
studio = os.path.join(BASE, "bom")
os.makedirs(os.path.join(studio, "periodo"))
dato = {"versione": "0.5.0", "periodo": "p", "todo": [{"id": "t1", "titolo": "Chiamare lo studio", "stato": "da-fare"}]}
testo = json.dumps(dato, ensure_ascii=False)
for nome, dati in (("senza BOM", testo.encode("utf-8")), ("con BOM", b"\xef\xbb\xbf" + testo.encode("utf-8"))):
    with open(os.path.join(studio, "periodo", "todo.json"), "wb") as f:
        f.write(dati)
    letto = pannello.leggi_json(os.path.join(studio, "periodo", "todo.json"))
    voci = pannello.vista_periodo(studio)["todo"]["todo"]
    controllo("todo.json %s: leggi_json e la vista periodo mostrano la stessa cosa" % nome,
              letto == dato and [v.get("titolo") for v in voci] == ["Chiamare lo studio"], (letto, voci))
with open(os.path.join(studio, "periodo", "obiettivo.md"), "wb") as f:
    f.write(b"\xef\xbb\xbf# Obiettivo\n\nFare bene.\n")
controllo("un testo con BOM non porta il BOM in testa", pannello.leggi_testo(os.path.join(studio, "periodo", "obiettivo.md")).startswith("# Obiettivo"))

# 7. Audit #12: le fonti non elencano i file di sistema (anche con le maiuscole diverse)
os.makedirs(os.path.join(studio, "fonti"))
for n in ("fattura.pdf", "desktop.ini", "Desktop.INI", "Thumbs.db", "THUMBS.DB", ".DS_Store", ".ds_store", "LEGGIMI.md", "thumbs.db.pdf"):
    open(os.path.join(studio, "fonti", n), "w").close()
os.makedirs(os.path.join(studio, "fonti", "clienti"))
visti = sorted(v["nome"] for v in pannello.vista_fonti(studio))
controllo("fonti: niente desktop.ini, Thumbs.db, .DS_Store (qualsiasi maiuscola); restano gli altri file",
          visti == ["clienti", "fattura.pdf", "thumbs.db.pdf"], visti)

# 8. Audit #10: ferma_corsa legge l'output di corsa.py come UTF-8, anche se non è valido
corse = os.path.join(studio, "grafi", "corse")
os.makedirs(corse)
open(os.path.join(corse, "g-20260101-000000.json"), "w").write("{}")
visto = {}


def run_finto(cmd, **kw):
    visto.update(kw)
    return subprocess.CompletedProcess(cmd, 0, "", "")


with mock.patch.object(pannello, "cerca_script", lambda *a: "corsa.py"), mock.patch.object(subprocess, "run", run_finto):
    codice, corpo = pannello.ferma_corsa(studio, "g-20260101-000000")
controllo("ferma_corsa: subprocess.run decodifica in UTF-8 con errors=replace (non in cp1252)",
          codice == 200 and visto.get("encoding") == "utf-8" and visto.get("errors") == "replace", visto)
Pannello_script = os.path.join(BASE, "corsa-sporca.py")
with open(Pannello_script, "w", encoding="utf-8") as f:
    f.write("import sys\nsys.stdout.buffer.write(b'Fermata \\x81\\x8d\\x8f')\n")
with mock.patch.object(pannello, "cerca_script", lambda *a: Pannello_script):
    codice, corpo = pannello.ferma_corsa(studio, "g-20260101-000000")
controllo("ferma_corsa: un output con byte non UTF-8 non rompe lo stop", codice == 200, (codice, corpo))

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
