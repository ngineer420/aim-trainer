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
V = "6"

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

GRIDSHOT_BODY = """  <h1>Gridshot</h1>

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

TRACKING_BODY = """  <h1>Tracking Trainer</h1>

  <p>One target, moving continuously on a smooth path that never repeats. There is
  nothing to click. Your score is the percentage of the session your crosshair spent
  <em>inside</em> the target &mdash; <strong>time on target</strong> &mdash; sampled
  continuously rather than at discrete moments. It is the only drill on this site with
  no hits and no misses, because neither concept applies.</p>

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
    ("Should I use a different sensitivity for tracking?",
     "Most people find they want slightly lower sensitivity for tracking than for "
     "flicking, and having to choose is exactly why this drill is useful. Rather than "
     "switching between two settings, use the score to find one you can both flick and "
     "track at &mdash; that is the setting that will hold up in a game."),
]

PRECISION_BODY = """  <h1>Precision Trainer</h1>

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


def preset_body(game, size_note, cfg, why, extra_faq):
    return """  <h1>%(game)s Aim Trainer</h1>

  <p>The flick drill, retuned to feel like %(game)s. Same engine, same scoring, same
  browser &mdash; targets appear one at a time at random positions, shrink over their
  lifespan, and you are scored on average time-to-click, accuracy and throughput. What
  changes is the three numbers that decide how the drill feels, and they are printed
  below rather than left implied.</p>

  <div class="callout">
    <strong>This page's tuning.</strong> Targets start at <strong>%(start)spx</strong>
    and shrink to <strong>%(end)spx</strong> over a lifespan of
    <strong>%(life)sms</strong>, against the default drill's 58px, 34px and 1300ms.
    %(size_note)s
  </div>

  <h2 id="why">Why these numbers</h2>
  %(why)s

  <h2 id="honesty">What this is not</h2>
  <p>It is not a replica of %(game)s's hitboxes, and no browser page can be. A real
  hitbox is a three-dimensional volume attached to an animating skeleton, at a distance,
  behind a weapon with its own spread and recoil model, on a server with its own tick
  rate. What a flat circle on a web page can copy is the <em>feel</em> of the aiming
  problem &mdash; roughly how big the thing you are clicking is relative to the screen,
  and roughly how long you have to do it &mdash; and that is what has been tuned here.</p>

  <p>Treat it as a warm-up that puts your hand in approximately the right register before
  you load the game, not as a simulator. The transferable part of aim training is the
  motor habit, and motor habits do not care whether the target was a circle or a
  character model. Your score here is also, as on every drill on this site, a browser
  measurement: it includes your screen's refresh interval, your mouse's polling rate and
  your operating system's input handling, none of which are you.</p>

  <h2 id="routine">A sensible routine</h2>
  <p>Two or three thirty-second runs before you play, not twenty minutes. Aim training
  has sharply diminishing returns per session and works far better as a short daily habit
  than as an occasional long grind &mdash; the goal before a session is a warm hand and a
  calibrated sense of your sensitivity, both of which take about ninety seconds. If you
  want to actually improve rather than just warm up, the three tier-one drills each
  isolate a different half of the problem: <a href="/gridshot/">gridshot</a> for movement
  between known points, <a href="/tracking-trainer/">tracking</a> for continuous
  correction, <a href="/precision-trainer/">precision</a> for the last few pixels.</p>

  <p>One thing worth doing on this page specifically: keep your in-game sensitivity and
  your desktop sensitivity aligned before you use it. A warm-up at a different
  sensitivity from the one you are about to play at is worse than no warm-up, because you
  spend the first minutes of the match recalibrating away from what you just practised.</p>

%(faq)s

