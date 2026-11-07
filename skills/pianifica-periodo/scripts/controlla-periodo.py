#!/usr/bin/env python3
# redacy 0.3.0 · skills/pianifica-periodo/scripts/controlla-periodo.py
"""Controlla periodo/todo.json e periodo/idee.json contro i loro schemi.

Solo libreria standard. I due schemi (todo.schema.json, idee.schema.json) si
cercano accanto a questo script: nel plugin in skills/pianifica-periodo/scripts/,
nella cartella dello studio in .agents/hooks/.

Due modi:
  controlla-periodo.py <file>   esce 0 se il file è valido, 1 con un messaggio
                                in italiano per ogni errore.
  da hook (senza argomenti)     legge da stdin il JSON dell'evento PostToolUse;
                                si sveglia solo se la scrittura ha toccato
                                periodo/todo.json o periodo/idee.json; se il file
                                è rotto lo dice al modello, altrimenti esce 0 in silenzio.
"""
import datetime
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
FILE_CONTROLLATI = {"todo.json": "todo.schema.json", "idee.json": "idee.schema.json"}


# ---------------------------------------------------------------- il controllo

def _tipo_ok(valore, tipo):
    if tipo == "object":
        return isinstance(valore, dict)
    if tipo == "array":
        return isinstance(valore, list)
    if tipo == "string":
        return isinstance(valore, str)
    if tipo == "null":
        return valore is None
    if tipo == "integer":
        return isinstance(valore, int) and not isinstance(valore, bool)
    if tipo == "number":
        return isinstance(valore, (int, float)) and not isinstance(valore, bool)
    if tipo == "boolean":
        return isinstance(valore, bool)
    return True


def _nome_tipo(valore):
    if valore is None:
        return "null"
    if isinstance(valore, bool):
        return "vero/falso"
    if isinstance(valore, str):
        return "testo"
    if isinstance(valore, (int, float)):
        return "numero"
    if isinstance(valore, list):
        return "elenco"
    return "oggetto"


def _mostra(valore):
    testo = json.dumps(valore, ensure_ascii=False)
    return testo if len(testo) <= 40 else testo[:37] + "..."


def valida(valore, schema, percorso, errori):
    """Il sottoinsieme di JSON Schema che usano i due schemi."""
    dove = percorso or "il file"
    tipi = schema.get("type")
    if tipi is not None:
        elenco = tipi if isinstance(tipi, list) else [tipi]
        if not any(_tipo_ok(valore, t) for t in elenco):
            attesi = " o ".join({"string": "testo", "object": "oggetto", "array": "elenco",
                                 "null": "null"}.get(t, t) for t in elenco)
            errori.append(f"{dove}: dovrebbe essere {attesi}, trovato {_nome_tipo(valore)}")
            return
    if "const" in schema and valore != schema["const"]:
        errori.append(f"{dove}: deve valere {_mostra(schema['const'])}, trovato {_mostra(valore)}")
    if "enum" in schema and valore not in schema["enum"]:
        ammessi = ", ".join(f"«{v}»" for v in schema["enum"])
        errori.append(f"{dove}: {_mostra(valore)} non è fra i valori ammessi ({ammessi})")
    if isinstance(valore, str):
        if "minLength" in schema and len(valore) < schema["minLength"]:
            errori.append(f"{dove}: non può essere vuoto")
        if "pattern" in schema and not re.search(schema["pattern"], valore):
            aiuto = schema.get("description", "")
            errori.append(f"{dove}: {_mostra(valore)} non ha la forma giusta"
                          + (f" ({aiuto})" if aiuto else ""))
    if isinstance(valore, dict):
        proprieta = schema.get("properties", {})
        for nome in schema.get("required", []):
            if nome not in valore:
                errori.append(f"{dove}: manca il campo «{nome}»")
        if schema.get("additionalProperties") is False:
            for nome in valore:
                if nome not in proprieta:
                    errori.append(f"{dove}: campo «{nome}» non previsto (ammessi: "
                                  + ", ".join(proprieta) + ")")
        for nome, sotto in proprieta.items():
            if nome in valore:
                valida(valore[nome], sotto, f"{percorso}.{nome}" if percorso else nome, errori)
    if isinstance(valore, list) and "items" in schema:
        for i, voce in enumerate(valore):
            valida(voce, schema["items"], f"{percorso}[{i}]", errori)


def _data_vera(testo):
    try:
        datetime.date.fromisoformat(testo)
        return True
    except ValueError:
        return False


