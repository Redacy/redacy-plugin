#!/usr/bin/env python3
# redacy 0.4.0 · skills/pannello/scripts/pannello.py
"""Il pannello: una pagina sola, in locale, che mostra lo studio e ferma una corsa.

Un server su 127.0.0.1, solo libreria standard, uno per cartella dello studio.
Legge la cartella (periodo/, memoria/, grafi/, workspace/, fonti/) e non ha un database.
Non lancia claude né codex. Gli unici gesti sono due:
  - ferma una corsa (scrive grafi/corse/<id>.stop, come fa `corsa.py ferma <id> --da pannello`);
  - prepara il riepilogo per «Richiedi supporto umano» (il pannello non invia niente).

Uso:
  python3 pannello.py [--cartella DIR]          accende il pannello (o riusa quello acceso) e stampa l'indirizzo
  python3 pannello.py --primo-piano             resta in primo piano (lo usa .claude/launch.json)
  python3 pannello.py --stato                   dice se il pannello della cartella è acceso
  python3 pannello.py --spegni                  spegne il pannello della cartella
  python3 pannello.py --vista NOME              stampa una vista in JSON senza server
                                                (stato, periodo, recenti, grafi, corse, file-chiave, memoria, supporto,
                                                file, file-firma, su-misura)

Opzioni: --porta N (altrimenti una porta stabile per cartella, 47000-47999), --inattivo-ore N
(il server si spegne da solo dopo N ore senza richieste, 8 di default, 0 = mai).

La cartella si trova da --cartella, dalla variabile REDACY_CARTELLA, o risalendo da cwd fino a una
cartella con AGENTS.md e almeno una fra grafi/, memoria/, periodo/.

Sicurezza (server locale): ascolta solo su 127.0.0.1; controlla l'intestazione Host (contro il
DNS rebinding); ogni richiesta con Origin deve avere l'Origin del pannello; il POST dello stop vuole
un gettone casuale (scritto in interfaccia/pannello.json, messo nella pagina) in X-Gettone, un
Origin uguale al pannello e Content-Type application/json; niente CORS; la pagina ha una
Content-Security-Policy senza rete; i file si leggono solo da percorsi fissi della cartella.
"""

import argparse
import datetime
import errno
import hmac
import http.client
import http.server
import importlib.util
import json
import os
import re
import secrets
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import zlib

VERSIONE_FORMATO = 1
NOME_PANNELLO = "redacy"
URL_SUPPORTO = "https://redacy.com"
NOME_VOCE_LAUNCH = "pannello redacy"
NOME_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORMATO_ORA = "%Y-%m-%dT%H:%M:%SZ"
PERSA_DOPO_DEFAULT = 20
MAX_PAGINE_MEMORIA = 3000
MAX_BYTE_PAGINA = 256 * 1024
MAX_BYTE_FILE = 16 * 1024 * 1024
MAX_CORSE = 30
MAX_CORPO_POST = 4096
RIGHE_LOG = 8
QUI = os.path.dirname(os.path.abspath(__file__))

# Flag di CreateProcess (Windows). Scritti a mano: in subprocess ci sono solo su Windows.
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def su_windows():
    """Vero su Windows. Ogni ramo solo-Windows di questo file passa di qui (le prove lo forzano)."""
    return os.name == "nt"

CSP = ("default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data:; font-src 'self'; connect-src 'self'; base-uri 'none'; "
       "form-action 'none'; frame-ancestors 'none'")


# ---------------------------------------------------------------- tempo

def adesso_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def scrivi_ora(dt):
    return dt.astimezone(datetime.timezone.utc).strftime(FORMATO_ORA)


