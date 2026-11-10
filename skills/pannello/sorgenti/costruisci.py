#!/usr/bin/env python3
"""Monta scripts/pagina.html, la pagina del pannello, dai pezzi di questa cartella.

Uso: python3 costruisci.py            scrive ../scripts/pagina.html
     python3 costruisci.py --controlla esce con 1 se pagina.html non è quella che uscirebbe dai pezzi

I pezzi:
  guscio.html      la struttura e la navigazione (barra a sinistra, pannello a destra, foglio del supporto).
                   Carica contenuti.css, dati.js e contenuti.js: nel prototipo sono file accanto.
  fonte.js         nel plugin prende il posto di dati.js: i dati arrivano dal server locale.
  contenuti/*.js   l'interno dei cinque pannelli, in ordine di nome; contenuti/contenuti.css i suoi stili.

La pagina che esce è un file solo, senza risorse esterne (il server la serve con una
Content-Security-Policy senza rete) e con il segnaposto {{GETTONE}} che il server riempie.
Solo libreria standard.
"""
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, "..", "scripts", "pagina.html")


def leggi(*parti):
    with open(os.path.join(QUI, *parti), encoding="utf-8") as f:
        return f.read()


def dentro_script(js):
    # un </script> dentro il codice chiuderebbe il tag; <!-- e <script cambierebbero come l'HTML lo legge
    if "<!--" in js or re.search(r"<script", js, re.I):
        raise SystemExit("costruisci.py: <!-- o <script dentro il codice: scrivili a pezzi ('<' + 'script')")
    return js.replace("</script", "<\\/script")


def sostituisci(html, vecchio, nuovo):
    if html.count(vecchio) != 1:
        raise SystemExit("costruisci.py: nel guscio non trovo una volta sola: %r" % vecchio)
    return html.replace(vecchio, nuovo, 1)


def monta():
    html = leggi("guscio.html")
    cartella = os.path.join(QUI, "contenuti")
    js = "\n".join(leggi("contenuti", n) for n in sorted(os.listdir(cartella)) if n.endswith(".js"))
    css = leggi("contenuti", "contenuti.css")

    html = sostituisci(html, '<link rel="stylesheet" href="contenuti.css">',
                       '<style id="contenuti-css">\n' + css.replace("</style", "<\\/style") + '\n</style>')
    html = sostituisci(html, '<script src="dati.js"></script>',
                       '<script id="fonte">\n' + dentro_script(leggi("fonte.js")) + '\n</script>')
    html = sostituisci(html, '<script src="contenuti.js"></script>',
                       '<script id="contenuti">\n' + dentro_script(js) + '\n</script>')
    html = sostituisci(html, '<meta charset="utf-8">',
                       '<meta charset="utf-8">\n<meta name="redacy-gettone" content="{{GETTONE}}">')
    html = re.sub(r"<title>[^<]*</title>", "<title>Pannello · redacy</title>", html, count=1)
    if not html.startswith("<!doctype html>\n"):
        raise SystemExit("costruisci.py: il guscio deve cominciare con <!doctype html> su una riga")

    # niente risorse esterne: solo il link al supporto può uscire dalla pagina
    esterne = [u for u in re.findall(r"""(?:src|href)\s*=\s*["'](https?:[^"']+)""", html)
               if not u.startswith("https://redacy.com")]
    esterne += re.findall(r"@import|fonts\.googleapis|cdnjs|jsdelivr|unpkg", html)
    if esterne:
        raise SystemExit("costruisci.py: risorse esterne nella pagina: %s" % sorted(set(esterne))[:5])
    return html


def main(argv):
    html = monta()
    if "--controlla" in argv:
        try:
            with open(USCITA, encoding="utf-8") as f:
                ora = f.read()
        except OSError:
            ora = None
        if ora != html:
            print("pagina.html non è aggiornata: rilancia python3 skills/pannello/sorgenti/costruisci.py")
            return 1
        print("pagina.html è aggiornata")
        return 0
    tmp = USCITA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    os.replace(tmp, USCITA)
    print("scritta %s (%d byte)" % (os.path.relpath(USCITA, os.getcwd()), len(html.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
