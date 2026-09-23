(() => {
  "use strict";

  /* ============================================================
     PURE, DOM-INDEPENDENT LOGIC
     Everything in this block takes plain values in and returns plain
     values out — no `document`, no `window`. Sanity-checked with a
     throwaway Node script before commit; safe to unit test forever.
     ============================================================ */

  /** Accuracy percentage from hit/miss counts. 0 hits+misses -> 0 (not NaN). */
  function calcAccuracy(hits, misses) {
    const total = hits + misses;
    if (total <= 0) return 0;
    return (hits / total) * 100;
  }

  /** Mean of an array of per-target reaction times (ms). Empty/missing -> null. */
  function calcAverageReactionTime(reactionTimes) {
    if (!Array.isArray(reactionTimes) || reactionTimes.length === 0) return null;
    const sum = reactionTimes.reduce((a, b) => a + b, 0);
    return sum / reactionTimes.length;
  }

  /** Effective hits-per-second over the session's wall-clock duration. */
  function calcThroughput(hits, elapsedMs) {
    if (!elapsedMs || elapsedMs <= 0) return 0;
    return hits / (elapsedMs / 1000);
  }

  /** Diameter (px) of a target at `elapsedMs` into its lifespan; clamps to [0,1]. */
  function targetSizeAtElapsed(elapsedMs, lifespanMs, startDiameter, endDiameter) {
    if (!lifespanMs || lifespanMs <= 0) return endDiameter;
    const t = Math.min(1, Math.max(0, elapsedMs / lifespanMs));
    return startDiameter + (endDiameter - startDiameter) * t;
  }

  /**
   * Random center position for a target fully inside an areaWidth x areaHeight
   * rectangle. `rng` is injectable (defaults to Math.random) so callers can
   * pass a seeded generator for deterministic tests.
   */
  function randomTargetPosition(areaWidth, areaHeight, targetDiameter, rng) {
    const random = typeof rng === "function" ? rng : Math.random;
    const availW = Math.max(0, areaWidth - targetDiameter);
    const availH = Math.max(0, areaHeight - targetDiameter);
    const radius = targetDiameter / 2;
    return {
      x: radius + random() * availW,
      y: radius + random() * availH,
    };
  }

  /** Percent of a session spent with the cursor inside the tracking target. */
  function calcTimeOnTarget(onTargetMs, elapsedMs) {
    if (!elapsedMs || elapsedMs <= 0) return 0;
    return Math.min(100, Math.max(0, (onTargetMs / elapsedMs) * 100));
  }

  /** Centres of a cols x rows grid filling an area, row-major. Gridshot's nine
      slots: fixed, so every target appears at one of nine known places and the
      drill trains flicks between known points rather than visual search. */
  function gridCellCenters(areaWidth, areaHeight, cols, rows) {
    const out = [];
    const cw = areaWidth / cols;
    const ch = areaHeight / rows;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) out.push({ x: (c + 0.5) * cw, y: (r + 0.5) * ch });
    }
    return out;
  }

  /** Largest target that sits inside a grid cell with room around it. */
  function gridTargetDiameter(areaWidth, areaHeight, cols, rows) {
    const cell = Math.min(areaWidth / cols, areaHeight / rows);
    return Math.max(24, Math.min(84, cell * 0.62));
  }

  /**
   * Where the tracking target is at `tMs` into the session.
   *
   * Two sine components per axis at incommensurate frequencies: the sum never
   * repeats inside a session, has no corners for the cursor to cut, and is a
   * pure function of time — so the path can be checked from Node and the
   * render loop never has to remember where the target was last frame.
   * Amplitudes total 1, so the normalised coordinate stays in [0, 1] and the
   * target can never leave the box.
   */
  function trackingPathPoint(tMs, path, areaWidth, areaHeight, diameter) {
    const r = diameter / 2;
    const availW = Math.max(0, areaWidth - diameter);
    const availH = Math.max(0, areaHeight - diameter);
    const t = tMs / 1000;
    const ux = 0.5 + 0.5 * (0.62 * Math.sin(path.wx1 * t + path.px1) + 0.38 * Math.sin(path.wx2 * t + path.px2));
    const uy = 0.5 + 0.5 * (0.62 * Math.sin(path.wy1 * t + path.py1) + 0.38 * Math.sin(path.wy2 * t + path.py2));
    return {
      x: r + Math.min(1, Math.max(0, ux)) * availW,
      y: r + Math.min(1, Math.max(0, uy)) * availH,
    };
  }

  /** A fresh randomised path. `rng` is injectable so a check can pin it. */
  function randomTrackingPath(rng) {
    const random = typeof rng === "function" ? rng : Math.random;
    const band = (lo, hi) => lo + random() * (hi - lo);
    const phase = () => random() * Math.PI * 2;
    return {
      wx1: band(0.30, 0.55), wx2: band(0.75, 1.25), px1: phase(), px2: phase(),
      wy1: band(0.35, 0.60), wy2: band(0.85, 1.40), py1: phase(), py2: phase(),
    };
  }

  /** Is a point inside a circular target of `diameter` centred on cx, cy? */
  function isInsideTarget(px, py, cx, cy, diameter) {
    const dx = px - cx;
    const dy = py - cy;
    const r = diameter / 2;
    return dx * dx + dy * dy <= r * r;
  }

  /**
   * Best-so-far for an engine's headline number, in whichever direction counts
   * as better for that engine. Split from updateBestRecord because accuracy
   * and average time are not the headline on every drill: gridshot's is
   * targets/second and tracking's is percent time-on-target.
   */
  function updateBestMetric(prevBest, value, lowerIsBetter) {
    const prev = typeof prevBest === "number" && !Number.isNaN(prevBest) ? prevBest : null;
    if (value == null || Number.isNaN(value)) return { best: prev, improved: false };
    if (prev === null) return { best: value, improved: true };
    const better = lowerIsBetter ? value < prev : value > prev;
    return { best: better ? value : prev, improved: better };
  }

  // Rating tiers keyed by average reaction time (ms). Ordered fastest-first;
  // first tier whose `max` the average is <= wins. Casual players typically
  // average ~350-450ms, which straddles the Solid/Casual tiers below.
  const RATING_TIERS = [
    { max: 220, tier: "S", label: "Superhuman" },
    { max: 280, tier: "A+", label: "Elite" },
    { max: 340, tier: "A", label: "Sharp" },
    { max: 400, tier: "B", label: "Solid" },
    { max: 460, tier: "C", label: "Casual" },
    { max: 550, tier: "D", label: "Developing" },
    { max: Infinity, tier: "E", label: "Needs Practice" },
  ];

  /* The other three drills measure different motor skills in different units,
     so they cannot share the millisecond ladder above. Each has its own, in the
     same seven-tier shape, ordered best-first and read with `min`. These are
     calibrated against the drills as they are configured here — target size,
     lifespan, grid spacing — and are a difficulty curve, not a measurement of
     any population. */
  const GRIDSHOT_TIERS = [
    { min: 2.2, tier: "S", label: "Superhuman" },
    { min: 1.8, tier: "A+", label: "Elite" },
    { min: 1.5, tier: "A", label: "Sharp" },
    { min: 1.2, tier: "B", label: "Solid" },
    { min: 0.9, tier: "C", label: "Casual" },
    { min: 0.6, tier: "D", label: "Developing" },
    { min: -Infinity, tier: "E", label: "Needs Practice" },
  ];

  const TRACKING_TIERS = [
    { min: 85, tier: "S", label: "Superhuman" },
    { min: 75, tier: "A+", label: "Elite" },
    { min: 65, tier: "A", label: "Sharp" },
    { min: 52, tier: "B", label: "Solid" },
    { min: 40, tier: "C", label: "Casual" },
    { min: 25, tier: "D", label: "Developing" },
    { min: -Infinity, tier: "E", label: "Needs Practice" },
  ];

  const PRECISION_TIERS = [
    { min: 95, tier: "S", label: "Superhuman" },
    { min: 90, tier: "A+", label: "Elite" },
    { min: 84, tier: "A", label: "Sharp" },
    { min: 76, tier: "B", label: "Solid" },
    { min: 66, tier: "C", label: "Casual" },
    { min: 52, tier: "D", label: "Developing" },
    { min: -Infinity, tier: "E", label: "Needs Practice" },
  ];

  /* Which number each drill is rated on, and which way is better. Flick is the
     original engine and keeps the original ladder untouched. */
  const ENGINE_RATINGS = {
    flick: { key: "avgReaction", lowerIsBetter: true, tiers: RATING_TIERS },
    precision: { key: "accuracy", lowerIsBetter: false, tiers: PRECISION_TIERS },
    gridshot: { key: "throughput", lowerIsBetter: false, tiers: GRIDSHOT_TIERS },
    tracking: { key: "onTargetPct", lowerIsBetter: false, tiers: TRACKING_TIERS },
  };

  /** Rating tier for a finished summary under a given engine's ladder. */
  function getRatingForEngine(summary, engine) {
    const cfg = ENGINE_RATINGS[engine] || ENGINE_RATINGS.flick;
    const v = summary ? summary[cfg.key] : null;
    if (v == null || Number.isNaN(v)) return { tier: "—", label: "No data" };
    for (const t of cfg.tiers) {
      if (cfg.lowerIsBetter ? v <= t.max : v >= t.min) return t;
    }
    return cfg.tiers[cfg.tiers.length - 1];
  }

  const CASUAL_AVG_LOW = 350;
  const CASUAL_AVG_HIGH = 450;

  /** Looks up the rating tier object for a given average reaction time (ms). */
  function getRatingTier(avgReactionMs) {
    if (avgReactionMs == null || Number.isNaN(avgReactionMs)) {
      return { tier: "—", label: "No data" };
    }
    for (const t of RATING_TIERS) {
      if (avgReactionMs <= t.max) return t;
    }
    return RATING_TIERS[RATING_TIERS.length - 1];
  }

  /** A plain-language sentence comparing avgReactionMs to the casual-player band. */
  function compareToAverage(avgReactionMs) {
    if (avgReactionMs == null || Number.isNaN(avgReactionMs)) {
      return "Play a session to see how you compare to the average player.";
    }
    const ms = Math.round(avgReactionMs);
    if (avgReactionMs < CASUAL_AVG_LOW) {
      const pct = Math.round((1 - avgReactionMs / CASUAL_AVG_HIGH) * 100);
      return `Casual players average ${CASUAL_AVG_LOW}-${CASUAL_AVG_HIGH}ms — your ${ms}ms average is well ahead of that.`;
    }
    if (avgReactionMs <= CASUAL_AVG_HIGH) {
      return `Right in the typical casual range of ${CASUAL_AVG_LOW}-${CASUAL_AVG_HIGH}ms (your average: ${ms}ms).`;
    }
    return `Casual players average ${CASUAL_AVG_LOW}-${CASUAL_AVG_HIGH}ms — your ${ms}ms average has room to catch up. Keep training!`;
  }

  /** A plain-language sentence for the drills the millisecond ladder does not
      describe. Same job as compareToAverage, one per engine. */
  function compareForEngine(summary, engine) {
    if (!summary) return "";
    if (engine === "gridshot") {
      const tps = summary.throughput;
      if (!tps) return "Clear some targets to see how your rate compares.";
      return `You cleared ${tps.toFixed(2)} targets per second. Steady grid shooting sits around 1.2-1.5/s; past 1.8/s you are flicking without hunting for the next target.`;
    }
    if (engine === "tracking") {
      const pct = summary.onTargetPct || 0;
      return `Your crosshair was inside the target for ${pct.toFixed(1)}% of the session. Around 50-65% is solid smooth tracking; past 75% means you are leading the target rather than chasing it.`;
    }
    if (engine === "precision") {
      const acc = summary.accuracy || 0;
      return `You hit ${acc.toFixed(1)}% of what you shot at. Precision is scored on that first: a slow, clean run beats a fast, sloppy one here, which is the opposite of the flick drill.`;
    }
    return compareToAverage(summary.avgReaction);
  }

  /** Builds the full stat summary for a finished session from raw counters.
      `engine` and `onTargetMs` default so the original call site is unchanged. */
  function buildSessionSummary({ hits, misses, reactionTimes, elapsedMs, onTargetMs, engine }) {
    const accuracy = calcAccuracy(hits, misses);
    const avgReaction = calcAverageReactionTime(reactionTimes);
    const throughput = calcThroughput(hits, elapsedMs);
    const onTargetPct = onTargetMs == null ? null : calcTimeOnTarget(onTargetMs, elapsedMs);
    const summary = { hits, misses, accuracy, avgReaction, throughput, onTargetPct, elapsedMs };
    summary.rating = engine ? getRatingForEngine(summary, engine) : getRatingTier(avgReaction);
    return summary;
  }

  /**
   * Given a previous best record ({accuracy, avgTime} or null) and a fresh
   * session summary, returns the updated best record plus whether either
   * stat improved (a "new best"). Accuracy: higher is better. Avg time:
   * lower is better, and only counts if the session had at least one hit.
   */
  function updateBestRecord(prevBest, summary) {
    const prev = prevBest || { accuracy: 0, avgTime: null };
    let bestAccuracy = prev.accuracy || 0;
    let bestAvgTime = typeof prev.avgTime === "number" ? prev.avgTime : null;
    let improved = false;

    if (summary.accuracy > bestAccuracy) {
      bestAccuracy = summary.accuracy;
      improved = true;
    }
    if (summary.avgReaction != null) {
      if (bestAvgTime == null || summary.avgReaction < bestAvgTime) {
        bestAvgTime = summary.avgReaction;
        improved = true;
      }
    }
    return { record: { accuracy: bestAccuracy, avgTime: bestAvgTime }, improved };
  }

  /* A run that the browser stopped rendering is not a run.
     `tick()` re-arms itself with requestAnimationFrame, and a hidden tab stops
     delivering animation frames. The target expiry timer is a setTimeout, and a
     hidden tab keeps firing that. So a backgrounded run kept counting misses
     and never reached endSession(): a 15s run hidden at t=1s still sat on the
     game screen at t=31s with 23 misses on the board. The clock had read 0.0s
     for fifteen seconds.

     The measurement cannot be salvaged after the fact. Time-to-click is read
     from performance.now(), which does not pause, so every target that expired
     while the tab was hidden is a miss the user never saw and never had the
     chance to take. Time-on-target is worse: the tracking loop simply did not
     run. So the run is abandoned rather than scored, and nothing is written to
     localStorage.

     Pure so the rule can be asserted without a browser. */
  function shouldAbandonRun(visibilityState, runIsLive) {
    return runIsLive === true && visibilityState === "hidden";
  }

  const PURE = {
    shouldAbandonRun,
    calcAccuracy,
    calcAverageReactionTime,
    calcThroughput,
    calcTimeOnTarget,
    targetSizeAtElapsed,
    randomTargetPosition,
    gridCellCenters,
    gridTargetDiameter,
    trackingPathPoint,
    randomTrackingPath,
    isInsideTarget,
    getRatingTier,
    getRatingForEngine,
    compareToAverage,
    compareForEngine,
    buildSessionSummary,
    updateBestRecord,
    updateBestMetric,
    RATING_TIERS,
    GRIDSHOT_TIERS,
    TRACKING_TIERS,
    PRECISION_TIERS,
    ENGINE_RATINGS,
    CASUAL_AVG_LOW,
    CASUAL_AVG_HIGH,
  };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = PURE;
  }

  /* ============================================================
     DOM / GAME WIRING
     Everything below touches the document and is skipped entirely
     when this file is `require()`d from Node for the pure-function
     sanity checks above.
     ============================================================ */

  if (typeof document === "undefined") return;

  const STORAGE_PREFIX = "flicktrainer:";
  const HISTORY_LIMIT = 10;
  const TARGET_START_DIAMETER = 58;
  const TARGET_END_DIAMETER = 34;
  const TARGET_LIFESPAN_MS = 1300;

  /* ---------------- which drill this page runs ----------------
     One engine file, six pages. `data-engine` on <body> picks the drill and
     `data-preset` optionally retunes the flick spawner for a specific game.
     Both absent is the original trainer at `/`, so index.html behaves exactly
     as it did.

     The three tier-1 drills measure different motor skills in different units
     — targets/second, percent time-on-target, accuracy-first — which is why
     each is its own page rather than another duration button. Precision is
     deliberately NOT a third engine: it is the same single-target spawner with
     shrinking off and a small target, because that is all it needs to be. */
  const ENGINE_CONFIG = {
    flick: {
      spawner: "single", shrink: true,
      start: TARGET_START_DIAMETER, end: TARGET_END_DIAMETER, life: TARGET_LIFESPAN_MS,
      primary: "avgReaction", primaryLowerIsBetter: true,
    },
    precision: {
      // Static and small. Nothing shrinks, so there is no reward for rushing —
      // the only way to score is to put the crosshair in the right place.
      spawner: "single", shrink: false,
      start: 26, end: 26, life: 1900,
      primary: "accuracy", primaryLowerIsBetter: false,
    },
    gridshot: {
      spawner: "grid", cols: 3, rows: 3, live: 3,
      primary: "throughput", primaryLowerIsBetter: false,
    },
    tracking: {
      spawner: "track", diameter: 76,
      primary: "onTargetPct", primaryLowerIsBetter: false,
    },
  };

  /* Game presets: the flick spawner with target size and time-to-live retuned
     to the exposure window each game actually gives you. Stated on each page. */
  const PRESETS = {
    // Small hitboxes, one-tap kills, and peeks resolved in well under a second.
    valorant: { start: 44, end: 30, life: 1100 },
    // Larger player models and long angle holds, so the window is the widest.
    csgo: { start: 52, end: 38, life: 1500 },
    // Big targets that are almost never still, and the shortest window of the
    // three because an opponent is normally behind a wall a moment later.
    fortnite: { start: 68, end: 44, life: 900 },
  };

  const DRILL_NAMES = {
    flick: "FlickTrainer",
    gridshot: "FlickTrainer Gridshot",
    tracking: "FlickTrainer Tracking",
    precision: "FlickTrainer Precision",
  };
  const ENGINE = document.body.getAttribute("data-engine") || "flick";
  const PRESET = document.body.getAttribute("data-preset") || null;
  const DRILL_NAME = DRILL_NAMES[ENGINE] || DRILL_NAMES.flick;
  const CFG = Object.assign(
    {},
    ENGINE_CONFIG[ENGINE] || ENGINE_CONFIG.flick,
    (PRESET && PRESETS[PRESET]) || {}
  );

  /* Each drill keeps its own history. One shared 10-entry list looked tidy and
     was not: a gridshot run would evict the tracking run before it, and the
     tracking page would then say "no sessions on this drill yet" for a drill
     you had just played twice. Flick keeps the legacy unscoped key so nobody
     loses the history they already have; presets share it, because a preset is
     the flick drill with different numbers rather than a different drill. */
  const HISTORY_KEY = STORAGE_PREFIX + "history" + (ENGINE === "flick" ? "" : ":" + ENGINE);

  // Legacy key shape for the original trainer, so nobody loses a personal best
  // to this change; every new drill namespaces itself.
  function bestKey(mode, variant) {
    const scope = ENGINE === "flick" && !PRESET
      ? ""
      : (PRESET ? PRESET : ENGINE) + ":";
    return `${STORAGE_PREFIX}best:${scope}${mode}:${variant}`;
  }

  function loadJSON(key) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }

  function saveJSON(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch {
      return false; // private browsing / quota exceeded — degrade silently
    }
  }

  function loadHistory() {
    const h = loadJSON(HISTORY_KEY);
    return Array.isArray(h) ? h : [];
  }

  function pushHistory(entry) {
    const history = loadHistory();
    history.unshift(entry);
    saveJSON(HISTORY_KEY, history.slice(0, HISTORY_LIMIT));
  }

  function formatMs(ms) {
    if (ms == null || Number.isNaN(ms)) return "—";
    return `${Math.round(ms)}ms`;
  }

  function formatPct(p) {
    return `${Math.round(p)}%`;
  }

  function modeLabel(mode, variant) {
    return mode === "timed" ? `Timed ${variant}s` : `${variant} targets`;
  }

  /* The theme toggle used to live here. It now lives in assets/js/nav.js, which
     every page loads: the header carrying `#theme-toggle` is shared across all
     eight files, and app.js is only on index.html, so binding it here left the
     stored `ft-theme` unread on the guides and legal pages. */

  document.getElementById("year").textContent = new Date().getFullYear();

  /* ============================================================
     PROGRESSION LAYER — XP / ranks / achievements / streak / sound
     Ported from the sibling cabinets (cpsboost, reflexzap) so all three
     sites share one engagement model. Like the combo/spark flavour, none
     of this feeds the accuracy or reaction-time measurement: it only
     *reads* a finished session's summary.
     ============================================================ */

  const PROFILE_KEY = STORAGE_PREFIX + "profile";
  const SOUND_KEY = STORAGE_PREFIX + "sound-muted";

  const RANK_TITLES = [
    { level: 1, title: "Rookie" },
    { level: 2, title: "Plinker" },
    { level: 3, title: "Marksman" },
    { level: 4, title: "Sharpshooter" },
    { level: 5, title: "Gunslinger" },
    { level: 6, title: "Dead-Eye" },
    { level: 7, title: "Ace Shot" },
    { level: 8, title: "Sniper Elite" },
    { level: 9, title: "Range Legend" },
    { level: 10, title: "Dead-Eye God" },
  ];

  function xpForLevel(level) { return 50 * level * (level - 1); }
  function levelForXp(xp) {
    let level = 1;
    while (xp >= xpForLevel(level + 1)) level += 1;
    return Math.min(level, RANK_TITLES.length);
  }
  function titleForLevel(level) {
    const entry = RANK_TITLES[Math.min(level, RANK_TITLES.length) - 1];
    return entry ? entry.title : RANK_TITLES[RANK_TITLES.length - 1].title;
  }

  const ACHIEVEMENTS = [
    { id: "first_session", icon: "🎯", title: "First Blood", desc: "Complete your first session.", check: (c) => c.totalSessions >= 1 },
    { id: "sharp_eye", icon: "👁️", title: "Sharp Eye", desc: "Finish a session at 90%+ accuracy.", check: (c) => c.accuracy >= 90 },
    { id: "flawless", icon: "🏵️", title: "Flawless Run", desc: "Finish a session of 5+ targets with zero misses.", check: (c) => c.misses === 0 && c.hits >= 5 },
    { id: "quick_draw", icon: "⚡", title: "Quick Draw", desc: "Average under 300ms per target.", check: (c) => c.avgReaction != null && c.avgReaction < 300 },
    { id: "superhuman", icon: "👑", title: "Superhuman", desc: "Average 220ms or better.", check: (c) => c.avgReaction != null && c.avgReaction <= 220 },
    { id: "fifty_hits", icon: "💯", title: "Fifty Down", desc: "Land 50+ hits in one session.", check: (c) => c.hits >= 50 },
    { id: "marathon", icon: "⏱️", title: "Range Marathon", desc: "Complete a 60-second session.", check: (c) => c.completedSixty },
    { id: "combo_20", icon: "🔥", title: "Combo x20", desc: "Reach a 20-hit streak.", check: (c) => c.maxCombo >= 20 },
    { id: "pb_breaker", icon: "🏆", title: "Record Breaker", desc: "Beat your personal best 5 times.", check: (c) => c.pbBeatenCount >= 5 },
    { id: "streak_3", icon: "🔥", title: "3-Day Streak", desc: "Train 3 days in a row.", check: (c) => c.streak >= 3 },
    { id: "streak_7", icon: "🔥", title: "Week Warrior", desc: "Train 7 days in a row.", check: (c) => c.streak >= 7 },
    { id: "sessions_10", icon: "🕹️", title: "Range Regular", desc: "Complete 10 sessions.", check: (c) => c.totalSessions >= 10 },
    { id: "sessions_50", icon: "🕹️", title: "Range Veteran", desc: "Complete 50 sessions.", check: (c) => c.totalSessions >= 50 },
    { id: "level_10", icon: "⭐", title: "Dead-Eye God", desc: "Reach the max level.", check: (c) => c.level >= RANK_TITLES.length },
  ];

  const EMPTY_PROFILE = {
    totalXP: 0,
    totalSessions: 0,
    pbBeatenCount: 0,
    streak: 0,
    lastPlayedDate: null,
    achievements: [],
  };

  function loadProfile() {
    const raw = loadJSON(PROFILE_KEY);
    if (raw && typeof raw === "object") {
      const merged = Object.assign({}, EMPTY_PROFILE, raw);
      if (!Array.isArray(merged.achievements)) merged.achievements = [];
      return merged;
    }
    return Object.assign({}, EMPTY_PROFILE);
  }

  function saveProfile(profile) { saveJSON(PROFILE_KEY, profile); }

  function dateKey(d) { return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`; }

  // A day played back-to-back extends the streak; a gap restarts it at 1.
  // Replaying on a day already counted leaves the streak untouched.
  function updateStreak(profile, now) {
    const today = dateKey(now);
    if (profile.lastPlayedDate === today) return profile.streak;
    const yesterday = dateKey(new Date(now.getTime() - 86400000));
    profile.streak = profile.lastPlayedDate === yesterday ? profile.streak + 1 : 1;
    profile.lastPlayedDate = today;
    return profile.streak;
  }

  // XP is weighted on the rating tier (i.e. reaction speed) with bonuses for
  // the things worth encouraging: beating your own record, sitting through a
  // full 60s run, holding a long streak, and shooting clean.
  const TIER_XP = { "S": 45, "A+": 34, "A": 26, "B": 18, "C": 12, "D": 8 };

  function xpForSession({ tier, accuracy, isNewBest, isFirstBest, completedSixty, maxCombo }) {
    let xp = 10;
    xp += TIER_XP[tier] != null ? TIER_XP[tier] : 4;
    if (isNewBest && !isFirstBest) xp += 30;
    if (completedSixty) xp += 12;
    if (maxCombo >= 20) xp += 10;
    if (accuracy >= 90) xp += 8;
    return xp;
  }

  function recordSession({ summary, maxCombo, isNewBest, isFirstBest, completedSixty, now }) {
    const profile = loadProfile();
    const prevLevel = levelForXp(profile.totalXP);

    profile.totalSessions += 1;
    if (isNewBest && !isFirstBest) profile.pbBeatenCount += 1;
    const streak = updateStreak(profile, now);
    const gained = xpForSession({
      tier: summary.rating.tier,
      accuracy: summary.accuracy,
      isNewBest,
      isFirstBest,
      completedSixty,
      maxCombo,
    });
    profile.totalXP += gained;
    const newLevel = levelForXp(profile.totalXP);

    const ctx = {
      accuracy: summary.accuracy,
      avgReaction: summary.avgReaction,
      hits: summary.hits,
      misses: summary.misses,
      totalSessions: profile.totalSessions,
      pbBeatenCount: profile.pbBeatenCount,
      streak,
      completedSixty,
      maxCombo,
      level: newLevel,
    };
    const newlyUnlocked = [];
    ACHIEVEMENTS.forEach((a) => {
      if (profile.achievements.indexOf(a.id) === -1 && a.check(ctx)) {
        profile.achievements.push(a.id);
        newlyUnlocked.push(a);
      }
    });

    saveProfile(profile);
    return { profile, xpGained: gained, leveledUp: newLevel > prevLevel, newLevel, newlyUnlocked };
  }

  /* ---------------- progression rendering ---------------- */

  const chipLevel = document.getElementById("chip-level");
  const chipStreak = document.getElementById("chip-streak");
  const xpRankLabel = document.getElementById("xp-rank-label");
  const xpProgressLabel = document.getElementById("xp-progress-label");
  const xpBarFill = document.getElementById("xp-bar-fill");
  const achievementsGrid = document.getElementById("achievements-grid");
  const unlockStack = document.getElementById("unlock-stack");

  function renderStatusChips(profile) {
    const level = levelForXp(profile.totalXP);
    if (chipLevel) chipLevel.textContent = `LV ${level}`;
    if (chipStreak) {
      chipStreak.textContent = `🔥${profile.streak}`;
      chipStreak.classList.toggle("is-zero", profile.streak === 0);
    }
    if (xpRankLabel) xpRankLabel.textContent = titleForLevel(level);
    if (xpProgressLabel && xpBarFill) {
      const base = xpForLevel(level);
      const next = xpForLevel(level + 1);
      const span = next - base || 1;
      const into = Math.max(0, profile.totalXP - base);
      const maxed = level >= RANK_TITLES.length;
      xpProgressLabel.textContent = maxed ? "Max Level" : `${into} / ${span} XP`;
      xpBarFill.style.width = (maxed ? 100 : Math.min(100, (into / span) * 100)) + "%";
    }
  }

  function renderAchievements(profile) {
    if (!achievementsGrid) return;
    achievementsGrid.textContent = "";
    ACHIEVEMENTS.forEach((a) => {
      const unlocked = profile.achievements.indexOf(a.id) !== -1;
      const el = document.createElement("div");
      el.className = "badge" + (unlocked ? " unlocked" : "");
      el.title = `${a.title}: ${a.desc}`;
      const icon = document.createElement("span");
      icon.className = "badge-icon";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = a.icon;
      const title = document.createElement("span");
      title.className = "badge-title";
      title.textContent = a.title;
      el.appendChild(icon);
      el.appendChild(title);
      achievementsGrid.appendChild(el);
    });
  }

  function queueUnlockToasts(items, kickerFor) {
    if (!unlockStack || !items.length) return;
    items.forEach((item, i) => {
      setTimeout(() => {
        const el = document.createElement("div");
        el.className = "unlock-toast";
        const icon = document.createElement("span");
        icon.className = "unlock-icon";
        icon.setAttribute("aria-hidden", "true");
        icon.textContent = item.icon;
        const text = document.createElement("span");
        text.className = "unlock-text";
        const kicker = document.createElement("span");
        kicker.className = "unlock-kicker";
        kicker.textContent = kickerFor(item);
        const title = document.createElement("span");
        title.className = "unlock-title";
        title.textContent = item.title;
        text.appendChild(kicker);
        text.appendChild(title);
        el.appendChild(icon);
        el.appendChild(text);
        unlockStack.appendChild(el);
        playAchievementChime();
        setTimeout(() => el.remove(), 3600);
      }, i * 550);
    });
  }

  /* ---------------- arcade sound synth (WebAudio, no audio files) ----------------
     Same synth the sibling cabinets use: short oscillator blips, so the site
     still ships zero binary assets and makes zero third-party requests. */

  let audioCtx = null;
  let soundMuted = false;
  try { soundMuted = localStorage.getItem(SOUND_KEY) === "1"; } catch { /* ignore */ }

  function getAudioCtx() {
    if (audioCtx) return audioCtx;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    audioCtx = new Ctx();
    return audioCtx;
  }

  function playTone(freq, startOffset, duration, type, peakGain) {
    if (soundMuted) return;
    const ctx = getAudioCtx();
    if (!ctx) return;
    if (ctx.state === "suspended") ctx.resume();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = type || "sine";
    osc.frequency.value = freq;
    const t0 = ctx.currentTime + startOffset;
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(peakGain || 0.07, t0 + 0.012);
    gain.gain.exponentialRampToValueAtTime(0.0001, t0 + duration);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t0);
    osc.stop(t0 + duration + 0.02);
  }

  // A hit is a light-gun "pew" — pitch rises with the combo so a hot streak
  // audibly climbs.
  function playHitShot(comboBoost) {
    playTone(640 + Math.min(comboBoost || 0, 420), 0, 0.055, "square", 0.04);
  }
  function playMissThud() { playTone(120, 0, 0.16, "sawtooth", 0.05); }
  function playAchievementChime() {
    [660, 880, 1320].forEach((f, i) => playTone(f, i * 0.09, 0.16, "triangle", 0.07));
  }
  function playLevelUpFanfare() {
    [523, 659, 784, 1046, 1318].forEach((f, i) => playTone(f, i * 0.08, 0.22, "square", 0.06));
  }
  function playNewBestSparkle() {
    [988, 1318, 1568, 2093].forEach((f, i) => playTone(f, i * 0.06, 0.14, "sine", 0.07));
  }
  function playStageClear() {
    [392, 523, 659, 784].forEach((f, i) => playTone(f, i * 0.1, 0.2, "square", 0.055));
  }

  const soundToggleBtn = document.getElementById("sound-toggle");
  function renderSoundToggle() {
    if (!soundToggleBtn) return;
    soundToggleBtn.textContent = soundMuted ? "🔇" : "🔊";
    soundToggleBtn.setAttribute("aria-pressed", String(!soundMuted));
  }
  if (soundToggleBtn) {
    soundToggleBtn.addEventListener("click", () => {
      soundMuted = !soundMuted;
      try { localStorage.setItem(SOUND_KEY, soundMuted ? "1" : "0"); } catch { /* ignore */ }
      renderSoundToggle();
      if (!soundMuted) playHitShot(0);
    });
    renderSoundToggle();
  }

  const statusChipBtn = document.getElementById("status-chip");
  if (statusChipBtn) {
    statusChipBtn.addEventListener("click", () => {
      const panel = document.getElementById("achievements-panel");
      if (panel) panel.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  /* ---------------- screens ---------------- */

  const screens = {
    setup: document.getElementById("screen-setup"),
    game: document.getElementById("screen-game"),
    results: document.getElementById("screen-results"),
  };

  function showScreen(name) {
    Object.entries(screens).forEach(([key, el]) => {
      el.hidden = key !== name;
    });
  }

  /* ---------------- setup screen ---------------- */

  let mode = "timed"; // "timed" | "count"
  let duration = 30; // seconds, for timed mode
  let targetCount = 30; // targets, for count mode

  const modeButtons = Array.from(document.querySelectorAll(".mode-opt"));
  const durationButtons = Array.from(document.querySelectorAll(".duration-opt"));
  const countButtons = Array.from(document.querySelectorAll(".count-opt"));
  const timedOptionsEl = document.getElementById("timed-options");
  const countOptionsEl = document.getElementById("count-options");
  const bestAccuracyVal = document.getElementById("best-accuracy-val");
  const bestAvgTimeVal = document.getElementById("best-avgtime-val");
  const bestPrimaryVal = document.getElementById("best-primary-val");

  function currentVariant() {
    return mode === "timed" ? duration : targetCount;
  }

  function refreshBestRow() {
    const best = loadJSON(bestKey(mode, currentVariant()));
    // Each drill's card shows only the stats that drill actually produces.
    if (bestAccuracyVal) bestAccuracyVal.textContent = best ? formatPct(best.accuracy) : "—";
    if (bestAvgTimeVal) bestAvgTimeVal.textContent = best && best.avgTime != null ? formatMs(best.avgTime) : "—";
    if (bestPrimaryVal) bestPrimaryVal.textContent = formatPrimary(best ? best.primary : null);
  }

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      mode = btn.dataset.mode;
      modeButtons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      timedOptionsEl.style.display = mode === "timed" ? "" : "none";
      countOptionsEl.style.display = mode === "count" ? "" : "none";
      refreshBestRow();
    });
  });
  durationButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      duration = parseInt(btn.dataset.duration, 10);
      durationButtons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      refreshBestRow();
    });
  });
  countButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      targetCount = parseInt(btn.dataset.count, 10);
      countButtons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      refreshBestRow();
    });
  });

  document.getElementById("start-btn").addEventListener("click", startSession);
  document.getElementById("change-mode-btn").addEventListener("click", () => {
    refreshBestRow();
    showScreen("setup");
  });

  refreshBestRow();

  /* ---------------- game screen ---------------- */

  const gameArea = document.getElementById("game-area");
  const hudPrimaryLabel = document.getElementById("hud-primary-label");
  const hudPrimaryVal = document.getElementById("hud-primary-val");
  const hudHits = document.getElementById("hud-hits");
  const hudMisses = document.getElementById("hud-misses");
  const hudAccuracy = document.getElementById("hud-accuracy");
  const hudCombo = document.getElementById("hud-combo");
  const hudOnTarget = document.getElementById("hud-ontarget");
  const comboWrap = document.getElementById("combo-wrap");
  const quitBtn = document.getElementById("quit-btn");

  let session = null; // active session state, see startSession()
  let rafId = null;
  let countdownTimer = null;
  let combo = 0; // presentation-only hit streak (never feeds the accuracy/time math)
  let maxCombo = 0; // best streak this session — feeds XP/achievements only
  let lastResult = null; // last finished session, for the share string

  // Flavour layer: a running hit streak shown in the HUD. Pure cosmetics.
  function setCombo(n) {
    combo = n;
    if (combo > maxCombo) maxCombo = combo;
    if (hudCombo) hudCombo.textContent = String(combo);
    if (comboWrap) comboWrap.classList.toggle("is-hot", combo >= 5);
  }

  // Flavour layer: a pixel hit-spark burst at a hit target's centre.
  function spawnSpark(x, y) {
    if (!gameArea) return;
    const s = document.createElement("span");
    s.className = "hit-spark";
    s.style.left = x + "px";
    s.style.top = y + "px";
    gameArea.appendChild(s);
    setTimeout(() => s.remove(), 320);
  }

  function startSession() {
    session = {
      mode,
      variant: currentVariant(),
      engine: ENGINE,
      hits: 0,
      misses: 0,
      reactionTimes: [],
      startedAt: performance.now(),
      endsAt: mode === "timed" ? performance.now() + duration * 1000 : null,
      targetsSpawned: 0,
      activeTarget: null, // {el, spawnedAt, timeoutId} — single-target spawner
      grid: null,         // gridshot state
      track: null,        // tracking state
      ended: false,
    };

    hudPrimaryLabel.textContent = mode === "timed" ? "Time" : "Targets";
    gameArea.innerHTML = "";
    maxCombo = 0;
    setCombo(0);
    updateHud();
    showScreen("game");
    // Defer the first spawn one frame so the game-area has real layout
    // dimensions — the grid and the tracking path both need them.
    requestAnimationFrame(() => {
      if (!session || session.ended) return;
      if (CFG.spawner === "grid") startGrid();
      else if (CFG.spawner === "track") startTracking();
      else spawnTarget();
      tick();
    });
  }

  /* Shared hit/miss accounting. Every spawner routes through these two, so the
     three drills cannot drift apart on what counts as a hit or when the clock
     is read. The flavour layer (spark, combo, blip) hangs off them and, as
     ever, never feeds back into the counters. */
  function registerHit(spawnedAt, x, y) {
    session.hits += 1;
    session.reactionTimes.push(performance.now() - spawnedAt);
    spawnSpark(x, y);
    setCombo(combo + 1);
    playHitShot(combo * 12);
  }

  function registerMiss(fromUser) {
    session.misses += 1;
    setCombo(0);
    if (fromUser) playMissThud();
  }

  function updateHud() {
    if (!session) return;
    if (hudHits) hudHits.textContent = String(session.hits);
    if (hudMisses) hudMisses.textContent = String(session.misses);
    if (hudAccuracy) hudAccuracy.textContent = formatPct(calcAccuracy(session.hits, session.misses));
    if (hudOnTarget && session.track) {
      const elapsed = performance.now() - session.startedAt;
      hudOnTarget.textContent = formatPct(calcTimeOnTarget(session.track.onTargetMs, elapsed));
    }
    if (session.mode === "timed") {
      const remaining = Math.max(0, session.endsAt - performance.now());
      hudPrimaryVal.textContent = (remaining / 1000).toFixed(1) + "s";
    } else {
      hudPrimaryVal.textContent = `${session.hits + session.misses}/${session.variant}`;
    }
  }

  function tick() {
    if (!session || session.ended) return;
    if (session.track) stepTracking();
    updateHud();
    if (session.mode === "timed" && performance.now() >= session.endsAt) {
      endSession();
      return;
    }
    rafId = requestAnimationFrame(tick);
  }

  function spawnTarget() {
    if (!session || session.ended) return;
    const rect = gameArea.getBoundingClientRect();
    const pos = randomTargetPosition(rect.width, rect.height, CFG.start);
    const el = document.createElement("button");
    el.type = "button";
    el.className = "target";
    el.style.left = pos.x + "px";
    el.style.top = pos.y + "px";
    el.style.width = CFG.start + "px";
    el.style.height = CFG.start + "px";
    el.setAttribute("aria-label", "Target");

    const spawnedAt = performance.now();
    session.targetsSpawned += 1;

    let shrinkRaf = null;
    function shrink() {
      const elapsed = performance.now() - spawnedAt;
      const size = targetSizeAtElapsed(elapsed, CFG.life, CFG.start, CFG.end);
      el.style.width = size + "px";
      el.style.height = size + "px";
      // `session` and not just `session.activeTarget`: endSession() nulls the
      // whole session, and one already-scheduled frame of this loop still
      // fires afterwards. It threw a TypeError at the end of every single run
      // — harmless, because the frame does nothing useful by then, but it put
      // a red line in the console after each session and would have masked a
      // real error.
      if (elapsed < CFG.life && session && session.activeTarget && session.activeTarget.el === el) {
        shrinkRaf = requestAnimationFrame(shrink);
      }
    }
    // Precision targets are static: no shrink loop at all, so there is nothing
    // in the frame budget and nothing that rewards shooting early.
    if (CFG.shrink) shrinkRaf = requestAnimationFrame(shrink);

    const timeoutId = setTimeout(() => {
      resolveTarget(el, false, shrinkRaf);
    }, CFG.life);

    // `pointerdown`, not `click`: it fires the instant the button goes down,
    // which is the correct sample point for a tool measuring milliseconds —
    // `click` only lands on mouseup, adding the user's release time to every
    // reading. Pointer events unify mouse/touch/pen, so this single listener
    // covers every input type without double-counting. Matches cpsboost and
    // reflexzap, which already sample on pointerdown.
    el.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      e.preventDefault();
      resolveTarget(el, true, shrinkRaf);
    });

    session.activeTarget = { el, spawnedAt, timeoutId, shrinkRaf };
    gameArea.appendChild(el);
  }

  function resolveTarget(el, wasHit, shrinkRaf) {
    if (!session || session.ended) return;
    if (!session.activeTarget || session.activeTarget.el !== el) return; // already resolved

    clearTimeout(session.activeTarget.timeoutId);
    if (shrinkRaf) cancelAnimationFrame(shrinkRaf);

    if (wasHit) {
      registerHit(
        session.activeTarget.spawnedAt,
        parseFloat(el.style.left) || 0,
        parseFloat(el.style.top) || 0
      );
      el.classList.add("hit");
      setTimeout(() => el.remove(), 180);
    } else {
      // A target that timed out is a miss, but not user input — no thud.
      registerMiss(false);
      el.remove();
    }
    session.activeTarget = null;
    updateHud();

    const doneByCount = session.mode === "count" && session.targetsSpawned >= session.variant;
    if (doneByCount) {
      endSession();
      return;
    }
    spawnTarget();
  }

  /* ---------------- gridshot ----------------
     Nine fixed cells, three targets live at once, and nothing ever times out:
     a target sits there until it is shot. That is what makes the score a rate
     rather than a latency — you are measured on how many you can clear in the
     session, not on how quickly you answered any one of them. */

  function startGrid() {
    const rect = gameArea.getBoundingClientRect();
    session.grid = {
      cells: gridCellCenters(rect.width, rect.height, CFG.cols, CFG.rows),
      diameter: gridTargetDiameter(rect.width, rect.height, CFG.cols, CFG.rows),
      occupied: new Set(),
    };
    for (let i = 0; i < CFG.live; i++) spawnGridTarget();
  }

  function freeCellIndex() {
    if (!session || !session.grid) return -1;
    const free = [];
    for (let i = 0; i < session.grid.cells.length; i++) {
      if (!session.grid.occupied.has(i)) free.push(i);
    }
    if (!free.length) return -1;
    return free[Math.floor(Math.random() * free.length)];
  }

  function spawnGridTarget() {
    const index = freeCellIndex();
    if (index < 0) return;
    spawnGridTargetAt(index);
  }

  function spawnGridTargetAt(index) {
    const g = session.grid;
    const cell = g.cells[index];
    g.occupied.add(index);

    const el = document.createElement("button");
    el.type = "button";
    el.className = "target";
    el.style.left = cell.x + "px";
    el.style.top = cell.y + "px";
    el.style.width = g.diameter + "px";
    el.style.height = g.diameter + "px";
    el.setAttribute("aria-label", "Target");

    const spawnedAt = performance.now();
    session.targetsSpawned += 1;

    // Same sampling rule as everywhere else on this site: pointerdown, once.
    el.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      e.preventDefault();
      resolveGridTarget(el, index, spawnedAt);
    });

    gameArea.appendChild(el);
  }

  function resolveGridTarget(el, index, spawnedAt) {
    if (!session || session.ended || !session.grid) return;
    if (!session.grid.occupied.has(index)) return; // already resolved

    registerHit(spawnedAt, parseFloat(el.style.left) || 0, parseFloat(el.style.top) || 0);
    el.classList.add("hit");
    setTimeout(() => el.remove(), 180);

    // Pick the replacement cell while this one is still marked occupied, so the
    // next target never appears in the slot you have just cleared.
    const next = freeCellIndex();
    session.grid.occupied.delete(index);
    if (next >= 0) spawnGridTargetAt(next);

    updateHud();
  }

  /* ---------------- tracking ----------------
     One target on a smooth randomised path, scored on the share of the session
     the cursor spent inside it. The cursor position is sampled on pointermove
     and the time is integrated on the rAF frame, so the score does not depend
     on how often the pointer happens to fire. The area rect is cached and
     refreshed only on scroll/resize: reading it per pointermove would be a
     forced layout in the hot path. */

  function cacheTrackRect() {
    if (!session || !session.track) return;
    const r = gameArea.getBoundingClientRect();
    session.track.rect = r;
    session.track.w = r.width;
    session.track.h = r.height;
  }

  function startTracking() {
    const el = document.createElement("div");
    el.className = "target target--track";
    el.style.width = CFG.diameter + "px";
    el.style.height = CFG.diameter + "px";
    gameArea.appendChild(el);

    session.track = {
      el,
      path: randomTrackingPath(Math.random),
      d: CFG.diameter,
      rect: null, w: 0, h: 0,
      cursor: null,       // area-relative pointer position, null until it moves
      inside: false,
      onTargetMs: 0,
      lastT: performance.now(),
    };
    cacheTrackRect();
    stepTracking();
  }

  function stepTracking() {
    const t = session.track;
    if (!t) return;
    const now = performance.now();
    const dt = Math.min(100, now - t.lastT); // a backgrounded tab must not bank time
    t.lastT = now;

    const p = trackingPathPoint(now - session.startedAt, t.path, t.w, t.h, t.d);
    // transform only: the target moves every frame and must never touch layout.
    t.el.style.transform = `translate3d(${p.x}px, ${p.y}px, 0) translate(-50%, -50%)`;

    const on = !!t.cursor && isInsideTarget(t.cursor.x, t.cursor.y, p.x, p.y, t.d);
    if (on) t.onTargetMs += dt;
    if (on !== t.inside) {
      t.inside = on;
      t.el.classList.toggle("is-on", on);
    }
  }

  gameArea.addEventListener("pointermove", (e) => {
    if (!session || session.ended || !session.track) return;
    const r = session.track.rect;
    if (!r) return;
    session.track.cursor = { x: e.clientX - r.left, y: e.clientY - r.top };
  });
  gameArea.addEventListener("pointerleave", () => {
    if (session && session.track) session.track.cursor = null;
  });
  window.addEventListener("scroll", cacheTrackRect, { passive: true });
  window.addEventListener("resize", cacheTrackRect);

  // Clicking empty space (not a target) inside the game area counts as a miss,
  // independent of whatever target happens to be active/shrinking at the time.
  // Same `pointerdown` sampling as the target itself, for the same reason.
  gameArea.addEventListener("pointerdown", (e) => {
    if (!session || session.ended) return;
    // Tracking is not a clicking drill: there is nothing to whiff, so a click
    // in the range must not invent a miss out of a stray mouse button.
    if (session.engine === "tracking") return;
    if (e.target !== gameArea) return; // the target's own handler already fired
    registerMiss(true);
    updateHud();
    const flash = document.createElement("span");
    flash.className = "miss-flash";
    const rect = gameArea.getBoundingClientRect();
    flash.style.left = e.clientX - rect.left + "px";
    flash.style.top = e.clientY - rect.top + "px";
    flash.textContent = "miss";
    gameArea.appendChild(flash);
    setTimeout(() => flash.remove(), 500);
  });

  quitBtn.addEventListener("click", () => endSession(true));

  /* ---------------- backgrounded tab ----------------
     endSession(true) is the quit path: it clears the expiry timer, cancels the
     frame loop, empties the range, returns to setup and drops the session
     without writing a best, a history entry or any XP. That is exactly what an
     abandoned run needs, so the handler reuses it rather than inventing a
     second teardown that could drift from it. */
  function abandonRun() {
    if (!shouldAbandonRun(document.visibilityState, !!session && !session.ended)) return;
    endSession(true);
    setCombo(0);
    showToast("Run abandoned — the tab was hidden");
  }

  document.addEventListener("visibilitychange", abandonRun);
  // Safari on iOS can put a page in the back/forward cache without ever
  // reporting a visibilitychange, so pagehide is the second net.
  window.addEventListener("pagehide", () => {
    if (!session || session.ended) return;
    endSession(true);
    setCombo(0);
  });

  function cleanupActiveTarget() {
    if (session && session.activeTarget) {
      clearTimeout(session.activeTarget.timeoutId);
      if (session.activeTarget.shrinkRaf) cancelAnimationFrame(session.activeTarget.shrinkRaf);
    }
  }

  function endSession(quit) {
    if (!session || session.ended) return;
    session.ended = true;
    cleanupActiveTarget();
    if (rafId) cancelAnimationFrame(rafId);
    gameArea.innerHTML = "";

    if (quit) {
      showScreen("setup");
      refreshBestRow();
      session = null;
      return;
    }

    const elapsedMs = performance.now() - session.startedAt;
    const summary = buildSessionSummary({
      hits: session.hits,
      misses: session.misses,
      reactionTimes: session.reactionTimes,
      elapsedMs,
      onTargetMs: session.track ? session.track.onTargetMs : null,
      engine: session.engine,
    });

    const key = bestKey(session.mode, session.variant);
    const prevBest = loadJSON(key);
    const { record, improved: statsImproved } = updateBestRecord(prevBest, summary);
    // ...plus this drill's headline number, whichever direction is better.
    const primary = updateBestMetric(
      prevBest ? prevBest.primary : null,
      summary[CFG.primary],
      !!CFG.primaryLowerIsBetter
    );
    record.primary = primary.best;
    const improved = statsImproved || primary.improved;
    saveJSON(key, record);

    pushHistory({
      mode: session.mode,
      variant: session.variant,
      engine: session.engine,
      accuracy: summary.accuracy,
      avgReaction: summary.avgReaction,
      primary: summary[CFG.primary],
      ts: Date.now(),
    });

    lastResult = { summary, mode: session.mode, variant: session.variant };

    const gameResult = recordSession({
      summary,
      maxCombo,
      isNewBest: improved,
      isFirstBest: prevBest == null,
      completedSixty: session.mode === "timed" && session.variant === 60,
      now: new Date(),
    });
    renderStatusChips(gameResult.profile);
    renderAchievements(gameResult.profile);

    renderResults(summary, record, improved);

    playStageClear();
    if (improved && prevBest != null) setTimeout(playNewBestSparkle, 420);
    if (gameResult.leveledUp) {
      setTimeout(playLevelUpFanfare, gameResult.newlyUnlocked.length ? 700 : 300);
    }
    queueUnlockToasts(gameResult.newlyUnlocked, () =>
      gameResult.leveledUp ? `Achievement Unlocked · LV ${gameResult.newLevel}` : "Achievement Unlocked"
    );

    session = null;
  }

  /* ---------------- results screen ---------------- */

  const ratingTierEl = document.getElementById("rating-tier");
  const ratingLabelEl = document.getElementById("rating-label");
  const ratingCompareEl = document.getElementById("rating-compare");
  const resHits = document.getElementById("res-hits");
  const resMisses = document.getElementById("res-misses");
  const resAccuracy = document.getElementById("res-accuracy");
  const resAvgTime = document.getElementById("res-avgtime");
  const resThroughput = document.getElementById("res-throughput");
  const resBestAvgTime = document.getElementById("res-best-avgtime");
  const resOnTarget = document.getElementById("res-ontarget");
  const resBestPrimary = document.getElementById("res-best-primary");

  /** The drill's headline number, formatted in its own units. */
  function formatPrimary(v) {
    if (v == null || Number.isNaN(v)) return "—";
    if (typeof v !== "number") return "—";
    if (CFG.primary === "avgReaction") return formatMs(v);
    if (CFG.primary === "throughput") return `${v.toFixed(2)}/s`;
    return formatPct(v);
  }
  const newBestFlag = document.getElementById("new-best-flag");
  const historyListEl = document.getElementById("history-list");
  const historyChartEl = document.getElementById("history-chart");

  document.getElementById("restart-btn").addEventListener("click", startSession);

  /* ---------------- friend challenge links ----------------
     A shared result is a URL, not a dead text blob:
     `?ms=210&acc=88&mode=timed&v=30` opens the trainer already set to the
     sender's mode and variant, with their average time-to-click shown as the
     number to beat and a verdict once the session ends. Average time is the
     primary metric (it's what the rating tiers key off), so that's what the
     verdict compares; accuracy rides along as context.

     Every param is validated before use — a hand-edited or hostile query
     string can only ever degrade to "no challenge", never a broken session. */

  // A challenge link has to come back to the drill it was set on, so the page's
  // own canonical is the base rather than a hardcoded site root.
  const canonicalLink = document.querySelector('link[rel="canonical"]');
  const SITE_URL = (canonicalLink && canonicalLink.href) || "https://flicktrainer.com/";
  const CHALLENGE_VARIANTS = { timed: [15, 30, 60], count: [10, 30, 50] };
  const challengeBanner = document.getElementById("challenge-banner");
  const challengeText = document.getElementById("challenge-text");
  const challengeVerdict = document.getElementById("challenge-verdict");
  let challenge = null; // { ms, acc, mode, variant } once a valid link is opened

  function readChallengeFromUrl() {
    let params;
    try {
      params = new URLSearchParams(window.location.search);
    } catch {
      return null;
    }
    const ms = Number(params.get("ms"));
    // Outside a plausible time-to-click this is junk, not a challenge.
    if (!Number.isFinite(ms) || ms < 50 || ms > 5000) return null;

    const rawMode = params.get("mode");
    const m = rawMode === "count" ? "count" : "timed";
    const allowed = CHALLENGE_VARIANTS[m];
    const rawVariant = parseInt(params.get("v"), 10);
    const variant = allowed.indexOf(rawVariant) !== -1 ? rawVariant : allowed[1];

    const rawAcc = Number(params.get("acc"));
    const acc = Number.isFinite(rawAcc) && rawAcc >= 0 && rawAcc <= 100 ? rawAcc : null;

    return { ms: Math.round(ms), acc: acc, mode: m, variant: variant };
  }

  function buildChallengeUrl(summary, m, v) {
    const parts = [
      "ms=" + Math.round(summary.avgReaction != null ? summary.avgReaction : 0),
      "acc=" + Math.round(summary.accuracy),
      "mode=" + encodeURIComponent(m),
      "v=" + encodeURIComponent(v),
    ];
    return SITE_URL + "?" + parts.join("&");
  }

  // Drive the existing setup buttons rather than duplicating their state, so a
  // challenge link leaves the UI in exactly the state a manual click would.
  function selectSetup(m, v) {
    const modeBtn = document.querySelector(`.mode-opt[data-mode="${m}"]`);
    if (modeBtn) modeBtn.click();
    const sel = m === "timed" ? `.duration-opt[data-duration="${v}"]` : `.count-opt[data-count="${v}"]`;
    const variantBtn = document.querySelector(sel);
    if (variantBtn) variantBtn.click();
  }

  function applyChallenge() {
    challenge = readChallengeFromUrl();
    if (!challenge) return;
    selectSetup(challenge.mode, challenge.variant);
    /* Gridshot and tracking ship no mode selector — both are scored over a
       session length, so "30 targets" is not a run they can do. selectSetup
       silently leaves the page on its own settings when those buttons are
       absent, so read them back before writing the banner: it has to name the
       run the visitor is about to play, not the one in the link. The verdict
       compares `ms` alone, so nothing about the comparison changes. */
    challenge.mode = mode;
    challenge.variant = currentVariant();
    if (challengeText) {
      const accPart = challenge.acc != null ? ` at ${Math.round(challenge.acc)}% accuracy` : "";
      challengeText.textContent =
        `A friend averaged ${challenge.ms}ms${accPart} on ${modeLabel(challenge.mode, challenge.variant)}. Beat it.`;
    }
    if (challengeBanner) challengeBanner.hidden = false;
  }

  function renderChallengeVerdict(summary) {
    if (!challengeVerdict) return;
    if (!challenge || summary.avgReaction == null) {
      challengeVerdict.hidden = true;
      return;
    }
    const diff = Math.round(summary.avgReaction) - challenge.ms; // negative = faster
    challengeVerdict.hidden = false;
    challengeVerdict.classList.toggle("is-win", diff < 0);
    challengeVerdict.classList.toggle("is-loss", diff > 0);
    if (diff < 0) {
      challengeVerdict.textContent =
        `Challenge beaten — ${Math.abs(diff)}ms faster than their ${challenge.ms}ms.`;
    } else if (diff === 0) {
      challengeVerdict.textContent = `Dead heat — you matched their ${challenge.ms}ms exactly.`;
    } else {
      challengeVerdict.textContent =
        `Challenge missed by ${diff}ms — they averaged ${challenge.ms}ms. Try again.`;
    }
  }

  /* ---------------- share / copy result ---------------- */

  const shareBtn = document.getElementById("share-btn");
  const toastEl = document.getElementById("toast");
  let toastTimer = null;

  function showToast(msg) {
    if (!toastEl) return;
    toastEl.textContent = msg;
    toastEl.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.remove("show"), 1600);
  }

  function fallbackCopy(text) {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); } catch { /* clipboard unsupported */ }
    ta.remove();
  }

  function copyText(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  }

  function buildShareText() {
    if (!lastResult) return "";
    const { summary, mode: m, variant: v } = lastResult;
    const profile = loadProfile();
    const level = levelForXp(profile.totalXP);
    return (
      `I shot ${formatPct(summary.accuracy)} accuracy at ${formatMs(summary.avgReaction)} per target ` +
      `on ${DRILL_NAME} (${modeLabel(m, v)} — ${titleForLevel(level)}, LV ${level})! ` +
      `Beat me: ${buildChallengeUrl(summary, m, v)}`
    );
  }

  if (shareBtn) {
    shareBtn.addEventListener("click", () => {
      const text = buildShareText();
      if (!text) return;
      copyText(text);
      showToast("Challenge link copied!");
    });
  }

  function renderResults(summary, bestRecord, improved) {
    ratingTierEl.textContent = summary.rating.tier;
    ratingLabelEl.textContent = summary.rating.label;
    ratingCompareEl.textContent = compareForEngine(summary, ENGINE);

    // Every tile is optional: the drills do not all report the same six
    // numbers, so each page ships only the tiles that mean something on it.
    if (resHits) resHits.textContent = String(summary.hits);
    if (resMisses) resMisses.textContent = String(summary.misses);
    if (resAccuracy) resAccuracy.textContent = formatPct(summary.accuracy);
    if (resAvgTime) resAvgTime.textContent = formatMs(summary.avgReaction);
    if (resThroughput) resThroughput.textContent = `${summary.throughput.toFixed(2)}/s`;
    if (resOnTarget) resOnTarget.textContent = summary.onTargetPct == null ? "—" : formatPct(summary.onTargetPct);
    if (resBestAvgTime) resBestAvgTime.textContent = bestRecord && bestRecord.avgTime != null ? formatMs(bestRecord.avgTime) : "—";
    if (resBestPrimary) resBestPrimary.textContent = formatPrimary(bestRecord ? bestRecord.primary : null);
    newBestFlag.hidden = !improved;
    renderChallengeVerdict(summary);

    renderHistory();
    showScreen("results");
  }

  function renderHistory() {
    const history = loadHistory();
    historyListEl.innerHTML = "";
    historyChartEl.innerHTML = "";

    if (history.length === 0) {
      const li = document.createElement("li");
      li.className = "h-empty";
      li.textContent = "No sessions yet — this was your first!";
      historyListEl.appendChild(li);
      return;
    }

    // Belt and braces on top of the per-drill key: entries written before the
    // drills existed carry no `engine` and are flick's, and a stale mixed list
    // must never draw a targets-per-second run on the same axis as a
    // millisecond one — that would claim they were comparable.
    const rows = history.filter((h) => (h.engine || "flick") === ENGINE);
    if (rows.length === 0) {
      const li = document.createElement("li");
      li.className = "h-empty";
      li.textContent = "No sessions on this drill yet.";
      historyListEl.appendChild(li);
      return;
    }

    // Entries written before the drills existed carry no `primary`; on the
    // original trainer that number was the average reaction time.
    const historyPrimary = (h) => (h.primary != null ? h.primary : h.avgReaction);
    const maxPrimary = Math.max(...rows.map((h) => Math.abs(historyPrimary(h) || 0)), 0.0001);
    // Oldest-to-newest left-to-right for the sparkline-style bars.
    rows
      .slice()
      .reverse()
      .forEach((h) => {
        const bar = document.createElement("div");
        bar.className = "history-bar";
        const v = historyPrimary(h);
        const heightPct = v ? Math.max(6, (Math.abs(v) / maxPrimary) * 100) : 6;
        bar.style.height = heightPct + "%";
        bar.title = `${modeLabel(h.mode, h.variant)} — ${formatPrimary(historyPrimary(h))}`;
        historyChartEl.appendChild(bar);
      });

    /* The row's second number is whichever of the drill's stats the headline is
       not — the original trainer printed accuracy beside its millisecond
       average and should keep doing so. Tracking gets neither: it never
       registers a hit or a miss, so its accuracy is 0/0 and printing it would
       be a fabricated zero. */
    const secondary = (h) => {
      if (ENGINE === "tracking") return "";
      if (CFG.primary === "accuracy") return h.avgReaction != null ? formatMs(h.avgReaction) : "";
      return h.accuracy != null ? formatPct(h.accuracy) : "";
    };

    rows.forEach((h) => {
      const li = document.createElement("li");
      const date = new Date(h.ts);
      const second = secondary(h);
      li.innerHTML =
        `<span class="h-mode">${modeLabel(h.mode, h.variant)}</span>` +
        `<span>${formatPrimary(historyPrimary(h))}${second ? " · " + second : ""}</span>` +
        `<span>${date.toLocaleDateString()}</span>`;
      historyListEl.appendChild(li);
    });
  }

  /* ---------------- init ---------------- */

  (function initProgression() {
    const profile = loadProfile();
    renderStatusChips(profile);
    renderAchievements(profile);
    applyChallenge();
  })();
})();
