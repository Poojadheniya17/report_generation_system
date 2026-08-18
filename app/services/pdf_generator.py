"""
PDF generation service, Manager Edition
Implements all Tripp Driskell changes from PDF comments + revised layout doc.

Key changes from previous version:
- Manager Edition: third person "the employee" throughout
- Cover: Manager Edition subtitle, updated description
- BFI bars: full 1-5 track visible, dot = score, orange line = norm
- Gauge: full blue arc to +3, needle shows score position
- TRIAD profile: stacked vertically like BFI bars (consistent visual language)
- Domain headers: score + level only, no norm/diff in header
- Section labels: "Natural Work Style" + "Manager Considerations"
- Facet headers: name + level only, no score
- TRIAD interpretation: matches domain page design language
  Flow: title + score → overall interpretation → Likely Contribution → Manager Considerations
- Page 12: Manager Action Guide with 4 AI sections
- Role Cluster Proximity: Option F (ranked table + mini TRIAD)
- Font size increase for print readability
- Reduced white space, content flows continuously
"""
from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

# ── palette ──────────────────────────────────────────────────────────────────
BLUE       = "#1C3F6E"
BLUE_MID   = "#2E6DB4"
BLUE_LIGHT = "#EAF0FB"
ORANGE     = "#0F766E"
NORM_COLOR = "#E07B3F"
GREEN      = "#2D7A2D"
LEVEL_AVG  = "#B45309"
LEVEL_LOW  = "#B91C1C"
WHITE      = "#FFFFFF"
BG_CARD    = "#F4F7FC"
TEXT_DARK  = "#1A2535"
TEXT_MID   = "#4A5568"
TEXT_LIGHT = "#8A9BB8"
RULE       = "#D8E3F0"

# Role cluster coordinates from Tripp's Excel TRIAD_Clusters sheet
ROLE_CLUSTERS = [
    ("Team Leader",     2.58,  0.04,  2.35),
    ("Task Motivator",  0.64, -0.04,  1.96),
    ("Power Seeker",   -0.43, -2.43,  2.13),
    ("Critic",         -0.92, -1.31, -0.30),
    ("Attention Seeker",-2.46,  0.00,  0.50),
    ("Negative",       -2.75, -2.22, -2.22),
    ("Social",         -0.03,  2.84, -0.45),
    ("Coordinator",     1.69,  2.15,  0.56),
    ("Follower",        0.56,  1.24, -2.39),
    ("Teamwork Support",2.24,  0.11, -2.15),
    ("Evaluator",       2.30, -2.23, -0.10),
    ("Problem Solver",  1.28,  0.02, -0.25),
    ("Task Completer",  2.64, -0.08, -0.56),
]


def _esc(t: str) -> str:
    return (str(t).replace("&","&amp;").replace("<","&lt;")
            .replace(">","&gt;").replace('"',"&quot;"))

def _level_cls(level: str) -> str:
    return level.lower().replace(" ","_")

def _diff_str(d: float) -> str:
    return f"+{d:.2f}" if d >= 0 else f"{d:.2f}"

# --- TRIAD dominant-dimension helpers -------------------------------------
# Shared by the "Location on the TRIAD Role Map" paragraph and the TRIAD
# Employee Snapshot bridge paragraph. Both previously hardcoded sociability
# as the always-dominant theme; these helpers pick the actually-dominant
# dimension (largest absolute score) per employee instead.

_TRIAD_DISPLAY_NAME = {"task": "Task orientation", "sociability": "Sociability", "dominance": "Dominance"}
_TRIAD_CANONICAL_ORDER = ["sociability", "dominance", "task"]

def _triad_dims(t: dict) -> dict:
    return {"task": t["task"], "sociability": t["sociability"], "dominance": t["dominance"]}

def _triad_dominant_key(t: dict) -> str:
    dims = _triad_dims(t)
    return max(dims, key=lambda k: abs(dims[k]["score"]))

def _triad_magnitude_phrase(key: str, dim: dict) -> str:
    """e.g. 'strong task orientation' or 'a mild pull away from sociability'."""
    name = _TRIAD_DISPLAY_NAME[key].lower()
    lbl = dim["direction_label"]
    if lbl == "Balanced":
        return f"a balanced {name}"
    strength, _, direction = lbl.partition(" tendency ")
    strength = strength.lower()
    if direction == "toward":
        return f"{strength} {name}"
    return f"a {strength} pull away from {name}"

def _domains_at_level(report: dict, names: list[str], level: str = "high") -> list[str]:
    """Which of `names` (personality domains) actually scored at `level` for
    this employee — used so we only claim a TRIAD theme is 'reinforced by'
    a personality domain when that domain's own score actually supports it."""
    hits = []
    for name in names:
        for d in report.get("domains", []):
            if d.get("name","").lower() == name.lower() and (d.get("level") or "").lower() == level:
                hits.append(name)
                break
    return hits

def _trait_at_level(report: dict, name: str, level: str) -> bool:
    """Check whether a personality domain OR facet named `name` scored at
    `level` for this employee. Checking facets (not just domains) matters:
    TRIAD Dominance correlates most precisely with the Assertiveness facet,
    not the parent Extraversion domain, and an employee can have Low
    Extraversion overall while still having High Assertiveness within it."""
    lvl = level.lower()
    for d in report.get("domains", []):
        if d.get("name","").lower() == name.lower() and (d.get("level") or "").lower() == lvl:
            return True
        for f in d.get("facets", []):
            if f.get("name","").lower() == name.lower() and (f.get("level") or "").lower() == lvl:
                return True
    return False

def _fit_label(similarity: float) -> str:
    if similarity >= 0.90: return "Very High"
    if similarity >= 0.80: return "High"
    if similarity >= 0.65: return "Moderate"
    if similarity >= 0.50: return "Low"
    return "Very Low"

def _fit_color(label: str) -> str:
    return {"Very High": GREEN, "High": GREEN,
            "Moderate": "#E07B3F", "Low": "#C0392B", "Very Low": "#C0392B"}.get(label, TEXT_MID)

def _font_css() -> str:
    return """
@font-face {
  font-family: 'RF';
  font-weight: 400;
  src: local('Arial'), local('Liberation Sans'), local('Helvetica');
}
@font-face {
  font-family: 'RF';
  font-weight: 700;
  src: local('Arial Bold'), local('Arial-BoldMT'), local('Liberation Sans Bold');
}"""


# ── SVG charts ────────────────────────────────────────────────────────────────

def _bfi_bar_svg(score: float, norm: float, w: int = 420, h: int = 32) -> str:
    """
    BFI bar, full 1-5 track always visible.
    Dot (open circle) = employee score.
    Orange vertical line = norm.
    Tripp: "show the entire range from 1-5... have the bar go all the way from 1-5.
    Keep the norm and have the dot represent the person's score."
    """
    lo, hi = 1.0, 5.0
    def px(v): return max(4, min(w - 4, int((v - lo) / (hi - lo) * w)))
    sx = px(score)  # score dot position
    nx = px(norm)   # norm line position
    r  = 6          # dot radius
    mid_y = h // 2

    # norm label above the line
    nlx = max(20, min(w - 20, nx))

    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <rect x="0" y="{mid_y-4}" width="{w}" height="8" rx="4" fill="#DCE8F5"/>
  <text x="{nlx}" y="9" text-anchor="middle" font-size="7" fill="{NORM_COLOR}"
        font-family="RF,Arial" font-weight="bold">norm</text>
  <line x1="{nx}" y1="11" x2="{nx}" y2="{h-1}" stroke="{NORM_COLOR}" stroke-width="2"/>
  <circle cx="{sx}" cy="{mid_y}" r="{r}" fill="{WHITE}" stroke="{BLUE}" stroke-width="2.5"/>
</svg>"""


def _gauge_svg(score: float, w: int = 200, h: int = 140) -> str:
    """
    Gauge: full blue arc from -3 to +3 (entire range).
    Needle points to the score position.
    Tripp: "blue arch run all the way down to +3, then the needle and the number
    show where the person's score is."
    """
    cx  = w // 2
    cy  = h - 30
    R   = cx - 18
    lo, hi = -3.0, 3.0

    def s2a(s): return math.pi * (1.0 - (s - lo) / (hi - lo))
    def pt(r, a): return cx + r * math.cos(a), cy - r * math.sin(a)

    a_L = s2a(-3)
    a_R = s2a(3)
    a_S = s2a(score)

    lx, ly = pt(R, a_L)
    rx, ry = pt(R, a_R)
    sx, sy = pt(R, a_S)

    # Full arc from -3 to +3 (the blue background track)
    full_arc = f'<path d="M {lx:.1f} {ly:.1f} A {R} {R} 0 1 1 {rx:.1f} {ry:.1f}" fill="none" stroke="{BLUE}" stroke-width="14" stroke-linecap="round"/>'

    # Needle
    nr = R - 10
    nx2, ny2 = pt(nr, a_S)
    score_str = f"{score:+.2f}"

    # Labels: -3 left, 0 top, +3 right
    l3x, l3y = pt(R + 14, a_L)
    p3x, p3y = pt(R + 14, a_R)

    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  {full_arc}
  <line x1="{cx}" y1="{cy}" x2="{nx2:.1f}" y2="{ny2:.1f}"
        stroke="{TEXT_DARK}" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="5" fill="{TEXT_DARK}"/>
  <text x="{l3x:.1f}" y="{l3y+4:.1f}" text-anchor="end" font-size="9.5"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{cx}" y="{cy - R - 10}" text-anchor="middle" font-size="9.5"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{p3x:.1f}" y="{p3y+4:.1f}" text-anchor="start" font-size="9.5"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="15" font-weight="bold"
        fill="{BLUE}" font-family="RF,Arial">{score_str}</text>
</svg>"""


