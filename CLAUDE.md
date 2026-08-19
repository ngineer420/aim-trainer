# flicktrainer.com — working notes for Claude

Free browser **aim trainer** (targets pop up, click them fast and accurately;
tracks accuracy + average time-to-click, rates you Needs Practice → Superhuman)
built as a **true pixel-art arcade LIGHT-GUN SHOOTER cabinet**. Static,
zero-dependency site: vanilla HTML/CSS/JS, no build step, GitHub Pages
(`CNAME` → flicktrainer.com, Cloudflare DNS). Everything runs client-side;
nothing is uploaded.

## Four drills and three game presets — `data-engine` / `data-preset` on `<body>`

One engine file, seven playable pages. `document.body.dataset.engine` picks the
drill and `data-preset` optionally retunes the flick spawner; both absent is the
original trainer at `/`, so index.html behaves exactly as it did.

| `data-engine` | page | spawner | headline number |
|---|---|---|---|
| (none) / `flick` | `/` | one shrinking target, random position | avg time-to-click (ms) |
| `gridshot` | `/gridshot/` | fixed 3×3, three live, no expiry | targets/second |
| `tracking` | `/tracking-trainer/` | one target on a smooth path | % time on target |
| `precision` | `/precision-trainer/` | one small static target, long life | accuracy % |

| `data-preset` | page | start / end / life |
|---|---|---|
| `valorant` | `/valorant-aim-trainer/` | 44px → 30px, 1100ms |
| `csgo` | `/csgo-aim-trainer/` | 52px → 38px, 1500ms |
| `fortnite` | `/fortnite-aim-trainer/` | 68px → 44px, 900ms |

`ENGINE_CONFIG` and `PRESETS` at the top of the IIFE own every difference. Things
that follow from that and must not be undone:

- **`ENGINE_RATINGS` keys each drill's ladder to the number it actually
  reports.** Only flick is read downwards (`lowerIsBetter`); a drill scored on a
  rate or a percentage must never inherit "lower is better".
- **Gridshot and tracking ship no mode selector.** Both are scored over a session
  length, so "30 targets" is not a run they can do — and `endSession` is only
  reachable from the timed clock for those spawners, so a count-mode gridshot
  would never end. Duration options only. `#count-options` may only ship where a
  `.mode-opt` exists, because the mode handler writes to it unguarded.
- **Tracking registers no hits and no misses**, so its accuracy is 0/0. Never
  print it — a fabricated zero is worse than an omitted tile. Its HUD and results
  show time-on-target and nothing else.
- **Gridshot targets never expire**, so a miss there is only ever a shot that
  landed on empty space, and its accuracy means shot discipline rather than
  keeping up with a spawn timer.
- **Per-drill history keys** (see localStorage below). One shared 10-entry list
  meant a gridshot run evicted the tracking run before it.
- The progression layer (XP, streak, achievements) is deliberately **shared**
  across all seven pages: it is one marksman card, not one per drill. Bear in
  mind some thresholds were tuned for flick and are easier on gridshot.

## The drill and preset pages are GENERATED

`tools/build_drills.py` renders all twelve files (six clean paths + six
byte-identical flat aliases). **Edit that script, never the HTML it writes** —
`node --test test/scoring.test.js` runs `--check` and fails on a hand-edit.

```
python3 tools/build_drills.py && python3 tools/sync_nav.py
```

Order-independent and idempotent: `build_drills.py` carries whatever sync_nav has
put between the nav markers straight across. `index.html` is NOT generated; it is
the one page whose markup is not a variation on anything.

The canonical on every generated page is the **directory** form, and that is
load-bearing rather than cosmetic: `app.js` reads the challenge-link base off
`link[rel=canonical]`, so a flat canonical would mint `…/gridshot.html?ms=` links.

## Files

- `index.html` — the whole game UI (the cabinet) + About/FAQ + article list.
  Articles in `articles/`. `privacy.html` / `terms.html` / `404.html` too.
- `gridshot/`, `tracking-trainer/`, `precision-trainer/`,
  `valorant-aim-trainer/`, `csgo-aim-trainer/`, `fortnite-aim-trainer/` plus
  their flat `.html` aliases — **output of `tools/build_drills.py`**.
- `test/scoring.test.js` — `node --test test/scoring.test.js`. No package.json,
  no dependencies.
