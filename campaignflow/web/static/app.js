/* CampaignFlow UI behaviour.
   Handlers are delegated on document so they survive hx-boost page swaps. */
(() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* storage unavailable */ } },
  };

  // ---------- splash: once per browser session ----------
  if (document.documentElement.classList.contains('splash')) {
    try { sessionStorage.setItem('cf-seen', '1'); } catch { /* ignore */ }
    setTimeout(() => document.documentElement.classList.remove('splash'), reduced ? 0 : 2400);
  }

  // ---------- task filters & search (Today) ----------
  const FILTERS = {
    open: (s) => s !== 'done' && s !== 'gate-upcoming',   // hide external steps nobody can act on yet
    done: (s) => s === 'done',
    all: () => true,
  };

  function applyFilter() {
    const box = $('#bulk');
    if (!box) return;
    const active = $('.segmented [data-filter].on')?.dataset.filter || 'open';
    const q = ($('[data-search]')?.value || '').trim().toLowerCase();
    let any = false;
    $$('details[data-group-box]', box).forEach((group) => {
      const head = $('.group-head', group).textContent.toLowerCase();
      let visible = 0;
      $$('.task', group).forEach((row) => {
        const ok = FILTERS[active](row.dataset.state) &&
          (!q || row.textContent.toLowerCase().includes(q) || head.includes(q));
        row.hidden = !ok;
        if (ok) visible++;
      });
      group.hidden = visible === 0;
      if (visible) any = true;
    });
    const empty = $('.filter-empty', box);
    if (empty) empty.hidden = any || !$$('details[data-group-box]', box).length;
  }

  // ---------- selection bars ----------
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

  // ---------- numbers count up ----------
  function countUp(el) {
    const target = parseFloat(el.dataset.countTo);
    if (!isFinite(target) || reduced || target === 0) return;
    const decimals = (el.dataset.countTo.split('.')[1] || '').length;
    const start = performance.now();
    const dur = 700 + Math.min(target, 20) * 20;
    const delay = document.documentElement.classList.contains('splash') ? 1900 : 150;
    el.textContent = (0).toFixed(decimals);
    setTimeout(() => {
      const tick = (now) => {
        const t = Math.min(1, (now - start - delay) / dur);
        const eased = 1 - Math.pow(1 - Math.max(t, 0), 3);
        el.textContent = (target * eased).toFixed(decimals);
        if (t < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, 0);
  }

  // ---------- celebration when a plan is locked in ----------
  function confetti() {
    if (reduced) return;
    const colors = ['#5b5bd6', '#a15bd6', '#1f8a4c', '#f0a84a', '#2b6fd6', '#ff6b78'];
    const cx = innerWidth / 2, cy = innerHeight * 0.35;
    for (let i = 0; i < 70; i++) {
      const p = document.createElement('i');
      p.className = 'confetti';
      const angle = Math.random() * Math.PI * 2;
      const dist = 140 + Math.random() * 260;
      p.style.setProperty('--x0', `${cx}px`);
      p.style.setProperty('--y0', `${cy}px`);
      p.style.setProperty('--x1', `${cx + Math.cos(angle) * dist}px`);
      p.style.setProperty('--y1', `${cy + Math.sin(angle) * dist + 220}px`);
      p.style.setProperty('--r', `${(Math.random() * 2 - 1) * 720}deg`);
      p.style.background = colors[i % colors.length];
      p.style.animationDelay = `${Math.random() * 120}ms`;
      document.body.appendChild(p);
      setTimeout(() => p.remove(), 1700);
    }
  }

  function dismiss(toast) {
    toast.classList.add('leaving');
    setTimeout(() => toast.remove(), 200);
  }

  function init() {
    const saved = store.get('cf-filter2');
    if (saved && FILTERS[saved]) {
      $$('.segmented [data-filter]').forEach((b) => b.classList.toggle('on', b.dataset.filter === saved));
    }
    applyFilter();
    updateBulk();
    updateAccept();
    $$('[data-count-to]').forEach(countUp);
    $$('.toast.ok').forEach((t) => {
      if (/Committed/.test(t.textContent)) confetti();
      setTimeout(() => dismiss(t), 4200);
    });
  }

  // ---------- events ----------
  document.addEventListener('change', (e) => {
    const t = e.target;
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
      store.set('cf-filter2', f.dataset.filter);
      applyFilter();
    }
    if (e.target.closest('[data-clear]')) {
      $$('#bulk input[type=checkbox]').forEach((b) => { b.checked = false; });
      updateBulk();
    }
    const x = e.target.closest('.toast-x');
    if (x) dismiss(x.closest('.toast'));
    if (e.target.closest('[data-shortcuts]')) $('#shortcuts')?.showModal();
    // Close an open popover when clicking elsewhere.
    $$('details.popover[open]').forEach((d) => { if (!d.contains(e.target)) d.open = false; });
    // Clicking a timeline bar highlights its row.
    const bar = e.target.closest('.g-bar');
    if (bar) {
      const row = document.querySelector(bar.getAttribute('href'));
      if (row) {
        e.preventDefault();
        row.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
        row.animate([{ background: 'var(--brand-soft)' }, { background: 'transparent' }], { duration: 1400 });
      }
    }
  });

  // Cursor spotlight on cards.
  document.addEventListener('pointermove', (e) => {
    const card = e.target.closest?.('.spot');
    if (!card) return;
    const r = card.getBoundingClientRect();
    card.style.setProperty('--mx', `${e.clientX - r.left}px`);
    card.style.setProperty('--my', `${e.clientY - r.top}px`);
  }, { passive: true });

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
