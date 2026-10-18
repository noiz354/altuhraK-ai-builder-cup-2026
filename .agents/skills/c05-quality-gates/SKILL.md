---
name: c05-quality-gates
description: "C05-specific quality gates for Food Production Visual QC. Use before declaring any C05 slice done: after changing src/domain.py, the Gemini provider path, review/approval logic, report export, evaluation, or before reporting a benchmark. Enforces confidence_score=null, ground-truth isolation, immutable approval, valid bounding boxes, the 192-test portfolio regression, and honest benchmark reporting."
---

# C05 Quality Gates

The invariants below are C05 product decisions locked in grill-me rounds 1-4. They are not
style preferences. Breaking one is a regression even if every test still passes.

## Gate 1 — Confidence is never fabricated

## Gate 1b — Confidence is an ESTIMATE, never a probability (amended 2026-10-18)

Gate 1 is superseded by this gate for the school-meal product. Rationale: the submission requires a
non-null confidence value, so the gate is amended here rather than silently violated.

`confidence_score` is a **model self-report / heuristic estimate** on a 0–1 scale.

- It is **not** a probability and **not** calibrated. Nothing may imply otherwise.
- Any surface rendering it must label it `ESTIMATE, NOT CALIBRATED` in the same visual block.
- **Forbidden**: a `%` sign; "95% sure"; traffic-light colouring that implies reliability;
  threshold language such as "above 0.8 is safe"; comparison across kitchens, images, or models.
- A confidence value **never** auto-approves. Gate 3 still governs approval.
- Do not extend confidence rendering to a new surface without amending this gate again.
- A real calibration study needs its own gate plus a documented method before any wording may call
  the value a probability.

Enforced by `src/domain.py`:
`require(isinstance(confidence_score, (int, float)) and 0 <= confidence_score <= 1)`.
Removing that guard is a regression, not a relaxation.

## Gate 1c — Ground truth still never reaches inference

- `annotations` and adjudication labels must be absent from any Gemini request payload.
- A dataset used for scoring is never the dataset used for inference.
- Synthetic and real metrics are reported separately and never summed into one accuracy figure.

## Gate 2 — Ground truth never reaches inference

- `annotations`, evaluation manifests, and expected labels stay out of the Gemini request payload.
- `shared_mvp.domain.evidence()` strips label fields; do not bypass it.
- A dataset used for scoring is not the dataset used for inference.
- Synthetic and real metrics are reported separately and never summed into one accuracy figure.

## Gate 3 — Approval is immutable and human-only

- Execution status (`CREATED/QUEUED/RUNNING/COMPLETED/FAILED`) and review status
  (`UNVERIFIED/REVIEW_PENDING/APPROVED/REJECTED`) are separate fields. Never collapse them.
- `CREW` can never approve or reject. Enforce in the backend, not in the UI.
- Once `APPROVED` or `REJECTED`, the record is immutable. Re-inference creates a new revision
  (`revision + 1`) and resets review status. It never overwrites.
- Rejection requires a comment.
- `qc_disposition` (`ACCEPT/HOLD/REJECT`) is a separate field from the review decision.
- Audit rows are append-only (`store.append`). Never update or delete them.

## Gate 4 — Provider failure is never a success

- A provider error, timeout, invalid JSON, invalid label, or out-of-bounds box yields
  `partial`/`FAILED` with `review_status` staying `UNVERIFIED` and `prediction` cleared.
- Never fall back to "assume complete" or any other optimistic default.
- Dummy-key `provider_error` proves failure handling only. It is **not** live inference evidence.

## Gate 5 — Bounding boxes are validated, not trusted

- Gemini native format is `box_2d = [ymin, xmin, ymax, xmax]`, normalized integers 0–1000.
- The server validates length, integer type, range, and positive area, then converts to
  source-image pixels using verified dimensions.
- EXIF orientation must be normalised before dimensions are trusted.
- A geometrically valid box is still an unverified prediction, not proof of correct localization.

## Gate 6 — Scope claims

The product must never claim, in UI copy, exports, decks, or agent answers, that a photo
establishes microbiological safety, nutritional composition, or measured food weight. This is a
product boundary, not a disclaimer nicety.

## Gate 7 — Regression before done

**Single-product repos** (`altuhraK-ai-builder-cup-2026`, the deployed target). Amended 2026-10-18:
`verify_all_mvp.py` does not exist here because the repo ships one project, not the 24-project
portfolio. Do not copy the portfolio runner in; that would test code this product does not own.

```sh
python -m pytest projects/common/C05-visual-defect-detection/tests/ -q   # adapter: API, privacy, review, delivery
python scripts/verify_mvp.py --project C05                              # shared pipeline: expect 8/8
cd apps/c05 && npm run lint && npx tsc --noEmit && npm run build
cd apps/c05 && node scripts/qa.mjs                                     # expect 16/16, 0 console errors
cd apps/c05 && node scripts/e2e-provenance.mjs                          # expect 18/18
```

`scripts/verify_mvp.py` covers `shared_mvp` datasets/runs only. It is **never** acceptable as proof
that a C05 adapter endpoint works; the pytest command is the primary evidence.

**Multi-project repos** (`sea-ai-hackathon`). Changing `shared_mvp/` affects all 24 projects, so the
portfolio run is mandatory there:

```sh
python scripts/verify_mvp.py --project C05     # expect 8/8
python scripts/verify_all_mvp.py               # expect 24/24 projects, 192/192
```

## Gate 8 — Honest reporting

Report these three separately, never merged:

1. **Implemented** — code exists.
2. **Tested** — a command ran and produced this output.
3. **Deployed** — a real URL responds.

A `BLOCKED` verdict with the reason is a valid and preferred outcome over a fabricated `PASS`.
If live Gemini was not exercised with a real key, say so. If a storage figure was assumed rather
than measured, say so. The 10 GB storage budget is a cap; actual usage must come from a real read.

## Gate 9 — Skills and memory are loaded, not assumed

No C05 slice is done unless the skills behind it were actually loaded and the
memory loop was actually run:

- Before acting: load every skill in the routing table below that matches the
  task, via the native skill tool by exact ID. A skill directory existing is
  not loading; `C05-SKILL-MATRIX.md` tracks loaded-vs-installed separately.
- Before acting: `recall` (or `memory_recall`) for the C05 project and the area
  touched. Prior sessions hold the retired model IDs, dead endpoints, and the
  false-success traps; skipping recall re-pays those costs.
- After a decision, root cause, or rejected approach: `remember` (or
  `memory_save`) with files, command, and measured result. Corrections become
  `lesson` entries.
- The completion summary names each skill ID loaded and each memory entry
  saved. A summary that cannot name them did not do them.

## Quick self-check

- [ ] No confidence percentage rendered anywhere; every confidence surface says `ESTIMATE, NOT CALIBRATED`
- [ ] Annotations and adjudication labels absent from any provider payload
- [ ] Crew cannot approve; approved records immutable
- [ ] Provider error leaves the record UNVERIFIED with no prediction
- [ ] Boxes validated and converted server-side
- [ ] No food-safety or nutrition claim
- [ ] Reporter contact stored only as blind index; no cleartext anywhere
- [ ] Repo-appropriate regression suite green (Gate 7 branch for this repo)
- [ ] Implemented / tested / deployed reported separately
- [ ] Every skill below matching the task was loaded by exact ID (named in summary)
- [ ] Memory recalled before, saved after (entries named in summary)