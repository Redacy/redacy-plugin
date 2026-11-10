#!/usr/bin/env python3
# redacy 0.4.2 · skills/pannello/scripts/ferma.py
"""Hook PreToolUse: nega i passi di una corsa che l'utente ha fermato dal pannello.

Sta in .agents/hooks/ della cartella dello studio (lo copia `inizia`) e gira prima di ogni strumento,
in Claude Code e in Codex. Legge l'evento da stdin (JSON), cerca fra le corse della cartella quella
che porta il `session_id` di questa conversazione nel campo `sessione`, e se esiste la richiesta di
stop grafi/corse/<id>.stop nega lo strumento con un motivo che dice di fermarsi e di dirlo all'utente.

Le altre conversazioni nella stessa cartella non sono toccate: la corsa si riconosce dal `sessione`,
che corsa.py scrive da $CLAUDE_CODE_SESSION_ID (Claude) o $CODEX_THREAD_ID (Codex).

Dopo il primo rifiuto la conversazione deve poter continuare (l'utente può chiedere altro): il rifiuto
vale per 60 secondi dal primo (segnato in grafi/corse/.<id>.notificato), poi gli strumenti tornano a
girare. Una scrittura in memoria/LOG.md passa sempre: è la riga che l'agente deve scrivere.

Esce 0 in silenzio se non ha niente da dire, e anche se qualcosa va storto (un hook che si rompe non
deve bloccare il lavoro). Solo libreria standard.
"""

import datetime
import json
import os
import re
import sys

FINESTRA_SECONDI = 60
NOME_OK = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
FORMATO_ORA = "%Y-%m-%dT%H:%M:%SZ"


def su_windows():
    """Vero su Windows. I rami solo-Windows di questo file passano di qui (le prove lo forzano)."""
    return os.name == "nt"


def adesso():
    return datetime.datetime.now(datetime.timezone.utc)


def trova_cartella(evento):
    candidati = [evento.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR"), os.getcwd()]
    for c in candidati:
        if not c or not isinstance(c, str):
            continue
        corrente = os.path.realpath(c)
        while True:
            if os.path.isdir(os.path.join(corrente, "grafi", "corse")):
                return corrente
            padre = os.path.dirname(corrente)
            if padre == corrente:
                break
            corrente = padre
    return None


def sessioni(evento):
    visti = set()
    for v in (evento.get("session_id"), os.environ.get("CLAUDE_CODE_SESSION_ID"),
              os.environ.get("CODEX_THREAD_ID"), os.environ.get("CODEX_SESSION_ID")):
        if isinstance(v, str) and v.strip():
            visti.add(v.strip())
    return visti


def legge_log(evento):
    """Vero se lo strumento scrive nel registro (memoria/LOG.md): quella scrittura passa."""
    try:
        testo = json.dumps(evento.get("tool_input") or {}, ensure_ascii=False)
        if su_windows():  # il percorso ha la barra rovesciata, doppia nel JSON
            testo = testo.replace("\\\\", "/")
        return "memoria/LOG.md" in testo
    except (TypeError, ValueError):
        return False


def passo_fermato(corsa):
    for p in corsa.get("passi") or []:
        if isinstance(p, dict) and p.get("stato") in ("fermato", "in-corso"):
            return p.get("id")
    return None


def decidi(evento):
    """Restituisce il motivo del rifiuto, o None."""
    cartella = trova_cartella(evento)
    mie = sessioni(evento)
    if not cartella or not mie:
        return None
    corse = os.path.join(cartella, "grafi", "corse")
    try:
        nomi = sorted(os.listdir(corse))
    except OSError:
        return None
    for n in nomi:
        if n.startswith(".") or not n.endswith(".stop"):
            continue
        id_corsa = n[:-5]
        if not NOME_OK.match(id_corsa):
            continue
        try:
            with open(os.path.join(corse, id_corsa + ".json"), encoding="utf-8") as f:
                corsa = json.load(f)
        except (OSError, ValueError):
            continue
        if not isinstance(corsa, dict) or corsa.get("sessione") not in mie:
            continue
        if legge_log(evento):
            return None
        marcatore = os.path.join(corse, "." + id_corsa + ".notificato")
        ora = adesso()
        try:
            with open(marcatore, encoding="utf-8") as f:
                prima = datetime.datetime.strptime(f.read().strip(), FORMATO_ORA).replace(tzinfo=datetime.timezone.utc)
            if (ora - prima).total_seconds() > FINESTRA_SECONDI:
                continue
        except (OSError, ValueError):
            try:
                with open(marcatore, "w", encoding="utf-8") as f:
                    f.write(ora.strftime(FORMATO_ORA) + "\n")
            except OSError:
                pass
        passo = passo_fermato(corsa)
        return ("STOP: la corsa %s%s è stata fermata dall'utente col pulsante Ferma del pannello. "
                "Non fare altri passi, non riprovare e non chiuderla. Scrivi una riga in memoria/LOG.md "
                "e di' all'utente che si è fermata e a quale passo. Poi chiudi il turno."
                % (id_corsa, (" (passo " + str(passo) + ")") if passo else ""))
    return None


def main():
    try:
        testo = sys.stdin.read()
        evento = json.loads(testo) if testo.strip() else {}
        if not isinstance(evento, dict):
            return 0
        if evento.get("hook_event_name") not in (None, "PreToolUse"):
            return 0
        motivo = decidi(evento)
    except Exception:
        return 0
    if motivo:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                                 "permissionDecisionReason": motivo}}, ensure_ascii=False))
    return 0


def flussi_utf8():
    """Su Windows i flussi che non sono un terminale usano la tabella locale (cp1252): chi li legge vuole UTF-8."""
    for f in (sys.stdin, sys.stdout, sys.stderr):
        try:
            if not f.isatty():
                f.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass


if __name__ == "__main__":
    flussi_utf8()
    sys.exit(main())
