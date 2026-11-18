/* Shared helpers: DOM, formatting, API, charts, icons and small UI components. Loaded first. */
(() => {
  const FS = window.FS = { state: { exp: 'static', R: null, D: null, schema: {}, last: {}, recent: {} }, views: {} };

  /* ---------- DOM + formatting ---------- */
  FS.$ = (s, r = document) => r.querySelector(s);
  FS.$$ = (s, r = document) => [...r.querySelectorAll(s)];
  FS.el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) k === 'class' ? n.className = v : n.setAttribute(k, v);
    kids.flat().forEach(k => k != null && n.append(k instanceof Node ? k : document.createTextNode(String(k))));
    return n;                                         // text is always inserted as text, never as HTML
  };
  FS.clear = (node, ...kids) => { node.replaceChildren(...kids.flat().filter(k => k != null)); return node; };
  FS.pct = x => (x == null ? 'n/a' : (x * 100).toFixed(1) + '%');
  FS.num = x => (x == null ? 'n/a' : Number(x).toLocaleString());
  FS.css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  FS.res = () => FS.state.R && FS.state.R[FS.state.exp];       // training results of the selected experiment
  FS.data = () => FS.state.D && FS.state.D[FS.state.exp];      // previews / samples of the selected experiment
  FS.UNIT = { static: 'apps', network: 'flows' };
  const { el, clear } = FS;

  /* ---------- API + alert ---------- */
  FS.alert = (msg) => { const a = FS.$('#alert'); a.textContent = msg || ''; a.hidden = !msg; };
  FS.api = async (url, opts) => {
    let res;
    try { res = await fetch(url, opts); } catch (e) { throw new Error('Cannot reach the server. Is Flask running?'); }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  };

  /* ---------- icons (static SVG constants) ---------- */
  const ICONS = {
    grid: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.7-4 3-9 3s-9-1.3-9-3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5"/>',
    bars: '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    eye: '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
    shield: '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    layers: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>',
    alert: '<path d="M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17.01"/>',
    target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    activity: '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/>',
    sun: '<circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/>',
    menu: '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
    home: '<path d="M3 11l9-8 9 8"/><path d="M5 10v10h14V10"/>',
    check: '<polyline points="20 6 9 17 4 12"/>',
    info: '<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8.01"/>' };
  FS.icon = name => { const s = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); s.setAttribute('viewBox', '0 0 24 24'); s.innerHTML = ICONS[name] || ''; return s; };
  FS.fillIcons = (root = document) => FS.$$('[data-icon]', root).forEach(n => n.replaceChildren(FS.icon(n.dataset.icon)));

  /* ---------- charts (redrawn when the theme changes) ---------- */
  const instances = {}, painters = {};
  FS.colors = () => ({ green: FS.css('--green'), red: FS.css('--red'), blue: FS.css('--blue'), amber: FS.css('--orange'), purple: FS.css('--purple'), muted: FS.css('--muted') });
  FS.chart = (id, make) => {
    const paint = () => {
      const canvas = document.getElementById(id); if (!canvas) return;
      if (instances[id]) instances[id].destroy();
      Chart.defaults.color = FS.css('--muted'); Chart.defaults.borderColor = FS.css('--border');
      instances[id] = new Chart(canvas, make());
    };
    painters[id] = paint; paint();
  };
  FS.repaintCharts = () => Object.values(painters).forEach(p => p());
  FS.scales = (xTitle, yTitle, y = {}, x = {}) => ({ x: { title: { display: true, text: xTitle }, grid: { display: false }, ...x }, y: { title: { display: true, text: yTitle }, beginAtZero: true, ...y } });
  FS.donut = (id, counts) => FS.chart(id, () => {
    const c = FS.colors(), total = counts.benign + counts.malware, text = FS.css('--text');
    return { type: 'doughnut', data: { labels: ['Benign', 'Malware'], datasets: [{ data: [counts.benign, counts.malware], backgroundColor: [c.green, c.red], borderWidth: 0, borderRadius: 8, spacing: 3 }] },
      options: { maintainAspectRatio: false, cutout: '68%', plugins: { legend: { position: 'bottom' } } },
      plugins: [{ id: 'centre', afterDraw(ch) {             // total in the middle of the donut
        const { ctx, chartArea: a } = ch, x = (a.left + a.right) / 2, y = (a.top + a.bottom) / 2;
        ctx.save(); ctx.textAlign = 'center'; ctx.fillStyle = text; ctx.font = '700 20px sans-serif'; ctx.fillText(total.toLocaleString(), x, y + 4);
        ctx.fillStyle = FS.css('--muted'); ctx.font = '12px sans-serif'; ctx.fillText('records', x, y + 22); ctx.restore(); } }] };
  });
  FS.hbar = (id, items, label, color) => FS.chart(id, () => ({ type: 'bar',
    data: { labels: items.map(i => i.feature), datasets: [{ label, data: items.map(i => i.value), backgroundColor: color || FS.colors().green, borderRadius: 6 }] },
    options: { indexAxis: 'y', maintainAspectRatio: false, plugins: { legend: { display: false } },
      scales: { x: { title: { display: true, text: label } }, y: { title: { display: true, text: 'Feature' }, ticks: { autoSkip: false } } } } }));
  FS.curveChart = (id, models, key, xk, yk, xTitle, yTitle, ref) => FS.chart(id, () => {
    const c = FS.colors(), colors = [c.blue, c.green, c.amber];
    return { type: 'scatter', data: { datasets: [
      ...Object.entries(models).map(([name, m], i) => ({ label: `${name} (${(key === 'roc' ? m.tuned.roc_auc : m.tuned.pr_auc).toFixed(3)})`, showLine: true, pointRadius: 0, borderWidth: 2, tension: 0, borderColor: colors[i],
        data: m[key][xk].map((x, j) => ({ x, y: m[key][yk][j] })) })),
      { label: ref.label, showLine: true, pointRadius: 0, borderDash: [6, 6], borderColor: c.muted, borderWidth: 1, data: ref.data }] },
      options: { maintainAspectRatio: false, scales: { x: { type: 'linear', min: 0, max: 1, title: { display: true, text: xTitle } }, y: { type: 'linear', min: 0, max: 1, title: { display: true, text: yTitle } } } } };
  });

  /* ---------- UI components ---------- */
  FS.empty = (node, msg) => clear(node, el('div', { class: 'empty' }, msg));
  FS.pill = (text, tone = '') => el('span', { class: 'pill ' + tone }, text);
  FS.countUp = node => {                       // animate a number like "212,600" or "94.2%" from 0
    const m = /^([\d,]+(?:\.\d+)?)(%?)$/.exec(node.textContent); if (!m || !window.matchMedia || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const to = parseFloat(m[1].replace(/,/g, '')), dec = (m[1].split('.')[1] || '').length, t0 = performance.now();
    const fmt = v => (dec ? v.toFixed(dec) : Math.round(v).toLocaleString()) + m[2];
    const tick = t => { const k = Math.min(1, (t - t0) / 900); node.textContent = k < 1 ? fmt(to * (1 - Math.pow(1 - k, 3))) : m[0]; if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  };
  FS.kpi = ({ icon, tone, label, value, sub, delta }) => {
    const v = el('div', { class: 'kpi-value' }, value);
    const box = el('div', { class: 'kpi t-' + tone }, el('div', { class: 'kpi-icon tone-' + tone }, FS.icon(icon)),
      el('div', {}, el('div', { class: 'kpi-label' }, label), v, el('div', { class: 'kpi-sub' }, delta ? el('span', { class: delta.up ? 'up' : 'down' }, delta.text + ' ') : '', sub)));
    FS.countUp(v); return box;
  };
  FS.gradient = hex => ctx => {                 // soft fade under line charts
    const a = ctx.chart.chartArea; if (!a) return hex + '33';
    const g = ctx.chart.ctx.createLinearGradient(0, a.top, 0, a.bottom); g.addColorStop(0, hex + '66'); g.addColorStop(1, hex + '05'); return g;
  };
  FS.table = (head, rows, { sel, numeric = [], onRow } = {}) => el('table', { class: 't' },
    el('thead', {}, el('tr', {}, head.map((h, i) => el('th', { class: numeric.includes(i) ? 'n' : '' }, h)))),
    el('tbody', {}, rows.map((r, ri) => { const tr = el('tr', { class: (sel === ri ? 'sel ' : '') + (onRow ? 'click' : '') }, r.map((c, i) => el('td', { class: numeric.includes(i) ? 'n' : '' }, c)));
      if (onRow) tr.addEventListener('click', () => onRow(ri)); return tr; })));
  FS.rankBars = items => el('div', {}, ...items.map(i => { const bar = el('i'); bar.style.width = (i.value / Math.max(...items.map(x => x.value), 1e-9) * 100) + '%';
    return el('div', { class: 'rank' }, el('span', { class: 'name', title: i.label }, i.label), el('div', { class: 'bar' }, bar), el('span', { class: 'v' }, i.value.toFixed(3))); }));
  FS.contribBars = items => { const max = Math.max(...items.map(i => Math.abs(i.value)), 1e-9);
    return el('div', {}, ...items.map(i => { const w = Math.abs(i.value) / max * 50, fill = el('div', { class: 'fill' + (i.value < 0 ? ' neg' : '') });
      fill.style.width = w + '%'; fill.style.left = (i.value < 0 ? 50 - w : 50) + '%';
      return el('div', { class: 'contrib' }, el('span', { class: 'name', title: i.label }, i.label), el('div', { class: 'track' }, fill), el('span', { class: 'v' }, (i.value >= 0 ? '+' : '') + i.value.toFixed(3))); })); };
  FS.tabs = (container, onChange) => FS.$$('button', container).forEach(b => b.addEventListener('click', () => {
    FS.$$('button', container).forEach(x => x.classList.toggle('on', x === b)); onChange(b.dataset.tab); }));

  /* ---------- theme ---------- */
  FS.setTheme = t => {
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('fs-theme', t); } catch (e) { /* storage may be blocked */ }
    clear(FS.$('#theme-icon'), FS.icon(t === 'dark' ? 'sun' : 'moon')); FS.$('#theme-label').textContent = t === 'dark' ? 'Light mode' : 'Dark mode';
    FS.repaintCharts();
  };
})();
