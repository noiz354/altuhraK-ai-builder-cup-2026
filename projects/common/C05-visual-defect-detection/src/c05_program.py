"""Menu specifications, blind labelling, and dataset metrics for C05.

Ported from the donor and kept deliberately narrow. Per decision D4 the deck claim was downgraded
from "Vertex AI supervised tuning pipeline" to "dataset and label surface": there is no tuning job
in this codebase and none is implied. What lives here is the *data* that such a pipeline would
consume - versioned menu specs, blind annotations, adjudicated gold labels, and honest counts.

Three properties are load-bearing and each has a test:

1. **Blind labelling.** `annotation_queue` returns image metadata and nothing from the model
   output. An annotator who can see the prediction will anchor on it, which silently corrupts
   every metric computed from these labels.
2. **Separation of duties.** The capturing actor may not annotate their own image, and one
   annotator may not label the same inspection twice.
3. **Immutable gold.** Adjudicated labels can never be overwritten, matching the immutability rule
   that already governs inspection review decisions.

Metrics never coerce an unavailable figure to zero. A null with a reason is honest; a zero reads
as "measured, and it was nothing", which is a different and false claim.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request

# Meal-tray label vocabulary. Kept aligned with the prediction vocabulary on purpose: an
# annotator should not have to translate between two label sets.
LABELS = ('meal_complete', 'missing_component', 'uncertain')
UNCERTAINTY = ('occluded_component', 'poor_lighting', 'label_ambiguous', 'blurred_image',
               'component_out_of_frame', 'manifest_mismatch')
MENU_ID_PATTERN = re.compile(r'[A-Za-z0-9_-]{1,64}')


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _fraction(part, whole):
    return {'count': part, 'of': whole, 'rate': round(part / whole, 4) if whole else None}


def register(app, store, roles, scope_fn, actor_fn, body):
    def _require_role(role):
        if role not in roles:
            raise HTTPException(422, 'Unknown role')

    # ------------------------------------------------------------ menu specs

    @app.post('/api/menus', status_code=201)
    async def create_menu(request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role != 'ADMIN':
            raise HTTPException(403, 'Only ADMIN registers menu specifications')
        menu_id = payload.get('menu_id')
        if not isinstance(menu_id, str) or not MENU_ID_PATTERN.fullmatch(menu_id):
            raise HTTPException(422, 'menu_id must be 1-64 chars of letters, digits, _ or -')
        required = payload.get('required_components')
        if not isinstance(required, list) or not required or not all(
                isinstance(c, str) and c for c in required):
            raise HTTPException(422, 'required_components must be a non-empty string list')
        optional = payload.get('optional_components') or []
        if not isinstance(optional, list) or not all(isinstance(c, str) for c in optional):
            raise HTTPException(422, 'optional_components must be a string list')
        kitchen = payload.get('kitchen_id')
        if kitchen not in scope_fn('ADMIN'):
            raise HTTPException(403, 'Kitchen is outside assignment')

        existing = [m for m in store.list_kind('menu_spec') if m['menu_id'] == menu_id]
        version = max([m['version'] for m in existing], default=0) + 1
        spec = {
            'menu_id': menu_id, 'version': version,
            'menu_name': str(payload.get('menu_name') or menu_id)[:120],
            'kitchen_id': kitchen,
            'required_components': required,
            'optional_components': optional,
            'unverifiable_requirements': payload.get('unverifiable_requirements') or [],
            'effective_date': payload.get('effective_date'),
            'owner': str(payload.get('owner') or actor_fn(role))[:120],
            'status': 'draft',
            'created_at': now_iso(), 'approved_at': None, 'approved_by': None,
            'revision_history': [{'version': version, 'action': 'created',
                                  'actor': actor_fn(role), 'at': now_iso()}],
        }
        store.put('menu_spec', f'{menu_id}:v{version}', spec)
        store.append(f'menu:{menu_id}:v{version}', 'menu_created',
                     {'actor': actor_fn(role), 'kitchen': kitchen})
        return spec

    @app.post('/api/menus/{menu_id}/v/{version}/approve')
    async def approve_menu(menu_id: str, version: int, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role != 'ADMIN':
            raise HTTPException(403, 'Only ADMIN approves menu specifications')
        spec = store.get('menu_spec', f'{menu_id}:v{version}')
        if not spec:
            raise HTTPException(404, 'Unknown menu specification')
        if spec.get('status') == 'approved':
            raise HTTPException(409, 'Approved specifications are immutable')
        approved = {
            **spec, 'status': 'approved', 'approved_at': now_iso(),
            'approved_by': actor_fn(role),
            'revision_history': list(spec.get('revision_history', [])) + [
                {'version': version, 'action': 'approved', 'actor': actor_fn(role), 'at': now_iso()},
            ],
        }
        store.put('menu_spec', f'{menu_id}:v{version}', approved)
        store.append(f'menu:{menu_id}:v{version}', 'menu_approved',
                     {'actor': approved['approved_by']})
        return approved

    @app.get('/api/menus')
    async def list_menus(role: str = 'ADMIN'):
        _require_role(role)
        rows = [m for m in store.list_kind('menu_spec') if m['kitchen_id'] in scope_fn(role)]
        return {'menus': sorted(rows, key=lambda m: (m['menu_id'], m['version'])),
                'count': len(rows)}

    @app.get('/api/menus/{menu_id}/v/{version}')
    async def get_menu(menu_id: str, version: int, role: str = 'ADMIN'):
        _require_role(role)
        spec = store.get('menu_spec', f'{menu_id}:v{version}')
        if not spec or spec['kitchen_id'] not in scope_fn(role):
            raise HTTPException(404, 'Unknown menu specification')
        return spec

    # --------------------------------------------------------- blind labelling

    @app.get('/api/annotations/queue')
    async def annotation_queue(role: str = 'SUPERVISOR', kitchen_id: str | None = None):
        """Work queue for annotators, stripped of anything the model produced.

        Labelling blind is what makes an accuracy figure meaningful. If the annotator can see
        the prediction, agreement stops measuring the image and starts measuring the model.
        """
        if role not in ('SUPERVISOR', 'ADMIN'):
            raise HTTPException(403, 'Annotation requires SUPERVISOR or ADMIN')
        annotated = {a['inspection_id'] for a in store.list_kind('annotation')}
        out = []
        for row in store.list_kind('inspection'):
            if row['kitchen_id'] not in scope_fn(role):
                continue
            if kitchen_id and row['kitchen_id'] != kitchen_id:
                continue
            if row['inspection_id'] in annotated:
                continue
            out.append({
                'inspection_id': row['inspection_id'], 'revision': row.get('revision'),
                'kitchen_id': row['kitchen_id'], 'image_id': row.get('image_id'),
                'image_sha256': row.get('image_sha256'),
                'image_width': row.get('image_width'), 'image_height': row.get('image_height'),
                'menu_required_components': row.get('menu_required_components') or [],
                'manifest_id': row.get('manifest_id'), 'manifest_version': row.get('manifest_version'),
                'created_at': row.get('created_at'), 'annotation_count': 0,
            })
        return {'queue': sorted(out, key=lambda r: r.get('created_at') or ''), 'count': len(out)}

    @app.post('/api/inspections/{inspection_id}/annotations', status_code=201)
    async def submit_annotation(inspection_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in ('SUPERVISOR', 'ADMIN'):
            raise HTTPException(403, 'Annotation requires SUPERVISOR or ADMIN')
        record = store.get('inspection', inspection_id)
        if not record or record['kitchen_id'] not in scope_fn(role):
            raise HTTPException(404, 'Unknown inspection')
        if store.get('gold', inspection_id):
            raise HTTPException(409, 'Adjudicated gold labels are immutable')

        annotator = payload.get('annotator_id')
        if not isinstance(annotator, str) or not annotator.strip():
            raise HTTPException(422, 'annotator_id is required')
        annotator = annotator.strip()[:120]
        if annotator == record.get('actor_id'):
            raise HTTPException(422, 'The capturing actor may not annotate their own image')

        label = payload.get('image_level_label')
        if label not in LABELS:
            raise HTTPException(422, f'image_level_label must be one of {sorted(LABELS)}')
        missing = payload.get('missing_components') or []
        menu = record.get('menu_required_components') or []
        if not isinstance(missing, list) or not all(isinstance(c, str) for c in missing):
            raise HTTPException(422, 'missing_components must be a string list')
        if menu and any(c not in menu for c in missing):
            raise HTTPException(422, 'missing_components must reference the inspection menu')
        if label == 'missing_component' and not missing:
            raise HTTPException(422, 'missing_component requires at least one missing component')
        if label == 'uncertain' and payload.get('uncertainty_reason') not in UNCERTAINTY:
            raise HTTPException(422, f'uncertainty_reason must be one of {sorted(UNCERTAINTY)}')

        prior = [a for a in store.list_kind('annotation') if a['inspection_id'] == inspection_id]
        if any(a['annotator_id'] == annotator for a in prior):
            raise HTTPException(409, 'This annotator already labeled this inspection')

        annotation = {
            'inspection_id': inspection_id, 'annotator_id': annotator,
            'annotator_role': role, 'image_level_label': label,
            'missing_components': sorted(set(missing)),
            'uncertainty_reason': payload.get('uncertainty_reason'),
            'component_visibility_state': payload.get('component_visibility_state') or {},
            'annotated_at': now_iso(), 'blind_index': len(prior),
        }
        store.put('annotation', f'{inspection_id}:{annotator}', annotation)
        store.append(inspection_id, 'annotated',
                     {'annotator': annotator, 'label': label, 'blind_index': len(prior)})
        return {**annotation, 'annotations_on_record': len(prior) + 1}

    @app.post('/api/inspections/{inspection_id}/adjudicate', status_code=201)
    async def adjudicate(inspection_id: str, request: Request):
        payload = await body(request)
        if payload.get('role') != 'ADMIN':
            raise HTTPException(403, 'Adjudication requires ADMIN')
        record = store.get('inspection', inspection_id)
        if not record or record['kitchen_id'] not in scope_fn('ADMIN'):
            raise HTTPException(404, 'Unknown inspection')
        if store.get('gold', inspection_id):
            raise HTTPException(409, 'Adjudicated gold labels are immutable')
        annotations = [a for a in store.list_kind('annotation')
                       if a['inspection_id'] == inspection_id]
        if len(annotations) < 2:
            raise HTTPException(409, 'Adjudication needs at least two independent labels')

        labels = sorted({a['image_level_label'] for a in annotations})
        adjudicator = str(payload.get('adjudicator_id') or actor_fn('ADMIN'))[:120]
        gold = {
            'inspection_id': inspection_id, 'image_level_label': labels[0] if len(labels) == 1 else 'uncertain',
            'was_contested': len(labels) > 1, 'candidate_labels': labels,
            'missing_components': sorted({c for a in annotations for c in a.get('missing_components', [])}),
            'adjudicated_by': adjudicator, 'adjudicated_at': now_iso(),
            'source_annotations': [a['annotator_id'] for a in annotations],
            'note': str(payload.get('note') or '').strip() or None,
        }
        store.put('gold', inspection_id, gold)
        store.append(inspection_id, 'adjudicated',
                     {'adjudicator': adjudicator, 'label': gold['image_level_label'],
                      'contested': gold['was_contested']})
        return gold

    # ------------------------------------------------------- dataset metrics

    @app.get('/api/data/overview')
    async def data_overview(role: str = 'ADMIN'):
        """Dataset metrics for the label surface.

        Every figure carries numerator, denominator and source. A metric that cannot be computed
        is returned as null with a reason; it is never coerced to 0, because 0 reads as a
        measurement.
        """
        if role != 'ADMIN':
            raise HTTPException(403, 'Dataset metrics require ADMIN')
        inspections = store.list_kind('inspection')
        annotations = store.list_kind('annotation')
        golds = store.list_kind('gold')

        by_inspection: dict[str, list] = {}
        for annotation in annotations:
            by_inspection.setdefault(annotation['inspection_id'], []).append(annotation)
        multi = {k: v for k, v in by_inspection.items() if len(v) >= 2}
        agreed = sum(1 for v in multi.values()
                     if len({a['image_level_label'] for a in v}) == 1)

        sha_groups: dict[str, list] = {}
        for row in inspections:
            sha_groups.setdefault(row.get('image_sha256', '?'), []).append(row['inspection_id'])
        duplicates = {sha: ids for sha, ids in sha_groups.items() if len(ids) > 1}

        gold_labels = [g['image_level_label'] for g in golds]

        return {
            'dataset': {
                'inspections': len(inspections),
                'annotations': len(annotations),
                'adjudicated_gold_labels': len(golds),
                'distinct_image_hashes': len(sha_groups),
                'exact_duplicate_hashes': len(duplicates),
                'exact_duplicate_inspection_ids': sorted(
                    i for ids in duplicates.values() for i in ids),
                'source': 'store.list_kind over inspection, annotation and gold',
            },
            'annotation_coverage': _fraction(len(by_inspection), len(inspections)),
            'inter_annotator': {
                'records_with_two_or_more_labels': len(multi),
                'full_agreement': _fraction(agreed, len(multi)),
                'note': 'Agreement is between independent annotators, not against the model.',
            },
            'gold_label_distribution': {
                label: _fraction(gold_labels.count(label), len(golds)) for label in sorted(LABELS)
            },
            'tuning_readiness': {
                'ready': len(golds) >= 50 and not duplicates,
                'blocked_by': [
                    *([] if len(golds) >= 50 else [f'only {len(golds)} gold labels, want 50+']),
                    *(['exact duplicate images must be removed'] if duplicates else []),
                ],
                'note': ('Measures dataset readiness only. No Vertex AI tuning job is implemented; '
                         'see CLAIMS-REGISTER row 12.'),
            },
        }

    return app