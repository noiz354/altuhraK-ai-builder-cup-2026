"""Dataset contract, validation and leakage-free splitting for C05 tuning.

One dataset is a directory with `manifest.jsonl` and the images it names.
Each manifest line is one labelled photo:

    {"image": "images/0001.jpg",          # path relative to the dataset root
     "label": "missing_component",        # meal_complete | missing_component | uncertain
     "missing": ["vegetable"],            # manifest component keys absent from the plate
     "plate_type": "home_plate",          # see PLATE_TYPES
     "group_id": "household-017",         # photos that must stay in one split
     "source": "field_crew",              # synthetic | field_crew | parent_upload | other
     "uncertain_reason": null,            # one of UNCERTAINTY when label is uncertain
     "boxes": [],                         # optional [{x,y,w,h}] in source pixels
     "captured_at": null, "annotator": null, "notes": null}

`group_id` is the important field once MBG is served on household plates:
several photos of the same family's plates look alike, and letting them
straddle train and test inflates every metric. Splits are made per group.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

LABELS = ('meal_complete', 'missing_component', 'uncertain')
COMPONENTS = ('carbohydrate', 'protein', 'vegetable')
PLATE_TYPES = ('tray_compartment', 'home_plate', 'bowl', 'lunchbox', 'banana_leaf', 'other')
SOURCES = ('synthetic', 'field_crew', 'parent_upload', 'other')
UNCERTAINTY = ('occluded_component', 'poor_lighting', 'label_ambiguous', 'blurred_image',
               'component_out_of_frame', 'manifest_mismatch')
MAX_PIXELS = 4_000_000          # same ceiling the live intake enforces
MIN_SIDE = 224
NEAR_DUP_BITS = 4               # dHash Hamming distance treated as the same photo


@dataclass
class Example:
    image: str
    label: str
    missing: list[str]
    plate_type: str
    group_id: str
    source: str
    uncertain_reason: str | None = None
    boxes: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    # Filled by validation.
    sha256: str = ''
    dhash: str = ''
    width: int = 0
    height: int = 0

    def as_dict(self) -> dict:
        return {'image': self.image, 'label': self.label, 'missing': self.missing,
                'plate_type': self.plate_type, 'group_id': self.group_id, 'source': self.source,
                'uncertain_reason': self.uncertain_reason, 'boxes': self.boxes,
                'sha256': self.sha256, 'width': self.width, 'height': self.height, **self.extra}


def _check_row(row: dict) -> list[str]:
    errors = []
    label = row.get('label')
    missing = row.get('missing') or []
    if label not in LABELS:
        errors.append(f'label must be one of {LABELS}')
    if not isinstance(missing, list) or not set(missing) <= set(COMPONENTS):
        errors.append(f'missing must list keys from {COMPONENTS}')
    elif label == 'missing_component' and not missing:
        errors.append('missing_component needs at least one missing key')
    elif label == 'meal_complete' and missing:
        errors.append('meal_complete cannot list missing components')
    elif len(set(missing)) == len(COMPONENTS):
        errors.append('every component missing is an empty plate; label it uncertain/label_ambiguous')
    if row.get('plate_type') not in PLATE_TYPES:
        errors.append(f'plate_type must be one of {PLATE_TYPES}')
    if row.get('source') not in SOURCES:
        errors.append(f'source must be one of {SOURCES}')
    if not str(row.get('group_id') or '').strip():
        errors.append('group_id is required (household, kitchen-day or capture session)')
    reason = row.get('uncertain_reason')
    if reason is not None and reason not in UNCERTAINTY:
        errors.append(f'uncertain_reason must be one of {UNCERTAINTY}')
    if label == 'uncertain' and reason is None:
        errors.append('uncertain needs an uncertain_reason')
    for box in row.get('boxes') or []:
        if not all(isinstance(box.get(k), int) for k in ('x', 'y', 'w', 'h')) or box['w'] <= 0 or box['h'] <= 0:
            errors.append('boxes need positive integer x, y, w, h')
            break
    return errors


def normalize_image(path: Path) -> tuple[bytes, int, int]:
    """EXIF-upright RGB PNG, downscaled under the live pixel ceiling.

    This mirrors the live intake (`decode_image` in c05_api) so the tuned
    model sees training pixels prepared the same way as production pixels.
    """
    with Image.open(path) as opened:
        opened.load()
        image = ImageOps.exif_transpose(opened).convert('RGB')
    if image.width * image.height > MAX_PIXELS:
        scale = (MAX_PIXELS / (image.width * image.height)) ** 0.5
        image = image.resize((int(image.width * scale), int(image.height * scale)), Image.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue(), image.width, image.height


def dhash(image_bytes: bytes) -> str:
    with Image.open(io.BytesIO(image_bytes)) as img:
        small = img.convert('L').resize((9, 8), Image.LANCZOS)
    px = list(small.tobytes())
    bits = ''.join('1' if px[r * 9 + c] > px[r * 9 + c + 1] else '0' for r in range(8) for c in range(8))
    return f'{int(bits, 2):016x}'


def _hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count('1')


@dataclass
class ValidationReport:
    accepted: list[Example]
    rejected: list[dict]
    duplicates: list[dict]

    def summary(self) -> dict:
        def count(attr):
            return dict(Counter(getattr(e, attr) for e in self.accepted))
        return {
            'accepted': len(self.accepted),
            'rejected': len(self.rejected),
            'duplicates_dropped': len(self.duplicates),
            'groups': len({e.group_id for e in self.accepted}),
            'by_label': count('label'),
            'by_plate_type': count('plate_type'),
            'by_source': count('source'),
            'missing_components': dict(Counter(k for e in self.accepted for k in e.missing)),
            'warnings': self.warnings(),
        }

    def warnings(self) -> list[str]:
        out = []
        labels = Counter(e.label for e in self.accepted)
        total = sum(labels.values()) or 1
        for label in LABELS:
            share = labels.get(label, 0) / total
            if share < 0.1:
                out.append(f'{label} is {share:.0%} of the data; aim for at least 10% per label')
        if len(self.accepted) < 100:
            out.append('Fewer than 100 examples; Vertex supervised tuning recommends 100-500+ for a stable adapter')
        home = sum(1 for e in self.accepted if e.plate_type != 'tray_compartment')
        if home and home < 50:
            out.append(f'Only {home} non-tray photos; household plates vary a lot, collect more before trusting them')
        return out


def load_and_validate(root: Path, near_duplicates: bool = True) -> ValidationReport:
    root = Path(root)
    manifest = root / 'manifest.jsonl'
    if not manifest.is_file():
        raise FileNotFoundError(f'{manifest} not found')
    accepted: list[Example] = []
    rejected: list[dict] = []
    duplicates: list[dict] = []
    seen_sha: dict[str, str] = {}
    for line_no, line in enumerate(manifest.read_text(encoding='utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError:
            rejected.append({'line': line_no, 'errors': ['not valid JSON']})
            continue
        errors = _check_row(row)
        path = (root / str(row.get('image', ''))).resolve()
        if root.resolve() not in path.parents:
            errors.append('image path escapes the dataset root')
        elif not path.is_file():
            errors.append('image file not found')
        if errors:
            rejected.append({'line': line_no, 'image': row.get('image'), 'errors': errors})
            continue
        try:
            data, width, height = normalize_image(path)
        except Exception as exc:
            rejected.append({'line': line_no, 'image': row['image'], 'errors': [f'unreadable image: {type(exc).__name__}']})
            continue
        if min(width, height) < MIN_SIDE:
            rejected.append({'line': line_no, 'image': row['image'], 'errors': [f'shorter side below {MIN_SIDE}px']})
            continue
        if any(b['x'] + b['w'] > width or b['y'] + b['h'] > height for b in row.get('boxes') or []):
            # Boxes are in source pixels; a downscale would need them rescaled first.
            rejected.append({'line': line_no, 'image': row['image'], 'errors': ['box outside normalised image']})
            continue
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen_sha:
            duplicates.append({'line': line_no, 'image': row['image'], 'duplicate_of': seen_sha[sha], 'kind': 'exact'})
            continue
        known = {k: row.pop(k, None) for k in ('image', 'label', 'missing', 'plate_type', 'group_id', 'source',
                                               'uncertain_reason', 'boxes')}
        example = Example(image=known['image'], label=known['label'], missing=sorted(known['missing'] or []),
                          plate_type=known['plate_type'], group_id=str(known['group_id']), source=known['source'],
                          uncertain_reason=known['uncertain_reason'], boxes=known['boxes'] or [],
                          extra={k: v for k, v in row.items() if k in {'captured_at', 'annotator', 'notes', 'kitchen_id'}},
                          sha256=sha, dhash=dhash(data), width=width, height=height)
        seen_sha[sha] = example.image
        accepted.append(example)

    if near_duplicates:
        # A near-duplicate in a different group is the dangerous case: it would
        # survive the group split and leak. Same-group near-duplicates are kept.
        keep: list[Example] = []
        for ex in accepted:
            twin = next((k for k in keep if k.group_id != ex.group_id and _hamming(k.dhash, ex.dhash) <= NEAR_DUP_BITS), None)
            if twin:
                duplicates.append({'image': ex.image, 'duplicate_of': twin.image, 'kind': 'near_cross_group'})
            else:
                keep.append(ex)
        accepted = keep
    return ValidationReport(accepted, rejected, duplicates)


def split(examples: list[Example], ratios=(0.8, 0.1, 0.1), seed: int = 42) -> dict[str, list[Example]]:
    """Group-aware, label-stratified split.

    Groups are bucketed by their majority label, shuffled with a fixed seed,
    then filled into train/validation/test by image count, so each split gets
    a similar label mix and no group appears in two splits.
    """
    if abs(sum(ratios) - 1) > 1e-9:
        raise ValueError('ratios must sum to 1')
    groups: dict[str, list[Example]] = defaultdict(list)
    for ex in examples:
        groups[ex.group_id].append(ex)
    by_label: dict[str, list[str]] = defaultdict(list)
    for gid, members in groups.items():
        majority = Counter(m.label for m in members).most_common(1)[0][0]
        by_label[majority].append(gid)
    rng = random.Random(seed)
    out = {'train': [], 'validation': [], 'test': []}
    names = list(out)
    for label in sorted(by_label):
        gids = sorted(by_label[label])
        rng.shuffle(gids)
        total = sum(len(groups[g]) for g in gids)
        targets = [r * total for r in ratios]
        filled = [0.0, 0.0, 0.0]
        for gid in gids:
            # Put the group where it closes the largest relative shortfall.
            idx = max(range(3), key=lambda i: (targets[i] - filled[i]) / (targets[i] or 1))
            out[names[idx]].extend(groups[gid])
            filled[idx] += len(groups[gid])
    return out


def write_split_manifests(splits: dict[str, list[Example]], out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, rows in splits.items():
        with (out_dir / f'{name}.jsonl').open('w', encoding='utf-8') as fh:
            for ex in rows:
                fh.write(json.dumps(ex.as_dict(), ensure_ascii=False) + '\n')
        stats[name] = {'examples': len(rows), 'groups': len({e.group_id for e in rows}),
                       'by_label': dict(Counter(e.label for e in rows))}
    return stats


def load_split(path: Path) -> list[Example]:
    """Read a split manifest written by write_split_manifests."""
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        rows.append(Example(image=r['image'], label=r['label'], missing=r['missing'], plate_type=r['plate_type'],
                            group_id=r['group_id'], source=r['source'], uncertain_reason=r.get('uncertain_reason'),
                            boxes=r.get('boxes') or [], sha256=r['sha256'], width=r['width'], height=r['height']))
    return rows
