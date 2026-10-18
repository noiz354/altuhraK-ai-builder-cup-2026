"""Contact privacy helpers for C05 public intake.

Design decision (2026-10-18): reporter contacts are NEVER stored in cleartext.
A plain hash of a phone number is trivially brute-forced because the input space
is small, so we use HMAC-SHA256 with a server-held secret. The HMAC output is a
*blind index*: it still supports exact-match duplicate detection, but it cannot
be reversed without the secret.

Retention policy:
  - Raw contact is never persisted. Only the blind index and a masked hint.
  - `RETENTION_DAYS` bounds how long a claim may hold PII-linked data before a
    purge is required. Purging drops the blind index and the masked hint.
  - Resolution does NOT auto-purge, because an open health escalation still needs
    the duplicate-detection signal. Call `purge_claim` explicitly once the
    escalation is closed and the retention window has passed.

The secret is read from `C05_CONTACT_HMAC_SECRET`. If it is unset the helper
raises, so a deployment cannot silently fall back to cleartext.
"""
from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

SECRET_ENV = 'C05_CONTACT_HMAC_SECRET'

# Public-facing claims stay reviewable for 90 days, then the blind index is dropped.
RETENTION_DAYS = 90


class ContactPrivacyNotConfigured(RuntimeError):
    """Raised when the HMAC secret is missing. Never fall back to cleartext."""


def _secret() -> bytes:
    raw = os.environ.get(SECRET_ENV, '').strip()
    if not raw:
        raise ContactPrivacyNotConfigured(
            f'{SECRET_ENV} is not set; refusing to store reporter contact without an HMAC key'
        )
    return raw.encode('utf-8')


def normalize(contact: str) -> str:
    """Canonical form for matching: casefolded and whitespace-collapsed.

    This is intentionally lossy about formatting but preserves every digit and
    letter, so `+62 812-3456` and `628123456` are not treated as the same value
    unless the caller strips separators first with `canonical_digits`.
    """
    return ' '.join(str(contact).strip().casefold().split())


def canonical_digits(contact: str) -> str:
    """Digits-only form for phone matching, with a leading-plus convention.

    `canonical_digits('+62 812-3456')` -> '628123456'
    Use this before `blind_index` so formatting variants collide as one person.
    """
    text = str(contact).strip()
    plus = text.lstrip().startswith('+')
    digits = ''.join(ch for ch in text if ch.isdigit())
    return f'+{digits}' if plus and digits else digits


def blind_index(contact: str, *, canonical: bool = True) -> str:
    """Deterministic HMAC-SHA256 index. Equal inputs give equal indexes."""
    value = canonical_digits(contact) if canonical else normalize(contact)
    if not value:
        raise ValueError('contact must not be empty')
    return hmac.new(_secret(), value.encode('utf-8'), hashlib.sha256).hexdigest()


def digits_only(contact: str) -> str:
    """Digits with no country-code prefix marker, used for masking and length checks."""
    return ''.join(ch for ch in str(contact) if ch.isdigit())


def mask_contact(contact: str) -> str:
    """Human-safe hint for support, e.g. `*********7890`. Never the full value.

    Length is computed from digits only. `canonical_digits` may carry a leading `+`, and using
    its length here would mis-size the mask and leak that a prefix marker was present.

    A value of four or fewer digits is masked completely: revealing all of it would be
    equivalent to returning the raw contact.
    """
    digits = digits_only(contact)
    if not digits:
        return '****'
    if len(digits) <= 4:
        return '*' * len(digits)
    return '*' * (len(digits) - 4) + digits[-4:]


def contact_record(contact: str) -> dict:
    """The only shape permitted to be persisted for a reporter contact."""
    return {
        'contact_blind_index': blind_index(contact),
        'contact_masked': mask_contact(contact),
    }


def purge_claim(claim: dict) -> dict:
    """Strip PII-linked fields from a claim. Returns a new dict; input unchanged."""
    purged = dict(claim)
    purged.pop('contact_blind_index', None)
    purged.pop('contact_masked', None)
    purged.pop('reporter_contact', None)
    purged.pop('reporter_contact_normalized', None)
    purged['contact_purged'] = True
    purged['contact_purged_at'] = datetime.now(timezone.utc).isoformat()
    return purged


def retention_deadline(created_at: str | None) -> str | None:
    """ISO timestamp after which `purge_claim` must be called."""
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(str(created_at).replace('Z', '+00:00'))
    except ValueError:
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (created + timedelta(days=RETENTION_DAYS)).isoformat()


def is_retention_due(claim: dict, *, now: datetime | None = None) -> bool:
    """True when the claim is past its retention window and still holds PII."""
    if claim.get('contact_purged'):
        return False
    deadline = retention_deadline(claim.get('created_at'))
    if deadline is None:
        return False
    reference = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)
    return reference >= datetime.fromisoformat(deadline)


def public_view(claim: dict) -> dict:
    """Fields safe to return on a public report. Strips everything PII-adjacent."""
    return {
        'claim_id': claim.get('claim_id'),
        'meal_date': claim.get('meal_date'),
        'symptoms': claim.get('symptoms'),
        'status': claim.get('status'),
        'contact_masked': claim.get('contact_masked'),
        'contact_purged': bool(claim.get('contact_purged', False)),
        'kitchen_id': claim.get('kitchen_id'),
    }