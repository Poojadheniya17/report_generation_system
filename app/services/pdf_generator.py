"""
PDF generation service — rebuilt to exactly match the approved Jordan Avery report
that Tripp reviewed and approved (fine-tooth-comb review, June 2026).

Visual spec extracted directly from the approved PDF:
- Colours: primary blue #1B4F8C, accent orange #E07B3F, light bg #F0F4FA
- Cover: "Understanding How You Work" as giant hero, participant info row at bottom
- BFI bars: navy fill, open-circle score marker, orange vertical norm line, score+level right
- TRIAD page: semicircle gauge view (3 side by side) + scale view below
- TRIAD interpretation: score large left, bar -3..+3, interpretation + implications two-col
- Domain pages: domain name large, 2-col prefs/needs, facet detail below
- Recommendations: three cards (Strengths/Blind Spots/Dev Suggestions) + navy focus box
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any

# ── palette (matches approved PDF exactly) ───────────────────────────────────
BLUE       = "#1C3F6E"    # primary — headings, bars, cover
BLUE_MID   = "#2E6DB4"    # secondary
BLUE_LIGHT = "#E8F0FB"    # card backgrounds
ORANGE     = "#E07B3F"    # norm markers, accent labels
WHITE      = "#FFFFFF"
BG_PAGE    = "#FFFFFF"
BG_CARD    = "#F4F7FC"
TEXT_DARK  = "#1A2535"
TEXT_MID   = "#4A5568"
TEXT_LIGHT = "#8A9BB8"
RULE       = "#D8E3F0"
GREEN_HIGH = "#2D7A2D"
AMBER_LOW  = "#555E6B"


def _esc(t: str) -> str:
    return (str(t).replace("&","&amp;").replace("<","&lt;")
            .replace(">","&gt;").replace('"',"&quot;"))

def _level_cls(level: str) -> str:
    return level.lower().replace(" ","_")

def _diff_str(d: float) -> str:
    return f"+{d:.2f}" if d >= 0 else f"{d:.2f}"

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

def _bfi_bar_svg(score: float, norm: float, w: int = 380, h: int = 28) -> str:
    """
    Horizontal BFI bar matching approved PDF:
    - Blue filled bar from left to score
    - Open circle at score position
    - Orange vertical line at norm, labelled 'norm' above in orange
    - Scale 1-5
    """
    lo, hi = 1.0, 5.0
    def px(v): return max(4, min(w - 4, int((v - lo) / (hi - lo) * w)))
    bw = px(score)
    nx = px(norm)
    track_y = h // 2
    r = 7  # open circle radius

    # norm label x — nudge away from edges
    nlx = max(22, min(w - 22, nx))

    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <rect x="0" y="{track_y-4}" width="{w}" height="8" rx="4" fill="#DCE8F5"/>
  <rect x="0" y="{track_y-4}" width="{bw}" height="8" rx="4" fill="{BLUE}"/>
  <text x="{nlx}" y="8" text-anchor="middle" font-size="7" fill="{ORANGE}" font-family="RF,Arial" font-weight="bold">norm</text>
  <line x1="{nx}" y1="11" x2="{nx}" y2="{h-1}" stroke="{ORANGE}" stroke-width="2"/>
  <circle cx="{bw}" cy="{track_y}" r="{r}" fill="{WHITE}" stroke="{BLUE}" stroke-width="2"/>
</svg>"""


