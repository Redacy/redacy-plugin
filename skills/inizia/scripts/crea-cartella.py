#!/usr/bin/env python3
"""Crea la cartella dello studio dal modello del plugin redacy.

Uso:
    python3 crea-cartella.py <cartella>              crea ciò che manca, non tocca ciò che c'è
    python3 crea-cartella.py <cartella> --controlla  dice cosa manca o non va, senza scrivere
    python3 crea-cartella.py <cartella> --innesta    dopo il sì dell'utente: aggiunge `@AGENTS.md` al CLAUDE.md
                                                     che c'è già e i controlli di redacy ai file degli hook che
                                                     c'erano già (prima salva una copia .prima-di-redacy)
    python3 crea-cartella.py <cartella> --aggiorna   rinfresca le copie che sono del plugin (script, controlli,
                                                     schemi, pagina del pannello); riscrive i comandi dei controlli
                                                     automatici scritti per un altro computer; porta il nuovo
                                                     AGENTS.md (con una copia di prima); non tocca nient'altro

Cosa fa, nell'ordine:
1. copia l'albero di skills/inizia/modello/ nella cartella (i file .tienimi tengono solo la cartella);
2. crea i collegamenti .claude/skills -> ../.agents/skills e .claude/rules -> ../.agents/regole;
3. copia gli script che gli hook e l'agente lanciano senza il plugin (tabella COPIE), con la
   versione e l'origine nelle prime righe;
4. copia .claude/launch.json dal modello del pannello;
5. se ha creato qualcosa, scrive una riga in memoria/LOG.md.

Non sovrascrive mai un file che c'è già: lo salta e lo dice. Un file sorgente che manca nel
plugin è un avviso, non un errore. Se il CLAUDE.md o un file degli hook c'erano già e non portano
`@AGENTS.md` o i controlli di redacy, lo dice con un `avviso:` (con --controlla è un `non va:`); lo stesso se un
file degli hook non è JSON o non ha la forma giusta (--innesta non lo può sistemare e lo dice).
--controlla avvisa anche se una copia del plugin è diversa dall'originale (rovinata o cambiata a mano), se i
controlli automatici sono scritti per un altro computer (un hook per bash su Windows, o il contrario: --aggiorna
riscrive solo i `command` dei gruppi del plugin) e se l'AGENTS.md è di un'altra versione di redacy (--aggiorna lo
sostituisce tenendo una copia `AGENTS.md.prima-di-redacy`; se ha la stessa versione ma è diverso, lo lascia com'è).
Solo libreria standard (Python 3.8 o più recente).

Uscite: 0 fatto (o, con --controlla, niente manca); 1 con --controlla qualcosa manca o non va, o con --innesta
un file non si può sistemare; 2 uso sbagliato; 3 fatto in parte: alcune cartelle non si possono scrivere da
questa sessione (in Codex .agents/ e .codex/ sono protette). Se sono quelle, lo script stampa la riga `comando:`
da lanciare una volta nel terminale per finire; per le altre cartelle dice quali sono e di controllare i permessi.
"""

import argparse
import copy
import datetime
import json
import os
import shlex
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Gli script che vivono in un'altra skill e che la cartella deve avere in proprio.
# (origine nel plugin, destinazione nella cartella)
COPIE = [
    ("skills/crea-grafo/scripts/corsa.py", ".agents/script/corsa.py"),
    ("skills/crea-grafo/scripts/controlla-grafo.py", ".agents/script/controlla-grafo.py"),
    ("skills/crea-grafo/scripts/yaml_ridotto.py", ".agents/script/yaml_ridotto.py"),
    ("skills/pianifica-periodo/scripts/controlla-periodo.py", ".agents/hooks/controlla-periodo.py"),
    ("skills/pianifica-periodo/scripts/todo.schema.json", ".agents/hooks/todo.schema.json"),
    ("skills/pianifica-periodo/scripts/idee.schema.json", ".agents/hooks/idee.schema.json"),
    ("skills/pannello/scripts/ferma.py", ".agents/hooks/ferma.py"),
    ("skills/pannello/scripts/pannello.py", ".agents/script/pannello.py"),
    ("skills/pannello/scripts/pagina.html", ".agents/script/pagina.html"),
]

# Copiati così come sono: il formato del file non ammette una riga in più.
COPIE_TALI = [
    ("skills/pannello/modello/launch.json", ".claude/launch.json"),
]

# I collegamenti: Claude Code cerca skill e regole in .claude/, Codex in .agents/.
COLLEGAMENTI = [
    (".claude/skills", "../.agents/skills"),
    (".claude/rules", "../.agents/regole"),
]

SEGNAPOSTO = ".tienimi"
ADATTATORI_HOOK = [".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json"]
FILE_JSON = [".agents/hooks.json", ".claude/settings.json", ".codex/hooks.json", ".claude/launch.json",
             "periodo/todo.json", "periodo/idee.json"]
CARTELLE_PROTETTE = (".agents/", ".codex/", ".claude/")
POLICY = ".agents/policy"
COSA_FARE_UTENTE = "apri il file e correggilo, o rimetti una copia buona"
COSA_FARE_PLUGIN = "cancellalo e rilancia lo script senza opzioni: lo ricrea"
COSA_FARE_HOOK = ("se nel file ci sono solo i controlli di redacy, cancellalo e rilancia lo script senza opzioni (lo ricrea); "
                  "se ci sono anche impostazioni dell'utente, correggilo (o rimetti una copia buona) e poi lancia lo stesso "
                  "script con --innesta")
COSA_FARE_JSON = {".agents/hooks.json": COSA_FARE_PLUGIN, ".claude/launch.json": COSA_FARE_PLUGIN,
                  ".claude/settings.json": COSA_FARE_HOOK, ".codex/hooks.json": COSA_FARE_HOOK}


