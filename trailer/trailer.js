/* CampaignFlow trailer: one paused GSAP timeline, rendered frame by frame.

   Everything is timed from build/timeline.json (the narration), so the
   picture follows the voice. window.renderAt(t) seeks the timeline, then
   applies the procedural layers (camera, footage frames, particles, grain,
   shake, captions) and resolves once every image for that frame is decoded. */
(async () => {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const TL = await (await fetch('build/timeline.json')).json();
  const CLIPS = ['daily', 'plan', 'switch', 'lock', 'campaign', 'revise', 'cycle'];
  const FOOT = {};
  for (const c of CLIPS) FOOT[c] = await (await fetch(`build/footage/${c}/meta.json`)).json();

  const LINE = Object.fromEntries(TL.lines.map((l) => [l.id, l]));
  const SC = Object.fromEntries(TL.scenes.map((s) => [s.id, s]));
  const at = (id) => LINE[id].start;
  const end = (id) => LINE[id].start + LINE[id].dur;
  const mark = (clip, label) => {
    const m = FOOT[clip].marks.find((x) => x.label === label);
    if (!m) throw new Error(`missing mark ${clip}/${label}`);
    return m;
  };

  const tl = gsap.timeline({ paused: true });
  const P = { shake: 0, glitch: 0, think: 0, stat: 0, n1: 1, n2: 0, n3: 0, burst: [] };
  // fromTo that never renders early: the timeline is only ever seeked forward.
  const T = (target, t, dur, from, to, ease = 'power3.out') =>
    tl.fromTo(target, from, { ...to, duration: dur, ease, immediateRender: false }, Math.max(0, t));
  const kick = (t, amount = 1, dur = 0.5) => T(P, t, dur, { shake: amount }, { shake: 0 }, 'power2.out');
  const flash = (t, o = 0.5, dur = 0.5) => T('#flash', t, dur, { opacity: o, backgroundColor: '#ffffff' }, { opacity: 0, backgroundColor: '#ffffff' }, 'power2.out');
  const burst = (t, x, y, n = 70, hue = 250) => P.burst.push({ t, x, y, n, hue });
  const sceneIn = (el, t, dur = 0.45) => T(el, t, dur, { opacity: 0 }, { opacity: 1 }, 'power2.out');
  const sceneOut = (el, t, dur = 0.4) => T(el, t, dur, { opacity: 1 }, { opacity: 0 }, 'power2.in');
  const el = (html) => { const d = document.createElement('div'); d.innerHTML = html.trim(); return d.firstChild; };

  // =====================================================================
  // HOOK
  // =====================================================================
  const hook = SC.hook;
  tl.set('#s-hook', { opacity: 1 }, 0);
  T('#clock', at('h1') - 0.15, 0.6, { opacity: 0, scale: 1.5, filter: 'blur(24px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)' }, 'expo.out');
  kick(at('h1'), 0.6);
  T('#clock', at('h2') - 0.12, 0.5, { y: 0, scale: 1 }, { y: -255, scale: 0.42 }, 'expo.inOut');
  const words = ['h2', 'h3', 'h4'];
  words.forEach((id, i) => {
    const w = `#w-${id}`;
    T(w, at(id) - 0.06, 0.4, { opacity: 0, scale: 1.9, filter: 'blur(30px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)' }, 'expo.out');
    kick(at(id), 0.9 + i * 0.25, 0.45);
    flash(at(id) - 0.02, 0.12 + i * 0.05, 0.3);
    const next = i < 2 ? at(words[i + 1]) - 0.1 : at('h5') - 0.3;
    T(w, next, 0.16, { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.85 }, 'power2.in');
  });
  const BUB = [
    ['SC', 'Sari-Sari Co.', 'Can we get the cut by noon? 🙏', 120, 140, -4, 38],
    ['KM', 'Kape Manila', 'Banner has to go live at 12!', 1380, 110, 3, 205],
    ['BP', 'BuildPH', "Where's the article draft?", 90, 640, 3, 160],
    ['PR', 'Producer', 'Filming moved to Thursday 😬', 1400, 620, -3, 15],
    ['SC', 'Sari-Sari Co.', 'TYPO IN THE LIVE AD!!', 690, 60, -2, 0],
    ['KM', 'Kape Manila', 'Need 3 more thumbnails', 1430, 360, 2, 205],
    ['AL', 'Account lead', "Who's free this afternoon?", 70, 390, -3, 280],
    ['BP', 'BuildPH', 'Any update??', 760, 800, 2, 160],
    ['SC', 'Sari-Sari Co.', 'Client wants changes', 1120, 860, -2, 38],
  ];
  const bubbles = $('#bubbles');
  const bStart = at('h2') - 0.2, bEnd = at('h5') - 0.35;
  BUB.forEach(([av, who, msg, x, y, r, h], i) => {
    const b = el(`<div class="bubble abs" style="left:${x}px;top:${y}px">
      <div class="av" style="background:hsl(${h} 70% 22%);color:hsl(${h} 90% 75%)">${av}</div>
      <div><div class="who">${who}<span>now</span></div><div class="msg">${msg}</div></div></div>`);
    bubbles.appendChild(b);
    const t = bStart + (bEnd - bStart) * (i / (BUB.length - 1)) ** 0.85;
    T(b, t, 0.45, { opacity: 0, scale: 0.55, y: 50, rotation: r - 10 }, { opacity: 1, scale: 1, y: 0, rotation: r }, 'back.out(1.9)');
  });
  T('#bubbles', at('h5') - 0.25, 0.5, { filter: 'blur(0px)', opacity: 1, scale: 1 }, { filter: 'blur(16px)', opacity: 0.22, scale: 0.94 });
  T('#clock', at('h5') - 0.3, 0.3, { opacity: 1 }, { opacity: 0 });
  T('#which', at('h5') - 0.08, 0.45, { opacity: 0, scale: 1.3, filter: 'blur(26px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)' }, 'expo.out');
  T(P, at('h5') - 0.08, 0.9, { glitch: 1 }, { glitch: 0 }, 'power2.out');
  flash(at('h5') - 0.08, 0.4, 0.6);
  kick(at('h5'), 1.4, 0.7);
  T('#s-hook', hook.end - 0.35, 0.4, { opacity: 1, scale: 1, filter: 'blur(0px)' }, { opacity: 0, scale: 1.12, filter: 'blur(18px)' }, 'power2.in');

  // =====================================================================
  // PROBLEM
  // =====================================================================
  const pr = SC.problem;
  sceneIn('#s-problem', pr.start - 0.05);
  T('#orb1', pr.start, 1.2, { backgroundColor: '#3b2fd9' }, { backgroundColor: '#8a1530' });
  T('#orb2', pr.start, 1.2, { backgroundColor: '#8a2bd6' }, { backgroundColor: '#5a1040' });
  T('#prob-head .kicker', pr.start + 0.05, 0.6, { opacity: 0, x: -30 }, { opacity: 1, x: 0 });
  T('#prob-head h2', pr.start + 0.15, 0.7, { opacity: 0, y: 40, filter: 'blur(14px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' });

  const board = $('#board');
  const X = (h) => 380 + (h - 9) * 210;   // board x for an hour of the day
  for (let h = 9; h <= 15; h++) board.appendChild(el(`<div class="axis"><span style="left:${X(h) - 380}px">${String(h).padStart(2, '0')}:00</span></div>`));
  board.appendChild(el(`<div class="lane-label" style="top:96px"><span style="width:40px;height:40px;border-radius:50%;display:grid;place-items:center;background:#1d3a2a;color:#7ee2a8;font-size:15px;font-weight:800">CE</span>Carlo · Editor</div>`));
  board.appendChild(el(`<div class="lane-track" style="top:80px"><div class="hatch" style="left:${X(12) - 380}px;width:210px"><em>lunch</em></div></div>`));
  board.appendChild(el(`<div class="lane-label" style="top:250px;color:#9a9ab0;font-size:20px">Requests, in arrival order →</div>`));
  const dl = el(`<div id="deadline" style="left:${X(12)}px;opacity:0"><span>BANNER DUE 12:00</span></div>`);
  board.appendChild(dl);
  const Q = [
    { id: 'typo', name: 'Fix typo', sub: '0.5h', u: true, qx: 380, h0: 9, h1: 9.5 },
    { id: 'thumb', name: 'Thumbnail set', sub: '2h', qx: 640, h0: 9.5, h1: 11.5 },
    { id: 'banner', name: 'Resize banner', sub: '1.5h · due 12:00', qx: 940, h0: 13, h1: 14.5 },
  ];
  const chips = {};
  Q.forEach((q, i) => {
    const c = el(`<div class="chip" style="left:${q.qx}px;top:236px;width:250px;opacity:0">${q.u ? '<span class="u">URGENT</span>' : ''}${q.name}<small>${q.sub}</small>
      <div class="redov" style="position:absolute;inset:0;border-radius:12px;background:linear-gradient(180deg,#ff6b7c,#e3334a);opacity:0"></div>
      <span class="lbl" style="position:absolute;left:16px;z-index:2;display:none"></span></div>`);
    board.appendChild(c);
    chips[q.id] = c;
    T(c, at('p1') - 0.3 + i * 0.16, 0.45, { opacity: 0, y: 40, scale: 0.8 }, { opacity: 1, y: 0, scale: 1 }, 'back.out(1.7)');
    const tFly = at('p1') + 0.85 + i * 0.55;
    T(c, tFly, 0.6, { left: q.qx, top: 236, width: 250 }, { left: X(q.h0), top: 86, width: (q.h1 - q.h0) * 210 }, 'power3.inOut');
  });
  // Banner tries the 11:30 gap first, then gets pushed past lunch.
  // (handled by the fly-in landing directly at 13:00; lunch hatch flashes)
  T(`#board .hatch`, at('p1') + 2.0, 0.5, { backgroundColor: 'rgba(255,255,255,0)' }, { backgroundColor: 'rgba(255,181,71,.18)' }, 'power2.out');
  T(`#board .hatch`, at('p1') + 2.5, 0.6, { backgroundColor: 'rgba(255,181,71,.18)' }, { backgroundColor: 'rgba(255,255,255,0)' }, 'power2.in');
  // p2: editing card blocked by the filming gate.
  const edit = el(`<div class="chip" style="left:1240px;top:236px;width:300px;opacity:0">🎬 Edit brand video<small>3–6h</small></div>`);
  const gate = el(`<div id="gate" style="left:1270px;top:330px;opacity:0">🎬 Filming · not confirmed</div>`);
  board.appendChild(edit); board.appendChild(gate);
  T(edit, at('p2') - 0.1, 0.4, { opacity: 0, y: 40 }, { opacity: 1, y: 0 }, 'back.out(1.7)');
  T(gate, at('p2') + 0.45, 0.4, { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1 }, 'back.out(2)');
  T(edit, at('p2') + 0.75, 0.25, { y: 0 }, { y: -70 }, 'power2.in');
  T(edit, at('p2') + 1.0, 0.5, { y: -70 }, { y: 0 }, 'bounce.out');
  kick(at('p2') + 1.0, 0.6, 0.35);
  T(edit, at('p2') + 1.05, 0.35, { opacity: 1 }, { opacity: 0.4 });
  // "...or that a banner is due at noon!"
  T(dl, at('p2') + 2.25, 0.5, { opacity: 0, scaleY: 0, transformOrigin: '50% 0%' }, { opacity: 1, scaleY: 1 }, 'expo.out');
  T(chips.banner, at('p2') + 2.6, 0.25, { scale: 1 }, { scale: 1.08 }, 'power2.out');
  T(chips.banner, at('p2') + 2.85, 0.35, { scale: 1.08 }, { scale: 1 }, 'power2.in');
  // p3: guess wrong -> late
  T($('.redov', chips.banner), at('p3') + 0.3, 0.3, { opacity: 0 }, { opacity: 1 });
  const late = el(`<div id="late" style="left:${X(13.15)}px;top:-118px;white-space:nowrap">LATE +2.5h</div>`);
  board.appendChild(late);
  T(late, at('p3') + 0.75, 0.35, { opacity: 0, scale: 2.6, rotation: -20 }, { opacity: 1, scale: 1, rotation: -9 }, 'expo.in');
  kick(at('p3') + 1.1, 1.6, 0.6);
  T('#flash', at('p3') + 1.1, 0.5, { opacity: 0.25, backgroundColor: '#ff3355' }, { opacity: 0, backgroundColor: '#ff3355' });
  T(P, at('p3') + 1.1, 0.5, { glitch: 0.5 }, { glitch: 0 });
  T('#board', end('p3') + 0.3, 0.6, { opacity: 1 }, { opacity: 0.45 });
  T('#stat', end('p3') + 0.3, 0.7, { opacity: 0, y: 50, filter: 'blur(10px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' }, 'expo.out');
  T(P, end('p3') + 0.45, 1.3, { stat: 0 }, { stat: 56.1 }, 'power2.out');

  // =====================================================================
  // TURN
  // =====================================================================
  const tu = SC.turn;
  T('#s-problem', tu.start - 0.1, 0.9, { opacity: 1, scale: 1, filter: 'blur(0px)' }, { opacity: 0, scale: 0.12, filter: 'blur(30px)' }, 'expo.in');
  T('#orb1', tu.start + 0.4, 1.2, { backgroundColor: '#8a1530' }, { backgroundColor: '#3b2fd9' });
  T('#orb2', tu.start + 0.4, 1.2, { backgroundColor: '#5a1040' }, { backgroundColor: '#8a2bd6' });
  tl.set('#s-turn', { opacity: 1 }, tu.start);
  T('#think', at('t1') - 0.12, 0.2, { opacity: 0 }, { opacity: 1 });
  T(P, at('t1') - 0.05, LINE.t1.dur * 0.9, { think: 0 }, { think: 34 }, 'none');
  T('#think', at('t2') - 0.45, 0.4, { opacity: 1, scale: 1, filter: 'blur(0px)' }, { opacity: 0, scale: 0.5, filter: 'blur(16px)' }, 'expo.in');
  flash(at('t2') - 0.08, 0.95, 0.9);
  kick(at('t2') - 0.05, 1.2, 0.6);
  T('#rays', at('t2') - 0.08, 0.8, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1 }, 'expo.out');
  T('#logo', at('t2') - 0.08, 0.8, { opacity: 0, scale: 0.2, rotation: -25 }, { opacity: 1, scale: 1, rotation: 0 }, 'back.out(1.7)');
  ['#ll1', '#ll2', '#ll3'].forEach((s, i) => T(s, at('t2') + 0.25 + i * 0.12, 0.4, { strokeDasharray: 24, strokeDashoffset: 24 }, { strokeDasharray: 24, strokeDashoffset: 0 }, 'power2.out'));
  const word = $('#word');
  'CampaignFlow'.split('').forEach((ch, i) => {
    const s = el(`<span${i >= 8 ? ' class="grad"' : ''}>${ch}</span>`);
    word.appendChild(s);
    T(s, at('t2') + 0.05 + i * 0.035, 0.6, { opacity: 0, y: 70, filter: 'blur(12px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' }, 'expo.out');
  });
  burst(at('t2') + 0.05, 960, 400, 110, 250);
  T('#tagline', at('t2') + 1.0, 0.8, { opacity: 0, y: 20 }, { opacity: 1, y: 0 });
  T('#s-turn', tu.end - 0.45, 0.45, { opacity: 1, scale: 1, filter: 'blur(0px)' }, { opacity: 0, scale: 1.1, filter: 'blur(14px)' }, 'power2.in');

  // =====================================================================
  // FEATURES
  // =====================================================================
  const FEATURES = [
    { id: 'daily', num: '01', kicker: 'Daily check-in', lines: ['Your morning,', 'in two taps.'],
      sub: 'CampaignFlow only asks what changed.', url: 'campaignflow · Today',
      chips: [['✕', 'No forms, no spreadsheets', at('d2')], ['✓', 'Did the client approve?', at('d3')], ['✓', "Who's in today?", at('d3') + 0.9]] },
    { id: 'plan', num: '02', kicker: 'Plan the day', lines: ['Ranks it.', 'Fits it.', 'Plans it.'],
      sub: 'A min-heap and a greedy scheduler, working together.', url: 'campaignflow · Plan',
      chips: [['⛰', 'Min-heap priority queue', at('q2')], ['⚡', 'Greedy time-slot allocation', at('q3')], ['⇄', 'Compare with first-come, first-served', at('q4')]] },
    { id: 'lock', num: '03', kicker: 'Commit', lines: ['Love it?', 'Lock it in.'],
      sub: 'Commitments never move, until you unlock them.', url: 'campaignflow · Plan',
      chips: [['🔒', 'One click to commit', at('l1')], ['↻', 'Replans route around locked work', at('l2')], ['⤺', 'Unlock anytime', at('l2') + 1.8]] },
    { id: 'campaign', num: '04', kicker: 'New campaigns', lines: ['New client?', 'New campaign.', 'In seconds.'],
      sub: 'Templates fill in every step, link and estimate.', url: 'campaignflow · Campaigns',
      chips: [['▦', 'Ready-made templates', at('n1')], ['⛓', 'Steps, links & estimates', at('n2')], ['↺', 'Revision rounds, never loops', at('n3') + 1.6]] },
    { id: 'cycle', num: '05', kicker: 'Safe by design', lines: ['No impossible', 'loops.', 'Ever.'],
      sub: 'Depth-first search checks every link before it reaches your plan.', url: 'campaignflow · Edit task',
      chips: [['◉', 'Unvisited · active · finished', at('c1')], ['⟲', 'Loops caught instantly', at('c2') + 1.6], ['⌖', 'Shows exactly where', at('c2') + 3.2]] },
  ];
  const feats = $('#features');
  const WINS = {};   // per feature: window state for renderAt

  FEATURES.forEach((f, fi) => {
    const s = SC[f.id];
    const sc = el(`<div class="scene" id="s-${f.id}" style="perspective:2200px">
      <div class="ghostnum">${f.num}</div>
      <div class="ftext"><div class="kicker">${f.num} — ${f.kicker}</div>
        <h2>${f.lines.map((l, i) => `<span class="ln${i === f.lines.length - 1 ? ' grad' : ''}">${l}</span>`).join('')}</h2>
        <p>${f.sub}</p><ul>${f.chips.map(([ic, tx]) => `<li><i>${ic}</i>${tx}</li>`).join('')}</ul></div>
      <div class="float abs" style="inset:0">
        <div class="win"><div class="win-bar"><i></i><i></i><i></i><span>${f.url}</span></div>
          <div class="screen"><div class="cam"><img alt=""></div><div class="vizes"></div>
            <div class="overlay-icon"></div><div class="glare"></div></div></div></div>
    </div>`);
    feats.appendChild(sc);
    const W = { scene: sc, cam: $('.cam', sc), img: $('img', sc), float: $('.float', sc), segs: [], camState: { cx: 0.5, cy: 0.5, z: 1 }, last: null };
    WINS[f.id] = W;
    W.camProxy = { ...W.camState };
    W.camKeys = [];

    // whip in / out
    if (fi === 0) {
      T(sc, s.start, 0.6, { opacity: 0 }, { opacity: 1 }, 'power2.out');
    } else {
      T(sc, s.start, 0.5, { opacity: 0, x: 240, filter: 'blur(26px)' }, { opacity: 1, x: 0, filter: 'blur(0px)' }, 'power3.out');
    }
    if (fi < FEATURES.length - 1) {
      T(sc, s.end - 0.32, 0.32, { opacity: 1, x: 0, filter: 'blur(0px)' }, { opacity: 0, x: -240, filter: 'blur(26px)' }, 'power2.in');
    } else {
      T(sc, s.end - 0.45, 0.45, { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.94 }, 'power2.in');
    }
    T($('.ghostnum', sc), s.start + 0.05, 1.2, { opacity: 0, x: -80 }, { opacity: 1, x: 0 }, 'expo.out');
    T($('.kicker', sc), s.start + 0.1, 0.5, { opacity: 0, x: -24 }, { opacity: 1, x: 0 });
    $$('.ln', sc).forEach((ln, i) => T(ln, s.start + 0.2 + i * 0.1, 0.7, { opacity: 0, y: 50, filter: 'blur(12px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' }, 'expo.out'));
    T($('p', sc), s.start + 0.6, 0.6, { opacity: 0, y: 16 }, { opacity: 1, y: 0 });
    $$('li', sc).forEach((li, i) => T(li, f.chips[i][2] - 0.1, 0.5, { opacity: 0, x: -30 }, { opacity: 1, x: 0 }, 'back.out(1.6)'));
    const win = $('.win', sc);
    T(win, s.start + 0.1, 1.0, { opacity: 0, x: 260, rotationY: -38, rotationX: 10, scale: 0.86, transformPerspective: 2200 },
      { opacity: 1, x: 0, rotationY: -9, rotationX: 3, scale: 1, transformPerspective: 2200 }, 'expo.out');
    T($('.glare', sc), s.start + 0.6, 1.2, { x: -1500 }, { x: 1500 }, 'power2.inOut');
    // nav pills
    const pills = $$('#nav span');
    T(pills[fi], s.start + 0.1, 0.3, { backgroundColor: 'rgba(116,116,255,0)', color: '#5d5d72', borderColor: 'rgba(255,255,255,.08)' },
      { backgroundColor: 'rgba(116,116,255,.28)', color: '#ffffff', borderColor: 'rgba(116,116,255,.65)' });
    T(pills[fi], s.end - 0.1, 0.3, { backgroundColor: 'rgba(116,116,255,.28)', color: '#ffffff', borderColor: 'rgba(116,116,255,.65)' },
      { backgroundColor: 'rgba(116,116,255,0)', color: '#5d5d72', borderColor: 'rgba(255,255,255,.08)' });
  });
  T('#nav', SC.daily.start + 0.3, 0.6, { opacity: 0, y: -10 }, { opacity: 1, y: 0 });
  T('#nav', SC.cycle.end - 0.4, 0.4, { opacity: 1 }, { opacity: 0 });

  // --- footage segments & camera ---------------------------------------
  // seg: show `clip` during [t0, t1); clip time = a + (t - b) * rate
  const seg = (fid, clip, t0, t1, a, b, rate = 1) => WINS[fid].segs.push({ clip, t0, t1, a, b, rate });
  const clipToT = (s, ct) => s.b + (ct - s.a) / s.rate;
  // camera keyframe: move to mark (or full frame) at time t
  const cam = (fid, t, target, z, dur = 0.8, ease = 'power3.inOut') => WINS[fid].camKeys.push({ t, target, z, dur, ease });
  const viz = (fid, html) => { const v = el(`<div class="viz">${html}</div>`); $('.vizes', WINS[fid].scene).appendChild(v); return v; };
  const vizIn = (v, t) => T(v, t, 0.45, { opacity: 0, clipPath: 'inset(0% 100% 0% 0%)' }, { opacity: 1, clipPath: 'inset(0% 0% 0% 0%)' }, 'expo.inOut');
  const vizOut = (v, t) => T(v, t, 0.4, { opacity: 1, clipPath: 'inset(0% 0% 0% 0%)' }, { opacity: 0, clipPath: 'inset(0% 0% 0% 100%)' }, 'expo.inOut');

  // 01 DAILY ---------------------------------------------------------------
  {
    const s = SC.daily, y1 = mark('daily', 'yes1');
    seg('daily', 'daily', s.start, s.end + 1, y1.t, at('d3') + 0.3);
    cam('daily', s.start, 'full', 1, 0.01);
    cam('daily', at('d1') + 0.5, mark('daily', 'tasks'), 1.25, 2.6, 'power2.inOut');
    cam('daily', at('d3') - 0.35, mark('daily', 'attn'), 2.0, 0.75);
    cam('daily', at('d4') + 0.25, 'full', 1.06, 1.1);
  }
  // 02 PLAN ----------------------------------------------------------------
  {
    const s = SC.plan;
    const hero = mark('plan', 'hero');
    seg('plan', 'plan', s.start, at('q2') - 0.3, hero.t, at('q1') + 0.6);
    cam('plan', s.start, 'full', 1, 0.01);
    cam('plan', at('q1') + 0.9, mark('plan', 'gantt'), 1.25, 1.2);

    // heap visual
    const hv = viz('plan', `<div class="viz-title">Min-heap · ranked by (urgency, deadline)</div>
      <svg id="heap-edges" width="1120" height="700" style="position:absolute;inset:0"></svg><div class="crown" style="left:505px;top:96px">▲ NEXT UP</div>`);
    vizIn(hv, at('q2') - 0.35);
    vizOut(hv, at('q3') - 0.45);
    const SLOT = [[560, 165], [300, 330], [820, 330], [160, 505], [440, 505], [690, 505], [960, 505]];
    const svg = $('#heap-edges', hv);
    [[0, 1], [0, 2], [1, 3], [1, 4], [2, 5], [2, 6]].forEach(([a, b]) => {
      const ln = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      ln.setAttribute('x1', SLOT[a][0]); ln.setAttribute('y1', SLOT[a][1]); ln.setAttribute('x2', SLOT[b][0]); ln.setAttribute('y2', SLOT[b][1]);
      ln.style.opacity = 0; ln.dataset.child = b; svg.appendChild(ln);
    });
    SLOT.slice(0, 6).forEach(([x, y]) => hv.appendChild(el(`<div class="hslot" style="left:${x}px;top:${y}px"></div>`)));
    const ITEMS = [
      { id: 'T2', name: 'Thumbnail set', due: 'Tmrw 17:00', key: [1, 2460, 'T2'] },
      { id: 'C4-1', name: 'Article draft', due: 'Tmrw 17:00', key: [1, 2460, 'C4-1'] },
      { id: 'C3-1', name: 'Caption copy', due: 'Tmrw 15:00', key: [1, 2340, 'C3-1'] },
      { id: 'T3', name: 'Resize banner', due: 'Today 12:00', key: [1, 720, 'T3'] },
      { id: 'C2-4', name: 'Brand story edit', due: 'Tmrw 12:00', key: [1, 2160, 'C2-4'] },
      { id: 'T1', name: 'Fix typo in ad', due: '⚡ URGENT · 11:00', key: [0, 660, 'T1'], urgent: true },
    ];
    const less = (a, b) => { for (let i = 0; i < 3; i++) { if (a.key[i] < b.key[i]) return true; if (a.key[i] > b.key[i]) return false; } return false; };
    const steps = [];   // each: {pos: {id: slot}, add?: id, swap?: [id,id]}
    const arr = [];
    const snap = (extra) => steps.push({ pos: Object.fromEntries(arr.map((it, i) => [it.id, i])), ...extra });
    for (const it of ITEMS) {
      arr.push(it); snap({ add: it.id });
      let i = arr.length - 1;
      while (i > 0) {
        const p = (i - 1) >> 1;
        if (!less(arr[i], arr[p])) break;
        [arr[i], arr[p]] = [arr[p], arr[i]]; snap({ swap: [arr[i].id, arr[p].id] }); i = p;
      }
    }
    const nodes = {};
    ITEMS.forEach((it) => {
      const n = el(`<div class="hnode${it.urgent ? ' urgent' : ''}"><b>${it.name}</b><small>${it.due}</small></div>`);
      n.style.left = '0px'; n.style.top = '0px'; hv.appendChild(n); nodes[it.id] = n;
    });
    const t0 = at('q2') + 0.05, t1 = end('q2') + 1.0, dt = (t1 - t0) / steps.length;
    const where = {};
    steps.forEach((st, k) => {
      const t = t0 + k * dt;
      for (const [id, slot] of Object.entries(st.pos)) {
        const [x, y] = SLOT[slot];
        if (!(id in where)) {
          T(nodes[id], t, 0.32, { x: 560, y: 660, opacity: 0, scale: 0.6 }, { x, y, opacity: 1, scale: 1 }, 'back.out(1.4)');
          const edge = svg.querySelector(`line[data-child="${slot}"]`);
          if (edge) T(edge, t + 0.1, 0.25, { opacity: 0 }, { opacity: 1 });
        } else if (where[id] !== slot) {
          const [px, py] = SLOT[where[id]];
          T(nodes[id], t, Math.min(0.3, dt * 0.95), { x: px, y: py }, { x, y }, 'power2.inOut');
        }
        where[id] = slot;
      }
    });
    T($('.crown', hv), t1 + 0.05, 0.4, { opacity: 0, y: 10 }, { opacity: 1, y: 0 });
    T(nodes.T1, t1 + 0.05, 0.4, { boxShadow: '0 0 0px rgba(255,77,97,0)' }, { boxShadow: '0 0 50px rgba(255,77,97,.8)' });

    // lanes visual (greedy allocation)
    const lv = viz('plan', `<div class="viz-title">Greedy allocation · earliest free slot</div><div id="lv-src">↓ POPPED FROM THE HEAP</div>`);
    vizIn(lv, at('q3') - 0.45);
    vizOut(lv, at('q4') - 0.35);
    const LX = (h) => 210 + (h - 9) * 87;
    const axis = el('<div class="lv-axis"></div>');
    for (let h = 9; h <= 19; h++) axis.appendChild(el(`<span style="left:${LX(h) - 210}px">${String(h).padStart(2, '0')}</span>`));
    lv.appendChild(axis);
    const LANES = [
      { name: 'Bea', role: 'writer', y: 135, off: [[18, 19]], busy: [[10, 11, 'call'], [12, 13, 'lunch']] },
      { name: 'Carlo', role: 'editor', y: 245, off: [[18, 19]], busy: [[12, 13, 'lunch'], [15, 15.5, '']] },
      { name: 'Dani', role: 'editor · writer', y: 355, off: [[9, 10]], busy: [[12, 13, 'lunch']] },
      { name: 'Ely', role: 'not checked in', y: 465, off: [[9, 19]], busy: [] },
    ];
    LANES.forEach((ln) => {
      lv.appendChild(el(`<div class="lv-name" style="top:${ln.y + 14}px">${ln.name}<small>${ln.role}</small></div>`));
      const lane = el(`<div class="lv-lane" style="top:${ln.y}px"></div>`);
      ln.off.forEach(([a, b]) => lane.appendChild(el(`<div class="lv-off" style="left:${LX(a) - 210}px;width:${(b - a) * 87}px"></div>`)));
      ln.busy.forEach(([a, b, l]) => lane.appendChild(el(`<div class="hatch" style="left:${LX(a) - 210}px;width:${(b - a) * 87}px"><em style="bottom:-24px;font-size:13px">${l}</em></div>`)));
      lv.appendChild(lane);
    });
    const PLACE = [
      ['Fix typo', 1, 9, 9.5, true], ['Resize banner', 1, 9.5, 11], ['Brand story edit', 2, 13, 19],
      ['Caption copy', 2, 10, 12], ['Article draft', 0, 13, 18], ['Thumbnail set', 1, 13, 15],
    ];
    const p0 = at('q3') + 0.1, p1 = end('q3') + 0.4, pd = (p1 - p0) / PLACE.length;
    PLACE.forEach(([name, lane, a, b, urgent], k) => {
      const left = LX(a), top = LANES[lane].y, w = (b - a) * 87;
      const c = el(`<div class="lv-chip${urgent ? ' urgent' : ''}" style="left:${left}px;top:${top}px;width:${w}px">${name}</div>`);
      lv.appendChild(c);
      const t = p0 + k * pd;
      T(c, t, 0.55, { opacity: 0, x: 560 - left - w / 2, y: 60 - top, scale: 0.5 }, { opacity: 1, x: 0, y: 0, scale: 1 }, 'power3.inOut');
      T(c, t + 0.5, 0.35, { boxShadow: '0 0 40px rgba(160,160,255,1)' }, { boxShadow: '0 8px 26px rgba(93,93,240,.5)' }, 'power2.out');
    });

    // switch footage
    const tg = mark('switch', 'toggle');
    const sw = { clip: 'switch', t0: at('q4') - 0.35, t1: s.end + 1, a: tg.t, b: at('q4') + 1.05, rate: 1 };
    WINS.plan.segs.push(sw);
    cam('plan', at('q4') - 0.36, tg, 1.9, 0.01);
    cam('plan', clipToT(sw, mark('switch', 'risk').t) - 0.2, mark('switch', 'risk'), 1.8, 0.8);
    cam('plan', end('q4') - 0.5, mark('switch', 'hero'), 1.45, 0.9);
  }
  // 03 LOCK ----------------------------------------------------------------
  {
    const s = SC.lock, lb = mark('lock', 'lockbtn');
    const sg = { clip: 'lock', t0: s.start, t1: s.end + 1, a: lb.t, b: at('l1') + 0.35, rate: 1 };
    WINS.lock.segs.push(sg);
    const click = clipToT(sg, lb.t) + 0.55;
    cam('lock', s.start, mark('lock', 'schedule'), 1.3, 0.01);
    cam('lock', at('l1') - 0.1, lb, 1.9, 0.6);
    cam('lock', click + 0.35, mark('lock', 'toast'), 1.7, 0.5);
    cam('lock', clipToT(sg, mark('lock', 'gantt').t) + 0.05, mark('lock', 'gantt'), 1.3, 0.9);
    const ov = $('.overlay-icon', WINS.lock.scene);
    ov.innerHTML = '<svg width="110" height="110" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
    T(ov, click + 0.05, 0.45, { opacity: 0, scale: 2.6 }, { opacity: 1, scale: 1 }, 'back.out(1.8)');
    T(ov, click + 1.1, 0.4, { opacity: 1, scale: 1 }, { opacity: 0, scale: 1.4 }, 'power2.in');
    flash(click + 0.1, 0.3, 0.4);
    kick(click + 0.1, 0.9, 0.4);
    burst(click + 0.1, 1280, 540, 90, 255);
  }
  // 04 CAMPAIGN ------------------------------------------------------------
  {
    const s = SC.campaign;
    const pv = viz('campaign', `<div class="viz-title">Template · Client video</div>
      <svg id="pipe-svg" width="1120" height="700" style="position:absolute;inset:0"><defs><marker id="ah" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="rgba(170,170,255,.9)"/></marker></defs></svg>
      <div id="pipe-count"><span><b id="pc1">0</b>steps</span><span><b id="pc2">0</b>links</span><span><b id="pc3">0</b>estimates</span></div>`);
    vizIn(pv, s.start + 0.25);
    vizOut(pv, at('n2') - 0.2);
    const PN = [
      ['Scriptwriting', 'writing · 2–4h', false, 60, 120], ['Script approval', 'external gate', true, 425, 120], ['Filming', 'external gate', true, 790, 120],
      ['Editing', 'editing · 3–6h', false, 790, 340], ['Client review', 'external gate', true, 425, 340], ['Final approval', 'external gate', true, 60, 340],
    ];
    const PATHS = ['M330,172 L418,172', 'M695,172 L783,172', 'M925,224 L925,333', 'M790,392 L702,392', 'M425,392 L337,392'];
    const pt0 = s.start + 0.6, pstep = Math.min(0.32, (at('n1') + LINE.n1.dur - pt0) / 6);
    PN.forEach(([name, meta, gate, x, y], i) => {
      const n = el(`<div class="pn${gate ? ' gate' : ''}" style="left:${x}px;top:${y}px"><span class="ic">${gate ? '⚑' : '✎'}</span><b>${name}</b><small>${meta}</small></div>`);
      pv.appendChild(n);
      T(n, pt0 + i * pstep, 0.4, { opacity: 0, scale: 0.6, y: 20 }, { opacity: 1, scale: 1, y: 0 }, 'back.out(1.8)');
    });
    const psvg = $('#pipe-svg', pv);
    PATHS.forEach((d, i) => {
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', d); p.setAttribute('marker-end', 'url(#ah)'); psvg.appendChild(p);
      const len = 110;
      T(p, pt0 + (i + 1) * pstep - 0.05, 0.3, { strokeDasharray: len, strokeDashoffset: len, opacity: 1 }, { strokeDasharray: len, strokeDashoffset: 0, opacity: 1 }, 'power2.out');
      tl.set(p, { opacity: 0 }, 0);
    });
    T(P, pt0, pstep * 6, { pc1: 0, pc2: 0, pc3: 0 }, { pc1: 6, pc2: 5, pc3: 2 }, 'none');
    // fast-forward footage of creating a campaign
    const cA = 0.6, cB = mark('campaign', 'newgroup').t + 0.9, w0 = at('n2') - 0.2, w1 = at('n3') - 0.1;
    const cs = { clip: 'campaign', t0: w0, t1: w1, a: cA, b: w0, rate: (cB - cA) / (w1 - w0) };
    WINS.campaign.segs.push(cs);
    cam('campaign', w0 - 0.01, mark('campaign', 'templates'), 1.35, 0.01);
    cam('campaign', clipToT(cs, mark('campaign', 'form').t) - 0.6, mark('campaign', 'form'), 1.4, 0.6);
    cam('campaign', clipToT(cs, mark('campaign', 'newgroup').t) - 0.1, mark('campaign', 'newgroup'), 1.55, 0.5);
    // the revision round
    const rv = mark('revise', 'review');
    const rs = { clip: 'revise', t0: w1, t1: s.end + 1, a: rv.t, b: at('n3') + 1.6, rate: 1 };
    WINS.campaign.segs.push(rs);
    cam('campaign', w1 - 0.01, rv, 1.8, 0.01);
    cam('campaign', clipToT(rs, mark('revise', 'revgroup').t), mark('revise', 'revgroup'), 1.45, 0.8);
  }
  // 05 CYCLE ---------------------------------------------------------------
  {
    const s = SC.cycle;
    const gv = viz('cycle', `<div class="viz-title">Depth-first search · cycle check</div>
      <div id="legend"><span><i style="background:rgba(255,255,255,.35)"></i>unvisited</span><span><i style="background:var(--amber)"></i>on the path</span><span><i style="background:var(--green)"></i>finished</span></div>
      <svg id="graph-svg" width="1120" height="700" style="position:absolute;inset:0"><defs>
        <marker id="ga" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="rgba(255,255,255,.5)"/></marker>
        <marker id="gr" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#ff4d61"/></marker></defs></svg>
      <div id="stack-label">DFS STACK</div><div class="ring" style="left:430px;top:230px"></div><div class="ring r2" style="left:430px;top:230px"></div>
      <div id="cyc-msg">⚠ Circular dependency: Article draft → Copy edit &amp; layout → Article draft</div>`);
    vizIn(gv, s.start + 0.3);
    const GN = [['Z', 'Brief approved', 'GATE', 160], ['A', 'Article draft', 'WRITING', 430], ['B', 'Copy edit', 'EDITING', 700], ['C', 'Client review', 'GATE', 970]];
    const gnodes = {};
    const COL = {
      white: { backgroundColor: 'rgba(255,255,255,0.06)', borderColor: 'rgba(255,255,255,0.25)' },
      gray: { backgroundColor: 'rgba(255,181,71,0.20)', borderColor: 'rgba(255,181,71,1)' },
      black: { backgroundColor: 'rgba(57,224,155,0.16)', borderColor: 'rgba(57,224,155,1)' },
      red: { backgroundColor: 'rgba(255,77,97,0.30)', borderColor: 'rgba(255,77,97,1)' },
    };
    const state = {};
    GN.forEach(([k, name, tag, x], i) => {
      const n = el(`<div class="gn" style="left:${x}px;top:230px">${name}<small>${tag}</small></div>`);
      gv.appendChild(n); gnodes[k] = n; state[k] = 'white';
      T(n, s.start + 0.5 + i * 0.12, 0.4, { opacity: 0, scale: 0.7 }, { opacity: 1, scale: 1 }, 'back.out(1.7)');
    });
    const gsvg = $('#graph-svg', gv);
    const edges = {};
    [['Z', 'A', 260, 330], ['A', 'B', 530, 600], ['B', 'C', 800, 870]].forEach(([a, b, x1, x2], i) => {
      const p = document.createElementNS('http://www.w3.org/2000/svg', 'path');
      p.setAttribute('d', `M${x1},230 L${x2 - 4},230`); p.setAttribute('class', 'e'); p.setAttribute('marker-end', 'url(#ga)');
      gsvg.appendChild(p); edges[a + b] = p;
      T(p, s.start + 0.7 + i * 0.12, 0.3, { opacity: 0 }, { opacity: 1 });
    });
    const loop = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    loop.setAttribute('d', 'M700,274 C700,400 430,400 430,278'); loop.setAttribute('class', 'e loop'); loop.setAttribute('marker-end', 'url(#gr)');
    gsvg.appendChild(loop);
    tl.set(loop, { opacity: 0 }, 0);
    const paint = (k, to, t) => { T(gnodes[k], t, 0.18, { ...COL[state[k]] }, { ...COL[to] }, 'power2.out'); state[k] = to; };
    const stackBoxes = [];
    const push = (k, t, i) => {
      const b = el(`<div class="stackbox" style="left:${60 + i * 220}px;top:525px">${GN.find((g) => g[0] === k)[1]}</div>`);
      gv.appendChild(b); stackBoxes.push(b);
      T(b, t, 0.22, { opacity: 0, y: -24 }, { opacity: 1, y: 0 }, 'back.out(2)');
      return b;
    };
    const pop = (b, t) => T(b, t, 0.18, { opacity: 1, y: 0 }, { opacity: 0, y: 20 }, 'power2.in');
    // pass 1: acyclic, everything finishes green
    let t = s.start + 1.0;
    const d1 = 0.2, order = ['Z', 'A', 'B', 'C'], bx = [];
    order.forEach((k, i) => { paint(k, 'gray', t); bx.push(push(k, t, i)); t += d1; });
    [...order].reverse().forEach((k, i) => { paint(k, 'black', t); pop(bx[3 - i], t); t += d1; });
    // reset, then the loop appears
    const r0 = at('c2') - 0.25;
    order.forEach((k) => paint(k, 'white', r0));
    T(loop, at('c2') + 0.1, 0.7, { strokeDasharray: '12 9', strokeDashoffset: 0, opacity: 0 }, { strokeDasharray: '12 9', strokeDashoffset: -60, opacity: 1 }, 'power2.out');
    // pass 2: Z, A, B on the path, then the edge B->A hits a node that is still on the path
    let t2 = at('c2') + 0.75; const bx2 = [];
    ['Z', 'A', 'B'].forEach((k, i) => { paint(k, 'gray', t2); bx2.push(push(k, t2, i)); t2 += 0.22; });
    const hit = at('c2') + 1.6;
    T(loop, hit - 0.15, 0.3, { strokeWidth: 3.5 }, { strokeWidth: 7 });
    paint('A', 'red', hit); paint('B', 'red', hit);
    T($('.ring', gv), hit, 0.8, { opacity: 1, scale: 0.4 }, { opacity: 0, scale: 1.6 }, 'power2.out');
    T($('.ring.r2', gv), hit + 0.25, 0.8, { opacity: 1, scale: 0.4 }, { opacity: 0, scale: 1.6 }, 'power2.out');
    T('#cyc-msg', hit + 0.1, 0.45, { opacity: 0, y: 20 }, { opacity: 1, y: 0 }, 'back.out(1.6)');
    kick(hit, 1.3, 0.55);
    T('#flash', hit, 0.4, { opacity: 0.2, backgroundColor: '#ff3355' }, { opacity: 0, backgroundColor: '#ff3355' });
    vizOut(gv, at('c2') + 2.6);
    const ts = mark('cycle', 'toast');
    const cs = { clip: 'cycle', t0: at('c2') + 2.6, t1: s.end + 1, a: ts.t, b: at('c2') + 3.25, rate: 1 };
    WINS.cycle.segs.push(cs);
    cam('cycle', at('c2') + 2.59, mark('cycle', 'picker'), 1.35, 0.01);
    cam('cycle', at('c2') + 3.05, ts, 2.2, 0.6);
  }

  // =====================================================================
  // IMPACT
  // =====================================================================
  const im = SC.impact;
  sceneIn('#s-impact', im.start);
  T('#imp-head .kicker', im.start + 0.1, 0.5, { opacity: 0, y: 14 }, { opacity: 1, y: 0 });
  T('#imp-head h2', im.start + 0.2, 0.8, { opacity: 0, y: 40, filter: 'blur(12px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' }, 'expo.out');
  [['#st1', 'i1'], ['#st2', 'i2'], ['#st3', 'i3']].forEach(([s, id]) => {
    T(s, at(id) - 0.25, 0.8, { opacity: 0, y: 80, rotationX: 25, transformPerspective: 1600 }, { opacity: 1, y: 0, rotationX: 0, transformPerspective: 1600 }, 'expo.out');
    T(`${s} .bar`, at(id) - 0.05, 0.9, { scaleX: 0 }, { scaleX: 1 }, 'expo.out');
    flash(at(id) - 0.05, 0.1, 0.35);
  });
  T(P, at('i1') + 0.6, 0.5, { n1: 1 }, { n1: 0 }, 'power2.inOut');
  T('#st1 .big', at('i1') + 1.05, 0.35, { scale: 1.25 }, { scale: 1 }, 'back.out(2)');
  burst(at('i1') + 1.05, 390, 540, 50, 150);
  T(P, at('i2') + 0.2, 1.4, { n2: 0 }, { n2: 24 }, 'power2.out');
  T(P, at('i3') + 0.4, 1.0, { n3: 0 }, { n3: 2 }, 'power2.out');
  T('#imp-note', end('i3') + 0.1, 0.6, { opacity: 0 }, { opacity: 1 });
  T('#s-impact', im.end - 0.4, 0.4, { opacity: 1, scale: 1 }, { opacity: 0, scale: 1.05 }, 'power2.in');

  // =====================================================================
  // END
  // =====================================================================
  const en = SC.end;
  tl.set('#s-end', { opacity: 1 }, en.start);
  T('#e1', at('e1') - 0.06, 0.4, { opacity: 0, scale: 1.5, filter: 'blur(24px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)' }, 'expo.out');
  kick(at('e1'), 0.8, 0.4);
  T('#e1', at('e2') - 0.14, 0.18, { opacity: 1, y: 0 }, { opacity: 0, y: -60 }, 'power2.in');
  T('#e2', at('e2') - 0.06, 0.4, { opacity: 0, scale: 1.5, filter: 'blur(24px)' }, { opacity: 1, scale: 1, filter: 'blur(0px)' }, 'expo.out');
  kick(at('e2'), 1.0, 0.45);
  T('#e2', at('e3') - 0.4, 0.3, { opacity: 1, scale: 1 }, { opacity: 0, scale: 0.85 }, 'power2.in');
  flash(at('e3') - 0.1, 0.7, 0.8);
  T('#end-logo', at('e3') - 0.1, 0.8, { opacity: 0, scale: 0.3, rotation: -20 }, { opacity: 1, scale: 1, rotation: 0 }, 'back.out(1.6)');
  T('#end-name', at('e3') + 0.05, 0.8, { opacity: 0, y: 50, filter: 'blur(14px)' }, { opacity: 1, y: 0, filter: 'blur(0px)' }, 'expo.out');
  burst(at('e3') + 0.05, 960, 380, 120, 260);
  T('#end-tag', end('e3') + 0.3, 0.7, { opacity: 0, y: 16 }, { opacity: 1, y: 0 });
  T('#credits', end('e3') + 1.0, 0.8, { opacity: 0, y: 16 }, { opacity: 1, y: 0 });
  T('#blackout', TL.duration - 0.9, 0.9, { opacity: 0 }, { opacity: 1 }, 'power1.in');

  // camera tweens (built last so each starts from the previous key)
  const markToCam = (m) => (m === 'full' ? { cx: 0.5, cy: 0.5 } : { cx: m.x + m.w / 2, cy: m.y + m.h / 2 });
  for (const W of Object.values(WINS)) {
    W.camKeys.sort((a, b) => a.t - b.t);
    let prev = { cx: 0.5, cy: 0.5, z: 1 };
    for (const k of W.camKeys) {
      const nx = { ...markToCam(k.target), z: k.z };
      T(W.camProxy, k.t, k.dur, { ...prev }, { ...nx }, k.ease);
      prev = nx;
    }
  }

  // =====================================================================
  // Procedural layers
  // =====================================================================
  const NOCAP = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 't1', 't2', 'e1', 'e2', 'e3']);
  const capEl = $('#cap');
  const world = $('#world');
  const orbs = [$('#orb1'), $('#orb2'), $('#orb3')];
  const floor = $('#floor');
  const rays = $('#rays');
  const whichLayers = $$('#which .w i');
  const pctx = $('#particles').getContext('2d');
  const gctx = $('#grain').getContext('2d');
  // seeded random
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) - 1) / 2147483646;
  const DUST = Array.from({ length: 110 }, () => ({ x: rnd() * 1920, y: rnd() * 1080, vx: (rnd() - 0.5) * 14, vy: -6 - rnd() * 16, r: 0.6 + rnd() * 2.2, ph: rnd() * 6.28 }));
  P.burst.forEach((b) => { b.parts = Array.from({ length: b.n }, () => { const a = rnd() * 6.283, sp = 250 + rnd() * 900; return { vx: Math.cos(a) * sp, vy: Math.sin(a) * sp - 200, r: 2 + rnd() * 4, hue: b.hue + (rnd() - 0.5) * 90, rot: rnd() * 6 }; }); });
  const GRAIN = Array.from({ length: 6 }, () => {
    const im = gctx.createImageData(480, 270);
    for (let i = 0; i < im.data.length; i += 4) { const v = rnd() * 255; im.data[i] = im.data[i + 1] = im.data[i + 2] = v; im.data[i + 3] = 255; }
    return im;
  });
  const imgCache = new Map();
  const frameFor = (clip, ct) => {
    const fr = FOOT[clip].frames;
    let lo = 0, hi = fr.length - 1;
    ct = Math.max(1.2, Math.min(ct, fr[hi]));   // skip the first frames while the page loads
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (fr[mid] <= ct) lo = mid; else hi = mid - 1; }
    return `build/footage/${clip}/${String(lo).padStart(5, '0')}.jpg`;
  };

  window.TIMELINE = TL;
  window.renderAt = async (t) => {
    tl.seek(t, true);
    const fi = Math.round(t * 60);

    // shake + world drift
    const sh = P.shake;
    const sx = sh * 14 * Math.sin(t * 91.3) * Math.cos(t * 37.1), sy = sh * 10 * Math.sin(t * 77.7 + 1.3);
    world.style.transform = `translate(${sx}px, ${sy}px) rotate(${sh * 0.35 * Math.sin(t * 53.1)}deg)`;
    orbs[0].style.transform = `translate(${Math.sin(t * 0.21) * 160}px, ${Math.cos(t * 0.17) * 110}px)`;
    orbs[1].style.transform = `translate(${Math.cos(t * 0.19) * 180}px, ${Math.sin(t * 0.23) * 120}px)`;
    orbs[2].style.transform = `translate(${Math.sin(t * 0.13 + 2) * 260}px, ${Math.cos(t * 0.11) * 160}px)`;
    floor.style.backgroundPosition = `0px ${(t * 38) % 90}px`;
    rays.style.transform = `rotate(${t * 9}deg)`;
    // glitch
    whichLayers.forEach((l, i) => {
      const g = P.glitch, dir = i ? -1 : 1;
      l.style.transform = `translate(${dir * g * (10 + 12 * Math.sin(t * 120 + i))}px, ${g * 4 * Math.sin(t * 80)}px)`;
      l.style.opacity = g > 0.02 ? 0.85 : 0;
    });
    // hook clock seconds
    $('#clock .s').textContent = ':' + String(12 + Math.min(47, Math.floor(t * 1.6))).padStart(2, '0');
    // counters
    $('#stat-n').textContent = P.stat.toFixed(1) + '%';
    $('#think').textContent = 'What if your schedule could think?'.slice(0, Math.round(P.think));
    const n1 = $('#n1'); n1.textContent = String(Math.round(P.n1));
    $('#n2').textContent = String(Math.round(P.n2));
    $('#n3').textContent = String(Math.round(P.n3));
    if (P.pc1 !== undefined) { $('#pc1').textContent = Math.round(P.pc1); $('#pc2').textContent = Math.round(P.pc2); $('#pc3').textContent = Math.round(P.pc3); }

    // captions
    let cap = '', co = 0;
    for (const l of TL.lines) {
      if (NOCAP.has(l.id)) continue;
      const a = l.start - 0.08, b = l.start + l.dur + 0.3;
      if (t >= a && t <= b) { cap = l.cap; co = Math.min(1, (t - a) / 0.15, (b - t) / 0.15); }
    }
    if (capEl.textContent !== cap && cap) capEl.textContent = cap;
    capEl.style.opacity = co;
    capEl.style.transform = `translateX(-50%) translateY(${(1 - co) * 12}px)`;

    // particles (ambient dust + bursts)
    pctx.clearRect(0, 0, 1920, 1080);
    for (const d of DUST) {
      const x = ((d.x + d.vx * t) % 1920 + 1920) % 1920, y = ((d.y + d.vy * t) % 1080 + 1080) % 1080;
      pctx.globalAlpha = 0.25 + 0.25 * Math.sin(t * 1.5 + d.ph);
      pctx.fillStyle = '#b8b8ff';
      pctx.beginPath(); pctx.arc(x, y, d.r, 0, 6.283); pctx.fill();
    }
    for (const b of P.burst) {
      const age = t - b.t;
      if (age < 0 || age > 1.6) continue;
      for (const p of b.parts) {
        const x = b.x + p.vx * age * (1 - age * 0.35), y = b.y + p.vy * age + 520 * age * age;
        pctx.globalAlpha = Math.max(0, 1 - age / 1.6);
        pctx.fillStyle = `hsl(${p.hue} 90% 70%)`;
        pctx.save(); pctx.translate(x, y); pctx.rotate(p.rot + age * 8); pctx.fillRect(-p.r, -p.r * 0.6, p.r * 2, p.r * 1.2); pctx.restore();
      }
    }
    pctx.globalAlpha = 1;
    gctx.putImageData(GRAIN[fi % GRAIN.length], 0, 0);

    // feature windows: float, camera, footage
    const waits = [];
    for (const [fid, W] of Object.entries(WINS)) {
      const s = SC[fid];
      if (t < s.start - 0.1 || t > s.end + 0.2) continue;
      W.float.style.transform = `translateY(${Math.sin(t * 1.1) * 7}px)`;
      const c = W.camProxy, z = Math.max(1, c.z), Wd = 1120, Ht = 700;
      let tx = Wd / 2 - c.cx * Wd * z, ty = Ht / 2 - c.cy * Ht * z;
      tx = Math.min(0, Math.max(Wd - Wd * z, tx)); ty = Math.min(0, Math.max(Ht - Ht * z, ty));
      W.cam.style.transform = `translate(${tx}px, ${ty}px) scale(${z})`;
      let sg = W.segs.find((x) => t >= x.t0 && t < x.t1) || W.segs.filter((x) => x.t0 <= t).pop() || W.segs[0];
      if (!sg) continue;
      const src = frameFor(sg.clip, sg.a + (t - sg.b) * sg.rate);
      if (W.last !== src) {
        W.img.src = src; W.last = src;
        waits.push(W.img.decode().catch(() => {}));
      }
    }
    await Promise.all(waits);
    await document.fonts.ready;
  };
  window.ready = true;
})().catch((e) => { window.renderError = String(e && e.stack || e); console.error(e); });
