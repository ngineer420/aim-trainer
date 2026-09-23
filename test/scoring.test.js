/* Run with:  node --test test/scoring.test.js
   No package.json, no dependencies — node:test and node:assert only.

   The README has always described the pure helpers at the top of app.js as
   "sanity-checked from Node before each commit". That check used to be an
   ad-hoc one-liner someone had to remember to type. Three drills' worth of
   scoring later it is worth writing down, because the failure modes here are
   silent: a tracking path that drifts outside its box, a grid that can respawn
   a target where you just clicked, or a rating ladder read from the wrong end
   all produce plausible-looking numbers rather than an error.

   It also checks the OUTPUT of tools/build_drills.py, so a hand-edit to one of
   the twelve generated files fails the suite rather than drifting quietly. */

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const A = require("../assets/js/app.js");
const REPO = path.join(__dirname, "..");

/* Every .html the site ships, discovered rather than listed: a new page must
   not be able to skip the checks below by not being added to an array. */
const ALL_HTML = (function walk(dir, base) {
  const out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name.startsWith(".") || e.name === "node_modules") continue;
    const abs = path.join(dir, e.name);
    const rel = base ? `${base}/${e.name}` : e.name;
    if (e.isDirectory()) out.push(...walk(abs, rel));
    else if (e.name.endsWith(".html")) out.push(rel);
  }
  return out;
})(REPO, "").sort();

/* ======================== the original helpers ======================== */

test("accuracy is a bounded percentage, and 0/0 is 0 rather than NaN", () => {
  assert.strictEqual(A.calcAccuracy(0, 0), 0);
  assert.strictEqual(A.calcAccuracy(10, 0), 100);
  assert.strictEqual(A.calcAccuracy(0, 10), 0);
  assert.strictEqual(A.calcAccuracy(3, 1), 75);
  for (let h = 0; h <= 40; h++) {
    for (let m = 0; m <= 40; m++) {
      const a = A.calcAccuracy(h, m);
      assert.ok(Number.isFinite(a) && a >= 0 && a <= 100, `out of bounds at ${h}/${m}: ${a}`);
    }
  }
});

test("average reaction time ignores an empty session instead of dividing by zero", () => {
  assert.strictEqual(A.calcAverageReactionTime([]), null);
  assert.strictEqual(A.calcAverageReactionTime([100, 200, 300]), 200);
});

test("targets never spawn where part of them would be off the playfield", () => {
  for (const d of [26, 44, 58, 84]) {
    for (let i = 0; i < 2000; i++) {
      const p = A.randomTargetPosition(600, 400, d);
      // left/top are the CENTRE — the sprite is translated by -50%.
      assert.ok(p.x - d / 2 >= -0.01 && p.x + d / 2 <= 600.01, `x escaped at d=${d}: ${p.x}`);
      assert.ok(p.y - d / 2 >= -0.01 && p.y + d / 2 <= 400.01, `y escaped at d=${d}: ${p.y}`);
    }
  }
});

/* ========================= time on target ========================= */

test("time on target is a bounded percentage and survives a zero-length session", () => {
  assert.strictEqual(A.calcTimeOnTarget(500, 0), 0);
  assert.strictEqual(A.calcTimeOnTarget(0, 1000), 0);
  assert.strictEqual(A.calcTimeOnTarget(500, 1000), 50);
  // A frame accounted twice, or a clock that jumped backwards, must not be
  // able to report more than the whole session.
  assert.strictEqual(A.calcTimeOnTarget(2000, 1000), 100);
  assert.strictEqual(A.calcTimeOnTarget(-50, 1000), 0);
});

/* ============================ gridshot ============================ */

test("the grid fills its area with nine distinct, evenly spaced centres", () => {
  const cells = A.gridCellCenters(600, 300, 3, 3);
  assert.strictEqual(cells.length, 9);
  const seen = new Set(cells.map((c) => `${c.x},${c.y}`));
  assert.strictEqual(seen.size, 9, "two cells share a centre");
  // Row-major, and the first cell is half a cell in from the corner.
  assert.deepStrictEqual(cells[0], { x: 100, y: 50 });
  assert.deepStrictEqual(cells[8], { x: 500, y: 250 });
  for (const c of cells) {
    assert.ok(c.x > 0 && c.x < 600 && c.y > 0 && c.y < 300, "a centre left the area");
  }
});

