"""Student delivery verification for C05.

After a QC inspection is approved, the meal travels to a student. The student photographs what
they actually received and the server compares it visually against the approved QC image. The
result is a score plus a quality-alert flag that a supervisor must clear.

Design (decided 2026-10-18):
- The endpoint is KITCHEN-SCOPED, not public. The student page reads role+kitchen from the
  session and the backend rejects a verification whose kitchen differs from the inspection.
- The score is a normalised mean absolute error on 64x64 greyscale (0 = identical, 1 = identical).
- Quality alert fires when the visual score drops below 0.85 or when the student image is
  materially darker, brighter, or softer than the approved image.
- Status starts as PENDING_REVIEW; a supervisor approves or rejects it. Nothing is auto-approved.
"""
from __future__ import annotations

import base64
import io
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request
from PIL import Image

from c05_privacy import mask_contact  # noqa: F401  (kept for symmetry with the claims lane)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _quality(image):
    values = list(image.getdata())
    brightness = sum(values) / (len(values) * 255)
    grid = list(image.resize((32, 32)).getdata())
    edge_total = 0
    samples = 0
    for y in range(1, 31):
        for x in range(1, 31):
            idx = y * 32 + x
            edge_total += abs(grid[idx - 1] - grid[idx + 1]) + abs(grid[idx - 32] - grid[idx + 32])
            samples += 1
    sharpness = (edge_total / (samples * 2 * 255)) if samples else 0.0
    if brightness < 0.05 or brightness > 0.99 or sharpness < 0.002:
        status = 'reject'
    elif brightness < 0.18 or brightness > 0.92 or sharpness < 0.01:
        status = 'review'
    else:
        status = 'ok'
    return {'brightness': round(brightness, 4), 'sharpness': round(sharpness, 4), 'status': status}


def _decode(payload):
    import base64 as _b64
    from shared_mvp.contracts import Invalid
    data = payload.get('data_base64')
    if not isinstance(data, str) or not data:
        raise HTTPException(422, 'data_base64 is required')
    try:
        raw = _b64.b64decode(data, validate=True)
    except Exception:
        raise HTTPException(422, 'data_base64 is not valid base64') from None
    if len(raw) > 4 * 1024 * 1024:
        raise HTTPException(422, 'Image exceeds 4 MiB limit')
    try:
        with Image.open(io.BytesIO(raw)) as opened:
            opened.load()
            image = opened.convert('RGB')
    except Exception:
        raise HTTPException(422, 'Corrupt or unsupported image') from None
    if image.width < 320 or image.height < 240:
        raise HTTPException(422, 'Image must be at least 320x240')
    mime = payload.get('mime_type', 'image/png')
    if mime not in ('image/jpeg', 'image/png'):
        raise HTTPException(422, 'Only JPEG or PNG is accepted')
    return raw, image, image.width, image.height


