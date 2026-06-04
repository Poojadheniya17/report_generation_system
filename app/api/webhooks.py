"""Typeform webhook endpoint."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_signature
from app.db.session import get_db
from app.services.ingestion import ingest_response
from app.services.typeform import parse_typeform_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


@router.post("/typeform", status_code=status.HTTP_202_ACCEPTED)
async def typeform_webhook(
    request: Request,
    db: Session = Depends(get_db),
    typeform_signature: str | None = Header(default=None, alias="Typeform-Signature"),
):
    """
    Receive a Typeform submission.

    We read the RAW body for two reasons:
      1. Signature verification must run on the exact bytes Typeform signed.
      2. We store the raw payload verbatim as the source of truth.

    Returns 202 immediately after persisting raw data. Scoring/interpretation
    run as separate steps (so a scoring failure never causes Typeform to retry
    and re-deliver an already-stored submission).
    """
    raw_body = await request.body()

    # In production the secret is required. In dev (no secret set) we allow
    # unsigned requests so you can test with curl, but log loudly.
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

    response, created = ingest_response(db, payload, parsed)

    return {
        "status": "received" if created else "duplicate_ignored",
        "response_id": str(response.id),
        "answers_stored": len(parsed.get("answers", {})),
    }
