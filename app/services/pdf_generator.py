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
from datetime import date
from typing import Any

# ── palette ──────────────────────────────────────────────────────────────────
BLUE       = "#1C3F6E"
BLUE_MID   = "#2E6DB4"
BLUE_LIGHT = "#EAF0FB"
ORANGE     = "#E07B3F"
GREEN      = "#2D7A2D"
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

def _fit_label(similarity: float) -> str:
    if similarity >= 0.90: return "Very High"
    if similarity >= 0.80: return "High"
    if similarity >= 0.65: return "Moderate"
    if similarity >= 0.50: return "Low"
    return "Very Low"

def _fit_color(label: str) -> str:
    return {"Very High": GREEN, "High": GREEN,
            "Moderate": ORANGE, "Low": "#C0392B", "Very Low": "#C0392B"}.get(label, TEXT_MID)

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
  <text x="{nlx}" y="9" text-anchor="middle" font-size="7" fill="{ORANGE}"
        font-family="RF,Arial" font-weight="bold">norm</text>
  <line x1="{nx}" y1="11" x2="{nx}" y2="{h-1}" stroke="{ORANGE}" stroke-width="2"/>
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
  <text x="{l3x:.1f}" y="{l3y+4:.1f}" text-anchor="end" font-size="8"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{cx}" y="{cy - R - 10}" text-anchor="middle" font-size="8"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{p3x:.1f}" y="{p3y+4:.1f}" text-anchor="start" font-size="8"
        fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="13" font-weight="bold"
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
    pad_x = 90   # extra horizontal space for "Open-Mindedness" label
    pad_y = 72
    total_w = size + 2 * pad_x
    total_h = size + 2 * pad_y
    cx, cy = total_w / 2, total_h / 2
    r_max = size * 0.36
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
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="8" fill="{BLUE}" font-family="RF,Arial" font-weight="bold">{nm}</text>\n'
        labels += f'<text x="{lx:.1f}" y="{ly+10:.1f}" text-anchor="{anchor}" font-size="7.5" fill="{TEXT_MID}" font-family="RF,Arial">{sc_lbl}</text>\n'

    legend_y = total_h - 8
    return f"""<svg width="{total_w}" height="{total_h}" viewBox="0 0 {total_w} {total_h}" xmlns="http://www.w3.org/2000/svg">
{grid}{spokes}
<polygon points="{score_pts}" fill="{BLUE}" fill-opacity="0.15" stroke="{BLUE}" stroke-width="2"/>
<polygon points="{norm_pts}" fill="none" stroke="{ORANGE}" stroke-width="1.5" stroke-dasharray="5,3"/>
{labels}
<circle cx="{pad_x+4}" cy="{legend_y}" r="5" fill="{BLUE}" fill-opacity="0.5"/>
<text x="{pad_x+14}" y="{legend_y+4}" font-size="8" fill="{TEXT_DARK}" font-family="RF,Arial">Employee score</text>
<circle cx="{pad_x+90}" cy="{legend_y}" r="5" fill="none" stroke="{ORANGE}" stroke-width="1.5"/>
<text x="{pad_x+100}" y="{legend_y+4}" font-size="8" fill="{TEXT_DARK}" font-family="RF,Arial">Workplace norm</text>
</svg>"""


