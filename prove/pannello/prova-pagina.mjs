#!/usr/bin/env node
// prova-pagina.mjs · redacy 0.4.1
// La pagina vera del pannello in un Chromium senza finestra, contro il server vero:
//  - parte, prende i dati dal server (stato, testo dei file, scelte su misura) e non scrive errori in console
//    (vale anche per la Content-Security-Policy: una risorsa esterna bloccata è un errore);
//  - niente bottoni rossi nelle finestre; il dock c'è;
//  - «Ferma» dal pannello Oggi, con la sua conferma, ferma davvero la corsa in corso.
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
  ch.stderr.on('data', (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) ok(m[1]); });
  setTimeout(() => fine(1, 'FALLISCE il Chromium non parte: ' + CHROMIUM), 20000);
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
await valuta(`document.querySelector('.pc-btn-ferma[data-id="${idInCorso}"]').click()`);
await aspetta(`!!document.querySelector('[data-az="ferma-si"]')`, 4000, 'la conferma di «Ferma» non compare');
await foto('conferma.png');
await valuta(`document.querySelector('[data-az="ferma-si"]').click()`);
await dormi(2500);
const stato = await valuta(`fetch('/api/corse', {cache: 'no-store'}).then(function (r) { return r.json(); }).then(function (x) {
  var l = Array.isArray(x) ? x : (x.corse || []); var c = l.find(function (k) { return k.id === '${idInCorso}'; }); return c ? c.stato : 'non trovata'; })`);
await foto('dopo-ferma.png');
if (stato !== 'fermata') fine(1, 'FALLISCE dopo «Ferma» la corsa è ' + stato);

ws.close();
if (errori.length) fine(1, 'FALLISCE errori in console: ' + errori.slice(0, 5).join(' | '));
fine(0, 'PASSA pagina vera: dati dal server (' + v.file + ' file), niente bottoni rossi, «Ferma» ha fermato ' + idInCorso);
