# redacy 0.4.2 · prove/inizia/_workspace.py (lo lancia prova-cartella.sh)
# Prova che crea-workspace.py scriva i percorsi dei dati come li vede il workspace (dalla sua cartella),
# e che controlla-workspace.py passi ancora. Una riga per controllo: «ok» o «NO». In fondo PASSA o FALLISCE.
import os
import re
import subprocess
import sys

RADICE, BASE = sys.argv[1], sys.argv[2]
FALLITE = []
os.makedirs(BASE, exist_ok=True)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok  " if ok else "NO  ") + descrizione + ((" · " + str(dettaglio)[:300]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def lancia(*argv):
    r = subprocess.run([sys.executable, "-I", *argv], capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


D = os.path.join(BASE, "studio-%d" % os.getpid())
rc, _ = lancia(os.path.join(RADICE, "skills/inizia/scripts/crea-cartella.py"), D, "--plugin", RADICE)
CREA = os.path.join(RADICE, "skills/crea-workspace/scripts/crea-workspace.py")
CONTROLLA = os.path.join(RADICE, "skills/crea-workspace/scripts/controlla-workspace.py")
os.makedirs(os.path.join(D, "fonti", "listini"))
rc, u = lancia(CREA, "preventivi-officina", "--descrizione", "Prepara i preventivi", "--cartella", D,
               "--dati", "fonti/listini/", "--dati", "/srv/dati/clienti", "--dati", "C:\\Studio\\Pratiche", "--dati", "fonti\\ordini")
controllo("crea-workspace.py esce 0", rc == 0, u)
avvisi = [r for r in u.splitlines() if r.startswith("avviso:")]
agenti = open(os.path.join(D, "workspace/preventivi-officina/AGENTS.md"), encoding="utf-8").read()
scheda = open(os.path.join(D, "workspace/preventivi-officina/memoria/preventivi-officina.md"), encoding="utf-8").read()
controllo("un percorso dello studio si scrive dal workspace: `../../fonti/listini/`", "`../../fonti/listini/`" in agenti, agenti)
controllo("lo stesso nella scheda di memoria", "`../../fonti/listini/`" in scheda, scheda)
controllo("un percorso intero resta com'è (Unix e Windows)", "`/srv/dati/clienti`" in agenti and "`C:\\Studio\\Pratiche`" in agenti, agenti)
controllo("la barra rovesciata di un percorso dello studio diventa «/»", "`../../fonti/ordini`" in agenti, agenti)
controllo("il percorso scritto in AGENTS.md c'è davvero, partendo dalla cartella del workspace",
          os.path.isdir(os.path.normpath(os.path.join(D, "workspace/preventivi-officina", "../../fonti/listini/"))))
controllo("non scrive più il percorso nudo `fonti/listini/`", not re.search(r"`fonti/listini/`", agenti))
controllo("«il percorso non esiste ancora» guarda ancora dalla cartella dello studio (fonti/listini c'è, non dà avviso)",
          not any("fonti/listini" in r for r in avvisi), avvisi)
rc, u = lancia(CONTROLLA, os.path.join(D, "workspace/preventivi-officina"))
controllo("controlla-workspace.py esce 0 (gli avvisi sui «da completare» non fermano)", rc == 0 and "esito: ok" in u, u)
rc, u = lancia(CREA, "senza-dati", "--descrizione", "Niente dati", "--cartella", D)
controllo("senza --dati: «nessun dato indicato» e il controllo passa",
          rc == 0 and lancia(CONTROLLA, os.path.join(D, "workspace/senza-dati"))[0] == 0)

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