- `assets/js/app.js` — **pure, DOM-free stats/rating helpers up top**
  (`calcAccuracy`, `calcAverageReactionTime`, `calcThroughput`,
  `targetSizeAtElapsed`, `randomTargetPosition`, `getRatingTier`,
  `buildSessionSummary`, `updateBestRecord`, `RATING_TIERS` — `module.exports`
  for Node sanity checks), then one IIFE with the screen state machine, the
  target spawn/shrink/resolve loop, localStorage bests + history, and the
  flavour layer (combo streak + hit-sparks).
- `assets/css/styles.css` — the whole design system, one file. The base theme is
  at the top; the **"FLICK TRAINER — full pixel-art arcade LIGHT-GUN cabinet"**
  block at the very bottom is the arcade skin (overrides base for the cabinet).
- `assets/js/nav.js` — loaded by **every** page: the theme toggle (moved out of
  app.js, which only index.html loads) plus the portfolio toolbar's fades,
  active-chip centring, Escape and click-outside. Pure enhancement — the nav is
  fully usable with JS off.
- `assets/fonts/pressstart2p.woff2` — self-hosted pixel font (see below).
- `tools/sync_nav.py` + `tools/nav_data.py` — the nav is **generated**, not
  hand-pasted (see below).

## The chrome is one shared block — never hand-edit it

Eight hand-duplicated .html files used to carry two drifting header variants.
They now carry one: identical skip link, identical `<header class="site-header">`
with the same brand markup and a `#theme-toggle`, then the toolbar. Only
index.html adds `#status-chip` and `#sound-toggle` inside `.header-actions`,
because those drive app.js and app.js is only on the game page.

The `<nav class="toolbar">` between `<!-- nav:start -->` and `<!-- nav:end -->` is
rendered by `python3 tools/sync_nav.py` from `tools/nav_data.py` — the four
guides are the rail, the sheet is those four plus a hub link back to the trainer.
`sync_nav.py` is copied verbatim across the portfolio (**do not modify it**);
`nav_data.py` is the only per-site file. Edit the nav there and re-run, never by
hand in eight files. `python3 tools/sync_nav.py --check` exits nonzero on drift —
run it before shipping. Spec: ngineer420/ngineer420.github.io#13.

**Neither the header nor the toolbar is sticky**, and neither may become sticky:
nothing in the chrome may overlay an AdSense anchor unit. The header is a fixed
54px and the bar 45px, so closed chrome is 99px on every page, under the
portfolio's 100px budget — check with a measurement, not by eye, before adding
anything to either.

## Design language — the pixel-art light-gun cabinet

Bar = **metekamil.com** (full-screen true pixel-art arcade screen). This is a
genuine 8-bit cabinet, not "web pretending to be arcade":

- **Self-hosted pixel font** `assets/fonts/pressstart2p.woff2` (Press Start 2P,
  OFL) via `@font-face "PixArc"`, applied to all arcade chrome text. This is the
  one deliberate exception to "system-fonts only" — it is **same-origin**, so it
  still makes **no third-party request** (the privacy intent of the rule holds).
- **Pixel-art discipline**: FLAT colours, HARD pixel edges (layered
  `box-shadow` borders, `border-radius:0`), `image-rendering: pixelated`, hard
  offset `text-shadow` (no `-webkit-text-stroke`, no `skewX`, no blurred glows).
  An animated diagonal-stripe backdrop on `.crt-screen` (`stripe-scroll`).
- **Full cabinet**: `.cabinet` → `.marquee` (pixel "FLICK TRAINER" logo) →
  `.crt`/`.crt-screen` (the shooting range) → `.deck` (chunky pixel controls).
  All three app screens (`#screen-setup` / `#screen-game` / `#screen-results`)
  live inside one persistent `.cabinet` under the marquee; the JS still toggles
  them via `hidden`, so the structure is unchanged.

**This cabinet's genre flavour = LIGHT-GUN SHOOTER** (Time Crisis / Point Blank /
House of the Dead). Siblings share the arcade chrome but each is a *different*
genre so they never feel like clones — reflexzap = quick-draw duel
(yellow/purple), cpsboost = fighting game (pink), wpmflex = type-rush
(cyan/green). flicktrainer's distinct bits:
- **RED/ORANGE danger palette** (scoped as `--pa*` custom props on `.cabinet`
  so the article pages keep the base theme untouched).