def _gauge_svg(score: float, w: int = 170, h: int = 125) -> str:
    """
    Speedometer semicircle.
    SVG arc facts (y-axis DOWN):
      sweep=0 = counter-clockwise visually
      sweep=1 = clockwise visually
    We want arcs going LEFT → UP OVER TOP → RIGHT = clockwise in SVG = sweep=1
    Background: full semicircle from left to right, sweep=1, large=1
    Filled:     from left to score point,            sweep=1, large=0 (always < 180deg span)
    """
    import math as _m
    cx  = w // 2
    cy  = h - 30
    R   = cx - 14

    def s2a(s): return _m.pi * (1 - (s + 3) / 6)
    def pt(r, a): return cx + r * _m.cos(a), cy - r * _m.sin(a)

    a_L = s2a(-3)
    a_R = s2a(3)
    a_S = s2a(score)

    lx, ly = pt(R, a_L)
    rx, ry = pt(R, a_R)
    sx, sy = pt(R, a_S)

    # Background: left to right, clockwise (over top), large arc
    bg = (f'<path d="M {lx:.1f} {ly:.1f} A {R} {R} 0 1 1 {rx:.1f} {ry:.1f}" ' +
          f'fill="none" stroke="#DCE8F5" stroke-width="13" stroke-linecap="round"/>')

    # Filled: left to score, clockwise (over top), small arc
    filled = (f'<path d="M {lx:.1f} {ly:.1f} A {R} {R} 0 0 1 {sx:.1f} {sy:.1f}" ' +
              f'fill="none" stroke="{BLUE}" stroke-width="13" stroke-linecap="round"/>')

    # Needle
    nr = R - 8
    nx, ny = pt(nr, a_S)

    # Labels
    llx, lly = pt(R + 15, a_L)
    lrx, lry = pt(R + 15, a_R)
    score_str = f"{score:+.2f}"

    return f'''<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">
  {bg}
  {filled}
  <line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="{TEXT_DARK}" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="{cx}" cy="{cy}" r="5" fill="{TEXT_DARK}"/>
  <text x="{llx:.1f}" y="{lly+4:.1f}" text-anchor="end" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{cx}" y="{cy - R - 10}" text-anchor="middle" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{lrx:.1f}" y="{lry+4:.1f}" text-anchor="start" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
  <text x="{cx}" y="{cy + 20}" text-anchor="middle" font-size="15" font-weight="bold" fill="{BLUE}" font-family="RF,Arial">{score_str}</text>
</svg>'''
def _scale_bar_svg(score: float, w: int = 180, h: int = 32) -> str:
    """
    Horizontal scale -3..+3 with dot marker. Matches approved PDF scale view.
    """
    lo, hi = -3.0, 3.0
    pct = (score - lo) / (hi - lo)
    mx = int(pct * w)
    cx = w // 2

    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <line x1="0" y1="12" x2="{w}" y2="12" stroke="{RULE}" stroke-width="1.5"/>
  <line x1="{cx}" y1="6" x2="{cx}" y2="18" stroke="{TEXT_LIGHT}" stroke-width="1"/>
  <circle cx="{mx}" cy="12" r="6" fill="{BLUE}"/>
  <text x="0" y="{h}" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{cx}" y="{h}" text-anchor="middle" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{w}" y="{h}" text-anchor="end" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
</svg>"""


def _triad_interp_bar_svg(score: float, w: int = 480, h: int = 20) -> str:
    """Thin bar for TRIAD interpretation page — matches approved PDF style."""
    lo, hi = -3.0, 3.0
    pct = (score - lo) / (hi - lo)
    cx = w // 2
    mx = int(pct * w)
    fill_x = min(cx, mx)
    fill_w = abs(mx - cx)
    return f"""<svg width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg" style="display:block">
  <rect x="0" y="7" width="{w}" height="6" rx="3" fill="{RULE}"/>
  <rect x="{fill_x}" y="7" width="{fill_w}" height="6" rx="0" fill="{BLUE}"/>
  <line x1="{cx}" y1="3" x2="{cx}" y2="17" stroke="{TEXT_LIGHT}" stroke-width="1" stroke-dasharray="2,2"/>
  <circle cx="{mx}" cy="10" r="5" fill="{BLUE}" stroke="{WHITE}" stroke-width="1.5"/>
  <text x="0" y="{h}" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">-3</text>
  <text x="{w//2}" y="{h}" text-anchor="middle" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">0</text>
  <text x="{w}" y="{h}" text-anchor="end" font-size="8" fill="{TEXT_LIGHT}" font-family="RF,Arial">+3</text>
