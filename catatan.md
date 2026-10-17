# Google Cloud
Production (utama):
- https://c05-frontend-723420820074.asia-southeast2.run.app
Staging:
- https://c05-frontend-staging-723420820074.asia-southeast2.run.app

# Tech Stack
Frontend — Next.js 16, React 19, TypeScript, Tailwind CSS v4, shadcn/base-ui. Standalone server di Cloud Run, proxy server-side ke backend.
Backend — Python 3.12, FastAPI + uvicorn, Pydantic v2, Pillow, httpx. Satu service dengan adapter Crew/Admin/Agent di atas shared runtime shared_mvp.
AI — Gemini 2.5 Flash via Vertex AI (endpoint global, ADC bearer, thinking dimatikan). Output terstruktur lewat responseSchema, label meal_complete / missing_component / uncertain, confidence_score selalu null.
Data — Firestore (database c05prod/c05staging) untuk records, Cloud Storage untuk gambar, cache lokal untuk inference.
Infra — Cloud Run asia-southeast2 (2 service, scale-to-zero, maks 2 instance), Artifact Registry, service account least-privilege, Secret Manager tidak dipakai (workload identity).
Verifikasi — pytest, Playwright/Chromium (18 checks, 390px + 1440px), tsc, next build.

# Next Update
1. mungkin saya butuh bantuan untuk kira kira pipeline untuk trainingnya mas pada dataset sudah kita kumpulkan, anggap mbg pakai piring rumah masing masing mas haha
2. coba di scaffold aja mas, min. data pipeline nya mas
3. palingan sisa gemini api mas? bisa mas provide kah ?
4. sama gemini api ya mas, terserah providernya apa mas
5. gabung gabungin aja mas, misalkan ada orang yang mengaku *keracunan* mbg tapi jumlah nya terlalu banyak anggap saja mas, jadinya perlu detect apakah ini benar benar scam

# Update 16 Okt 2026
Status: sudah jalan & dites di lokal, **belum di-commit, belum di-deploy**.

## Poin 1–2 — Pipeline training (scaffold)
Folder: `projects/common/C05-visual-defect-detection/training/` (panduan lengkap di `training/README.md`).
- Format dataset: `manifest.jsonl` per foto → label, komponen yang hilang, jenis piring (`home_plate`, `bowl`, `tray_compartment`, `lunchbox`, `banana_leaf`), `group_id` (rumah tangga/sesi foto).
- `synth` — generator data sintetis "piring rumah masing-masing" (bentuk piring, motif, meja, blur/gelap/tertutup tangan). Hanya untuk tes alur, bukan ukur kualitas.
- `prepare` — validasi label, buang duplikat (persis & mirip), split train/validation/test **per rumah tangga** biar tidak bocor, ekspor ke format tuning Gemini di Vertex AI.
- `upload` → GCS, `tune` → buat tuning job (default dry-run, baru jalan kalau pakai `--submit`), `status` → cek job.
- `eval` — akurasi per label & per jenis piring, fokus ke recall `missing_component`.
- Prompt training memakai kode yang sama dengan inferensi live, jadi formatnya tidak bisa beda.
- Model hasil tuning tinggal dipasang lewat env `C05_GEMINI_ENDPOINT`, tanpa ubah kode.
- Sudah dijalankan dengan data sintetis (160 foto). Upload GCS & tuning job sungguhan **belum**.

## Poin 3–4 — Gemini API
- Sudah ada dari awal: provider bisa diganti lewat env `C05_GEMINI_PROVIDER=auto|gemini-api|vertex`.
- Production pakai Vertex (tagihan ke project GCP), jadi tidak perlu API key baru.
- Kalau mau jalur Gemini API: buat key sendiri di AI Studio, isi `GEMINI_API_KEY` di `.env` (jangan di-commit).

## Poin 5 — Deteksi klaim keracunan palsu
Halaman baru:
- `/report` — form publik lapor sakit setelah makan MBG (ada peringatan "ke Puskesmas / 119 dulu").
- `/claims` — konsol supervisor/admin, laporan dikelompokkan per dapur per hari.

