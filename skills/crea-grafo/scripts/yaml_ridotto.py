# redacy 0.3.0 · skills/crea-grafo/scripts/yaml_ridotto.py
"""Lettore del sottoinsieme di yaml usato dai grafi di redacy.

Solo libreria standard, niente PyYAML. Ammesso: mappe e liste a blocchi,
mappe e liste in linea su una riga, testo (anche fra virgolette), interi,
decimali, true/false, null, testo a blocchi con | e |-, commenti con #.
Tutto il resto dà un ErroreYaml con riga e motivo.

Uso da riga di comando: python3 yaml_ridotto.py file.yaml
(stampa il dato letto come JSON).
"""

import json
import re
import sys

AIUTO = """Uso: python3 yaml_ridotto.py FILE.yaml

Legge un file yaml del sottoinsieme che usano i grafi e ne stampa il
contenuto come JSON. Se il file è fuori dal sottoinsieme (ancore, alias,
tag, testo ripiegato, liste in linea su più righe, tabulazioni nel
rientro, chiavi ripetute, rientro incoerente, documenti multipli) scrive
il numero di riga e il motivo ed esce con 1.

Opzioni:
  -h, --help   mostra questo aiuto

Uscite: 0 letto bene; 1 errore nel file o uso sbagliato."""


class ErroreYaml(Exception):
    """Errore di lettura: .riga (da 1) e .motivo (in italiano)."""

    def __init__(self, riga, motivo):
        Exception.__init__(self, motivo)
        self.riga = riga
        self.motivo = motivo

    def __str__(self):
        return "riga %s: %s" % (self.riga, self.motivo)


class Mappa(dict):
    """Una mappa letta; .righe dice a che riga sta ogni chiave."""

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)
        self.righe = {}


class Lista(list):
    """Una lista letta; .righe dice a che riga sta ogni voce."""

    def __init__(self, *args):
        list.__init__(self, *args)
        self.righe = []


_INTERO = re.compile(r"^[+-]?(0|[1-9][0-9]*)$")
_DECIMALE = re.compile(r"^[+-]?(0|[1-9][0-9]*)\.[0-9]+$")
_DUE_PUNTI = re.compile(r":(\s|$)")
_FUGHE = {'"': '"', "\\": "\\", "n": "\n", "t": "\t", "r": "\r", "/": "/"}


# ---------------------------------------------------------------- scalari

def _errore_marcatore(c, riga):
    if c == "&":
        return ErroreYaml(riga, "ancora (&nome) non ammessa: scrivi due volte i campi invece di riusarli")
    if c == "*":
        return ErroreYaml(riga, "alias (*nome) non ammesso; se è un percorso con l'asterisco, mettilo fra virgolette")
    return ErroreYaml(riga, "tag (!nome) non ammesso: scrivi il valore senza tag")


def _plain(t, riga):
    t = t.strip()
    if _DUE_PUNTI.search(t):
        raise ErroreYaml(riga, "testo semplice con \": \" dentro: mettilo fra virgolette")
    if t in ("", "~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True", "TRUE"):
        return True
    if t in ("false", "False", "FALSE"):
        return False
    if _INTERO.match(t):
        return int(t)
    if _DECIMALE.match(t):
        return float(t)
    return t


def _fra_virgolette(s, p, riga):
    q = s[p]
    p += 1
    out = []
    while p < len(s):
        c = s[p]
        if q == '"':
            if c == "\\":
                if p + 1 >= len(s):
                    break
                e = s[p + 1]
                if e in _FUGHE:
                    out.append(_FUGHE[e])
                    p += 2
                    continue
                if e == "u" and re.match(r"^[0-9a-fA-F]{4}$", s[p + 2:p + 6]):
                    out.append(chr(int(s[p + 2:p + 6], 16)))
                    p += 6
                    continue
                raise ErroreYaml(riga, "sequenza \\%s non ammessa fra virgolette doppie (ammesse \\\" \\\\ \\n \\t \\r \\/ \\uXXXX)" % e)
            if c == '"':
                return "".join(out), p + 1
        else:
            if c == "'":
                if s[p + 1:p + 2] == "'":
                    out.append("'")
                    p += 2
                    continue
                return "".join(out), p + 1
        out.append(c)
        p += 1
    raise ErroreYaml(riga, "virgolette non chiuse: un testo fra virgolette sta su una sola riga")


