"""flicktrainer.com navigation data — the single source of truth for the toolbar.

This is the ONLY file that differs between sites. `sync_nav.py` is generic and
copies verbatim. Nothing here is computed at runtime by the browser: sync_nav
renders it into the static HTML of every page.

Tier rule (portfolio spec, ngineer420.github.io#13): a page is tier 1 only if it
answers a *different question*. flicktrainer now has four drills that do, because
they measure different motor skills and report them in different units — average
time-to-click in milliseconds, targets cleared per second, percent of a session
on target — and a page reporting a different unit is not the same page with a
value baked in. It is the units, not the settings, that make the case: the
in-deck Timed/Count and 15s/30s/60s controls are still parameters of one running
session, still have no URLs, and are still deliberately not links.

The three game presets ARE tier 2, and are the textbook case for it: valorant /
csgo / fortnite run the same flick drill with the same scoring and three
different numbers for target size and lifespan. They hang off `/` as VARIANTS,
so a visitor on a preset page sees the Flick chip marked as the current *set*
rather than the current page.

Home used to take the sheet's hub row rather than a rail chip, on the grounds
that it was the brand and not a peer of the list. That reasoning expired when the
site gained three more drills: `/` is now the flick drill, one of four siblings,
and leaving it as the only drill without a chip would make it the odd one out in
its own group. It takes the first chip, which also gives it the
`aria-current="page"` target the hub row was there to provide, so HUBS is empty.
"""

# Noun used in the menu trigger: "All 8 drills & guides".
#
# It was "guides" while every destination was something to read. It cannot stay
# that now that half of the eight are the drills themselves, and it cannot
# become "drills" for the same reason in reverse. Not "pages" either: the site
# has far more of those, so any count attached to it would be false. The set is
# genuinely two kinds of thing, so the noun says two kinds of thing.
NOUN = "drills & guides"

# Tier-1 destinations, in rail order (the rail cap is 8; this site has exactly
# 8, so every one of them is visible and none is sheet-only).
#   label -> rail chip text, <= 18 chars
#   long  -> anchor text in the sheet
#   group -> sheet grouping key. Unused at <= 8 destinations — the spec says
#            group headings are noise at that size and the renderer emits a flat
#            list — but kept so the arrangement is already decided at the ninth.
TOOLS = [
    # The four drills, each measuring a different motor skill in its own unit.
    {"href": "/",                     "label": "Flick",     "long": "Flick Aim Trainer",      "group": "drills", "tier": 1},
    {"href": "/gridshot/",            "label": "Gridshot",  "long": "Gridshot",               "group": "drills", "tier": 1},
    {"href": "/tracking-trainer/",    "label": "Tracking",  "long": "Tracking Trainer",       "group": "drills", "tier": 1},
    {"href": "/precision-trainer/",   "label": "Precision", "long": "Precision Trainer",      "group": "drills", "tier": 1},
    # Then the guides, in traffic order (the same order the homepage's own
    # "Learn more" card grid uses).
    {"href": "/articles/what-is-a-good-reaction-time.html", "label": "Time-to-Click",  "long": "What Is a Good Time-to-Click?", "group": "guides", "tier": 1},
    {"href": "/articles/flick-vs-tracking-aim.html",        "label": "Flick vs Track", "long": "Flicking vs. Tracking",        "group": "guides", "tier": 1},
    {"href": "/articles/history-of-aim-trainers.html",      "label": "History",        "long": "History of Aim Trainers",      "group": "guides", "tier": 1},
    {"href": "/articles/how-this-test-works.html",          "label": "How It Works",   "long": "How This Test Works",          "group": "guides", "tier": 1},
]

# Sheet groups, in order. Declared for the ninth destination; at eight the
# renderer emits one flat list and never reads this.
GROUPS = [
    ("drills", "Drills"),
    ("guides", "Guides"),
]

# Tier 2: the same flick drill with three sets of numbers. One parent only, which
# is all sync_nav supports and all this site needs. `bytes` is the generic
# renderer's per-item payload and means nothing here, so it is None; no page on
# this site opens a `sizechips` region, because the drill switcher under the
# cabinet already carries these links with room for their labels.
VARIANTS = {
    "parent": "/",
    "aria": "Game presets",
    "label": "Tuned for",
    "items": [
        {"href": "/valorant-aim-trainer/", "label": "Valorant", "bytes": None},
        {"href": "/csgo-aim-trainer/",     "label": "CS:GO",    "bytes": None},
        {"href": "/fortnite-aim-trainer/", "label": "Fortnite", "bytes": None},
    ],
}

# No hub row. It existed only to give `/` a labelled route in the chrome; the
# Flick chip is that route now, and a hub row pointing at a destination already
# listed above it would carry aria-current twice.
HUBS = []

# No footer tool list here today, and the spec says not to add one where none
# exists — the rail carries all eight tier-1 destinations visibly on every page,
# which is the crawl path.
FOOTER = []

# One-time --migrate: this site has no nav markup at all to strip, so the only
# op is dropping the marker pair in the one place the spec allows — a direct
# child of <body>, immediately after </header> and above <main>.
MIGRATE = [
    {"op": "insert_after", "region": "nav", "pattern": r"</header>", "indent": ""},
]
