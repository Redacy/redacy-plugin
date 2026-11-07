
/* ---------- PROCESSI ---------- */
function quandoParte(g) {
  const i = g.innesco || {};
  if (i.tipo === 'orario') { const q = String(i.quando || '').replace(/\s*Europe\/Rome\s*/i, '').trim(); return q ? cap(q) : 'A un\'ora fissa'; }
  if (i.tipo === 'evento') {
    if (i.fatto === 'file-nuovo') return 'Quando arriva un file nuovo in ' + (i.file || 'una cartella');
    return 'Quando succede: ' + (i.fatto || 'un fatto');
  }
  if (i.tipo === 'parola') return 'Quando lo chiedi tu';
  return i.tipo ? cap(String(i.tipo)) : 'Quando lo chiedi tu';
}
function quandoCorto(g) { const q = quandoParte(g); return q; }
function autonomiaParole(g) {
  const a = g.autonomia || {}; const liv = a.livello || 'L0';
  const m = { L0: 'Prepara tutto, l\'ultima parola è tua', L1: 'Prepara e consegna dopo il tuo sì', L2: 'Consegna da solo e ti racconta cosa ha fatto' };
  const chi = a.si ? 'L\'ha deciso ' + a.si : 'Non l\'ha ancora deciso nessuno';
  return { cosa: m[liv] || ('Livello ' + liv), chi: chi };
}
function tettiParole(g) {
  const t = g.tetti || {}; const p = [];
  if (t.corse_al_giorno) p.push('al massimo ' + t.corse_al_giorno + ' al giorno');
  if (t.contemporanee != null) p.push(t.contemporanee === 1 ? 'uno alla volta' : 'fino a ' + t.contemporanee + ' insieme');
  return p.length ? cap(p.join(', ')) : 'Nessun limite';
}
function esitoParole(c) {
  const e = eff(c);
  if (e === 'in-corso') return 'sta lavorando';
  if (e === 'persa') return 'non dà più notizie';
  if (e === 'finita') return 'è andato a buon fine';
  if (e === 'fermata') return c.stop && c.stop.chi === 'pannello' ? 'fermato da te' : 'fermato';
  if (e === 'fallita') { const pf = arr(c.passi).find((p) => p.stato === 'fallito'); return 'non è riuscito' + (pf && pf.nota ? ': ' + pf.nota : ''); }
  return e;
}
function ultimaVolta(g) {
  const c = ultimaCorsa(g); if (!c) return 'Non è ancora partito';
  return cap(quando(c.inizio)) + ' · ' + esitoParole(c);
}
const TIPI = { agente: { ic: 'spark', et: 'Un agente' }, cli: { ic: 'term', et: 'Un comando' }, uscita: { ic: 'out', et: 'Un risultato' }, umano: { ic: 'person', et: 'Un passo tuo' } };
const tipoDi = (def) => TIPI[def && def.tipo] || { ic: 'circle', et: 'Un passo' };
const icInnesco = (g) => ({ orario: 'clock', evento: 'bolt', parola: 'chat' }[(g.innesco || {}).tipo] || 'bolt');

