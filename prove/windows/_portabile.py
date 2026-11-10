# redacy 0.4.2 · prove/windows/_portabile.py (lo lancia prova-portabile.sh)
import contextlib
import importlib.util
import json
import ntpath
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import types
from unittest import mock

RADICE, BASE = sys.argv[1], sys.argv[2]
os.makedirs(BASE, exist_ok=True)
FALLITE = []


def carica(nome, rel):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(RADICE, rel))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


# 1. i moduli si caricano anche senza fcntl (come su Windows)
with mock.patch.dict(sys.modules, {"fcntl": None}):
    try:
        pannello = carica("pannello_p", "skills/pannello/scripts/pannello.py")
        corsa = carica("corsa_p", "skills/crea-grafo/scripts/corsa.py")
        controllo("pannello.py e corsa.py si caricano senza fcntl", True)
    except ImportError as e:
        controllo("pannello.py e corsa.py si caricano senza fcntl", False, e)
        sys.exit(1)
periodo = carica("periodo_p", "skills/pianifica-periodo/scripts/controlla-periodo.py")
ferma = carica("ferma_p", "skills/pannello/scripts/ferma.py")
cartella_py = carica("cartella_p", "skills/inizia/scripts/crea-cartella.py")


# 2. il lucchetto sul ramo Windows: msvcrt finto
class MsvcrtFinto(types.ModuleType):
    LK_LOCK, LK_UNLCK = 1, 0

    def __init__(self):
        super().__init__("msvcrt")
        self.chiamate = []

    def locking(self, fd, modo, n):
        self.chiamate.append((modo, n))


for nome, mod in (("pannello", pannello), ("corsa", corsa)):
    finto = MsvcrtFinto()
    d = tempfile.mkdtemp(dir=BASE)
    fd = os.open(os.path.join(d, ".lock"), os.O_RDWR | os.O_CREAT, 0o600)
    with mock.patch.dict(sys.modules, {"msvcrt": finto}), mock.patch.object(mod, "su_windows", lambda: True):
        mod.blocca_file(fd)
        mod.sblocca_file(fd)
    os.close(fd)
    controllo("%s: il lucchetto Windows blocca e sblocca un byte con msvcrt.locking" % nome,
              finto.chiamate == [(1, 1), (0, 1)], finto.chiamate)
finto = MsvcrtFinto()
with mock.patch.dict(sys.modules, {"msvcrt": finto}), mock.patch.object(corsa, "su_windows", lambda: True):
    with corsa.lucchetto(os.path.join(BASE, ".prova.lock")):
        pass
controllo("corsa.lucchetto() usa lo stesso ramo", finto.chiamate == [(1, 1), (0, 1)], finto.chiamate)

# il lucchetto Unix funziona ancora (due processi non entrano insieme)
with corsa.lucchetto(os.path.join(BASE, ".unix.lock")):
    r = subprocess.run([sys.executable, "-I", "-c",
                        "import fcntl,os,sys;fd=os.open(sys.argv[1],os.O_RDWR);"
                        "fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)", os.path.join(BASE, ".unix.lock")],
                       capture_output=True)
controllo("macOS/Linux: il lucchetto con fcntl tiene fuori un altro processo", r.returncode != 0)


# 3. pid_vivo su Windows: kernel32 finto, e os.kill non viene mai chiamato
class Kernel32Finto:
    def __init__(self, apre, codice, ultimo_errore=0):
        self.apre, self.codice, self.ultimo = apre, codice, ultimo_errore
        self.chiusi = 0
        self.accesso = None

        def apri(accesso, ereditare, pid):  # funzioni, non metodi: pannello.py ci mette restype e argtypes
            self.accesso = accesso
            return 4321 if self.apre else 0

        def codice_uscita(h, ref):
            ref._obj.value = self.codice
            return 1

        def chiudi(h):
            self.chiusi += 1

        self.OpenProcess, self.GetExitCodeProcess, self.CloseHandle = apri, codice_uscita, chiudi


import ctypes


def vivo(k):
    with mock.patch.object(ctypes, "WinDLL", lambda *a, **kw: k, create=True), \
         mock.patch.object(ctypes, "get_last_error", lambda: k.ultimo, create=True):
        return pannello.pid_vivo(1234)


