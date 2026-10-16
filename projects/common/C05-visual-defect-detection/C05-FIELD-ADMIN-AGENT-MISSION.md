# C05 — Field Crew App, Admin Command Center & Agentic AI (Mission Brief)

Status: **MISSION LOCKED · implementation slices Day 3–Day 4 pending · not production certified**
Owner scope: `C05-visual-defect-detection` only. Shared runtime changes must not regress the other 23 projects.

## 1. Mission

Build one integrated MVP with three experiences on the **same** inspection data, auth model, evidence, business rules and audit history:

1. **Field Crew App** — mobile-first, installable PWA for kitchen QC crew (360–430px).
2. **Admin Command Center** — desktop-first monitoring and review dashboard.
3. **Embedded Gemini Operations Agent** — one tool-using assistant, shared by crew and admin, role-filtered.

Operational question the MVP must answer: can a crew member capture a meal-box image, have Gemini inspect the expected visible components, and produce a reviewable QC record that a supervisor can monitor and act on?

## 2. Locked decisions (from grill-me rounds 1–4)

| Area | Decision |
|---|---|
| Labels | `meal_complete`, `missing_component`, `uncertain`. Expected components come from a versioned meal manifest. |
| Confidence | `confidence_score = null` = NOT_CALIBRATED. No percentage shown anywhere. |
| Ground truth | Kept in a separate evaluation manifest; never sent to Gemini. |
| Bounding boxes | Gemini native `box_2d = [ymin, xmin, ymax, xmax]`, normalized 0–1000, validated and converted server-side to source-image pixels; both forms preserved for audit. |
| Execution status | `CREATED → QUEUED → RUNNING → COMPLETED / FAILED`. |
| Review status | `UNVERIFIED → REVIEW_PENDING → APPROVED / REJECTED`. Separate from execution status. |
| QC disposition | `ACCEPT / HOLD / REJECT`, stored separately. Approval of a review is not clearance of the meal. |
| Inference trigger | One primary Gemini multimodal request per explicit `Run Inspection`. Long-form explanation stays opt-in. |
| Limits | JPEG ≤ 4 MiB, prefer < 1 MiB, 12s timeout (configurable), max one bounded retry, explicit idempotency key. |
| Storage budget | Hard cap 10 GB for dataset, artifacts, logs and caches. Measure actual usage, never invent it. |
| Export | Draft = `UNVERIFIED — NOT APPROVED`. Official export requires APPROVED review and an immutable snapshot hash. |
| Failure rule | Gemini failure never yields PASS. Inspection stays FAILED/UNVERIFIED with manual recapture path. |
| Out of scope claims | No microbiological safety, nutritional composition, or measured weight claims from photos. |

## 3. Roles and permissions (server-enforced)

- **CREW**: capture, submit, view own/assigned inspections, read-only agent tools, cannot approve.
- **SUPERVISOR**: review assigned kitchen, approve/reject, request recapture, record disposition, create follow-ups.
- **ADMIN**: all kitchens in tenant, manage assignments and manifest versions, metrics, reports, broader agent.

Tenant + kitchen isolation enforced server-side. Never hide privileged actions only in the UI.

## 4. Required agent tools (typed, scoped, audited)

Read-only: `get_inspection`, `list_inspections`, `get_inspection_evidence`, `get_kitchen_summary`, `get_pending_reviews`, `get_meal_manifest`.
Controlled write: `create_followup_task` (requires explicit human confirmation, idempotent).

Each tool: input schema validation, role check, tenant/kitchen scope, result limits, audit event. Agent must never approve QC evidence or mutate predictions.

## 5. Relevant skills routing (verified installed IDs)

| Task | Primary skill | Supporting |
|---|---|---|
| Requirements/design closure | `grill-with-docs`, `domain-modeling` | `interview-me` |
| Spec + task breakdown | `to-spec`, `to-tickets` | `planning-and-task-breakdown` |
| Interface design (inspection API, agent tools) | `codebase-design`, `api-and-interface-design` | `documentation-and-adrs` |
| Test-first implementation | `tdd` | `python-testing-patterns` |
| Debugging | `diagnosing-bugs` | `debugging-and-error-recovery` |
| Crew/Admin UI | `frontend-ui-engineering`, `ui-design` | `accessibility`, `userflow` |
| Browser evidence | `browser-testing-with-devtools` | `performance`, `core-web-vitals` |
| Firebase auth/storage/firestore/hosting | `firebase-auth-basics`, `firebase-firestore`, `firebase-app-hosting-basics` | `firebase-basics`, `firebase-security-rules-auditor` |
| Security and injection resistance | `security-and-hardening` | `firebase-security-rules-auditor` |
| Release/deploy | `shipping-and-launch`, `ci-cd-and-automation` | `firebase-hosting-basics` |
| Cost/observability | `observability-and-instrumentation` | `backend-resilience-patterns` |

Rules: one primary skill per responsibility; verify skill ID before load; do not preload; no skill claims a PASS without executable evidence.

## 6. Implementation order (Day 3 → Day 4)

**Slice A — Crew to Gemini**: camera/upload → image validation → manifest → one Gemini request → structured validation → persistent inspection revision → result UI with overlay.

**Slice B — Admin Review**: real-record KPIs → review queue → evidence side-by-side → approve/reject/recapture → immutable audit → official export.

**Slice C — Agentic Operations**: agent panel → role-filtered read tools → grounded answer → proposed follow-up → explicit confirmation → audit.

**Slice D — Delivery**: browser E2E evidence, live Gemini evidence (real key), deployment config only with an approved project, monitoring, demo rehearsal.

P1 (Pub/Sub, Cloud Run worker, DLQ, offline queue, cost dashboards) only after P0 is demonstrably working. If queue infrastructure is unavailable, keep the synchronous path and report the queue as incomplete.

## 7. Acceptance evidence required

Crew: login/kitchen assignment, upload validation, real inference invoked, persisted inspection, geometrically valid overlay, cannot approve, sees review outcome.

Admin: real-record metrics, scoped queue, permission-checked review, immutable approved evidence, re-inference creates revision, append-only audit, correct report metadata, cross-tenant denial.

Agent: authorized tools only, real data, no fabricated numbers, schema-validated IO, denied unauthorized access, confirmed writes only, prompt-injection in image cannot trigger privileged action.

Regression: `python scripts/verify_mvp.py --project C05` and `python scripts/verify_all_mvp.py` must stay green (8 C05 tests, 192 portfolio tests).

## 8. Honest reporting rules

- No PASS without an executed command, screenshot, or provider response artifact.
- Dummy-key `provider_error` is a failure-path test, not live inference proof.
- Synthetic metrics never presented as real accuracy; `real_accuracy_status = NOT_ESTABLISHED` when labels are insufficient.
- Deployment URL only if deployment actually succeeded.

## 9. Current baseline (verified before this brief)

- C05 8/8 tests passing; portfolio 24/24 (192 tests).
- Deterministic baseline intact; invalid provider output retains baseline; 12s timeout configurable; dummy-key path verified.
- Live Gemini success, deployed E2E, real holdout evaluation, measured storage: NOT YET VERIFIED.

## 10. Immediate next action

Start Slice A with `tdd` + `codebase-design` on the inspection interface; keep the shared runtime green at every commit.