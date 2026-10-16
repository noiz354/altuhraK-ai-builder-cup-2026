# C05 Deployment Runbook

Target project: `gen-lang-client-0170811162` · Region: `asia-southeast2`
Service names (new, never colliding with `paydash-web` or siblings):
`c05-backend-staging`, `c05-frontend-staging`.
AR repo: new `c05` repo in asia-southeast2 (Docker format).

## 0. Prerequisites (all read-only checks)

```bash
gcloud auth list --filter=status:ACTIVE --format=value(account)
gcloud config get-value project   # expect gen-lang-client-0170811162
gcloud beta billing projects describe gen-lang-client-0170811162 \
  --format='value(billingEnabled)'   # expect True
gcloud run services list --project=gen-lang-client-0170811162 \
  --format='value(metadata.name)' | grep -x -e c05-backend-staging -e c05-frontend-staging \
  && echo 'NAME COLLISION - STOP' || echo 'names free'
```

## 1. Runtime identity (least privilege)

```bash
P=gen-lang-client-0170811162
gcloud iam service-accounts create c05-runtime --project=$P \
  --display-name='C05 Cloud Run runtime'
gcloud projects add-iam-policy-binding $P \
  --member=serviceAccount:c05-runtime@$P.iam.gserviceaccount.com \
  --role=roles/aiplatform.user
```

## 2. Build, tag with full commit SHA, push

```bash
cd sea-ai-hackathon
SHA=$(git -C /home/norman2/13-10-26-ai-builder-cup-26 rev-parse HEAD)
R=asia-southeast2-docker.pkg.dev/$P/c05
gcloud artifacts repositories create c05 --project=$P --repository-format=docker \
  --location=asia-southeast2 --description='C05 hackathon images'
gcloud auth configure-docker asia-southeast2-docker.pkg.dev
docker build -f deploy/Containerfile.backend -t $R/backend:$SHA .
docker build -f apps/c05/Containerfile -t $R/frontend:$SHA apps/c05
docker push $R/backend:$SHA
docker push $R/frontend:$SHA
# record digests
gcloud artifacts docker images describe $R/backend:$SHA --format='value(image_summary.digest)'
gcloud artifacts docker images describe $R/frontend:$SHA --format='value(image_summary.digest)'
```

## 3. Deploy backend (no traffic yet is impossible on first create; verify then lock)

Use `--env-vars-file`, never inline `--set-env-vars` for the full set: an
image-only redeploy was observed to drop vars that were set inline, silently
reverting the service to SQLite. The env file is versioned in
`deploy/backend-staging.env` and is the single source of truth.

```bash
SHA=<from step 2>; P=gen-lang-client-0170811162
R=asia-southeast2-docker.pkg.dev/$P/c05
gcloud run deploy c05-backend-staging --project=$P --region=asia-southeast2 \
  --image=$R/backend:$SHA \
  --service-account=c05-runtime@$P.iam.gserviceaccount.com \
  --set-env-vars=C05_GEMINI_PROVIDER=vertex,GOOGLE_CLOUD_PROJECT=$P,GEMINI_MODEL=gemini-2.5-flash,C05_GEMINI_LOCATION=global,GEMINI_TIMEOUT_SECONDS=150,C05_INSPECTION_MODE=local \
  --cpu=1 --memory=512Mi --concurrency=4 --timeout=300s \
  --min-instances=0 --max-instances=2 --ingress=all --allow-unauthenticated \
  --labels=app=c05,env=staging
BE_URL=$(gcloud run services describe c05-backend-staging --project=$P \
  --region=asia-southeast2 --format='value(status.url)')
BE_HOST=${BE_URL#https://}
gcloud run services update c05-backend-staging --project=$P --region=asia-southeast2 \
  --set-env-vars=^,^,MVP_ALLOWED_HOSTS=$BE_HOST
```

## 4. Deploy frontend against the backend URL

```bash
gcloud run deploy c05-frontend-staging --project=$P --region=asia-southeast2 \
  --image=$R/frontend:$SHA \
  --service-account=c05-runtime@$P.iam.gserviceaccount.com \
  --set-env-vars=C05_API_BASE_URL=$BE_URL \
  --cpu=1 --memory=512Mi --concurrency=10 --timeout=60s \
  --min-instances=0 --max-instances=2 --ingress=all --allow-unauthenticated \
  --labels=app=c05,env=staging
FE_URL=$(gcloud run services describe c05-frontend-staging --project=$P \
  --region=asia-southeast2 --format='value(status.url)')
```

## 5. Staging smoke (see QA_DEPLOYMENT_CHECKLIST.md)

One controlled real Gemini call only. Everything else must pass without inference.

## 6. Rollback

See ROLLBACK_RUNBOOK.md. Traffic revert is one command; data written to ephemeral
disk is NOT recoverable, which is why staging must not hold anything irreplaceable.