def morto_se_kill(*a):
    raise AssertionError("os.kill chiamato")


try:
    with mock.patch.object(pannello, "su_windows", lambda: True), mock.patch.object(os, "kill", morto_se_kill):
        k = Kernel32Finto(True, 259)
        controllo("pid_vivo Windows: processo in esecuzione (STILL_ACTIVE) è vivo", vivo(k) is True and k.chiusi == 1)
        controllo("pid_vivo Windows: chiede solo PROCESS_QUERY_LIMITED_INFORMATION", k.accesso == 0x1000, hex(k.accesso))
        controllo("pid_vivo Windows: processo finito (codice 0) è morto", vivo(Kernel32Finto(True, 0)) is False)
        controllo("pid_vivo Windows: pid che non c'è (errore 87) è morto", vivo(Kernel32Finto(False, 0, 87)) is False)
        controllo("pid_vivo Windows: accesso negato (5) vuol dire che c'è", vivo(Kernel32Finto(False, 0, 5)) is True)
        controllo("pid_vivo: un pid non valido è morto", pannello.pid_vivo(0) is False and pannello.pid_vivo("x") is False)
except AssertionError as e:
    controllo("pid_vivo Windows non chiama os.kill", False, e)
controllo("pid_vivo su Linux: il proprio pid è vivo, uno inesistente no", pannello.pid_vivo(os.getpid()) and not pannello.pid_vivo(2 ** 22 + 12345))

class MsvcrtConFlock(MsvcrtFinto):
    """msvcrt finto che blocca davvero (con flock): se il genitore non rilascia il lucchetto, il figlio resta fermo."""

    def locking(self, fd, modo, n):
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX if modo == self.LK_LOCK else fcntl.LOCK_UN)


# 4. il pannello parte senza fork (Popen staccato), si riconosce, si spegne
studio = os.path.join(BASE, "studio")
os.makedirs(os.path.join(studio, "grafi"), exist_ok=True)
open(os.path.join(studio, "AGENTS.md"), "w").write("# prova\n")
FLAG = 0x00000008 | 0x00000200 | 0x08000000
visti = {}
popen_vero = subprocess.Popen


def popen_finto(cmd, **kw):
    visti["cmd"], visti["flag"] = cmd, kw.pop("creationflags", None)
    visti["stdin"] = kw.get("stdin")
    return popen_vero(cmd, start_new_session=True, **kw)  # su Linux il distacco lo fa la sessione nuova


def fork_vietato(*a):
    raise AssertionError("os.fork chiamato su Windows")


def _vivo_unix(pid):
    with contextlib.suppress(ChildProcessError):
        os.waitpid(pid, os.WNOHANG)  # il figlio finito resta zombie finché non lo si raccoglie
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


try:
    with mock.patch.dict(sys.modules, {"msvcrt": MsvcrtConFlock()}), \
         mock.patch.object(pannello, "su_windows", lambda: True), \
         mock.patch.object(pannello, "pid_vivo_windows", _vivo_unix), \
         mock.patch.object(subprocess, "Popen", popen_finto), \
         mock.patch.object(os, "fork", fork_vietato), \
         mock.patch.object(os, "setsid", fork_vietato):
        info, nuovo = pannello.accendi(studio, None, False, 1.0)
        controllo("pannello Windows: parte senza os.fork e dice che è nuovo", nuovo is True and info["porta"])
        controllo("pannello Windows: Popen con DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW",
                  visti.get("flag") == FLAG, visti.get("flag"))
        controllo("pannello Windows: il figlio rilancia questo file in primo piano, con la porta e le ore",
                  visti["cmd"][1].endswith("pannello.py") and "--primo-piano" in visti["cmd"]
                  and visti["cmd"][visti["cmd"].index("--porta") + 1] == str(info["porta"])
                  and "--inattivo-ore" in visti["cmd"], visti["cmd"])
        controllo("pannello Windows: il figlio non legge dal terminale", visti["stdin"] == subprocess.DEVNULL)
        scritto = json.load(open(os.path.join(studio, "interfaccia", "pannello.json")))
        controllo("pannello Windows: pannello.json ha porta, pid e gettone", scritto["porta"] == info["porta"]
                  and isinstance(scritto["pid"], int) and len(scritto["gettone"]) >= 20)
        url = "http://127.0.0.1:%d/" % info["porta"]
        controllo("pannello Windows: rispondere due volte riusa quello acceso",
                  pannello.accendi(studio, None, False, 1.0)[1] is False)
        pid = scritto["pid"]
        pannello.spegni(studio)
        controllo("pannello Windows: spegni ferma il processo e non lascia pannello.json",
                  not _vivo_unix(pid) and not os.path.exists(os.path.join(studio, "interfaccia", "pannello.json")))
