"""
Ingestion service: takes a parsed Typeform payload and persists it.

Idempotent on typeform_response_id — Typeform retries webhooks on non-2xx,
so a replay of the same submission must not create a duplicate. If we've
already stored it, we return the existing row instead of erroring.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    AuditLog,
    ProcessingStatus,
    Respondent,
    SurveyResponse,
)


def _log(db: Session, response_id, action: str, status: str, detail: str | None = None) -> None:
    db.add(AuditLog(response_id=response_id, action=action, status=status, detail=detail))


def ingest_response(
    db: Session, raw_payload: dict[str, Any], parsed: dict[str, Any]
) -> tuple[SurveyResponse, bool]:
    """
    Store a survey response. Returns (response, created) where `created` is
    False if this submission was already ingested (idempotent replay).
    """
    response_id = parsed["response_id"]

    existing = db.scalar(
        select(SurveyResponse).where(
            SurveyResponse.typeform_response_id == response_id
        )
    )
    if existing is not None:
        _log(db, existing.id, "ingest", "duplicate", "Replay of existing response ignored")
        db.commit()
        return existing, False

    # Attach/create respondent if we have an email.
    respondent: Respondent | None = None
    email = parsed.get("respondent_email")
    if email:
        respondent = db.scalar(select(Respondent).where(Respondent.email == email))
        if respondent is None:
            respondent = Respondent(email=email, full_name=parsed.get("respondent_name"))
            db.add(respondent)
            db.flush()  # get respondent.id without committing yet

    response = SurveyResponse(
        respondent_id=respondent.id if respondent else None,
        typeform_form_id=parsed.get("form_id"),
        typeform_response_id=response_id,
        typeform_token=parsed.get("token"),
        submitted_at=parsed.get("submitted_at"),
        raw_payload=raw_payload,
        answers=parsed.get("answers", {}),
        status=ProcessingStatus.received,
    )
    db.add(response)
    db.flush()

    _log(db, response.id, "ingest", "ok", f"{len(parsed.get('answers', {}))} answers stored")
    db.commit()
    db.refresh(response)
    return response, True