def leggi_ora(testo):
    return datetime.datetime.strptime(testo, FORMATO_ORA).replace(tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------- la cartella e gli script degli altri

def e_studio(cartella):
    if not os.path.isfile(os.path.join(cartella, "AGENTS.md")):
        return False
    return any(os.path.isdir(os.path.join(cartella, d)) for d in ("grafi", "memoria", "periodo"))


def trova_cartella(esplicita=None):
    if esplicita:
        c = os.path.realpath(esplicita)
        if not os.path.isdir(c):
            raise SystemExit("Non trovo la cartella %s." % esplicita)
        return c
    amb = os.environ.get("REDACY_CARTELLA")
    if amb:
        return trova_cartella(amb)
    corrente = os.path.realpath(os.getcwd())
    inizio = corrente
    while True:
        if e_studio(corrente):
            return corrente
        padre = os.path.dirname(corrente)
        if padre == corrente:
            raise SystemExit(
                "Non trovo la cartella dello studio: risalendo da %s non c'è nessuna cartella con AGENTS.md "
                "e grafi/, memoria/ o periodo/. Spostati nella cartella dello studio, oppure usa --cartella." % inizio)
        corrente = padre


def cerca_script(nome, cartella):
    """Cerca uno script di B (corsa.py, yaml_ridotto.py): in REDACY_SCRIPT_GRAFI, nella cartella
    (.agents/script/), accanto a questo file, nel plugin (skills/crea-grafo/scripts/)."""
    candidati = []
    amb = os.environ.get("REDACY_SCRIPT_GRAFI")
    if amb:
        candidati.append(os.path.join(amb, nome))
    if cartella:
        candidati.append(os.path.join(cartella, ".agents", "script", nome))
    candidati.append(os.path.join(QUI, nome))
    candidati.append(os.path.normpath(os.path.join(QUI, "..", "..", "crea-grafo", "scripts", nome)))
    for c in candidati:
        if os.path.isfile(c):
            return c
    return None


def carica_modulo(percorso, nome):
    spec = importlib.util.spec_from_file_location(nome, percorso)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def carica_yaml(cartella):
    p = cerca_script("yaml_ridotto.py", cartella)
    if not p:
        return None
    try:
        return carica_modulo(p, "yaml_ridotto_pannello")
    except Exception:
        return None


# ---------------------------------------------------------------- letture di file

def leggi_testo(percorso, massimo=MAX_BYTE_PAGINA):
    try:
        if os.path.islink(percorso) or not os.path.isfile(percorso):
            return None
        with open(percorso, "rb") as f:
            dati = f.read(massimo)
        return dati.decode("utf-8", errors="replace")
    except OSError:
        return None


def leggi_json(percorso):
    t = leggi_testo(percorso)
    if t is None:
        return None
    try:
        return json.loads(t)
    except ValueError:
        return None


def dentro(cartella, percorso):
    """Vero se il percorso reale sta dentro la cartella."""
    try:
        r = os.path.realpath(percorso)
        base = os.path.realpath(cartella)
        return r == base or r.startswith(base + os.sep)
    except OSError:
        return False


def elenco(cartella, sotto, suffisso=None):
    """I nomi dei file regolari (non nascosti, non collegamenti) di una sottocartella, in ordine."""
    d = os.path.join(cartella, sotto)
    try:
        nomi = sorted(os.listdir(d))
    except OSError:
        return []
    out = []
    for n in nomi:
        if n.startswith("."):
            continue
        p = os.path.join(d, n)
        if os.path.islink(p) or not os.path.isfile(p):
            continue
        if suffisso and not n.endswith(suffisso):
            continue
        out.append(n)
    return out


def sottocartelle(cartella, sotto):
    d = os.path.join(cartella, sotto)
    try:
        nomi = sorted(os.listdir(d))
    except OSError:
        return []
    return [n for n in nomi if not n.startswith(".") and os.path.isdir(os.path.join(d, n))
            and not os.path.islink(os.path.join(d, n))]


def nome_leggibile(nome):
    t = (nome or "").replace("-", " ").strip()
    return t[:1].upper() + t[1:] if t else ""


def primo_titolo(testo):
    for riga in (testo or "").splitlines():
        m = re.match(r"^#\s+(.+?)\s*#*\s*$", riga)
        if m:
            return m.group(1).strip()
    return ""


def pulisci_riga(riga):
    r = riga.strip()
    r = re.sub(r"\*\*(.+?)\*\*", r"\1", r)
    r = re.sub(r"(?<!\*)\*(?!\*)(.+?)\*", r"\1", r)
    r = re.sub(r"`([^`]+)`", r"\1", r)
    r = re.sub(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]", r"\1", r)
    r = re.sub(r"^[-*+>]\s+", "", r)
    return r.strip()


def prima_riga_di_testo(testo):
    """La prima riga che non è titolo, commento HTML, frontmatter, import (@x) o vuota."""
    t = testo or ""
    if t.startswith("---"):
        fine = t.find("\n---", 3)
        if fine != -1:
            t = t[fine + 4:]
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    for riga in t.splitlines():
        r = riga.strip()
        if not r or r.startswith("#") or r.startswith("@") or r.startswith("```") or r.startswith("|") or r.startswith("---"):
            continue
        return pulisci_riga(r)[:240]
    return ""


def togli_codice(testo):
    t = re.sub(r"```.*?```", "", testo or "", flags=re.S)
    t = re.sub(r"~~~.*?~~~", "", t, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", t)


def collegamenti_di(testo):
    visti = []
    for m in re.finditer(r"\[\[([^\]\n]+)\]\]", togli_codice(testo)):
        nome = re.split(r"[|#]", m.group(1))[0].strip()
        if nome and nome not in visti:
            visti.append(nome)
    return visti


# ---------------------------------------------------------------- le viste

def vista_periodo(cartella):
    ob_testo = leggi_testo(os.path.join(cartella, "periodo", "obiettivo.md")) or ""
    obiettivo = prima_riga_di_testo(ob_testo)
    vuoto = (not obiettivo) or obiettivo.lower().startswith("nessun obiettivo")
    todo = leggi_json(os.path.join(cartella, "periodo", "todo.json"))
    if not isinstance(todo, dict) or not isinstance(todo.get("todo"), list):
        todo = {"versione": "0.3.0", "periodo": "", "todo": []}
    idee = leggi_json(os.path.join(cartella, "periodo", "idee.json"))
    if not isinstance(idee, dict) or not isinstance(idee.get("idee"), list):
        idee = {"versione": "0.3.0", "periodo": "", "idee": []}
    voci = [t for t in todo["todo"] if isinstance(t, dict)]
    todo["todo"] = voci
    oggi = datetime.date.today().isoformat()
    aspettano = []
    for t in voci:
        if t.get("stato") != "fatto" and t.get("chi") == "tu":
            scad = t.get("scadenza") or ""
            aspettano.append({"id": t.get("id"), "in_ritardo": bool(scad) and scad < oggi})
    return {"obiettivo": "" if vuoto else obiettivo, "obiettivo_vuoto": vuoto,
            "todo": todo, "idee": idee, "aspettano_te": aspettano}


RIGA_LOG = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · ([^·]+?) · (.*)$")


def vista_log(cartella, massimo=RIGHE_LOG):
    t = leggi_testo(os.path.join(cartella, "memoria", "LOG.md"), massimo=2 * 1024 * 1024) or ""
    righe = [r.rstrip() for r in t.splitlines() if RIGA_LOG.match(r.rstrip())]
    righe = righe[-massimo:][::-1]
    analizzate = []
    for r in righe:
        m = RIGA_LOG.match(r)
        analizzate.append({"quando": m.group(1), "tipo": m.group(2).strip(), "testo": m.group(3).strip()})
    return righe, analizzate


def leggi_corse_grezze(cartella):
    """Le corse (dict) più recenti per prime, e i problemi incontrati."""
    d = os.path.join(cartella, "grafi", "corse")
    problemi = []
    try:
        nomi = [n for n in os.listdir(d) if n.endswith(".json") and not n.startswith(".")]
    except OSError:
        return [], problemi
    corse = []
    for n in nomi:
        p = os.path.join(d, n)
        if os.path.islink(p):
            continue
        dato = leggi_json(p)
        if not isinstance(dato, dict) or "stato" not in dato:
            problemi.append("grafi/corse/%s: non è una corsa leggibile" % n)
            continue
        dato.setdefault("id", n[:-5])
        if not isinstance(dato.get("passi"), list):
            dato["passi"] = []
        corse.append(dato)
    corse.sort(key=lambda c: (str(c.get("inizio") or ""), str(c.get("id"))), reverse=True)
    return corse, problemi


def stop_richiesto(cartella, id_corsa):
    if not NOME_OK.match(id_corsa or ""):
        return None
    p = os.path.join(cartella, "grafi", "corse", id_corsa + ".stop")
    t = leggi_testo(p, massimo=4096)
    if t is None:
        return None
    try:
        dato = json.loads(t.strip().splitlines()[0]) if t.strip() else {}
    except (ValueError, IndexError):
        dato = {}
    if not isinstance(dato, dict):
        dato = {}
    return {"chi": str(dato.get("chi") or "sconosciuto")[:80], "quando": dato.get("quando") or "",
            "perche": str(dato.get("perche") or "")[:200]}


def arricchisci_corsa(cartella, c, adesso=None):
    """Aggiunge i campi derivati: stato_effettivo, persa, minuti_senza_segni, passo_corrente, passi_totali."""
    adesso = adesso or adesso_utc()
    c = dict(c)
    stato = c.get("stato")
    persa = False
    minuti = None
    if stato == "in-corso":
        try:
            minuti = int((adesso - leggi_ora(c["ultimo_segno"])).total_seconds() // 60)
        except (KeyError, TypeError, ValueError):
            minuti = None
        limite = c.get("persa_dopo_minuti") or PERSA_DOPO_DEFAULT
        persa = minuti is None or minuti > limite
    stop = None
    effettivo = stato
    if stato == "in-corso":
        stop = stop_richiesto(cartella, c.get("id", ""))
        if stop:
            effettivo = "fermata"
        elif persa:
            effettivo = "persa"
    c["persa"] = persa and not stop
    c["minuti_senza_segni"] = minuti
    c["stop_richiesto"] = stop
    c["stato_effettivo"] = effettivo
    passi = c.get("passi") or []
    c["passi_totali"] = len(passi)
    corrente = 0
    for i, p in enumerate(passi):
        if isinstance(p, dict) and p.get("stato") in ("in-corso", "fermato", "fallito"):
            corrente = i + 1
            break
        if isinstance(p, dict) and p.get("stato") == "fatto":
            corrente = i + 1
    c["passo_corrente"] = corrente
    return c


def vista_corse(cartella):
    grezze, problemi = leggi_corse_grezze(cartella)
    ricche = [arricchisci_corsa(cartella, c) for c in grezze[:max(MAX_CORSE, 1)]]
    in_corso = [c for c in ricche if c["stato"] == "in-corso" and c["stato_effettivo"] in ("in-corso", "persa")]
    ultime = [c for c in ricche if c not in in_corso][:20]
    return {"corse": ricche, "in_corso": in_corso, "ultime": ultime, "problemi": problemi}


def vista_grafi(cartella, corse=None):
    yr = carica_yaml(cartella)
    out = []
    problemi = []
    if corse is None:
        corse = leggi_corse_grezze(cartella)[0]
    for n in elenco(cartella, "grafi", ".yaml"):
        rel = "grafi/" + n
        if yr is None:
            problemi.append("%s: manca yaml_ridotto.py, non so leggerlo" % rel)
            continue
        try:
            dato = yr.leggi_file(os.path.join(cartella, "grafi", n))
        except Exception as e:  # ErroreYaml, OSError
            motivo = getattr(e, "motivo", None) or str(e)
            riga = getattr(e, "riga", None)
            problemi.append("%s%s: %s" % (rel, (":%s" % riga) if riga else "", motivo))
            continue
        if not isinstance(dato, dict):
            problemi.append("%s: non è un grafo" % rel)
            continue
        g = json.loads(json.dumps(dato))
        g["file"] = rel
        g.setdefault("grafo", n[:-5])
        try:
            g["archi"] = [list(a) for a in yr.archi_del_grafo(dato)]
        except Exception:
            g["archi"] = []
        ultima = None
        for c in corse:
            if c.get("grafo") == g["grafo"]:
                ultima = c
                break
        g["ultima_corsa"] = None if ultima is None else {
            "id": ultima.get("id"), "stato": ultima.get("stato"), "inizio": ultima.get("inizio"), "fine": ultima.get("fine")}
        out.append(g)
    return {"grafi": out, "problemi": problemi}


def vista_workspace(cartella, grafi, todo):
    out = []
    for nome in sottocartelle(cartella, "workspace"):
        base = "workspace/" + nome
        agents = leggi_testo(os.path.join(cartella, base, "AGENTS.md")) or ""
        pagine = len(elenco(cartella, base + "/memoria", ".md"))
        processi = []
        for g in grafi:
            for p in g.get("passi") or []:
                if isinstance(p, dict) and p.get("workspace") == nome:
                    processi.append(g.get("grafo"))
                    break
        aperti = [t for t in todo if t.get("stato") != "fatto" and str(t.get("dove") or "").startswith(base)]
        out.append({"nome": nome, "titolo": primo_titolo(agents) or nome_leggibile(nome), "percorso": base,
                    "serve": prima_riga_di_testo(agents), "pagine_memoria": pagine, "todo_aperti": len(aperti),
                    "processi": processi})
    return out


def vista_memoria(cartella):
    pagine = []
    aree = [("studio", "memoria")] + [(n, "workspace/%s/memoria" % n) for n in sottocartelle(cartella, "workspace")]
    for area, rel in aree:
        for n in elenco(cartella, rel, ".md"):
            if area == "studio" and n == "LOG.md":
                continue
            if len(pagine) >= MAX_PAGINE_MEMORIA:
                break
            t = leggi_testo(os.path.join(cartella, rel, n)) or ""
            pid = n[:-3]
            pagine.append({"id": pid, "area": area, "dove": rel + "/" + n,
                           "titolo": primo_titolo(t) or nome_leggibile(pid), "riga": prima_riga_di_testo(t),
                           "collegamenti": collegamenti_di(t)})
    per_area = {}
    for p in pagine:
        per_area.setdefault(p["area"], {})[p["id"]] = p

    def risolvi(da, nome):
        if nome in per_area.get(da["area"], {}):
            return per_area[da["area"]][nome]
        if nome in per_area.get("studio", {}):
            return per_area["studio"][nome]
        for area in sorted(per_area):
            if nome in per_area[area]:
                return per_area[area][nome]
        return None

    chiave = lambda p: p["area"] + "/" + p["id"]
    nodi = {chiave(p): {"id": p["id"], "chiave": chiave(p), "area": p["area"], "dove": p["dove"], "titolo": p["titolo"],
                        "riga": p["riga"], "mancante": False, "grado": 0, "citata_da": []} for p in pagine}
    archi = []
    visti = set()
    for p in pagine:
        for nome in p["collegamenti"]:
            dest = risolvi(p, nome)
            if dest is None:
                k = "?/" + nome
                if k not in nodi:
                    nodi[k] = {"id": nome, "chiave": k, "area": "", "dove": "", "titolo": nome_leggibile(nome), "riga": "",
                               "mancante": True, "grado": 0, "citata_da": []}
                a = (chiave(p), k, True)
            else:
                a = (chiave(p), chiave(dest), False)
            if a[0] == a[1] or (a[0], a[1]) in visti:
                continue
            visti.add((a[0], a[1]))
            archi.append({"da": a[0], "a": a[1], "mancante": a[2]})
            nodi[a[0]]["grado"] += 1
            nodi[a[1]]["grado"] += 1
            nodi[a[1]]["citata_da"].append(a[0])
    mancanti = [n for n in nodi.values() if n["mancante"]]
    # «collegamenti» come li conta la pagina: coppie di pagine che ci sono, senza direzione
    coppie = {tuple(sorted((a["da"], a["a"]))) for a in archi if not a["mancante"]}
    return {"memoria": pagine,
            "grafo": {"nodi": list(nodi.values()), "archi": archi,
                      "conteggi": {"pagine": len(pagine), "collegamenti": len(coppie), "mancanti": len(mancanti)}}}


# ---------------------------------------------------------------- il testo dei file per la pagina

def file_del_pannello(cartella):
    """I file che la pagina mostra come interfaccia, per percorso relativo.

    Solo percorsi fissi: AGENTS.md, periodo/ (.md, .json), memoria/*.md, grafi/*.yaml e le corse più
    recenti, workspace/<area>/AGENTS.md e workspace/<area>/memoria/*.md. Mai fonti/, mai le cartelle
    nascoste (.agents, .claude, .codex), mai interfaccia/.
    """
    out = []
    if os.path.isfile(os.path.join(cartella, "AGENTS.md")) and not os.path.islink(os.path.join(cartella, "AGENTS.md")):
        out.append("AGENTS.md")
    out += ["periodo/" + n for n in elenco(cartella, "periodo") if n.endswith((".md", ".json"))]
    out += ["memoria/" + n for n in elenco(cartella, "memoria", ".md")[:MAX_PAGINE_MEMORIA]]
    out += ["grafi/" + n for n in elenco(cartella, "grafi") if n.endswith((".yaml", ".yml"))]
    d = os.path.join(cartella, "grafi", "corse")

    def quando(n):
        try:
            return os.stat(os.path.join(d, n)).st_mtime
        except OSError:
            return 0
    out += ["grafi/corse/" + n for n in sorted(elenco(cartella, "grafi/corse", ".json"), key=quando, reverse=True)[:MAX_CORSE]]
    for area in sottocartelle(cartella, "workspace"):
        if "AGENTS.md" in elenco(cartella, "workspace/" + area):
            out.append("workspace/%s/AGENTS.md" % area)
        out += ["workspace/%s/memoria/%s" % (area, n) for n in elenco(cartella, "workspace/%s/memoria" % area, ".md")]
    return [r for r in out if dentro(cartella, os.path.join(cartella, r))]


def firma_file(cartella, elenco_file=None):
    """Cambia quando cambia uno dei file della pagina: la pagina rilegge i testi solo allora."""
    righe = []
    for rel in (elenco_file if elenco_file is not None else file_del_pannello(cartella)):
        try:
            st = os.stat(os.path.join(cartella, rel))
            righe.append("%s %d %d" % (rel, st.st_size, st.st_mtime_ns))
        except OSError:
            continue
    return "%08x" % (zlib.crc32("\n".join(righe).encode("utf-8")) & 0xffffffff)


def vista_file(cartella):
    """Il testo dei file della pagina, al massimo MAX_BYTE_FILE in tutto (MAX_BYTE_PAGINA per file)."""
    tutti = file_del_pannello(cartella)
    testi, totale, troncato = {}, 0, False
    for rel in tutti:
        t = leggi_testo(os.path.join(cartella, rel))
        if t is None:
            continue
        n = len(t.encode("utf-8"))
        if totale + n > MAX_BYTE_FILE:
            troncato = True
            break
        testi[rel] = t
        totale += n
    return {"firma": firma_file(cartella, tutti), "file": testi, "troncato": troncato}


PANNELLI = ("oggi", "processi", "periodo", "memoria", "aree")
TEMI = ("auto", "chiaro", "scuro")
COLORE = re.compile(r"^#[0-9a-fA-F]{6}$")


def vista_su_misura(cartella):
    """Le scelte del pannello per questo utente, da interfaccia/su-misura.json: solo le chiavi note e valide.

    Il file lo scrive l'agente dello studio dal modello della skill (modello/su-misura.json); se manca
    o non si legge, la pagina usa i suoi valori di partenza.
    """
    p = os.path.join(cartella, "interfaccia", "su-misura.json")
    dato = None
    if dentro(cartella, p):
        t = leggi_testo(p, 16 * 1024)
        try:
            dato = json.loads(t) if t else None
        except ValueError:
            dato = None
    if not isinstance(dato, dict):
        return {}
    out = {}
    if dato.get("tema") in TEMI:
        out["tema"] = dato["tema"]
    if dato.get("primo") in PANNELLI:
        out["primo"] = dato["primo"]
    if isinstance(dato.get("ordine"), list):
        ordine = []
        for x in dato["ordine"]:
            if x in PANNELLI and x not in ordine:
                ordine.append(x)
        out["ordine"] = ordine + [x for x in PANNELLI if x not in ordine]
    if isinstance(dato.get("frase"), bool):
        out["frase"] = dato["frase"]
    acc = dato.get("accento")
    if isinstance(acc, dict):
        a = {k: acc[k] for k in ("chiaro", "scuro") if isinstance(acc.get(k), str) and COLORE.match(acc[k])}
        if a:
            out["accento"] = a
    if isinstance(dato.get("titolo"), str) and dato["titolo"].strip():
        out["titolo"] = dato["titolo"].strip()[:60]
    return out


def vista_fonti(cartella):
    nomi = []
    d = os.path.join(cartella, "fonti")
    try:
        for n in sorted(os.listdir(d)):
            if n.startswith(".") or n == "LEGGIMI.md":
                continue
            p = os.path.join(d, n)
            nomi.append({"nome": n, "percorso": "fonti/" + n, "cartella": os.path.isdir(p) and not os.path.islink(p)})
    except OSError:
        pass
    return nomi[:200]


def versione_cartella(cartella):
    t = leggi_testo(os.path.join(cartella, ".agents", "hooks.json"), massimo=20000) or ""
    m = re.search(r"redacy (\d+\.\d+\.\d+[\w.-]*)", t)
    if m:
        return "redacy " + m.group(1)
    todo = leggi_json(os.path.join(cartella, "periodo", "todo.json"))
    if isinstance(todo, dict) and isinstance(todo.get("versione"), str):
        return "redacy " + todo["versione"]
    return "redacy"


def nome_studio(cartella):
    """Il titolo di memoria/studio.md se c'è, se no il nome della cartella."""
    t = primo_titolo(leggi_testo(os.path.join(cartella, "memoria", "studio.md")) or "")
    return t or os.path.basename(cartella.rstrip(os.sep))


def vista_supporto(cartella, stato):
    """Il riepilogo che l'utente copia in «Richiedi supporto umano»: nomi, conteggi, l'ultima nota d'errore."""
    cart = stato["cartella"]
    righe = []
    adesso = datetime.datetime.now()
    righe.append("Studio: %s · %s · %s" % (cart["nome"], cart["versione"], adesso.strftime("%d/%m/%Y %H:%M")))
    ob = stato["periodo"]["obiettivo"]
    righe.append("Obiettivo: %s" % (ob if ob else "non ancora scritto"))
    aree = [w["nome"] for w in stato["workspace"]]
    righe.append("Aree di lavoro: %s" % (", ".join(aree) if aree else "nessuna"))
    pr = ["%s (%s)" % (g.get("grafo"), "acceso" if g.get("acceso") else "spento") for g in stato["grafi"]]
    righe.append("Processi: %s" % (", ".join(pr) if pr else "nessuno"))
    inc = [nome_leggibile(c.get("grafo")) + (" (non dà notizie)" if c["persa"] else "") for c in stato["corse_in_corso"]]
    righe.append("In corso: %s" % (", ".join(inc) if inc else "niente"))
    ultimo = None
    for c in stato["corse"]:
        if c.get("stato") == "fallita" or c.get("stato_effettivo") == "persa":
            ultimo = c
            break
    if ultimo:
        passo = None
        for p in ultimo.get("passi") or []:
            if isinstance(p, dict) and p.get("stato") == "fallito":
                passo = p
                break
        if passo:
            nota = str(passo.get("nota") or "").strip()
            righe.append("Ultimo problema: %s, non riuscito al passo %s%s" % (
                ultimo.get("grafo"), passo.get("id"), (": " + nota) if nota else ""))
        else:
            righe.append("Ultimo problema: %s non dà notizie" % ultimo.get("grafo"))
    else:
        righe.append("Ultimo problema: nessuno")
    righe.append("Cose che toccano a te: %d" % stato["conta"]["per_te"])
    mem = stato["memoria_grafo"]["conteggi"]
    righe.append("Memoria: %d pagine, %d collegamenti, %d da scrivere" % (mem["pagine"], mem["collegamenti"], mem["mancanti"]))
    righe.append("")
    righe.append("Cosa mi serve:")
    return {"url": URL_SUPPORTO, "righe": righe, "testo": "\n".join(righe)}


def vista_stato(cartella):
    periodo = vista_periodo(cartella)
    log, log_righe = vista_log(cartella)
    corse = vista_corse(cartella)
    grezze = leggi_corse_grezze(cartella)[0]
    grafi = vista_grafi(cartella, grezze)
    mem = vista_memoria(cartella)
    todo_voci = periodo["todo"]["todo"]
    workspace = vista_workspace(cartella, grafi["grafi"], todo_voci)
    conta = {"per_te": len(periodo["aspettano_te"]), "in_corso": len(corse["in_corso"]),
             "pagine": mem["grafo"]["conteggi"]["pagine"], "collegamenti": mem["grafo"]["conteggi"]["collegamenti"],
             "mancanti": mem["grafo"]["conteggi"]["mancanti"], "aree": len(workspace), "processi": len(grafi["grafi"])}
    fatti = sorted([t for t in todo_voci if t.get("stato") == "fatto"], key=lambda t: str(t.get("aggiornato") or ""), reverse=True)[:8]
    stato = {
        "ora": scrivi_ora(adesso_utc()),
        "cartella": {"nome": nome_studio(cartella), "percorso": cartella, "versione": versione_cartella(cartella)},
        "periodo": periodo,
        "log": log, "log_righe": log_righe,
        "recenti": {"log": log_righe, "todo_fatti": fatti,
                    "corse_finite": [c for c in corse["ultime"] if c["stato"] in ("finita", "fallita", "fermata")][:8]},
        "workspace": workspace,
        "grafi": grafi["grafi"],
        "corse": corse["corse"], "corse_in_corso": corse["in_corso"], "corse_ultime": corse["ultime"],
        "file_chiave": {"grafi": [{"file": g["file"], "grafo": g.get("grafo")} for g in grafi["grafi"]],
                        "workspace": [{"percorso": w["percorso"], "titolo": w["titolo"]} for w in workspace],
                        "fonti": vista_fonti(cartella)},
        "memoria": mem["memoria"], "memoria_grafo": mem["grafo"],
        "conta": conta,
        "problemi": corse["problemi"] + grafi["problemi"],
    }
    stato["supporto"] = vista_supporto(cartella, stato)
    return stato


VISTE = {
    "stato": lambda c: vista_stato(c),
    "periodo": lambda c: vista_periodo(c),
    "recenti": lambda c: vista_stato(c)["recenti"],
    "grafi": lambda c: vista_grafi(c),
    "corse": lambda c: vista_corse(c),
    "file-chiave": lambda c: vista_stato(c)["file_chiave"],
    "memoria": lambda c: vista_memoria(c),
    "supporto": lambda c: vista_stato(c)["supporto"],
    "file": lambda c: vista_file(c),
    "file-firma": lambda c: {"firma": firma_file(c)},
    "su-misura": lambda c: vista_su_misura(c),
}


# ---------------------------------------------------------------- lo stop

def ferma_corsa(cartella, id_corsa, perche=""):
    """Chiede lo stop di una corsa. Restituisce (codice http, dict).
    Passa da `corsa.py ferma <id> --da pannello`; se corsa.py non c'è scrive lo stesso file .stop."""
    if not NOME_OK.match(id_corsa or ""):
        return 400, {"ok": False, "errore": "L'id della corsa non è valido."}
    perche = " ".join(str(perche or "").split())[:200]
    percorso = os.path.join(cartella, "grafi", "corse", id_corsa + ".json")
    if not os.path.isfile(percorso):
        return 404, {"ok": False, "errore": "Questa corsa non c'è."}
    script = cerca_script("corsa.py", cartella)
    if script:
        cmd = [sys.executable, script, "ferma", id_corsa, "--da", "pannello", "--cartella", cartella]
        if perche:
            cmd += ["--perche", perche]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=cartella,
                               **({"creationflags": CREATE_NO_WINDOW} if su_windows() else {}))
        except (OSError, subprocess.TimeoutExpired):
            return 500, {"ok": False, "errore": "Non sono riuscito a fermare la corsa."}
        if r.returncode == 0:
            return 200, {"ok": True, "stato": "fermata"}
        if r.returncode == 3:
            return 409, {"ok": False, "errore": "Questa corsa non sta più girando."}
        if r.returncode == 2:
            return 404, {"ok": False, "errore": "Questa corsa non c'è."}
        return 500, {"ok": False, "errore": "Non sono riuscito a fermare la corsa."}
    corsa = leggi_json(percorso)
    if not isinstance(corsa, dict) or corsa.get("stato") != "in-corso":
        return 409, {"ok": False, "errore": "Questa corsa non sta più girando."}
    dest = os.path.join(cartella, "grafi", "corse", id_corsa + ".stop")
    riga = json.dumps({"chi": "pannello", "quando": scrivi_ora(adesso_utc()), "perche": perche}, ensure_ascii=False)
    fd, tmp = tempfile.mkstemp(prefix=".stop-", dir=os.path.dirname(dest))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(riga + "\n")
        os.replace(tmp, dest)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return 500, {"ok": False, "errore": "Non sono riuscito a fermare la corsa."}
    return 200, {"ok": True, "stato": "fermata"}


# ---------------------------------------------------------------- pannello.json e il processo

def percorso_info(cartella):
    return os.path.join(cartella, "interfaccia", "pannello.json")


def leggi_info(cartella):
    dato = leggi_json(percorso_info(cartella))
    return dato if isinstance(dato, dict) else None


def sostituisci(tmp, dest):
    """os.replace. Su Windows, se un altro processo ha il file aperto in lettura in quell'istante, riprova per un secondo."""
    for tentativo in range(20):
        try:
            return os.replace(tmp, dest)
        except PermissionError:
            if not su_windows() or tentativo == 19:
                raise
            time.sleep(0.05)


def scrivi_info(cartella, info):
    d = os.path.join(cartella, "interfaccia")
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".pannello-", dir=d)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o600)
    sostituisci(tmp, percorso_info(cartella))


