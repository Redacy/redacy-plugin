/* redacy · skills/pannello/sorgenti/fonte.js
   Da dove arrivano i dati del pannello nel plugin: dal server locale (pannello.py), nella stessa forma
   dei dati finti del prototipo, window.DATI = {stato, file}.
   - all'avvio: /api/stato, /api/file (il testo dei file) e /api/su-misura (le scelte dell'utente);
   - ogni 4 secondi: /api/stato e /api/file-firma; il testo dei file si rilegge solo se la firma cambia;
   - «Ferma»: POST /api/ferma col gettone che il server mette nella pagina.
   La pagina parte quando window.DATI_PRONTI si risolve. Se il server non risponde, un avviso lo dice e
   si riprova da soli. */
(function () {
  'use strict';
  window.REDACY_PANNELLO = true;
  var meta = document.querySelector('meta[name="redacy-gettone"]');
  var GETTONE = meta ? meta.getAttribute('content') : '';
  var OGNI = 4000;
  var file = {}, firmaFile = null, inCorso = false, falliti = 0;

  function prendi(u) {
    return fetch(u, { cache: 'no-store', headers: { Accept: 'application/json' } }).then(function (r) {
      if (!r.ok) throw new Error(u + ' ' + r.status);
      return r.json();
    });
  }

  function giro() {
    return Promise.all([prendi('/api/stato'), prendi('/api/file-firma')]).then(function (x) {
      var stato = x[0], ff = x[1] && x[1].firma;
      if (ff && ff === firmaFile) return { stato: stato, file: file, firma_file: firmaFile };
      return prendi('/api/file').then(function (y) {
        file = (y && y.file) || {}; firmaFile = y && y.firma;
        return { stato: stato, file: file, firma_file: firmaFile };
      });
    });
  }

  /* l'avviso: una riga in alto, sopra a tutto */
  var avviso = null, via = null;
  function mostraAvviso(testo, breve) {
    if (!document.body) return;
    if (!avviso) {
      avviso = document.createElement('p');
      avviso.setAttribute('role', 'status');
      avviso.style.cssText = 'position:fixed;z-index:2147483000;left:50%;transform:translateX(-50%);' +
        'top:calc(env(safe-area-inset-top, 0px) + 12px);margin:0;max-width:min(560px, calc(100vw - 32px));' +
        'padding:10px 16px;border-radius:12px;background:#2a1f12;color:#fff4e0;font:500 14px/1.4 -apple-system,' +
        'BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;box-shadow:0 8px 30px rgba(0,0,0,.25);text-align:center';
      document.body.appendChild(avviso);
    }
    avviso.textContent = testo;
    avviso.hidden = false;
    clearTimeout(via);
    if (breve) via = setTimeout(nascondiAvviso, 6000);
  }
  function nascondiAvviso() { if (avviso) avviso.hidden = true; }

  function aggiorna() {
    if (inCorso) return;
    inCorso = true;
    giro().then(function (d) {
      falliti = 0; if (avviso && !via) nascondiAvviso();
      window.DATI = d;
      if (window.Contenuti && window.Contenuti.carica) window.Contenuti.carica(d);
    }, function () {
      falliti++;
      if (falliti >= 2) mostraAvviso('Non riesco a leggere lo studio. Riprovo da solo; se dura, riaccendi il pannello.');
    }).then(function () { inCorso = false; });
  }

  function ferma(id) {
    return fetch('/api/ferma', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Gettone': GETTONE },
      body: JSON.stringify({ id: id })
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok || (j && j.ok === false)) mostraAvviso('Non si è fermato' + (j && j.errore ? ': ' + j.errore : '. Riprova.'), true);
      });
    }, function () {
      mostraAvviso('Non si è fermato: il pannello non risponde.', true);
    }).then(function () { inCorso = false; aggiorna(); });
  }

  /* la prima volta si riprova finché il server risponde */
  window.DATI_PRONTI = new Promise(function (pronto) {
    function prova() {
      Promise.all([giro(), prendi('/api/su-misura').catch(function () { return {}; })]).then(function (x) {
        nascondiAvviso();
        window.DATI = x[0];
        window.REDACY_MISURA = x[1] || {};
        if (window.Contenuti) {
          window.Contenuti.suFerma = ferma;
          if (window.Contenuti.carica) window.Contenuti.carica(x[0]);
        }
        setInterval(function () { if (!document.hidden) aggiorna(); }, OGNI);
        document.addEventListener('visibilitychange', function () { if (!document.hidden) aggiorna(); });
        pronto(x[0]);
      }, function () {
        mostraAvviso('Non riesco a leggere lo studio. Riprovo da solo; se dura, riaccendi il pannello.');
        setTimeout(prova, 2000);
      });
    }
    prova();
  });
})();
