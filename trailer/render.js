/* Render the trailer frame by frame.

   node trailer/render.js                      -> build/video.mp4 (silent, full length)
   node trailer/render.js --fps 30 --from 20 --to 40
   node trailer/render.js --stills 3,9.5,24     -> build/stills/t003.0.jpg ...

   Files are served straight from the trailer folder through Playwright's
   request routing, so no web server is needed. */
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const BUILD = path.join(ROOT, 'build');
const args = Object.fromEntries(process.argv.slice(2).reduce((acc, a, i, all) => {
  if (a.startsWith('--')) acc.push([a.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]);
  return acc;
}, []));
const FPS = Number(args.fps || 60);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.jpg': 'image/jpeg', '.woff2': 'font/woff2', '.css': 'text/css' };

(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('pageerror', e.message));
  await page.route('http://trailer.local/**', async (route) => {
    const rel = decodeURIComponent(new URL(route.request().url()).pathname).replace(/^\/+/, '');
    const file = path.join(ROOT, rel);
    if (!file.startsWith(ROOT) || !fs.existsSync(file)) return route.fulfill({ status: 404, body: 'not found' });
    route.fulfill({ status: 200, body: fs.readFileSync(file), contentType: TYPES[path.extname(file)] || 'application/octet-stream' });
  });
  await page.goto('http://trailer.local/index.html');
  await page.waitForFunction(() => window.ready || window.renderError, null, { timeout: 60000 });
  const err = await page.evaluate(() => window.renderError);
  if (err) { console.error(err); process.exit(1); }
  const duration = await page.evaluate(() => window.TIMELINE.duration);

  if (args.stills) {
    const dir = path.join(BUILD, 'stills');
    fs.mkdirSync(dir, { recursive: true });
    for (const s of String(args.stills).split(',').map(Number)) {
      // Render a short run-up so time-dependent state settles exactly as in the video.
      for (let k = 6; k >= 0; k--) await page.evaluate((t) => window.renderAt(t), Math.max(0, s - k / FPS));
      await page.screenshot({ path: path.join(dir, `t${s.toFixed(1).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 88 });
    }
    console.log('stills written to', dir);
    await browser.close();
    return;
  }

  const from = Number(args.from || 0), to = Math.min(Number(args.to || duration), duration);
  const out = path.resolve(args.out || path.join(BUILD, 'video.mp4'));
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const n0 = Math.round(from * FPS), n1 = Math.round(to * FPS);
  const started = Date.now();
  for (let n = n0; n < n1; n++) {
    await page.evaluate((t) => window.renderAt(t), n / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if ((n - n0) % (FPS * 5) === 0) {
      const done = (n - n0) / (n1 - n0), el = (Date.now() - started) / 1000;
      console.log(`${(n / FPS).toFixed(1)}s  ${(done * 100).toFixed(0)}%  elapsed ${el.toFixed(0)}s  eta ${done ? (el / done - el).toFixed(0) : '?'}s`);
    }
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  console.log('wrote', out);
  await browser.close();
})();
