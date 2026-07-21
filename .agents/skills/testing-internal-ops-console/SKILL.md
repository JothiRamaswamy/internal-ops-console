---
name: Testing the Internal Operations Console
description: How to set up, run, and E2E-test the internal-ops-console monorepo (FastAPI + Vite/React + Postgres), including seeded users, RBAC rules, and where the key business rules live.
---

# Internal Operations Console — testing guide

Monorepo at repo root: `backend/` (FastAPI :8000), `frontend/` (Vite/React :5173), Postgres 16 via Docker :5432.

## Setup
```bash
docker compose up -d                       # Postgres
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head && python -m app.seed  # seed is idempotent/deterministic
uvicorn app.main:app --host 0.0.0.0 --port 8000
cd frontend && npm install && npm run dev    # http://localhost:5173 (proxies /api → :8000)
```
Health check: `http://localhost:8000/api/health`.

**Gotcha:** if the frontend shows a Vite import-resolution overlay (e.g. `Failed to resolve import "@/App"`), it's a stale Vite cache. Kill node/vite, `rm -rf frontend/node_modules/.vite`, restart `npm run dev`.

## Auth
No passwords — dev-only signed-cookie session with a top-right user switcher. Seeded users:
- `admin@example.com` ADMIN — everything (prod flag writes, unlimited refunds)
- `ops@example.com` OPS_REVIEWER — KYC review, refunds ≤ $2,000, non-prod flag writes (NO prod)
- `support@example.com` SUPPORT_AGENT — refunds ≤ $250, feature_flag:read only. **No `kyc:read`** — KYC queue is empty for support (spec text claiming support reads KYC is inaccurate vs code).
- `readonly@example.com` READ_ONLY — read KYC/refunds/flags/audit; no writes.

Ground truth for RBAC: `backend/app/permissions.py` (`ROLE_PERMISSIONS`, `REFUND_LIMIT_MINOR`).

## Key business rules (all enforced server-side; UI disabling is supplementary)
- **KYC** (`kyc_service.py`): decisions only from NEEDS_REVIEW; reject requires a reason from a fixed set. Detail page disables Approve/Reject/Assign for non-reviewers + shows a view-only banner.
- **Refunds** (`refund_service.py`): refundable from SUCCEEDED/PARTIALLY_REFUNDED; partial vs full recalculates status; role limit enforced (support 25000 minor = $250). Provider IDs ending `FAIL` deterministically fail — seed `pay_007` = `pi_mock_0007_FAIL` (MOCK_PROVIDER). A failed refund consumes no balance and payment stays SUCCEEDED.
- **Feature flags** (`feature_flag_service.py`): new flags start disabled everywhere at v1/0%. Rollout slider disabled while flag is off. PRODUCTION writes require `feature_flag:write_prod` + a non-empty reason (UI "Confirm production change" dialog; Apply disabled until reason typed). Non-prod needs `feature_flag:write_nonprod`. Optimistic concurrency via `expected_version` (v increments each save). List shows `On · N%`.

## Testing tips
- Good full-balance SUCCEEDED payments for refund tests: `pay_018` ($1,999), `pay_030` ($1,999, use for support-limit test).
- Feature flag create form: key/description/owner/comma-separated tags; lands on detail page.
- Audit tab supports entity-type filter (KycCase/Refund/FeatureFlag) and per-row Details showing before/after JSON.
- Integrations tab: 3 mock sources (Persona/Stripe/LaunchDarkly) with sub-tab data tables.

## Devin Secrets Needed
None — all auth is local dev seeded users; no external API keys required.