def _triad_bar_svg(score: float, w: int = 460, h: int = 32) -> str:
    """
    TRIAD horizontal bar, matches BFI bar style for consistency.
    Tripp: "stack these on top of each other then present them in a similar
    fashion to the personality score chart above for consistency."
    Full -3 to +3 track. Dot = score.
    """
    lo, hi = -3.0, 3.0
    def px(v): return max(4, min(w - 4, int((v - lo) / (hi - lo) * w)))
    sx = px(score)
    cx = px(0)  # centre (0)
    mid_y = h // 2
    r = 6

    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <rect x="0" y="{mid_y-4}" width="{w}" height="8" rx="4" fill="#DCE8F5"/>
  <line x1="{cx}" y1="{mid_y-8}" x2="{cx}" y2="{mid_y+8}"
        stroke="{TEXT_LIGHT}" stroke-width="1" stroke-dasharray="3,2"/>
  <circle cx="{sx}" cy="{mid_y}" r="{r}" fill="{WHITE}" stroke="{BLUE}" stroke-width="2.5"/>
  <text x="2" y="{h}" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{cx}" y="{h}" text-anchor="middle" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{w-2}" y="{h}" text-anchor="end" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
</svg>"""


def _radar_svg(domains: list[dict], size: int = 260) -> str:
    n = 5
    pad_x = 118  # extra horizontal space for "Open-Mindedness" label - must scale with size/r_max
    pad_y = 40
    total_w = size + 2 * pad_x
    total_h = size + 2 * pad_y
    cx, cy = total_w / 2, total_h / 2
    r_max = size * 0.44
    lo, hi = 1.0, 5.0

    def pt(i, v):
        ang = math.radians(90 + 360 / n * i)
        r = r_max * (v - lo) / (hi - lo)
        return cx - r * math.cos(ang), cy - r * math.sin(ang)

    def label_pt(i):
        ang = math.radians(90 + 360 / n * i)
        r = r_max + 32
        return cx - r * math.cos(ang), cy - r * math.sin(ang)

    grid = ""
    for ring in [1,2,3,4,5]:
        pts = " ".join(f"{pt(i,float(ring))[0]:.1f},{pt(i,float(ring))[1]:.1f}" for i in range(n))
        grid += f'<polygon points="{pts}" fill="none" stroke="{RULE}" stroke-width="0.8"/>\n'
    spokes = "".join(
        f'<line x1="{pt(i,lo)[0]:.1f}" y1="{pt(i,lo)[1]:.1f}" x2="{pt(i,hi)[0]:.1f}" y2="{pt(i,hi)[1]:.1f}" stroke="{RULE}" stroke-width="0.8"/>\n'
        for i in range(n)
    )
    scores = [d["score"] for d in domains]
    norms  = [d["norm"]  for d in domains]
    score_pts = " ".join(f"{pt(i,v)[0]:.1f},{pt(i,v)[1]:.1f}" for i,v in enumerate(scores))
    norm_pts  = " ".join(f"{pt(i,v)[0]:.1f},{pt(i,v)[1]:.1f}" for i,v in enumerate(norms))

    short = ["Extraversion","Agreeableness","Conscientiousness","Neg. Emotionality","Open-Mindedness"]
    anchors = ["middle","start","start","end","end"]
    labels = ""
    for i,(nm,anchor) in enumerate(zip(short,anchors)):
        lx, ly = label_pt(i)
        sc_lbl = f"{domains[i]['score']:.2f} · {domains[i]['level']}"
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="10" fill="{BLUE}" font-family="RF,Arial" font-weight="bold">{nm}</text>\n'
        labels += f'<text x="{lx:.1f}" y="{ly+10:.1f}" text-anchor="{anchor}" font-size="9" fill="{TEXT_MID}" font-family="RF,Arial">{sc_lbl}</text>\n'

    legend_y = total_h - 8
    return f"""<svg width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg">
{grid}{spokes}
<polygon points="{score_pts}" fill="{BLUE}" fill-opacity="0.15" stroke="{BLUE}" stroke-width="2"/>
<polygon points="{norm_pts}" fill="none" stroke="{NORM_COLOR}" stroke-width="1.5" stroke-dasharray="5,3"/>
{labels}
<circle cx="{pad_x+4}" cy="{legend_y}" r="5" fill="{BLUE}" fill-opacity="0.5"/>
<text x="{pad_x+14}" y="{legend_y+4}" font-size="9.5" fill="{TEXT_DARK}" font-family="RF,Arial">Employee score</text>
<circle cx="{pad_x+90}" cy="{legend_y}" r="5" fill="none" stroke="{NORM_COLOR}" stroke-width="1.5"/>
<text x="{pad_x+100}" y="{legend_y+4}" font-size="9.5" fill="{TEXT_DARK}" font-family="RF,Arial">Workplace norm</text>
</svg>"""


def _role_proximity_svg(task: float, soc: float, dom: float, w: int = 560, h: int = 390) -> str:
    """
    Proper ternary TRIAD Role Navigator matching Tripp's approved visual.
    Triangle: Task Orientation (top, green), Sociability (bottom-left, blue),
    Dominance (bottom-right, orange).
    13 fixed role cluster coloured dots + employee star.
    Clean, minimal — SHL/Hogan style.
    """
    import math as _m

    ROLE_COLORS = [
        "#2563EB","#16A34A","#DC2626","#6B7280","#9333EA",
        "#374151","#0891B2","#059669","#3B82F6","#10B981",
        "#F59E0B","#8B5CF6","#EF4444",
    ]

    def norm(v): return (v + 3) / 6.0

    # Triangle vertices — extra padding for axis labels
    pad_t, pad_b, pad_l, pad_r = 56, 48, 56, 56
    vt = (w / 2,       pad_t)           # top   — Task Orientation
    vl = (pad_l,       h - pad_b - 16)  # left  — Sociability
    vr = (w - pad_r,   h - pad_b - 16)  # right — Dominance

    def to_xy(t_sc, s_sc, d_sc):
        t = norm(t_sc); s = norm(s_sc); d = norm(d_sc)
        tot = t + s + d or 1
        t, s, d = t/tot, s/tot, d/tot
        return (t*vt[0] + s*vl[0] + d*vr[0],
                t*vt[1] + s*vl[1] + d*vr[1])

    # Light grid lines (3 levels per axis)
    grid = ""
    N = 20
    for step in [0.25, 0.50, 0.75]:
        for axis in range(3):
            pts = []
            for i in range(N + 1):
                a = i / N
                if axis == 0:   b, c = step - a, 1 - step
                elif axis == 1: b, c = a, step
                else:           b, c = step, a
                b = step - a if axis == 0 else (a if axis == 1 else step)
                c = 1 - a - b
                if 0 <= a <= 1 and 0 <= b <= 1 and 0 <= c <= 1:
                    if axis == 0:   coords = (a*6-3, b*6-3, c*6-3)
                    elif axis == 1: coords = (c*6-3, a*6-3, b*6-3)
                    else:           coords = (b*6-3, c*6-3, a*6-3)
                    x, y = to_xy(*coords)
                    if (pad_l-5 < x < w-pad_r+5 and pad_t-5 < y < h-pad_b+5):
                        pts.append(f"{x:.1f},{y:.1f}")
            if len(pts) > 1:
                grid += f'<polyline points="{" ".join(pts)}" fill="none" stroke="#E8EDF5" stroke-width="0.7"/>\n'

    # Triangle — tri-color gradient wash (green/blue/orange) + gradient edges,
    # matching the shading style in Tripp's reference mockup
    G = "#16A34A"
    TRI_BLUE = "#2563EB"
    TRI_ORANGE = "#F97316"
    diag = _m.hypot(w, h)
    tri_defs = f'''<defs>
    <radialGradient id="triGradTask" cx="{vt[0]:.1f}" cy="{vt[1]:.1f}" r="{diag*0.85:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{G}" stop-opacity="0.40"/>
      <stop offset="100%" stop-color="{G}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="triGradSoc" cx="{vl[0]:.1f}" cy="{vl[1]:.1f}" r="{diag*0.85:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{TRI_BLUE}" stop-opacity="0.40"/>
      <stop offset="100%" stop-color="{TRI_BLUE}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="triGradDom" cx="{vr[0]:.1f}" cy="{vr[1]:.1f}" r="{diag*0.85:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{TRI_ORANGE}" stop-opacity="0.40"/>
      <stop offset="100%" stop-color="{TRI_ORANGE}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="triEdgeTS" x1="{vt[0]:.1f}" y1="{vt[1]:.1f}" x2="{vl[0]:.1f}" y2="{vl[1]:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{G}"/>
      <stop offset="100%" stop-color="{TRI_BLUE}"/>
    </linearGradient>
    <linearGradient id="triEdgeSD" x1="{vl[0]:.1f}" y1="{vl[1]:.1f}" x2="{vr[0]:.1f}" y2="{vr[1]:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{TRI_BLUE}"/>
      <stop offset="100%" stop-color="{TRI_ORANGE}"/>
    </linearGradient>
    <linearGradient id="triEdgeDT" x1="{vr[0]:.1f}" y1="{vr[1]:.1f}" x2="{vt[0]:.1f}" y2="{vt[1]:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{TRI_ORANGE}"/>
      <stop offset="100%" stop-color="{G}"/>
    </linearGradient>
    <clipPath id="triClip">
      <polygon points="{vt[0]:.1f},{vt[1]:.1f} {vl[0]:.1f},{vl[1]:.1f} {vr[0]:.1f},{vr[1]:.1f}"/>
    </clipPath>
  </defs>\n'''

    tri = (
        f'<polygon points="{vt[0]:.1f},{vt[1]:.1f} {vl[0]:.1f},{vl[1]:.1f} {vr[0]:.1f},{vr[1]:.1f}" fill="#FEFEFE"/>\n' +
        f'<g clip-path="url(#triClip)">\n' +
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="url(#triGradTask)"/>\n' +
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="url(#triGradSoc)"/>\n' +
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="url(#triGradDom)"/>\n' +
        f'</g>\n' +
        f'<line x1="{vt[0]:.1f}" y1="{vt[1]:.1f}" x2="{vl[0]:.1f}" y2="{vl[1]:.1f}" stroke="url(#triEdgeTS)" stroke-width="2"/>\n' +
        f'<line x1="{vl[0]:.1f}" y1="{vl[1]:.1f}" x2="{vr[0]:.1f}" y2="{vr[1]:.1f}" stroke="url(#triEdgeSD)" stroke-width="2"/>\n' +
        f'<line x1="{vr[0]:.1f}" y1="{vr[1]:.1f}" x2="{vt[0]:.1f}" y2="{vt[1]:.1f}" stroke="url(#triEdgeDT)" stroke-width="2"/>\n'
    )

    # Axis labels
    axlbls = (
        f'<text x="{vt[0]}" y="{vt[1]-22}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="{G}" font-family="RF,Arial">Task Orientation</text>\n' +
        f'<text x="{vt[0]}" y="{vt[1]-11}" text-anchor="middle" font-size="9" fill="{G}" font-family="RF,Arial">(Structure)</text>\n' +
        f'<text x="{vl[0]}" y="{vl[1]+18}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="{BLUE}" font-family="RF,Arial">Sociability</text>\n' +
        f'<text x="{vl[0]}" y="{vl[1]+29}" text-anchor="middle" font-size="9" fill="{BLUE}" font-family="RF,Arial">(Connect)</text>\n' +
        f'<text x="{vr[0]}" y="{vr[1]+18}" text-anchor="middle" font-size="10.5" font-weight="bold" fill="{TRI_ORANGE}" font-family="RF,Arial">Dominance</text>\n' +
        f'<text x="{vr[0]}" y="{vr[1]+29}" text-anchor="middle" font-size="9" fill="{TRI_ORANGE}" font-family="RF,Arial">(Influence)</text>\n'
    )

    # Role cluster dots — manual label offsets to avoid overlaps
    # (dx, dy, anchor): nudge relative to dot centre
    LABEL_OFFSETS = [
        ( 0, -12, "middle"),   # Team Leader
        (  12, -10, "start"),  # Task Motivator
        (  12,   4, "start"),  # Power Seeker
        ( -12, -10, "end"),    # Critic
        (  16,  16, "start"),  # Attention Seeker
        ( -16, -12, "end"),    # Negative
        ( -12,  -9, "end"),    # Social
        ( -14,  -9, "end"),    # Coordinator
        ( -12,  -9, "end"),    # Follower
        ( -14,  -9, "end"),    # Teamwork Support
        (  12,  -9, "start"),  # Evaluator
        (   0, -12, "middle"), # Problem Solver
        (  12,  -9, "start"),  # Task Completer
    ]
    dots = ""
    # Compute all dot positions first, then apply a small cosmetic separation
    # nudge to any pair close enough to visually merge (e.g. Task Motivator /
    # Critic sit ~5pt apart in Tripp's source cluster data with a 6pt dot
    # radius each). This only nudges the drawn marker position for legibility;
    # it does not alter the underlying scores or the similarity table.
    raw_xy = [to_xy(tc, sc2, dc) for (_, tc, sc2, dc) in ROLE_CLUSTERS]
    xy = list(raw_xy)
    MIN_SEP = 15.0
    for _ in range(4):  # a few relaxation passes is enough for this dataset
        for a in range(len(xy)):
            for b in range(a + 1, len(xy)):
                ax, ay = xy[a]; bx, by = xy[b]
                ddx, ddy = bx - ax, by - ay
                dist = math.hypot(ddx, ddy) or 0.01
                if dist < MIN_SEP:
                    push = (MIN_SEP - dist) / 2
                    ux, uy = ddx / dist, ddy / dist
                    xy[a] = (ax - ux * push, ay - uy * push)
                    xy[b] = (bx + ux * push, by + uy * push)

    for i, (rname, tc, sc2, dc) in enumerate(ROLE_CLUSTERS):
        rx, ry = xy[i]
        color = ROLE_COLORS[i % len(ROLE_COLORS)]
        dx, dy, anchor = LABEL_OFFSETS[i] if i < len(LABEL_OFFSETS) else (0, -12, "middle")
        lx = rx + dx
        ly = ry + dy
        dots += (
            f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="6" fill="{color}" opacity="0.88" stroke="{WHITE}" stroke-width="1"/>\n' +
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="8.5" fill="#1A2535" font-family="RF,Arial">{rname}</text>\n'
        )

    # Employee star
    ex, ey = to_xy(task, soc, dom)
    def star_pts(cx, cy, ro=11, ri=4.5, n=5):
        pts = []
        for k in range(n*2):
            r = ro if k%2==0 else ri
            a = _m.radians(k*180/n - 90)
            pts.append(f"{cx+r*_m.cos(a):.1f},{cy+r*_m.sin(a):.1f}")
        return " ".join(pts)

    star = (f'<polygon points="{star_pts(ex, ey)}" ' +
            f'fill="{BLUE}" stroke="{WHITE}" stroke-width="2"/>\n')

    # Legend
    ly_leg = h - 14
    lx_leg = pad_l
    legend = (
        f'<polygon points="{star_pts(lx_leg+8, ly_leg, 6, 2.5)}" fill="{BLUE}" stroke="{WHITE}" stroke-width="1"/>\n' +
        f'<text x="{lx_leg+18}" y="{ly_leg+4}" font-size="9.5" fill="#374151" font-family="RF,Arial">Your Position</text>\n' +
        f'<circle cx="{lx_leg+100}" cy="{ly_leg}" r="5" fill="#2563EB" opacity="0.88" stroke="{WHITE}" stroke-width="1"/>\n' +
        f'<text x="{lx_leg+110}" y="{ly_leg+4}" font-size="9.5" fill="#374151" font-family="RF,Arial">Role Cluster</text>\n'
    )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="white"/>
  {tri_defs}{tri}{grid}{axlbls}{dots}{star}{legend}
</svg>'''



def _compute_role_distances(task: float, soc: float, dom: float) -> list[tuple[str,float,str]]:
    """Compute Euclidean distance from employee to each role cluster, return sorted list."""
    results = []
    for role, tc, sc2, dc in ROLE_CLUSTERS:
        dist = math.sqrt((task-tc)**2 + (soc-sc2)**2 + (dom-dc)**2)
        # Convert distance to similarity percentage (max possible distance ~10.4)
        max_d = math.sqrt((6.0**2)*3)
        similarity = max(0.0, 1.0 - dist / max_d)
        results.append((role, similarity, _fit_label(similarity)))
    results.sort(key=lambda x: -x[1])
    return results


# ── CSS ───────────────────────────────────────────────────────────────────────
def _css(font_css: str) -> str:
    return f"""
{font_css}
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'RF', Arial, sans-serif; color: {TEXT_DARK}; font-size: 11pt;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

