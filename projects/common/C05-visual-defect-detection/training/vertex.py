"""Vertex AI supervised-tuning export and job control for C05.

Training examples are built with the same prompt builder the live service
uses (`shared_mvp.provider.build_prompt`), the same evidence construction and
the same image preparation, so the tuned model is trained on exactly the
request shape it will receive in production. The target is the C05 output
contract, which the live domain validator also enforces.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
ROOT = PROJECT.parent.parent.parent
for extra in (str(PROJECT / 'src'), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from shared_mvp.contracts import model as _model  # noqa: E402
from shared_mvp.domain import evidence as _evidence  # noqa: E402
from shared_mvp.provider import build_prompt  # noqa: E402

from dataset import Example, normalize_image  # noqa: E402

CONFIG = json.loads((PROJECT / 'config' / 'project.json').read_text(encoding='utf-8'))
OUT_MODEL = _model(CONFIG['output'], 'C05Output')
DEFAULT_REGION = 'us-central1'


def image_id_for(ex: Example) -> str:
    return ex.sha256[:32]


def live_request(image_id: str, width: int, height: int) -> tuple[dict, str]:
    """(prompt, evidence_id) exactly as c05_api + shared runtime would build them."""
    record = {'image_id': image_id, 'asset_path': f'{image_id}.png', 'width': width, 'height': height}
    ref = f'C05:images:{image_id}'
    # The deterministic baseline only handles 64x64 fixtures; for any real photo
    # it returns this "uncertain / unsupported_dimensions" result (domain.compute).
    baseline = {'predicted_label': 'uncertain', 'regions': [], 'needs_review': True,
                'confidence_score': 0.35, 'evidence_ids': [ref],
                'components': []}
    run = {'baseline_result': baseline, 'evidence': _evidence('C05', {'images': [record]}, {ref}),
           'config': {'params': {'image_id': image_id}}}
    return build_prompt(CONFIG, run, OUT_MODEL), ref


def target_for(ex: Example, ref: str) -> dict:
    target = {'predicted_label': ex.label, 'regions': ex.boxes, 'needs_review': ex.label != 'meal_complete',
              'confidence_score': 1.0, 'evidence_ids': [ref],
              'components': []}
    return OUT_MODEL.model_validate(target).model_dump()


def export_split(examples: list[Example], dataset_root: Path, build_dir: Path, name: str,
                 gcs_prefix: str | None) -> dict:
    """Write normalised images and `{name}.jsonl` in Gemini SFT format.

    With no gcs_prefix the file uses `file://` URIs for local inspection; Vertex
    needs gs:// URIs, so pass --gcs-prefix before submitting a job.
    """
    images_dir = build_dir / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    out = build_dir / f'{name}.jsonl'
    with out.open('w', encoding='utf-8') as fh:
        for ex in examples:
            data, width, height = normalize_image(dataset_root / ex.image)
            image_id = image_id_for(ex)
            (images_dir / f'{image_id}.png').write_bytes(data)
            prompt, ref = live_request(image_id, width, height)
            uri = (f'{gcs_prefix.rstrip("/")}/images/{image_id}.png' if gcs_prefix
                   else (images_dir / f'{image_id}.png').resolve().as_uri())
            fh.write(json.dumps({'contents': [
                {'role': 'user', 'parts': [{'text': json.dumps(prompt, ensure_ascii=False)},
                                           {'fileData': {'mimeType': 'image/png', 'fileUri': uri}}]},
                {'role': 'model', 'parts': [{'text': json.dumps(target_for(ex, ref))}]},
            ]}, ensure_ascii=False) + '\n')
    return {'file': str(out), 'examples': len(examples)}


def upload(build_dir: Path, gcs_prefix: str) -> dict:
    """Copy build/images and the split files to gs://bucket/prefix."""
    from google.cloud import storage  # type: ignore

    if not gcs_prefix.startswith('gs://'):
        raise ValueError('gcs_prefix must start with gs://')
    bucket_name, _, prefix = gcs_prefix[5:].partition('/')
    bucket = storage.Client().bucket(bucket_name)
    count = 0
    for path in sorted(build_dir.rglob('*')):
        if path.is_file() and (path.suffix == '.png' or path.name in {'train.jsonl', 'validation.jsonl'}):
            rel = path.relative_to(build_dir).as_posix()
            bucket.blob(f'{prefix.rstrip("/")}/{rel}' if prefix else rel).upload_from_filename(str(path))
            count += 1
    return {'uploaded': count, 'prefix': gcs_prefix}


def _session():
    import google.auth  # type: ignore
    from google.auth.transport.requests import AuthorizedSession  # type: ignore

    creds, project = google.auth.default(scopes=['https://www.googleapis.com/auth/cloud-platform'])
    return AuthorizedSession(creds), project


def tuning_request(base_model: str, gcs_prefix: str, display_name: str, epochs: int,
                   adapter_size: str, lr_multiplier: float | None) -> dict:
    hyper = {'epochCount': epochs, 'adapterSize': adapter_size}
    if lr_multiplier:
        hyper['learningRateMultiplier'] = lr_multiplier
    return {'baseModel': base_model, 'tunedModelDisplayName': display_name,
            'supervisedTuningSpec': {'trainingDatasetUri': f'{gcs_prefix.rstrip("/")}/train.jsonl',
                                     'validationDatasetUri': f'{gcs_prefix.rstrip("/")}/validation.jsonl',
                                     'hyperParameters': hyper}}


def submit_tuning(body: dict, project: str | None, region: str) -> dict:
    session, adc_project = _session()
    project = project or os.environ.get('GOOGLE_CLOUD_PROJECT') or adc_project
    url = f'https://{region}-aiplatform.googleapis.com/v1/projects/{project}/locations/{region}/tuningJobs'
    res = session.post(url, json=body, timeout=60)
    if res.status_code >= 300:
        raise RuntimeError(f'Tuning job rejected: HTTP {res.status_code} {res.text[:400]}')
    return res.json()


def tuning_status(job_name: str) -> dict:
    """job_name is projects/{p}/locations/{r}/tuningJobs/{id} as returned on submit."""
    region = job_name.split('/locations/')[1].split('/')[0]
    session, _ = _session()
    res = session.get(f'https://{region}-aiplatform.googleapis.com/v1/{job_name}', timeout=60)
    res.raise_for_status()
    job = res.json()
    return {'name': job.get('name'), 'state': job.get('state'), 'error': job.get('error'),
            'tuned_model': (job.get('tunedModel') or {}).get('model'),
            'endpoint': (job.get('tunedModel') or {}).get('endpoint'),
            'create_time': job.get('createTime'), 'end_time': job.get('endTime')}