- The CRT is the **shooting range**: a grid "range floor" with a **custom pixel
  crosshair cursor** (inline-SVG data URI, `crispEdges`) and **pixel bullseye
  target sprites** (`.target` / `.pix-target` — concentric hard box-shadow rings,
  red/white/yellow).
- Idle = an **attract/title screen** ("DEAD-EYE RANGE" + blinking INSERT COIN).
- Live HUD strip (`.range-hud`): TIME/HITS/MISS/ACC + a **COMBO streak**.
- Results = a **STAGE CLEAR** banner + a big pixel **letter GRADE stamp**
  (`#rating-tier`, S/A/B/… from `RATING_TIERS`) + "RELOAD" button.

## The flavour layer (app.js) — never touches the measurement

`combo`, `setCombo()`, `spawnSpark()` are **pure cosmetics** layered on top of
the existing hit/miss resolution:
- On a hit: spawn a `.hit-spark` burst at the target centre + `setCombo(combo+1)`.
- On a miss (target timed out, or an empty-space whiff): `setCombo(0)`.
- Reset to 0 at `startSession()`.
They read from, but never write to, `session.hits` / `session.reactionTimes` /
`session.misses`. `#hud-combo` / `#combo-wrap` are the only new DOM ids.

## Hard rules (don't regress)

- **The accuracy/timing math is sacred.** Average time-to-click =
  `performance.now()` at the click minus the target's `spawnedAt`; accuracy =
  hits/(hits+misses). The pure helpers are DOM-free and Node-checkable. The HUD,
  crosshair, combo, sprites, and grade are flavour and must **never** feed back
  into hits/misses/reactionTimes.
- **Keep every element id the JS relies on** (enumerate by reading app.js):
  `screen-setup/game/results`, `.mode-opt[data-mode]` / `.duration-opt[data-duration]`
  / `.count-opt[data-count]`, `timed-options` / `count-options`,
  `best-accuracy-val` / `best-avgtime-val`, `start-btn` / `restart-btn` /
  `change-mode-btn` / `quit-btn`, `game-area`, `hud-primary-label/-val`,
  `hud-hits/-misses/-accuracy`, `rating-tier/-label`, `rating-compare`,
  `res-hits/-misses/-accuracy/-avgtime/-throughput/-best-avgtime`,
  `new-best-flag`, `history-chart` / `history-list`. The arcade skin only
  restyles/rewraps these — it doesn't rename them. The drills add three more,
  all optional and all `if (el)`-guarded: `hud-ontarget`, `res-ontarget`,
  `res-best-primary` / `best-primary-val`.
  **Which of these are actually required is asserted in `test/scoring.test.js`** —
  a page missing an unguarded one throws on load and the drill is simply dead,
  which is not visible from reading the page.
- **Do not duplicate input handlers.** The target has its own `pointerdown`
  listener and `.game-area` has one empty-space `pointerdown` listener — keep
  pointer handling as-is. **`pointerdown`, never `click`:** it fires on press
  rather than release, so it doesn't fold the user's mouse-release time into a
  millisecond-scale reading, and pointer events already unify mouse/touch/pen so
  a second listener would double-count. The siblings sample the same way.
