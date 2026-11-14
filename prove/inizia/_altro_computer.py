# redacy 0.4.2 · prove/inizia/_altro_computer.py (lo lancia prova-cartella.sh)
# Prova crea-cartella.py con i controlli automatici scritti per un altro computer (una cartella nata su Linux e
# usata su Windows, o il contrario) e con le scritture che devono andare a capo con \n anche su Windows.
# Il ramo Windows si forza con `mock` (come fa prove/windows/_portabile.py): qui non si lancia niente di vero.
# Una riga per controllo: «ok» o «NO». In fondo PASSA o FALLISCE.
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import types
from pathlib import Path
from unittest import mock

RADICE, BASE = sys.argv[1], sys.argv[2]
SCRIPT = os.path.join(RADICE, "skills", "inizia", "scripts", "crea-cartella.py")
FALLITE = []
os.makedirs(BASE, exist_ok=True)
HOOK = [".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json"]

spec = importlib.util.spec_from_file_location("crea_cartella_k1", SCRIPT)
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok  " if ok else "NO  ") + descrizione + ((" · " + str(dettaglio)[:400]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def albero(cartella):
    out = {}
    for base, _, nomi in os.walk(cartella):
        for n in nomi:
            p = os.path.join(base, n)
            if not os.path.islink(p):
                out[os.path.relpath(p, cartella)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def json_di(cartella, rel):
    return json.load(open(os.path.join(cartella, rel), encoding="utf-8"))


def comandi(cartella, rel):
    return [h["command"] for gs in json_di(cartella, rel)["hooks"].values() for g in gs for h in g["hooks"]]


def lancia(cartella, *opzioni, windows=False, rispondono=("python",)):
    """Lancia main() qui dentro: con windows=True `su_windows()` è vero e solo gli interpreti in `rispondono`
    rispondono da Python 3 (gli altri come lo stub del Microsoft Store). Restituisce (uscita, testo)."""
    def run_finto(argv, **kw):
        ok = " ".join(argv[:-2]) in rispondono
        return types.SimpleNamespace(returncode=0 if ok else 9009, stdout="3\n" if ok else "", stderr="")

    buf = io.StringIO()
    contesto = [mock.patch.object(M, "su_windows", lambda: windows)]
    if windows:
        contesto.append(mock.patch.object(subprocess, "run", run_finto))
    with contextlib.ExitStack() as pila, contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        for c in contesto:
            pila.enter_context(c)
        rc = M.main([str(cartella), "--plugin", RADICE, *opzioni])
    return rc, buf.getvalue()


def avvisi_hook(u):
    return [r for r in u.splitlines() if r.startswith("avviso: ") and "altro computer" in r]


# ---------------------------------------------------------------- una cartella nata su Linux, usata su Windows
L = os.path.join(BASE, "nata-linux-%d" % os.getpid())
rc, u = lancia(L)
controllo("su Linux la cartella nasce con i comandi del modello (bash e python3)",
          rc == 0 and all("python3" in c and "[ ! -f" in c for r in HOOK for c in comandi(L, r)), u)
rc, u = lancia(L, "--controlla")
controllo("su Linux --controlla è pulito, senza avvisi", rc == 0 and "avviso" not in u, u)
prima_linux = albero(L)

rc, u = lancia(L, "--controlla", windows=True)
av = avvisi_hook(u)
controllo("su Windows (forzato) --controlla avvisa sui tre file, in due parole dice «bash con python3» e che fare",
          rc == 0 and len(av) == 3 and all(any(f"avviso: {r}:" in a for a in av) for r in HOOK)
          and all("(bash con python3)" in a and "--aggiorna" in a for a in av), u)
controllo("l'avviso non cambia il codice di uscita e --controlla non scrive", rc == 0 and albero(L) == prima_linux, u)

rc, u = lancia(L, "--aggiorna", windows=True)
agg = [r for r in u.splitlines() if r.startswith("aggiornato: ")]
controllo("--aggiorna riscrive i tre file e per ognuno stampa «aggiornato: <file> (controlli riscritti per questo computer)»",
          rc == 0 and sorted(agg) == sorted(f"aggiornato: {r} (controlli riscritti per questo computer)" for r in HOOK), u)
tutti = " ".join(c for r in HOOK for c in comandi(L, r))
controllo("ora i comandi sono quelli di Windows: python -c …; exit $LASTEXITCODE, niente python3 né [ ]",
          "python -c" in tutti and "$LASTEXITCODE" in tutti and "python3" not in tutti and "[ ! -f" not in tutti, tutti[:200])
controllo("i tre file hanno ancora le stesse voci, il solo cambiamento è il comando",
          len({json.dumps(json_di(L, r)["hooks"], sort_keys=True) for r in HOOK}) == 1)
controllo("un file fatto solo dei controlli di redacy non ha bisogno della copia di sicurezza",
          not any(f.endswith(".prima-di-redacy") for f in albero(L)), sorted(albero(L)))
controllo(".agents/hooks.json conserva la sua chiave «description»", "description" in json_di(L, ".agents/hooks.json"))
rc, u = lancia(L, "--controlla", windows=True)
controllo("su Windows poi --controlla non avvisa più", rc == 0 and "avviso" not in u, u)
dopo = albero(L)
rc, u = lancia(L, "--aggiorna", windows=True)
controllo("una seconda --aggiorna non cambia niente (nemmeno le copie) e non stampa «aggiornato:»",
          rc == 0 and albero(L) == dopo and "aggiornato: " not in u, u)

# ---------------------------------------------------------------- una cartella nata su Windows, usata su Linux
W = os.path.join(BASE, "nata-windows-%d" % os.getpid())
rc, u = lancia(W, windows=True)
controllo("su Windows (forzato) la cartella nasce con i comandi di Windows",
          rc == 0 and all("python -c" in c and "$LASTEXITCODE" in c for r in HOOK for c in comandi(W, r)), u)
rc, u = lancia(W, "--controlla", windows=True)
controllo("su Windows --controlla è pulito", rc == 0 and "avviso" not in u, u)
rc, u = lancia(W, "--controlla")
av = avvisi_hook(u)
controllo("su Linux --controlla avvisa sui tre file («Windows con python»)",
          rc == 0 and len(av) == 3 and all("(Windows con python)" in a and "--aggiorna" in a for a in av), u)
rc, u = lancia(W, "--aggiorna")
controllo("su Linux --aggiorna li riscrive", rc == 0 and u.count("aggiornato: ") == 3, u)
modello = {r: json.load(open(os.path.join(RADICE, "skills/inizia/modello", r), encoding="utf-8"))["hooks"] for r in HOOK}
controllo("le voci tornano quelle del modello (comando e matcher)", all(json_di(W, r)["hooks"] == modello[r] for r in HOOK))
rc, u = lancia(W, "--controlla")
controllo("su Linux poi --controlla non avvisa più", rc == 0 and "avviso" not in u, u)

# ---------------------------------------------------------------- un hook dell'utente nello stesso file resta com'è
U = os.path.join(BASE, "utente-%d" % os.getpid())
mio = {"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mio", "timeout": 5}]}
altro = {"permissions": {"allow": ["Bash(ls)"]}, "env": {"A": "è"},
         "hooks": {"PreToolUse": [mio], "Stop": [{"hooks": [{"type": "command", "command": "echo fine"}]}]}}
