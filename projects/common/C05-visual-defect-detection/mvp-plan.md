# MVP plan — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Deliver one fixture-to-reviewed-export flow for inspektur kualitas produk.
Order: schema+fixtures → baseline → API → console → AI adapter → adversarial validation → review/export → optional deployment.
Must retain [BR-001](spec.md), evidence validation, review revision, bounded inputs, failure behavior.
Cut first: styling, dashboards, extra languages/formats, cloud adapters, extra datasets. If AI unavailable, finish baseline and label AI pending; not a completed GenAI submission.
Do not build: kamera live, reject lini produksi, generalisasi ke semua cacat.
Open domain decision: Produk/cacat apa dan dataset gambar berizin apa yang tersedia?
No promised schedule/team size/deadline; choose tasks from [todo](todo.md) and record evidence.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
