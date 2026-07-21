# Build vs. Buy: Replacing Retool for Internal Ops

**Question.** A Series C fintech (~60 engineers) pays ~$250K/year for Retool but
uses it for only three internal apps: a **KYC review queue**, a **refunds
dashboard**, and a **feature-flag admin panel**. Should they build a lightweight
in-house alternative (using Devin) and drop the license?

**Short answer.** Yes — for *these three narrowly-scoped, high-value, and stable
workflows*, building and owning them is the better long-term decision, and this
repository is a working proof that the build is modest in size. But treat it as a
**targeted replacement, not a blanket "stop buying tools" mandate.** Keep the
option to buy for the next class of internal tools, and only cut the Retool
contract once the in-house apps are in production and stable.

This repo is the concrete artifact behind that recommendation: all three apps,
real business logic, RBAC, auditing, and mocked integrations, in one monorepo.

---

## 1. The cost picture

### Cost of buying (status quo)

| Item | Estimate |
| --- | --- |
| Retool license | **~$250K/year** |
| 3-year total | **~$750K** |
| Trend | Rises with seats/usage; platform pricing is outside your control |

For three apps, $250K/year is a high cost-per-app. Retool pricing scales with
users and it's easy for a 60-person company to land in an enterprise tier whose
cost is disconnected from the three workflows actually in use.

### Cost of building (with Devin)

The honest cost of build isn't the first version — it's **ongoing ownership**.

| Phase | Traditional estimate | With Devin |
| --- | --- | --- |
| Initial build (3 apps, this scope) | ~1–2 eng-months | Days–weeks (this repo is the head start) |
| Ongoing maintenance | ~0.25–0.5 FTE | Meaningfully lower — Devin handles routine changes, upgrades, new filters/columns |
| New internal app (later) | 2–6 eng-weeks each | Days each |

Even at a fully-loaded senior-engineer cost of ~$250K/year, **0.3–0.5 FTE of
maintenance (~$75K–$125K/year) is well under the license**, and Devin pushes the
real number lower by absorbing the incremental, well-specified changes that make
up most internal-tool maintenance.

**Rough 3-year comparison**

| | Buy (Retool) | Build (with Devin) |
| --- | --- | --- |
| Year 1 | ~$250K | Build + ~0.3–0.5 FTE maintenance (~$100K–$175K all-in) |
| Years 2–3 | ~$250K/yr | ~$75K–$125K/yr maintenance |
| **3-yr total** | **~$750K** | **~$250K–$425K** |

The savings are real (order of **$300K–$500K over three years**), but the
strategic value — owning the code, the data path, and the roadmap — matters more
than the line-item savings.

---

## 2. What you gain by building

- **No per-seat licensing.** Cost decouples from headcount and usage.
- **Full customization.** KYC reviewers get exactly the queue, filters, and
  decision workflow they need; refund limits and approval rules are codified in
  your own service layer, not approximated in a GUI.
- **Own your data and integrations.** Vendor data (Persona, Stripe,
  LaunchDarkly) flows through adapters *you* control, in *your* database, with no
  third-party platform in the path of sensitive KYC/PII and payment operations.
- **First-class auditability & RBAC.** Every mutation is an immutable audit
  event; permissions are enforced server-side and are versioned in code and
  reviewed in PRs — valuable for a regulated fintech.
- **No vendor lock-in / pricing risk.** No exposure to platform repricing,
  seat-count creep, or feature paywalls.
- **Composability.** These apps live next to your services and can call internal
  APIs, share auth/SSO, and be tested in CI like any other code.

## 3. What you give up (and must plan for)

- **You now own everything.** Uptime, upgrades, security patching, dependency
  maintenance, and on-call for these tools become yours. Retool bundles all of
  this into the license.
- **Managed connectors.** Retool ships hundreds of prebuilt data-source
  connectors and auth flows. You'll build/maintain each integration adapter
  (mitigated here by a clean adapter pattern, and by Devin for the boilerplate).
- **Speed for *new*, ad-hoc tools.** Retool's drag-and-drop shines when a team
  wants a throwaway CRUD screen this afternoon. A codebase has more ceremony for
  that specific case.
- **Out-of-the-box platform features.** SSO/SAML, granular audit exports,
  environment management, and access reviews come free with Retool; you'd add
  them (SSO is the notable gap in this prototype — it uses a dev-only session).
- **Governance & self-serve.** Retool lets non-engineers assemble tools. In-house
  means changes go through engineering.

---

## 4. Why these three apps are good build candidates

Not all internal tools should be built. These three score well on every "build"
criterion:

- **High value & long-lived.** KYC, refunds, and feature flags are core,
  permanent fintech operations — not throwaway screens. Amortizing a build over
  years is easy.
- **Non-trivial, opinionated business logic.** State machines, refund limits and
  idempotency, optimistic concurrency on flag writes, and audit requirements are
  exactly the things that are awkward to encode in a GUI builder but natural in
  code.
- **Compliance-sensitive data.** Keeping KYC/PII and payment operations inside
  your own stack (not a third-party UI platform) is a real risk reduction.
- **Stable, well-understood requirements.** Low churn means low maintenance,
  which is where build economics live or die.

A **poor** build candidate, by contrast, is a rarely-used, quickly-changing,
low-stakes CRUD screen for a single team — keep buying (or use a builder) for
those.

---

## 5. Recommendation & rollout

**Build these three, in-house, and use Devin to do it and maintain it** — but
de-risk the transition:

1. **Ship in-house apps to production** alongside Retool (this repo is the
   starting point). Add the production-grade gaps below.
2. **Run in parallel** for one full cycle (a KYC review week, a refunds cycle, a
   flag rollout) to confirm parity.
3. **Cut over**, then **downgrade/drop the Retool contract** once stable. Don't
   cancel before parity is proven.
4. **Keep a "buy" lane** for future one-off tools; don't over-rotate into
   building everything.

### Production gaps to close before cutover

- **SSO/SAML** and real user provisioning (this prototype uses a dev-only
  signed-cookie session with a user switcher).
- **Real integration adapters** for Persona / Stripe / LaunchDarkly (the
  interfaces exist; implementations are mocked here) plus secret management.
- **Webhook signature verification** and retry/idempotency hardening.
- **Observability**: logging, metrics, alerting, and audit-log export/retention.
- **Backups & DR** for the Postgres database.
- **CI/CD** with the included tests wired into the pipeline.

### Decision rule going forward

> Build when a tool is **high-value, long-lived, logic-heavy, or
> compliance-sensitive**. Buy when it's **ad-hoc, low-stakes, fast-changing, or
> needs non-engineer self-serve.** With Devin lowering both build and maintenance
> cost, that line moves meaningfully toward "build."

**Bottom line:** replacing Retool for these three apps is justified on cost
(~$300K–$500K over three years) and, more importantly, on control, security, and
customization — provided the team accepts ownership and closes the production
gaps above before cancelling the license.