def _role_proximity_svg(task: float, soc: float, dom: float, w: int = 530, h: int = 380) -> str:
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

    # Triangle
    tri = (f'<polygon points="{vt[0]:.1f},{vt[1]:.1f} {vl[0]:.1f},{vl[1]:.1f} ' +
           f'{vr[0]:.1f},{vr[1]:.1f}" fill="#F8FAFF" stroke="#C8D5E8" stroke-width="1.5"/>\n')

    # Axis labels
    G = "#16A34A"
    axlbls = (
        f'<text x="{vt[0]}" y="{vt[1]-22}" text-anchor="middle" font-size="9" font-weight="bold" fill="{G}" font-family="RF,Arial">Task Orientation</text>\n' +
        f'<text x="{vt[0]}" y="{vt[1]-11}" text-anchor="middle" font-size="7.5" fill="{G}" font-family="RF,Arial">(Structure)</text>\n' +
        f'<text x="{vl[0]}" y="{vl[1]+18}" text-anchor="middle" font-size="9" font-weight="bold" fill="{BLUE}" font-family="RF,Arial">Sociability</text>\n' +
        f'<text x="{vl[0]}" y="{vl[1]+29}" text-anchor="middle" font-size="7.5" fill="{BLUE}" font-family="RF,Arial">(Connect)</text>\n' +
        f'<text x="{vr[0]}" y="{vr[1]+18}" text-anchor="middle" font-size="9" font-weight="bold" fill="{ORANGE}" font-family="RF,Arial">Dominance</text>\n' +
        f'<text x="{vr[0]}" y="{vr[1]+29}" text-anchor="middle" font-size="7.5" fill="{ORANGE}" font-family="RF,Arial">(Influence)</text>\n'
    )

    # Role cluster dots — manual label offsets to avoid overlaps
    # (dx, dy, anchor): nudge relative to dot centre
    LABEL_OFFSETS = [
        ( 0, -12, "middle"),   # Team Leader
        (  12, -10, "start"),  # Task Motivator
        (  12,   4, "start"),  # Power Seeker
        ( -12, -10, "end"),    # Critic
        ( -12,  -9, "end"),    # Attention Seeker
        (   0,  12, "middle"), # Negative
        ( -12,  -9, "end"),    # Social
        ( -14,  -9, "end"),    # Coordinator
        ( -12,  -9, "end"),    # Follower
        ( -14,  -9, "end"),    # Teamwork Support
        (  12,  -9, "start"),  # Evaluator
        (   0, -12, "middle"), # Problem Solver
        (  12,  -9, "start"),  # Task Completer
    ]
    dots = ""
    for i, (rname, tc, sc2, dc) in enumerate(ROLE_CLUSTERS):
        rx, ry = to_xy(tc, sc2, dc)
        color = ROLE_COLORS[i % len(ROLE_COLORS)]
        dx, dy, anchor = LABEL_OFFSETS[i] if i < len(LABEL_OFFSETS) else (0, -12, "middle")
        lx = rx + dx
        ly = ry + dy
        dots += (
            f'<circle cx="{rx:.1f}" cy="{ry:.1f}" r="6" fill="{color}" opacity="0.88" stroke="{WHITE}" stroke-width="1"/>\n' +
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="7.5" fill="#1A2535" font-family="RF,Arial">{rname}</text>\n'
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
        f'<text x="{lx_leg+18}" y="{ly_leg+4}" font-size="8" fill="#374151" font-family="RF,Arial">Your Position</text>\n' +
        f'<circle cx="{lx_leg+100}" cy="{ly_leg}" r="5" fill="#2563EB" opacity="0.88" stroke="{WHITE}" stroke-width="1"/>\n' +
        f'<text x="{lx_leg+110}" y="{ly_leg+4}" font-size="8" fill="#374151" font-family="RF,Arial">Role Cluster</text>\n'
    )

    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">
  <rect width="{w}" height="{h}" fill="white"/>
  {grid}{tri}{axlbls}{dots}{star}{legend}
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
body {{ font-family: 'RF', Arial, sans-serif; color: {TEXT_DARK}; font-size: 10pt;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

.page {{ width: 210mm; height: 297mm; position: relative; page-break-after: always;
         overflow: hidden; background: {WHITE}; }}

/* ── COVER ── */
.cover {{ background: {BLUE}; display: flex; flex-direction: column;
          height: 297mm; justify-content: space-between; }}
.cover-body {{ padding: 56px 60px 36px; flex: 1; display: flex; flex-direction: column;
               justify-content: flex-start; }}
.cover-tag {{ font-size: 8.5pt; font-weight: 700; letter-spacing: 3px;
              color: rgba(255,255,255,0.55); text-transform: uppercase; margin-bottom: 18px; }}
.cover-edition {{ font-size: 11pt; font-weight: 700; color: {ORANGE}; margin-bottom: 22px; }}
.cover-title {{ font-size: 40pt; font-weight: 700; color: {WHITE}; line-height: 1.1; margin-bottom: 20px; }}
.cover-rule {{ width: 44px; height: 3px; background: {ORANGE}; margin-bottom: 22px; }}
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
.eyebrow {{ font-size: 7.5pt; font-weight: 700; letter-spacing: 2px; color: {BLUE};
            text-transform: uppercase; border-bottom: 1.5px solid {BLUE};
            padding-bottom: 7px; margin-bottom: 20px; }}
h2 {{ font-size: 12pt; font-weight: 700; color: {BLUE}; margin: 20px 0 8px; }}
h2:first-of-type {{ margin-top: 0; }}
p {{ line-height: 1.68; margin-bottom: 10px; font-size: 10pt; }}
.lead {{ font-size: 10.5pt; line-height: 1.72; margin-bottom: 18px; }}
.subtitle {{ font-size: 9.5pt; color: {TEXT_MID}; margin-bottom: 18px; }}

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
.callout {{ background: {BG_CARD}; border-radius: 0 8px 8px 0; border-left: 3px solid {BLUE}; padding: 14px 18px; margin-top: 16px; }}
.callout-label {{ font-size: 9pt; font-weight: 700; color: {BLUE}; margin-bottom: 3px; }}
.callout-sub {{ font-size: 8pt; color: {TEXT_LIGHT}; margin-bottom: 8px; }}
.callout p {{ font-size: 9.5pt; margin: 0; }}

/* ── GLANCE BARS ── */
.glance-card {{ background: {BG_CARD}; border-radius: 10px; padding: 14px 20px; margin-bottom: 10px; }}
.glance-card-title {{ font-size: 7.5pt; font-weight: 700; letter-spacing: 2px;
                      text-transform: uppercase; color: {TEXT_MID};
                      text-align: center; margin-bottom: 14px; }}
.bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }}
.bar-name {{ font-size: 10pt; font-weight: 700; color: {TEXT_DARK}; width: 150px; flex-shrink: 0; }}
.bar-track {{ flex: 1; }}
.bar-right {{ width: 68px; text-align: right; flex-shrink: 0; }}
.bar-score {{ font-size: 11pt; font-weight: 700; color: {BLUE}; line-height: 1; }}
.bar-level {{ font-size: 8pt; font-weight: 700; }}
.bar-level-high   {{ color: {GREEN}; }}
.bar-level-average {{ color: {BLUE}; }}
.bar-level-low    {{ color: #555E6B; }}
.scale-row {{ display: flex; justify-content: space-between; padding: 4px 0 0;
              font-size: 8pt; color: {TEXT_LIGHT}; }}
.radar-center {{ display: flex; justify-content: center; }}

/* ── GAUGE ── */
.gauge-row {{ display: flex; justify-content: space-around; align-items: flex-end;
              padding: 8px 0 4px; }}
.gauge-item {{ text-align: center; }}
.gauge-dim-name {{ font-size: 9.5pt; font-weight: 700; color: {BLUE}; margin-top: 4px; }}

/* ── TRIAD PROFILE, stacked bars like BFI ── */
.triad-stack-row {{ display: flex; align-items: center; gap: 16px; margin-bottom: 14px;
                    padding-bottom: 12px; border-bottom: 1px solid {RULE}; }}
.triad-stack-row:last-child {{ border-bottom: none; margin-bottom: 0; }}
.triad-stack-left {{ width: 160px; flex-shrink: 0; }}
.triad-stack-name {{ font-size: 10.5pt; font-weight: 700; color: {BLUE}; }}
.triad-stack-score {{ font-size: 20pt; font-weight: 700; color: {BLUE}; line-height: 1.1; }}
.triad-stack-pill {{ display: inline-block; font-size: 7.5pt; font-weight: 700;
                     color: {WHITE}; background: {ORANGE}; padding: 3px 10px;
                     border-radius: 20px; margin-top: 4px; }}
.triad-stack-track {{ flex: 1; }}

/* ── DOMAIN PAGES ── */
.domain-header {{ margin-bottom: 12px; }}
.domain-title-row {{ display: flex; align-items: baseline; gap: 12px;
                     margin-bottom: 8px; flex-wrap: wrap; }}
.domain-name {{ font-size: 14pt; font-weight: 700; color: {BLUE}; }}
.level-badge {{ font-size: 8pt; font-weight: 700; padding: 2px 8px; border-radius: 4px; }}
.badge-high    {{ background: #DCF0DC; color: {GREEN}; }}
.badge-average {{ background: {BLUE_LIGHT}; color: {BLUE}; }}
.badge-low     {{ background: #E8EDF5; color: #555E6B; }}
.domain-bar {{ margin-bottom: 10px; }}
.section-intro {{ font-size: 9.5pt; line-height: 1.65; margin-bottom: 10px; }}

.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 10px; }}
.two-col > div {{
  background: {BG_CARD};
  border-radius: 6px;
  padding: 10px 12px;
}}
.col-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.5px; color: {BLUE};
              text-transform: uppercase; margin-bottom: 5px; }}
.col-text {{ font-size: 9pt; line-height: 1.62; margin: 0; }}

.facet-rule {{ border-top: 1px solid {RULE}; padding-top: 8px; margin: 8px 0; }}
.facet-rule-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.5px;
                     text-transform: uppercase; color: {TEXT_LIGHT}; }}
