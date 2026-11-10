
/* ---------- memoria: ricerca di pagine (serve al Markdown) ---------- */
const nodiMem = () => arr(S.memoria_grafo && S.memoria_grafo.nodi);
const stem = (n) => String(n.chiave || n.id || '').split('/').pop();
function cercaPagina(nome, area) {
  nome = String(nome).replace(/\.md$/, '').trim(); const l = nodiMem();
  const candidati = l.filter((n) => stem(n) === nome || n.id === nome);
  if (candidati.length) return candidati.find((n) => n.area === area && !n.mancante) || candidati.find((n) => !n.mancante) || candidati[0];
  const lo = nome.toLowerCase();
  return l.find((n) => String(n.titolo || '').toLowerCase() === lo) || null;
}

/* ---------- Markdown: un piccolo renderer, tutto con escape ---------- */
function mdInline(t, ctx) {
  ctx = ctx || {}; const tok = []; const metti = (h) => { tok.push(h); return '\u0000' + (tok.length - 1) + '\u0000'; };
  t = String(t);
  t = t.replace(/`([^`]+)`/g, (m, c) => {
    const lk = ctx.noFile ? null : (F[c.trim()] != null || /^(AGENTS\.md|memoria\/[\w\-.\/]+\.md|grafi\/[\w\-.]+\.yaml|periodo\/[\w\-.]+|workspace\/[\w\-]+)$/.test(c.trim())) ? linkFile(c.trim()) : null;
    return metti(lk ? '<button type="button" class="pc-chip pc-chip-file" data-az="vai" data-p="' + esc(lk.pannello) + '" data-v="' + esc(lk.voce) + '" title="' + esc(lk.et) + '"><code>' + esc(c) + '</code></button>' : '<code class="pc-cod">' + esc(c) + '</code>');
  });
  t = t.replace(/\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g, (m, a, b) => {
    const n = cercaPagina(a, ctx.area);
    const lab = (b && b.trim()) || (n && n.titolo) || umano(a.trim());
    if (n && n.mancante) return metti('<button type="button" class="pc-chip pc-chip-manca" data-az="wiki" data-k="' + esc(n.chiave) + '" title="Pagina ancora da scrivere">' + esc(lab) + '</button>');
    if (n) return metti('<button type="button" class="pc-chip" data-az="wiki" data-k="' + esc(n.chiave) + '">' + esc(lab) + '</button>');
    return metti('<span class="pc-chip pc-chip-manca" title="Pagina ancora da scrivere">' + esc(lab) + '</span>');
  });
  t = t.replace(/\[([^\]]+)\]\(([^)\s]+)(?:\s+"[^"]*")?\)/g, (m, tx, u) => {
    if (/^(https?:|mailto:)/i.test(u)) return metti('<a class="pc-a" href="' + esc(u) + '" target="_blank" rel="noopener noreferrer">' + esc(tx) + '</a>');
    return metti('<span>' + esc(tx) + '</span>');
  });
  t = esc(t);
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/__([^_]+)__/g, '<strong>$1</strong>');
  t = t.replace(/(^|[\s(])\*([^*\s][^*]*)\*(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>').replace(/(^|[\s(])_([^_\s][^_]*)_(?=[\s).,;:!?]|$)/g, '$1<em>$2</em>');
  return t.replace(/\u0000(\d+)\u0000/g, (m, i) => tok[+i]);
}
function mdBlocchi(src, ctx, toc) {
  const L = src.split('\n'); let i = 0; const out = [];
  const ind = (s) => s.match(/^\s*/)[0].length;
  const LI = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
  const inizioBlocco = (l) => /^(#{1,6}\s|```|\s*>|\s*([-*+]|\d+[.)])\s+|(-{3,}|\*{3,}|_{3,})\s*$)/.test(l);
  function lista(i0) {
    let k = i0; const base = ind(L[k]); const ordinata = /^\s*\d/.test(L[k]); const voci = [];
    while (k < L.length) {
      const mm = L[k].match(LI);
      if (!mm || mm[1].length < base) break;
      if (mm[1].length > base && voci.length) { const r = lista(k); voci[voci.length - 1].sub += r[0]; k = r[1]; continue; }
      const v = { t: mm[3], sub: '' }; voci.push(v); k++;
      while (k < L.length && /^\s+\S/.test(L[k]) && !LI.test(L[k]) && ind(L[k]) > base) { v.t += ' ' + L[k].trim(); k++; }
      if (k + 1 < L.length && /^\s*$/.test(L[k]) && LI.test(L[k + 1]) && ind(L[k + 1]) >= base) k++;
    }
    const tg = ordinata ? 'ol' : 'ul';
    return ['<' + tg + ' class="pc-lista">' + voci.map((v) => '<li>' + mdInline(v.t, ctx) + v.sub + '</li>').join('') + '</' + tg + '>', k];
  }
  const celle = (r) => r.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
  while (i < L.length) {
    const l = L[i]; let m;
    if (/^\s*$/.test(l)) { i++; continue; }
    if ((m = l.match(/^\s*```/))) { const cod = []; i++; while (i < L.length && !/^\s*```/.test(L[i])) cod.push(L[i++]); i++; out.push('<pre class="pc-pre"><code>' + esc(cod.join('\n')) + '</code></pre>'); continue; }
    if ((m = l.match(/^(#{1,6})\s+(.*?)\s*#*\s*$/))) {
      const n = m[1].length; const id = (ctx.uid || 'x') + '-h' + toc.length;
      toc.push({ n: n, id: id, t: m[2].replace(/[`*_]/g, '') });
      out.push('<h' + n + ' class="pc-h pc-h' + n + '" id="' + id + '">' + mdInline(m[2], ctx) + '</h' + n + '>'); i++; continue;
    }
    if (/^(-{3,}|\*{3,}|_{3,})\s*$/.test(l)) { out.push('<hr class="pc-hr">'); i++; continue; }
    if (/^\s*>/.test(l)) { const q = []; while (i < L.length && /^\s*>/.test(L[i])) q.push(L[i++].replace(/^\s*>\s?/, '')); out.push('<blockquote class="pc-cit">' + mdBlocchi(q.join('\n'), ctx, []) + '</blockquote>'); continue; }
    if (l.indexOf('|') >= 0 && i + 1 < L.length && /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$/.test(L[i + 1])) {
      const th = celle(l); i += 2; const rows = [];
      while (i < L.length && L[i].indexOf('|') >= 0 && !/^\s*$/.test(L[i])) rows.push(celle(L[i++]));
      out.push('<table class="pc-tab"><thead><tr>' + th.map((c) => '<th>' + mdInline(c, ctx) + '</th>').join('') + '</tr></thead><tbody>' +
        rows.map((r) => '<tr>' + th.map((_, j) => '<td>' + mdInline(r[j] || '', ctx) + '</td>').join('') + '</tr>').join('') + '</tbody></table>');
      continue;
    }
    if (LI.test(l)) { const r = lista(i); out.push(r[0]); i = r[1]; continue; }
    const p = [l.trim()]; i++;
    while (i < L.length && !/^\s*$/.test(L[i]) && !inizioBlocco(L[i]) && !(L[i].indexOf('|') >= 0 && i + 1 < L.length && /^\s*\|?\s*:?-{2,}/.test(L[i + 1] || ''))) p.push(L[i++].trim());
    out.push('<p class="pc-p">' + mdInline(p.join(' '), ctx) + '</p>');
  }
  return out.join('');
}
function md(src, ctx) {
  ctx = ctx || {}; const toc = [];
  src = String(src == null ? '' : src).replace(/\r\n?/g, '\n').replace(/<\!--[\s\S]*?-->/g, '');
  const html = mdBlocchi(src, ctx, toc);
  return { html: html, toc: toc };
}
const primoTitolo = (src) => { const m = String(src || '').replace(/<\!--[\s\S]*?-->/g, '').match(/^#\s+(.+)$/m); return m ? m[1].trim() : ''; };
function primoParagrafo(src) {
  const t = String(src || '').replace(/<\!--[\s\S]*?-->/g, '').split('\n'); let i = 0;
  while (i < t.length && (/^\s*$/.test(t[i]) || /^#/.test(t[i]))) i++;
  const p = []; while (i < t.length && !/^\s*$/.test(t[i]) && !/^(#|```|\s*[-*]\s)/.test(t[i])) p.push(t[i++].trim());
  return p.join(' ').replace(/[`*_]/g, '').replace(/\[\[([^\]|]+)(?:\|[^\]]+)?\]\]/g, '$1');
}

/* ---------- YAML: il sottoinsieme che scrivono i processi ---------- */
function yamlParse(txt) {
  const lines = String(txt).replace(/\r/g, '').split('\n').map((raw) => ({ raw: raw, ind: raw.match(/^ */)[0].length, t: raw.trim() })).filter((l) => l.t && l.t[0] !== '#');
  let p = 0;
  const isSeq = (l) => l.t === '-' || l.t.indexOf('- ') === 0;
  function flow(s) {
    let i = 0;
    const ws = () => { while (s[i] === ' ') i++; };
    function val() {
      ws();
      if (s[i] === '{') { i++; const o = {}; ws(); while (s[i] !== '}' && i < s.length) { ws(); const k = key(); ws(); if (s[i] === ':') i++; o[k] = val(); ws(); if (s[i] === ',') i++; ws(); } i++; return o; }
      if (s[i] === '[') { i++; const a = []; ws(); while (s[i] !== ']' && i < s.length) { a.push(val()); ws(); if (s[i] === ',') i++; ws(); } i++; return a; }
      if (s[i] === '"' || s[i] === "'") { const q = s[i++]; let r = ''; while (i < s.length && s[i] !== q) { if (s[i] === '\\' && q === '"') i++; r += s[i++]; } i++; return r; }
      let r = ''; while (i < s.length && ',}]'.indexOf(s[i]) < 0) r += s[i++]; return scalar(r.trim());
    }
    function key() { ws(); if (s[i] === '"' || s[i] === "'") { const q = s[i++]; let r = ''; while (i < s.length && s[i] !== q) r += s[i++]; i++; return r; } let r = ''; while (i < s.length && s[i] !== ':' && s[i] !== ',' && s[i] !== '}') r += s[i++]; return r.trim(); }
    return val();
  }
  function scalar(s) {
    s = s.trim();
    if (s === '' || s === '~' || s === 'null') return null;
    if (s === 'true') return true; if (s === 'false') return false;
    if (/^-?\d+(\.\d+)?$/.test(s)) return Number(s);
    if (s[0] === '"') { const m = s.match(/^"((?:\\.|[^"\\])*)"/); if (m) return m[1].replace(/\\n/g, '\n').replace(/\\"/g, '"').replace(/\\\\/g, '\\'); }
    if (s[0] === "'") { const m = s.match(/^'((?:''|[^'])*)'/); if (m) return m[1].replace(/''/g, "'"); }
    if (s[0] === '{' || s[0] === '[') return flow(s);
    return s.replace(/\s+#.*$/, '');
  }
  function kv(t) { const m = t.match(/^("[^"]*"|'[^']*'|[^\s:#\[{"'][^:]*?)\s*:(?:\s+(.*))?$/); if (!m) return null; return [m[1].replace(/^["']|["']$/g, ''), m[2] == null ? '' : m[2]]; }
  function bloccoScalare(ind, tipo) {
    const righe = []; let minI = 1e9;
    while (p < lines.length && lines[p].ind > ind) { righe.push(lines[p]); minI = Math.min(minI, lines[p].ind); p++; }
    const t = righe.map((l) => l.raw.slice(minI));
    return tipo === '>' ? t.join(' ') : t.join('\n') + '\n';
  }
  function nodo(ind) { return isSeq(lines[p]) ? seq(ind) : map(ind); }
  function map(ind) {
    const o = {};
    while (p < lines.length && lines[p].ind === ind && !isSeq(lines[p])) {
      const r = kv(lines[p].t); if (!r) { p++; continue; }
      p++;
      if (r[1] === '') { o[r[0]] = (p < lines.length && (lines[p].ind > ind || (lines[p].ind === ind && isSeq(lines[p])))) ? nodo(lines[p].ind) : null; }
      else if (/^[|>][+-]?$/.test(r[1])) o[r[0]] = bloccoScalare(ind, r[1][0]);
      else o[r[0]] = scalar(r[1]);
    }
    return o;
  }
  function seq(ind) {
    const a = [];
    while (p < lines.length && lines[p].ind === ind && isSeq(lines[p])) {
      const t = lines[p].t.replace(/^-\s*/, '');
      if (t === '') { p++; a.push(p < lines.length && lines[p].ind > ind ? nodo(lines[p].ind) : null); continue; }
      const k = kv(t);
      if (k && !/^[\[{"']/.test(t)) { const off = lines[p].t.length - t.length; lines[p] = { raw: lines[p].raw, ind: ind + off, t: t }; a.push(map(ind + off)); }
      else { a.push(scalar(t)); p++; }
    }
    return a;
  }
  if (!lines.length) return null;
  return nodo(lines[0].ind);
}

/* ---------- testo grezzo con la sintassi colorata ---------- */
function coloraTesto(txt, re, f) {
  let out = '', last = 0, m; re.lastIndex = 0;
  while ((m = re.exec(txt))) { out += esc(txt.slice(last, m.index)) + f(m); last = m.index + m[0].length; if (m[0].length === 0) re.lastIndex++; }
  return out + esc(txt.slice(last));
}
function valColor(v) {
  const s = v.trim(); if (!s) return esc(v);
  if (/^(true|false|null|~)$/.test(s)) return '<span class="pc-s-kw">' + esc(v) + '</span>';
  if (/^-?\d+(\.\d+)?$/.test(s)) return '<span class="pc-s-n">' + esc(v) + '</span>';
  if (/^["']/.test(s)) return '<span class="pc-s-str">' + esc(v) + '</span>';
  if (/^[{\[]/.test(s)) return coloraTesto(v, /("(?:\\.|[^"\\])*"|'[^']*')|(\b(?:true|false|null)\b)|(-?\b\d+(?:\.\d+)?\b)|([\w\-]+)(?=\s*:)/g, (m) => m[1] ? '<span class="pc-s-str">' + esc(m[0]) + '</span>' : m[2] ? '<span class="pc-s-kw">' + esc(m[0]) + '</span>' : m[3] ? '<span class="pc-s-n">' + esc(m[0]) + '</span>' : '<span class="pc-s-k">' + esc(m[0]) + '</span>');
  return '<span class="pc-s-v">' + esc(v) + '</span>';
}
function coloraYaml(txt) {
  return String(txt).replace(/\r/g, '').split('\n').map((l) => {
    if (/^\s*#/.test(l)) return '<span class="pc-s-c">' + esc(l) + '</span>';
    const m = l.match(/^(\s*(?:-\s+)?)([^\s:#\[{"'][^:]*?|"[^"]*")(\s*:)(\s+.*)?$/);
    if (m) return esc(m[1]) + '<span class="pc-s-k">' + esc(m[2]) + '</span>' + esc(m[3]) + (m[4] ? valColor(m[4]) : '');
    const d = l.match(/^(\s*-\s+)(.*)$/); if (d) return esc(d[1]) + valColor(d[2]);
    return esc(l);
  }).join('\n');
}
function coloraJson(txt) {
  return coloraTesto(String(txt), /("(?:\\.|[^"\\])*")(\s*:)?|\b(true|false|null)\b|(-?\d+(?:\.\d+)?)/g, (m) => m[1] ? (m[2] ? '<span class="pc-s-k">' + esc(m[1]) + '</span>' + esc(m[2]) : '<span class="pc-s-str">' + esc(m[1]) + '</span>') : m[3] ? '<span class="pc-s-kw">' + esc(m[3]) + '</span>' : '<span class="pc-s-n">' + esc(m[4]) + '</span>');
}
function coloraMd(txt) {
  return String(txt).split('\n').map((l) => /^#{1,6}\s/.test(l) ? '<span class="pc-s-k">' + esc(l) + '</span>' : /^\s*<\!--/.test(l) ? '<span class="pc-s-c">' + esc(l) + '</span>' : esc(l)).join('\n');
}
function coloraPer(path, txt) { return /\.ya?ml$/.test(path) ? coloraYaml(txt) : /\.json$/.test(path) ? coloraJson(txt) : coloraMd(txt); }

/* ---------- chiavi e valori leggibili ---------- */
function vista(v, prof) {
  prof = prof || 0;
  if (v == null) return '<span class="pc-nullo">vuoto</span>';
  if (typeof v === 'boolean') return '<span class="pc-bool">' + (v ? 'sì' : 'no') + '</span>';
  if (typeof v === 'number') return '<span class="pc-num">' + v + '</span>';
  if (typeof v === 'string') return v.indexOf('\n') >= 0 && v.trim().indexOf('\n') >= 0 ? '<span class="pc-testoV pc-testoV-multi">' + esc(v.trim()) + '</span>' : '<span class="pc-testoV">' + esc(v.trim()) + '</span>';
  if (Array.isArray(v)) {
    if (!v.length) return '<span class="pc-nullo">nessuno</span>';
    if (v.every((x) => x == null || typeof x !== 'object')) return '<span class="pc-valori">' + v.map((x) => '<span class="pc-val">' + vista(x, prof + 1) + '</span>').join('') + '</span>';
    return '<div class="pc-schede">' + v.map((x, i) => '<div class="pc-scheda"><div class="pc-scheda-n">' + (i + 1) + '</div>' + vista(x, prof + 1) + '</div>').join('') + '</div>';
  }
  const ks = Object.keys(v); if (!ks.length) return '<span class="pc-nullo">vuoto</span>';
  return '<dl class="pc-kv' + (prof ? ' pc-kv-in' : '') + '">' + ks.map((k) => '<div class="pc-kv-r"><dt>' + esc(k) + '</dt><dd>' + vista(v[k], prof + 1) + '</dd></div>').join('') + '</dl>';
}
/* il file, mostrato come interfaccia + il grezzo a un clic */
function sezioneFile(path, opz) {
  opz = opz || {}; const txt = F[path]; if (txt == null) return '';
  let corpo = '';
  try {
    if (/\.ya?ml$/.test(path)) corpo = vista(yamlParse(txt));
    else if (/\.json$/.test(path)) corpo = vista(JSON.parse(txt));
  } catch (e) { corpo = '<p class="pc-p pc-tenue">Non riesco a leggere questo file come schede: guarda il testo qui sotto.</p>'; }
  return '<section class="pc-file"><h2 class="pc-sez">' + (opz.titolo || 'Guarda il file com\'è scritto') + '</h2>' +
    '<div class="pc-file-nome">' + ico('file', 16) + '<code>' + esc(path) + '</code></div>' + corpo +
    '<details class="pc-grezzo"' + (opz.aperto ? ' open' : '') + '><summary>' + ico('code', 16) + '<span>Mostra il testo grezzo</span></summary><pre class="pc-pre pc-pre-colori"><code>' + coloraPer(path, txt) + '</code></pre></details></section>';
}
