# redacy 0.3.1 · skills/crea-grafo/scripts/controlla-grafo.py
"""Controlla i grafi (grafi/<nome>.yaml) contro il formato di redacy.

Si usa da riga di comando (controlla-grafo.py <file|cartella>) e si può
importare per percorso (importlib): controlla_file(percorso) restituisce
(errori, avvisi), due liste di testi.
"""

import datetime
import difflib
import importlib
import os
import re
import sys

AIUTO = """Uso: python3 controlla-grafo.py FILE.yaml|CARTELLA [...]

Controlla che un grafo rispetti il formato: campi obbligatori e sconosciuti,
tipi, nomi, innesco, passi (id unici, "dopo" verso passi scritti prima,
nessun ciclo, almeno un passo agente), tetti, autonomia e prove.
Per una cartella controlla tutti i file .yaml direttamente dentro, senza
scendere nelle sottocartelle.

Ogni errore dice file, riga, campo, cosa non va e cosa fare. Gli avvisi
("avviso: ...") non fermano: un workspace che non c'è ancora, un orario
senza fuso.

Opzioni:
  -h, --help   mostra questo aiuto

Uscite: 0 nessun errore (gli avvisi non contano); 1 almeno un errore."""

_cartella = os.path.dirname(os.path.abspath(__file__))
if _cartella not in sys.path:
    sys.path.insert(0, _cartella)
yl = importlib.import_module("yaml_ridotto")

KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATA = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
FUSO = re.compile(r"\b[A-Z][A-Za-z]+/[A-Za-z_]+(/[A-Za-z_]+)?\b|\bUTC\b|\bGMT\b|[+-][0-9]{2}:?[0-9]{2}\b")
VIETATI_COMANDO = ";|&`$<>"

CAMPI_GRAFO = ("grafo", "versione", "obiettivo", "descrizione", "acceso", "innesco",
               "passi", "tetti", "uscite", "autonomia", "prove")
OBBLIGATORI_GRAFO = ("grafo", "versione", "obiettivo", "acceso", "innesco",
                     "passi", "tetti", "uscite", "autonomia")
SUGGERIMENTI = {
    "grafo": "scrivi `grafo: <nome-del-file>` (kebab-case, senza .yaml)",
    "versione": "scrivi `versione: 1`",
    "obiettivo": "scrivi `obiettivo: ...` in una riga, al massimo 200 caratteri",
    "acceso": "scrivi `acceso: false` (o `true` se deve partire da solo)",
    "innesco": "aggiungi il blocco `innesco` con `tipo: parola` (oppure `orario` o `evento`)",
    "passi": "aggiungi la lista `passi`, con almeno un passo di tipo agente",
    "tetti": "aggiungi il blocco `tetti` con `contemporanee: 1`",
    "uscite": "scrivi `uscite: []` se non produce niente fuori dalla corsa",
    "autonomia": "aggiungi il blocco `autonomia` con `livello: L0`, `da: AAAA-MM-GG` e `si: null`",
}

TIPI_INNESCO = ("parola", "orario", "evento")
CAMPI_INNESCO = ("tipo", "quando", "fatto", "file")
TIPI_PASSO = ("cli", "agente", "umano", "uscita")
CAMPI_PASSO = ("id", "tipo", "nome", "descrizione", "dopo", "comando", "minuti",
               "workspace", "prompt", "modello", "forma", "dove")
SOLO_PER = {
    "comando": ("cli",),
    "minuti": ("cli", "agente"),
    "workspace": ("agente",),
    "prompt": ("agente",),
    "modello": ("agente",),
    "forma": ("umano", "uscita"),
    "dove": ("umano", "uscita"),
}
OBBLIGATORI_PASSO = {
    "cli": ("comando",),
    "agente": ("workspace", "prompt"),
    "umano": ("forma", "dove"),
    "uscita": ("forma", "dove"),
}
FORME_UMANO = ("decisione", "lettura", "invio", "fatto")
MODELLI = ("forte", "media", "leggera")
CAMPI_TETTI = ("contemporanee", "corse_al_giorno", "corse_a_settimana", "finestra_minuti")
CAMPI_AUTONOMIA = ("livello", "da", "si")
LIVELLI = ("L0", "L1", "L2")
CAMPI_PROVA = ("data", "esito_atteso", "input")