.facet {{ margin-bottom: 9px; padding-bottom: 8px; border-bottom: 1px solid {RULE}; }}
.facet:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.facet-header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }}
.facet-name {{ font-size: 9.5pt; font-weight: 700; color: {BLUE}; flex: 1; }}
.facet-bar {{ margin-bottom: 5px; }}
.facet-body {{ font-size: 9pt; line-height: 1.6; margin-bottom: 7px; }}
.facet-two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
.facet-two-col > div {{
  background: {BG_CARD};
  border-radius: 5px;
  padding: 8px 10px;
}}

/* ── TRIAD INTERPRETATION, consistent with domain pages ── */
.triad-interp-block {{ margin-bottom: 20px; padding-bottom: 18px;
                       border-bottom: 1px solid {RULE}; }}
.triad-interp-block:last-child {{ border-bottom: none; margin-bottom: 0; }}
.triad-interp-header {{ display: flex; align-items: baseline; gap: 14px; margin-bottom: 8px; }}
.triad-interp-score {{ font-size: 22pt; font-weight: 700; color: {BLUE}; }}
.triad-interp-name {{ font-size: 13pt; font-weight: 700; color: {BLUE}; }}
.dir-pill {{ display: inline-block; font-size: 7.5pt; font-weight: 700;
             color: {WHITE}; background: {ORANGE}; padding: 3px 10px;
             border-radius: 20px; margin-left: 6px; }}
