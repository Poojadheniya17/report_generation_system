"""
Login portal — Tripp-only. Basic and functional per the original scope:
login, view all generated reports, download them. No branding, no user
management, no styling beyond readable defaults.

Auth is a single shared password (not per-user accounts) since there's only
one person using this. Session is a signed cookie via Starlette's
SessionMiddleware (added in main.py) — no separate session table needed.
"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.models import Report, SurveyResponse

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


def require_login(request: Request) -> None:
    """Raises via redirect (handled by the route itself) if not authenticated.
    Kept as a plain check rather than a dependency-that-raises so each route
    can redirect to /login with a clean 302 instead of a raw 401 page."""
    return request.session.get("authenticated") is True


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    if request.session.get("authenticated"):
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(request: Request, password: str = Form(...)):
    settings = get_settings()
    if password == settings.portal_password:
        request.session["authenticated"] = True
        return RedirectResponse("/dashboard", status_code=302)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Incorrect password."}, status_code=401
    )


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=302)


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    # Left join so responses without a Report row yet (still processing)
    # still show up in the list, matching the ProcessingStatus lifecycle.
    stmt = (
        select(SurveyResponse, Report)
        .outerjoin(Report, Report.response_id == SurveyResponse.id)
        .order_by(SurveyResponse.received_at.desc())
    )
    rows = []
    for response, report in db.execute(stmt).all():
        rows.append({
            # "respondent_name" comes from a hidden field, not an answered
            # question — it's captured on the Respondent row at ingest time
            # (via parsed["respondent_name"]), not stored on
            # SurveyResponse.answers directly. Role IS an answered question
            # (ref="Role"), so it's read straight off response.answers.
            "name": response.respondent.full_name if response.respondent else None,
            "role": (response.answers or {}).get("Role"),
            "submitted_at": response.submitted_at or response.received_at,
            "status": response.status,
            "report_id": report.id if report else None,
            "has_pdf": bool(report and report.storage_url),
        })

    return templates.TemplateResponse(request, "dashboard.html", {"rows": rows})


@router.get("/reports/{report_id}/download")
def download_report(report_id: str, request: Request, db: Session = Depends(get_db)):
    if not require_login(request):
        return RedirectResponse("/login", status_code=302)

    # report_id arrives as a raw string from the URL path. SQLAlchemy's
    # Uuid column type expects an actual uuid.UUID instance for db.get() —
    # passing the string straight through raises a confusing AttributeError
    # deep in the SQL layer instead of a clean 404. Convert explicitly, and
    # treat a malformed/tampered URL as "not found" rather than a 500.
    try:
        report_uuid = uuid.UUID(report_id)
    except ValueError:
        return HTMLResponse("Report not found.", status_code=404)

    report = db.get(Report, report_uuid)
    if not report or not report.storage_url:
        return HTMLResponse("Report not found.", status_code=404)

    path = Path(report.storage_url)
    if not path.exists():
        return HTMLResponse("Report file is missing on disk.", status_code=404)

    return FileResponse(path, media_type="application/pdf", filename=path.name)