def pid_vivo_windows(pid):
    """Su Windows os.kill(pid, 0) non è un controllo: può terminare il processo. Qui si chiede solo il suo stato."""
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetExitCodeProcess.restype = wintypes.BOOL
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return ctypes.get_last_error() == 5  # ACCESS_DENIED: c'è, ma non è nostro
    try:
        codice = wintypes.DWORD()
        if not k.GetExitCodeProcess(h, ctypes.byref(codice)):
            return False
        return codice.value == 259  # STILL_ACTIVE
    finally:
        k.CloseHandle(h)


def pid_vivo(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    if su_windows():
        return pid_vivo_windows(pid)
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno == errno.EPERM
    return True


def blocca_file(fd):
    """Lucchetto esclusivo su un file aperto: aspetta finché lo ottiene. Unix: fcntl.flock. Windows: msvcrt.locking."""
    if su_windows():
        import msvcrt
        os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # riprova da solo per circa 10 secondi, poi OSError
                return
            except OSError:
                time.sleep(0.05)
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_EX)


def sblocca_file(fd):
    if su_windows():
        import msvcrt
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return
    import fcntl
    fcntl.flock(fd, fcntl.LOCK_UN)


def risponde(porta, cartella, timeout=1.5):
    """Vero se su quella porta c'è il pannello di questa cartella."""
    try:
        conn = http.client.HTTPConnection("127.0.0.1", porta, timeout=timeout)
        conn.request("GET", "/api/ciao", headers={"Host": "127.0.0.1:%d" % porta})
        r = conn.getresponse()
        corpo = r.read(4096)
        conn.close()
        if r.status != 200:
            return False
        d = json.loads(corpo.decode("utf-8"))
        return d.get("pannello") == NOME_PANNELLO and os.path.realpath(d.get("cartella", "")) == os.path.realpath(cartella)
    except (OSError, ValueError, http.client.HTTPException):
        return False


