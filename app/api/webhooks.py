"""Typeform webhook endpoint — full pipeline: ingest -> score -> interpret -> PDF."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_signature
from app.db.session import get_db
from app.models.models import AuditLog, ProcessingStatus, Report
from app.services.ingestion import ingest_response
from app.services.typeform import parse_typeform_payload

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()

# Output directory for generated PDFs (M4 will replace with S3/cloud storage)
PDF_OUTPUT_DIR = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp/reports"))
PDF_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _model_call(system_prompt: str, user_message: str) -> str:
    """Call Anthropic claude-sonnet to generate interpretation JSON."""
    import anthropic
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text


@router.post("/typeform", status_code=status.HTTP_202_ACCEPTED)
async def typeform_webhook(
    request: Request,
    db: Session = Depends(get_db),
    typeform_signature: str | None = Header(default=None, alias="Typeform-Signature"),
):
    """
    Receive a Typeform submission and run the full pipeline:
    1. Verify signature
    2. Ingest raw payload (idempotent)
    3. Score (TRIAD + BFI-2)
    4. AI interpretation
    5. Generate PDF
    6. Save PDF path to Report.storage_url
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

    # 1. Ingest
    response, created = ingest_response(db, payload, parsed)

    if not created:
        return {
            "status": "duplicate_ignored",
            "response_id": str(response.id),
        }

    # Create the Report row now, tied to this response, so every stage below
    # has a real row to update. Without this, storage_url can never be saved
    # (there'd be nothing in the `reports` table to attach it to), which
    # breaks report retrieval later — a portal can't list/download from an
    # empty table.
    rpt = Report(response_id=response.id)
    db.add(rpt)
    db.commit()
    db.refresh(rpt)

    # 2. Score
    from app.services.scoring import score_all
    answers = parsed.get("answers", {})
    # Real Typeform refs are "TRIAD_1".."TRIAD_18" and "BFI_1".."BFI_60" —
    # score_triad()/score_bfi2() need bare integer keys (1..18 / 1..60), so
    # convert rather than just filter-and-pass-through.
    triad_answers: dict[int, float] = {}
    bfi_answers: dict[int, float] = {}
    for k, v in answers.items():
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
    scores = score_all(triad_answers, bfi_answers)

    response.status = ProcessingStatus.scored
    db.add(AuditLog(response_id=response.id, action="score", status="ok"))
    db.commit()

    # 3. Interpret
    from app.services.interpretation import interpret
    participant = {
        "name": parsed.get("respondent_name") or "",
        "role": parsed.get("respondent_role") or "",
    }
    report = interpret(participant, scores, _model_call)

    response.status = ProcessingStatus.interpreted
    rpt.interpretation = json.dumps(report)
    db.add(AuditLog(response_id=response.id, action="interpret", status="ok"))
    db.commit()

    # 4. Generate PDF
    from app.services.pdf_generator import generate_pdf
    pdf_bytes = generate_pdf(participant, report)

    # 5. Save PDF
    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in participant["name"]) or "unnamed"
    pdf_path = PDF_OUTPUT_DIR / f"{safe_name}_{response.id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # 6. Update the Report row directly — no re-query, no risk of a stale
    # or mistyped filter column.
    from datetime import datetime, timezone
    rpt.storage_url = str(pdf_path)
    rpt.generated_at = datetime.now(timezone.utc)
    response.status = ProcessingStatus.report_ready
    db.add(AuditLog(response_id=response.id, action="generate_pdf", status="ok",
                     detail=f"{round(len(pdf_bytes) / 1024, 1)} KB"))
    db.commit()

    return {
        "status": "processed",
        "response_id": str(response.id),
        "pdf_path": str(pdf_path),
        "pdf_size_kb": round(len(pdf_bytes) / 1024, 1),
    }
