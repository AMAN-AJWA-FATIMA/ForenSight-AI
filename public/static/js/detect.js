/* Detect view: analyse a held-out test record, typed features or a CSV with the saved model. */
(() => {
  const { el, clear, pct, $ } = FS;

  function renderResult(box, data, truth) {
    const p = data.predictions[0], mal = p.malware_probability >= 0.5, meter = el('i');
    requestAnimationFrame(() => requestAnimationFrame(() => { meter.style.width = p.malware_probability * 100 + '%'; }));
    const nodes = [el('div', { class: 'row-inline' }, FS.radar(p.malware_probability, 84), el('span', { class: 'verdict glow sev-' + FS.sev(p.malware_probability).k + (mal ? ' mal' : ' ben') }, mal ? 'Potentially malicious' : 'Likely benign'),
        FS.pill('Threat level: ' + FS.sev(p.malware_probability).t, ({ low: 'green', elev: 'amber' })[FS.sev(p.malware_probability).k] || 'red'),
        truth ? FS.pill(`True label: ${truth} · ${(mal ? 'malware' : 'benign') === truth ? 'correct' : 'incorrect'}`, (mal ? 'malware' : 'benign') === truth ? 'green' : 'red') : null),
      el('p', {}, `Malware probability ${pct(p.malware_probability)} · ${data.model}`), el('div', { class: 'meter' }, meter),
      el('p', { class: 'muted' }, 'This is the model’s score, not a certainty. Values near 50% are uncertain.')];
    if (data.partial_input) nodes.push(el('p', { class: 'muted' }, `${data.n_features_filled_with_median} features were not supplied and use the training median.`));
    if (p.explanation && p.explanation.length) nodes.push(el('h3', {}, 'Features behind this result'), el('p', { class: 'muted' }, 'Red pushes towards malware, green towards benign.'),
      FS.contribBars(p.explanation.map(x => ({ label: `${x.feature} = ${x.value}`, value: x.contribution }))));
    if (data.n_rows > 1) nodes.push(el('h3', {}, `All rows (${data.n_rows}${data.n_rows > 50 ? ', first 50 shown' : ''})`), el('div', { class: 'table-wrap' }, FS.table(['Row', 'Label', 'Malware probability'], data.predictions.slice(0, 50).map(x => [x.row + 1, x.label, pct(x.malware_probability)]), { numeric: [2] })));
    nodes.push(el('p', { class: 'muted' }, data.disclaimer)); clear(box, nodes);
  }

  async function run(opts, truth, btn) {
    FS.alert(''); if (btn) btn.disabled = true; const exp = FS.state.exp, pr = FS.progress();
    clear($('#detect-result'), el('div', { class: 'scan' }, FS.radar(null, 150), el('p', { class: 'muted' }, 'Running model inference…'), pr.node));
    try { const data = await FS.api(`/api/${exp}/predict`, opts); pr.done(); await new Promise(r => setTimeout(r, 400)); FS.state.last[exp] = { data, truth }; FS.markDirty('explain'); renderResult($('#detect-result'), data, truth); }
    catch (e) { pr.done(); FS.alert(e.message); FS.empty($('#detect-result'), 'The analysis did not finish.'); } finally { if (btn) btn.disabled = false; }
  }
  const json = body => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  function setTab(name) { FS.$$('#detect-tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === name)); FS.$$('.pane').forEach(p => p.classList.toggle('on', p.id === 'pane-' + name)); }
  function fillForm(f) { FS.$$('#feature-inputs input').forEach(i => { const v = f[i.dataset.name]; if (v == null) return; if (i.type === 'checkbox') i.checked = v >= .5; else i.value = v; }); }

  function analyse(sample) {                       // used by the dashboard table
    FS.go('detect'); setTab('record'); fillForm(sample.features);
    return run(json({ features: sample.features }), sample.true_label);
  }

  async function render() {
    const d = FS.data(), picker = $('#picker'); clear(picker);
    if (d && d.samples.length) {
      const sel = el('select', { 'aria-label': 'Choose a test record' }, d.samples.map((s, i) => el('option', { value: i }, `Record ${i + 1} · ${s.id}`))), btn = el('button', { class: 'btn', type: 'button' }, 'Analyse record');
      btn.addEventListener('click', () => { const s = d.samples[+sel.value]; fillForm(s.features); run(json({ features: s.features }), s.true_label, btn); });
      picker.append(sel, btn);
    } else picker.append(el('span', { class: 'muted' }, 'Run `python -m src.evaluation.dashboard_data` to load test records.'));
    const exp = FS.state.exp, holder = $('#feature-inputs');
    if (!FS.state.schema[exp]) { try { FS.state.schema[exp] = await FS.api(`/api/${exp}/schema`); } catch (e) { return FS.empty(holder, e.message); } }
    const sc = FS.state.schema[exp], binary = exp === 'static';
    $('#form-help').textContent = binary ? 'Tick the permissions and API calls the app uses. Unticked features count as absent.' : 'Enter the flow values you know. Blank fields use the training median.';
    clear(holder, ...sc.top_features.map(f => { const id = 'f-' + f.replace(/\W/g, '_');
      return binary ? el('label', { class: 'field check', for: id }, el('input', { type: 'checkbox', id, 'data-name': f }), f)
        : el('label', { class: 'field', for: id }, f, el('input', { type: 'number', step: 'any', id, 'data-name': f, placeholder: 'median ' + sc.background[f] }), el('small', {}, `training range ${sc.feature_stats[f].min} to ${sc.feature_stats[f].max}`)); }));
    const last = FS.state.last[exp]; if (last) renderResult($('#detect-result'), last.data, last.truth); else FS.empty($('#detect-result'), 'Run an analysis to see the verdict and the features behind it.');
  }

  FS.tabs($('#detect-tabs'), name => setTab(name));
  $('#feature-form').addEventListener('submit', ev => {
    ev.preventDefault(); const features = {}, binary = FS.state.exp === 'static';
    for (const i of FS.$$('#feature-inputs input')) {
      if (binary) features[i.dataset.name] = i.checked ? 1 : 0;
      else if (i.value.trim() !== '') { const v = Number(i.value); if (!Number.isFinite(v)) return FS.alert(`"${i.dataset.name}" must be a number.`); features[i.dataset.name] = v; }
    }
    if (!Object.keys(features).length) return FS.alert('Enter at least one value first.');
    run(json({ features }), null, ev.submitter);
  });
  $('#form-reset').addEventListener('click', () => FS.$$('#feature-inputs input').forEach(i => { if (i.type === 'checkbox') i.checked = false; else i.value = ''; }));
  $('#csv-form').addEventListener('submit', ev => {
    ev.preventDefault(); const f = $('#csv-file').files[0];
    if (!f) return FS.alert('Choose a CSV file first.'); if (!f.name.toLowerCase().endsWith('.csv')) return FS.alert('Only .csv files are accepted.');
    if (f.size > 25 * 1024 * 1024) return FS.alert('File is larger than 25 MB.');
    const fd = new FormData(); fd.append('file', f); run({ method: 'POST', body: fd }, null, ev.submitter);
  });

  FS.detect = { analyse, renderResult };
  FS.views.detect = { render };
})();
