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
import re
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
    except json.JSONDecodeError:
        pass

    # Fallback: the model may have added stray text before/after the JSON
    # object despite instructions not to. Extract between the first '{' and
    # the last '}' and try again before giving up - this is a real,
    # non-hypothetical failure mode worth guarding against, since each
    # failed attempt costs a paid API call.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            raise InterpretationError(
                f"Model did not return valid JSON even after stripping stray text: {e}"
            )
    raise InterpretationError("Model did not return valid JSON: no '{' / '}' found in response")


def validate_report(report: dict) -> None:
    # Top level
    for key in ("executive_summary","triad","domains","manager_action_guide","role_cluster_proximity"):
        if key not in report:
            raise InterpretationError(f"Missing top-level key: {key}")

    if not report["executive_summary"].get("text","").strip():
        raise InterpretationError("executive_summary.text is empty")

    # TRIAD employee snapshot — separate synthesis paragraph, checked before
    # the per-dimension fields below
    triad_snapshot = report["triad"].get("employee_snapshot", {}).get("text", "").strip()
    if not triad_snapshot:
        raise InterpretationError("triad.employee_snapshot.text is empty")

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
            missing = DOMAIN_REQUIRED - dom.keys()
            raise InterpretationError(f"Domain '{expected}' missing fields: {missing}")
        facets = dom["facets"]
        exp_facets = DOMAIN_FACETS_DISPLAY[expected]
        if len(facets) != 3:
            raise InterpretationError(f"Domain '{expected}' must have 3 facets, got {len(facets)}")
        for j, fac in enumerate(facets):
            if fac.get("name") != exp_facets[j]:
                raise InterpretationError(f"{expected} facet {j} should be '{exp_facets[j]}'")
            if not FACET_REQUIRED.issubset(fac.keys()):
                missing = FACET_REQUIRED - fac.keys()
                raise InterpretationError(f"Facet '{exp_facets[j]}' missing fields: {missing}")

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
        if not isinstance(s, dict):
            raise InterpretationError(
                f"role_cluster_proximity.strengths item must be a {{title, explanation}} object, got {type(s).__name__}: {s!r}"
            )
        if not s.get("title","").strip() or not s.get("explanation","").strip():
            raise InterpretationError("role_cluster_proximity.strengths item missing title/explanation")
    dev_areas = rcp.get("development_areas", [])
    if not (3 <= len(dev_areas) <= 5):
        raise InterpretationError(f"role_cluster_proximity.development_areas should have 3-5 items, got {len(dev_areas)}")
    for d in dev_areas:
        if not isinstance(d, dict):
            raise InterpretationError(
                f"role_cluster_proximity.development_areas item must be a {{title, explanation}} object, got {type(d).__name__}: {d!r}"
            )
        if not d.get("title","").strip() or not d.get("explanation","").strip():
            raise InterpretationError("role_cluster_proximity.development_areas item missing title/explanation")


# Per-field word caps, calibrated against Jordan Avery's approved 19-page baseline
# (see interpretation_prompt.py for the matching prompt instructions). These are the
# SAME numbers given to the model as hard limits; this is a post-hoc check for when
# the model doesn't comply, since prompt instructions are not enforced automatically.
# Kept a little looser than the prompt limits (roughly +25%) so we only flag genuine
# overflow risk, not every field that ran a few words long.
_LENGTH_BUDGET = {
    "domain.meaning": 70,
    "domain.preferences": 38,
    "domain.potential_needs": 44,
    "facet.meaning": 44,
    "facet.preferences": 25,
    "facet.potential_needs": 28,
    "triad.interpretation": 50,
    "triad.likely_contribution": 56,
    "triad.manager_considerations": 56,
    "mag.narrative": 65,
    "mag.bullet": 18,
    "rcp.explanation": 38,
}

# Section-total budgets, measured directly from Jordan Avery's approved
# baseline PDF (narrative + every bullet in that section, summed). This is
# the check that actually catches real overflow: a narrative and every
# bullet can each individually pass _LENGTH_BUDGET above while the combined
# total for one fixed-height box still runs ~2x over what fits — that's
# exactly what happened with Leadership Summary (14 bullets vs baseline's
# 11, each bullet compliant on its own) before this check existed.
_SECTION_TOTAL_BUDGET = {
    "communication_style": 175,
    "motivators_stressors": 160,
    "delegation_guide": 200,
    "leadership_summary": 220,
}


def _wc(text: str) -> int:
    return len((text or "").split())


def _desplit_em_dash(text: str) -> str:
    """Deterministically remove em dashes from a single string.

    The system prompt already instructs the model never to use em dashes
    (see interpretation_prompt.py), but that's a soft instruction the model
    doesn't reliably follow (12 em dashes measured in a live-generated
    report on 2026-08-06). Word budgets have the self-correcting render
    pipeline as a hard backstop regardless of model compliance; em dashes
    had no equivalent, so this closes that gap the same way: guarantee the
    zero-em-dash rule holds no matter what the model actually writes.

    Rule: split on " — " (or a bare em dash with adjacent whitespace).
    If the text immediately following starts with an uppercase letter,
    treat it as an independent clause and join with ". " (period). Uppercase
    here reliably means a proper noun or a clause that reads as a complete
    sentence on its own (confirmed against all 12 real occurrences found).
    Otherwise it's a parenthetical/appositive fragment, so join with ", ".
    """
    if not text or "\u2014" not in text:
        return text
    parts = re.split(r"\s*\u2014\s*", text)
    out = parts[0]
    for part in parts[1:]:
        if part and part[0].isupper():
            out = out.rstrip(" ,") 
            if not out.endswith((".", "!", "?")):
                out += "."
            out += " " + part
        else:
            out = out.rstrip(" .") + ", " + part
    return out