def _senza_commento(s):
    out = []
    q = None
    i = 0
    n = len(s)
    prec = None  # ultimo carattere non spazio fuori dalle virgolette
    while i < n:
        c = s[i]
        if q:
            if q == '"' and c == "\\":
                out.append(s[i:i + 2])
                i += 2
                continue
            if q == "'" and c == "'" and s[i + 1:i + 2] == "'":
                out.append("''")
                i += 2
                continue
            if c == q:
                q = None
                prec = c
            out.append(c)
            i += 1
            continue
        if c == "#" and (i == 0 or s[i - 1] in " \t"):
            break
        if c in "\"'" and prec in (None, ":", "-", ",", "[", "{") and (i == 0 or s[i - 1] in " \t[{,"):
            q = c
        out.append(c)
        if c not in " \t":
            prec = c
        i += 1
    return "".join(out)


# ------------------------------------------------------------ in linea

def _salta(s, p):
    while p < len(s) and s[p] in " \t":
        p += 1
    return p


def _non_chiusa(riga):
    return ErroreYaml(riga, "mappa o lista in linea non chiusa sulla stessa riga: chiudila qui o scrivila a blocchi")


def _flow_valore(s, p, riga):
    p = _salta(s, p)
    if p >= len(s):
        raise _non_chiusa(riga)
    c = s[p]
    if c == "{":
        return _flow_mappa(s, p, riga)
    if c == "[":
        return _flow_lista(s, p, riga)
    if c in "\"'":
        return _fra_virgolette(s, p, riga)
    if c in "&*!":
        raise _errore_marcatore(c, riga)
    q = p
    while q < len(s) and s[q] not in ",]}":
        q += 1
    return _plain(s[p:q], riga), q


def _flow_mappa(s, p, riga):
    m = Mappa()
    p += 1
    while True:
        p = _salta(s, p)
        if p >= len(s):
            raise _non_chiusa(riga)
        if s[p] == "}":
            return m, p + 1
        if s[p] in "\"'":
            k, p = _fra_virgolette(s, p, riga)
        else:
            if s[p] in "&*!":
                raise _errore_marcatore(s[p], riga)
            q = p
            while q < len(s):
                if s[q] in ",}":
                    break
                if s[q] == ":" and (q + 1 >= len(s) or s[q + 1] in " ,}"):
                    break
                q += 1
            k = s[p:q].strip()
            p = q
            if k == "":
                raise ErroreYaml(riga, "chiave vuota nella mappa in linea")
        p = _salta(s, p)
        if p >= len(s):
            raise _non_chiusa(riga)
        if s[p] != ":":
            raise ErroreYaml(riga, "nella mappa in linea manca \":\" dopo la chiave \"%s\"" % k)
        p = _salta(s, p + 1)
        if p < len(s) and s[p] in ",}":
            v = None
        else:
            v, p = _flow_valore(s, p, riga)
        if k in m:
            raise ErroreYaml(riga, "chiave ripetuta: \"%s\"" % k)
        m[k] = v
        m.righe[k] = riga
        p = _salta(s, p)
        if p >= len(s):
            raise _non_chiusa(riga)
        if s[p] == ",":
            p += 1
            continue
        if s[p] == "}":
            return m, p + 1
        raise ErroreYaml(riga, "nella mappa in linea mi aspettavo \",\" o \"}\" e ho trovato \"%s\"" % s[p])


