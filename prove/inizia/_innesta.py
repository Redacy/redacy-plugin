# redacy 0.4.2 · prove/inizia/_innesta.py (lo lancia prova-cartella.sh)
# Prova crea-cartella.py con ciò che c'era già nella cartella (--innesta) e con le copie vecchie (--aggiorna).
# Una riga per controllo: «ok» o «NO». In fondo PASSA o FALLISCE.
import hashlib
import json
import os
import subprocess
import sys

RADICE, BASE = sys.argv[1], sys.argv[2]
SCRIPT = os.path.join(RADICE, "skills", "inizia", "scripts", "crea-cartella.py")
FALLITE = []
os.makedirs(BASE, exist_ok=True)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok  " if ok else "NO  ") + descrizione + ((" · " + str(dettaglio)[:300]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def lancia(cartella, *opzioni):
    r = subprocess.run([sys.executable, "-I", SCRIPT, cartella, "--plugin", RADICE, *opzioni],
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def albero(cartella):
    """Le impronte di tutti i file della cartella."""
    out = {}
    for base, _, nomi in os.walk(cartella):
        for n in nomi:
            p = os.path.join(base, n)
            if os.path.islink(p):
                continue
            out[os.path.relpath(p, cartella)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
    return out


def scrivi(cartella, rel, dati):
    p = os.path.join(cartella, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "wb").write(dati if isinstance(dati, bytes) else dati.encode("utf-8"))


def leggi(cartella, rel):
    return open(os.path.join(cartella, rel), "rb").read()


# ---------------------------------------------------------------- --innesta
D = os.path.join(BASE, "innesta-%d" % os.getpid())
CLAUDE = "# Il mio CLAUDE\nRegola mia: usare l'euro.\n"
SETTINGS = {"permissions": {"allow": ["Bash(ls)"]},
            "hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo mio"}]}]}}
scrivi(D, "CLAUDE.md", CLAUDE)
scrivi(D, ".claude/settings.json", json.dumps(SETTINGS, indent=1))
scrivi(D, ".codex/hooks.json", "{}\n")

rc, u = lancia(D)
righe = [r for r in u.splitlines() if r.startswith("avviso:")]
controllo("la creazione esce 0 e dà un avviso per CLAUDE.md", rc == 0 and any("CLAUDE.md" in r and "AGENTS.md" in r for r in righe), u)
controllo("dà un avviso per .claude/settings.json e uno per .codex/hooks.json",
          any(".claude/settings.json" in r for r in righe) and any(".codex/hooks.json" in r for r in righe), righe)
controllo("gli avvisi sono contati nell'esito", "3 avvisi" in u.splitlines()[-1], u.splitlines()[-1])
controllo("non ha toccato CLAUDE.md né i due file degli hook", leggi(D, "CLAUDE.md") == CLAUDE.encode()
          and json.loads(leggi(D, ".claude/settings.json")) == SETTINGS and leggi(D, ".codex/hooks.json") == b"{}\n")

rc, u = lancia(D, "--controlla")
nonva = [r for r in u.splitlines() if r.startswith("non va:")]
controllo("--controlla esce 1 con un «non va:» per ognuno dei tre file",
          rc == 1 and any("CLAUDE.md" in r for r in nonva) and any(".claude/settings.json" in r for r in nonva)
          and any(".codex/hooks.json" in r for r in nonva), u)

prima = albero(D)
rc, u = lancia(D, "--innesta")
controllo("--innesta esce 0 e dice «3 innestati»", rc == 0 and "esito: 3 innestati" in u, u)
c = leggi(D, "CLAUDE.md")
controllo("CLAUDE.md: tutto il testo di prima c'è, poi @AGENTS.md", c.startswith(CLAUDE.encode()) and c.rstrip().endswith(b"@AGENTS.md"), c)
s = json.loads(leggi(D, ".claude/settings.json"))
pre = s["hooks"]["PreToolUse"]
controllo("settings.json: permessi e hook dell'utente restano, nello stesso ordine, prima di quelli di redacy",
          s["permissions"] == SETTINGS["permissions"] and pre[0] == SETTINGS["hooks"]["PreToolUse"][0]
          and "ferma.py" in pre[1]["hooks"][0]["command"] and "controlla-periodo.py" in s["hooks"]["PostToolUse"][0]["hooks"][0]["command"], s)
controllo(".codex/hooks.json senza «hooks» riceve le due voci", "ferma.py" in json.dumps(json.loads(leggi(D, ".codex/hooks.json"))), leggi(D, ".codex/hooks.json"))
controllo("le copie di prima sono accanto ai file, uguali all'originale",
          leggi(D, "CLAUDE.md.prima-di-redacy") == CLAUDE.encode()
          and json.loads(leggi(D, ".claude/settings.json.prima-di-redacy")) == SETTINGS
          and leggi(D, ".codex/hooks.json.prima-di-redacy") == b"{}\n")