test("grid targets stay inside their own cell at any sane area size", () => {
  for (const [w, h] of [[320, 300], [600, 400], [1180, 480], [200, 200]]) {
    const d = A.gridTargetDiameter(w, h, 3, 3);
    const cell = Math.min(w / 3, h / 3);
    assert.ok(d >= 24, `target got untappably small at ${w}x${h}: ${d}`);
    assert.ok(d <= 84, `target got absurdly large at ${w}x${h}: ${d}`);
    // The clamp floor can exceed a very small cell; everywhere else the
    // target must leave a gap so two neighbours never touch.
    if (cell * 0.62 >= 24) assert.ok(d < cell, `target overflows its cell at ${w}x${h}`);
  }
});

/* ============================ tracking ============================ */

test("the tracking target can never leave the playfield, at any moment", () => {
  const rng = (() => { let s = 42; return () => (s = (s * 1103515245 + 12345) % 2147483648) / 2147483648; })();
  for (let run = 0; run < 40; run++) {
    const p = A.randomTrackingPath(rng);
    const d = 76;
    for (let t = 0; t <= 120000; t += 37) {
      const pt = A.trackingPathPoint(t, p, 600, 400, d);
      assert.ok(Number.isFinite(pt.x) && Number.isFinite(pt.y), `NaN position at t=${t}`);
      assert.ok(pt.x - d / 2 >= -0.01 && pt.x + d / 2 <= 600.01, `x escaped at t=${t}: ${pt.x}`);
      assert.ok(pt.y - d / 2 >= -0.01 && pt.y + d / 2 <= 400.01, `y escaped at t=${t}: ${pt.y}`);
    }
  }
});

test("the tracking path is a pure function of time — no drift, no frame memory", () => {
  const p = A.randomTrackingPath();
  for (const t of [0, 1, 999, 12345.6, 300000]) {
    const a = A.trackingPathPoint(t, p, 500, 300, 60);
    const b = A.trackingPathPoint(t, p, 500, 300, 60);
    assert.deepStrictEqual(a, b, `position at t=${t} is not reproducible`);
  }
});

test("the tracking path is continuous — no jumps for a reaction test to hide in", () => {
  const p = A.randomTrackingPath();
  let prev = A.trackingPathPoint(0, p, 600, 400, 76);
  for (let t = 16; t <= 60000; t += 16) {
    const pt = A.trackingPathPoint(t, p, 600, 400, 76);
    const step = Math.hypot(pt.x - prev.x, pt.y - prev.y);
    assert.ok(step < 40, `path jumped ${step.toFixed(1)}px in one frame at t=${t}`);
    prev = pt;
  }
});

test("a degenerate playfield does not produce a target outside it", () => {
  const p = A.randomTrackingPath();
  // Target wider than the box: availW is clamped to 0, so it pins to centre-ish
  // rather than returning NaN or a negative coordinate.
  const pt = A.trackingPathPoint(1234, p, 40, 40, 76);
  assert.ok(Number.isFinite(pt.x) && Number.isFinite(pt.y));
});

test("the inside-target test is a circle, not the bounding box", () => {
  assert.ok(A.isInsideTarget(100, 100, 100, 100, 40), "the centre must count as inside");
  assert.ok(A.isInsideTarget(119, 100, 100, 100, 40), "just inside the radius");
  assert.ok(!A.isInsideTarget(121, 100, 100, 100, 40), "just outside the radius");
  // The corner of the bounding box is outside the circle — this is the whole
  // reason the test is not a rectangle check.
  assert.ok(!A.isInsideTarget(119, 119, 100, 100, 40), "box corner must not count");
});

/* ======================= per-engine rating ======================= */

