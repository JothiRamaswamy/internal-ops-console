# Frontend — Internal Operations Console

React 18 + Vite + TypeScript + Tailwind, with TanStack Query for data fetching.
The UI is a dense, neutral internal-tool console (not a marketing site): sortable
tables, status badges, confirmation dialogs, toasts, empty/loading/error states,
and query-string-driven filters.

## Requirements

- Node 18+
- The backend running on `http://localhost:8000` (see `../backend/README.md`)

## Setup & run

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

The dev server proxies `/api` to the backend (configurable via
`VITE_API_BASE_URL`, see `.env.example`), so cookies are same-origin and no CORS
config is needed in development.

Sign in with a seeded user (e.g. `admin@example.com`) — the login screen and the
top-right switcher let you jump between roles to see how permissions change what
you can do.

## Scripts

```bash
npm run dev         # start dev server
npm run build       # type-check (tsc -b) + production build to dist/
npm run preview     # preview the production build
npm run lint        # eslint
npm run typecheck   # tsc --noEmit
```

## Layout

```
src/
├── main.tsx            providers (QueryClient, Auth, Toast, Router)
├── App.tsx             routes + auth gate
├── api/                fetch client (stable error shape) + typed query fns
├── auth/               AuthContext (dev user switcher, permission checks)
├── components/         AppShell, UserSwitcher, Dialog, Toast, shared UI
├── lib/format.ts       money / date formatting helpers
├── types.ts            shared API types
└── pages/              Overview, KYC (list/detail), Refunds (list/detail),
                        Feature flags (list/detail), Audit, Integrations
```

## Notes

- **No business logic in components** — the client calls the API and renders the
  result; all rules (limits, transitions, concurrency) are enforced server-side.
- Permission-gated actions are also disabled in the UI for clarity, but the
  server is the source of truth.
- Money is received and sent as integer minor units and formatted for display.
