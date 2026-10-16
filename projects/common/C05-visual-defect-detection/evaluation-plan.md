# Evaluation — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Domain metrics: precision/recall defect dan IoU region pada holdout fixture.
Baseline: [BR-001](spec.md). Compare model-assisted result on same snapshot, tasks and holdout; report support/error counts and denominators.
Proposed structural targets: happy/edge/security fixture assertions all pass; zero unresolved evidence IDs; zero external writes; model-disabled baseline deterministic; stale review cannot export. These are proposed acceptance gates, not measured outcomes.
No numerical model-quality target until a relevant labeled set and review rubric exist. Synthetic fixture success does not prove industry accuracy or social impact. Temporal profiles use chronological holdout; image/classification keep labels outside inference; extraction profiles score field-level precision/recall; retrieval record expected source IDs.
Record seed, split IDs, baseline config, model/prompt versions, actual tokens, latency and errors in `evaluation/results.json`. Never estimate tokenizer counts as billed usage. User benefit measured separately by reviewer task completion/correction time where reviewers are available; otherwise unavailable.
