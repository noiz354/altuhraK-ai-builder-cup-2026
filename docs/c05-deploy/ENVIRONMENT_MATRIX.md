# C05 Environment Matrix

Names and sources only. **No secret values are recorded anywhere in this repo.**

| Variable | Backend | Frontend | Source in cloud | Local value |
|---|---|---|---|---|
| `PORT` | required | required | set by Cloud Run (8080 here) | 8000 / 3000 |
| `C05_GEMINI_PROVIDER` | `vertex` | – | env | `auto`→vertex |
| `GOOGLE_CLOUD_PROJECT` | `gen-lang-client-0170811162` | – | env | same |
| `GEMINI_MODEL` | `gemini-2.5-flash` (frozen) | – | env | same |
| `C05_GEMINI_LOCATION` | `global` | – | env | same |
| `GEMINI_TIMEOUT_SECONDS` | 150 | – | env | 150 |
| `MVP_ALLOWED_HOSTS` | **backend `*.run.app` hostname(s)** | – | env (deploy step writes it) | unset = loopback-only |
| `C05_API_BASE_URL` | – | backend Cloud Run URL | env (deploy step writes it) | `http://127.0.0.1:8000` |
| `C05_DB_PATH` | /tmp path (ephemeral) | – | env; replaced by durable adapter before prod | unset |
| `GEMINI_API_KEY` | **not used** (Vertex ADC) | never | – | unset |

## ADC (no keys)

Local: `gcloud auth application-default login` (already present on this machine).
Cloud Run: attach the runtime service account; ADC discovers it automatically.
Never set `GOOGLE_APPLICATION_CREDENTIALS` on a Cloud Run service.

## Existing Secret Manager entries (metadata only, values never read)

`GEMINI_API_KEY`, `DATABASE_URL`, `BETTER_AUTH_SECRET`, `FIREBASE_SERVICE_ACCOUNT_JSON`,
`PAYMENTS_PUBLIC_ORIGIN`, `XENDIT_SECRET_KEY` — these belong to existing workloads
(PayDash). C05 must NOT reuse them without verifying ownership; the Vertex path
needs no API key at all.

## What changes per environment

Only three values differ between local, staging, and production:
`MVP_ALLOWED_HOSTS`, `C05_API_BASE_URL`, and (once persistence lands) the database
target. Everything else is identical, by design.