- **Cache-bust:** `styles.css?v=` and `app.js?v=` on **every** HTML page
  (index, 404, privacy, terms, articles/*), and `nav.js?v=` alongside them.
  **Bump the `?v=` on any coupled
  HTML+CSS/JS change** or cached visitors get new HTML with stale CSS = a broken
  raw page. Currently `?v=6`.
- **Ads: AdSense Auto ads only.** Single commented `<script>` in `<head>`
  (client `ca-pub-7560786263587509`). **NEVER add `.ad-slot` divs** or manual
  units.
- **Zero external requests.** No webfonts/CDNs/beacons (the pixel font is
  same-origin). Light **and** dark themes must both work — the cabinet palette is
  self-contained so it renders identically in both; only the page chrome flips.
- **Respect `prefers-reduced-motion`** — every animation (stripe-scroll, blink,
  combo pulse, hit-spark, target-hit) has a reduce fallback at the bottom of the
  pixel block.
- The `erabb.it` 🐇 mark is the portfolio signature — **last in `<body>`**, flush
  to the corner, `cursor: default`.

## The progression layer (app.js) — also never touches the measurement

Ported from the sibling cabinets so all three sites share one engagement model.
It only *reads* a finished session's summary; it never feeds hits/misses/times.

- **XP / levels / ranks** — `xpForLevel` (`50·L·(L-1)`), `levelForXp`,
  `titleForLevel`, `RANK_TITLES` (10 levels, Rookie → Dead-Eye God). XP is
  weighted by the session's rating tier (`TIER_XP`) with bonuses for beating a
  personal best, finishing a 60s run, a 20+ combo, and 90%+ accuracy.
- **14 `ACHIEVEMENTS`**, each a `{id, icon, title, desc, check(ctx)}`; `ctx`
  carries accuracy / avgReaction / hits / misses / maxCombo / totalSessions /
  pbBeatenCount / streak / completedSixty / level.
- **Daily streak** — `updateStreak()`; consecutive days extend it, a gap resets
  it to 1, replaying the same day is a no-op.
- **WebAudio synth** — `playTone()` + named blips (`playHitShot`,
  `playMissThud`, `playStageClear`, `playAchievementChime`,
  `playLevelUpFanfare`, `playNewBestSparkle`). Oscillators only, so the site
  still ships **zero binary audio assets**. Muting persists; `#sound-toggle`.
  The miss thud fires only on a real whiff, never on a target timing out —
  unprompted noise for a non-action is worse than silence.
- **Share string** — `#share-btn` copies an accuracy/time/rank line via
  `navigator.clipboard` with a `document.execCommand` fallback, `#toast` confirms.

New DOM ids: `status-chip`/`chip-level`/`chip-streak`, `sound-toggle`,
`xp-rank-label`/`xp-progress-label`/`xp-bar-fill`,
`achievements-panel`/`achievements-grid`, `unlock-stack`, `toast`, `share-btn`.

## Friend challenge links (URL state)

A shared result is a **URL**, not a dead text blob. `#share-btn` copies
`https://flicktrainer.com/?ms=<avg>&acc=<pct>&mode=<timed|count>&v=<variant>`;
opening that link preselects the sender's mode + variant, shows
`#challenge-banner` under the marquee (visible on every screen, since it's a
sibling of the three `.screen` sections), and renders `#challenge-verdict`
(`.is-win` / `.is-loss`) on the results deck once a session ends.

- `ms` — must be finite and within `50 <= ms <= 5000`, else no challenge.
- `mode` — `count` or anything else falls back to `timed`.
- `v` — must be in `CHALLENGE_VARIANTS[mode]` (`timed`: 15/30/60,
  `count`: 10/30/50), else falls back to that mode's middle option.
- `acc` — optional, `0..100`; it's context in the banner only.
- **Average time-to-click is the metric the verdict compares** (it's what the
  rating tiers key off); accuracy rides along as flavour. **Lower is better**,
  so `diff < 0` is the win branch — same as reflexzap, inverted vs cpsboost.
- **Validate every param before use.** A hand-edited or hostile query string
  must only ever degrade to "no challenge"; banner text is set via
  `textContent` so it can't inject markup.
- `applyChallenge()` drives the existing `.mode-opt` / `.duration-opt` /
  `.count-opt` buttons via `.click()` rather than duplicating their state, so a
  challenge link leaves the UI exactly as a manual click would (including
  `refreshBestRow()`).

## localStorage keys

`ft-theme` (light/dark), `flicktrainer:profile` (XP / sessions / streak /
unlocked achievements — shared across every drill), `flicktrainer:sound-muted`.

Scoped per drill, so a targets-per-second run can never be compared against a
millisecond one:

- `flicktrainer:best:<scope><mode>:<variant>` where `<scope>` is `""` for the
  original flick drill, `<preset>:` on a preset page, else `<engine>:`. A preset
  wins over the engine, because a preset page's numbers really are its own.
- `flicktrainer:history` for flick and its presets — the legacy unscoped key, so
  nobody loses the sessions they already have — and `flicktrainer:history:<engine>`
  for each of the other drills.

## Shipping

Worktree under `.claude/worktrees/`, open a PR, **merge** when done (currently
"merge as they land"). Never push straight to `main`; never force-push. Verify
with a headless render of the idle screen; force the live-range and results
states via a **throwaway preview** (copy index.html, drop the `app.js`
`<script>`, un-hide `#screen-game`/`#screen-results`, inject a couple `.target`
sprites + a `.hit-spark` + a combo value) since `--screenshot` can't drive the
game. Delete previews before committing.
