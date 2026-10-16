# C05 Deployment Evidence

## Status: PRODUCTION_DEPLOYED + PRODUCTION_VERIFIED

Production services in `gen-lang-client-0170811162`, asia-southeast2:
- c05-backend rev 00001-4ll, image backend:0d13805
  digest sha256:d6e3882dfacdb00496ef486b76ba2a875669413aa6750c3ebc8d394d2aab25d5
- c05-frontend rev 00001-426, image frontend:878112f
  digest sha256:595435edac797b6b7d8ba5401545b34796025c95a5110b3406c4f8b14b36162e
- URLs: https://c05-backend-723420820074.asia-southeast2.run.app
  https://c05-frontend-723420820074.asia-southeast2.run.app
- Data plane (isolated from staging): Firestore database c05prod,
  bucket gs://c05-assets-prod, same least-privilege runtime SA.
- Traffic: 100 percent on the verified revisions (first deployment, no
  predecessor to split against).

### Proven on production (live URLs)
- Capture 201; inference INFERENCE_SUCCEEDED, gemini-2.5-flash, 2179/255
  tokens, 7514 ms, label missing_component, confidence null.
- Crew self-approve 403; report pre-review UNVERIFIED - NOT APPROVED;
  ADMIN approve 200; report post-review OFFICIAL with
  INFERENCE_SUCCEEDED/model provenance.
- Browser E2E vs production frontend: 18/18 at 390px and 1440px.
- PayDash and all 6 sibling services untouched (verified by name before
  every deploy; no shared service, secret, or IAM binding modified).

## Previous status: STAGING_DEPLOYED + STAGING_VERIFIED

Staging services live in `gen-lang-client-0170811162`, asia-southeast2:
- c05-backend-staging rev 00010-hkl, image backend:0d13805
  digest sha256:d6e3882dfacdb00496ef486b76ba2a875669413aa6750c3ebc8d394d2aab25d5
- c05-frontend-staging rev 00001-pmn, image frontend:878112f
  digest sha256:595435edac797b6b7d8ba5401545b34796025c95a5110b3406c4f8b14b36162e
- URLs: https://c05-backend-staging-723420820074.asia-southeast2.run.app
  https://c05-frontend-staging-723420820074.asia-southeast2.run.app
- Runtime SA: c05-runtime (roles/aiplatform.user + datastore.user +
  storage.objectCreator/Viewer on c05-assets-staging)
- Data: Firestore database c05staging, bucket gs://c05-assets-staging

### Proven on staging (live URLs, real revision rollouts)
- Live Gemini: INFERENCE_SUCCEEDED, gemini-2.5-flash, http 200, 2173-2179 in /
  255-260 out, 7-8 s. Single controlled call policy held throughout.
- RBAC: crew self-approve 403, supervisor write 403, cross-kitchen scoped.
- Review: UNVERIFIED - NOT APPROVED before, OFFICIAL after ADMIN approve.
- Agent grounded in persisted data.
- **Persistence across a genuine new revision (fresh empty disks): record 200
  with label + provenance intact, image rehydrated from Cloud Storage,
  re-run INFERENCE_SUCCEEDED with fresh tokens, overview total preserved.**
  The original persistence blocker (1 row before recreate, 0 after) is FIXED.
- Browser E2E vs deployed frontend: 18/18 at 390px and 1440px.

### Auth defects found by staging (fixed)
- ADC file check fails on Cloud Run; google.auth.default() via metadata
  server is the primary path, gcloud CLI the fallback.
- google-auth 2.41.1 vs 2.62.0 was a red herring; the real cause was the
  missing `requests` package, without which the metadata credential path is
  silently skipped by library design. requirements.txt pins both with reasons.
- MVP_ALLOWED_HOSTS must name the backend run.app hostname; hostile Host 403.

## Previous status (kept for the record): PREPARED

No Cloud Run service, revision, URL, or traffic split exists for C05.
No image has been pushed to Artifact Registry. No cloud resource was created,
modified, or deleted during this preparation.

## What WAS proven (local containers, Docker, zero cloud cost)

| Claim | Evidence | Date |
|---|---|---|
| Backend image builds | `c05-backend:local`, 251 MB, digest `...79f7d48aba16` (local tag) | 2026-10-16 |
| Frontend image builds | `c05-frontend:local`, 396 MB | 2026-10-16 |
| Container binds 0.0.0.0, health 200 | `Up … (healthy)`, `GET /health → 200` on published port | 2026-10-16 |
| Frontend→backend proxy works in containers | `GET /api/proxy/api/infra/readiness → 200` | 2026-10-16 |
| DNS-rebinding guard intact | `Host: evil.example.com → 403` | 2026-10-16 |
| Cloud-style Host accepted when allow-listed | `Host: c05-backend-staging-*.run.app → 200` | 2026-10-16 |
| Local disk is NOT durable | 1 inspection before container recreate, **0 after** | 2026-10-16 |
| No credentials baked into layers | `.dockerignore` excludes `.env*`, keys, `*.sqlite`; smoke container readiness shows `provider_resolved: null` | 2026-10-16 |
| Full local workflow in container | capture 201 → `INFERENCE_BLOCKED`/baseline → self-approve 403 → `UNVERIFIED - NOT APPROVED` → APPROVED → `OFFICIAL` → agent grounded answer | 2026-10-16 |

## Smoke defects found by container testing (fixed)

1. `fixtures/sample.py` is loaded by `shared_mvp/app.py` at startup. The first
   `.dockerignore` excluded it as test-only; the container exited 1 with
   `FileNotFoundError` before binding a port. Fixed by copying fixtures into
   the image. Lesson: distinguish "test fixtures" from "startup fixtures".
2. `c05_entry.py` bound `127.0.0.1`; unreachable from outside the container.
   Fixed to `0.0.0.0` with a regression test.
3. The shared Host guard 403'd the frontend proxy (`Host: host.docker.internal`)
   and would 403 every Cloud Run request. Fixed with explicit `MVP_ALLOWED_HOSTS`.

## Regression at preparation time

Portfolio 192/192, C05 8/8, C05 project tests 37/37 (was 31: +6 deployment-guard
tests), frontend `tsc` clean, production build clean, browser 18/18.

## Deferred to staging execution

Service URLs, revisions, image digests, deploy timestamps, runtime identity,
traffic allocation, the single controlled Gemini call, and the full checklist —
all recorded here only after they exist.
