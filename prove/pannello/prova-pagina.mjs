#!/usr/bin/env node
// prova-pagina.mjs · redacy 0.5.0
// La pagina vera del pannello in un Chromium senza finestra, contro il server vero:
//  - parte, prende i dati dal server (stato, testo dei file, scelte su misura) e non scrive errori in console
//    (vale anche per la Content-Security-Policy: una risorsa esterna bloccata è un errore);
//  - niente bottoni rossi nelle finestre; il dock c'è;
//  - «Ferma» dal pannello Oggi, con la sua conferma, ferma davvero la corsa in corso;
//  - un file dello studio che non si legge (todo.json rotto) compare in Oggi, «Da guardare», col nome del file e la
//    frase «controlla <file>»; senza file rotti la voce non c'è; uno studio nuovo con un file rotto non è «pronto».
// Uso: node prova-pagina.mjs <url del pannello> <id della corsa in corso> <cartella per le foto>
// Il Chromium: $REDACY_CHROMIUM, oppure quello di Playwright in ~/.cache/ms-playwright, oppure chromium o
// google-chrome nel PATH. Se non c'è, stampa SALTA ed esce con 0. Serve Node 22 o più (WebSocket).
import { spawn, execFileSync } from 'node:child_process';
import { existsSync, readdirSync, writeFileSync, mkdtempSync, mkdirSync } from 'node:fs';
import { tmpdir, homedir } from 'node:os';
import { join } from 'node:path';

const [url, idInCorso, cartellaFoto] = process.argv.slice(2);
if (!url || !idInCorso || !cartellaFoto) { console.log('FALLISCE uso: node prova-pagina.mjs <url> <id in corso> <cartella foto>'); process.exit(1); }
if (typeof WebSocket === 'undefined') { console.log('SALTA serve Node 22 o più'); process.exit(0); }

function trovaChromium() {
  if (process.env.REDACY_CHROMIUM && existsSync(process.env.REDACY_CHROMIUM)) return process.env.REDACY_CHROMIUM;
  const pw = join(homedir(), '.cache', 'ms-playwright');
  if (existsSync(pw)) {
    for (const d of readdirSync(pw).sort().reverse()) {
      for (const p of [join(pw, d, 'chrome-linux', 'headless_shell'), join(pw, d, 'chrome-linux', 'chrome')]) if (existsSync(p)) return p;
    }
  }
  for (const n of ['chromium', 'chromium-browser', 'google-chrome']) {
    try { return execFileSync('which', [n], { encoding: 'utf8' }).trim() || null; } catch (e) { /* prossimo */ }
  }
  return null;
}
const CHROMIUM = trovaChromium();
if (!CHROMIUM) { console.log('SALTA nessun Chromium trovato'); process.exit(0); }
mkdirSync(cartellaFoto, { recursive: true });

const dir = mkdtempSync(join(tmpdir(), 'prova-pagina-'));
const ch = spawn(CHROMIUM, ['--headless=new', '--no-sandbox', '--hide-scrollbars', '--remote-debugging-port=0', '--user-data-dir=' + dir, 'about:blank'],
  { stdio: ['ignore', 'ignore', 'pipe'] });
