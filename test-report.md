# Test Report — Internal Operations Console (PR #1)

**PR:** https://github.com/JothiRamaswamy/internal-ops-console/pull/1
**Environment:** Postgres 16 (Docker :5432) + FastAPI backend (:8000) + Vite/React frontend (:5173). Auth via dev-only seeded user switcher.
**Method:** Full end-to-end browser testing of every tab and each golden path plus adversarial business-rule checks (required reasons, role limits, production gating, provider failure). All actions performed through the UI.

## Result summary

| Area | Result |
|------|--------|
| App shell + Overview (6 nav tabs, summary cards, recent audit) | ✅ Pass |
| KYC approve / reject with required reason + persistence + audit | ✅ Pass |
| KYC READ_ONLY restriction (controls disabled + banner) | ✅ Pass |
| Refund partial + balance/status math | ✅ Pass |
| Refund provider failure (FAIL-suffixed payment) | ✅ Pass |
| Support refund limit ($250): >$250 blocked, ≤$250 allowed | ✅ Pass |
| Feature flag create → disabled everywhere | ✅ Pass |
| Feature flag dev rollout + targeting filter | ✅ Pass |
| Feature flag production reason gating (empty blocked, filled applies) | ✅ Pass |
| Feature flag change history + list "On · N%" | ✅ Pass |
| RBAC OPS: prod write blocked, non-prod allowed | ✅ Pass |
| RBAC READ_ONLY: cannot create/edit flags | ✅ Pass |
| Integrations (3 sources + mock tables) | ✅ Pass |
| Audit filters + before/after JSON details | ✅ Pass |
| SUPPORT_AGENT KYC read | ⚠️ Discrepancy (see below) |

## Escalations / discrepancies

- **SUPPORT_AGENT cannot read KYC.** The task spec described support as being able to "read KYC/flags", but `backend/app/permissions.py` grants SUPPORT_AGENT only `refund:read`, `refund:create`, `feature_flag:read` — no `kyc:read`. As a result the KYC queue is empty for Sam Support and the summary cards show "—". This is internally consistent with the code, but conflicts with the written spec. Additionally, the UI shows a generic "No KYC cases match these filters." message rather than an access-denied notice, which could mislead a support user into thinking there are simply no cases. Recommend the team decide whether support should have `kyc:read` (spec) or whether the spec text is wrong, and consider a clearer "no access" state.
- **Client allows submitting an over-limit refund.** For support, the Confirm button stays enabled at $300 even though the inline "This exceeds your refund limit of $250.00" warning is shown; the server correctly rejects it (`REFUND_LIMIT_EXCEEDED` → toast "This refund exceeds your role's refund limit."). Enforcement is correct server-side; the client could optionally disable the button to match the KYC/flag patterns. Not a blocker.

## Evidence

### App shell + Overview
All six nav tabs render; summary cards show numeric values; recent audit reflects the actions performed during testing.

![Overview](https://app.devin.ai/attachments/d940d028-244a-417f-b205-2443aa11c48f/ss_2233201f.png)

### KYC — READ_ONLY restriction
Approve/Reject/Assign/Request-more-info all disabled with the amber "Your role can view this case but cannot make review decisions." banner. (Approve/Reject golden path as admin was verified earlier: kyc_027 approved, kyc_002 rejected with SUSPECTED_FRAUD, both persisted and appeared in Audit.)

![KYC read-only](https://app.devin.ai/attachments/4a5566a9-67c4-457a-b4f5-d0e0fe08cd6a/ss_473aee02.png)

### Refund — partial (admin)
$500 partial refund on pay_018 ($1,999): status → Partially Refunded, remaining $1,499.00, refunded $500.00, history row Succeeded with provider ref.

![Partial refund](https://app.devin.ai/attachments/3c7bc661-a728-4d90-896c-b8439b7318fa/ss_04f4fbda.png)

### Refund — provider failure
pay_007 (`pi_mock_0007_FAIL`, MOCK_PROVIDER): refund FAILED with "Provider declined the refund (simulated failure).", payment stayed Succeeded, $0 consumed.

![Provider failure](https://app.devin.ai/attachments/0825c15f-5885-4532-b27f-02d740e7bf50/ss_6fd18993.png)

### Refund — support role limit
$300 as Sam Support → inline warning + backend error toast "This refund exceeds your role's refund limit."; no refund created.

![Support limit blocked](https://app.devin.ai/attachments/e249acde-0d12-4d78-a17e-d696356eca4a/ss_ec0f91ca.png)

$200 as Sam Support → succeeds; status → Partially Refunded, remaining $1,799.00.

![Support $200 success](https://app.devin.ai/attachments/c4e034d2-fc52-4597-a5c0-a4f6b5cb7ee3/ss_fd6688ff.png)

### Feature flags — dev rollout + targeting
Development enabled, rollout 25%, targeting filter plan=enterprise, saved → version v2.

![Dev rollout config](https://app.devin.ai/attachments/d0d443d8-679f-47f6-affe-2cd002072294/ss_5bf0b4a6.png)

### Feature flags — production reason gating
"Confirm production change" dialog; "Apply to production" DISABLED while reason empty.

![Prod reason dialog empty](https://app.devin.ai/attachments/442129a6-d367-4083-b1c8-2b2fc27ca7fe/ss_77d6c5a3.png)

After entering a reason and applying: Production → v2 Enabled, reason logged in Change history.

![Prod applied](https://app.devin.ai/attachments/c9183f8e-a624-49f8-80f1-1eaca6d21d75/ss_5b1e89b1.png)

### Feature flags — list "On · N%"
List shows the new flag Dev "On · 25%" (later "On · 40%" after ops edit) and Prod "On · 0%".

![Flag list](https://app.devin.ai/attachments/d8d62c15-b5e5-46d3-8ce2-18014d14e284/ss_4a008f28.png)

### RBAC — OPS
Production card controls disabled with no "Save to production" button; OPS saved a Development change (→ v3 by Olivia Ops).

![OPS restriction](https://app.devin.ai/attachments/9c5eea18-c203-42eb-b952-5ac91fc22901/ss_fe68df50.png)

### RBAC — READ_ONLY
"New flag" button disabled; all env controls (toggles, sliders, filters) disabled.

![Read-only flags](https://app.devin.ai/attachments/da18a5eb-56d2-45ae-9c92-083afc98cf72/ss_e821dddc.png)

### Integrations
Three connected sources — Persona (14), Stripe (12), LaunchDarkly (13) — each sub-tab renders a populated mock data table.

![Integrations](https://app.devin.ai/attachments/d71e05d1-c172-48e9-9b0d-cf2e2c07bbca/ss_478ea83f.png)

### Audit — filters + details
Entity-type filter narrows to Refund-only events (10); row Details expands before/after JSON.

![Audit filter](https://app.devin.ai/attachments/1a1b7b60-69ef-47b4-b44c-355ac0f23ed4/ss_43b83541.png)

## Notes
- All business rules enforced server-side and confirmed at runtime.
- Optimistic version incremented correctly on each flag save (v1 → v2 → v3); no version-conflict scenario was force-triggered.
