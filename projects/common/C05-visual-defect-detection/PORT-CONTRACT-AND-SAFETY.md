# C05 Port Contract & Donor Safety Review (Phase 0)

Date: 2026-10-18
Donor: `sea-ai-hackathon` (read-only reference, nested git repo, divergent history)
Target: `altuhraK-ai-builder-cup-2026` (deployed)

Governing gates: `.agents/skills/c05-quality-gates/SKILL.md` (verified byte-identical to the donor copy).

---

## T0.4 (done first, because it changes the plan) — Gate 1 conflict

### The finding

`c05-quality-gates` **Gate 1** states, verbatim:

> `confidence_score` is `null` (`NOT_CALIBRATED`). No calibration methodology exists.
> - Never render a percentage, probability, or "how sure" number anywhere in UI, export, or agent copy.
> - If a future calibration study exists, it needs its own gate and a documented method before this
>   skill permits any non-null value.

The target repo currently **violates Gate 1**. `git diff` on `src/domain.py` shows the guard was
inverted from enforced to permitted:

```
-  require(output['confidence_score'] is None, 'C05 MVP does not have a calibrated confidence score')
+  require(isinstance(output['confidence_score'], (int, float)) and 0 <= output['confidence_score'] <= 1, ...)
```

and `c05-status.tsx` now renders `confidence_score: 0.95 (ESTIMATED, NOT_CALIBRATED)`.

This change was made at the user's explicit request ("jangan null dong"). It is therefore a
**deliberate product decision**, not an accident — which means the gate must be amended, not
silently violated.

### Gate 1b — confidence *estimate*, not probability (proposed, needs sign-off)

| Rule | Statement |
|---|---|
| What the number is | A **model self-report** / heuristic estimate on a 0–1 scale. |
| What it is NOT | A probability. Not calibrated. Not comparable across images, kitchens, or models. |
| Required label | Any surface rendering it must read `ESTIMATE, NOT CALIBRATED` in the same visual block. |
| Forbidden renderings | No `%`. No "95% sure". No traffic-light colouring that implies reliability. No threshold language ("above 0.8 is safe"). |
| Human approval | Unchanged and independent. Confidence **never** auto-approves. Gate 3 still holds. |
| Calibration path | A real study needs its own gate + documented method before any wording may call it a probability. |

If this is rejected, the alternative is to revert `domain.py` to the null guard and drop the UI
rendering. That is a one-commit revert and the rest of the plan is unaffected.

**Status: RESOLVED 2026-10-18** — user approved Gate 1b. `c05-quality-gates/SKILL.md` amended:
Gate 1 superseded by Gate 1b (estimate, not probability) plus Gate 1c (ground truth). The guard in
`domain.py` is now the enforcement point rather than a violation.

---

## T0.4b (done) — Gate 7 amendment

Gate 7 requires three commands in order:

| Command | Present in `altuhraK-ai-builder-cup-2026`? |
|---|---|
| `python scripts/verify_mvp.py --project C05` | yes (8/8) |
| `python scripts/verify_all_mvp.py` (192/192 portfolio) | **MISSING** |
| `cd apps/c05 && node scripts/qa.mjs` (16/16 browser) | yes |

`verify_all_mvp.py` exists only in the donor. The portfolio regression **cannot currently be run**
against the deploy repo, so Gate 7 cannot be declared green there.

Options: (a) copy `verify_all_mvp.py` plus the 23 other projects it walks — large and pointless for a
single-product repo; (b) amend Gate 7 for the single-product target repo to
`verify_mvp.py` + adapter pytest + `qa.mjs` + `e2e-provenance.mjs`. Recommend **(b)**.

**Status: RESOLVED 2026-10-18** — user approved the amendment. `c05-quality-gates` Gate 7 now has two
branches: single-product repos use adapter pytest + `verify_mvp.py` + `qa.mjs` + `e2e-provenance.mjs`;
multi-project repos keep the mandatory 192/192 portfolio run.

---

