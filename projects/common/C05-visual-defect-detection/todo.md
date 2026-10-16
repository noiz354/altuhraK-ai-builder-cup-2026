# Tasks — C05
Status: `DESIGN_ASSUMPTION` · draft MVP · implementation not started · C05.

Read [workflow](../../../docs/coding-agent-workflow.md) once. Choose one unchecked task. Read only its context; status/evidence in [SESSION](SESSION.md). Dependencies by task number.

| Task | Depends | Context | Change / evidence | Requirements |
|---|---|---|---|---|
| [x] C05-TASK-001 | none | data-design, test-fixtures | schema+fixture generator; validation report | FR-001,NFR-001 |
| [x] C05-TASK-002 | 001 | spec, data-design, test-fixtures | implement BR-001; deterministic happy/edge outputs | FR-002,NFR-002 |
| [x] C05-TASK-003 | 002 | api-contract, shared runtime | importer/run API+store; HTTP happy/error report | FR-001,FR-006,NFR-003 |
| [x] C05-TASK-004 | 003 | prd, api-contract | console with evidence and baseline states; UI run evidence | FR-004 |
| [ ] C05-TASK-005 | 003 | ai-ml-design, spec, shared runtime | provider+structured validator; mock vs live labeled, timeout evidence | FR-003,FR-006,NFR-003 |
| [x] C05-TASK-006 | 004,005 | security-privacy, spec, shared runtime | review/export revision+security cases; recorded assertions | FR-004,FR-005,NFR-001 |
| [ ] C05-TASK-007 | 006 | evaluation-plan, test-fixtures | compare baseline/AI on holdout; results artifact with versions | FR-002,FR-003,NFR-002,NFR-004 |
| [ ] C05-TASK-008 | 007 | mvp-plan, demo-script, shared deployment | run locally; optional gated cloud deployment only when ready | FR-001..006,NFR-001..004 |

Context names are local `.md` files; shared runtime=`../../../docs/shared/runtime-contract.md`, shared deployment=`../../../docs/shared/deployment.md`. Store file paths/commands/result per task. Implement code fresh in this project; don't copy O02's domain design into unrelated concepts.

## Implementation evidence

[local-mvp.md](local-mvp.md) and [evaluation/results.json](evaluation/results.json) record executed local checks. TASK-005 provider adapter is implemented/tested offline; live model behavior and domain AI benefit remain unverified. TASK-007 has baseline/structural results but no live-AI comparison. TASK-008 local app works; cloud deployment is pending.
