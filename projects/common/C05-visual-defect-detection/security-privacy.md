# Security/privacy — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Apply [shared security](../../../docs/shared/security.md); invariants in [spec](spec.md).
Domain abuse case: asset_path ../secret => 422; teks instruksi pada gambar tidak memicu tool.
Consequence boundary: kamera live, reject lini produksi, generalisasi ke semua cacat.
Data source choice: synthetic and generated assets for MVP. Real data/license/consent, authentication, retention and legal review are production extensions, not verified compliance claims.
API authorization for local fixture mode is single-user loopback. Public demo requires gate, rate/cost limits and isolation before deployment. Review does not authorize any external action.
Test before public demo: attempted traversal, unknown source IDs, injection in source, oversized input, stale approval. No credentials or raw real-world personal data in fixtures/logs.

## Storage policy (C05)
- Hard cap: 10 GB total for datasets, model artifacts, logs, demo assets, caches, and experiments.
- Synthetic fixtures only unless a licensed dataset is explicitly added with source and license.
- Do not commit binaries, checkpoints, image caches, or generated exports exceeding the cap.
- Remove or regenerate interim artifacts before adding new data.
