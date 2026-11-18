/* Splash: types the two lines, then opens the dashboard (automatically on the first visit of a browser session). */
(() => {
  const $ = s => document.querySelector(s), lines = [$('#l1'), $('#l2')], text = lines.map(l => l.textContent), go = $('#go'), bar = $('#bar'), caret = $('.caret');
  let seen = false; try { seen = sessionStorage.getItem('fs-seen'); sessionStorage.setItem('fs-seen', '1'); } catch (e) { /* storage may be blocked */ }
  const finish = () => { caret.remove(); go.classList.add('show'); if (!seen) { bar.classList.add('run'); setTimeout(() => { location.href = go.href; }, 2500); } };
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return finish();
  lines.forEach(l => { l.textContent = ''; });
  let n = 0, k = 0;
  const type = () => { const l = lines[n]; l.after(caret); l.textContent = text[n].slice(0, ++k);
    if (k < text[n].length) return setTimeout(type, 38);
    n++; k = 0; n < lines.length ? setTimeout(type, 400) : finish(); };
  setTimeout(type, 900);
})();
