#!/usr/bin/env python3
# redacy 0.4.2 · prove/ci/catena.py
"""La catena del plugin senza modello, uguale su Linux, macOS e Windows.

Parte dal plugin INSTALLATO (la cartella che Claude Code o Codex hanno messo nella loro cache) e fa quello
che l'agente lancerebbe a un primo avvio, in una cartella nuova con spazi e un accento nel nome:

  1. crea la cartella dello studio (crea-cartella.py) e la controlla
  2. mette dati finti e un grafo, e il controllo del grafo passa
  3. una corsa scritta passo per passo, poi chiusa
  4. il pannello si accende su 127.0.0.1 e risponde, e un secondo avvio riusa il primo
  5. lo stop dalla pagina ferma una corsa (il comando dopo lo stop esce 3)
  6. gli hook, come li lancia l'harness (le righe di .claude/settings.json e .codex/hooks.json),
     con un ingresso di prova: ferma.py nega, controlla-periodo.py segnala un file rotto
  7. il pannello si spegne e la porta è chiusa

Uso: python catena.py --plugin <radice del plugin installato> --base <cartella di lavoro> [--nome claude|codex]
Esce 0 solo se ogni passo PASSA. Ogni passo stampa una riga PASSA o FALLISCE, e la tabella va anche in
$GITHUB_STEP_SUMMARY. Solo libreria standard.
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
CHECKOUT = os.path.normpath(os.path.join(QUI, "..", ".."))
RISULTATI = []
STATO = {}


def passo(nome):
    def deco(f):
        def corri():
            da = time.time()
            try:
                dettaglio = f() or ""
                RISULTATI.append((nome, "PASSA", str(dettaglio)))
                print("PASSA      %-52s %5.1fs  %s" % (nome, time.time() - da, dettaglio), flush=True)
            except Exception as e:  # un passo rosso non ferma gli altri: una corsa mostra tutti i difetti
                msg = (type(e).__name__ + ": " + str(e)).replace("\n", " | ")
                RISULTATI.append((nome, "FALLISCE", msg))
                print("FALLISCE   %-52s %5.1fs  %s" % (nome, time.time() - da, msg), flush=True)
        corri.nome = nome
        PASSI.append(corri)
        return corri
    return deco


PASSI = []


def esegui(args, cwd=None, env=None, ingresso=None, timeout=120):
    e = dict(os.environ)
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    e["PYTHONUTF8"] = "1"
    if env:
        e.update(env)
    return subprocess.run(args, cwd=cwd, env=e, input=ingresso, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def py(*args, **kw):
    return esegui([sys.executable] + [str(a) for a in args], **kw)


def deve(cond, msg):
    if not cond:
        raise AssertionError(msg)


def http(url, metodo="GET", corpo=None, intestazioni=None):
    req = urllib.request.Request(url, data=corpo, method=metodo, headers=intestazioni or {})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def porta_aperta(porta):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect(("127.0.0.1", porta))
        return True
    except OSError:
        return False
    finally:
        s.close()


def info_pannello():
    with open(os.path.join(STATO["D"], "interfaccia", "pannello.json"), encoding="utf-8") as f:
        return json.load(f)


def corsa_json(id_corsa):
    with open(os.path.join(STATO["D"], "grafi", "corse", id_corsa + ".json"), encoding="utf-8") as f:
        return json.load(f)


def script(nome):
    return os.path.join(STATO["D"], ".agents", "script", nome)


# ------------------------------------------------------------------------------------------ i passi

@passo("0 ambiente: python, git, i file del plugin installato")
def ambiente():
    P = STATO["P"]
    for rel in ("skills/inizia/scripts/crea-cartella.py", "skills/pannello/scripts/pannello.py",
                "skills/crea-grafo/scripts/corsa.py", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        deve(os.path.isfile(os.path.join(P, rel)), "nel plugin installato manca " + rel)
    cfg = []
    for k in ("core.autocrlf", "core.symlinks"):
        r = esegui(["git", "config", "--get", k])
        cfg.append("%s=%s" % (k, r.stdout.strip() or "-"))
    versione = json.load(open(os.path.join(P, ".claude-plugin", "plugin.json"), encoding="utf-8"))["version"]
    STATO["versione"] = versione
    return "python %s su %s, plugin %s, %s, radice %s" % (sys.version.split()[0], sys.platform, versione, " ".join(cfg), P)


@passo("1 inizia: crea la cartella (spazi e accento) e la controlla")
def cartella():
    D = os.path.join(STATO["B"], "Studio Ferrante è così")
    STATO["D"] = D
    os.makedirs(D, exist_ok=True)
    crea = os.path.join(STATO["P"], "skills", "inizia", "scripts", "crea-cartella.py")
    r = py(crea, D, "--plugin", STATO["P"])
    deve(r.returncode == 0, "crea-cartella.py esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-400:]))
    r = py(crea, D, "--controlla", "--plugin", STATO["P"])
    deve(r.returncode == 0, "--controlla esce %s: %s" % (r.returncode, (r.stdout + r.stderr)[-400:]))
    for rel in ("AGENTS.md", "CLAUDE.md", "memoria/INDICE.md", "periodo/todo.json", ".agents/hooks.json",
                ".claude/settings.json", ".codex/hooks.json", ".agents/script/corsa.py",
                ".agents/script/pannello.py", ".agents/hooks/ferma.py", ".agents/hooks/controlla-periodo.py"):
        deve(os.path.isfile(os.path.join(D, *rel.split("/"))), "manca " + rel)
    for rel in (".agents/script/corsa.py", ".agents/hooks/ferma.py"):
        testa = open(os.path.join(D, *rel.split("/")), encoding="utf-8").read(400)
        deve("redacy " + STATO["versione"] in testa, rel + " non porta la versione in testa")
    avvisi = [r_ for r_ in r.stdout.splitlines() if r_.startswith("avviso")]
    return "albero completo, ogni copia con la versione" + (", avvisi: " + "; ".join(avvisi) if avvisi else "")


@passo("2 grafo: i dati finti, controlla-grafo.py passa")
def grafo():
    D = STATO["D"]
    prep = os.path.join(CHECKOUT, "prove", "pannello", "_prepara.py")
    r = py(prep, D, "--plugin", STATO["P"])
    deve(r.returncode == 0, "_prepara.py esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-400:]))
    g = os.path.join(D, "grafi", "giro-scadenze.yaml")
    deve(os.path.isfile(g), "manca grafi/giro-scadenze.yaml")
    r = py(script("controlla-grafo.py"), g, cwd=D)
    deve(r.returncode == 0, "controlla-grafo.py esce %s: %s" % (r.returncode, (r.stdout + r.stderr)[-400:]))
    lento = ("grafo: giro-lento\nversione: 1\nobiettivo: Cinque passi lenti, per provare lo stop dal pannello.\nacceso: false\n"
             "innesco: {tipo: parola}\npassi:\n" +
             "".join("  - id: passo-%d\n    tipo: agente\n    nome: Passo %d\n    workspace: orchestratore\n    prompt: Fai il passo %d\n" % (i, i, i)
                     for i in range(1, 6)) +
             "tetti:\n  contemporanee: 2\nuscite: []\nautonomia: {livello: L0, da: \"2026-11-07\", si: null}\n")
    with open(os.path.join(D, "grafi", "giro-lento.yaml"), "w", encoding="utf-8", newline="\n") as f:
        f.write(lento)
    r = py(script("controlla-grafo.py"), os.path.join(D, "grafi", "giro-lento.yaml"), cwd=D)
    deve(r.returncode == 0, "controlla-grafo.py su giro-lento esce %s: %s" % (r.returncode, (r.stdout + r.stderr)[-400:]))
    return "giro-scadenze e giro-lento validi"


@passo("3 corsa: tutti i passi scritti, poi chiusa")
def corsa():
    D = STATO["D"]
    r = py(script("corsa.py"), "apri", "giro-scadenze", "--avviato-da", "utente", cwd=D)
    deve(r.returncode == 0, "corsa.py apri esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-400:]))
    id_c = r.stdout.strip().splitlines()[-1]
    c = corsa_json(id_c)
    for p in c["passi"]:
        for az, extra in (("inizio", []), ("fatto", ["--esito", "prova " + p["id"]])):
            r = py(script("corsa.py"), "passo", id_c, p["id"], az, *extra, cwd=D)
            deve(r.returncode == 0, "corsa.py passo %s %s esce %s: %s" % (p["id"], az, r.returncode, (r.stderr or r.stdout)[-300:]))
    r = py(script("corsa.py"), "chiudi", id_c, "finita", cwd=D)
    deve(r.returncode == 0, "corsa.py chiudi esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-300:]))
    c = corsa_json(id_c)
    deve(c["stato"] == "finita" and all(p["stato"] == "fatto" for p in c["passi"]), "la corsa non è finita: " + c["stato"])
    STATO["corsa_finita"] = id_c
    return "corsa %s, %d passi fatti" % (id_c, len(c["passi"]))


@passo("4 pannello: si accende su 127.0.0.1, risponde, un secondo avvio lo riusa")
def pannello():
    D = STATO["D"]
    r = py(script("pannello.py"), "--cartella", D, cwd=D)
    deve(r.returncode == 0, "pannello.py esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-400:]))
    deve("acceso" in r.stdout, "l'uscita non dice «acceso»: " + r.stdout[-200:])
    inf = info_pannello()
    STATO["porta"], STATO["gettone"], STATO["pid"] = inf["porta"], inf["gettone"], inf["pid"]
    url = "http://127.0.0.1:%d" % inf["porta"]
    STATO["url"] = url
    st, corpo = http(url + "/")
    deve(st == 200 and inf["gettone"] in corpo, "la pagina / dà %s e porta il gettone: %s" % (st, inf["gettone"] in corpo))
    for v in ("ciao", "stato", "periodo", "grafi", "corse", "memoria", "file-chiave"):
        st, corpo = http("%s/api/%s" % (url, v))
        deve(st == 200, "/api/%s dà %s" % (v, st))
        json.loads(corpo)
    st, corpo = http(url + "/api/grafi")
    deve("giro-scadenze" in corpo, "/api/grafi non mostra giro-scadenze")
    st, corpo = http(url + "/api/corse")
    deve(STATO["corsa_finita"] in corpo, "/api/corse non mostra la corsa finita")
    st, corpo = http(url + "/api/stato")
    deve(st == 200 and len(corpo) > 20, "/api/stato vuoto")
    st, _ = http(url + "/api/inesistente")
    deve(st == 404, "una vista inesistente dà %s e non 404" % st)
    r = py(script("pannello.py"), "--cartella", D, cwd=D)
    deve(r.returncode == 0, "il secondo avvio esce %s" % r.returncode)
    deve(info_pannello()["pid"] == inf["pid"] and info_pannello()["porta"] == inf["porta"], "il secondo avvio non ha riusato il primo")
    return "%s: pagina e sette viste 200, /api/stato risponde, secondo avvio riusa pid %s" % (url, inf["pid"])


@passo("5 stop: dalla pagina, il comando dopo lo stop esce 3")
def stop():
    D, url = STATO["D"], STATO["url"]
    r = py(script("corsa.py"), "apri", "giro-lento", "--avviato-da", "conversazione", "--sessione", "sessione-ci-1", cwd=D)
    deve(r.returncode == 0, "corsa.py apri giro-lento esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-300:]))
    id_c = r.stdout.strip().splitlines()[-1]
    STATO["corsa_stop"] = id_c
    r = py(script("corsa.py"), "passo", id_c, "passo-1", "inizio", cwd=D)
    deve(r.returncode == 0, "il primo passo non parte")
    corpo = json.dumps({"id": id_c, "perche": "prova della catena"}).encode("utf-8")
    st, risposta = http(url + "/api/ferma", "POST", corpo,
                        {"Origin": url, "Content-Type": "application/json", "X-Gettone": STATO["gettone"]})
    deve(st == 200, "il POST /api/ferma dà %s: %s" % (st, risposta[:200]))
    st2, _ = http(url + "/api/ferma", "POST", corpo, {"Origin": url, "Content-Type": "application/json"})
    deve(st2 in (401, 403), "il POST senza gettone dà %s e non è rifiutato" % st2)
    r = py(script("corsa.py"), "passo", id_c, "passo-1", "fatto", cwd=D)
    deve(r.returncode == 3, "il comando dopo lo stop esce %s invece di 3" % r.returncode)
    c = corsa_json(id_c)
    deve(c["stato"] == "fermata" and c["stop"]["chi"] == "pannello", "la corsa non risulta fermata dal pannello: %s" % c["stato"])
    return "POST con gettone 200, senza gettone %s, comando dopo lo stop esce 3, corsa fermata" % st2


def comandi_hook(file_rel, evento):
    d = json.load(open(os.path.join(STATO["D"], *file_rel.split("/")), encoding="utf-8"))
    out = []
    for g in d["hooks"][evento]:
        for h in g["hooks"]:
            out.append(h["command"])
    deve(out, "%s non ha hook %s" % (file_rel, evento))
    return out


def shell_hook():
    """Le shell con cui l'harness lancia un hook: bash dove c'è (Claude Code su Windows usa Git Bash), e su Windows anche PowerShell."""
    shells = []
    b = shutil.which("bash")
    if b:
        shells.append(("bash", [b, "-c"]))
    if os.name == "nt":
        p = shutil.which("pwsh") or shutil.which("powershell")
        if p:
            shells.append(("powershell", [p, "-NoProfile", "-NonInteractive", "-Command"]))
    deve(shells, "nessuna shell per lanciare gli hook")
    return shells


def lancia_hook(shell, comando, evento):
    return esegui(shell + [comando], cwd=STATO["D"], env={"CLAUDE_PROJECT_DIR": STATO["D"]},
                  ingresso=json.dumps(evento, ensure_ascii=False))


@passo("6a hook ferma.py (PreToolUse): nega dopo lo stop, tace per un'altra conversazione")
def hook_ferma():
    D = STATO["D"]
    dettagli = []
    for file_rel in (".claude/settings.json", ".codex/hooks.json"):
        for nome_shell, shell in shell_hook():
            for cmd in comandi_hook(file_rel, "PreToolUse"):
                ev = {"hook_event_name": "PreToolUse", "session_id": "sessione-ci-1", "cwd": D,
                      "tool_name": "Bash", "tool_input": {"command": "ls"}}
                r = lancia_hook(shell, cmd, ev)
                deve(r.returncode == 0, "%s/%s: esce %s: %s" % (file_rel, nome_shell, r.returncode, (r.stderr or r.stdout)[-300:]))
                deve('"permissionDecision": "deny"' in r.stdout and "STOP" in r.stdout,
                     "%s/%s: non nega la corsa fermata. uscita: %r err: %r" % (file_rel, nome_shell, r.stdout[-200:], r.stderr[-200:]))
                ev["session_id"] = "un-altra-conversazione"
                r = lancia_hook(shell, cmd, ev)
                deve(r.returncode == 0 and not r.stdout.strip(), "%s/%s: nega anche un'altra conversazione: %r" % (file_rel, nome_shell, r.stdout[-200:]))
                dettagli.append("%s/%s" % (file_rel.split("/")[0], nome_shell))
    return "nega la sessione fermata e tace per un'altra: " + ", ".join(dettagli)


@passo("6b hook controlla-periodo.py (PostToolUse): segnala un todo.json rotto, tace su uno valido")
def hook_periodo():
    D = STATO["D"]
    todo = os.path.join(D, "periodo", "todo.json")
    buono = open(todo, encoding="utf-8").read()
    dettagli = []
    try:
        for file_rel in (".claude/settings.json", ".codex/hooks.json"):
            for nome_shell, shell in shell_hook():
                for cmd in comandi_hook(file_rel, "PostToolUse"):
                    ev = {"hook_event_name": "PostToolUse", "cwd": D, "tool_name": "Write",
                          "tool_input": {"file_path": todo}}
                    with open(todo, "w", encoding="utf-8", newline="\n") as f:
                        f.write('{"versione": "0.3.0", "periodo": "", "todo": "non una lista"}\n')
                    r = lancia_hook(shell, cmd, ev)
                    deve(r.returncode == 2 and "non è valido" in (r.stdout + r.stderr),
                         "%s/%s: un todo.json rotto esce %s, uscita %r" % (file_rel, nome_shell, r.returncode, (r.stdout + r.stderr)[-250:]))
                    with open(todo, "w", encoding="utf-8", newline="\n") as f:
                        f.write(buono)
                    r = lancia_hook(shell, cmd, ev)
                    deve(r.returncode == 0 and not r.stdout.strip(), "%s/%s: un todo.json valido esce %s: %r" % (file_rel, nome_shell, r.returncode, (r.stdout + r.stderr)[-250:]))
                    r = lancia_hook(shell, cmd, {})
                    deve(r.returncode == 0, "%s/%s: un evento vuoto esce %s" % (file_rel, nome_shell, r.returncode))
                    dettagli.append("%s/%s" % (file_rel.split("/")[0], nome_shell))
    finally:
        with open(todo, "w", encoding="utf-8", newline="\n") as f:
            f.write(buono)
    return "rotto = exit 2 col messaggio, valido e vuoto = exit 0: " + ", ".join(dettagli)


@passo("6c hook con lo script che manca: non blocca (esce 0)")
def hook_senza_script():
    vuota = os.path.join(STATO["B"], "Cartella senza hook")
    os.makedirs(vuota, exist_ok=True)
    for file_rel in (".claude/settings.json", ".codex/hooks.json"):
        for nome_shell, shell in shell_hook():
            for ev_nome in ("PreToolUse", "PostToolUse"):
                for cmd in comandi_hook(file_rel, ev_nome):
                    r = esegui(shell + [cmd], cwd=vuota, env={"CLAUDE_PROJECT_DIR": vuota}, ingresso="{}")
                    deve(r.returncode == 0, "%s/%s/%s con lo script mancante esce %s: %r" % (file_rel, nome_shell, ev_nome, r.returncode, (r.stdout + r.stderr)[-200:]))
    return "tutti gli hook escono 0"


@passo("7 pannello: si spegne, la porta si chiude, pannello.json sparisce")
def spegni():
    D = STATO["D"]
    r = py(script("pannello.py"), "--cartella", D, "--spegni", cwd=D)
    deve(r.returncode == 0, "--spegni esce %s: %s" % (r.returncode, (r.stderr or r.stdout)[-300:]))
    for _ in range(30):
        if not porta_aperta(STATO["porta"]):
            break
        time.sleep(0.5)
    deve(not porta_aperta(STATO["porta"]), "la porta %s è ancora aperta dopo --spegni" % STATO["porta"])
    deve(not os.path.exists(os.path.join(D, "interfaccia", "pannello.json")), "pannello.json c'è ancora")
    return "porta %s chiusa" % STATO["porta"]


def tabella(nome):
    righe = ["### Catena senza modello · %s · %s" % (nome, sys.platform), "", "| Passo | Esito | Dettaglio |", "|---|---|---|"]
    for n, e, d in RISULTATI:
        righe.append("| %s | %s | %s |" % (n, e, d.replace("|", "\\|")[:300]))
    return "\n".join(righe) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plugin", required=True, help="la radice del plugin installato")
    ap.add_argument("--base", required=True, help="la cartella di lavoro (vuota o nuova)")
    ap.add_argument("--nome", default="plugin", help="etichetta per la tabella (claude o codex)")
    a = ap.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    STATO["P"] = os.path.realpath(a.plugin)
    STATO["B"] = os.path.realpath(a.base)
    os.makedirs(STATO["B"], exist_ok=True)
    try:
        for p in PASSI:
            # i passi dipendono dai precedenti: se la cartella non nasce, il resto non ha senso
            if p.nome.startswith(("2", "3", "4", "5", "6", "7")) and "D" not in STATO and not p.nome.startswith("6c"):
                RISULTATI.append((p.nome, "FALLISCE", "saltato: la cartella dello studio non c'è"))
                print("FALLISCE   %-52s  saltato: la cartella dello studio non c'è" % p.nome)
                continue
            p()
    finally:
        if STATO.get("D") and os.path.isfile(os.path.join(STATO["D"], "interfaccia", "pannello.json")):
            py(script("pannello.py"), "--cartella", STATO["D"], "--spegni", cwd=STATO["D"])
    t = tabella(a.nome)
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(t + "\n")
    with open(os.path.join(STATO["B"], "catena-%s.json" % a.nome), "w", encoding="utf-8") as f:
        json.dump([{"passo": n, "esito": e, "dettaglio": d} for n, e, d in RISULTATI], f, ensure_ascii=False, indent=1)
    rossi = [n for n, e, _ in RISULTATI if e != "PASSA"]
    print("ESITO: PASSA" if not rossi else "ESITO: FALLISCE " + ", ".join(rossi))
    return 0 if not rossi else 1


if __name__ == "__main__":
    sys.exit(main())