</svg>"""


def _radar_svg(domains: list[dict], size: int = 260) -> str:
    """Pentagon radar — matches approved PDF profile shape."""
    n = 5
    pad = 56
    total = size + 2 * pad
    cx, cy = total / 2, total / 2
    r_max = size * 0.38
    lo, hi = 1.0, 5.0

    def pt(i, v):
        ang = math.radians(90 + 360 / n * i)
        r = r_max * (v - lo) / (hi - lo)
        return cx - r * math.cos(ang), cy - r * math.sin(ang)

    def label_pt(i):
        ang = math.radians(90 + 360 / n * i)
        r = r_max + 24
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

    short = ["Extraversion","Agreeableness","Conscientiousness","Negative Emotionality","Open-Mindedness"]
    lc_anchors = ["middle","start","start","end","end"]
    score_labels = [f"{d['score']:.2f} · {d['level']}" for d in domains]

    labels = ""
    for i,(nm,sc_lbl,anchor) in enumerate(zip(short, score_labels, lc_anchors)):
        lx, ly = label_pt(i)
        labels += f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anchor}" font-size="8" fill="{BLUE}" font-family="RF,Arial" font-weight="bold">{nm}</text>\n'
        labels += f'<text x="{lx:.1f}" y="{ly+10:.1f}" text-anchor="{anchor}" font-size="7.5" fill="{TEXT_MID}" font-family="RF,Arial">{sc_lbl}</text>\n'

    legend_y = total - 8
    return f"""<svg width="{total}" height="{total}" viewBox="0 0 {total} {total}" xmlns="http://www.w3.org/2000/svg">
{grid}{spokes}
<polygon points="{score_pts}" fill="{BLUE}" fill-opacity="0.15" stroke="{BLUE}" stroke-width="2"/>
<polygon points="{norm_pts}" fill="none" stroke="{ORANGE}" stroke-width="1.5" stroke-dasharray="5,3"/>
{labels}
<circle cx="{pad+4}" cy="{legend_y}" r="5" fill="{BLUE}" fill-opacity="0.5"/>
<text x="{pad+14}" y="{legend_y+4}" font-size="8" fill="{TEXT_DARK}" font-family="RF,Arial">Your score</text>
<circle cx="{pad+74}" cy="{legend_y}" r="5" fill="none" stroke="{ORANGE}" stroke-width="1.5"/>
<text x="{pad+84}" y="{legend_y+4}" font-size="8" fill="{TEXT_DARK}" font-family="RF,Arial">Workplace norm</text>
</svg>"""


# ── CSS ───────────────────────────────────────────────────────────────────────
def _css(font_css: str) -> str:
    return f"""
{font_css}
@page {{ size: A4; margin: 0; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: 'RF', Arial, sans-serif; color: {TEXT_DARK}; font-size: 9.5pt;
       -webkit-print-color-adjust: exact; print-color-adjust: exact; }}

.page {{ width: 210mm; height: 297mm; position: relative; overflow: hidden;
         page-break-after: always; background: {WHITE}; }}

/* ── COVER ── */
.cover {{ background: {BLUE}; display: flex; flex-direction: column; justify-content: space-between; }}
.cover-body {{ padding: 52px 56px 32px; flex: 1; display: flex; flex-direction: column; justify-content: flex-start; }}
.cover-tag {{ font-size: 7pt; font-weight: 700; letter-spacing: 3px; color: rgba(255,255,255,0.55);
              text-transform: uppercase; margin-bottom: 20px; }}
.cover-title {{ font-size: 42pt; font-weight: 700; color: {WHITE}; line-height: 1.1; margin-bottom: 20px; }}
.cover-rule {{ width: 44px; height: 3px; background: {ORANGE}; margin-bottom: 20px; }}
.cover-desc {{ font-size: 9.5pt; color: rgba(255,255,255,0.62); line-height: 1.65; max-width: 360px; }}
.cover-meta {{ display: flex; gap: 40px; padding: 24px 56px; border-top: 1px solid rgba(255,255,255,0.15); }}
.cover-meta-item .label {{ font-size: 6.5pt; letter-spacing: 2px; color: rgba(255,255,255,0.45);
                           text-transform: uppercase; margin-bottom: 5px; }}
.cover-meta-item .value {{ font-size: 12pt; font-weight: 700; color: {WHITE}; }}
.cover-footer {{ padding: 12px 56px; border-top: 1px solid rgba(255,255,255,0.1);
                 font-size: 7pt; color: rgba(255,255,255,0.3); letter-spacing: 1px;
                 display: flex; justify-content: space-between; align-items: center; }}

/* ── CONTENT ── */
.content {{ padding: 44px 52px 72px; }}
.eyebrow {{ font-size: 7pt; font-weight: 700; letter-spacing: 2px; color: {BLUE};
            text-transform: uppercase; border-bottom: 1.5px solid {BLUE};
            padding-bottom: 7px; margin-bottom: 22px; }}