test("every engine has a rating ladder keyed to the number it actually reports", () => {
  const units = { flick: "avgReaction", precision: "accuracy", gridshot: "throughput", tracking: "onTargetPct" };
  for (const [engine, key] of Object.entries(units)) {
    const cfg = A.ENGINE_RATINGS[engine];
    assert.ok(cfg, `${engine} has no rating config`);
    assert.strictEqual(cfg.key, key, `${engine} is rated on the wrong number`);
    assert.ok(Array.isArray(cfg.tiers) && cfg.tiers.length === 7, `${engine} ladder is the wrong shape`);
  }
  // Only flick's ladder is read downwards; a drill scored on a rate or a
  // percentage must not inherit "lower is better".
  assert.strictEqual(A.ENGINE_RATINGS.flick.lowerIsBetter, true);
  for (const e of ["precision", "gridshot", "tracking"]) {
    assert.strictEqual(A.ENGINE_RATINGS[e].lowerIsBetter, false, `${e} is rated backwards`);
  }
});

test("each ladder is monotone — improving can never lower your grade", () => {
  const order = ["E", "D", "C", "B", "A", "A+", "S"];
  const rank = (t) => order.indexOf(t);
  const sweeps = {
    flick: { from: 900, to: 100, step: -5, key: "avgReaction" },
    precision: { from: 0, to: 100, step: 1, key: "accuracy" },
    gridshot: { from: 0, to: 4, step: 0.02, key: "throughput" },
    tracking: { from: 0, to: 100, step: 1, key: "onTargetPct" },
  };
  for (const [engine, s] of Object.entries(sweeps)) {
    let prev = -1;
    for (let v = s.from; s.step > 0 ? v <= s.to : v >= s.to; v += s.step) {
      const r = A.getRatingForEngine({ [s.key]: v }, engine);
      const i = rank(r.tier);
      assert.ok(i >= 0, `${engine} produced an unknown tier ${r.tier} at ${v}`);
      assert.ok(i >= prev, `${engine} grade fell while improving to ${v}`);
      prev = i;
    }
    assert.strictEqual(prev, order.length - 1, `${engine} never reaches S`);
  }
});

test("a session with nothing in it is 'no data', not a grade", () => {
  for (const engine of Object.keys(A.ENGINE_RATINGS)) {
    const r = A.getRatingForEngine({}, engine);
    assert.strictEqual(r.tier, "—", `${engine} graded an empty session`);
  }
  assert.strictEqual(A.getRatingForEngine({ avgReaction: NaN }, "flick").tier, "—");
});

test("an unknown engine falls back to the flick ladder rather than throwing", () => {
  const r = A.getRatingForEngine({ avgReaction: 200 }, "not-a-drill");
  assert.strictEqual(r.tier, A.getRatingForEngine({ avgReaction: 200 }, "flick").tier);
});

/* ===================== the session summary ===================== */

test("the summary reports each drill's headline number in its own units", () => {
  const base = { hits: 30, misses: 5, reactionTimes: [300, 320, 280], elapsedMs: 30000 };

  const flick = A.buildSessionSummary(base);
  assert.strictEqual(flick.avgReaction, 300);
  assert.ok(Math.abs(flick.throughput - 1) < 1e-9, "30 targets in 30s is 1/s");
  assert.strictEqual(flick.onTargetPct, null, "a drill with no tracking has no on-target figure");

  const grid = A.buildSessionSummary({ ...base, engine: "gridshot" });
  assert.strictEqual(grid.rating.tier, A.getRatingForEngine(grid, "gridshot").tier);

  const track = A.buildSessionSummary({ hits: 0, misses: 0, reactionTimes: [], elapsedMs: 30000, onTargetMs: 18000, engine: "tracking" });
  assert.strictEqual(track.onTargetPct, 60);
  assert.strictEqual(track.avgReaction, null, "tracking registers no clicks");
});

test("the original call site still works unchanged", () => {
  // buildSessionSummary gained two optional arguments; index.html's behaviour
  // must not depend on passing them.
  const s = A.buildSessionSummary({ hits: 10, misses: 2, reactionTimes: [400], elapsedMs: 15000 });
  assert.strictEqual(s.rating.tier, A.getRatingTier(400).tier);
});

/* ======================= best-record tracking ======================= */

