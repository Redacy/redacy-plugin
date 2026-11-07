#!/usr/bin/env python3
"""controlla-onboarding.py · redacy 0.3.0

Controlla la cartella dello studio dopo un onboarding di prova (`inizia` coi dati finti di
dati-finti.sh). Lo usano prova-onboarding-claude.sh e prova-onboarding-codex.sh.

Uso:
    python3 controlla-onboarding.py --plugin <radice> --studio <cartella> --dati <cartella dati>
        --impronta <file> --finale <file col messaggio finale> --harness claude|codex
        [--senza-pannello]

Stampa una riga `ok:` o `no:` per controllo, e in fondo PASSA o FALLISCE <i controlli falliti>.
Esce 0 se PASSA, 1 se no. Solo libreria standard.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

FONTI = {
    "la procedura": r"procedura[-_ ]?dichiarazioni",
    "le pratiche": r"pratiche[ _-]?2026",
    "il foglio delle scadenze": r"scadenze[ _-]?2026",
    "la posta": r"posta|gmail",
}
PAGINE_DI_SERVIZIO = {"INDICE.md", "LOG.md", "fonti-dati.md", "studio.md"}
RIGA_LOG = re.compile(r"^- \d{4}-\d{2}-\d{2} \d{2}:\d{2} · (inizia|impara|workspace|grafo|corsa|periodo|fonte) · .+")


def impronta(cartella):
    righe = []
    for base, dirs, nomi in os.walk(cartella):
        dirs.sort()
        for nome in sorted(nomi):
            p = Path(base) / nome
            righe.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(cartella)}")
    return "\n".join(righe) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plugin", required=True)
    ap.add_argument("--studio", required=True)
    ap.add_argument("--dati", required=True)
    ap.add_argument("--impronta", help="scrive (con --scrivi-impronta) o confronta l'impronta dei dati")
    ap.add_argument("--scrivi-impronta", action="store_true")
    ap.add_argument("--finale")
    ap.add_argument("--harness", choices=["claude", "codex"], default="claude")
    ap.add_argument("--senza-pannello", action="store_true")
    a = ap.parse_args()

    plugin, studio, dati = Path(a.plugin), Path(a.studio), Path(a.dati)
    if a.scrivi_impronta:
        Path(a.impronta).write_text(impronta(dati), encoding="utf-8")
        return 0

    esiti = []

    def segna(ok, cosa, perche=""):
        esiti.append((ok, cosa))
        print(("ok: " if ok else "no: ") + cosa + ("" if ok or not perche else f" ({perche})"))

    # 1. L'albero, col controllo dello script stesso
    r = subprocess.run([sys.executable, str(plugin / "skills/inizia/scripts/crea-cartella.py"), str(studio), "--controlla"],
                       capture_output=True, text=True)
    mancano = [l for l in r.stdout.splitlines() if l.startswith(("manca:", "non va:"))]
    segna(r.returncode == 0, "l'albero della cartella c'è (crea-cartella.py --controlla)", "; ".join(mancano[:5]))

    # 2. fonti-dati.md nomina tutte le fonti, ognuna con la sua strada
    fd = studio / "memoria/fonti-dati.md"
    testo = fd.read_text(encoding="utf-8") if fd.is_file() else ""
    sezione = testo.split("## Fonti", 1)[1] if "## Fonti" in testo else ""
    righe = [l for l in sezione.splitlines() if l.startswith("- ")]
    for nome, rx in FONTI.items():
        trovate = [l for l in righe if re.search(rx, l, re.I)]
        segna(bool(trovate) and all("strada:" in l for l in trovate),
              f"fonti-dati.md ha una riga con la strada per {nome}", "nessuna riga" if not trovate else "riga senza «strada:»")
    pratiche = [l for l in righe if re.search(FONTI["le pratiche"], l, re.I)]
    segna(any(re.search(r"resta dov", l, re.I) for l in pratiche), "le pratiche restano dove sono (strada: resta dov'è)")
    posta = [l for l in righe if re.search(FONTI["la posta"], l, re.I)]
    segna(any(re.search(r"~~posta|da collegare", l, re.I) for l in posta), "la posta è segnata da collegare (~~posta)")

    # 3. La pagina dello studio e la pagina della procedura
    st = studio / "memoria/studio.md"
    segna(st.is_file() and re.search(r"Fabbri|Moretti", st.read_text(encoding="utf-8")) is not None,
          "memoria/studio.md c'è e parla dello studio")
    pagine = [p for p in (studio / "memoria").glob("*.md") if p.name not in PAGINE_DI_SERVIZIO]
    proc = [p for p in pagine if re.search(r"dichiar", p.read_text(encoding="utf-8"), re.I)]
    segna(bool(proc), "c'è una pagina di memoria sulla procedura delle dichiarazioni", f"pagine: {[p.name for p in pagine]}")
    indice = (studio / "memoria/INDICE.md").read_text(encoding="utf-8") if (studio / "memoria/INDICE.md").is_file() else ""
    segna(bool(proc) and any(f"[[{p.stem}]]" in indice for p in proc), "INDICE.md collega la pagina della procedura")
    segna("[[studio]]" in indice, "INDICE.md collega [[studio]]")

    # 4. La regola di Laura: nella policy (Claude) o almeno in memoria (Codex tiene .agents/ in sola lettura)
    pol = studio / ".agents/policy/cosa-faccio-da-solo.md"
    in_policy = pol.is_file() and "Laura" in pol.read_text(encoding="utf-8")
    in_memoria = any("Laura" in p.read_text(encoding="utf-8") for p in (studio / "memoria").glob("*.md"))
    if a.harness == "claude":
        segna(in_policy, "la regola «le mail ai clienti le manda solo Laura» è nella policy")
    else:
        segna(in_policy or in_memoria, "la regola «le mail ai clienti le manda solo Laura» è nella policy o in memoria")
    if pol.is_file():
        segna(not any(l.lstrip().startswith("|") for l in pol.read_text(encoding="utf-8").splitlines()),
              "la policy è fatta di righe, senza tabelle")

    # 5. Almeno un'area di lavoro valida
    ws = [d for d in sorted((studio / "workspace").glob("*")) if d.is_dir()]
    validi = [d for d in ws if (d / "AGENTS.md").is_file() and (d / "CLAUDE.md").is_file() and (d / "memoria").is_dir()]
    controllo_ws = plugin / "skills/crea-workspace/scripts/controlla-workspace.py"
    if validi and controllo_ws.is_file():
        validi = [d for d in validi if subprocess.run([sys.executable, str(controllo_ws), str(d)], capture_output=True).returncode == 0]
    segna(bool(validi), "c'è almeno un'area di lavoro valida in workspace/ (AGENTS.md, CLAUDE.md, memoria/)",
          f"trovate: {[d.name for d in ws]}")

    # 6. I dati dell'utente non sono stati toccati
    if a.impronta:
        segna(Path(a.impronta).read_text(encoding="utf-8") == impronta(dati), "i dati dell'utente sono intatti (stessa impronta di prima)")

    # 7. L'obiettivo non è stato riscritto; i file del periodo sono validi
    modello = plugin / "skills/inizia/modello/periodo/obiettivo.md"
    ob = studio / "periodo/obiettivo.md"
    segna(ob.is_file() and ob.read_bytes() == modello.read_bytes(), "periodo/obiettivo.md non è stato riscritto")
    cp = studio / ".agents/hooks/controlla-periodo.py"
    for nome in ("todo.json", "idee.json"):
        p = studio / "periodo" / nome
        if cp.is_file():
            ok = subprocess.run([sys.executable, str(cp), str(p)], capture_output=True, cwd=studio).returncode == 0
        else:
            try:
                json.loads(p.read_text(encoding="utf-8")); ok = True
            except (OSError, ValueError):
                ok = False
        segna(ok, f"periodo/{nome} è valido")

    # 8. Il registro: righe nella forma giusta, almeno due di inizia
    log = studio / "memoria/LOG.md"
    righe_log = [l for l in log.read_text(encoding="utf-8").splitlines() if l.startswith("- ")] if log.is_file() else []
    storte = [l for l in righe_log if not RIGA_LOG.match(l)]
    segna(not storte, "ogni riga di LOG.md ha la forma «- AAAA-MM-GG HH:MM · tipo · frase»", f"storte: {storte[:2]}")
    segna(sum(" · inizia · " in l for l in righe_log) >= 2, "LOG.md ha la riga della cartella e quella dell'onboarding")

    # 9. Il pannello: acceso, col pid vivo e la pagina che risponde 200
    url = ""
    if a.senza_pannello:
        print("nota: pannello non controllato (--senza-pannello)")
    else:
        pj = studio / "interfaccia/pannello.json"
        dati_p = {}
        try:
            dati_p = json.loads(pj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        pid = dati_p.get("pid")
        vivo = False
        if isinstance(pid, int):
            try:
                os.kill(pid, 0); vivo = True
            except OSError:
                pass
        segna(vivo, "interfaccia/pannello.json ha un pid vivo", f"pannello.json: {dati_p or 'assente'}")
        porta = dati_p.get("porta") or dati_p.get("port")
        url = dati_p.get("url") or (f"http://127.0.0.1:{porta}/" if porta else "")
        codice = None
        if url:
            try:
                codice = urllib.request.urlopen(url, timeout=5).status
            except Exception as e:  # noqa: BLE001 - qualunque errore è un «no»
                codice = str(e)
        segna(codice == 200, "la pagina del pannello risponde 200", f"{url} -> {codice}")

    # 10. Il messaggio finale spiega il sistema
    finale = Path(a.finale).read_text(encoding="utf-8") if a.finale and Path(a.finale).is_file() else ""
    segna(re.search(r"pannello", finale, re.I) is not None, "il messaggio finale parla del pannello")
    if not a.senza_pannello:
        segna(re.search(r"127\.0\.0\.1|localhost", finale) is not None, "il messaggio finale dà l'indirizzo del pannello")
    segna(re.search(r"memoria", finale, re.I) is not None, "il messaggio finale dice della memoria dello studio")
    nomi_ws = [d.name for d in ws]
    segna(re.search(r"area di lavoro|aree di lavoro|workspace", finale, re.I) is not None or any(n in finale for n in nomi_ws),
          "il messaggio finale nomina l'agente AI creato")
    segna(re.search(r"prossima volta|d'ora in poi|da adesso|adesso puoi|quando vuoi|cosa succede", finale, re.I) is not None,
          "il messaggio finale dice cosa succederà")

    if a.harness == "codex":
        segna("crea-cartella.py" in finale, "su Codex la chiusura dà la riga che finisce la cartella (crea-cartella.py)")
        segna("/hooks" in finale, "su Codex la chiusura dice di approvare i controlli con /hooks")

    falliti = [c for ok, c in esiti if not ok]
    print(f"controlli: {len(esiti) - len(falliti)} ok su {len(esiti)}")
    if falliti:
        print("FALLISCE " + "; ".join(falliti))
        return 1
    print("PASSA")
    return 0


if __name__ == "__main__":
    sys.exit(main())
