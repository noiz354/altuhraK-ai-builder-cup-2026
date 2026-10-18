# C05 — Meal QC: Food Production Visual Quality Control
Status: runnable local MVP + deployed prototype. Claim status per row in [CLAIMS-REGISTER.md](CLAIMS-REGISTER.md).

Track: Sustainability / Social Impact (school-meal program). User: kitchen crew, supervisor, student.
Tujuan: memeriksa komponen piring makan (nasi/karbohidrat, protein, sayur) terhadap manifest versi
dari foto, lalu manusia yang memutuskan. Raman donor ingredient lot dan laporan sakit dari
kitchen/plate hingga lot pemasok, dengan verifikasi visual studentsaat makanan tiba.

**Visual only.** Tidak membuktikan keamanan mikrobiologis, komposisi gizi, atau berat terukur.

> The "Visual Defect Detection" framing in the historical text below is superseded by the
> submission deck. See the product-context note in [AGENTS.md](AGENTS.md).

## Read only what the task needs
Mulai [todo](todo.md), pilih satu task; baca [PRD](prd.md) sekali saat mulai proyek.
API: [spec](spec.md) + [API](api-contract.md) + [data](data-design.md).
Domain: spec + data + [fixtures](test-fixtures.md). AI: [AI design](ai-ml-design.md) + spec.
UI: PRD + API. Eval: [evaluation](evaluation-plan.md) + fixtures.
Shared rules: [AGENTS](AGENTS.md). Resume: [SESSION](SESSION.md).

MVP local synthetic fixture dulu; provider model optional untuk baseline, deployment task terpisah.
Data sintetis. Tidak mencakup pengukuran laboratorium, prediksi kondisi fisik makanan, atau
keputusan klinis.

## Local implementation

**Runnable local baseline available:** [local-mvp.md](local-mvp.md). Original text above records the proposed design. Current verification: [evaluation/results.json](evaluation/results.json).