def controlli_oltre_lo_schema(nome, dati, cartella_periodo, errori):
    elenco_chiave = "todo" if nome == "todo.json" else "idee"
    voci = dati.get(elenco_chiave) if isinstance(dati, dict) else None
    if not isinstance(voci, list):
        return
    visti = {}
    for i, voce in enumerate(voci):
        if not isinstance(voce, dict):
            continue
        id_ = voce.get("id")
        if isinstance(id_, str):
            if id_ in visti:
                errori.append(f"{elenco_chiave}[{i}].id: «{id_}» c'è già alla voce {visti[id_]}; gli id sono unici")
            else:
                visti[id_] = i
        campi_data = ["scadenza", "aggiornato"] if nome == "todo.json" else ["arrivata"]
        for campo in campi_data:
            v = voce.get(campo)
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) and not _data_vera(v):
                errori.append(f"{elenco_chiave}[{i}].{campo}: {v} non è una data che esiste")
        esito = voce.get("esito")
        if isinstance(esito, dict):
            v = esito.get("data")
            if isinstance(v, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) and not _data_vera(v):
                errori.append(f"{elenco_chiave}[{i}].esito.data: {v} non è una data che esiste")
            if "todo" in esito and esito.get("stato") != "portata nel periodo":
                errori.append(f"{elenco_chiave}[{i}].esito.todo: si indica solo per le idee «portata nel periodo»")
            if esito.get("stato") == "portata nel periodo" and "todo" in esito:
                path_todo = os.path.join(cartella_periodo, "todo.json")
                try:
                    with open(path_todo, encoding="utf-8") as f:
                        todo = json.load(f)
                    ids = {t.get("id") for t in todo.get("todo", []) if isinstance(t, dict)}
                    if esito["todo"] not in ids:
                        errori.append(f"{elenco_chiave}[{i}].esito.todo: «{esito['todo']}» non c'è in todo.json")
                except (OSError, ValueError, AttributeError):
                    pass  # niente todo.json leggibile: non è affare di questo file


def controlla_file(percorso):
    """Ritorna la lista degli errori (vuota se il file è valido)."""
    nome = os.path.basename(percorso)
    if nome not in FILE_CONTROLLATI:
        return [f"{nome}: non so controllarlo (so controllare todo.json e idee.json)"]
    try:
        with open(percorso, encoding="utf-8") as f:
            testo = f.read()
    except OSError as e:
        return [f"{nome}: non riesco a leggerlo ({e.strerror or e})"]
    try:
        dati = json.loads(testo)
    except ValueError as e:
        riga = getattr(e, "lineno", None)
        dove = f" alla riga {riga}" if riga else ""
        return [f"{nome}: non è un JSON valido{dove} ({getattr(e, 'msg', e)})"]
    try:
        with open(os.path.join(QUI, FILE_CONTROLLATI[nome]), encoding="utf-8") as f:
            schema = json.load(f)
    except (OSError, ValueError):
        return [f"{nome}: lo schema {FILE_CONTROLLATI[nome]} non c'è accanto allo script o è rotto"]
    errori = []
    valida(dati, schema, "", errori)
    if not errori:
        controlli_oltre_lo_schema(nome, dati, os.path.dirname(os.path.abspath(percorso)), errori)
    return errori


# ----------------------------------------------------------------- l'hook

def file_toccati(evento):
    """I periodo/todo.json e periodo/idee.json che l'evento nomina, come percorsi assoluti.

    Claude Code: tool_input.file_path (Write, Edit, MultiEdit).
    Codex: apply_patch con il testo della patch in tool_input (il percorso è nel testo).
    Una shell che scrive: il comando è nel testo di tool_input.
    """
    cartella = evento.get("cwd") or os.getcwd()
    testo = json.dumps(evento.get("tool_input", ""), ensure_ascii=False)
    trovati = []
    for m in re.finditer(r"((?:[^\s\"'\\=:;|<>()]|\\/)*periodo/(?:todo|idee)\.json)", testo):
        p = m.group(1).replace("\\/", "/")
        assoluto = p if os.path.isabs(p) else os.path.join(cartella, p)
        assoluto = os.path.normpath(assoluto)
        if assoluto not in trovati:
            trovati.append(assoluto)
    return trovati


def segnala_al_modello(messaggio):
    """Come si dice al modello che il file è rotto, su Claude Code e su Codex.

    Esce 2 con il messaggio su stderr: in tutti e due gli harness un hook PostToolUse
    che esce 2 rimanda lo stderr al modello. In più stampa il JSON `decision: block`
    che i due leggono dallo stdout, perché il messaggio arrivi anche se uno dei due
    ignora il codice di uscita.
    """
    risposta = {
        "decision": "block",
        "reason": messaggio,
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": messaggio},
    }
    print(json.dumps(risposta, ensure_ascii=False))
    print(messaggio, file=sys.stderr)
    sys.exit(2)


def da_hook():
    try:
        evento = json.load(sys.stdin)
    except ValueError:
        sys.exit(0)  # non è un evento che capisco: in silenzio
    if not isinstance(evento, dict):
        sys.exit(0)
    messaggi = []
    for percorso in file_toccati(evento):
        if not os.path.exists(percorso):
            continue  # la scrittura è fallita o il file non c'è più: niente da dire
        errori = controlla_file(percorso)
        if errori:
            relativo = os.path.relpath(percorso, evento.get("cwd") or os.getcwd())
            messaggi.append(f"{relativo} non è valido:\n- " + "\n- ".join(errori)
                            + "\nCorreggi il file adesso, poi rilancia: python3 .agents/hooks/controlla-periodo.py "
                            + relativo)
    if messaggi:
        segnala_al_modello("\n\n".join(messaggi))
    sys.exit(0)


def main(argv):
    if len(argv) == 1:
        if sys.stdin.isatty():
            print("Uso: controlla-periodo.py <periodo/todo.json | periodo/idee.json>", file=sys.stderr)
            return 1
        da_hook()
    if argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    esito = 0
    for percorso in argv[1:]:
        errori = controlla_file(percorso)
        if errori:
            esito = 1
            print(f"{percorso}: NON valido")
            for e in errori:
                print(f"  - {e}")
        else:
            print(f"{percorso}: valido")
    return esito


if __name__ == "__main__":
    sys.exit(main(sys.argv))