Sinyal kejanggalan (masing-masing menunjuk klaim mana yang memicu):
- jumlah korban > porsi yang dikirim ke sekolah itu
- sekolah tidak dilayani dapur tersebut
- gejala muncul sebelum jam makan / lebih dari 72 jam setelahnya
- nomor HP sama, foto sama, kalimat copy-paste
- banyak laporan masuk dalam 15 menit

Aturan pengaman:
- Prioritas kesehatan (URGENT/HIGH/ROUTINE) dihitung terpisah, tidak pernah diturunkan oleh sinyal kecurigaan.
- Gemini hanya merangkum pola & saran verifikasi; tidak bisa ubah skor, tidak boleh pakai kata "scam/fake".
- Tutup kasus "tidak terbukti" hanya ADMIN, wajib alasan + konfirmasi korban sudah ditindaklanjuti medis, tidak bisa diubah lagi. Semua tercatat di audit trail.
- Nomor HP disimpan sebagai hash, foto hanya sidik jarinya, teks disamarkan sebelum dikirim ke Gemini.

Demo: login role ADMIN → `/claims` → "Load demo scenario". Isinya gelombang 32 klaim copy-paste (skor 100) vs outbreak realistis (skor 0, kesehatan URGENT).
Agent juga bisa ditanya soal klaim ("Any poisoning claims?").

## Perubahan lain
- Hapus decorator nyasar di `c05_api.py`.
- Prompt di `shared_mvp/provider.py` dipisah ke fungsi `build_prompt` (hasil identik, dipakai pipeline training).

## Hasil tes
- 70 tes unit lolos (termasuk 17 tes klaim + 9 tes pipeline baru), `verify_mvp` 8/8, `tsc` & `next build` lolos.
- Form laporan & konsol klaim sudah dicoba di browser.

## Belum / perlu dicek
- Ringkasan Gemini untuk klaim **belum dites ke Gemini sungguhan** (di lokal tidak ada kredensial → status `INFERENCE_BLOCKED`, halaman tetap jalan). Cek sekali setelah deploy ke staging.
- Model production `gemini-2.5-flash` **pensiun 20 Okt 2026**, di tengah masa penilaian juri (19 Okt–6 Nov).
- Dari review sebelumnya: agent masih regex+template (belum Gemini), data production masih sepi. (Teks Indonesia di UI & blok "Prerequisites" sudah beres — lihat Update UI di bawah.)
- Deadline submit: **18 Okt 2026** (deck PDF, video ±3 menit, prototype di Cloud Run, semua bahasa Inggris).

# Update UI & panduan (16 Okt 2026)
- Halaman baru **`/guide`** (menu "Guide"): tur 5 menit, hak akses tiap role, langkah per halaman, arti sinyal/warna/status, FAQ. Bahasa Inggris untuk juri.
- Panel **"How this page works"** (bisa dilipat) di Crew, Admin, Claims, Agent.
- Halaman depan: blok "Prerequisites" diganti "Open the guide" + 4 kartu langkah + link lapor sakit.
- Claims: kode sinyal diganti kalimat biasa (mis. `CLAIMS_EXCEED_PORTIONS` → "More people sick than meals served"), penjelasan muncul saat sinyal diklik, tiap tombol keputusan ada keterangannya.
- Crew: tombol "Gemini AI check" (default, direkomendasikan) & "Quick rule check" + keterangan; tips foto.
- Semua teks Indonesia di UI → Inggris (label manifest, saran pertanyaan agent, jawaban agent). `scripts/qa.mjs` ikut disesuaikan.
- Halaman Report: 3 langkah "apa yang terjadi setelah lapor".

# Panduan Penggunaan (Tutorial)
Buka aplikasi → menu **Guide** untuk versi lengkap (bahasa Inggris). Ringkasan untuk tim:

**Ganti peran & dapur** — pojok kanan atas: `Role` (CREW / SUPERVISOR / ADMIN) dan `Kitchen`. Peran reset ke SUPERVISOR kalau halaman di-refresh.

| Role | Bisa | Tidak bisa |
|---|---|---|
| CREW | foto & cek nampan | approve, lihat klaim |
| SUPERVISOR | + approve/reject, lihat klaim, eskalasi | menutup insiden |
| ADMIN | semua, termasuk tutup insiden & load demo | mengubah keputusan yang sudah final |

