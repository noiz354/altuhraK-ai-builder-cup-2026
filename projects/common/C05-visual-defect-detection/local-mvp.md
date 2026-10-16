# C05 — runnable local MVP

Status: **LOCAL_BASELINE_VERIFIED**. This is a local implementation slice, not a claim that every original production/hackathon requirement is complete.

From repository root:
```sh
python -m pip install -r requirements.txt
python run.py --project C05 --port 8000
```
Open http://127.0.0.1:8000. Load the synthetic sample, run baseline, inspect evidence, approve current revision, download JSON. Draft edits invalidate approval. Run/evidence/review history persist in SQLite outside the repository (default temporary-directory `sea-ai-mvp/C05.sqlite`).

Independent project entry: `python /home/norman2/13-10-26-ai-builder-cup-26/sea-ai-hackathon/projects/common/C05-visual-defect-detection/src/app.py` from the repository checkout. Shared runtime is required; this project is not a standalone copied directory.

## Implementation and evidence

- `src/domain.py`: project-specific validator/algorithm.
- `config/project.json`: typed-schema source; strict models compiled without eval.
- `fixtures/sample.py`: offline synthetic sample generator.
- `tests/acceptance.py`: project-specific oracle and edge cases.
- Shared API/console/store/provider in `shared_mvp/`; prompt v1 in `prompts/v1.md`.
- `python scripts/verify_mvp.py --project C05`: **8 tests passed**, result in [evaluation/results.json](evaluation/results.json).
- Verified scope: local synthetic baseline/API/UI assets/review/export/provider adapter. Unit/ASGI workflow verified; visual browser validation is recorded separately when performed.

## AI and limits

Set `GEMINI_API_KEY` and `GEMINI_MODEL` in the server environment to use the REST adapter. Credentials stay server-side. Actual model/API availability must be verified by the operator; no specific model version is assumed.
Without configuration, AI mode returns a clearly marked partial result with baseline retained. Test adapter returns are labeled `TEST_ADAPTER`, provider_called=false. **No live model result or baseline-vs-live-AI benchmark has been measured.**
This slice uses AI to augment/explain existing baseline result. Advanced generation, forecasting, visual classifiers and external integrations in the proposed specs may require further work; synthetic fixture success proves local mechanics only.
No external dataset/license download, cloud deployment, production authentication, real personal data or consequential action is included. Server binds loopback and rejects cross-origin requests. Public deployment requires the separate deployment gate and durable storage design.
