# Prototype Submission — Meal QC (team altuhraK)
1. Challenges :
- Manufacturing: Intelligent Operations & Industrial Efficiency

2. Prototype Link Deployed on GCP or Cloud run :
- Production (utama): https://c05-frontend-723420820074.asia-southeast2.run.app
- Staging: https://c05-frontend-staging-723420820074.asia-southeast2.run.app
- ⚠ Dicek 17 Okt: production DAN staging masih versi lama (belum "Meal QC"; /guide, /supply, /claims, /report = 404). Deploy dulu:
  `deploy/deploy-update.sh staging` → cek → `deploy/deploy-update.sh prod` (dari mesin yang punya gcloud + docker).
  Sekalian ganti model (gemini-2.5-flash pensiun 20 Okt): `GEMINI_MODEL=<id> deploy/deploy-update.sh ...`
- Nama service `c05-*` hanya nama teknis; produknya Meal QC.

3. Final Prototype PPT/Deck converted into PDF :
- Deck: docs/submission/altuhraK - Final Prototype Deck.pptx (template resmi) → PowerPoint: File › Export › PDF
- Deck .pptx sudah diisi semua slide Meal QC (17 Okt): ide 4 langkah, opportunities, 8 fitur, alur 3 jalur, mock trace bahan baku, arsitektur, teknologi, biaya, 6 snapshot, benchmark, future, links. Sisa: link YouTube di slide 14 (`[YouTube link]`), export PDF.
- Urutan wajib (15 slide template) dan isi yang harus mengikuti flow Meal QC terbaru:
  - Team Details — nama tim sudah "altuhraK"; **isi nama lengkap & peran** (placeholder `[...]`)
  - Brief about the idea — 3 masalah: bahan tidak tercatat (sebelum masak), cek makanan tidak tercatat (sebelum saji), laporan sakit sulit dicek (setelah saji)
  - Opportunities — a) different, b) how it solves, c) USP
  - List of features — termasuk lacak lot bahan (supplier, asal, jarak, suhu tiba, harga) + insight otomatis
  - Process flow diagram — Supply (catat & terima bahan) → Check meal (Crew) → Review (Supervisor) → Report illness (publik) → Illness reports / trace ke supplier
  - Architecture diagram — Cloud Run, Vertex AI Gemini, Firestore, Cloud Storage, IAM
  - Technologies — tabel layer/teknologi/layanan Google
  - Estimated implementation cost — dari docs/c05-deploy/COST_ESTIMATE.md
  - Snapshots of the prototype — Crew/Review, Claims, Outbreak/Report, Ingredient trace (screenshot lama dari versi lokal; ganti dari production setelah deploy bila sempat)
  - Prototype Performance report/Benchmarking — projects/common/C05-visual-defect-detection/evaluation/benchmark.py + bukti deploy
  - Additional Details/Future Development
  - Links — prototype, repo, **video `[YouTube link]`**

4. GitHub Repository Link (Public Access) :
- https://github.com/noiz354/altuhraK-ai-builder-cup-2026
- Kode Meal QC terbaru sudah di-push (main = origin/main). Yang belum di-commit: submission.md dan penghapusan catatan.md.

5. Demo Video Link (3-4 minutes) :
- [YouTube link — belum]
- Rekam otomatis (caption sudah "Meal QC", termasuk trace ke supplier): `cd apps/c05 && node scripts/demo-walkthrough.mjs <URL-production> --video --out demo-output`
- Naskah narasi: docs/submission/DEMO_VIDEO_SCRIPT.md

6. Brief Description of Your Solution (please include how you are leveraging Google services in your submission) :

Meal QC is food quality control and ingredient traceability for Indonesia's free school-meal programme (MBG), and for any food business. Each ingredient lot records supplier, origin, travel time, arrival temperature and price, so any meal traces back to its suppliers; automatic checks flag warm deliveries, expiring stock and overpricing. Before serving, crew photograph each tray; Gemini on Vertex AI checks it against the meal manifest and returns schema-validated JSON, then a supervisor accepts, holds or rejects. Illness reports from a public form are checked against delivery records and screened for fraud; Gemini explains patterns but never changes scores or closes cases. Every decision needs a written reason and lands in an audit trail.

Google services: Vertex AI Gemini (tray vision, incident summaries, supervised tuning), Cloud Run, Firestore (records, audit trail), Cloud Storage and Artifact Registry, via a least-privilege service account. People decide; every AI result is audited.
