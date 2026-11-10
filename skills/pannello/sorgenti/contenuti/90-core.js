
/* ---------- il nucleo: barra, livelli, montaggio ---------- */
const PANNELLI = [
  { id: 'oggi', titolo: 'Oggi', riga: 'Cosa aspetta te e cosa sta lavorando', icona: icoPannello('<circle cx="12" cy="12" r="4"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4"/>') },
  { id: 'processi', titolo: 'Processi', riga: 'I lavori che seguono sempre gli stessi passi', icona: icoPannello('<rect x="3" y="4" width="6" height="5" rx="1.5"/><rect x="15" y="15" width="6" height="5" rx="1.5"/><path d="M9 6.5h3a3 3 0 0 1 3 3v5.5"/>') },
  { id: 'periodo', titolo: 'Periodo', riga: 'Obiettivo, cose da fare e idee', icona: icoPannello('<path d="M5 5h14v15H5z"/><path d="M9 3v4M15 3v4M8.5 13l2.5 2.5L16 10"/>') },
  { id: 'memoria', titolo: 'Memoria', riga: 'Quello che lo studio sa', icona: icoPannello('<circle cx="6" cy="7" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="12" cy="17" r="2.5"/><path d="M8.3 8.2l2.6 6.5M15.9 7.5l-2.8 7.3M8.5 7h7"/>') },
  { id: 'aree', titolo: 'Aree', riga: 'Chi si occupa di cosa', icona: icoPannello('<rect x="3" y="3" width="8" height="8" rx="2"/><rect x="13" y="3" width="8" height="8" rx="2"/><rect x="3" y="13" width="8" height="8" rx="2"/><rect x="13" y="13" width="8" height="8" rx="2"/>') },
];
const titoloDi = (id) => PANNELLI.find((p) => p.id === id).titolo;
function barraHtml(ist) {
  if (!ist.pila.length) return '';
  const l = [titoloDi(ist.id)].concat(P[ist.id].livelli(ist));
  return '<nav class="pc-barra" aria-label="Dove sei"><button type="button" class="pc-indietro" data-az="indietro" aria-label="Indietro">‹ Indietro</button><ol class="pc-brici">' + l.map((x, i) => '<li' + (i === l.length - 1 ? ' aria-current="page"' : '') + '>' + esc(x) + '</li>').join('') + '</ol></nav>';
}
function scrollA(sc, el) { let y = 0, n = el; while (n && n !== sc) { y += n.offsetTop; n = n.offsetParent; } sc.scrollTo({ top: Math.max(0, y - 8), behavior: riduceMoto() ? 'auto' : 'smooth' }); }
function pulisciMem(ist) {
  if (ist.M) { try { ist.M.ro && ist.M.ro.disconnect(); ist.M.ctl.destroy(); } catch (e) {} ist.M = null; }
  if (ist._ctlA) { try { ist._ctlA.destroy(); } catch (e) {} ist._ctlA = null; }
  if (ist._roA && ist.id === 'memoria') { try { ist._roA.disconnect(); } catch (e) {} ist._roA = null; }
}
function render(ist, dir) {
  const mod = P[ist.id], root = ist.root; root.dataset.modo = ist.modo;
  if (ist.modo === 'anteprima') {
    pulisciMem(ist); root.innerHTML = mod.anteprima(ist); if (mod.dopoAnteprima) mod.dopoAnteprima(ist, root); return;
  }
  if (ist.id !== 'memoria') pulisciMem(ist);
  if (mod.custom) { mod.pieno(ist, dir); return; }
  const sc = $(root, '.pc-scroll'), top = sc ? sc.scrollTop : 0;
  root.innerHTML = barraHtml(ist) + '<div class="pc-corpo' + (dir ? (dir === 'indietro' ? ' pc-anima-i' : ' pc-anima-a') : '') + '">' + mod.pieno(ist) + '</div>';
  if (!dir) { const s2 = $(root, '.pc-scroll'); if (s2) s2.scrollTop = top; }
  if (mod.dopo) mod.dopo(ist, root);
}
function aggiornaTutte() { ISTANZE.forEach((ist) => { try { ist._r(null); } catch (e) { setTimeout(() => { throw e; }); } }); }
function vaiA(ist, p, v) {
  if (p === ist.id) { ist.vai(v); return; }
  ist.el.dispatchEvent(new CustomEvent('contenuti:vai', { bubbles: true, detail: { pannello: p, voce: v == null ? null : v } }));
}
function monta(id, el, modo) {
  const mod = P[id]; if (!mod) throw new Error('Contenuti: pannello sconosciuto ' + id);
  const root = document.createElement('div'); root.className = 'pc'; root.dataset.pannello = id; el.appendChild(root);
  const ist = {
    id: id, el: el, root: root, modo: modo === 'anteprima' ? 'anteprima' : 'pieno', pila: [], uid: 'pcu' + (++UID), conferma: null, M: null,
    _r(dir) { render(ist, dir); },
    _prof() { root.dispatchEvent(new CustomEvent('contenuti:profondita', { bubbles: true, detail: { pannello: id, livelli: [titoloDi(id)].concat(ist.modo === 'pieno' ? mod.livelli(ist) : []) } })); },
    aggiorna(m) { if (m === 'anteprima' || m === 'pieno') { const cambia = m !== ist.modo; ist.modo = m; ist._r(null); if (cambia) ist._prof(); } else ist._r(null); },
    vai(v) { let ok = false; try { ok = !!mod.vai(ist, v); } catch (e) { ok = false; } if (ok) { ist._r('avanti'); ist._prof(); } return ok; },
    indietro() { if (!ist.pila.length) return false; ist.pila.pop(); ist._r('indietro'); ist._prof(); return true; },
    smonta() { ISTANZE.delete(ist); pulisciMem(ist); if (ist._ro) ist._ro.disconnect(); if (ist._roA) ist._roA.disconnect(); root.remove(); },
  };
  root.addEventListener('click', (e) => {
    if (ist.modo !== 'pieno') return; const el2 = e.target.closest('[data-az]'); if (!el2 || !root.contains(el2)) return;
    const a = el2.dataset.az;
    if (a === 'indietro') { ist.indietro(); return; }
    if (a === 'vai') { vaiA(ist, el2.dataset.p, el2.dataset.v); return; }
    if (a === 'copia') { copia(el2); return; }
    if (a === 'ancora') { const t = document.getElementById(el2.dataset.id); const sc = $(root, '.pc-scroll'); if (t && sc) scrollA(sc, t); return; }
    const r = mod.az ? mod.az(ist, a, el2, e) : null;
    if (r == null && a === 'wiki') { vaiA(ist, 'memoria', el2.dataset.k); return; }
    if (r === 'avanti' || r === 'indietro') { ist._r(r); ist._prof(); } else if (r === 'rirendi') ist._r(null);
  });
  ISTANZE.add(ist); ist._r(null); ist._prof();
  return ist;
}