lancia(U)
d = json_di(U, ".claude/settings.json")
d["hooks"]["PreToolUse"].insert(0, mio)  # prima il suo, poi quello di redacy
d["hooks"]["Stop"] = altro["hooks"]["Stop"]
d.update({"permissions": altro["permissions"], "env": altro["env"]})
open(os.path.join(U, ".claude/settings.json"), "w", encoding="utf-8").write(json.dumps(d, indent=1, ensure_ascii=False))
rc, u = lancia(U, "--aggiorna", windows=True)
d = json_di(U, ".claude/settings.json")
controllo("l'hook dell'utente, i permessi, le altre chiavi e l'ordine restano identici; cambia solo il comando di redacy",
          d["permissions"] == altro["permissions"] and d["env"] == altro["env"] and d["hooks"]["PreToolUse"][0] == mio
          and d["hooks"]["Stop"] == altro["hooks"]["Stop"] and list(d) == ["hooks", "permissions", "env"]
          and "python -c" in d["hooks"]["PreToolUse"][1]["hooks"][0]["command"]
          and "python -c" in d["hooks"]["PostToolUse"][0]["hooks"][0]["command"], d)
controllo("se il file ha qualcosa oltre ai gruppi del plugin, prima salva la copia (.prima-di-redacy) uguale a com'era",
          os.path.isfile(os.path.join(U, ".claude/settings.json.prima-di-redacy"))
          and "python3" in open(os.path.join(U, ".claude/settings.json.prima-di-redacy"), encoding="utf-8").read(), u)
