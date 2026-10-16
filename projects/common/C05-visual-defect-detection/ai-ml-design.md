# AI/ML — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Task: Analisis visual sebagai kandidat detector kedua; jelaskan hanya area yang terlihat. Normal/defect/unknown; koordinat harus dalam bounds.
Non-AI authority: [BR-001](spec.md) — local generated PNG + pixel baseline + held-out annotations.
Input: minimal authorized records/evidence relevant to run params; exclude labels/hidden answers and unrelated portfolio context.
Output: [domain schema](data-design.md) inside shared response envelope. Parse structured JSON; validate IDs, numeric bounds, and evidence references; unsupported claim => needs_review or reject, not silent acceptance.
Prompt v1 sections: role/task; schema; relevant evidence IDs/content; no external facts; null/unknown policy. Put source content in delimited data, never as instructions. Store prompt version, model ID, configuration, usage and raw response for reproducibility; synthetic data only.
Provider selection is config, not a hardcoded alleged model version/price. For image/document profiles preserve page/region source links. Failure: one bounded schema repair at most, then partial with baseline intact. Mock output must be visibly labeled mock and never reported as live model evidence.
Measure AI benefit via [evaluation](evaluation-plan.md); do not require AI to outperform baseline without results.