h2 {{ font-size: 11.5pt; font-weight: 700; color: {BLUE}; margin: 18px 0 8px; }}
h2:first-of-type {{ margin-top: 0; }}
p {{ line-height: 1.68; margin-bottom: 10px; font-size: 9.5pt; }}
.lead {{ font-size: 10pt; line-height: 1.72; margin-bottom: 18px; }}
.subtitle {{ font-size: 9pt; color: {TEXT_MID}; margin-bottom: 20px; }}

.footer {{ position: absolute; bottom: 20px; left: 52px; right: 52px;
           display: flex; justify-content: space-between;
           font-size: 7.5pt; color: {TEXT_LIGHT};
           border-top: 1px solid {RULE}; padding-top: 8px; }}

/* ── CALLOUT ── */
.callout {{ background: {BG_CARD}; border-radius: 8px; padding: 16px 20px; margin-top: 18px; }}
.callout-label {{ font-size: 8pt; font-weight: 700; color: {BLUE}; margin-bottom: 3px; }}
.callout-sub {{ font-size: 7.5pt; color: {TEXT_LIGHT}; margin-bottom: 8px; }}
.callout p {{ font-size: 9pt; margin: 0; }}

/* ── GLANCE PAGE ── */
.glance-card {{ background: {BG_CARD}; border-radius: 10px; padding: 20px 24px; margin-bottom: 16px; }}
.glance-card-title {{ font-size: 7pt; font-weight: 700; letter-spacing: 2px;
                      text-transform: uppercase; color: {TEXT_MID};
                      text-align: center; margin-bottom: 16px; }}
.bar-row {{ display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }}
.bar-name {{ font-size: 9.5pt; font-weight: 700; color: {TEXT_DARK}; width: 148px; flex-shrink: 0; }}
.bar-track {{ flex: 1; }}
.bar-right {{ width: 68px; text-align: right; flex-shrink: 0; }}
.bar-score {{ font-size: 11pt; font-weight: 700; color: {BLUE}; line-height: 1; }}
.bar-level {{ font-size: 7.5pt; font-weight: 700; }}
.bar-level-high {{ color: {GREEN_HIGH}; }}
.bar-level-average {{ color: {BLUE}; }}
.bar-level-low {{ color: {AMBER_LOW}; }}
.scale-row {{ display: flex; align-items: center; justify-content: space-between;
              font-size: 8pt; color: {TEXT_LIGHT}; margin-top: 6px; padding: 0 4px; }}
.radar-center {{ display: flex; justify-content: center; }}

/* ── TRIAD PROFILE PAGE ── */
.triad-card {{ background: {BG_CARD}; border-radius: 10px; padding: 20px 24px; margin-bottom: 14px; }}
.triad-card-title {{ font-size: 7pt; font-weight: 700; letter-spacing: 2px;
                     text-transform: uppercase; color: {TEXT_MID};
                     text-align: center; margin-bottom: 16px; }}
.gauge-row {{ display: flex; justify-content: space-around; align-items: flex-end; }}
.gauge-item {{ text-align: center; }}
.gauge-dim-name {{ font-size: 9pt; font-weight: 700; color: {TEXT_DARK}; margin-top: 4px; }}
.scale-view-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }}
.scale-item {{ }}
.scale-name {{ font-size: 8pt; font-weight: 700; color: {TEXT_DARK}; margin-bottom: 3px; }}
.scale-score {{ font-size: 13pt; font-weight: 700; color: {BLUE}; margin-bottom: 6px; }}

/* ── DOMAIN PAGES ── */
.domain-header {{ margin-bottom: 14px; }}
.domain-title-row {{ display: flex; align-items: baseline; gap: 12px;
                     margin-bottom: 8px; flex-wrap: wrap; }}
