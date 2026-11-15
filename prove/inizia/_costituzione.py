# redacy 0.5.0 · prove/inizia/_costituzione.py (lo lancia prova-cartella.sh) · SOLO C3
# Prova che --aggiorna porti anche il nuovo AGENTS.md (la costituzione, uguale in ogni studio) a chi ha già la
# cartella, e che --controlla lo dica. Una riga per controllo: «ok» o «NO». In fondo PASSA o FALLISCE.
import hashlib
import os
import subprocess
import sys

RADICE, BASE = sys.argv[1], sys.argv[2]
SCRIPT = os.path.join(RADICE, "skills", "inizia", "scripts", "crea-cartella.py")
MODELLO = os.path.join(RADICE, "skills", "inizia", "modello", "AGENTS.md")
FALLITE = []
os.makedirs(BASE, exist_ok=True)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok  " if ok else "NO  ") + descrizione + ((" · " + str(dettaglio)[:400]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def lancia(cartella, *opzioni):
    r = subprocess.run([sys.executable, "-I", SCRIPT, cartella, "--plugin", RADICE, *opzioni],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def leggi(cartella, rel):
    return open(os.path.join(cartella, rel), "rb").read()


def scrivi(cartella, rel, dati):
    p = os.path.join(cartella, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(dati if isinstance(dati, bytes) else dati.encode("utf-8"))


def albero(cartella):
    out = {}
    for base, _, nomi in os.walk(cartella):
        for n in nomi:
            p = os.path.join(base, n)
            if not os.path.islink(p):
                out[os.path.relpath(p, cartella)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


modello = open(MODELLO, "rb").read()
testa = modello.split(b"\n", 1)[0]
assert testa.startswith(b"<!-- redacy 0.5.0 "), testa
vecchio = modello.replace(b"<!-- redacy 0.5.0 ", b"<!-- redacy 0.3.1 ", 1) + b"\nUna regola vecchia.\n"

# ---------------------------------------------------------------- AGENTS.md di una versione vecchia
A = os.path.join(BASE, "vecchio-%d" % os.getpid())
lancia(A)
scrivi(A, "AGENTS.md", vecchio)
scrivi(A, "memoria/studio.md", "# Il mio studio\nRegola mia: l'euro.\n")
scrivi(A, "memoria/LOG.md", "- 2026-01-01 · mia riga\n")
scrivi(A, "periodo/obiettivo.md", "# Obiettivo mio\n")
scrivi(A, "periodo/todo.json", '{"versione": "0.3.0", "periodo": "x", "todo": []}\n')
scrivi(A, ".agents/policy/cosa-faccio-da-solo.md", "## Da solo\n- una mia riga\n")
scrivi(A, ".agents/regole/memoria.md", "# regola modificata dall'utente\n")
scrivi(A, "CLAUDE.md", "@AGENTS.md\nIl mio.\n")
scrivi(A, "workspace/mio/AGENTS.md", "<!-- redacy 0.3.1 -->\n# un workspace\n")
scrivi(A, "interfaccia/su-misura.json", '{"titolo": "mio"}\n')
utente = {k: v for k, v in albero(A).items() if k != "AGENTS.md"}

rc, u = lancia(A, "--controlla")
av = [r for r in u.splitlines() if r.startswith("avviso: AGENTS.md")]
controllo("--controlla: AGENTS.md di redacy 0.3.1 dà un «avviso:» con le due versioni e --aggiorna (non cambia l'uscita)",
          rc == 0 and len(av) == 1 and "redacy 0.3.1" in av[0] and "porta la 0.5.0" in av[0] and "--aggiorna" in av[0]
          and "copia di prima" in av[0], u)
rc, u = lancia(A, "--aggiorna")
agg = [r for r in u.splitlines() if r.startswith("aggiornato: AGENTS.md")]
controllo("--aggiorna: «aggiornato: AGENTS.md (copia di prima: AGENTS.md.prima-di-redacy)»",
          rc == 0 and agg == ["aggiornato: AGENTS.md (copia di prima: AGENTS.md.prima-di-redacy)"], u)
controllo("dopo, AGENTS.md è uguale al modello, byte per byte", leggi(A, "AGENTS.md") == modello)
controllo("la copia contiene quello di prima", leggi(A, "AGENTS.md.prima-di-redacy") == vecchio)
ora = albero(A)
controllo("memoria, periodo, policy, regole, CLAUDE.md, workspace, su-misura: identici prima e dopo (hash)",
          all(ora.get(k) == v for k, v in utente.items()) and sorted(set(ora) - set(utente)) == ["AGENTS.md", "AGENTS.md.prima-di-redacy"],
          sorted(set(ora) ^ set(utente)))
rc, u = lancia(A, "--controlla")
controllo("poi --controlla non dice più niente su AGENTS.md", rc == 0 and "AGENTS.md" not in u, u)
rc, u = lancia(A, "--aggiorna")
controllo("la seconda --aggiorna non cambia niente e non stampa «aggiornato:»", rc == 0 and albero(A) == ora and "aggiornato: " not in u, u)

# una copia di sicurezza che c'è già non si sovrascrive
scrivi(A, "AGENTS.md", vecchio)
rc, u = lancia(A, "--aggiorna")
controllo("se AGENTS.md.prima-di-redacy c'è già, la nuova copia ha un altro nome e la vecchia resta",
          "(copia di prima: AGENTS.md.prima-di-redacy-2)" in u and leggi(A, "AGENTS.md.prima-di-redacy") == vecchio
          and leggi(A, "AGENTS.md.prima-di-redacy-2") == vecchio, u)

# ---------------------------------------------------------------- a capo di Windows e BOM non sono «cambiato a mano»
W = os.path.join(BASE, "crlf-%d" % os.getpid())
lancia(W)
scrivi(W, "AGENTS.md", b"\xef\xbb\xbf" + modello.replace(b"\n", b"\r\n"))
prima = albero(W)
rc, u = lancia(W, "--aggiorna")
controllo("AGENTS.md uguale al modello ma con \\r\\n e BOM: né avviso né aggiornamento", rc == 0 and "AGENTS.md" not in u and albero(W) == prima, u)

# ---------------------------------------------------------------- stessa versione, ma cambiato a mano
M = os.path.join(BASE, "a-mano-%d" % os.getpid())
lancia(M)
a_mano = modello + b"\nUna regola dell'utente.\n"
scrivi(M, "AGENTS.md", a_mano)
prima = albero(M)
rc, u = lancia(M, "--aggiorna")
controllo("--aggiorna: stessa versione ma contenuto diverso non lo tocca e dice «AGENTS.md è stato cambiato a mano: non lo tocco»",
          rc == 0 and "avviso: AGENTS.md è stato cambiato a mano: non lo tocco" in u and albero(M) == prima
          and leggi(M, "AGENTS.md") == a_mano and "aggiornato: AGENTS.md" not in u, u)
rc, u = lancia(M, "--controlla")
av = [r for r in u.splitlines() if r.startswith("avviso: AGENTS.md")]
controllo("--controlla: stessa versione, contenuto diverso → avviso «cambiato a mano o rovinato: … cancellalo e rilancia lo script»",
          rc == 0 and len(av) == 1 and "cambiato a mano o rovinato" in av[0] and "cancellalo e rilancia lo script" in av[0], u)
# un AGENTS.md troncato (rovinato) è la stessa cosa
scrivi(M, "AGENTS.md", modello[:200])
rc, u = lancia(M, "--aggiorna")
controllo("un AGENTS.md troncato (testa buona, resto perso) non si tocca e lo dice", "non lo tocco" in u and leggi(M, "AGENTS.md") == modello[:200], u)

# ---------------------------------------------------------------- AGENTS.md di un altro agente
X = os.path.join(BASE, "altro-agente-%d" % os.getpid())
lancia(X)
altro = b"# Un altro agente\nNon e' di redacy.\n"
scrivi(X, "AGENTS.md", altro)
prima = albero(X)
rc, u = lancia(X, "--aggiorna")
controllo("--aggiorna: un AGENTS.md senza la nostra testa non si tocca e non dice niente su AGENTS.md",
          rc == 0 and albero(X) == prima and "AGENTS.md" not in u, u)
rc, u = lancia(X, "--controlla")
controllo("--controlla: niente su un AGENTS.md che non è nostro", rc == 0 and "AGENTS.md" not in u, u)
scrivi(X, "AGENTS.md", b"<!-- un commento -->\n# Altro\n")
prima = albero(X)
rc, u = lancia(X, "--aggiorna")
controllo("una prima riga che comincia con <!-- ma non con «redacy» non è nostra: non si tocca", albero(X) == prima and "AGENTS.md" not in u, u)

# ---------------------------------------------------------------- niente AGENTS.md: --aggiorna non lo crea
Z = os.path.join(BASE, "senza-%d" % os.getpid())
lancia(Z)
os.remove(os.path.join(Z, "AGENTS.md"))
rc, u = lancia(Z, "--aggiorna")
controllo("--aggiorna non crea un AGENTS.md che manca (lo fa lo script senza opzioni)", rc == 0 and not os.path.exists(os.path.join(Z, "AGENTS.md")), u)

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