.triad-interp-bar {{ margin: 8px 0 12px; }}
.triad-three-col {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
.triad-three-col > div {{
  background: {BG_CARD};
  border-radius: 6px;
  padding: 10px 12px;
}}
.triad-three-col p {{ font-size: 9pt; line-height: 1.62; margin: 0; }}

/* ── MANAGER ACTION GUIDE ── */
.mag-section {{ background: {BG_CARD}; border-radius: 8px; padding: 10px 14px;
                margin-bottom: 8px; }}
.mag-section-title {{
  font-size: 9pt;
  font-weight: 700;
  color: {BLUE};
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid {RULE};
}}
.mag-narrative {{ font-size: 9pt; line-height: 1.6; margin-bottom: 8px; }}
.mag-sub-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1px;
                  color: {BLUE}; text-transform: uppercase; margin-bottom: 4px; margin-top: 6px; }}
.mag-list {{ list-style: none; padding: 0; }}
.mag-list li {{ display: flex; gap: 8px; font-size: 9pt; line-height: 1.55;
                margin-bottom: 4px; align-items: flex-start; }}
.bullet {{ color: {ORANGE}; font-size: 11pt; line-height: 1.2; flex-shrink: 0; }}

/* ── ROLE PROXIMITY ── */
.ternary-map {{ display: flex; justify-content: center; }}
.proximity-grid {{ display: flex; flex-direction: column; gap: 16px; margin-top: 12px; }}
.proximity-right {{ }}
.proximity-table-label {{ font-size: 8pt; font-weight: 700; letter-spacing: 1px;
                           text-transform: uppercase; color: {BLUE}; margin-bottom: 8px; }}
.proximity-table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; }}
.proximity-table th {{ font-size: 7.5pt; font-weight: 700; letter-spacing: 1px;
                       text-transform: uppercase; color: {TEXT_MID};
                       border-bottom: 1.5px solid {RULE}; padding: 6px 8px;
                       text-align: left; }}
