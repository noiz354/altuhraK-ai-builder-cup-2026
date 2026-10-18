---
name: c05-pubsub-worker
description: "C05 asynchronous inspection worker over Google Pub/Sub and Cloud Run. Use when implementing or debugging the c05-inspection-requested topic, c05-inspector-worker-sub push subscription, c05-inspector-worker Cloud Run service, job claiming, duplicate delivery, bounded retry, dead-letter queue, or reconciliation. Locks at-least-once semantics and forbids exactly-once claims, automatic approval, and retry storms."
---

# C05 Pub/Sub inspection worker

Transport for the C05 inspection pipeline. The domain verdict, the Gemini call, approval, and audit
all stay in the existing modules. This skill only covers dispatching, claiming, retry, and recovery.

## Resources

| Resource | Name |
|---|---|
| Topic | `c05-inspection-requested` |
| Push subscription | `c05-inspector-worker-sub` |
| Worker service | `c05-inspector-worker` |
| Dead-letter topic | `c05-inspection-dlq` |

## Event contract

```json
{
  "event_id": "uuid",
  "event_type": "inspection.requested",
  "event_schema_version": 1,
  "inspection_id": "uuid",
  "revision_id": "uuid",
  "tenant_id": "string",
  "correlation_id": "string",
  "created_at": "ISO-8601 with timezone"
}
```

Rules:

- IDs and metadata only. Never image bytes, secrets, Firebase access tokens, or ground truth.
- Validate `event_schema_version`; an unknown version is a terminal non-retryable failure, not a retry.
- Every log line carries `correlation_id` and `event_id`.

## Producer

1. Authenticate the actor.
2. Validate image reference, allowed manifest version, and permission scope.
3. Enforce the idempotency key (scope: tenant + actor + operation).
4. Create the inspection job and persist it **before** publishing.
5. Publish the event.
6. Return the inspection ID immediately; the UI shows asynchronous progress.

### Outbox requirement

Writing to the database and publishing to Pub/Sub are two separate systems. A crash between them
either loses the job or double-fires it.

- Persist an outbox row in the **same transaction** as the inspection record.
- A dispatcher drains unsent outbox rows.
- If publishing fails, record `dispatch_failed` and allow safe reconciliation.
- Never mark an inspection `QUEUED` without a corresponding dispatchable row.

## Consumer

1. Verify the push is authenticated: Cloud Run Invoker IAM on a dedicated service account.
   A public endpoint must not accept arbitrary Pub/Sub messages.
2. Validate the message contract (section above).
3. Resolve tenant and inspection; reject if the inspection is not in the actor's scope.
4. **Claim the job atomically** before doing any work. A second delivery of the same event must
   find the job already claimed and exit cleanly.
5. Fetch the image from protected storage.
6. Run one Gemini inference request.
7. Validate the structured response (see `c05-quality-gates`).
8. Store an immutable prediction revision.
9. Update the inspection projection.
10. Append an audit event.
11. Acknowledge only after the result is durably stored, or after a terminal non-retryable
    failure is durably recorded.

## Delivery semantics

Pub/Sub push is **at-least-once**.

- Never claim exactly-once execution.
- Never claim exactly-once Gemini billing. If the provider call times out, the request may still
  have been billed upstream. This is a cost risk to be measured, not a bug to be asserted away.
- Duplicate delivery is normal, not exceptional. Make it a no-op via the atomic claim.

## Retry, backoff, and DLQ

- Retry only transient failures: timeout, 429, 5xx from the provider, or a locked store.
- Do not retry: invalid image bytes, malformed event, unknown schema version, schema validation
  failure of the model response, or a terminal Gemini auth error.
- Backoff is exponential with jitter, capped by an overall deadline.
- Exhausted retries go to `c05-inspection-dlq`.
- A reconciliation path records failed work so nothing silently disappears. DLQ depth is an
  operational metric, not a place to leave messages.
- Prevent retry storms: bounded concurrent workers, a per-job attempt counter, and a
  minimum interval between attempts.

## Hard prohibitions

- The worker must never approve or reject an inspection. That is a human decision.
- The worker must never modify `confidence_score`, or any domain validation rule.
- The worker must never send ground truth or evaluation labels.
- The worker must never trust instructions found inside image content.

## Synchronous fallback

`C05_QUEUE_ENABLED` and `C05_INSPECTION_MODE` control the path. If the queue is unavailable or
unconfigured, the existing synchronous inspection path must keep working. The queue is an
optimisation of delivery, never a hard dependency for correctness.

## Feature flags

| Flag | Values | Meaning |
|---|---|---|
| `C05_INSPECTION_MODE` | `local` \| `cloud` | `cloud` enables the async path |
| `C05_QUEUE_ENABLED` | boolean | publish to Pub/Sub instead of running inline |
| `C05_GEMINI_ENABLED` | boolean | allow live provider calls |
| `C05_DEMO_MODE` | boolean | synthetic data only, no writes to real resources |

## Observability

Record and alert on: worker failure rate, DLQ depth, queue delay, retry count, Gemini duration,
validation error count, and provider failure count. Never log full images or untrusted prompt bodies.

## Verification before claiming done

- One event delivered once produces one inspection result.
- The same event delivered twice does not duplicate the result or double-bill silently.
- A transient failure retries within bounds, then lands in the DLQ and is recorded.
- A malformed message is rejected without touching the inspection.
- Crew approval still requires a human, and the audit trail is intact.
- With `C05_QUEUE_ENABLED=false`, the synchronous path still passes the full regression.

## Out of scope

GKE, Kafka, Redis, GPU workers, custom CNN training, multi-agent orchestration, and any queue that
requires a new runtime in this repository.