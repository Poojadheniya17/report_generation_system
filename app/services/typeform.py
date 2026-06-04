"""
Parse a Typeform webhook payload into a normalized answers map.

Typeform's `form_response.answers` is a list where each item has a `field`
(with `ref`, `id`, `type`) and a typed value key (`number`, `choice`,
`choices`, `text`, `boolean`, etc.). We flatten this into:

    { field_ref: value }

keyed by the field's `ref` when present (refs are stable and you control
them in the form builder), falling back to the field `id`.

We deliberately do NOT score here. We only normalize so the scoring engine
gets a clean { ref -> value } dict. The full payload is stored verbatim
elsewhere as the source of truth.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any


def _extract_answer_value(answer: dict[str, Any]) -> Any:
    """Pull the typed value out of one Typeform answer object."""
    atype = answer.get("type")
    # Direct scalar types
    if atype in ("number", "text", "email", "boolean", "date", "url", "phone_number"):
        return answer.get(atype)
    # Single choice -> use label (or ref if you prefer stable values)
    if atype == "choice":
        choice = answer.get("choice", {})
        return choice.get("label") if "label" in choice else choice.get("ref")
    # Multiple choice
    if atype == "choices":
        choices = answer.get("choices", {})
        return choices.get("labels") or choices.get("refs")
    # Opinion-scale / rating come through as "number" but guard anyway
    if "number" in answer:
        return answer["number"]
    return None


def parse_typeform_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """
    Returns a dict with:
      form_id, response_id, token, submitted_at (datetime|None),
      hidden (dict), answers ({field_ref: value}), respondent_email, respondent_name
    """
    form_response = payload.get("form_response", {})

    answers_map: dict[str, Any] = {}
    email: str | None = None
    name: str | None = None

    for answer in form_response.get("answers", []):
        field = answer.get("field", {})
        key = field.get("ref") or field.get("id")
        if not key:
            continue
        value = _extract_answer_value(answer)
        answers_map[key] = value

        if answer.get("type") == "email" and email is None:
            email = value

    # Typeform "hidden fields" often carry email/name passed via the survey link.
    hidden = form_response.get("hidden", {}) or {}
    email = email or hidden.get("email")
    name = hidden.get("name") or hidden.get("full_name")

    submitted_raw = form_response.get("submitted_at")
    submitted_at: datetime | None = None
    if submitted_raw:
        try:
            submitted_at = datetime.fromisoformat(submitted_raw.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            submitted_at = None

    return {
        "form_id": form_response.get("form_id"),
        "response_id": form_response.get("token") or form_response.get("response_id"),
        "token": form_response.get("token"),
        "submitted_at": submitted_at,
        "hidden": hidden,
        "answers": answers_map,
        "respondent_email": email,
        "respondent_name": name,
    }
