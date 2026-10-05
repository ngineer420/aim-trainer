#!/usr/bin/env python3
"""Render the drill and game-preset pages from one shared cabinet shell.

    python3 tools/build_drills.py            # write all twelve files
    python3 tools/build_drills.py --check    # exit 1 if any output is stale

WHY THIS EXISTS. index.html is hand-written and stays that way — it is the one
page whose markup is not a variation on anything. The six pages below are: same
cabinet, same three screens, same results deck, with a different `data-engine`
and a different explainer. Each ships TWICE, at `/x/index.html` and at the flat
`/x.html` alias, byte-identical, which is the pattern the portfolio already uses
on qrmint. Twelve files agreeing on two hundred lines of shared chrome is
exactly the shape of thing that drifts when it is maintained by hand, and drift
in the shell is invisible until a page loses its ad tag or its erabbit mark.

So: the shell lives here once, the per-page content lives in PAGES, and the
files on disk are output. Edit this file, not the HTML it writes.

This is not a build step in the sense CLAUDE.md rules out — the site still ships
plain static HTML with nothing computed at page load, exactly like
tools/sync_nav.py, which this script is deliberately shaped after. The nav
region is emitted as an empty marker pair and whatever sync_nav has put between
the markers is carried across on every subsequent run, so the two scripts can be
run in either order, any number of times, without fighting over the same bytes.

test/scoring.test.js checks the OUTPUT independently — pairs identical, one ad
tag, mark last in body, no external requests, the ids the engine needs — so a
hand-edit that bypasses this script still gets caught.
"""

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NAV_RE = re.compile(r"(<!-- nav:start -->)(.*?)(<!-- nav:end -->)", re.S)

# Bump together with the ?v= in every other page whenever a coupled
# HTML/CSS/JS change ships, or cached visitors get new HTML with stale CSS.
V = "7"

# Copied byte-for-byte from index.html. It is commented out across this whole
# site; a new page is not the place to unilaterally turn ads on.
AD_TAG = """<!--
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-7560786263587509" crossorigin="anonymous"></script>
-->"""

ERABBIT = (
    '<a href="https://erabb.it" class="erabbit-mark" aria-label="erabb.it">'
    '<img src="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 '
    'viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>&#128007;</text>'
    '</svg>" width="10" height="10" alt=""></a>'
)

DRILLS = [
    ("/", "Flick"),
    ("/gridshot/", "Gridshot"),
    ("/tracking-trainer/", "Tracking"),
    ("/precision-trainer/", "Precision"),
]
PRESETS_NAV = [
    ("/valorant-aim-trainer/", "Valorant"),
    ("/csgo-aim-trainer/", "CS:GO"),
    ("/fortnite-aim-trainer/", "Fortnite"),
]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def faq(items):
    out = ["  <h2>Frequently asked questions</h2>"]
    for q, a in items:
        out += ['  <div class="faq-item">', "    <h3>%s</h3>" % q, "    <p>%s</p>" % a, "  </div>"]
    return "\n".join(out)


TAG_RE = re.compile(r"<[^>]+>")


