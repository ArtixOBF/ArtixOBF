/* CampaignFlow UI behaviour: selection bars, filters, search, toasts, shortcuts.
   All handlers are delegated on document so they survive hx-boost page swaps. */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };

  const FILTERS = {
    all: () => true,
    ready: (s) => s === 'ready' || s === 'gate-ready',
    waiting: (s) => ['waiting', 'gate-upcoming', 'needs-info'].includes(s),
    committed: (s) => s === 'committed',
    done: (s) => s === 'done',
  };

  function updateBulk() {
    const bar = $('#bulkbar');
    if (!bar) return;
    const n = $$('#bulk input[name=ids]:checked').length;
    bar.classList.toggle('show', n > 0);
    $('[data-count]', bar).textContent = n;
  }

  function updateAccept() {
    const out = $('[data-accept-count]');
    if (out) out.textContent = $$('#accept-form input[name=ids]:checked').length;
  }

  function applyFilter() {
    const box = $('#bulk');
    if (!box) return;
    const active = $('.segmented [data-filter].on')?.dataset.filter || 'all';
    const q = ($('[data-search]')?.value || '').trim().toLowerCase();
    let anyVisible = false;
    $$('details[data-group-box]', box).forEach((group) => {
      const head = $('.group-head', group).textContent.toLowerCase();
      let visible = 0;
      $$('tbody tr', group).forEach((tr) => {
        const ok = FILTERS[active](tr.dataset.state) &&
          (!q || tr.textContent.toLowerCase().includes(q) || head.includes(q));
        tr.hidden = !ok;
        if (ok) visible++;
      });
      const filtering = active !== 'all' || q;
      group.hidden = filtering && visible === 0;
      $('.group-empty', group).hidden = visible > 0 || filtering;
      if (visible) anyVisible = true;
    });
    const empty = $('.filter-empty', box);
    if (empty) empty.hidden = anyVisible || !$$('details[data-group-box]', box).length;
  }

  function init() {
    // Restore the last task filter.
    const saved = store.get('cf-filter');
    if (saved && $(`.segmented [data-filter="${saved}"]`)) {
      $$('.segmented [data-filter]').forEach((b) => b.classList.toggle('on', b.dataset.filter === saved));
    }
    applyFilter();
    updateBulk();
    updateAccept();
    // Success toasts fade out; errors stay until dismissed.
    $$('.toast.ok').forEach((t) => setTimeout(() => dismiss(t), 4200));
  }

  function dismiss(toast) {
    toast.classList.add('leaving');
    setTimeout(() => toast.remove(), 200);
  }

  document.addEventListener('change', (e) => {
    const t = e.target;
    if (t.matches('[data-select-group]')) {
      $$(`input[name=ids][data-group="${t.dataset.selectGroup}"]`)
        .forEach((b) => { if (!b.closest('tr').hidden) b.checked = t.checked; });
    }
    if (t.matches('[data-select-all]')) {
      $$('#accept-form input[name=ids]').forEach((b) => { b.checked = t.checked; });
    }
    if (t.matches('.segmented input[type=radio]')) {
      $$('label', t.closest('.segmented')).forEach((l) => l.classList.toggle('on', l.contains(t)));
    }
    updateBulk();
    updateAccept();
  });

  document.addEventListener('click', (e) => {
    const f = e.target.closest('[data-filter]');
    if (f) {
      $$('[data-filter]', f.parentElement).forEach((b) => b.classList.toggle('on', b === f));
      store.set('cf-filter', f.dataset.filter);
      applyFilter();
    }
    if (e.target.closest('[data-clear]')) {
      $$('#bulk input[type=checkbox]').forEach((b) => { b.checked = false; });
      updateBulk();
    }
    const x = e.target.closest('.toast-x');
    if (x) dismiss(x.closest('.toast'));
    if (e.target.closest('[data-shortcuts]')) $('#shortcuts')?.showModal();
    // Clicking a timeline bar flashes its row in the table.
    const bar = e.target.closest('.g-bar');
    if (bar) {
      const row = document.querySelector(bar.getAttribute('href'));
      if (row) {
        e.preventDefault();
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.animate([{ background: 'var(--brand-soft)' }, { background: 'transparent' }], { duration: 1400 });
      }
    }
  });

  document.addEventListener('input', (e) => {
    if (e.target.matches('[data-search]')) applyFilter();
    if (e.target.matches('[data-picker-filter]')) {
      const q = e.target.value.trim().toLowerCase();
      $$('.pick', e.target.closest('.picker')).forEach((p) => { p.hidden = q && !p.dataset.pickText.includes(q); });
    }
  });

  document.addEventListener('keydown', (e) => {
    const typing = e.target.closest('input, select, textarea, [contenteditable]');
    if (e.key === 'Escape') {
      if (typing) e.target.blur();
      $$('#bulk input[type=checkbox]:checked').forEach((b) => { b.checked = false; });
      updateBulk();
      return;
    }
    if (typing || e.metaKey || e.ctrlKey || e.altKey) return;
    const go = { '1': '/today', '2': '/plan', '3': '/intake' }[e.key];
    if (go && location.pathname !== go) location.href = go;
    if (e.key === '/') { const s = $('[data-search]'); if (s) { e.preventDefault(); s.focus(); } }
    if (e.key === '?') $('#shortcuts')?.showModal();
  });

  document.addEventListener('htmx:beforeRequest', () => document.documentElement.classList.add('is-loading'));
  document.addEventListener('htmx:afterRequest', () => document.documentElement.classList.remove('is-loading'));
  document.addEventListener('htmx:afterSettle', init);
  document.addEventListener('DOMContentLoaded', init);
})();
