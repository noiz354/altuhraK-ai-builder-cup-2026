# C05 Claims Register

Every claim in the submission deck must appear here with a status label and a reproducible check.
Status vocabulary is fixed:

| Status | Meaning |
|---|---|
| `live-tested` | Executed against a real provider or real deployed service, with recorded evidence |
| `deployed` | Running on the submitted link; reachable and functional at evaluation time |
| `synthetic` | Synthetic data or fixture scenario; **not** a field-accuracy claim |
| `prepared` | Code/contract/surface exists but was not executed for this submission |

A claim may never be presented with a stronger status than the row allows.

## Deck claim register

| # | Deck claim | Status | Reproducible check | Notes |
|---|---|---|---|---|
| 1 | Gemini multimodal tray check with structured output | `live-tested` | `POST /api/inspections/{id}/run` with `{"role":"CREW","mode":"ai"}`; assert `inference_status == INFERENCE_SUCCEEDED` and `prediction_source == model` | Requires `GEMINI_MODEL` + Vertex ADC |
| 2 | Per-component assessment with bounding box and confidence | `live-tested` | Same run; assert `prediction.components` has keys `carbohydrate`, `protein`, `vegetable`, each with `status`, `box`, `confidence_score` | Confidence is an **estimate**, not calibrated |
| 3 | Deterministic baseline fallback when provider fails | `live-tested` | Run with an unset `GEMINI_MODEL`; assert `inference_status == INFERENCE_BLOCKED` and `prediction_source == baseline`, HTTP still 200 | Manual QC must never be blocked |
| 4 | Human review is the only approval path | `deployed` | `POST /api/inspections/{id}/review` requires `decision in {ACCEPT,HOLD,REJECT}`; assert `CREW` receives 403 | Locked by `c05-quality-gates` |
| 5 | Student delivery verification with visual diff | `live-tested` | `POST /api/delivery-verifications` on an `APPROVED` inspection; assert `visual_score`, `quality_alert`, `quality_alert_reasons` present | Kitchen-scoped, not public |
| 6 | Quality alert triggers on degradation | `live-tested` | Submit a degraded student image; assert `quality_alert == true` and a reason such as `visual_difference_high` | Thresholds: score < 0.85, sharpness/brightness drop |
| 7 | Operations agent is grounded in real records | `live-tested` | `POST /api/agent/chat`; assert `tool_calls` names `get_inspection` / `get_kitchen_summary` / `list_inspections` and `grounded == true` | Rule-based, not an LLM planner |
| 8 | Suggested questions, rating and feedback loop | `live-tested` | `GET /api/agent/suggestions`; `POST /api/agent/feedback`; assert `feedback_id` returned | Feedback is stored, not yet used for tuning |
| 9 | **Lot traceability / supply insights** | `live-tested` | `POST/GET/PATCH /api/supply/lots`, `GET /api/supply/anomalies`; assert `checks.temp_ok`, scope 403, status-transition 409, reject-requires-reason 422 | Ported as `src/c05_supply.py`. Thresholds are named constants: 5 °C, 3 shelf days, +20% price. |
| 10 | **Illness report form / claim integrity** | `live-tested` | `POST /api/claims`; assert `contact_masked` present, `contact_blind_index` absent, `503` when `C05_CONTACT_HMAC_SECRET` unset; trace resolves a supplier | Ported as `src/c05_claims.py`. 8 integrity checks, each naming the records it compared. |
| 11 | **Grounded incident summary** | `live-tested` | `POST /api/agent/investigate`; the 7 clauses in `tests/test_c05_investigate.py` | `src/c05_investigate.py`. Decision words are filtered from output, not merely discouraged. No provider is wired, so narration is skipped and the summary says so. |
| 12 | **Vertex AI supervised tuning pipeline** | `prepared` | No tuning code exists in either repo | **Downgraded 2026-10-18; implemented as a label surface only.** `GET /api/data/overview` reports dataset metrics, duplicate hashes, inter-annotator agreement and `tuning_readiness.blocked_by`. Do not present as a delivered tuning pipeline. |
| 13 | **Phone numbers are hashed** | `live-tested` | `tests/test_c05_supply_claims.py` greps store, audit trail, list response and trace for the cleartext value; `test_missing_secret_refuses_intake` asserts 503 | **Was an overclaim.** Fixed: HMAC-SHA256 blind index + masked last-4, 90-day retention, `purge_claim`. |
| 14 | Role/kitchen access control | `prepared` | **No authentication exists.** Role is client-side React state; the backend trusts the `role` parameter | Must be described as an in-app demo role switch. Asset reads and intake are now bounded, but that is not identity. |
| 15 | Deployed prototype link stays functional | `deployed` | `curl -I https://c05-frontend-723420820074.asia-southeast2.run.app` and load `/crew`, `/admin`, `/delivery` | Must be re-checked immediately before submission |
| 16 | Automated test counts | `live-tested` | `python -m pytest projects/common/C05-visual-defect-detection/tests/ -q` (adapter) and `node scripts/e2e-provenance.mjs` + `node scripts/e2e-lanes.mjs` (browser) | Last measured 2026-10-18: **181 adapter tests passed**, e2e-provenance 18/18, e2e-lanes 34/34. Re-measure at submission time. |
| 17 | Asset reads are scoped | `live-tested` | `tests/test_c05_guards.py::AssetScope`; assert 404 without a role and 404 cross-kitchen, and that a 403 would have revealed existence | Tray photos are no longer world-readable by URL. |
| 18 | Public intake is rate limited | `live-tested` | `tests/test_c05_guards.py::RateLimit`; assert 429 after capacity and that a different identity keeps its own budget | In-process token bucket. Per-process, so the effective limit multiplies with Cloud Run instances — not a DDoS control. |

## Rules

1. Never upgrade a row's status without attaching the executed evidence.
2. Rows 12 and 14 are the honest gap list. They are the work queue, not the pitch.
3. A passing test suite is not proof of live inference or deployment.
4. Deck snapshots are illustrations, not evidence. Evidence is the command above.

## Deck corrections required before submission (2026-10-18)

| Slide | Currently says | Must say |
|---|---|---|
| Features | "Tuning pipeline — Household-plate dataset to Vertex AI supervised tuning" | "Label dataset: versioned menus, blind annotation and adjudicated gold labels. No tuning job is implemented." |
| Features | "Claim integrity — 8 checks vs delivery records" | Keep, but state that phone numbers are stored as an HMAC blind index and staff see the last four digits only. |
| Architecture / Identity | "Identity: one least-privilege service account" | This is accurate for the Google Cloud service account and must not be read as end-user identity. There is no end-user authentication. |
| Opportunities | "Anything can be traced back to its suppliers" | Keep. The trace is records-based and synthetic. |
| Prototype | Role switch implied as access control | State plainly that role and kitchen are a demo switch with no authentication behind them. |