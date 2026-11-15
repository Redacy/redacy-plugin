#!/usr/bin/env python3
# redacy 0.5.0 · prove/ci/percorso.py
"""Stampa la cartella dove un programma ha installato il plugin.

  percorso.py claude <CLAUDE_CONFIG_DIR>   legge plugins/installed_plugins.json
  percorso.py codex <file>                 legge l'uscita JSON di `codex plugin add --json` (campo installedPath)
Esce 1 con un messaggio se non la trova. Solo libreria standard.
"""
import json
import os
import sys


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("claude", "codex"):
        print(__doc__, file=sys.stderr)
        return 1
    try:
        if sys.argv[1] == "claude":
            with open(os.path.join(sys.argv[2], "plugins", "installed_plugins.json"), encoding="utf-8") as f:
                voci = json.load(f)["plugins"]["redacy@redacy"]
            p = voci[0]["installPath"]
        else:
            testo = open(sys.argv[2], encoding="utf-8").read()
            p = json.loads(testo[testo.index("{"):])["installedPath"]
    except (OSError, ValueError, KeyError, IndexError) as e:
        print("non trovo il percorso installato: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        return 1
    if not os.path.isdir(p):
        print("il percorso %s non è una cartella" % p, file=sys.stderr)
        return 1
    print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