const fine = (codice, testo) => { console.log(testo); try { ch.kill(); } catch (e) { /* già spento */ } process.exit(codice); };
const wsBrowser = await new Promise((ok) => {
  let buf = '';
  const attesa = setTimeout(() => fine(1, 'FALLISCE il Chromium non parte: ' + CHROMIUM), 20000);
  ch.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) { clearTimeout(attesa); ok(m[1]); } });
});
const porta = new URL(wsBrowser).port;
const lista = await (await fetch(`http://127.0.0.1:${porta}/json/list`)).json();
const ws = new WebSocket(lista.find((t) => t.type === 'page').webSocketDebuggerUrl);
await new Promise((ok) => ws.addEventListener('open', ok));
let n = 0; const attese = new Map(); const errori = [];
ws.addEventListener('message', (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && attese.has(m.id)) { attese.get(m.id)(m); attese.delete(m.id); return; }
  if (m.method === 'Runtime.exceptionThrown') errori.push('eccezione ' + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === 'Runtime.consoleAPICalled' && ['error', 'assert'].includes(m.params.type)) errori.push('console ' + m.params.args.map((x) => x.value ?? x.description).join(' '));
  if (m.method === 'Log.entryAdded' && m.params.entry.level === 'error') errori.push('log ' + m.params.entry.text + ' ' + (m.params.entry.url || ''));
});
const cmd = (method, params = {}) => new Promise((ok) => { const id = ++n; attese.set(id, ok); ws.send(JSON.stringify({ id, method, params })); });
const dormi = (ms) => new Promise((r) => setTimeout(r, ms));
const valuta = async (expr) => { const r = await cmd('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); return r.result?.result?.value; };
const foto = async (nome) => { const r = await cmd('Page.captureScreenshot', { format: 'png' }); writeFileSync(join(cartellaFoto, nome), Buffer.from(r.result.data, 'base64')); };
const aspetta = async (expr, ms, perche) => { const t0 = Date.now(); while (Date.now() - t0 < ms) { if (await valuta(expr)) return; await dormi(200); } fine(1, 'FALLISCE ' + perche); };

await cmd('Runtime.enable'); await cmd('Log.enable'); await cmd('Page.enable');
await cmd('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
await cmd('Page.navigate', { url: url.replace(/\/?$/, '/') + '#tutto' });

// 1. i dati arrivano dal server e la pagina parte
await aspetta('!!(window.DATI && window.DATI.stato && window.DATI.stato.cartella && window.Contenuti)', 15000, 'i dati non arrivano dal server');
await dormi(1500);
const c = await valuta(`JSON.stringify({
  plugin: window.REDACY_PANNELLO === true,
  file: Object.keys(window.DATI.file || {}).length,
  agents: typeof (window.DATI.file || {})['AGENTS.md'] === 'string',
  fonti: Object.keys(window.DATI.file || {}).some(function (k) { return k.indexOf('fonti/') === 0; }),
  carica: typeof Contenuti.carica === 'function',
  ferma: typeof Contenuti.suFerma === 'function',
  rossi: document.querySelectorAll('.sem, .semafori').length,
  dock: !!document.querySelector('nav[aria-label], .dock, [class*="dock"]'),
  titolo: document.title
})`);
const v = JSON.parse(c);
await foto('casa.png');
if (!v.plugin) fine(1, 'FALLISCE la pagina non sa di essere nel plugin (REDACY_PANNELLO)');
if (v.file < 5 || !v.agents) fine(1, 'FALLISCE il testo dei file non è arrivato: ' + c);
if (v.fonti) fine(1, 'FALLISCE nella pagina c\'è il contenuto di fonti/');
if (!v.carica || !v.ferma) fine(1, 'FALLISCE Contenuti.carica o suFerma mancano: ' + c);
if (v.rossi) fine(1, 'FALLISCE ci sono ancora i bottoni rossi delle finestre');
if (!v.dock) fine(1, 'FALLISCE non trovo il dock');

// 2. «Ferma» dal pannello Oggi, con la conferma
await valuta(`location.hash = '#oggi'`);
await aspetta(`!!document.querySelector('.pc-btn-ferma[data-id="${idInCorso}"]')`, 8000, 'in Oggi non c\'è «Ferma» per la corsa in corso');
// senza file illeggibili la sezione «Da guardare» non ha la voce dei problemi
const VOCE_PROBLEMA = `Array.from(document.querySelectorAll('.pc-voce-err')).filter(function (e) { return /Un file dello studio non si legge/.test(e.textContent); })`;
if (await valuta(`${VOCE_PROBLEMA}.length`) !== 0) fine(1, 'FALLISCE in Oggi c\'è una voce «Un file dello studio non si legge» ma nessun file è rotto');
await valuta(`document.querySelector('.pc-btn-ferma[data-id="${idInCorso}"]').click()`);
await aspetta(`!!document.querySelector('[data-az="ferma-si"]')`, 4000, 'la conferma di «Ferma» non compare');
await foto('conferma.png');
await valuta(`document.querySelector('[data-az="ferma-si"]').click()`);
await dormi(2500);
const stato = await valuta(`fetch('/api/corse', {cache: 'no-store'}).then(function (r) { return r.json(); }).then(function (x) {
  var l = Array.isArray(x) ? x : (x.corse || []); var c = l.find(function (k) { return k.id === '${idInCorso}'; }); return c ? c.stato : 'non trovata'; })`);
await foto('dopo-ferma.png');
if (stato !== 'fermata') fine(1, 'FALLISCE dopo «Ferma» la corsa è ' + stato);

// 3. Un file dello studio che non si legge compare in «Da guardare», con il nome e la frase da copiare
const radice = await valuta('window.DATI.stato.cartella.percorso');
writeFileSync(join(radice, 'periodo', 'todo.json'), '{"todo": [');
await aspetta(`${VOCE_PROBLEMA}.length === 1`, 12000, 'un todo.json rotto non compare in «Da guardare»');
const p = JSON.parse(await valuta(`(function () { var e = ${VOCE_PROBLEMA}[0]; return JSON.stringify({
  html: e.outerHTML, titolo: e.querySelector('.pc-voce-h').textContent, forte: e.querySelector('.pc-meta-forte').textContent,
  frase: e.querySelector('[data-az="copia"]').dataset.t, sezione: e.closest('.pc-sezione').querySelector('.pc-sez').textContent,
  anteprima: Array.from(document.querySelectorAll('.pc-ao-err')).map(function (x) { return x.textContent; }),
  guardare: Contenuti.riassunto('oggi').guardare }); })()`));
await foto('problema.png');
if (!/^periodo\/todo\.json: /.test(p.forte)) fine(1, 'FALLISCE la voce non dice il file rotto: ' + p.forte);
if (p.frase !== 'controlla periodo/todo.json') fine(1, 'FALLISCE la frase da copiare è «' + p.frase + '»');
if (!/^Da guardare/.test(p.sezione)) fine(1, 'FALLISCE la voce non sta in «Da guardare»: ' + p.sezione);
if (!/periodo\/todo\.json.*Non si legge/.test(p.anteprima.join('|'))) fine(1, 'FALLISCE l\'anteprima non dice «Non si legge»: ' + p.anteprima.join('|'));
if (!(p.guardare >= 1)) fine(1, 'FALLISCE il conto «da guardare» non cresce: ' + p.guardare);
// il testo viene da nomi di file dell'utente: niente HTML che passa
const xss = await valuta(`(function () { var s = JSON.parse(JSON.stringify(window.DATI.stato)); s.problemi = ['x<img src=y onerror=alert(1)>.json: non si legge'];
  Contenuti.carica({ stato: s, file: window.DATI.file }); return document.querySelectorAll('.pc-voce-err img').length; })()`);
if (xss !== 0) fine(1, 'FALLISCE il nome di un file entra come HTML nella pagina');
// uno studio nuovo e vuoto con un file che non si legge: la vista normale, non «Lo studio è pronto»
const vuoto = JSON.parse(await valuta(`(function () {
  var base = { ora: window.DATI.stato.ora, cartella: window.DATI.stato.cartella, periodo: { obiettivo: '', obiettivo_vuoto: true, todo: { todo: [], idee: [] }, idee: { idee: [] }, aspettano_te: [] }, grafi: [], corse: [], corse_in_corso: [], corse_ultime: [], workspace: [], problemi: [] };
  function testo(s) { Contenuti.carica({ stato: s, file: {} }); var e = document.createElement('div'); var i = Contenuti.monta('oggi', e, 'pieno'); var t = e.textContent; i.smonta(); return t; }
  var senza = testo(base); base.problemi = ['periodo/todo.json: non si legge, chiedi di ripararlo']; var con = testo(base);
  return JSON.stringify({ senza: senza, con: con, riass: Contenuti.riassunto('oggi').guardare }); })()`));
if (!/Lo studio è pronto/.test(vuoto.senza)) fine(1, 'FALLISCE lo studio nuovo e vuoto non dice «Lo studio è pronto»');
if (/Lo studio è pronto/.test(vuoto.con) || !/Un file dello studio non si legge/.test(vuoto.con)) fine(1, 'FALLISCE con un file illeggibile lo studio vuoto mostra ancora «Lo studio è pronto»: ' + vuoto.con.slice(0, 120));
console.log('HTML della voce: ' + p.html);

ws.close();
if (errori.length) fine(1, 'FALLISCE errori in console: ' + errori.slice(0, 5).join(' | '));
fine(0, 'PASSA pagina vera: dati dal server (' + v.file + ' file), niente bottoni rossi, «Ferma» ha fermato ' + idInCorso + ', un todo.json rotto compare in «Da guardare»');