# ---------------------------------------------------------------- Windows
# Su macOS e Linux niente di questo parte: si copia il modello com'è. Su Windows `python3` di solito non
# c'è (c'è `python` o `py -3`), PowerShell 5.1 non ha `&&` e i collegamenti simbolici chiedono privilegi:
# i file che nascono da qui portano il comando giusto per la macchina su cui gira questo script.

def su_windows():
    """Vero su Windows. Ogni ramo solo-Windows di questo file passa di qui (le prove lo forzano)."""
    return os.name == "nt"


def risponde_python3(nome, esito=None):
    """Vero se questo interprete (una lista: ["py", "-3"]) risponde da Python 3. Lo stub di Microsoft Store
    risponde con un errore: non vale. Con `esito` ogni interprete si prova una volta sola."""
    chiave = " ".join(nome)
    if esito is not None and chiave in esito.sonde:
        return esito.sonde[chiave]
    try:
        r = subprocess.run(nome + ["-c", "import sys; print(sys.version_info[0])"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        risponde = r.returncode == 0 and r.stdout.strip() == "3"
    except (OSError, subprocess.SubprocessError):
        risponde = False
    if esito is not None:
        esito.sonde[chiave] = risponde
    return risponde


def python_windows(esito=None):
    """Come una shell di Windows lancia questo stesso Python: `python`, `py -3` o `python3`.

    Il primo che risponde da Python 3 (lo stub di Microsoft Store risponde con un errore, e si scarta).
    Se nessuno risponde, restituisce `python` e mette un avviso."""
    if esito is not None and getattr(esito, "python", None):
        return esito.python
    trovato = None
    for nome in (["python"], ["py", "-3"], ["python3"]):
        if risponde_python3(nome, esito):
            trovato = " ".join(nome)
            break
    if trovato is None:
        trovato = "python"
        if esito is not None:
            esito.avvisi.append("non trovo `python` né `py -3` sul PATH: i comandi degli hook dicono `python`; "
                                "installa Python 3 e rilancia (o scrivi tu il nome giusto in .agents/hooks.json, "
                                ".claude/settings.json e .codex/hooks.json)")
    if esito is not None:
        esito.python = trovato
    return trovato


def comando_hook(python, script):
    """La riga di un hook che va bene in bash (Git Bash) e in PowerShell: niente `&&`, niente `[ ]`, niente
    variabili di shell. Se lo script non c'è non fa niente ed esce 0 (Python da solo, con un file mancante,
    esce 2 e bloccherebbe). Il `; exit $LASTEXITCODE` finale fa uscire PowerShell con il codice dello script
    (senza, un 2 diventa 1 e il messaggio non arriva al modello); in bash la variabile è vuota e non cambia niente."""
    return (python + " -c \"import os,runpy;f=os.path.join(os.environ.get('CLAUDE_PROJECT_DIR','.'),"
            "'.agents','hooks','" + script + "');os.path.isfile(f) and runpy.run_path(f,run_name='__main__')\""
            "; exit $LASTEXITCODE")


def adatta_hook_windows(testo, python):
    """Il JSON degli hook con ogni comando riscritto per Windows. Le altre chiavi restano come sono."""
    dati = json.loads(testo)

    def giro(nodo):
        if isinstance(nodo, dict):
            c = nodo.get("command")
            if isinstance(c, str):
                m = re.search(r"/\.agents/hooks/([A-Za-z0-9_.-]+\.py)", c)
                if m:
                    nodo["command"] = comando_hook(python, m.group(1))
            for v in nodo.values():
                giro(v)
        elif isinstance(nodo, list):
            for v in nodo:
                giro(v)

    giro(dati)
    return json.dumps(dati, indent=2, ensure_ascii=False) + "\n"


def adatta_launch_windows(testo, eseguibile):
    """launch.json lancia Python senza shell: su Windows serve il Python che c'è, non `python3`."""
    dati = json.loads(testo)
    for voce in dati.get("configurations", []) if isinstance(dati, dict) else []:
        if isinstance(voce, dict) and voce.get("runtimeExecutable") == "python3":
            voce["runtimeExecutable"] = eseguibile
    return json.dumps(dati, indent=2, ensure_ascii=False) + "\n"


def giunzione_windows(dest, bersaglio):
    """Un collegamento di cartella che non chiede privilegi (mklink /J). Vero se è riuscito."""
    try:
        r = subprocess.run(["cmd", "/c", "mklink", "/J", str(dest), str(bersaglio)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def scrivi_testo(p, testo):
    """Scrive un file di testo in UTF-8 con a capo `\\n` anche su Windows (`write_text` non ha `newline` prima di Python 3.10)."""
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)


def flussi_utf8():
    """Su Windows i flussi che non sono un terminale usano la tabella locale (cp1252): chi li legge vuole UTF-8."""
    for f in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if not f.isatty():
                f.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


def radice_plugin(da_argomento):
    if da_argomento:
        return Path(da_argomento).resolve()
    # scripts/ -> inizia/ -> skills/ -> radice del plugin
    return Path(__file__).resolve().parents[3]


def versione_plugin(radice):
    for manifesto in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        p = radice / manifesto
        try:
            v = json.loads(p.read_text(encoding="utf-8")).get("version")
            if v:
                return v
        except (OSError, ValueError):
            continue
    return "sconosciuta"


def elementi_modello(modello):
    """Le cartelle e i file del modello, in ordine, come percorsi relativi in stringa, sempre con `/`
    (su Windows `str(Path)` darebbe `\\`: le voci di creati/saltati/mancano devono dire lo stesso ovunque)."""
    cartelle, file = [], []
    for base, dirs, nomi in os.walk(modello):
        dirs.sort()
        rel_base = Path(base).relative_to(modello)
        if rel_base != Path("."):
            cartelle.append(rel_base.as_posix())
        for nome in sorted(nomi):
            if nome == SEGNAPOSTO or nome == ".DS_Store":
                continue
            file.append((rel_base / nome).as_posix())
    return cartelle, file


def con_testa(sorgente, origine, versione):
    """Il testo del file copiato, con versione e origine nelle prime righe."""
    testo = sorgente.read_text(encoding="utf-8")
    nota = f"redacy {versione} · copiato da {origine} nel plugin · non modificarlo qui: si rinfresca con crea-cartella.py --aggiorna"
    if sorgente.suffix == ".json":
        dati = json.loads(testo)
        if isinstance(dati, dict):
            vecchio = dati.get("$comment")
            commento = nota if not vecchio else f"{nota} · {vecchio}"
            dati = {"$comment": commento, **{k: v for k, v in dati.items() if k != "$comment"}}
            return json.dumps(dati, indent=2, ensure_ascii=False) + "\n"
        return testo
    if sorgente.suffix == ".html":
        righe = testo.splitlines(keepends=True)
        if righe and righe[0].lstrip().lower().startswith("<!doctype"):
            return righe[0] + f"<!-- {nota} -->\n" + "".join(righe[1:])
        return f"<!-- {nota} -->\n{testo}"
    if sorgente.suffix == ".md":
        return f"<!-- {nota} -->\n{testo}"
    righe = testo.splitlines(keepends=True)
    if righe and righe[0].startswith("#!"):
        return righe[0] + f"# {nota}\n" + "".join(righe[1:])
    return f"# {nota}\n{testo}"


RE_FORMA_BASH = re.compile(r'\[ ! -f "\$f" \] \|\| (?P<py>\S+) "\$f"')
RE_FORMA_WINDOWS = re.compile(r'^(?P<py>.+?) -c "import os,runpy;')
RE_TESTA_COSTITUZIONE = re.compile(rb"<!-- redacy (\S+) ")
RE_VERSIONE_COPIA = re.compile(r"redacy (\S+) · copiato da")
RE_IMPORT_AGENTS = re.compile(rb"(?m)^[ \t]*@AGENTS\.md\b")  # sui byte: la codifica del CLAUDE.md non conta
RE_SCRIPT = re.compile(r"([A-Za-z0-9_-]+\.py)")
SUFFISSO_COPIA = ".prima-di-redacy"


def voci_plugin(radice, esito=None):
    """Le voci degli hook del plugin (come finiscono nella cartella su questa macchina), dal modello."""
    testo = (radice / "skills/inizia/modello/.agents/hooks.json").read_text(encoding="utf-8")
    if su_windows():
        testo = adatta_hook_windows(testo, python_windows(esito))
    return json.loads(testo).get("hooks", {})


def chiavi_gruppo(gruppo):
    """I nomi degli script (ferma.py, controlla-periodo.py) che un gruppo di hook lancia."""
    chiavi = set()
    for h in gruppo.get("hooks", []) if isinstance(gruppo, dict) else []:
        c = h.get("command") if isinstance(h, dict) else None
        if isinstance(c, str):
            chiavi.update(RE_SCRIPT.findall(c))
    return chiavi


def gruppi_mancanti(hooks, voci):
    """I gruppi del plugin che `hooks` (il campo hooks di un file) non ha ancora, come (evento, gruppo)."""
    mancanti = []
    for evento, gruppi in voci.items():
        presenti = hooks.get(evento, []) if isinstance(hooks, dict) else []
        for g in gruppi:
            k = chiavi_gruppo(g)
            if not any(isinstance(x, dict) and k <= chiavi_gruppo(x) for x in presenti if isinstance(presenti, list)):
                mancanti.append((evento, g))
    return mancanti


def solo_del_plugin(hooks, voci):
    """Dal campo hooks di un file, solo i gruppi che lanciano gli script del plugin (per confrontare i tre file)."""
    chiavi = set().union(*[chiavi_gruppo(g) for gs in voci.values() for g in gs]) if voci else set()
    out = {}
    for evento, gruppi in (hooks or {}).items():
        if isinstance(gruppi, list):
            mio = [g for g in gruppi if chiavi_gruppo(g) and chiavi_gruppo(g) <= chiavi]
            if mio:
                out[evento] = mio
    return out


def forma_del_comando(comando):
    """Per quale sistema è scritto il comando di un hook del plugin: ("bash", interprete), ("windows", interprete)
    o None se non è nessuna delle due forme (un comando che l'utente ha scritto a modo suo: non si tocca)."""
    m = RE_FORMA_BASH.search(comando)
    if m:
        return "bash", m.group("py")
    m = RE_FORMA_WINDOWS.match(comando)
    if m:
        return "windows", m.group("py")
    return None


def comandi_di_oggi(voci):
    """I comandi dei gruppi del plugin come vanno su questo computer: {nome dello script: comando}."""
    oggi = {}
    for gs in voci.values():
        for g in gs:
            for h in g.get("hooks", []):
                nomi = set(RE_SCRIPT.findall(h.get("command", "")))
                if len(nomi) == 1:
                    oggi[nomi.pop()] = h["command"]
    return oggi


def comandi_da_riscrivere(dati, voci, esito=None):
    """I comandi dei gruppi del plugin in `dati` (il JSON di un file degli hook) che non vanno su questo computer:
    [(gruppo, hook, nome dello script, forma in due parole)].

    Su macOS e Linux vanno quelli nella forma del modello (bash con python3). Su Windows quelli nella forma di
    comando_hook() il cui interprete (`python`, `py -3`...) risponde da Python 3 su questo computer, anche se
    python_windows() ne sceglierebbe un altro: riscriverli in Codex vuol dire riapprovare gli hook."""
    hooks = dati.get("hooks") if isinstance(dati, dict) else None
    if not isinstance(hooks, dict):
        return []
    chiavi_plugin = set().union(*[chiavi_gruppo(g) for gs in voci.values() for g in gs]) if voci else set()
    oggi = comandi_di_oggi(voci)
    trovati = []
    for gruppi in hooks.values():
        for g in gruppi if isinstance(gruppi, list) else []:
            k = chiavi_gruppo(g)
            if not k or not k <= chiavi_plugin or not isinstance(g.get("hooks"), list):
                continue
            for h in g["hooks"]:
                c = h.get("command") if isinstance(h, dict) else None
                forma = forma_del_comando(c) if isinstance(c, str) else None
                nomi = set(RE_SCRIPT.findall(c)) if forma else set()
                if forma is None or len(nomi) != 1:
                    continue
                nome = nomi.pop()
                sistema, py = forma
                if su_windows():
                    se_no = (f"bash con {py}" if sistema == "bash" else
                             None if risponde_python3(py.split(), esito) else f"Windows con {py}, che qui non risponde")
                else:
                    se_no = f"Windows con {py}" if sistema == "windows" else None
                if se_no and oggi.get(nome, c) != c:  # se il comando di oggi è lo stesso, riscriverlo non serve a niente
                    trovati.append((g, h, nome, se_no))
    return trovati


def aggiorna_hook(cartella, radice, esito):
    """Riscrive SOLO i `command` dei gruppi del plugin (e il loro `matcher`) nella forma di questo computer, nei file
    degli hook che li hanno scritti per un altro. Il resto del file resta com'è; se c'è altro oltre ai gruppi del
    plugin, prima salva una copia. Passa da scrivi(): in Codex .agents/ e .codex/ sono protette."""
    voci = voci_plugin(radice, esito)
    oggi = comandi_di_oggi(voci)
    matcher = {frozenset(chiavi_gruppo(g)): g["matcher"] for gs in voci.values() for g in gs if "matcher" in g}
    chiavi_plugin = set().union(*[chiavi_gruppo(g) for gs in voci.values() for g in gs]) if voci else set()
    for rel in ADATTATORI_HOOK:
        p = cartella / rel
        if not p.is_file():
            continue
        try:
            dati = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        trovati = comandi_da_riscrivere(dati, voci, esito)
        if not trovati:
            continue
        for g, h, nome, _ in trovati:
            h["command"] = oggi[nome]
            if frozenset(chiavi_gruppo(g)) in matcher:  # una cartella di prima di PowerShell ha il matcher vecchio
                g["matcher"] = matcher[frozenset(chiavi_gruppo(g))]
        solo_plugin = set(dati) <= {"hooks", "description"} and all(
            isinstance(gs, list) and all(chiavi_gruppo(g) and chiavi_gruppo(g) <= chiavi_plugin for g in gs)
            for gs in dati["hooks"].values())
        def azione(p=p, dati=dati, copia=not solo_plugin):
            if copia:
                copia_di_sicurezza(p)
            scrivi_testo(p, json.dumps(dati, indent=2, ensure_ascii=False) + "\n")
        if scrivi(esito, rel, azione):
            esito.aggiornati.append(f"{rel} (controlli riscritti per questo computer)")


def problemi_innesto(cartella, radice, esito=None):
    """Ciò che c'era già nella cartella e non è collegato a redacy: [(file, cosa manca, spiegazione)].

    Il CLAUDE.md che non importa AGENTS.md, e i file degli hook che non hanno i controlli del plugin.
    Un file degli hook che non è JSON ("json") o non ha la forma giusta ("forma") non si può innestare:
    ma si dice, senza che i controlli non partano in silenzio."""
    trovati = []
    claude = cartella / "CLAUDE.md"
    if claude.is_file():
        try:
            grezzo = claude.read_bytes()
        except OSError:
            grezzo = None
        agents = cartella / "AGENTS.md"
        stesso = claude.is_symlink() and agents.exists() and claude.resolve() == agents.resolve()
        if grezzo is not None and grezzo.startswith(b"\xef\xbb\xbf"):
            grezzo = grezzo[3:]
        if grezzo is not None and not stesso and not RE_IMPORT_AGENTS.search(grezzo):
            trovati.append(("CLAUDE.md", "import",
                            "non importa AGENTS.md: Claude Code non legge le regole dello studio"))
    voci = voci_plugin(radice, esito)
    for rel in ADATTATORI_HOOK:
        p = cartella / rel
        if not p.is_file():
            continue
        try:
            dati = json.loads(p.read_text(encoding="utf-8-sig"))
        except OSError:
            continue
        except ValueError as e:
            trovati.append((rel, "json", f"non è JSON valido ({e})"))
            continue
        if not isinstance(dati, dict):
            trovati.append((rel, "forma", "non ha la forma giusta (non è un oggetto { … })"))
            continue
        hooks = dati.get("hooks", {})
        if not isinstance(hooks, dict):
            trovati.append((rel, "forma", "non ha la forma giusta (il campo hooks non è un oggetto { … })"))
            continue
        mancanti = gruppi_mancanti(hooks, voci)
        if mancanti:
            nomi = sorted(set().union(*[chiavi_gruppo(g) for _, g in mancanti]))
            trovati.append((rel, "hook", "non ha i controlli di redacy (" + ", ".join(nomi) + "): "
                            "lo stop dal pannello e il controllo delle cose da fare non partono"))
    return trovati


def copia_di_sicurezza(p):
    """Salva una copia accanto al file (.prima-di-redacy, poi -2, -3...), senza mai sovrascriverne una."""
    n, dest = 1, Path(str(p) + SUFFISSO_COPIA)
    while os.path.lexists(dest):
        n += 1
        dest = Path(f"{p}{SUFFISSO_COPIA}-{n}")
    shutil.copy2(p, dest)
    return dest


def innesta(cartella, radice, esito):
    """Sistema ciò che problemi_innesto() trova, senza togliere né riordinare niente di ciò che c'è."""
    fatti = 0
    voci = voci_plugin(radice, esito)
    for rel, tipo, spiega in problemi_innesto(cartella, radice, esito):
        p = cartella / rel
        if tipo in ("json", "forma"):
            esito.non_sistemati.append(f"{rel} {spiega}: {COSA_FARE_HOOK}")
            continue
        def azione(p=p, tipo=tipo):
            copia = copia_di_sicurezza(p)
            if tipo == "import":
                grezzo = p.read_bytes()
                eol = b"\r\n" if b"\r\n" in grezzo else b"\n"
                prefisso = b"" if not grezzo or grezzo.endswith(b"\n") else eol
                with p.open("ab") as f:
                    f.write(prefisso + eol + b"@AGENTS.md" + eol)
            else:
                dati = json.loads(p.read_text(encoding="utf-8-sig"))
                hooks = dati.setdefault("hooks", {})
                for evento, g in gruppi_mancanti(hooks, voci):
                    if not isinstance(hooks.get(evento), list):
                        hooks[evento] = []
                    hooks[evento].append(copy.deepcopy(g))
                scrivi_testo(p, json.dumps(dati, indent=2, ensure_ascii=False) + "\n")
            return copia
        try:
            copia = azione()
        except OSError as e:
            esito.non_scritti.append(f"{rel} ({e.strerror or e})")
            continue
        esito.creati.append(f"{rel} (copia di prima: {copia.name})")
        fatti += 1
    return fatti


def versione_della_copia(p):
    """La versione scritta nelle prime righe di una copia del plugin, o None."""
    try:
        testo = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    m = RE_VERSIONE_COPIA.search(testo[:2000])
    return m.group(1) if m else None


def copie_vecchie(cartella, radice, versione):
    """Le copie del plugin nella cartella con una versione diversa da quella del plugin: [(rel, versione)]."""
    vecchie = []
    for origine, rel in COPIE:
        p = cartella / rel
        if p.is_file() and (radice / origine).is_file():
            v = versione_della_copia(p)
            if v is not None and v != versione:
                vecchie.append((rel, v))
    return vecchie


def copie_diverse(cartella, radice, versione):
    """Le copie del plugin con la versione di oggi (o senza più la testa) ma un contenuto diverso da quello che il plugin
    darebbe adesso: rovinate (un file troncato) o cambiate a mano. [rel]"""
    diverse = []
    for origine, rel in COPIE:
        p, sorgente = cartella / rel, radice / origine
        if not (p.is_file() and sorgente.is_file()):
            continue
        if versione_della_copia(p) not in (None, versione):
            continue  # è di un'altra versione: la dice copie_vecchie()
        try:
            if p.read_text(encoding="utf-8") != con_testa(sorgente, origine, versione):
                diverse.append(rel)
        except (OSError, ValueError):
            diverse.append(rel)  # non si legge come UTF-8: rovinata
    return diverse


def aggiorna(cartella, radice, versione, esito):
    """Rinfresca solo le copie del plugin (tabella COPIE) che differiscono da ciò che il plugin darebbe oggi."""
    uguali = 0
    for origine, rel in COPIE:
        sorgente = radice / origine
        dest = cartella / rel
        if not sorgente.is_file():
            esito.avvisi.append(f"{rel}: manca la sorgente {origine} nel plugin, non toccato")
            continue
        atteso = con_testa(sorgente, origine, versione)
        esiste = os.path.lexists(dest)
        if esiste:
            try:
                if dest.read_text(encoding="utf-8") == atteso:
                    uguali += 1
                    continue
            except (OSError, UnicodeDecodeError):
                pass
        def scrivi_copia(d=dest, s=sorgente):
            d.parent.mkdir(parents=True, exist_ok=True)
            scrivi_testo(d, atteso)
            shutil.copymode(s, d)
        if scrivi(esito, rel, scrivi_copia):
            (esito.aggiornati if esiste else esito.creati).append(rel)
    return uguali


# ---------------------------------------------------------------- C3: la costituzione (AGENTS.md)
# È uguale in ogni studio: una correzione del plugin deve arrivare anche a chi ha già la cartella.

def stato_costituzione(cartella, radice):
    """L'AGENTS.md della cartella rispetto a quello che il plugin porta oggi.

    None se non c'è, se è un collegamento o se non è nostro (la prima riga non comincia con `<!-- redacy `).
    Se no (stato, versione scritta in testa, versione del plugin): stato è "uguale", "vecchia" (la versione in
    testa è diversa) o "a-mano" (stessa versione ma contenuto diverso: cambiato a mano o rovinato).
    Gli a capo di Windows e il BOM non contano come differenza."""
    mio, modello = cartella / "AGENTS.md", radice / "skills/inizia/modello/AGENTS.md"
    if mio.is_symlink() or not mio.is_file() or not modello.is_file():
        return None
    try:
        ora, nuovo = mio.read_bytes(), modello.read_bytes()
    except OSError:
        return None
    ora, nuovo = [b[3:] if b.startswith(b"\xef\xbb\xbf") else b for b in (ora, nuovo)]
    if not ora.startswith(b"<!-- redacy "):
        return None
    ora, nuovo = ora.replace(b"\r\n", b"\n"), nuovo.replace(b"\r\n", b"\n")
    testa_mia, testa_nuova = RE_TESTA_COSTITUZIONE.match(ora), RE_TESTA_COSTITUZIONE.match(nuovo)
    v_mia = testa_mia.group(1).decode("ascii", "replace") if testa_mia else "sconosciuta"
    v_plugin = testa_nuova.group(1).decode("ascii", "replace") if testa_nuova else versione_plugin(radice)
    if ora == nuovo:
        return "uguale", v_mia, v_plugin
    return ("vecchia" if v_mia != v_plugin else "a-mano"), v_mia, v_plugin


def controlla_costituzione(cartella, radice, esito):
    """--controlla: un `avviso:` se AGENTS.md è di un'altra versione di redacy, o se è cambiato a mano o rovinato."""
    stato = stato_costituzione(cartella, radice)
    if stato is None or stato[0] == "uguale":
        return
    if stato[0] == "vecchia":
        esito.avvisi.append(f"AGENTS.md è di redacy {stato[1]} e il plugin porta la {stato[2]}: lancia lo stesso script "
                            "con --aggiorna (tiene una copia di prima)")
    else:
        esito.avvisi.append(f"AGENTS.md è diverso da quello di redacy {stato[2]} (cambiato a mano o rovinato): "
                            "se non l'hai cambiato tu, cancellalo e rilancia lo script senza opzioni: lo ricrea")


def aggiorna_costituzione(cartella, radice, esito):
    """--aggiorna: porta il nuovo AGENTS.md (prima salva copia_di_sicurezza) se quello della cartella è di una versione
    diversa; se ha la stessa versione ma un contenuto diverso non lo tocca e lo dice. Se non è nostro, non fa e non dice niente."""
    stato = stato_costituzione(cartella, radice)
    if stato is None or stato[0] == "uguale":
        return
    if stato[0] == "a-mano":
        esito.avvisi.append("AGENTS.md è stato cambiato a mano: non lo tocco")
        return
    nome_copia = []
    def azione():
        nome_copia.append(copia_di_sicurezza(cartella / "AGENTS.md").name)
        shutil.copyfile(radice / "skills/inizia/modello/AGENTS.md", cartella / "AGENTS.md")
    if scrivi(esito, "AGENTS.md", azione):
        esito.aggiornati.append(f"AGENTS.md (copia di prima: {nome_copia[0]})")


class Esito:
    def __init__(self):
        self.creati, self.saltati, self.avvisi, self.mancano, self.non_va = [], [], [], [], []
        self.non_scritti = []
        self.aggiornati = []
        self.non_sistemati = []
        self.python = None
        self.sonde = {}


def scrivi(esito, rel, azione):
    """Esegue una scrittura; un permesso negato (la sandbox di Codex tiene .agents/ e .codex/
    in sola lettura) non ferma lo script: la voce va fra i non scritti."""
    try:
        azione()
        return True
    except OSError as e:
        esito.non_scritti.append(f"{rel} ({e.strerror or e})")
        return False


def crea(cartella, radice, versione, esito):
    modello = radice / "skills/inizia/modello"
    cartelle, file = elementi_modello(modello)
    for rel in cartelle:
        dest = cartella / rel
        if not dest.exists():
            if scrivi(esito, f"{rel}/", lambda d=dest: d.mkdir(parents=True, exist_ok=True)):
                esito.creati.append(f"{rel}/")
    for rel in file:
        dest = cartella / rel
        if os.path.lexists(dest):
            esito.saltati.append(rel)
            continue
        def copia(d=dest, s=modello / rel, r=rel):
            d.parent.mkdir(parents=True, exist_ok=True)
            if su_windows() and r in ADATTATORI_HOOK:
                scrivi_testo(d, adatta_hook_windows(s.read_text(encoding="utf-8"), python_windows(esito)))
            else:
                shutil.copyfile(s, d)
            shutil.copymode(s, d)
        if scrivi(esito, rel, copia):
            esito.creati.append(rel)
    for rel, bersaglio in COLLEGAMENTI:
        dest = cartella / rel
        if os.path.lexists(dest):
            esito.saltati.append(rel)
            continue
        try:
            os.symlink(bersaglio, dest, target_is_directory=True)
            esito.creati.append(f"{rel} -> {bersaglio}")
        except OSError as e:
            if su_windows() and giunzione_windows(dest, (dest.parent / bersaglio).resolve()):
                esito.creati.append(f"{rel} -> {bersaglio} (giunzione)")
            elif isinstance(e, PermissionError):
                esito.non_scritti.append(f"{rel} ({e.strerror or e})")
            else:
                esito.avvisi.append(f"{rel}: collegamento non creato ({e}); Claude non vedrà {bersaglio[3:]}")
    for origine, rel in COPIE + COPIE_TALI:
        sorgente = radice / origine
        dest = cartella / rel
        if not sorgente.is_file():
            esito.avvisi.append(f"{rel}: manca la sorgente {origine} nel plugin, non copiato")
            continue
        if os.path.lexists(dest):
            esito.saltati.append(rel)
            continue
        tale = (origine, rel) in COPIE_TALI
        def copia(d=dest, s=sorgente, o=origine, t=tale):
            d.parent.mkdir(parents=True, exist_ok=True)
            if t and su_windows():
                scrivi_testo(d, adatta_launch_windows(s.read_text(encoding="utf-8"), sys.executable or "python"))
            elif t:
                shutil.copyfile(s, d)
            else:
                scrivi_testo(d, con_testa(s, o, versione))
                shutil.copymode(s, d)
        if scrivi(esito, rel, copia):
            esito.creati.append(rel)
    for rel, tipo, spiega in problemi_innesto(cartella, radice, esito):
        if tipo in ("json", "forma"):
            esito.avvisi.append(f"{rel} c'era già e {spiega}: i controlli di redacy non partono e --innesta non lo "
                                f"può sistemare. Dillo all'utente: {COSA_FARE_HOOK}")
            continue
        esito.avvisi.append(f"{rel} c'era già e {spiega}. Dillo all'utente e, dopo il suo sì, "
                            "lancia lo stesso script con --innesta")
    log = cartella / "memoria/LOG.md"
    if esito.creati and log.is_file():
        quando = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        file_creati = [c for c in esito.creati if not c.endswith("/")]
        riga = (f"- {quando} · inizia · cartella preparata con redacy {versione}: "
                f"{len(file_creati)} file e collegamenti creati, {len(esito.saltati)} già presenti")
        if esito.non_scritti:
            riga += f", {len(esito.non_scritti)} da finire con una riga nel terminale"
        riga += "\n"
        def aggiungi():
            testo = log.read_text(encoding="utf-8")
            with log.open("a", encoding="utf-8", newline="\n") as f:
                if testo and not testo.endswith("\n"):
                    f.write("\n")
                f.write(riga)
        scrivi(esito, "memoria/LOG.md", aggiungi)


def controlla(cartella, radice, esito):
    modello = radice / "skills/inizia/modello"
    cartelle, file = elementi_modello(modello)
    for rel in cartelle:
        if not (cartella / rel).is_dir():
            esito.mancano.append(f"{rel}/")
    for rel in file:
        if not os.path.lexists(cartella / rel):
            esito.mancano.append(rel)
    for rel, bersaglio in COLLEGAMENTI:
        if not os.path.lexists(cartella / rel):
            esito.mancano.append(f"{rel} -> {bersaglio}")
    for origine, rel in COPIE + COPIE_TALI:
        if not os.path.lexists(cartella / rel):
            if (radice / origine).is_file():
                esito.mancano.append(rel)
            else:
                esito.avvisi.append(f"{rel}: manca anche la sorgente {origine} nel plugin")
    for rel in FILE_JSON:
        p = cartella / rel
        if p.is_file():
            try:
                json.loads(p.read_text(encoding="utf-8-sig"))
            except ValueError as e:
                esito.non_va.append(f"{rel}: JSON non valido ({e}): {COSA_FARE_JSON.get(rel, COSA_FARE_UTENTE)}")
    voci_p = voci_plugin(radice, esito)
    for rel in ADATTATORI_HOOK:
        p = cartella / rel
        try:
            altro = comandi_da_riscrivere(json.loads(p.read_text(encoding="utf-8-sig")), voci_p, esito)
        except (OSError, ValueError):
            continue
        if altro:
            esito.avvisi.append(f"{rel}: i controlli automatici sono scritti per un altro computer ({altro[0][3]}): "
                                "lancia lo stesso script con --aggiorna")
    for rel, tipo, spiega in problemi_innesto(cartella, radice, esito):
        if tipo == "json":  # già detto qui sopra
            continue
        if tipo == "forma":
            esito.non_va.append(f"{rel} {spiega}: {COSA_FARE_HOOK}")
            continue
        esito.non_va.append(f"{rel} {spiega}: con il sì dell'utente, --innesta lo sistema")
    nostre = {}
    for rel in ADATTATORI_HOOK:
        p = cartella / rel
        if p.is_file():
            try:
                hooks = json.loads(p.read_text(encoding="utf-8-sig")).get("hooks")
            except (ValueError, AttributeError):
                continue
            if isinstance(hooks, dict) and not gruppi_mancanti(hooks, voci_p):
                nostre[rel] = solo_del_plugin(hooks, voci_p)
    if len(set(json.dumps(v, sort_keys=True) for v in nostre.values())) > 1:
        esito.non_va.append("le voci degli hook non sono uguali in " + ", ".join(sorted(nostre)))
    vecchie = copie_vecchie(cartella, radice, versione_plugin(radice))
    if vecchie:
        esito.avvisi.append(f"{len(vecchie)} copie del plugin in .agents/ sono di redacy {vecchie[0][1]} e il plugin è "
                            f"{versione_plugin(radice)}: lancia lo stesso script con --aggiorna")
    for rel in copie_diverse(cartella, radice, versione_plugin(radice)):
        esito.avvisi.append(f"{rel} è diverso dall'originale del plugin (rovinato o cambiato a mano): "
                            "lancia lo stesso script con --aggiorna")
    controlla_costituzione(cartella, radice, esito)
    policy = cartella / POLICY
    if policy.is_dir():
        for p in sorted(policy.glob("*.md")):
            for n, riga in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if riga.lstrip().startswith("|"):
                    esito.non_va.append(f"{POLICY}/{p.name}:{n}: una tabella; le policy sono elenchi di righe")
                    break


def cartella_di(voce):
    """La cartella (la prima del percorso) di una voce di non_scritti come «.agents/script/corsa.py (Permission denied)»."""
    rel = voce.split(" (")[0].replace("\\", "/")
    parti = rel.split("/")
    return parti[0] + "/" if len(parti) > 1 else "la cartella dello studio"


def stampa(esito, cartella, solo_controllo, solo_innesto=False, uguali=None):
    opzione = " --innesta" if solo_innesto else (" --aggiorna" if uguali is not None else "")
    print(f"cartella: {cartella}")
    if solo_controllo:
        for r in esito.mancano:
            print(f"manca: {r}")
        for r in esito.non_va:
            print(f"non va: {r}")
        for r in esito.avvisi:
            print(f"avviso: {r}")
        if esito.mancano or esito.non_va:
            print(f"esito: mancano {len(esito.mancano)}, non vanno {len(esito.non_va)}")
        else:
            print("esito: non manca niente")
        return
    for r in esito.creati:
        print(f"{'innestato' if solo_innesto else 'creato'}: {r}")
    for r in esito.aggiornati:
        print(f"aggiornato: {r}")
    for r in esito.saltati:
        print(f"saltato (c'è già): {r}")
    for r in esito.avvisi:
        print(f"avviso: {r}")
    for r in esito.non_scritti:
        print(f"non scritto: {r}")
    for r in esito.non_sistemati:
        print(f"non sistemato: {r}")
    if solo_innesto:
        resto = f", {len(esito.non_scritti)} non scritti" if esito.non_scritti else ""
        resto += f", {len(esito.non_sistemati)} da sistemare a mano" if esito.non_sistemati else ""
        print(f"esito: {len(esito.creati)} innestati{resto}")
    elif uguali is not None:
        resto = f", {len(esito.non_scritti)} non scritti" if esito.non_scritti else ""
        print(f"esito: {len(esito.aggiornati)} aggiornati, {len(esito.creati)} ricreati, {uguali} già uguali, "
              f"{len(esito.avvisi)} avvisi{resto}")
    else:
        print(f"esito: {len(esito.creati)} creati, {len(esito.saltati)} saltati, {len(esito.avvisi)} avvisi"
              + (f", {len(esito.non_scritti)} non scritti" if esito.non_scritti else ""))
    altre = sorted({cartella_di(r) for r in esito.non_scritti if cartella_di(r) not in CARTELLE_PROTETTE})
    if altre:  # una cartella che non è fra quelle protette di Codex: la riga `comando:` rifallirebbe uguale
        print("da finire: non riesco a scrivere in " + ", ".join(altre) + ": controlla i permessi di "
              + ("quella cartella" if len(altre) == 1 else "quelle cartelle")
              + " (o che il file non sia aperto in un altro programma) e rilancia lo stesso script.")
    if any(cartella_di(r) in CARTELLE_PROTETTE for r in esito.non_scritti):
        print("da finire: questa sessione non può scrivere alcune cartelle (in Codex .agents/ e .codex/ "
              "sono protette). Lancia una volta questa riga nel terminale, fuori da Codex:")
        if su_windows():  # PowerShell e cmd: virgolette doppie, niente shlex, niente &&
            print(f'comando: {python_windows(esito)} "{Path(__file__).resolve()}" "{cartella}"{opzione}')
        else:
            print(f"comando: python3 {shlex.quote(str(Path(__file__).resolve()))} {shlex.quote(str(cartella))}{opzione}")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Crea la cartella dello studio dal modello del plugin redacy.")
    ap.add_argument("cartella", help="la cartella dello studio (si crea se non c'è)")
    gr = ap.add_mutually_exclusive_group()
    gr.add_argument("--controlla", action="store_true", help="dice cosa manca o non va, senza scrivere")
    gr.add_argument("--innesta", action="store_true",
                    help="dopo il sì dell'utente: @AGENTS.md nel CLAUDE.md che c'è già e i controlli di redacy nei "
                         "file degli hook che c'erano già (prima salva una copia .prima-di-redacy)")
    gr.add_argument("--aggiorna", action="store_true",
                    help="rinfresca le copie del plugin (script, controlli, schemi, pagina) se sono diverse da quelle del plugin")
    ap.add_argument("--plugin", help="la radice del plugin (di solito si trova da sola)")
    a = ap.parse_args(argv)

    radice = radice_plugin(a.plugin)
    if not (radice / "skills/inizia/modello").is_dir():
        print(f"errore: non trovo il modello in {radice}/skills/inizia/modello", file=sys.stderr)
        return 2
    if not a.cartella.strip():
        print("errore: la cartella è vuota: dimmi quale (con una variabile di shell non impostata succede così)",
              file=sys.stderr)
        return 2
    cartella = Path(a.cartella).expanduser().resolve()
    if cartella.exists() and not cartella.is_dir():
        print(f"errore: {cartella} non è una cartella", file=sys.stderr)
        return 2
    esito = Esito()
    if a.controlla:
        if not cartella.is_dir():
            print(f"cartella: {cartella}\nmanca: la cartella stessa\nesito: mancano 1, non vanno 0")
            return 1
        controlla(cartella, radice, esito)
        stampa(esito, cartella, True)
        return 1 if (esito.mancano or esito.non_va) else 0
    if (a.innesta or a.aggiorna) and not cartella.is_dir():
        print(f"errore: {cartella} non c'è: prima si prepara la cartella, senza opzioni", file=sys.stderr)
        return 2
    if a.innesta:
        innesta(cartella, radice, esito)
        stampa(esito, cartella, False, solo_innesto=True)
        return 3 if esito.non_scritti else (1 if esito.non_sistemati else 0)
    if a.aggiorna:
        uguali = aggiorna(cartella, radice, versione_plugin(radice), esito)
        aggiorna_hook(cartella, radice, esito)
        aggiorna_costituzione(cartella, radice, esito)
        stampa(esito, cartella, False, uguali=uguali)
        return 3 if esito.non_scritti else 0
    try:
        cartella.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        print(f"errore: non posso creare {cartella} ({e})", file=sys.stderr)
        return 2
    crea(cartella, radice, versione_plugin(radice), esito)
    stampa(esito, cartella, False)
    return 3 if esito.non_scritti else 0


if __name__ == "__main__":
    flussi_utf8()
    sys.exit(main())