.page {{ width: 210mm; height: 297mm; position: relative; page-break-after: always;
         overflow: hidden; background: {WHITE}; }}

/* ── COVER ── */
.cover {{ background: {BLUE}; display: flex; flex-direction: column;
          height: 297mm; justify-content: space-between; }}
.cover-body {{ padding: 56px 60px 36px; flex: 1; display: flex; flex-direction: column;
               justify-content: flex-start; }}
.cover-tag {{ font-size: 13pt; font-weight: 700; letter-spacing: 3px;
              color: {WHITE}; text-transform: uppercase; margin-bottom: 18px; }}
.cover-title {{ font-size: 40pt; font-weight: 700; color: #4CC9F0; line-height: 1.1; margin-bottom: 20px; }}
.cover-desc {{ font-size: 10pt; color: rgba(255,255,255,0.65); line-height: 1.65; max-width: 400px; }}
.cover-meta {{ display: flex; gap: 44px; padding: 24px 60px;
               border-top: 1px solid rgba(255,255,255,0.15); }}
.cover-meta-item .label {{ font-size: 7pt; letter-spacing: 2px; color: rgba(255,255,255,0.45);
                           text-transform: uppercase; margin-bottom: 5px; }}
.cover-meta-item .value {{ font-size: 12pt; font-weight: 700; color: {WHITE}; }}
.cover-footer {{ padding: 12px 60px; border-top: 1px solid rgba(255,255,255,0.1);
                 font-size: 7.5pt; color: rgba(255,255,255,0.3);
                 display: flex; justify-content: space-between; }}

/* ── CONTENT ── */
.content {{ padding: 40px 56px 58px; }}
.eyebrow {{ font-size: 19pt; font-weight: 700; letter-spacing: 2px; color: {BLUE};
            text-transform: uppercase; border-bottom: 1.5px solid {BLUE};
            padding-bottom: 9px; margin-bottom: 22px; }}
h2 {{ font-size: 12pt; font-weight: 700; color: {BLUE}; margin: 20px 0 8px; }}
.sub-h {{ font-size: 11pt; font-weight: 700; color: {TEXT_DARK}; margin: 6px 0 10px; }}
h2:first-of-type {{ margin-top: 0; }}
p {{ line-height: 1.7; margin-bottom: 10px; font-size: 10.5pt; }}
.lead {{ font-size: 10.5pt; line-height: 1.72; margin-bottom: 18px; }}
.subtitle {{ font-size: 10pt; color: {TEXT_MID}; margin-bottom: 18px; }}

.footer {{ position: absolute; bottom: 18px; left: 56px; right: 56px;
           display: flex; justify-content: space-between;
           font-size: 7.5pt; color: {TEXT_LIGHT};
           border-top: 1px solid {RULE}; padding-top: 8px; }}

/* ── TRIAD DIMENSION LIST (welcome page) ── */
.triad-dim-list {{
  margin: 8px 0 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}}
.triad-dim-item {{
  display: flex;
  gap: 10px;
  align-items: baseline;
  padding: 7px 12px;
  background: {BG_CARD};
  border-radius: 6px;
  border-left: 3px solid {BLUE};
}}
.triad-dim-label {{
  font-size: 9.5pt;
  font-weight: 700;
  color: {BLUE};
  min-width: 120px;
  flex-shrink: 0;
}}
.triad-dim-desc {{
  font-size: 9.5pt;
  color: {TEXT_DARK};
  line-height: 1.5;
}}

/* ── CALLOUT ── */
.callout {{ background: {BG_CARD}; border-radius: 0 8px 8px 0; border-left: 3px solid {BLUE}; padding: 14px 18px; margin-top: 16px; margin-bottom: 20px; }}
.callout-spacious {{ background: {BG_CARD}; border-radius: 0 8px 8px 0; border-left: 3px solid {BLUE}; padding: 22px 28px; margin-top: 24px; margin-bottom: 20px; }}
.callout-spacious p {{ font-size: 10.5pt; line-height: 1.7; margin: 0; }}
.callout-label {{ font-size: 9pt; font-weight: 700; color: {BLUE}; margin-bottom: 3px; }}
.callout-sub {{ font-size: 8pt; color: {TEXT_LIGHT}; margin-bottom: 8px; }}
.callout p {{ font-size: 9.5pt; margin: 0 0 8px; }}
.callout p:last-child {{ margin-bottom: 0; }}

/* ── GLANCE BARS ── */
.glance-card {{ background: {BG_CARD}; border-radius: 10px; padding: 34px 34px; margin-bottom: 38px; }}
.glance-card-title {{ font-size: 11pt; font-weight: 700; letter-spacing: 1.5px;
                      text-transform: uppercase; color: {BLUE};
                      text-align: center; margin-bottom: 16px; }}
.fig-caption {{ font-size: 8.5pt; color: {TEXT_MID}; font-style: italic; text-align: center;
                margin: -8px 0 16px; }}
.fig-captions-label {{ font-size: 9pt; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
                       color: {TEXT_MID}; margin-bottom: 14px; }}
.report-transition {{ margin-top: 20px; padding-top: 16px; border-top: 1px solid {RULE}; }}
.report-transition-note {{ font-size: 8pt; color: {TEXT_LIGHT}; font-style: italic;
                           margin-bottom: 10px; }}
.bar-row {{ display: flex; align-items: center; gap: 18px; margin-bottom: 16px; }}
.bar-name {{ font-size: 10pt; font-weight: 700; color: {TEXT_DARK}; width: 150px; flex-shrink: 0; }}
.bar-track {{ flex: 0 0 340px; }}
.bar-right {{ width: 68px; text-align: right; flex-shrink: 0; }}
.bar-score {{ font-size: 11pt; font-weight: 700; color: {BLUE}; line-height: 1; }}
.bar-level {{ font-size: 8pt; font-weight: 700; }}
.bar-level-high   {{ color: {GREEN}; }}
.bar-level-average {{ color: {LEVEL_AVG}; }}
.bar-level-low    {{ color: {LEVEL_LOW}; }}
.scale-row {{ display: flex; justify-content: space-between; padding: 4px 0 0;
              font-size: 8pt; color: {TEXT_MID}; margin-left: 168px; width: 340px; }}
.domain-scale-row {{ display: flex; justify-content: space-between; padding: 4px 0 0;
                     font-size: 8pt; color: {TEXT_MID}; width: 500px; }}
.radar-center {{ display: flex; justify-content: center; }}

/* ── GAUGE ── */
.gauge-row {{ display: flex; justify-content: space-around; align-items: flex-end;
              padding: 18px 0 8px; }}
.gauge-item {{ text-align: center; }}
.gauge-dim-name {{ font-size: 12pt; font-weight: 700; color: {BLUE}; margin-top: 10px; }}

/* ── TRIAD PROFILE, stacked bars like BFI ── */
.triad-stack-row {{ display: flex; align-items: center; gap: 20px; margin-bottom: 32px;
                    padding-bottom: 30px; border-bottom: 1px solid {RULE}; }}
.triad-stack-row:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.triad-stack-left {{ width: 180px; flex-shrink: 0; }}
.triad-stack-name {{ font-size: 11.5pt; font-weight: 700; color: {BLUE}; }}
.triad-stack-score {{ font-size: 30pt; font-weight: 700; color: {BLUE}; line-height: 1.15; }}
.triad-stack-pill {{ display: inline-block; font-size: 8.5pt; font-weight: 700;
                     color: {WHITE}; background: {ORANGE}; padding: 4px 12px;
                     border-radius: 20px; margin-top: 6px; }}
.triad-stack-track {{ flex: 1; }}

/* ── DOMAIN PAGES ── */
.domain-header {{ margin-bottom: 12px; }}
.domain-title-row {{ display: flex; align-items: baseline; gap: 12px;
                     margin-bottom: 8px; flex-wrap: wrap; }}
.domain-name {{ font-size: 14pt; font-weight: 700; color: {BLUE}; }}
.level-badge {{ font-size: 8pt; font-weight: 700; padding: 2px 8px; border-radius: 4px; }}
.badge-high    {{ background: #DCF0DC; color: {GREEN}; }}
.badge-average {{ background: #FCEEDD; color: {LEVEL_AVG}; }}
.badge-low     {{ background: #FBE2E2; color: {LEVEL_LOW}; }}
.domain-bar {{ margin-bottom: 10px; }}
.section-intro {{ font-size: 10pt; line-height: 1.65; margin-bottom: 10px; }}

.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; }}
.two-col > div {{
  background: {BG_CARD};
  border-radius: 6px;
  padding: 10px 12px;
}}
.full-box {{
  background: {BG_CARD};
  border-radius: 6px;
  padding: 14px 18px;
  margin-bottom: 10px;
}}
.col-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.5px; color: {BLUE};
              text-transform: uppercase; margin-bottom: 5px; }}
.col-text {{ font-size: 9.5pt; line-height: 1.62; margin: 0; }}

.facet-rule {{ border-top: 1px solid {RULE}; padding-top: 8px; margin: 8px 0; }}
.facet-rule-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.5px;
                     text-transform: uppercase; color: {TEXT_LIGHT}; }}
.facet {{ margin-bottom: 9px; padding-bottom: 8px; border-bottom: 1px solid {RULE}; }}
.facet:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.facet-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }}
.facet-name {{ font-size: 9.5pt; font-weight: 700; color: {BLUE}; }}
.facet-bar {{ margin-bottom: 5px; }}
.facet-body {{ font-size: 9.5pt; line-height: 1.6; margin-bottom: 7px; }}
.facet-two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.facet-two-col > div {{
  background: {BG_CARD};
  border-radius: 5px;
  padding: 8px 10px;
}}

