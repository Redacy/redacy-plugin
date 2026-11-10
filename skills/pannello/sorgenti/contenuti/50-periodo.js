
/* ---------- PERIODO ---------- */
const todoLista = () => arr(S.periodo && S.periodo.todo && S.periodo.todo.todo);
const ideeLista = () => arr(S.periodo && S.periodo.idee && S.periodo.idee.idee);
const dataCorta = (s) => s ? (giornoParole(s) === 'oggi' || giornoParole(s) === 'ieri' ? giornoParole(s) : 'il ' + fGM.format(dataDaYMD(s))) : '';
function obiettivoHtml(ist) {
  const src = F['periodo/obiettivo.md'];
  if (S.periodo && S.periodo.obiettivo_vuoto) return '<p class="pc-vuoto">Per questo periodo non c\'è ancora un obiettivo. Per darglielo ' + chiedi('pianifichiamo il periodo') + '</p>';
  if (src != null) { const t = primoTitolo(src); const corpo = src.replace(/<\!--[\s\S]*?-->/g, '').replace(/^#\s+.*$/m, ''); const r = md(corpo, { uid: ist.uid + 'o' }); return { titolo: t, html: r.html }; }
  return { titolo: 'Obiettivo del periodo', html: '<p class="pc-p">' + esc(S.periodo.obiettivo || '') + '</p>' };
}
function cardTodo(t, ist) {
  const fatto = t.stato === 'fatto'; const rit = !fatto && t.scadenza && giorniFra(t.scadenza, oggiYMD()) > 0; const lk = linkFile(t.dove);
  const st = fatto ? STATI.fatto : (t.stato === 'in corso' ? STATI['in-corso'] : (t.chi === 'tu' ? STATI.attesa : STATI['da-fare']));
  return '<article class="pc-todo' + (rit ? ' pc-todo-rit' : '') + (fatto ? ' pc-todo-fatto' : '') + (ist.evid === t.id ? ' pc-evid' : '') + '" id="' + ist.uid + '-' + esc(t.id) + '"><span class="pc-todo-ic pc-s-' + st.cls + '">' + ico(st.ic, 18) + '</span><div class="pc-todo-t"><h3 class="pc-voce-h">' + esc(t.cosa) + '</h3>' +
    '<p class="pc-meta">' + esc(cap(daParole(t.da))) + (t.scadenza && !fatto ? ' · entro ' + esc(giornoParole(t.scadenza)) : '') + (fatto && t.aggiornato ? ' · fatto ' + esc(dataCorta(t.aggiornato)) : '') + '</p>' +
    '<p class="pc-voce-tag">' + (rit ? '<span class="pc-tag pc-t-attesa">' + ico('alert', 14) + '<span>In ritardo di ' + plur(giorniRitardo(t), 'giorno', 'giorni') + '</span></span> ' : '') + (!fatto && st.cls !== 'attesa' ? tag(st) : '') + '</p></div>' +
    (lk ? '<button type="button" class="pc-btn" data-az="vai" data-p="' + esc(lk.pannello) + '" data-v="' + esc(lk.voce) + '">' + esc(lk.et) + ico('fwd', 14) + '</button>' : (t.dove ? '<span class="pc-dove">' + ico('folder', 14) + '<code>' + esc(t.dove) + '</code></span>' : '')) + '</article>';
}
function foglietto(i) {
  const dove = daParole(i.da_dove);
  return '<article class="pc-idea"><p class="pc-idea-t">' + esc(i.idea) + '</p><p class="pc-meta">Arrivata ' + esc(dove) + (i.arrivata ? ' ' + esc(dataCorta(i.arrivata)) : '') + '</p><p class="pc-idea-e">' + (i.esito ? ico('check', 14) + '<span>' + esc(i.esito) + '</span>' : ico('clock', 14) + '<span>Ancora da pesare nel prossimo piano</span>') + '</p></article>';
}
P.periodo = {
  pieno(ist) {
    const e = ist.pila[0];
    if (e && e.t === 'f') return '<div class="pc-scroll"><header class="pc-intro"><h1 class="pc-tit">' + esc(e.p.replace(/^periodo\//, '')) + '</h1><p class="pc-p pc-tenue">Il file così com\'è nella cartella del periodo, mostrato come schede.</p></header>' + sezioneFile(e.p, { titolo: 'Le schede del file', aperto: false }) + '</div>';
    const ob = obiettivoHtml(ist); const T = todoLista(); const fatte = T.filter((t) => t.stato === 'fatto').length; const perc = T.length ? Math.round(fatte / T.length * 100) : 0;
    const tu = T.filter((t) => t.chi === 'tu' && t.stato !== 'fatto'), ag = T.filter((t) => t.chi !== 'tu' && t.stato !== 'fatto'), fa = T.filter((t) => t.stato === 'fatto');
    const gruppo = (tit, l, vuoto) => '<section class="pc-sezione"><h2 class="pc-sez">' + tit + (l.length ? ' <span class="pc-sez-n">' + l.length + '</span>' : '') + '</h2>' + (l.length ? '<div class="pc-voci">' + l.map((t) => cardTodo(t, ist)).join('') + '</div>' : '<p class="pc-vuoto">' + vuoto + '</p>') + '</section>';
    const idee = ideeLista(); const vuotoTutto = !T.length && !idee.length;
    return '<div class="pc-scroll"><section class="pc-ob"><p class="pc-et">' + (typeof ob === 'string' ? 'Obiettivo' : esc(ob.titolo)) + (S.periodo.todo && S.periodo.todo.periodo ? ' · ' + esc(S.periodo.todo.periodo) : '') + '</p>' +
      '<div class="pc-ob-md">' + (typeof ob === 'string' ? ob : ob.html) + '</div>' +
      (T.length ? '<div class="pc-prog"><div class="pc-barra-p" role="progressbar" aria-valuemin="0" aria-valuemax="' + T.length + '" aria-valuenow="' + fatte + '" aria-label="Cose fatte"><span style="width:' + perc + '%"></span></div><p class="pc-meta">' + plur(fatte, 'cosa fatta', 'cose fatte') + ' su ' + T.length + '</p></div>' : '') + '</section>' +
      (vuotoTutto ? '' : '<div class="pc-cols">' + '<div class="pc-col">' + gruppo('Tocca a te', tu, 'Niente aspetta te.') + gruppo('Tocca agli agenti', ag, 'Nessun agente ha qualcosa in coda.') + '</div>' +
      '<div class="pc-col">' + gruppo('Fatto', fa, 'Ancora niente di fatto.') +
      '<section class="pc-sezione"><h2 class="pc-sez">Le idee' + (idee.length ? ' <span class="pc-sez-n">' + idee.length + '</span>' : '') + '</h2>' + (idee.length ? '<div class="pc-idee">' + idee.map(foglietto).join('') + '</div><p class="pc-meta pc-nota-idee">Le idee non cambiano il periodo: le pesi quando fai il prossimo piano.</p>' : '<p class="pc-vuoto">Nessuna idea in attesa.</p>') + '</section></div></div>') +
      '<section class="pc-sezione"><h2 class="pc-sez">Guarda i file come sono scritti</h2><div class="pc-fbtn">' +
      ['periodo/todo.json', 'periodo/idee.json'].filter((p) => F[p] != null).map((p) => '<button type="button" class="pc-btn" data-az="file" data-p="' + p + '">' + ico('file', 14) + p.replace('periodo/', '') + ico('fwd', 14) + '</button>').join('') + '</div></section></div>';
  },
  anteprima() {
    const T = todoLista(); const fatte = T.filter((t) => t.stato === 'fatto').length; const perc = T.length ? Math.round(fatte / T.length * 100) : 0;
    if (!T.length && (!S.periodo || S.periodo.obiettivo_vuoto || !S.periodo.obiettivo)) return '<div class="pc-an pc-an-vuota"><p class="pc-an-tit">Ancora nessun obiettivo</p><p class="pc-an-sub2">Decidi con l\'agente cosa conta nelle prossime settimane: da lì nascono le cose da fare.</p></div>';
    const ob = S.periodo && S.periodo.obiettivo_vuoto ? 'Ancora nessun obiettivo' : (S.periodo.obiettivo || '');
    return '<div class="pc-an pc-an-per"><p class="pc-an-et2">Obiettivo del periodo</p><p class="pc-an-ob">' + esc(ob) + '</p><div class="pc-prog"><div class="pc-barra-p" aria-hidden="true"><span style="width:' + perc + '%"></span></div><p class="pc-an-pie">' + T.length + ' cose, ' + fatte + (fatte === 1 ? ' fatta' : ' fatte') + '</p></div></div>';
  },
  vai(ist, v) {
    v = String(v || ''); const p = v.indexOf('/') < 0 ? 'periodo/' + v : v;
    if (/^periodo\/(todo|idee)\.json$/.test(p) && F[p] != null) { ist.pila = [{ t: 'f', p: p }]; return true; }
    if (/obiettivo/.test(v)) { ist.pila = []; return true; }
    if (todoLista().some((t) => t.id === v)) { ist.pila = []; ist.evid = v; ist._evidDopo = true; return true; }
    return false;
  },
  az(ist, a, el) { if (a === 'file') { ist.pila = [{ t: 'f', p: el.dataset.p }]; return 'avanti'; } return null; },
  livelli(ist) { return ist.pila.map((e) => e.p.replace(/^periodo\//, '')); },
  dopo(ist, root) {
    if (ist._evidDopo) { ist._evidDopo = false; const el = document.getElementById(ist.uid + '-' + ist.evid); const sc = $(root, '.pc-scroll'); if (el && sc) scrollA(sc, el); }
  },
};

/* ---------- AREE ---------- */
const radice = () => ({ titolo: primoTitolo(F['AGENTS.md']) || 'L\'orchestratore dello studio', par: (primoParagrafo(F['AGENTS.md']).match(/^.*?[.!?](?=\s|$)/) || [primoParagrafo(F['AGENTS.md'])])[0] });
function offRel(el, cont) { let x = 0, y = 0, n = el; while (n && n !== cont) { x += n.offsetLeft; y += n.offsetTop; n = n.offsetParent; } return { x: x, y: y, w: el.offsetWidth, h: el.offsetHeight }; }
const senzaH1 = (t) => String(t).replace(/<\!--[\s\S]*?-->/g, '').replace(/^\s*#\s+.*\n?/, '');
function conta(w) {
  const p = [plur(w.pagine_memoria, 'pagina di memoria', 'pagine di memoria')];
  if (w.todo_aperti) p.push(plur(w.todo_aperti, 'cosa aperta', 'cose aperte'));
  const np = arr(w.processi).length; if (np) p.push(plur(np, 'processo', 'processi'));
  return p.join(' · ');
}
function pezzoSx(l) { return l.map((w) => '<button type="button" class="pc-area" data-az="area" data-n="' + esc(w.nome) + '" data-aree-n="1"><span class="pc-area-t">' + esc(w.titolo) + '</span><span class="pc-area-s">' + esc(w.serve) + '</span><span class="pc-area-c">' + esc(conta(w)) + '</span></button>').join(''); }
function connetti(ist) {
  const root = ist.root, c = $(root, '.pc-aree'); if (!c) return; const svg = $(c, '.pc-aree-svg'), orch = $(c, '.pc-orch'); if (!svg || !orch) return;
  const wCont = c.offsetWidth, hCont = c.offsetHeight; svg.setAttribute('width', wCont); svg.setAttribute('height', hCont); svg.setAttribute('viewBox', '0 0 ' + wCont + ' ' + hCont);
  const o = offRel(orch, c); const larga = c.dataset.or === 'l'; let d = '';
  $$(c, '.pc-area').forEach((a) => {
    const r = offRel(a, c);
    if (larga) { const dx = r.x + r.w / 2 < o.x + o.w / 2; const x0 = dx ? o.x : o.x + o.w, y0 = o.y + o.h / 2, x1 = dx ? r.x + r.w : r.x, y1 = r.y + r.h / 2, k = Math.abs(x1 - x0) / 2; d += '<path class="pc-arco pc-arco-ok" d="M' + x0 + ',' + y0 + ' C' + (x0 + (dx ? -k : k)) + ',' + y0 + ' ' + (x1 + (dx ? k : -k)) + ',' + y1 + ' ' + x1 + ',' + y1 + '"/>'; }
    else { const x0 = o.x + 22, y0 = o.y + o.h, x1 = r.x, y1 = r.y + r.h / 2; d += '<path class="pc-arco pc-arco-ok" d="M' + x0 + ',' + y0 + ' L' + x0 + ',' + (y1 - 10) + ' Q' + x0 + ',' + y1 + ' ' + (x0 + 10) + ',' + y1 + ' L' + x1 + ',' + y1 + '"/>'; }
  });
  svg.innerHTML = d;
}
function areeLivello1(ist) {
  const ws = arr(S.workspace); const r = radice();
  const sx = ws.filter((_, i) => i % 2 === 0), dx = ws.filter((_, i) => i % 2 === 1);
  return '<div class="pc-scroll"><header class="pc-intro"><h1 class="pc-tit">Chi si occupa di cosa</h1><p class="pc-p pc-tenue">Al centro c\'è l\'orchestratore: riceve le richieste e decide a quale area affidarle. Ogni area ha il suo modo di lavorare e la sua memoria.</p></header>' +
    '<div class="pc-aree" data-or="' + (ist.areeOr || 'l') + '"><div class="pc-aree-col pc-aree-sx">' + pezzoSx(sx) + '</div><button type="button" class="pc-orch" data-az="orch"><span class="pc-orch-et">' + ico('spark', 16) + 'L\'orchestratore</span><span class="pc-area-t">' + esc(r.titolo) + '</span><span class="pc-area-s">' + esc(r.par.length > 200 ? r.par.slice(0, 197).replace(/\s+\S*$/, '') + '…' : r.par) + '</span><span class="pc-proc-vai">Leggi come lavora' + ico('fwd', 14) + '</span></button><div class="pc-aree-col pc-aree-dx">' + pezzoSx(dx) + '</div><svg class="pc-aree-svg" aria-hidden="true"></svg></div></div>';
}
function areaDettaglio(ist, w) {
  const path = w.percorso + '/AGENTS.md'; const src = F[path]; const r = src != null ? md(senzaH1(src), { uid: ist.uid + 'a', area: w.nome }) : null;
  const pagine = arr(S.memoria).filter((m) => m.area === w.nome);
  const aperte = todoLista().filter((t) => t.stato !== 'fatto' && t.dove && String(t.dove).replace(/\/$/, '') === w.percorso);
  return '<div class="pc-scroll"><header class="pc-passo-testa"><div><p class="pc-meta">Area di lavoro</p><h1 class="pc-tit">' + esc(w.titolo) + '</h1></div></header><p class="pc-obj-g">' + esc(w.serve) + '</p>' +
    '<div class="pc-cols pc-cols-2"><section class="pc-sezione"><h2 class="pc-sez">Le sue pagine di memoria<span class="pc-sez-n">' + pagine.length + '</span></h2>' + (pagine.length ? '<p class="pc-chips">' + pagine.map((m) => '<button type="button" class="pc-chip" data-az="vai" data-p="memoria" data-v="' + esc(m.dove) + '">' + ico('file', 14) + esc(m.titolo) + '</button>').join(' ') + '</p>' : '<p class="pc-vuoto">Ancora nessuna pagina.</p>') + '</section>' +
    '<section class="pc-sezione"><h2 class="pc-sez">I suoi processi<span class="pc-sez-n">' + arr(w.processi).length + '</span></h2>' + (arr(w.processi).length ? '<p class="pc-chips">' + arr(w.processi).map((g) => '<button type="button" class="pc-chip" data-az="vai" data-p="processi" data-v="' + esc(g) + '">' + ico('spark', 14) + esc(nomeProc(g)) + '</button>').join(' ') + '</p>' : '<p class="pc-vuoto">Nessun processo lavora qui.</p>') + '</section></div>' +
    '<section class="pc-sezione"><h2 class="pc-sez">Cose aperte<span class="pc-sez-n">' + aperte.length + '</span></h2>' + (aperte.length ? '<div class="pc-voci">' + aperte.map((t) => cardTodo(t, ist)).join('') + '</div>' : '<p class="pc-vuoto">Niente di aperto in quest\'area.</p>') + '</section>' +
    '<h2 class="pc-sez">Come lavora questa area</h2><div class="pc-md">' + (r ? r.html : '<p class="pc-vuoto">Il testo non è nei dati.</p>') + '</div>' + (src != null ? sezioneFile(path, { titolo: 'Guarda il file com\'è scritto' }) : '') + '</div>';
}
P.aree = {
  pieno(ist) {
    const e = ist.pila[0];
    if (!e) { ist.areeOr = (ist.root.clientWidth || 700) >= 640 ? 'l' : 's'; return areeLivello1(ist); }
    if (e.t === 'o') {
      const src = F['AGENTS.md'] || ''; const r = md(senzaH1(src), { uid: ist.uid + 'r' }); const toc = r.toc.filter((t) => t.n === 2);
      return '<div class="pc-scroll"><header class="pc-passo-testa"><div><p class="pc-meta">L\'orchestratore dello studio</p><h1 class="pc-tit">' + esc(radice().titolo) + '</h1></div></header>' +
        (toc.length ? '<nav class="pc-toc" aria-label="Indice delle sezioni"><p class="pc-et">In questa pagina</p><ol>' + toc.map((t) => '<li><button type="button" class="pc-chip" data-az="ancora" data-id="' + esc(t.id) + '">' + esc(t.t) + '</button></li>').join('') + '</ol></nav>' : '') +
        '<div class="pc-md">' + r.html + '</div>' + sezioneFile('AGENTS.md') + '</div>';
    }
    const w = arr(S.workspace).find((x) => x.nome === e.n); return w ? areaDettaglio(ist, w) : '<div class="pc-scroll"><p class="pc-vuoto">Area non trovata.</p></div>';
  },
  anteprima() {
    const ws = arr(S.workspace); const r = radice();
    return '<div class="pc-an pc-an-aree"><p class="pc-an-orch">' + ico('spark', 14) + '<span>' + esc(r.titolo) + '</span></p><div class="pc-an-tessere">' + ws.map((w) => '<span class="pc-tess"><span class="pc-tess-t">' + esc(w.titolo) + '</span><span class="pc-tess-c">' + esc(conta(w)) + '</span></span>').join('') + '</div><p class="' + (ws.length ? 'pc-an-pie">' + plur(ws.length, 'area', 'aree') : 'pc-an-sub2">Ogni lavoro che affidi diventa un\'area, con il suo agente AI.') + '</p></div>';
  },
  vai(ist, v) {
    v = String(v || ''); if (v === 'orchestratore' || v === 'AGENTS.md' || v === 'radice') { ist.pila = [{ t: 'o' }]; return true; }
    const m = v.match(/^workspace\/([^\/]+)/); const n = m ? m[1] : v; const w = arr(S.workspace).find((x) => x.nome === n || x.titolo === v);
    if (!w) return false; ist.pila = [{ t: 'a', n: w.nome }]; return true;
  },
  az(ist, a, el) {
    if (a === 'area') { ist.pila = [{ t: 'a', n: el.dataset.n }]; return 'avanti'; }
    if (a === 'orch') { ist.pila = [{ t: 'o' }]; return 'avanti'; }
    return null;
  },
  livelli(ist) { const e = ist.pila[0]; if (!e) return []; if (e.t === 'o') return [radice().titolo]; const w = arr(S.workspace).find((x) => x.nome === e.n); return [w ? w.titolo : e.n]; },
  dopo(ist, root) {
    if (!$(root, '.pc-aree')) return;
    connetti(ist); requestAnimationFrame(() => connetti(ist));
    if (!ist._roA && typeof ResizeObserver !== 'undefined') {
      ist._roA = new ResizeObserver(() => { if (ist.modo !== 'pieno' || ist.pila.length) return; const o = (root.clientWidth || 700) >= 640 ? 'l' : 's'; const c = $(root, '.pc-aree'); if (!c) return; if (c.dataset.or !== o) { ist._r(null); } else connetti(ist); });
      ist._roA.observe(root);
    }
  },
};