rc, u = lancia(D, "--controlla")
controllo("dopo --innesta --controlla non dice più niente sui tre file", rc == 0 and "non va" not in u, u)
dopo = albero(D)
rc, u = lancia(D, "--innesta")
controllo("seconda --innesta: 0 innestati e niente cambia (nemmeno una copia in più)",
          rc == 0 and "esito: 0 innestati" in u and albero(D) == dopo, u)
rc, u = lancia(D)
controllo("una nuova creazione non dà più avvisi", rc == 0 and "avviso" not in u, u)

# una copia di sicurezza che c'è già non si sovrascrive
E = os.path.join(BASE, "innesta-copia-%d" % os.getpid())
scrivi(E, "CLAUDE.md", "mio\n")
scrivi(E, "CLAUDE.md.prima-di-redacy", "una copia vecchia\n")
lancia(E)
rc, u = lancia(E, "--innesta")
controllo("una copia .prima-di-redacy che c'è già resta com'è, la nuova ha un altro nome",
          rc == 0 and leggi(E, "CLAUDE.md.prima-di-redacy") == b"una copia vecchia\n"
          and leggi(E, "CLAUDE.md.prima-di-redacy-2") == b"mio\n", u)

# a capo di Windows e file senza l'ultimo a capo
F = os.path.join(BASE, "innesta-crlf-%d" % os.getpid())
scrivi(F, "CLAUDE.md", b"riga uno\r\nriga due")
lancia(F)
lancia(F, "--innesta")
controllo("CLAUDE.md con \\r\\n e senza a capo finale: resta com'è, @AGENTS.md va a capo con \\r\\n",
          leggi(F, "CLAUDE.md") == b"riga uno\r\nriga due\r\n\r\n@AGENTS.md\r\n", leggi(F, "CLAUDE.md"))

# CLAUDE.md che importa già AGENTS.md (con altro testo): niente avviso
G = os.path.join(BASE, "innesta-gia-%d" % os.getpid())
scrivi(G, "CLAUDE.md", "# mio\n\n@AGENTS.md\nnote\n")
rc, u = lancia(G)
controllo("un CLAUDE.md che importa già AGENTS.md non dà avvisi", rc == 0 and "avviso" not in u, u)

# un JSON rotto non si tocca
H = os.path.join(BASE, "innesta-rotto-%d" % os.getpid())
scrivi(H, ".claude/settings.json", "{ non json")
lancia(H)
rc, u = lancia(H, "--innesta")
controllo("un settings.json che non è JSON non viene toccato, e --innesta dice che non lo può sistemare (esce 1, non «0 innestati» muto)",
          rc == 1 and leggi(H, ".claude/settings.json") == b"{ non json" and "non sistemato: .claude/settings.json" in u
          and "da sistemare a mano" in u, u)

# --innesta e --aggiorna non creano la cartella
rc, u = lancia(os.path.join(BASE, "non-c-e"), "--innesta")
controllo("--innesta su una cartella che non c'è esce 2 e non crea niente", rc == 2 and not os.path.exists(os.path.join(BASE, "non-c-e")), u)

# ---------------------------------------------------------------- --aggiorna
A = os.path.join(BASE, "aggiorna-%d" % os.getpid())
lancia(A)
scrivi(A, "interfaccia/su-misura.json", '{"titolo": "Il mio studio"}\n')
with open(os.path.join(A, "memoria", "INDICE.md"), "a", encoding="utf-8") as f:
    f.write("- [[mia]] · una riga dell'utente\n")
scrivi(A, ".claude/launch.json", '{"version": "0.0.1", "configurations": []}\n')
p = os.path.join(A, ".agents/script/corsa.py")
testo = open(p, encoding="utf-8").read()
vecchio = testo.replace("redacy 0.4.2 ·", "redacy 0.4.0 ·", 1)
assert vecchio != testo
open(p, "w", encoding="utf-8").write(vecchio)
with open(os.path.join(A, ".agents/hooks/ferma.py"), "a", encoding="utf-8") as f:
    f.write("# modificato a mano\n")
os.remove(os.path.join(A, ".agents/script/pagina.html"))
utente = {k: v for k, v in albero(A).items() if k.startswith(("memoria/", "periodo/", "interfaccia/")) or k in ("AGENTS.md", "CLAUDE.md", ".claude/launch.json")}

