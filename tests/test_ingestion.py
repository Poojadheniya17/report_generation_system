"""
End-to-end test of the ingestion flow against SQLite.

We swap JSONB->JSON and PG UUID->String at import time so the same models
run on SQLite in CI/sandbox. Production uses Postgres with the real types.
"""
import json
import os
import sys

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///./test_tripp.db"
os.environ["TYPEFORM_WEBHOOK_SECRET"] = "test_secret_123"
os.environ["ENVIRONMENT"] = "development"

# --- SQLite compatibility shim for Postgres types -------------------------
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import JSON, String, types


class _UUIDShim(types.TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return str(value) if value is not None else None

    def process_result_value(self, value, dialect):
        import uuid as _u
        return _u.UUID(value) if value is not None else None


pg.JSONB = JSON
pg.UUID = lambda *a, **k: _UUIDShim()
# --------------------------------------------------------------------------

if os.path.exists("test_tripp.db"):
    os.remove("test_tripp.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import compute_signature  # noqa: E402
from app.db.session import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import models  # noqa: E402,F401

Base.metadata.create_all(bind=engine)

client = TestClient(app)

SECRET = "test_secret_123"

# A realistic (trimmed) Typeform webhook payload.
PAYLOAD = {
    "event_id": "evt_01",
    "event_type": "form_response",
    "form_response": {
        "form_id": "AbCdEf",
        "token": "resp_token_0001",
        "submitted_at": "2026-06-04T10:15:00Z",
        "hidden": {"email": "jane@example.com", "name": "Jane Doe"},
        "answers": [
            {"type": "number", "number": 2, "field": {"ref": "triad_q1", "type": "opinion_scale"}},
            {"type": "number", "number": 3, "field": {"ref": "triad_q2", "type": "opinion_scale"}},
            {"type": "number", "number": 5, "field": {"ref": "bfi_q1", "type": "opinion_scale"}},
            {"type": "email", "email": "jane@example.com", "field": {"ref": "email", "type": "email"}},
        ],
    },
}


def _post(body: dict, with_sig: bool = True):
    raw = json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if with_sig:
        headers["Typeform-Signature"] = compute_signature(raw, SECRET)
    return client.post("/webhooks/typeform", content=raw, headers=headers)


def run():
    results = []

    # 1. Health
    r = client.get("/health")
    results.append(("health endpoint", r.status_code == 200 and r.json()["status"] == "ok"))

    # 2. Reject missing signature
    r = _post(PAYLOAD, with_sig=False)
    results.append(("rejects missing signature", r.status_code == 401))

    # 3. Reject tampered body (sign correct body, then change it)
    raw = json.dumps(PAYLOAD).encode()
    sig = compute_signature(raw, SECRET)
    tampered = json.dumps({**PAYLOAD, "event_id": "evt_TAMPERED"}).encode()
    r = client.post("/webhooks/typeform", content=tampered,
                    headers={"Typeform-Signature": sig, "Content-Type": "application/json"})
    results.append(("rejects tampered body", r.status_code == 401))

    # 4. Accept valid signed submission
    r = _post(PAYLOAD)
    ok = r.status_code == 202 and r.json()["status"] == "received"
    results.append(("accepts valid submission", ok))
    results.append(("extracts answers", r.json().get("answers_stored") == 4))

    # 5. Idempotency — replay same response_id
    r2 = _post(PAYLOAD)
    results.append(("idempotent replay ignored", r2.json()["status"] == "duplicate_ignored"))

    # 6. Only one row exists
    r = client.get("/responses")
    results.append(("exactly one stored response", len(r.json()) == 1))

    # 7. Raw payload + normalized answers both stored
    resp_id = r.json()[0]["id"]
    detail = client.get(f"/responses/{resp_id}").json()
    results.append(("normalized answers present", detail["answers"].get("triad_q1") == 2))

    print("\n  TRIPP INGESTION — TEST RESULTS")
    print("  " + "=" * 40)
    passed = 0
    for name, ok in results:
        mark = "PASS" if ok else "FAIL"
        print(f"  [{mark}] {name}")
        passed += ok
    print("  " + "=" * 40)
    print(f"  {passed}/{len(results)} passed\n")
    return passed == len(results)


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
