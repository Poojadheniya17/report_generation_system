"""
Interpretation service — Manager Edition.
Pipeline: scoring.score_all() -> interpret() -> validated report dict -> generate_pdf()

Changes from participant version:
- TRIAD fields: adds likely_contribution + manager_considerations
- recommendations replaced by manager_action_guide
- Validation updated for new schema
- direction_label still computed by code, injected as data
"""
from __future__ import annotations

import json
from typing import Any

from app.services.interpretation_prompt import (
    DISPLAY_NAMES,
    SYSTEM_PROMPT,
    triad_direction_label,
)
from app.services.pdf_generator import ROLE_CLUSTERS, _compute_role_distances

DOMAIN_ORDER = [
    "Extraversion", "Agreeableness", "Conscientiousness",
    "Negative Emotionality", "Open-Mindedness",
]
DOMAIN_FACETS_DISPLAY = {
    "Extraversion":         ["Sociability", "Assertiveness", "Energy Level"],
    "Agreeableness":        ["Compassion", "Respectfulness", "Trust"],
    "Conscientiousness":    ["Organization", "Productiveness", "Responsibility"],
    "Negative Emotionality":["Anxiety", "Depression", "Emotional Volatility"],
    "Open-Mindedness":      ["Intellectual Curiosity", "Aesthetic Sensitivity", "Creative Imagination"],
}

DOMAIN_REQUIRED = {"name","score","norm","diff","level","meaning","preferences","potential_needs","facets"}
FACET_REQUIRED  = {"name","score","norm","diff","level","meaning","preferences","potential_needs"}
TRIAD_REQUIRED  = {"score","direction_label","interpretation","likely_contribution","manager_considerations"}

MAG_SECTIONS = {
    "communication_style":  {"narrative", "recommendations"},
    "motivators_stressors": {"narrative", "motivators", "stressors"},
    "delegation_guide":     {"narrative", "best_suited_for", "recommendations"},
    "leadership_summary":   {"narrative", "strengths", "watch_points", "actions"},
}


class InterpretationError(RuntimeError):
    pass


def build_user_message(participant: dict[str, Any], scores: dict[str, Any]) -> str:
    triad = scores["triad"]
    payload = {
        "employee": {
            "name": participant.get("name", ""),
            "role": participant.get("role", ""),
        },
        "triad": {
            "task": {
                "score": round(triad["task"]["score"], 2),
                "direction_label": triad_direction_label(triad["task"]["score"]),
            },
            "sociability": {
                "score": round(triad["sociability"]["score"], 2),
                "direction_label": triad_direction_label(triad["sociability"]["score"]),
            },
            "dominance": {
                "score": round(triad["dominance"]["score"], 2),
                "direction_label": triad_direction_label(triad["dominance"]["score"]),
            },
        },
        "domains": [],
    }

    # Role cluster proximity data - top 3 nearest clusters with their TRIAD
    # signature and similarity, so the model can write a grounded, specific
    # interpretation instead of a generic description of the cluster.
    task_s = triad["task"]["score"]
    soc_s  = triad["sociability"]["score"]
    dom_s  = triad["dominance"]["score"]
    distances = _compute_role_distances(task_s, soc_s, dom_s)
    sig = {name: (tc, sc2, dc) for name, tc, sc2, dc in ROLE_CLUSTERS}
    payload["role_cluster_proximity"] = {
        "employee_scores": {
            "task": round(task_s, 2),
            "sociability": round(soc_s, 2),
            "dominance": round(dom_s, 2),
        },
        "top_matches": [
            {
                "role": role,
                "similarity_pct": round(sim * 100),
                "fit_label": fit,
                "triad_signature": {
                    "task": sig[role][0],
                    "sociability": sig[role][1],
                    "dominance": sig[role][2],
                },
            }
            for role, sim, fit in distances[:3]
        ],
    }
    for d in scores["bfi2"]["domains"]:
        dom = {
            "name":  DISPLAY_NAMES[d["name"]],
            "score": round(d["score"], 2),
            "norm":  d["norm"],
            "diff":  round(d["diff"], 2),
            "level": d["level"],
            "facets": [
                {
                    "name":  DISPLAY_NAMES[f["name"]],
                    "score": round(f["score"], 2),
                    "norm":  f["norm"],
                    "diff":  round(f["diff"], 2),
                    "level": f["level"],
                }
                for f in d["facets"]
            ],
        }
        payload["domains"].append(dom)

    return (
        "Generate the Manager Edition Work Style Report for the following employee. "
        "Use THIRD PERSON (the employee / they / their) throughout ALL fields. "
        "Use direction_label values VERBATIM for TRIAD. "
        "Use score/norm/diff/level values exactly as provided for BFI-2. "
        "Write all prose fields and fully populate the manager_action_guide section.\n\n"
        + json.dumps(payload, indent=2)
    )


def parse_model_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise InterpretationError(f"Model did not return valid JSON: {e}")


