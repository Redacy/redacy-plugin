# redacy 0.4.1 · skills/ordina-dati/scripts/inventario.py
"""Fa l'inventario di una cartella, in sola lettura.

Uso: python3 inventario.py CARTELLA [--testo] [--elenco] [--massimo N]
                           [--senza-doppioni] [--tetto-doppioni-mb N]

Stampa un JSON (con --testo un riassunto in italiano): quanti file e cartelle,
la profondità, i tipi per estensione, la data più vecchia e la più recente,
come sono nominati i file, i doppioni per contenuto, le cartelle vuote, i file
molto grandi e i nomi che Windows o OneDrive rifiutano o che sono copie.

Non scrive niente, non segue i collegamenti, salta le cartelle nascoste e di
sistema. Il contenuto di un file si legge solo per l'impronta dei doppioni, e
solo fra file della stessa dimensione. I file che stanno solo sul cloud
(OneDrive, iCloud) non si aprono mai, per non scaricarli.

Solo libreria standard, Python 3.9 o più. Gira su Windows, macOS e Linux.
Le funzioni sui nomi (problemi_nome, SISTEMA, e_nascosto) le usa anche
skills/riordina-cartella/scripts/riordina.py.

Uscite: 0 fatto · 1 uso sbagliato · 2 la cartella non c'è o non si legge.
"""

import datetime
import hashlib
import json
import os
import re
import stat
import sys
import unicodedata
from collections import Counter, defaultdict

MASSIMO_FILE = 20000          # oltre, si guarda solo l'inizio e lo si dice
GRANDE_BYTE = 100 * 1024 * 1024   # un file «molto grande»
TETTO_HASH_FILE = 512 * 1024 * 1024   # un file più grande non si confronta
TETTO_HASH_TOTALE_MB = 2048   # quanti MB si leggono in tutto per i doppioni
TESTA_HASH = 64 * 1024        # prima impronta: i primi 64 KB
MAX_ELENCO = 20               # righe per elenco, senza --elenco
TETTO_PERCORSO = 259          # MAX_PATH di Windows meno il terminatore
TETTO_NOME = 255

# Cartelle e file di sistema: non si guardano e non si toccano.
SISTEMA = {
    "$recycle.bin", "system volume information", "recycler", "__macosx",
    "node_modules", "__pycache__", "thumbs.db", "desktop.ini", ".ds_store",
    "icon\r", "$windows.~bt", "$windows.~ws", "config.msi", "msocache",
}
# Le voci di una cartella dello studio che il riordino non tocca.
VOCI_STUDIO = {"agents.md", "claude.md", "memoria", "periodo", "grafi", "workspace",
               "interfaccia", "fonti", ".agents", ".claude", ".codex"}

CARATTERI_WINDOWS = set('<>:"/\\|?*')
RISERVATI = {"con", "prn", "aux", "nul", ".lock", "desktop.ini"}
RISERVATI |= {"com%d" % i for i in range(10)} | {"lpt%d" % i for i in range(10)}
RISERVATI |= {"com\u00b9", "com\u00b2", "com\u00b3", "lpt\u00b9", "lpt\u00b2", "lpt\u00b3"}

RE_COPIA = re.compile(r"^(copia di |copy of )|( - copia| - copy)( \(\d+\))?$|\s\(\d+\)$", re.I)

# Attributi dei file solo sul cloud (Windows) e flag «dataless» (macOS).
ATTR_OFFLINE = 0x1000
ATTR_RECALL_ON_OPEN = 0x40000
ATTR_RECALL_ON_DATA_ACCESS = 0x400000
ATTR_HIDDEN = 0x2
ATTR_SYSTEM = 0x4
ATTR_REPARSE = 0x400
TAG_JUNCTION = 0xA0000003
TAG_SYMLINK = 0xA000000C
SF_DATALESS = 0x40000000

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
        "agosto", "settembre", "ottobre", "novembre", "dicembre"]

