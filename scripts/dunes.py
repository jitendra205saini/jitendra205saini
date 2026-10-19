"""Contribution Dunes — renders a GitHub contribution calendar as a desert night.

Stars in the sky are the daily grid, dune heights are weekly totals,
and a camel walks the ridge. Monochrome, no dependencies.

Usage: GITHUB_TOKEN=... python scripts/dunes.py <username> <out.svg>
       python scripts/dunes.py --demo <out.svg>
"""
import json
import math
import os
import random
import sys
import urllib.request

W, H = 900, 260
PAD_X = 30
SKY_TOP, SKY_ROWS_GAP = 22, 11
DUNE_BASE, DUNE_MAX = 232, 70

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
    weeks = []
    for w in range(53):
        base = max(0, math.sin(w / 6) * 4 + rnd.random() * 5)
        weeks.append([(int(max(0, base + rnd.gauss(0, 2))) if rnd.random() > .3 else 0,
                       f"2026-{1 + w * 12 // 53:02d}-01", d) for d in range(7)])
    return sum(c for w in weeks for c, _, _ in w), weeks


def smooth(pts):
    """Catmull-Rom through points -> cubic Bezier path segments."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d


def ridge(heights, scale, lift, step):
    n = len(heights)
    xs = [PAD_X + i * (W - 2 * PAD_X) / (n - 1) for i in range(n)]
    # light moving average so dunes roll instead of spiking
    sm = [sum(heights[max(0, i - step):i + step + 1]) / len(heights[max(0, i - step):i + step + 1])
          for i in range(n)]
    top = max(sm) or 1
    return [(x, DUNE_BASE - lift - (h / top) ** .6 * DUNE_MAX * scale) for x, h in zip(xs, sm)]


CAMEL = ("M-14,0 L-13,-8 L-15,-13 L-12,-12 L-10,-9 L-6,-10 L-4,-16 L0,-17 L3,-12 "
         "L6,-16 L9,-16 L11,-11 L13,-15 L13,-20 L16,-22 L19,-21 L17,-18 L16,-12 "
         "L13,-7 L12,0 L10,0 L10,-6 L5,-7 L4,0 L2,0 L2,-7 L-6,-7 L-7,0 L-9,0 "
         "L-9,-7 L-11,-6 L-12,0 Z")

LEVELS = ["#1A1A1A", "#444444", "#7A7A7A", "#B5B5B5", "#F8F8F8"]


def render(total, weeks):
    counts = [c for w in weeks for c, _, _ in w if c]
    q = sorted(counts) or [1]
    cuts = [q[int(len(q) * f)] for f in (.25, .5, .75)] if counts else [1, 2, 3]

    def level(c):
        return 0 if c == 0 else 1 + sum(c > t for t in cuts)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%">',
           "<style>.m{font-family:'JetBrains Mono','Fira Code',Consolas,monospace}"
           "@keyframes tw{0%,100%{opacity:1}50%{opacity:.25}}.tw{animation:tw 3s ease-in-out infinite}"
           "</style>",
           f'<rect width="{W}" height="{H}" rx="6" fill="#0B0B0B"/>',
           f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="6" fill="none" stroke="#2A2A2A"/>']

    # sky: the contribution grid as a starfield
    n = len(weeks)
    gx = (W - 2 * PAD_X) / (n - 1)
    rnd = random.Random(total)
    for wi, week in enumerate(weeks):
        for c, date, wd in week:
            lv = level(c)
            x = PAD_X + wi * gx + rnd.uniform(-2, 2)
            y = SKY_TOP + wd * SKY_ROWS_GAP + rnd.uniform(-2, 2)
            r = (.7, 1, 1.3, 1.7, 2.1)[lv]
            cls = ' class="tw"' if lv == 4 else ""
            delay = f' style="animation-delay:{rnd.uniform(0, 3):.1f}s"' if lv == 4 else ""
            out.append(f'<circle{cls}{delay} cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{LEVELS[lv]}">'
                       f'<title>{c} on {date}</title></circle>')

    # moon with the yearly total
    out.append(f'<circle cx="{W - 70}" cy="122" r="22" fill="#F8F8F8"/>'
               f'<circle cx="{W - 61}" cy="116" r="20" fill="#0B0B0B"/>')
    out.append(f'<text x="{W - 104}" y="118" class="m" font-size="18" font-weight="700" '
               f'fill="#F8F8F8" text-anchor="end">{total:,}</text>'
               f'<text x="{W - 104}" y="133" class="m" font-size="9" fill="#777" '
               f'text-anchor="end" letter-spacing="1">CONTRIBUTIONS / YEAR</text>')

    # dunes: weekly totals, a far layer and a near layer
    weekly = [sum(c for c, _, _ in w) for w in weeks]
    far = ridge(weekly[::-1], .55, 12, 4)
    far = [(W - x + 0, y) for x, y in far][::-1]
    near = ridge(weekly, 1, 0, 2)
    for pts, fill, stroke in ((far, "#111111", "#333333"), (near, "#161616", "#F8F8F8")):
        d = smooth(pts)
        out.append(f'<path d="{d} L{W - PAD_X},{H} L{PAD_X},{H} Z" fill="{fill}"/>')
        out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="1.4"/>')
    out.append(f'<rect x="0" y="{DUNE_BASE}" width="{W}" height="{H - DUNE_BASE}" fill="#161616"/>')
    out.append(f'<line x1="{PAD_X}" y1="{DUNE_BASE}" x2="{W - PAD_X}" y2="{DUNE_BASE}" stroke="#2A2A2A"/>')

    # camel walking the near ridge
    path = smooth([(x, y - 1) for x, y in near])
    out.append(f'<path id="ridge" d="{path}" fill="none"/>')
    out.append(f'<g><path d="{CAMEL}" fill="#F8F8F8"/>'
               f'<animateMotion dur="40s" repeatCount="indefinite" rotate="auto">'
               f'<mpath href="#ridge"/></animateMotion></g>')

    # month labels
    seen = set()
    for wi, week in enumerate(weeks):
        m = week[0][1][5:7]
        if m not in seen and wi < n - 2:
            seen.add(m)
            name = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()[int(m) - 1]
            out.append(f'<text x="{PAD_X + wi * gx:.0f}" y="{H - 10}" class="m" font-size="9" '
                       f'fill="#555" letter-spacing="1">{name}</text>')

    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    user, dest = sys.argv[1], sys.argv[2]
    data = demo() if user == "--demo" else fetch(user, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(render(*data))
    print(f"wrote {dest}")
