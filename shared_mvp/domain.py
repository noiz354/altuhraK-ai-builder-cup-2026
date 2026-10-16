from collections import Counter
import re

from shared_mvp.contracts import Invalid


def tokens(text):
    return set(re.findall(r'\w+', text.casefold()))


def ranked(query, docs, text_key='text', id_key='doc_id'):
    words = tokens(query)
    pairs = [(len(words & tokens(d[text_key])), d) for d in docs]
    return [d for score, d in sorted(pairs, key=lambda p: (-p[0], p[1][id_key])) if score][:3]


def eid(pid, collection, record_id):
    return f'{pid}:{collection}:{record_id}'


def result(data, status='ok', authorized=None):
    return {'result': data, 'status': status, 'authorized': authorized}


def require(condition, message):
    if not condition:
        raise Invalid(message)


def evidence_refs(value):
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'evidence_ids':
                if not isinstance(item, list):
                    raise Invalid('evidence_ids must be array')
                found.update(item)
            else:
                found.update(evidence_refs(item))
    elif isinstance(value, list):
        for item in value:
            found.update(evidence_refs(item))
    return found


def evidence(pid, data, allowed=None):
    """Exclude evaluator collections and unapproved/unauthorized documents."""
    output = []
    for collection, rows in data.items():
        if collection in {'labels', 'annotations', 'events'} or not isinstance(rows, list):
            continue
        for idx, original in enumerate(rows):
            row = dict(original)
            row.pop('answer', None)
            row.pop('is_fraud', None)
            row.pop('is_laundering', None)
            row.pop('Is Laundering', None)
            key = next((k for k in row if k.endswith('_id')), None)
            ref = eid(pid, collection, row[key] if key else str(idx))
            if allowed is None or ref in allowed:
                output.append({'evidence_id': ref, 'collection': collection,
                               'record_id': row[key] if key else str(idx),
                               'source_excerpt': row, 'locator': None})
            for page in row.get('pages', []):
                page_ref = f'{ref}:page:{page["page"]}'
                if allowed is None or page_ref in allowed:
                    output.append({'evidence_id': page_ref, 'collection': collection,
                                   'record_id': row[key], 'source_excerpt': {'text': page['text']},
                                   'locator': {'page': page['page'], 'span_start': 0, 'span_end': len(page['text'])}})
    return output