/* ── TRIAD INTERPRETATION, consistent with domain pages ── */
.triad-interp-block {{ margin-bottom: 14px; padding-bottom: 12px;
                       border-bottom: 1px solid {RULE}; }}
.triad-interp-block:last-child {{ border-bottom: none; margin-bottom: 0; }}
.triad-interp-header {{ display: flex; align-items: baseline; gap: 14px; margin-bottom: 6px; }}
.triad-interp-score {{ font-size: 22pt; font-weight: 700; color: {BLUE}; }}
.triad-interp-name {{ font-size: 13pt; font-weight: 700; color: {BLUE}; }}
.dir-pill {{ display: inline-block; font-size: 7.5pt; font-weight: 700;
             color: {WHITE}; background: {ORANGE}; padding: 3px 10px;
             border-radius: 20px; margin-left: 6px; }}
.triad-interp-bar {{ margin: 6px 0 10px; }}
.triad-three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
.triad-three-col > div {{
  background: {BG_CARD};
  border-radius: 6px;
  padding: 10px 12px;
}}
.triad-three-col p {{ font-size: 9.5pt; line-height: 1.62; margin: 0; }}

/* ── MANAGER ACTION GUIDE ── */
.mag-section {{ background: {BG_CARD}; border-radius: 10px; padding: 14px 22px;
                margin-bottom: 18px; }}
.mag-section-title {{
  font-size: 12pt;
  font-weight: 700;
  color: {BLUE};
  margin-bottom: 13px;
  padding-bottom: 10px;
  border-bottom: 1px solid {RULE};
}}
.mag-narrative {{ font-size: 9.5pt; line-height: 1.68; margin-bottom: 13px; }}
.mag-sub-label {{ font-size: 8pt; font-weight: 700; letter-spacing: 1px;
                  color: {BLUE}; text-transform: uppercase; margin-bottom: 7px; margin-top: 10px; }}
.mag-list {{ list-style: none; padding: 0; }}
.mag-list li {{ display: flex; gap: 8px; font-size: 9.5pt; line-height: 1.6;
                margin-bottom: 7px; align-items: flex-start; }}
.bullet {{ color: {ORANGE}; font-size: 11pt; line-height: 1.2; flex-shrink: 0; }}

/* ── ROLE PROXIMITY ── */
.ternary-map {{ display: flex; flex-direction: column; align-items: center; }}
.proximity-grid {{ display: flex; flex-direction: column; gap: 24px; margin-top: 16px; }}
.proximity-right {{ }}
.proximity-table-label {{ font-size: 11pt; font-weight: 700; letter-spacing: 1px;
                           text-transform: uppercase; color: {BLUE}; margin-bottom: 12px; }}
.proximity-table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; }}
.proximity-table th {{ font-size: 8.5pt; font-weight: 700; letter-spacing: 1px;
                       text-transform: uppercase; color: {TEXT_MID};
                       border-bottom: 1.5px solid {RULE}; padding: 10px 10px;
                       text-align: left; }}
.proximity-table td {{ padding: 16px 12px; border-bottom: 1px solid {RULE};
                       vertical-align: middle; font-size: 11pt; }}
.proximity-table tr:nth-child(1) td {{ background: rgba(28,63,110,0.04); }}
.proximity-table tr:last-child td {{ border-bottom: none; }}
.rank-1 {{ font-weight: 700; }}
.fit-bar {{ height: 8px; border-radius: 4px; background: {BLUE}; display: inline-block; }}

/* ── TABLE OF CONTENTS ── */
.toc-list {{ margin-top: 24px; }}
.toc-bar {{ display: flex; align-items: center; gap: 20px; padding: 26px 0 26px 26px;
            border-left: 5px solid {BLUE}; margin-bottom: 14px; }}
.toc-bar:nth-child(2) {{ border-left-color: {ORANGE}; }}
.toc-bar:nth-child(3) {{ border-left-color: {BLUE}; }}
.toc-bar:nth-child(4) {{ border-left-color: {ORANGE}; }}
.toc-bar-title {{ font-size: 15pt; font-weight: 700; color: {TEXT_DARK}; flex: 1; }}
.toc-bar-desc {{ font-size: 9.5pt; color: {TEXT_MID}; flex: 1.2; line-height: 1.6; }}
.toc-bar-page {{ font-size: 20pt; font-weight: 700; color: {TEXT_MID}; flex-shrink: 0; }}
"""


# ── footer ────────────────────────────────────────────────────────────────────
def _footer(employee: str, page_num: int) -> str:
    return f"""<div class="footer">
  <span>Work Style Report &nbsp;·&nbsp; {_esc(employee)}</span>
  <span>Florida Maxima Corporation</span>
  <span>{page_num}</span>