.proximity-table td {{ padding: 8px 10px; border-bottom: 1px solid {RULE};
                       vertical-align: middle; font-size: 10pt; }}
.proximity-table tr:nth-child(1) td {{ background: rgba(28,63,110,0.04); }}
.proximity-table tr:last-child td {{ border-bottom: none; }}
.rank-1 {{ font-weight: 700; }}
.fit-bar {{ height: 8px; border-radius: 4px; background: {BLUE}; display: inline-block; }}
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
    <div class="cover-edition">Manager Edition</div>
    <div class="cover-title">Understanding<br>How They Work</div>
    <div class="cover-rule"></div>
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


def _welcome(p: dict, pg: int) -> str:
    employee = p.get("name","the employee")
    return f"""<div class="page content">
  <div class="eyebrow">What's in the Work Style Report?</div>
  <p>This report is organized into four sections that help managers understand employee work style, interpret assessment results, and apply practical leadership strategies.</p>

  <h2>Introduction</h2>
  <p>This report provides practical leadership insights about {_esc(employee)} derived from two evidence-based frameworks. Together, they describe how {_esc(employee)} is likely to approach work, interact with others, respond to workplace demands, and contribute to team performance. These insights should be used alongside direct observation, ongoing feedback, and direct conversations.</p>

  <h2>Personality Assessment</h2>
  <p>Personality reflects a person's natural behavioral tendencies and typical patterns likely to emerge during everyday work interactions. The Five Factor Model measures normal personality characteristics that influence how individuals approach work, relationships, leadership, and career success.</p>

  <h2>The TRIAD Model Role Profile</h2>
  <p>TRIAD (Tracking Roles In and Across Domains) examines the fit between individual profiles and role performance. It measures three primary dimensions:</p>
  <div class="triad-dim-list">
    <div class="triad-dim-item"><span class="triad-dim-label">Task Orientation</span><span class="triad-dim-desc">The degree to which the employee prefers structure, organization, planning, and focus on outcomes.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Sociability</span><span class="triad-dim-desc">How the employee connects, communicates, collaborates, and builds relationships with others.</span></div>
    <div class="triad-dim-item"><span class="triad-dim-label">Dominance</span><span class="triad-dim-desc">How the employee influences others, asserts ideas, takes initiative, and guides direction.</span></div>
  </div>

  {_footer(employee, pg)}
</div>"""


def _exec_summary(p: dict, report: dict, pg: int) -> str:
    employee = p.get("name","the employee")
    summary  = _esc(report["executive_summary"]["text"])
    t = report["triad"]

    # Build bridge text cleanly, name each dimension without repeating "tendency"
    task_lbl = _esc(t["task"]["direction_label"])
    soc_lbl  = _esc(t["sociability"]["direction_label"])
    dom_lbl  = _esc(t["dominance"]["direction_label"])

    bridge = (
        f"Read together, the two frameworks tell a consistent story about {_esc(employee)}. "
        f"Sociability is the dominant TRIAD theme ({soc_lbl}, {t['sociability']['score']:+.2f}), "
        f"reinforced by high Agreeableness and Extraversion in the personality results, "
        f"pointing to someone who naturally builds and holds teams together. "
        f"Dominance runs at a {dom_lbl.lower()} level ({t['dominance']['score']:+.2f}), "
        f"suggesting influence through ideas and collaboration rather than positional authority. "
        f"Task orientation is {task_lbl.lower()} ({t['task']['score']:+.2f}), "
        f"describing someone who keeps work moving without generating friction around process."
    )

    return f"""<div class="page content">
  <div class="eyebrow">Personality Assessment</div>
  <h2>Employee Snapshot</h2>
  <p class="lead">{summary}</p>
  <div class="callout">
    <div class="callout-label">Workplace Contribution Profile</div>
    <div class="callout-sub">A combined read across the Personality and TRIAD assessment results.</div>
    <p>{bridge}</p>
  </div>
  {_footer(employee, pg)}
</div>"""


