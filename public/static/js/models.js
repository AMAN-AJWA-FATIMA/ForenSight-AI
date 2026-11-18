/* Models view: comparison table, ROC / PR curves, confusion matrices and a train-vs-test reliability check. */
(() => {
  const { el, clear, pct, num, $ } = FS;
  const METRICS = [['accuracy', 'Accuracy'], ['precision', 'Precision'], ['recall', 'Recall'], ['f1', 'F1'], ['false_positive_rate', 'FPR'], ['roc_auc', 'ROC-AUC']];

  function confusion(name, cm) {
    const [[tn, fp], [fn, tp]] = cm, c = (v, label, k) => el('div', { class: k }, el('b', {}, num(v)), el('small', {}, label));
    return el('div', { class: 'card' }, el('h3', {}, name), el('div', { class: 'cm' }, el('div', { class: 'h' }), el('div', { class: 'h' }, 'Pred. benign'), el('div', { class: 'h' }, 'Pred. malware'),
      el('div', { class: 'h' }, 'True benign'), c(tn, 'correct', 'good'), c(fp, 'false alarms', 'bad'), el('div', { class: 'h' }, 'True malware'), c(fn, 'missed', 'bad'), c(tp, 'caught', 'good')));
  }

  FS.views.models = { render() {
    const r = FS.res(); if (!r) return FS.empty($('#model-table'), 'No results yet. Train the models first (see the README).');
    const names = Object.keys(r.models), best = r.models[r.best_model];
    clear($('#model-table'), FS.table(['Model', 'Baseline F1', ...METRICS.map(m => m[1] + ' (tuned)')], names.map(n => [n + (n === r.best_model ? ' ★' : ''), pct(r.models[n].baseline.f1), ...METRICS.map(([k]) => pct(r.models[n].tuned[k]))]),
      { sel: names.indexOf(r.best_model), numeric: [1, 2, 3, 4, 5, 6, 7] }));
    $('#model-note').textContent = `★ selected by ${r.selection_rule}; the test set was used once. Missing malware (low recall) is usually costlier than an extra manual review (higher FPR).`;
    const prev = r.test_class_counts.malware / (r.test_class_counts.malware + r.test_class_counts.benign);
    FS.curveChart('c-m-roc', r.models, 'roc', 'fpr', 'tpr', 'False-positive rate', 'True-positive rate (recall)', { label: 'Chance', data: [{ x: 0, y: 0 }, { x: 1, y: 1 }] });
    FS.curveChart('c-m-pr', r.models, 'pr', 'recall', 'precision', 'Recall', 'Precision', { label: 'No skill', data: [{ x: 0, y: prev }, { x: 1, y: prev }] });
    clear($('#cms'), ...names.map(n => confusion(n, r.models[n].tuned.confusion_matrix)));
    const tr = best.train, te = best.tuned, gap = (tr.f1 - te.f1) * 100;
    clear($('#reliability'), FS.table(['Metric', 'Training', 'Test', 'Gap'], [['accuracy', 'Accuracy'], ['precision', 'Precision'], ['recall', 'Recall'], ['f1', 'F1']].map(([k, l]) => [l, pct(tr[k]), pct(te[k]), ((tr[k] - te[k]) * 100).toFixed(1) + ' pp']), { numeric: [1, 2, 3] }));
    $('#reliability-note').textContent = `Training scores use up to 30,000 training records. ` + (gap > 2 ? `The ${gap.toFixed(1)} pp F1 gap suggests some overfitting, so trust the test score.` : `The gap is small (${gap.toFixed(1)} pp), with no strong sign of overfitting on this split.`);
  } };
})();
