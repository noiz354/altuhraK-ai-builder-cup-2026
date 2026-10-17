"""C05 tuning pipeline CLI.

    python training/pipeline.py synth   --out training/data/synthetic
    python training/pipeline.py prepare --data training/data/synthetic --build training/build/run1 \
                                        [--gcs-prefix gs://BUCKET/c05-tuning/run1]
    python training/pipeline.py upload  --build training/build/run1 --gcs-prefix gs://BUCKET/c05-tuning/run1
    python training/pipeline.py tune    --gcs-prefix gs://BUCKET/c05-tuning/run1 --base-model MODEL [--submit]
    python training/pipeline.py status  --job projects/P/locations/R/tuningJobs/ID
    python training/pipeline.py eval    --data training/data/synthetic --build training/build/run1 \
                                        --predictor majority|gemini

Every step writes a JSON artifact into the build directory so a run can be
audited later: validation report, split stats, export stats, tuning request,
evaluation report.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import dataset  # noqa: E402


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')


def cmd_synth(args) -> dict:
    import synth
    return synth.generate(Path(args.out), args.households, args.photos, args.seed)


def cmd_prepare(args) -> dict:
    import vertex

    data, build = Path(args.data), Path(args.build)
    report = dataset.load_and_validate(data)
    summary = report.summary()
    _write(build / 'validation_report.json', {**summary, 'rejected': report.rejected, 'duplicates': report.duplicates})
    if not report.accepted:
        raise SystemExit('No valid examples; see validation_report.json')
    splits = dataset.split(report.accepted, seed=args.seed)
    split_stats = dataset.write_split_manifests(splits, build / 'splits')
    leaked = ({e.group_id for e in splits['train']} & {e.group_id for e in splits['test']}) | \
             ({e.group_id for e in splits['train']} & {e.group_id for e in splits['validation']})
    if leaked:
        raise SystemExit(f'Group leakage across splits: {sorted(leaked)[:5]}')
    exported = {name: vertex.export_split(splits[name], data, build, name, args.gcs_prefix)
                for name in ('train', 'validation')}
    result = {'validation': summary, 'splits': split_stats, 'export': exported,
              'gcs_prefix': args.gcs_prefix, 'prepared_at': datetime.now(timezone.utc).isoformat()}
    _write(build / 'prepare.json', result)
    return result


def cmd_upload(args) -> dict:
    import vertex
    return vertex.upload(Path(args.build), args.gcs_prefix)


def cmd_tune(args) -> dict:
    import vertex

    body = vertex.tuning_request(args.base_model, args.gcs_prefix, args.display_name, args.epochs,
                                 args.adapter_size, args.lr_multiplier)
    if not args.submit:
        return {'dry_run': True, 'region': args.region, 'request': body,
                'next': 'Re-run with --submit to create the tuning job (billed to the Cloud project).'}
    job = vertex.submit_tuning(body, args.project, args.region)
    return {'submitted': True, 'job': job.get('name'), 'state': job.get('state')}


def cmd_status(args) -> dict:
    import vertex
    status = vertex.tuning_status(args.job)
    if status.get('endpoint'):
        status['serve_with'] = f"C05_GEMINI_ENDPOINT={status['endpoint']}"
    return status


def cmd_eval(args) -> dict:
    import evaluate

    build = Path(args.build)
    train = dataset.load_split(build / 'splits' / 'train.jsonl')
    test = dataset.load_split(build / 'splits' / 'test.jsonl')
    if args.predictor == 'majority':
        predictions = evaluate.predict_majority(train, test)
    else:
        predictions = asyncio.run(evaluate.predict_gemini(test, Path(args.data), args.concurrency))
    result = {'predictor': args.predictor, **evaluate.report(test, predictions),
              'evaluated_at': datetime.now(timezone.utc).isoformat()}
    _write(build / f'eval_{args.predictor}.json', result)
    return result


def main(argv=None) -> None:
    p = argparse.ArgumentParser(description='C05 tuning pipeline')
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('synth', help='generate a synthetic household-plate dataset')
    s.add_argument('--out', default=str(HERE / 'data' / 'synthetic'))
    s.add_argument('--households', type=int, default=40)
    s.add_argument('--photos', type=int, default=4)
    s.add_argument('--seed', type=int, default=7)
    s.set_defaults(fn=cmd_synth)

    s = sub.add_parser('prepare', help='validate, split by group, export Vertex SFT JSONL')
    s.add_argument('--data', required=True)
    s.add_argument('--build', required=True)
    s.add_argument('--gcs-prefix', default=None)
    s.add_argument('--seed', type=int, default=42)
    s.set_defaults(fn=cmd_prepare)

    s = sub.add_parser('upload', help='copy images and JSONL to Cloud Storage')
    s.add_argument('--build', required=True)
    s.add_argument('--gcs-prefix', required=True)
    s.set_defaults(fn=cmd_upload)

    s = sub.add_parser('tune', help='create a Vertex supervised tuning job (dry run unless --submit)')
    s.add_argument('--gcs-prefix', required=True)
    s.add_argument('--base-model', required=True,
                   help='a Gemini model that Vertex supports for tuning in --region; check before choosing')
    s.add_argument('--display-name', default='c05-meal-qc')
    s.add_argument('--epochs', type=int, default=4)
    s.add_argument('--adapter-size', default='ADAPTER_SIZE_FOUR')
    s.add_argument('--lr-multiplier', type=float, default=None)
    s.add_argument('--region', default='us-central1')
    s.add_argument('--project', default=None)
    s.add_argument('--submit', action='store_true')
    s.set_defaults(fn=cmd_tune)

    s = sub.add_parser('status', help='poll a tuning job')
    s.add_argument('--job', required=True)
    s.set_defaults(fn=cmd_status)

    s = sub.add_parser('eval', help='score the held-out test split')
    s.add_argument('--data', required=True)
    s.add_argument('--build', required=True)
    s.add_argument('--predictor', choices=['majority', 'gemini'], default='majority')
    s.add_argument('--concurrency', type=int, default=4)
    s.set_defaults(fn=cmd_eval)

    args = p.parse_args(argv)
    print(json.dumps(args.fn(args), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