function layoutWF(g, W, forza) {
  const passi = arr(g.passi); const ids = ['@T'].concat(passi.map((p) => p.id));
  const archi = arr(g.archi).filter((a) => a && ids.indexOf(a[0]) >= 0 && ids.indexOf(a[1]) >= 0);
  const haIn = {}; archi.forEach((a) => { haIn[a[1]] = 1; });
  const edges = archi.concat(passi.filter((p) => !haIn[p.id]).map((p) => ['@T', p.id]));
  const layer = { '@T': 0 };
  for (let it = 0; it < ids.length + 1; it++) edges.forEach((e) => { if (layer[e[0]] != null && (layer[e[1]] == null || layer[e[1]] < layer[e[0]] + 1) && layer[e[0]] + 1 <= ids.length) layer[e[1]] = layer[e[0]] + 1; });
  ids.forEach((i) => { if (layer[i] == null) layer[i] = 1; });
  const maxL = Math.max.apply(null, ids.map((i) => layer[i]));
  const col = []; for (let l = 0; l <= maxL; l++) col.push(ids.filter((i) => layer[i] === l));
  const H = { w: 152, h: 94, gx: 32, gy: 16, pad: 16 };
  const natW = (maxL + 1) * H.w + maxL * H.gx + 2 * H.pad;
  const orient = forza || (natW <= W + 70 ? 'o' : 'v');
  const d = orient === 'o' ? H : { w: Math.max(200, Math.min(320, W - 2 * 16)), h: 74, gx: 18, gy: 36, pad: 16 };
  const pos = {};
  const maxN = Math.max.apply(null, col.map((c) => c.length));
  col.forEach((c, l) => c.forEach((id, k) => {
    if (orient === 'o') {
      const colH = c.length * d.h + (c.length - 1) * d.gy, tot = maxN * d.h + (maxN - 1) * d.gy;
      pos[id] = { x: d.pad + l * (d.w + d.gx), y: d.pad + (tot - colH) / 2 + k * (d.h + d.gy) };
    } else {
      const rowW = c.length * d.w + (c.length - 1) * d.gx, tot = maxN * d.w + (maxN - 1) * d.gx;
      pos[id] = { x: d.pad + (tot - rowW) / 2 + k * (d.w + d.gx), y: d.pad + l * (d.h + d.gy) };
    }
  }));
  const w = orient === 'o' ? (maxL + 1) * d.w + maxL * d.gx + 2 * d.pad : maxN * d.w + (maxN - 1) * d.gx + 2 * d.pad;
  const h = orient === 'o' ? maxN * d.h + (maxN - 1) * d.gy + 2 * d.pad : (maxL + 1) * d.h + maxL * d.gy + 2 * d.pad;
  const arcs = edges.map((e) => {
    const a = pos[e[0]], b = pos[e[1]]; let p;
    if (orient === 'o') { const x1 = a.x + d.w, y1 = a.y + d.h / 2, x2 = b.x, y2 = b.y + d.h / 2, dx = Math.max(24, (x2 - x1) / 2); p = 'M' + x1 + ',' + y1 + ' C' + (x1 + dx) + ',' + y1 + ' ' + (x2 - dx) + ',' + y2 + ' ' + x2 + ',' + y2; }
    else { const x1 = a.x + d.w / 2, y1 = a.y + d.h, x2 = b.x + d.w / 2, y2 = b.y, dy = Math.max(16, (y2 - y1) / 2); p = 'M' + x1 + ',' + y1 + ' C' + x1 + ',' + (y1 + dy) + ' ' + x2 + ',' + (y2 - dy) + ' ' + x2 + ',' + y2; }
    return { da: e[0], a: e[1], d: p };
  });
  return { orient: orient, d: d, pos: pos, w: w, h: h, arcs: arcs, ids: ids };
}
function nodoStati(g) {
  const c = ultimaCorsa(g); const st = c ? statiPassi(c, g) : {}; return { c: c, st: st };
}
function wfHtml(ist, g, W) {
  const L = layoutWF(g, W); const ns = nodoStati(g); const d = L.d; const mid = ist.uid + '-fr';
  let h = '<div class="pc-wf" role="group" aria-label="Il processo disegnato passo per passo" tabindex="0"><div class="pc-wf-in" data-or="' + L.orient + '" style="width:' + L.w + 'px;height:' + L.h + 'px">' +
    '<svg class="pc-wf-svg" width="' + L.w + '" height="' + L.h + '" viewBox="0 0 ' + L.w + ' ' + L.h + '" aria-hidden="true"><defs><marker id="' + mid + '" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto"><path d="M1 1.5L8.5 5L1 8.5z" class="pc-frecc"/></marker></defs>';
  L.arcs.forEach((a) => { const ok = a.da === '@T' ? !!ns.c : ns.st[a.da] === 'fatto'; h += '<path class="pc-arco' + (ok ? ' pc-arco-ok' : '') + '" d="' + a.d + '" marker-end="url(#' + mid + ')"/>'; });
  h += '</svg>';
  const T = L.pos['@T'];
  h += '<div class="pc-nodo pc-nodo-innesco" style="left:' + T.x + 'px;top:' + T.y + 'px;width:' + d.w + 'px;height:' + d.h + 'px"><span class="pc-nodo-ic">' + ico(icInnesco(g), 20) + '</span><span class="pc-nodo-et">Parte</span><span class="pc-nodo-nome">' + esc(quandoParte(g)) + '</span></div>';
  arr(g.passi).forEach((p) => {
    const k = ns.c ? ns.st[p.id] : null; const s = k ? STATI[k] : null; const tp = tipoDi(p); const q = L.pos[p.id];
    h += '<button type="button" class="pc-nodo' + (s ? ' pc-s-' + s.cls : '') + (k === 'in-corso' ? ' pc-pulsa' : '') + '" data-az="passo" data-g="' + esc(g.grafo) + '" data-p="' + esc(p.id) + '" style="left:' + q.x + 'px;top:' + q.y + 'px;width:' + d.w + 'px;height:' + d.h + 'px" aria-label="' + esc(p.nome + (s ? ': ' + s.et : '')) + '">' +
      '<span class="pc-nodo-ic" title="' + esc(tp.et) + '">' + ico(tp.ic, 20) + '</span><span class="pc-nodo-et">' + esc(tp.et) + '</span><span class="pc-nodo-nome">' + esc(p.nome || umano(p.id)) + '</span>' +
      (s ? '<span class="pc-nodo-st">' + ico(s.ic, 14) + '<span>' + esc(s.et) + '</span></span>' : '') + '</button>';
  });
  return h + '</div></div>';
}
function schedaProcesso(g) {
  const c = ultimaCorsa(g); const au = autonomiaParole(g); const lk = c ? percorso(c, g) : '';
  return '<button type="button" class="pc-proc" data-az="grafo" data-g="' + esc(g.grafo) + '"><span class="pc-proc-testa"><span class="pc-proc-nome">' + esc(nomeProc(g.grafo)) + '</span>' +
    '<span class="pc-tag ' + (g.acceso ? 'pc-t-ok' : 'pc-t-calmo') + '">' + ico(g.acceso ? 'power' : 'minus', 14) + '<span>' + (g.acceso ? 'Acceso' : 'Spento') + '</span></span></span>' +
    '<span class="pc-proc-obj">' + esc(g.obiettivo) + '</span>' +
    '<dl class="pc-dl"><div><dt>Parte</dt><dd>' + esc(quandoParte(g)) + '</dd></div><div><dt>Fa da solo</dt><dd>' + esc(au.cosa) + '. <span class="pc-tenue">' + esc(au.chi) + '.</span></dd></div><div><dt>Ultima volta</dt><dd>' + esc(ultimaVolta(g)) + '</dd></div></dl>' +
    (lk ? '<span class="pc-proc-perc">' + lk + '</span>' : '') + '<span class="pc-proc-vai">Apri il processo' + ico('fwd', 14) + '</span></button>';
}
function righeCorse(g) {
  const l = corsePer(g.grafo); if (!l.length) return '<p class="pc-vuoto">Non è ancora girato.</p>';
  return '<div class="pc-corse">' + l.map((c) => {
    const st = statoCorsa(c);
    const passi = arr(c.passi).map((p) => { const def = defPasso(g, p.id); const s = STATI[p.stato] || STATI['da-fare'];
      return '<li class="pc-cp"><span class="pc-s-' + s.cls + ' pc-cp-ic">' + ico(s.ic, 14) + '</span><div><p class="pc-cp-h">' + esc(def ? def.nome : umano(p.id)) + ' <span class="pc-tenue">· ' + esc(s.et.toLowerCase()) + '</span></p>' +
        (p.esito ? '<p class="pc-cp-e">' + esc(p.esito) + '</p>' : '') + (p.nota ? '<p class="pc-cp-e pc-cp-nota">' + esc(p.nota) + '</p>' : '') + '</div></li>'; }).join('');
    return '<details class="pc-corsa"><summary><span class="pc-corsa-s">' + tag(st) + '<span class="pc-corsa-q">' + esc(cap(quando(c.inizio))) + '</span></span><span class="pc-corsa-e">' + esc(cap(esitoParole(c))) + '</span></summary><ul class="pc-cps">' + passi + '</ul></details>';
  }).join('') + '</div>';
}
function passoSchedaHtml(ist, g, p) {
  const tp = tipoDi(p); const ns = nodoStati(g); const k = ns.c ? ns.st[p.id] : null; const s = k ? STATI[k] : null;
  const rp = ns.c && arr(ns.c.passi).find((x) => x.id === p.id);
  const riga = (et, v) => v ? '<div><dt>' + et + '</dt><dd>' + v + '</dd></div>' : '';
  const area = p.workspace ? arr(S.workspace).find((w) => w.nome === p.workspace) : null;
  const idx = idxPasso(g, p.id); const prima = arr(g.archi).filter((a) => a[1] === p.id).map((a) => defPasso(g, a[0])).filter(Boolean);
  const dopo = arr(g.archi).filter((a) => a[0] === p.id).map((a) => defPasso(g, a[1])).filter(Boolean);
  const chipPasso = (q) => '<button type="button" class="pc-chip" data-az="passo" data-g="' + esc(g.grafo) + '" data-p="' + esc(q.id) + '">' + esc(q.nome || umano(q.id)) + '</button>';
  const forma = { bozza: 'una bozza', invio: 'un invio da fare a mano' }[p.forma] || p.forma;
  let cosa = '';
  if (p.tipo === 'agente') cosa = '<span class="pc-testoV">' + esc(p.prompt || '') + '</span>';
  else if (p.tipo === 'cli') cosa = 'Lancia un comando: <code class="pc-cod">' + esc(p.comando || '') + '</code>';
  else if (p.tipo === 'uscita') cosa = 'Lascia il risultato' + (forma ? ' come ' + esc(forma) : '');
  else if (p.tipo === 'umano') cosa = 'Aspetta te: rileggi e decidi' + (forma ? ' (' + esc(forma) + ')' : '');
  return '<div class="pc-scroll"><header class="pc-passo-testa"><span class="pc-passo-ic">' + ico(tp.ic, 26) + '</span><div><p class="pc-meta">' + esc(tp.et) + ' · passo ' + (idx + 1) + ' di ' + arr(g.passi).length + ' del processo ' + esc(nomeProc(g.grafo)) + '</p><h2 class="pc-tit">' + esc(p.nome || umano(p.id)) + '</h2></div>' + (s ? tag(s) : '') + '</header>' +
    '<dl class="pc-dl pc-dl-grande">' + riga('Cosa fa', cosa) +
    riga('In che area lavora', area ? '<button type="button" class="pc-chip" data-az="vai" data-p="aree" data-v="' + esc(area.nome) + '">' + esc(area.titolo) + '</button> <span class="pc-tenue">' + esc(area.serve) + '</span>' : (p.workspace ? esc(p.workspace) : '')) +
    riga('Dove lascia il risultato', p.dove ? esc(p.dove) + (forma && p.tipo !== 'agente' ? ' <span class="pc-tenue">(' + esc(forma) + ')</span>' : '') : '') +
    riga('Prima', prima.length ? prima.map(chipPasso).join(' ') : '<span class="pc-tenue">È il primo: parte ' + esc(quandoParte(g).toLowerCase()) + '</span>') +
    riga('Dopo', dopo.length ? dopo.map(chipPasso).join(' ') : '<span class="pc-tenue">È l\'ultimo passo</span>') + '</dl>' +
    '<h3 class="pc-sez">Nell\'ultima volta che è girato</h3>' + (ns.c ? '<div class="pc-ultima"><dl class="pc-dl"><div><dt>Quando</dt><dd>' + esc(cap(quando(ns.c.inizio))) + (rp && rp.inizio ? ' · il passo è partito ' + esc(quando(rp.inizio)) : '') + '</dd></div>' +
      '<div><dt>Com\'è andata</dt><dd>' + (s ? tag(s) : '') + '</dd></div>' + (rp && rp.esito ? '<div><dt>Esito</dt><dd>' + esc(rp.esito) + '</dd></div>' : '') + (rp && rp.nota ? '<div><dt>Nota</dt><dd>' + esc(rp.nota) + '</dd></div>' : '') + '</dl></div>' : '<p class="pc-vuoto">Non è ancora girato.</p>') +
    sezioneFile(g.file) + '</div>';
}
function legendaStati(g) {
  const ns = nodoStati(g); if (!ns.c) return '';
  const visti = {}; Object.keys(ns.st).forEach((k) => { visti[ns.st[k]] = 1; });
  return '<ul class="pc-leg">' + Object.keys(STATI).filter((k) => visti[k]).map((k) => '<li class="pc-s-' + STATI[k].cls + '">' + ico(STATI[k].ic, 14) + '<span>' + STATI[k].et + '</span></li>').join('') + '</ul>';
}
function gDaPila(ist) { const e = ist.pila[0]; return e && e.t === 'g' ? grafoPer(e.id) : null; }
function miniWF(g, ist) {
  const L = layoutWF(g, 99999, 'o'); const ns = nodoStati(g); const d = L.d;
  const nodo = (id, def) => {
    const q = L.pos[id]; const k = id === '@T' ? null : (ns.c ? ns.st[id] : null); const s = k ? STATI[k] : null;
    const tp = id === '@T' ? { ic: icInnesco(g) } : tipoDi(def);
    return '<g class="pc-mn' + (s ? ' pc-s-' + s.cls : '') + (k === 'in-corso' ? ' pc-pulsa-s' : '') + '" transform="translate(' + q.x + ',' + q.y + ')"><rect width="' + d.w + '" height="' + d.h + '" rx="16" class="pc-mn-r"/>' +
      '<svg x="' + (d.w / 2 - 28) + '" y="' + (d.h / 2 - 28) + '" width="56" height="56" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">' + IC[tp.ic] + '</svg>' +
      (s ? '<circle cx="' + (d.w - 8) + '" cy="8" r="17" class="pc-mn-b"/><svg x="' + (d.w - 8 - 12) + '" y="-4" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" class="pc-mn-g">' + IC[s.ic] + '</svg>' : '') + '</g>';
  };
  return '<svg class="pc-mini-svg" viewBox="0 0 ' + L.w + ' ' + L.h + '" preserveAspectRatio="xMidYMid meet" aria-hidden="true">' +
    L.arcs.map((a) => '<path class="pc-arco" d="' + a.d + '" style="stroke-width:5"/>').join('') +
    nodo('@T') + arr(g.passi).map((p) => nodo(p.id, p)).join('') + '</svg>';
}
function gAnteprima() {
  const gs = grafi(); if (!gs.length) return null;
  const run = gs.find((g) => { const c = ultimaCorsa(g); return c && eff(c) === 'in-corso'; });
  if (run) return run;
  return gs.slice().sort((a, b) => String((ultimaCorsa(b) || {}).inizio || '').localeCompare(String((ultimaCorsa(a) || {}).inizio || '')))[0];
}
P.processi = {
  pieno(ist) {
    const W = Math.max(280, (ist.root.clientWidth || 600) - 40);
    const e = ist.pila[0];
    if (!e) {
      const gs = grafi();
      return '<div class="pc-scroll"><header class="pc-intro"><h2 class="pc-tit">I tuoi processi</h2><p class="pc-p pc-tenue">Lavori che seguono sempre gli stessi passi. Apri un processo per vedere come funziona, passo per passo.</p></header><div class="pc-proc-lista">' +
        (gs.length ? gs.map(schedaProcesso).join('') : '<p class="pc-vuoto">Non c\'è ancora nessun processo.</p>') + '</div></div>';
    }
    const g = grafoPer(e.id); if (!g) return '<div class="pc-scroll"><p class="pc-vuoto">Processo non trovato.</p></div>';
    if (ist.pila[1] && ist.pila[1].t === 'p') { const p = defPasso(g, ist.pila[1].id); if (p) return passoSchedaHtml(ist, g, p); }
    const au = autonomiaParole(g);
    return '<div class="pc-scroll"><header class="pc-passo-testa"><div><h2 class="pc-tit">' + esc(nomeProc(g.grafo)) + '</h2></div><span class="pc-tag ' + (g.acceso ? 'pc-t-ok' : 'pc-t-calmo') + '">' + ico(g.acceso ? 'power' : 'minus', 14) + '<span>' + (g.acceso ? 'Acceso' : 'Spento') + '</span></span></header>' +
      '<p class="pc-obj-g">' + esc(g.obiettivo) + '</p>' + (g.descrizione ? '<p class="pc-p">' + esc(String(g.descrizione).trim()) + '</p>' : '') +
      '<dl class="pc-dl pc-dl-grande"><div><dt>Quando parte</dt><dd>' + esc(quandoParte(g)) + '</dd></div><div><dt>Quanto fa da solo</dt><dd>' + esc(au.cosa) + '. <span class="pc-tenue">' + esc(au.chi) + '.</span></dd></div>' +
      '<div><dt>Limiti</dt><dd>' + esc(tettiParole(g)) + '</dd></div><div><dt>Cosa produce</dt><dd>' + (arr(g.uscite).length ? esc(arr(g.uscite).join(', ')) : '<span class="pc-tenue">niente di scritto</span>') + '</dd></div></dl>' +
      '<h3 class="pc-sez">Passo per passo</h3>' + wfHtml(ist, g, W) + legendaStati(g) +
      '<p class="pc-suggerimento">Tocca un passo per vedere cosa fa.</p>' +
      '<h3 class="pc-sez">Le ultime volte che è girato</h3>' + righeCorse(g) + sezioneFile(g.file) + '</div>';
  },
  anteprima(ist) {
    const g = gAnteprima(); const gs = grafi(); const acc = gs.filter((x) => x.acceso).length;
    if (!g) return '<div class="pc-an"><p class="pc-an-et">Nessun processo</p></div>';
    const c = ultimaCorsa(g); const pc = c && eff(c) === 'in-corso' ? passoCorrente(c, g) : null;
    return '<div class="pc-an pc-an-proc"><p class="pc-an-tit">' + esc(nomeProc(g.grafo)) + '</p><p class="pc-an-sub">' + (pc ? 'Sta lavorando · ' + esc(pc.nome) : c ? esc(cap(esitoParole(c))) : 'Non è ancora partito') + '</p><div class="pc-mini">' + miniWF(g, ist) + '</div><p class="pc-an-pie">' + plur(gs.length, 'processo', 'processi') + ', ' + acc + (acc === 1 ? ' acceso' : ' accesi') + '</p></div>';
  },
  vai(ist, v) {
    v = String(v || ''); const m = v.match(/^(?:grafi\/)?([^\/]+?)(?:\.ya?ml)?(?:\/([^\/]+))?$/); if (!m) return false;
    const g = grafoPer(m[1]); if (!g) return false;
    ist.pila = [{ t: 'g', id: g.grafo }];
    if (m[2] && defPasso(g, m[2])) ist.pila.push({ t: 'p', id: m[2] });
    return true;
  },
  az(ist, a, el) {
    if (a === 'grafo') { ist.pila = [{ t: 'g', id: el.dataset.g }]; return 'avanti'; }
    if (a === 'passo') { const g = el.dataset.g; ist.pila = [{ t: 'g', id: g }, { t: 'p', id: el.dataset.p }]; return 'avanti'; }
    return null;
  },
  livelli(ist) {
    const out = []; const e = ist.pila[0]; if (!e) return out;
    out.push(nomeProc(e.id));
    if (ist.pila[1]) { const g = grafoPer(e.id); const p = defPasso(g, ist.pila[1].id); out.push(p ? (p.nome || umano(p.id)) : umano(ist.pila[1].id)); }
    return out;
  },
  dopo(ist, root) {
    const w = $(root, '.pc-wf'); if (!w) return;
    if (!ist._ro && typeof ResizeObserver !== 'undefined') {
      ist._ro = new ResizeObserver(() => {
        const e = ist.pila[0]; if (!e || ist.modo !== 'pieno' || ist.pila[1]) return;
        const g = grafoPer(e.id); const W = Math.max(280, (root.clientWidth || 600) - 40);
        const cur = $(root, '.pc-wf-in'); if (!g || !cur) return;
        if (layoutWF(g, W).orient !== cur.dataset.or) ist._r(null);
      });
      ist._ro.observe(root);
    }
  },
};