test("a best is only replaced in the direction that counts as better", () => {
  assert.deepStrictEqual(A.updateBestMetric(null, 1.4, false), { best: 1.4, improved: true });
  assert.deepStrictEqual(A.updateBestMetric(1.4, 1.9, false), { best: 1.9, improved: true });
  assert.deepStrictEqual(A.updateBestMetric(1.9, 1.4, false), { best: 1.9, improved: false });
  assert.deepStrictEqual(A.updateBestMetric(300, 250, true), { best: 250, improved: true });
  assert.deepStrictEqual(A.updateBestMetric(250, 300, true), { best: 250, improved: false });
  // A drill that produced no headline number must never wipe a real one.
  assert.deepStrictEqual(A.updateBestMetric(1.9, null, false), { best: 1.9, improved: false });
  assert.deepStrictEqual(A.updateBestMetric(1.9, NaN, false), { best: 1.9, improved: false });
});

/* ================== the twelve generated pages ================== */

const DRILL_PAGES = [
  { slug: "gridshot", engine: "gridshot", preset: null },
  { slug: "tracking-trainer", engine: "tracking", preset: null },
  { slug: "precision-trainer", engine: "precision", preset: null },
  { slug: "valorant-aim-trainer", engine: null, preset: "valorant" },
  { slug: "csgo-aim-trainer", engine: null, preset: "csgo" },
  { slug: "fortnite-aim-trainer", engine: null, preset: "fortnite" },
];

// Unguarded lookups in app.js: a page missing one of these throws on load and
// the drill is simply dead. They are cheap to assert and expensive to notice.
const REQUIRED_IDS = [
  "year", "screen-setup", "screen-game", "screen-results", "start-btn",
  "change-mode-btn", "restart-btn", "game-area", "quit-btn",
  "hud-primary-label", "hud-primary-val", "rating-tier", "rating-label",
  "rating-compare", "new-best-flag", "history-chart", "history-list",
];

