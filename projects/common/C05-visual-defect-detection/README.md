# C05 — Visual Defect Detection
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Track: Manufacturing. User: inspektur kualitas produk.
Tujuan: menandai cacat visual pada satu jenis produk untuk review inspektur.

## Read only what the task needs
Mulai [todo](todo.md), pilih satu task; baca [PRD](prd.md) sekali saat mulai proyek.
API: [spec](spec.md) + [API](api-contract.md) + [data](data-design.md).
Domain: spec + data + [fixtures](test-fixtures.md). AI: [AI design](ai-ml-design.md) + spec.
UI: PRD + API. Eval: [evaluation](evaluation-plan.md) + fixtures.
Shared rules: [AGENTS](AGENTS.md). Resume: [SESSION](SESSION.md).

MVP local synthetic fixture dulu; provider model optional untuk baseline, deployment task terpisah.
Belum ada code, riset pasar terverifikasi, dataset eksternal, atau hasil benchmark.
Tidak mencakup: kamera live, reject lini produksi, generalisasi ke semua cacat.

## Local implementation

**Runnable local baseline available:** [local-mvp.md](local-mvp.md). Original text above records the proposed design. Current verification: [evaluation/results.json](evaluation/results.json).
