# Demo video — narration script (3–4 minutes)

Recording: `cd apps/c05 && node scripts/demo-walkthrough.mjs <production-url> --video --out demo-output`
produces `demo-output/demo-walkthrough.webm` (1440×900, on-screen captions). Read the narration
below over it, or trim and re-time it in any editor. Upload to YouTube as **Unlisted** or **Public**.

Run it against **staging first**. Each run writes one inspection, one review, one decision and one
test report into that environment's data.

The rows follow the walkthrough's on-screen captions in order.

| # | On screen | Narration (English) |
|---|---|---|
| 1 | Home | "School-meal kitchens have three blind spots: nobody knows where the ingredients came from, trays are checked by eye and never recorded, and illness reports can't be checked against the facts. Meal QC traces every ingredient from supplier to plate, checks every tray, and handles illness reports fairly." |
| 2 | Guide | "Anyone can start here: a built-in guide explains every page, role and signal in plain language." |
| 3 | Check meal — photo | "The kitchen crew photographs a tray. The manifest lists what every tray must contain. This one has rice and protein, but the vegetable compartment is empty." |
| 4 | Check meal — result | "Behind the scenes, Gemini on Vertex AI checks the photo and returns validated, structured output. It is never auto-approved: the result arrives marked not yet reviewed, with an audit trail." |
| 5 | Review | "The supervisor sees live counts of checks waiting for a decision, compares the result with the meal list and records a disposition. Decisions are final and audited." |
| 6 | Illness reports — incident | "After serving, illness reports are grouped by kitchen and day and checked against what was actually served. Here: 35 reports and 340 people affected, but this kitchen served only 230 portions to that school." |
| 7 | Illness reports — signals | "Each conflict is a plain-language signal, and health priority stays URGENT regardless. One click shows the exact reports behind it: one template, three phone numbers, one reused photo." |
| 8 | Illness reports — Gemini | "Gemini explains the pattern and suggests checks. It cannot change the score, accuse anyone, or close the case." |
| 9 | Illness reports — decision | "Every decision needs a written reason and lands in the audit trail. Closing a case needs confirmed medical follow-up first." |
| 10 | Real outbreak | "Compare a real outbreak: no conflicts, clinic visits, one hospital admission. Same engine — this one is escalated now." |
| 11 | Trace to supplier | "And it is traced in one click: that day's chicken came 145 km from a trader with no cold chain and arrived at 11.5 °C." |
| 12 | Report illness | "Parents and teachers report from any phone. Care comes first: the form points to the Puskesmas and 119. Phone numbers are stored only as a hash, and the report joins today's incident instantly." |
| 13 | Closing | "Meal QC: Gemini works behind the scenes, people decide, everything is audited — built on Cloud Run, Vertex AI, Firestore and Cloud Storage." |

If the recording runs long, cut the pauses in steps 2 and 10 first.