controllo("«aggiornato:» per il file dell'utente e per gli altri due", u.count("aggiornato: ") == 3, u)
rc, u = lancia(U, "--controlla", windows=True)
controllo("poi su Windows --controlla è pulito", rc == 0 and "avviso" not in u, u)

# ---------------------------------------------------------------- py -3 su un PC dove risponde anche python: non si riscrive
P = os.path.join(BASE, "py3-%d" % os.getpid())
rc, u = lancia(P, windows=True, rispondono=("py -3",))
controllo("con solo py -3 che risponde i comandi nascono con py -3", all(c.startswith("py -3 -c") for r in HOOK for c in comandi(P, r)), u)
prima = albero(P)
rc, u = lancia(P, "--controlla", windows=True, rispondono=("python", "py -3"))
controllo("su un PC dove risponde anche python, --controlla non avvisa (py -3 va bene)", rc == 0 and "avviso" not in u, u)
rc, u = lancia(P, "--aggiorna", windows=True, rispondono=("python", "py -3"))
controllo("e --aggiorna non riscrive niente (in Codex ogni riscrittura chiede di riapprovare gli hook)",
          rc == 0 and albero(P) == prima and "aggiornato: " not in u, u)
rc, u = lancia(P, "--controlla", windows=True, rispondono=("python",))
av = avvisi_hook(u)
controllo("se py -3 non risponde più, --controlla avvisa e dice che l'interprete non risponde",
          len(av) == 3 and all("py -3" in a and "non risponde" in a for a in av), u)
rc, u = lancia(P, "--aggiorna", windows=True, rispondono=("python",))
controllo("e --aggiorna li riscrive con python", rc == 0 and u.count("aggiornato: ") == 3
          and all(c.startswith("python -c") for r in HOOK for c in comandi(P, r)), u)

# ---------------------------------------------------------------- il matcher con PowerShell (audit Windows #4)
vecchio_matcher = "Write|Edit|MultiEdit|NotebookEdit|apply_patch|Bash|shell|exec_command|local_shell|unified_exec"
mod = [json.load(open(os.path.join(RADICE, "skills/inizia/modello", r), encoding="utf-8"))["hooks"]["PostToolUse"][0]["matcher"]
       for r in HOOK]
controllo("il matcher di PostToolUse è lo stesso nei tre file del modello e nomina PowerShell",
          len(set(mod)) == 1 and "PowerShell" in mod[0].split("|"), mod)
V = os.path.join(BASE, "matcher-vecchio-%d" % os.getpid())
lancia(V)
for r in HOOK:
    t = open(os.path.join(V, r), encoding="utf-8").read()
    assert mod[0] in t
    open(os.path.join(V, r), "w", encoding="utf-8").write(t.replace(mod[0], vecchio_matcher))
rc, u = lancia(V, "--controlla")
controllo("una cartella col matcher di prima non risulta «senza controlli» (niente non va, niente avvisi)",
          rc == 0 and "non va" not in u and "non ha i controlli" not in u and "avviso" not in u, u)
rc, u = lancia(V, "--aggiorna", windows=True)
controllo("--aggiorna, quando riscrive i comandi, riallinea anche il matcher dei gruppi del plugin",
          all(json_di(V, r)["hooks"]["PostToolUse"][0]["matcher"] == mod[0] for r in HOOK), u)
rc, u = lancia(V, "--innesta")
controllo("--innesta riconosce ancora le voci col matcher di prima (0 innestati)", rc == 0 and "esito: 0 innestati" in u, u)

# ---------------------------------------------------------------- Codex: .agents/ e .codex/ protette
if hasattr(os, "geteuid") and os.geteuid() != 0:
    C = os.path.join(BASE, "codex-%d" % os.getpid())
    lancia(C)
    for r in (".agents/hooks.json", ".codex/hooks.json"):
        os.chmod(os.path.join(C, r), 0o444)
    rc, u = lancia(C, "--aggiorna", windows=True)
    for r in (".agents/hooks.json", ".codex/hooks.json"):
        os.chmod(os.path.join(C, r), 0o644)
    controllo("con i file in sola lettura esce 3, «non scritto:» e la riga «comando:» (con --aggiorna), il resto si riscrive",
              rc == 3 and "non scritto: .agents/hooks.json" in u and "non scritto: .codex/hooks.json" in u
              and any(r.startswith("comando: ") and r.endswith(" --aggiorna") for r in u.splitlines())
              and u.count("aggiornato: ") == 1 and "python -c" in comandi(C, ".claude/settings.json")[0], u)
