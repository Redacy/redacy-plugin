#!/usr/bin/env bash
# redacy 0.5.0 · prove/coerenza/prova-testi.sh
# Controlla, senza modello e senza rete, che i testi e le promesse del plugin siano coerenti:
#   a. ogni testo con `python3` ha anche la riga per Windows («Su Windows» e `py -3`)
#   b. `inizia` parla di Python prima del passo 0
#   c. nessuna espansione di shell valida solo in bash per l'id della sessione
#   d. il supporto umano porta sempre a redacy.com/contatti
#   e. la strada verso una persona c'è dove deve, ed è detta «una volta sola»
#   f. nessun programma promesso fuori dall'elenco, Linux una volta sola nel README, con la sua frase
#   g. niente rete fuori dal pannello (regola sotto)
#   h. la PRIVACY dice ancora le tre cose che contano
#   j. le opzioni `--qualcosa` che un testo fa lanciare con uno script del plugin esistono in quello script
#   i. nessuna variabile `$nome` senza graffe seguita da un carattere non ASCII nelle prove (la bash 3.2 dei Mac la legge male)
#
# Regola del punto g, semplice e statica. Nei file .py sotto skills/:
#   1. i moduli di rete (urllib, requests, socket, smtplib, ftplib, http.*, ssl, webbrowser)
#      si importano solo in skills/pannello/scripts/pannello.py;
#   2. ogni indirizzo http:// o https:// dentro una stringa del codice è https://redacy.com/contatti,
#      http://127.0.0.1 o http://localhost. Commenti e docstring sono documentazione e non contano.
#      Unica eccezione: il prefisso https://redacy.com dentro startswith(...), che confronta e non apre niente.
#
# Serve bash, python3 e grep. Gira anche in Git Bash su Windows; se python3 non c'è: PYTHON=python oppure PYTHON="py -3".
# Uso: bash prove/coerenza/prova-testi.sh   (la radice si deduce da $0, così gira anche su una copia)
set -u
RADICE="$(cd "$(dirname "$0")/../.." && pwd)"
PY="${PYTHON:-python3}"
cd "$RADICE" || { echo "FALLISCE non trovo $RADICE"; exit 1; }
$PY -I -c "import sys" >/dev/null 2>&1 || { echo "FALLISCE manca Python 3 ($PY)"; exit 1; }

TEMPO="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/redacy-testi-$$")"
mkdir -p "$TEMPO"
trap 'rm -rf "$TEMPO"' EXIT
export TEMPO
NERRORI=0
FALLITI=""
ok() { echo "ok $1"; }
no() { # <controllo> <perché, anche su più righe>
  echo "FALLISCE $1"
  [ -z "${2:-}" ] || printf '%s\n' "$2" | head -6 | sed 's/^/           | /'
  NERRORI=$((NERRORI + 1)); FALLITI="${FALLITI}${FALLITI:+, }$1"
}

