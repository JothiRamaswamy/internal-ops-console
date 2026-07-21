# Backend — Internal Operations Console

FastAPI + SQLAlchemy 2 + Alembic. All business rules live in the service layer
(`app/services/`); routers are thin and permissions are enforced server-side.

## Requirements

- Python 3.10+
- PostgreSQL 16 (via the repo's `docker compose up -d`)

## Setup

```bash
cd backend
python -m venv .venv
. .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configuration is read from a `.env` file at the repo root (see `../.env.example`).
The defaults point at the Dockerized Postgres and work with no edits:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/internal_ops
SESSION_SECRET=dev-secret-change-me
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
```

## Database

```bash
# from repo root: docker compose up -d
alembic upgrade head        # apply migrations
python -m app.seed          # load deterministic demo data (idempotent reset)
```

`app.seed` wipes and reloads the domain tables with a fixed random seed, so the
data is identical on every run.

## Run

```bash
uvicorn app.main:app --reload      # http://localhost:8000
```

- Health check: `GET http://localhost:8000/api/health`
- Interactive docs: `http://localhost:8000/docs`

## Project layout

```
app/
├── main.py            FastAPI app, CORS, error handlers, security headers
├── config.py          Pydantic settings
├── db.py              engine + session dependency
├── deps.py            current-user dependency, client IP
├── security.py        signed-cookie session helpers
├── permissions.py     roles → permissions, refund limits
├── errors.py          AppError + stable error codes
├── schemas.py         request models (Pydantic)
├── serializers.py     response shaping
├── models/            SQLAlchemy models (incl. integration_* tables)
├── services/          business logic: kyc, refund, feature_flag, audit, overview
├── providers/         pluggable KYC & payment adapters (mock + real stubs)
└── routers/           HTTP endpoints
```

## Key business rules

- **KYC:** only `NEEDS_REVIEW` cases are decidable; rejections require a reason;
  terminal cases are immutable; every transition is audited.
- **Refunds:** amount must be > 0 and ≤ remaining refundable; failed/fully
  refunded payments can't be refunded; per-role dollar limits; idempotency keys
  return the original result; money is integer minor units. The mock provider
  fails deterministically when a provider payment ID ends in `FAIL`.
- **Feature flags:** per-environment config `{enabled, rollout_percentage,
  filters[]}`; production writes need an elevated role + a change reason;
  optimistic concurrency via a version check; archived flags are frozen; keys are
  immutable; every change writes a version row and an audit event.

## API overview

```
Auth          /api/auth/{users,login,logout,me}
KYC           /api/kyc, /api/kyc/summary, /api/kyc/{id}[/assign|approve|reject|request-more-info]
Refunds       /api/payments, /api/payments/summary, /api/payments/{id}, /api/payments/{id}/refunds
Feature flags /api/feature-flags (GET list, POST create), /api/feature-flags/{id}[/value|archive|restore]
Audit         /api/audit-events
Overview      /api/overview
Integrations  /api/integrations[/persona|stripe|launchdarkly]
Webhooks      /api/webhooks/kyc/mock
```

Errors use a stable shape:

```json
{ "error": { "code": "REFUND_AMOUNT_EXCEEDED", "message": "...", "details": {} } }
```

## Tests & lint

```bash
. .venv/bin/activate
ruff check app tests
pytest
```

Tests run against a `internal_ops_test` database (auto-created on the same
Postgres instance). Override with `TEST_DATABASE_URL` if needed.