## T0.1 — Verified contract map

Every row was read from donor source. "Scope" is what the donor actually enforces, not what it should.

### Supply

| Method | Path | Donor role check | Kitchen scope | Side effects | Status codes | UI consumer |
|---|---|---|---|---|---|---|
| POST | `/api/supply/lots` | `_require_role(role, write=True)` | `kitchen` must be in `_scope(role)` | writes `supply_lot`; appends audit | 201, 403, 422 | `supply-lot-form` |
| GET | `/api/supply/lots` | `_require_role(role)` | optional `kitchen_id` filter | none | 200 | `supply-lot-list` |
| GET | `/api/supply/lots/{lot_id}` | `_require_role(role)` | scope | none | 200, 404, 403 | detail pane |
| PATCH | `/api/supply/lots/{lot_id}` | write | scope | mutates lot | 200, 403, 404, 422 | `supply-lot-list` |
| GET | `/api/supply/anomalies` | `_require_role(role)` | filters by `kitchen_id`, then by `_scope(role)` | none | 200, 403 | `supply-anomaly-card` |

Validated fields on lot create (from source): `received_at` required ISO-8601; `expires_at` optional
ISO date; `menu_id` + `menu_version` must be supplied together, `menu_version` must be `int`.

### Claims / illness intake

| Method | Path | Donor role check | Kitchen scope | Side effects | Status codes | UI consumer |
|---|---|---|---|---|---|---|
| POST | `/api/claims` | **NONE — public** | kitchen from payload only | writes `claim`; appends `claim_submitted` | 201, 422 | `claim-form` |
| GET | `/api/claims` | role | `kitchen_id` + date range filter | none | 200 | `claim-list` |
| GET | `/api/claims/{claim_id}` | role | scope | none | 200, 404 | `claim-trace` |
| PATCH | `/api/claims/{claim_id}` | role | scope | mutates claim | 200, 403, 404 | `claim-trace` |
| GET | `/api/claims/{claim_id}/trace` | role | scope | none | 200, 404 | `claim-trace` |

Donor stores `reporter_contact` **and** `reporter_contact_normalized` in cleartext and echoes them.
Duplicate detection compares the cleartext normalized contact. **Do not port this.**

### Agent investigation

| Method | Path | Role check | Scope | Side effects |
|---|---|---|---|---|
| POST | `/api/agent/investigate` | role | scope | writes agent session |
| GET | `/api/agent/runs` | role | scope | none |

**"Grounded" definition for T0.4.** An incident summary is grounded only if all of these hold, and
each is a test, not a code comment:

1. **Allowed sources.** Only `inspection`, `supply_lot`, `claim`, and `delivery_verification` records
   whose `kitchen_id` is inside the caller's `_scope(role)`. No other collection is readable.
2. **Every claim is sourced.** The response carries `sources: [{kind, id, field}]`. A sentence with
   no source entry is a defect, not a style issue.
3. **Sources are shown.** The UI renders the source list. An answer the operator cannot audit is not
   grounded.
4. **No score mutation.** The endpoint must not call any write path on `inspection`,
   `qc_disposition`, `review_status`, or `delivery_verification`. Test: snapshot all in-scope records
   before and after, assert byte-identical.
5. **No decision language.** The summary may describe conflicts and patterns. It may not contain
   "approved", "rejected", "safe", "unsafe", or a recommendation to close a case. Assert on the text.
6. **Counts are computed, not generated.** Counts come from the same query that produced the source
   list, so a count can never disagree with its own citations.
7. **Provider failure is visible.** If Gemini is unavailable, the summary states that and returns the
   computed facts only — never an invented narrative.

### Menus / tuning surface

| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/api/menus` | ADMIN | writes `menu` |
| POST | `/api/menus/{id}/v/{ver}/approve` | ADMIN | immutable version approval |
| GET | `/api/menus`, `/{id}/v/{ver}` | role | read |
| GET | `/api/annotations/queue` | ADMIN | dataset surface |
| POST | `/api/inspections/{id}/annotations` | ADMIN | writes `annotation` |
| POST | `/api/inspections/{id}/adjudicate` | ADMIN | final |
| GET | `/api/data/overview` | **ADMIN only** | dataset metrics |

**No Vertex AI tuning code exists in either repo.** `grep tunedModel|supervisedTuning|tuningJob|pipelineModel`
returns nothing. Per D4 this stays "dataset and label surface". Do not add tuning-job endpoints that
would imply a pipeline we cannot run.

---

## T0.2 — Donor safety verdicts

"Donor-equivalent payload" is not "safe to port". Verdict per family.

| Family | Verdict | Reason | Required change when porting |
|---|---|---|---|
| Supply lots | **Mostly safe** | Scope enforced, writes audited, fields validated | Add rate limit if reachable without auth; confirm `PATCH` cannot silently rewrite `received_at` after linking to a menu |
| Supply anomalies | **Safe** | Read-only, filtered by scope | none |
| Claims create | **UNSAFE AS-IS** | No auth; cleartext contact; no rate limit; unbounded body | Use `c05_privacy.contact_record`; rate limit; cap body size; reject when `C05_CONTACT_HMAC_SECRET` unset rather than storing cleartext |
| Claims read/update/trace | **Unsafe without auth** | Role is a client-supplied parameter (D5) | Acceptable only if the deck stops calling this access control |
| Agent investigate | **Conditional** | Must satisfy the 7-point grounded definition above | Tests, not code comments |
| Menus/annotations/adjudication | **Safe** | ADMIN-gated, immutable versions | Preserve immutability; do not let adjudicate overwrite an existing annotation |
| Data overview | **Safe** | ADMIN only; already returns `null` + reason for unavailable metrics | Keep the null-with-reason discipline; never coerce to `0` |
| Reports | **Conditional** | Must use `c05_privacy.public_view` for any public surface | Strip blind index, name, internal notes |

### Cross-cutting donor issues (apply to every ported endpoint)

1. **No authentication exists.** `_scope(role)` is derived from a client-supplied `role`. Every
   "enforced" row in the map above is a *demo* boundary. Do not describe any of it as access control.
2. **No rate limiting anywhere.** `shared_mvp/app.py` has a request-size middleware but nothing
   bounds request rate. Public intake needs one.
3. **`404` vs `403` leaks existence.** Returning 403 for out-of-scope and 404 for unknown lets an
   attacker enumerate valid IDs. Pick one per endpoint and test it.
4. **Assets endpoint is unscoped.** `shared_mvp` `/api/assets/{name}` serves any file in the project
   asset root to any caller. Tray images are therefore world-readable by URL.

---

## T0.3 — Deliberately not ported

| Donor code | Reason |
|---|---|
| `domain.validate_output` null-confidence guard | Would silently break the deployed confidence feature. Pending Gate 1b. |
| Donor `create_inspection` idempotent replay | Deployed version fixes a real `KeyError` there. |
| Donor `CameraCapture` | Deployed `crew-inspection.tsx` has the MediaStream-attach fix plus per-component overlay. |
| Donor `agent/chat` list-only branch | Deployed version resolves short IDs and answers per inspection. |
| Donor cleartext contact fields | Replaced by `c05_privacy` blind index. |
| `verify_all_mvp.py` | Meaningless in a single-product repo; Gate 7 amendment proposed instead. |

## Open decisions

| # | Question | Decision | Status |
|---|---|---|---|
| Q1 | Gate 1b or revert confidence to null? | Adopt Gate 1b — estimate, not probability | **Done** |
| Q2 | Amend Gate 7 for a single-product repo? | Yes; document the substitution | **Done** |
| Q3 | `/api/assets/{name}` scope | Scope it to the caller's kitchen; tray images are the most sensitive asset | **In progress (Phase 1)** |
| Q4 | Rate limiter | In-process token bucket now; Cloud Armor only under real traffic | **In progress (Phase 1)** |