def _flow_lista(s, p, riga):
    lista = Lista()
    p += 1
    while True:
        p = _salta(s, p)
        if p >= len(s):
            raise _non_chiusa(riga)
        if s[p] == "]":
            return lista, p + 1
        v, p = _flow_valore(s, p, riga)
        lista.append(v)
        lista.righe.append(riga)
        p = _salta(s, p)
        if p >= len(s):
            raise _non_chiusa(riga)
        if s[p] == ",":
            p += 1
            continue
        if s[p] == "]":
            return lista, p + 1
        raise ErroreYaml(riga, "nella lista in linea mi aspettavo \",\" o \"]\" e ho trovato \"%s\"" % s[p])


def _in_linea(resto, riga):
    c = resto[0]
    if c in "&*!":
        raise _errore_marcatore(c, riga)
    if c == ">":
        raise ErroreYaml(riga, "testo ripiegato (>) non ammesso: usa | per il testo su più righe")
    if c == "|":
        raise ErroreYaml(riga, "il testo a blocchi (|) va subito dopo \"chiave:\" o dopo \"-\"")
    if c in "@`":
        raise ErroreYaml(riga, "il carattere \"%s\" a inizio testo è riservato: metti il testo fra virgolette" % c)
    if c == "?" and (len(resto) == 1 or resto[1] == " "):
        raise ErroreYaml(riga, "chiavi non semplici (\"? \") non ammesse")
    if c in "{[":
        v, p = _flow_valore(resto, 0, riga)
        if _salta(resto, p) < len(resto):
            raise ErroreYaml(riga, "testo dopo la chiusura della mappa o lista in linea")
        return v
    if c in "\"'":
        v, p = _fra_virgolette(resto, 0, riga)
        if _salta(resto, p) < len(resto):
            raise ErroreYaml(riga, "testo dopo le virgolette di chiusura")
        return v
    return _plain(resto, riga)


# ------------------------------------------------------------- a blocchi

def _e_voce(text):
    return text == "-" or text.startswith("- ")