def strip_em_dashes(value):
    """Recursively apply _desplit_em_dash to every string in a report dict/list."""
    if isinstance(value, str):
        return _desplit_em_dash(value)
    if isinstance(value, dict):
        return {k: strip_em_dashes(v) for k, v in value.items()}
    if isinstance(value, list):
        return [strip_em_dashes(v) for v in value]
    return value


def check_length_budget(report: dict) -> list[str]:
    """Non-fatal check: returns a list of human-readable warnings for any field
    that overshot its word budget enough to risk pushing content onto a phantom
    overflow page. Does not raise — callers should log/print these, not fail on
    them, since a single long field is a quality issue, not a broken response."""
    warnings: list[str] = []

    snapshot_text = report.get("triad", {}).get("employee_snapshot", {}).get("text", "")
    n = _wc(snapshot_text)
    if n > 120:
        warnings.append(f"triad.employee_snapshot.text: {n} words (budget 120)")

    for dim in ("task", "sociability", "dominance"):
        t = report.get("triad", {}).get(dim, {})
        for field, key in (
            ("interpretation", "triad.interpretation"),
            ("likely_contribution", "triad.likely_contribution"),
            ("manager_considerations", "triad.manager_considerations"),
        ):
            n = _wc(t.get(field, ""))
            if n > _LENGTH_BUDGET[key]:
                warnings.append(f"triad.{dim}.{field}: {n} words (budget {_LENGTH_BUDGET[key]})")

    for dom in report.get("domains", []):
        name = dom.get("name", "?")
        for field, key in (
            ("meaning", "domain.meaning"),
            ("preferences", "domain.preferences"),
            ("potential_needs", "domain.potential_needs"),
        ):
            n = _wc(dom.get(field, ""))
            if n > _LENGTH_BUDGET[key]:
                warnings.append(f"domain[{name}].{field}: {n} words (budget {_LENGTH_BUDGET[key]})")
        for fac in dom.get("facets", []):
            fname = fac.get("name", "?")
            for field, key in (
                ("meaning", "facet.meaning"),
                ("preferences", "facet.preferences"),
                ("potential_needs", "facet.potential_needs"),
            ):
                n = _wc(fac.get(field, ""))
                if n > _LENGTH_BUDGET[key]:
                    warnings.append(f"domain[{name}].facet[{fname}].{field}: {n} words (budget {_LENGTH_BUDGET[key]})")

    mag = report.get("manager_action_guide", {})
    _mag_bullet_fields = {
        "communication_style": ["recommendations"],
        "motivators_stressors": ["motivators", "stressors"],
        "delegation_guide": ["best_suited_for", "recommendations"],
        "leadership_summary": ["strengths", "watch_points", "actions"],
    }
    for section, bullet_fields in _mag_bullet_fields.items():
        sec = mag.get(section, {})
        narrative = sec.get("narrative", "")
        n = _wc(narrative)
        if n > _LENGTH_BUDGET["mag.narrative"]:
            warnings.append(f"manager_action_guide.{section}.narrative: {n} words (budget {_LENGTH_BUDGET['mag.narrative']})")

        section_total = n
        bullet_count = 0
        for field in bullet_fields:
            for i, bullet in enumerate(sec.get(field, [])):
                bn = _wc(bullet)
                section_total += bn
                bullet_count += 1
                if bn > _LENGTH_BUDGET["mag.bullet"]:
                    warnings.append(f"manager_action_guide.{section}.{field}[{i}]: {bn} words (budget {_LENGTH_BUDGET['mag.bullet']})")

        budget = _SECTION_TOTAL_BUDGET[section]
        if section_total > budget:
            warnings.append(
                f"manager_action_guide.{section}: SECTION TOTAL {section_total} words across "
                f"narrative + {bullet_count} bullets (budget {budget}) — likely to overflow its box "
                f"even though individual fields may be within their own limits"
            )

    rcp = report.get("role_cluster_proximity", {})
    for field in ("strengths", "development_areas"):
        for i, item in enumerate(rcp.get(field, [])):
            n = _wc(item.get("explanation", ""))
            if n > _LENGTH_BUDGET["rcp.explanation"]:
                warnings.append(f"role_cluster_proximity.{field}[{i}].explanation: {n} words (budget {_LENGTH_BUDGET['rcp.explanation']})")

    return warnings


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
    try:
        validate_report(report)
    except InterpretationError:
        raise
    except Exception as e:
        # Safety net: catches any shape mismatch we didn't specifically
        # anticipate (e.g. a section coming back as the wrong type) and
        # turns it into a clean, readable message instead of a raw
        # traceback. The raw response is already saved by the caller,
        # so nothing is lost even when this fires.
        raise InterpretationError(
            f"Unexpected problem validating the model's response ({type(e).__name__}: {e}). "
            f"Check the saved raw response to see the actual structure returned."
        )
    report = strip_em_dashes(report)
    report = inject_verified_numbers(report, scores)

    length_warnings = check_length_budget(report)
    if length_warnings:
        print(f"[interpretation] WARNING: {len(length_warnings)} field(s) over the length budget "
              f"and at risk of pushing content onto a phantom overflow page:")
        for w in length_warnings:
            print(f"  - {w}")

    return report
