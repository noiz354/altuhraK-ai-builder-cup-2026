# C05 Deployment Architecture

Status: **PREPARED, NOT DEPLOYED** · Date: 2026-10-16 · Model freeze in effect.

## Topology

```
Browser (mobile 390px / desktop 1440px, verified 18/18)
  │  HTTPS, no credentials in bundles, no direct backend calls
  v
c05-frontend  (Cloud Run, public ingress, min 0 / max 2)
  │  Next.js standalone server; /api/proxy/* forwards server-side
  │  with the browser's Host stripped (fetch sets Host from target)
  v
c05-backend   (Cloud Run, PUBLIC ingress, min 0 / max 2)
  │  FastAPI+uvicorn on 0.0.0.0:$PORT; RBAC enforced in-app
  │  (CREW < SUPERVISOR < ADMIN, kitchen-scoped, verified: crew self-approve 403)
  ├── Gemini via Vertex AI, global endpoint (ADC bearer, cached 45 min)
  ├── SQLite on instance-local disk  <-- EPHEMERAL (see blocker)
  └── images in container tmp dir   <-- EPHEMERAL (see blocker)
```

## Service boundaries

| Concern | Where | Why |
|---|---|---|
| Browser-user RBAC | backend in-app (`ROLES`, `_scope`) | Cloud Run IAM cannot express kitchen roles; UI hiding is not enforcement |
| DNS-rebinding guard | backend middleware, `MVP_ALLOWED_HOSTS` | must name the backend `*.run.app` hostname or every request 403s |
| Credential custody | frontend proxy keeps secrets server-side | browser bundles contain no keys |
| Provider calls | backend only | model responses carry provenance (`http_status`, `request_id`) |

## Public / private

Both services take **public ingress** (`--ingress=all`): the frontend must serve
browsers, and the backend must accept calls from the frontend service. Backend
safety comes from in-app RBAC (verified 403s), not from hiding it. Unauthenticated
requests can create inspections and run inference — same as local — but cannot
approve, cannot write via the agent, and cannot read outside the caller's kitchen.

## CRITICAL BLOCKER: persistence (proven, not theoretical)

A container restart test destroyed all state: **1 inspection before → 0 after**.
Cloud Run local disk is per-instance and ephemeral; revisions, scale events, and
recycles all wipe it. Shipping the current SQLite-on-disk as production storage
would silently lose every inspection, review, report, and image.

The deploy runbook therefore stages with ephemeral disk for wiring checks only,
and production is **BLOCKED** until the Store gains a durable adapter
(Firestore or Cloud SQL) behind the existing `Store.get/put/append` API.
Only 4 raw-SQL call sites bypass the API, all in `c05_api.py` with the identical
`SELECT payload FROM items` shape, so the swap is tractable. Do NOT work around
this with max-instances 1: that does not make local disk durable.

## Identities

Deploy identity: the operator's owner account (one-time `gcloud run deploy`).
Runtime identity: a dedicated service account with only
`roles/aiplatform.user` (+ datastore/storage roles once persistence lands).
Never owner/editor for runtime. Never long-lived JSON keys; workload identity only.

## Regions

Target: `asia-southeast2` (Jakarta) — Indonesian users, and the existing
`paydash-web`, `budget-guard`, `reconciliation-fleet-v2` all run there.
Vertex AI `global` endpoint is region-independent.
