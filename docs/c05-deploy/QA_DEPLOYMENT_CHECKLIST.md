# C05 Deployment QA Checklist

Run against the deployed URLs, never localhost. Use synthetic QA data only.
Record every HTTP status, timestamp, revision, and sanitized trace in
DEPLOYMENT_EVIDENCE.md.

## A. Availability

- [ ] `$FE_URL/crew`, `/admin`, `/agent` return 200
- [ ] deployed revision is the intended digest (`.../revisions/list`)
- [ ] static assets load; no app-attributable console errors
- [ ] `/health` on the backend returns 200

## B. Capture

- [ ] CREW `POST /api/inspections` returns **201**
- [ ] record persists (GET returns it)
- [ ] image reference readable after a **new revision** is deployed
  (expected to FAIL with ephemeral disk — record the outcome honestly)

## C. Inference (one controlled real call)

- [ ] record `inference_status`, `prediction_source`, `provider_http_status`,
      `provider_request_id`, model, latency, tokens
- [ ] on failure: classify as `INFERENCE_FAILED`/`INFERENCE_BLOCKED` with the
      real category — this **passes** the failure-tolerance test but is **not**
      evidence of successful inference. Report both facts separately.

## D. Review

- [ ] CREW self-approve → **403**
- [ ] report pre-review → 200 containing `UNVERIFIED - NOT APPROVED`
- [ ] ADMIN review with `decision` + `qc_disposition` → 200
- [ ] report post-review → `OFFICIAL`, approvals durable across revision

## E. Agent

- [ ] answer grounded in persisted data (tool calls visible)
- [ ] SUPERVISOR write without approval → **403**

## F. Scope isolation

- [ ] CREW reads own kitchen; manipulated requests for another kitchen fail

## G. Responsive UI

- [ ] rerun `node scripts/e2e-provenance.mjs $FE_URL` — expect 18/18 at both widths
- [ ] no horizontal overflow on /admin; touch targets per project standard

## H. Resilience

- [ ] restart/new-revision behaviour recorded
- [ ] duplicate submission does not corrupt state
- [ ] provider timeout classification observed or explicitly not triggered
