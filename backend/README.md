# Backend — Internal Operations Console

FastAPI + SQLAlchemy 2 + Alembic. All business rules live in the service layer
(`app/services/`); routers are thin and permissions are enforced server-side.

## Requirements

- Python 3.10+
- PostgreSQL 16 running locally (no Docker required)

Install and start Postgres, then create the database:

```bash
# macOS (Homebrew):  brew install postgresql@16 && brew services start postgresql@16
# Ubuntu/Debian:     sudo apt install postgresql && sudo service postgresql start
createdb internal_ops
```

## Setup

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

> The examples call each tool via `.venv/bin/...` so no activation is needed.
> If you prefer, activate once with `. .venv/bin/activate` (Windows:
> `.venv\Scripts\activate`) and drop the `.venv/bin/` prefix from the commands
> below.

Configuration is read from a `.env` file at the repo root (see `../.env.example`).
The defaults assume a local Postgres with a `postgres`/`postgres` role; edit
`DATABASE_URL` to match your own credentials if they differ:

```
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/internal_ops
SESSION_SECRET=dev-secret-change-me
APP_ENV=development
CORS_ORIGINS=http://localhost:5173
```

## Database

```bash
# ensure the local Postgres is running and `internal_ops` exists (createdb internal_ops)
.venv/bin/alembic upgrade head        # apply migrations
.venv/bin/python -m app.seed          # load deterministic demo data (idempotent reset)
```

`app.seed` wipes and reloads with a fixed random seed, so the data is identical
on every run. It models the real flow: it populates the `integration_*` staging
tables (raw vendor mirrors), then runs the sync/ETL layer to normalize them into
the domain tables (`kyc_cases` + events, `payments`); operator-owned data (KYC
decisions, in-console refunds) and console-owned feature flags are layered on
after.

Run the sync on its own (idempotent — re-runnable for backfill/reconciliation):

```bash
.venv/bin/python -m app.sync          # integration_* source tables -> normalized domain
```

It's also exposed at `POST /api/integrations/sync` (ADMIN / OPS_REVIEWER), which
the Integrations tab's "Sync now" button calls.

## Run

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # http://localhost:8000
```

`--host 0.0.0.0` binds all interfaces (useful inside a container/VM); omit it to
bind localhost only.

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
├── services/          business logic: kyc, refund, feature_flag, audit, overview, sync (ETL)
│                       (audit is written for every mutation; there is no audit read API)
├── sync.py            CLI entrypoint for the integration sync/ETL
├── providers/         Persona KYC + Stripe payment adapters + normalization (mock + real stubs)
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
Overview      /api/overview
Integrations  /api/integrations (health), /api/integrations/{persona|stripe} (recent synced rows)
Sync (ETL)    /api/integrations/sync   (POST; ADMIN / OPS_REVIEWER)
```

Errors use a stable shape:

```json
{ "error": { "code": "REFUND_AMOUNT_EXCEEDED", "message": "...", "details": {} } }
```

## Tests & lint

```bash
.venv/bin/ruff check app tests
.venv/bin/pytest
```

Tests run against a `internal_ops_test` database (auto-created on the same
Postgres instance). Override with `TEST_DATABASE_URL` if needed.
