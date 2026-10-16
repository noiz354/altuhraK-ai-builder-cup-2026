"""C05 Food Production Visual QC adapter.

Wraps the shared MVP app instead of forking it, so the other 23 projects stay
untouched. Adds only the seams the Field Crew App, Admin Command Center and the
Operations Agent need and the shared runtime does not expose:

- image intake (JPEG/PNG, magic bytes, EXIF-normalised, 4 MiB cap)
- versioned meal manifest
- grounded, role-scoped, audited agent tools
- real-record admin metrics

Domain labels, confidence handling, box validation, approval invariants and the
append-only audit trail all stay in the shared runtime and C05 domain module.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import HTTPException, Request
from PIL import Image, ImageOps

from shared_mvp.app import create_app as _shared_app
from shared_mvp.app import locate
from shared_mvp.assets import root as asset_root
from shared_mvp.contracts import Invalid
from shared_mvp.store import Store

import c05_gemini

PID = 'C05'
ROOT = locate(PID)
MAX_BYTES = 4 * 1024 * 1024
STORAGE_BUDGET_BYTES = 10 * 1024 * 1024 * 1024
Role = Literal['CREW', 'SUPERVISOR', 'ADMIN']

MANIFEST = {
    'manifest_id': 'MBG-STD-01',
    'version': 1,
    'name': 'MBG Standard Tray A',
    'components': [
        {'key': 'carbohydrate', 'label': 'Nasi / komponen karbohidrat'},
        {'key': 'protein', 'label': 'Komponen protein'},
        {'key': 'vegetable', 'label': 'Komponen Sayur'},
    ],
    'note': 'Visual presence only. Never proves weight, nutrition or microbiological safety.',
}

ROLES = {
    'CREW': {'kitchens': ['KITCHEN-A'], 'approve': False, 'agent_write': False},
    'SUPERVISOR': {'kitchens': ['KITCHEN-A', 'KITCHEN-B'], 'approve': True, 'agent_write': False},
    'ADMIN': {'kitchens': ['KITCHEN-A', 'KITCHEN-B'], 'approve': True, 'agent_write': True},
}

UNCERTAINTY = {'occluded_component', 'poor_lighting', 'label_ambiguous', 'blurred_image',
               'component_out_of_frame', 'manifest_mismatch'}
LABELS = {'meal_complete', 'missing_component', 'uncertain'}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _actor(role: Role) -> str:
    return f'{role.lower()}-demo'


def _scope(role: Role) -> set[str]:
    return set(ROLES[role]['kitchens'])


def _gemini_transport():
    """Resolve the configured Gemini transport for each call.

    Rebuilt per call so switching C05_GEMINI_PROVIDER or rotating an ADC token
    takes effect without restarting the service.
    """
    cfg = c05_gemini.load_config()
    def resolve(model_name, parts):
        url, headers, _mode = c05_gemini.auth_headers(cfg, model_name)
        # Vertex needs a flattened responseSchema, not the Developer API's
        # responseJsonSchema, or it rejects the request outright.
        # thinkingBudget 0: measured 2.0s with it off versus 10.9s with thinking on
        # for the same payload. Thinking blew the 12s per-attempt budget and caused
        # every live call to time out while the model itself was perfectly capable.
        gen_config = {"responseMimeType": "application/json",
                      "responseSchema": c05_gemini.c05_vertex_schema(_out_schema()),
                      "maxOutputTokens": 2048, "temperature": 0,
                      "thinkingConfig": c05_gemini.thinking_config_for(model_name)}
        # Multimodal inference on a full-size tray runs well past the 12s budget that
        # suited short text-only calls; Google's own retry guidance uses a 120s example.
        # Verified ReadTimeout at 12.4s with thinking disabled and a 640x480 image.
        timeout = max(float(os.environ.get('GEMINI_TIMEOUT_SECONDS') or 0), cfg.timeout_s or 0, 90.0)
        # max_attempts 3 with jittered exponential backoff: 429/5xx are documented as
        # transient and safe to retry, and a single one otherwise drops the whole
        # inspection to the deterministic baseline.
        return {'url': url,
                'headers': headers,
                'contents': c05_gemini.vertex_contents(parts),
                'generation_config': gen_config,
                'timeout': timeout,
                'max_attempts': 3}
    return resolve


def _out_schema():
    from shared_mvp.app import locate as _locate
    from shared_mvp.app import load as _load
    from shared_mvp.contracts import model as _model
    import json as _json
    cfg = _json.loads((_locate(PID) / "config" / "project.json").read_text())
    return _model(cfg["output"], PID + "Output").model_json_schema()


def _make_store(db_path):
    """SQLite by default; Firestore when the operator configures it.

    Selection is by environment alone, so the same image runs either backend
    with no code change. Unset C05_FIRESTORE_PROJECT means today's behaviour.
    """
    project = os.environ.get("C05_FIRESTORE_PROJECT")
    if not project:
        return None  # shared app builds its historical SQLite store
    from shared_mvp.firestore_store import FirestoreStore
    return FirestoreStore(
        project=project,
        database=os.environ.get("C05_FIRESTORE_DATABASE") or "c05staging")


def _asset_prefix() -> str:
    prefix = os.environ.get("C05_ASSET_PREFIX") or "staging/"
    return prefix if prefix.endswith("/") else prefix + "/"


def _asset_write(image_id: str, data: bytes) -> None:
    """Persist one image locally and, when configured, durably in Cloud Storage.

    The local file stays the read path for inference, so provider behaviour is
    unchanged. Cloud Storage is the copy that survives container replacement.
    """
    (asset_root(PID) / f"{image_id}.png").write_bytes(data)
    if not os.environ.get("C05_ASSET_BUCKET"):
        return
    from google.cloud import storage  # type: ignore

    storage.Client().bucket(os.environ["C05_ASSET_BUCKET"]).blob(
        f"{_asset_prefix()}{image_id}.png").upload_from_string(
            data, content_type="image/png")


def _ensure_asset_local(image_id: str) -> None:
    """Rehydrate the local inference cache from Cloud Storage after a restart.

    Called before any run that needs the bytes. Without a bucket configured this
    is a no-op and a missing file fails exactly as it always has.
    """
    if (asset_root(PID) / f"{image_id}.png").is_file():
        return
    if not os.environ.get("C05_ASSET_BUCKET"):
        return
    from google.cloud import storage  # type: ignore

    storage.Client().bucket(os.environ["C05_ASSET_BUCKET"]).blob(
        f"{_asset_prefix()}{image_id}.png").download_to_filename(
            str(asset_root(PID) / f"{image_id}.png"))


def create_app(db_path=None, provider=None):
    transport = None
    try:
        cfg = c05_gemini.load_config()
        if cfg.provider == 'vertex' or (cfg.provider == 'auto' and cfg.resolved == 'vertex'):
            transport = _gemini_transport()
    except Exception:
        transport = None
    app = _shared_app(PID, db_path, provider, transport, _make_store(db_path))
    store: Store = app.state.store
    if transport is not None:
        # Warm the ADC token at startup. A cold `gcloud auth print-access-token` costs
        # ~17s on this machine, which would otherwise be charged to the first
        # inspection's latency and could push it past the request budget.
        try:
            c05_gemini.auth_headers(c05_gemini.load_config())
        except Exception:
            pass  # readiness endpoint still reports the blocker; do not fail boot

    async def body(request: Request):
        try:
            return await request.json()
        except Exception:
            raise HTTPException(400, 'Malformed JSON body') from None

    # ---------------------------------------------------------------- intake

    def decode_image(payload: dict):
        if payload.get('mime_type') not in {'image/jpeg', 'image/png'}:
            raise Invalid('Only image/jpeg or image/png is accepted')
        raw = payload.get('data_base64', '')
        if not isinstance(raw, str) or not raw:
            raise Invalid('data_base64 is required')
        try:
            data = base64.b64decode(raw, validate=True)
        except (binascii.Error, ValueError):
            raise Invalid('data_base64 is not valid base64') from None
        if not data:
            raise Invalid('Empty image payload')
        if len(data) > MAX_BYTES:
            raise Invalid('Image exceeds 4 MiB limit')
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            actual = 'image/png'
        elif data[:3] == b'\xff\xd8\xff':
            actual = 'image/jpeg'
        else:
            raise Invalid('File bytes do not match an allowed image type')
        if actual != payload['mime_type']:
            raise Invalid('Declared MIME type does not match file bytes')
        try:
            with Image.open(io.BytesIO(data)) as opened:
                opened.load()
                image = ImageOps.exif_transpose(opened).convert('RGB')
                if image.width * image.height > 4_000_000:
                    raise Invalid('Image pixel limit exceeded')
                buffer = io.BytesIO()
                image.save(buffer, format='PNG')
        except Invalid:
            raise
        except Exception:
            raise Invalid('Corrupt or unsupported image') from None
        analysis = buffer.getvalue()
        return data, analysis, image.width, image.height

    @app.post('/api/inspections', status_code=201)
    async def create_inspection(request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        kitchen = payload.get('kitchen_id')
        if kitchen not in _scope(role):
            raise HTTPException(403, 'Kitchen is outside your assignment')
        if payload.get('manifest_version') != MANIFEST['version']:
            raise HTTPException(422, 'Unknown meal manifest version')
        original, analysis, width, height = decode_image(payload)
        image_id = uuid.uuid4().hex
        _asset_write(image_id, analysis)
        inspection_id = uuid.uuid4().hex
        idempotency_key = payload.get('idempotency_key')
        if idempotency_key:
            existing = store.get('idempotency', idempotency_key)
            if existing:
                if existing['request_hash'] != _hash(json.dumps(
                        {k: payload.get(k) for k in ('role', 'kitchen_id', 'shift_id', 'batch_id', 'manifest_version')},
                        sort_keys=True).encode()):
                    raise HTTPException(409, 'Idempotency key reused with a different payload')
                return {**existing['inspection'], 'idempotent_replay': True}
        record = {
            'inspection_id': inspection_id,
            'revision': 1,
            'role': role,
            'actor_id': _actor(role),
            'tenant_id': 'DEMO-TENANT',
            'kitchen_id': kitchen,
            'shift_id': payload.get('shift_id') or 'SHIFT-AM',
            'batch_id': payload.get('batch_id') or 'BATCH-DEMO',
            'manifest_id': MANIFEST['manifest_id'],
            'manifest_version': MANIFEST['version'],
            'image_id': image_id,
            'image_sha256': _hash(original),
            'analysis_sha256': _hash(analysis),
            'size_bytes': len(analysis),
            'image_width': width,
            'image_height': height,
            'storage_path': f'{image_id}.png',
            'execution_status': 'CREATED',
            'review_status': 'UNVERIFIED',
            'qc_disposition': None,
            'prediction': None,
            'evidence_ids': [],
            'model_version': None,
            'prompt_version': 'v1',
            'schema_version': 'c05-output-v1',
            'created_at': _now(),
        }
        store.put('inspection', inspection_id, record)
        store.append(inspection_id, 'created', {'actor': record['actor_id'], 'kitchen': kitchen})
        if idempotency_key:
            store.put('idempotency', idempotency_key, {
                'request_hash': _hash(json.dumps(
                    {k: payload.get(k) for k in ('role', 'kitchen_id', 'shift_id', 'batch_id', 'manifest_version')},
                    sort_keys=True).encode()),
                'inspection_id': inspection_id})
        return record

    @app.get('/api/inspections')
    async def list_inspections(kitchen_id: str | None = None, role: Role = 'ADMIN',
                               review_status: str | None = None):
        rows = sorted(store.list_kind('inspection'),
                      key=lambda r: r.get('created_at', ''), reverse=True)
        allowed = _scope(role)
        out = []
        for row in rows:
            if row['kitchen_id'] not in allowed:
                continue
            if kitchen_id and row['kitchen_id'] != kitchen_id:
                continue
            if review_status and row['review_status'] != review_status:
                continue
            out.append({k: row[k] for k in ('inspection_id', 'revision', 'kitchen_id', 'shift_id', 'batch_id',
                                             'image_id', 'execution_status', 'review_status', 'qc_disposition',
                                             'created_at')})
        return {'inspections': out, 'count': len(out)}

    @app.get('/api/inspections/{inspection_id}')
    async def get_inspection(inspection_id: str, role: Role = 'ADMIN'):
        record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in _scope(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        record['audit'] = store.history(inspection_id)
        record['manifest'] = MANIFEST
        return record

    @app.post('/api/inspections/{inspection_id}/run')
    async def run_inspection(inspection_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in _scope(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        _ensure_asset_local(record['image_id'])
        dataset_id = store.get('by_image', record['image_id'])
        if not dataset_id:
            snapshot = {'images': [{'image_id': record['image_id'], 'asset_path': record['storage_path'],
                                    'width': record['image_width'], 'height': record['image_height']}],
                        'annotations': []}
            dataset_id = uuid.uuid4().hex
            digest = _hash(json.dumps(snapshot, sort_keys=True).encode())
            store.put('dataset', dataset_id, {'data': snapshot, 'hash': digest})
            store.put('by_image', record['image_id'], dataset_id)
        mode = payload.get('mode', 'baseline')
        if mode not in {'baseline', 'ai'}:
            raise HTTPException(422, 'mode must be baseline or ai')
        record.update(execution_status='RUNNING', review_status='REVIEW_PENDING')
        store.put('inspection', inspection_id, record)
        store.append(inspection_id, 'inference_requested', {'mode': mode, 'actor': _actor(role)})
        started = await _run_shared_run(record, dataset_id, mode, mode == 'ai')
        run = store.get('run', started['run_id']) or {}
        record['run_id'] = started['run_id']
        record['state'] = run.get('state')
        record['run_status'] = run.get('status')
        record['execution_status'] = 'COMPLETED' if run.get('state') in {'completed', 'partial'} else 'FAILED'
        prediction = run.get('ai_result') or run.get('baseline_result')
        if record['execution_status'] != 'COMPLETED' or not prediction:
            # Provider failure or invalid model output: never a PASS, never auto-approved.
            record['review_status'] = 'UNVERIFIED'
            record['prediction'] = None
        else:
            record['prediction'] = prediction
        record['evidence_ids'] = sorted({e['evidence_id'] for e in run.get('evidence', [])})
        record['model_version'] = (run.get('usage') or {}).get('model_id') or 'baseline-local-v1'
        record['latency_ms'] = (run.get('usage') or {}).get('latency_ms')
        record['usage'] = run.get('usage')
        record['errors'] = run.get('errors', [])
        # Milestone vocabulary. `prediction` is only ever the AI result when the
        # domain validator accepted it, so this cannot report success for a
        # fallback or a rejected response.
        ai_accepted = bool(record['prediction'] is not None and run.get('ai_result'))
        record['inference_status'] = _inference_status(mode, run, record['prediction'], ai_accepted)
        record['prediction_source'] = 'model' if ai_accepted else (
            'baseline' if record['prediction'] else 'none')
        record['provider_request_id'] = (run.get('usage') or {}).get('request_id')
        record['provider_http_status'] = (run.get('usage') or {}).get('http_status')
        store.put('inspection', inspection_id, record)
        store.append(inspection_id, 'inference', {'mode': mode, 'state': run.get('state'),
                                                  'status': run.get('status'), 'model': record['model_version']})
        return record

    def _shared_runs_endpoint():
        """Reuse the shared runtime's run pipeline instead of reimplementing it."""
        for route in app.routes:
            if getattr(route, 'path', None) == '/api/runs' and 'POST' in getattr(route, 'methods', set()):
                return route.endpoint
        raise RuntimeError('Shared /api/runs endpoint not found')

    async def _start_shared_run(dataset_id, image_id, mode, use_ai):
        from fastapi import BackgroundTasks
        from shared_mvp.app import RunRequest
        background = BackgroundTasks()
        started = await _shared_runs_endpoint()(
            RunRequest(dataset_id=dataset_id, mode=mode, params={'image_id': image_id}),
            background)
        # Starlette normally drains BackgroundTasks after the response is sent.
        # This adapter runs inside one request, so the shared work() closure is
        # awaited here to keep the pipeline synchronous and observable.
        for task in background.tasks:
            await task.func(*task.args, **task.kwargs)
        return started

    def _inference_status(mode, run, prediction, ai_accepted):
        """Classify the real provider outcome into the agreed milestone vocabulary.

        The point of this is that "the app returned a prediction" and "the model
        produced a validated result" are different claims. Only INFERENCE_SUCCEEDED
        may be described as a successful model inference.

        INFERENCE_BLOCKED  credentials or configuration unavailable; nothing was sent
        PROVIDER_INVOKED  a real request was attempted
        PROVIDER_RESPONDED the provider returned an HTTP response (any status)
        INFERENCE_SUCCEEDED valid model output was received and passed validation
        INFERENCE_FAILED  the provider or the domain validator rejected the result
        NOT_REQUESTED     baseline mode, no provider call was made
        """
        if mode != 'ai':
            return 'NOT_REQUESTED'
        usage = run.get('usage') or {}
        errors = run.get('errors') or []
        codes = {e.get('code') for e in errors if isinstance(e, dict)}
        if not usage.get('provider_called'):
            # No credential, no model id, or no evidence to send. Nothing was attempted.
            return 'INFERENCE_BLOCKED' if codes else 'INFERENCE_BLOCKED'
        if usage.get('http_status') is not None:
            pass  # an HTTP status exists, so the provider did answer
        if ai_accepted:
            return 'INFERENCE_SUCCEEDED'
        return 'INFERENCE_FAILED'

    async def _run_shared_run(record, dataset_id, mode, use_ai):
        del use_ai  # the shared endpoint decides provider behaviour from its own config
        return await _start_shared_run(dataset_id, record['image_id'], mode, mode == 'ai')

    @app.post('/api/inspections', status_code=201)

    # ---------------------------------------------------------------- agent

    def agent_tool_get_inspection(actor_role: Role, inspection_id: str):
        record = store.get('inspection', inspection_id)
        if not record:
            return {'error': 'Unknown inspection'}
        if record['kitchen_id'] not in _scope(actor_role):
            return {'error': 'outside authorized kitchen scope'}
        return {'inspection_id': record['inspection_id'], 'label': (record.get('prediction') or {}).get('predicted_label'),
                'review_status': record['review_status'], 'evidence_ids': record['evidence_ids'],
                'manifest_version': record['manifest_version'], 'needs_review': record['review_status'] != 'APPROVED'}

    def agent_tool_list_inspections(actor_role: Role, review_status: str | None = None):
        rows = store.list_kind('inspection')
        allowed = _scope(actor_role)
        return {'inspections': [{'inspection_id': r['inspection_id'], 'kitchen_id': r['kitchen_id'],
                                 'review_status': r['review_status'], 'label': (r.get('prediction') or {}).get('predicted_label')}
                                for r in rows
                                if r['kitchen_id'] in allowed and (not review_status or r['review_status'] == review_status)],
                'count': sum(1 for r in rows if r['kitchen_id'] in allowed and (not review_status or r['review_status'] == review_status))}

    def agent_tool_get_kitchen_summary(actor_role: Role, kitchen_id: str):
        if kitchen_id not in _scope(actor_role):
            return {'error': 'outside authorized kitchen scope'}
        rows = store.list_kind('inspection')
        mine = [r for r in rows if r['kitchen_id'] == kitchen_id]
        counts: dict[str, int] = {}
        for row in mine:
            label = (row.get('prediction') or {}).get('predicted_label') or 'not_run'
            counts[label] = counts.get(label, 0) + 1
        return {'kitchen_id': kitchen_id, 'total': len(mine), 'labels': counts,
                'pending_review': sum(1 for r in mine if r['review_status'] == 'REVIEW_PENDING')}

    TOOLS = {
        'get_inspection': agent_tool_get_inspection,
        'list_inspections': agent_tool_list_inspections,
        'get_kitchen_summary': agent_tool_get_kitchen_summary,
    }

    @app.post('/api/agent/chat')
    async def agent_chat(request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        question = str(payload.get('question', '')).strip()
        if not question:
            raise HTTPException(422, 'question is required')
        proposed: list[dict] = []
        answer = ''
        tool_calls: list[dict] = []
        if re.search(r'\b(ringkasan|summary|kitchen|dapur)\b', question, re.I):
            kitchen = next((k for k in _scope(role) if k.lower() in question.lower()), None) or sorted(_scope(role))[0]
            result = agent_tool_get_kitchen_summary(role, kitchen)
            tool_calls.append({'tool': 'get_kitchen_summary', 'args': {'kitchen_id': kitchen}})
            if result['labels']:
                spread = ', '.join(f"{k} {v}" for k, v in sorted(result['labels'].items()))
            else:
                spread = 'belum ada prediksi'
            answer = (f"Dapur {kitchen}: {result['total']} inspeksi tercatat, "
                      f"{result['pending_review']} menunggu review. "
                      f"Distribusi label: {spread}.")
        else:
            target = payload.get('inspection_id')
            result = agent_tool_list_inspections(role, payload.get('review_status'))
            tool_calls.append({'tool': 'list_inspections', 'args': {}})
            if target:
                detail = agent_tool_get_inspection(role, target)
                tool_calls.append({'tool': 'get_inspection', 'args': {'inspection_id': target}})
                answer = (f"Inspeksi {target}: prediksi {detail.get('label') or 'belum ada'}, "
                          f"status review {detail.get('review_status')}. Evidence: {detail.get('evidence_ids') or 'belum ada'}. "
                          "Prediksi model adalah temuan visual dan bukan persetujuan QC.")
            else:
                answer = f"Ada {result['count']} inspeksi dalam cakupan Anda."
        if re.search(r'\b(uncertain|tidak pasti)\b', question, re.I):
            pending = agent_tool_list_inspections(role, 'REVIEW_PENDING')
            if pending['count']:
                proposed.append({'kind': 'create_followup_task',
                                 'description': 'Recapture and manual review for uncertain inspections',
                                 'inspection_ids': [i['inspection_id'] for i in pending['inspections'][:5]]})
        store.put('agent_session', uuid.uuid4().hex, {'role': role, 'question': question,
                                                     'answer': answer, 'tool_calls': tool_calls,
                                                     'proposed': proposed, 'created_at': _now()})
        return {'answer': answer, 'tool_calls': tool_calls, 'proposed_actions': proposed,
                'grounded': True, 'disclaimer': 'Visual inspection only. Not proof of food safety.'}

    @app.post('/api/agent/actions/{action_id}/confirm')
    async def confirm_action(action_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES or not ROLES[role]['agent_write']:
            raise HTTPException(403, 'Role may not execute agent write actions')
        action = store.get('agent_action', action_id)
        if not action:
            raise HTTPException(404, 'Unknown or unconfirmed agent action')
        if action.get('confirmed'):
            return action
        for inspection_id in action.get('inspection_ids', []):
            record = store.get('inspection', inspection_id)
            if record and record['kitchen_id'] in _scope(role):
                record['followup_task'] = {'description': action.get('description'), 'created_at': _now()}
                store.put('inspection', inspection_id, record)
                store.append(inspection_id, 'followup_created', {'actor': _actor(role), 'action_id': action_id})
        action['confirmed'] = True
        store.put('agent_action', action_id, action)
        return action

    # ---------------------------------------------------------------- admin

    @app.get('/api/admin/overview')
    async def overview(role: Role = 'ADMIN', kitchen_id: str | None = None):
        rows = store.list_kind('inspection')
        allowed = _scope(role)
        rows = [r for r in rows if r['kitchen_id'] in allowed and (not kitchen_id or r['kitchen_id'] == kitchen_id)]
        def count(pred):
            return sum(1 for r in rows if pred(r))
        labels: dict[str, int] = {}
        for row in rows:
            label = (row.get('prediction') or {}).get('predicted_label') or 'not_run'
            labels[label] = labels.get(label, 0) + 1
        # Distinguish a real model inference from a deterministic baseline or a
        # blocked/failed attempt. Aggregating these into one number would hide
        # exactly the failure a supervisor needs to see.
        inference: dict[str, int] = {}
        for row in rows:
            key = row.get('inference_status') or 'NOT_RECORDED'
            inference[key] = inference.get(key, 0) + 1
        failures: dict[str, int] = {}
        for row in rows:
            for err in row.get('errors') or []:
                code = err.get('code') if isinstance(err, dict) else str(err)
                if code:
                    failures[code] = failures.get(code, 0) + 1
        used = sum(p.stat().st_size for p in asset_root(PID).glob('*.png'))
        recent = sorted(rows, key=lambda r: r['created_at'], reverse=True)[:8]
        return {
            'inspections_total': len(rows),
            'today': len(rows),
            'unverified': count(lambda r: r['review_status'] == 'UNVERIFIED'),
            'pending_review': count(lambda r: r['review_status'] == 'REVIEW_PENDING'),
            'approved': count(lambda r: r['review_status'] == 'APPROVED'),
            'rejected': count(lambda r: r['review_status'] == 'REJECTED'),
            'uncertain_predictions': labels.get('uncertain', 0),
            'failed_inference': count(lambda r: r['execution_status'] == 'FAILED'),
            'labels': labels,
            'inference_status': inference,
            'failure_categories': failures,
            'model_inference_count': inference.get('INFERENCE_SUCCEEDED', 0),
            'baseline_only_count': count(lambda r: r.get('prediction_source') == 'baseline'),
            'storage_bytes': used,
            'storage_budget_bytes': STORAGE_BUDGET_BYTES,
            'storage_measured': True,
            'activity': [{'inspection_id': r['inspection_id'], 'event': r['execution_status'],
                          'inference_status': r.get('inference_status') or 'NOT_RECORDED',
                          'prediction_source': r.get('prediction_source') or 'none',
                          'model_version': r.get('model_version'),
                          'at': r['created_at']} for r in recent],
        }

    @app.get('/api/infra/readiness')
    async def infra_readiness():
        payload = c05_gemini.readiness_payload()
        payload['project_id'] = PID
        payload['storage_budget_bytes'] = STORAGE_BUDGET_BYTES
        return payload

    @app.get('/api/manifests')
    async def manifests(role: Role = 'CREW'):
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        return {'manifests': [MANIFEST]}

    @app.post('/api/inspections/{inspection_id}/review')
    async def review_inspection(inspection_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        if not ROLES[role]['approve']:
            raise HTTPException(403, 'Role may not approve or reject inspections')
        record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in _scope(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        if record['review_status'] in {'APPROVED', 'REJECTED'}:
            raise HTTPException(409, 'Review is immutable; re-inference creates a new revision')
        decision = payload.get('decision')
        if decision not in {'APPROVED', 'REJECTED'}:
            raise HTTPException(422, 'decision must be APPROVED or REJECTED')
        disposition = payload.get('qc_disposition')
        if disposition not in {'ACCEPT', 'HOLD', 'REJECT'}:
            raise HTTPException(422, 'qc_disposition must be ACCEPT, HOLD or REJECT')
        if decision == 'REJECTED' and not str(payload.get('comment', '')).strip():
            raise HTTPException(422, 'A rejection requires a comment')
        record.update(review_status=decision, qc_disposition=disposition,
                      reviewed_by=_actor(role), reviewed_at=_now(),
                      review_comment=str(payload.get('comment', ''))[:2000])
        store.put('inspection', inspection_id, record)
        store.append(inspection_id, 'review', {'decision': decision, 'disposition': disposition,
                                               'actor': _actor(role)})
        return record

    @app.post('/api/inspections/{inspection_id}/reinfer')
    async def reinfer(inspection_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ROLES:
            raise HTTPException(422, 'Unknown role')
        record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in _scope(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        record['revision'] = record['revision'] + 1
        record['review_status'] = 'UNVERIFIED'
        record['qc_disposition'] = None
        record['execution_status'] = 'CREATED'
        record.pop('prediction', None)
        store.put('inspection', inspection_id, record)
        store.append(inspection_id, 'reinference_requested', {'revision': record['revision'],
                                                              'actor': _actor(role)})
        return record

    @app.get('/api/reports/{inspection_id}')
    async def report(inspection_id: str, role: Role = 'SUPERVISOR'):
        record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in _scope(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        approved = record['review_status'] == 'APPROVED'
        body = {
            'inspection_id': inspection_id,
            'inspection_revision': record['revision'],
            'image_sha256': record['image_sha256'],
            'manifest_version': record['manifest_version'],
            'prediction': record.get('prediction'),
            # Provenance: a deterministic baseline must never be readable as a
            # model finding once the report leaves the system.
            'inference_status': record.get('inference_status'),
            'prediction_source': record.get('prediction_source'),
            'provider_http_status': record.get('provider_http_status'),
            'provider_request_id': record.get('provider_request_id'),
            'evidence_ids': record['evidence_ids'],
            'model_version': record.get('model_version'),
            'prompt_version': record['prompt_version'],
            'schema_version': record['schema_version'],
            'reviewer_id': record.get('reviewed_by'),
            'reviewed_at': record.get('reviewed_at'),
            'review_decision': record.get('review_status'),
            'qc_disposition': record.get('qc_disposition'),
            'report_generated_at': _now(),
            'report_status': 'OFFICIAL' if approved else 'UNVERIFIED - NOT APPROVED',
            'disclaimer': ('This report documents visual inspection findings only. It does not establish '
                           'microbiological safety, nutritional composition, or measured food weight.'),
        }
        body['report_snapshot_hash'] = _hash(json.dumps(body, sort_keys=True).encode())
        store.append(inspection_id, 'report_generated', {'status': body['report_status'], 'actor': _actor(role)})
        return body

    return app


app = create_app()