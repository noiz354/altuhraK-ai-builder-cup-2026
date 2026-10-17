# Prototype Submission
1. Challenges :
- Manufacturing: Intelligent Operations & Industrial Efficiency

2. Prototype Link Deployed on GCP or Cloud run :
- Production (utama): https://c05-frontend-723420820074.asia-southeast2.run.app
- Staging: https://c05-frontend-staging-723420820074.asia-southeast2.run.app
- ⚠ Production masih versi lama (tanpa Claims / Report / Guide / agent Gemini). Deploy dulu:
  `deploy/deploy-update.sh staging` → cek → `deploy/deploy-update.sh prod` (dari mesin yang punya gcloud + docker).

3. Final Prototype PPT/Deck converted into PDF :
- Deck: https://claude.ai/artifact/WEdEiWRDTF3rhvqnYUJguU → Download → PDF
- Isi sudah mengikuti urutan wajib (17 slide):
  - Team Details — **isi nama tim, nama lengkap & peran** (placeholder `[...]`)
  - Brief about the idea — slide "The problem" + "The idea"
  - Opportunities — a) different, b) how it solves, c) USP
  - List of features — 8 fitur
  - Process flow diagram — 2 alur (tray QC & illness claims) + learning loop
  - Architecture diagram — Cloud Run, Vertex AI Gemini, Firestore, Cloud Storage, IAM
  - Technologies — tabel layer/teknologi/layanan Google
  - Estimated implementation cost — dari docs/c05-deploy/COST_ESTIMATE.md
  - Snapshots of the prototype — 4 slide, 8 screenshot (ganti screenshot Crew setelah deploy, lihat catatan)
  - Prototype Performance report/Benchmarking — evaluation/benchmark.py + bukti deploy
  - Additional Details/Future Development
  - Links — prototype, repo, **video `[YouTube link]`**

4. GitHub Repository Link (Public Access) :
- https://github.com/noiz354/altuhraK-ai-builder-cup-2026
- ⚠ Perubahan baru belum di-commit/push.

5. Demo Video Link (3-4 minutes) :
- [YouTube link — belum]
- Rekam otomatis: `cd apps/c05 && node scripts/demo-walkthrough.mjs <URL-production> --video --out demo-output`
- Naskah narasi: docs/submission/DEMO_VIDEO_SCRIPT.md

6. Brief Description of Your Solution (please include how you are leveraging Google services in your submission) :

C05 is a quality-control and claim-integrity platform for school-meal kitchens such as those in Indonesia's free-meal programme (MBG). It covers the whole meal lifecycle. Before a meal leaves, kitchen crew photograph each tray. Gemini 2.5 Flash on Vertex AI compares the photo with a versioned meal manifest and returns structured JSON (meal_complete, missing_component or uncertain). A domain validator rejects anything off-contract, and a supervisor accepts, holds or rejects the batch. After the meal is eaten, parents and schools can report illness through a public, care-first form. Reports are grouped by kitchen and day and checked against delivery records: portions served, serving time, and which schools were served. The check also looks for shared phone numbers, reused photos, copy-paste wording and submission bursts. Gemini then explains the pattern in plain English and suggests verification steps. It cannot change the score, accuse reporters or close a case. Health priority is computed separately and is never lowered. An operations agent built on Gemini function calling answers supervisors' questions using role-scoped, read-only tools, and every tool call is shown.

Google services: Vertex AI Gemini for multimodal inspection with responseSchema, for incident summaries and for agent function calling. A Vertex AI supervised-tuning pipeline (dataset in Cloud Storage) adapts the model to household plates. Cloud Run hosts the Next.js frontend and the FastAPI backend, with scale-to-zero. Firestore stores records and the append-only audit trail, Cloud Storage holds images, and Artifact Registry holds the container images. A least-privilege service account authenticates through Application Default Credentials, so no API key exists. People make every decision, and every AI result carries its provenance.

# Checklist sebelum submit (deadline 18 Okt 2026)
- [ ] Isi Team Details di deck (nama tim, nama, peran)
- [ ] Deploy: `deploy/deploy-update.sh staging`, smoke PASS, lalu `prod`
- [ ] Ganti model jika perlu sebelum 20 Okt (gemini-2.5-flash pensiun): `GEMINI_MODEL=<id> deploy/deploy-update.sh prod`
- [ ] Production: Claims → role ADMIN → Load demo scenario
- [ ] Rekam video dari production, tambah narasi, upload YouTube (Unlisted/Public), isi link di deck & di sini
- [ ] Ganti screenshot Crew di deck dengan hasil Gemini dari production (opsional, lebih kuat)
- [ ] Export deck → PDF
- [ ] Commit + push ke GitHub (repo publik)
- [ ] Share deck jika perlu dilihat orang lain (artifact masih privat)

# Pitch Deck
1. AI-Powered Food Inspection — Mendeteksi potensi ketidaklengkapan komponen makanan secara otomatis melalui foto, sehingga proses Quality Control lebih cepat dan efisien.
2. Human-in-the-Loop Verification — Menggabungkan analisis AI dengan verifikasi manusia untuk memastikan keputusan QC tetap akurat, transparan, dan dapat dipertanggungjawabkan.
3. End-to-End Quality Management — Mengintegrasikan Crew App, Admin Dashboard, dan Agentic AI dalam satu platform untuk memantau kualitas makanan di berbagai dapur.
4. Transparent & Auditable AI — Setiap hasil inspeksi memiliki riwayat, status persetujuan, dan sumber prediksi yang dapat ditelusuri, termasuk ketika AI gagal atau menghasilkan ketidakpastian.
5. Data-Driven Quality Improvement — Membangun fondasi dataset dan machine learning untuk meningkatkan akurasi deteksi, mengidentifikasi pola masalah, dan mendukung pengambilan keputusan berbasis data.
6. ~~Butuh feedback loop, misalkan incident atau student report page sekarang~~ → sudah: halaman `/report` + `/claims` (claim integrity).