else:
    print("salto  file degli hook in sola lettura (si è root)")

# ---------------------------------------------------------------- a capo `\n` in ogni scrittura (audit Windows #7)
scritture = []
vera_open = open


def open_spiata(file, mode="r", buffering=-1, encoding=None, errors=None, newline=None, *a, **k):
    if ("w" in mode or "a" in mode) and "b" not in mode:
        scritture.append((str(file), mode, newline))
    return vera_open(file, mode, buffering, encoding, errors, newline, *a, **k)


import builtins
import io as _io
N = os.path.join(BASE, "a-capo-%d" % os.getpid())
os.makedirs(os.path.join(N, ".claude"))
open(os.path.join(N, ".claude/settings.json"), "w", encoding="utf-8").write('{"permissions": {}}')
with mock.patch.object(builtins, "open", open_spiata), mock.patch.object(_io, "open", open_spiata):
    lancia(N, windows=True)                    # crea: hook e launch.json di Windows, copie, LOG
    lancia(N, "--innesta")                     # l'innesto del settings.json
    for r in (".agents/script/corsa.py",):
        t = open(os.path.join(N, r), encoding="utf-8").read()
        vera_open(os.path.join(N, r), "w", encoding="utf-8").write(t.replace("redacy 0.4.2 ·", "redacy 0.4.0 ·", 1))
    lancia(N, "--aggiorna")                    # rinfresca una copia
    t = vera_open(os.path.join(N, ".agents/hooks.json"), encoding="utf-8").read()
    vera_open(os.path.join(N, ".agents/hooks.json"), "w", encoding="utf-8").write(t.replace("python -c", "python3 -c"))
    lancia(N, "--aggiorna", windows=False)
sbagliate = [s for s in scritture if s[2] != "\n"]
controllo("ogni scrittura di testo (hook di Windows, launch.json, copie, LOG, innesto, aggiorna) apre con newline=\"\\n\"",
          len(scritture) >= 10 and not sbagliate, (len(scritture), sbagliate[:3]))

# ---------------------------------------------------------------- UTF-8 nelle sonde e nelle giunzioni (audit Windows #10)
chiamate = []


def run_spia(argv, **kw):
    chiamate.append((list(argv), kw))
    return types.SimpleNamespace(returncode=0, stdout="3\n", stderr="")


def symlink_no(*a, **k):
    raise OSError(22, "A required privilege is not held by the client")


G = os.path.join(BASE, "sonde-%d" % os.getpid())
with mock.patch.object(M, "su_windows", lambda: True), mock.patch.object(subprocess, "run", run_spia), \
        mock.patch.object(os, "symlink", symlink_no), contextlib.redirect_stdout(io.StringIO()):
    M.main([G, "--plugin", RADICE])
sonde = [kw for argv, kw in chiamate if "-c" in argv]
giunzioni = [kw for argv, kw in chiamate if argv[:3] == ["cmd", "/c", "mklink"]]
controllo("la sonda di Python e la giunzione leggono l'uscita con encoding=utf-8 e errors=replace",
          sonde and giunzioni and all(kw.get("encoding") == "utf-8" and kw.get("errors") == "replace" for kw in sonde + giunzioni),
          (len(sonde), len(giunzioni), (sonde + giunzioni)[:1]))
P3 = os.path.join(BASE, "py3-bis-%d" % os.getpid())
lancia(P3, windows=True, rispondono=("py -3",))
chiamate.clear()
with mock.patch.object(M, "su_windows", lambda: True), mock.patch.object(subprocess, "run", run_spia), \
        contextlib.redirect_stdout(io.StringIO()):
    M.main([P3, "--controlla", "--plugin", RADICE])  # comandi con py -3: la sonda sceglie python e controlla py -3
sonde_n = [" ".join(argv[:-2]) for argv, kw in chiamate if "-c" in argv]
controllo("ogni interprete si prova una volta sola (la stessa sonda per scegliere e per controllare)",
          sorted(sonde_n) == ["py -3", "python"], sonde_n)

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
