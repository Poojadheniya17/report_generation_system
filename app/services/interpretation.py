"""
Interpretation service: scored data -> AI -> validated report JSON.

Pipeline:
    scoring.score_all() -> interpret() -> validated report dict -> pdf_generator.generate_pdf()

Key design:
- TRIAD direction_label computed here (not by AI), injected into user message
- BFI-2 level comes from scoring engine, injected into user message
- AI writes only prose fields
- After AI call: parse -> validate -> overwrite all numeric fields with engine values
- focus_paragraph validated as non-empty and distinct from development_suggestions
"""
from __future__ import annotations

import json
from typing import Any

from app.services.interpretation_prompt import (
    DISPLAY_NAMES,
    SYSTEM_PROMPT,
    triad_direction_label,
)

DOMAIN_ORDER = [
    "Extraversion",
    "Agreeableness",
    "Conscientiousness",
    "Negative Emotionality",
    "Open-Mindedness",
]
DOMAIN_FACETS_DISPLAY = {
    "Extraversion": ["Sociability", "Assertiveness", "Energy Level"],
    "Agreeableness": ["Compassion", "Respectfulness", "Trust"],
    "Conscientiousness": ["Organization", "Productiveness", "Responsibility"],
    "Negative Emotionality": ["Anxiety", "Depression", "Emotional Volatility"],
    "Open-Mindedness": ["Intellectual Curiosity", "Aesthetic Sensitivity", "Creative Imagination"],
}

DOMAIN_REQUIRED = {"name","score","norm","diff","level","meaning","preferences","potential_needs","facets"}
FACET_REQUIRED  = {"name","score","norm","diff","level","meaning","preferences","potential_needs"}
TRIAD_REQUIRED  = {"score","direction_label","interpretation","workplace_implications"}


class InterpretationError(RuntimeError):
    pass


def build_user_message(participant: dict[str, Any], scores: dict[str, Any]) -> str:
    triad = scores["triad"]
    payload = {
        "participant": {
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
    for d in scores["bfi2"]["domains"]:
        dom = {
            "name": DISPLAY_NAMES[d["name"]],
            "score": round(d["score"], 2),
            "norm": d["norm"],
            "diff": round(d["diff"], 2),
            "level": d["level"],
            "facets": [
                {
                    "name": DISPLAY_NAMES[f["name"]],
                    "score": round(f["score"], 2),
                    "norm": f["norm"],
                    "diff": round(f["diff"], 2),
                    "level": f["level"],
                }
                for f in d["facets"]
            ],
        }
        payload["domains"].append(dom)

    return (
        "Generate the Work Style Report for the following participant. "
        "IMPORTANT: Use second person (you/your) in ALL fields — never third person. "
        "Use direction_label values VERBATIM for TRIAD dimensions. "
        "Use the score/norm/diff/level values exactly as provided for BFI-2. "
        "Write all prose fields: interpretation, meaning, preferences, potential_needs, "
        "executive_summary, recommendations (including a unique focus_paragraph).\n\n"
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
    for key in ("executive_summary", "triad", "domains", "recommendations"):
        if key not in report:
            raise InterpretationError(f"Missing top-level key: {key}")

    if not report["executive_summary"].get("text", "").strip():
        raise InterpretationError("executive_summary.text is empty")

    # triad
    for dim in ("task", "sociability", "dominance"):
        t = report["triad"].get(dim)
        if not t:
            raise InterpretationError(f"Missing triad.{dim}")
        for fld in TRIAD_REQUIRED:
            if fld not in t or str(t[fld]).strip() == "":
                raise InterpretationError(f"triad.{dim}.{fld} missing/empty")

    # domains
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

    # recommendations — now includes focus_paragraph
    rec = report["recommendations"]
    counts = {"strengths": (3, 6), "blind_spots": (2, 4), "development_suggestions": (3, 5)}
    for field, (lo, hi) in counts.items():
        items = rec.get(field)
        if not isinstance(items, list):
            raise InterpretationError(f"recommendations.{field} must be a list")
        if not (lo <= len(items) <= hi):
            raise InterpretationError(f"recommendations.{field} must have {lo}–{hi} items, got {len(items)}")

    focus = rec.get("focus_paragraph", "").strip()
    if not focus or len(focus) < 50:
        raise InterpretationError("recommendations.focus_paragraph is missing or too short")
    # Ensure it's not literally copying a dev suggestion
    for suggestion in rec.get("development_suggestions", []):
        if suggestion.strip().lower() == focus.lower():
            raise InterpretationError("focus_paragraph must not duplicate a development_suggestion verbatim")


def inject_verified_numbers(report: dict, scores: dict[str, Any]) -> dict:
    """Overwrite all numeric fields with our engine values. Prose is left as AI wrote it."""
    triad = scores["triad"]
    for dim in ("task", "sociability", "dominance"):
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