def acceso(cartella):
    """Le informazioni del pannello acceso di questa cartella, o None."""
    info = leggi_info(cartella)
    if not info:
        return None
    if pid_vivo(info.get("pid")) and isinstance(info.get("porta"), int) and risponde(info["porta"], cartella):
        return info
    return None


def porta_stabile(cartella):
    return 47000 + zlib.crc32(os.path.realpath(cartella).encode("utf-8")) % 1000


def apri_socket_libera(cartella, preferita=None):
    """Sceglie una porta libera su 127.0.0.1: la preferita, la stabile della cartella, le successive."""
    base = preferita or porta_stabile(cartella)
    for porta in [base] + [47000 + (base - 47000 + i) % 1000 for i in range(1, 60)]:
        try:
            return porta, crea_server(porta)
        except OSError as e:
            if e.errno in (errno.EPERM, errno.EACCES):
                raise SystemExit(
                    "Il sistema non mi lascia aprire una porta su 127.0.0.1 (%s). Succede in Codex dentro la sandbox: "
                    "lancia lo stesso comando fuori dalla sandbox (chiedi il permesso) o da un terminale tuo." % e.strerror)
            continue
    raise SystemExit("Non trovo una porta libera su 127.0.0.1.")


def eseguibile_python():
    """Come launch.json lancia Python: `python3` su macOS e Linux, il Python che sta girando su Windows."""
    return sys.executable if su_windows() and sys.executable else "python3"