# --- a. ogni testo con python3 ha la riga per Windows ---
manca=""; n=0
for f in skills/*/SKILL.md skills/*/references/*.md; do
  [ -f "$f" ] || continue
  if grep -q "python3" "$f"; then
    n=$((n + 1))
    { grep -q "Su Windows" "$f" && grep -qF -- 'py -3' "$f"; } || manca="${manca}${manca:+
}$f"
  fi
done
if [ -n "$manca" ]; then no "a. testi con python3 senza la riga per Windows (Su Windows… python, py -3)" "$manca"
else ok "a. $n testi con python3, tutti con la riga per Windows"; fi

# --- b. inizia: Python prima del passo 0 ---
I="skills/inizia/SKILL.md"
rb=""
lp="$(grep -n "^## Prima di tutto: Python" "$I" | head -1 | cut -d: -f1)"
l0="$(grep -n "^## Passo 0" "$I" | head -1 | cut -d: -f1)"
[ -n "$lp" ] || rb="manca la sezione «Prima di tutto: Python»"
[ -n "$l0" ] || rb="${rb}${rb:+; }manca il «Passo 0»"
if [ -n "$lp" ] && [ -n "$l0" ] && [ "$lp" -ge "$l0" ]; then rb="${rb}${rb:+; }la sezione Python sta dopo il Passo 0"; fi
for k in "python --version" "py -3" "winget" "--accept-source-agreements" "--accept-package-agreements"; do
  grep -qF -- "$k" "$I" || rb="${rb}${rb:+; }manca «${k}»"
done
if [ -n "$rb" ]; then no "b. inizia: Python prima di tutto" "$rb"
else ok "b. inizia: la sezione Python (riga $lp) viene prima del Passo 0 (riga $l0), con python --version, py -3 e winget (con i due consensi)"; fi

# --- c. niente espansione solo-bash dell'id della sessione ---
r="$(grep -rnF '${CLAUDE_CODE_SESSION_ID:-' skills README.md 2>/dev/null || true)"
if [ -n "$r" ]; then no "c. espansione \${CLAUDE_CODE_SESSION_ID:-…} ancora presente" "$r"
else ok "c. nessuna espansione solo-bash dell'id della sessione"; fi

# --- d. il supporto porta a redacy.com/contatti ---
$PY -I - > "${TEMPO}/d.txt" <<'PY'
import os, re, sys
ext = (".md", ".py", ".js", ".html", ".json")
files = ["README.md", "PRIVACY.md", "CONNECTORS.md"]
for d, _, nomi in os.walk("skills"):
    files += [os.path.join(d, n) for n in nomi if n.endswith(ext)]
out = []
for f in files:
    if not os.path.isfile(f):
        continue
    for i, riga in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
        s = riga.rstrip("\n")
        if "supporto" in s.lower() and "redacy.com" in s and "redacy.com/contatti" not in s:
            out.append("%s:%d: supporto senza /contatti: %s" % (f, i, s.strip()[:90]))
        if f.startswith("skills") and f.endswith(".py") and 'startswith("https://redacy.com")' in s:
            continue  # il prefisso confrontato da costruisci.py non apre niente
        if f.startswith("skills"):
            for m in re.finditer(r"https://redacy\.com(?!/contatti)", s):
                out.append("%s:%d: https://redacy.com senza /contatti: %s" % (f, i, s.strip()[:90]))
print("\n".join(out))
PY
rd="$(cat "${TEMPO}/d.txt")"
if [ -n "$rd" ]; then no "d. il supporto non porta a redacy.com/contatti" "$rd"
else ok "d. ogni «supporto» con redacy.com porta a /contatti, e in skills/ nessun https://redacy.com spoglio"; fi

# --- e. la strada verso una persona c'è dove deve ---
re_=""
for f in skills/inizia/modello/AGENTS.md skills/inizia/SKILL.md skills/programma/SKILL.md skills/collega-sensore/SKILL.md; do
  grep -q "redacy.com/contatti" "$f" || re_="${re_}${re_:+; }$f senza redacy.com/contatti"
done
grep -q "una volta sola" skills/inizia/modello/AGENTS.md || re_="${re_}${re_:+; }AGENTS.md del modello senza «una volta sola»"
if [ -n "$re_" ]; then no "e. la strada verso una persona" "$re_"
else ok "e. redacy.com/contatti nei quattro posti, e «una volta sola» nel modello"; fi

# --- f. nessun programma fuori dall'elenco ---
lista="README.md PRIVACY.md CONNECTORS.md"
for f in .claude-plugin/*.json .codex-plugin/plugin.json .agents/plugins/marketplace.json; do
  [ -f "$f" ] && lista="$lista $f"
done
lista="$lista $(find skills -name '*.md' | tr '\n' ' ')"
# shellcheck disable=SC2086
rf="$(grep -iwnE 'cursor|gemini|copilot|windsurf|opencode|cline|aider' $lista 2>/dev/null | head -5 || true)"
for k in "app di Claude" "Cowork" "Claude Code" "Codex" "Windows" "macOS"; do
  grep -qF -- "$k" README.md || rf="${rf}${rf:+
}il README non nomina «${k}»"
done
FL="Funziona su macOS e Windows; da terminale anche su Linux."
grep -qF -- "$FL" README.md || rf="${rf}${rf:+
}il README non contiene la frase «${FL}»"
[ "$(grep -io "linux" README.md | wc -l | tr -d ' ')" = "1" ] || rf="${rf}${rf:+
}la parola Linux nel README deve comparire una volta sola"
if [ -n "$rf" ]; then no "f. programmi o sistemi fuori elenco" "$rf"
else ok "f. nessun programma fuori elenco in README, PRIVACY, CONNECTORS, manifesti e skill; README con l'elenco giusto e Linux una volta sola"; fi

# --- g. niente rete fuori dal pannello ---
$PY -I - > "${TEMPO}/g.txt" <<'PY'
import ast, io, os, re, tokenize
PANNELLO = os.path.join("skills", "pannello", "scripts", "pannello.py")
RETE = ("urllib", "requests", "socket", "smtplib", "ftplib", "http", "ssl", "webbrowser")
OK_URL = ("https://redacy.com/contatti", "http://127.0.0.1", "http://localhost")
out = []
n = 0
for d, _, nomi in os.walk("skills"):
    for nome in nomi:
        if not nome.endswith(".py"):
            continue
        f = os.path.join(d, nome)
        n += 1
        src = open(f, encoding="utf-8", errors="replace").read()
        if f != PANNELLO:
            moduli = []
            try:
                for nodo in ast.walk(ast.parse(src)):
                    if isinstance(nodo, ast.Import):
                        moduli += [a.name for a in nodo.names]
                    elif isinstance(nodo, ast.ImportFrom) and nodo.module:
                        moduli.append(nodo.module)
            except SyntaxError:
                moduli = re.findall(r"^\s*(?:import|from)\s+([\w.]+)", src, re.M)
            for m in moduli:
                if m.split(".")[0] in RETE:
                    out.append("%s: importa %s, ammesso solo in pannello.py" % (f, m))
        # indirizzi nelle stringhe del codice (commenti e docstring non contano)
        try:
            prec = None
            toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
            for i, t in enumerate(toks):
                if t.type == tokenize.STRING:
                    doc = prec in (None, tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT)
                    dopo = next((x for x in toks[i + 1:] if x.type not in (tokenize.COMMENT, tokenize.NL)), None)
                    doc = doc and dopo is not None and dopo.type in (tokenize.NEWLINE, tokenize.ENDMARKER)
                    if not doc:
                        riga = t.line
                        for m in re.finditer(r"https?://[^\s\"'`)>\]]*", t.string):
                            u = m.group(0)
                            if u.startswith(OK_URL):
                                continue
                            if u == "https://redacy.com" and "startswith(" in riga:
                                continue
                            out.append("%s:%d: indirizzo non ammesso: %s" % (f, t.start[0], u))
                if t.type not in (tokenize.COMMENT, tokenize.NL):
                    prec = t.type
        except (tokenize.TokenError, IndentationError):
            for i, riga in enumerate(src.splitlines(), 1):
                if re.match(r"\s*#", riga):
                    continue
                for u in re.findall(r"https?://[^\s\"'`)>\]]*", riga):
                    if not u.startswith(OK_URL):
                        out.append("%s:%d: indirizzo non ammesso: %s" % (f, i, u))
print("\n".join(out))
PY
rg="$(cat "${TEMPO}/g.txt")"
if [ -n "$rg" ]; then no "g. rete non dichiarata nei .py" "$rg"
else ok "g. moduli di rete solo in pannello.py, indirizzi solo redacy.com/contatti o locali"; fi

# --- h. la PRIVACY dice ancora le tre cose che contano ---
rh=""
for k in "non ha telemetria" "127.0.0.1" "non parla con nessun server di Redacy"; do
  grep -qF -- "$k" PRIVACY.md || rh="${rh}${rh:+; }PRIVACY.md non dice «${k}»"
done
if [ -n "$rh" ]; then no "h. la PRIVACY" "$rh"
else ok "h. PRIVACY.md: nessuna telemetria, 127.0.0.1, nessun server di Redacy"; fi

# --- j. le opzioni che i testi fanno lanciare esistono negli script ---
# Per ogni riga di un .md sotto skills/ o del README che nomina uno script .py del plugin (cercato per nome sotto
# skills/) e, sulla stessa riga, opzioni --qualcosa dentro apici inversi: ogni opzione deve comparire fra virgolette
# nel codice di almeno uno degli script nominati (in add_argument o nella lettura di argv a mano, come fa
# inventario.py). Se nessuno script si trova, la riga si salta. Eccezioni: opzioni di altri programmi (winget, ecc.).
$PY -I - > "${TEMPO}/j.txt" <<'PY'
import os, re
ECCEZIONI = {"--accept-source-agreements", "--accept-package-agreements", "--plugin-dir", "--version", "--id"}
script = {}
for d, _, nomi in os.walk("skills"):
    for nome in nomi:
        if nome.endswith(".py"):
            testo = open(os.path.join(d, nome), encoding="utf-8", errors="replace").read()
            # un'opzione c'è se è scritta fra virgolette nel codice (add_argument, o argv letto a mano)
            script.setdefault(nome, set()).update(re.findall(r"[\"'](--[A-Za-z][A-Za-z0-9-]*)[\"']", testo))
files = ["README.md"]
for d, _, nomi in os.walk("skills"):
    files += [os.path.join(d, n) for n in nomi if n.endswith(".md")]
out = []
n = 0
for f in files:
    for i, riga in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
        nominati = [x for x in set(re.findall(r"([A-Za-z0-9_-]+\.py)\b", riga)) if x in script]
        if not nominati:
            continue
        for span in re.findall(r"`([^`]*)`", riga):
            for o in re.findall(r"(?<![\w-])(--[A-Za-z][A-Za-z0-9-]*)", span):
                if o in ECCEZIONI:
                    continue
                n += 1
                if not any(o in script[x] for x in nominati):
                    out.append("%s:%d: %s non è un'opzione di %s" % (f, i, o, ", ".join(sorted(nominati))))
print("\n".join(out))
open(os.path.join(os.environ["TEMPO"], "j.n"), "w").write(str(n))
PY
rj="$(cat "${TEMPO}/j.txt")"
if [ -n "$rj" ]; then no "j. opzioni che il testo promette e lo script non ha" "$rj"
else ok "j. $(cat "${TEMPO}/j.n") opzioni nominate nei testi, tutte presenti negli script"; fi

# --- i. variabili senza graffe prima di un carattere non ASCII, nelle prove .sh ---
$PY -I - > "${TEMPO}/i.txt" <<'PY'
import os, re
rx = re.compile(rb"\$[A-Za-z_][A-Za-z0-9_]*[^\x00-\x7f]")
for d, _, nomi in os.walk("prove"):
    for nome in nomi:
        if nome.endswith(".sh"):
            f = os.path.join(d, nome)
            for i, riga in enumerate(open(f, "rb").read().split(b"\n"), 1):
                m = rx.search(riga)
                if m:
                    print("%s:%d: %s" % (f, i, m.group(0).decode("utf-8", "replace")))
PY
ri="$(cat "${TEMPO}/i.txt")"
if [ -n "$ri" ]; then no "i. variabile senza graffe prima di un carattere non ASCII" "$ri"
else ok "i. nelle prove .sh nessuna variabile senza graffe prima di un carattere non ASCII"; fi

if [ "$NERRORI" -eq 0 ]; then echo PASSA; exit 0; fi
echo "FALLISCE $FALLITI"
exit 1
