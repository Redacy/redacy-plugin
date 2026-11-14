# redacy 0.4.2 · prove/grafi/_robusto.py (lo lanciano prova-controllo.sh e prova-corsa.sh)
"""controlla-grafo.py, yaml_ridotto.py e corsa.py davanti a file rotti e a nomi che Windows non accetta.

Uso: python3 _robusto.py RADICE CARTELLA_DI_PROVA [controllo|corsa]
 - un campo `file:` con \\\\server\\x o \\Users\\x non è un percorso relativo;
 - nomi riservati da Windows (con, aux, nul, prn, com1...) rifiutati come nome di grafo (controlla-grafo e corsa apri);
 - yaml annidato troppo in fondo (400 rientri, 5000 parentesi): un errore con la riga, niente RecursionError;
 - yaml non UTF-8: il «Cosa fare» dice di salvare il file in UTF-8;
 - yaml_ridotto.py lanciato a mano con l'uscita in cp1252: niente UnicodeEncodeError;
 - corsa.py: uno `.stop` non UTF-8 vale come stop senza motivo; un registro troncato o di forma strana (`passi: 5`,
   un passo senza `id` o senza `stato`) non dà un traceback in nessun comando e dice di aprire una corsa nuova;
   `elenco` la mostra come rovinata e va avanti con le altre; i messaggi di uso sono in italiano, con un solo «Uso:».
Una riga per controllo: «ok» o «FALLISCE». In fondo PASSA oppure FALLISCE <perché>. Niente rete, niente processi veri.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

sys.dont_write_bytecode = True
RADICE, BASE = sys.argv[1], sys.argv[2]
PARTE = sys.argv[3] if len(sys.argv) > 3 else "tutte"   # «controllo» (controlla-grafo, yaml_ridotto), «corsa» (corsa.py) o tutte
SCRIPT = os.path.join(RADICE, "skills", "crea-grafo", "scripts")
CONTROLLA = os.path.join(SCRIPT, "controlla-grafo.py")
CORSA = os.path.join(SCRIPT, "corsa.py")
YAML = os.path.join(SCRIPT, "yaml_ridotto.py")
BUONO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "buoni", "smista-fatture-in-arrivo.yaml")
FALLITE = []
shutil.rmtree(BASE, ignore_errors=True)
os.makedirs(BASE)


def controllo(descrizione, ok, dettaglio=""):
    print(("ok        " if ok else "FALLISCE  ") + descrizione + ((" · " + str(dettaglio)[:500]) if not ok and dettaglio else ""))
    if not ok:
        FALLITE.append(descrizione)


def scrivi(percorso, dati):
    os.makedirs(os.path.dirname(percorso), exist_ok=True)
    with open(percorso, "wb") as f:
        f.write(dati if isinstance(dati, bytes) else dati.encode("utf-8"))


def lancia(script, *args, env=None):
    e = dict(os.environ)
    e.update(env or {})
    r = subprocess.run([sys.executable, script] + list(args), capture_output=True, encoding="utf-8", errors="replace",
                       timeout=120, env=e)
    return r.returncode, r.stdout, r.stderr


def pulito(*testi):
    return all("Traceback" not in t for t in testi)


def carica(percorso, nome):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


with open(BUONO, encoding="utf-8") as f:
    TESTO_BUONO = f.read()
_n = [0]


def studio():
    _n[0] += 1
    d = os.path.join(BASE, "studio-%d" % _n[0])
    scrivi(os.path.join(d, "AGENTS.md"), "# Studio\n")
    scrivi(os.path.join(d, "grafi", "smista-fatture-in-arrivo.yaml"), TESTO_BUONO)
    return d


def prova_controllo():
    # ---- controlla-grafo: percorsi di rete e nomi riservati
    G = carica(CONTROLLA, "controlla_grafo_robusto")
    controllo("percorso relativo normale accettato", G._percorso_relativo_ok("fonti/fatture/a.md") and G._percorso_relativo_ok("istruzioni\\a.md"))
    for v in ("\\\\server\\x\\a.md", "\\Users\\a.md", "/etc/a", "C:\\x", "~/a", "..\\a", "a/../b"):
        controllo("percorso non relativo rifiutato: %s" % v, not G._percorso_relativo_ok(v))

    d = studio()
    for nome in ("con", "aux", "nul", "prn", "com1", "lpt9"):
        scrivi(os.path.join(d, "grafi", nome + ".yaml"), TESTO_BUONO.replace("grafo: smista-fatture-in-arrivo", "grafo: " + nome))
        errori, avvisi = G.controlla_file(os.path.join(d, "grafi", nome + ".yaml"))
        controllo("controlla-grafo: il nome «%s» è riservato da Windows, con una frase che dice di sceglierne un altro" % nome,
                  any("riservato" in e and "scegli" in e for e in errori), errori)
    errori, _ = G.controlla_file(os.path.join(d, "grafi", "smista-fatture-in-arrivo.yaml"))
    controllo("controlla-grafo: il grafo buono resta senza errori", errori == [], errori)

    # ---- yaml annidato troppo in fondo, yaml non UTF-8
    d = studio()
    profondo = "grafo: x\na:\n" + "".join(" " * i + "k%d:\n" % i for i in range(1, 400))
    scrivi(os.path.join(d, "grafi", "prof.yaml"), profondo)
    rc, out, err = lancia(CONTROLLA, os.path.join(d, "grafi", "prof.yaml"))
    controllo("yaml con 400 livelli: un errore con la riga, niente RecursionError",
              rc == 1 and "troppi livelli" in out and "prof.yaml:" in out and "RecursionError" not in out + err and pulito(out, err), (rc, out, err))
    scrivi(os.path.join(d, "grafi", "par.yaml"), "grafo: par\na: " + "[" * 5000 + "\n")
    rc, out, err = lancia(CONTROLLA, os.path.join(d, "grafi", "par.yaml"))
    controllo("yaml con 5000 parentesi: un errore con la riga, niente RecursionError",
              rc == 1 and "troppi livelli" in out and "par.yaml:2:" in out and pulito(out, err), (rc, out, err))
    rc, out, err = lancia(YAML, os.path.join(d, "grafi", "prof.yaml"))
    controllo("yaml_ridotto.py a mano su 400 livelli: una riga con il numero, uscita 1, niente traceback",
              rc == 1 and "troppi livelli" in err and pulito(out, err), (rc, err))
    scrivi(os.path.join(d, "grafi", "latin.yaml"), b"grafo: latin\nobiettivo: perch\xe9\npassi: []\n")
    rc, out, err = lancia(CONTROLLA, os.path.join(d, "grafi", "latin.yaml"))
    controllo("yaml non UTF-8: il «Cosa fare» dice di salvare il file in UTF-8",
              rc == 1 and "non è in UTF-8" in out and "Cosa fare: salva il file in UTF-8" in out, out)

    # ---- yaml_ridotto.py a mano con l'uscita in cp1252
    scrivi(os.path.join(d, "freccia.yaml"), "grafo: a → b\nnome: più\n")
    rc, out, err = lancia(YAML, os.path.join(d, "freccia.yaml"), env={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
    controllo("yaml_ridotto.py con l'uscita in cp1252 e una freccia nel testo: niente UnicodeEncodeError",
              rc == 0 and pulito(out, err) and "UnicodeEncodeError" not in err, (rc, err))
    r = subprocess.run([sys.executable, YAML, os.path.join(d, "freccia.yaml")], capture_output=True,
                       env=dict(os.environ, PYTHONIOENCODING="cp1252"))
    controllo("yaml_ridotto.py con l'uscita in cp1252: i byte dell'uscita sono UTF-8 e il testo torna uguale",
              r.returncode == 0 and json.loads(r.stdout.decode("utf-8")) == {"grafo": "a → b", "nome": "più"}, r.stdout[:200])



def prova_corsa():
    # ---- corsa.py: un registro rovinato
    d = studio()
    rc, out, err = lancia(CORSA, "apri", "con", "--cartella", d)
    controllo("corsa apri con: rifiutato come nome riservato, una riga, niente traceback",
              rc == 1 and "riservato" in err and pulito(out, err) and len(err.strip().splitlines()) == 1, (rc, err))
    rc, id_corsa, err = lancia(CORSA, "apri", "smista-fatture-in-arrivo", "--cartella", d)
    id_corsa = id_corsa.strip()
    controllo("corsa apri: apre una corsa", rc == 0 and id_corsa.startswith("smista-fatture-in-arrivo-"), (rc, err))
    corse = os.path.join(d, "grafi", "corse")
    file_corsa = os.path.join(corse, id_corsa + ".json")
    with open(file_corsa, "rb") as f:
        BUONA = f.read()


    def con_corsa(dati):
        scrivi(file_corsa, dati)


    # uno .stop non UTF-8: stop senza motivo (la corsa si ferma), niente traceback
    scrivi(os.path.join(corse, id_corsa + ".stop"), b"\xff\xfe\x00")
    rc, out, err = lancia(CORSA, "battito", id_corsa, "--cartella", d)
    controllo("uno .stop non UTF-8 vale come stop senza motivo: uscita 3 e il messaggio di stop, niente traceback",
              rc == 3 and "Corsa fermata da" in err and pulito(out, err), (rc, err))
    os.remove(os.path.join(corse, id_corsa + ".stop"))

    STRANE = [
        ("troncato", BUONA[:100]),
        ("vuoto", b""),
        ("non UTF-8", b'{"stato": "in-corso", "passi": [], "x": "\xe9"}'),
        ("passi: 5", b'{"stato":"in-corso","passi":5}'),
        ("un passo senza id", b'{"stato":"in-corso","passi":[{"x":1}]}'),
        ("un passo senza stato", b'{"stato":"in-corso","passi":[{"id":"leggi-fattura"}]}'),
        ("un passo che non è un oggetto", b'{"stato":"in-corso","passi":["a"]}'),
        ("stato che non è un testo", b'{"stato":5,"passi":[]}'),
        ("radice che è un elenco", b"[1, 2]"),
    ]
    for nome, dati in STRANE:
        for comando in (["passo", id_corsa, "leggi-fattura", "inizio"], ["battito", id_corsa], ["chiudi", id_corsa, "finita"],
                        ["stato", id_corsa], ["ferma", id_corsa]):
            con_corsa(dati)
            rc, out, err = lancia(CORSA, *(comando + ["--cartella", d]))
            controllo("registro %s, comando %s: uscita 1, «rovinato» e «corsa nuova», niente traceback" % (nome, comando[0]),
                      rc == 1 and "rovinato" in err and "corsa nuova" in err and pulito(out, err), (rc, err))
        con_corsa(dati)
        rc, out, err = lancia(CORSA, "elenco", "--cartella", d)
        controllo("registro %s, elenco: uscita 0, la corsa è mostrata come rovinata" % nome,
                  rc == 0 and ("%s\trovinata" % id_corsa) in out and pulito(out, err), (rc, out, err))
    # elenco va avanti con le altre
    con_corsa(BUONA[:100])
    rc, altra, err = lancia(CORSA, "apri", "smista-fatture-in-arrivo", "--cartella", d, "--persa-dopo", "30")
    altra = altra.strip()
    rc, out, err = lancia(CORSA, "elenco", "--cartella", d)
    controllo("elenco con una corsa rovinata e una buona: mostra tutte e due",
              rc == 0 and ("%s\tin corso" % altra) in out and ("%s\trovinata" % id_corsa) in out, (rc, out, err))
    # campi strani ma la forma regge
    con_corsa(json.dumps(dict(json.loads(BUONA.decode("utf-8")), persa_dopo_minuti="abc", ultimo_segno=5)).encode("utf-8"))
    for comando in (["stato", id_corsa], ["elenco"]):
        rc, out, err = lancia(CORSA, *(comando + ["--cartella", d]))
        controllo("persa_dopo_minuti e ultimo_segno strani, comando %s: niente traceback" % comando[0], rc == 0 and pulito(out, err), (rc, err))
    # un registro con il BOM (salvato da un programma di Windows) si legge
    con_corsa(b"\xef\xbb\xbf" + BUONA)
    rc, out, err = lancia(CORSA, "battito", id_corsa, "--cartella", d)
    controllo("un registro con il BOM si legge", rc == 0 and pulito(out, err), (rc, err))

    # ---- i messaggi d'uso
    rc, out, err = lancia(CORSA, "apri")
    controllo("corsa.py apri senza il grafo: un solo «Uso:», in italiano", rc == 1 and "Uso: Uso:" not in err
              and "required" not in err and "mancano questi argomenti: grafo" in err, err)
    rc, out, err = lancia(CORSA, "foo")
    controllo("corsa.py foo: il comando non esiste, in italiano", rc == 1 and "invalid choice" not in err
              and "non esiste" in err and "apri" in err, err)
    rc, out, err = lancia(CORSA, "apri", "x", "--avviato-da", "zz")
    controllo("corsa.py apri --avviato-da zz: valore non ammesso, in italiano", rc == 1 and "invalid choice" not in err
              and "non e' ammesso" in err, err)
    rc, out, err = lancia(CORSA, "apri", "x", "--sessione")
    controllo("corsa.py apri --sessione senza valore: in italiano", rc == 1 and "expected" not in err and "serve un valore" in err, err)



if PARTE in ("tutte", "controllo"):
    prova_controllo()
if PARTE in ("tutte", "corsa"):
    prova_corsa()

print()
if FALLITE:
    print("FALLISCE " + "; ".join(FALLITE[:6]) + (" … (%d in tutto)" % len(FALLITE) if len(FALLITE) > 6 else ""))
    sys.exit(1)
print("PASSA")
