"""Swappable Gemini transport for C05.

One config selects the provider. Switching is configuration, never a code change.

    C05_GEMINI_PROVIDER = auto | gemini-api | vertex

`auto` resolves, in order:
  1. `vertex`     when GOOGLE_CLOUD_PROJECT is set (Application Default Credentials)
  2. `gemini-api` when GEMINI_API_KEY is set (Gemini Developer API)

Billing matters. Google Cloud credits on a Cloud Billing account normally do **not** cover the
Gemini Developer API key path; that path bills the separate AI Studio account attached to the key.
Vertex bills the Cloud project. `c05-doctor` reports which one is selected so an operator does not
have to guess.

Credentials are read from the environment only. Nothing here logs, returns, or persists a secret.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["auto", "gemini-api", "vertex"]

DEFAULT_TIMEOUT = 12.0
MODEL_RE = re.compile(r"[A-Za-z0-9._-]+")
ENDPOINT_RE = re.compile(r"projects/[\w-]+/locations/(?P<region>[a-z0-9-]+)/endpoints/\d+")


@dataclass
class GeminiConfig:
    provider: Provider = "auto"
    model: str | None = None
    timeout_s: float = DEFAULT_TIMEOUT
    project: str | None = None
    location: str = "us-central1"
    api_key_present: bool = field(default=False, repr=False)
    adc_present: bool = field(default=False, repr=False)

    @property
    def resolved(self) -> Literal["gemini-api", "vertex"] | None:
        """Which transport would actually be used. None means neither is usable."""
        if self.provider == "gemini-api":
            return "gemini-api" if self.api_key_present and self.model else None
        if self.provider == "vertex":
            return "vertex" if self.project and self.adc_present and self.model else None
        if self.project and self.adc_present and self.model:
            return "vertex"
        if self.api_key_present and self.model:
            return "gemini-api"
        return None

    def as_dict(self) -> dict:
        """Report shape for /api/infra/readiness. Contains no secret material."""
        return {
            "provider_requested": self.provider,
            "provider_resolved": self.resolved,
            "model": self.model,
            "timeout_s": self.timeout_s,
            "project": self.project,
            "location": self.location,
            "credentials": {
                "gemini_api_key": self.api_key_present,
                "adc": self.adc_present,
                "adc_check_error": _ADC_CHECK_ERROR[0] or None,
                "adc_check_detail": _ADC_CHECK_DETAIL[0],
            },
            "billing_note": (
                "Vertex bills the Google Cloud project. The Gemini Developer API key bills the "
                "AI Studio account tied to that key, which is usually NOT the Cloud Billing "
                "account holding your credits."
            ),
            "blocking": self.blocking(),
        }

    def blocking(self) -> list[str]:
        """Exactly what prevents a live call, judged against the transport that would be used.

        An unused path is not a blocker. In `auto` mode the fallback that did not win must not
        be reported as a problem, otherwise a ready configuration looks broken.
        """
        transport = self.resolved
        if transport is not None and self.model:
            return []  # resolved implies the model is present and credentials are usable

        out: list[str] = []
        if not self.model:
            out.append("No model configured. Set GEMINI_MODEL.")

        if self.provider == "gemini-api":
            if not self.api_key_present:
                out.append("C05_GEMINI_PROVIDER=gemini-api but GEMINI_API_KEY is unset.")
            return out

        if self.provider == "vertex":
            if not self.project:
                out.append("C05_GEMINI_PROVIDER=vertex but GOOGLE_CLOUD_PROJECT is unset.")
            if not self.adc_present:
                out.append("C05_GEMINI_PROVIDER=vertex but no Application Default Credentials found.")
            return out

        # auto: report both paths, because either could still be completed by the operator
        if not self.project:
            out.append("Vertex path unavailable: GOOGLE_CLOUD_PROJECT is not set.")
        elif not self.adc_present:
            out.append("Vertex path unavailable: no Application Default Credentials found.")
        if not self.api_key_present:
            out.append("Developer API path unavailable: GEMINI_API_KEY is not set.")
        return out


def load_config(env: dict | None = None) -> GeminiConfig:
    env = os.environ if env is None else env
    raw = (env.get("C05_GEMINI_PROVIDER") or "auto").strip().lower()
    provider: Provider = raw if raw in {"auto", "gemini-api", "vertex"} else "auto"
    try:
        timeout = float(env.get("GEMINI_TIMEOUT_SECONDS") or DEFAULT_TIMEOUT)
    except ValueError:
        timeout = DEFAULT_TIMEOUT
    return GeminiConfig(
        provider=provider,
        model=(env.get("GEMINI_MODEL") or env.get("C05_GEMINI_MODEL") or None),
        timeout_s=timeout,
        project=(env.get("GOOGLE_CLOUD_PROJECT") or env.get("C05_GCP_PROJECT") or None),
        location=(env.get("C05_GEMINI_LOCATION") or "global"),
        api_key_present=bool(env.get("GEMINI_API_KEY")),
        adc_present=_adc_present(),
    )


def _adc_present() -> bool:
    """Whether Application Default Credentials can be resolved. Never reads contents.

    File checks first (fast, no network). Then `google.auth.default()`, which is
    the only check that passes on Cloud Run: there is no gcloud CLI and no ADC
    file there, only the metadata server behind the attached service account.
    """
    explicit = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if explicit:
        return os.path.isfile(explicit)
    home = os.path.expanduser("~")
    if os.path.isfile(
        os.path.join(home, ".config", "gcloud", "application_default_credentials.json")
    ):
        return True
    detail: dict[str, object] = {}
    try:
        import google.auth  # type: ignore

        detail["has_lib"] = True
        from google.auth.compute_engine import _metadata  # type: ignore
        from google.auth.transport import _http_client  # type: ignore

        try:
            detail["gce_ping"] = bool(
                _metadata.ping(request=_http_client.Request()))
        except Exception as exc:
            detail["gce_ping"] = f"{type(exc).__name__}"
        google.auth.default()
        _ADC_CHECK_DETAIL[0] = detail
        return True
    except Exception as exc:
        # Type name only: enough to distinguish "no credentials configured" from
        # "metadata server unreachable", and contains no secret material.
        detail["error"] = type(exc).__name__
        _ADC_CHECK_DETAIL[0] = detail
        _ADC_CHECK_ERROR[0] = type(exc).__name__
        return False


# Last ADC probe failure, exception type name only. Lets a deployed readiness
# endpoint say WHY credentials are missing instead of just that they are.
_ADC_CHECK_ERROR: list[str] = [""]
_ADC_CHECK_DETAIL: list[dict] = [{}]


def auth_headers(cfg: GeminiConfig, model_name: str | None = None) -> tuple[str, dict[str, str], str]:
    """Return (url, headers, auth_mode). Raises when the selected provider is unusable.

    model_name lets the caller pass the model actually being requested, so the URL
    cannot drift from the model_id recorded in usage metadata.
    """
    transport = cfg.resolved
    if transport is None:
        raise ProviderNotConfigured("; ".join(cfg.blocking()) or "No usable Gemini provider.")
    model = model_name or cfg.model or ""

    if transport == "gemini-api":
        key = os.environ.get("GEMINI_API_KEY", "")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent"
        )
        return url, {"x-goog-api-key": key}, "api-key"

    project = cfg.project or ""
    endpoint = (os.environ.get("C05_GEMINI_ENDPOINT") or "").strip()
    if endpoint:
        # A tuned Gemini model is served from its own regional endpoint resource,
        # projects/{p}/locations/{region}/endpoints/{id}, not the publisher path.
        match = ENDPOINT_RE.fullmatch(endpoint)
        if not match:
            raise ProviderNotConfigured(
                "C05_GEMINI_ENDPOINT must be projects/{project}/locations/{region}/endpoints/{id}")
        url = f"https://{match['region']}-aiplatform.googleapis.com/v1/{endpoint}:generateContent"
        return url, {"Authorization": f"Bearer {_adc_token(cfg)}"}, "adc-bearer"
    # `global` is the endpoint that serves publisher models on projects that have no
    # regional publisher catalogue. Verified working on gen-lang-client-0170811162.
    host = "aiplatform.googleapis.com" if cfg.location == "global" else f"{cfg.location}-aiplatform.googleapis.com"
    url = (
        f"https://{host}/v1/projects/{project}"
        f"/locations/{cfg.location}/publishers/google/models/{model}:generateContent"
    )
    token = _adc_token(cfg)
    return url, {"Authorization": f"Bearer {token}"}, "adc-bearer"


_TOKEN_CACHE: dict[str, tuple[str, float]] = {}
_TOKEN_LOCK = threading.Lock()
# Refresh well before the 60 minute hard expiry so an in-flight call never
# receives a token that dies mid-request.
_TOKEN_TTL_S = 45 * 60


def _adc_token(cfg: GeminiConfig) -> str:
    """Resolve a short-lived access token via Application Default Credentials.

    Cached. A cold `gcloud auth print-access-token` costs roughly 17 seconds on this
    machine, which on its own exceeds the 12 second inference budget and made every
    live call fail. Tokens are valid for an hour, so one lookup per process is enough.
    """
    key = f"{cfg.project or ''}:{cfg.location}"
    now = time.time()
    with _TOKEN_LOCK:
        cached = _TOKEN_CACHE.get(key)
        if cached and now < cached[1]:
            return cached[0]

    # Preferred path: google-auth resolves credentials from the environment,
    # the well-known ADC file, or the Cloud Run metadata server, with no
    # subprocess and no gcloud CLI. The CLI fallback stays for machines where
    # only `gcloud auth login` state exists.
    try:
        import google.auth  # type: ignore
        import google.auth.transport.requests  # type: ignore

        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        token = (creds.token or "").strip()
        if token:
            with _TOKEN_LOCK:
                _TOKEN_CACHE[key] = (token, time.time() + _TOKEN_TTL_S)
            return token
    except Exception:
        pass

    try:
        proc = subprocess.run(
            ["gcloud", "auth", "print-access-token"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProviderNotConfigured(f"Could not reach gcloud for ADC token: {exc}") from None
    token = (proc.stdout or "").strip()
    if proc.returncode != 0 or not token:
        detail = (proc.stderr or "").strip().splitlines()
        raise ProviderNotConfigured(
            "ADC token unavailable. Run: gcloud auth application-default login"
            + (f" ({detail[-1][:120]})" if detail else "")
        )
    with _TOKEN_LOCK:
        _TOKEN_CACHE[key] = (token, time.time() + _TOKEN_TTL_S)
    return token


class ProviderNotConfigured(RuntimeError):
    """Selected provider cannot be called. Never surfaces credential values."""


def vertex_contents(parts: list[dict]) -> list[dict]:
    """Vertex requires an explicit role on every content entry.

    The Developer API omits it, so this lives here rather than in the shared
    provider body.
    """
    return [{"role": "user", "parts": parts}]


def vertex_response_schema(schema: dict) -> dict:
    """Flatten a Pydantic JSON schema into the subset Vertex accepts.

    Vertex rejects `$defs`/`$ref` (400 "Request contains an invalid argument") and the
    Developer API field name `responseJsonSchema`. Pydantic emits `$defs` whenever a
    nested object repeats, which is exactly what the C05 regions array does.
    """
    defs = schema.get("$defs", {})

    def resolve(node):
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            target = defs.get(node["$ref"].split("/")[-1], {})
            merged = {k: v for k, v in target.items() if k != "defs"}
            return resolve({**merged, **{k: v for k, v in node.items() if k != "$ref"}})

        out = {}
        for k, v in node.items():
            if k in {"$defs", "$schema", "additionalProperties", "title"}:
                continue
            # Pydantic writes a nullable union as type: ["number", "null"]. Vertex
            # rejects an array `type` and requires nullable: true instead.
            if k == "type" and isinstance(v, list):
                concrete = [t for t in v if t != "null"]
                out["type"] = concrete[0] if len(concrete) == 1 else concrete
                if len(concrete) != len(v):
                    out["nullable"] = True
                continue
            if k in {"maxLength", "maxItems"}:
                continue  # proto3 JSON schema subset Vertex does not model
            out[k] = resolve(v)
        return out

    flat = resolve(schema)
    flat.pop("$defs", None)
    return flat


C05_LABELS = ("meal_complete", "missing_component", "uncertain")


def thinking_config_for(model: str) -> dict:
    """Return the thinking control this model family actually honours.

    Measured against the live global endpoint, not inferred:

    | model             | thinkingBudget:0        | thinkingLevel:LOW         |
    |-------------------|-------------------------|---------------------------|
    | gemini-2.5-flash  | 200, no thoughts token  | 400 not supported         |
    | gemini-3.8-flash  | 200, 58 thoughts tokens | 200, no thoughts token    |
    | gemini-3.8-flash  | -                       | MINIMAL -> 400 unsupported |

    The silent-ignore case is the dangerous one. Carrying `thinkingBudget: 0` from
    Gemini 2.5 into Gemini 3.8 still returns HTTP 200, so nothing looks wrong, but
    thinking keeps running and roughly a quarter of the latency budget is spent on
    reasoning tokens that the C05 guard will never use. `thinkingLevel` is also the
    only spelling accepted on Gemini 3, and 2.5 rejects it outright, so the two
    families cannot share one setting.
    """
    model = (model or "").lower()
    override = os.environ.get("C05_GEMINI_THINKING_CONFIG")
    if override:
        try:
            return json.loads(override)
        except ValueError:
            pass
    if model.startswith("gemini-3") or model.startswith("gemini-4"):
        return {"thinkingLevel": os.environ.get("C05_GEMINI_THINKING_LEVEL", "LOW")}
    return {"thinkingBudget": 0}


def c05_vertex_schema(schema: dict) -> dict:
    """Flatten the C05 output schema for Vertex and pin the label vocabulary.

    The label set is enforced twice on purpose. `domain.validate_output` is the
    authority and must keep rejecting bad labels; the enum simply stops the model
    from spending a live request on a label that can never be accepted. Vertex
    documents `format: "enum"` with a string list as supported for structured
    output, so this is within the accepted subset.
    """
    flat = vertex_response_schema(schema)
    label = flat.get("properties", {}).get("predicted_label")
    if isinstance(label, dict):
        label["format"] = "enum"
        label["enum"] = list(C05_LABELS)
    return flat


def structured_generation_config(out_schema: dict) -> dict:
    """Shared JSON-schema request body used by both transports."""
    return {
        "responseMimeType": "application/json",
        "responseJsonSchema": out_schema,
        "maxOutputTokens": 2048,
        "temperature": 0,
    }


def readiness_payload(cfg: GeminiConfig | None = None) -> dict:
    cfg = cfg or load_config()
    payload = cfg.as_dict()
    payload["ready"] = cfg.resolved is not None
    payload["gcloud_available"] = _command_exists("gcloud")
    return payload


def _command_exists(name: str) -> bool:
    """PATH lookup only. gcloud --version is slow and would add seconds to every readiness call."""
    return shutil.which(name) is not None


if __name__ == "__main__":  # `python src/c05_gemini.py` prints readiness, never secrets
    print(json.dumps(readiness_payload(), indent=2))