.domain-name {{ font-size: 15pt; font-weight: 700; color: {BLUE}; }}
.domain-meta {{ font-size: 8pt; color: {TEXT_LIGHT}; }}
.level-badge {{ font-size: 8pt; font-weight: 700; padding: 2px 9px; border-radius: 4px; }}
.badge-high    {{ background: #DCF0DC; color: {GREEN_HIGH}; }}
.badge-average {{ background: {BLUE_LIGHT}; color: {BLUE}; }}
.badge-low     {{ background: #E8EDF5; color: {AMBER_LOW}; }}
.domain-bar {{ margin-bottom: 12px; }}
.domain-meaning {{ font-size: 9.5pt; line-height: 1.68; margin-bottom: 14px; }}
.two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 14px; }}
.col-label {{ font-size: 6.5pt; font-weight: 700; letter-spacing: 1.5px; color: {BLUE};
              text-transform: uppercase; margin-bottom: 5px; }}
.col-text {{ font-size: 8.5pt; line-height: 1.62; margin: 0; }}
.facet-rule {{ border-top: 1px solid {RULE}; padding-top: 10px; margin: 12px 0 12px; }}
.facet-rule-label {{ font-size: 6.5pt; font-weight: 700; letter-spacing: 1.5px;
                     text-transform: uppercase; color: {TEXT_LIGHT}; }}
.facet {{ margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid {RULE}; }}
.facet:last-child {{ border-bottom: none; margin-bottom: 0; padding-bottom: 0; }}
.facet-header {{ display: flex; align-items: center; gap: 9px; margin-bottom: 6px; flex-wrap: wrap; }}
.facet-name {{ font-size: 9pt; font-weight: 700; color: {BLUE}; }}
.facet-meta {{ font-size: 7.5pt; color: {TEXT_LIGHT}; flex: 1; }}
.facet-bar {{ margin-bottom: 7px; }}
.facet-meaning {{ font-size: 8.5pt; line-height: 1.62; margin-bottom: 9px; }}

/* ── TRIAD INTERPRETATION ── */
.triad-ref {{ font-size: 8.5pt; color: {TEXT_LIGHT}; font-style: italic;
              line-height: 1.55; margin-bottom: 20px; }}
.triad-interp-block {{ margin-bottom: 22px; padding-bottom: 18px; border-bottom: 1px solid {RULE}; }}
.triad-interp-block:last-child {{ border-bottom: none; margin-bottom: 0; }}
.triad-interp-top {{ display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }}
.triad-interp-score {{ font-size: 22pt; font-weight: 700; color: {BLUE}; min-width: 72px; }}
.triad-interp-name {{ font-size: 11pt; font-weight: 700; color: {BLUE}; }}
.dir-pill {{ font-size: 8pt; font-weight: 700; color: {WHITE}; background: {ORANGE};
             padding: 3px 11px; border-radius: 20px; white-space: nowrap; }}
.triad-interp-bar {{ margin: 8px 0 12px; }}
.triad-interp-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.triad-interp-cols p {{ font-size: 8.5pt; line-height: 1.62; margin: 0; }}

/* ── RECOMMENDATIONS ── */
.rec-card {{ background: {BG_CARD}; border-radius: 8px; padding: 16px 20px; margin-bottom: 12px; }}
.rec-card-label {{ font-size: 7.5pt; font-weight: 700; letter-spacing: 1px;
                   text-transform: uppercase; margin-bottom: 10px; }}
.rec-label-strengths {{ color: {BLUE}; }}
.rec-label-blind {{ color: {ORANGE}; }}
.rec-label-dev {{ color: {BLUE}; }}
.rec-list {{ list-style: none; padding: 0; }}
.rec-list li {{ display: flex; gap: 8px; font-size: 9pt; line-height: 1.62;
                margin-bottom: 7px; align-items: flex-start; }}
.bullet {{ color: {ORANGE}; font-size: 11pt; line-height: 1.2; flex-shrink: 0; }}
.focus-box {{ background: {BLUE}; color: {WHITE}; padding: 20px 24px;
              border-radius: 8px; margin-top: 8px; }}
.focus-label {{ font-size: 7pt; font-weight: 700; letter-spacing: 1.5px;
                text-transform: uppercase; color: rgba(255,255,255,0.6); margin-bottom: 9px; }}
.focus-text {{ font-size: 9.5pt; line-height: 1.68; color: {WHITE}; margin: 0; }}
"""


# ── footer ────────────────────────────────────────────────────────────────────
def _footer(name: str, page_num: int) -> str:
    return f"""<div class="footer">
  <span>Work Style Report &nbsp;·&nbsp; {_esc(name)}</span>
  <span>Florida Maxima Corporation</span>
  <span>{page_num}</span>
</div>"""


# ── pages ─────────────────────────────────────────────────────────────────────

def _cover(p: dict, pg: int) -> str:
    name  = _esc(p.get("name",""))
    role  = _esc(p.get("role",""))
    today = date.today().strftime("%B %d, %Y").replace(" 0"," ")
    return f"""<div class="page cover">
  <div class="cover-body">
    <div class="cover-tag">Work Style Report</div>
    <div class="cover-title">Understanding<br>How You Work</div>
    <div class="cover-rule"></div>
    <div class="cover-desc">A clear, evidence based view of your natural working style, grounded in
    the TRIAD behavioral model and the BFI-2 personality framework.</div>
  </div>
  <div class="cover-meta">
    <div class="cover-meta-item"><div class="label">Prepared For</div><div class="value">{name}</div></div>
    <div class="cover-meta-item"><div class="label">Role / Job Title</div><div class="value">{role}</div></div>
    <div class="cover-meta-item"><div class="label">Date</div><div class="value">{today}</div></div>
  </div>
  <div class="cover-footer">
    <span>Florida Maxima Corporation &nbsp;|&nbsp; © 2025</span>
    <span>{pg}</span>
  </div>
</div>"""


def _welcome(p: dict, pg: int) -> str:
    name = p.get("name","")
    return f"""<div class="page content">
  <div class="eyebrow">What's in your Work Style Report</div>
  <h2>Welcome</h2>
  <p>This assessment is built to support real workplace decisions, from role fit and team composition to focused
  development. It describes tendencies rather than limits, and is meant to start a conversation rather than settle one.</p>
  <p>This report highlights how you think, act, and interact in professional settings. It helps you understand how your
  patterns influence communication, motivation, problem solving, and collaboration, and how small, intentional
  shifts can lift both your performance and your team's.</p>
  <p>The goal is self awareness with purpose. We want to help you line up your natural tendencies with the work
  environments, roles, and relationships that bring out your best. Everything here is grounded in behavioral science
  and practical workplace research, so you get a clear and usable view of how you work.</p>
  <h2>Personality Work Assessment</h2>
  <p>This part of the report turns key psychological tendencies into practical, work focused insights. Each section shows
  your Preferences and Typical Behavior alongside your Potential Needs.</p>
  <p><strong>Preferences / Typical Behavior.</strong> How you naturally operate when you feel comfortable and engaged.</p>
  <p><strong>Potential Needs / Blind Spots.</strong> The conditions, feedback, and structure that keep your motivation and
  effectiveness high. These patterns show how your personality supports performance, communication, and decision making.</p>
  <p>The assessment looks at both broad personality domains, such as Extraversion, Conscientiousness, and Emotional
  Stability, and the more specific sub facets beneath them. Together they give a complete and finely tuned picture
  of how you tend to work.</p>
  <h2>The TRIAD Model Role Profile</h2>
  <p>The TRIAD Model looks at three foundational dimensions that shape how people approach work and relationships.
  Task Orientation is your preference for structure, organization, and focus on outcomes. Sociability is how you
  connect, communicate, and collaborate. Dominance is how you influence, assert, and take initiative. Together
  they form your Role Profile, a snapshot of your most natural way of contributing on a team.</p>
  {_footer(name, pg)}
</div>"""


def _exec_summary(p: dict, report: dict, pg: int) -> str:
    name    = p.get("name","")
    summary = _esc(report["executive_summary"]["text"])
    t       = report["triad"]
    bridge  = (
        f"Your TRIAD profile shows a {_esc(t['task']['direction_label'].lower())} task orientation "
        f"({t['task']['score']:+.2f}), {_esc(t['sociability']['direction_label'].lower())} sociability "
        f"({t['sociability']['score']:+.2f}), and {_esc(t['dominance']['direction_label'].lower())} dominance "
        f"({t['dominance']['score']:+.2f}). Read alongside your Big Five results, these dimensions tell a "
        f"consistent story about how you engage with work and the people around it."
    )
    return f"""<div class="page content">
  <div class="eyebrow">Executive Summary</div>
  <p class="lead">{summary}</p>
  <div class="callout">
    <div class="callout-label">How the Two Frameworks Connect</div>
    <div class="callout-sub">A combined read across your TRIAD role profile and your Big Five results.</div>
    <p>{bridge}</p>
  </div>
  {_footer(name, pg)}
</div>"""


def _glance(p: dict, report: dict, pg: int) -> str:
    name    = p.get("name","")
    domains = report["domains"]

    rows = ""
    for d in domains:
        lc = _level_cls(d["level"])
        rows += f"""<div class="bar-row">
      <span class="bar-name">{_esc(d['name'])}</span>
      <div class="bar-track">{_bfi_bar_svg(d['score'], d['norm'], w=360, h=28)}</div>
      <div class="bar-right">
        <div class="bar-score">{d['score']:.2f}</div>
        <div class="bar-level bar-level-{lc}">{_esc(d['level'])}</div>
      </div>
    </div>"""

    scale_row = '<div class="scale-row" style="display:flex;justify-content:space-between;padding:4px 0 0;font-size:8pt;color:#8A9BB8"><span>1</span><span>2</span><span>3</span><span>4</span><span>5</span></div>'

    return f"""<div class="page content">
  <div class="eyebrow">Personality Profile at a Glance</div>
  <p class="subtitle">Two views of the same five domains, so you can read the pattern more than one way.</p>

  <div class="glance-card">
    <div class="glance-card-title">Score vs Norm</div>
    {rows}
    {scale_row}
  </div>

  <div class="glance-card">
    <div class="glance-card-title">Profile Shape</div>
    <div class="radar-center">{_radar_svg(domains, size=250)}</div>
  </div>

  {_footer(name, pg)}
</div>"""


def _triad_profile(p: dict, report: dict, pg: int) -> str:
    name  = p.get("name","")
    triad = report["triad"]
    dims  = [("task","Task Orientation"),("sociability","Sociability"),("dominance","Dominance")]

    gauges = ""
    for key, label in dims:
        d = triad[key]
        gauges += f"""<div class="gauge-item">
      {_gauge_svg(d['score'], w=155, h=105)}
      <div class="gauge-dim-name">{_esc(label)}</div>
    </div>"""

    scales = ""
    for key, label in dims:
        d = triad[key]
        scales += f"""<div class="scale-item">
      <div class="scale-name">{_esc(label)}</div>
      <div class="scale-score">{d['score']:+.2f}</div>
      {_scale_bar_svg(d['score'], w=150, h=32)}
    </div>"""

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Role Profile</div>
  <p class="subtitle">Three dimensions of how you contribute on a team, shown two ways.</p>

  <div class="triad-card">
    <div class="triad-card-title">Gauge View</div>
    <div class="gauge-row">{gauges}</div>
  </div>

  <div class="triad-card">
    <div class="triad-card-title">Scale View</div>
    <div class="scale-view-grid">{scales}</div>
  </div>

  {_footer(name, pg)}
</div>"""


def _domain(p: dict, domain: dict, pg: int) -> str:
    name   = p.get("name","")
    dname  = _esc(domain["name"])
    score  = domain["score"]
    norm   = domain["norm"]
    diff   = domain["diff"]
    level  = domain["level"]
    lc     = _level_cls(level)

    facets_html = ""
    for f in domain["facets"]:
        flc = _level_cls(f["level"])
        facets_html += f"""<div class="facet">
      <div class="facet-header">
        <span class="facet-name">{_esc(f['name'])}</span>
        <span class="facet-meta">{f['score']:.2f} / norm {f['norm']:.2f}</span>
        <span class="level-badge badge-{flc}">{_esc(f['level'])}</span>
      </div>
      <div class="facet-bar">{_bfi_bar_svg(f['score'], f['norm'], w=480, h=26)}</div>
      <p class="facet-meaning">{_esc(f['meaning'])}</p>
      <div class="two-col">
        <div><div class="col-label">Preferences</div><p class="col-text">{_esc(f['preferences'])}</p></div>
        <div><div class="col-label">Potential Needs</div><p class="col-text">{_esc(f['potential_needs'])}</p></div>
      </div>
    </div>"""

    return f"""<div class="page content">
  <div class="eyebrow">Personality Work Assessment</div>
  <div class="domain-block">
  <div class="domain-header">
    <div class="domain-title-row">
      <span class="domain-name">{dname}</span>
      <span class="domain-meta">{score:.2f} / norm {norm:.2f} / diff {_diff_str(diff)}</span>
      <span class="level-badge badge-{lc}">{_esc(level)}</span>
    </div>
    <div class="domain-bar">{_bfi_bar_svg(score, norm, w=500, h=28)}</div>
  </div>
  <p class="domain-meaning">{_esc(domain['meaning'])}</p>
  <div class="two-col">
    <div><div class="col-label">Preferences / Typical Behavior</div><p class="col-text">{_esc(domain['preferences'])}</p></div>
    <div><div class="col-label">Potential Needs / Blind Spots</div><p class="col-text">{_esc(domain['potential_needs'])}</p></div>
  </div>
  <div class="facet-rule"><span class="facet-rule-label">Facet Detail</span></div>
  {facets_html}
  </div>
  {_footer(name, pg)}
</div>"""


def _triad_interpretation(p: dict, report: dict, pg: int) -> str:
    name  = p.get("name","")
    triad = report["triad"]
    dims  = [("task","Task Orientation"),("sociability","Sociability"),("dominance","Dominance")]

    blocks = ""
    for key, label in dims:
        d = triad[key]
        blocks += f"""<div class="triad-interp-block">
      <div class="triad-interp-top">
        <span class="triad-interp-score">{d['score']:+.2f}</span>
        <div>
          <div class="triad-interp-name">{_esc(label)}</div>
          <span class="dir-pill" style="display:inline-block;margin-top:5px">{_esc(d['direction_label'])}</span>
        </div>
      </div>
      <div class="triad-interp-bar">{_triad_interp_bar_svg(d['score'], w=500, h=22)}</div>
      <div class="triad-interp-cols">
        <div><div class="col-label">Interpretation</div><p>{_esc(d['interpretation'])}</p></div>
        <div><div class="col-label">Workplace Implications</div><p>{_esc(d['workplace_implications'])}</p></div>
      </div>
    </div>"""

    return f"""<div class="page content">
  <div class="eyebrow">TRIAD Model Role Profile Interpretation</div>
  <p class="triad-ref">This report interprets team role tendencies using the TRIAD Model
  (Driskell, Driskell, Burke &amp; Salas, 2017), which defines three core behavioral
  dimensions that together describe team role behavior.</p>
  {blocks}
  {_footer(name, pg)}
</div>"""


def _recommendations(p: dict, report: dict, pg: int) -> str:
    name = p.get("name","")
    rec  = report["recommendations"]

    def items(lst):
        return "".join(f'<li><span class="bullet">›</span><span>{_esc(i)}</span></li>' for i in lst)

    focus = _esc(rec.get("focus_paragraph",""))

    return f"""<div class="page content">
  <div class="eyebrow">Summary &amp; Recommendations</div>
  <p class="subtitle">Practical guidance that lines up with your TRIAD, domain, and facet patterns.</p>

  <div class="rec-card">
    <div class="rec-card-label rec-label-strengths">Strengths</div>
    <ul class="rec-list">{items(rec['strengths'])}</ul>
  </div>

  <div class="rec-card">
    <div class="rec-card-label rec-label-blind">Blind Spots</div>
    <ul class="rec-list">{items(rec['blind_spots'])}</ul>
  </div>

  <div class="rec-card">
    <div class="rec-card-label rec-label-dev">Development Suggestions</div>
    <ul class="rec-list">{items(rec['development_suggestions'])}</ul>
  </div>

  <div class="focus-box">
    <div class="focus-label">Where to Focus First</div>
    <p class="focus-text">{focus}</p>
  </div>

  {_footer(name, pg)}
</div>"""


# ── entry point ───────────────────────────────────────────────────────────────
def generate_pdf(participant: dict[str, Any], report: dict[str, Any]) -> bytes:
    from weasyprint import HTML, CSS as WpCSS

    font_css = _font_css()
    css      = _css(font_css)

    pg = 1
    pages = []
    pages.append(_cover(participant, pg));              pg += 1
    pages.append(_welcome(participant, pg));            pg += 1
    pages.append(_exec_summary(participant, report, pg)); pg += 1
    pages.append(_glance(participant, report, pg));     pg += 1
    pages.append(_triad_profile(participant, report, pg)); pg += 1
    for domain in report["domains"]:
        pages.append(_domain(participant, domain, pg)); pg += 1
    pages.append(_triad_interpretation(participant, report, pg)); pg += 1
    pages.append(_recommendations(participant, report, pg)); pg += 1

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>{css}</style></head>
<body>{"".join(pages)}</body></html>"""

    return HTML(string=html).write_pdf(
        stylesheets=[WpCSS(string="@page { size: A4; margin: 0; }")]
    )