def _glance(p: dict, report: dict, pg: int) -> str:
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

    return f"""<div class="page content">
  <div class="eyebrow">Personality Assessment</div>
  <h2>Personality at a Glance</h2>
  <p class="subtitle">Each score is compared to a normative sample. The norm represents the average
  score of the general population and serves as a reference point for interpreting results.</p>

  <div class="glance-card">
    <div class="glance-card-title">Score vs Norm</div>
    {rows}
    <div class="scale-row"><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span></div>
  </div>

  <div class="glance-card">
    <div class="glance-card-title">Profile Shape</div>
    <div class="radar-center">{_radar_svg(domains, size=210)}</div>
  </div>

  {_footer(employee, pg)}
</div>"""


def _domain(p: dict, domain: dict, pg: int) -> str:
    employee = p.get("name","")
    dname    = _esc(domain["name"])
    score    = domain["score"]
    norm     = domain["norm"]
    level    = domain["level"]
    lc       = _level_cls(level)

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
  <div class="eyebrow">Personality Assessment</div>
  <div class="domain-header">
    <div class="domain-title-row">
      <span class="domain-name">{dname}</span>
      <span class="level-badge badge-{lc}">{_esc(level)}</span>
    </div>
    <div class="domain-bar">{_bfi_bar_svg(score, norm, w=500, h=32)}</div>
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


def _triad_profile(p: dict, report: dict, pg: int) -> str:
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
      <div class="triad-stack-track">{_triad_bar_svg(d['score'], w=340, h=32)}</div>
    </div>"""

    # Gauge view
    gauges = ""
    for key, label in dims:
        d = triad[key]
        gauges += f'''<div class="gauge-item">
      {_gauge_svg(d['score'], w=160, h=130)}
      <div class="gauge-dim-name">{_esc(label)}</div>
    </div>'''

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Assessment</div>
  <h2>TRIAD at a Glance</h2>
  <p class="subtitle">The TRIAD profile summarises {_esc(employee)}'s natural tendencies toward Task Orientation,
  Sociability, and Dominance, a snapshot of how they are most likely to contribute within a team.</p>

  <div class="glance-card">
    <div class="glance-card-title">Gauge View</div>
    <div class="gauge-row">{gauges}</div>
  </div>

  <div class="glance-card">
    <div class="glance-card-title">Scale View</div>
    {rows}
  </div>

  {_footer(employee, pg)}
</div>"""


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
      <div class="triad-three-col">
        <div><div class="col-label">Overall Interpretation</div><p>{_esc(d['interpretation'])}</p></div>
        <div><div class="col-label">Likely Contribution</div><p>{contrib}</p></div>
        <div><div class="col-label">Manager Considerations</div><p>{mgr_con}</p></div>
      </div>
    </div>"""

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Assessment</div>
  <p class="subtitle">This report interprets team role tendencies using the TRIAD Model
  (Driskell, Driskell, Burke &amp; Salas, 2017), which defines three core behavioral
  dimensions that together describe team role behavior.</p>
  {blocks}
  {_footer(employee, pg)}
</div>"""


def _role_proximity(p: dict, report: dict, pg: int) -> str:
    """
    Role Cluster Proximity, Option F: ranked table + mini TRIAD visual.
    Tripp: "right now a version of F inside the role proximity section will suffice."
    """
    employee = p.get("name","")
    t = report["triad"]
    task = t["task"]["score"]
    soc  = t["sociability"]["score"]
    dom  = t["dominance"]["score"]

    distances = _compute_role_distances(task, soc, dom)
    top5      = distances[:5]

    # Bar width proportional to similarity
    def bar_w(sim): return max(4, int(sim * 80))

    rows = ""
    for i,(role,sim,fit) in enumerate(top5):
        rank = i + 1
        star = "★ " if rank == 1 else f"{rank} "
        pct  = f"{sim*100:.0f}%"
        fcolor = _fit_color(fit)
        bw = bar_w(sim)
        cls = "rank-1" if rank == 1 else ""
        rows += f"""<tr>
      <td><span class="{cls}">{star}</span></td>
      <td class="{cls}">{_esc(role)}</td>
      <td>{pct}</td>
      <td><span class="fit-bar" style="width:{bw}px;background:{fcolor}"></span></td>
      <td style="color:{fcolor};font-weight:{'700' if rank==1 else '400'}">{_esc(fit)}</td>
    </tr>"""

    mini_svg = _role_proximity_svg(task, soc, dom)

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Assessment</div>
  <h2>TRIAD Role Navigator</h2>
  <p class="subtitle">{_esc(employee)}'s location in the TRIAD role space. The closer {_esc(employee)} is to a role, the more naturally they are likely to exhibit the behaviors associated with that role.</p>

  <div class="proximity-grid">
    <div class="ternary-map">{mini_svg}</div>
    <div class="proximity-right">
      <div class="proximity-table-label">Closest Role Matches</div>
      <table class="proximity-table">
        <thead>
          <tr>
            <th style="width:44px">Rank</th>
            <th style="width:160px">Role</th>
            <th style="width:90px">Similarity</th>
            <th style="width:140px">Fit</th>
            <th style="width:100px">Fit Level</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
      <p style="font-size:8pt;color:{TEXT_LIGHT};margin-top:10px;font-style:italic">
        Based on {_esc(employee)}'s combined Task Orientation, Sociability, and Dominance scores.
      </p>
    </div>
  </div>
  {_footer(employee, pg)}
