# Fixtures — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Implementation task must create actual fixture files plus expected baseline output; the descriptions here are exact intended cases, not executed tests.
Seed=42. Keep input fixture and oracle separate; model never sees expected labels/verdicts.
- `happy`: gambar putih 64x64 dengan kotak hitam x=10,y=20,w=5,h=4 => defect dan box yang sama; all-white => normal.
- `edge`: gambar korup => 422; gambar non-64x64 pada baseline => unsupported_dimensions, bukan resize diam-diam.
- `adversarial`: asset_path ../secret => 422; teks instruksi pada gambar tidak memicu tool.
- `invalid`: duplicated record ID, unknown field, missing required field, nonfinite quantity, invalid enum/time => 422 without processing.
- `provider_failure`: timeout/invalid JSON/fabricated evidence ID => partial, baseline retained, explicit error, no invented results.
- `review_revision`: before approval export 409; approved unchanged revision succeeds; edited revision invalidates approval.
Metric oracle: precision/recall defect dan IoU region pada holdout fixture. Synthetic generated images for image profiles; no network downloads necessary for baseline.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