def aggiorna_launch(cartella, porta):
    """Tiene d'accordo .claude/launch.json col pannello acceso: cambia solo la voce del pannello, e solo se il file c'è."""
    p = os.path.join(cartella, ".claude", "launch.json")
    t = leggi_testo(p, massimo=64 * 1024)
    if t is None:
        return
    try:
        dato = json.loads(t)
    except ValueError:
        return
    if not isinstance(dato, dict):
        return
    voci = dato.setdefault("configurations", [])
    if not isinstance(voci, list):
        return
    voce = None
    for v in voci:
        if isinstance(v, dict) and v.get("name") == NOME_VOCE_LAUNCH:
            voce = v
    nuova = {"name": NOME_VOCE_LAUNCH, "runtimeExecutable": eseguibile_python(),
             "runtimeArgs": [".agents/script/pannello.py", "--primo-piano", "--porta", str(porta)],
             "port": porta, "autoPort": False}
    if voce == nuova:
        return
    if voce is None:
        voci.append(nuova)
    else:
        voce.clear()
        voce.update(nuova)
    fd, tmp = tempfile.mkstemp(prefix=".launch-", dir=os.path.dirname(p))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(dato, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, p)


# ---------------------------------------------------------------- il server

class Stato(object):
    """Quello che il gestore delle richieste deve sapere."""
    cartella = ""
    porta = 0
    gettone = ""
    pagina = None
    ultima_richiesta = time.time()