%(keep)s""" % {
        "game": game,
        "start": cfg["start"],
        "end": cfg["end"],
        "life": cfg["life"],
        "size_note": size_note,
        "why": why,
        "faq": faq(extra_faq),
        "keep": keep_reading([
            ("/gridshot/", "Gridshot", "Nine fixed positions, three targets live at once, scored in targets per second."),
            ("/tracking-trainer/", "Tracking Trainer", "One target on a smooth path, scored on the share of the session your crosshair was inside it."),
            ("/precision-trainer/", "Precision Trainer", "Small static targets, accuracy first &mdash; the drill where taking your time is correct."),
        ]),
    }


PAGES = [
    {
        "slug": "gridshot",
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
        "title": "Valorant Aim Trainer - Free Browser Drill, Small Targets",
        "description": (
            "Free Valorant aim trainer in your browser. Small 44px targets on a short 1100ms "
            "lifespan, tuned for tap-firing at head level. No download, no sign-up, nothing "
            "uploaded."
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
        "size_note": (
            "The smallest targets and the second-shortest window on this site, because that is "
            "the shape of the aiming problem this game sets."
        ),
        "why": (
            "  <p>Valorant is a tap-firing game played at head level. Most engagements are "
            "decided by a single accurate shot rather than a burst, movement accuracy is "
            "heavily penalised so you are usually stopped when you fire, and the thing you are "
            "aiming at is a head-sized target you are trying to be pre-aimed at rather than "
            "swing onto.</p>\n"
            "  <p>So the tuning is small targets and a short window: 44px, shrinking to 30px, "
            "held for 1100ms. Small, because the accuracy demand is the defining feature. "
            "Short, because the moment when a peek is winnable does not last, and a drill that "
            "lets you take two seconds over every shot trains the wrong tempo for it. The "
            "combination is deliberately unforgiving &mdash; expect your accuracy here to sit "
            "below what you get on the default drill.</p>"
        ),
        "faq": [
            ("Will this actually improve my Valorant aim?",
             "It will warm your hand up and it will train the motor habit of settling before "
             "you fire, which does transfer. It will not train crosshair placement, peeker's "
             "advantage, movement accuracy or recoil control, which are where most of the "
             "actual aiming skill in that game lives. Use it as a ninety-second warm-up, not "
             "as a substitute for playing."),
            ("Are these the real hitbox sizes?",
             "No, and they could not be &mdash; a hitbox is a 3D volume on an animating model "
             "at a variable distance, and this is a flat circle on a web page. The 44px/30px/"
             "1100ms tuning is chosen to make the aiming problem <em>feel</em> like the game's, "
             "which is the most a browser drill can honestly claim."),
            ("Should I match my in-game sensitivity?",
             "Yes, and it matters more than anything else on this page. Warming up at a "
             "different sensitivity from the one you are about to play at is worse than not "
             "warming up, because you spend the first rounds recalibrating away from what you "
             "just practised."),
        ],
    },
    {
        "slug": "csgo-aim-trainer", "engine": None, "preset": "csgo",
        "game": "CS:GO",
        "title": "CS:GO Aim Trainer - Free Browser Drill, Counter-Strike Tuning",
        "description": (
            "Free CS:GO aim trainer in your browser. Medium 52px targets on a longer 1500ms "
            "lifespan, tuned for deliberate tap and burst discipline. No download, nothing "
            "uploaded."
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
        "size_note": (
            "The most forgiving window on this site, because Counter-Strike rewards the shot "
            "you set up over the shot you rush."
        ),
        "why": (
            "  <p>Counter-Strike is the most deliberate of the three games here. Engagements "
            "are frequently decided by who was already holding the angle rather than who "
            "reacted fastest, the economy makes a wasted round expensive enough that "
            "discipline beats aggression, and the core mechanical skill is stopping, firing a "
            "controlled tap or burst, and stopping again.</p>\n"
            "  <p>So the tuning is medium targets and the longest window: 52px, shrinking to "
            "38px, held for 1500ms. The extra time is the point &mdash; it makes rushing "
            "strictly worse than settling, which is the habit the game rewards. If your "
            "accuracy here is not noticeably better than on the "
            "<a href=\"/valorant-aim-trainer/\">Valorant tuning</a>, you are firing on arrival "
            "rather than on settling, and the extra 400ms is telling you so.</p>"
        ),
        "faq": [
            ("Why are the targets bigger than the Valorant page?",
             "Because the aiming problem is differently shaped, not because the game is "
             "easier. Counter-Strike engagements more often involve a body at a held angle "
             "than a head-sized target you must be pre-aimed at, and the tuning reflects the "
             "tempo rather than a claim about difficulty."),
            ("Does this help with spray control?",
             "No. Spray control is recoil-pattern memorisation combined with counter-movement, "
             "and neither exists in a browser page with no weapon and no recoil model. This "
             "drill trains the first shot, which is the part of the fight that recoil has not "
             "affected yet."),
            ("Is this good for CS2 as well?",
             "Yes &mdash; nothing here is version-specific. The tuning targets the tempo of "
             "Counter-Strike aiming generally, which the sequel did not change."),
        ],
    },
    {
        "slug": "fortnite-aim-trainer", "engine": None, "preset": "fortnite",
        "game": "Fortnite",
        "title": "Fortnite Aim Trainer - Free Browser Drill, Fast Target Swaps",
        "description": (
            "Free Fortnite aim trainer in your browser. Larger 68px targets on the shortest "
            "900ms lifespan, tuned for fast target acquisition between builds. No download, "
            "nothing uploaded."
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
        "size_note": (
            "The largest targets and the shortest window on this site &mdash; the opposite "
            "trade from the Valorant tuning, and deliberately so."
        ),
        "why": (
            "  <p>Fortnite asks a different question from the other two. The opponent is "
            "rarely still and rarely exposed for long: they are building, edit-peeking, "
            "falling, or crossing a gap between structures, and the window in which they are "
            "shootable at all is often shorter than the window in which they are hard to "
            "hit precisely. Acquisition speed dominates fine precision.</p>\n"
            "  <p>So the tuning inverts the Valorant page: larger targets, 68px shrinking to "
            "44px, on the shortest lifespan here at 900ms. It is a drill about getting there "
            "in time rather than getting there exactly, and your average time-to-click is the "
            "number to watch on it &mdash; accuracy should be comfortable, and if it is not, "
            "the targets are outrunning you rather than outsizing you.</p>"
        ),
        "faq": [
            ("Why are the targets larger but the time shorter?",
             "Because that is the trade the game makes. Opponents are exposed briefly and "
             "often at close range, so the difficulty is arriving inside the window rather "
             "than landing inside a small area. The Valorant tuning makes the opposite trade, "
             "and running both is a quick way to see which half of your aim is weaker."),
            ("Does this help with building or editing?",
             "Not at all &mdash; those are keybind and muscle-memory skills with no aiming "
             "component, and no browser drill touches them. This trains the shooting half of "
             "a fight only."),
            ("Should I use timed or count mode here?",
             "Timed, and preferably 30 or 60 seconds. This tuning is about sustaining fast "
             "acquisition, and a fixed target count lets you pause between targets in a way "
             "the game never will."),
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
    p["body"] = preset_body(p["game"], p["size_note"], cfg, p["why"], p["faq"])

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
      <div class="marquee-logo"><span class="mq-1">Flick</span><span class="mq-2">%(mq2)s</span></div>
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
  <div class="footer-inner">
    <div>&copy; <span id="year"></span> flicktrainer.com</div>
    <div class="footer-links">
      <a href="/privacy.html">Privacy</a>
      <a href="/terms.html">Terms</a>
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