</div>"""


# ── page builders ─────────────────────────────────────────────────────────────

def _cover(p: dict, pg: int) -> str:
    employee = _esc(p.get("name",""))
    role     = _esc(p.get("role",""))
    manager  = _esc(p.get("manager",""))
    today    = date.today().strftime("%B %d, %Y").replace(" 0"," ")
    return f"""<div class="page cover">
  <div class="cover-body">
    <div class="cover-tag">Work Style Report</div>
    <div class="cover-title">Manager Edition</div>
    <div class="cover-desc">Evidence-based guidance for optimizing employee performance,
    team integration, and workplace effectiveness.</div>
  </div>
  <div class="cover-meta">
    <div class="cover-meta-item"><div class="label">Employee</div><div class="value">{employee}</div></div>
    <div class="cover-meta-item"><div class="label">Role / Job Title</div><div class="value">{role}</div></div>
    <div class="cover-meta-item"><div class="label">Date</div><div class="value">{today}</div></div>
  </div>
  <div class="cover-footer">
    <span>Florida Maxima Corporation &nbsp;|&nbsp; © 2026</span>
    <span>{pg}</span>
  </div>
</div>"""


def _toc(p: dict, pg: int, entries: list[tuple[str, int, str]]) -> str:
    """Combined 'What's in the report' intro + Table of Contents on one page,
    per Tripp: 'See the revised layout doc for layout... WHAT'S IN THE WORK
    STYLE REPORT? Box [...] [Table of Contents]' - these go together."""
    employee = p.get("name", "")
    rows = ""
    for i, (title, page_num, desc) in enumerate(entries, start=1):
        rows += f"""<div class="toc-bar">
      <div class="toc-bar-title">{_esc(title)}</div>
      <div class="toc-bar-desc">{_esc(desc)}</div>
      <div class="toc-bar-page">{page_num:02d}</div>
    </div>"""
    return f"""<div class="page content">
  <div class="eyebrow">What's in the Work Style Report?</div>
  <div class="callout"><p>This report is organized into four sections that help managers and team leaders understand employee work style, interpret assessment results, and apply practical leadership strategies.</p></div>
  <div class="toc-list" style="margin-top:22px">{rows}</div>
  {_footer(employee, pg)}
</div>"""


def _introduction_1(p: dict, pg: int) -> str:
    """Introduction to the Work Style Report, page 1 of 2. Content and
    structure per Tripp's revised layout doc, Section 1."""
    employee = p.get("name","the employee")
    return f"""<div class="page content">
  <div class="eyebrow">Introduction to the Work Style Report</div>
  <div class="callout"><p>This section introduces the Work Style Report and provides an overview of the Personality and TRIAD assessments. Together, these evidence-based methods offer a structured understanding of how employees are likely to approach work, contribute to teams, and perform in the workplace.</p></div>

  <p>This report provides practical leadership insights derived from two evidence-based frameworks. Together, they offer a structured view of how an employee is likely to approach work, interact with others, respond to workplace demands, and contribute to team performance.</p>
  <p>This report serves as a management tool that helps leaders better understand employee strengths, development opportunities, communication preferences, and potential performance drivers.</p>
  <p>These insights should be considered alongside other tools such as direct observation, feedback, experience, and ongoing conversations with {_esc(employee)} to foster optimal workplace performance.</p>

  <h2 style="margin-top:34px">Personality Assessment</h2>
  <p>Personality reflects a person's natural behavioral tendencies or typical patterns of behavior that are likely to emerge during everyday work interactions. The Five Factor Model of personality has been used with considerable success in workplace settings by measuring normal personality characteristics that influence how individuals approach work, relationships, leadership, and career success. This assessment measures five broad personality factors, described below.</p>
  <p><strong>Extraversion</strong> reflects the extent to which a person is outgoing and sociable versus reserved and introverted. Higher scores may indicate a greater desire to socialize with others, be more assertive in expressing themselves, and display higher energy and enthusiasm. Lower scores may indicate a greater preference for independent work, greater self-reliance, and reflection.</p>
  <p><strong>Agreeableness</strong> reflects the extent to which a person is compassionate towards others, respectful, and trusting. Higher scores may indicate a person who is concerned with others' well-being, trusting, and respectful of others. Lower scores may indicate a person who is more critical and analytic, more independent and objective, and more uncompromising.</p>
  <p><strong>Conscientiousness</strong> refers to a tendency towards structure and orderliness, industriousness, and reliability. Higher scores may indicate a person who is well-organized, persistent in pursuing goals, and responsible. Lower scores may indicate a person who is more spontaneous, but less dependable and responsible.</p>
  <p><strong>Negative Emotionality</strong> reflects emotional stability and susceptibility to negative emotions. Higher scores may indicate a person who can be more emotionally unstable or moody, temperamental, and anxious and irritable. Lower scores may indicate a person that is calm, secure, self-confident, and not anxious or nervous.</p>
  <p><strong>Open-Mindedness</strong> reflects imagination, curiosity, and appreciation for new ideas. Higher scores may indicate a person who is intellectually curious, creative, and inquisitive. Lower scores may indicate a person who is more practical, pragmatic, and prefers established convention.</p>

  {_footer(employee, pg)}
</div>"""


def _introduction_2(p: dict, pg: int) -> str:
    """Introduction to the Work Style Report, page 2 of 2."""
    employee = p.get("name","the employee")
    return f"""<div class="page content">

  <p>There are two points to consider in interpreting the personality assessment. First, there is no one "good" or "bad" personality profile; rather, each pattern offers strengths as well as potential developmental opportunities depending on the work and task setting and role requirements. Second, each of the broad Five Factors is also broken down into lower-level or more specific personality facets that provide more granular detail into the person's behavioral tendencies. These are provided in the following assessment report.</p>

  <h2 style="margin-top:34px">The TRIAD Model Role Profile</h2>
  <p>Employees not only "perform" in work groups, but they perform certain roles. For example, a person may perform the role of a Team Leader, and others may fill the roles of Problem Solver, Task Motivator, or Teamwork Support. Having these roles performed effectively enables overall task success.</p>
  <p>We have developed a tool called TRIAD (Tracking Roles In and Across Domains) to examine the fit between individual profiles and role performance, and to identify individuals who would best fill separate task leader, social, problem solver, and other roles.</p>
  <p>The TRIAD assessment measures three primary role dimensions:</p>
  <div class="triad-dim-list">
    <div class="triad-dim-item"><span class="triad-dim-label">Task Orientation</span><span class="triad-dim-desc">The degree to which an employee prefers structure, organization, planning, and focus on outcomes.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Sociability</span><span class="triad-dim-desc">How an employee connects, communicates, collaborates, and builds relationships with others.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Dominance</span><span class="triad-dim-desc">How an employee influences others, asserts ideas, takes initiative, and guides direction.</span></div>
  </div>
  <p style="margin-top:14px">Together, these dimensions create a Role Profile, a snapshot of how an employee is most naturally inclined to contribute within a team environment.</p>
  <p>Understanding an employee's TRIAD profile can help managers identify where the individual is likely to add value, what work environments may be most energizing, and where potential sources of friction or misalignment may emerge. This profile serves as a foundation for understanding team contribution, communication patterns, leadership tendencies, and responses to workplace demands.</p>
  <p>Moreover, by integrating the results from the Personality Assessment and the TRIAD Role Profile, we are able to get an overall picture of {_esc(employee)}'s work style and key strengths and weaknesses.</p>

  {_footer(employee, pg)}
</div>"""


def _personality_section_intro(p: dict, report: dict, pg: int) -> str:
    """Personality Assessment section start (box + How to Use framework)
    merged with the Employee Snapshot (Work Style Summary), per Tripp's
    revised layout doc. Combined onto one page - each was under 200pt of
    content on its own, leaving 140-160mm of blank space when split."""
    employee = p.get("name","the employee")
    raw_summary = report["executive_summary"]["text"]
    paras = [para.strip() for para in raw_summary.split("\n\n") if para.strip()]
    summary_html = "".join(f'<p class="lead">{_esc(para)}</p>' for para in paras)

    return f"""<div class="page content">
  <div class="eyebrow">Personality Assessment</div>
  <div class="callout"><p>This section presents the employee's Personality assessment results across the five major personality domains and their underlying facets. These evidence-based insights help managers better understand the employee's natural behavioral tendencies, workplace preferences, and potential performance drivers.</p></div>

  <h2 style="margin-top:22px">How to Use The Personality Assessment</h2>
  <p>The Personality Assessment translates well-established psychological characteristics into practical workplace insights. It examines patterns that influence communication, decision-making, work habits, motivation, and interpersonal interactions.</p>
  <p>These results help managers and team leaders better understand how {_esc(employee)} is likely to function in the workplace by identifying:</p>
  <div class="triad-dim-list">
    <div class="triad-dim-item"><span class="triad-dim-label">Likely Workplace Behaviors</span><span class="triad-dim-desc">How the employee naturally approaches work, communicates with others, makes decisions, and carries out responsibilities.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Management Considerations</span><span class="triad-dim-desc">The leadership approaches, feedback, structure, and work environment most likely to support the employee's performance, engagement, and long-term success.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Development Opportunities</span><span class="triad-dim-desc">Areas where targeted coaching, experiences, or skill development can help the employee build on strengths and address potential challenges.</span></div>
  </div>

  <div class="report-transition">
    <h3 class="sub-h">Employee Snapshot</h3>
    <div class="callout"><p>This snapshot provides a concise, high-level summary of the employee's overall work style. It highlights the employee's most prominent workplace characteristics before exploring the detailed assessment results that follow.</p></div>
    {summary_html}
  </div>

  {_footer(employee, pg)}
</div>"""


