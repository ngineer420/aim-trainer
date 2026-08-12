/* flicktrainer.com — chrome behaviour, loaded on every page.

   This lives in its own file rather than at the end of app.js because app.js is
   the aim-trainer engine and only index.html loads it: the four guides, the two
   legal pages and 404 would otherwise get the shared header and toolbar without
   any of the behaviour. Nothing here is required for the nav to work — see the
   block comment below.
   ================================================================== */

/* The theme toggle moved here from app.js when the two header variants were
   consolidated into one block. It had been running on index.html only, so a
   visitor who chose light and then opened a guide got the guide in dark: the
   stored preference was never read outside the game page. Loading it everywhere
   is what makes one shared header honest. */
(function theme() {
  const root = document.documentElement;
  let store = null;
  try {
    store = window.localStorage;
  } catch (e) {
    /* storage disabled — the toggle still works for this page view */
  }
  const stored = store && store.getItem("ft-theme");
  if (stored) root.setAttribute("data-theme", stored);

  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const current =
      root.getAttribute("data-theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    if (store) store.setItem("ft-theme", next);
  });
})();

/* ================================================================== *
 * toolbar v1 — the portfolio navigation pattern.                      *
 * Spec: github.com/ngineer420/ngineer420.github.io/issues/13          *
 *                                                                     *
 * Copy this block verbatim into any site in the portfolio. It is pure *
 * enhancement: with JS off, <details>/<summary> still discloses the   *
 * sheet, the rail is still a native scroll container of real links,   *
 * the edge fades are still CSS and the scrim is still CSS. Only the   *
 * active-chip centring, Escape and click-outside are lost.            *
 * ================================================================== */
(function toolbar() {
  const bar = document.querySelector(".toolbar");
  if (!bar) return;
  const rail = bar.querySelector(".tb-rail");
  const menu = bar.querySelector("details.tb-menu");

  if (rail) {
    // js-on hands the right-hand fade over to measurement. Until then the
    // CSS keeps it on, so a JS-disabled visitor never gets a chip clipped
    // mid-word with nothing to say there is more of the row.
    rail.classList.add("js-on");
    const fades = () => {
      const max = rail.scrollWidth - rail.clientWidth;
      rail.classList.toggle("can-l", rail.scrollLeft > 1);
      rail.classList.toggle("can-r", rail.scrollLeft < max - 1);
    };
    // Assigning scrollLeft, never scrollIntoView: that also scrolls every
    // ancestor and the document, which on a phone drops the visitor below
    // the header on arrival.
    const current = rail.querySelector("[aria-current]");
    if (current) {
      rail.scrollLeft = Math.max(
        0,
        current.offsetLeft - (rail.clientWidth - current.offsetWidth) / 2
      );
    }
    rail.addEventListener("scroll", fades, { passive: true });
    window.addEventListener("resize", fades);
    fades();
  }

  if (menu) {
    // A disclosure, not a modal: focus is deliberately not trapped, Tab
    // walks the links and straight out the other side.
    window.addEventListener("keydown", (e) => {
      if (e.key !== "Escape" || !menu.open) return;
      menu.open = false;
      const summary = menu.querySelector("summary");
      if (summary) summary.focus();
    });
    document.addEventListener("click", (e) => {
      if (menu.open && !menu.contains(e.target)) menu.open = false;
    });
  }
})();
