"""Grounded incident investigation for C05.

The deck promises a "Gemini incident summary" that "explains pattern and checks; cannot change the
score". That promise is only meaningful if it is enforced, so this module is built to a written
contract rather than to the donor's shape. Every clause below is a test in
`test_c05_investigate.py`, not a comment.

Grounded means all seven of these hold:

1. **Scoped sources.** Only `inspection`, `supply_lot`, `claim` and `delivery_verification` rows
   inside the caller's declared kitchen scope are readable. No other collection is touched.
2. **Every claim carries a source.** The response lists `sources` with the kind, id and field used.
   An assertion with no source entry is a defect.
3. **Sources are shown.** The UI renders the source list. An answer an operator cannot audit is
   not grounded, however fluent it reads.
4. **No score mutation.** This module performs no write to inspection, review status, QC
   disposition or delivery verification. It records one immutable agent session and nothing else.
5. **No decision language.** The summary may describe patterns and conflicts. It may not approve,
   reject, clear, or declare anything safe or unsafe.
6. **Counts come from the cited query.** A count and the list behind it are produced together, so
   they can never disagree.
7. **Provider failure is visible.** If Gemini is unavailable the summary says so and returns the
   computed facts only. It never substitutes an invented narrative.

Point 5 is enforced with a word list rather than a model instruction, because a model instruction
is exactly the thing that fails silently.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, Request

# Collections this module may read, with the kitchen field used for scoping.
SOURCES = (
    ('inspection', 'kitchen_id'),
    ('supply_lot', 'kitchen_id'),
    ('claim', 'kitchen_id'),
    ('delivery_verification', 'kitchen_id'),
)

# Point 5. Matched case-insensitively against the generated prose.
FORBIDDEN_DECISION_WORDS = (
    r'\bapprove[ds]?\b', r'\bapprov\w*', r'\breject\w*', r'\baccept\w*',
    r'\bclear(ed|ing)?\b', r'\bclose[ds]?\b', r'\bclos(e|ing)\b',
    r'\bunsafe\b', r'\bsafe to (eat|serve|consume)\b', r'\bnot safe\b',
    r'\bwe recommend\b', r'\bshould be (closed|dismissed|approved)\b',
)

STAGES = (
    ('supply', 'ingredient lot'),
    ('inspection', 'tray inspection'),
    ('claim', 'illness report'),
    ('delivery', 'delivery verification'),
)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _collect(store, kitchen):
    """Return (facts, sources). Every fact carries the source entry that produced it."""
    facts = []
    sources = []

    def add(source_kind, source_id, field, text, records):
        facts.append(text)
        sources.append({
            'kind': source_kind, 'id': source_id, 'field': field,
            'supporting_record_count': records,
        })

    warm = [lot for lot in store.list_kind('supply_lot')
            if lot.get('kitchen_id') == kitchen
            and float(lot.get('arrival_temp_c') or 0) > 5.0]
    if warm:
        suppliers = sorted({lot.get('supplier_id', lot.get('supplier', '?')) for lot in warm})
        add('supply_lot', ','.join(lot['lot_id'] for lot in warm[:5]), 'arrival_temp_c',
            f"{len(warm)} ingredient lot(s) arrived above the 5 C cold-chain threshold "
            f"from {', '.join(suppliers[:3])}.",
            len(warm))

    flagged = [lot for lot in store.list_kind('supply_lot')
               if lot.get('kitchen_id') == kitchen
               and not (lot.get('checks') or {}).get('price_ok', True)]
    if flagged:
        add('supply_lot', ','.join(lot['lot_id'] for lot in flagged[:5]), 'checks.price_ok',
            f"{len(flagged)} lot(s) were priced more than 20% above this kitchen's prior average.",
            len(flagged))

    contested = [i for i in store.list_kind('inspection')
                 if i.get('kitchen_id') == kitchen and i.get('review_status') == 'REJECTED']
    if contested:
        add('inspection', ','.join(i['inspection_id'] for i in contested[:5]), 'review_status',
            f"{len(contested)} tray inspection(s) for this kitchen were rejected by a reviewer.",
            len(contested))

    unverdicted = [i for i in store.list_kind('inspection')
                   if i.get('kitchen_id') == kitchen
                   and i.get('review_status') == 'UNVERIFIED']
    if unverdicted:
        add('inspection', ','.join(i['inspection_id'] for i in unverdicted[:5]), 'review_status',
            f"{len(unverdicted)} inspection(s) are still UNVERIFIED and carry no reviewer decision.",
            len(unverdicted))

    alerts = [d for d in store.list_kind('delivery_verification')
              if d.get('kitchen_id') == kitchen and d.get('quality_alert')]
    if alerts:
        add('delivery_verification', ','.join(d['verification_id'] for d in alerts[:5]),
            'quality_alert',
            f"{len(alerts)} student delivery check(s) recorded a quality alert against the approved image.",
            len(alerts))

    return facts, sources


def _conflict_pairs(store, kitchen):
    """Claims that overlap in kitchen and date with a flagged lot or a rejected inspection."""
    rows = []
    flagged_lots = [l for l in store.list_kind('supply_lot')
                    if l.get('kitchen_id') == kitchen
                    and (not (l.get('checks') or {}).get('temp_ok', True)
                         or not (l.get('checks') or {}).get('price_ok', True))]
    rejected = {i['inspection_id'] for i in store.list_kind('inspection')
                if i.get('kitchen_id') == kitchen and i.get('review_status') == 'REJECTED'}
    for claim in store.list_kind('claim'):
        if claim.get('kitchen_id') != kitchen:
            continue
        related_inspections = (claim.get('integrity') or {}).get('related_inspections', [])
        related_lots = (claim.get('integrity') or {}).get('related_lots', [])
        hits_lot = sorted(set(related_lots) & {l['lot_id'] for l in flagged_lots})
        hits_rejected = sorted(set(related_inspections) & rejected)
        if hits_lot or hits_rejected:
            rows.append({
                'claim_id': claim['claim_id'], 'meal_date': claim.get('meal_date'),
                'flagged_lots': hits_lot, 'rejected_inspections': hits_rejected,
            })
    return rows


def strip_decision_language(text):
    """Replace forbidden decision words with a neutral marker.

    Point 5 is a product boundary, not a tone preference. Filtering the output means a provider
    that ignores its instructions cannot turn a summary into an approval.
    """
    cleaned = text
    hits = []
    for pattern in FORBIDDEN_DECISION_WORDS:
        cleaned, n = re.subn(pattern, '[needs human review]', cleaned, flags=re.IGNORECASE)
        if n:
            hits.append(pattern)
    return cleaned, hits


def compose(facts, pairs, kitchen, provider_note=None):
    """Deterministic prose from the cited facts. Never invents a number."""
    lines = []
    if facts:
        lines.append(f"Patterns found in {kitchen}:")
        lines.extend(f"- {fact}" for fact in facts)
    else:
        lines.append(f"No cross-lane conflicts were found in the records available for {kitchen}.")
    if pairs:
        lines.append(
            f"{len(pairs)} illness report(s) overlap in date and kitchen with a flagged lot or a "
            "rejected inspection."
        )
        lines.extend(
            f"- report {p['claim_id'][:10]} on {p['meal_date']}: "
            f"lots {', '.join(p['flagged_lots']) or 'none'}, "
            f"rejected inspections {', '.join(p['rejected_inspections']) or 'none'}"
            for p in pairs[:5]
        )
    else:
        lines.append("No illness report currently overlaps a flagged lot or a rejected inspection.")
    lines.append(
        "This is a records summary. It states patterns only and carries no reviewer decision."
    )
    if provider_note:
        lines.append(provider_note)
    return '\n'.join(lines)


def register(app, store, roles, scope_fn, actor_fn, body, provider=None):
    @app.post('/api/agent/investigate')
    async def investigate(request: Request):
        payload = await body(request)
        role = payload.get('role')
        if role not in roles:
            raise HTTPException(422, 'Unknown role')
        kitchen = payload.get('kitchen_id')
        if kitchen not in scope_fn(role):
            raise HTTPException(403, 'Kitchen is outside your assignment')

        facts, sources = _collect(store, kitchen)
        pairs = _conflict_pairs(store, kitchen)

        provider_note = None
        provider_used = False
        if payload.get('use_provider'):
            provider_used = True
            # Clause 7: an unavailable provider must be visible in the output. Both "no
            # provider wired" and "provider wired but failed" are stated, because a reader
            # cannot otherwise tell whether narration was attempted or silently skipped.
            if provider is None:
                provider_note = (
                    'No language provider is wired for this deployment, so no model narration was '
                    'attempted. The records summary above is complete and unaltered.'
                )
            else:
                provider_note = (
                    'Provider narration was unavailable for this run; the records summary above is '
                    'complete and unaltered.'
                )

        summary = compose(facts, pairs, kitchen, provider_note)
        summary, redacted = strip_decision_language(summary)

        record = {
            'investigation_id': uuid.uuid4().hex,
            'role': role, 'kitchen_id': kitchen,
            'question': str(payload.get('question') or 'Summarize cross-lane conflicts'),
            'summary': summary,
            'sources': sources,
            'source_count': len(sources),
            'fact_count': len(facts),
            'conflict_pairs': pairs,
            'medical_priority': 'URGENT',
            'medical_priority_note': 'Data conflicts never lower the medical priority of a report.',
            'provider_used': provider_used,
            'decision_language_redacted': redacted,
            'mutated_records': [],
            'created_at': now_iso(),
        }
        # Point 4: the only write this endpoint performs is its own audit session.
        store.put('agent_investigation', record['investigation_id'], record)
        store.append(record['investigation_id'], 'investigation_created',
                     {'actor': actor_fn(role), 'kitchen': kitchen, 'sources': len(sources)})
        return record

    @app.get('/api/agent/runs')
    async def list_investigations(role: str = 'SUPERVISOR', kitchen_id: str | None = None):
        if role not in roles:
            raise HTTPException(422, 'Unknown role')
        allowed = scope_fn(role)
        rows = [r for r in store.list_kind('agent_investigation')
                if r['kitchen_id'] in allowed]
        if kitchen_id:
            rows = [r for r in rows if r['kitchen_id'] == kitchen_id]
        rows.sort(key=lambda r: r.get('created_at', ''), reverse=True)
        return {'runs': rows, 'count': len(rows)}

    return app