def _nome_tipo(v):
    if v is None:
        return "vuoto"
    if isinstance(v, bool):
        return "vero/falso"
    if isinstance(v, int):
        return "un numero intero"
    if isinstance(v, float):
        return "un numero con la virgola"
    if isinstance(v, str):
        return "un testo"
    if isinstance(v, list):
        return "una lista"
    if isinstance(v, dict):
        return "un blocco con sottocampi"
    return "un valore strano"


def _intero(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _data_valida(v):
    if not isinstance(v, str) or not DATA.match(v):
        return False
    try:
        datetime.date.fromisoformat(v)
    except ValueError:
        return False
    return True


def _percorso_relativo_ok(v):
    return not (v.startswith("/") or v.startswith("~") or re.match(r"^[A-Za-z]:[\\/]", v)
                or ".." in v.replace("\\", "/").split("/"))


def _cartella_studio(percorso):
    d = os.path.dirname(os.path.realpath(percorso))
    while True:
        if os.path.isfile(os.path.join(d, "AGENTS.md")) and os.path.isdir(os.path.join(d, "grafi")):
            return d
        su = os.path.dirname(d)
        if su == d:
            return None
        d = su


class _Controllo:
    def __init__(self, percorso, g):
        self.file = percorso
        self.g = g
        self.errori = []  # (riga, testo)
        self.avvisi = []
        self.workspace = []  # (riga, campo, nome)

    # --- messaggi
    def err(self, riga, campo, cosa, fare):
        self.errori.append((riga or 1, "%s:%s: %s: %s. Cosa fare: %s" % (self.file, riga or 1, campo, cosa, fare)))

    def avv(self, riga, campo, cosa, fare):
        self.avvisi.append((riga or 1, "%s:%s: %s: %s. Cosa fare: %s" % (self.file, riga or 1, campo, cosa, fare)))

    def r(self, *percorso):
        return yl.riga(self.g, *percorso) or 1

    # --- pezzi comuni
    def sconosciuti(self, m, ammessi, base, percorso):
        for k in m:
            if k not in ammessi:
                vicino = difflib.get_close_matches(str(k), ammessi, n=1)
                fare = "toglilo"
                if vicino:
                    fare = "correggi il nome (forse intendevi `%s`) o toglilo" % vicino[0]
                self.err(self.r(*(tuple(percorso) + (k,))), (base + "." if base else "") + str(k),
                         "campo sconosciuto, non fa parte del formato",
                         "%s; i campi ammessi qui sono: %s" % (fare, ", ".join(ammessi)))

    def testo(self, m, k, base, percorso, obbligatorio=True, massimo=None, una_riga=False, fare=None):
        """Controlla un campo di testo. Restituisce il testo se è valido, altrimenti None."""
        campo = (base + "." if base else "") + k
        riga = self.r(*(tuple(percorso) + (k,)))
        if k not in m:
            if obbligatorio:
                self.err(self.r(*percorso) if percorso else 1, campo, "manca il campo obbligatorio", fare or "aggiungilo")
            return None
        v = m[k]
        if not isinstance(v, str) or not v.strip():
            self.err(riga, campo, "dev'essere un testo non vuoto e c'è %s" % _nome_tipo(v), fare or "scrivi un testo")
            return None
        if una_riga and "\n" in v.strip():
            self.err(riga, campo, "dev'essere su una riga sola", "scrivilo in una riga")
            return None
        if massimo and len(v.strip()) > massimo:
            self.err(riga, campo, "è lungo %d caratteri e il massimo è %d" % (len(v.strip()), massimo),
                     "accorcialo a %d caratteri o meno" % massimo)
            return None
        return v

    def numero(self, m, k, base, percorso, minimo=1, massimo=None, obbligatorio=False):
        campo = (base + "." if base else "") + k
        riga = self.r(*(tuple(percorso) + (k,)))
        if k not in m:
            if obbligatorio:
                self.err(self.r(*percorso), campo, "manca il campo obbligatorio", "scrivilo, per esempio `%s: 1`" % k)
            return None
        v = m[k]
        if not _intero(v):
            self.err(riga, campo, "dev'essere un numero intero e c'è %s" % _nome_tipo(v), "scrivi un numero intero, per esempio `%s: 1`" % k)
            return None
        if v < minimo or (massimo is not None and v > massimo):
            lim = "da %d a %d" % (minimo, massimo) if massimo is not None else "%d o più" % minimo
            self.err(riga, campo, "vale %d ma deve essere %s" % (v, lim), "scrivi un numero %s" % lim)
            return None
        return v

    # --- il grafo
    def controlla(self):
        g = self.g
        self.sconosciuti(g, CAMPI_GRAFO, "", ())
        for k in OBBLIGATORI_GRAFO:
            if k not in g:
                self.err(1, k, "manca il campo obbligatorio", SUGGERIMENTI[k])
        if "grafo" in g:
            nome = g["grafo"]
            riga = self.r("grafo")
            if not isinstance(nome, str) or not KEBAB.match(nome):
                self.err(riga, "grafo", "il nome dev'essere in kebab-case (minuscole, numeri e trattini) e c'è %s" % (
                    repr(nome) if isinstance(nome, str) else _nome_tipo(nome)),
                    "scrivi un nome come `giro-posta-mattina`")
            else:
                attesto = os.path.splitext(os.path.basename(self.file))[0]
                if nome != attesto:
                    self.err(riga, "grafo", "il nome del grafo (%s) è diverso dal nome del file (%s)" % (nome, attesto),
                             "fai coincidere i due: rinomina il file in %s.yaml o scrivi `grafo: %s`" % (nome, attesto))
        if "versione" in g:
            v = g["versione"]
            if not _intero(v) or v < 1:
                self.err(self.r("versione"), "versione", "dev'essere un numero intero da 1 in su", "scrivi `versione: 1`")
        self.testo(g, "obiettivo", "", (), obbligatorio=False, massimo=200, una_riga=True,
                   fare="scrivi in una riga a cosa serve, al massimo 200 caratteri")
        self.testo(g, "descrizione", "", (), obbligatorio=False)
        if "acceso" in g and not isinstance(g["acceso"], bool):
            self.err(self.r("acceso"), "acceso", "dev'essere true o false e c'è %s" % _nome_tipo(g["acceso"]),
                     "scrivi `acceso: false` o `acceso: true`")
        tipo_innesco = self.innesco() if "innesco" in g else None
        if "passi" in g:
            self.passi()
        if "tetti" in g:
            self.tetti(tipo_innesco)
        if "uscite" in g:
            self.uscite()
        if "autonomia" in g:
            self.autonomia()
        if "prove" in g:
            self.prove()
        self.avvisi_workspace()

    # --- innesco
    def innesco(self):
        m = self.g["innesco"]
        base = ("innesco",)
        if not isinstance(m, yl.Mappa):
            self.err(self.r("innesco"), "innesco", "dev'essere un blocco con almeno `tipo` e c'è %s" % _nome_tipo(m),
                     "scrivi `innesco: {tipo: parola}`")
            return None
        self.sconosciuti(m, CAMPI_INNESCO, "innesco", base)
        tipo = m.get("tipo")
        valido = isinstance(tipo, str) and tipo in TIPI_INNESCO
        if "tipo" not in m:
            self.err(self.r("innesco"), "innesco.tipo", "manca il campo obbligatorio", "scrivi `tipo: parola`, `tipo: orario` o `tipo: evento`")
        elif not valido:
            self.err(self.r("innesco", "tipo"), "innesco.tipo", "vale %r ma i tipi sono parola, orario ed evento" % (tipo,),
                     "scegli uno dei tre")
        dovuto = {"quando": "orario", "fatto": "evento", "file": "evento"}
        for k in ("quando", "fatto", "file"):
            if not valido:
                break
            if tipo == dovuto[k]:
                self.testo(m, k, "innesco", base, fare="aggiungilo: serve a un innesco di tipo %s" % tipo)
            elif k in m:
                self.err(self.r("innesco", k), "innesco." + k, "non serve a un innesco di tipo %s" % tipo,
                         "toglilo, oppure cambia `tipo` in %s" % dovuto[k])
        if valido and tipo == "orario" and isinstance(m.get("quando"), str) and m["quando"].strip():
            if not FUSO.search(m["quando"]):
                self.avv(self.r("innesco", "quando"), "innesco.quando", "l'orario non dice il fuso",
                         "aggiungilo in fondo, per esempio \"ogni giorno alle 21:00 Europe/Rome\"")
        if valido and tipo == "evento":
            if isinstance(m.get("fatto"), str) and m["fatto"].strip() and not KEBAB.match(m["fatto"]):
                self.err(self.r("innesco", "fatto"), "innesco.fatto", "dev'essere in kebab-case e c'è %r" % m["fatto"],
                         "scrivi il fatto con minuscole e trattini, come `nuova-fattura`")
            f = m.get("file")
            if isinstance(f, str) and f.strip() and not _percorso_relativo_ok(f):
                self.err(self.r("innesco", "file"), "innesco.file", "dev'essere un percorso relativo alla cartella dello studio e c'è %r" % f,
                         "scrivi un percorso che parte dalla cartella dello studio, come `fonti/fatture/*.pdf`")
        return tipo if valido else None

    # --- passi
    def passi(self):
        passi = self.g["passi"]
        if not isinstance(passi, yl.Lista) or len(passi) == 0:
            self.err(self.r("passi"), "passi", "dev'essere una lista con almeno un passo",
                     "aggiungi i passi, ognuno con `- id: ...` e `tipo: ...`")
            return
        tutti = set()
        for p in passi:
            if isinstance(p, dict) and isinstance(p.get("id"), str):
                tutti.add(p["id"])
        visti = {}
        agenti = 0
        for n, p in enumerate(passi):
            riga_p = self.r("passi", n)
            if not isinstance(p, yl.Mappa):
                self.err(riga_p, "passi[%d]" % (n + 1), "ogni passo dev'essere un blocco con `id` e `tipo`",
                         "scrivi `- id: nome-del-passo` e sotto `tipo: agente`")
                continue
            pid = p.get("id")
            lab = "passi[%s]" % pid if isinstance(pid, str) and KEBAB.match(pid) else "passi[%d]" % (n + 1)
            pr = ("passi", n)
            self.sconosciuti(p, CAMPI_PASSO, lab, pr)
            # id
            if "id" not in p:
                self.err(riga_p, lab + ".id", "manca il campo obbligatorio", "dai al passo un `id` in kebab-case")
            elif not isinstance(pid, str) or not KEBAB.match(pid):
                self.err(self.r(*(pr + ("id",))), lab + ".id", "dev'essere in kebab-case e c'è %s" % (
                    repr(pid) if isinstance(pid, str) else _nome_tipo(pid)), "scrivi un id con minuscole e trattini, come `leggi-posta`")
            elif pid in visti:
                self.err(self.r(*(pr + ("id",))), lab + ".id", "id ripetuto: c'è già un passo con id %s alla riga %d" % (pid, visti[pid]),
                         "dai a ogni passo un id diverso")
            else:
                visti[pid] = self.r(*(pr + ("id",)))
            # tipo
            tipo = p.get("tipo")
            valido = isinstance(tipo, str) and tipo in TIPI_PASSO
            if "tipo" not in p:
                self.err(riga_p, lab + ".tipo", "manca il campo obbligatorio", "scrivi `tipo: cli`, `agente`, `umano` o `uscita`")
            elif not valido:
                self.err(self.r(*(pr + ("tipo",))), lab + ".tipo", "vale %r ma i tipi sono cli, agente, umano e uscita" % (tipo,),
                         "scegli uno dei quattro")
            if valido and tipo == "agente":
                agenti += 1
            # nome e descrizione
            self.testo(p, "nome", lab, pr, obbligatorio=False)
            self.testo(p, "descrizione", lab, pr, obbligatorio=False)
            # campi per tipo
            if valido:
                for k, tipi in SOLO_PER.items():
                    if k in p and tipo not in tipi:
                        self.err(self.r(*(pr + (k,))), "%s.%s" % (lab, k), "non si usa nei passi di tipo %s (serve ai passi %s)" % (tipo, " e ".join(tipi)),
                                 "toglilo, oppure cambia il tipo del passo")
                for k in OBBLIGATORI_PASSO[tipo]:
                    if k not in p:
                        self.err(riga_p, "%s.%s" % (lab, k), "manca il campo obbligatorio per un passo di tipo %s" % tipo,
                                 "aggiungi `%s`" % k)
                self.campi_del_tipo(p, tipo, lab, pr)
            # dopo
            self.dopo(p, n, pid, lab, pr, tutti, visti)
        if agenti == 0:
            self.err(self.r("passi"), "passi", "non c'è nessun passo di tipo agente",
                     "aggiungi almeno un passo con `tipo: agente`: è quello che fa il lavoro")
        self.cicli(passi)

    def campi_del_tipo(self, p, tipo, lab, pr):
        if tipo == "cli" and "comando" in p:
            c = self.testo(p, "comando", lab, pr, fare="scrivi un comando, per esempio `python3 .agents/script/prepara-fatture.py`")
            if c is not None:
                trovati = sorted(set(ch for ch in c if ch in VIETATI_COMANDO or ch in "\n\r"))
                if trovati:
                    mostra = " ".join(repr(t)[1:-1] if t in "\n\r" else t for t in trovati)
                    self.err(self.r(*(pr + ("comando",))), lab + ".comando",
                             "il comando contiene caratteri non ammessi (%s): vale un comando solo, senza shell" % mostra,
                             "togli quei caratteri; se servono più comandi, fai più passi")
        if tipo in ("cli", "agente") and "minuti" in p:
            self.numero(p, "minuti", lab, pr, minimo=1, massimo=600)
        if tipo == "agente":
            if "workspace" in p:
                w = self.testo(p, "workspace", lab, pr, fare="scrivi il nome di una cartella di workspace/, o `orchestratore`")
                if w is not None:
                    w = w.strip()
                    if w != "orchestratore" and not KEBAB.match(w):
                        self.err(self.r(*(pr + ("workspace",))), lab + ".workspace",
                                 "dev'essere `orchestratore` o il nome di una cartella di workspace/ in kebab-case, e c'è %r" % w,
                                 "scrivi il nome della cartella con minuscole e trattini")
                    elif w != "orchestratore":
                        self.workspace.append((self.r(*(pr + ("workspace",))), lab + ".workspace", w))
            if "prompt" in p:
                self.prompt(p, lab, pr)
            if "modello" in p and (not isinstance(p["modello"], str) or p["modello"] not in MODELLI):
                self.err(self.r(*(pr + ("modello",))), lab + ".modello", "vale %r ma i modelli sono forte, media e leggera" % (p["modello"],),
                         "scegli uno dei tre, o togli il campo e lascia decidere al programma")
        if tipo in ("umano", "uscita"):
            if "forma" in p:
                if tipo == "umano":
                    if not isinstance(p["forma"], str) or p["forma"] not in FORME_UMANO:
                        self.err(self.r(*(pr + ("forma",))), lab + ".forma",
                                 "per un passo umano vale %r ma le forme sono %s" % (p["forma"], ", ".join(FORME_UMANO)),
                                 "scegli una delle quattro")
                else:
                    self.testo(p, "forma", lab, pr, fare="scrivi che cosa esce, per esempio `bozza`, `promemoria`, `file`")
            if "dove" in p:
                self.testo(p, "dove", lab, pr, fare="scrivi dove si trova la cosa, per esempio `il pannello`")

    def prompt(self, p, lab, pr):
        v = p["prompt"]
        riga = self.r(*(pr + ("prompt",)))
        campo = lab + ".prompt"
        if isinstance(v, yl.Mappa):
            self.sconosciuti(v, ("file",), campo, pr + ("prompt",))
            if "file" not in v:
                self.err(riga, campo + ".file", "manca il campo obbligatorio", "scrivi `{file: percorso.md}`")
            elif not isinstance(v["file"], str) or not v["file"].strip():
                self.err(self.r(*(pr + ("prompt", "file"))), campo + ".file", "dev'essere un percorso e c'è %s" % _nome_tipo(v["file"]),
                         "scrivi il percorso di un file di testo, come `{file: istruzioni/leggi.md}`")
            elif not _percorso_relativo_ok(v["file"]):
                self.err(self.r(*(pr + ("prompt", "file"))), campo + ".file", "dev'essere un percorso relativo alla cartella dello studio e c'è %r" % v["file"],
                         "scrivi un percorso che parte dalla cartella dello studio")
            return
        if not isinstance(v, str) or not v.strip():
            self.err(riga, campo, "dev'essere una skill (`/nome`), un testo breve o `{file: percorso.md}` e c'è %s" % _nome_tipo(v),
                     "scrivi `/nome-della-skill` o poche righe di istruzioni")
        elif len(v.strip()) > 300:
            self.err(riga, campo, "è lungo %d caratteri e il massimo è 300" % len(v.strip()),
                     "accorcialo, oppure mettilo in un file e scrivi `{file: percorso.md}`")

    def dopo(self, p, n, pid, lab, pr, tutti, visti):
        if "dopo" not in p:
            return
        riga = self.r(*(pr + ("dopo",)))
        campo = lab + ".dopo"
        d = p["dopo"]
        if n == 0:
            self.err(riga, campo, "il primo passo non può avere `dopo`: non c'è niente prima",
                     "toglilo")
            return
        if not isinstance(d, yl.Lista):
            self.err(riga, campo, "dev'essere una lista di id e c'è %s" % _nome_tipo(d),
                     "scrivi `dopo: [id-del-passo-prima]`")
            return
        if len(d) == 0:
            self.err(riga, campo, "la lista è vuota",
                     "scrivi gli id dei passi da aspettare, oppure togli `dopo` e il passo segue quello scritto prima")
            return
        gia = set()
        for j, x in enumerate(d):
            rj = self.r(*(pr + ("dopo", j)))
            if not isinstance(x, str):
                self.err(rj, campo, "ogni voce dev'essere l'id di un passo e c'è %s" % _nome_tipo(x), "scrivi l'id di un passo")
            elif x == pid:
                self.err(rj, campo, "un passo non può venire dopo se stesso (%s)" % x, "metti l'id del passo che lo precede")
            elif x in gia:
                self.err(rj, campo, "l'id %s è scritto due volte" % x, "toglilo una volta")
            elif x in visti:
                pass
            elif x in tutti:
                self.err(rj, campo, "il passo %s è scritto dopo questo: `dopo` può puntare solo a passi scritti prima" % x,
                         "sposta più in alto il passo %s, o cambia `dopo`" % x)
            else:
                self.err(rj, campo, "non c'è nessun passo con id %s" % x,
                         "scrivi l'id di un passo che esiste; quelli del grafo sono: %s" % ", ".join(sorted(tutti)) if tutti else "scrivi l'id di un passo che esiste")
            if isinstance(x, str):
                gia.add(x)

    def cicli(self, passi):
        archi = [(a, b) for a, b in yl.archi_del_grafo(self.g) if a != b]
        succ = {}
        for a, b in archi:
            succ.setdefault(a, []).append(b)
        stato = {}
        trovato = []

        def visita(u, pila):
            stato[u] = 1
            pila.append(u)
            for v in succ.get(u, []):
                if trovato:
                    return
                if stato.get(v) == 1:
                    trovato.append(pila[pila.index(v):] + [v])
                    return
                if stato.get(v) is None:
                    visita(v, pila)
            pila.pop()
            stato[u] = 2

        for u in list(succ):
            if stato.get(u) is None and not trovato:
                visita(u, [])
        if trovato:
            giro = trovato[0]
            riga = 1
            for n, p in enumerate(passi):
                if isinstance(p, yl.Mappa) and p.get("id") == giro[0]:
                    riga = self.r("passi", n)
                    break
            self.err(riga, "passi", "c'è un ciclo fra i passi: %s" % " -> ".join(giro),
                     "ogni passo deve venire dopo passi scritti prima: togli una delle frecce del giro")

    # --- tetti, uscite
    def tetti(self, tipo_innesco):
        m = self.g["tetti"]
        if not isinstance(m, yl.Mappa):
            self.err(self.r("tetti"), "tetti", "dev'essere un blocco con almeno `contemporanee` e c'è %s" % _nome_tipo(m),
                     "scrivi `tetti: {contemporanee: 1}`")
            return
        self.sconosciuti(m, CAMPI_TETTI, "tetti", ("tetti",))
        self.numero(m, "contemporanee", "tetti", ("tetti",), minimo=1, obbligatorio=True)
        self.numero(m, "corse_al_giorno", "tetti", ("tetti",), minimo=1)
        self.numero(m, "corse_a_settimana", "tetti", ("tetti",), minimo=1)
        self.numero(m, "finestra_minuti", "tetti", ("tetti",), minimo=1)
        if tipo_innesco in ("orario", "evento") and "corse_al_giorno" not in m and "corse_a_settimana" not in m:
            self.err(self.r("tetti"), "tetti", "con un innesco di tipo %s serve almeno uno fra `corse_al_giorno` e `corse_a_settimana`" % tipo_innesco,
                     "aggiungi, per esempio, `corse_al_giorno: 1`")

    def uscite(self):
        u = self.g["uscite"]
        if not isinstance(u, yl.Lista):
            self.err(self.r("uscite"), "uscite", "dev'essere una lista di testi (anche vuota) e c'è %s" % _nome_tipo(u),
                     "scrivi `uscite: []` oppure una lista di righe `- ...`")
            return
        for j, x in enumerate(u):
            if not isinstance(x, str) or not x.strip():
                self.err(self.r("uscite", j), "uscite[%d]" % (j + 1), "ogni uscita dev'essere un testo non vuoto e c'è %s" % _nome_tipo(x),
                         "scrivi cosa produce il grafo, in una riga")

    # --- autonomia, prove
    def autonomia(self):
        m = self.g["autonomia"]
        if not isinstance(m, yl.Mappa):
            self.err(self.r("autonomia"), "autonomia", "dev'essere un blocco con `livello`, `da` e `si` e c'è %s" % _nome_tipo(m),
                     "scrivi `autonomia: {livello: L0, da: 2026-11-07, si: null}`")
            return
        base = ("autonomia",)
        self.sconosciuti(m, CAMPI_AUTONOMIA, "autonomia", base)
        riga_a = self.r("autonomia")
        livello = m.get("livello")
        liv_ok = isinstance(livello, str) and livello in LIVELLI
        if "livello" not in m:
            self.err(riga_a, "autonomia.livello", "manca il campo obbligatorio", "scrivi `livello: L0` (L0 prepara e basta)")
        elif not liv_ok:
            self.err(self.r("autonomia", "livello"), "autonomia.livello", "vale %r ma i livelli sono L0, L1 e L2" % (livello,),
                     "scegli uno dei tre")
        if "da" not in m:
            self.err(riga_a, "autonomia.da", "manca il campo obbligatorio", "scrivi la data di questo livello, `da: AAAA-MM-GG`")
        elif not _data_valida(m["da"]):
            self.err(self.r("autonomia", "da"), "autonomia.da", "dev'essere una data AAAA-MM-GG e c'è %r" % (m["da"],),
                     "scrivi una data vera, come 2026-11-07")
        si = None
        if "si" not in m:
            self.err(riga_a, "autonomia.si", "manca il campo obbligatorio", "scrivi `si: null` se non hai ancora dato il tuo sì, altrimenti chi e dove")
        else:
            si = m["si"]
            if si is not None:
                si = self.testo(m, "si", "autonomia", base, massimo=120, una_riga=True,
                                fare="scrivi chi ha dato il sì e dove, in una riga, oppure `si: null`")
        riga_si = self.r("autonomia", "si") if "si" in m else riga_a
        if "si" in m and m["si"] is None:
            if liv_ok and livello != "L0":
                self.err(riga_si, "autonomia.si", "il livello %s vuole il tuo sì scritto e `si` è null" % livello,
                         "scrivi in `si` chi ha dato il sì e dove, oppure torna a `livello: L0`")
            if self.g.get("acceso") is True:
                self.err(self.r("acceso"), "acceso", "il grafo è acceso ma `autonomia.si` è null: un grafo acceso vuole il tuo sì scritto",
                         "scrivi in `autonomia.si` chi ha dato il sì e dove, oppure metti `acceso: false`")

    def prove(self):
        pr = self.g["prove"]
        if not isinstance(pr, yl.Lista):
            self.err(self.r("prove"), "prove", "dev'essere una lista di prove e c'è %s" % _nome_tipo(pr),
                     "scrivi voci `- data: AAAA-MM-GG` con `esito_atteso: ...`, oppure togli `prove`")
            return
        for n, p in enumerate(pr):
            lab = "prove[%d]" % (n + 1)
            base = ("prove", n)
            if not isinstance(p, yl.Mappa):
                self.err(self.r(*base), lab, "ogni prova dev'essere un blocco con `data` ed `esito_atteso`",
                         "scrivi `- data: 2026-11-07` e sotto `esito_atteso: ...`")
                continue
            self.sconosciuti(p, CAMPI_PROVA, lab, base)
            if "data" not in p:
                self.err(self.r(*base), lab + ".data", "manca il campo obbligatorio", "scrivi `data: AAAA-MM-GG`")
            elif not _data_valida(p["data"]):
                self.err(self.r(*(base + ("data",))), lab + ".data", "dev'essere una data AAAA-MM-GG e c'è %r" % (p["data"],),
                         "scrivi una data vera, come 2026-11-07")
            self.testo(p, "esito_atteso", lab, base, fare="scrivi cosa ti aspetti che succeda")
            self.testo(p, "input", lab, base, obbligatorio=False)

    # --- avvisi
    def avvisi_workspace(self):
        if not self.workspace:
            return
        radice = _cartella_studio(self.file)
        if radice is None:
            return
        for riga, campo, nome in self.workspace:
            if not os.path.isdir(os.path.join(radice, "workspace", nome)):
                self.avv(riga, campo, "la cartella workspace/%s non c'è ancora" % nome,
                         "crea il workspace prima della prima corsa, o correggi il nome")


def _consigli_yaml(motivo):
    m = motivo.lower()
    if "ancora" in m or "alias" in m:
        return "scrivi i campi per intero invece di riusarli: ancore e alias non sono ammessi nei grafi"
    if "tag" in m:
        return "togli il tag: scrivi il valore semplice"
    if "ripiegato" in m:
        return "usa `|` per il testo su più righe"
    if "più righe" in m or "non chiusa" in m:
        return "scrivi la lista o il blocco su una riga sola, oppure a blocchi con il rientro"
    if "tabulazion" in m:
        return "sostituisci le tabulazioni con spazi"
    if "ripetuta" in m:
        return "tieni una sola chiave con quel nome"
    if "rientro" in m:
        return "allinea le righe con lo stesso rientro (2 spazi per livello)"
    if "documento multiplo" in m or "---" in m:
        return "tieni un solo documento per file"
    if "virgolette" in m or "\": \"" in m:
        return "metti il testo fra virgolette doppie"
    return "riscrivi quella riga con il sottoinsieme ammesso: blocchi con rientro, testo, numeri, true/false, `|`"


def controlla_file(percorso):
    """Controlla un file di grafo. Restituisce (errori, avvisi): liste di testi."""
    percorso = str(percorso)
    try:
        g = yl.leggi_file(percorso)
    except yl.ErroreYaml as e:
        return (["%s:%s: yaml: %s. Cosa fare: %s" % (percorso, e.riga, e.motivo, _consigli_yaml(e.motivo))], [])
    except OSError as e:
        return (["%s:1: file: non riesco a leggerlo (%s). Cosa fare: controlla il percorso" % (percorso, e.strerror)], [])
    if not isinstance(g, yl.Mappa):
        return (["%s:1: file: il grafo dev'essere un elenco di campi `nome: valore` e non lo è. Cosa fare: parti da `grafo: <nome>` e scrivi i campi obbligatori" % percorso], [])
    c = _Controllo(percorso, g)
    c.controlla()
    return ([t for _, t in sorted(c.errori, key=lambda x: x[0])],
            [t for _, t in sorted(c.avvisi, key=lambda x: x[0])])


def _plurale(n, uno, molti):
    return "%d %s" % (n, uno if n == 1 else molti)


def main(argv):
    if len(argv) == 1 and argv[0] in ("-h", "--help"):
        print(AIUTO)
        return 0
    if not argv or any(a.startswith("-") for a in argv):
        print(AIUTO, file=sys.stderr)
        return 1
    file_da_fare = []
    errori_tot = 0
    avvisi_tot = 0
    for a in argv:
        if os.path.isdir(a):
            for nome in sorted(os.listdir(a)):
                p = os.path.join(a, nome)
                if nome.endswith(".yaml") and os.path.isfile(p):
                    file_da_fare.append(p)
        elif os.path.isfile(a):
            file_da_fare.append(a)
        else:
            print("%s:1: file: non c'è. Cosa fare: controlla il percorso" % a)
            errori_tot += 1
    for p in file_da_fare:
        errori, avvisi = controlla_file(p)
        for e in errori:
            print(e)
        for v in avvisi:
            print("avviso: " + v)
        errori_tot += len(errori)
        avvisi_tot += len(avvisi)
    print("riepilogo: %s controllat%s, %s, %s" % (
        _plurale(len(file_da_fare), "grafo", "grafi"),
        "o" if len(file_da_fare) == 1 else "i",
        "nessun errore" if errori_tot == 0 else _plurale(errori_tot, "errore", "errori"),
        _plurale(avvisi_tot, "avviso", "avvisi")))
    return 1 if errori_tot else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
