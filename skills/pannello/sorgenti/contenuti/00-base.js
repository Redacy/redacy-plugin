/* Contenuti dei cinque pannelli del pannello redacy. Contratto: _lavoro/CONTRATTO.md.
   Nessuna libreria. Il testo dei file e' dato: ogni stringa passa da esc() prima di diventare HTML. */
(function () {
'use strict';
/* I dati: window.DATI al caricamento, oppure Contenuti.carica(dati) dopo (il plugin li prende dal server). */
let D = window.DATI || { stato: {}, file: {} };
let S = D.stato || {}, F = D.file || {};
let FIRMA = null;
let UID = 0;
const ISTANZE = new Set();

/* ---------- piccoli attrezzi ---------- */
const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const cap = (s) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
const plur = (n, uno, molti) => n + ' ' + (n === 1 ? uno : molti);
const umano = (id) => cap(String(id || '').replace(/[-_]+/g, ' ').trim());
const arr = (x) => Array.isArray(x) ? x : [];
const $ = (r, s) => r.querySelector(s);
const $$ = (r, s) => Array.from(r.querySelectorAll(s));
const riduceMoto = () => { try { return window.matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) { return false; } };

/* ---------- icone a tratto, 24x24 ---------- */
const IC = {
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  x: '<path d="M6 6l12 12M18 6L6 18"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
  bolt: '<path d="M13 3L5.5 13.5H11L10 21l8-10.5h-5.5z"/>',
  chat: '<path d="M5 6h14v9.5h-8.5L6.5 19v-3.5H5z"/>',
  spark: '<path d="M12 3.5l1.8 5.2 5.2 1.8-5.2 1.8L12 17.5l-1.8-5.2L5 10.5l5.2-1.8z"/>',
  term: '<rect x="3.5" y="5" width="17" height="14" rx="2"/><path d="M7.5 10l3 2.5-3 2.5M13 15h4"/>',
  out: '<path d="M4 14v4.5h16V14M12 15V4M8 8l4-4 4 4"/>',
  person: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 19.5c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5"/>',
  flag: '<path d="M6 21V4M6 5h11l-2.2 4L17 13H6"/>',
  stop: '<rect x="6.5" y="6.5" width="11" height="11" rx="1.5"/>',
  minus: '<path d="M6.5 12h11"/>',
  circle: '<circle cx="12" cy="12" r="6.5"/>',
  dots: '<circle cx="6" cy="12" r="1.7" fill="currentColor"/><circle cx="12" cy="12" r="1.7" fill="currentColor"/><circle cx="18" cy="12" r="1.7" fill="currentColor"/>',
  back: '<path d="M14.5 6l-6 6 6 6"/>',
  fwd: '<path d="M9.5 6l6 6-6 6"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  file: '<path d="M7 3.5h7l4 4v13H7z"/><path d="M14 3.5V8h4"/>',
  folder: '<path d="M3.5 6.5h6l2 2.5h9v9.5h-17z"/>',
  search: '<circle cx="11" cy="11" r="6"/><path d="M16 16l4 4"/>',
  alert: '<path d="M12 4l9 15.5H3z"/><path d="M12 10v4.5M12 17.2v.1"/>',
  code: '<path d="M9 7l-5 5 5 5M15 7l5 5-5 5"/>',
  link: '<path d="M10 14l4-4M8.5 11.5l-2 2a3.2 3.2 0 0 0 4.5 4.5l2-2M15.5 12.5l2-2A3.2 3.2 0 0 0 13 6l-2 2"/>',
  power: '<path d="M12 4v7M7 7.5a6.5 6.5 0 1 0 10 0"/>',
  note: '<path d="M5 4.5h14v11l-4.5 4H5z"/><path d="M14.5 20v-4.5H19"/>',
};
const ico = (n, s) => '<svg class="pc-i" viewBox="0 0 24 24" width="' + (s || 18) + '" height="' + (s || 18) + '" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">' + IC[n] + '</svg>';
const icoPannello = (d) => '<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';

/* ---------- tempo: tutto rispetto a stato.ora, fuso Europe/Rome ---------- */
const TZ = 'Europe/Rome';
const mk = (o) => { try { return new Intl.DateTimeFormat('it-IT', Object.assign({ timeZone: TZ }, o)); } catch (e) { return new Intl.DateTimeFormat('it-IT', o); } };
const fData = mk({ weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
const fGM = mk({ day: 'numeric', month: 'long' });
const fWGM = mk({ weekday: 'long', day: 'numeric', month: 'long' });
const fOra = mk({ hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const fYMD = (() => { try { return new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' }); } catch (e) { return null; } })();
const adesso = () => new Date(S.ora || Date.now());
const ymd = (d) => fYMD ? fYMD.format(d) : d.toISOString().slice(0, 10);
const oggiYMD = () => ymd(adesso());
const utcDay = (s) => { const [y, m, d] = s.split('-').map(Number); return Date.UTC(y, m - 1, d); };
const giorniFra = (a, b) => Math.round((utcDay(b) - utcDay(a)) / 86400000); // b - a
const dataDaYMD = (s) => new Date(utcDay(s) + 12 * 3600000);
function giornoParole(s) { // 'YYYY-MM-DD' -> oggi / domani / ieri / lunedì 9 novembre
  if (!s) return '';
  const dd = giorniFra(oggiYMD(), s);
  if (dd === 0) return 'oggi'; if (dd === 1) return 'domani'; if (dd === -1) return 'ieri';
  return fWGM.format(dataDaYMD(s));
}
function quando(iso) { // 2026-11-07T17:40:57Z -> oggi alle 18:40
  if (!iso) return '';
  const d = new Date(iso); const dd = giorniFra(oggiYMD(), ymd(d));
  const ora = fOra.format(d);
  if (dd === 0) return 'oggi alle ' + ora; if (dd === -1) return 'ieri alle ' + ora;
  return 'il ' + fGM.format(d) + ' alle ' + ora;
}
function durata(min) {
  min = Math.max(0, Math.round(min));
  if (min < 1) return 'meno di un minuto';
  if (min < 60) return plur(min, 'minuto', 'minuti');
  const h = Math.floor(min / 60), m = min % 60;
  const hs = plur(h, 'ora', 'ore');
  return m ? hs + ' e ' + plur(m, 'minuto', 'minuti') : hs;
}
const minFra = (a, b) => (new Date(b) - new Date(a)) / 60000;

/* ---------- accesso ai dati ---------- */
const grafi = () => arr(S.grafi);
const grafoPer = (id) => grafi().find((g) => g.grafo === id) || null;
const nomeProc = (id) => umano(id);
const corse = () => arr(S.corse);
const eff = (c) => c.stato_effettivo || c.stato;
const lavorando = () => arr(S.corse_in_corso).filter((c) => eff(c) === 'in-corso');
const perse = () => arr(S.corse_in_corso).filter((c) => eff(c) === 'persa');
function daGuardare() {
  const v = {}; const l = [];
  corse().concat(arr(S.corse_in_corso)).forEach((c) => { if (!v[c.id] && ['fallita', 'persa'].indexOf(eff(c)) >= 0) { v[c.id] = 1; l.push(c); } });
  return l.sort((a, b) => String(b.inizio).localeCompare(String(a.inizio)));
}
const corsePer = (gid) => corse().filter((c) => c.grafo === gid).sort((a, b) => String(b.inizio).localeCompare(String(a.inizio)));
function ultimaCorsa(g) {
  const l = corsePer(g.grafo);
  return (g.ultima_corsa && l.find((c) => c.id === g.ultima_corsa.id)) || l[0] || null;
}
const defPasso = (g, pid) => g ? arr(g.passi).find((p) => p.id === pid) || null : null;
const idxPasso = (g, pid) => g ? arr(g.passi).findIndex((p) => p.id === pid) : -1;

/* stato "mostrato" di ogni passo di una corsa, con le correzioni:
   - un passo umano e' il turno della persona solo se tutti i passi prima sono fatti e la corsa e' in corso */
function statiPassi(c, g) {
  const out = {}; if (!c) return out;
  const ps = arr(c.passi); let prima = true;
  ps.forEach((p, i) => {
    let k = p.stato;
    const def = defPasso(g, p.id);
    if (eff(c) === 'persa' && k === 'in-corso') k = 'persa';
    else if (def && def.tipo === 'umano' && eff(c) === 'in-corso' && prima && (k === 'da-fare' || k === 'in-corso')) k = 'attesa';
    out[p.id] = k;
    if (p.stato !== 'fatto') prima = false;
  });
  return out;
}
const STATI = {
  'fatto': { et: 'Fatto', ic: 'check', cls: 'ok' },
  'in-corso': { et: 'Sta lavorando', ic: 'dots', cls: 'corre' },
  'attesa': { et: 'Tocca a te', ic: 'flag', cls: 'attesa' },
  'fermato': { et: 'Fermato', ic: 'stop', cls: 'ferma' },
  'fallito': { et: 'Non è riuscito', ic: 'x', cls: 'err' },
  'persa': { et: 'Non dà notizie', ic: 'alert', cls: 'err' },
  'saltato': { et: 'Saltato', ic: 'minus', cls: 'calmo' },
  'da-fare': { et: 'Da fare', ic: 'circle', cls: 'calmo' },
};
const statoCorsa = (c) => ({
  'in-corso': { et: 'Sta lavorando', ic: 'dots', cls: 'corre' },
  'persa': { et: 'Non dà notizie', ic: 'alert', cls: 'err' },
  'finita': { et: 'Finito', ic: 'check', cls: 'ok' },
  'fallita': { et: 'Non è riuscito', ic: 'x', cls: 'err' },
  'fermata': { et: 'Fermato', ic: 'stop', cls: 'ferma' },
}[eff(c)] || { et: eff(c), ic: 'circle', cls: 'calmo' });
const tag = (st, testo) => '<span class="pc-tag pc-t-' + st.cls + '">' + ico(st.ic, 14) + '<span>' + esc(testo || st.et) + '</span></span>';

function passoCorrente(c, g) { // il passo in corso (o il primo non fatto) in parole
  const ps = arr(c.passi); let i = ps.findIndex((p) => p.stato === 'in-corso');
  if (i < 0) i = ps.findIndex((p) => p.stato !== 'fatto');
  if (i < 0) return null;
  const def = defPasso(g, ps[i].id);
  return { n: i + 1, tot: ps.length, id: ps[i].id, nome: def ? def.nome : umano(ps[i].id), def };
}

/* i turni della persona dentro le corse in corso */
function turniUmani() {
  const out = [];
  lavorando().forEach((c) => {
    const g = grafoPer(c.grafo); const st = statiPassi(c, g);
    arr(c.passi).forEach((p) => { if (st[p.id] === 'attesa') {
      const def = defPasso(g, p.id) || {};
      out.push({ tipo: 'passo', corsa: c, grafo: g, passo: p, def: def, id: c.id + '/' + p.id });
    } });
  });
  return out;
}
/* tutto cio' che aspetta la persona, nell'ordine: in ritardo prima, poi per scadenza */
function tocca() {
  const todos = arr(S.periodo && S.periodo.todo && S.periodo.todo.todo);
  const aspetta = arr(S.periodo && S.periodo.aspettano_te);
  const l = aspetta.map((a) => {
    const t = todos.find((x) => x.id === a.id) || { id: a.id, cosa: a.id };
    const rit = a.in_ritardo != null ? !!a.in_ritardo : (t.scadenza && giorniFra(t.scadenza, oggiYMD()) > 0);
    return { tipo: 'todo', id: t.id, t: t, ritardo: rit };
  });
  turniUmani().forEach((u) => l.push(u));
  return l.sort((a, b) => {
    const ra = a.ritardo ? 0 : 1, rb = b.ritardo ? 0 : 1; if (ra !== rb) return ra - rb;
    const sa = a.t && a.t.scadenza ? a.t.scadenza : (a.tipo === 'passo' ? '0000' : '9999');
    const sb = b.t && b.t.scadenza ? b.t.scadenza : (b.tipo === 'passo' ? '0000' : '9999');
    return sa.localeCompare(sb);
  });
}
function giorniRitardo(t) { return t && t.scadenza ? Math.max(0, giorniFra(t.scadenza, oggiYMD())) : 0; }

/* da dove arriva un todo, e dove porta il campo "dove" */
function daParole(da) {
  const m = { giro: 'dal giro del giorno', piano: 'dal piano del periodo', conversazione: 'da una conversazione', corsa: 'da un lavoro' };
  return m[da] || (da ? 'da ' + da : 'dal piano del periodo');
}
function linkFile(p) {
  if (!p) return null; p = String(p).replace(/^\.\//, '').replace(/\/$/, '');
  if (p === 'AGENTS.md') return { pannello: 'aree', voce: 'orchestratore', et: 'Apri l\'orchestratore' };
  let g = grafi().find((x) => x.file === p || x.grafo === p); if (g) return { pannello: 'processi', voce: g.grafo, et: 'Apri il processo' };
  let m = arr(S.memoria_grafo && S.memoria_grafo.nodi).find((n) => n.dove === p); if (m) return { pannello: 'memoria', voce: m.dove, et: 'Apri la pagina' };
  m = p.match(/^workspace\/([^\/]+)(\/AGENTS\.md)?$/); if (m && arr(S.workspace).some((w) => w.nome === m[1])) return { pannello: 'aree', voce: m[1], et: 'Apri l\'area' };
  if (/^periodo\//.test(p)) return { pannello: 'periodo', voce: p, et: 'Apri il periodo' };
  return null;
}
