# flicktrainer.com

A free, ad-supported browser-based FPS aim training game.

Circular targets pop up at random positions and shrink over their lifespan — click them as fast and accurately as you can. Two modes:

- **Timed**: targets keep spawning for a chosen duration (15s / 30s / 60s), one at a time.
- **Target Count**: the session ends after a fixed number of targets (10 / 30 / 50), regardless of time.

Tracks hits, misses, accuracy, average time-to-click per target, and effective targets/second throughput, then rates the session against tiers (Needs Practice → Superhuman) benchmarked against a casual-player average of ~350-450ms. Best accuracy/avg-time per mode+variant and the last 10 sessions are saved to `localStorage`.

Everything runs client-side — no backend, no build step, no uploads. Deployed as static files on GitHub Pages.

## Local development

No build tooling required. Serve the folder with any static file server, e.g.:

```
python3 -m http.server 8000
```

Then open `http://localhost:8000`.

## Structure

```
index.html            Main app, the flick drill (setup / game / results screens)
gridshot/index.html    The three tier-1 drills, at their clean paths...
tracking-trainer/index.html
precision-trainer/index.html
valorant-aim-trainer/index.html   ...and the three tier-2 game presets.
csgo-aim-trainer/index.html
fortnite-aim-trainer/index.html
gridshot.html          Flat aliases of all six, byte-identical to the above.
tracking-trainer.html  All twelve are OUTPUT of tools/build_drills.py.
precision-trainer.html
valorant-aim-trainer.html
csgo-aim-trainer.html
fortnite-aim-trainer.html
articles/              Original written content (AdSense content-depth round)
privacy.html           Privacy policy (required for ad networks)
terms.html             Terms of use
404.html               Custom not-found page
assets/css/styles.css  Design system
assets/js/app.js       Pure scoring/spawn logic + game/DOM wiring
tools/nav_data.py      The nav's single source of truth
tools/sync_nav.py      Renders the toolbar into every .html between markers
tools/build_drills.py  Renders the drill + preset pages from one shared shell
test/scoring.test.js   node:test coverage for the scoring and the built pages
CNAME                   GitHub Pages custom domain (flicktrainer.com)
```

The trainer runs **four drills** off one engine, selected by `data-engine` on
`<body>`, each reporting a different unit: flick (average time-to-click),
gridshot (targets per second), tracking (percent of the session on target) and
precision (accuracy). Three further pages are the flick drill retuned per game
via `data-preset`, with their target size and lifespan stated on the page.

`articles/` holds four original written pieces (reaction-time benchmarks, flicking vs. tracking technique, aim-trainer history, and how this test's scoring works) linked from the homepage's &ldquo;Learn more&rdquo; section and `sitemap.xml`, added to demonstrate genuine content depth beyond the single tool page for AdSense review.

The scoring and game-timing math (accuracy, average reaction time, throughput,
rating-tier lookup, target spawn positioning, shrink-over-time sizing, best-record
updates, and the drill engines' grid geometry, tracking path and per-engine rating
ladders) lives in dependency-free functions at the top of `assets/js/app.js`,
exported via `module.exports` when `typeof module !== "undefined"`.

## Tests

```
node --test test/scoring.test.js
```

No `package.json` and no dependencies — `node:test` and `node:assert` only. It
covers the pure helpers (a tracking target that can never leave the playfield at
any moment, a grid whose cells never collide, ladders that are monotone in the
right direction for each drill's own unit) and the twelve generated pages (pairs
byte-identical, one ad tag, mark last in body, no external requests, every
element the engine reads unguarded, sitemap entry present, unique title and
canonical).

The drill and preset pages are generated. Regenerate and re-sync the nav after
editing `tools/build_drills.py`:

```
python3 tools/build_drills.py && python3 tools/sync_nav.py
python3 tools/build_drills.py --check && python3 tools/sync_nav.py --check
```

Both scripts are order-independent and idempotent, and both `--check` modes run
inside the node suite.

## Enabling ads (Google AdSense)

1. Deploy the site and get it live at flicktrainer.com.
2. Apply at https://adsense.google.com with the live URL. Approval requires a working privacy policy (already included) and some real content/traffic — it isn't instant.
3. Once approved, uncomment the AdSense `<script>` tag in `index.html`'s `<head>` and replace `ca-pub-XXXXXXXXXXXXXXXX` with your publisher ID. Auto ads then places ad units automatically — no manual placement needed.

## Custom domain (flicktrainer.com)

**Note: flicktrainer.com has not been registered/purchased yet.** The `CNAME` file already tells GitHub Pages to serve this repo at that domain, so once the domain is registered, DNS just needs to be pointed at GitHub Pages:

- Apex domain (`flicktrainer.com`): four `A` records to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
- `www` subdomain (optional): `CNAME` record to `<username>.github.io`.

Then enable Pages in the repo's Settings → Pages, and enter `flicktrainer.com` as the custom domain (GitHub will offer to enforce HTTPS once DNS propagates). Until the domain is registered and DNS is configured, the site remains reachable at its default `github.io` Pages URL.
