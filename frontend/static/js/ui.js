/* Motion + display helpers: stagger, chart replay, section switcher, counters, radar, severity, progress. Loaded after core.js. */
(() => {
  const { $$, el } = FS, calm = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  FS.stagger = (root, sel = '.kpi,.card') => $$(sel, root).filter(n => !n.closest('[hidden]')).forEach((n, i) => {
    n.classList.remove('fx-up'); void n.offsetWidth; n.style.setProperty('--i', Math.min(i, 10)); n.classList.add('fx-up'); });
  FS.replay = root => $$('canvas', root).forEach(c => { const ch = window.Chart && Chart.getChart(c); if (ch) { ch.resize(); ch.reset(); ch.update(); } });
  FS.seg = bar => {                                  // show one section at a time, or everything
    const view = bar.closest('.view'), btns = $$('button', bar);
    const set = k => { btns.forEach(b => b.classList.toggle('on', b.dataset.show === k));
      $$('[data-panel]', view).forEach(p => { p.hidden = !(k === 'all' || p.dataset.panel.split(' ').includes(k)); });
      FS.stagger(view, '[data-panel]'); setTimeout(() => FS.replay(view), 40); };
    btns.forEach(b => b.addEventListener('click', () => set(b.dataset.show))); set(btns[0].dataset.show);
  };
  FS.countUp = n => {                                // animates every number in the text, e.g. "212,600 → 190,000" or "94.2%"
    const src = n.textContent, re = /\d[\d,]*(?:\.\d+)?/g; if (calm() || !re.test(src)) return; re.lastIndex = 0; const t0 = performance.now();
    const tick = t => { const k = Math.min(1, (t - t0) / 900), e = 1 - Math.pow(1 - k, 3);
      n.textContent = k < 1 ? src.replace(re, m => { const d = (m.split('.')[1] || '').length, v = parseFloat(m.replace(/,/g, '')) * e; return d ? v.toFixed(d) : Math.round(v).toLocaleString(); }) : src;
      if (k < 1) requestAnimationFrame(tick); };
    requestAnimationFrame(tick);
  };
  FS.sev = p => p < .2 ? { k: 'low', t: 'Low', c: '#1FA971' } : p < .5 ? { k: 'elev', t: 'Elevated', c: '#F2A93B' } : p < .8 ? { k: 'high', t: 'High', c: '#E5484D' } : { k: 'crit', t: 'Critical', c: '#E5484D' };
  FS.radar = (p, px = 120) => {                      // p = malware probability; the closer the blip is to the centre, the higher the score
    const r = el('div', { class: 'radar', role: 'img', 'aria-label': p == null ? 'Scanning' : `Threat radar, malware probability ${(p * 100).toFixed(0)}%` }); r.style.setProperty('--r', px + 'px');
    if (p != null) { const d = (1 - p) * 42, b = el('i', { class: 'blip' }); b.style.cssText = `left:${50 + d * .77}%;top:${50 - d * .64}%;--bc:${FS.sev(p).c}`; r.append(b); }
    return r;
  };
  FS.progress = () => {                              // eases towards 92% while the request runs; done() completes it
    const bar = el('i'), box = el('div', { class: 'prog' }, bar); let w = 8; bar.style.width = w + '%';
    const id = setInterval(() => { w += (92 - w) * .12; bar.style.width = w + '%'; }, 250);
    return { node: box, done: () => { clearInterval(id); bar.style.width = '100%'; } };
  };
})();