</div>"""


def _manager_action_guide(p: dict, report: dict, pg: int) -> list[str]:
    """
    Manager Action Guide, two pages:
    Page 1: Communication Style + Motivators & Stressors
    Page 2: Delegation Guide + Leadership Summary & Action Plan
    Returns list of two page HTML strings.
    """
    employee = p.get("name","")
    mag = report.get("manager_action_guide", {})

    def section(title, narrative, bullets_dict):
        html = f'<div class="mag-section"><div class="mag-section-title">{_esc(title)}</div>'
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
    subtitle = '<p class="subtitle">Practical leadership strategies that help managers communicate more effectively, support employee development, and maximise workplace performance.</p>'

    page1 = f"""<div class="page content">
  {eyebrow}
  {subtitle}
  {section("Communication Style",
    comm.get("narrative",""),
    {"Manager Recommendations": comm.get("recommendations",[])}
  )}
  {section("Motivators &amp; Stressors",
    mot.get("narrative",""),
    {"Key Motivators": mot.get("motivators",[]),
     "Potential Stressors": mot.get("stressors",[])}
  )}
  {_footer(employee, pg)}
</div>"""

    page2 = f"""<div class="page content">
  {eyebrow}
  {section("Delegation Guide",
    dele.get("narrative",""),
    {"Best Suited For": dele.get("best_suited_for",[]),
     "Management Recommendations": dele.get("recommendations",[])}
  )}
  {section("Leadership Summary &amp; Action Plan",
    lead.get("narrative",""),
    {"Strengths to Leverage": lead.get("strengths",[]),
     "Potential Watch Points": lead.get("watch_points",[]),
     "Recommended Actions": lead.get("actions",[])}
  )}
  {_footer(employee, pg + 1)}
</div>"""

    return [page1, page2]


# ── entry point ───────────────────────────────────────────────────────────────
def generate_pdf(participant: dict[str, Any], report: dict[str, Any]) -> bytes:
    """
    participant: {"name": str, "role": str, "manager": str (optional)}
    report:      validated dict from interpretation.interpret()
    Returns PDF as bytes.
    """
    from weasyprint import HTML, CSS as WpCSS

    font_css = _font_css()
    css      = _css(font_css)

    pg = 1
    pages = []
    pages.append(_cover(participant, pg));                    pg += 1
    pages.append(_welcome(participant, pg));                  pg += 1
    pages.append(_exec_summary(participant, report, pg));     pg += 1
    pages.append(_glance(participant, report, pg));           pg += 1
    for domain in report["domains"]:
        pages.append(_domain(participant, domain, pg));       pg += 1
    pages.append(_triad_profile(participant, report, pg));    pg += 1
    pages.append(_triad_interpretation(participant, report, pg)); pg += 1
    pages.append(_role_proximity(participant, report, pg));   pg += 1
    mag_pages = _manager_action_guide(participant, report, pg)
    for mp in mag_pages:
        pages.append(mp); pg += 1

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{"".join(pages)}</body></html>"""

    return HTML(string=html).write_pdf(
        stylesheets=[WpCSS(string="@page { size: A4; margin: 0; }")]
    )