except AssertionError as e:
    controllo("pannello Windows senza fork", False, e)
finally:
    p = os.path.join(studio, "interfaccia", "pannello.json")
    if os.path.exists(p):
        with contextlib.suppress(Exception):
            os.kill(json.load(open(p))["pid"], signal.SIGKILL)

# spegni con un server che muore di colpo (come TerminateProcess): pannello.json va tolto da spegni
studio2 = os.path.join(BASE, "studio2")
os.makedirs(os.path.join(studio2, "interfaccia"), exist_ok=True)
proc = subprocess.Popen([sys.executable, "-I", "-c", "import time;time.sleep(60)"])
pannello.scrivi_info(studio2, {"pid": proc.pid, "porta": 47999, "cartella": studio2, "gettone": "x"})
uccisi = []
kill_vero = os.kill


def uccidi(pid, sig):
    uccisi.append(sig)
    kill_vero(pid, signal.SIGKILL)
    proc.wait()


with mock.patch.object(pannello, "su_windows", lambda: True), \
     mock.patch.object(pannello, "pid_vivo_windows", lambda pid: proc.poll() is None), \
     mock.patch.object(pannello, "risponde", lambda *a, **k: True), \
     mock.patch.object(os, "kill", uccidi):
    pannello.spegni(studio2)
controllo("spegni Windows: dopo la terminazione toglie pannello.json", not os.path.exists(pannello.percorso_info(studio2)) and uccisi)

# 5. launch.json: python3 su Unix, il Python che gira su Windows
controllo("launch.json: su Linux resta python3", pannello.eseguibile_python() == "python3")
with mock.patch.object(pannello, "su_windows", lambda: True):
    controllo("launch.json: su Windows è sys.executable", pannello.eseguibile_python() == sys.executable)
    d = tempfile.mkdtemp(dir=BASE)
    os.makedirs(os.path.join(d, ".claude"))
    shutil.copy(os.path.join(RADICE, "skills/pannello/modello/launch.json"), os.path.join(d, ".claude/launch.json"))
    pannello.aggiorna_launch(d, 47123)
    v = json.load(open(os.path.join(d, ".claude/launch.json")))["configurations"][0]
    controllo("aggiorna_launch su Windows scrive sys.executable e la porta", v["runtimeExecutable"] == sys.executable and v["port"] == 47123)
d = tempfile.mkdtemp(dir=BASE)
os.makedirs(os.path.join(d, ".claude"))
shutil.copy(os.path.join(RADICE, "skills/pannello/modello/launch.json"), os.path.join(d, ".claude/launch.json"))
pannello.aggiorna_launch(d, 47123)
controllo("aggiorna_launch su Linux scrive python3",
          json.load(open(os.path.join(d, ".claude/launch.json")))["configurations"][0]["runtimeExecutable"] == "python3")

# 6. i percorsi con la barra rovesciata negli hook
ev_win = {"cwd": "C:\\Users\\Mario Rossi\\studio", "tool_input": {"file_path": "C:\\Users\\Mario Rossi\\studio\\periodo\\todo.json"}}
def windows_per(modulo):
    pila = contextlib.ExitStack()
    pila.enter_context(mock.patch.object(modulo, "su_windows", lambda: True))
    pila.enter_context(mock.patch.object(os, "path", ntpath))
    return pila


with windows_per(periodo):
    t = periodo.file_toccati(ev_win)
controllo("controlla-periodo su Windows trova periodo\\todo.json con il disco e gli spazi",
          t == ["C:\\Users\\Mario Rossi\\studio\\periodo\\todo.json"], t)
with windows_per(periodo):
    t3 = periodo.file_toccati({"cwd": "C:\\s", "tool_input": {"command": "echo {} > C:\\s\\periodo\\idee.json"}})
