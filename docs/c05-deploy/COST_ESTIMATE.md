# C05 Cost Estimate

Date: 2026-10-16 · Billing account `012515-52824D-3783CD` is **open**; remaining
credit balance is **UNKNOWN** (not exposed via CLI — check the console credits page).
Budgets `daily-2usd-envelope-IDR` (~IDR 960k) and `Hackathon-Guardrail-IDR`
(~IDR 2.4M) exist as **alerts, not caps**.

Assumptions: asia-southeast2, 2 services, 1 vCPU / 512 Mi per service,
min 0 / max 2, ~30 deployment + demo days left on credits. Gemini 2.5-flash
pricing moves; verify before budgeting inference.

| Scenario | Cloud Run (idle→light) | AR (<1 GB) | Logging | Gemini (~200 calls) | Monthly total |
|---|---|---|---|---|---|
| Low (demo, few runs/day) | $0–2 | <$0.10 | ~$0 | ~$1–3 | **~$2–5** |
| Medium (evaluators, daily use) | $3–8 | <$0.50 | ~$0.50 | ~$5–15 | **~$10–25** |
| High (always-warm, heavy use) | $15–40 | ~$1 | ~$2 | ~$30+ | **~$50+** |

## Cost controls actually configured

- Scale-to-zero (`--min-instances=0`): no idle CPU billing.
- `--max-instances=2`: a runaway cannot scale past 2 instances per service.
- `--concurrency=4`, `--timeout=300s`, `--cpu=1 --memory=512Mi`: bounded per request.
- No Cloud SQL, no always-on VMs, no load balancer: $0 fixed infra.
- Staging services get deleted or scaled to zero after verification.

## Major risks

1. **Gemini inference dominates** if evaluators hammer the demo; each multimodal
   call is ~2.1k input tokens with 7–21 s latency. No per-user rate limit exists.
2. **Credits expire 2026-10-22** (recorded). Anything running past that bills the
   linked payment method.
3. **Durable persistence (BLOCKED item) will add cost** — Firestore or Cloud SQL
   changes this sheet; re-estimate before provisioning.

Pricing references: cloud.google.com/run/pricing, cloud.google.com/artifact-registry/pricing,
docs.cloud.google.com/gemini-enterprise-agent-platform pricing page. Free tier covers
the first 2M Cloud Run requests/month; this deployment will not approach it.
