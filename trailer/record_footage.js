/* Record high-quality app footage for the trailer.

   Uses Chrome's screencast stream (sharp JPEG frames + timestamps) instead of
   the low-bitrate video recorder, and logs zoom targets (element boxes at a
   given moment) so the trailer camera can push in on them.

   Usage (app running on :5000):  node trailer/record_footage.js [clip ...]
   Output: trailer/build/footage/<clip>/NNNNN.jpg + meta.json */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const BASE = process.env.CF_URL || 'http://127.0.0.1:5000';
const OUT = path.resolve(__dirname, 'build', 'footage');
const VW = 1440, VH = 900, DSF = 1.5;

const CURSOR = () => {
  const mount = () => {
    if (document.getElementById('fx-cursor')) return;
    const st = document.createElement('style');
    st.textContent = `#fx-cursor{position:fixed;z-index:2147483647;left:0;top:0;pointer-events:none;
        transform:translate(-3px,-2px);filter:drop-shadow(0 3px 4px rgba(0,0,0,.35))}
      .fx-rip{position:fixed;z-index:2147483646;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%;
        border:3px solid rgba(124,124,240,.95);pointer-events:none;animation:fxr .6s ease-out forwards}
      @keyframes fxr{from{transform:scale(.3);opacity:1}to{transform:scale(1.7);opacity:0}}`;
    document.documentElement.appendChild(st);
    const c = document.createElement('div'); c.id = 'fx-cursor';
    c.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26"><path d="M3 2l7 19 2.6-7.6L20 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    const p = JSON.parse(sessionStorage.getItem('fx-pos') || '[1100,600]');
    c.style.left = p[0] + 'px'; c.style.top = p[1] + 'px';
    addEventListener('mousemove', (e) => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px';
      sessionStorage.setItem('fx-pos', JSON.stringify([e.clientX, e.clientY])); }, true);
    addEventListener('mousedown', (e) => { const r = document.createElement('div'); r.className = 'fx-rip';
      r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px'; document.documentElement.appendChild(r);
      setTimeout(() => r.remove(), 650); }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount); else mount();
};

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function newPage(browser) {
  const ctx = await browser.newContext({ viewport: { width: VW, height: VH }, deviceScaleFactor: DSF });
  await ctx.addInitScript(CURSOR);
  await ctx.addInitScript(() => { sessionStorage.setItem('cf-seen', '1'); try { localStorage.setItem('cf-filter2', 'open'); } catch (e) {} });
  return { ctx, page: await ctx.newPage() };
}

async function reset(browser) {
  const ctx = await browser.newContext();
  await ctx.request.post(BASE + '/reset-demo');
  await ctx.close();
}

async function capture(page, name, fn) {
  const dir = path.join(OUT, name);
  fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  const marks = [];
  let t0 = null;
  cdp.on('Page.screencastFrame', ({ data, metadata, sessionId }) => {
    if (t0 === null) t0 = metadata.timestamp;
    const file = String(frames.length).padStart(5, '0') + '.jpg';
    fs.writeFileSync(path.join(dir, file), Buffer.from(data, 'base64'));
    frames.push(+(metadata.timestamp - t0).toFixed(4));
    cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
  });
  const startWall = Date.now();
  await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 90, maxWidth: VW * DSF, maxHeight: VH * DSF, everyNthFrame: 1 });
  // Keep pixels changing so the stream never stalls during holds.
  await page.evaluate(() => { const d = document.createElement('i'); d.id = 'fx-tick';
    d.style.cssText = 'position:fixed;left:0;top:0;width:1px;height:1px;z-index:2147483647;pointer-events:none';
    document.documentElement.appendChild(d); let n = 0; setInterval(() => { d.style.background = (n++ % 2) ? 'rgba(0,0,0,.004)' : 'rgba(0,0,0,.006)'; }, 16); });

  const now = () => (Date.now() - startWall) / 1000;
  const h = {
    async mark(label, sel, pad = 12) {
      const loc = (typeof sel === 'string' ? page.locator(sel) : sel).first();
      const b = await loc.boundingBox();
      if (!b) throw new Error('no box for ' + label);
      marks.push({ label, t: +now().toFixed(3), x: (b.x - pad) / VW, y: (b.y - pad) / VH, w: (b.width + 2 * pad) / VW, h: (b.height + 2 * pad) / VH });
    },
    async move(sel, opt = {}) {
      const loc = (typeof sel === 'string' ? page.locator(sel) : sel).first();
      await loc.scrollIntoViewIfNeeded();
      const b = await loc.boundingBox();
      await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2, { steps: opt.steps || 22 });
      await sleep(opt.pause ?? 200);
    },
    async click(sel, opt = {}) {
      await h.move(sel, opt);
      await page.mouse.down(); await sleep(80); await page.mouse.up();
      await sleep(opt.after ?? 800);
    },
    async type(sel, text) { await h.click(sel, { after: 120 }); await page.keyboard.type(text, { delay: 38 }); },
    async scrollBy(dy, steps = 14) { for (let i = 0; i < steps; i++) { await page.mouse.wheel(0, dy / steps); await sleep(22); } await sleep(250); },
    sleep,
  };
  await fn(page, h);
  await sleep(300);
  await cdp.send('Page.stopScreencast');
  await sleep(200);
  const meta = { name, frames, duration: frames[frames.length - 1], width: VW * DSF, height: VH * DSF, marks };
  fs.writeFileSync(path.join(dir, 'meta.json'), JSON.stringify(meta));
  console.log(`${name}: ${frames.length} frames, ${meta.duration.toFixed(1)}s, ${(frames.length / meta.duration).toFixed(1)} fps, marks: ${marks.map((m) => m.label).join(', ')}`);
}

