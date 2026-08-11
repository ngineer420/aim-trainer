# flicktrainer.com — working notes for Claude

Free browser **aim trainer** (targets pop up, click them fast and accurately;
tracks accuracy + average time-to-click, rates you Needs Practice → Superhuman)
built as a **true pixel-art arcade LIGHT-GUN SHOOTER cabinet**. Static,
zero-dependency site: vanilla HTML/CSS/JS, no build step, GitHub Pages
(`CNAME` → flicktrainer.com, Cloudflare DNS). Everything runs client-side;
nothing is uploaded.

## Files

- `index.html` — the whole game UI (the cabinet) + About/FAQ + article list.
  Articles in `articles/`. `privacy.html` / `terms.html` / `404.html` too.
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
- `assets/fonts/pressstart2p.woff2` — self-hosted pixel font (see below).

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
  restyles/rewraps these — it doesn't rename them.
- **Do not duplicate input handlers.** The target has its own `pointerdown`
  listener and `.game-area` has one empty-space `pointerdown` listener — keep
  pointer handling as-is. **`pointerdown`, never `click`:** it fires on press
  rather than release, so it doesn't fold the user's mouse-release time into a
  millisecond-scale reading, and pointer events already unify mouse/touch/pen so
  a second listener would double-count. The siblings sample the same way.
- **Cache-bust:** `styles.css?v=` and `app.js?v=` on **every** HTML page
  (index, 404, privacy, terms, articles/*). **Bump the `?v=` on any coupled
  HTML+CSS/JS change** or cached visitors get new HTML with stale CSS = a broken
  raw page. Currently `?v=4`.
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

`ft-theme` (light/dark), `flicktrainer:best:<mode>:<variant>` (per-mode best
accuracy + avg time), `flicktrainer:history` (last 10 sessions),
`flicktrainer:profile` (XP / sessions / streak / unlocked achievements),
`flicktrainer:sound-muted`.

## Shipping

Worktree under `.claude/worktrees/`, open a PR, **merge** when done (currently
"merge as they land"). Never push straight to `main`; never force-push. Verify
with a headless render of the idle screen; force the live-range and results
states via a **throwaway preview** (copy index.html, drop the `app.js`
`<script>`, un-hide `#screen-game`/`#screen-results`, inject a couple `.target`
sprites + a `.hit-spark` + a combo value) since `--screenshot` can't drive the
game. Delete previews before committing.
