# redacy 0.3.1 · skills/crea-workspace/scripts/controlla-workspace.py
"""Controlla la cartella di un workspace (workspace/<nome>/).

Uso: python3 controlla-workspace.py CARTELLA
Solo libreria standard, Python 3.9 o più.
"""

import os
import re
import sys

AIUTO = """Uso: python3 controlla-workspace.py CARTELLA_DEL_WORKSPACE

Controlla che il workspace sia un agente intero e in ordine:
  - AGENTS.md c'è e non è vuoto
  - CLAUDE.md contiene solo "@AGENTS.md"
  - ci sono .agents/skills, .agents/regole e .agents/policy
  - c'è memoria/INDICE.md e la scheda memoria/<nome>.md, non vuoti
  - nessun segnaposto {{...}} è rimasto in nessun file
  - nessuna tabella nei file di .agents/policy (la policy è un elenco di righe)

Gli avvisi non fermano: un "(da completare)" rimasto, una scheda non
collegata dall'indice.

Uscite: 0 tutto a posto · 1 c'è almeno un errore (o l'uso è sbagliato).
Opzioni:
  -h, --help   mostra questo aiuto
"""

RE_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RE_SEGNAPOSTO = re.compile(r"\{\{[^{}]*\}\}")
RE_TABELLA_RIGA = re.compile(r"^\s*\|.*\|\s*$")
RE_TABELLA_SEPARATORE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$")
SALTA = {".git", "__pycache__", "node_modules"}


def leggi(percorso):
    try:
        with open(percorso, encoding="utf-8") as fh:
            return fh.read()
    except (OSError, UnicodeDecodeError):
        return None


def non_vuoto(percorso):
    testo = leggi(percorso)
    return testo is not None and testo.strip() != ""


def controlla(cartella):
    errori = []
    avvisi = []
    cartella = os.path.abspath(cartella)
    if not os.path.isdir(cartella):
        return ["la cartella %s non esiste." % cartella], avvisi
    nome = os.path.basename(cartella.rstrip(os.sep))
    if not RE_KEBAB.match(nome):
        errori.append(
            "il nome della cartella \"%s\" non è in kebab-case: rinominala con solo minuscole, numeri e trattini." % nome
        )

    def qui(*parti):
        return os.path.join(cartella, *parti)

    if not os.path.isfile(qui("AGENTS.md")):
        errori.append("manca AGENTS.md: scrivilo (chi sei, dominio, come lavori).")
    elif not non_vuoto(qui("AGENTS.md")):
        errori.append("AGENTS.md è vuoto: scrivi chi è il workspace, il dominio e come lavora.")

    if not os.path.isfile(qui("CLAUDE.md")):
        errori.append("manca CLAUDE.md: deve contenere solo la riga @AGENTS.md.")
    else:
        testo = leggi(qui("CLAUDE.md"))
        if testo is None or testo.strip() != "@AGENTS.md":
            errori.append("CLAUDE.md deve contenere solo la riga @AGENTS.md: riscrivilo così.")

    for sotto in ("skills", "regole", "policy"):
        if not os.path.isdir(qui(".agents", sotto)):
            errori.append("manca la cartella .agents/%s/: creala (anche vuota)." % sotto)

    if not os.path.isfile(qui("memoria", "INDICE.md")):
        errori.append("manca memoria/INDICE.md: l'indice delle pagine di memoria.")
    elif not non_vuoto(qui("memoria", "INDICE.md")):
        errori.append("memoria/INDICE.md è vuoto: scrivi almeno il collegamento alla scheda.")
    else:
        if "[[%s]]" % nome not in (leggi(qui("memoria", "INDICE.md")) or ""):
            avvisi.append("memoria/INDICE.md non collega la scheda: aggiungi [[%s]]." % nome)

    scheda = qui("memoria", nome + ".md")
    if not os.path.isfile(scheda):
        errori.append("manca la scheda memoria/%s.md: cosa fa, quando si usa, dove stanno i dati." % nome)
    elif not non_vuoto(scheda):
        errori.append("la scheda memoria/%s.md è vuota: scrivi cosa fa, quando si usa, dove stanno i dati." % nome)

    for radice, cartelle, files in os.walk(cartella):
        cartelle[:] = sorted(c for c in cartelle if c not in SALTA)
        for f in sorted(files):
            pieno = os.path.join(radice, f)
            rel = os.path.relpath(pieno, cartella)
            testo = leggi(pieno)
            if testo is None:
                continue
            righe = testo.split("\n")
            for n, riga in enumerate(righe, 1):
                if RE_SEGNAPOSTO.search(riga):
                    errori.append(
                        "%s riga %d: è rimasto un segnaposto %s. Scrivi il contenuto vero."
                        % (rel, n, RE_SEGNAPOSTO.search(riga).group(0))
                    )
                if "(da completare" in riga:
                    avvisi.append("%s riga %d: c'è ancora un \"(da completare)\"." % (rel, n))
            if rel.startswith(os.path.join(".agents", "policy") + os.sep):
                for n, riga in enumerate(righe, 1):
                    if RE_TABELLA_SEPARATORE.match(riga) or RE_TABELLA_RIGA.match(riga):
                        errori.append(
                            "%s riga %d: c'è una tabella. La policy è un elenco di righe, una voce per riga: riscrivila."
                            % (rel, n)
                        )
                        break
    return errori, avvisi


def main(argv):
    if any(a in ("-h", "--help") for a in argv):
        sys.stdout.write(AIUTO)
        return 0
    if len(argv) != 1:
        sys.stderr.write("errore: serve la cartella del workspace, una sola. Guarda --help.\n")
        return 1
    errori, avvisi = controlla(argv[0])
    for a in avvisi:
        print("avviso: %s" % a)
    for e in errori:
        print("errore: %s" % e)
    if errori:
        print("esito: %d problemi da correggere" % len(errori))
        return 1
    print("esito: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
