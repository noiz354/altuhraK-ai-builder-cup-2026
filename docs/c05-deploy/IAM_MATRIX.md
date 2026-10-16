# C05 IAM Matrix

Principle: runtime gets exactly the permissions its code paths exercise.
Verified against the actual call sites, not assumed.

| Identity | Resource | Permission | Purpose |
|---|---|---|---|
| Operator (`roles/owner`, existing) | project | deploy Cloud Run, push AR | one-time staging deploy only |
| `c05-runtime@<project>.iam.gserviceaccount.com` (to create) | Vertex AI | `roles/aiplatform.user` (covers `aiplatform.endpoints.predict`) | `generateContent` calls from `c05_gemini.py` |
| same | Cloud Logging | `roles/logging.logWriter` (default on Cloud Run SA) | stdout logs, no secrets |
| same | Artifact Registry | read on `c05` repo | pull images (Cloud Run default SA handles this) |
| same | Cloud Run | `roles/run.invoker` on **c05-frontend** for end users (`allUsers` acceptable for a hackathon demo; restrict for anything real) | browser access |
| same | Cloud Run | `roles/run.invoker` on **c05-backend**, granted to the frontend runtime SA only | service-to-service proxy calls |
| nobody | Secret Manager | no grants | C05 needs no secrets; Vertex uses workload identity |
| nobody | PayDash services/data | no grants, no changes | protected workloads |

## Explicitly forbidden

- `roles/owner` or `roles/editor` on any runtime service account.
- Long-lived service-account JSON keys (workload identity satisfies every need).
- `GOOGLE_APPLICATION_CREDENTIALS` as a Cloud Run env var.
- Reusing PayDash secrets (`GEMINI_API_KEY`, `DATABASE_URL`, …) for C05.
- `MVP_ALLOWED_HOSTS=*` — name exact hostnames or the DNS-rebinding guard is void.