class _Lettore:
    def __init__(self, testo):
        testo = testo.replace("\r\n", "\n").replace("\r", "\n")
        if testo.startswith("﻿"):
            testo = testo[1:]
        self.raw = testo.split("\n")
        self.sost = {}
        self.saltate = set()
        self._voci = {}
        primo = True
        for i, r in enumerate(self.raw):
            s = r.strip()
            if not s or s.startswith("#"):
                continue
            if r.startswith("%"):
                raise ErroreYaml(i + 1, "direttive (%) non ammesse")
            if r.startswith("---") and (len(r) == 3 or r[3] in " \t"):
                if not primo:
                    raise ErroreYaml(i + 1, "documento multiplo (---) non ammesso: un file è un documento solo")
                resto = _senza_commento(r[3:]).strip()
                if resto:
                    raise ErroreYaml(i + 1, "dopo --- non si scrive niente sulla stessa riga")
                self.saltate.add(i)
            elif r.startswith("...") and (len(r) == 3 or r[3] in " \t"):
                raise ErroreYaml(i + 1, "documento multiplo o fine documento (...) non ammesso")
            primo = False

    def voce(self, i):
        """(rientro, testo senza commento) della riga i, o None se vuota."""
        if i in self.sost:
            return self.sost[i]
        if i in self.saltate:
            return None
        if i in self._voci:
            return self._voci[i]
        r = self.raw[i]
        s = r.strip()
        if not s or s.startswith("#"):
            self._voci[i] = None
            return None
        ws = r[:len(r) - len(r.lstrip(" \t"))]
        if "\t" in ws:
            raise ErroreYaml(i + 1, "tabulazione nel rientro: usa solo spazi")
        testo = _senza_commento(r[len(ws):]).rstrip()
        v = (len(ws), testo) if testo else None
        self._voci[i] = v
        return v

    def sig(self, i):
        while i < len(self.raw):
            if self.voce(i) is not None:
                return i
            i += 1
        return None

    def documento(self):
        i = self.sig(0)
        if i is None:
            return None
        ind, _ = self.voce(i)
        valore, j = self.blocco(i, ind)
        k = self.sig(j)
        if k is not None:
            raise ErroreYaml(k + 1, "rientro incoerente: questa riga non appartiene a niente di quello che la precede")
        return valore

    def chiave(self, text, riga):
        """(chiave, resto) se la riga è 'chiave: valore', altrimenti None."""
        c = text[0]
        if c in "{[":
            return None
        if c in "\"'":
            k, p = _fra_virgolette(text, 0, riga)
            q = _salta(text, p)
            if q < len(text) and text[q] == ":" and (q + 1 >= len(text) or text[q + 1] == " "):
                return k, text[q + 1:].strip()
            return None
        if c == "?" and (len(text) == 1 or text[1] == " "):
            raise ErroreYaml(riga, "chiavi non semplici (\"? \") non ammesse")
        m = _DUE_PUNTI.search(text)
        if not m:
            return None
        k = text[:m.start()].rstrip()
        if k == "":
            raise ErroreYaml(riga, "chiave vuota")
        if k[0] in "&*!":
            raise _errore_marcatore(k[0], riga)
        return k, text[m.start() + 1:].strip()

    def blocco(self, i, ind):
        _, text = self.voce(i)
        if _e_voce(text):
            return self.lista(i, ind)
        if self.chiave(text, i + 1) is not None:
            return self.mappa(i, ind)
        return _in_linea(text, i + 1), i + 1

    def mappa(self, i, ind):
        m = Mappa()
        while True:
            j = self.sig(i)
            if j is None:
                i = len(self.raw)
                break
            i = j
            ind2, text = self.voce(i)
            if ind2 < ind:
                break
            if ind2 > ind:
                raise ErroreYaml(i + 1, "rientro incoerente: la riga è più rientrata delle altre della mappa (un testo su più righe si scrive con |)")
            if _e_voce(text):
                raise ErroreYaml(i + 1, "una voce di lista (-) dentro una mappa: manca la chiave prima")
            kv = self.chiave(text, i + 1)
            if kv is None:
                raise ErroreYaml(i + 1, "la riga non è nella forma \"chiave: valore\"")
            k, resto = kv
            if k in m:
                raise ErroreYaml(i + 1, "chiave ripetuta: \"%s\"" % k)
            m.righe[k] = i + 1
            valore, i = self.dopo_chiave(i, ind, resto)
            m[k] = valore
        return m, i

    def dopo_chiave(self, i, ind, resto):
        if resto == "":
            j = self.sig(i + 1)
            if j is not None:
                ind2, text2 = self.voce(j)
                if ind2 > ind:
                    return self.blocco(j, ind2)
                if ind2 == ind and _e_voce(text2):
                    return self.lista(j, ind)
            return None, i + 1
        if resto[0] == "|":
            return self.testo_blocco(i, ind, resto)
        return _in_linea(resto, i + 1), i + 1

    def lista(self, i, ind):
        lista = Lista()
        while True:
            j = self.sig(i)
            if j is None:
                i = len(self.raw)
                break
            i = j
            ind2, text = self.voce(i)
            if ind2 < ind:
                break
            if ind2 > ind:
                raise ErroreYaml(i + 1, "rientro incoerente: la riga è più rientrata delle altre voci della lista")
            if not _e_voce(text):
                break
            lista.righe.append(i + 1)
            dopo = text[1:]
            resto = dopo.lstrip(" ")
            if resto == "":
                j = self.sig(i + 1)
                if j is not None and self.voce(j)[0] > ind:
                    v, i = self.blocco(j, self.voce(j)[0])
                else:
                    v, i = None, i + 1
            elif resto[0] == "|":
                v, i = self.testo_blocco(i, ind, resto)
            else:
                nuovo = ind + 1 + (len(dopo) - len(resto))
                self.sost[i] = (nuovo, resto)
                v, i = self.blocco(i, nuovo)
            lista.append(v)
        return lista, i

    def testo_blocco(self, i, ind, intest):
        if intest not in ("|", "|-"):
            raise ErroreYaml(i + 1, "indicatore di testo a blocchi \"%s\" non ammesso: usa | oppure |-" % intest)
        j = i + 1
        righe = []
        bind = None
        n = len(self.raw)
        while j < n:
            r = self.raw[j]
            if r.strip() == "":
                righe.append("")
                j += 1
                continue
            sp = len(r) - len(r.lstrip(" "))
            if r[sp:sp + 1] == "\t":
                raise ErroreYaml(j + 1, "tabulazione nel rientro: usa solo spazi")
            if bind is None:
                if sp <= ind:
                    break
                bind = sp
            elif sp < bind:
                if sp <= ind:
                    break
                raise ErroreYaml(j + 1, "rientro incoerente dentro il testo a blocchi")
            righe.append(r[bind:].rstrip())
            j += 1
        while righe and righe[-1] == "":
            righe.pop()
        testo = "\n".join(righe)
        if righe and intest == "|":
            testo += "\n"
        return testo, j


