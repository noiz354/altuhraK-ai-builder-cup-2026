# Demo video — narration script (3–4 minutes)

Recording: `cd apps/c05 && node scripts/demo-walkthrough.mjs <production-url> --video --out demo-output`
produces `demo-output/demo-walkthrough.webm` (1440×900, on-screen captions). Read the narration
below over it, or trim and re-time it in any editor. Upload to YouTube as **Unlisted** or **Public**.

Run it against **staging first**. Each run writes one inspection, one review, one decision and one
test report into that environment's data.

| # | On screen | Narration (English) |
|---|---|---|
| 1 | Home | "School-meal kitchens have two blind spots: incomplete trays that leave unnoticed, and illness reports nobody can check against the facts. C05 closes both on Google Cloud." |
| 2 | Guide | "Anyone can start here: a five-minute guide explains every page, role and signal in plain language." |
| 3 | Crew — photo | "The kitchen crew photographs a tray. The manifest lists what every tray must contain. This one has rice and protein, but the vegetable compartment is empty." |
| 4 | Crew — Gemini check | "Gemini 2.5 Flash on Vertex AI checks the photo and returns structured JSON. Our validator rejects anything off-contract, and the result stays UNVERIFIED with full provenance — model, latency, request ID." |
| 5 | Admin | "The supervisor sees live KPIs that separate real model inferences from fallbacks, opens the finding, puts the batch on HOLD and approves the review. Decisions are final and audited." |
| 6 | Claims — incident | "Now the harder problem. Illness reports are grouped by kitchen and day. Here: 35 reports and 340 people affected — but this kitchen served only 230 portions to that school. Health priority stays URGENT regardless." |
| 7 | Claims — signal | "Each conflict is a plain-language signal. One click shows the exact reports behind it: one template, three phone numbers, one reused photo." |
| 8 | Claims — Gemini | "Gemini reads the reports, with phone numbers masked, and explains the pattern with suggested checks. It cannot change the score, accuse anyone, or close the case." |
| 9 | Claims — decision | "The supervisor escalates to the health office with a written reason. Closing a case as unsubstantiated needs an admin and confirmed medical follow-up." |
| 10 | Claims — outbreak | "Compare a real outbreak: no conflicts, clinic visits, a hospital admission. Same engine — this one goes straight to the health office." |
| 11 | Report illness | "Parents and teachers report from any phone. Care comes first: the form points to the Puskesmas and 119. Phone numbers are stored only as a hash." |
| 12 | Agent | "Finally, the operations agent. Gemini function calling picks role-scoped, read-only tools and answers in plain language — every tool call is shown." |
| 13 | Closing | "C05: Gemini sees and explains, people decide, everything is audited — on Cloud Run, Vertex AI, Firestore and Cloud Storage." |

If the recording runs long, cut the pauses in steps 2 and 10 first.
