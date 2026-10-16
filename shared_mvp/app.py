from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import Response, JSONResponse
from pydantic import Field, ValidationError

from shared_mvp.contracts import Invalid, Strict, model, validated, validate_collections
from shared_mvp.domain import evidence, evidence_refs
from shared_mvp.provider import ProviderFailure, call_gemini
from shared_mvp.store import Store
from shared_mvp.assets import resolve

ROOT = Path(__file__).resolve().parents[1]


def _allowed_hosts() -> set[str]:
    """Host names accepted past the DNS-rebinding guard.

    Defaults preserve the historical strict local behaviour exactly. Setting
    `MVP_ALLOWED_HOSTS` (for example to the Cloud Run service hostname) permits
    additional hosts in the target environment.
    """
    base = {"localhost", "127.0.0.1", "testserver", "[", ""}
    extra = {h.strip().lower() for h in os.environ.get("MVP_ALLOWED_HOSTS", "").split(",") if h.strip()}
    return base | extra


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def locate(pid):
    choices = list((ROOT / 'projects').glob(f'*/*{pid}-*'))
    if len(choices) != 1:
        raise ValueError('Unknown project ID')
    return choices[0]


class DatasetRequest(Strict):
    project_id: str
    data: dict


class RunRequest(Strict):
    dataset_id: str
    mode: Literal['baseline', 'ai'] = 'baseline'
    params: dict


class ReviewRequest(Strict):
    expected_revision: int = Field(ge=1)
    decision: Literal['approve', 'reject']
    comment: str = Field(default='', max_length=2000)


class EditRequest(Strict):
    expected_revision: int = Field(ge=1)
    draft: dict


