# C05 Skill Integration Matrix

Scope: `projects/common/C05-visual-defect-detection/**`, `apps/c05/**`, and any `shared_mvp/` change
that affects them. Verified against the live registries, not assumed from documentation.

## Installed — project scope (`.agents/skills/`)

| Skill ID | Source repo | Why C05 needs it | Status 2026-10-16 |
|---|---|---|---|
| `gemini-api-dev` | `google-gemini/gemini-skills` | Live multimodal inference, structured output, function calling | listed earlier; not re-verified this session |
| `agent-platform-inference` | `google/skills` | Only if C05 moves to Vertex AI / Gen AI SDK with ADC | listed earlier |
| `cloud-run-basics` | `google/skills` | Deploy the QC API and the inspection worker | **INSTALLED + LOADED** (catalog of 163 skills, verified by name) |
| `gcloud` | `google/skills` | Guardrails for every gcloud invocation | **INSTALLED + LOADED** (SKILL.md read; leaf-help + quiet + datar-planning rules adopted) |
| `cloud-logging-query-generation` | `google/skills` | LQL for Cloud Run diagnosis | **INSTALLED + LOADED + EXERCISED**: skill-pattern query vs live prod logs returned zero 5xx; sole 4xx was the intentional crew self-approve 403 |
| `cloud-run-alert-configuration` | `google/skills` | SRE alerting policies for Cloud Run | INSTALLED, not yet exercised |
| `google-cloud-waf-security` | `google/skills` | IAM, service accounts, least privilege | **INSTALLED** |
| `google-cloud-waf-cost-optimization` | `google/skills` | Protect Google credits | **INSTALLED** |
| `firebase-auth-basics` | `firebase/agent-skills` | CREW / SUPERVISOR / ADMIN identity |
| `firebase-firestore` | `firebase/agent-skills` | Inspection, revision, review, audit records |
| `firebase-security-rules-auditor` | `firebase/agent-skills` | Per-kitchen and per-role rule audit |
| `firebase-basics` | `firebase/agent-skills` | CLI setup, project selection, config download |
| `firebase-app-hosting-basics` | `firebase/agent-skills` | Hosting the Next.js Crew/Admin app |
| `vercel-react-best-practices` | `vercel-labs/agent-skills` | React/Next.js correctness in `apps/c05` |
| `web-design-guidelines` | `vercel-labs/agent-skills` | Accessibility and interaction quality gate |
| `c05-quality-gates` | local, this repo | Locks the C05 domain invariants |
| `c05-pubsub-worker` | local, this repo | Locks the async worker contract |

## Corrections to the proposed install list

| Proposed ID | Reality | Action |
|---|---|---|
| `firebase-firestore-standard` | **Does not exist.** The skill is `firebase-firestore`. | Installed under the real ID. |
| `pubsub-basics` | **Not present** in `google/skills`. | Replaced by the local `c05-pubsub-worker` skill. |
| `react-best-practices` | Real ID is `vercel-react-best-practices`. | Installed under the real ID. |
| `gemini-live-api-dev` | Exists but is audio/video streaming. | Skipped, C05 inspects still images. |
| `gke-basics` | Exists but Kubernetes is out of scope. | Skipped. |
| `cloud-storage-basics` | **Does not exist.** Verified against the live 163-skill catalog; the real ID is `google-cloud-storage-basics`. | Not installed (Storage already deployed and verified without it). |

## Duplicate with the global scope

These exist in **both** `~/.agents/skills/` and project `.agents/skills/`. The project copy wins
inside `sea-ai-hackathon`. The global copies predate this integration and were installed for other
repos; they were left untouched on purpose rather than deleted.

`firebase-auth-basics`, `firebase-basics`, `firebase-app-hosting-basics`,
`firebase-security-rules-auditor`, `web-design-guidelines`, `firebase-firestore`

## Explicitly skipped

| Skill | Reason |
|---|---|
| `gke-basics` | Kubernetes is disproportionate for this MVP |
| `gemini-live-api-dev` | Audio/video streaming; C05 needs static image inspection |
| `google/skills` non-WAF skills (BigQuery, Ads, AlloyDB, mobile ads, agent-platform tuning …) | No C05 requirement |

## Reporting rule

Installed is not the same as used. Every claim in a delivery report must map to an executed
command. See `c05-quality-gates` Gate 8.

## Mandatory routing — load by exact ID before acting (Gate 9)

One primary skill per responsibility; supporting skills only when the task genuinely
crosses the boundary. AgentMemory recall/save wraps every row.

| Task | Required skills (load first) | Trigger |
|---|---|---|
| Any C05 implementation slice | `c05-quality-gates`, `recall` → `remember`/`lesson` | always |
| Gemini inference / provider transport / structured output | `gemini-api-dev`, `agent-platform-inference` | touching `c05_gemini.py`, `provider.py`, prompts, schemas |
| Any gcloud command (plan, generate, or execute) | `gcloud` | leaf-help validation + quiet + data-reduction rules apply |
| Cloud Run deploy, config, revision, traffic | `cloud-run-basics` | container, service, revision, or traffic work |
| Firestore records / rules audit | `firebase-firestore`, `firebase-security-rules-auditor`, `firebase-basics` | records, rules, or project selection |
| Auth / identity (crew/admin roles) | `firebase-auth-basics` | login, roles, session work |
| Next.js hosting | `firebase-app-hosting-basics` | frontend deploy |
| Log diagnosis / audit | `cloud-logging-query-generation` | any log query; read the service reference file first |
| Alerting policies | `cloud-run-alert-configuration` | SLO / alert work |
| Spend review / rightsizing | `google-cloud-waf-cost-optimization` | cost questions |
| Security review (IAM, network, data) | `google-cloud-waf-security` | security questions |
| Async worker / queue semantics | `c05-pubsub-worker` | Pub/Sub or worker-contract work |
| React/Next correctness, accessibility | `vercel-react-best-practices`, `web-design-guidelines` | UI changes |
| Handoff between agents/sessions | `handoff`, `recap`, `session-history` | session boundaries |
| Removing bad memory | `forget` | explicit user request only |

Enforcement: the completion summary must name every skill ID loaded and every
memory entry saved. `c05-quality-gates` Gate 9 fails the slice otherwise.