for (const page of DRILL_PAGES) {
  const clean = path.join(REPO, page.slug, "index.html");
  const flat = path.join(REPO, `${page.slug}.html`);

  test(`/${page.slug}/ ships as an identical flat/clean pair`, () => {
    const html = fs.readFileSync(clean, "utf8");
    assert.strictEqual(fs.readFileSync(flat, "utf8"), html, "the flat alias has drifted");
    // app.js reads the challenge-link base off the canonical, so the directory
    // form is load-bearing, not decorative.
    assert.ok(
      html.includes(`<link rel="canonical" href="https://flicktrainer.com/${page.slug}/">`),
      "canonical must be the directory form"
    );
  });

  test(`/${page.slug}/ selects its own engine`, () => {
    const html = fs.readFileSync(clean, "utf8");
    const body = html.match(/<body([^>]*)>/)[1];
    if (page.engine) assert.ok(body.includes(`data-engine="${page.engine}"`), `wrong engine: ${body}`);
    else assert.ok(!body.includes("data-engine"), "a preset page must stay on the flick engine");
    if (page.preset) assert.ok(body.includes(`data-preset="${page.preset}"`), `wrong preset: ${body}`);
    else assert.ok(!body.includes("data-preset"), "a drill page must not carry a preset");
  });

  test(`/${page.slug}/ has every element the engine reads unguarded`, () => {
    const html = fs.readFileSync(clean, "utf8");
    for (const id of REQUIRED_IDS) {
      assert.ok(html.includes(`id="${id}"`), `missing #${id} — the drill would throw on load`);
    }
    // The mode switch writes to both option panels without checking, so it
    // may only ship where both exist.
    if (/class="mode-opt"/.test(html)) {
      assert.ok(html.includes('id="timed-options"'), "mode switch without #timed-options");
      assert.ok(html.includes('id="count-options"'), "mode switch without #count-options");
    }
  });

  test(`/${page.slug}/ carries the portfolio furniture`, () => {
    const html = fs.readFileSync(clean, "utf8");
    const adTags = html.match(/adsbygoogle\.js\?client=ca-pub-7560786263587509/g) || [];
    assert.strictEqual(adTags.length, 1, "exactly one AdSense tag");
    assert.ok(!/class="[^"]*ad-slot/.test(html), "no manually placed ad units");
    assert.match(html, /erabbit-mark[\s\S]*?<\/a>\s*<\/body>/, "the mark must be last in body");
    assert.ok(html.includes("<!-- nav:start -->"), "the toolbar region must be present");
    assert.ok(html.includes('aria-current="page"'), "the active nav link must be marked");
    const h1s = html.match(/<h1[\s>]/g) || [];
    assert.strictEqual(h1s.length, 1, "every page needs exactly one h1");
    // The h1 has to come before the first h2, or a crawler reads the page as
    // starting halfway down. The marquee is the h1, and the marquee is the
    // first thing inside <main>.
    const h1At = html.indexOf("<h1");
    const h2At = html.indexOf("<h2");
    assert.ok(h1At > -1 && (h2At === -1 || h1At < h2At), "the h1 must precede every h2");
    assert.ok(!/\?v=5\b/.test(html), "stale cache-bust");
  });

  test(`/${page.slug}/ makes no external requests`, () => {
    const html = fs.readFileSync(clean, "utf8");
    // A hyperlink is not a request. What this rule exists to ban is a
    // SUBRESOURCE the browser fetches without being asked: a script, a
    // stylesheet, a font, an image, a frame, a beacon. Footer links to sibling
    // sites cost the visitor nothing until they click one, so they are matched
    // separately from src= and <link href=>.
    const subresources = [
      ...html.matchAll(/<(?:script|img|iframe|source|video|audio)[^>]+src="(https?:\/\/[^"]+)"/g),
      ...html.matchAll(/<link[^>]+href="(https?:\/\/[^"]+)"/g),
    ]
      .map((m) => m[1])
      .filter((u) => !u.startsWith("https://flicktrainer.com/"))
      .filter((u) => !u.startsWith("https://pagead2.googlesyndication.com/"));
    assert.deepStrictEqual(subresources, [], "unexpected external subresource");
    assert.ok(!/<link[^>]+fonts\./.test(html), "no web fonts");
  });

  test(`/${page.slug}/ is listed in the sitemap, once`, () => {
    const sitemap = fs.readFileSync(path.join(REPO, "sitemap.xml"), "utf8");
    assert.ok(sitemap.includes(`<loc>https://flicktrainer.com/${page.slug}/</loc>`));
    assert.ok(!sitemap.includes(`${page.slug}.html`), "the flat alias is not a second URL");
  });
}

test("the preset pages state the tuning they claim to apply", () => {
  // The whole justification for a tier-2 page is that its numbers are really
  // different AND really stated. A preset page that quotes the wrong figures
  // is a doorway page with extra steps.
  const tuning = {
    "valorant-aim-trainer": [44, 30, 1100],
    "csgo-aim-trainer": [52, 38, 1500],
    "fortnite-aim-trainer": [68, 44, 900],
  };
  for (const [slug, [start, end, life]] of Object.entries(tuning)) {
    const html = fs.readFileSync(path.join(REPO, slug, "index.html"), "utf8");
    assert.ok(html.includes(`${start}px`), `${slug} does not state its start size`);
    assert.ok(html.includes(`${end}px`), `${slug} does not state its end size`);
    assert.ok(html.includes(`${life}ms`), `${slug} does not state its lifespan`);
  }
});

test("every page is unique in the ways a search engine reads", () => {
  const pages = ["index.html"].concat(DRILL_PAGES.map((p) => `${p.slug}/index.html`));
  const seen = { title: new Map(), description: new Map(), canonical: new Map() };
  for (const rel of pages) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    const grab = {
      title: (html.match(/<title>([^<]+)<\/title>/) || [])[1],
      description: (html.match(/<meta name="description" content="([^"]+)"/) || [])[1],
      canonical: (html.match(/<link rel="canonical" href="([^"]+)"/) || [])[1],
    };
    for (const key of Object.keys(seen)) {
      assert.ok(grab[key], `${rel} has no ${key}`);
      assert.ok(!seen[key].has(grab[key]), `${rel} duplicates the ${key} of ${seen[key].get(grab[key])}`);
      seen[key].set(grab[key], rel);
    }
  }
});

