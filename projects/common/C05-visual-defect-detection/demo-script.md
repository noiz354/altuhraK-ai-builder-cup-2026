# Demo — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Suggested 150-second storyboard, not an organizer time requirement:
0–20s: introduce inspektur kualitas produk and goal.
20–55s: load happy fixture; display baseline. Expected: gambar putih 64x64 dengan kotak hitam x=10,y=20,w=5,h=4 => defect dan box yang sama; all-white => normal.
55–95s: optional AI result, show evidence and distinction from baseline; if unavailable show visibly labeled recorded/mock result.
95–120s: edge case: gambar korup => 422; gambar non-64x64 pada baseline => unsupported_dimensions, bukan resize diam-diam.
120–140s: approve current revision then export; edit and show approval invalidation.
140–150s: actual evaluation results and limitations; no scores or impact metrics without measurement.
Use synthetic identifiers and fixtures; no live consequential action.
