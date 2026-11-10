
/* ---------- MEMORIA: il grafo a forze, scritto qui, niente librerie ---------- */
const PAL = ['#2f6fb6', '#d9902c', '#1f9a80', '#c75a48', '#7c8a2e', '#5b7f95'];
let MEMC = {};
function mulberry(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function assesta(nodes, edges, vert) {
  const n = nodes.length, rnd = mulberry(11); const aree = []; nodes.forEach((x) => { if (aree.indexOf(x.area) < 0) aree.push(x.area); });
  nodes.forEach((x, i) => {
    const ai = aree.indexOf(x.area), ang = ai / Math.max(1, aree.length) * Math.PI * 2;
    x.x = Math.cos(ang) * 220 + (rnd() - .5) * 160; x.y = Math.sin(ang) * 150 + (rnd() - .5) * 120; if (vert) { const t = x.x; x.x = x.y; x.y = t; } x.vx = 0; x.vy = 0;
  });
  const N = 460;
  for (let it = 0; it < N; it++) {
    const al = 1 - it / N; const fx = new Array(n).fill(0), fy = new Array(n).fill(0);
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      let dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y; let d2 = dx * dx + dy * dy + 0.5; const d = Math.sqrt(d2);
      const f = 11000 / d2 * (0.35 + al); dx /= d; dy /= d; fx[i] += dx * f; fy[i] += dy * f; fx[j] -= dx * f; fy[j] -= dy * f;
      const mn = nodes[i].r + nodes[j].r + 16; if (d < mn) { const p = (mn - d) * 0.5; fx[i] += dx * p; fy[i] += dy * p; fx[j] -= dx * p; fy[j] -= dy * p; }
    }
    edges.forEach((e) => {
      const a = nodes[e.a], b = nodes[e.b]; const dx = b.x - a.x, dy = b.y - a.y, d = Math.sqrt(dx * dx + dy * dy) + 0.01;
      const tg = 96 + a.r + b.r, f = (d - tg) * 0.035; fx[e.a] += dx / d * f; fy[e.a] += dy / d * f; fx[e.b] -= dx / d * f; fy[e.b] -= dy / d * f;
    });
    const cen = {}; nodes.forEach((x) => { if (x.miss) return; const c = cen[x.area] || (cen[x.area] = { x: 0, y: 0, n: 0 }); c.x += x.x; c.y += x.y; c.n++; });
    nodes.forEach((x, i) => {
      if (vert) { fx[i] -= x.x * 0.017; fy[i] -= x.y * 0.009; } else { fx[i] -= x.x * 0.009; fy[i] -= x.y * 0.017; }
      if (!x.miss && cen[x.area] && cen[x.area].n > 1) { fx[i] += (cen[x.area].x / cen[x.area].n - x.x) * 0.012; fy[i] += (cen[x.area].y / cen[x.area].n - x.y) * 0.012; }
      x.vx = (x.vx + fx[i]) * 0.78; x.vy = (x.vy + fy[i]) * 0.78; const sp = Math.sqrt(x.vx * x.vx + x.vy * x.vy), mx = 24 * (0.3 + al);
      if (sp > mx) { x.vx *= mx / sp; x.vy *= mx / sp; }
      x.x += x.vx; x.y += x.vy;
    });
  }
}
function memModello(vert) {
  const G = S.memoria_grafo || { nodi: [], archi: [] }; const nodi = arr(G.nodi), archi = arr(G.archi);
  const sig = nodi.length + '/' + archi.length + '/' + (nodi[0] && nodi[0].chiave) + '/' + (nodi[nodi.length - 1] && nodi[nodi.length - 1].chiave);
  const ck = vert ? 'v' : 'o'; if (MEMC[ck] && MEMC[ck].sig === sig) return MEMC[ck];
  const idx = {}; const nodes = nodi.map((x, i) => { idx[x.chiave] = i; return { k: x.chiave, t: x.titolo || umano(stem(x)), area: x.area, dove: x.dove, g: x.grado || 0, miss: !!x.mancante, riga: x.riga, cit: arr(x.citata_da), r: 6 + Math.sqrt(x.grado || 0) * 3.6 + (x.mancante ? -1 : 1) }; });
  const edges = archi.filter((e) => idx[e.da] != null && idx[e.a] != null).map((e) => ({ a: idx[e.da], b: idx[e.a], miss: !!e.mancante }));
  assesta(nodes, edges, vert);
  const adj = nodes.map(() => new Set()); edges.forEach((e) => { adj[e.a].add(e.b); adj[e.b].add(e.a); });
  const aree = []; nodes.forEach((x) => { if (!x.miss && aree.indexOf(x.area) < 0) aree.push(x.area); });
  MEMC[ck] = { sig: sig, nodes: nodes, edges: edges, adj: adj, aree: aree, idx: idx };
  return MEMC[ck];
}
const coloreArea = (m, area) => { const i = m.aree.indexOf(area); return PAL[(i < 0 ? 5 : i) % PAL.length]; };
function leggiColori(root) {
  const cs = getComputedStyle(root); const g = (n, d) => (cs.getPropertyValue(n) || '').trim() || d;
  return { t: g('--_t', '#1c1c1e'), t2: g('--_t2', '#4a4a50'), t3: g('--_t3', '#6b6b73'), acc: g('--_acc', '#2f5fd0'), att: g('--_att', '#b26a00') };
}
function chiaro(c) { // il colore del testo e' chiaro? allora lo sfondo e' scuro
  try { const x = document.createElement('canvas').getContext('2d'); x.fillStyle = '#000'; x.fillStyle = c; const s = x.fillStyle; let r, g, b;
    if (s[0] === '#') { r = parseInt(s.substr(1, 2), 16); g = parseInt(s.substr(3, 2), 16); b = parseInt(s.substr(5, 2), 16); } else { const m = s.match(/[\d.]+/g); r = +m[0]; g = +m[1]; b = +m[2]; }
    return (r * 299 + g * 587 + b * 114) / 1000 > 140; } catch (e) { return false; }
}
function grafoCtrl(canvas, root, opz) {
  let m = memModello(false); opz = opz || {};
  let nodes = m.nodes.map((n) => Object.assign({}, n)); let edges = m.edges, adj = m.adj, scelto = false;
  const ctx = canvas.getContext('2d'); let W = 0, H = 0, dpr = 1; const view = { k: 1, tx: 0, ty: 0 };
  let hover = null, sel = null, filtro = null, mosso = false, pend = null, raf = 0, anim = 0, intro = 0, inIntro = false;
  const ordG = nodes.map((n) => n.g).sort((a, b) => b - a); const sogliaG = opz.statico ? (ordG[2] || 1) : (ordG[Math.min(ordG.length - 1, Math.max(3, Math.round(ordG.length * 0.3)))] || 1);
  let col = leggiColori(root), scuro = chiaro(col.t);
  const toW = (x, y) => ({ x: (x - view.tx) / view.k, y: (y - view.ty) / view.k });
  function fit() {
    if (!W || !H || !nodes.length) return; let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
    nodes.forEach((n) => { x0 = Math.min(x0, n.x - n.r); x1 = Math.max(x1, n.x + n.r); y0 = Math.min(y0, n.y - n.r); y1 = Math.max(y1, n.y + n.r); });
    const pad = opz.statico ? 22 : 34, bw = x1 - x0 + 1, bh = y1 - y0 + 1;
    const k = Math.min((W - 2 * pad) / bw, (H - 2 * pad) / bh, opz.statico ? 2.4 : 1.8);
    view.k = k; view.tx = W / 2 - (x0 + x1) / 2 * k; view.ty = H / 2 - (y0 + y1) / 2 * k;
  }
  const lit = (i) => { if (hover != null) return i === hover || adj[hover].has(i); if (filtro) return filtro.has(i); return true; };
  function draw() {
    raf = 0; if (!W) return; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
    ctx.lineCap = 'round'; const spento = hover != null || filtro;
    edges.forEach((e) => {
      const a = nodes[e.a], b = nodes[e.b]; const acceso = hover != null ? (e.a === hover || e.b === hover) : filtro ? (filtro.has(e.a) && filtro.has(e.b)) : true;
      ctx.globalAlpha = spento ? (acceso ? 0.95 : 0.07) : 0.5; ctx.strokeStyle = hover != null && acceso ? col.acc : col.t3; ctx.lineWidth = hover != null && acceso ? 2 : 1.2;
      ctx.setLineDash(e.miss ? [4, 4] : []); ctx.beginPath(); ctx.moveTo(a.x * view.k + view.tx, a.y * view.k + view.ty); ctx.lineTo(b.x * view.k + view.tx, b.y * view.k + view.ty); ctx.stroke();
    });
    ctx.setLineDash([]);
    const ord = nodes.map((_, i) => i).sort((i, j) => (lit(i) ? 1 : 0) - (lit(j) ? 1 : 0));
    ord.forEach((i) => {
      const n = nodes[i], sx = n.x * view.k + view.tx, sy = n.y * view.k + view.ty, sr = Math.max(4, n.r * view.k); const l = lit(i);
      ctx.globalAlpha = spento && !l ? 0.16 : 1; const c = coloreArea(m, n.area);
      ctx.beginPath(); ctx.arc(sx, sy, sr, 0, 6.2832);
      if (n.miss) { ctx.fillStyle = scuro ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.05)'; ctx.fill(); ctx.setLineDash([4, 3]); ctx.strokeStyle = col.t2; ctx.lineWidth = 1.6; ctx.stroke(); ctx.setLineDash([]); }
      else { ctx.fillStyle = c; ctx.fill(); ctx.strokeStyle = scuro ? 'rgba(255,255,255,.5)' : 'rgba(0,0,0,.28)'; ctx.lineWidth = 1.4; ctx.stroke(); }
      if (sel === i || hover === i) { ctx.beginPath(); ctx.arc(sx, sy, sr + 4, 0, 6.2832); ctx.strokeStyle = col.acc; ctx.lineWidth = 2.4; ctx.stroke(); }
    });
    ctx.globalAlpha = 1; ctx.font = '600 12.5px ' + (getComputedStyle(root).fontFamily || 'system-ui'); ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    nodes.forEach((n, i) => {
      const sg = opz.statico ? (W < 300 ? ordG[0] : ordG[2]) : sogliaG; const mostra = n.g >= sg || (hover != null ? lit(i) : false) || sel === i || (filtro && filtro.has(i));
      if (!mostra) return; if ((spento && !lit(i))) return;
      const sx = n.x * view.k + view.tx, sy = n.y * view.k + view.ty + Math.max(4, n.r * view.k) + 15;
      let t = n.t; if (t.length > 26) t = t.slice(0, 25) + '…';
      ctx.lineWidth = 4; ctx.strokeStyle = scuro ? 'rgba(12,14,22,.82)' : 'rgba(255,255,255,.86)'; ctx.lineJoin = 'round'; ctx.strokeText(t, sx, sy);
      ctx.fillStyle = col.t; ctx.fillText(t, sx, sy);
    });
  }
  const pianifica = () => { if (!raf) raf = requestAnimationFrame(draw); };
  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight; if (!w || !h) return;
    if (!scelto) { scelto = true; if (h > w * 1.25) { m = memModello(true); nodes = m.nodes.map((n) => Object.assign({}, n)); edges = m.edges; adj = m.adj; ctl.nodes = nodes; } }
    dpr = Math.min(2, window.devicePixelRatio || 1); if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) { canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr); }
    W = w; H = h; col = leggiColori(root); scuro = chiaro(col.t);
    if (pend != null) { const p = pend; pend = null; centra(p, true); } else if (!mosso && !inIntro) fit();
    draw();
  }
  function centra(i, subito) {
    if (i == null || !nodes[i]) return; if (!W) { pend = i; return; }
    const k = Math.max(view.k, 1.05), tx = W / 2 - nodes[i].x * k, ty = H / 2 - nodes[i].y * k; mosso = true;
    cancelAnimationFrame(anim); if (subito || riduceMoto()) { view.k = k; view.tx = tx; view.ty = ty; pianifica(); return; }
    const a = { k: view.k, tx: view.tx, ty: view.ty }, t0 = performance.now();
    const passo = (t) => { const p = Math.min(1, (t - t0) / 380), e = 1 - Math.pow(1 - p, 3); view.k = a.k + (k - a.k) * e; view.tx = a.tx + (tx - a.tx) * e; view.ty = a.ty + (ty - a.ty) * e; draw(); if (p < 1) anim = requestAnimationFrame(passo); };
    anim = requestAnimationFrame(passo);
  }
  function nodoIn(x, y) {
    let best = null, bd = 1e9;
    nodes.forEach((n, i) => { const sx = n.x * view.k + view.tx, sy = n.y * view.k + view.ty, r = Math.max(4, n.r * view.k) + 5, d = Math.hypot(x - sx, y - sy); if (d <= r && d < bd) { bd = d; best = i; } });
    return best;
  }
  const ctl = {
    nodes: nodes, resize: resize, draw: pianifica, centra: centra,
    setSel(k) { sel = k == null ? null : m.idx[k]; if (sel === undefined) sel = null; pianifica(); },
    setFiltro(testo) {
      const q = String(testo || '').trim().toLowerCase(); if (!q) { filtro = null; pianifica(); return []; }
      const ids = []; nodes.forEach((n, i) => { if (n.t.toLowerCase().indexOf(q) >= 0) ids.push(i); }); filtro = ids.length ? new Set(ids) : new Set(); pianifica(); return ids.map((i) => nodes[i]);
    },
    intro() {
      if (riduceMoto() || opz.statico) return; const fin = nodes.map((n) => [n.x, n.y]);
      nodes.forEach((n) => { n.x *= 0.15; n.y *= 0.15; }); const t0 = performance.now(); fit0();
      inIntro = true;
      const passo = (t) => { const p = Math.min(1, (t - t0) / 650), e = 1 - Math.pow(1 - p, 3); nodes.forEach((n, i) => { n.x = fin[i][0] * (0.15 + 0.85 * e); n.y = fin[i][1] * (0.15 + 0.85 * e); }); if (p >= 1) { inIntro = false; if (!mosso) fit(); } draw(); if (p < 1) intro = requestAnimationFrame(passo); };
      function fit0() { nodes.forEach((n, i) => { n.xs = n.x; n.ys = n.y; n.x = fin[i][0]; n.y = fin[i][1]; }); fit(); nodes.forEach((n) => { n.x = n.xs; n.y = n.ys; }); }
      intro = requestAnimationFrame(passo);
    },
    destroy() { cancelAnimationFrame(raf); cancelAnimationFrame(anim); cancelAnimationFrame(intro); },
    rifit() { mosso = false; cancelAnimationFrame(anim); fit(); pianifica(); },
    byKey: (k) => m.idx[k], model: m,
  };
  if (!opz.statico) {
    const pt = new Map(); let modo = null, drag = null, start = null, pinch = null;
    canvas.addEventListener('pointerdown', (e) => {
      canvas.setPointerCapture(e.pointerId); pt.set(e.pointerId, { x: e.offsetX, y: e.offsetY }); cancelAnimationFrame(anim); if (inIntro) { cancelAnimationFrame(intro); inIntro = false; }
      if (pt.size === 2) { const [a, b] = Array.from(pt.values()); pinch = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, k: view.k, tx: view.tx, ty: view.ty, cx: (a.x + b.x) / 2, cy: (a.y + b.y) / 2 }; modo = 'pinch'; return; }
      const h = nodoIn(e.offsetX, e.offsetY); start = { x: e.offsetX, y: e.offsetY, mosso: false, h: h };
      if (h != null) { modo = 'nodo'; drag = { i: h, ox: toW(e.offsetX, e.offsetY).x - nodes[h].x, oy: toW(e.offsetX, e.offsetY).y - nodes[h].y }; } else { modo = 'pan'; drag = { tx: view.tx, ty: view.ty }; }
    });
    canvas.addEventListener('pointermove', (e) => {
      if (pt.has(e.pointerId)) pt.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
      if (modo === 'pinch' && pt.size >= 2) { const [a, b] = Array.from(pt.values()); const d = Math.hypot(a.x - b.x, a.y - b.y) || 1; const k = Math.max(0.3, Math.min(5, pinch.k * d / pinch.d)); const wx = (pinch.cx - pinch.tx) / pinch.k, wy = (pinch.cy - pinch.ty) / pinch.k; const cx = (a.x + b.x) / 2, cy = (a.y + b.y) / 2; view.k = k; view.tx = cx - wx * k; view.ty = cy - wy * k; mosso = true; pianifica(); return; }
      if (modo && start) {
        const dx = e.offsetX - start.x, dy = e.offsetY - start.y; if (Math.hypot(dx, dy) > 4) start.mosso = true; if (!start.mosso) return; mosso = true;
        if (modo === 'nodo') { const w = toW(e.offsetX, e.offsetY); nodes[drag.i].x = w.x - drag.ox; nodes[drag.i].y = w.y - drag.oy; } else { view.tx = drag.tx + dx; view.ty = drag.ty + dy; }
        pianifica(); return;
      }
      if (e.pointerType === 'mouse' || e.pointerType === 'pen') { const h = nodoIn(e.offsetX, e.offsetY); if (h !== hover) { hover = h; canvas.style.cursor = h != null ? 'pointer' : 'grab'; if (opz.suHover) opz.suHover(h != null ? nodes[h] : null); pianifica(); } }
    });
    const su = (e) => {
      const era = modo; pt.delete(e.pointerId);
      if (era === 'nodo' && start && !start.mosso && opz.suClic) opz.suClic(nodes[start.h]);
      if (pt.size === 0) { modo = null; drag = null; start = null; pinch = null; } else if (pt.size === 1 && era === 'pinch') { modo = null; start = null; }
    };
    canvas.addEventListener('pointerup', su); canvas.addEventListener('pointercancel', su);
    canvas.addEventListener('pointerleave', (e) => { if (e.pointerType === 'mouse' && hover != null && !modo) { hover = null; if (opz.suHover) opz.suHover(null); pianifica(); } });
    canvas.addEventListener('wheel', (e) => {
      e.preventDefault(); cancelAnimationFrame(anim); const f = Math.exp(-e.deltaY * 0.0016), k = Math.max(0.3, Math.min(5, view.k * f)), w = toW(e.offsetX, e.offsetY);
      view.k = k; view.tx = e.offsetX - w.x * k; view.ty = e.offsetY - w.y * k; mosso = true; pianifica();
    }, { passive: false });
    canvas.style.cursor = 'grab';
  }
  return ctl;
}
function paginaMem(ist, n) {
  const chips = (ks) => ks.map((k) => { const x = nodiMem().find((q) => q.chiave === k); return x ? '<button type="button" class="pc-chip' + (x.mancante ? ' pc-chip-manca' : '') + '" data-az="wiki" data-k="' + esc(k) + '">' + esc(x.titolo) + '</button>' : ''; }).join(' ');
  const cita = arr(n.citata_da);
  const verso = arr(S.memoria_grafo.archi).filter((e) => e.da === n.chiave).map((e) => e.a);
  if (n.mancante) return '<div class="pc-scroll pc-pag"><div class="pc-pag-testa"><span class="pc-tag pc-t-calmo">' + ico('note', 14) + '<span>Pagina da scrivere</span></span></div><h1 class="pc-tit">' + esc(n.titolo) + '</h1>' +
    '<p class="pc-p">Questa pagina non c\'è ancora: la citano ' + (cita.length ? chips(cita) : 'altre pagine') + '.</p><p class="pc-p pc-tenue">Quando l\'agente la scrive, comparirà qui come pagina e nel grafo come cerchio pieno.</p></div>';
  const src = F[n.dove]; const r = src != null ? md(src, { uid: ist.uid + 'm', area: n.area }) : null;
  return '<div class="pc-scroll pc-pag"><div class="pc-pag-testa"><span class="pc-area-pt" style="background:' + coloreArea(memModello(), n.area) + '"></span><span class="pc-meta">Area ' + esc(n.area) + ' · <code class="pc-cod">' + esc(n.dove) + '</code></span></div>' +
    '<div class="pc-md">' + (r ? r.html : '<p class="pc-vuoto">Il testo di questa pagina non è nei dati.</p>') + '</div>' +
    (verso.length ? '<h2 class="pc-sez">Rimanda a</h2><p class="pc-chips">' + chips(verso) + '</p>' : '') +
    '<h2 class="pc-sez">Citata da</h2>' + (cita.length ? '<p class="pc-chips">' + chips(cita) + '</p>' : '<p class="pc-vuoto">Nessun\'altra pagina la cita.</p>') + '</div>';
}
function aggiornaRisultati(ist, M) {
  const q = M.input.value; const lista = M.ctl.setFiltro(q);
  const ul = $(M.dom, '.pc-ris');
  if (!q.trim()) { ul.hidden = true; ul.innerHTML = ''; return; }
  ul.hidden = false; ul.innerHTML = lista.length ? lista.slice(0, 8).map((n) => '<li><button type="button" class="pc-ris-b" data-az="wiki" data-k="' + esc(n.k) + '"><span class="pc-area-pt' + (n.miss ? ' pc-area-pt-m' : '') + '" style="background:' + (n.miss ? 'transparent' : coloreArea(M.ctl.model, n.area)) + '"></span>' + esc(n.t) + (n.miss ? ' <span class="pc-tenue">(da scrivere)</span>' : '') + '</button></li>').join('') : '<li class="pc-ris-v">Nessuna pagina con questo titolo.</li>';
}
function memCostruisci(ist) {
  const root = ist.root; root.innerHTML = '';
  const bw = document.createElement('div'); bw.className = 'pc-barra-w'; root.appendChild(bw);
  const dom = document.createElement('div'); dom.className = 'pc-corpo pc-mem'; root.appendChild(dom);
  const m = memModello();
  dom.innerHTML = '<div class="pc-mem-g"><div class="pc-mem-sopra"><header class="pc-mem-testa"><h1 class="pc-tit">Quello che lo studio sa</h1><p class="pc-p pc-tenue">Ogni cerchio è una pagina di memoria, le linee sono i collegamenti. Tocca un cerchio per leggerla.</p></header><label class="pc-cerca"><span class="pc-sr">Cerca una pagina per titolo</span>' + ico('search', 16) + '<input type="search" class="pc-cerca-i" placeholder="Cerca una pagina per titolo" autocomplete="off" spellcheck="false"></label>' +
    '<ul class="pc-ris" hidden></ul></div><div class="pc-mem-cv"><canvas class="pc-cv" role="img" aria-label="Il grafo della memoria: ' + m.nodes.length + ' pagine collegate fra loro. Per aprirne una usa la ricerca o l\'elenco."></canvas></div>' +
    '<ul class="pc-leg pc-leg-mem">' + m.aree.map((a) => '<li><span class="pc-area-pt" style="background:' + coloreArea(m, a) + '"></span>' + esc(a) + '</li>').join('') + (m.nodes.some((x) => x.miss) ? '<li><span class="pc-area-pt pc-area-pt-m"></span>da scrivere</li>' : '') + '</ul>' +
    '<details class="pc-elenco"><summary>' + ico('file', 16) + '<span>Elenco delle pagine</span></summary><p class="pc-chips">' + m.nodes.map((n) => '<button type="button" class="pc-chip' + (n.miss ? ' pc-chip-manca' : '') + '" data-az="wiki" data-k="' + esc(n.k) + '">' + esc(n.t) + '</button>').join(' ') + '</p></details></div><div class="pc-mem-p"></div>';
  const canvas = $(dom, '.pc-cv');
  const ctl = grafoCtrl(canvas, root, { suClic(n) { ist.pila = [{ t: 'pag', k: n.k }]; ist._r('avanti'); ist._prof(); } });
  const M = { dom: dom, bw: bw, ctl: ctl, input: $(dom, '.pc-cerca-i'), pag: $(dom, '.mem-p, .pc-mem-p') };
  M.input.addEventListener('input', () => aggiornaRisultati(ist, M));
  M.input.addEventListener('keydown', (e) => { if (e.key === 'Enter') { const b = $(dom, '.pc-ris-b'); if (b) b.click(); } else if (e.key === 'Escape' && M.input.value) { M.input.value = ''; aggiornaRisultati(ist, M); e.stopPropagation(); } });
  if (typeof ResizeObserver !== 'undefined') { M.ro = new ResizeObserver(() => ctl.resize()); M.ro.observe($(dom, '.pc-mem-cv')); }
  ctl.resize(); ctl.intro();
  return M;
}
P.memoria = {
  custom: true,
  pieno(ist, dir) {
    const root = ist.root; let M = ist.M;
    if (!M || !root.contains(M.dom)) { M = ist.M = memCostruisci(ist); }
    M.bw.innerHTML = barraHtml(ist);
    const e = ist.pila[ist.pila.length - 1]; const pane = M.pag;
    if (!e) { const era = M.dom.hasAttribute('data-pag'); M.dom.removeAttribute('data-pag'); pane.innerHTML = ''; M.ctl.setSel(null); if (era) requestAnimationFrame(() => M.ctl.rifit()); return; }
    const n = nodiMem().find((q) => q.chiave === e.k); if (!n) { pane.innerHTML = '<div class="pc-scroll"><p class="pc-vuoto">Pagina non trovata.</p></div>'; M.dom.setAttribute('data-pag', '1'); return; }
    M.dom.setAttribute('data-pag', '1'); pane.innerHTML = paginaMem(ist, n); pane.dataset.dir = dir || 'avanti';
    pane.classList.remove('pc-anima-a', 'pc-anima-i'); void pane.offsetWidth; if (dir) pane.classList.add(dir === 'indietro' ? 'pc-anima-i' : 'pc-anima-a');
    M.ctl.setSel(n.chiave); const ix = M.ctl.byKey(n.chiave); requestAnimationFrame(() => requestAnimationFrame(() => M.ctl.centra(ix)));
    if (M.input.value) { M.input.value = ''; aggiornaRisultati(ist, M); }
  },
  anteprima(ist) {
    const m = memModello(); const st = S.memoria_grafo.conteggi || {};
    return '<div class="pc-an pc-an-mem"><div class="pc-mem-cv"><canvas class="pc-cv" aria-hidden="true"></canvas></div><p class="pc-an-pie">' + (st.pagine || m.nodes.filter((n) => !n.miss).length) + ' pagine, ' + (st.collegamenti || m.edges.length) + ' collegamenti</p></div>';
  },
  dopoAnteprima(ist, root) {
    const cv = $(root, '.pc-cv'); if (!cv) return; const ctl = grafoCtrl(cv, root, { statico: true }); ist.M = null;
    const go = () => ctl.resize(); requestAnimationFrame(go);
    if (typeof ResizeObserver !== 'undefined') { const ro = new ResizeObserver(go); ro.observe($(root, '.pc-mem-cv')); ist._roA = ro; }
    ist._ctlA = ctl;
  },
  vai(ist, v) {
    v = String(v || ''); const l = nodiMem(); const n = l.find((q) => q.dove === v || q.chiave === v) || l.find((q) => q.dove === 'memoria/' + v) || l.find((q) => stem(q) === v.replace(/\.md$/, '') && !q.mancante) || l.find((q) => stem(q) === v) || l.find((q) => stem(q) === v.split('/').pop().replace(/\.md$/, ''));
    if (!n) return false; ist.pila = [{ t: 'pag', k: n.chiave }]; return true;
  },
  az(ist, a, el) {
    if (a === 'wiki') {
      const k = el.dataset.k; if (!nodiMem().some((q) => q.chiave === k)) return null;
      const last = ist.pila[ist.pila.length - 1]; if (last && last.k === k) return 'rirendi';
      ist.pila.push({ t: 'pag', k: k }); return 'avanti';
    }
    return null;
  },
  livelli(ist) { return ist.pila.map((e) => { const n = nodiMem().find((q) => q.chiave === e.k); return n ? n.titolo : e.k; }); },
};
