/* Landing view: KPIs, ROC curve, class donut, top features, live recent analyses, model comparison, insights. */
(() => {
  const { el, clear, pct, num, $ } = FS;
  const RESULT = (truth, p) => truth === 'malware' ? (p >= 0.5 ? ['Caught', 'green'] : ['Missed', 'red']) : (p >= 0.5 ? ['False alarm', 'amber'] : ['Cleared', 'green']);

  function kpis(r) {
    const L = r.data_log, m = r.models[r.best_model], b = m.tuned, d = (b.f1 - m.baseline.f1) * 100;
    clear($('#kpis'),
      FS.kpi({ icon: 'layers', tone: 'blue', label: 'Samples analysed', value: num(L.rows_final), sub: `${num(r.n_test)} held out for testing` }),
      FS.kpi({ icon: 'alert', tone: 'orange', label: 'Malware share', value: pct(L.class_counts.malware / L.rows_final), sub: `${num(L.class_counts.malware)} malware · ${num(L.class_counts.benign)} benign` }),
      FS.kpi({ icon: 'activity', tone: 'purple', label: 'F1-score', value: pct(b.f1), sub: `${r.best_model} vs baseline`, delta: { up: d >= 0, text: `${d >= 0 ? '▲ +' : '▼ '}${d.toFixed(1)} pp` } }),
      FS.kpi({ icon: 'target', tone: 'green', label: 'Malware caught (recall)', value: pct(b.recall), sub: `${pct(b.false_negative_rate)} missed` }));
  }

  function charts(r) {
    const b = r.models[r.best_model].tuned, mod = r.models[r.best_model];
    $('#roc-note').textContent = `${r.best_model} · AUC ${b.roc_auc.toFixed(3)}`;
    FS.chart('c-roc', () => { const c = FS.colors(); return { type: 'scatter', data: { datasets: [
      { label: 'ROC curve', showLine: true, pointRadius: 0, borderWidth: 2, tension: 0, borderColor: c.green, backgroundColor: FS.gradient(c.green), fill: 'origin', data: mod.roc.fpr.map((x, i) => ({ x, y: mod.roc.tpr[i] })) },
      { label: 'Chance', showLine: true, pointRadius: 0, borderDash: [6, 6], borderColor: c.muted, borderWidth: 1, data: [{ x: 0, y: 0 }, { x: 1, y: 1 }] }] },
      options: { maintainAspectRatio: false, scales: { x: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'False-positive rate' } }, y: { type: 'linear', min: 0, max: 1, title: { display: true, text: 'True-positive rate (recall)' } } } } }; });
    FS.donut('c-donut', r.data_log.class_counts);
    const names = Object.keys(r.models);
    FS.chart('c-compare', () => { const c = FS.colors(); return { type: 'bar', data: { labels: names, datasets: [['precision', 'Precision', c.blue], ['recall', 'Recall', c.green], ['f1', 'F1', c.amber]].map(([k, l, col]) => ({ label: l, data: names.map(n => r.models[n].tuned[k] * 100), backgroundColor: col, borderRadius: 6 })) },
      options: { maintainAspectRatio: false, scales: FS.scales('Algorithm', 'Score (%)', { min: Math.max(0, Math.floor(Math.min(...names.map(n => r.models[n].tuned.precision * 100)) - 5)), max: 100 }) } }; });
    clear($('#top-features'), FS.rankBars(r.importance.permutation.items.slice(0, 5).map(i => ({ label: i.feature, value: Math.max(i.value, 0) }))));
  }

  function insights(r) {
    const b = r.models[r.best_model].tuned, [[, fp], [fn, tp]] = b.confusion_matrix, top = r.importance.permutation.items[0], li = (icon, tone, text) => el('li', {}, el('div', { class: 'kpi-icon tone-' + tone }, FS.icon(icon)), el('div', {}, text));
    clear($('#insights'),
      li('check', 'green', `${r.best_model} is the best model (F1 ${pct(b.f1)}), chosen by cross-validation on training data only.`),
      li('alert', 'orange', `It missed ${num(fn)} of ${num(fn + tp)} malware records and wrongly flagged ${num(fp)} benign ones.`),
      top ? li('eye', 'blue', `${top.feature} is the feature it relies on most. This is a pattern the model uses, not proof of cause.`) : null);
  }

  async function recent(r) {
    const box = $('#recent'), d = FS.data(), exp = FS.state.exp;
    if (!d || !d.samples.length) return FS.empty(box, 'Run `python -m src.evaluation.dashboard_data` to show live analyses here.');
    const ben = d.samples.filter(s => s.true_label === 'benign'), mal = d.samples.filter(s => s.true_label === 'malware'), picks = [];
    for (let i = 0; i < 4; i++) { if (ben[i]) picks.push(ben[i]); if (mal[i]) picks.push(mal[i]); }
    clear(box, el('div', { class: 'sk', style: 'height:150px' }));
    try {
      if (!FS.state.recent[exp]) FS.state.recent[exp] = await FS.api(`/api/${exp}/predict`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ records: picks.map(s => s.features) }) });
      if (FS.state.exp !== exp) return;                      // user switched experiment while waiting
      const preds = FS.state.recent[exp].predictions;
      clear(box, FS.table(['Record', 'True label', 'Predicted', 'Malware probability', 'Result'],
        picks.map((s, i) => { const p = preds[i].malware_probability, [text, tone] = RESULT(s.true_label, p);
          return [s.id, FS.pill(s.true_label, s.true_label === 'malware' ? 'red' : 'green'), preds[i].label, pct(p), FS.pill(text, tone)]; }),
        { numeric: [3], onRow: i => FS.detect.analyse(picks[i]) }));
    } catch (e) { FS.empty(box, e.message); }
  }

  FS.views.dashboard = { render() {
    const r = FS.res(); if (!r) return ['#kpis', '#recent', '#insights'].forEach(s => FS.empty($(s), 'No results yet. Train the models first (see the README).'));
    kpis(r); charts(r); insights(r); return recent(r);
  } };
})();
