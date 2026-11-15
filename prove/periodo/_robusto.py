# redacy 0.5.0 · prove/periodo/_robusto.py (lo lancia prova-schemi.sh)
"""controlla-periodo.py davanti a file che non sono UTF-8, vuoti, troncati o con i tipi sbagliati, a mano e da hook.

Uso: python3 _robusto.py RADICE CARTELLA_DI_PROVA
 - un todo.json o idee.json scritto da PowerShell 5.1 (UTF-16 con BOM) o in cp1252: niente traceback; a mano esce 1, da hook
   esce 2 (quello che fa arrivare «correggi» al modello) con «non è scritto in UTF-8: riscrivilo con lo strumento di
   scrittura dei file, non con un comando della shell»;
 - un file UTF-8 con il BOM è valido;
 - vuoto, troncato, radice non oggetto, tipi sbagliati nei campi, annidamento enorme: una riga che dice che cosa non va;
 - un evento dell'hook con i campi di tipo sbagliato: in silenzio, uscita 0.
Una riga per controllo: «ok» o «FALLISCE». In fondo PASSA oppure FALLISCE <perché>. Niente rete.
"""
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
RADICE, BASE = sys.argv[1], sys.argv[2]
C = os.path.join(RADICE, "skills", "pianifica-periodo", "scripts", "controlla-periodo.py")
FALLITE = []
shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(os.path.join(BASE, "periodo"))

TODO = {"versione": "0.3.0", "periodo": "2026-11", "todo": [
    {"id": "t1", "cosa": "Riordinare le fatture", "chi": "agente", "stato": "in corso", "scadenza": "2026-11-14",
     "dove": "workspace/contabilita", "da": "piano", "aggiornato": "2026-11-07"}]}
IDEE = {"versione": "0.3.0", "periodo": "2026-11", "idee": [
    {"id": "i1", "idea": "Promemoria ai clienti", "da_dove": "conversazione", "arrivata": "2026-11-07"}]}


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)[:500]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def scrivi(nome, dati):
    p = os.path.join(BASE, "periodo", nome)
    with open(p, "wb") as f:
        f.write(dati if isinstance(dati, bytes) else dati.encode("utf-8"))
    return p


def a_mano(percorso):
    r = subprocess.run([sys.executable, C, percorso], capture_output=True, encoding="utf-8", errors="replace", timeout=60)
    return r.returncode, r.stdout, r.stderr


def da_hook(percorso, evento=None):
    ev = evento if evento is not None else {"cwd": BASE, "tool_name": "Write", "tool_input": {"file_path": percorso}}
    r = subprocess.run([sys.executable, C], input=json.dumps(ev), capture_output=True, encoding="utf-8", errors="replace",
                       timeout=60)
    return r.returncode, r.stdout, r.stderr


def dett(rc, out, err):
    """Il dettaglio di un controllo fallito su una riga sola: uscita e inizio di stdout e stderr."""
    def uno(t):
        return t[:200].replace("\r", "").replace("\n", " | ")
    return "uscita %s · stdout: %s · stderr: %s" % (rc, uno(out), uno(err))


def pulito(*testi):
    return all("Traceback" not in t for t in testi)


MSG = "non è scritto in UTF-8: riscrivilo con lo strumento di scrittura dei file, non con un comando della shell"
buono = json.dumps(TODO, ensure_ascii=False)

# ---- file non UTF-8
CASI = [
    ("UTF-16 con BOM (PowerShell 5.1)", buono.encode("utf-16")),
    ("UTF-16 senza BOM", b"{\x00}\x00"),
    ("cp1252", buono.replace("Riordinare", "Riordinàre").encode("cp1252")),
    ("byte spaiati", b"\xff\xfe{\x00}\x00"),
]
for nome, dati in CASI:
    for file in ("todo.json", "idee.json"):
        p = scrivi(file, dati)
        rc, out, err = a_mano(p)
        controllo("%s in %s, a mano: uscita 1, «%s», niente traceback" % (nome, file, "non è scritto in UTF-8"),
                  rc == 1 and MSG in out and pulito(out, err), (rc, out, err))
        rc, out, err = da_hook(p)
        controllo("%s in %s, da hook: uscita 2 con il messaggio su stderr e il blocco su stdout" % (nome, file),
                  rc == 2 and MSG in err and '"decision": "block"' in out and pulito(out, err), (rc, out, err))

# ---- BOM UTF-8 e altri file validi
p = scrivi("todo.json", b"\xef\xbb\xbf" + buono.encode("utf-8"))
rc, out, err = a_mano(p)
controllo("todo.json UTF-8 con il BOM: valido", rc == 0 and "valido" in out and pulito(out, err), (rc, out, err))
rc, out, err = da_hook(p)
controllo("todo.json UTF-8 con il BOM, da hook: in silenzio, uscita 0", rc == 0 and out == "" and err == "", (rc, out, err))
p = scrivi("idee.json", json.dumps(IDEE, ensure_ascii=False))
rc, out, err = a_mano(p)
controllo("idee.json buono: valido", rc == 0 and "valido" in out, (rc, out, err))

