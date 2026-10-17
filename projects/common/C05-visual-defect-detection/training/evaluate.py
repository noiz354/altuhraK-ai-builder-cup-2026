"""Offline evaluation on the held-out test split.

Metrics are reported overall and per plate type, because the risk with
household plates is a model that does well on trays and quietly fails on
everything else. A missed `missing_component` is the costly error (an
incomplete meal goes out), so its recall is reported on its own line.
"""
from __future__ import annotations

import asyncio
import base64
import json
from collections import Counter, defaultdict
from pathlib import Path

from dataset import LABELS, Example, normalize_image


def metrics(pairs: list[tuple[str, str]]) -> dict:
    """pairs: (truth, prediction). Prediction may be 'error' when the call failed."""
    n = len(pairs)
    confusion = {t: Counter() for t in LABELS}
    for truth, pred in pairs:
        confusion[truth][pred] += 1
    per_label = {}
    for label in LABELS:
        tp = confusion[label][label]
        fn = sum(confusion[label].values()) - tp
        fp = sum(confusion[t][label] for t in LABELS if t != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {'precision': round(precision, 3), 'recall': round(recall, 3), 'f1': round(f1, 3),
                            'support': tp + fn}
    correct = sum(1 for t, p in pairs if t == p)
    return {'n': n, 'accuracy': round(correct / n, 3) if n else 0.0,
            'macro_f1': round(sum(v['f1'] for v in per_label.values()) / len(LABELS), 3),
            'missing_component_recall': per_label['missing_component']['recall'],
            'errors': sum(1 for _, p in pairs if p == 'error'),
            'per_label': per_label,
            'confusion': {t: dict(c) for t, c in confusion.items()}}


def report(examples: list[Example], predictions: list[str]) -> dict:
    overall = metrics([(e.label, p) for e, p in zip(examples, predictions)])
    by_plate: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for e, p in zip(examples, predictions):
        by_plate[e.plate_type].append((e.label, p))
    overall['by_plate_type'] = {k: {'n': len(v), 'accuracy': metrics(v)['accuracy'],
                                    'missing_component_recall': metrics(v)['missing_component_recall']}
                                for k, v in sorted(by_plate.items())}
    return overall


def predict_majority(train: list[Example], test: list[Example]) -> list[str]:
    """Reference floor: any tuned model has to beat 'always the most common label'."""
    top = Counter(e.label for e in train).most_common(1)[0][0]
    return [top for _ in test]


async def _predict_gemini_one(client, ex: Example, dataset_root: Path) -> str:
    import c05_gemini  # noqa: E402  (path set up by vertex import)
    from vertex import OUT_MODEL, image_id_for, live_request

    data, width, height = normalize_image(dataset_root / ex.image)
    prompt, _ = live_request(image_id_for(ex), width, height)
    cfg = c05_gemini.load_config()
    url, headers, _ = c05_gemini.auth_headers(cfg, cfg.model)
    body = {'contents': c05_gemini.vertex_contents([
                {'text': json.dumps(prompt, ensure_ascii=False)},
                {'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(data).decode('ascii')}}]),
            'generationConfig': {'responseMimeType': 'application/json',
                                 'responseSchema': c05_gemini.c05_vertex_schema(OUT_MODEL.model_json_schema()),
                                 'maxOutputTokens': 2048, 'temperature': 0,
                                 'thinkingConfig': c05_gemini.thinking_config_for(cfg.model or '')}}
    try:
        res = await client.post(url, headers=headers, json=body)
        res.raise_for_status()
        parts = res.json()['candidates'][0]['content']['parts']
        label = json.loads(''.join(p.get('text', '') for p in parts)).get('predicted_label')
        return label if label in LABELS else 'error'
    except Exception:
        return 'error'


async def predict_gemini(test: list[Example], dataset_root: Path, concurrency: int = 4) -> list[str]:
    """Live predictions through the same provider switch as the service.

    Point it at a tuned model with C05_GEMINI_ENDPOINT, or at the base model
    with GEMINI_MODEL, and compare the two reports.
    """
    import vertex  # noqa: F401  ensures src/ and repo root are importable
    import httpx

    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient(timeout=150) as client:
        async def one(ex):
            async with sem:
                return await _predict_gemini_one(client, ex, dataset_root)
        return list(await asyncio.gather(*(one(ex) for ex in test)))