def plain(html):
    """Strip inline markup so a schema string matches the visible sentence.

    The FAQ answers carry <em> and <a> for the reader. JSON-LD wants the text a
    person sees, so the same list feeds both and the two can never drift.
    """
    text = TAG_RE.sub("", html)
    for ent, ch in (("&mdash;", "—"), ("&ndash;", "–"), ("&amp;", "&"),
                    ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&nbsp;", " ")):
        text = text.replace(ent, ch)
    return " ".join(text.split())


def json_str(text):
    out = []
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch in "\n\r\t":
            out.append(" ")
        elif ord(ch) < 0x20:
            continue
        else:
            out.append(ch)
    return "".join(out)


def faq_jsonld(items):
    """FAQPage schema built from the same list that renders the visible FAQ."""
    if not items:
        return ""
    entities = []
    for q, a in items:
        entities.append(
            '    {"@type": "Question", "name": "%s", "acceptedAnswer": '
            '{"@type": "Answer", "text": "%s"}}' % (json_str(plain(q)), json_str(plain(a)))
        )
    return (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "FAQPage",\n'
        '  "mainEntity": [\n%s\n  ]\n'
        "}\n"
        "</script>" % ",\n".join(entities)
    )


def breadcrumb_jsonld(name, url):
    """Every generated page sits one level below the trainer at the root."""
    return (
        '<script type="application/ld+json">\n'
        "{\n"
        '  "@context": "https://schema.org",\n'
        '  "@type": "BreadcrumbList",\n'
        '  "itemListElement": [\n'
        '    {"@type": "ListItem", "position": 1, "name": "Flick Trainer", '
        '"item": "https://flicktrainer.com/"},\n'
        '    {"@type": "ListItem", "position": 2, "name": "%s", "item": "%s"}\n'
        "  ]\n"
        "}\n"
        "</script>" % (json_str(name), url)
    )


# Three peers, not nineteen. Each one answers a question somebody who just
# measured their aim plausibly has next, which is the only reason to link out.
RELATED = [
    ("https://reflexzap.com", "Reaction Time Test", "How fast you react to a signal"),
    ("https://cpsboost.com", "Click Speed Test", "Clicks per second, several formats"),
    ("https://hardwarecheckup.com", "Hardware Checkup", "Mouse, keyboard and display tests"),
]


def related_block(indent="  "):
    out = ['<nav class="footer-related" aria-label="Related tools">',
           "  <h2>Related tools</h2>",
           "  <ul>"]
    for href, label, blurb in RELATED:
        out.append('    <li><a href="%s" rel="noopener">%s</a> <span>%s</span></li>'
                   % (href, label, blurb))
    out += ["  </ul>", "</nav>"]
    return "\n".join(indent + ln for ln in out)


def keep_reading(items):
    out = ["  <h2>Keep training</h2>"]
    for href, title, blurb in items:
        out += ['  <div class="faq-item">',
                '    <h3><a href="%s">%s</a></h3>' % (href, title),
                "    <p>%s</p>" % blurb, "  </div>"]
    return "\n".join(out)


# --------------------------------------------------------------------------
# Page content
# --------------------------------------------------------------------------

GRIDSHOT_BODY = """  <h2>Gridshot</h2>

  <p>Nine fixed positions in a three-by-three grid. Three targets are alive at any
  moment; clear one and another appears in a cell that is currently empty. Your score
  is <strong>targets per second</strong> over the session, which is a different number
  from the millisecond average the <a href="/">flick drill</a> gives you and measures a
  different thing.</p>

  <h2 id="why-grid">Why the grid is fixed</h2>
  <p>The whole point of gridshot is that you always know where a target can be. There
  are nine possible positions and you have seen all of them within about two seconds of
  starting, so the drill stops testing <em>visual search</em> — hunting the screen for
  something that appeared somewhere unpredictable — and starts testing the thing it is
  named for: how fast you can move the crosshair between two known points and stop it
  there.</p>

  <p>That distinction matters more than it sounds. In a random-spawn drill a large part
  of your reaction time is finding the target, and finding is a perceptual skill that
  improves on a different curve from aiming. Separating them is why gridshot became the
  standard warm-up routine rather than one of a dozen interchangeable modes: it
  isolates the motor half. If your gridshot rate is good but your flick average is
  poor, your arm is fine and your eyes are doing the work slowly. If it is the other
  way round, you find things quickly and then wobble on the way there.</p>

  <h2 id="live-targets">Three at once, and nothing expires</h2>
  <p>Two rules make this drill continuous rather than turn-based. First, three targets
  are live simultaneously, so there is always somewhere to go next and the crosshair
  never idles waiting for a spawn. Second, <strong>targets never time out</strong>. In
  the flick drill a target you ignore for long enough disappears and counts as a miss;
  here it simply waits. A miss is only ever a shot that landed on empty space.</p>

  <p>That is deliberate, and it changes what your accuracy figure means. On this drill
  accuracy is <em>shot discipline</em> — the share of your clicks that landed on
  something — rather than a measure of whether you kept up with the spawn rate. Keeping
  up is what targets per second measures, and separating the two numbers is more useful
  than folding them together. You can be fast and sloppy, or slow and clean, and the
  results screen will tell you which.</p>

  <p>When a target is cleared, its replacement is chosen from the cells that are empty
  <em>at that moment</em>, with the just-cleared cell still counted as occupied. So a
  target can never respawn where you have just clicked. Without that rule the optimal
  strategy would be to sit on one cell and click as fast as you can, which measures your
  mouse button rather than your aim.</p>

  <h2 id="targets-per-second">Reading targets per second</h2>
  <p>Targets per second is hits divided by session length. It is a rate, not a latency,
  and it rewards a completely different thing from a millisecond average: consistency.
  One brilliant flick does nothing to a thirty-second rate, and one moment of hesitation
  costs you the same as one slow flick. That makes it a much steadier number
  session-to-session than a reaction time average, which is why it is worth tracking as
  a progress metric.</p>

  <p>As a rough calibration on this drill's target size and spacing: steady grid
  shooting sits around 1.2 to 1.5 targets per second, and past 1.8 you are flicking
  straight to the next target rather than hunting for it. Those are the drill's own
  rating bands and nothing more — a difficulty curve tuned to how this page is
  configured, not a measurement of any population. Target size, grid spacing and screen
  size all move the number, so compare your rate to your own rate on the same machine
  rather than to anyone else's.</p>

  <h2 id="training">How to actually train with it</h2>
  <p>Gridshot is a warm-up before it is a workout. Two or three thirty-second runs at
  the start of a session get your hand calibrated to your sensitivity, which is most of
  what a warm-up is for. Beyond that, the useful discipline is to run it at a rate you
  can hold cleanly rather than the fastest rate you can survive: overshooting and
  correcting builds the habit of overshooting, and that habit follows you into the game.
  Watch the accuracy number, and back off the pace until it stops falling.</p>

  <p>Sixty-second runs are the honest test. Fifteen seconds rewards a burst; a minute
  exposes whether your form holds when your forearm gets tired, which is much closer to
  what a real match asks of it. If your rate over sixty seconds is well below your rate
  over fifteen, the thing to train is endurance and grip, not speed.</p>

%(faq)s

%(keep)s"""

GRIDSHOT_FAQ = [
    ("What is a good gridshot score?",
     "On this drill's configuration, around 1.2&ndash;1.5 targets per second is steady, "
     "and past 1.8 is quick. Treat those as this page's own difficulty bands rather than "
     "a population statistic &mdash; target size, spacing, screen size and mouse polling "
     "rate all move the number, so the only comparison that means anything is against "
     "your own previous runs on the same setup."),
    ("Why do targets not disappear on their own?",
     "Because gridshot measures how fast you can clear targets, not whether you can keep "
     "up with a spawn timer. With no expiry, a miss is only ever a shot that landed on "
     "empty space, which makes the accuracy figure a clean measure of shot discipline "
     "instead of a mix of two things."),
    ("Is gridshot better than random-spawn flicking?",
     "It is not better, it is narrower. Fixed positions remove visual search and isolate "
     "the movement, which is what makes it a good warm-up and a good progress metric. "
     "Random spawns are closer to a real game, where you do have to find things. Running "
     "both and comparing them tells you which half is holding you back."),
    ("Does it work on a trackpad or a phone?",
     "It runs, and the drill is the same, but the numbers are not comparable to a mouse. "
     "A trackpad cannot flick, and a touchscreen removes the movement entirely &mdash; you "
     "are tapping locations, not aiming at them. Compare like with like."),
]

TRACKING_BODY = """  <h2>Tracking Trainer</h2>

  <p>One target, moving continuously on a smooth path that never repeats. There is
  nothing to click. Your score is the percentage of the session your crosshair spent
  <em>inside</em> the target &mdash; <strong>time on target</strong> &mdash; sampled
  continuously rather than at discrete moments. It is the only drill on this site with
  no hits and no misses, because neither concept applies.</p>

  <div class="callout callout--coarse">
    <strong>This drill needs a mouse or a trackpad.</strong> A touchscreen reports a
    position only while a finger is down, and the finger then covers the target it is
    supposed to follow. The score you get here on a phone is not a measurement of your
    tracking. Every other drill on this site works on touch &mdash; try
    <a href="/gridshot/">gridshot</a> or the <a href="/">flick drill</a> instead.
  </div>

  <h2 id="different">Why this is a different skill</h2>
  <p>Flicking and tracking are close to opposite motor problems. A flick is
  <em>ballistic</em>: you plan a movement, execute it as one burst, and correct at the
  end. Tracking is a <em>continuous feedback loop</em>: you are constantly comparing
  where the crosshair is against where the target is and adjusting, dozens of times a
  second, and the correction never stops. People who are excellent at one are routinely
  mediocre at the other, and the reason is that they train opposite habits &mdash; a
  flicker learns to commit to a movement, a tracker learns never to commit.</p>

  <p>Which one matters depends on what you play. Weapons with a high rate of fire and
  low per-shot damage reward tracking, because you have to keep the crosshair on a
  moving body for the length of a burst. Weapons that kill in one or two shots reward
  flicking, because there is one moment that counts and nothing after it. Most games
  ask for both, and most players train only the second.</p>

  <h2 id="path">How the path is generated</h2>
  <p>The target's position is the sum of <strong>two sine waves per axis</strong>, at
  frequencies that are not simple multiples of each other, with randomised phases each
  session. That gives three properties that matter for a tracking drill.</p>

  <p>It <strong>never repeats</strong> inside a session, so you cannot learn the pattern
  and pre-aim it. It has <strong>no corners</strong> &mdash; the path is smooth
  everywhere, so there is never a sudden direction change that turns the drill into a
  reaction test rather than a tracking one. And it is a <strong>pure function of
  time</strong>: the target's position depends only on how long the session has been
  running, not on where it was last frame, so the path cannot drift, accumulate error,
  or wander off the playfield. The two amplitudes sum to one, which is what
  mathematically guarantees the target stays inside the box.</p>

  <p>The target is drawn entirely with a CSS transform rather than by changing its
  position properties, so the render loop never triggers layout. That is not a
  micro-optimisation for its own sake: a layout pass inside the animation frame would
  show up as jitter, and jitter in a tracking drill is indistinguishable from your own
  hand shaking.</p>

  <h2 id="sampling">How time on target is measured</h2>
  <p>Your cursor position is read on every <code>pointermove</code> event, and the
  inside/outside test runs on every animation frame. Each frame adds its own elapsed
  time to the on-target total if the crosshair was inside the circle at that moment, and
  the total is divided by the session length at the end. Frame gaps longer than 100ms
  are clamped, so a browser tab that stalls cannot award or deny you a large block of
  time in one go.</p>

  <p>Sampling per frame rather than per mouse event matters. If you hold the mouse
  perfectly still while the target moves over your crosshair, no pointer event fires at
  all &mdash; an event-driven measurement would score that as nothing happening, when in
  fact you were on target the whole time. Conversely a fast mouse fires far more events
  than there are frames, and counting those would weight rapid movement more heavily
  than slow movement for no reason.</p>

  <h2 id="reading">Reading your percentage</h2>
  <p>Around 50 to 65 percent is solid smooth tracking on this drill's target size and
  speed. Past 75 percent means you are <em>leading</em> the target &mdash; predicting
  where it is going and putting the crosshair there &mdash; rather than chasing it,
  which is the actual skill and the thing that separates good tracking from fast
  reactions. Below about 40 percent, the usual cause is not reflexes but sensitivity.</p>

  <p>That is the single most useful thing this drill will tell you. If you are
  constantly overshooting and sawing back and forth across the target, your sensitivity
  is too high for the movement. If you run out of mousepad or your arm lags behind on
  the faster sweeps, it is too low. Tracking exposes a sensitivity mismatch far more
  clearly than flicking does, because flicking lets you correct at the end of every
  movement and tracking gives you nowhere to hide.</p>

%(faq)s

%(keep)s"""

TRACKING_FAQ = [
    ("Do I need to click anything?",
     "No. There is nothing to click and clicking does nothing &mdash; the drill only "
     "measures where your crosshair is. Just move the mouse and keep the crosshair "
     "inside the moving circle for as much of the session as you can."),
    ("What is a good time-on-target percentage?",
     "On this drill's target size and speed, 50&ndash;65% is solid and past 75% means you "
     "are leading the target rather than chasing it. Those are this page's own difficulty "
     "bands, not a population statistic: a bigger target or a slower path would move them "
     "immediately."),
    ("Why does my score jump around between runs?",
     "The path's phases are randomised every session, so one run may happen to sweep "
     "mostly across your comfortable arc and another mostly against it. Take the trend "
     "over several runs rather than any single number, and prefer the sixty-second option "
     "&mdash; it averages out far more of that variation."),
    ("Does this drill work on a phone or a tablet?",
     "No, and it is the one drill here that does not. A touchscreen only reports a "
     "position while a finger is pressed down, so the moment you lift the finger the "
     "drill sees no crosshair at all &mdash; and while the finger is down it hides the "
     "target underneath it. Use a mouse or a trackpad for this one. The other six drills "
     "are fine on touch."),
    ("Should I use a different sensitivity for tracking?",
     "Most people find they want slightly lower sensitivity for tracking than for "
     "flicking, and having to choose is exactly why this drill is useful. Rather than "
     "switching between two settings, use the score to find one you can both flick and "
     "track at &mdash; that is the setting that will hold up in a game."),
]

PRECISION_BODY = """  <h2>Precision Trainer</h2>

  <p>Small targets that do not shrink and do not rush you. One at a time, held for
  nearly two seconds, at a fixed 26-pixel size. Your score is <strong>accuracy
  first</strong> &mdash; the share of your clicks that landed on something &mdash; with
  speed reported alongside it rather than instead of it. This is the drill where taking
  your time is the correct strategy.</p>

  <h2 id="why-accuracy">Why accuracy is the headline</h2>
  <p>Every other drill on this site rewards speed, and speed drills quietly teach a bad
  habit: firing before the crosshair has settled, on the assumption that a fast miss
  costs less than a slow hit. In a timed drill that assumption is correct, which is the
  problem. In a game it is usually wrong &mdash; a missed shot is a missed shot plus the
  time to fire again plus whatever the target did in between.</p>

  <p>So this drill inverts the incentive. The rating is read from your accuracy, not
  your average time, and the targets are held long enough that there is no excuse for
  rushing. If you finish a run with 96 percent accuracy and a slow average, that is a
  good result here and the rating will say so. That is the opposite of how the
  <a href="/">flick drill</a> scores you, on purpose.</p>

  <h2 id="small-static">Small, static, and patient</h2>
  <p>Three configuration choices define this drill, and each removes a variable the
  other drills deliberately include.</p>

  <p><strong>The targets are small.</strong> 26 pixels across, against the flick drill's
  58. A small target punishes a wobbly final approach in a way a large one absorbs
  silently, so the errors this drill surfaces are the ones you would otherwise never
  notice.</p>

  <p><strong>They do not shrink.</strong> The flick drill shrinks its targets over their
  lifespan, which adds urgency &mdash; hesitate and the target you were aiming at gets
  harder. Here the target you started aiming at is the target you finish aiming at, so
  nothing punishes a careful correction.</p>

  <p><strong>They last much longer.</strong> Roughly 1.9 seconds against 1.3, which is
  ample time to move, settle and fire deliberately. The lifespan exists at all only so
  that walking away from the keyboard does not leave a session hanging.</p>

  <h2 id="micro">What it actually trains</h2>
  <p>The last few pixels. Most of an aiming movement is a large fast motion that gets
  you approximately there, and the part that decides whether you hit is the short
  correction at the end &mdash; the micro-adjustment. On a large target the correction
  can be sloppy and still land. On a small one it cannot, so this is the drill that tells
  you how good your micro-adjustment really is.</p>

  <p>It is also the best diagnostic on this site for grip and sensitivity. A tremor at
  the end of the movement usually means you are gripping too tightly or aiming with your
  fingers rather than your wrist and arm. Systematic overshoot means your sensitivity is
  higher than your hand's resolution &mdash; you cannot reliably move the crosshair less
  than the width of one of these targets. Both faults are invisible at 58 pixels and
  obvious at 26.</p>

  <h2 id="using">Using it alongside the other drills</h2>
  <p>Precision is the cool-down to gridshot's warm-up. Run it after you have been
  flicking for a while, when your hand is warm and slightly tired, because that is when
  form breaks down and this drill will show you exactly how. A useful routine is one
  gridshot run to calibrate, several minutes of whatever you are actually training, and
  a thirty-target precision run at the end &mdash; if the accuracy on that last run is
  well below your normal, you trained past the point where you were still training
  anything good.</p>

  <p>Count mode suits this drill better than timed mode, and it is the one drill here
  where that is true. A fixed number of targets removes the clock entirely, which means
  removing the last reason to rush.</p>

%(faq)s

%(keep)s"""

PRECISION_FAQ = [
    ("Is a slow run really a good result here?",
     "Yes, if it is accurate. The rating tiers on this page read from your accuracy "
     "rather than your average time, because the whole point of the drill is to practise "
     "not firing before the crosshair has settled. Speed is still reported &mdash; it is "
     "just not what you are graded on."),
    ("Why don't the targets shrink like they do on the main trainer?",
     "Shrinking adds time pressure, and time pressure is what this drill removes. A "
     "target that gets harder while you correct punishes careful correction, which is the "
     "exact habit this page exists to build."),
    ("Should I use timed or count mode?",
     "Count. A fixed number of targets takes the clock out of the drill completely, which "
     "is the last thing that might tempt you to rush. Thirty targets is a good default."),
    ("My accuracy is high but my time is terrible. Is that bad?",
     "Not on this drill. It becomes a problem only if the same gap shows up on the flick "
     "drill, where speed is what is being measured. Running both and comparing is how you "
     "find out whether you are genuinely deliberate or just slow."),
]


# ---------------------------------------------------------------------------
# The three game pages
#
# These used to be one template with the game's name substituted in, which made
# them 61% identical to each other as measured on five-word sequences. Three
# pages that say the same thing compete with each other and none of them wins.
#
# They are written out separately now because the three games genuinely set
# different aiming problems. Counter-Strike is a one-bullet game decided by a
# stopped first shot. Valorant is a one-bullet game decided by utility and a
# pre-aimed angle. Fortnite is a two-hundred-effective-hit-point game decided by
# how fast you can reacquire somebody who keeps rebuilding the room. The tuning
# numbers on each page follow from that, and so does the prose.
#
# test/scoring.test.js asserts the pairwise five-gram overlap stays under 25%.
# ---------------------------------------------------------------------------

CSGO_BODY = """  <h2>Counter-Strike aim is a stopped first bullet</h2>

  <p>Counter-Strike hands you a perfectly accurate first shot while you stand still, and
  takes it back the moment you move. Every other aiming habit in the game follows from
  that one rule. An AK-47 bullet to the head kills through a helmet at any distance on
  any map, so a stopped player whose crosshair is already at head height wins the duel
  before time-to-kill means anything. The M4A4 and the M4A1-S do not, which is why the
  two sides of the same round aim slightly differently for the same shot.</p>

  <p>This drill trains the stopped first bullet and nothing else. It gives you the
  longest window on the site on purpose, because in Counter-Strike the shot you set up
  beats the shot you rush, and a drill that rewards rushing would teach the opposite of
  what the game pays for.</p>

  <div class="callout">
    <strong>Counter-Strike tuning.</strong> A target opens at <strong>%(start)spx</strong>,
    closes to <strong>%(end)spx</strong>, and lives for <strong>%(life)sms</strong>. That
    is the most patient window here. Rushing costs you accuracy and buys you almost
    nothing, which is the trade the game makes.
  </div>

  <h2 id="sens">Sensitivity: read it in centimetres, not in the menu number</h2>

  <p>The number in the Counter-Strike video menu means nothing on its own, because it is
  multiplied by your mouse DPI. The two figures players actually compare are eDPI, which
  is DPI multiplied by in-game sensitivity, and cm/360, which is how far the mouse
  travels to turn all the way round.</p>

  <p>Professional Counter-Strike has settled into a narrow band. Almost everybody runs
  400 or 800 DPI, with an in-game sensitivity that puts eDPI somewhere between 700 and
  1000. At 800 eDPI a full turn takes about 52 cm of mousepad. That is a low
  sensitivity by the standards of most other shooters, and it is low for a reason: the
  game asks for small, exact corrections at head height far more often than it asks for
  large turns, and a low sensitivity makes small corrections cheap.</p>

  <p>One more setting belongs here. Leave <code>zoom_sensitivity_ratio_mouse</code> at
  1.0. It keeps your scoped AWP sensitivity matched to your unscoped sensitivity in
  degrees per centimetre, so the same hand movement means the same rotation whether you
  are scoped or not. Practising two different sensitivities is the fastest way to be
  mediocre at both.</p>

  <p>Set this page to the sensitivity you are about to play at. A warm-up at the wrong
  sensitivity is worse than no warm-up, because you spend the first rounds unlearning
  it.</p>

  <h2 id="flick">What a flick means in Counter-Strike</h2>

  <p>Less than you would think. Counter-Strike is a crosshair-placement game: you walk
  the map with the crosshair already at head height on the angle you are about to clear,
  so the usual correction when somebody appears is a few degrees, not a swing. Players
  who flick a long way in Counter-Strike are usually paying for a placement mistake they
  made two seconds earlier.</p>

  <p>The genuine long flick in this game is the AWP snap. One bullet anywhere above the
  legs ends the round, the rifle is slow to re-chamber, and the scope narrows your view
  to the point where an off-angle appearance really is a swing. That is one shot per
  fight at most, which is why the drill here is a single target at a time rather than a
  stream.</p>

  <h2 id="recoil">Spray control is a different skill, and this page does not have it</h2>

  <p>Counter-Strike recoil is deterministic. The AK-47 throws the first ten bullets up
  and then sideways in the same shape every single time, and controlling it means
  pulling the mouse along that shape from memory while counter-strafing to keep your
  feet still. It is pattern memorisation plus footwork.</p>

  <p>None of that exists in a browser page with no weapon, no recoil model and no
  movement keys. This drill covers the part of the fight that happens before recoil
  starts: finding the head and stopping on it. Learn the spray in the game, on a
  practice map, against a wall.</p>

  <h2 id="check">Reading your result</h2>

  <p>Compare your accuracy here against your accuracy on the
  <a href="/valorant-aim-trainer/">Valorant tuning</a>. The Valorant page gives you 400ms
  less per target and a smaller target. If your accuracy is not clearly better on this
  page, you are firing on arrival rather than on settling, and the extra 400ms is
  telling you so.</p>

  <p>Your number here also includes your monitor's refresh interval, your mouse polling
  rate and your operating system's input stack. Those are the same for every run on the
  same machine, so the trend is meaningful even though the absolute value is not a
  measurement of you alone.</p>

%(faq)s

%(keep)s"""


VALORANT_BODY = """  <h2>One bullet to the head, and the head is small</h2>

  <p>A Vandal round to the head does 160 damage at every range in Valorant. A full-health
  opponent with full shields has 150 effective hit points. There is no time-to-kill to
  discuss: you either put the first bullet in the head or you start a fight you might
  lose. The Phantom is almost the same story, except that its headshot damage falls from
  156 to 140 past about 15 metres, which still kills an unshielded head and still makes
  distance a decision rather than a detail.</p>

  <p>That is the whole reason this page carries the smallest targets on the site. The
  defining demand in Valorant is not speed of arrival, it is landing inside a small area
  on the first attempt.</p>

  <div class="callout">
    <strong>Valorant tuning.</strong> A target opens at <strong>%(start)spx</strong>,
    closes to <strong>%(end)spx</strong>, and lives for <strong>%(life)sms</strong>.
    Small and brief. Expect your accuracy on this page to sit several points below what
    you score on the <a href="/csgo-aim-trainer/">Counter-Strike tuning</a>, and do not
    read that as getting worse.
  </div>

  <h2 id="edpi">eDPI, and why Valorant numbers look so small</h2>

  <p>Valorant players compare eDPI, which is mouse DPI multiplied by the in-game
  sensitivity. The professional band sits between roughly 200 and 360, which usually
  means 800 DPI with an in-game sensitivity between 0.25 and 0.45.</p>

  <p>Those numbers look tiny next to Counter-Strike, and the reason is arithmetic rather
  than preference: Valorant's sensitivity scale is about three times coarser, so the same
  arm movement needs about a third of the number. A Valorant sensitivity of 0.35 and a
  Counter-Strike sensitivity of 1.1 turn you about the same distance. Convert between
  the two by dividing or multiplying by 3.18, and never by copying the raw value.</p>

  <p>Set the scoped multiplier to 1.0 unless you have a specific reason not to. It keeps
  the Operator matched to your hip sensitivity in degrees per centimetre.</p>

  <p>Whatever you play at, play this page at the same figure. A warm-up at a different
  sensitivity recalibrates your hand away from the one you are about to need.</p>

  <h2 id="flick">A Valorant flick is usually a correction, not a swing</h2>

  <p>Valorant duels are fought at known angles. Utility decides where and when the fight
  happens, so by the time an enemy is visible you should already be looking at head
  height on the spot they have to walk through. The adjustment that follows is small,
  and it has to be exact.</p>

  <p>The exceptions are the agents who create their own angles. A Jett dash, a Raze
  satchel jump and a Chamber teleport all put somebody somewhere you were not aiming,
  and those are genuine swings. So is an Operator hold that gets peeked from the wrong
  side. Both are one-shot situations, which is why this drill spawns one target at a
  time and scores you on whether you got it, not on how many you cleared.</p>

  <h2 id="movement">Standing still is a mechanic here</h2>

  <p>Valorant punishes firing while moving more heavily than most shooters. Your bullets
  go where you were pointing only if your feet have stopped, and the game gives you a
  short window after releasing a key before accuracy returns. Good players are
  constantly stopping, firing and moving again on a rhythm.</p>

  <p>A browser page has no movement keys, so it cannot train that rhythm. What it can
  train is the half of the habit that lives in your hand: settle, then fire. If you
  catch yourself clicking as the crosshair is still arriving on this page, you are doing
  the same thing in game and blaming the spread.</p>

  <h2 id="utility">What this drill deliberately leaves out</h2>

  <p>Aim is a minority of Valorant. Flashes, smokes, mollies, recon darts and trip wires
  decide most rounds before anybody shoots, and a browser page has none of them. It also
  has no peeker's advantage, no server tick, no shields and no crosshair-placement
  discipline, because there is no map to place a crosshair on.</p>

  <p>Treat this as ninety seconds of hand calibration before you queue. That is a real
  benefit and a small one, and anybody promising more from a web page is selling
  something.</p>

%(faq)s

%(keep)s"""


FORTNITE_BODY = """  <h2>Two hundred hit points, and none of them stand still</h2>

  <p>A Fortnite opponent has 100 health and up to 100 shield. Nothing in the loot pool
  reliably deletes 200 effective hit points in one shot, so a fight is a sequence:
  connect, they build, you reacquire, connect again. Time-to-kill is long by the
  standards of Counter-Strike and Valorant, and the aiming problem that follows is
  completely different. You are not being asked for one perfect bullet. You are being
  asked to keep finding somebody who will not stay found.</p>

  <p>So this page carries the largest targets on the site and the shortest window. The
  difficulty is arriving inside the window, not landing inside a small area.</p>

  <div class="callout">
    <strong>Fortnite tuning.</strong> A target opens at <strong>%(start)spx</strong>,
    closes to <strong>%(end)spx</strong>, and lives for only
    <strong>%(life)sms</strong>. This is the exact opposite trade from the
    <a href="/valorant-aim-trainer/">Valorant tuning</a>. Watch your average
    time-to-click here, not your accuracy.
  </div>

  <h2 id="sens">Fortnite sensitivity is four numbers, not one</h2>

  <p>Fortnite does not have a single sensitivity slider. It has X and Y sensitivity as
  percentages, a Targeting multiplier for aiming down sights, a Scope multiplier for
  optics, and separate Build and Edit sensitivities that only affect how fast you turn
  while placing or editing a piece.</p>

  <p>Competitive players usually run 800 DPI with X and Y between about 6 and 9 per
  cent, and set Targeting and Scope somewhere between 40 and 55 per cent. Build and Edit
  sensitivity are then set much higher, often 1.7x to 2.3x, because turning a hundred and
  eighty degrees to place a wall behind you is a different job from lining up a head.</p>

  <p>That split is why Fortnite aim feels unstable to players arriving from other
  shooters: you are running two sensitivities in the same fight and switching between
  them several times a second. Match the hipfire figure when you use this page, since
  that is the one your shotgun uses.</p>

  <h2 id="bloom">Bloom caps how precise it is worth being</h2>

  <p>Most Fortnite automatic weapons fire into a spread cone rather than at a point. The
  cone is small on the first shot from a standstill and opens up as you keep firing,
  jump, or sprint. There is no fixed recoil pattern to memorise, because the scatter is
  random inside the cone.</p>

  <p>The practical consequence is that past a certain point extra precision buys you
  nothing, and the skill becomes shot pacing and positioning instead. Tapping a rifle
  from a standstill keeps the cone tight. Holding the trigger while jumping does not.
  This drill cannot simulate any of that, and it does not try.</p>

  <h2 id="flick">The Fortnite flick is a box fight</h2>

  <p>Here is the shot this page is built around. You are in a one-by-one box. Somebody
  edits a wall, and for roughly a fifth of a second there is a human-sized opening with a
  human in it, three metres away. You snap, you fire a shotgun, and either you took half
  their health or you did not.</p>

  <p>That is a very large target, a very large angular distance, and a very short window,
  which is exactly the 68px, 900ms shape this page uses. It is also why Fortnite players
  can have excellent aim by their own game's standard and still score poorly on drills
  built for Counter-Strike: they have trained a different motor skill, and it is the
  correct one for their game.</p>

  <h2 id="axis">The third axis</h2>

  <p>The other two games are played on flat ground against opponents at roughly your own
  eye level. Fortnite is played on ramps, in towers and out of the sky, so a large share
  of engagements need a vertical correction as well as a horizontal one, and your Y
  sensitivity matters as much as your X.</p>

  <p>A flat browser page cannot reproduce height, but random spawn positions do at least
  spread your corrections across both axes. If you find your downward flicks are
  consistently worse than your upward ones, that is real and it will show up on a ramp.</p>

  <h2 id="controller">One honest caveat about controller</h2>

  <p>A large part of the Fortnite player base plays on a controller with aim assist,
  which is a fundamentally different skill: the game is helping you track, and your job
  becomes managing that help rather than producing the movement yourself. This is a
  mouse drill. It will not tell a controller player anything useful about their aim, and
  a poor score on it does not mean what it would mean for a mouse player.</p>

%(faq)s

%(keep)s"""


PAGES = [
    {
        "slug": "gridshot",
        "faq": GRIDSHOT_FAQ,
        "engine": "gridshot", "preset": None,
        "title": "Gridshot Aim Trainer - Free 3x3 Grid Drill, No Download",
        "description": (
            "Free gridshot trainer in your browser. Nine fixed positions, three targets live "
            "at once, scored in targets per second over 15, 30 or 60 seconds. No download, no "
            "sign-up, nothing uploaded."
        ),
        "jsonld_name": "Gridshot Aim Trainer",
        "jsonld_desc": (
            "Free browser-based gridshot aim training drill: a fixed 3x3 grid with three "
            "targets live simultaneously, scored in targets cleared per second."
        ),
        "mq2": "Grid",
        "marquee_sub": "Nine Cells &middot; Three Live &middot; flicktrainer.com",
        "attract_1": "Grid", "attract_2": "Shot",
        "attract_blink": "Insert Coin &mdash; Nine Cells",
        "modes": False,
        "hud": ["primary", "hits", "misses", "acc", "combo"],
        "best": ["primary:Best Rate", "accuracy:Best Acc"],
        "tiles": ["hits", "misses", "accuracy", "avgtime", "throughput", "primary:Best Rate"],
        "howto": (
            "Your score is <strong>targets per second</strong>: hits divided by session "
            "length. Steady grid shooting on this configuration sits around 1.2&ndash;1.5/s, "
            "and past 1.8/s you are flicking straight to the next target rather than hunting "
            "for it. Targets never expire here, so a miss is only ever a shot that landed on "
            "empty space."
        ),
        "body": GRIDSHOT_BODY % {
            "faq": faq(GRIDSHOT_FAQ),
            "keep": keep_reading([
                ("/tracking-trainer/", "Tracking Trainer", "The opposite motor problem: one target on a smooth path, scored on time on target rather than a rate."),
                ("/precision-trainer/", "Precision Trainer", "Small static targets and no time pressure &mdash; the drill that shows you your micro-adjustment."),
                ("/", "Flick Trainer", "Random spawns and shrinking targets, scored on average time-to-click. Visual search included."),
            ]),
        },
    },
    {
        "slug": "tracking-trainer",
        "faq": TRACKING_FAQ,
        "engine": "tracking", "preset": None,
        "title": "Tracking Aim Trainer - Free Smooth-Target Tracking Drill",
        "description": (
            "Free tracking aim trainer in your browser. Keep your crosshair inside one target "
            "moving on a smooth randomised path; scored on the percentage of the session you "
            "stayed on it. No download, nothing uploaded."
        ),
        "jsonld_name": "Tracking Aim Trainer",
        "jsonld_desc": (
            "Free browser-based tracking aim training drill: a single target moving on a "
            "smooth randomised path, scored as the percentage of the session the cursor spent "
            "inside it."
        ),
        "mq2": "Track",
        "marquee_sub": "Stay On Target &middot; flicktrainer.com",
        "attract_1": "Smooth", "attract_2": "Track",
        "attract_blink": "Insert Coin &mdash; Stay On Target",
        "modes": False,
        "hud": ["primary", "ontarget"],
        "best": ["primary:Best On Target"],
        "tiles": ["ontarget", "primary:Best On Target"],
        "howto": (
            "There is nothing to click. Keep your crosshair inside the moving target and you "
            "are scored on <strong>time on target</strong> &mdash; the share of the session it "
            "was inside, sampled every animation frame rather than on mouse events. "
            "50&ndash;65% is solid on this target size and speed; past 75% means you are "
            "leading the target rather than chasing it."
        ),
        "body": TRACKING_BODY % {
            "faq": faq(TRACKING_FAQ),
            "keep": keep_reading([
                ("/gridshot/", "Gridshot", "The opposite motor problem: ballistic movement between nine known positions, scored as a rate."),
                ("/precision-trainer/", "Precision Trainer", "Small static targets and no time pressure &mdash; the other drill that exposes a sensitivity mismatch."),
                ("/articles/flick-vs-tracking-aim.html", "Flicking vs. Tracking", "Why they are different skills, and which one your game actually asks for."),
            ]),
        },
    },
    {
        "slug": "precision-trainer",
        "faq": PRECISION_FAQ,
        "engine": "precision", "preset": None,
        "title": "Precision Aim Trainer - Small Static Targets, Accuracy First",
        "description": (
            "Free precision aim trainer in your browser. Small 26px targets that do not shrink "
            "and do not rush you, scored on accuracy first rather than speed. No download, "
            "nothing uploaded."
        ),
        "jsonld_name": "Precision Aim Trainer",
        "jsonld_desc": (
            "Free browser-based precision aim training drill: small static targets with a long "
            "lifespan, rated on accuracy rather than reaction speed."
        ),
        "mq2": "Precise",
        "marquee_sub": "Slow Is Smooth &middot; flicktrainer.com",
        "attract_1": "Dead", "attract_2": "Centre",
        "attract_blink": "Insert Coin &mdash; Take Your Time",
        "modes": True,
        "hud": ["primary", "hits", "misses", "acc", "combo"],
        "best": ["accuracy:Best Acc", "avgtime:Best Time"],
        "tiles": ["hits", "misses", "accuracy", "avgtime", "throughput", "avgbest:Best Time"],
        "howto": (
            "You are rated on <strong>accuracy</strong> here, not speed. Targets are 26px, do "
            "not shrink, and last nearly two seconds, so there is no reason to fire before the "
            "crosshair has settled &mdash; a slow clean run beats a fast sloppy one, which is "
            "the opposite of every other drill on this site. Count mode suits it best."
        ),
        "body": PRECISION_BODY % {
            "faq": faq(PRECISION_FAQ),
            "keep": keep_reading([
                ("/gridshot/", "Gridshot", "Nine fixed positions and three live targets, scored as a rate rather than on accuracy."),
                ("/tracking-trainer/", "Tracking Trainer", "Continuous correction instead of a settled shot &mdash; the other half of a sensitivity check."),
                ("/", "Flick Trainer", "Larger shrinking targets under time pressure, scored on average time-to-click."),
            ]),
        },
    },
]

PRESET_CFG = {
    "valorant": {"start": 44, "end": 30, "life": 1100},
    "csgo": {"start": 52, "end": 38, "life": 1500},
    "fortnite": {"start": 68, "end": 44, "life": 900},
}

PRESET_PAGES = [
    {
        "slug": "valorant-aim-trainer", "engine": None, "preset": "valorant",
        "game": "Valorant",
        "body_tpl": VALORANT_BODY,
        "title": "Valorant Aim Trainer - Free Browser Drill, Vandal One-Tap Tuning",
        "description": (
            "Free Valorant aim trainer in your browser. Small 44px targets on a short 1100ms "
            "lifespan, tuned for the Vandal one-tap at head level. Real eDPI guidance. No "
            "download, nothing uploaded."
        ),
        "jsonld_name": "Valorant Aim Trainer",
        "jsonld_desc": (
            "Free browser-based aim trainer tuned for Valorant: small targets on a short "
            "lifespan, scored on average time-to-click and accuracy."
        ),
        "mq2": "Tap",
        "marquee_sub": "One Tap &middot; Head Level &middot; flicktrainer.com",
        "attract_1": "Head", "attract_2": "Level",
        "attract_blink": "Insert Coin &mdash; One Tap",
        "faq": [
            ("How do I convert my Counter-Strike sensitivity to Valorant?",
             "Keep the same DPI and divide the Counter-Strike figure by 3.18. A Counter-Strike "
             "sensitivity of 1.1 becomes a Valorant sensitivity of about 0.35. Never copy the "
             "raw number across, because the two games scale it differently."),
            ("Will this improve my rank?",
             "It warms your hand up. Rank in Valorant turns far more on utility, positioning "
             "and communication than on raw aim, and no browser page touches any of those. "
             "Use it as a ninety-second warm-up before you queue."),
            ("Are these the real hitbox sizes?",
             "No. A hitbox is a three-dimensional volume on an animating model at a variable "
             "distance. This is a flat circle on a web page. The tuning copies how the aiming "
             "problem <em>feels</em>, which is the most a browser drill can honestly claim."),
            ("Why is my accuracy worse here than on the other two game pages?",
             "Because the targets are smaller and the window is shorter, which is deliberate. "
             "Compare this page against your own earlier runs on this page, not against the "
             "<a href=\"/fortnite-aim-trainer/\">Fortnite tuning</a>."),
        ],
    },
    {
        "slug": "csgo-aim-trainer", "engine": None, "preset": "csgo",
        "game": "CS:GO",
        "body_tpl": CSGO_BODY,
        "title": "CS:GO Aim Trainer - Free Browser Drill for CS2 One-Taps",
        "description": (
            "Free CS:GO and CS2 aim trainer in your browser. Medium 52px targets on a patient "
            "1500ms lifespan, tuned for the stopped first bullet. Real eDPI and cm/360 "
            "guidance. Nothing uploaded."
        ),
        "jsonld_name": "CS:GO Aim Trainer",
        "jsonld_desc": (
            "Free browser-based aim trainer tuned for Counter-Strike: medium targets on a "
            "longer lifespan, scored on average time-to-click and accuracy."
        ),
        "mq2": "Burst",
        "marquee_sub": "Counter Strike Tuning &middot; flicktrainer.com",
        "attract_1": "Spray", "attract_2": "Control",
        "attract_blink": "Insert Coin &mdash; Hold The Angle",
        "faq": [
            ("What eDPI should I use for Counter-Strike?",
             "Most professionals sit between 700 and 1000, which is 400 or 800 DPI with a low "
             "in-game figure. Pick one value inside that band, then leave it alone for a "
             "month. Changing it weekly is what actually holds people back."),
            ("Does this drill teach the AK-47 spray pattern?",
             "No. The pattern is a fixed shape you pull from memory while counter-strafing to "
             "keep your feet still, and this page has no weapon, no recoil model and no "
             "movement keys. Learn it in game, on a practice map, against a wall."),
            ("Is this tuning right for CS2 as well as CS:GO?",
             "Yes. CS2 changed the tick model and rewrote the smokes. It did not change the "
             "fact that a stopped bullet to the head ends the duel, and that is the whole "
             "subject of this page."),
            ("Why is the window longer here than on the other two game pages?",
             "Because Counter-Strike pays for patience. Firing on arrival rather than on "
             "settling is the most expensive habit in the game, and a drill that rewarded a "
             "rushed click would train exactly that."),
        ],
    },
    {
        "slug": "fortnite-aim-trainer", "engine": None, "preset": "fortnite",
        "game": "Fortnite",
        "body_tpl": FORTNITE_BODY,
        "title": "Fortnite Aim Trainer - Free Browser Drill for Box Fight Snaps",
        "description": (
            "Free Fortnite aim trainer in your browser. Large 68px targets on a 900ms "
            "lifespan, tuned for the box-fight shotgun snap. Real sensitivity guidance for "
            "all four sliders. Nothing uploaded."
        ),
        "jsonld_name": "Fortnite Aim Trainer",
        "jsonld_desc": (
            "Free browser-based aim trainer tuned for Fortnite: larger targets on a short "
            "lifespan, emphasising fast target acquisition."
        ),
        "mq2": "Swap",
        "marquee_sub": "Fast Swaps &middot; flicktrainer.com",
        "attract_1": "Quick", "attract_2": "Swap",
        "attract_blink": "Insert Coin &mdash; Fast Hands",
        "faq": [
            ("What sensitivity do Fortnite professionals use?",
             "Commonly 800 DPI with X and Y between 6 and 9 per cent, Targeting and Scope near "
             "50 per cent, and a much higher Build and Edit sensitivity. There is no single "
             "correct pair, because the four sliders trade against each other."),
            ("Does this train building or editing?",
             "No. Building and editing are keybind reflexes with no aiming component at all. "
             "Practise those in Creative, where you can reset a box in a second and repeat it "
             "a thousand times."),
            ("I play on a controller. Is this useful?",
             "Not very. Aim assist changes the task from producing the movement yourself to "
             "managing the help the game gives you, and a mouse drill measures only the first "
             "of those. A poor score here does not mean much for a controller player."),
            ("Should I use timed or count mode?",
             "Timed, at 30 or 60 seconds. This tuning is about sustaining fast reacquisition, "
             "and a fixed target count lets you rest between targets in a way that a box fight "
             "never will."),
        ],
    },
]

for p in PRESET_PAGES:
    cfg = PRESET_CFG[p["preset"]]
    p["modes"] = True
    p["hud"] = ["primary", "hits", "misses", "acc", "combo"]
    p["best"] = ["accuracy:Best Acc", "avgtime:Best Time"]
    p["tiles"] = ["hits", "misses", "accuracy", "avgtime", "throughput", "avgbest:Best Time"]
    p["howto"] = (
        "Targets start at <strong>%(start)spx</strong>, shrink to <strong>%(end)spx</strong> "
        "and last <strong>%(life)sms</strong>, against the default drill's 58px, 34px and "
        "1300ms. You are rated on average time-to-click, with accuracy and throughput "
        "alongside it." % cfg
    )
    p["body"] = p["body_tpl"] % {
        "start": cfg["start"],
        "end": cfg["end"],
        "life": cfg["life"],
        "faq": faq(p["faq"]),
        "keep": keep_reading([
            ("/gridshot/", "Gridshot",
             "Nine fixed positions, three targets live at once, scored in targets per second."),
            ("/tracking-trainer/", "Tracking Trainer",
             "One target on a smooth path, scored on the share of the session your crosshair "
             "was inside it."),
            ("/precision-trainer/", "Precision Trainer",
             "Small static targets, accuracy first &mdash; the drill where taking your time "
             "is correct."),
        ]),
    }

ALL_PAGES = PAGES + PRESET_PAGES


# --------------------------------------------------------------------------
# The shell
# --------------------------------------------------------------------------

HUD_PARTS = {
    "primary": '<div class="rh-stat"><span class="rh-label" id="hud-primary-label">Time</span><span class="rh-val" id="hud-primary-val">--</span></div>',
    "hits": '<div class="rh-stat"><span class="rh-label">Hits</span><span class="rh-val" id="hud-hits">0</span></div>',
    "misses": '<div class="rh-stat"><span class="rh-label">Miss</span><span class="rh-val" id="hud-misses">0</span></div>',
    "acc": '<div class="rh-stat"><span class="rh-label">Acc</span><span class="rh-val" id="hud-accuracy">--</span></div>',
    "combo": '<div class="rh-stat rh-combo" id="combo-wrap"><span class="rh-label">Combo</span><span class="rh-val" id="hud-combo">0</span></div>',
    "ontarget": '<div class="rh-stat"><span class="rh-label">On Target</span><span class="rh-val" id="hud-ontarget">--</span></div>',
}

TILE_IDS = {
    "hits": ("Hits", "res-hits", "0"),
    "misses": ("Misses", "res-misses", "0"),
    "accuracy": ("Accuracy", "res-accuracy", "0%"),
    "avgtime": ("Avg Time", "res-avgtime", "&mdash;"),
    "throughput": ("Throughput", "res-throughput", "0/s"),
    "ontarget": ("On Target", "res-ontarget", "&mdash;"),
}

BEST_IDS = {"primary": "best-primary-val", "accuracy": "best-accuracy-val", "avgtime": "best-avgtime-val"}


def render(p):
    slug = p["slug"]
    url = "https://flicktrainer.com/%s/" % slug

    body_attrs = ""
    if p["engine"]:
        body_attrs += ' data-engine="%s"' % p["engine"]
    if p["preset"]:
        body_attrs += ' data-preset="%s"' % p["preset"]

    # --- setup controls ---
    controls = []
    if p["modes"]:
        controls.append("""          <div class="deck-field">
            <span class="deck-label">Mode</span>
            <div class="segmented segmented--lg" role="group" aria-label="Game mode" id="mode-select">
              <button type="button" class="mode-opt" data-mode="timed" aria-pressed="true">Timed</button>
              <button type="button" class="mode-opt" data-mode="count" aria-pressed="false">Count</button>
            </div>
          </div>
""")
    controls.append("""          <div id="timed-options" class="deck-field">
            <span class="deck-label">Duration</span>
            <div class="segmented" role="group" aria-label="Duration" id="duration-select">
              <button type="button" class="duration-opt" data-duration="15" aria-pressed="false">15s</button>
              <button type="button" class="duration-opt" data-duration="30" aria-pressed="true">30s</button>
              <button type="button" class="duration-opt" data-duration="60" aria-pressed="false">60s</button>
            </div>
          </div>
""")
    if p["modes"]:
        # Only shipped where the mode switch exists to reveal it — its handler
        # writes to this element unguarded, and the count spawner only works on
        # the single-target drills anyway.
        controls.append("""          <div id="count-options" class="deck-field" style="display:none;">
            <span class="deck-label">Targets</span>
            <div class="segmented" role="group" aria-label="Target count" id="count-select">
              <button type="button" class="count-opt" data-count="10" aria-pressed="false">10</button>
              <button type="button" class="count-opt" data-count="30" aria-pressed="true">30</button>
              <button type="button" class="count-opt" data-count="50" aria-pressed="false">50</button>
            </div>
          </div>
""")

    best = []
    for spec in p["best"]:
        key, label = spec.split(":")
        best.append(
            '              <div class="best-stat">\n'
            '                <span class="best-stat-label">%s</span>\n'
            '                <span class="best-stat-val" id="%s">&mdash;</span>\n'
            "              </div>" % (label, BEST_IDS[key])
        )

    hud = "\n".join("            " + HUD_PARTS[k] for k in p["hud"])

    tiles = []
    for spec in p["tiles"]:
        if ":" in spec:
            key, label = spec.split(":")
            el = "res-best-primary" if key == "primary" else "res-best-avgtime"
            tiles.append('          <div class="stat-tile"><span class="stat-label">%s</span>'
                         '<span class="stat-val" id="%s">&mdash;</span></div>' % (label, el))
        else:
            label, el, initial = TILE_IDS[spec]
            tiles.append('          <div class="stat-tile"><span class="stat-label">%s</span>'
                         '<span class="stat-val" id="%s">%s</span></div>' % (label, el, initial))

    # --- the drill switcher ---
    sw = ['<nav class="drill-switch" aria-label="Drills and game presets">',
          '  <span class="drill-switch-label" id="ds-drills">Drills</span>',
          '  <ul aria-labelledby="ds-drills">']
    for href, label in DRILLS:
        cur = ""
        if href == "/%s/" % slug:
            cur = ' aria-current="page"'
        elif href == "/" and p["preset"]:
            # A preset IS the flick drill with different numbers, so the drill
            # it belongs to is marked as an ancestor rather than as this page.
            cur = ' aria-current="true"'
        sw.append('    <li><a href="%s"%s>%s</a></li>' % (href, cur, label))
    sw += ["  </ul>",
           '  <span class="drill-switch-label" id="ds-presets">Game presets</span>',
           '  <ul aria-labelledby="ds-presets">']
    for href, label in PRESETS_NAV:
        cur = ' aria-current="page"' if href == "/%s/" % slug else ""
        sw.append('    <li><a href="%s"%s>%s</a></li>' % (href, cur, label))
    sw += ["  </ul>", "</nav>"]
    switch = "\n".join("  " + ln for ln in sw)

    return TEMPLATE % {
        "title": esc(p["title"]),
        "description": esc(p["description"]),
        "url": url,
        "jsonld_name": p["jsonld_name"],
        "jsonld_desc": p["jsonld_desc"],
        "body_attrs": body_attrs,
        "mq2": p["mq2"],
        "marquee_sub": p["marquee_sub"],
        "attract_1": p["attract_1"],
        "attract_2": p["attract_2"],
        "attract_blink": p["attract_blink"],
        "controls": "".join(controls).rstrip("\n"),
        "best": "\n".join(best),
        "hud": hud,
        "tiles": "\n".join(tiles),
        "howto": p["howto"],
        "switch": switch,
        "body": p["body"],
        "h1": esc(p["title"]),
        "faq_ld": faq_jsonld(p["faq"]),
        "crumb_ld": breadcrumb_jsonld(p["jsonld_name"], url),
        "related": related_block(),
        "ad": AD_TAG,
        "erabbit": ERABBIT,
        "v": V,
    }


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="canonical" href="%(url)s">
<meta name="theme-color" content="#1a0808">

<meta property="og:type" content="website">
<meta property="og:title" content="%(title)s">
<meta property="og:description" content="%(description)s">
<meta property="og:url" content="%(url)s">
<meta property="og:image" content="https://flicktrainer.com/assets/og-image.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="%(title)s">
<meta name="twitter:description" content="%(description)s">

<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/css/styles.css?v=%(v)s">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "%(jsonld_name)s",
  "url": "%(url)s",
  "applicationCategory": "Game",
  "operatingSystem": "Any",
  "offers": { "@type": "Offer", "price": "0", "priceCurrency": "USD" },
  "description": "%(jsonld_desc)s"
}
</script>
%(faq_ld)s
%(crumb_ld)s