class Gestore(http.server.BaseHTTPRequestHandler):
    server_version = "redacy-pannello"
    sys_version = ""
    protocol_version = "HTTP/1.0"

    # niente log delle richieste
    def log_message(self, formato, *args):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").strip().lower()
        return host in ("127.0.0.1:%d" % Stato.porta, "localhost:%d" % Stato.porta)

    def _origin_ammessi(self):
        return ("http://127.0.0.1:%d" % Stato.porta, "http://localhost:%d" % Stato.porta)

    def _rispondi(self, codice, corpo, tipo="application/json; charset=utf-8", extra=None):
        if not isinstance(corpo, (bytes, bytearray)):
            corpo = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
        self.send_response(codice)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(corpo)

    def _rifiuta(self, codice, motivo):
        self._rispondi(codice, {"ok": False, "errore": motivo})

    def _controlli_comuni(self):
        if not self._host_ok():
            self._rifiuta(403, "Intestazione Host non ammessa.")
            return False
        origin = self.headers.get("Origin")
        if origin is not None and origin not in self._origin_ammessi():
            self._rifiuta(403, "Origine non ammessa.")
            return False
        return True

    def do_GET(self):
        Stato.ultima_richiesta = time.time()
        if not self._controlli_comuni():
            return
        percorso = self.path.split("?", 1)[0]
        if percorso == "/" or percorso == "/index.html":
            return self._pagina()
        if percorso == "/favicon.ico":
            return self._rispondi(204, b"", "image/x-icon")
        if percorso == "/api/ciao":
            return self._rispondi(200, {"pannello": NOME_PANNELLO, "formato": VERSIONE_FORMATO, "cartella": Stato.cartella,
                                        "ora": scrivi_ora(adesso_utc())})
        if percorso.startswith("/api/"):
            nome = percorso[len("/api/"):]
            f = VISTE.get(nome)
            if f is None:
                return self._rifiuta(404, "Vista sconosciuta.")
            try:
                return self._rispondi(200, f(Stato.cartella))
            except Exception as e:  # una vista rotta non abbatte il server
                return self._rispondi(500, {"ok": False, "errore": "La vista non si legge: %s" % e.__class__.__name__})
        if percorso.startswith("/assets/"):
            return self._asset(percorso[len("/assets/"):])
        return self._rifiuta(404, "Non c'è.")

    do_HEAD = do_GET

    def do_POST(self):
        Stato.ultima_richiesta = time.time()
        if not self._controlli_comuni():
            return
        percorso = self.path.split("?", 1)[0]
        if percorso != "/api/ferma":
            return self._rifiuta(404, "Non c'è.")
        if self.headers.get("Origin") not in self._origin_ammessi():
            return self._rifiuta(403, "Serve l'origine del pannello.")
        sfs = self.headers.get("Sec-Fetch-Site")
        if sfs is not None and sfs not in ("same-origin", "none"):
            return self._rifiuta(403, "Richiesta da un altro sito.")
        tipo = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if tipo != "application/json":
            return self._rifiuta(415, "Serve application/json.")
        gettone = self.headers.get("X-Gettone") or ""
        if not Stato.gettone or not hmac.compare_digest(gettone.encode("utf-8"), Stato.gettone.encode("utf-8")):
            return self._rifiuta(403, "Gettone mancante o sbagliato.")
        try:
            lunghezza = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            lunghezza = -1
        if lunghezza < 0 or lunghezza > MAX_CORPO_POST:
            return self._rifiuta(413, "Richiesta troppo lunga.")
        try:
            corpo = json.loads(self.rfile.read(lunghezza).decode("utf-8") or "{}")
        except ValueError:
            return self._rifiuta(400, "Il corpo non è JSON.")
        if not isinstance(corpo, dict) or not isinstance(corpo.get("id"), str):
            return self._rifiuta(400, "Manca l'id della corsa.")
        codice, risposta = ferma_corsa(Stato.cartella, corpo["id"], corpo.get("perche") or "")
        return self._rispondi(codice, risposta)

    def do_PUT(self):
        self._rifiuta(405, "Metodo non ammesso.")

    do_DELETE = do_PATCH = do_OPTIONS = do_PUT

    def _pagina(self):
        if Stato.pagina is None or not os.path.isfile(Stato.pagina):
            return self._rispondi(503, b"La pagina del pannello non c'e' (manca pagina.html).", "text/plain; charset=utf-8")
        with open(Stato.pagina, "rb") as f:
            html = f.read()
        html = html.replace(b"{{GETTONE}}", Stato.gettone.encode("ascii")).replace(b"{{PORTA}}", str(Stato.porta).encode("ascii"))
        self._rispondi(200, html, "text/html; charset=utf-8")

    def _asset(self, nome):
        if "/" in nome or "\\" in nome or nome.startswith(".") or not re.match(r"^[A-Za-z0-9._-]+$", nome):
            return self._rifiuta(404, "Non c'è.")
        tipi = {".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".png": "image/png",
                ".svg": "image/svg+xml", ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8"}
        ext = os.path.splitext(nome)[1].lower()
        if ext not in tipi:
            return self._rifiuta(404, "Non c'è.")
        p = os.path.join(os.path.dirname(Stato.pagina or QUI), "assets", nome)
        if not os.path.isfile(p) or os.path.islink(p):
            return self._rifiuta(404, "Non c'è.")
        with open(p, "rb") as f:
            self._rispondi(200, f.read(), tipi[ext])


class ServerPannello(http.server.ThreadingHTTPServer):
    daemon_threads = True
    # Su Windows SO_REUSEADDR lascia aprire una seconda porta uguale a una già in ascolto: lì no.
    allow_reuse_address = not su_windows()
    request_queue_size = 16


def crea_server(porta):
    return ServerPannello(("127.0.0.1", porta), Gestore)


def trova_pagina():
    for c in (os.path.join(QUI, "pagina.html"),):
        if os.path.isfile(c):
            return c
    return None


def servi(cartella, porta, server, ore_inattivo):
    """Scrive pannello.json e serve fino a SIGTERM, a --spegni o all'inattività."""
    Stato.cartella = cartella
    Stato.porta = porta
    Stato.gettone = secrets.token_urlsafe(32)
    Stato.pagina = trova_pagina()
    Stato.ultima_richiesta = time.time()
    info = {"formato": VERSIONE_FORMATO, "porta": porta, "pid": os.getpid(), "ora": scrivi_ora(adesso_utc()),
            "cartella": cartella, "gettone": Stato.gettone}
    scrivi_info(cartella, info)
    try:
        aggiorna_launch(cartella, porta)
    except OSError:
        pass

    def ferma_server(*_):
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, ferma_server)
    signal.signal(signal.SIGINT, ferma_server)
    if ore_inattivo and ore_inattivo > 0:
        def guardia():
            while True:
                time.sleep(30)
                if time.time() - Stato.ultima_richiesta > ore_inattivo * 3600:
                    ferma_server()
                    return
        threading.Thread(target=guardia, daemon=True).start()
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        try:
            attuale = leggi_info(cartella)
            if attuale and attuale.get("pid") == os.getpid():
                os.unlink(percorso_info(cartella))
        except OSError:
            pass
        server.server_close()