SCHEMI_DATA = [
    ("data AAAA-MM-GG", re.compile(r"(?<!\d)(19|20)\d\d([-_. ])(0[1-9]|1[0-2])\2(0[1-9]|[12]\d|3[01])(?!\d)")),
    ("data AAAAMMGG", re.compile(r"(?<!\d)(19|20)\d\d(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])(?!\d)")),
    ("data GG-MM-AAAA", re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])([-_. ])(0[1-9]|1[0-2])\2(19|20)\d\d(?!\d)")),
    ("solo l'anno", re.compile(r"(?<!\d)(19|20)\d\d(?!\d)")),
]
RE_NUMERO_INIZIO = re.compile(r"^\d{1,5}[ _.\-)]")
PAROLE_VERSIONE = {"v1", "v2", "v3", "rev", "rev1", "rev2", "def", "definitivo", "definitiva",
                   "finale", "bozza", "ok", "firmato", "firmata", "old", "vecchio", "nuovo", "new"}
PAROLE_VUOTE = {"del", "della", "delle", "dello", "dei", "degli", "di", "da", "per", "con", "the",
                "and", "una", "uno", "sul", "sulla", "nel", "nella", "alla", "allo", "copia",
                "copy", "pdf", "doc", "docx", "xls", "xlsx", "jpg"}


class Errore(Exception):
    def __init__(self, codice, testo):
        Exception.__init__(self, testo)
        self.codice = codice
        self.testo = testo


# ---------------------------------------------------------------- nomi

def problemi_nome(nome):
    """I motivi per cui Windows o OneDrive rifiutano un nome (un solo pezzo di percorso)."""
    p = []
    if not nome:
        return ["nome vuoto"]
    brutti = sorted(set(c for c in nome if c in CARATTERI_WINDOWS or ord(c) < 32))
    if brutti:
        mostra = " ".join(repr(c)[1:-1] if ord(c) < 32 else c for c in brutti)
        p.append("caratteri che Windows rifiuta: %s" % mostra)
    if any(0xD800 <= ord(c) <= 0xDFFF for c in nome):
        p.append("caratteri non leggibili nel nome")
    if nome != nome.rstrip(" ."):
        p.append("finisce con uno spazio o un punto")
    if nome != nome.lstrip(" "):
        p.append("comincia con uno spazio")
    base = nome.split(".")[0].rstrip(" ").lower()
    if nome.lower() in RISERVATI or base in RISERVATI:
        p.append("nome riservato di Windows")
    if nome.startswith("~$"):
        p.append("file temporaneo di Office (comincia con ~$)")
    if "_vti_" in nome.lower():
        p.append("OneDrive rifiuta «_vti_» nel nome")
    if len(nome) > TETTO_NOME:
        p.append("nome di %d caratteri, il tetto è %d" % (len(nome), TETTO_NOME))
    return p


def e_copia(nome):
    radice, _ = os.path.splitext(nome)
    return bool(RE_COPIA.search(radice))


def e_nascosto(nome):
    return nome.startswith(".") or nome.lower() in SISTEMA


def attributi(st):
    return getattr(st, "st_file_attributes", 0) or 0


def solo_cloud(st):
    a = attributi(st)
    if a & (ATTR_OFFLINE | ATTR_RECALL_ON_OPEN | ATTR_RECALL_ON_DATA_ACCESS):
        return True
    return bool((getattr(st, "st_flags", 0) or 0) & SF_DATALESS)


def nascosto_da_attributi(st):
    return bool(attributi(st) & (ATTR_HIDDEN | ATTR_SYSTEM))


def collegamento_cartella(voce, st):
    """Vero per un collegamento o una giunzione: non ci si entra."""
    if voce.is_symlink():
        return True
    giunzione = getattr(voce, "is_junction", None)
    if giunzione is not None:
        try:
            if giunzione():
                return True
        except OSError:
            pass
    if attributi(st) & ATTR_REPARSE and getattr(st, "st_reparse_tag", 0) in (TAG_JUNCTION, TAG_SYMLINK):
        return True
    return False


def e_studio(cartella):
    return os.path.isfile(os.path.join(cartella, "AGENTS.md")) and os.path.isdir(os.path.join(cartella, "grafi"))


# ---------------------------------------------------------------- giro

