
/* ---------- pezzi comuni ai pannelli ---------- */
const P = {};
function percorso(c, g) { // mini-percorso dei passi: fatto / in corso / da fare
  const st = statiPassi(c, g); const ps = arr(c.passi);
  return '<ol class="pc-perc" aria-label="Passi del lavoro">' + ps.map((p, i) => {
    const k = st[p.id] || p.stato; const s = STATI[k] || STATI['da-fare']; const def = defPasso(g, p.id);
    const nome = def ? def.nome : umano(p.id);
    return (i ? '<li class="pc-perc-lin pc-l-' + (ps[i - 1].stato === 'fatto' ? 'ok' : 'no') + '" aria-hidden="true"></li>' : '') +
      '<li class="pc-perc-p pc-s-' + s.cls + '" title="' + esc(nome + ': ' + s.et) + '"><span class="pc-perc-ic">' + ico(s.ic, 12) + '</span><span class="pc-sr">' + esc(nome + ': ' + s.et) + '</span></li>';
  }).join('') + '</ol>';
}
const linkBtn = (lk, cls) => lk ? '<button type="button" class="pc-btn ' + (cls || '') + '" data-az="vai" data-p="' + esc(lk.pannello) + '" data-v="' + esc(lk.voce) + '">' + esc(lk.et) + ico('fwd', 14) + '</button>' : '';
/* una frase da dire all'agente: un tocco la copia. Il pannello non fa partire niente. */
const copiaBtn = (f) => '<button type="button" class="pc-copia" data-az="copia" data-t="' + esc(f) + '" title="Copia la frase"><span>«' + esc(f) + '»</span></button>';
const chiedi = (f) => '<span class="pc-chiedi">scrivi all\'agente ' + copiaBtn(f) + '</span>';
function copia(el) {
  const t = el.dataset.t || ''; const sp = $(el, 'span'); if (!sp || el.dataset.fatto) return;
  const fine = (ok) => { el.dataset.fatto = '1'; const prima = sp.textContent; sp.textContent = ok ? 'Copiata' : 'Selezionala e copiala'; setTimeout(() => { sp.textContent = prima; delete el.dataset.fatto; }, 1600); };
  try { if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(() => fine(true), () => fine(false)); else fine(false); } catch (e) { fine(false); }
}