const CLIPS = {
  async daily(page, h) {
    await page.goto(BASE + '/today'); await sleep(1300);
    await h.mark('attn', '.attention');
    await h.move('.attention li:nth-child(1) button', { pause: 350 });
    await h.mark('yes1', '.attention li:nth-child(1)');
    await h.click('.attention li:nth-child(1) button', { after: 1400 });
    await h.mark('attn2', '.attention');
    await h.click('.attention li:first-child button', { after: 1500 });
    await h.mark('attn3', '.rail .card');
    await h.move('li.task:has(input[value="C2-4"])', { pause: 500 });
    await h.mark('tasks', '#bulk');
    await h.move('li.task:has(input[value="T1"])', { pause: 900 });
  },
  async plan(page, h) {
    await page.goto(BASE + '/today'); await sleep(900);
    await h.click('a[href="/plan"]', { after: 400 });
    await page.waitForSelector('.hero'); await sleep(200);
    await h.mark('hero', '.hero');
    await h.mark('gantt', '.gantt');
    await sleep(1800);
    await h.move('.g-bar.prop >> nth=0', { pause: 500 });
    await h.move('.g-bar.prop >> nth=4', { pause: 700 });
  },
  async switch(page, h) {
    await page.goto(BASE + '/plan'); await sleep(1600);
    await h.mark('toggle', '.plan-settings .segmented');
    await h.click('.segmented label:has-text("Order received")', { after: 300 });
    await page.waitForSelector('.g-bar.risk'); await sleep(900);
    await h.mark('hero', '.hero');
    await h.mark('risk', '.g-bar.risk', 40);
    await h.move('.g-bar.risk', { pause: 1600 });
    await h.mark('lane', page.locator('.g-row').nth(2), 4);
    await sleep(600);
  },
  async lock(page, h) {
    await page.goto(BASE + '/plan'); await sleep(1500);
    await h.scrollBy(330);
    await h.mark('schedule', '#accept-form');
    await h.move('#accept-form button.btn-primary', { pause: 450 });
    await h.mark('lockbtn', '#accept-form .acceptbar');
    await h.click('#accept-form button.btn-primary', { after: 300 });
    await page.waitForSelector('.schedule.locked'); await sleep(100);
    await h.mark('toast', '.toast', 6);
    await sleep(1400);
    await page.mouse.wheel(0, -2000); await sleep(700);
    await h.mark('hero', '.hero');
    await h.mark('gantt', '.gantt');
    await sleep(1600);
  },
  async campaign(page, h) {
    await page.goto(BASE + '/intake'); await sleep(1100);
    await h.mark('templates', '.templates');
    await h.click('label.template:has-text("Social media set")', { after: 500 });
    await h.type('#c-client', 'Halo Halo Hub');
    await h.type('#c-name', 'Holiday reels');
    await h.click('#c-deadline', { after: 100 });
    await page.fill('#c-deadline', '2026-11-25T17:00'); await sleep(350);
    await h.mark('form', 'form[action="/campaigns"]');
    await h.click('form[action="/campaigns"] button.btn-primary', { after: 300 });
    await page.waitForSelector('details.group:has-text("Holiday reels")'); await sleep(500);
    await h.scrollBy(1500, 18);
    await sleep(300);
    await h.mark('newgroup', 'details.group:has-text("Holiday reels")');
    await h.move('details.group:has-text("Holiday reels") li.task >> nth=0', { pause: 1200 });
  },
  async revise(page, h) {
    await page.goto(BASE + '/today'); await sleep(800);
    await h.click('[data-filter="all"]', { after: 500 });
    const group = 'details.group:has-text("Holiday reels")';
    await page.locator(group).scrollIntoViewIfNeeded(); await sleep(400);
    const row = page.locator(`${group} li.task:has-text("Client review")`).first();
    await h.move(row, { pause: 400 });
    await h.mark('review', row);
    await h.click(row.locator('button[title="Client asked for changes"]'), { after: 300 });
    await page.waitForSelector(`${group} li.task:has-text("Revision 1")`); await sleep(400);
    await page.locator(group).scrollIntoViewIfNeeded(); await sleep(300);
    await h.mark('revgroup', group);
    await h.move(page.locator(`${group} li.task:has-text("Revision 1")`), { pause: 1500 });
  },
  async cycle(page, h) {
    await page.goto(BASE + '/today'); await sleep(900);
    const row = page.locator('li.task:has(input[value="C4-1"])');
    await row.scrollIntoViewIfNeeded(); await sleep(300);
    await h.move(row, { pause: 300 });
    await h.click(row.locator('a[title="Edit"]'), { after: 300 });
    await page.waitForSelector('[data-picker-filter]'); await sleep(500);
    await h.type('[data-picker-filter]', 'copy'); await sleep(300);
    await h.mark('picker', '.picker');
    await h.click('input[name=prereqs][value="C4-2"]', { after: 500 });
    await h.click('button:has-text("Save changes")', { after: 200 });
    await page.waitForSelector('.toast.error'); await sleep(250);
    await h.mark('toast', '.toast.error', 10);
    await h.move('.toast.error', { pause: 2200 });
  },
};

(async () => {
  const only = process.argv.slice(2);
  const browser = await chromium.launch();
  let shared = null;
  for (const [name, fn] of Object.entries(CLIPS)) {
    if (only.length && !only.includes(name)) continue;
    // "revise" continues from "campaign" so the new campaign exists.
    if (name !== 'revise') { await reset(browser); if (shared) await shared.ctx.close(); shared = await newPage(browser); }
    else if (!shared) { shared = await newPage(browser); }
    await capture(shared.page, name, fn);
  }
  if (shared) await shared.ctx.close();
  await browser.close();
})();
