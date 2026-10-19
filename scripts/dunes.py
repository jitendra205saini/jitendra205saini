"""Contribution Dunes — renders a GitHub contribution calendar as a desert night.

Stars in the sky are the daily grid, the front dunes rise with weekly totals,
and a camel caravan walks the ridge. Monochrome, no dependencies.

Usage: GITHUB_TOKEN=... python scripts/dunes.py <username> <out.svg>
       python scripts/dunes.py --demo <out.svg>
"""
import datetime
import json
import math
import os
import random
import sys
import urllib.request

W, H = 900, 300
GRID_X0, GRID_X1 = 40, 860
SKY_TOP, SKY_GAP = 84, 10
GROUND = 288

QUERY = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date weekday}}}}}}"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "User-Agent": "dunes"},
    )
    with urllib.request.urlopen(req) as r:
        cal = json.load(r)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["contributionCount"], d["date"], d["weekday"]) for d in w["contributionDays"]]
             for w in cal["weeks"]]
    return cal["totalContributions"], weeks


def demo():
    rnd = random.Random(7)
    start = datetime.date(2025, 10, 19)
    weeks = []
    for w in range(53):
        active = w > 30 or 12 < w < 18
        weeks.append([(rnd.randint(1, 9) if active and rnd.random() > .35 else 0,
                       str(start + datetime.timedelta(w * 7 + d)), d) for d in range(7)])
    return sum(c for w in weeks for c, _, _ in w), weeks


