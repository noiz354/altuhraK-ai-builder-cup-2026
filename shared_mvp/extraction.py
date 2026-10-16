"""Structured-text comparator for decision/action extraction; no model involved."""
from shared_mvp.contracts import iso_date, Invalid


def extract_line(line, prefix, owners):
    if not line.startswith(prefix + '|'):
        return None
    parts = line.split('|')
    if len(parts) != 4 or not parts[1].strip():
        return None
    _, text, owner, due = parts
    owner = owner if owner in owners else None
    try:
        due = iso_date(due).isoformat()
    except Invalid:
        due = None
    return {'text': text.strip(), 'owner_id': owner, 'due_date': due,
            'needs_review': owner is None or due is None}
