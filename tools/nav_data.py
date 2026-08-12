"""flicktrainer.com navigation data — the single source of truth for the toolbar.

This is the ONLY file that differs between sites. `sync_nav.py` is generic and
copies verbatim. Nothing here is computed at runtime by the browser: sync_nav
renders it into the static HTML of every page.

Tier rule (portfolio spec, ngineer420.github.io#13): a page is tier 1 only if it
answers a *different question*. flicktrainer is one tool at `/` plus four guides,
so every tier-1 destination here is a guide. The in-deck Timed/Count and
15s/30s/60s/10/30/50 controls are a parameter of the one running session — they
are not pages, they have no URLs, and they are deliberately not links.

Home is the brand, per the spec, so `/` takes no rail chip and no slot in the
sheet's list. It appears once, as the sheet's bottom hub line: on this site `/`
is not a landing page, it is the tool the guides are about, and the audit's
actual finding was that a visitor on an article had no labelled route back to it.
The hub slot gives that route an explicit name without spending a rail chip on
"Home" or seating it among its own guides.
"""

# Noun used in the menu trigger: "All 4 guides". Every tier-1 destination here
# is an article; the tool itself is the hub line, not one of the four.
NOUN = "guides"

# Tier-1 destinations, in traffic order (the same order the homepage's own
# "Learn more" card grid uses). Four is well under the rail's cap of 8, so the
# rail carries all of them and the sheet renders flat.
#   label -> rail chip text, <= 18 chars
#   long  -> anchor text in the sheet
#   group -> sheet grouping key; unused at this size, the sheet renders flat
TOOLS = [
    {"href": "/articles/what-is-a-good-reaction-time.html", "label": "Reaction Time",  "long": "What's a Good Reaction Time?", "group": "guides", "tier": 1},
    {"href": "/articles/flick-vs-tracking-aim.html",        "label": "Flick vs Track", "long": "Flicking vs. Tracking",        "group": "guides", "tier": 1},
    {"href": "/articles/history-of-aim-trainers.html",      "label": "History",        "long": "History of Aim Trainers",      "group": "guides", "tier": 1},
    {"href": "/articles/how-this-test-works.html",          "label": "How It Works",   "long": "How This Test Works",          "group": "guides", "tier": 1},
]

# Declared for completeness. Four destinations is under the flat-list threshold,
# so sync_nav renders one unlabelled list and never reads this.
GROUPS = [
    ("guides", "Guides"),
]

# The route back to the tool, at the bottom of the sheet. There is no tier-2
# family on this site: the modes and durations are controls, not pages.
HUBS = [("/", "Back to the aim trainer")]

# No footer tool list here today, and the spec says not to add one where none
# exists — the rail carries all four guides visibly on every page and the sheet
# carries them plus the tool, so a footer duplicate would be pure boilerplate.
FOOTER = []

# One-time --migrate: this site has no nav markup at all to strip, so the only
# op is dropping the marker pair in the one place the spec allows — a direct
# child of <body>, immediately after </header> and above <main>.
MIGRATE = [
    {"op": "insert_after", "region": "nav", "pattern": r"</header>", "indent": ""},
]