/* ---------- OGGI ---------- */
function statoOggi() {
  const t = tocca(), lav = lavorando(), dg = daGuardare();
  const rit = t.filter((x) => x.ritardo).length;
  return { t: t, lav: lav, dg: dg, rit: rit, perTe: t.length };
}
function fraseOggi(o) {
  const parti = [];
  parti.push(o.perTe ? (o.perTe === 1 ? '1 cosa aspetta te' : o.perTe + ' cose aspettano te') : 'Non c\'è niente che aspetti te');
  if (o.lav.length) parti.push(o.lav.length === 1 ? '1 lavoro sta girando' : o.lav.length + ' lavori stanno girando');
  if (o.dg.length) parti.push(o.dg.length === 1 ? '1 cosa è da guardare' : o.dg.length + ' cose sono da guardare');
  let f = parti.length > 1 ? parti.slice(0, -1).join(', ') + ' e ' + parti[parti.length - 1] : parti[0];
  if (!o.dg.length) f += ', il resto è a posto';
  return cap(f) + '.';
}
function ferma(id) {
  const ora = S.ora; let c = arr(S.corse_in_corso).find((x) => x.id === id);
  const upd = (x) => { if (!x || x.id !== id) return; x.stato = 'fermata'; x.stato_effettivo = 'fermata'; x.fine = ora; x.persa = false; x.minuti_senza_segni = null;
    x.stop = { chi: 'pannello', quando: ora, perche: null };
    arr(x.passi).forEach((p) => { if (p.stato === 'in-corso') { p.stato = 'fermato'; p.fine = ora; } }); };
  [S.corse, S.corse_in_corso, S.corse_ultime, S.recenti && S.recenti.corse_finite].forEach((a) => arr(a).forEach(upd));
  if (!c) c = corse().find((x) => x.id === id);
  if (!c) return false;
  S.corse_in_corso = arr(S.corse_in_corso).filter((x) => x.id !== id);
  if (!arr(S.corse_ultime).some((x) => x.id === id)) { S.corse_ultime = arr(S.corse_ultime); S.corse_ultime.unshift(c); }
  if (S.recenti) { S.recenti.corse_finite = arr(S.recenti.corse_finite); if (!S.recenti.corse_finite.some((x) => x.id === id)) S.recenti.corse_finite.unshift(c); }
  grafi().forEach((g) => { if (g.ultima_corsa && g.ultima_corsa.id === id) { g.ultima_corsa.stato = 'fermata'; g.ultima_corsa.fine = ora; } });
  if (S.conta) S.conta.in_corso = Math.max(0, (S.conta.in_corso || 0) - 1);
  try { if (typeof window.Contenuti.suFerma === 'function') window.Contenuti.suFerma(id); } catch (e) {}
  aggiornaTutte();
  return true;
}
function vocePasso(u) {
  const g = u.grafo, nome = u.def.nome || umano(u.passo.id);
  const lk = { pannello: 'processi', voce: u.corsa.grafo + '/' + u.passo.id, et: 'Apri il passo' };
  return '<article class="pc-voce pc-voce-attesa"><span class="pc-voce-ic">' + ico('flag', 20) + '</span><div class="pc-voce-t">' +
    '<h3 class="pc-voce-h">' + esc(nome) + '</h3>' +
    '<p class="pc-meta">Dal processo ' + esc(nomeProc(u.corsa.grafo)) + ' · partito ' + esc(quando(u.corsa.inizio)) + (u.def.dove ? ' · ' + esc(u.def.dove) : '') + '</p></div>' + linkBtn(lk) + '</article>';
}
function voceTodo(x) {
  const t = x.t; const lk = linkFile(t.dove);
  const scad = t.scadenza ? (x.ritardo ? '<span class="pc-tag pc-t-attesa">' + ico('alert', 14) + '<span>In ritardo' + (giorniRitardo(t) ? ' di ' + plur(giorniRitardo(t), 'giorno', 'giorni') : '') + '</span></span>' : '<span class="pc-tag pc-t-calmo">' + ico('clock', 14) + '<span>Entro ' + esc(giornoParole(t.scadenza)) + '</span></span>') : '';
  return '<article class="pc-voce' + (x.ritardo ? ' pc-voce-rit' : ' pc-voce-attesa') + '"><span class="pc-voce-ic">' + ico('flag', 20) + '</span><div class="pc-voce-t">' +
    '<h3 class="pc-voce-h">' + esc(t.cosa) + '</h3><p class="pc-meta">' + esc(cap(daParole(t.da))) + '</p>' +
    (scad ? '<p class="pc-voce-tag">' + scad + '</p>' : '') + '</div>' + (lk ? linkBtn(lk) : '') + '</article>';
}
function cardLavoro(ist, c) {
  const g = grafoPer(c.grafo); const pc = passoCorrente(c, g);
  const conf = ist.conferma === c.id;
  const lk = { pannello: 'processi', voce: c.grafo, et: 'Apri il processo' };
  const segno = c.minuti_senza_segni != null ? c.minuti_senza_segni : minFra(c.ultimo_segno, S.ora);
  return '<article class="pc-lav" data-id="' + esc(c.id) + '"><header class="pc-lav-testa"><h3 class="pc-voce-h">' + esc(nomeProc(c.grafo)) + '</h3>' + tag(statoCorsa(c)) + '</header>' +
    percorso(c, g) +
    (pc ? '<p class="pc-p pc-lav-passo">Passo ' + pc.n + ' di ' + pc.tot + ': <strong>' + esc(pc.nome) + '</strong></p>' : '') +
    '<p class="pc-meta">Lavora da ' + esc(durata(minFra(c.inizio, S.ora))) + ' · ultimo segno di vita ' + (segno < 1 ? 'poco fa' : esc(durata(segno)) + ' fa') + '</p>' +
    (conf ? confermaHtml(c.id)
      : '<div class="pc-lav-az">' + linkBtn(lk) + '<button type="button" class="pc-btn pc-btn-ferma" data-az="ferma" data-id="' + esc(c.id) + '">' + ico('stop', 14) + 'Ferma</button></div>') + '</article>';
}
const confermaHtml = (id) => '<div class="pc-conf" role="alertdialog" aria-label="Conferma"><p class="pc-conf-t">Fermo questo lavoro? Il passo in corso si interrompe e non viene spedito niente.</p><div class="pc-conf-b"><button type="button" class="pc-btn pc-btn-pericolo" data-az="ferma-si" data-id="' + esc(id) + '">Ferma</button><button type="button" class="pc-btn" data-az="ferma-no">Lascia andare</button></div></div>';
function cardGuardare(ist, c) {
  const g = grafoPer(c.grafo); const lk = { pannello: 'processi', voce: c.grafo, et: 'Apri il processo' };
  let riga, dett;
  if (eff(c) === 'persa') {
    const pc = passoCorrente(c, g); const m = c.minuti_senza_segni != null ? c.minuti_senza_segni : minFra(c.ultimo_segno, S.ora);
    riga = nomeProc(c.grafo) + ' non dà notizie'; dett = 'Da ' + durata(m) + (pc ? '. Era al passo ' + pc.n + ' di ' + pc.tot + ': ' + pc.nome + '.' : '.');
  } else {
    const pf = arr(c.passi).find((p) => p.stato === 'fallito'); const def = pf && defPasso(g, pf.id);
    riga = nomeProc(c.grafo) + ' non è riuscito'; dett = cap(quando(c.inizio)) + (def ? ', al passo «' + def.nome + '»' : '') + (pf && pf.nota ? ': ' + pf.nota : '.');
  }
  const conf = ist.conferma === c.id; const puoFermare = eff(c) === 'persa';
  return '<article class="pc-voce pc-voce-err" data-id="' + esc(c.id) + '"><span class="pc-voce-ic">' + ico(eff(c) === 'persa' ? 'alert' : 'x', 20) + '</span><div class="pc-voce-t"><h3 class="pc-voce-h">' + esc(riga) + '</h3><p class="pc-meta pc-meta-forte">' + esc(dett) + '</p>' +
    '</div>' +
    '<div class="pc-voce-az">' + linkBtn(lk) + (puoFermare && !conf ? '<button type="button" class="pc-btn pc-btn-ferma" data-az="ferma" data-id="' + esc(c.id) + '">' + ico('stop', 14) + 'Ferma</button>' : '') + '</div>' +
    (conf ? confermaHtml(c.id) : '') + '</article>';
}
function recentiOggi() {
  const dg = {}; daGuardare().forEach((c) => { dg[c.id] = 1; }); const l = [];
  const r = S.recenti || {};
  arr(r.corse_finite).forEach((c) => { if (dg[c.id]) return; l.push({ q: c.fine || c.inizio, c: c }); });
  arr(r.todo_fatti).forEach((t) => l.push({ q: (t.aggiornato || '') + 'T12:00:00Z', t: t }));
  return l.sort((a, b) => String(b.q).localeCompare(String(a.q)));
}
function voceRecente(x) {
  if (x.t) return '<li class="pc-rec"><span class="pc-rec-ic pc-s-ok">' + ico('check', 14) + '</span><div><p class="pc-rec-h">' + esc(x.t.cosa) + '</p><p class="pc-meta">Fatto' + (x.t.aggiornato ? ' ' + esc(giornoParole(x.t.aggiornato) === 'oggi' || giornoParole(x.t.aggiornato) === 'ieri' ? giornoParole(x.t.aggiornato) : 'il ' + fGM.format(dataDaYMD(x.t.aggiornato))) : '') + (x.t.chi === 'agente' ? ' dagli agenti' : '') + '</p></div></li>';
  const c = x.c, st = statoCorsa(c), g = grafoPer(c.grafo);
  const esiti = arr(c.passi).filter((p) => p.esito).map((p) => p.esito);
  let come = '';
  if (eff(c) === 'finita') come = esiti.length ? esiti.join(' · ') : 'è andato a buon fine';
  else if (eff(c) === 'fermata') { const pc = passoCorrente(c, g) || null; const fp = arr(c.passi).find((p) => p.stato === 'fermato'); const def = fp && defPasso(g, fp.id);
    come = 'Fermato' + (c.stop && c.stop.chi === 'pannello' ? ' da te' : '') + (def ? ' al passo «' + def.nome + '»' : '') + (c.stop && c.stop.perche ? ': ' + c.stop.perche : '') + (esiti.length ? ' · prima: ' + esiti.join(' · ') : ''); }
  return '<li class="pc-rec"><span class="pc-rec-ic pc-s-' + st.cls + '">' + ico(st.ic, 14) + '</span><div><p class="pc-rec-h">' + esc(nomeProc(c.grafo)) + ' · ' + esc(st.et.toLowerCase()) + '</p><p class="pc-meta">' + esc(cap(quando(c.fine || c.inizio))) + '</p><p class="pc-rec-c">' + esc(come) + '</p></div></li>';
}
/* il periodo in una carta: l'obiettivo, a che punto è, la porta per aprirlo */
function cardPeriodo() {
  const T = todoLista(); const ob = (S.periodo && !S.periodo.obiettivo_vuoto && S.periodo.obiettivo) || '';
  if (!ob && !T.length) return '<p class="pc-vuoto">Il periodo non ha ancora un obiettivo. Per darglielo ' + chiedi('pianifichiamo il periodo') + '</p>';
  const fatte = T.filter((t) => t.stato === 'fatto').length; const perc = T.length ? Math.round(fatte / T.length * 100) : 0;
  return '<article class="pc-carta">' + (ob ? '<p class="pc-carta-ob">' + esc(ob) + '</p>' : '<p class="pc-meta">Il periodo non ha ancora un obiettivo.</p>') +
    (T.length ? '<div class="pc-prog"><div class="pc-barra-p" role="progressbar" aria-valuemin="0" aria-valuemax="' + T.length + '" aria-valuenow="' + fatte + '" aria-label="Cose fatte"><span style="width:' + perc + '%"></span></div><p class="pc-meta">' + plur(fatte, 'cosa fatta', 'cose fatte') + ' su ' + T.length + '</p></div>' : '') +
    '<div class="pc-lav-az">' + linkBtn({ pannello: 'periodo', voce: '', et: 'Apri il periodo' }) + '</div></article>';
}
/* le frasi che fanno partire i lavori: il pannello mostra, il lavoro si chiede all'agente */
const PASSI = [
  ['Metti in ordine i file', 'L\'agente guarda una cartella, propone una struttura e sposta solo dopo il tuo sì. Non cancella niente.', 'riordina questa cartella'],
  ['Dai un obiettivo al periodo', 'Decidi con l\'agente cosa conta nelle prossime settimane. Da lì nascono le cose da fare.', 'pianifichiamo il periodo'],
  ['Affida un lavoro', 'Un lavoro nuovo diventa un\'area: un agente AI con la sua memoria e i suoi limiti.', 'ho un lavoro nuovo'],
  ['Insegna come lavori', 'Una regola o una procedura detta una volta resta in memoria e vale per tutti gli agenti.', 'ricordati che…'],
];
function primiPassi() {
  return '<section class="pc-sezione"><h2 class="pc-sez">Per cominciare</h2><ol class="pc-passi">' + PASSI.map((p, i) =>
    '<li class="pc-carta pc-passo-c"><span class="pc-passo-n" aria-hidden="true">' + (i + 1) + '</span><h3 class="pc-voce-h">' + esc(p[0]) + '</h3><p class="pc-meta">' + esc(p[1]) + '</p><p class="pc-passo-f">' + copiaBtn(p[2]) + '</p></li>').join('') +
    '</ol><p class="pc-meta pc-frasi-nota">Tocca una frase per copiarla, poi incollala nella conversazione con l\'agente. Quello che nasce lo vedi qui.</p></section>';
}
const FRASI = ['cosa c\'è oggi', 'pianifichiamo il periodo', 'automatizza questo lavoro', 'ricordati che…', 'riordina questa cartella'];
P.oggi = {
  pieno(ist) {
    const o = statoOggi(); const d = cap(fData.format(adesso()));
    const sezione = (tit, n, corpo, vuoto) => '<section class="pc-sezione"><h2 class="pc-sez">' + esc(tit) + (n ? ' <span class="pc-sez-n">' + n + '</span>' : '') + '</h2>' + (corpo || '<p class="pc-vuoto">' + vuoto + '</p>') + '</section>';
    const rec = recentiOggi();
    const senzaProcessi = !grafi().length;
    const ob0 = S.periodo && !S.periodo.obiettivo_vuoto && S.periodo.obiettivo;
    if (senzaProcessi && !ob0 && !todoLista().length && !rec.length && !o.perTe && !o.lav.length && !o.dg.length)
      return '<div class="pc-scroll"><header class="pc-oggi-testa"><p class="pc-data">' + esc(d) + '</p><h1 class="pc-frase">Lo studio è pronto. Niente aspetta te.</h1></header>' + primiPassi() + '</div>';
    return '<div class="pc-scroll"><header class="pc-oggi-testa"><p class="pc-data">' + esc(d) + '</p><h1 class="pc-frase">' + esc(fraseOggi(o)) + '</h1></header>' +
      '<div class="pc-cols pc-cols-oggi"><div class="pc-col">' +
      sezione('Tocca a te', o.perTe, o.t.length ? '<div class="pc-voci">' + o.t.map((x) => x.tipo === 'passo' ? vocePasso(x) : voceTodo(x)).join('') + '</div>' : '', 'Niente aspetta te.') +
      (o.dg.length ? sezione('Da guardare', o.dg.length, '<div class="pc-voci">' + o.dg.map((c) => cardGuardare(ist, c)).join('') + '</div>') : '') +
      sezione('Fatto di recente', null, rec.length ? '<ul class="pc-recenti">' + rec.map(voceRecente).join('') + '</ul>' : '', 'Ancora niente di finito.') +
      '</div><div class="pc-col">' +
      sezione('Sta lavorando', o.lav.length, o.lav.length ? '<div class="pc-voci">' + o.lav.map((c) => cardLavoro(ist, c)).join('') + '</div>' : '',
        senzaProcessi ? 'Non c\'è ancora un processo. Quando un lavoro si ripete uguale, ' + chiedi('automatizza questo lavoro') : 'Adesso nessun lavoro è in corso.') +
      sezione('Il periodo', null, cardPeriodo()) +
      '<section class="pc-sezione"><h2 class="pc-sez">Puoi chiedere all\'agente</h2><p class="pc-frasi">' + FRASI.map((f) => copiaBtn(f)).join('') + '</p><p class="pc-meta pc-frasi-nota">Tocca una frase per copiarla, poi incollala nella conversazione.</p></section>' +
      '</div></div></div>';
  },
  anteprima(ist) {
    const o = statoOggi(); const n = o.perTe;
    const righe = [];
    righe.push('<p class="pc-an-r pc-s-corre">' + ico('dots', 16) + '<span>' + (o.lav.length === 1 ? '1 sta lavorando' : o.lav.length + ' stanno lavorando') + '</span></p>');
    if (o.rit) righe.push('<p class="pc-an-r pc-an-amb">' + ico('alert', 16) + '<span>' + (o.rit === 1 ? '1 in ritardo' : o.rit + ' in ritardo') + '</span></p>');
    if (o.dg.length) righe.push('<p class="pc-an-r pc-an-err">' + ico('x', 16) + '<span>' + (o.dg.length === 1 ? '1 da guardare' : o.dg.length + ' da guardare') + '</span></p>');
    if (!o.rit && !o.dg.length) righe.push('<p class="pc-an-r pc-s-ok">' + ico('check', 16) + '<span>il resto è a posto</span></p>');
    return '<div class="pc-an pc-an-oggi' + (n ? ' pc-an-att' : '') + '"><p class="pc-an-data">' + esc(cap(fWGM.format(adesso()))) + '</p><div class="pc-an-corpo"><div class="pc-big' + (n ? ' pc-big-att' : '') + '">' + n + '</div><div class="pc-an-testo"><p class="pc-an-et">' + (n === 1 ? 'cosa aspetta te' : 'cose aspettano te') + '</p>' + righe.join('') + '</div></div></div>';
  },
  vai() { return false; },
  az(ist, a, el) {
    if (a === 'ferma') { ist.conferma = el.dataset.id; return 'rirendi'; }
    if (a === 'ferma-no') { ist.conferma = null; return 'rirendi'; }
    if (a === 'ferma-si') { ist.conferma = null; ferma(el.dataset.id); return 'fatto'; }
    return null;
  },
  livelli() { return []; },
};