def _triad_section_intro(p: dict, report: dict, pg: int) -> str:
    """TRIAD Assessment section start (box + How to Use framework) merged
    with the TRIAD Employee Snapshot (Workplace Contribution Profile),
    per the revised layout doc. Combined onto one page for the same
    reason as the Personality section - each was too light on its own."""
    employee = p.get("name","the employee")

    # employee_snapshot.text is now genuinely AI-generated (see
    # interpretation_prompt.py "TRIAD SECTION: Employee Snapshot") — it used
    # to be a hardcoded template stitching together the dominant TRIAD score
    # and its personality correlate, which only ever stated that the two
    # frameworks "relate" rather than actually synthesizing what that means
    # for teamwork. Tripp flagged this directly; this replaces it with real
    # AI reasoning about team contribution, collaboration, and value, per
    # his original spec for this section.
    snapshot_text = _esc(report["triad"].get("employee_snapshot", {}).get("text", ""))

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Assessment</div>
  <div class="callout"><p>This section presents the employee's TRIAD assessment results across the three core dimensions of Task Orientation, Sociability, and Dominance. Together, these dimensions describe how the employee is most naturally inclined to contribute within a team.</p></div>

  <h2>How to Use The TRIAD Assessment</h2>
  <p>The TRIAD Assessment translates an employee's natural team role tendencies into practical workplace insights. It evaluates how the employee is most likely to contribute within a team by examining three core dimensions of behavior: Task Orientation, Sociability, and Dominance. Together, these dimensions provide a structured understanding of the employee's preferred role, interpersonal style, and approach to accomplishing work.</p>
  <p>These results help managers better understand how {_esc(employee)} is likely to contribute within a team by identifying:</p>
  <div class="triad-dim-list">
    <div class="triad-dim-item"><span class="triad-dim-label">Natural Team Contributions</span><span class="triad-dim-desc">The roles, responsibilities, and work activities the employee is most naturally inclined to perform and where they are likely to add the greatest value.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Management Considerations</span><span class="triad-dim-desc">The team environment, leadership approach, and opportunities that are most likely to support effective collaboration, engagement, and performance.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Development Opportunities</span><span class="triad-dim-desc">Practical strategies for expanding the employee's versatility, strengthening less-preferred team behaviors, and preparing for broader responsibilities.</span></div>
  </div>

  <div class="report-transition">
    <h3 class="sub-h">Employee Snapshot</h3>
    <div class="callout"><p>This snapshot provides a high-level overview of the employee's workplace contribution profile by integrating the Personality and TRIAD assessment results. It summarizes how the employee is likely to contribute within a team, collaborate with others, and add value in the workplace before exploring the detailed TRIAD interpretations that follow.</p></div>
    <p class="lead">{snapshot_text}</p>
  </div>

  {_footer(employee, pg)}
</div>"""


def _glance(p: dict, report: dict, pg: int) -> list[str]:
    employee = p.get("name","")
    domains  = report["domains"]

    rows = ""
    for d in domains:
        lc = _level_cls(d["level"])
        rows += f"""<div class="bar-row">
      <span class="bar-name">{_esc(d['name'])}</span>
      <div class="bar-track">{_bfi_bar_svg(d['score'], d['norm'], w=340, h=32)}</div>
      <div class="bar-right">
        <div class="bar-score">{d['score']:.2f}</div>
        <div class="bar-level bar-level-{lc}">{_esc(d['level'])}</div>
      </div>
    </div>"""

    page1 = f"""<div class="page content">
  <h2>Personality at a Glance</h2>
  <div class="callout-spacious" style="padding:14px 18px;margin-top:10px;margin-bottom:10px"><p>The following visualizations provide a high-level summary of the employee's assessment results before the detailed interpretations that follow.</p></div>
  <h3 class="sub-h" style="margin-top:10px;margin-bottom:4px">How to Interpret the Graphs</h3>
  <p class="subtitle" style="margin-bottom:6px">Each score is compared to a normative sample drawn from the general population. Scores above or below the norm indicate differences in natural behavioral tendencies, not a "more positive" or "more negative" result.</p>

  <div class="glance-card" style="margin-bottom:10px;padding:16px 20px">
    <div class="glance-card-title">Score vs Norm</div>
    <p class="fig-caption">Compares the employee's score on each personality domain to the average score (norm) of the general population.</p>
    {rows}
    <div class="scale-row"><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span></div>
  </div>

  <div class="glance-card" style="padding:12px 20px">
    <div class="glance-card-title">Profile Shape</div>
    <p class="fig-caption">Highlights the relative pattern across the five personality domains, making it easy to identify the employee's strongest and least prominent behavioral tendencies at a glance.</p>
    <div class="radar-center">{_radar_svg(domains, size=220)}</div>
  </div>
  {_footer(employee, pg)}
</div>"""
    return [page1]


def _domain(p: dict, domain: dict, pg: int, first: bool = False) -> str:
    employee = p.get("name","")
    dname    = _esc(domain["name"])
    score    = domain["score"]
    norm     = domain["norm"]
    level    = domain["level"]
    lc       = _level_cls(level)

    intro_note = ""
    if first:
        intro_note = '<p class="report-transition-note">Personality Assessment Report: each domain with its three facets. The marker shows your level and the colored line marks the norm.</p>'

    facets_html = ""
    for f in domain["facets"]:
        flc = _level_cls(f["level"])
        facets_html += f"""<div class="facet">
      <div class="facet-header">
        <span class="facet-name">{_esc(f['name'])}</span>
        <span class="level-badge badge-{flc}">{_esc(f['level'])}</span>
      </div>
      <div class="facet-bar">{_bfi_bar_svg(f['score'], f['norm'], w=480, h=30)}</div>
      <p class="facet-body">{_esc(f['meaning'])}</p>
      <div class="facet-two-col">
        <div><div class="col-label">Natural Work Style</div><p class="col-text">{_esc(f['preferences'])}</p></div>
        <div><div class="col-label">Manager Considerations</div><p class="col-text">{_esc(f['potential_needs'])}</p></div>
      </div>
    </div>"""

    return f"""<div class="page content">
  {intro_note}
  <div class="domain-header">
    <div class="domain-title-row">
      <span class="domain-name">{dname}</span>
      <span class="level-badge badge-{lc}">{_esc(level)}</span>
    </div>
    <div class="domain-bar">{_bfi_bar_svg(score, norm, w=500, h=32)}</div>
    <div class="domain-scale-row"><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span></div>
  </div>
  <p class="section-intro">{_esc(domain['meaning'])}</p>
  <div class="two-col">
    <div><div class="col-label">Natural Work Style</div><p class="col-text">{_esc(domain['preferences'])}</p></div>
    <div><div class="col-label">Manager Considerations</div><p class="col-text">{_esc(domain['potential_needs'])}</p></div>
  </div>
  <div class="facet-rule"><span class="facet-rule-label">Facet Detail</span></div>
  {facets_html}
  {_footer(employee, pg)}
</div>"""


def _triad_profile(p: dict, report: dict, pg: int) -> list[str]:
    """
    TRIAD bars stacked vertically, same visual language as BFI bars.
    Tripp: "stack these on top of each other then present them in a similar
    fashion to the personality score chart above for consistency."
    """
    employee = p.get("name","")
    triad    = report["triad"]
    dims     = [("task","Task Orientation"),("sociability","Sociability"),("dominance","Dominance")]

    rows = ""
    for key, label in dims:
        d = triad[key]
        rows += f"""<div class="triad-stack-row">
      <div class="triad-stack-left">
        <div class="triad-stack-name">{_esc(label)}</div>
        <div class="triad-stack-score">{d['score']:+.2f}</div>
        <div class="triad-stack-pill">{_esc(d['direction_label'])}</div>
      </div>
      <div class="triad-stack-track">{_triad_bar_svg(d['score'], w=440, h=38)}</div>
    </div>"""

    # Gauge view
    gauges = ""
    for key, label in dims:
        d = triad[key]
        gauges += f'''<div class="gauge-item">
      {_gauge_svg(d['score'], w=195, h=165)}
      <div class="gauge-dim-name">{_esc(label)}</div>
    </div>'''

    page1 = f"""<div class="page content">
  <h2>TRIAD at a Glance</h2>
  <div class="callout-spacious" style="padding:14px 18px;margin-top:10px;margin-bottom:10px"><p>The following visualizations provide a high-level summary of the employee's assessment results before the interpretations that follow.</p></div>
  <h3 class="sub-h" style="margin-top:10px;margin-bottom:4px">How to Interpret the Graphs</h3>
  <p class="subtitle" style="margin-bottom:6px">The TRIAD profile summarizes {_esc(employee)}'s natural tendencies toward Task Orientation, Sociability, and Dominance, a snapshot of how they are most likely to contribute within a team.</p>

  <div class="glance-card" style="margin-bottom:10px;padding:14px 20px">
    <div class="glance-card-title">TRIAD Snapshot</div>
    <p class="fig-caption">Provides a quick visual comparison of the employee's standing across the three TRIAD dimensions.</p>
    <div class="gauge-row">{gauges}</div>
  </div>

  <div class="glance-card" style="padding:14px 20px">
    <div class="glance-card-title">TRIAD Scores</div>
    <p class="fig-caption">Displays the employee's precise score on each TRIAD dimension relative to the full assessment scale.</p>
    {rows}
  </div>

  {_footer(employee, pg)}
</div>"""
    return [page1]


def _triad_interpretation(p: dict, report: dict, pg: int) -> str:
    """
    TRIAD interpretation, consistent with domain page design.
    Flow per dimension: title + score → overall interpretation →
    Likely Contribution → Manager Considerations
    Tripp: "Each TRIAD dimension should follow a similar flow... use the same
    design principles to create a cohesive reading experience."
    """
    employee = p.get("name","")
    triad    = report["triad"]
    dims     = [("task","Task Orientation"),("sociability","Sociability"),("dominance","Dominance")]

    blocks = ""
    for key, label in dims:
        d = triad[key]
        contrib = _esc(d.get("likely_contribution", d.get("workplace_implications","")))
        mgr_con = _esc(d.get("manager_considerations", d.get("workplace_implications","")))
        blocks += f"""<div class="triad-interp-block">
      <div class="triad-interp-header">
        <span class="triad-interp-score">{d['score']:+.2f}</span>
        <span class="triad-interp-name">{_esc(label)}</span>
        <span class="dir-pill">{_esc(d['direction_label'])}</span>
      </div>
      <div class="triad-interp-bar">{_triad_bar_svg(d['score'], w=500, h=32)}</div>
      <p class="section-intro">{_esc(d['interpretation'])}</p>
      <div class="two-col">
        <div><div class="col-label">Likely Contribution</div><p class="col-text">{contrib}</p></div>
        <div><div class="col-label">Manager Considerations</div><p class="col-text">{mgr_con}</p></div>
      </div>
    </div>"""

    return f"""<div class="page content">
  {blocks}
  {_footer(employee, pg)}
