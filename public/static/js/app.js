/* Boot: theme, hash router (one view at a time), experiment switch, initial data load. Loaded last. */
(() => {
  const { $ } = FS, VIEWS = ['dashboard', 'data', 'models', 'explain', 'detect'], dirty = new Set(VIEWS);
  let current = 'dashboard';

  const pill = () => { const a = $('#nav a.on'), p = $('#nav-pill'); if (a && p) { p.style.height = a.offsetHeight + 'px'; p.style.transform = 'translateY(' + a.offsetTop + 'px)'; } };
  function show(name) {
    current = VIEWS.includes(name) ? name : 'dashboard';
    VIEWS.forEach(v => $('#view-' + v).classList.toggle('on', v === current));
    FS.$$('#nav a').forEach(a => a.classList.toggle('on', a.dataset.view === current));
    $('#sidebar').classList.remove('open'); pill(); setTimeout(() => FS.stagger($('#view-' + current), '.kpi,.card:not([data-panel])'), 0);
    if (dirty.has(current)) { dirty.delete(current); try { const p = FS.views[current].render(); if (p && p.catch) p.catch(e => FS.alert('Display error: ' + e.message)); } catch (e) { FS.alert('Display error: ' + e.message); } }
  }
  FS.markDirty = name => dirty.add(name);                 // re-render a view next time it is opened
  FS.go = name => { if (location.hash === '#' + name) show(name); else location.hash = '#' + name; };   // hashchange calls show()
  window.addEventListener('hashchange', () => show(location.hash.slice(1)));

  function setExperiment(k) {
    FS.state.exp = k; FS.$$('.exp-btn').forEach(b => { b.classList.toggle('on', b.dataset.exp === k); b.setAttribute('aria-selected', b.dataset.exp === k); });
    VIEWS.forEach(v => dirty.add(v)); show(current);
  }

  FS.fillIcons(); FS.$$('.seg').forEach(b => FS.seg(b)); $('.content').classList.add('is-loading');
  FS.setTheme(document.documentElement.dataset.theme || 'light');
  $('#theme-btn').addEventListener('click', () => FS.setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'));
  $('#menu-btn').addEventListener('click', () => $('#sidebar').classList.toggle('open'));
  FS.$$('.exp-btn').forEach(b => b.addEventListener('click', () => setExperiment(b.dataset.exp)));

  (async () => {
    const [res, data] = await Promise.allSettled([FS.api('/api/results'), FS.api('/api/dashboard-data')]);
    if (res.status === 'fulfilled') FS.state.R = res.value; else FS.alert(res.reason.message);
    if (data.status === 'fulfilled') FS.state.D = data.value;
    if (FS.state.R && !FS.state.R.static && FS.state.R.network) FS.state.exp = 'network';
    setExperiment(FS.state.exp);
    show(location.hash.slice(1) || 'dashboard'); $('.content').classList.remove('is-loading');
  })();
})();