def gira(radice, massimo, avvisi):
    """Restituisce (file, cartelle, vuote, saltati, completo).
    file: lista di dict {rel, byte, mtime, cloud}; cartelle: lista di rel."""
    file, cartelle, vuote = [], [], []
    saltati = Counter()
    completo = True
    pila = [""]
    while pila:
        rel_dir = pila.pop()
        assoluta = os.path.join(radice, rel_dir) if rel_dir else radice
        try:
            with os.scandir(assoluta) as it:
                voci = sorted(it, key=lambda v: v.name)
        except OSError:
            saltati["cartelle che non si leggono"] += 1
            continue
        studio = e_studio(assoluta)
        figli_visti = 0
        sotto = []
        for voce in voci:
            nome = voce.name
            rel = nome if not rel_dir else rel_dir + "/" + nome
            if studio and nome.lower() in VOCI_STUDIO:
                saltati["voci della cartella dello studio"] += 1
                figli_visti += 1
                continue
            try:
                st = voce.stat(follow_symlinks=False)
            except OSError:
                saltati["voci che non si leggono"] += 1
                continue
            figli_visti += 1
            if voce.is_symlink():
                saltati["collegamenti (non seguiti)"] += 1
                continue
            if e_nascosto(nome) or nascosto_da_attributi(st):
                saltati["nascosti o di sistema"] += 1
                continue
            if stat.S_ISDIR(st.st_mode):
                if collegamento_cartella(voce, st):
                    saltati["collegamenti (non seguiti)"] += 1
                    continue
                cartelle.append(rel)
                sotto.append(rel)
            elif stat.S_ISREG(st.st_mode):
                if len(file) >= massimo:
                    completo = False
                    continue
                file.append({"rel": rel, "byte": st.st_size, "mtime": st.st_mtime, "cloud": solo_cloud(st)})
            else:
                saltati["altre voci (non file)"] += 1
        if rel_dir and figli_visti == 0:
            vuote.append(rel_dir)
        pila.extend(reversed(sotto))
    if not completo:
        avvisi.append("ho guardato i primi %s file: la cartella ne ha di più. I numeri valgono per quelli."
                      % numero(massimo))
    return file, cartelle, vuote, saltati, completo


# ---------------------------------------------------------------- doppioni

def impronta(percorso, quanti=None):
    h = hashlib.sha256()
    letti = 0
    with open(percorso, "rb") as f:
        while True:
            if quanti is not None and letti >= quanti:
                break
            pezzo = f.read(1024 * 1024 if quanti is None else min(1024 * 1024, quanti - letti))
            if not pezzo:
                break
            h.update(pezzo)
            letti += len(pezzo)
    return h.hexdigest(), letti


def doppioni(radice, file, tetto_mb):
    per_misura = defaultdict(list)
    for f in file:
        if f["byte"] > 0:
            per_misura[f["byte"]].append(f)
    non_controllati = Counter()
    budget = tetto_mb * 1024 * 1024
    letti = 0
    gruppi = []
    for misura in sorted(per_misura, reverse=True):
        candidati = per_misura[misura]
        if len(candidati) < 2:
            continue
        buoni = []
        for f in candidati:
            if f["cloud"]:
                non_controllati["solo sul cloud"] += 1
            elif misura > TETTO_HASH_FILE:
                non_controllati["troppo grandi"] += 1
            else:
                buoni.append(f)
        if len(buoni) < 2:
            continue
        if letti + misura * len(buoni) > budget:
            non_controllati["oltre il tetto di lettura"] += len(buoni)
            continue
        per_testa = defaultdict(list)
        for f in buoni:
            try:
                h, n = impronta(os.path.join(radice, f["rel"]), TESTA_HASH)
                letti += n
                per_testa[h].append(f)
            except OSError:
                non_controllati["non si aprono (forse aperti in un altro programma)"] += 1
        for stessi in per_testa.values():
            if len(stessi) < 2:
                continue
            per_tutto = defaultdict(list)
            for f in stessi:
                if misura <= TESTA_HASH:
                    per_tutto["testa"].append(f)
                    continue
                try:
                    h, n = impronta(os.path.join(radice, f["rel"]))
                    letti += n
                    per_tutto[h].append(f)
                except OSError:
                    non_controllati["non si aprono (forse aperti in un altro programma)"] += 1
            for g in per_tutto.values():
                if len(g) > 1:
                    gruppi.append({"byte": misura, "file": sorted(x["rel"] for x in g)})
    gruppi.sort(key=lambda g: (-g["byte"] * (len(g["file"]) - 1), g["file"][0]))
    in_piu = sum(len(g["file"]) - 1 for g in gruppi)
    return {
        "gruppi": gruppi,
        "file_in_piu": in_piu,
        "byte_in_piu": sum(g["byte"] * (len(g["file"]) - 1) for g in gruppi),
        "non_controllati": dict(non_controllati),
        "mb_letti": round(letti / 1024 / 1024, 1),
    }


