"""
Database models for the Work Style Assessment engine.

Design principle: the ingestion path NEVER depends on scoring. Raw Typeform
data lands in `survey_responses` untouched. Scoring runs as a separate step
that reads raw answers and writes to `scoring_results`. A scoring bug can
never corrupt the source-of-truth raw data, and we can re-score any response
at any time once the Excel logic is finalized.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

# Cross-dialect JSON column: real JSONB (with indexing/operators) on Postgres
# in production, plain JSON on SQLite for local dev — same models.py works
# against both without a separate test-only monkeypatch.
_JSON = JSON().with_variant(JSONB, "postgresql")


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class ProcessingStatus(str, enum.Enum):
    """Lifecycle of a single survey submission through the pipeline."""
    received = "received"        # raw payload stored
    scored = "scored"            # TRIAD + Big Five computed
    interpreted = "interpreted"  # Claude narrative generated (Week 2)
    report_ready = "report_ready"  # PDF generated + stored (Week 2)
    delivered = "delivered"      # emailed / available in portal
    failed = "failed"            # something broke; see audit_logs


class Respondent(Base):
    """A person who completed the assessment (a portal user in Week 4)."""
    __tablename__ = "respondents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    email: Mapped[str | None] = mapped_column(String(320), index=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="respondent")


class SurveyResponse(Base):
    """
    Raw Typeform submission. `raw_payload` is the complete webhook body,
    stored verbatim. `answers` is a normalized question_ref -> value map
    extracted from it for convenient scoring, but the raw payload remains
    the source of truth.
    """
    __tablename__ = "survey_responses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    respondent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("respondents.id"), nullable=True, index=True
    )

    # Typeform's own identifiers — used for idempotency (de-duping replays).
    typeform_form_id: Mapped[str | None] = mapped_column(String(64), index=True)
    typeform_response_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    typeform_token: Mapped[str | None] = mapped_column(String(128), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    raw_payload: Mapped[dict] = mapped_column(_JSON, nullable=False)
    answers: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)
    # Whatever Typeform hidden fields came through, whatever they're named.
    # Generic by design so nothing needs to know a specific field name
    # (e.g. assessment_id) ahead of time — if Tripp adds one, it just shows
    # up here automatically, no code change or coordination needed.
    hidden_fields: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)

    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, name="processing_status"),
        default=ProcessingStatus.received,
        nullable=False,
        index=True,
    )
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    respondent: Mapped["Respondent | None"] = relationship(back_populates="responses")
    scoring_result: Mapped["ScoringResult | None"] = relationship(
        back_populates="response", uselist=False
    )
    report: Mapped["Report | None"] = relationship(back_populates="response", uselist=False)


class ScoringResult(Base):
    """
    Computed scores. Kept in JSONB rather than rigid columns because the
    scoring spec (13 TRIAD clusters, 5 dimensions x 3 facets) is detailed
    and may be refined against the Excel. Shape:

      triad:    {"task_orientation": float, "sociability": float,
                 "dominance": float, "cluster": str}
      big_five: {"extraversion": {"score": float, "facets": {...},
                                  "norm": float}, ...}
    """
    __tablename__ = "scoring_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_responses.id"), unique=True, nullable=False, index=True
    )

    triad: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)
    big_five: Mapped[dict] = mapped_column(_JSON, nullable=False, default=dict)

    # Version of the scoring logic used — lets us re-score and compare safely.
    scoring_version: Mapped[str] = mapped_column(String(32), default="0.1.0")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    response: Mapped["SurveyResponse"] = relationship(back_populates="scoring_result")


class Report(Base):
    """Generated PDF metadata (Week 2 fills storage_url)."""
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("survey_responses.id"), unique=True, nullable=False, index=True
    )
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    response: Mapped["SurveyResponse"] = relationship(back_populates="report")


class AuditLog(Base):
    """Append-only record of every pipeline action — required for the audit trail."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=_uuid)
    response_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("survey_responses.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


Index("ix_audit_response_action", AuditLog.response_id, AuditLog.action)
