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
index.html            Main app (setup / game / results screens)
articles/              Original written content (AdSense content-depth round)
privacy.html           Privacy policy (required for ad networks)
terms.html             Terms of use
404.html               Custom not-found page
assets/css/styles.css  Design system
assets/js/app.js       Pure scoring/spawn logic + game/DOM wiring
CNAME                   GitHub Pages custom domain (flicktrainer.com)
```

`articles/` holds four original written pieces (reaction-time benchmarks, flicking vs. tracking technique, aim-trainer history, and how this test's scoring works) linked from the homepage's &ldquo;Learn more&rdquo; section and `sitemap.xml`, added to demonstrate genuine content depth beyond the single tool page for AdSense review.

The scoring and game-timing math (accuracy, average reaction time, throughput,
rating-tier lookup, target spawn positioning, shrink-over-time sizing, best-record
updates) lives in dependency-free functions at the top of `assets/js/app.js`,
exported via `module.exports` when `typeof module !== "undefined"` so they can be
sanity-checked from Node before each commit without needing a browser or test
framework installed.

## Enabling ads (Google AdSense)

1. Deploy the site and get it live at flicktrainer.com.
2. Apply at https://adsense.google.com with the live URL. Approval requires a working privacy policy (already included) and some real content/traffic — it isn't instant.
3. Once approved, uncomment the AdSense `<script>` tag in `index.html`'s `<head>` and replace `ca-pub-XXXXXXXXXXXXXXXX` with your publisher ID. Auto ads then places ad units automatically — no manual placement needed.

## Custom domain (flicktrainer.com)

**Note: flicktrainer.com has not been registered/purchased yet.** The `CNAME` file already tells GitHub Pages to serve this repo at that domain, so once the domain is registered, DNS just needs to be pointed at GitHub Pages:

- Apex domain (`flicktrainer.com`): four `A` records to `185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`.
- `www` subdomain (optional): `CNAME` record to `<username>.github.io`.

Then enable Pages in the repo's Settings → Pages, and enter `flicktrainer.com` as the custom domain (GitHub will offer to enforce HTTPS once DNS propagates). Until the domain is registered and DNS is configured, the site remains reachable at its default `github.io` Pages URL.