**1. Cek nampan (Crew)**
1. Pilih shift & batch → lihat daftar komponen wajib.
2. `Open camera` atau `Choose file` (JPEG/PNG, min 320×240, maks 4 MB).
3. Pilih **Gemini AI check** → `Run inspection`.
4. Hasil di kotak kuning = saran AI (UNVERIFIED). Kalau `uncertain` → foto ulang.

**2. Review (Admin, role SUPERVISOR/ADMIN)**
1. Lihat ringkasan angka di atas → filter antrian → `Open`.
2. Bandingkan temuan AI dengan komponen wajib.
3. Pilih ACCEPT / HOLD / REJECT → `Approve review` / `Reject review` (reject wajib komentar). Final & tercatat.

**3. Klaim keracunan (Claims, role SUPERVISOR/ADMIN)**
1. Role ADMIN → `Load demo scenario` (kalau daftar kosong).
2. Buka insiden: badge merah = prioritas kesehatan, bar "Conflicts" 0–100 = seberapa tidak cocok laporan dengan data pengiriman.
3. Klik sinyal di "What doesn't add up" → tabel menyaring laporan yang terkait.
4. `Analyze with Gemini` → ringkasan & saran verifikasi (butuh koneksi Gemini; di lokal muncul "not connected").
5. Ikuti "Required next steps" (selalu dimulai dari memastikan korban dapat perawatan).
6. Isi alasan → pilih keputusan. Tutup "unsubstantiated" hanya ADMIN + centang konfirmasi tindak lanjut medis.

**4. Lapor sakit (Report illness, publik)**
Pilih dapur, kode sekolah, tanggal makan, gejala, jam mulai, jumlah orang, nomor HP → `Send report` → simpan nomor referensi. Laporan langsung muncul di Claims.

**5. Agent**
Ketik pertanyaan atau klik saran, mis. "Summarize this kitchen's inspections", "Any poisoning claims?". Kotak abu-abu = sumber data. Usulan perubahan (kotak kuning) baru jalan setelah ADMIN konfirmasi.

**Skrip demo untuk video (±3 menit):** Guide → Crew (cek 1 foto dengan Gemini) → Admin (approve) → Claims (ADMIN, load demo, buka insiden skor 100, klik "More people sick than meals served", Analyze with Gemini, Escalate) → bandingkan dengan insiden skor 0 tapi URGENT → Report illness (kirim 1 laporan) → Agent "Any poisoning claims?".
# Update submission (16 Okt 2026, malam)
Fokus: semua poin di `submission.md`. Status & checklist lengkap ada di file itu.
- **Deck** (17 slide, urutan sesuai syarat): https://claude.ai/artifact/WEdEiWRDTF3rhvqnYUJguU → Download PDF. Isi placeholder `[...]` (nama tim, nama, peran, link video).
- **Agent sekarang Gemini function calling** (`src/c05_agent.py`): Gemini memilih tool read-only yang dibatasi role; jawaban tanpa tool / yang menuduh "scam/fake" ditolak → fallback ke router lama. UI menampilkan "Answered by Gemini" atau "Rule-based answer". Belum dites ke Gemini sungguhan (lokal tanpa kredensial).
- **Benchmark**: `python projects/common/C05-visual-defect-detection/evaluation/benchmark.py` → `evaluation/benchmark_report.json`. Optimasi deteksi copy-paste (1000 klaim: 2,8 s → ±1,3–2 s).
- **Deploy**: `deploy/deploy-update.sh staging|prod` (update service yang sudah ada, image by git SHA, smoke test otomatis). Harus dari mesin dengan gcloud + docker.
- **Video**: `apps/c05/scripts/demo-walkthrough.mjs <URL> --video` (rekam otomatis + caption) + naskah `docs/submission/DEMO_VIDEO_SCRIPT.md`.
- **Brief description** (bahasa Inggris) sudah di `submission.md` poin 6.
- Bug lama yang belum diperbaiki: tombol "Confirm" usulan agent selalu 404 (aksi tidak pernah disimpan).