controllo("controlla-periodo su Windows trova il percorso anche in un comando di shell", t3 == ["C:\\s\\periodo\\idee.json"], t3)
with windows_per(periodo):
    t2 = periodo.file_toccati({"cwd": "C:\\s", "tool_input": {"patch": "*** Update File: periodo/idee.json"}})
controllo("controlla-periodo su Windows trova ancora il percorso con la barra normale (Codex)",
          t2 == ["C:\\s\\periodo\\idee.json"], t2)
controllo("controlla-periodo su Linux: lo stesso evento Windows non cambia (nessun risultato)", periodo.file_toccati(ev_win) == [])
controllo("controlla-periodo su Linux: un percorso Unix si trova come prima",
          periodo.file_toccati({"cwd": "/x", "tool_input": {"file_path": "/x/periodo/todo.json"}}) == ["/x/periodo/todo.json"])
ev_log = {"tool_input": {"file_path": "C:\\s\\memoria\\LOG.md"}}
with mock.patch.object(ferma, "su_windows", lambda: True):
    controllo("ferma.py su Windows: una scrittura in memoria\\LOG.md passa", ferma.legge_log(ev_log) is True)
controllo("ferma.py su Linux: lo stesso percorso non conta", ferma.legge_log(ev_log) is False)
controllo("ferma.py su Linux: memoria/LOG.md conta", ferma.legge_log({"tool_input": {"file_path": "/s/memoria/LOG.md"}}) is True)

# 7. i comandi degli hook per Windows: provati in bash (e in PowerShell se c'è pwsh) con "python3" al posto del nome
cmd = cartella_py.comando_hook("python3", "controlla-periodo.py")
controllo("comando_hook: niente && e niente [ ] di bash", "&&" not in cmd and "[ " not in cmd and "||" not in cmd, cmd)
prog = tempfile.mkdtemp(dir=BASE)
os.makedirs(os.path.join(prog, "periodo"))
os.makedirs(os.path.join(prog, ".agents/hooks"))
for f in ("controlla-periodo.py", "todo.schema.json", "idee.schema.json"):
    shutil.copy(os.path.join(RADICE, "skills/pianifica-periodo/scripts", f), os.path.join(prog, ".agents/hooks", f))
open(os.path.join(prog, "periodo/todo.json"), "w").write(json.dumps(
    {"versione": "0.3.0", "periodo": "", "todo": [{"id": "t1", "stato": "boh"}]}))
evento = json.dumps({"cwd": prog, "hook_event_name": "PostToolUse", "tool_input": {"file_path": prog + "/periodo/todo.json"}})
env = dict(os.environ, CLAUDE_PROJECT_DIR=prog)
shells = [("bash", ["bash", "-c"])]
if shutil.which("pwsh"):
    shells.append(("PowerShell (pwsh)", ["pwsh", "-NoProfile", "-Command"]))
for nome, pre in shells:
    r = subprocess.run(pre + [cmd], input=evento, capture_output=True, text=True, env=env)
    controllo("l'hook di controllo in %s esce 2 e dice cosa non va" % nome, r.returncode == 2 and "non è fra i valori ammessi" in r.stderr,
              (r.returncode, r.stderr[-200:]))
    os.rename(os.path.join(prog, ".agents/hooks/controlla-periodo.py"), os.path.join(prog, "x.py"))
    r = subprocess.run(pre + [cmd], input=evento, capture_output=True, text=True, env=env)
    os.rename(os.path.join(prog, "x.py"), os.path.join(prog, ".agents/hooks/controlla-periodo.py"))
    controllo("l'hook con lo script che manca esce 0 in %s" % nome, r.returncode == 0, (r.returncode, r.stderr[-200:]))