def create_app(pid, db_path=None, provider=None, transport=None, store=None):
    root = locate(pid)
    schema = json.loads((root / 'config' / 'project.json').read_text())
    domain = load(root / 'src' / 'domain.py', f'domain_{pid}')
    fixture = load(root / 'fixtures' / 'sample.py', f'fixture_{pid}')
    inputs = model('{' + schema['inputs'].replace(';', ',') + '}', pid + 'Input')
    params_model = model(schema['params'], pid + 'Params')
    outputs = model(schema['output'], pid + 'Output')
    # A project may inject its own Store-compatible backend (for example the
    # Firestore adapter). When none is given the historical SQLite behaviour
    # applies exactly, so the other 23 projects are unaffected.
    if store is None:
        store = Store(db_path or str(Path(tempfile.gettempdir()) / 'sea-ai-mvp' / f'{pid}.sqlite'))
    active = threading.Lock()
    app = FastAPI(title=schema['name'], description='Local synthetic-data MVP; not a production deployment.')
    app.state.store = store
    app.state.output_model = outputs
    app.state.domain = domain
    app.state.fixture = fixture

    @app.middleware('http')
    async def bounded_local_request(request: Request, call_next):
        # Loopback server additionally rejects DNS-rebinding Host names.
        #
        # In cloud the Host header is the service URL rather than loopback, so this
        # guard would reject every real request. It stays strict by default and is
        # relaxed only when an operator names the exact hosts to accept, which
        # preserves the DNS-rebinding protection for local runs.
        host = request.headers.get('host', '').split(':')[0]
        if host not in _allowed_hosts():
            return JSONResponse({'detail': 'Local mode accepts loopback hosts only'}, status_code=403)
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}':
            return JSONResponse({'detail': 'Cross-origin writes are disabled'}, status_code=403)
        if request.method in {'POST', 'PATCH'}:
            # Stream with bound instead of materializing arbitrary content-length.
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > 2 * 1024 * 1024:
                    return JSONResponse({'detail': 'Payload limit 2 MiB'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
            try:
                json.loads(request._body)
            except (ValueError, UnicodeDecodeError):
                return JSONResponse({'detail': 'Malformed JSON'}, status_code=400)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
        return response

    @app.exception_handler(Invalid)
    async def invalid_handler(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=422)

    @app.exception_handler(ValidationError)
    async def validation_handler(request, exc):
        # Do not echo untrusted raw data or credentials from error input.
        return JSONResponse({'detail': [{'loc': list(e['loc']), 'type': e['type'], 'msg': e['msg']}
                                       for e in exc.errors(include_input=False)]}, status_code=422)

    @app.get('/')
    async def console():
        return Response((ROOT / 'shared_mvp' / 'ui' / 'index.html').read_bytes(), media_type='text/html')

    @app.get('/ui/{name}')
    async def ui_asset(name: Literal['app.js', 'style.css']):
        return Response((ROOT / 'shared_mvp' / 'ui' / name).read_bytes(), media_type='text/javascript' if name.endswith('.js') else 'text/css')

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'mode': 'local_fixture', 'project_id': pid}

    @app.get('/api/project')
    async def project_info():
        return {k: schema[k] for k in ['id', 'name', 'goal', 'track', 'inputs', 'params', 'output', 'limitations']}

    @app.get('/api/fixture')
    async def sample():
        return fixture.sample()

    @app.get('/api/assets/{name}')
    async def image_asset(name: str):
        path = resolve(pid, name)
        return Response(path.read_bytes(), media_type='image/png' if name.endswith('.png') else 'image/jpeg')

    @app.post('/api/datasets', status_code=201)
    async def import_data(body: DatasetRequest):
        if body.project_id != pid:
            raise Invalid('This app handles one project only')
        data = validated(inputs, body.data)
        count = validate_collections(data)
        domain.validate(data)
        digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
        dataset_id = uuid.uuid4().hex
        store.put('dataset', dataset_id, {'data': data, 'hash': digest})
        return {'dataset_id': dataset_id, 'project_id': pid, 'record_count': count, 'snapshot_hash': digest}

    def get_run(run_id):
        run = store.get('run', run_id)
        if not run:
            raise HTTPException(404, 'Unknown run')
        return run

    async def work(run_id, data, settings, mode):
        run = get_run(run_id)
        try:
            run['state'] = 'running'
            store.put('run', run_id, run)
            computed = domain.compute(data, settings)
            baseline = validated(outputs, computed['result'])
            entries = evidence(pid, data, computed.get('authorized'))
            if not evidence_refs(baseline) <= {e['evidence_id'] for e in entries}:
                raise Invalid('Domain returned unresolved evidence')
            run.update(state='completed', status=computed['status'], revision=1,
                       baseline_result=baseline, draft=baseline, evidence=entries)
            if mode == 'ai':
                try:
                    candidate, usage = await call_gemini(schema, run, outputs, provider, transport)
                    # Additional project-specific guards can reject plausible but unsafe outputs.
                    if hasattr(domain, 'validate_output'):
                        domain.validate_output(candidate, run)
                    if hasattr(domain, 'protect_output'):
                        domain.protect_output(candidate, run, data)
                    run.update(ai_result=candidate, draft=candidate, usage=usage)
                except (ProviderFailure, Invalid) as exc:
                    code = exc.code if isinstance(exc, ProviderFailure) else 'invalid_model_output'
                    run.update(state='partial', status=code, errors=[{'code': code, 'message': 'AI result unavailable; baseline retained', 'field': None}])
                    if isinstance(exc, ProviderFailure):
                        run['usage'].update(exc.usage)
            store.append(run_id, 'completed', {'state': run['state'], 'status': run['status']})
        except Exception as exc:
            run.update(state='failed', status='failed', errors=[{'code': 'baseline_error', 'message': type(exc).__name__, 'field': None}])
            store.append(run_id, 'failed', {'error_type': type(exc).__name__})
        finally:
            store.put('run', run_id, run)
            active.release()

    @app.post('/api/runs', status_code=202)
    async def start_run(body: RunRequest, background: BackgroundTasks):
        snapshot = store.get('dataset', body.dataset_id)
        if snapshot is None:
            raise HTTPException(404, 'Unknown dataset')
        settings = validated(params_model, body.params)
        domain.validate_params(snapshot['data'], settings)
        if not active.acquire(blocking=False):
            raise HTTPException(429, 'One active run per local app')
        run_id = uuid.uuid4().hex
        run = {'run_id': run_id, 'project_id': pid, 'dataset_id': body.dataset_id,
               'state': 'queued', 'status': 'ok', 'revision': 0,
               'baseline_result': None, 'ai_result': None, 'draft': None,
               'evidence': [], 'errors': [], 'review': None,
               'usage': {'provider_called': False, 'input_tokens': 0, 'output_tokens': 0,
                         'model_id': None, 'prompt_version': 'v1', 'latency_ms': 0},
               'config': {'seed': 42, 'algorithm_version': 'local-v1', 'params': settings,
                          'snapshot_hash': snapshot['hash'], 'max_provider_calls': 1}}
        try:
            store.put('run', run_id, run)
            store.append(run_id, 'queued', {'mode': body.mode, 'config': run['config']})
            background.add_task(work, run_id, snapshot['data'], settings, body.mode)
        except Exception:
            active.release()
            raise
        return {'run_id': run_id, 'state': 'queued'}

    @app.get('/api/runs/{run_id}')
    async def fetch_run(run_id: str):
        return get_run(run_id)

    @app.get('/api/runs/{run_id}/audit')
    async def audit(run_id: str):
        get_run(run_id)
        return store.history(run_id)

    def terminal(run, revision):
        if run['state'] not in {'completed', 'partial'} or revision != run['revision']:
            raise HTTPException(409, 'Run not reviewable or stale revision')

    @app.patch('/api/runs/{run_id}/draft')
    async def edit(run_id: str, body: EditRequest):
        with store.lock:
            run = get_run(run_id)
            terminal(run, body.expected_revision)
            draft = validated(outputs, body.draft)
            if not evidence_refs(draft) <= {e['evidence_id'] for e in run['evidence']}:
                raise Invalid('Unknown evidence ID')
            if hasattr(domain, 'validate_output'):
                domain.validate_output(draft, run)
            if hasattr(domain, 'protect_output'):
                domain.protect_output(draft, run, store.get('dataset', run['dataset_id'])['data'])
            run.update(draft=draft, revision=run['revision'] + 1, review=None)
            store.put('run', run_id, run)
            store.append(run_id, 'edited', {'revision': run['revision']})
            return run

    @app.post('/api/runs/{run_id}/reviews', status_code=201)
    async def review(run_id: str, body: ReviewRequest):
        with store.lock:
            run = get_run(run_id)
            terminal(run, body.expected_revision)
            run['review'] = {'actor': 'local-reviewer', 'decision': body.decision,
                             'revision': run['revision'], 'comment': body.comment,
                             'timestamp': datetime.now(timezone.utc).isoformat()}
            store.put('run', run_id, run)
            store.append(run_id, 'reviewed', run['review'])
            return run['review']

    @app.get('/api/runs/{run_id}/export')
    async def export(run_id: str):
        run = get_run(run_id)
        if not run['review'] or run['review']['decision'] != 'approve' or run['review']['revision'] != run['revision']:
            raise HTTPException(409, 'Current revision requires approval')
        if not evidence_refs(run['draft']) <= {e['evidence_id'] for e in run['evidence']}:
            raise HTTPException(409, 'Evidence no longer resolves')
        return JSONResponse(run, headers={'Content-Disposition': f'attachment; filename="{pid}-{run_id}.json"'})

    return app