%(ad)s
</head>
<body%(body_attrs)s>
<a class="skip-link" href="#main">Skip to content</a>

<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="/" aria-label="flicktrainer.com home">
      <span class="brand-mark"><span class="crosshair-mark">&#9678;</span>Flick<span class="accent-word">Trainer</span></span>
      <span class="brand-tag">browser aim training</span>
    </a>
    <div class="header-actions">
      <button id="status-chip" class="status-chip" type="button" title="View your rank, streak &amp; achievements">
        <span class="chip-level" id="chip-level">LV 1</span>
        <span class="chip-streak is-zero" id="chip-streak">&#128293;0</span>
      </button>
      <button id="sound-toggle" class="icon-btn" type="button" aria-label="Toggle sound effects" title="Toggle sound">&#128266;</button>
      <button id="theme-toggle" class="icon-btn" type="button" aria-label="Toggle dark/light theme" title="Toggle theme">&#9680;</button>
    </div>
  </div>
</header>

<!-- nav:start -->
<!-- nav:end -->

<main id="main">
  <div class="cabinet">
    <div class="marquee">
      <h1 class="marquee-logo"><span class="visually-hidden">%(h1)s</span><span class="mq-1" aria-hidden="true">Flick</span><span class="mq-2" aria-hidden="true">%(mq2)s</span></h1>
      <div class="marquee-sub">%(marquee_sub)s</div>
    </div>

    <div class="challenge-banner" id="challenge-banner" hidden>
      <span class="cb-kicker">Challenge</span>
      <span class="cb-text" id="challenge-text"></span>
    </div>

    <!-- ===================== SETUP SCREEN ===================== -->
    <section id="screen-setup" class="screen">
      <div class="crt">
        <div class="crt-screen">
          <div class="range-attract" aria-hidden="true">
            <div class="attract-title"><span class="at-1">%(attract_1)s</span><span class="at-2">%(attract_2)s</span></div>
            <div class="attract-targets">
              <span class="pix-target"></span>
              <span class="pix-target pix-target--sm"></span>
              <span class="pix-target"></span>
            </div>
            <div class="attract-blink blink">%(attract_blink)s</div>
          </div>
        </div>
      </div>

      <div class="deck deck--setup">
        <div class="deck-controls">