rc, u = lancia(A, "--controlla")
controllo("--controlla con una copia vecchia: un «avviso:» che dice --aggiorna, non un «non va:»",
          any(r.startswith("avviso:") and "0.4.0" in r and "--aggiorna" in r for r in u.splitlines())
          and not any(r.startswith("non va:") for r in u.splitlines()), u)
rc, u = lancia(A, "--aggiorna")
agg = [r for r in u.splitlines() if r.startswith("aggiornato:")]
controllo("--aggiorna: una riga «aggiornato:» per corsa.py e per ferma.py (modificato a mano), esito: 2 aggiornati",
          rc == 0 and sorted(agg) == ["aggiornato: .agents/hooks/ferma.py", "aggiornato: .agents/script/corsa.py"]
          and "esito: 2 aggiornati, 1 ricreati" in u, u)
controllo("--aggiorna rimette la copia che mancava (pagina.html)", os.path.isfile(os.path.join(A, ".agents/script/pagina.html")) and "creato: .agents/script/pagina.html" in u, u)
controllo("la copia aggiornata porta la versione del plugin", "redacy 0.4.2 ·" in open(p, encoding="utf-8").read()[:300]
          and "modificato a mano" not in open(os.path.join(A, ".agents/hooks/ferma.py"), encoding="utf-8").read())
ora = albero(A)
controllo("non ha toccato AGENTS.md, memoria/, periodo/, su-misura.json né launch.json",
          all(ora.get(k) == v for k, v in utente.items()))
rc, u = lancia(A, "--aggiorna")
controllo("seconda --aggiorna: 0 aggiornati, niente cambia", rc == 0 and "esito: 0 aggiornati, 0 ricreati" in u and albero(A) == ora, u)
rc, u = lancia(A, "--controlla")
controllo("dopo --aggiorna --controlla è pulito, senza avvisi", rc == 0 and "avviso" not in u, u)
rc, u = lancia(os.path.join(BASE, "non-c-e"), "--aggiorna")
controllo("--aggiorna su una cartella che non c'è esce 2 e non crea niente", rc == 2 and not os.path.exists(os.path.join(BASE, "non-c-e")), u)

