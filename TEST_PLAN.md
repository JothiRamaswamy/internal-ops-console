# Test Plan — Internal Operations Console (PR #1)

Env: Postgres (docker) + backend :8000 + frontend :5173, all confirmed up. Auth via seeded user switcher (top-right). Sign in as admin@example.com to start.

Code refs grounding the plan:
- Feature flags UI: `frontend/src/pages/FeatureFlagDetailPage.tsx` (EnvEditor toggle L92-107, rollout slider L116-127 disabled unless enabled, filters L133-197, prod confirm Dialog L398-444 with reason-required button `disabled={!reason.trim()}` L409). List/create: `FeatureFlagsPage.tsx` (New flag btn L98-104 `disabled={!canCreate}`, "On · N%" L28).
- Prod reason enforced server-side: `feature_flag_service.set_flag_value` L168-171; optimistic version L188-193.
- KYC decisions: `KycDetailPage.tsx` (Approve/Reject btns `disabled={!canReview||!isDecidable}` L155-168; reject reason dropdown L331-342). Reject reason enforced server-side `kyc_service.reject_case` L137-142.
- Refund: `PaymentDetailPage.tsx` (Issue refund L106-116, partial mode L271-289, limit warning L328-332). Server limit `refund_service` L103-109 (support=25000c). Provider FAIL: `providers/payment.py` L36 (id ends "FAIL"); seed payment `pay_007` = `pi_mock_0007_FAIL`, MOCK provider, SUCCEEDED.
- RBAC: `permissions.py` ROLE_PERMISSIONS; support lacks kyc:review, readonly lacks all writes.

## Test 1 — App shell + Overview (smoke)
Steps: Load app as admin. Confirm left nav shows: Overview, KYC, Refunds, Feature Flags, Audit, Integrations. On Overview, confirm summary cards render with numbers and a recent-audit list renders.
Pass: all 6 nav items present; cards show numeric values (not blank/error); recent audit list non-empty.
Fail if: any tab missing, blank page, or error/console errors.

## Test 2 — KYC decision + persistence + audit + RBAC
Steps (admin): KYC tab → filter to NEEDS_REVIEW → open a NEEDS_REVIEW case.
2a Approve: click Approve → Confirm approval. 
  Pass: toast "Case approved", status badge → APPROVED, Decision history gains "Kyc Case Approved by <admin>". Reload persists APPROVED.
2b Reject (different case): open another NEEDS_REVIEW case → Reject → pick a reason → Confirm rejection.
  Pass: toast "Case rejected", status → REJECTED, decision_reason shows chosen reason, history gains reject event.
2c Reject-reason enforcement (adversarial): verified via server rule (reason must be in allowed set L137). UI dropdown always sends a valid reason; note that empty/invalid reason is rejected by backend. Will confirm valid reason persists (proxy for enforcement).
2d Audit: Audit tab → confirm KYC_CASE_APPROVED and KYC_CASE_REJECTED events for the two cases appear at top.
2e RBAC: switch to readonly@example.com → open a NEEDS_REVIEW case → confirm Approve/Reject/Assign/Request-more-info buttons are DISABLED and amber banner "Your role can view this case but cannot make review decisions." shows.
Fail if: decision not persisted after reload; audit missing; readonly buttons enabled.

## Test 3 — Refund partial + status + role limit + provider failure
Steps (admin): Refunds tab → open a SUCCEEDED payment with full balance.
3a Partial refund: Issue refund → Partial → enter amount < total (e.g. half) → reason → Confirm.
  Pass: toast "Refund issued successfully", status → PARTIALLY_REFUNDED, Remaining refundable decreased by refunded amount, Refunded total increased, refund row appears SUCCEEDED with provider ref. Reload persists.
3b Role limit (adversarial, support@example.com): open a SUCCEEDED payment with remaining > $250 → Issue refund → Partial → enter e.g. $300 → observe inline red warning "This exceeds your refund limit of $250.00" AND if attempted, backend returns REFUND_LIMIT_EXCEEDED error toast. Then a refund ≤ $250 succeeds.
  Pass: >$250 blocked with clear limit error; ≤$250 succeeds.
3c Provider failure (optional): open payment `pi_mock_0007_FAIL` (search provider id / order). Issue small refund → Confirm.
  Pass: toast "Refund failed: Provider declined the refund (simulated failure)"; refund row status FAILED with failure reason; payment status stays SUCCEEDED (no balance consumed).
Fail if: limit not enforced; status/balance math wrong; FAIL payment shows success.

## Test 4 — Feature Flags (KEY FEATURE): create, configure dev, prod gating, RBAC, version
Steps (admin): Feature Flags tab.
4a Create: New flag → key e.g. `test-console-flag-<n>`, description, owner, tags "billing,beta" → Create flag.
  Pass: lands on detail page; all three envs (Development/Staging/Production) show "Disabled", v1, 0% rollout, no filters.
4b Configure DEVELOPMENT: toggle Enabled (switch turns green) → move rollout slider to a value (e.g. 25%) → Add targeting filter property=plan, operator=equals, value=enterprise → Save changes.
  Pass: toast "Flag updated"; Development card shows Enabled, 25%, filter persisted; version increments to v2. Reload persists.
  Adversarial check: before enabling, confirm rollout slider is DISABLED (grayed) when flag disabled (code L121 `disabled={!editable||!draft.enabled}`).
4c PRODUCTION reason gating: on Production card toggle Enabled → click "Save to production" → confirm a "Confirm production change" dialog appears; with empty reason the "Apply to production" button is DISABLED; type a reason → button enables → Apply.
  Pass: dialog required; empty-reason blocked; after apply toast "Flag updated", Production shows Enabled, version increments.
4d Change history + list: Change history table shows rows for Development (reason "—") and Production (with typed reason), correct By/When. Back to list: new flag row shows Prod "On · N%" and Dev "On · 25%".
4e RBAC (ops@example.com): open the flag → confirm Development card is editable (Save enabled after change) but Production card controls are DISABLED (ops lacks feature_flag:write_prod). Save a dev change succeeds.
  Adversarial: switch to readonly → New flag button disabled; on detail all env controls disabled.
Fail if: created flag not off-everywhere; prod save skips dialog or allows empty reason; version doesn't increment; ops can write prod; list "On · N%" wrong.

## Test 5 — Integrations
Steps (admin): Integrations tab. Confirm three connected sources: Persona, Stripe, LaunchDarkly, each with a record count. Switch sub-tabs → each shows a populated mock data table.
Pass: 3 sources with counts >0; each sub-tab renders non-empty table.

## Test 6 — Audit filters + details expand
Steps: Audit tab. Apply a filter (e.g. action/entity or actor) → list narrows accordingly. Click a row "Details" → before/after JSON expands.
Pass: filter changes result set; Details reveals before/after JSON for a FEATURE_FLAG_UPDATED or REFUND event from earlier tests.

Screenshots to capture: each of 6 tabs; KYC approve+reject state; partial refund result; support limit error; flag dev rollout config; production reason dialog (empty vs filled); change history; audit details expanded.