/* ---------- riassunto per le piastrelle fatte dalla direzione ---------- */
function riassunto(id) {
  if (id === 'oggi') {
    const o = statoOggi(); const righe = [];
    righe.push(o.lav.length ? (o.lav.length === 1 ? '1 lavoro sta girando' : o.lav.length + ' lavori stanno girando') : 'Nessun lavoro in corso');
    if (o.rit) righe.push(o.rit === 1 ? '1 in ritardo' : o.rit + ' in ritardo');
    if (o.dg.length) righe.push(o.dg.length === 1 ? '1 da guardare' : o.dg.length + ' da guardare');
    return { guardare: o.dg.length, numero: o.perTe, etichetta: o.perTe === 1 ? 'cosa aspetta te' : 'cose aspettano te', righe: righe, stato: (o.perTe || o.dg.length) ? 'attenzione' : o.lav.length ? 'corre' : 'ok' };
  }
  if (id === 'processi') {
    const gs = grafi(), acc = gs.filter((g) => g.acceso).length; const run = lavorando().length, persi = perse().length;
    const righe = [acc + (acc === 1 ? ' acceso' : ' accesi')]; if (run) righe.push(run === 1 ? '1 sta lavorando' : run + ' stanno lavorando'); if (persi) righe.push(persi === 1 ? '1 non dà notizie' : persi + ' non danno notizie');
    return { corre: run > 0, numero: gs.length, etichetta: gs.length === 1 ? 'processo' : 'processi', righe: righe, stato: persi ? 'attenzione' : run ? 'corre' : 'ok' };
  }
  if (id === 'periodo') {
    const T = todoLista(), fatte = T.filter((t) => t.stato === 'fatto').length, aperte = T.length - fatte; const rit = T.filter((t) => t.stato !== 'fatto' && t.scadenza && giorniFra(t.scadenza, oggiYMD()) > 0).length;
    return { totale: T.length, numero: aperte, etichetta: aperte === 1 ? 'cosa ancora da fare' : 'cose ancora da fare', righe: [T.length + ' cose, ' + fatte + (fatte === 1 ? ' fatta' : ' fatte'), (S.periodo && S.periodo.obiettivo) || ''].filter(Boolean), stato: rit ? 'attenzione' : 'calmo' };
  }
  if (id === 'memoria') {
    const c = S.memoria_grafo && S.memoria_grafo.conteggi || {}; const righe = [(c.collegamenti || 0) + ' collegamenti']; if (c.mancanti) righe.push(c.mancanti + (c.mancanti === 1 ? ' da scrivere' : ' da scrivere'));
    return { numero: c.pagine || 0, etichetta: c.pagine === 1 ? 'pagina' : 'pagine', righe: righe, stato: 'calmo' };
  }
  if (id === 'aree') {
    const ws = arr(S.workspace); return { numero: ws.length, etichetta: ws.length === 1 ? 'area' : 'aree', righe: ws.map((w) => w.titolo), stato: 'calmo' };
  }
  return null;
}

/* ---------- dati nuovi: rimette i dati e ridisegna le istanze montate, solo se qualcosa è cambiato ---------- */
function firmaDi(d) { const s = Object.assign({}, d.stato || {}); delete s.ora; let n = 0; try { n = Object.keys(d.file || {}).length; } catch (e) {} return JSON.stringify(s) + '|' + (d.firma_file || n); }
function carica(dati) {
  if (!dati || typeof dati !== 'object' || !dati.stato) return false;
  const f = firmaDi(dati);
  if (f === FIRMA && dati.file === F) { D = dati; S = dati.stato; return false; }
  const memPrima = JSON.stringify(S.memoria_grafo || null);
  D = dati; S = dati.stato || {}; F = dati.file || {}; FIRMA = f;
  const memCambia = JSON.stringify(S.memoria_grafo || null) !== memPrima;
  if (memCambia) MEMC = {};
  ISTANZE.forEach((ist) => { try { if (memCambia && ist.id === 'memoria') pulisciMem(ist); ist._r(null); } catch (e) { setTimeout(() => { throw e; }); } });
  try { document.dispatchEvent(new CustomEvent('contenuti:dati')); } catch (e) {}
  return true;
}
FIRMA = firmaDi(D);

window.Contenuti = { pannelli: PANNELLI, monta: monta, riassunto: riassunto, ferma: ferma, suFerma: null, carica: carica };
})();
