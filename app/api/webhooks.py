"""Typeform webhook endpoint — fast synchronous ingest, heavy work backgrounded.

Typeform expects a prompt response and may retry on a slow one. Everything
up through creating the Report row is fast (local DB writes only) and stays
synchronous, so the request returns almost instantly. Scoring, the live
Claude call, and PDF generation can take 10-30s combined, so those run via
FastAPI's BackgroundTasks *after* the response is already sent.

Important: the background function does NOT reuse the request's `db`
session. That session is tied to the request lifecycle and its cleanup
timing relative to background tasks isn't something to rely on — using it
inside a background task risks a "session already closed" error that only
shows up intermittently. The background function opens its own session via
SessionLocal() and closes it explicitly when done.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_signature
from app.db.session import SessionLocal, get_db
from app.models.models import AuditLog, ProcessingStatus, Report, SurveyResponse
from app.services.ingestion import ingest_response
from app.services.typeform import parse_typeform_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


def _get_model_call():
    """
    Build the real model call lazily (not at import time) so this module can
    still be imported without ANTHROPIC_API_KEY set (tests, tooling). Uses
    model_client.make_anthropic_model_call() rather than hand-rolling the
    Anthropic call here — that's the one place INTERPRETATION_MODEL and
    INTERPRETATION_MAX_TOKENS actually get read from the environment, and it
    correctly concatenates every text block in the response instead of only
    reading the first one.
    """
    from app.services.model_client import make_anthropic_model_call
    return make_anthropic_model_call(
        api_key=settings.anthropic_api_key,
        model=settings.interpretation_model,
        max_tokens=settings.interpretation_max_tokens,
    )


def process_submission(response_id) -> None:
    """
    Runs in the background, after the webhook has already returned 202 to
    Typeform. Owns its own DB session start to finish. Any failure here
    marks the response as failed with an AuditLog entry rather than
    crashing silently — there's no request left to raise an HTTPException
    to by this point.
    """
    db = SessionLocal()
    try:
        response = db.get(SurveyResponse, response_id)
        if response is None:
            return  # shouldn't happen; nothing sensible to do without a row

        rpt = db.query(Report).filter(Report.response_id == response_id).first()
        parsed_answers = response.answers or {}

        # 2. Score
        from app.services.scoring import score_all
        triad_answers: dict[int, float] = {}
        bfi_answers: dict[int, float] = {}
        for k, v in parsed_answers.items():
            if not isinstance(k, str) or v is None:
                continue
            if k.startswith("TRIAD_"):
                try:
                    triad_answers[int(k.split("_", 1)[1])] = float(v)
                except (ValueError, IndexError):
                    pass
            elif k.startswith("BFI_"):
                try:
                    bfi_answers[int(k.split("_", 1)[1])] = float(v)
                except (ValueError, IndexError):
                    pass
        scores = score_all(triad_answers, bfi_answers, triad_already_centered=False)

        response.status = ProcessingStatus.scored
        db.add(AuditLog(response_id=response_id, action="score", status="ok"))
        db.commit()

        # 3. Interpret
        from app.services.interpretation import interpret
        # "Name" is an answered question on the live form (confirmed from a
        # real submission) — not a hidden field like the original form
        # layout suggested. Respondent.full_name may still be None if this
        # response predates this fix or the field gets renamed again, so
        # fall back to the answered value directly.
        respondent_name = (
            (response.respondent.full_name if response.respondent else None)
            or parsed_answers.get("Name")
            or ""
        )
        participant = {
            "name": respondent_name,
            "role": parsed_answers.get("Role") or "",
        }
        report = interpret(participant, scores, _get_model_call())

        response.status = ProcessingStatus.interpreted
        rpt.interpretation = json.dumps(report)
        db.add(AuditLog(response_id=response_id, action="interpret", status="ok"))
        db.commit()

        # 4. Generate PDF
        from app.services.pdf_generator import generate_pdf
        pdf_bytes = generate_pdf(participant, report)

        # 5. Save PDF — R2 in production, local disk automatically as a
        # fallback if R2 isn't configured (see app/services/storage.py)
        from app.services.storage import save_pdf
        safe_name = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in participant["name"]
        ) or "unnamed"
        storage_key = f"{safe_name}_{response_id}.pdf"
        storage_ref = save_pdf(storage_key, pdf_bytes)

        # 6. Update the Report row
        rpt.storage_url = storage_ref
        rpt.generated_at = datetime.now(timezone.utc)
        response.status = ProcessingStatus.report_ready
        db.add(AuditLog(response_id=response_id, action="generate_pdf", status="ok",
                         detail=f"{round(len(pdf_bytes) / 1024, 1)} KB"))
        db.commit()

    except Exception as e:
        db.rollback()
        response = db.get(SurveyResponse, response_id)
        if response is not None:
            response.status = ProcessingStatus.failed
        db.add(AuditLog(response_id=response_id, action="background_processing",
                         status="error", detail=str(e)[:2000]))
        db.commit()
        raise
    finally:
        db.close()


@router.post("/typeform", status_code=status.HTTP_202_ACCEPTED)
async def typeform_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    typeform_signature: str | None = Header(default=None, alias="Typeform-Signature"),
):
    """
    Receive a Typeform submission. Verifies + ingests synchronously (fast),
    then hands scoring/interpretation/PDF generation off to a background
    task so Typeform gets its 202 back immediately instead of waiting
    10-30s for the full pipeline.
    """
    raw_body = await request.body()

    if settings.typeform_webhook_secret:
        if not verify_signature(raw_body, settings.typeform_webhook_secret, typeform_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Typeform signature",
            )

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Malformed JSON body")

    parsed = parse_typeform_payload(payload)
    if not parsed.get("response_id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload missing form_response token/response_id",
        )

    # 1. Ingest — fast, local DB write only, commits immediately.
    response, created = ingest_response(db, payload, parsed)

    if not created:
        return {
            "status": "duplicate_ignored",
            "response_id": str(response.id),
        }

    # Create the Report row now so the background task has one to update.
    rpt = Report(response_id=response.id)
    db.add(rpt)
    db.commit()

    # Everything from here (scoring, live AI call, PDF generation) happens
    # after this function returns — Typeform gets its 202 right away.
    background_tasks.add_task(process_submission, response.id)

    return {
        "status": "accepted",
        "response_id": str(response.id),
    }
