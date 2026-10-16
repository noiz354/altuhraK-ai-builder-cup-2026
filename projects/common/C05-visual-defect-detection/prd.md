# PRD — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Persona: inspektur kualitas produk. Job: menandai cacat visual pada satu jenis produk untuk review inspektur.
Journey: pilih fixture/input → lihat baseline → jalankan AI bila dikonfigurasi → bandingkan bukti/hasil → review → export.
Desain memakai profile `image`; scope baru ini belum merupakan validasi produk/kelayakan submission.

| ID | Must behavior | Acceptance |
|---|---|---|
| C05-FR-001 | Import/validate schema | Input valid mendapat dataset_id; invalid 422 |
| C05-FR-002 | Baseline deterministic | Hasil cocok [fixture](test-fixtures.md), tanpa model |
| C05-FR-003 | AI task: Analisis visual sebagai kandidat detector kedua; jelaskan hanya area yang terlihat. Normal/defect/unknown; koordinat harus dalam bounds. | Output schema/evidence valid atau partial |
| C05-FR-004 | Bandingkan dan tampilkan evidence | Baseline/model terpisah, sumber dapat dibuka |
| C05-FR-005 | Review sebelum export | Review tercatat per revision; tanpa review export 409 |
| C05-FR-006 | Invalid/empty/timeout handling | Tidak fabrikasi hasil saat evidence kurang |
| C05-NFR-001 | Privacy/tool boundary | Synthetic only, tanpa aksi eksternal/secret di client |
| C05-NFR-002 | Reproducibility | Seed/config/version dan output disimpan |
| C05-NFR-003 | Bounded operation | Batas run/calls/bytes ditegakkan server |
| C05-NFR-004 | Meaningful evaluation | precision/recall defect dan IoU region pada holdout fixture |

Non-goals: kamera live, reject lini produksi, generalisasi ke semua cacat.
Success targets adalah usulan internal di [evaluation](evaluation-plan.md), bukan measured results.
