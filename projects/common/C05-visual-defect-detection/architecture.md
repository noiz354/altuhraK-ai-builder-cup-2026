# Architecture — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Decision: [ADR-0001](adr/0001-mvp-boundary.md).
Pipeline: bounded importer → schema validator → local generated PNG + pixel baseline + held-out annotations → baseline result → optional model adapter → schema/evidence validator → review console → export.
Local implementation proposal: Python/FastAPI with Pydantic contracts, SQLite run/review store, simple HTML/JS console. Model API calls only on server. No agent framework unless multiple tool steps demonstrably needed.
Domain and provider modules separate: `src/domain/`, `src/importers/`, `src/providers/`, `src/api/`, `src/ui/`. Evaluation in `evaluation/`; fixtures in `fixtures/`; prompts in `prompts/`; model/bounds in `config/`.
Cloud options: Vertex AI/Gemini vision adapter; Cloud Storage optional, tanpa kamera live. Cloud Run is deployment option; fixture mode must run without cloud credentials. Do not provision resources while doing baseline task.
Source content and model output are untrusted. [shared contracts](../../../docs/shared/runtime-contract.md) owns state/API limits; spec owns domain rules. Browser never holds provider keys.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
