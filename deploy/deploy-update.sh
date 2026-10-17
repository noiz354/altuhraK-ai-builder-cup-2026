#!/usr/bin/env bash
# Roll the current working tree out to the EXISTING C05 Cloud Run services.
#
#   deploy/deploy-update.sh staging            # build, push, update staging, smoke test
#   deploy/deploy-update.sh prod               # same for production (asks first)
#   GEMINI_MODEL=<id> deploy/deploy-update.sh staging   # also switch the model
#
# What it does NOT do: create services, service accounts, buckets or IAM.
# Those exist already (see DEPLOYMENT_RUNBOOK.md). Updating with
# `gcloud run services update --image` keeps every existing env var, secret,
# service account and scaling setting; only the image (and, when asked, the
# model id via --update-env-vars, which merges) changes.
#
# Rollback: ROLLBACK_RUNBOOK.md (traffic back to the previous revision).
set -euo pipefail

ENV_NAME="${1:-}"
case "$ENV_NAME" in
  staging) SUFFIX="-staging" ;;
  prod)    SUFFIX="" ;;
  *) echo "usage: $0 staging|prod" >&2; exit 2 ;;
esac

P="${GOOGLE_CLOUD_PROJECT:-gen-lang-client-0170811162}"
REGION="asia-southeast2"
R="$REGION-docker.pkg.dev/$P/c05"
BE="c05-backend$SUFFIX"
FE="c05-frontend$SUFFIX"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# A dirty tree still deploys (the hackathon tree is rarely clean), but the tag
# says so, so a running revision can always be traced back.
TAG="$(git rev-parse --short=12 HEAD)"
if [ -n "$(git status --porcelain)" ]; then TAG="$TAG-dirty-$(date -u +%Y%m%d%H%M)"; fi

echo "== project $P · $ENV_NAME · services $BE / $FE · tag $TAG"
[ "$(gcloud config get-value account 2>/dev/null)" ] || { echo "gcloud is not logged in" >&2; exit 1; }
for svc in "$BE" "$FE"; do
  gcloud run services describe "$svc" --project="$P" --region="$REGION" --format='value(metadata.name)' >/dev/null \
    || { echo "Service $svc not found; this script only updates existing services." >&2; exit 1; }
done
if [ "$ENV_NAME" = prod ]; then
  read -r -p "Deploy tag $TAG to PRODUCTION? Type 'prod' to continue: " ok
  [ "$ok" = prod ] || { echo "aborted"; exit 1; }
fi

echo "== tests"
python scripts/verify_mvp.py --project C05 >/dev/null
(cd projects/common/C05-visual-defect-detection && python -m unittest discover -s tests -p 'test_*.py' 2>&1 | tail -1)

echo "== build + push"
gcloud auth configure-docker "$REGION-docker.pkg.dev" --quiet >/dev/null
docker build -f deploy/Containerfile.backend -t "$R/backend:$TAG" .
docker build -f apps/c05/Containerfile -t "$R/frontend:$TAG" apps/c05
docker push "$R/backend:$TAG"
docker push "$R/frontend:$TAG"

echo "== update $BE"
EXTRA=()
if [ -n "${GEMINI_MODEL:-}" ]; then EXTRA+=(--update-env-vars="GEMINI_MODEL=$GEMINI_MODEL"); fi
gcloud run services update "$BE" --project="$P" --region="$REGION" --image="$R/backend:$TAG" \
  --update-labels="git-tag=${TAG//[^a-z0-9-]/-}" "${EXTRA[@]}"

echo "== update $FE"
gcloud run services update "$FE" --project="$P" --region="$REGION" --image="$R/frontend:$TAG" \
  --update-labels="git-tag=${TAG//[^a-z0-9-]/-}"

BE_URL="$(gcloud run services describe "$BE" --project="$P" --region="$REGION" --format='value(status.url)')"
FE_URL="$(gcloud run services describe "$FE" --project="$P" --region="$REGION" --format='value(status.url)')"

echo "== smoke ($FE_URL)"
fail=0
check() {  # name, url, expected substring
  local body
  body="$(curl -fsS --max-time 60 "$2" || true)"
  if [[ "$body" == *"$3"* ]]; then echo "PASS  $1"; else echo "FAIL  $1"; fail=1; fi
}
check "backend health"            "$BE_URL/health"                                   '"status":"ok"'
check "gemini provider resolved"  "$BE_URL/api/infra/readiness"                      '"ready":true'
check "frontend proxy"            "$FE_URL/api/proxy/health"                          '"status":"ok"'
check "guide page"                "$FE_URL/guide"                                     'How to use C05 Visual QC'
check "report page"               "$FE_URL/report"                                    'Did a school meal make someone unwell?'
check "claims API"                "$FE_URL/api/proxy/api/claims/incidents?role=ADMIN" '"incidents"'
check "manifest in English"       "$FE_URL/api/proxy/api/manifests?role=CREW"        'Rice or other carbohydrate'
AGENT="$(curl -fsS --max-time 120 -H 'content-type: application/json' \
  -d '{"role":"ADMIN","question":"Summarize this kitchen'"'"'s inspections"}' "$FE_URL/api/proxy/api/agent/chat" || true)"
if [[ "$AGENT" == *'"engine":"gemini"'* ]]; then echo "PASS  agent answered by Gemini"
else echo "WARN  agent fell back to rules: $(echo "$AGENT" | grep -o '"fallback_reason":"[^"]*"' || echo 'no response')"; fi

echo
echo "Frontend: $FE_URL"
echo "Next: load the demo scenario (Claims, role ADMIN) and record the walkthrough:"
echo "  cd apps/c05 && node scripts/demo-walkthrough.mjs $FE_URL --video --out demo-output"
exit $fail