# ------------------------------------------------------------ interfaccia

def leggi(testo):
    """Legge un testo yaml del sottoinsieme: Mappa, Lista o scalare."""
    return _Lettore(testo).documento()


def leggi_file(percorso):
    """Come leggi, da un file. Gli OSError passano."""
    with open(percorso, "rb") as f:
        dati = f.read()
    try:
        testo = dati.decode("utf-8")
    except UnicodeDecodeError:
        raise ErroreYaml(1, "il file non è in UTF-8")
    return leggi(testo)


def riga(dato, *percorso):
    """La riga di una chiave o voce seguendo il percorso.

    Se il percorso si ferma prima, la riga dell'ultimo pezzo trovato.
    """
    ultima = None
    cur = dato
    for p in percorso:
        if isinstance(cur, Mappa) and p in cur.righe:
            ultima = cur.righe[p]
            cur = cur.get(p)
        elif isinstance(cur, Lista) and isinstance(p, int) and not isinstance(p, bool) and 0 <= p < len(cur.righe):
            ultima = cur.righe[p]
            cur = cur[p]
        else:
            break
    return ultima


def archi_del_grafo(dato):
    """Gli archi (da, a) dei passi di un grafo.

    Un passo senza "dopo" segue il passo scritto prima; il primo non ha archi
    in entrata; si saltano gli id che non esistono.
    """
    if not isinstance(dato, dict):
        return []
    passi = dato.get("passi")
    if not isinstance(passi, list):
        return []
    esistono = set()
    for p in passi:
        if isinstance(p, dict) and isinstance(p.get("id"), str):
            esistono.add(p["id"])
    archi = []
    prima = None
    for p in passi:
        if not isinstance(p, dict) or not isinstance(p.get("id"), str):
            prima = None
            continue
        pid = p["id"]
        dopo = p.get("dopo")
        if isinstance(dopo, str):
            dopo = [dopo]
        if isinstance(dopo, list):
            for d in dopo:
                if isinstance(d, str) and d in esistono:
                    archi.append((d, pid))
        elif dopo is None and prima is not None and prima in esistono:
            archi.append((prima, pid))
        prima = pid
    return archi


def main(argv):
    if len(argv) == 1 and argv[0] in ("-h", "--help"):
        print(AIUTO)
        return 0
    if len(argv) != 1:
        print(AIUTO, file=sys.stderr)
        return 1
    try:
        dato = leggi_file(argv[0])
    except ErroreYaml as e:
        print("%s:%s: %s" % (argv[0], e.riga, e.motivo), file=sys.stderr)
        return 1
    except OSError as e:
        print("%s: non riesco a leggerlo (%s)" % (argv[0], e.strerror), file=sys.stderr)
        return 1
    print(json.dumps(dato, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