# ---------------------------------------------------------------- nomi dei file

def parole(testo):
    return [p for p in re.split(r"[^\w]+", testo.lower()) if p]


def schemi_nomi(file, esempi):
    n = len(file) or 1
    conta = Counter()
    es = defaultdict(list)
    parole_file = Counter()
    sep = Counter()
    maiuscole = Counter()

    def segna(chiave, rel):
        conta[chiave] += 1
        if len(es[chiave]) < esempi:
            es[chiave].append(rel)

    for f in file:
        rel = f["rel"]
        nome = rel.rsplit("/", 1)[-1]
        radice, _ = os.path.splitext(nome)
        for etichetta, rx in SCHEMI_DATA:
            m = rx.search(radice)
            if m:
                dove = "all'inizio" if m.start() == 0 else ("alla fine" if m.end() == len(radice) else "in mezzo")
                segna("%s %s" % (etichetta, dove), rel)
                break
        if RE_NUMERO_INIZIO.match(radice):
            segna("un numero all'inizio", rel)
        pz = set(parole(radice))
        if pz & PAROLE_VERSIONE:
            segna("una parola di versione (def, finale, bozza, v1...)", rel)
        pezzi = rel.split("/")[:-1]
        if pezzi:
            padre = pezzi[-1].lower()
            if len(padre) >= 3 and padre in radice.lower():
                segna("il nome della cartella che lo contiene", rel)
            elif len(pezzi) > 1 and len(pezzi[0]) >= 3 and pezzi[0].lower() in radice.lower():
                segna("il nome della cartella di primo livello", rel)
        for p in pz:
            if len(p) >= 3 and not p.isdigit() and p not in PAROLE_VUOTE:
                parole_file[p] += 1
        sep["spazi" if " " in radice else "nessuno spazio"] += 1
        if "_" in radice:
            sep["trattini bassi"] += 1
        if "-" in radice:
            sep["trattini"] += 1
        lettere = [c for c in radice if c.isalpha()]
        if lettere and all(c.islower() for c in lettere):
            maiuscole["tutto minuscolo"] += 1
        elif lettere and all(c.isupper() for c in lettere):
            maiuscole["tutto maiuscolo"] += 1
        elif lettere:
            maiuscole["misto"] += 1
    schemi = [{"schema": k, "file": v, "per_cento": round(100 * v / n), "esempi": es[k]}
              for k, v in conta.most_common()]
    soglia = max(3, int(0.05 * len(file)))
    ricorrenti = [{"parola": p, "file": c} for p, c in parole_file.most_common(15) if c >= soglia]
    return {"schemi": schemi, "parole_ricorrenti": ricorrenti,
            "separatori": dict(sep), "maiuscole": dict(maiuscole)}


def nomi_problematici(radice, file, cartelle):
    out = []
    radice_abs = os.path.abspath(radice)
    per_cartella = defaultdict(dict)
    for rel in cartelle + [f["rel"] for f in file]:
        padre, _, nome = rel.rpartition("/")
        chiave = unicodedata.normalize("NFC", nome).casefold()
        altro = per_cartella[padre].get(chiave)
        motivi = list(problemi_nome(nome))
        if altro is not None:
            motivi.append("su Windows e OneDrive si scontra con «%s» (cambia solo per maiuscole)" % altro)
        else:
            per_cartella[padre][chiave] = nome
        if e_copia(nome):
            motivi.append("sembra una copia («Copia di», «(1)»)")
        lungo = len(os.path.join(radice_abs, *rel.split("/")))
        if lungo > TETTO_PERCORSO:
            motivi.append("percorso di %d caratteri, Windows ne regge %d" % (lungo, TETTO_PERCORSO))
        if motivi:
            out.append({"file": rel, "problemi": motivi})
    return out