def register(app, store, roles, scope_fn, actor_fn, body):
    def _require(role):
        if role not in roles:
            raise HTTPException(422, 'Unknown role')

    @app.post('/api/delivery-verifications', status_code=201)
    async def create_delivery_verification(request: Request):
        payload = await body(request)
        role = payload.get('role')
        _require(role)
        inspection_id = payload.get('inspection_id')
        record = store.get('inspection', inspection_id)
        if not record:
            # Accept the short IDs shown in the admin queue.
            matches = [r['inspection_id'] for r in store.list_kind('inspection')
                       if r['inspection_id'].startswith(str(inspection_id or ''))
                       and r['kitchen_id'] in scope_fn(role)]
            if len(matches) == 1:
                inspection_id = matches[0]
                record = store.get('inspection', inspection_id)
        if not record:
            raise HTTPException(404, 'Unknown inspection')
        if record['kitchen_id'] not in scope_fn(role):
            raise HTTPException(403, 'Inspection is outside your kitchen scope')
        if record.get('review_status') != 'APPROVED':
            raise HTTPException(409, 'Inspection must be approved before delivery verification')
        requested_kitchen = payload.get('kitchen_id')
        if requested_kitchen and requested_kitchen != record['kitchen_id']:
            raise HTTPException(403, 'Delivery verification is scoped to the inspection kitchen')

        raw, student_image, width, height = _decode(payload)

        from shared_mvp.assets import resolve as _resolve_asset
        storage_path = record.get('storage_path') or f"{record['image_id']}.png"
        try:
            qc_path = _resolve_asset('C05', storage_path)
        except Exception:
            raise HTTPException(404, 'QC image is no longer available for this inspection') from None
        with Image.open(qc_path) as qc_opened:
            qc_image = qc_opened.convert('L').resize((64, 64))
        student_grey = student_image.convert('L').resize((64, 64))
        diff = sum(abs(a - b) for a, b in zip(qc_image.getdata(), student_grey.getdata()))
        score = round(1.0 - (diff / (255 * 64 * 64)), 4)

        qc_quality = _quality(qc_image)
        student_quality = _quality(student_grey)
        alert_reasons = []
        if score < 0.85:
            alert_reasons.append('visual_difference_high')
        if student_quality['status'] != 'ok':
            alert_reasons.append(f'student_image_{student_quality["status"]}')
        if qc_quality['status'] == 'ok' and student_quality['brightness'] < qc_quality['brightness'] - 0.15:
            alert_reasons.append('brightness_decreased')
        if qc_quality['status'] == 'ok' and student_quality['sharpness'] < qc_quality['sharpness'] * 0.5:
            alert_reasons.append('sharpness_decreased')
        quality_alert = bool(alert_reasons)

        image_id = uuid.uuid4().hex
        from shared_mvp.assets import root as _asset_root
        import pathlib
        asset_dir = _asset_root('C05')
        (asset_dir / f'{image_id}.png').write_bytes(raw)

        verification_id = uuid.uuid4().hex
        verification = {
            'verification_id': verification_id,
            'inspection_id': inspection_id,
            'role': role,
            'actor_id': actor_fn(role),
            'kitchen_id': record['kitchen_id'],
            'image_id': image_id,
            'storage_path': f'{image_id}.png',
            'image_width': width,
            'image_height': height,
            'visual_score': score,
            'qc_quality': qc_quality,
            'student_quality': student_quality,
            'quality_alert': quality_alert,
            'quality_alert_reasons': alert_reasons,
            'status': 'PENDING_REVIEW',
            'created_at': now_iso(),
        }
        store.put('delivery_verification', verification_id, verification)
        store.append(verification_id, 'delivery_submitted', {
            'actor': actor_fn(role), 'score': score, 'alert': quality_alert,
        })
        return verification

    @app.get('/api/delivery-verifications')
    async def list_delivery_verifications(request: Request):
        role = request.query_params.get('role', 'ADMIN')
        _require(role)
        kitchen_id = request.query_params.get('kitchen_id')
        allowed = scope_fn(role)
        if kitchen_id:
            if kitchen_id not in allowed:
                raise HTTPException(403, 'Kitchen is outside your assignment')
            allowed = {kitchen_id}
        rows = [v for v in store.list_kind('delivery_verification')
                if v['kitchen_id'] in allowed]
        rows.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        return {'verifications': rows, 'count': len(rows)}

    @app.post('/api/delivery-verifications/{verification_id}/review')
    async def review_delivery_verification(verification_id: str, request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in roles or not roles[role]['approve']:
            raise HTTPException(403, 'Role cannot approve delivery verification')
        record = store.get('delivery_verification', verification_id)
        if not record or record['kitchen_id'] not in scope_fn(role):
            raise HTTPException(404, 'Unknown delivery verification')
        decision = payload.get('decision')
        if decision not in {'APPROVE', 'REJECT'}:
            raise HTTPException(422, 'decision must be APPROVE or REJECT')
        record['status'] = 'APPROVED' if decision == 'APPROVE' else 'REJECTED'
        record['reviewed_by'] = actor_fn(role)
        record['reviewed_at'] = now_iso()
        record['comment'] = payload.get('comment')
        store.put('delivery_verification', verification_id, record)
        store.append(verification_id, 'delivery_reviewed',
                     {'actor': actor_fn(role), 'decision': decision})
        return record

    return None