%(controls)s
        </div>

        <div class="deck-side">
          <div class="player-card">
            <div class="pc-title">Marksman Card</div>
            <div class="best-row" id="best-row">
%(best)s
            </div>
            <div class="pc-top">
              <span class="pc-rank" id="xp-rank-label">Rookie</span>
              <span class="pc-xp" id="xp-progress-label">0 / 100 XP</span>
            </div>
            <div class="pc-bar"><div class="pc-bar-fill" id="xp-bar-fill"></div></div>
          </div>
          <button type="button" id="start-btn" class="primary start-btn"><span class="start-text">Fire!</span></button>
          <div class="coin-door" aria-hidden="true"><span class="coin-slot"></span>Insert Coin &middot; Free Play</div>
        </div>
      </div>

      <section class="container-narrow" style="padding-top:0;">
        <h2>How this drill is scored</h2>
        <p>%(howto)s</p>
      </section>
    </section>

    <!-- ===================== GAME SCREEN ===================== -->
    <section id="screen-game" class="screen" hidden>
      <div class="crt">
        <div class="crt-screen crt-screen--range">
          <div class="range-hud">
%(hud)s
            <button type="button" id="quit-btn" class="icon-btn quit-btn">Quit</button>
          </div>
          <div class="game-area" id="game-area" tabindex="0"></div>
        </div>
      </div>
    </section>

    <!-- ===================== RESULTS SCREEN ===================== -->
    <section id="screen-results" class="screen" hidden>
      <div class="crt">
        <div class="crt-screen">
          <div class="stage-clear">
            <div class="sc-banner">Stage Clear</div>
            <div class="rating-badge" id="rating-badge">
              <span class="rating-tier" id="rating-tier">&mdash;</span>
              <span class="rating-label" id="rating-label">No data</span>
            </div>
            <p class="rating-compare" id="rating-compare"></p>
          </div>
        </div>
      </div>

      <div class="deck deck--results">
        <div class="stats-grid">
