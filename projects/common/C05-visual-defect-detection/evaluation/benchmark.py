"""C05 prototype benchmark: API latency, claim-triage scaling and detection checks.

    python projects/common/C05-visual-defect-detection/evaluation/benchmark.py [--out report.json]

Runs fully offline against an in-process app on a temporary SQLite store, so the
numbers measure this code, not the network or Gemini. Live Gemini latency and
token figures come from the recorded production evidence and are reported
separately, labelled as such.
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import io
import json
import os
import random
import statistics
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parent.parent.parent
for extra in (str(PROJECT / 'src'), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

os.environ.pop('GOOGLE_CLOUD_PROJECT', None)  # keep the run offline and deterministic

from PIL import Image  # noqa: E402

import c05_claims  # noqa: E402
from shared_mvp.testing import LocalClient  # noqa: E402

WIB = timezone(timedelta(hours=7))

# Recorded in docs/c05-deploy/DEPLOYMENT_EVIDENCE.md (production + staging, gemini-2.5-flash).
LIVE_GEMINI_EVIDENCE = {
    'source': 'docs/c05-deploy/DEPLOYMENT_EVIDENCE.md',
    'model': 'gemini-2.5-flash (Vertex AI, global endpoint, thinking off)',
    'production_inference_ms': 7514,
    'staging_inference_s_range': [7, 8],
    'input_tokens': [2173, 2179],
    'output_tokens': [255, 260],
    'thinking_off_vs_on_s': [2.0, 10.9],
    'browser_e2e_checks': '18/18 at 390px and 1440px',
}


def _load_api():
    spec = importlib.util.spec_from_file_location('c05_api_bench', PROJECT / 'src' / 'c05_api.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tray_b64() -> str:
    img = Image.new('RGB', (640, 480), (236, 238, 240))
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()


def _stats(samples_ms: list[float]) -> dict:
    s = sorted(samples_ms)
    pct = lambda p: s[min(len(s) - 1, int(round(p / 100 * (len(s) - 1))))]  # noqa: E731
    return {'n': len(s), 'p50_ms': round(pct(50), 1), 'p95_ms': round(pct(95), 1),
            'mean_ms': round(statistics.fmean(s), 1), 'max_ms': round(s[-1], 1)}


def _time(fn, n: int) -> dict:
    out = []
    for _ in range(n):
        t = time.perf_counter()
        res = fn()
        out.append((time.perf_counter() - t) * 1000)
        assert res.status_code < 300, (res.status_code, res.text[:200])
    return _stats(out)


def api_latency(client: LocalClient, n: int) -> dict:
    tray = _tray_b64()
    created: list[str] = []

    def create():
        r = client.post('/api/inspections', json={'role': 'SUPERVISOR', 'kitchen_id': 'KITCHEN-A',
                                                  'manifest_version': 1, 'mime_type': 'image/png',
                                                  'data_base64': tray})
        created.append(r.json()['inspection_id'])
        return r

    results = {'create_inspection': _time(create, n)}
    ids = iter(list(created))
    results['run_inspection_baseline'] = _time(
        lambda: client.post(f'/api/inspections/{next(ids)}/run', json={'role': 'SUPERVISOR', 'mode': 'baseline'}), n)
    results['admin_overview'] = _time(lambda: client.get('/api/admin/overview?role=ADMIN'), n)
    results['list_inspections'] = _time(lambda: client.get('/api/inspections?role=ADMIN'), n)
    client.post('/api/claims/demo-seed', json={'role': 'ADMIN'})
    today = datetime.now(WIB).date().isoformat()
    results['submit_claim'] = _time(lambda: client.post('/api/claims', json={
        'kitchen_id': 'KITCHEN-B', 'school_id': 'SDN-12', 'meal_date': today, 'reporter_type': 'parent',
        'contact': f'0812{random.randint(10_000_000, 99_999_999)}', 'affected_count': 1,
        'symptoms': ['nausea'], 'onset_at': datetime.now(timezone.utc).isoformat()}), n)
    results['list_claim_incidents'] = _time(lambda: client.get('/api/claims/incidents?role=ADMIN'), n)
    incident = max(client.get('/api/claims/incidents?role=ADMIN').json()['incidents'],
                   key=lambda i: i['integrity_score'])['incident_id']
    results['incident_detail_35_claims'] = _time(
        lambda: client.get(f'/api/claims/incidents/{incident}?role=ADMIN'), n)
    results['agent_chat'] = _time(lambda: client.post('/api/agent/chat', json={
        'role': 'ADMIN', 'question': 'Any poisoning claims?'}), n)
    return results


def _synthetic_claims(n: int, fake_share: float, rng: random.Random) -> tuple[list[dict], list[dict], set[str]]:
    """One kitchen-day with n claims, a share of them a coordinated wave."""
    day = datetime(2026, 10, 15, tzinfo=WIB)
    served_at = day.replace(hour=11, minute=30)
    schools = [f'SDN-{i:02d}' for i in range(1, 6)]
    services = [{'service_id': s, 'kitchen_id': 'KITCHEN-A', 'school_id': s, 'meal_date': '2026-10-15',
                 'batch_id': 'B', 'portions_served': 400, 'served_at': served_at.isoformat()} for s in schools]
    # Free-text reports from different people share topic words but not phrasing;
    # a pool this size keeps accidental near-duplicates at a realistic rate.
    words = ('vomited vomiting stomach ache fever diarrhoea dizzy nausea headache after lunch evening night '
             'morning clinic puskesmas doctor hospital child son daughter twins kids class grade teacher '
             'chicken egg rice tempeh fish vegetables soup smell sour cold warm cramps tired weak pale cried '
             'slept bathroom twice three times since hours home school bus water medicine oralit better worse '
             'still today yesterday noon around o clock mother father brother sister friend neighbour').split()
    claims, fake = [], set()
    n_fake = int(n * fake_share)
    for k in range(n):
        is_fake = k < n_fake
        cid = f'c{k:05d}'
        if is_fake:
            fake.add(cid)
            text = 'our children got severe food poisoning from the mbg lunch today and the kitchen must pay'
            contact = c05_claims.contact_hash(f'0812999900{k % 3:02d}')
            submitted = day.replace(hour=22) + timedelta(seconds=k * 5)
            school, affected = schools[0], 9
        else:
            text = ' '.join(rng.sample(words, rng.randint(9, 16)))
            contact = c05_claims.contact_hash(f'0813{k:08d}')
            submitted = day.replace(hour=13) + timedelta(minutes=rng.randint(0, 600))
            school, affected = rng.choice(schools[1:]), rng.randint(1, 2)
        claims.append({'claim_id': cid, 'school_id': school, 'affected_count': affected,
                       'onset_at': (served_at + timedelta(hours=rng.uniform(1, 8))).isoformat(),
                       'contact_hash': contact, 'photo': None, 'description': text,
                       'submitted_at': submitted.isoformat(), 'sought_medical': rng.random() < 0.2,
                       'hospitalized': False})
    return claims, services, fake


def triage_scaling(sizes: list[int]) -> list[dict]:
    rng = random.Random(1)
    rows = []
    for n in sizes:
        claims, services, fake = _synthetic_claims(n, 0.3, rng)
        t = time.perf_counter()
        result = c05_claims.assess_incident(claims, services, [])
        ms = (time.perf_counter() - t) * 1000
        flagged = {i for s in result['signals'] for i in s['claim_ids']}
        # A burst is the weakest signal (weight 10) and by design sweeps in any
        # claim filed in the same window; "strong" excludes burst-only hits.
        strong = {i for s in result['signals'] if s['code'] != 'SUBMISSION_BURST' for i in s['claim_ids']}
        genuine = {c['claim_id'] for c in claims} - fake
        rows.append({'claims': n, 'assess_ms': round(ms, 1),
                     'coordinated_flagged': f'{len(flagged & fake)}/{len(fake)}',
                     'genuine_flagged_any': f'{len(flagged & genuine)}/{len(genuine)}',
                     'genuine_flagged_strong': f'{len(strong & genuine)}/{len(genuine)}',
                     'signals': sorted(s['code'] for s in result['signals'])})
    return rows


def demo_scenario_detection() -> list[dict]:
    services, raw = c05_claims.demo_scenario(datetime.now(WIB).date())
    now = datetime.now(timezone.utc)
    by_incident: dict[str, list[dict]] = {}
    for r in raw:
        c = c05_claims.normalize_claim(r, now)
        c['submitted_at'], c['photo'] = r['submitted_at'], r.get('photo')
        by_incident.setdefault(c['incident_id'], []).append(c)
    rows = []
    for iid, claims in sorted(by_incident.items()):
        kitchen, day = claims[0]['kitchen_id'], claims[0]['meal_date']
        svc = [s for s in services if s['kitchen_id'] == kitchen and s['meal_date'] == day]
        res = c05_claims.assess_incident(claims, svc, [])
        wave = {c['claim_id'] for c in claims if c['contact_hash'] in {
            c05_claims.contact_hash(p) for p in ('081299990001', '081299990002', '081299990003')}}
        flagged = {i for s in res['signals'] for i in s['claim_ids']}
        rows.append({'incident': iid, 'claims': len(claims), 'integrity_score': res['integrity_score'],
                     'health_priority': res['health_priority'],
                     'coordinated_flagged': f'{len(flagged & wave)}/{len(wave)}',
                     'genuine_flagged': f'{len(flagged - wave)}/{len(claims) - len(wave)}'})
    return rows


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--n', type=int, default=30, help='requests per endpoint')
    p.add_argument('--out', default=str(HERE / 'benchmark_report.json'))
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        app = _load_api().create_app(str(Path(tmp) / 'bench.sqlite'))
        try:
            latency = api_latency(LocalClient(app), args.n)
        finally:
            app.state.store.close()
    report = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'environment': f'in-process ASGI, SQLite, Python {sys.version.split()[0]}, {sys.platform}',
        'api_latency_offline': latency,
        'claim_triage_scaling': triage_scaling([50, 200, 500, 1000]),
        'demo_scenario_detection': demo_scenario_detection(),
        'live_gemini_evidence': LIVE_GEMINI_EVIDENCE,
    }
    Path(args.out).write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
