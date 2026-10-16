# Behavioral spec — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Depends on [PRD](prd.md), [data](data-design.md), [shared contracts](../../../docs/shared/runtime-contract.md).

## C05-BR-001 — baseline authority (FR-002)
Demo baseline pada gambar grayscale sintetis 64x64: defect bila ada pixel intensitas <32, region=bounding box seluruh pixel tersebut. Label eval terpisah. Ini detector fixture, bukan klaim inspeksi pabrik.
Jumlah/score/kapasitas dari kode, bukan teks model. Output stable sort sesuai aturan di atas.

## C05-BR-002 — AI boundary (FR-003/004)
Analisis visual sebagai kandidat detector kedua; jelaskan hanya area yang terlihat. Normal/defect/unknown; koordinat harus dalam bounds.
Jangan mengganti hasil baseline; keluaran AI pada bagian terpisah. Input tanpa sumber cukup menghasilkan status insufficient_evidence/insufficient_data sesuai kondisi, bukan jawaban tebakan.

## Invariants
- C05-INV-001 (NFR-001): tidak ada external write/action tool; review hanya mengubah record review internal.
- C05-INV-002 (FR-004): setiap evidence_id harus ada dalam authorized snapshot run.
- C05-INV-003 (FR-002/NFR-002): hasil baseline sama untuk input/config yang sama; test/eval label tidak masuk model context.
- C05-INV-004 (FR-005): edit output menaikkan revision dan membatalkan approval sebelumnya.
- C05-INV-005 (FR-006/NFR-003): operasi dibatasi server; provider unavailable menyisakan baseline dan status partial.

## Given / When / Then
- C05-SC-001 (FR-001/002): given happy fixture, when baseline run, then gambar putih 64x64 dengan kotak hitam x=10,y=20,w=5,h=4 => defect dan box yang sama; all-white => normal.
- C05-SC-002 (FR-006): given edge fixture, when run/import, then gambar korup => 422; gambar non-64x64 pada baseline => unsupported_dimensions, bukan resize diam-diam.
- C05-SC-003 (NFR-001/FR-003): given adversarial fixture, when AI/run, then asset_path ../secret => 422; teks instruksi pada gambar tidak memicu tool.
- C05-SC-004 (FR-005): given result revision 1, when export before review, then 409; approve then export succeeds; edit revision 2 then export 409 again.
- C05-SC-005 (FR-006/NFR-003): given provider timeout or invalid JSON, when AI run, then baseline intact, partial status, error code and no invented evidence.