# ---------------------------------------------------------------- difetti piccoli (prove di rottura #1, #3, #4, #5, #16, #17)
def lancia_in(cwd, *argomenti):
    r = subprocess.run([sys.executable, "-I", SCRIPT, *argomenti, "--plugin", RADICE], cwd=cwd,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


# #5: una cartella vuota non vuol dire «qui»
V5 = os.path.join(BASE, "vuota5-%d" % os.getpid())
os.makedirs(V5)
for arg in ("", "   "):
    rc, u = lancia_in(V5, arg)
    controllo("l'argomento cartella %r esce 2 con una riga «errore:» e non scrive niente" % arg,
              rc == 2 and u.startswith("errore:") and len(u.strip().splitlines()) == 1 and os.listdir(V5) == [], u)

# #16: un BOM in un file JSON non è «JSON non valido»
B = os.path.join(BASE, "bom-%d" % os.getpid())
scrivi(B, ".claude/settings.json", b'\xef\xbb\xbf{"permissions": {"allow": ["x"]}}')
scrivi(B, "periodo/todo.json", b'\xef\xbb\xbf{"versione": "0.3.0", "periodo": "", "todo": []}')
lancia(B)
rc, u = lancia(B, "--controlla")
controllo("--controlla non dice «JSON non valido» per un file con BOM", "JSON non valido" not in u and "BOM" not in u, u)

# #4: un CLAUDE.md che non è UTF-8 si legge sui byte
L = os.path.join(BASE, "latin1-%d" % os.getpid())
scrivi(L, "CLAUDE.md", b"# Perch\xe9 s\xec\n")
rc, u = lancia(L)
controllo("un CLAUDE.md latin-1 senza @AGENTS.md ha il suo avviso", rc == 0 and any(r.startswith("avviso: CLAUDE.md") for r in u.splitlines()), u)
rc, u = lancia(L, "--innesta")
controllo("--innesta lo innesta lasciando intatti i byte di prima",
          rc == 0 and "esito: 1 innestati" in u and leggi(L, "CLAUDE.md") == b"# Perch\xe9 s\xec\n\n@AGENTS.md\n"
          and leggi(L, "CLAUDE.md.prima-di-redacy") == b"# Perch\xe9 s\xec\n", u)
rc, u = lancia(L, "--controlla")
controllo("poi --controlla è pulito", rc == 0 and "non va" not in u, u)
L2 = os.path.join(BASE, "latin1-gia-%d" % os.getpid())
scrivi(L2, "CLAUDE.md", b"# Perch\xe9\n@AGENTS.md\n")
rc, u = lancia(L2)
controllo("un CLAUDE.md latin-1 che importa già AGENTS.md non dà avvisi", rc == 0 and "avviso" not in u, u)

# #3: un file degli hook dell'utente che non si può leggere o non ha la forma giusta non passa in silenzio
for nome, contenuto in (("json-rotto", b'{"permissions": {"allow": ['), ("lista", b"[1, 2]"), ("null", b"null"),
                         ("hooks-lista", b'{"hooks": []}'), ("vuoto", b"")):
    for rel in (".claude/settings.json", ".codex/hooks.json"):
        X = os.path.join(BASE, "hookrotto-%s-%s-%d" % (nome, rel.split("/")[0].strip("."), os.getpid()))
        scrivi(X, rel, contenuto)
        rc, u = lancia(X)
        controllo("%s con «%s»: la creazione dà un avviso che nomina il file" % (rel, nome),
                  rc == 0 and any(r.startswith("avviso: " + rel) for r in u.splitlines()), u)
        rc, u = lancia(X, "--controlla")
        nonva = [r for r in u.splitlines() if r.startswith("non va: " + rel)]
        controllo("%s con «%s»: --controlla dice «non va:» col file e che cosa fare" % (rel, nome),
                  rc == 1 and len(nonva) == 1 and "cancellalo" in nonva[0] and "--innesta" in nonva[0], u)
        prima = leggi(X, rel)
        rc, u = lancia(X, "--innesta")
        controllo("%s con «%s»: --innesta non finge: dice che non lo può sistemare, esce 1, non lo tocca" % (rel, nome),
                  rc == 1 and ("non sistemato: " + rel) in u and leggi(X, rel) == prima
                  and not os.path.exists(os.path.join(X, rel + ".prima-di-redacy")), u)

# #1: una copia del plugin rovinata (stessa versione, contenuto diverso) o un JSON rotto si vede, e si sa che cosa fare
R = os.path.join(BASE, "rovinata-%d" % os.getpid())
lancia(R)
corsa = os.path.join(R, ".agents/script/corsa.py")
integro = leggi(R, ".agents/script/corsa.py")
open(corsa, "wb").write(integro[:300])                      # troncato, ma la testa con la versione c'è
open(os.path.join(R, ".agents/script/pagina.html"), "wb").write(b"<")   # troncato fino a perdere la testa
scrivi(R, ".agents/hooks.json", b'{"hooks')
scrivi(R, ".claude/launch.json", b'{"version"')
scrivi(R, "periodo/todo.json", b'{"todo": [')
rc, u = lancia(R, "--controlla")
righe = u.splitlines()
controllo("--controlla: una copia troncata (corsa.py) è un «avviso:» che dice «lancia lo stesso script con --aggiorna»",
          any(r.startswith("avviso: .agents/script/corsa.py è diverso dall'originale") and "--aggiorna" in r for r in righe), u)
controllo("--controlla: una copia troncata fino a perdere la testa (pagina.html) è segnalata uguale",
          any(r.startswith("avviso: .agents/script/pagina.html è diverso") for r in righe), u)
controllo("--controlla: i file del plugin con JSON rotto dicono «cancellalo e rilancia lo script senza opzioni»",
          all(any(r.startswith("non va: " + f + ": JSON non valido") and "cancellalo e rilancia lo script senza opzioni" in r for r in righe)
              for f in (".agents/hooks.json", ".claude/launch.json")), u)
controllo("--controlla: un JSON dell'utente rotto dice «apri il file e correggilo»",
          any(r.startswith("non va: periodo/todo.json: JSON non valido") and "apri il file e correggilo" in r for r in righe), u)
rc, u = lancia(R, "--aggiorna")
controllo("--aggiorna riscrive le due copie rovinate", leggi(R, ".agents/script/corsa.py") == integro
          and leggi(R, ".agents/script/pagina.html").startswith(b"<!doctype html>") and "esito: 2 aggiornati" in u, u)

# #17: una cartella che non si scrive e non è di Codex non dà la colpa a Codex né propone la riga che rifallirebbe
if hasattr(os, "geteuid") and os.geteuid() != 0:
    Q = os.path.join(BASE, "sola-lettura-%d" % os.getpid())
    os.makedirs(os.path.join(Q, "memoria"))
    os.chmod(os.path.join(Q, "memoria"), 0o555)
    rc, u = lancia(Q)
    os.chmod(os.path.join(Q, "memoria"), 0o755)
    controllo("memoria/ in sola lettura: esce 3, dice quale cartella e i permessi, senza Codex né riga «comando:»",
              rc == 3 and "da finire: non riesco a scrivere in memoria/" in u and "permessi" in u
              and "Codex" not in u and "comando:" not in u, u)
else:
    print("salto  cartella in sola lettura (si è root)")


print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE))
    sys.exit(1)
print("PASSA")
