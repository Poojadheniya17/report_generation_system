"""
Scoring engine: raw survey answers -> TRIAD + BFI-2 scores.

Faithful to Copy_of_Work_Style_Report_Scoring_Logic.xlsx. Produces output
shaped to feed directly into the AI interpretation prompt (AI_JSON_Interpreation
.docx): triad {task,sociability,dominance} and bfi2 domains/facets each with
score, norm, diff, level.

Two scales are in play (confirmed from the workbook's raw data):
  - TRIAD items: a centered scale (workbook stores -3..+3). Dimension score =
    plain mean of its 6 items. No reverse-scoring.
  - BFI-2 items: 1..5 Likert. Reverse items recoded (6 - x). Facet = mean of
    its 4 items; domain = mean of its 3 facets.

The TRIAD scale is configurable (TRIAD_SCALE) so that if the live Typeform
turns out to use 1..5 with a different centering, it's a one-line change.

Cluster assignment (13 TRIAD roles) is implemented but OFF by default, because
the client's current report spec interprets the three TRIAD scores directly
rather than assigning a named role. Enable via assign_cluster=True once
confirmed with the client.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from app.services.scoring_key import (
    BFI2_KEY,
    DOMAIN_TO_FACETS,
    DOMAINS,
    FACET_TO_DOMAIN,
    LEVEL_THRESHOLD,
    NORMS,
    TRIAD_CLUSTERS,
    TRIAD_ITEMS,
)

BFI_LIKERT_MAX = 5  # reverse score = (max+1) - x = 6 - x

# TRIAD scale conversion. Typeform forces a 1-7 opinion scale; the client's
# model uses a centered -3..+3 scale (so the three dimensions can later be
# placed in 3D space for Euclidean role-cluster matching). The conversion is
# x - 4  (1->-3, 4->0, 7->+3). Verified consistent with the workbook's stored
# TRIAD values (integers within -3..+3). If the live form's scale changes,
# adjust TRIAD_RAW_OFFSET only.
TRIAD_RAW_OFFSET = 4  # subtract from a 1-7 answer to center it


def convert_triad_scale(raw_1to7: float) -> float:
    """Convert a single TRIAD answer from Typeform's 1-7 to the centered -3..+3."""
    return float(raw_1to7) - TRIAD_RAW_OFFSET


class ScoringError(ValueError):
    """Raised when required answers are missing or malformed."""


def _level_from_diff(diff: float) -> str:
    """BFI2_Scoring *_Level rule: |diff|<0.25 -> Average, else High/Low."""
    if abs(diff) < LEVEL_THRESHOLD:
        return "Average"
    return "High" if diff > 0 else "Low"


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def _facet_items() -> dict[str, list[tuple[int, bool]]]:
    """facet -> list of (item_number, reverse) from the BFI-2 key."""
    out: dict[str, list[tuple[int, bool]]] = {}
    for item_no, facet, reverse in BFI2_KEY:
        out.setdefault(facet, []).append((item_no, reverse))
    return out


_FACET_ITEMS = _facet_items()


# --- BFI-2 -----------------------------------------------------------------
def score_bfi2(bfi_answers: dict[int, float]) -> dict:
    """
    bfi_answers: {1..60: value(1..5)}.
    Returns {"domains": [ {name, score, norm, diff, level, facets:[...]} ]}
    in canonical report order, matching the interpretation doc's schema.
    """
    missing = [i for i in range(1, 61) if i not in bfi_answers]
    if missing:
        raise ScoringError(f"Missing BFI-2 answers for items: {missing}")

    # 1. facet scores (mean of 4 items, reverse where flagged)
    facet_scores: dict[str, float] = {}
    for facet, items in _FACET_ITEMS.items():
        vals = []
        for item_no, reverse in items:
            v = float(bfi_answers[item_no])
            vals.append((BFI_LIKERT_MAX + 1) - v if reverse else v)
        facet_scores[facet] = _mean(vals)

    # 2. domain scores (mean of 3 facets)
    domain_scores: dict[str, float] = {}
    for domain, facets in DOMAIN_TO_FACETS.items():
        domain_scores[domain] = _mean([facet_scores[f] for f in facets])

    # 3. assemble with norms/diffs/levels in canonical order
    domains_out = []
    for domain in DOMAINS:
        d_score = domain_scores[domain]
        d_norm = NORMS[domain]
        d_diff = d_score - d_norm
        facets_out = []
        for facet in DOMAIN_TO_FACETS[domain]:
            f_score = facet_scores[facet]
            f_norm = NORMS[facet]
            f_diff = f_score - f_norm
            facets_out.append(
                {
                    "name": facet,
                    "score": round(f_score, 4),
                    "norm": f_norm,
                    "diff": round(f_diff, 4),
                    "level": _level_from_diff(f_diff),
                }
            )
        domains_out.append(
            {
                "name": domain,
                "score": round(d_score, 4),
                "norm": d_norm,
                "diff": round(d_diff, 4),
                "level": _level_from_diff(d_diff),
                "facets": facets_out,
            }
        )
    return {"domains": domains_out}


# --- TRIAD -----------------------------------------------------------------
def score_triad(
    triad_answers: dict[int, float],
    assign_cluster: bool = False,
    already_centered: bool = True,
) -> dict:
    """
    triad_answers: {1..18: value}. Items 1-6 Task, 7-12 Sociability,
    13-18 Dominance. Each dimension = mean of its 6 items.

    already_centered:
      - True  (default): answers are already on the -3..+3 scale (e.g. the
        client's workbook fixtures).
      - False: answers are raw 1-7 from the live Typeform; each is converted
        via convert_triad_scale() before averaging.

    If assign_cluster=True, also returns the nearest of the 13 role clusters
    (Euclidean distance in Task/Soc/Dom space). OFF by default.
    """
    missing = [i for i in range(1, 19) if i not in triad_answers]
    if missing:
        raise ScoringError(f"Missing TRIAD answers for items: {missing}")

    def val(i: int) -> float:
        v = float(triad_answers[i])
        return v if already_centered else convert_triad_scale(v)

    scores = {
        dim: _mean([val(i) for i in items])
        for dim, items in TRIAD_ITEMS.items()
    }
    out = {
        "task": {"score": round(scores["Task"], 4)},
        "sociability": {"score": round(scores["Sociability"], 4)},
        "dominance": {"score": round(scores["Dominance"], 4)},
    }

    if assign_cluster:
        t, s, d = scores["Task"], scores["Sociability"], scores["Dominance"]
        best_role, best_dist = None, math.inf
        for role, ct, cs, cd in TRIAD_CLUSTERS:
            dist = math.dist((t, s, d), (ct, cs, cd))
            if dist < best_dist:
                best_role, best_dist = role, dist
        out["cluster"] = {"role": best_role, "distance": round(best_dist, 4)}

    return out


# --- combined --------------------------------------------------------------
def score_all(
    triad_answers: dict[int, float],
    bfi_answers: dict[int, float],
    assign_cluster: bool = False,
    triad_already_centered: bool = True,
) -> dict:
    """Full score object ready to feed the interpretation prompt.

    triad_already_centered: set False when passing raw 1-7 answers straight
    from the live Typeform webhook (the pipeline converts them to -3..+3).
    """
    return {
        "triad": score_triad(
            triad_answers,
            assign_cluster=assign_cluster,
            already_centered=triad_already_centered,
        ),
        "bfi2": score_bfi2(bfi_answers),
        "scoring_version": "1.0.0",
    }
