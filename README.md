# C05 — Food Production Visual Quality Control

Meal-tray inspection for production kitchens: the Field Crew captures a tray photo,
Gemini classifies it against a versioned meal manifest, a supervisor reviews the
finding, and an approved report is exported. A grounded operations agent answers
questions from persisted inspection data. Provider failure never blocks manual QC.

**Live deployment:** https://c05-frontend-723420820074.asia-southeast2.run.app
(`/crew`, `/admin`, `/agent`)

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/base-ui |
| Backend | Python 3.12, FastAPI + uvicorn, Pydantic v2, Pillow, httpx |
| AI | Gemini 2.5 Flash via Vertex AI (`global` endpoint, ADC, thinking off) |
| Data | Firestore (records), Cloud Storage (images), local cache for inference |
| Infra | Cloud Run `asia-southeast2`, Artifact Registry, least-privilege SA |

## Google AI usage

Gemini performs live multimodal inference (`inlineData` image + structured
`responseSchema`) through a swappable provider transport (`auto | gemini-api |
vertex`). Every run records provenance: `inference_status`
(`NOT_REQUESTED | INFERENCE_BLOCKED | PROVIDER_INVOKED | PROVIDER_RESPONDED |
INFERENCE_SUCCEEDED | INFERENCE_FAILED`), `prediction_source` (`model | baseline |
none`), provider HTTP status and request ID. `INFERENCE_SUCCEEDED` is emitted
only for domain-validated model output; `confidence_score` stays `null`
(uncalibrated by design); approvals are human-only and immutable.

## Run locally

```bash
pip install -r requirements.txt
python projects/common/C05-visual-defect-detection/src/c05_entry.py  # :8000

cd apps/c05 && npm ci && npm run dev  # :3000
```

```bash
python scripts/verify_mvp.py --project C05   # 8/8
cd apps/c05 && node scripts/e2e-provenance.mjs  # 18 browser checks
```

Copy `projects/common/C05-visual-defect-detection/.env.example` to `.env` for
live provider configuration. Never commit real credentials.

## Layout

- `projects/common/C05-visual-defect-detection/` — API adapter, domain guards, config, tests
- `shared_mvp/` — shared runtime (transport, store, contracts; SQLite default, Firestore adapter)
- `apps/c05/` — Next.js crew/admin/agent frontend + server-side proxy
- `scripts/verify_mvp.py` — project verification
- `deploy/` — backend Containerfile + dockerignore
- `docs/c05-deploy/` — architecture, runbooks, IAM/cost matrices, evidence log
