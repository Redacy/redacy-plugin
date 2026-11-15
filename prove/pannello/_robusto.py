# redacy 0.5.0 · prove/pannello/_robusto.py (lo lancia prova-server.sh)
"""Il pannello davanti a dati strani e a cartelle che non vanno: niente 500, niente traceback, niente attese.

Uso: python3 _robusto.py RADICE CARTELLA_DI_PROVA
 - tipi strani nei file dell'utente (scadenza numerica, `passi: 5`, `persa_dopo_minuti: "abc"`, `grafo: [...]`):
   ogni vista risponde, la voce strana si ignora o finisce in `problemi`;
 - todo.json e idee.json che non si leggono compaiono in `problemi`, col loro nome;
 - --porta fuori da 1024-65535: una riga, esce 2; una porta sotto 1024 vietata non cita Codex;
 - interfaccia che è un file o una cartella non scrivibile: una riga con la causa, subito;
 - interfaccia/pannello.json sparito mentre il pannello gira: la seconda accensione lo riprende, --spegni funziona.
Le parti che accendono il pannello vero girano solo su Linux.
"""
import importlib.util
import json
import os
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


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


spec = importlib.util.spec_from_file_location("pannello_robusto", PANNELLO)
pannello = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pannello)


def studio(nome):
    d = os.path.join(BASE, nome)
    r = subprocess.run([sys.executable, PREPARA, d], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        print("FALLISCE preparazione di %s: %s" % (nome, r.stderr))
        sys.exit(1)
    return d


def scrivi(d, rel, testo):
    p = os.path.join(d, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


def pannello_cli(d, *args):
    t0 = time.time()
    r = subprocess.run([sys.executable, PANNELLO, "--cartella", d] + list(args), capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    return r, time.time() - t0


def una_riga(testo):
    return len(testo.strip().splitlines()) == 1 and "Traceback" not in testo


# 1. Tipi strani nei file dell'utente
A = studio("strani")
ora = pannello.scrivi_ora(pannello.adesso_utc())
scrivi(A, "periodo/todo.json", json.dumps({"versione": "0.5.0", "periodo": "p", "todo": [
    {"id": "a", "chi": "tu", "stato": "da-fare", "scadenza": 20261201},
    {"id": "b", "chi": "tu", "stato": "da-fare", "scadenza": ["2026-01-01"]},
    {"id": "c", "chi": "tu", "stato": "da-fare", "scadenza": "2020-01-01"}]}))
scrivi(A, "grafi/x.yaml", "grafo:\n  a: 1\npassi: 5\n")
scrivi(A, "grafi/corse/strana-20261114-100000.json", json.dumps(
    {"id": "strana-20261114-100000", "grafo": "giro", "stato": "in-corso", "inizio": ora, "ultimo_segno": ora,
     "persa_dopo_minuti": "abc", "passi": []}))
scrivi(A, "grafi/corse/lista-20261114-100001.json", json.dumps(
    {"id": 7, "grafo": ["x"], "stato": "in-corso", "inizio": ora, "ultimo_segno": ora, "passi": []}))
errori = {}
risposte = {}
for nome, f in sorted(pannello.VISTE.items()):
    try:
        risposte[nome] = f(A)
    except Exception as e:
        errori[nome] = "%s: %s" % (e.__class__.__name__, e)
controllo("nessuna vista si rompe con scadenza numerica, `passi: 5`, persa_dopo_minuti «abc», grafo a lista", not errori, errori)
stato = risposte.get("stato") or {}
aspettano = {v["id"]: v["in_ritardo"] for v in (stato.get("periodo") or {}).get("aspettano_te", [])}
controllo("la scadenza strana è ignorata (non in ritardo), quella vera conta", aspettano == {"a": False, "b": False, "c": True}, aspettano)
controllo("il grafo con `passi: 5` finisce in problemi col suo nome",
          any("grafi/x.yaml" in p for p in stato.get("problemi", [])), stato.get("problemi"))
controllo("la corsa con persa_dopo_minuti «abc» e quella con grafo a lista si leggono lo stesso",
          {c["id"] for c in stato.get("corse", [])} >= {"strana-20261114-100000", "lista-20261114-100001"},
          [c["id"] for c in stato.get("corse", [])])

# 2. todo.json e idee.json che non si leggono
B = studio("rotti")
controllo("todo.json e idee.json sani: nessun problema", pannello.vista_stato(B)["problemi"] == [], pannello.vista_stato(B)["problemi"])
scrivi(B, "periodo/todo.json", '{"todo": [')
scrivi(B, "periodo/idee.json", "")
v = pannello.vista_stato(B)
controllo("todo.json rotto e idee.json vuoto: due problemi, ognuno col suo nome",
          len(v["problemi"]) == 2 and any(p.startswith("periodo/todo.json:") for p in v["problemi"])
          and any(p.startswith("periodo/idee.json:") for p in v["problemi"]), v["problemi"])
controllo("la vista periodo li porta anche lei", len(pannello.vista_periodo(B).get("problemi", [])) == 2)
os.unlink(os.path.join(B, "periodo", "todo.json"))
controllo("todo.json assente non è un problema", not any("todo.json" in p for p in pannello.vista_stato(B)["problemi"]))

# 2b. Il riepilogo per il supporto dice quali file non si leggono, dopo «Ultimo problema»
def riepilogo(d):
    return pannello.vista_supporto(d, pannello.vista_stato(d))["righe"]


C0 = studio("supporto")
righe = riepilogo(C0)
i = [k for k, r in enumerate(righe) if r.startswith("Ultimo problema")]
controllo("supporto: «File che non si leggono: nessuno» subito dopo «Ultimo problema»",
          len(i) == 1 and righe[i[0] + 1] == "File che non si leggono: nessuno", righe)
scrivi(C0, "periodo/todo.json", "{")
scrivi(C0, "grafi/x.yaml", "grafo:\n  a: 1\npassi: 5\n")
righe = riepilogo(C0)
i = [k for k, r in enumerate(righe) if r.startswith("Ultimo problema")]
voce = righe[i[0] + 1] if i else ""
controllo("supporto: con file rotti li elenca separati da virgola",
          voce.startswith("File che non si leggono: periodo/todo.json: non si legge") and ", grafi/x.yaml" in voce and voce.count("\n") == 0, voce)

# 2c. L'orfano si cerca solo sulle prime due porte, con un timeout corto (su Windows una porta chiusa lo consuma tutto)
visti = []


class ConnessioneFinta(object):
    def __init__(self, host, porta, timeout=None):
        visti.append((porta, timeout))

    def request(self, *a, **k):
        raise OSError("chiusa")


with mock.patch.object(pannello.http.client, "HTTPConnection", ConnessioneFinta):
    trovato = pannello.trova_orfano(BASE, 47100)
controllo("trova_orfano: due porte sole (la preferita e la successiva), timeout di 0,4 secondi",
          trovato is None and visti == [(47100, 0.4), (47101, 0.4)], visti)

# 3. Una porta sotto 1024 vietata non cita Codex
def crea_vietato(porta):
    import errno
    raise OSError(errno.EACCES, "Permission denied")


with mock.patch.object(pannello, "crea_server", crea_vietato), mock.patch.object(pannello, "su_windows", lambda: False):
    try:
        pannello.apri_socket_libera(BASE, 80)
        messaggio = None
    except SystemExit as e:
        messaggio = str(e)
controllo("porta 80 vietata: dice di usare una porta sopra 1024, senza Codex",
          bool(messaggio) and "1024" in messaggio and "Codex" not in messaggio and "sandbox" not in messaggio, messaggio)

if sys.platform != "linux":
    print("SALTA     le prove che accendono il pannello vero: servono Linux")
else:
    # 4. --porta fuori intervallo
    for porta in ("70000", "-1", "99999", "80", "0", "1023"):
        r, _ = pannello_cli(B, "--porta", porta)
        controllo("--porta %s: una riga in italiano, esce 2, niente traceback" % porta,
                  r.returncode == 2 and una_riga(r.stderr) and "1024" in r.stderr and r.stdout == "", (r.returncode, r.stdout, r.stderr))

    # 5. interfaccia che è un file
    C = studio("interfaccia-file")
    subprocess.run(["rm", "-rf", os.path.join(C, "interfaccia")])
    scrivi(C, "interfaccia", "x")
    r, t = pannello_cli(C)
    controllo("interfaccia che è un file: una riga con la causa, esce non-zero, subito",
              r.returncode != 0 and una_riga(r.stderr) and "interfaccia" in r.stderr and t < 3, (r.returncode, r.stderr, round(t, 1)))

    # 6. interfaccia non scrivibile
    E = studio("interfaccia-sola-lettura")
    subprocess.run(["rm", "-rf", os.path.join(E, "interfaccia")])
    os.makedirs(os.path.join(E, "interfaccia"))
    os.chmod(os.path.join(E, "interfaccia"), 0o555)
    try:
        if os.access(os.path.join(E, "interfaccia"), os.W_OK):
            print("SALTA     interfaccia non scrivibile: questo utente scrive comunque (root?)")
        else:
            r, t = pannello_cli(E)
            controllo("interfaccia non scrivibile: una riga che dice la causa, subito, senza i 8 secondi",
                      r.returncode != 0 and una_riga(r.stderr) and "interfaccia" in r.stderr and "scrittura" in r.stderr and t < 3,
                      (r.returncode, r.stderr, round(t, 1)))
    finally:
        os.chmod(os.path.join(E, "interfaccia"), 0o755)

    # 7. il pannello vero davanti ai dati strani: 200 su ogni vista
    try:
        r, _ = pannello_cli(A)
        porta = int(r.stdout.split("127.0.0.1:")[1].split("/")[0])
        codici = {}
        for nome in ("stato", "periodo", "supporto", "recenti", "file-chiave", "corse", "grafi"):
            try:
                codici[nome] = urllib.request.urlopen("http://127.0.0.1:%d/api/%s" % (porta, nome), timeout=10).status
            except Exception as e:
                codici[nome] = str(e)
        controllo("il server risponde 200 su tutte le viste, anche con i dati strani", set(codici.values()) == {200}, codici)
    finally:
        pannello_cli(A, "--spegni")

    # 8. pannello.json sparito mentre il pannello gira
    D = studio("orfano")
    info_json = os.path.join(D, "interfaccia", "pannello.json")
    try:
        r1, _ = pannello_cli(D)
        info1 = json.load(open(info_json, encoding="utf-8"))
        ciao = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/api/ciao" % info1["porta"], timeout=5).read().decode("utf-8"))
        controllo("/api/ciao dice anche il pid del server", ciao.get("pid") == info1["pid"], (ciao, info1["pid"]))
        os.unlink(info_json)
        r2, _ = pannello_cli(D)
        info2 = json.load(open(info_json, encoding="utf-8")) if os.path.exists(info_json) else {}
        controllo("pannello.json sparito: la seconda accensione riprende lo stesso pannello e dice «già acceso»",
                  r2.returncode == 0 and "già acceso" in r2.stdout and ":%d/" % info1["porta"] in r2.stdout
                  and info2.get("porta") == info1["porta"] and info2.get("pid") == info1["pid"], (r2.stdout, r2.stderr, info2))
        controllo("il file riscritto non porta un gettone inventato (lo sa solo il server)", "gettone" not in info2, info2)
        r3, _ = pannello_cli(D, "--spegni")
        time.sleep(0.5)
        try:
            os.kill(info1["pid"], 0)
            vivo = True
        except OSError:
            vivo = False
        controllo("--spegni spegne il pannello ripreso: nessun processo orfano, nessun pannello.json",
                  "spento" in r3.stdout and not vivo and not os.path.exists(info_json), (r3.stdout, vivo))
    finally:
        pannello_cli(D, "--spegni")
        try:
            os.kill(json.load(open(info_json, encoding="utf-8"))["pid"], 15)
        except Exception:
            pass

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
