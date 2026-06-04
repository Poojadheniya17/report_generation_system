# Tripp — Work Style Assessment Engine (Phase 1)

Automated pipeline that turns a Typeform submission into a scored, interpreted,
PDF work-style report. This repo is the **Week 1 foundation**: database, FastAPI
backend, and a secured Typeform webhook.

## Architecture principle

The **ingestion path never depends on scoring.** Raw Typeform payloads land in
`survey_responses` verbatim (source of truth). Scoring runs as a *separate* step
that reads raw answers and writes to `scoring_results`. Consequences:

- A scoring bug can never corrupt raw data.
- Any response can be re-scored once the Excel logic is finalized (`scoring_version`).
- Typeform never retries a submission because scoring failed — we 202 as soon as
  raw data is safely stored.

## Pipeline

```
Typeform → [signed webhook] → verify HMAC → store raw + normalized answers (202)
                                                  ↓ (separate step, Week 1 end)
                                          scoring engine → scoring_results
                                                  ↓ (Week 2)
                                       Claude interpret → ReportLab PDF → S3 → email
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in DATABASE_URL; leave secret blank for curl tests
uvicorn app.main:app --reload
# docs at http://localhost:8000/docs
```

In development the app auto-creates tables on startup. In production, Alembic
owns the schema.

## Webhook security

Typeform signs each request with HMAC-SHA256 over the **raw body**, sent as
`Typeform-Signature: sha256=<base64>`. We verify against the raw bytes
(`app/core/security.py`). Set `TYPEFORM_WEBHOOK_SECRET` to the same value you
enter in the Typeform webhook settings. With the secret set, unsigned or
tampered requests are rejected with 401.

## Tests

```bash
DEBUG=false PYTHONPATH=. python tests/test_ingestion.py
```

Covers: signature accept/reject, tampered-body rejection, answer extraction,
idempotent replay, raw + normalized storage. (Runs on SQLite via a type shim;
production uses Postgres unchanged.)

## Layout

```
app/
  core/      config, HMAC security
  db/        engine + session
  models/    SQLAlchemy ORM (respondents, survey_responses, scoring_results,
             reports, audit_logs)
  services/  typeform parsing, ingestion
  api/       webhook + system/inspection routes
  main.py    FastAPI app
tests/
```

## Wiring up Typeform via API token (no UI clicking)

The client gives you a **Personal Access Token** (Typeform → Settings →
Personal tokens). With it, you configure everything from the command line —
the client never has to touch the webhook UI.

```bash
# 1. Find the form
python -m scripts.setup_webhook list-forms --token tfp_xxx

# 2. Confirm the survey's question refs (verify the 80 questions)
python -m scripts.setup_webhook list-fields --token tfp_xxx --form ABC123

# 3. Register the webhook against your deployed URL (auto-generates a secret)
python -m scripts.setup_webhook create --token tfp_xxx --form ABC123 \
       --url https://your-app.up.railway.app/webhooks/typeform
#   -> prints TYPEFORM_WEBHOOK_SECRET=<value>  (set this on the server)

# inspect / remove
python -m scripts.setup_webhook inspect --token tfp_xxx --form ABC123
python -m scripts.setup_webhook delete  --token tfp_xxx --form ABC123
```

The `create` call sets the URL, enables delivery, and installs the signing
secret in one PUT (per Typeform's API). Copy the printed secret into the
server's `TYPEFORM_WEBHOOK_SECRET` env var so signature verification passes.

> EU-hosted Typeform accounts use `api.eu.typeform.com`; set `base_url` on
> `TypeformClient` accordingly.

## Week 1 status

- [x] Project structure + config
- [x] DB schema (decoupled raw vs scored) + audit log
- [x] FastAPI app + health/inspection routes
- [x] Typeform webhook with HMAC verification + idempotency
- [ ] Scoring engine (TRIAD + Big Five) — **needs `Work_Style_Report_Scoring_Logic.xlsx`**
- [ ] 100+ scoring unit tests validated against Excel
- [ ] Alembic migration for initial schema
```
