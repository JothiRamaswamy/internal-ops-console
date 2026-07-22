# Internal Operations Console

A lightweight, in-house alternative to a Retool-style internal tool platform,
built as a demonstration of what a small team can own themselves using Devin.
It bundles the three internal apps a Series C fintech actually uses into one
console:

- **KYC Review Queue** — triage identity-verification cases from Persona,
  approve / reject / request-more-info with full audit history.
- **Refunds Dashboard** — search payments and issue full/partial refunds with
  role-based limits, idempotency, and provider-failure handling.
- **Feature-Flag Admin** — a mini PostHog-style panel to create flags and manage
  per-environment enable/disable, rollout percentages, and targeting filters.

It also ships **integration source tables** representing the external data
sources this product connects to (Persona for KYC, Stripe for payments). A
**sync/ETL layer** reads those raw vendor rows and normalizes them into the
domain tables (KYC cases + events, payments), so the whole thing runs end-to-end
with realistic seeded data and no external credentials. Feature flags are
console-owned and have no integration source.

> See [`RECOMMENDATION.md`](./RECOMMENDATION.md) for the build-vs-buy analysis
> this repository was created to support.

## Architecture

Monorepo with a clean separation of concerns:

```
internal-ops-console/
├── backend/     FastAPI + SQLAlchemy 2 + Alembic (Python 3.10+)
├── frontend/    React + Vite + TypeScript + Tailwind
└── .env.example
```

- **Database:** PostgreSQL 16.
- **Backend:** FastAPI with a service/domain layer holding all business rules;
  server-side RBAC; money stored as integer minor units; an immutable audit log
  is written for every mutation.
- **Integrations:** two connected sources — Persona (KYC) and Stripe (payments).
  The Integrations tab shows each connector's health, sync freshness, and a
  sample of recently-synced rows.
- **Frontend:** React SPA that talks to the API over a same-origin `/api` proxy
  with cookie sessions. Business logic stays on the server.
- **Auth:** development-only signed-cookie session with a seeded user switcher
  (replace with SSO in production).

| Area | Choice |
| --- | --- |
| DB | PostgreSQL 16 (local install) |
| Backend | FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Frontend | React 18, Vite 5, TypeScript, Tailwind, TanStack Query |
| Tests | pytest (backend), tsc/eslint (frontend) |

## Quick start

Prerequisites: PostgreSQL 16, Python 3.10+, Node 18+ (all installed locally — no
Docker required).

```bash
# 1. Create the database (Postgres must be running locally)
#    macOS (Homebrew):  brew install postgresql@16 && brew services start postgresql@16
#    Ubuntu/Debian:     sudo apt install postgresql && sudo service postgresql start
createdb internal_ops
# Ensure a `postgres` role with password `postgres` exists (matches .env.example),
# or edit DATABASE_URL in .env to match your local Postgres credentials:
psql -d postgres -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || true

# 2. Backend (see backend/README.md for details)
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp ../.env.example ../.env                     # defaults work out of the box
.venv/bin/alembic upgrade head                 # create schema
.venv/bin/python -m app.seed                   # load demo data
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload   # http://localhost:8000

# 3. Frontend (in another terminal)
cd frontend
npm install
npm run dev -- --host 0.0.0.0                  # http://localhost:5173
```

> The `.venv/bin/...` calls run each tool from the virtualenv without needing to
> activate it; if you prefer, run `. .venv/bin/activate` once and drop the
> `.venv/bin/` prefix. `--host 0.0.0.0` binds the servers on all interfaces
> (handy when running in a container/VM); drop it to bind localhost only.

Open http://localhost:5173 and sign in as one of the seeded users to explore the
different roles.

## Seeded users

| Email | Role | Can do |
| --- | --- | --- |
| `admin@example.com` | ADMIN | Everything, incl. production flag writes & unlimited refunds |
| `ops@example.com` | OPS_REVIEWER | KYC decisions, refunds up to $2,000, non-prod flag writes |
| `support@example.com` | SUPPORT_AGENT | Refunds up to $250, read KYC/flags |
| `readonly@example.com` | READ_ONLY | Read-only across the app |

## What's mocked vs. real

Everything is real application logic (state machines, RBAC, idempotency,
optimistic concurrency, auditing). The only mocks are the **external vendors**:
KYC and payment providers are pluggable adapters with deterministic mock
implementations. The `integration_*` tables are the read-only staging source
(raw vendor mirrors); the sync/ETL layer (`app/services/sync_service.py`,
runnable via `python -m app.sync` or `POST /api/integrations/sync`) normalizes
them into the domain tables. Ingestion is sync-only (no webhooks); write-backs
go outbound to the vendor via an adapter and reconcile on the next sync.
Swapping in real providers is an adapter implementation, not a rewrite.

## Testing & checks

```bash
# backend
cd backend
.venv/bin/ruff check app tests
.venv/bin/pytest

# frontend
cd frontend
npm run lint
npm run typecheck
npm run build
```