# ---- vuoto, troncato, radice sbagliata, tipi sbagliati
STRANI = [
    ("vuoto", b"", "è vuoto"),
    ("solo spazi", b"  \n", "è vuoto"),
    ("troncato", buono[:60].encode("utf-8"), "non è un JSON valido"),
    ("radice elenco", b"[]", "dovrebbe essere oggetto"),
    ("radice null", b"null", "dovrebbe essere oggetto"),
    ("radice numero", b"5", "dovrebbe essere oggetto"),
    ("todo non elenco", b'{"versione":"0.3.0","periodo":"2026-11","todo":{"a":1}}', "dovrebbe essere elenco"),
    ("voci che non sono oggetti", b'{"versione":"0.3.0","periodo":"2026-11","todo":[1,"a",null,[]]}', "dovrebbe essere oggetto"),
    ("campi di tipo sbagliato", b'{"versione":3,"periodo":[],"todo":[{"id":[1],"cosa":5,"chi":{},"stato":null}]}', "dovrebbe essere testo"),
    # il limite dipende dal Python: il 3.12 si ferma a un numero fisso di livelli («troppi livelli»), i più nuovi seguono la
    # pila vera, i 100000 livelli entrano e il file non chiuso dà un normale errore di JSON: va bene l'uno o l'altro
    ("annidamento enorme", b"[" * 100000, ("troppi livelli", "non è un JSON valido")),
    ("NUL dentro", b'{"versione":"0.3.0",\x00}', "non è scritto in UTF-8"),
]
for nome, dati, atteso in STRANI:
    ammessi = (atteso,) if isinstance(atteso, str) else atteso
    p = scrivi("todo.json", dati)
    rc, out, err = a_mano(p)
    controllo("todo.json %s, a mano: uscita 1, «%s», niente traceback" % (nome, "» oppure «".join(ammessi)),
              rc == 1 and any(a in out for a in ammessi) and pulito(out, err), dett(rc, out, err))
    rc, out, err = da_hook(p)
    controllo("todo.json %s, da hook: uscita 2, niente traceback" % nome,
              rc == 2 and pulito(out, err) and "Correggi il file" in err, dett(rc, out, err))
p = scrivi("idee.json", b'{"versione":"0.3.0","periodo":"2026-11","idee":[{"id":[1],"esito":{"stato":"portata nel periodo","todo":[1]}}]}')
rc, out, err = a_mano(p)
controllo("idee.json con esito.todo che è un elenco: uscita 1, niente traceback", rc == 1 and pulito(out, err), (rc, out, err))

# idea «portata nel periodo» con un todo.json che non si legge: non è affare di questo file
idea_ok = {"versione": "0.3.0", "periodo": "2026-11", "idee": [
    {"id": "i1", "idea": "x", "da_dove": "utente", "arrivata": "2026-11-07",
     "esito": {"stato": "portata nel periodo", "data": "2026-11-08", "perche": "serve", "todo": "t1"}}]}
for nome, dati in (("non UTF-8", b"\xff\xfe"), ("con id che non è un testo", b'{"todo":[{"id":[1]}]}'), ("elenco", b"[]")):
    scrivi("todo.json", dati)
    p = scrivi("idee.json", json.dumps(idea_ok))
    rc, out, err = a_mano(p)
    controllo("idee.json che rimanda a un todo.json %s: niente traceback" % nome, pulito(out, err), (rc, out, err))

# ---- l'hook davanti a eventi strani
scrivi("todo.json", buono)
for nome, ev in (("cwd numerico", {"cwd": 5, "tool_input": {"file_path": "periodo/todo.json"}}),
                 ("cwd elenco", {"cwd": ["a"], "tool_input": {"command": "echo > periodo/todo.json"}}),
                 ("file_path numerico", {"tool_input": {"file_path": 5}}),
                 ("tool_input vuoto", {"tool_input": None}),
                 ("evento che è un elenco", [])):
    rc, out, err = da_hook(None, ev)
    controllo("hook con un evento strano (%s): in silenzio, uscita 0" % nome, rc == 0 and pulito(out, err), (rc, out, err))
r = subprocess.run([sys.executable, C], input=b"\xff\xfe\x00", capture_output=True, timeout=60)
controllo("hook con un evento non UTF-8 su stdin: in silenzio, uscita 0", r.returncode == 0 and b"Traceback" not in r.stderr, r)

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE[:5]) + (" … (%d in tutto)" % len(FALLITE) if len(FALLITE) > 5 else ""))
    sys.exit(1)
print("PASSA")
