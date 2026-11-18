/* Explainability view: global importance plus the explanation of the latest analysis. */
(() => {
  const { clear, $ } = FS;
  FS.views.explain = { render() {
    const r = FS.res(); if (!r) return FS.empty($('#explain-note'), 'No results yet. Train the models first (see the README).');
    clear($('#explain-note'), 'Importance shows what the model relies on. It does not show what causes malware. Methods used: model importance, permutation importance and per-prediction occlusion. SHAP and LIME are not used.');
    $('#imp-native-sub').textContent = `${r.best_model}: ${r.importance.native.kind}`; $('#imp-perm-sub').textContent = r.importance.permutation.kind;
    FS.hbar('c-imp-native', r.importance.native.items.slice(0, 10), 'Importance', FS.colors().blue);
    FS.hbar('c-imp-perm', r.importance.permutation.items.slice(0, 10), 'Drop in F1', FS.colors().green);
    const last = FS.state.last[FS.state.exp];
    if (last) FS.detect.renderResult($('#explain-local'), last.data, last.truth);
    else FS.empty($('#explain-local'), 'No analysis yet. Open Detect, or click a record on the dashboard.');
  } };
})();