def validate_report(report: dict) -> None:
    # Top level
    for key in ("executive_summary","triad","domains","manager_action_guide","role_cluster_proximity"):
        if key not in report:
            raise InterpretationError(f"Missing top-level key: {key}")

    if not report["executive_summary"].get("text","").strip():
        raise InterpretationError("executive_summary.text is empty")

    # TRIAD — now has 5 required fields
    for dim in ("task","sociability","dominance"):
        t = report["triad"].get(dim)
        if not t:
            raise InterpretationError(f"Missing triad.{dim}")
        for fld in TRIAD_REQUIRED:
            if fld not in t or str(t[fld]).strip() == "":
                raise InterpretationError(f"triad.{dim}.{fld} missing/empty")

    # Domains
    domains = report["domains"]
    if len(domains) != 5:
        raise InterpretationError(f"Expected 5 domains, got {len(domains)}")
    for i, dom in enumerate(domains):
        expected = DOMAIN_ORDER[i]
        if dom.get("name") != expected:
            raise InterpretationError(f"Domain {i} should be '{expected}', got '{dom.get('name')}'")
        if not DOMAIN_REQUIRED.issubset(dom.keys()):
            raise InterpretationError(f"Domain '{expected}' missing fields")
        facets = dom["facets"]
        exp_facets = DOMAIN_FACETS_DISPLAY[expected]
        if len(facets) != 3:
            raise InterpretationError(f"Domain '{expected}' must have 3 facets, got {len(facets)}")
        for j, fac in enumerate(facets):
            if fac.get("name") != exp_facets[j]:
                raise InterpretationError(f"{expected} facet {j} should be '{exp_facets[j]}'")
            if not FACET_REQUIRED.issubset(fac.keys()):
                raise InterpretationError(f"Facet '{exp_facets[j]}' missing fields")

    # Manager Action Guide
    mag = report["manager_action_guide"]
    for section, required_fields in MAG_SECTIONS.items():
        if section not in mag:
            raise InterpretationError(f"manager_action_guide.{section} missing")
        sec = mag[section]
        for fld in required_fields:
            if fld not in sec:
                raise InterpretationError(f"manager_action_guide.{section}.{fld} missing")
            val = sec[fld]
            if isinstance(val, str) and not val.strip():
                raise InterpretationError(f"manager_action_guide.{section}.{fld} is empty")
            if isinstance(val, list) and len(val) == 0:
                raise InterpretationError(f"manager_action_guide.{section}.{fld} has no items")

    # Role Cluster Proximity
    rcp = report["role_cluster_proximity"]
    if not rcp.get("business_interpretation","").strip():
        raise InterpretationError("role_cluster_proximity.business_interpretation is empty")
    word_count = len(rcp["business_interpretation"].split())
    if not (60 <= word_count <= 180):
        raise InterpretationError(
            f"role_cluster_proximity.business_interpretation should be ~75-150 words, got {word_count}"
        )
    strengths = rcp.get("strengths", [])
    if not (4 <= len(strengths) <= 6):
        raise InterpretationError(f"role_cluster_proximity.strengths should have 4-6 items, got {len(strengths)}")
    for s in strengths:
        if not s.get("title","").strip() or not s.get("explanation","").strip():
            raise InterpretationError("role_cluster_proximity.strengths item missing title/explanation")
    dev_areas = rcp.get("development_areas", [])
    if not (3 <= len(dev_areas) <= 5):
        raise InterpretationError(f"role_cluster_proximity.development_areas should have 3-5 items, got {len(dev_areas)}")
    for d in dev_areas:
        if not d.get("title","").strip() or not d.get("explanation","").strip():
            raise InterpretationError("role_cluster_proximity.development_areas item missing title/explanation")


def inject_verified_numbers(report: dict, scores: dict[str, Any]) -> dict:
    """Overwrite numeric fields with engine values. Prose is left as AI wrote it."""
    triad = scores["triad"]
    for dim in ("task","sociability","dominance"):
        report["triad"][dim]["score"] = round(triad[dim]["score"], 2)
        report["triad"][dim]["direction_label"] = triad_direction_label(triad[dim]["score"])

    score_by_display: dict[str, dict] = {}
    for d in scores["bfi2"]["domains"]:
        score_by_display[DISPLAY_NAMES[d["name"]]] = d
        for f in d["facets"]:
            score_by_display[DISPLAY_NAMES[f["name"]]] = f

    for dom in report["domains"]:
        src = score_by_display.get(dom["name"])
        if src:
            dom["score"] = round(src["score"], 2)
            dom["norm"]  = src["norm"]
            dom["diff"]  = round(src["diff"], 2)
            dom["level"] = src["level"]
        for fac in dom["facets"]:
            fsrc = score_by_display.get(fac["name"])
            if fsrc:
                fac["score"] = round(fsrc["score"], 2)
                fac["norm"]  = fsrc["norm"]
                fac["diff"]  = round(fsrc["diff"], 2)
                fac["level"] = fsrc["level"]
    return report


def interpret(
    participant: dict[str, Any],
    scores: dict[str, Any],
    model_call,
) -> dict:
    """
    participant: {"name", "role"}
    scores:      output of scoring.score_all()
    model_call:  callable(system_prompt, user_message) -> str
    Returns validated, number-verified report dict.
    """
    user_message = build_user_message(participant, scores)
    raw = model_call(SYSTEM_PROMPT, user_message)
    report = parse_model_json(raw)
    validate_report(report)
    report = inject_verified_numbers(report, scores)
    return report
