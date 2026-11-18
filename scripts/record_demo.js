/* Records CampaignFlow demo videos with Playwright.

   Usage (server must be running on :5000):
     node scripts/record_demo.js            # writes raw .webm clips to docs/videos/raw/
     bash scripts/make_videos.sh            # converts to .mp4 and builds the full demo

   Each clip starts from fresh demo data. A fake cursor, click ripples, a
   caption bar and a title card are injected so viewers can follow along. */

const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = process.env.CF_URL || 'http://127.0.0.1:5000';
const OUT = path.resolve(__dirname, '..', 'docs', 'videos', 'raw');
const W = 1440, H = 900;

// Overlay lives on <html>, outside <body>, so hx-boost body swaps keep it.
const OVERLAY = () => {
  const css = `
    #demo-cursor { position: fixed; z-index: 2147483647; width: 22px; height: 22px; pointer-events: none;
      left: 0; top: 0; transform: translate(-3px, -2px); transition: transform .05s; filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
    .demo-ripple { position: fixed; z-index: 2147483646; width: 36px; height: 36px; margin: -18px 0 0 -18px; border-radius: 50%;
      border: 3px solid rgba(91,91,214,.85); pointer-events: none; animation: demo-rip .55s ease-out forwards; }
    @keyframes demo-rip { from { transform: scale(.3); opacity: 1; } to { transform: scale(1.6); opacity: 0; } }
    #demo-cap { position: fixed; z-index: 2147483645; left: 50%; bottom: 28px; transform: translateX(-50%) translateY(20px);
      max-width: 900px; padding: 14px 22px; border-radius: 14px; background: rgba(17,17,24,.92); color: #fff;
      font: 500 19px/1.4 Inter, system-ui, sans-serif; letter-spacing: -.01em; text-align: center; opacity: 0;
      box-shadow: 0 12px 40px rgba(0,0,0,.35); transition: opacity .3s, transform .3s; pointer-events: none; }
    #demo-cap.on { opacity: 1; transform: translateX(-50%) translateY(0); }
    #demo-cap b { color: #b3b3ff; font-weight: 600; }
    #demo-title { position: fixed; inset: 0; z-index: 2147483644; display: grid; place-items: center; pointer-events: none;
      background: radial-gradient(900px 500px at 50% 40%, #2a2a6a, #0e0e14 70%); color: #fff; opacity: 0; transition: opacity .45s; }
    #demo-title.on { opacity: 1; }
    #demo-title .k { font: 600 14px Inter, system-ui; letter-spacing: .14em; text-transform: uppercase; color: #9d9dff; text-align: center; }
    #demo-title .t { font: 700 52px/1.1 Inter, system-ui; letter-spacing: -.03em; margin: 12px 0 10px; text-align: center; }
    #demo-title .s { font: 400 20px Inter, system-ui; color: #b8b8c8; text-align: center; max-width: 760px; }`;
  const mount = () => {
    if (document.getElementById('demo-cursor')) return;
    const st = document.createElement('style'); st.textContent = css; document.documentElement.appendChild(st);
    const c = document.createElement('div'); c.id = 'demo-cursor';
    c.innerHTML = '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.6-7.6L20 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    const cap = document.createElement('div'); cap.id = 'demo-cap'; document.documentElement.appendChild(cap);
    const t = document.createElement('div'); t.id = 'demo-title'; document.documentElement.appendChild(t);
    const pos = JSON.parse(sessionStorage.getItem('demo-pos') || '[720,450]');
    c.style.left = pos[0] + 'px'; c.style.top = pos[1] + 'px';
    window.addEventListener('mousemove', (e) => {
      c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      sessionStorage.setItem('demo-pos', JSON.stringify([e.clientX, e.clientY]));
    }, true);
    window.addEventListener('mousedown', (e) => {
      const r = document.createElement('div'); r.className = 'demo-ripple';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
      document.documentElement.appendChild(r); setTimeout(() => r.remove(), 600);
      c.style.transform = 'translate(-3px,-2px) scale(.85)';
    }, true);
    window.addEventListener('mouseup', () => { c.style.transform = 'translate(-3px,-2px)'; }, true);
    window.__cap = (html) => {
      const el = document.getElementById('demo-cap');
      if (!html) { el.classList.remove('on'); sessionStorage.removeItem('demo-cap'); return; }
      el.innerHTML = html; el.classList.add('on');
      sessionStorage.setItem('demo-cap', html);
    };
    window.__title = (k, t, s) => {
      const el = document.getElementById('demo-title');
      if (!t) { el.classList.remove('on'); return; }
      el.innerHTML = `<div><div class="k">${k}</div><div class="t">${t}</div><div class="s">${s || ''}</div></div>`;
      el.classList.add('on');
    };
    // Keep the caption visible across full page loads.
    const saved = sessionStorage.getItem('demo-cap');
    if (saved) { cap.innerHTML = saved; cap.classList.add('on'); }
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function helpers(page) {
  const h = {
    async cap(text, hold = 0) { await page.evaluate((t) => window.__cap(t), text); if (hold) await sleep(hold); },
    async title(k, t, s, hold = 2600) {
      await page.evaluate(([a, b, c]) => window.__title(a, b, c), [k, t, s]);
      await sleep(hold);
      await page.evaluate(() => window.__title());
      await sleep(500);
    },
    async move(sel, opts = {}) {
      const loc = (typeof sel === 'string' ? page.locator(sel) : sel).first();
      await loc.scrollIntoViewIfNeeded();
      const b = await loc.boundingBox();
      const x = b.x + (opts.dx ?? b.width / 2), y = b.y + (opts.dy ?? b.height / 2);
      await page.mouse.move(x, y, { steps: opts.steps || 28 });
      await sleep(opts.pause ?? 250);
      return loc;
    },
    async click(sel, opts = {}) {
      await h.move(sel, opts);
      await page.mouse.down(); await sleep(90); await page.mouse.up();
      await sleep(opts.after ?? 900);
    },
    async type(sel, text) {
      await h.click(sel, { after: 200 });
      await page.keyboard.type(text, { delay: 55 });
      await sleep(300);
    },
    async scroll(dy, steps = 12) {
      for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await sleep(30); }
      await sleep(400);
    },
    async settle(ms = 1200) { await page.waitForLoadState('domcontentloaded'); await sleep(ms); },
  };
  return h;
}

async function resetDemo(browser) {
  const ctx = await browser.newContext();
  const res = await ctx.request.post(BASE + '/reset-demo');
  if (!res.ok()) throw new Error('reset failed: ' + res.status());
  await ctx.close();
}

async function record(browser, name, fn, { splash = false } = {}) {
  await resetDemo(browser);
  const ctx = await browser.newContext({
    viewport: { width: W, height: H },
    recordVideo: { dir: OUT, size: { width: W, height: H } },
  });
  await ctx.addInitScript(OVERLAY);
  if (!splash) await ctx.addInitScript(() => sessionStorage.setItem('cf-seen', '1'));
  await ctx.addInitScript(() => { try { localStorage.setItem('cf-filter2', 'open'); } catch (e) {} });
  const page = await ctx.newPage();
  const h = helpers(page);
  const t0 = Date.now();
  await fn(page, h);
  await sleep(600);
  const video = page.video();
  await ctx.close();
  const file = path.join(OUT, name + '.webm');
  await video.saveAs(file);
  await video.delete();
  console.log(`${name}: ${((Date.now() - t0) / 1000).toFixed(1)}s`);
}

// ------------------------------------------------------------------ scenes
const scenes = {
  async '01-daily-review'(page, h) {
    await page.goto(BASE + '/today');
    await sleep(2900);   // splash screen plays
    await h.title('CampaignFlow · 1 of 5', 'Daily review', 'Update only what changed, then let the planner do the rest.');
    await h.cap('Each morning starts on <b>Today</b>: what is ready, what is due, and who is in.', 2600);
    await h.move('.stats .stat:nth-child(1)'); await h.move('.stats .stat:nth-child(2)'); await h.move('.stats .stat:nth-child(3)');
    await sleep(600);
    await h.cap('The <b>“needs you”</b> box asks simple yes/no questions instead of a long form.', 2200);
    await h.move('.attention');
    await sleep(800);
    await h.cap('The client approved the script, so we confirm that external step…', 1200);
    await h.click('.attention li:nth-child(1) button', { after: 1800 });
    await h.settle(800);
    await h.cap('…and Ely is in today, so the planner can now give Ely work.', 1200);
    await h.click('.attention li:first-child button', { after: 1800 });
    await h.settle(1200);
    await h.cap('Done work and future external steps are hidden, so the list stays short.', 1600);
    await h.click('[data-filter="done"]', { after: 1300 });
    await h.click('[data-filter="all"]', { after: 1300 });
    await h.click('[data-filter="open"]', { after: 1000 });
    await h.cap('Search filters instantly across every campaign.', 600);
    await h.type('[data-search]', 'edit');
    await sleep(1600);
    await page.fill('[data-search]', ''); await page.dispatchEvent('[data-search]', 'input');
    await h.cap('Tick several tasks and a bulk-action bar slides up.', 600);
    await h.click('input[name=ids][value="C3-1"]', { after: 400 });
    await h.click('input[name=ids][value="C4-1"]', { after: 1500 });
    await h.move('#bulkbar', { pause: 1200 });
    await page.keyboard.press('Escape');
    await sleep(800);
    await h.cap('Now everything is up to date. Time to plan the day.', 1400);
    await h.click('a.btn-glow', { after: 2200 });
    await h.cap('');
  },

  async '02-plan-and-compare'(page, h) {
    await page.goto(BASE + '/today'); await sleep(400);
    await h.title('CampaignFlow · 2 of 5', 'Plan the day', 'A min-heap ranks ready work; a greedy allocator fills each person\'s free time.');
    await h.click('a[href="/plan"]', { after: 2200 });
    await h.cap('One sentence sums up the plan: <b>6 tasks, all on time</b>.', 2400);
    await h.move('.hero-title', { pause: 600 });
    await h.cap('The timeline shows who does what, around meetings and lunch.', 1200);
    for (const sel of ['.g-bar.prop >> nth=0', '.g-bar.prop >> nth=1', '.g-bar.prop >> nth=3']) {
      await h.move(sel, { pause: 900 });
    }
    await h.cap('Our proposal compares two rules on the same data. Switch to <b>order received</b>…', 1400);
    await h.click('.segmented label:has-text("Order received")', { after: 2600 });
    await h.cap('…and the banner due at 12:00 is now <b>late</b>: it waits behind earlier requests.', 1200);
    await h.move('.g-bar.risk', { pause: 1600 });
    await h.move('.hero-title', { pause: 1600 });
    await h.cap('Prioritising by <b>deadline</b> avoids that late task.', 800);
    await h.click('.segmented label:has-text("Deadline")', { after: 2400 });
    await h.cap('Anything that cannot start today is listed with a plain reason.', 600);
    await h.scroll(420);
    await h.move('.reasons li:nth-child(1)', { pause: 900 });
    await h.move('.reasons li:nth-child(2)', { pause: 900 });
    await h.move('.reasons li:nth-child(3)', { pause: 1400 });
    await h.cap('');
  },

  async '03-lock-in'(page, h) {
    await page.goto(BASE + '/plan'); await sleep(400);
    await h.title('CampaignFlow · 3 of 5', 'Lock in the plan', 'Accepted work becomes a commitment that replanning never moves.');
    await h.cap('Untick anything you do not want today…', 400);
    await h.scroll(380);
    await h.click('#accept-form li:nth-child(6) input', { after: 1400 });
    await h.cap('…then press <b>Lock in plan</b>.', 400);
    await h.click('#accept-form button.btn-primary', { after: 2600 });
    await h.cap('Locked work shows in purple. The unticked task is offered again.', 400);
    await page.mouse.wheel(0, -2000); await sleep(800);
    await h.move('.g-bar.lock >> nth=0', { pause: 900 });
    await h.move('.g-bar.prop', { pause: 1600 });
    await h.cap('Changed your mind? <b>Unlock</b> releases a commitment.', 400);
    await h.scroll(700);
    await h.click('.schedule.locked form button', { after: 1500 });
    await h.settle(800);
    await page.mouse.wheel(0, -2000); await sleep(900);
    await h.cap('The unlocked task goes straight back into the recommended plan.', 3200);
    await h.cap('');
  },

  async '04-new-campaign'(page, h) {
    await page.goto(BASE + '/intake'); await sleep(400);
    await h.title('CampaignFlow · 4 of 5', 'New campaign in seconds', 'Templates create the steps, links between them and time estimates.');
    await h.cap('Pick a template. Its steps are shown as a pipeline; flags are external steps.', 600);
    await h.move('label.template:nth-child(1)', { pause: 800 });
    await h.click('label.template:has-text("Social media set")', { after: 700 });
    await h.cap('Fill in the client, a name and the deadline.', 300);
    await h.type('#c-client', 'Halo Halo Hub');
    await h.type('#c-name', 'Holiday reels');
    await h.click('#c-deadline', { after: 200 });
    await page.fill('#c-deadline', '2026-11-25T17:00'); await sleep(600);
    await h.click('form[action="/campaigns"] button.btn-primary', { after: 2000 });
    await h.cap('The new campaign appears on Today with every step ready to plan.', 400);
    await h.scroll(1400);
    await h.move(page.locator('details.group:has-text("Holiday reels")'), { pause: 2400 });
    await h.cap('When a client asks for changes, a revision round is added: <b>no loops, no reopened work</b>.', 400);
    await h.click('[data-filter="all"]', { after: 900 });
    const row = page.locator('details.group:has-text("Holiday reels") li.task:has-text("Client review")').first();
    await h.move(row, { pause: 500 });
    await h.click(row.locator('button[title="Client asked for changes"]'), { after: 2000 });
    await h.scroll(1400);
    await h.move(page.locator('details.group:has-text("Holiday reels") li.task:has-text("Revision 1")'), { pause: 2400 });
    await h.cap('');
  },

  async '05-cycle-detection'(page, h) {
    await page.goto(BASE + '/today'); await sleep(400);
    await h.title('CampaignFlow · 5 of 5', 'Safe by design', 'Depth-first search rejects impossible circular dependencies.');
    await h.cap('Let\'s try to break it: make <b>Article draft</b> wait for its own copy edit.', 400);
    await h.scroll(900);
    const row = page.locator('li.task:has(input[value="C4-1"])');
    await h.move(row, { pause: 400 });
    await h.click(row.locator('a[title="Edit"]'), { after: 1600 });
    await h.type('[data-picker-filter]', 'copy');
    await h.click('input[name=prereqs][value="C4-2"]', { after: 900 });
    await h.cap('Save, and the DFS cycle check finds the loop before it can reach the planner.', 400);
    await h.click('button:has-text("Save changes")', { after: 3200 });
    await h.move('.toast', { pause: 2600 });
    await h.cap('The error names the exact loop, and nothing was saved.', 2400);
    await h.cap('');
  },
};

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const only = process.argv.slice(2);
  for (const [name, fn] of Object.entries(scenes)) {
    if (only.length && !only.includes(name)) continue;
    await record(browser, name, fn, { splash: name === '01-daily-review' });
  }
  await browser.close();
})();
