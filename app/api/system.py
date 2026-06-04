"""Health check + read-only inspection routes (useful during dev/QA)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import SurveyResponse

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/responses")
def list_responses(db: Session = Depends(get_db), limit: int = 20):
    rows = db.scalars(
        select(SurveyResponse).order_by(SurveyResponse.received_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "typeform_response_id": r.typeform_response_id,
            "status": r.status.value,
            "answer_count": len(r.answers or {}),
            "received_at": r.received_at.isoformat() if r.received_at else None,
        }
        for r in rows
    ]


@router.get("/responses/{response_id}")
def get_response(response_id: str, db: Session = Depends(get_db)):
    r = db.get(SurveyResponse, response_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Response not found")
    return {
        "id": str(r.id),
        "status": r.status.value,
        "answers": r.answers,
        "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
    }