def smooth(pts):
    """Catmull-Rom through points -> cubic Bezier path."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def dune_line(base, waves, data=None, amp=0):
    """Ridge points across the full width: rolling sine dunes, optionally lifted by data."""
    pts = []
    for i in range(46):
        x = -10 + i * (W + 20) / 45
        y = base - sum(a * (1 + math.sin(x / l + p)) / 2 for a, l, p in waves)
        if data:
            t = min(max((x - GRID_X0) / (GRID_X1 - GRID_X0), 0), 1) * (len(data) - 1)
            j = int(t)
            v = data[j] + (data[min(j + 1, len(data) - 1)] - data[j]) * (t - j)
            y -= v * amp
        pts.append((x, y))
    return pts


def leg(x, phase):
    """A two-segment leg hanging from the belly, swinging while it walks."""
    return (f'<g transform="translate({x},-14)"><path d="M0,0 L-0.6,7 L0,14" stroke="#F8F8F8" '
            f'stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" fill="none"/>'
            f'<animateTransform attributeName="transform" type="rotate" additive="sum" '
            f'values="{-14 * phase};{14 * phase};{-14 * phase}" dur="0.9s" repeatCount="indefinite"/></g>')


# single-hump dromedary facing right, feet at y=0
CAMEL = (
    leg(-9, 1) + leg(7, -1)  # far legs first so the body overlaps them
    + '<path d="M-14,-17 Q-17,-12 -15,-8" stroke="#F8F8F8" stroke-width="1.4" '
      'fill="none" stroke-linecap="round"/>'
    + '<path d="M-14,-15 Q-15,-21 -9,-22 Q-2,-37 3,-33 Q8,-29 10,-22 '
      'Q13,-22 14,-26 Q15,-33 18,-36 Q21,-38 24,-36 L25,-34 Q22,-34 20,-31 '
      'Q18,-24 16,-18 Q14,-13 9,-12 L-10,-12 Q-14,-12 -14,-15 Z" fill="#F8F8F8"/>'
    + '<circle cx="21.5" cy="-35.5" r="0.6" fill="#0B0B0B"/>'
    + leg(-6, -1) + leg(10, 1)
)

LEVELS = ["#1C1C1C", "#4A4A4A", "#808080", "#BBBBBB", "#F8F8F8"]


def stats(weeks):
    days = [(c, d) for w in weeks for c, d, _ in w]
    best = max(days, key=lambda t: t[0])
    run = longest = 0
    for c, _ in days:
        run = run + 1 if c else 0
        longest = max(longest, run)
    return best, longest


def render(total, weeks):
    counts = sorted(c for w in weeks for c, _, _ in w if c)
    cuts = [counts[int(len(counts) * f)] for f in (.25, .5, .75)] if counts else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 + sum(c > t for t in cuts)

    rnd = random.Random(total)
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">',
         '<defs>'
         '<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#050505"/><stop offset="1" stop-color="#141414"/></linearGradient>'
         '<linearGradient id="d1" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#171717"/><stop offset="1" stop-color="#0E0E0E"/></linearGradient>'
         '<linearGradient id="d2" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#1F1F1F"/><stop offset="1" stop-color="#101010"/></linearGradient>'
         '<linearGradient id="d3" x1="0" y1="0" x2="0" y2="1">'
         '<stop offset="0" stop-color="#2A2A2A"/><stop offset=".5" stop-color="#151515"/>'
         '<stop offset="1" stop-color="#0B0B0B"/></linearGradient>'
         '<radialGradient id="glow"><stop offset="0" stop-color="#F8F8F8" stop-opacity=".18"/>'
         '<stop offset="1" stop-color="#F8F8F8" stop-opacity="0"/></radialGradient>'
         '<linearGradient id="trail" x1="0" x2="1"><stop offset="0" stop-color="#F8F8F8" stop-opacity="0"/>'
         '<stop offset="1" stop-color="#F8F8F8"/></linearGradient>'
         f'<clipPath id="frame"><rect width="{W}" height="{H}" rx="8"/></clipPath>'
         '</defs>',
         "<style>.m{font-family:'JetBrains Mono','Fira Code',Consolas,monospace}"
         "@keyframes tw{0%,100%{opacity:1}50%{opacity:.2}}.tw{animation:tw 3.2s ease-in-out infinite}"
         "@keyframes shoot{0%,88%{transform:translate(0,0);opacity:0}90%{opacity:1}"
         "100%{transform:translate(-260px,110px);opacity:0}}.sh{animation:shoot 9s linear infinite}"
         "</style>",
         '<g clip-path="url(#frame)">',
         f'<rect width="{W}" height="{H}" fill="url(#sky)"/>']

    # background dust stars, purely decorative
    for _ in range(90):
        o.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(4, 190):.0f}" '
                 f'r="{rnd.choice((.4, .5, .6))}" fill="#3A3A3A"/>')

    # the contribution grid as a starfield
    n = len(weeks)
    gx = (GRID_X1 - GRID_X0) / (n - 1)
    for wi, week in enumerate(weeks):
        for c, date, wd in week:
            lv = level(c)
            x = GRID_X0 + wi * gx + rnd.uniform(-1.5, 1.5)
            y = SKY_TOP + wd * SKY_GAP + rnd.uniform(-1.5, 1.5)
            r = (.6, 1, 1.3, 1.7, 2.2)[lv]
            tw = f' class="tw" style="animation-delay:{rnd.uniform(0, 3.2):.1f}s"' if lv >= 3 else ""
            o.append(f'<circle{tw} cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{LEVELS[lv]}">'
                     f'<title>{c} contributions on {date}</title></circle>')

    # shooting star
    o.append('<g class="sh"><line x1="760" y1="20" x2="700" y2="45" stroke="url(#trail)" '
             'stroke-width="1.2" stroke-linecap="round"/></g>')

    # moon with craters and a soft halo
    mx, my = 800, 40
    o.append(f'<circle cx="{mx}" cy="{my}" r="60" fill="url(#glow)"/>'
             f'<circle cx="{mx}" cy="{my}" r="20" fill="#EDEDED"/>'
             f'<circle cx="{mx - 6}" cy="{my - 5}" r="4" fill="#D2D2D2"/>'
             f'<circle cx="{mx + 7}" cy="{my + 4}" r="5" fill="#D9D9D9"/>'
             f'<circle cx="{mx - 3}" cy="{my + 10}" r="2.5" fill="#D2D2D2"/>')

    # stats, top-left
    best, longest = stats(weeks)
    o.append(f'<text x="40" y="34" class="m" font-size="22" font-weight="700" fill="#F8F8F8">{total:,}</text>'
             f'<text x="40" y="49" class="m" font-size="9" fill="#777" letter-spacing="1.5">CONTRIBUTIONS IN THE LAST YEAR</text>'
             f'<text x="290" y="34" class="m" font-size="14" font-weight="700" fill="#CCCCCC">{best[0]}</text>'
             f'<text x="290" y="49" class="m" font-size="9" fill="#777" letter-spacing="1.5">BEST DAY</text>'
             f'<text x="400" y="34" class="m" font-size="14" font-weight="700" fill="#CCCCCC">{longest}d</text>'
             f'<text x="400" y="49" class="m" font-size="9" fill="#777" letter-spacing="1.5">LONGEST STREAK</text>')

    # dunes: two decorative layers behind, the data-driven ridge in front
    weekly = [sum(c for c, _, _ in w) for w in weeks]
    sm = [sum(weekly[max(0, i - 2):i + 3]) / len(weekly[max(0, i - 2):i + 3]) for i in range(n)]
    top = max(sm) or 1
    norm = [(v / top) ** .6 for v in sm]

    layers = [
        (dune_line(200, [(34, 70, 0), (14, 31, 2)]), "url(#d1)", "#262626"),
        (dune_line(232, [(26, 55, 1.3), (12, 23, 4)]), "url(#d2)", "#3A3A3A"),
        (dune_line(266, [(10, 40, .5), (5, 17, 3)], norm, 62), "url(#d3)", "#F8F8F8"),
    ]
    for pts, fill, stroke in layers:
        d = smooth(pts)
        o.append(f'<path d="{d} L{W + 10},{H} L-10,{H} Z" fill="{fill}"/>')
        o.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.3"/>')

    # wind ripples on the front sand
    for _ in range(14):
        x, y = rnd.uniform(20, W - 60), rnd.uniform(276, 292)
        o.append(f'<path d="M{x:.0f},{y:.0f} q12,-3 24,0" stroke="#262626" fill="none"/>')

    # camel caravan walking the front ridge, staying upright
    near = layers[2][0]
    o.append(f'<path id="ridge" d="{smooth([(x, y + 1) for x, y in near])}" fill="none"/>')
    for scale, lag, shade in ((1.25, 0, "1"), (1.1, 2.2, ".85"), (.75, 4, ".7")):
        o.append(f'<g opacity="{shade}"><g transform="scale({scale})">{CAMEL}</g>'
                 f'<animateMotion dur="60s" begin="-{10 - lag}s" repeatCount="indefinite">'
                 f'<mpath href="#ridge"/></animateMotion></g>')

    # month labels, sitting in the sand
    seen, last_x = set(), -99
    for wi, week in enumerate(weeks):
        m = week[0][1][5:7]
        if m not in seen and 0 < wi < n - 2:
            seen.add(m)
            if GRID_X0 + wi * gx - last_x < 40:
                continue
            last_x = GRID_X0 + wi * gx
            name = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()[int(m) - 1]
            o.append(f'<text x="{GRID_X0 + wi * gx:.0f}" y="{SKY_TOP - 8}" class="m" font-size="8" '
                     f'fill="#555" letter-spacing="1">{name}</text>')

    o.append(f'</g><rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="8" fill="none" stroke="#2A2A2A"/>')
    o.append("</svg>")
    return "\n".join(o)


if __name__ == "__main__":
    user, dest = sys.argv[1], sys.argv[2]
    data = demo() if user == "--demo" else fetch(user, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(render(*data))
    print(f"wrote {dest}")