test("the drill pages have not been hand-edited", () => {
  // tools/build_drills.py owns those twelve files. A hand-edit to one member of
  // a pair is exactly how the two halves drift apart, invisibly.
  const { spawnSync } = require("node:child_process");
  const run = spawnSync("python3", ["tools/build_drills.py", "--check"], { cwd: REPO, encoding: "utf8" });
  if (run.error) return; // no python3 here; the pair-identity tests still cover the worst case
  assert.strictEqual(run.status, 0, `build_drills.py --check failed:\n${run.stderr}`);
});

test("no page promises a drill it does not have", () => {
  // Issue #13 explicitly rules these out as copy-only doorways on an unchanged
  // engine. The wording belongs on the homepage; the URLs must not exist.
  for (const banned of ["flick-training", "mouse-accuracy-test"]) {
    assert.ok(!fs.existsSync(path.join(REPO, `${banned}.html`)), `${banned}.html should not exist`);
    assert.ok(!fs.existsSync(path.join(REPO, banned)), `/${banned}/ should not exist`);
    const sitemap = fs.readFileSync(path.join(REPO, "sitemap.xml"), "utf8");
    assert.ok(!sitemap.includes(banned), `${banned} must not be in the sitemap`);
  }
});

/* ================= a backgrounded tab must not score a run =================

   tick() is the only path to endSession(), and it re-arms itself with
   requestAnimationFrame, which a hidden tab stops delivering. The target
   expiry is a setTimeout, which a hidden tab keeps firing. The two together
   produced a run that counted misses forever and never ended: measured in
   headless Chrome, a 15s run hidden at t=1s read 0.0s on the clock at t=16s
   and was still on the game screen at t=31s with 23 misses.

   The rule that stops it is DOM-free, so it is asserted here. The wiring in
   app.js routes document.visibilitychange through this one predicate. */

test("a run is abandoned when, and only when, the tab goes hidden", () => {
  assert.strictEqual(A.shouldAbandonRun("hidden", true), true);
  assert.strictEqual(A.shouldAbandonRun("visible", true), false);
  // No live run: switching tabs on the setup or results screen changes nothing.
  assert.strictEqual(A.shouldAbandonRun("hidden", false), false);
  assert.strictEqual(A.shouldAbandonRun("visible", false), false);
  // Safari reports "prerender" while a page is warming up in the background.
  // That is not hidden and it is not a live run either.
  assert.strictEqual(A.shouldAbandonRun("prerender", true), false);
});

