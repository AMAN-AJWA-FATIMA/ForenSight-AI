/* Dataset view: before/after numbers, preprocessing steps, raw/processed preview and one EDA panel. */
(() => {
  const { el, clear, num, $ } = FS;

  function compare(label, icon, tone, before, after, sub) {
    return FS.kpi({ icon, tone, label, value: `${num(before)} → ${num(after)}`, sub });
  }
  function steps(r, d) {
    const L = r.data_log, rs = d.raw_stats, f = d.features, net = FS.state.exp === 'network';
    const list = [
      ['Raw data', `${num(rs.rows)} rows × ${num(rs.columns)} columns` + (net ? ' (CSV files merged)' : '')],
      ['Cleaning', `${num(L.rows_dropped_missing_label)} unlabelled rows removed, labels set to 0 / 1` + (net ? `, ${f.identifier_columns_removed.length} ID columns dropped` : '')],
      ['Missing values', `${num(rs.invalid_non_numeric_cells + rs.infinite_cells)} invalid or infinite cells set to missing, then median-imputed`],
      ['Duplicates', `${num(L.duplicate_rows_removed)} exact duplicate rows removed`],
      ['Feature filter', `${num(f.zero_variance_removed.length)} constant features removed`],
      ['Model input', `${num(d.processed_stats.rows)} × ${num(d.processed_stats.features)}, ${r.split.split(' (')[0].toLowerCase()}`]];
    clear($('#steps'), ...list.map(([t, s]) => el('div', { class: 'step' }, el('b', {}, t), el('span', {}, s))));
  }
  function preview(d) {
    const show = which => { const t = d[which === 'raw' ? 'raw_preview' : 'processed_preview'];
      clear($('#preview'), FS.table(t.columns, t.rows.map(r => r.map(v => v == null ? '—' : v)), { numeric: [] })); };
    $('#preview-note').textContent = FS.state.exp === 'network' ? 'First 5 rows. IP address columns are hidden.' : 'First 5 rows (first columns and the label).';
    FS.$$('#preview-tabs button').forEach((b, i) => b.classList.toggle('on', i === 0)); show('raw');
    FS.tabs($('#preview-tabs'), show);
  }
  function eda(d) {
    const body = $('#eda-body'); clear(body);
    if (FS.state.exp === 'static') {
      $('#eda-title').textContent = 'Features that separate the classes'; $('#eda-sub').textContent = 'Share of apps (%) that use each feature, for the 10 features whose usage differs most.';
      body.append(el('div', { class: 'chart tall' }, el('canvas', { id: 'c-eda' })));
      const names = Object.keys(d.feature_frequency);
      FS.chart('c-eda', () => { const c = FS.colors(); return { type: 'bar', data: { labels: names, datasets: [
        { label: 'Benign apps', data: names.map(n => d.feature_frequency[n].benign), backgroundColor: c.green, borderRadius: 5 }, { label: 'Malware apps', data: names.map(n => d.feature_frequency[n].malware), backgroundColor: c.red, borderRadius: 5 }] },
        options: { indexAxis: 'y', maintainAspectRatio: false, scales: { x: { title: { display: true, text: 'Apps using the feature (%)' }, beginAtZero: true, max: 100 }, y: { title: { display: true, text: 'Feature' }, ticks: { autoSkip: false } } } } }; });
    } else {
      $('#eda-title').textContent = 'Flow features that separate the classes'; $('#eda-sub').textContent = 'Share of each class (%) per value range, for the two flow features most related to the label.';
      Object.entries(d.histograms).forEach(([name, h], i) => {
        body.append(el('div', { class: 'chart' }, el('canvas', { id: 'c-eda-' + i })));
        const mid = h.edges.slice(0, -1).map((e, j) => ((e + h.edges[j + 1]) / 2).toFixed(1));
        FS.chart('c-eda-' + i, () => { const c = FS.colors(); return { type: 'bar', data: { labels: mid, datasets: [{ label: 'Benign', data: h.benign, backgroundColor: c.green }, { label: 'Malware', data: h.malware, backgroundColor: c.red }] },
          options: { maintainAspectRatio: false, scales: { x: { title: { display: true, text: name }, ticks: { maxTicksLimit: 8 } }, y: { title: { display: true, text: '% of class' }, beginAtZero: true } } } }; });
      });
    }
  }

  FS.views.data = { render() {
    const r = FS.res(), d = FS.data();
    if (!r || !d) return ['#prep-kpis', '#steps', '#preview', '#eda-body'].forEach(s => FS.empty($(s), 'Run `python -m src.evaluation.dashboard_data` to generate this view.'));
    const rs = d.raw_stats, ps = d.processed_stats;
    clear($('#prep-kpis'), compare('Rows', 'layers', 'blue', rs.rows, ps.rows, 'raw → cleaned'), compare('Features', 'grid', 'purple', rs.feature_columns, ps.features, 'raw → model input'),
      compare('Missing / invalid cells', 'alert', 'orange', rs.missing_cells + rs.invalid_non_numeric_cells + rs.infinite_cells, ps.missing_cells_before_imputation, 'imputed later, inside the pipeline'),
      compare('Duplicate rows', 'database', 'green', rs.duplicate_rows, ps.duplicate_rows, 'raw → cleaned'));
    steps(r, d); preview(d); eda(d);
  } };
})();