CATEGORIE = [("caratteri che", "caratteri che Windows rifiuta"), ("caratteri non", "caratteri non leggibili"),
             ("finisce", "spazio o punto in fondo"), ("comincia", "spazio all'inizio"),
             ("nome riservato", "nomi riservati di Windows"), ("file temporaneo", "file temporanei di Office"),
             ("onedrive", "rifiutati da OneDrive"), ("nome di", "nomi troppo lunghi"),
             ("su windows", "doppi per maiuscole"), ("sembra una copia", "copie"),
             ("percorso", "percorsi troppo lunghi")]


def categoria(motivo):
    m = motivo.lower()
    for inizio, nome in CATEGORIE:
        if m.startswith(inizio):
            return nome
    return "altro"


# ---------------------------------------------------------------- insieme

def data_locale(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def inventario(cartella, massimo=MASSIMO_FILE, con_doppioni=True, tetto_mb=TETTO_HASH_TOTALE_MB,
               elenco=False, esempi=3):
    radice = os.path.abspath(os.path.expanduser(cartella))
    if not os.path.exists(radice):
        raise Errore(2, "La cartella %s non c'è." % radice)
    if not os.path.isdir(radice):
        raise Errore(2, "%s è un file, non una cartella: per un file basta guardarne l'inizio." % radice)
    try:
        os.listdir(radice)
    except OSError as e:
        raise Errore(2, "Non riesco a leggere %s (%s)." % (radice, e.strerror or e))
    avvisi = []
    file, cartelle, vuote, saltati, completo = gira(radice, massimo, avvisi)
    cap = None if elenco else MAX_ELENCO

    def taglia(lista):
        return lista if cap is None else lista[:cap]

    tipi = Counter()
    byte_tipo = Counter()
    for f in file:
        est = os.path.splitext(f["rel"])[1].lower() or "(senza estensione)"
        tipi[est] += 1
        byte_tipo[est] += f["byte"]
    profondita = max([r.count("/") + 1 for r in cartelle + [f["rel"] for f in file]] or [0])
    vecchio = min(file, key=lambda f: f["mtime"]) if file else None
    recente = max(file, key=lambda f: f["mtime"]) if file else None
    per_anno = Counter(datetime.datetime.fromtimestamp(f["mtime"]).year for f in file)
    primo = Counter()
    sciolti = 0
    for f in file:
        if "/" in f["rel"]:
            primo[f["rel"].split("/")[0]] += 1
        else:
            sciolti += 1
    livello1 = sorted(c for c in cartelle if "/" not in c)
    livelli = Counter(c.count("/") + 1 for c in cartelle)
    grandi = sorted((f for f in file if f["byte"] >= GRANDE_BYTE), key=lambda f: -f["byte"])
    problemi = nomi_problematici(radice, file, cartelle)
    cloud = sum(1 for f in file if f["cloud"])
    if cloud:
        avvisi.append("%s file stanno solo sul cloud: non li ho aperti, per non scaricarli." % numero(cloud))
    dop = doppioni(radice, file, tetto_mb) if con_doppioni else None
    if dop is not None:
        nc = sum(dop["non_controllati"].values())
        if nc:
            avvisi.append("%s file della stessa dimensione di un altro non li ho confrontati (%s)."
                          % (numero(nc), ", ".join("%s %s" % (v, k) for k, v in dop["non_controllati"].items())))
        tutti = len(dop["gruppi"])
        dop["gruppi_in_tutto"] = tutti
        dop["gruppi"] = taglia(dop["gruppi"])
    conta_problemi = Counter(categoria(m) for p in problemi for m in p["problemi"])
    out = {
        "cartella": radice,
        "quando": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "completo": completo,
        "file": len(file),
        "cartelle": len(cartelle),
        "profondita": profondita,
        "byte": sum(f["byte"] for f in file),
        "tipi": [{"estensione": e, "file": n, "byte": byte_tipo[e]} for e, n in tipi.most_common()],
        "date": {
            "nota": "data di modifica dei file",
            "piu_vecchia": {"data": data_locale(vecchio["mtime"]), "file": vecchio["rel"]} if vecchio else None,
            "piu_recente": {"data": data_locale(recente["mtime"]), "file": recente["rel"]} if recente else None,
            "per_anno": {str(a): per_anno[a] for a in sorted(per_anno)},
        },
        "struttura": {
            "cartelle_per_livello": {str(k): livelli[k] for k in sorted(livelli)},
            "primo_livello": taglia([{"nome": c, "file": primo.get(c, 0)} for c in livello1]),
            "primo_livello_in_tutto": len(livello1),
            "file_sciolti_in_cima": sciolti,
            "primo_livello_sono_anni": bool(livello1) and all(re.fullmatch(r"(19|20)\d\d", c) for c in livello1),
        },
        "nomi": schemi_nomi(file, esempi),
        "doppioni": dop,
        "cartelle_vuote": taglia(sorted(vuote)),
        "cartelle_vuote_in_tutto": len(vuote),
        "file_grandi": taglia([{"file": f["rel"], "byte": f["byte"]} for f in grandi]),
        "file_grandi_in_tutto": len(grandi),
        "soglia_file_grandi_mb": GRANDE_BYTE // (1024 * 1024),
        "nomi_problematici": taglia(problemi),
        "nomi_problematici_in_tutto": len(problemi),
        "nomi_problematici_per_motivo": dict(conta_problemi),
        "solo_cloud": cloud,
        "saltati": dict(saltati),
        "avvisi": avvisi,
    }
    if elenco:
        out["elenco"] = [{"file": f["rel"], "byte": f["byte"],
                          "modificato": datetime.datetime.fromtimestamp(f["mtime"]).strftime("%Y-%m-%d %H:%M")}
                         for f in file]
    return out


# ---------------------------------------------------------------- testo

def numero(n):
    return "{:,}".format(n).replace(",", ".")


def misura(b):
    for unita, quanto in (("GB", 1024 ** 3), ("MB", 1024 ** 2), ("KB", 1024)):
        if b >= quanto:
            return ("%.1f %s" % (b / quanto, unita)).replace(".", ",")
    return "%d byte" % b


def data_a_voce(testo):
    a, m, g = testo.split("-")
    return "%d %s %s" % (int(g), MESI[int(m) - 1], a)


def testo(inv):
    r = ["Cartella: %s" % inv["cartella"]]
    r.append("File: %s in %s cartelle, fino a %d livelli. In tutto %s."
             % (numero(inv["file"]), numero(inv["cartelle"]), inv["profondita"], misura(inv["byte"])))
    if inv["tipi"]:
        t = " · ".join("%s %s" % (x["estensione"].lstrip("."), numero(x["file"])) for x in inv["tipi"][:6])
        altri = sum(x["file"] for x in inv["tipi"][6:])
        r.append("Tipi: %s%s" % (t, " · altri %s" % numero(altri) if altri else ""))
    d = inv["date"]
    if d["piu_vecchia"]:
        r.append("Date (di modifica): dal %s al %s. Per anno: %s" % (
            data_a_voce(d["piu_vecchia"]["data"]), data_a_voce(d["piu_recente"]["data"]),
            " · ".join("%s %s" % (a, numero(n)) for a, n in d["per_anno"].items())))
    s = inv["struttura"]
    if s["primo_livello_in_tutto"]:
        nomi = ", ".join(x["nome"] for x in s["primo_livello"][:8])
        r.append("Primo livello: %s cartelle (%s%s)%s, %s file sciolti in cima." % (
            numero(s["primo_livello_in_tutto"]), nomi, "..." if s["primo_livello_in_tutto"] > 8 else "",
            ", sono anni" if s["primo_livello_sono_anni"] else "", numero(s["file_sciolti_in_cima"])))
    n = inv["nomi"]
    if n["schemi"]:
        r.append("Nei nomi: " + " · ".join("%s %d%%" % (x["schema"], x["per_cento"]) for x in n["schemi"][:5]))
    if n["parole_ricorrenti"]:
        r.append("Parole ricorrenti: " + " · ".join("%s %s" % (x["parola"], numero(x["file"]))
                                                   for x in n["parole_ricorrenti"][:8]))
    dop = inv["doppioni"]
    if dop is None:
        r.append("Doppioni: non cercati.")
    elif dop["gruppi_in_tutto"]:
        r.append("Doppioni: %s gruppi di file uguali, %s file in più, %s. Non ho cancellato niente." % (
            numero(dop["gruppi_in_tutto"]), numero(dop["file_in_piu"]), misura(dop["byte_in_piu"])))
    else:
        r.append("Doppioni: nessuno.")
    r.append("Cartelle vuote: %s." % numero(inv["cartelle_vuote_in_tutto"]))
    if inv["file_grandi_in_tutto"]:
        r.append("File oltre %d MB: %s." % (inv["soglia_file_grandi_mb"], numero(inv["file_grandi_in_tutto"])))
    if inv["nomi_problematici_in_tutto"]:
        r.append("Nomi da sistemare: %s (%s)." % (numero(inv["nomi_problematici_in_tutto"]), ", ".join(
            "%s %s" % (k, v) for k, v in sorted(inv["nomi_problematici_per_motivo"].items(), key=lambda x: -x[1]))))
    if inv["saltati"]:
        r.append("Saltati: " + ", ".join("%s %s" % (v, k) for k, v in inv["saltati"].items()) + ".")
    for a in inv["avvisi"]:
        r.append("Avviso: %s" % a)
    return "\n".join(r) + "\n"


# ---------------------------------------------------------------- comando

AIUTO = __doc__.split("\n\n", 1)[1]


def leggi_argomenti(argv):
    a = {"cartella": None, "testo": False, "elenco": False, "massimo": MASSIMO_FILE,
         "doppioni": True, "tetto_mb": TETTO_HASH_TOTALE_MB}
    i = 0
    while i < len(argv):
        x = argv[i]
        i += 1
        if x in ("-h", "--help"):
            sys.stdout.write("Uso: python3 inventario.py CARTELLA [opzioni]\n\n" + AIUTO)
            sys.exit(0)
        elif x == "--testo":
            a["testo"] = True
        elif x == "--elenco":
            a["elenco"] = True
        elif x == "--senza-doppioni":
            a["doppioni"] = False
        elif x in ("--massimo", "--tetto-doppioni-mb"):
            if i >= len(argv) or not argv[i].isdigit() or int(argv[i]) < 1:
                raise Errore(1, "Dopo %s serve un numero intero positivo." % x)
            a["massimo" if x == "--massimo" else "tetto_mb"] = int(argv[i])
            i += 1
        elif x.startswith("-") and len(x) > 1:
            raise Errore(1, "Opzione sconosciuta: %s. Guarda --help." % x)
        elif a["cartella"] is None:
            a["cartella"] = x
        else:
            raise Errore(1, "La cartella è una sola: ho letto anche «%s»." % x)
    if not a["cartella"]:
        raise Errore(1, "Manca la cartella. Esempio: inventario.py \"C:\\Users\\Studio\\Pratiche\" --testo")
    return a


def prepara_uscita():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv):
    prepara_uscita()
    try:
        a = leggi_argomenti(argv)
        inv = inventario(a["cartella"], a["massimo"], a["doppioni"], a["tetto_mb"], a["elenco"])
        if a["testo"]:
            sys.stdout.write(testo(inv))
        else:
            sys.stdout.write(json.dumps(inv, ensure_ascii=False, indent=1) + "\n")
        return 0
    except Errore as e:
        sys.stderr.write("errore: %s\n" % e.testo)
        return e.codice
    except KeyboardInterrupt:
        sys.stderr.write("errore: fermato a metà. Non ho scritto niente.\n")
        return 1
    except Exception as e:  # mai un traceback all'utente
        sys.stderr.write("errore: qualcosa non è andato (%s: %s). Non ho scritto niente.\n" % (type(e).__name__, e))
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
