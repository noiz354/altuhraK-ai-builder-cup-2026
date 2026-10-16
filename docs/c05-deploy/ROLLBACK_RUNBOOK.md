# C05 Rollback Runbook

## Traffic rollback (safe, immediate)

```bash
P=gen-lang-client-0170811162; RGN=asia-southeast2
# list revisions, newest first
gcloud run revisions list --project=$P --region=$RGN \
  --service=c05-backend-staging --format='table(metadata.name,spec.containers[0].image)' --limit=5
# send 100% back to the last known-good revision (replace REV)
gcloud run services update-traffic c05-backend-staging --project=$P --region=$RGN \
  --to-revisions=REV=100
# same for c05-frontend-staging
```

## What rollback does NOT undo

- **Data.** Traffic rollback does not restore SQLite rows, images, reviews, or
  reports. Ephemeral disk is gone with the old revision. There is no database
  backup because there is no database yet.
- **Secrets/env.** Reverted only if the old revision carried the old values;
  verify with `gcloud run services describe`.
- **Provider side.** Gemini calls already made cannot be un-made (billing only).

## Verified rollback targets

| Service | Known-good revision | Image digest | Verified at |
|---|---|---|---|
| c05-backend-staging | _fill after staging deploy_ | _fill_ | _fill_ |
| c05-frontend-staging | _fill after staging deploy_ | _fill_ | _fill_ |

Until staging exists, the known-good state is **local**: portfolio commit
`8388c86`, frontend commit `770e854`, images `c05-backend:local`,
`c05-frontend:local` (rebuildable from those commits).

## Never do this

- Do not delete old revisions to "clean up" — they are the rollback targets.
- Do not delete the AR repo, buckets, or any backup as a shortcut.
- Do not touch `paydash-web` or any sibling service during a C05 rollback.