r = subprocess.run(["bash", "-c", cmd], input="{}", capture_output=True, text=True, cwd=prog, env={k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"})
controllo("l'hook senza CLAUDE_PROJECT_DIR (Codex) cerca da cwd", r.returncode == 0, r.stderr[-200:])

# 8. crea-cartella su Windows: hook, launch.json, giunzione, comando di ripresa
spec = os.path.join(RADICE, "skills/inizia/modello")
def crea_come_windows(destinazione, prima=None):
    os.makedirs(destinazione, exist_ok=True)
    if prima:
        prima(destinazione)
    esito = cartella_py.Esito()
    chiamate = []

    def run_finto(argv, **kw):
        chiamate.append(argv)
        if argv[:3] == ["cmd", "/c", "mklink"]:
            os.makedirs(argv[4], exist_ok=True)  # la giunzione finta è una cartella
            return types.SimpleNamespace(returncode=0, stdout="", stderr="")
        return types.SimpleNamespace(returncode=0, stdout="3\n", stderr="")

    def symlink_rifiutato(*a, **k):
        raise OSError(22, "A required privilege is not held by the client")

    with mock.patch.object(cartella_py, "su_windows", lambda: True), \
         mock.patch.object(subprocess, "run", run_finto), \
         mock.patch.object(os, "symlink", symlink_rifiutato):
        cartella_py.crea(__import__("pathlib").Path(destinazione), __import__("pathlib").Path(RADICE), "0.4.2", esito)
    return esito, chiamate


D = os.path.join(BASE, "cartella-win")
esito, chiamate = crea_come_windows(D)
voci = {}
for r_ in (".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json"):
    testo = open(os.path.join(D, r_), encoding="utf-8").read()
    voci[r_] = json.loads(testo)["hooks"]
controllo("Windows: le voci degli hook sono uguali nei tre file", len({json.dumps(v, sort_keys=True) for v in voci.values()}) == 1)
tutti = json.dumps(voci[".claude/settings.json"])
controllo("Windows: gli hook non dicono python3 e non hanno && né [ ]", "python3" not in tutti and "&&" not in tutti and "[ ! -f" not in tutti, tutti[:200])
controllo("Windows: gli hook dicono il nome trovato da python_windows (qui «python»: il primo che risponde)",
          '"command": "python -c' in open(os.path.join(D, ".claude/settings.json"), encoding="utf-8").read())
controllo("Windows: gli hook nominano ferma.py e controlla-periodo.py", "ferma.py" in tutti and "controlla-periodo.py" in tutti)
lj = json.load(open(os.path.join(D, ".claude/launch.json"), encoding="utf-8"))["configurations"][0]
controllo("Windows: .claude/launch.json lancia sys.executable, non python3", lj["runtimeExecutable"] == sys.executable, lj)
controllo("Windows: i collegamenti ripiegano sulla giunzione (mklink /J)",
          any(c[:4] == ["cmd", "/c", "mklink", "/J"] for c in chiamate) and any("(giunzione)" in c for c in esito.creati), esito.creati[:4])
controllo("Windows: il LOG dice cosa è stato creato", "· inizia ·" in open(os.path.join(D, "memoria/LOG.md"), encoding="utf-8").read())
# non sovrascrive: un settings.json dell'utente resta
D2 = os.path.join(BASE, "cartella-win-esistente")
esito2, _ = crea_come_windows(D2, prima=lambda d: (os.makedirs(os.path.join(d, ".claude")),
                                                     open(os.path.join(d, ".claude/settings.json"), "w").write('{"mio": 1}')))
controllo("Windows: un .claude/settings.json che c'è già non si tocca",
          open(os.path.join(D2, ".claude/settings.json")).read() == '{"mio": 1}' and ".claude/settings.json" in esito2.saltati)
# la riga di ripresa
e3 = cartella_py.Esito()
e3.non_scritti.append(".agents/ (Permission denied)")
e3.python = "py -3"
import io
buf = io.StringIO()
with mock.patch.object(cartella_py, "su_windows", lambda: True), contextlib.redirect_stdout(buf):
    cartella_py.stampa(e3, __import__("pathlib").Path("C:/Users/Mario Rossi/studio"), False)
riga = [r for r in buf.getvalue().splitlines() if r.startswith("comando: ")]
controllo("Windows: la riga comando: usa py -3, virgolette doppie e niente && né apici",
          len(riga) == 1 and riga[0].startswith('comando: py -3 "') and "&&" not in riga[0] and "'" not in riga[0], riga)
# Linux: la copia è quella di sempre, byte per byte
DL = os.path.join(BASE, "cartella-linux")
subprocess.run([sys.executable, "-I", os.path.join(RADICE, "skills/inizia/scripts/crea-cartella.py"), DL], capture_output=True)
for rel in (".claude/settings.json", ".codex/hooks.json", ".agents/hooks.json"):
    if open(os.path.join(DL, rel), "rb").read() != open(os.path.join(spec, rel), "rb").read():
        controllo("Linux: %s è la copia esatta del modello" % rel, False)
        break
else:
    controllo("Linux: i tre file degli hook sono la copia esatta del modello (python3 e bash)", True)
controllo("Linux: launch.json è la copia esatta del modello",
          open(os.path.join(DL, ".claude/launch.json"), "rb").read() == open(os.path.join(RADICE, "skills/pannello/modello/launch.json"), "rb").read())

# 9. python_windows: scarta lo stub (codice 9009), prende il primo che risponde 3
risposte = {"python": types.SimpleNamespace(returncode=9009, stdout="", stderr="Python was not found"),
            "py": types.SimpleNamespace(returncode=0, stdout="3\n", stderr="")}
with mock.patch.object(subprocess, "run", lambda argv, **kw: risposte[argv[0]]):
    controllo("python_windows scarta lo stub di Microsoft Store e sceglie py -3", cartella_py.python_windows(None) == "py -3")
with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError()):
    e = cartella_py.Esito()
    controllo("python_windows senza niente sul PATH dice «python» e mette un avviso", cartella_py.python_windows(e) == "python" and e.avvisi)

# 10. porta riservata dal sistema (Windows): EACCES al bind vuol dire «prova la prossima», non «sandbox»
import errno
chiamate_porte = []

def crea_server_finto(porta):
    chiamate_porte.append(porta)
    if len(chiamate_porte) == 1:
        raise OSError(errno.EACCES, "Permission denied")
    return "server"

with mock.patch.object(pannello, "crea_server", crea_server_finto), mock.patch.object(pannello, "su_windows", lambda: True):
    try:
        porta_ok, srv = pannello.apri_socket_libera(BASE, 47100)
        controllo("Windows: una porta con EACCES (riservata) si salta e si prova la successiva",
                  srv == "server" and porta_ok == 47101 and chiamate_porte == [47100, 47101], (porta_ok, chiamate_porte))
    except SystemExit as e:
        controllo("Windows: una porta con EACCES (riservata) si salta e si prova la successiva", False, e)
chiamate_porte.clear()
with mock.patch.object(pannello, "crea_server", crea_server_finto), mock.patch.object(pannello, "su_windows", lambda: False):
    try:
        pannello.apri_socket_libera(BASE, 47100)
        controllo("Linux e macOS: EACCES al bind resta il messaggio della sandbox", False, "non si è fermato")
    except SystemExit as e:
        controllo("Linux e macOS: EACCES al bind resta il messaggio della sandbox", "sandbox" in str(e) and chiamate_porte == [47100], (e, chiamate_porte))

# 11. --innesta e --aggiorna con i comandi degli hook di Windows: riconoscono le voci per il nome dello script
D3 = os.path.join(BASE, "cartella-win-innesta")
esito3, _ = crea_come_windows(D3)
radice_p = __import__("pathlib").Path(RADICE)
with mock.patch.object(cartella_py, "su_windows", lambda: True), mock.patch.object(subprocess, "run", lambda argv, **kw: types.SimpleNamespace(returncode=0, stdout="3\n", stderr="")):
    controllo("Windows: una cartella appena creata non ha niente da innestare",
              cartella_py.problemi_innesto(__import__("pathlib").Path(D3), radice_p) == [])
    open(os.path.join(D3, ".claude/settings.json"), "w", encoding="utf-8").write('{"permissions": {}}')
    trovati = cartella_py.problemi_innesto(__import__("pathlib").Path(D3), radice_p)
    controllo("Windows: un settings.json senza hook è segnalato", [r for r, _, _ in trovati] == [".claude/settings.json"], trovati)
    e4 = cartella_py.Esito()
    cartella_py.innesta(__import__("pathlib").Path(D3), radice_p, e4)
    innestato = open(os.path.join(D3, ".claude/settings.json"), encoding="utf-8").read()
    controllo("Windows: l'innesto scrive i comandi di Windows (niente python3, niente [ ])",
              "ferma.py" in innestato and "python3" not in innestato and "[ ! -f" not in innestato and cartella_py.problemi_innesto(__import__("pathlib").Path(D3), radice_p) == [], innestato[:200])

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
