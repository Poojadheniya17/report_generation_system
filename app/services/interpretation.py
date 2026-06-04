"""
Interpretation service: scored data -> Claude -> validated report JSON.

Pipeline position:
    scoring.score_all()  ->  interpret()  ->  report JSON (fills the template)

The client's prompt demands strict, complete, consistently-structured JSON.
We do not trust the model blindly: after the call we PARSE and VALIDATE the
output against the exact schema (5 domains in order, 15 facets in order,
required fields present, recommendation item counts within range). If the
model returns something malformed, validate_report() raises with a precise
reason so the pipeline can retry or flag rather than ship a broken report.

The numeric fields (score/norm/diff/level) come from OUR verified scoring
engine, not the model — we inject them, so the model only writes prose. This
guarantees the report's numbers always match the scoring engine exactly even
if the model would have echoed them imperfectly.
"""
from __future__ import annotations

import json
from typing import Any

from app.services.interpretation_prompt import DISPLAY_NAMES, SYSTEM_PROMPT

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
    "Open-Mindedness": [
        "Intellectual Curiosity",
        "Aesthetic Sensitivity",
        "Creative Imagination",
    ],
}

DOMAIN_REQUIRED = {"name", "score", "norm", "diff", "level", "meaning", "preferences", "potential_needs", "facets"}
FACET_REQUIRED = {"name", "score", "norm", "diff", "level", "meaning", "preferences", "potential_needs"}


class InterpretationError(RuntimeError):
    pass


# --- build the user message from scores ------------------------------------
def build_user_message(participant: dict[str, Any], scores: dict[str, Any]) -> str:
    """
    Compose the participant-data message the model interprets. We hand it the
    numbers (with display names) and ask it to fill the prose fields. Sending
    the computed score/norm/diff/level means the model interprets consistent,
    correct data rather than recomputing anything.
    """
    triad = scores["triad"]
    payload = {
        "participant": {
            "name": participant.get("name", ""),
            "role": participant.get("role", ""),
        },
        "triad": {
            "task": {"score": round(triad["task"]["score"], 2)},
            "sociability": {"score": round(triad["sociability"]["score"], 2)},
            "dominance": {"score": round(triad["dominance"]["score"], 2)},
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
        "Generate the Work Style Report for the following participant data. "
        "Use these exact score, norm, diff, and level values in the output; "
        "write the interpretation, meaning, preferences, potential_needs, "
        "executive_summary, and recommendations fields.\n\n"
        + json.dumps(payload, indent=2)
    )


# --- parse + validate ------------------------------------------------------
def parse_model_json(raw_text: str) -> dict:
    """Extract the JSON object from the model's text, tolerating stray fences."""
    text = raw_text.strip()
    if text.startswith("```"):
        # strip ```json ... ``` if the model added them despite instructions
        text = text.split("```", 2)[1] if text.count("```") >= 2 else text
        if text.startswith("json"):
            text = text[4:]
        text = text.strip().rstrip("`").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise InterpretationError(f"Model did not return valid JSON: {e}")


def validate_report(report: dict) -> None:
    """Validate against the client's exact schema. Raises on any violation."""
    # top-level keys
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
        for fld in ("score", "interpretation", "workplace_implications"):
            if fld not in t or str(t[fld]).strip() == "":
                raise InterpretationError(f"triad.{dim}.{fld} missing/empty")

    # domains: exactly 5, correct order
    domains = report["domains"]
    if len(domains) != 5:
        raise InterpretationError(f"Expected 5 domains, got {len(domains)}")
    for i, dom in enumerate(domains):
        expected = DOMAIN_ORDER[i]
        if dom.get("name") != expected:
            raise InterpretationError(f"Domain {i} should be '{expected}', got '{dom.get('name')}'")
        if not DOMAIN_REQUIRED.issubset(dom.keys()):
            raise InterpretationError(f"Domain '{expected}' missing fields: {DOMAIN_REQUIRED - set(dom.keys())}")
        facets = dom["facets"]
        exp_facets = DOMAIN_FACETS_DISPLAY[expected]
        if len(facets) != 3:
            raise InterpretationError(f"Domain '{expected}' must have 3 facets, got {len(facets)}")
        for j, fac in enumerate(facets):
            if fac.get("name") != exp_facets[j]:
                raise InterpretationError(
                    f"{expected} facet {j} should be '{exp_facets[j]}', got '{fac.get('name')}'"
                )
            if not FACET_REQUIRED.issubset(fac.keys()):
                raise InterpretationError(
                    f"Facet '{exp_facets[j]}' missing fields: {FACET_REQUIRED - set(fac.keys())}"
                )

    # recommendations: count ranges per the client's spec
    rec = report["recommendations"]
    counts = {"strengths": (3, 6), "blind_spots": (2, 4), "development_suggestions": (3, 5)}
    for field, (lo, hi) in counts.items():
        items = rec.get(field)
        if not isinstance(items, list):
            raise InterpretationError(f"recommendations.{field} must be a list")
        if not (lo <= len(items) <= hi):
            raise InterpretationError(
                f"recommendations.{field} must have {lo}-{hi} items, got {len(items)}"
            )


def inject_verified_numbers(report: dict, scores: dict[str, Any]) -> dict:
    """
    Overwrite the model's numeric fields with our verified engine values, so
    the report's numbers are guaranteed correct regardless of what the model
    echoed. Prose fields are left as the model wrote them.
    """
    triad = scores["triad"]
    for dim in ("task", "sociability", "dominance"):
        report["triad"][dim]["score"] = round(triad[dim]["score"], 2)

    score_by_display = {}
    for d in scores["bfi2"]["domains"]:
        score_by_display[DISPLAY_NAMES[d["name"]]] = d
        for f in d["facets"]:
            score_by_display[DISPLAY_NAMES[f["name"]]] = f

    for dom in report["domains"]:
        src = score_by_display.get(dom["name"])
        if src:
            dom["score"], dom["norm"], dom["diff"], dom["level"] = (
                round(src["score"], 2), src["norm"], round(src["diff"], 2), src["level"],
            )
        for fac in dom["facets"]:
            fsrc = score_by_display.get(fac["name"])
            if fsrc:
                fac["score"], fac["norm"], fac["diff"], fac["level"] = (
                    round(fsrc["score"], 2), fsrc["norm"], round(fsrc["diff"], 2), fsrc["level"],
                )
    return report


# --- orchestration (model call is injected for testability) ----------------
def interpret(
    participant: dict[str, Any],
    scores: dict[str, Any],
    model_call,
) -> dict:
    """
    participant: {"name", "role"}
    scores: output of scoring.score_all()
    model_call: callable(system_prompt: str, user_message: str) -> str
                (the raw model text). Injected so this is unit-testable without
                a live API key, and so the API client can be swapped freely.

    Returns the validated, number-verified report dict.
    """
    user_message = build_user_message(participant, scores)
    raw = model_call(SYSTEM_PROMPT, user_message)
    report = parse_model_json(raw)
    validate_report(report)
    report = inject_verified_numbers(report, scores)
    return report