test("app.js actually listens for the tab being hidden", () => {
  // The predicate above is worthless if nothing calls it. This is the cheap
  // check that the wiring did not get dropped in a later refactor.
  const js = fs.readFileSync(path.join(REPO, "assets/js/app.js"), "utf8");
  assert.match(js, /addEventListener\("visibilitychange"/, "no visibilitychange handler");
  assert.match(js, /addEventListener\("pagehide"/, "no pagehide handler");
  // endSession(true) is the quit path: it writes no best, no history entry and
  // no XP. An abandoned run must go through it and not through endSession().
  const handler = js.slice(js.indexOf("function abandonRun"), js.indexOf("function abandonRun") + 400);
  assert.match(handler, /endSession\(true\)/, "an abandoned run must not be scored");
});

/* ===================== the game pages are different pages =====================

   Issue #17: the three game-branded pages were one template with the game's
   name substituted in, which measured at 61% shared five-word sequences. Three
   pages that say the same thing compete with each other and Google keeps one.
   This is the guard that stops the template creeping back. */

function bodyWords(rel) {
  const html = fs.readFileSync(path.join(REPO, rel), "utf8");
  const main = html.slice(html.indexOf("<main"), html.indexOf("</main>"));
  return main
    .replace(/<script[\s\S]*?<\/script>/g, " ")
    .replace(/<style[\s\S]*?<\/style>/g, " ")
    .replace(/<nav[\s\S]*?<\/nav>/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z]+;|&#\d+;/g, " ")
    .toLowerCase()
    .match(/[a-z0-9']+/g) || [];
}

function fiveGrams(words) {
  const out = new Set();
  for (let i = 0; i + 5 <= words.length; i++) out.add(words.slice(i, i + 5).join(" "));
  return out;
}

test("no two game pages share more than a quarter of their prose", () => {
  const slugs = ["csgo-aim-trainer", "valorant-aim-trainer", "fortnite-aim-trainer"];
  const grams = new Map(slugs.map((s) => [s, fiveGrams(bodyWords(`${s}/index.html`))]));
  for (let i = 0; i < slugs.length; i++) {
    for (let j = i + 1; j < slugs.length; j++) {
      const a = grams.get(slugs[i]);
      const b = grams.get(slugs[j]);
      let shared = 0;
      for (const g of a) if (b.has(g)) shared++;
      const pct = (100 * shared) / Math.min(a.size, b.size);
      assert.ok(
        pct < 25,
        `${slugs[i]} and ${slugs[j]} share ${pct.toFixed(1)}% of their five-grams`
      );
    }
  }
});

test("each game page names things that only apply to that game", () => {
  // A cheap proxy for "is this really about the game". Generic tuning prose
  // could pass the overlap test by being differently generic.
  const required = {
    "csgo-aim-trainer": ["AK-47", "cm/360", "eDPI", "counter-strafing"],
    "valorant-aim-trainer": ["Vandal", "Phantom", "eDPI", "160 damage"],
    "fortnite-aim-trainer": ["shield", "Build and Edit", "box", "aim assist"],
  };
  for (const [slug, terms] of Object.entries(required)) {
    const html = fs.readFileSync(path.join(REPO, slug, "index.html"), "utf8");
    for (const term of terms) {
      assert.ok(html.includes(term), `${slug} never mentions "${term}"`);
    }
  }
});

/* ============================ structured data ============================ */

test("every JSON-LD block on every page parses", () => {
  let blocks = 0;
  for (const rel of ALL_HTML) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    for (const m of html.matchAll(
      /<script type="application\/ld\+json">([\s\S]*?)<\/script>/g
    )) {
      blocks++;
      try {
        JSON.parse(m[1]);
      } catch (e) {
        assert.fail(`${rel}: ${e.message}`);
      }
    }
  }
  assert.ok(blocks >= 30, `only ${blocks} JSON-LD blocks found`);
});

test("FAQPage schema quotes the questions the page actually shows", () => {
  // Schema that does not match the visible copy is a manual action waiting to
  // happen. Both come from one list in build_drills.py; this proves it.
  for (const rel of ALL_HTML) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    const ld = [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)]
      .map((m) => JSON.parse(m[1]))
      .find((d) => d["@type"] === "FAQPage");
    if (!ld) continue;
    for (const q of ld.mainEntity) {
      const visible = html.includes(`<h3>${q.name}</h3>`) ||
        html.includes(q.name.replace(/'/g, "&#x27;")) ||
        html.includes(q.name.replace(/'/g, "'"));
      assert.ok(visible, `${rel}: schema asks "${q.name}" but the page does not`);
    }
  }
});

test("every page below the root carries a BreadcrumbList", () => {
  for (const rel of ALL_HTML) {
    if (rel === "index.html" || rel === "404.html") continue;
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    assert.ok(html.includes('"BreadcrumbList"'), `${rel} has no BreadcrumbList`);
  }
});

test("the sitemap carries a lastmod for every url", () => {
  const sitemap = fs.readFileSync(path.join(REPO, "sitemap.xml"), "utf8");
  const urls = sitemap.match(/<url>/g) || [];
  const mods = sitemap.match(/<lastmod>\d{4}-\d{2}-\d{2}<\/lastmod>/g) || [];
  assert.strictEqual(mods.length, urls.length, "a url is missing its lastmod");
});

test("every page links its sibling sites, and keeps the erabbit mark", () => {
  for (const rel of ALL_HTML) {
    if (rel === "404.html") continue;
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    assert.ok(html.includes("footer-related"), `${rel} has no related-tools block`);
    assert.match(html, /erabbit-mark[\s\S]*?<\/a>\s*<\/body>/, `${rel}: the mark must be last`);
    // Not a link farm. Four peers, chosen, not enumerated.
    const peers = (html.match(/class="footer-related"[\s\S]*?<\/nav>/) || [""])[0];
    const links = peers.match(/<a /g) || [];
    assert.ok(links.length >= 3 && links.length <= 5, `${rel}: ${links.length} peers is not 3-5`);
  }
});

test("the tracking drill states its touch limitation, and the homepage does not overclaim", () => {
  // The tracking drill samples the cursor from pointermove only, which on a
  // touchscreen fires only while a finger is down — and the finger then covers
  // the target. The page says so rather than quietly scoring 5%.
  const tracking = fs.readFileSync(path.join(REPO, "tracking-trainer/index.html"), "utf8");
  assert.ok(tracking.includes("callout--coarse"), "no touch-device callout");
  assert.match(tracking, /needs a mouse or a trackpad/i, "the limitation is not stated");
  const home = fs.readFileSync(path.join(REPO, "index.html"), "utf8");
  const faq = home.slice(home.indexOf("<h3>Does this work on mobile?</h3>"));
  assert.match(faq.slice(0, 900), /tracking-trainer/, "the blanket yes has no exception");
});

/* ================ the privacy policy points at something real ================

   The policy used to end with "Questions about this policy can be sent to the
   site owner via the contact link in the footer." There was no contact link in
   any footer, so the sentence was false from the day it was written.

   The address is written with HTML numeric character references, so the source
   bytes carry no plain address for a crawler to grep. A browser decodes them
   while parsing, which is why these assertions decode them too. Verified in
   headless Chrome: the anchor's protocol is "mailto:", it takes keyboard
   focus, and the accessibility tree names it with the real address. */

const CONTACT = "hello@goodbotbad.bot";

function decodeEntities(text) {
  return text.replace(/&#(\d+);/g, (_, code) => String.fromCharCode(Number(code)));
}

test("every footer carries a working contact link", () => {
  for (const rel of ALL_HTML) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    const footer = (html.match(/<div class="footer-links">[\s\S]*?<\/div>/) || [])[0];
    assert.ok(footer, `${rel} has no footer-links block`);
    const decoded = decodeEntities(footer);
    assert.ok(decoded.includes(`mailto:${CONTACT}`), `${rel}: no contact link in the footer`);
    assert.ok(/>Contact</.test(decoded), `${rel}: the contact link is not labelled`);
  }
});

test("the address is not sitting in the source as plain text", () => {
  // Light obfuscation only. It stops a crawler that greps the HTML. It does not
  // pretend to stop one that runs a browser, and it must never cost a real
  // visitor the link.
  for (const rel of ALL_HTML) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    assert.ok(!html.includes(CONTACT), `${rel}: plain address in the source`);
  }
});

test("the privacy policy's contact claim is accurate", () => {
  const html = fs.readFileSync(path.join(REPO, "privacy.html"), "utf8");
  const section = (html.match(/<h2>Contact<\/h2>[\s\S]*?<\/p>/) || [""])[0];
  const plain = decodeEntities(section.replace(/<[^>]+>/g, " "));
  assert.ok(plain.includes(CONTACT), "the policy does not name the address");
  assert.ok(/footer/i.test(plain), "the policy does not mention the footer");
  assert.ok(!/contact link in the footer\.\s*<\/p>/.test(html),
    "the old sentence, which pointed at a link that did not exist, is back");
});

test("the footer link set is the same on every page", () => {
  // The legal pages used to swap their own link for a Home link, so "the
  // footer" meant two different things depending on where you were standing.
  let shape = null;
  for (const rel of ALL_HTML) {
    const html = fs.readFileSync(path.join(REPO, rel), "utf8");
    const footer = (html.match(/<div class="footer-links">[\s\S]*?<\/div>/) || [""])[0];
    const labels = [...footer.matchAll(/<a\b[^>]*>(.*?)<\/a>/g)]
      .map((m) => decodeEntities(m[1]).trim()).join(" | ");
    if (shape === null) shape = labels;
    assert.strictEqual(labels, shape, `${rel} has a different footer from the rest`);
  }
  assert.strictEqual(shape, "Privacy | Terms | Contact");
});