</div>"""


def _role_cluster_proximity(p: dict, report: dict, pg: int) -> list[str]:
    """
    Role Cluster Proximity: business-interpretation write-up matching the
    mockup Tripp included in the revised layout doc, PLUS the TRIAD Role
    Map moved in here per his follow-up feedback: "we have the TRIAD role
    map image... following the two other triad graphs. It would seem to
    work best in the role cluster proximity sub-section... Role Cluster
    Proximity -> descriptive box like in the other areas of the report ->
    TRIAD role map image with a figure caption -> followed by 'Location
    on the TRIAD Role Map' etc." Descriptive box + figure caption wording
    supplied by Tripp directly.

    Business Interpretation / Strengths / Development Areas are AI-generated
    per employee (report["role_cluster_proximity"]) - see
    interpretation_prompt.py's ROLE CLUSTER PROXIMITY section for the
    generation rules. Business Applications was dropped per Tripp's request
    (redundant with Business Interpretation).

    Split across two pages - too much content for one without overflow.
    """
    employee = p.get("name","the employee")
    t = report["triad"]
    task = t["task"]["score"]
    soc  = t["sociability"]["score"]
    dom  = t["dominance"]["score"]

    distances = _compute_role_distances(task, soc, dom)
    top5 = distances[:5]
    top3 = distances[:3]
    top_role = top3[0][0]

    sig = {name: (tc, sc2, dc) for name, tc, sc2, dc in ROLE_CLUSTERS}

    # Fixed "archetype" flavor text per role - this part is legitimately
    # generic (describing what the role cluster itself means), not a claim
    # about this specific employee, so it's fine to keep fixed.
    role_archetype = {
        "Coordinator": "Balances people and process, links subteams and functions, and facilitates communication and coordination.",
        "Social": "Less task-structured and more relationship-driven, oriented around morale and connection rather than process.",
        "Problem Solver": "More independent and analytical, oriented toward resolving issues directly rather than through group coordination.",
        "Team Leader": "Directive and outcome-focused, leading more through authority and structure than through relationship-building.",
        "Task Motivator": "Energizes others toward outcomes, pushing pace and progress more than facilitating consensus.",
    }

    def _overlap_clause(cluster_sig: tuple[float, float, float], rank: int) -> str:
        """Build the 'Overlaps on X' opening clause from this employee's
        REAL per-dimension distance to this specific cluster, instead of a
        fixed claim that doesn't adapt per employee (bug: the previous
        version hardcoded e.g. 'Overlaps on dominance and task focus' for
        Task Motivator regardless of the employee - accurate for Jordan
        Avery, whose task score genuinely was close to Task Motivator's, but
        wrong for Alex Rivera, whose task score is actually the WORST-
        matching dimension of the three for that same cluster)."""
        tc, sc2, dc = cluster_sig
        gaps = sorted([
            ("task orientation", abs(task - tc)),
            ("sociability", abs(soc - sc2)),
            ("dominance", abs(dom - dc)),
        ], key=lambda g: g[1])
        closest_name, closest_gap = gaps[0]
        second_name, second_gap = gaps[1]

        overlap = f"{'Close' if closest_gap <= 0.3 else 'Partial'} overlap on {closest_name}"
        if second_gap <= 0.6:
            overlap += f" and {second_name}"
        overlap += "."
        return f"Primary match. {overlap}" if rank == 0 else overlap

    sig_rows = ""
    for rank, (name, sim, fit) in enumerate(top3):
        tc, sc2, dc = sig.get(name, (0, 0, 0))
        fit_text = f"{_overlap_clause((tc, sc2, dc), rank)} {role_archetype.get(name, '')}".strip()
        sig_rows += f"""<tr>
      <td style="font-weight:700;color:{BLUE}">{_esc(name)}</td>
      <td style="font-size:9pt">Task {tc:+.2f} &middot; Soc {sc2:+.2f} &middot; Dom {dc:+.2f}</td>
      <td style="font-size:9.5pt">{_esc(fit_text)}</td>
    </tr>"""

    def bar_w(sim): return max(4, int(sim * 80))
    match_rows = ""
    for i,(role,sim,fit) in enumerate(top5):
        rank = i + 1
        star = "&#9733; " if rank == 1 else f"{rank} "
        pct  = f"{sim*100:.0f}%"
        fcolor = _fit_color(fit)
        bw = bar_w(sim)
        cls = "rank-1" if rank == 1 else ""
        match_rows += f"""<tr>
      <td><span class="{cls}">{star}</span></td>
      <td class="{cls}">{_esc(role)}</td>
      <td>{pct}</td>
      <td><span class="fit-bar" style="width:{bw}px;background:{fcolor}"></span></td>
      <td style="color:{fcolor};font-weight:{'700' if rank==1 else '400'}">{_esc(fit)}</td>
    </tr>"""

    mini_svg = _role_proximity_svg(task, soc, dom)

    page1 = f"""<div class="page content">
  <h2>Role Cluster Proximity</h2>

  <div class="callout"><p>This section compares the employee's TRIAD profile with 13 TRIAD team role profiles to identify the roles that most closely align with their unique combination of Task Orientation, Sociability, and Dominance. These results highlight likely role strengths, potential development areas, and practical applications in the workplace.</p></div>

  <div class="ternary-map">
    <div class="glance-card-title" style="margin-bottom:6px">TRIAD Role Map</div>
    <p class="fig-caption">Shows the employee's location within the TRIAD role space relative to the 13 TRIAD team role profiles.</p>
    {mini_svg}
  </div>

  <div class="proximity-table-label" style="margin-top:16px">Closest Role Matches</div>
  <table class="proximity-table" style="margin-bottom:6px">
    <thead>
      <tr>
        <th style="width:44px">Rank</th>
        <th style="width:160px">Role</th>
        <th style="width:90px">Similarity</th>
        <th style="width:140px">Fit</th>
        <th style="width:100px">Fit Level</th>
      </tr>
    </thead>
    <tbody>{match_rows}</tbody>
  </table>
  <p style="font-size:9pt;color:{TEXT_LIGHT};font-style:italic">
    Based on {_esc(employee)}'s combined Task Orientation, Sociability, and Dominance scores.
  </p>

  {_footer(employee, pg)}
</div>"""

    rcp = report["role_cluster_proximity"]
    strengths_html = "".join(
        f'<li><span class="bullet">&rsaquo;</span><span><strong>{_esc(s["title"])}:</strong> {_esc(s["explanation"])}</span></li>'
        for s in rcp["strengths"]
    )
    dev_html = "".join(
        f'<li><span class="bullet">&rsaquo;</span><span><strong>{_esc(d["title"])}:</strong> {_esc(d["explanation"])}</span></li>'
        for d in rcp["development_areas"]
    )

    _dims = _triad_dims(t)
    _dominant_key = _triad_dominant_key(t)
    _region_label = {"sociability": "upper-social", "task": "upper-task", "dominance": "dominance-leaning"}[_dominant_key]
    _sorted_keys = sorted(_dims, key=lambda k: abs(_dims[k]["score"]), reverse=True)
    _phrases = [_triad_magnitude_phrase(k, _dims[k]) for k in _sorted_keys]
    _combo_desc = ", ".join(_phrases[:-1]) + f", and {_phrases[-1]}"

    page2 = f"""<div class="page content">

  <h3 class="sub-h" style="margin-top:0">Location on the TRIAD Role Map</h3>
  <p>This coordinate (Task Orientation {task:+.2f}, Sociability {soc:+.2f}, Dominance {dom:+.2f}) plots in the {_region_label} region of the TRIAD space, reflecting a combination of {_combo_desc}. That region aligns most closely with the {_esc(top_role)} cluster, with secondary proximity to the {_esc(top3[1][0])} and {_esc(top3[2][0])} profiles.</p>

  <table class="proximity-table" style="margin:14px 0 18px">
    <thead>
      <tr>
        <th style="width:130px">Role Cluster</th>
        <th style="width:170px">TRIAD Signature</th>
        <th>Fit Description</th>
      </tr>
    </thead>
    <tbody>{sig_rows}</tbody>
  </table>

  <h3 class="sub-h">Business Interpretation</h3>
  <p>{_esc(rcp["business_interpretation"])}</p>

  <div class="full-box" style="margin-top:16px">
    <div class="col-label">Strengths</div>
    <ul class="mag-list">
      {strengths_html}
    </ul>
  </div>

  {_footer(employee, pg + 1)}
</div>"""

    page3 = f"""<div class="page content">

  <div class="full-box">
    <div class="col-label">Potential Development Areas</div>
    <ul class="mag-list">
      {dev_html}
    </ul>
  </div>

  {_footer(employee, pg + 2)}