%(tiles)s
        </div>
        <div class="new-best-flag" id="new-best-flag" hidden>New Record &mdash; Sharpshooter!</div>
        <div class="challenge-verdict" id="challenge-verdict" hidden></div>
        <div class="btn-row">
          <button type="button" id="restart-btn" class="primary start-btn"><span class="start-text">Reload</span></button>
          <button type="button" id="share-btn" class="icon-btn">Copy challenge link</button>
          <button type="button" id="change-mode-btn" class="icon-btn">Change Mode</button>
        </div>
      </div>

      <div class="panel history-panel">
        <h2>Recent sessions</h2>
        <div class="history-chart" id="history-chart" aria-hidden="true"></div>
        <ol class="history-list" id="history-list"></ol>
      </div>
    </section>
  </div>
  <!-- /.cabinet -->

%(switch)s

  <section class="achievements-panel" id="achievements-panel">
    <h2>Achievements</h2>
    <div class="achievements-grid" id="achievements-grid"></div>
  </section>

  <section class="container-narrow" style="padding-top:0;">
%(body)s
  </section>
</main>

<div class="toast" id="toast" role="status" aria-live="polite"></div>
<div class="unlock-stack" id="unlock-stack" aria-live="polite"></div>

<footer class="site-footer">
%(related)s
  <div class="footer-inner">
    <div>&copy; <span id="year"></span> flicktrainer.com</div>
    <div class="footer-links">
      <a href="/privacy.html">Privacy</a>
      <a href="/terms.html">Terms</a>
      <a href="&#109;&#97;&#105;&#108;&#116;&#111;&#58;&#104;&#101;&#108;&#108;&#111;&#64;&#103;&#111;&#111;&#100;&#98;&#111;&#116;&#98;&#97;&#100;&#46;&#98;&#111;&#116;">Contact</a>
    </div>
  </div>
</footer>

<script src="/assets/js/app.js?v=%(v)s"></script>
<script src="/assets/js/nav.js?v=%(v)s"></script>
%(erabbit)s
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if any output is stale")
    args = ap.parse_args()

    stale = []
    for p in ALL_PAGES:
        rendered = render(p)
        for target in (ROOT / ("%s.html" % p["slug"]), ROOT / p["slug"] / "index.html"):
            existing = target.read_text(encoding="utf-8") if target.exists() else None
            html = rendered
            if existing:
                nav = NAV_RE.search(existing)
                if nav:
                    html = NAV_RE.sub(
                        lambda m, body=nav.group(2): m.group(1) + body + m.group(3),
                        rendered, count=1)
            if args.check:
                if existing != html:
                    stale.append(target.relative_to(ROOT))
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            if existing != html:
                target.write_text(html, encoding="utf-8")
                print("wrote %s" % target.relative_to(ROOT))

    if args.check:
        if stale:
            for path in stale:
                print("stale: %s" % path, file=sys.stderr)
            print("\nRun `python3 tools/build_drills.py` (then tools/sync_nav.py).", file=sys.stderr)
            return 1
        print("all drill pages up to date")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
