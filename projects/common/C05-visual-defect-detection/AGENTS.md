# Agent entry — C05

Read [shared agent rules](../../../docs/shared/agent-rules.md), then [README](README.md) and [todo](todo.md). Follow the current user's scope instructions.
These docs are proposed MVP decisions; they do not certify event eligibility or production readiness.
Authority: PRD scope → spec behavior → data/API contracts → task instructions. If inconsistent, fix the canonical contract before implementing dependent code.

## Product context authority (decided 2026-10-18)
The shipped product is a **school-meal kitchen QC system**, defined by the submission deck
`bugs/altuhraK - Final Prototype Deck.pptx.pdf`. The deck is the source of truth for *what the
product does*. This file, `README.md`, and the spec set were written earlier for a generic
manufacturing visual-defect-detection MVP and are being reconciled. Where an older doc still
describes "normal/defect", a production line, or a single product type, the deck wins and the doc
is stale — fix the doc rather than reverting the product.

Claim discipline is mandatory. Every deck claim must map to a reproducible check and be labelled
with exactly one of: `live-tested`, `deployed`, `synthetic`, or `prepared`. Never present
`prepared` as `deployed`, and never present `synthetic` as a field-accuracy claim. The known gap
list lives in [CLAIMS-REGISTER.md](CLAIMS-REGISTER.md).

Authentication is **not implemented**. The role and kitchen selectors are a client-side demo switch
(`apps/c05/src/components/providers.tsx`), and the backend trusts the client-supplied `role`
parameter. RBAC in the deck must be described as an in-app role switch, never as identity or
access control.
Do not read all 24 projects; do not read every local doc for one task. Select context from todo. Record result, files and next step in SESSION. Do not mark work complete without actual execution evidence.

## Local scope
- Project ID: C05
- Name: Meal QC — Food Production Visual Quality Control
- Track: Sustainability / Social Impact (school-meal program)
- Goal: memeriksa komponen piring makan (nasi/karbohidrat, protein, sayur) terhadap manifest versi terhadap foto, lalu manusia yang memutuskan
- AI scope: Gemini multimodal structured output per komponen + bounding box + confidence score estimasi. Output divalidasi server-side; TIDAK PERNAH auto-approve.
- Limitations: **Visual only.** Tidak membuktikan keamanan mikrobiologis, komposisi gizi, atau berat terukur. Data sintetis. Tidak mencakup prediksi kondisi fisik makanan, pengukuran laboratorium, atau keputusan klinis.

## Runtime commands
- Start QC service: `python projects/common/C05-visual-defect-detection/src/c05_entry.py` (port 8000)
- Start frontend: `cd apps/c05 && npm run dev` (port 3000)
- **Adapter tests (primary, covers `/api/inspections`, privacy, review, delivery):**
  `python -m pytest projects/common/C05-visual-defect-detection/tests/ -q`
- Shared pipeline tests (secondary; does NOT cover the C05 adapter):
  `python scripts/verify_mvp.py --project C05`
- Frontend: `cd apps/c05 && npm run lint && npx tsc --noEmit && npm run build`
- Browser: `cd apps/c05 && node scripts/e2e-provenance.mjs`

Do not present `scripts/verify_mvp.py` as evidence that the C05 adapter works. It exercises
`shared_mvp` datasets/runs only.

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