def avvia_staccato_windows(cartella, porta, ore_inattivo):
    """Windows: lancia questo stesso file come processo figlio staccato, senza finestra, e aspetta che risponda.

    Il figlio fa quello che fa il ramo Unix dopo il fork: apre la porta, scrive interfaccia/pannello.json
    (porta, pid, gettone) e serve. Il genitore lo legge da lì, come sul ramo Unix. Restituisce le informazioni."""
    cmd = [sys.executable, os.path.abspath(__file__), "--cartella", cartella, "--primo-piano",
           "--porta", str(porta), "--inattivo-ore", str(ore_inattivo)]
    with open(os.path.join(cartella, "interfaccia", "pannello.log"), "ab") as log:
        figlio = subprocess.Popen(cmd, cwd=cartella, stdin=subprocess.DEVNULL, stdout=log, stderr=log, close_fds=True,
                                  creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW)
    fine = time.time() + 15
    while time.time() < fine:
        info = acceso(cartella)
        if info:
            return info
        if figlio.poll() is not None:
            break
        time.sleep(0.1)
    raise SystemExit("Il pannello non è partito: guarda interfaccia/pannello.log.")


def accendi(cartella, porta_scelta, primo_piano, ore_inattivo):
    """Riusa il pannello acceso o ne accende uno. Restituisce (info, nuovo)."""
    os.makedirs(os.path.join(cartella, "interfaccia"), exist_ok=True)
    lucchetto = os.open(os.path.join(cartella, "interfaccia", ".pannello.lock"), os.O_RDWR | os.O_CREAT, 0o600)
    blocca_file(lucchetto)
    try:
        info = acceso(cartella)
        if info:
            try:
                aggiorna_launch(cartella, info["porta"])
            except OSError:
                pass
            return info, False
        porta, server = apri_socket_libera(cartella, porta_scelta)
        if primo_piano:
            os.close(lucchetto)
            lucchetto = None
            servi(cartella, porta, server, ore_inattivo)
            return None, True
        if su_windows():
            # Niente fork: si chiude la porta e il lucchetto, e un figlio staccato rifà il giro in primo piano.
            server.server_close()
            sblocca_file(lucchetto)
            os.close(lucchetto)
            lucchetto = None
            return avvia_staccato_windows(cartella, porta, ore_inattivo), True
        pid = os.fork()
        if pid > 0:
            server.server_close()
            # il processo che resta in vita fa il resto: qui si aspetta che il pannello risponda
            fine = time.time() + 8
            while time.time() < fine:
                info = acceso(cartella)
                if info and info.get("porta") == porta:
                    return info, True
                time.sleep(0.1)
            raise SystemExit("Il pannello non è partito: guarda interfaccia/pannello.log.")
        # figlio: si stacca dal terminale
        os.close(lucchetto)
        lucchetto = None
        os.setsid()
        if os.fork() > 0:
            os._exit(0)
        os.chdir(cartella)
        log = os.open(os.path.join(cartella, "interfaccia", "pannello.log"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        nullo = os.open(os.devnull, os.O_RDONLY)
        os.dup2(nullo, 0)
        os.dup2(log, 1)
        os.dup2(log, 2)
        try:
            servi(cartella, porta, server, ore_inattivo)
        except BaseException as e:  # il figlio non torna mai nel chiamante
            sys.stderr.write("pannello: %r\n" % (e,))
        os._exit(0)
    finally:
        if lucchetto is not None:
            sblocca_file(lucchetto)
            os.close(lucchetto)


def spegni(cartella):
    info = leggi_info(cartella)
    if not info or not pid_vivo(info.get("pid")) or not risponde(info.get("porta", 0), cartella):
        print("Non c'è un pannello acceso per questa cartella.")
        return 0
    try:
        os.kill(info["pid"], signal.SIGTERM)  # su Windows termina il processo di colpo: il server non tiene niente in sospeso
    except OSError:
        pass
    fine = time.time() + 5
    while time.time() < fine and pid_vivo(info["pid"]):
        time.sleep(0.1)
    if su_windows():
        # il server terminato così non ha tolto da sé pannello.json
        try:
            attuale = leggi_info(cartella)
            if attuale and attuale.get("pid") == info["pid"]:
                os.unlink(percorso_info(cartella))
        except OSError:
            pass
    print("Pannello spento.")
    return 0


def main(argv=None):
    for flusso in (sys.stdout, sys.stderr):
        try:
            flusso.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Il pannello dello studio: una pagina sola, in locale.", add_help=True)
    ap.add_argument("--cartella", help="la cartella dello studio (se manca: REDACY_CARTELLA, poi risalendo da cwd)")
    ap.add_argument("--porta", type=int, help="la porta (se manca: una porta stabile per cartella)")
    ap.add_argument("--primo-piano", action="store_true", help="resta in primo piano (per .claude/launch.json)")
    ap.add_argument("--stato", action="store_true", help="dice se il pannello della cartella è acceso")
    ap.add_argument("--spegni", action="store_true", help="spegne il pannello della cartella")
    ap.add_argument("--vista", choices=sorted(VISTE), help="stampa una vista in JSON, senza server")
    ap.add_argument("--inattivo-ore", type=float, default=8.0, help="si spegne dopo N ore senza richieste (0 = mai)")
    args = ap.parse_args(argv)
    cartella = trova_cartella(args.cartella)
    if args.vista:
        print(json.dumps(VISTE[args.vista](cartella), ensure_ascii=False, indent=2))
        return 0
    if args.spegni:
        return spegni(cartella)
    if args.stato:
        info = acceso(cartella)
        if info:
            print("Acceso: http://127.0.0.1:%d/ (pid %d)" % (info["porta"], info["pid"]))
            return 0
        print("Spento.")
        return 1
    info, nuovo = accendi(cartella, args.porta, args.primo_piano, args.inattivo_ore)
    if info is None:  # primo piano: è finito
        return 0
    print("Il pannello è %s: http://127.0.0.1:%d/" % ("acceso" if nuovo else "già acceso", info["porta"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