</div>"""
    return [page1, page2, page3]


def _manager_action_guide(p: dict, report: dict, pg: int) -> list[str]:
    """
    Manager Action Guide, two pages:
    Page 1: Communication Style + Motivators & Stressors
    Page 2: Delegation Guide + Leadership Summary & Action Plan
    Returns list of two page HTML strings.
    """
    employee = p.get("name","")
    mag = report.get("manager_action_guide", {})

    def section(title, narrative, bullets_dict, extra_style=""):
        html = f'<div class="mag-section" style="{extra_style}"><div class="mag-section-title">{_esc(title)}</div>'
        if narrative:
            html += f'<p class="mag-narrative">{_esc(narrative)}</p>'
        for sub_label, items in bullets_dict.items():
            if items:
                html += f'<div class="mag-sub-label">{_esc(sub_label)}</div>'
                html += '<ul class="mag-list">'
                for item in items:
                    html += f'<li><span class="bullet">›</span><span>{_esc(item)}</span></li>'
                html += '</ul>'
        html += '</div>'
        return html

    comm = mag.get("communication_style", {})
    mot  = mag.get("motivators_stressors", {})
    dele = mag.get("delegation_guide", {})
    lead = mag.get("leadership_summary", {})

    eyebrow = '<div class="eyebrow">Manager Action Guide</div>'
    subtitle = '<div class="callout"><p>This section translates the assessment insights into practical leadership strategies that help managers communicate more effectively, support employee development, and maximize workplace performance.</p></div>'

    page1 = f"""<div class="page content">
  {eyebrow}
  {subtitle}
  {section("Communication Style",
    comm.get("narrative",""),
    {"Manager Recommendations": comm.get("recommendations",[])},
    extra_style="margin-bottom:36px"
  )}
  {section("Motivators & Stressors",
    mot.get("narrative",""),
    {"Key Motivators": mot.get("motivators",[]),
     "Potential Stressors": mot.get("stressors",[])}
  )}
  {_footer(employee, pg)}
</div>"""

    page2 = f"""<div class="page content">
  {section("Delegation Guide",
    dele.get("narrative",""),
    {"Best Suited For": dele.get("best_suited_for",[]),
     "Management Recommendations": dele.get("recommendations",[])}
  )}
  {section("Management Summary & Action Plan",
    lead.get("narrative",""),
    {"Strengths to Leverage": lead.get("strengths",[]),
     "Potential Watch Points": lead.get("watch_points",[]),
     "Recommended Actions": lead.get("actions",[])}
  )}
  {_footer(employee, pg + 1)}
</div>"""

    return [page1, page2]


def _inject_anchor(page_html: str, anchor_id: str) -> str:
    """Insert an invisible anchor as the first child inside a page's opening
    <div>, so we can later ask WeasyPrint's own Document.pages[i].anchors
    which PHYSICAL page this content actually landed on after real layout.
    Used only for measuring accurate TOC page numbers (see generate_pdf)."""
    idx = page_html.find(">")
    return page_html[:idx + 1] + f'<a id="{anchor_id}"></a>' + page_html[idx + 1:]


def _scale_typography(css_text: str, scale: float) -> str:
    """Scale every font-size (pt) and line-height (unitless) declaration in
    the CSS by `scale`. Deliberately narrow regexes - only match right after
    the property name - so this never touches unrelated numbers: page
    dimensions (mm), colors, border-widths, padding, and positioning are all
    left exactly as Tripp approved. Only text density changes, and only when
    content actually needs it (see generate_pdf's retry loop)."""
    def scale_fontsize(m):
        return f"font-size: {float(m.group(1)) * scale:.2f}pt"

    def scale_lineheight(m):
        return f"line-height: {float(m.group(1)) * scale:.3f}"

    css_text = re.sub(r'font-size:\s*(\d+(?:\.\d+)?)pt', scale_fontsize, css_text)
    css_text = re.sub(r'line-height:\s*(\d+(?:\.\d+)?)(?!\w)', scale_lineheight, css_text)
    return css_text


def _find_overflowing_pages(pdf_bytes: bytes, min_clearance_pt: float = 15.0) -> list[int]:
    """Render-and-measure check: open the actual rendered PDF and find any
    page where content runs within `min_clearance_pt` of the footer zone
    (or overlaps it outright - clearance can go negative). This is the same
    technique used throughout manual QA of this report (comparing rendered
    page content bounds against the known footer y-position), now run
    automatically as part of every generation instead of only being caught
    by someone reviewing a PDF by hand. Returns 0-indexed page numbers.

    This exists because per-field word caps (interpretation_prompt.py) are
    a preventive measure, not a guarantee - live model output varies by a
    few words every run, and no fixed cap can be proven safe for content
    that hasn't been written yet. This is the actual safety net: it
    measures the real rendered geometry, so it catches overflow regardless
    of why it happened."""
    import fitz  # pymupdf
    FOOTER_Y = 820.0
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    overflowing = []
    for i, page in enumerate(doc):
        blocks = [b for b in page.get_text("blocks") if b[6] == 0]
        content = [b for b in blocks if b[1] < FOOTER_Y - 5]
        if not content:
            continue
        clearance = FOOTER_Y - max(b[3] for b in content)
        if clearance < min_clearance_pt:
            overflowing.append(i)
    doc.close()
    return overflowing


# ── entry point ───────────────────────────────────────────────────────────────
def generate_pdf(participant: dict[str, Any], report: dict[str, Any]) -> bytes:
    """
    participant: {"name": str, "role": str, "manager": str (optional)}
    report:      validated dict from interpretation.interpret()
    Returns PDF as bytes.

    Self-correcting on two axes, because AI-generated content length varies
    by a few words on every single run and no fixed word budget can be
    proven safe in advance for content that hasn't been written yet:

    1. TOC page numbers: renders once to measure, via WeasyPrint's own
       Document.pages[i].anchors, which PHYSICAL page each section actually
       landed on after real layout - not a hand-calculated formula, which
       goes stale the moment any page's content differs from what the
       formula assumed.

    2. Footer overlap: after that same measurement render, checks the
       ACTUAL rendered PDF geometry (_find_overflowing_pages) for any page
       running too close to or overlapping the footer. If found, shrinks
       typography very slightly (_scale_typography - font-size and
       line-height only, never padding/margins/positions) and re-renders,
       stepping down until every page clears the footer or a minimum
       readable scale is reached. A 2-6% type-scale difference is not
       visually noticeable; overlapping text is.

    Word-count caps in interpretation_prompt.py remain the first line of
    defense (cheaper - no extra render passes when content already fits),
    this is what guarantees correctness even when a cap gets missed.
    """
    from weasyprint import HTML, CSS as WpCSS

    font_css = _font_css()
    base_css = _css(font_css)
    page_css = WpCSS(string="@page { size: A4; margin: 0; }")

    def build_pages(toc_entries: list[tuple[str, int, str]]) -> list[str]:
        """Build the full ordered page list. toc_entries only affects the
        TOC page's own printed text — every other page's position in the
        sequence is identical regardless of what toc_entries contains, so
        this is safe to call once with placeholder data (Pass 1) and again
        with the real, measured data (Pass 2)."""
        pg = 1
        pages: list[str] = []
        pages.append(_cover(participant, pg));                          pg += 1
        pages.append(_toc(participant, pg, toc_entries));                pg += 1

        intro1 = _inject_anchor(_introduction_1(participant, pg), "section-intro")
        pages.append(intro1);                                            pg += 1
        pages.append(_introduction_2(participant, pg));                  pg += 1

        personality = _inject_anchor(
            _personality_section_intro(participant, report, pg), "section-personality")
        pages.append(personality);                                       pg += 1
        for gp in _glance(participant, report, pg):
            pages.append(gp); pg += 1
        for i, domain in enumerate(report["domains"]):
            pages.append(_domain(participant, domain, pg, first=(i == 0))); pg += 1

        triad_intro = _inject_anchor(
            _triad_section_intro(participant, report, pg), "section-triad")
        pages.append(triad_intro);                                       pg += 1
        for tp in _triad_profile(participant, report, pg):
            pages.append(tp); pg += 1
        pages.append(_triad_interpretation(participant, report, pg));    pg += 1
        for rp in _role_cluster_proximity(participant, report, pg):
            pages.append(rp); pg += 1

        mag_pages = _manager_action_guide(participant, report, pg)
        if mag_pages:
            mag_pages[0] = _inject_anchor(mag_pages[0], "section-mag")
        for mp in mag_pages:
            pages.append(mp); pg += 1

        return pages

    def render(pages: list[str], css: str):
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{"".join(pages)}</body></html>"""
        return HTML(string=html).render(stylesheets=[page_css])

    # --- Find a type scale where nothing overlaps the footer. Starts at
    # 100% (the common case - no adjustment needed) and steps down only if
    # the measurement render actually shows overflow, stopping at a floor
    # where any further shrinkage would hurt readability more than it helps.
    placeholder_toc = [("", 0, "")] * 4
    scale = 1.0
    scale_floor = 0.90
    scale_step = 0.02
    measure_doc = None

    while True:
        css = _scale_typography(base_css, scale) if scale != 1.0 else base_css
        measure_pages = build_pages(placeholder_toc)
        measure_doc = render(measure_pages, css)
        overflowing = _find_overflowing_pages(measure_doc.write_pdf())
        if not overflowing:
            break
        if scale <= scale_floor + 1e-9:
            print(f"[pdf_generator] WARNING: {len(overflowing)} page(s) still running tight on the "
                  f"footer at the minimum type scale ({scale:.0%}): pages {[p+1 for p in overflowing]}. "
                  f"Shipping the best-effort render rather than blocking - worth checking "
                  f"check_length_budget() output from interpretation.py for this report.")
            break
        scale = round(scale - scale_step, 2)
        print(f"[pdf_generator] {len(overflowing)} page(s) running tight on the footer "
              f"(pages {[p+1 for p in overflowing]}) - retrying at {scale:.0%} type scale.")

    css = _scale_typography(base_css, scale) if scale != 1.0 else base_css

    def find_anchor_page(anchor_id: str) -> int:
        for i, page in enumerate(measure_doc.pages):
            if anchor_id in page.anchors:
                return i + 1  # convert 0-indexed to the printed page number
        return 0  # shouldn't happen; 0 makes a missing anchor obvious in the TOC rather than silently wrong

    toc_entries = [
        ("Introduction to the Work Style Report", find_anchor_page("section-intro"),
         "An overview of the Personality and TRIAD frameworks and how this report should be used."),
        ("Personality Assessment", find_anchor_page("section-personality"),
         "The employee's results across the five major personality domains and their underlying facets."),
        ("TRIAD Assessment", find_anchor_page("section-triad"),
         "The employee's Task Orientation, Sociability, and Dominance, plus closest role cluster matches."),
        ("Manager Action Guide", find_anchor_page("section-mag"),
         "Practical strategies for communication, motivation, delegation, and leadership."),
    ]

    # --- Final render with the real, measured TOC page numbers, at whatever
    # type scale it took to clear every page's footer.
    final_doc = render(build_pages(toc_entries), css)
    return final_doc.write_pdf()
