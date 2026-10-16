#!/usr/bin/env bash
# C05 Gemini provider doctor.
#
# Prints readiness for BOTH transports so an operator can see which one is
# usable and, crucially, which billing account each path draws from.
# It never prints a credential value.
set -uo pipefail

ENV_FILE="${1:-$(dirname "$0")/../.env}"

say() { printf '%-46s %s\n' "$1" "$2"; }

echo "C05 Gemini provider readiness"
echo "env file: $ENV_FILE"
[ -f "$ENV_FILE" ] && echo "(file exists; values are NOT printed)" || echo "(no .env yet)"
echo

echo "-- configured (values hidden) --"
say "C05_GEMINI_PROVIDER" "${C05_GEMINI_PROVIDER:-<unset, defaults to auto>}"
say "GEMINI_MODEL" "${GEMINI_MODEL:+<set>}${GEMINI_MODEL:-<unset>}"
say "GEMINI_API_KEY" "${GEMINI_API_KEY:+<set, value hidden>}${GEMINI_API_KEY:-<unset>}"
say "GOOGLE_CLOUD_PROJECT" "${GOOGLE_CLOUD_PROJECT:-<unset, default project: gen-lang-client-0170811162>}"
say "C05_GEMINI_LOCATION" "${C05_GEMINI_LOCATION:-<unset, defaults to us-central1>}"
say "GEMINI_TIMEOUT_SECONDS" "${GEMINI_TIMEOUT_SECONDS:-<unset, defaults to 12>}"
echo

echo "-- local checks --"
if command -v gcloud >/dev/null 2>&1; then
  say "gcloud" "$(gcloud --version 2>/dev/null | head -1)"
  say "active account" "$(gcloud auth list --filter=status:ACTIVE --format='value(account)' 2>/dev/null | head -1)"
  say "default project" "$(gcloud config get-value project 2>/dev/null | head -1)"
else
  say "gcloud" "NOT INSTALLED (Vertex path unavailable)"
fi
ADC="$HOME/.config/gcloud/application_default_credentials.json"
[ -f "$ADC" ] && say "ADC file" "present" || say "ADC file" "absent (Vertex path unavailable)"
echo

echo "-- resolved transport --"
python3 "$(dirname "$0")/c05_gemini.py" 2>/dev/null || \
  python3 "$(cd "$(dirname "$0")/.." && pwd)/src/c05_gemini.py"
echo

cat <<'NOTE'
Billing warning
  Vertex            -> bills the Google Cloud project (your Cloud Billing credits apply).
  Gemini Developer  -> bills the AI Studio account attached to the key, which is
                       usually a DIFFERENT account from your Cloud Billing one.

To switch, change configuration only. No code change is needed.
  export C05_GEMINI_PROVIDER=vertex      # cloud billing, needs ADC
  export GOOGLE_CLOUD_PROJECT=gen-lang-client-0170811162
  export C05_GEMINI_PROVIDER=gemini-api  # developer key billing
  export C05_GEMINI_PROVIDER=auto        # vertex if project+ADC, else api key
NOTE