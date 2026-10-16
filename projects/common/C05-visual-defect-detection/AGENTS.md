# Agent entry — C05

Read [shared agent rules](../../../docs/shared/agent-rules.md), then [README](README.md) and [todo](todo.md). Follow the current user's scope instructions.
These docs are proposed MVP decisions; they do not certify event eligibility or production readiness.
Authority: PRD scope → spec behavior → data/API contracts → task instructions. If inconsistent, fix the canonical contract before implementing dependent code.
Do not read all 24 projects; do not read every local doc for one task. Select context from todo. Record result, files and next step in SESSION. Do not mark work complete without actual execution evidence.

## Local scope
- Project ID: C05
- Name: Visual Defect Detection
- Track: Manufacturing
- Goal: menandai cacat visual pada satu jenis produk untuk review inspektur
- AI scope: Analisis visual sebagai kandidat detector kedua; jelaskan hanya area yang terlihat. Normal/defect/unknown; koordinat harus dalam bounds.
- Limitations: Data sintetis; belum divalidasi untuk penggunaan nyata. Tidak mencakup: kamera live, reject lini produksi, generalisasi ke semua cacat

## Runtime commands
- Start: `python run.py --project C05 --port 8000`
- Test: `python scripts/verify_mvp.py --project C05`
- Syntax sanity: `python -m py_compile src/domain.py`

## Environment variables (dummy or real values supplied by operator; never commit secrets)
- `GEMINI_API_KEY`: optional for live provider; leave unset for deterministic baseline.
- `GEMINI_MODEL`: optional; use an existing Gemini model ID, e.g. `gemini-2.0-flash`.
- `DEMO_ACCESS_GROUP`: optional for C11; default is `A`.
- Do not hardcode or commit these values.

## Skill routing for this project
- Global routing: `~/.config/opencode/AGENTS.md`.
- Matt skills when linked: `tdd`, `diagnosing-bugs`, `codebase-design`, `grill-with-docs`, `to-spec`, `to-tickets`.
- Google stack skills where relevant: `firebase-*`, `gcloud`, `golang-*`, `context7`.
- Vercel Labs skills only after verifying exact IDs in the active runtime; otherwise use installed equivalents and report the fallback.

## Agent memory (mandatory)

The `agentmemory` MCP server is this project's cross-session record.

- **Before acting:** `agentmemory.memory_recall` for this project id and the area you are
  touching, and before any change to `shared_mvp/`. Prior sessions record dead ends, retired
  model ids, and dead endpoints that current code does not reveal.
- **Before reporting completion:** `agentmemory.memory_save` when a change matters — a root
  cause, a file/signature/config/env change, a contract or invariant change, a wrong dependency,
  model id, endpoint or quota, a changed verification result, or a rejected approach.
- Record negatives as carefully as positives, with file paths, the exact command, and the
  measured result.
- Never store secrets. Record that a credential exists and how to obtain it, never its value.
- A memory is a claim. Save it as BLOCKED or UNKNOWN if it is not substantiated by an executed
  check. A passing suite is not proof of live inference, deployment, or production readiness.

## Verification expectation
- Run the project test command before claiming completion.
- Report executed vs proposed checks and any live-model or browser validation not performed.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
