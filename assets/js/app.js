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

  /** Builds the full stat summary for a finished session from raw counters. */
  function buildSessionSummary({ hits, misses, reactionTimes, elapsedMs }) {
    const accuracy = calcAccuracy(hits, misses);
    const avgReaction = calcAverageReactionTime(reactionTimes);
    const throughput = calcThroughput(hits, elapsedMs);
    const rating = getRatingTier(avgReaction);
    return { hits, misses, accuracy, avgReaction, throughput, rating };
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

  const PURE = {
    calcAccuracy,
    calcAverageReactionTime,
    calcThroughput,
    targetSizeAtElapsed,
    randomTargetPosition,
    getRatingTier,
    compareToAverage,
    buildSessionSummary,
    updateBestRecord,
    RATING_TIERS,
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
  const HISTORY_KEY = STORAGE_PREFIX + "history";
  const HISTORY_LIMIT = 10;
  const TARGET_START_DIAMETER = 58;
  const TARGET_END_DIAMETER = 34;
  const TARGET_LIFESPAN_MS = 1300;

  function bestKey(mode, variant) {
    return `${STORAGE_PREFIX}best:${mode}:${variant}`;
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

  /* ---------------- theme toggle ---------------- */

  (function initTheme() {
    const stored = localStorage.getItem("ft-theme");
    if (stored) document.documentElement.setAttribute("data-theme", stored);
    document.getElementById("theme-toggle").addEventListener("click", () => {
      const current =
        document.documentElement.getAttribute("data-theme") ||
        (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      const next = current === "dark" ? "light" : "dark";
      document.documentElement.setAttribute("data-theme", next);
      localStorage.setItem("ft-theme", next);
    });
  })();

  document.getElementById("year").textContent = new Date().getFullYear();

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

  function currentVariant() {
    return mode === "timed" ? duration : targetCount;
  }

  function refreshBestRow() {
    const best = loadJSON(bestKey(mode, currentVariant()));
    bestAccuracyVal.textContent = best ? formatPct(best.accuracy) : "—";
    bestAvgTimeVal.textContent = best && best.avgTime != null ? formatMs(best.avgTime) : "—";
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
  const quitBtn = document.getElementById("quit-btn");

  let session = null; // active session state, see startSession()
  let rafId = null;
  let countdownTimer = null;

  function startSession() {
    session = {
      mode,
      variant: currentVariant(),
      hits: 0,
      misses: 0,
      reactionTimes: [],
      startedAt: performance.now(),
      endsAt: mode === "timed" ? performance.now() + duration * 1000 : null,
      targetsSpawned: 0,
      activeTarget: null, // {el, spawnedAt, timeoutId}
      ended: false,
    };

    hudPrimaryLabel.textContent = mode === "timed" ? "Time" : "Targets";
    gameArea.innerHTML = "";
    updateHud();
    showScreen("game");
    // Defer first spawn one frame so the game-area has real layout dimensions.
    requestAnimationFrame(() => {
      spawnTarget();
      tick();
    });
  }

  function updateHud() {
    if (!session) return;
    hudHits.textContent = String(session.hits);
    hudMisses.textContent = String(session.misses);
    hudAccuracy.textContent = formatPct(calcAccuracy(session.hits, session.misses));
    if (session.mode === "timed") {
      const remaining = Math.max(0, session.endsAt - performance.now());
      hudPrimaryVal.textContent = (remaining / 1000).toFixed(1) + "s";
    } else {
      hudPrimaryVal.textContent = `${session.hits + session.misses}/${session.variant}`;
    }
  }

  function tick() {
    if (!session || session.ended) return;
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
    const pos = randomTargetPosition(rect.width, rect.height, TARGET_START_DIAMETER);
    const el = document.createElement("button");
    el.type = "button";
    el.className = "target";
    el.style.left = pos.x + "px";
    el.style.top = pos.y + "px";
    el.style.width = TARGET_START_DIAMETER + "px";
    el.style.height = TARGET_START_DIAMETER + "px";
    el.setAttribute("aria-label", "Target");

    const spawnedAt = performance.now();
    session.targetsSpawned += 1;

    let shrinkRaf = null;
    function shrink() {
      const elapsed = performance.now() - spawnedAt;
      const size = targetSizeAtElapsed(elapsed, TARGET_LIFESPAN_MS, TARGET_START_DIAMETER, TARGET_END_DIAMETER);
      el.style.width = size + "px";
      el.style.height = size + "px";
      if (elapsed < TARGET_LIFESPAN_MS && session.activeTarget && session.activeTarget.el === el) {
        shrinkRaf = requestAnimationFrame(shrink);
      }
    }
    shrinkRaf = requestAnimationFrame(shrink);

    const timeoutId = setTimeout(() => {
      resolveTarget(el, false, shrinkRaf);
    }, TARGET_LIFESPAN_MS);

    el.addEventListener("click", (e) => {
      e.stopPropagation();
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
      session.hits += 1;
      session.reactionTimes.push(performance.now() - session.activeTarget.spawnedAt);
      el.classList.add("hit");
      setTimeout(() => el.remove(), 180);
    } else {
      session.misses += 1;
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

  // Clicking empty space (not a target) inside the game area counts as a miss,
  // independent of whatever target happens to be active/shrinking at the time.
  gameArea.addEventListener("click", (e) => {
    if (!session || session.ended) return;
    if (e.target !== gameArea) return; // target's own click handler already fired
    session.misses += 1;
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
    });

    const key = bestKey(session.mode, session.variant);
    const prevBest = loadJSON(key);
    const { record, improved } = updateBestRecord(prevBest, summary);
    saveJSON(key, record);

    pushHistory({
      mode: session.mode,
      variant: session.variant,
      accuracy: summary.accuracy,
      avgReaction: summary.avgReaction,
      ts: Date.now(),
    });

    renderResults(summary, record, improved);
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
  const newBestFlag = document.getElementById("new-best-flag");
  const historyListEl = document.getElementById("history-list");
  const historyChartEl = document.getElementById("history-chart");

  document.getElementById("restart-btn").addEventListener("click", startSession);

  function renderResults(summary, bestRecord, improved) {
    ratingTierEl.textContent = summary.rating.tier;
    ratingLabelEl.textContent = summary.rating.label;
    ratingCompareEl.textContent = compareToAverage(summary.avgReaction);

    resHits.textContent = String(summary.hits);
    resMisses.textContent = String(summary.misses);
    resAccuracy.textContent = formatPct(summary.accuracy);
    resAvgTime.textContent = formatMs(summary.avgReaction);
    resThroughput.textContent = `${summary.throughput.toFixed(2)}/s`;
    resBestAvgTime.textContent = bestRecord && bestRecord.avgTime != null ? formatMs(bestRecord.avgTime) : "—";
    newBestFlag.hidden = !improved;

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

    const maxAvg = Math.max(...history.map((h) => h.avgReaction || 0), 1);
    // Oldest-to-newest left-to-right for the sparkline-style bars.
    history
      .slice()
      .reverse()
      .forEach((h) => {
        const bar = document.createElement("div");
        bar.className = "history-bar";
        const heightPct = h.avgReaction ? Math.max(6, (h.avgReaction / maxAvg) * 100) : 6;
        bar.style.height = heightPct + "%";
        bar.title = `${modeLabel(h.mode, h.variant)} — ${formatMs(h.avgReaction)}`;
        historyChartEl.appendChild(bar);
      });

    history.forEach((h) => {
      const li = document.createElement("li");
      const date = new Date(h.ts);
      li.innerHTML =
        `<span class="h-mode">${modeLabel(h.mode, h.variant)}</span>` +
        `<span>${formatPct(h.accuracy)} · ${formatMs(h.avgReaction)}</span>` +
        `<span>${date.toLocaleDateString()}</span>`;
      historyListEl.appendChild(li);
    });
  }
})();
