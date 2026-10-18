"""Behaviour tests for the C05 contact-privacy contract.

These lock the decision that reporter contacts are never stored in cleartext.
Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_privacy.py -q
"""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'src'
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

import c05_privacy as privacy  # noqa: E402

SECRET = 'test-secret-not-a-real-credential'


class BlindIndex(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {privacy.SECRET_ENV: SECRET})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_index_is_deterministic_for_same_contact(self):
        a = privacy.blind_index('+62 812-3456')
        b = privacy.blind_index('+628123456')
        self.assertEqual(a, b, 'formatting variants must collide as one person')

    def test_index_differs_for_different_contacts(self):
        self.assertNotEqual(privacy.blind_index('+62 812-3456'), privacy.blind_index('+62 812-9999'))

    def test_index_is_not_a_plain_hash(self):
        """A plain SHA-256 would be brute-forceable over the phone number space."""
        import hashlib
        plain = hashlib.sha256(b'628123456').hexdigest()
        self.assertNotEqual(privacy.blind_index('+628123456'), plain)

    def test_index_changes_with_secret(self):
        first = privacy.blind_index('+628123456')
        with mock.patch.dict(os.environ, {privacy.SECRET_ENV: 'a-different-secret'}):
            self.assertNotEqual(first, privacy.blind_index('+628123456'))

    def test_empty_contact_rejected(self):
        with self.assertRaises(ValueError):
            privacy.blind_index('   ')


class MissingSecret(unittest.TestCase):
    def test_missing_secret_raises_instead_of_falling_back(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop(privacy.SECRET_ENV, None)
            with self.assertRaises(privacy.ContactPrivacyNotConfigured):
                privacy.blind_index('+628123456')

    def test_blank_secret_is_treated_as_missing(self):
        with mock.patch.dict(os.environ, {privacy.SECRET_ENV: '   '}, clear=True):
            with self.assertRaises(privacy.ContactPrivacyNotConfigured):
                privacy.blind_index('+628123456')


class Masking(unittest.TestCase):
    def test_mask_shows_only_last_four_digits(self):
        masked = privacy.mask_contact('+62 812-3456')
        self.assertTrue(masked.endswith('3456'))
        self.assertNotIn('812', masked)

    def test_mask_ignores_a_leading_plus_in_the_length(self):
        """Regression: canonical_digits keeps '+', which mis-sized the mask."""
        self.assertEqual(privacy.mask_contact('+62 812-3456'), '*****3456')
        self.assertEqual(privacy.mask_contact('628123456'), '*****3456')

    def test_mask_short_value_is_fully_hidden(self):
        """Regression: a <=4 digit value must never be returned in cleartext."""
        masked = privacy.mask_contact('123')
        self.assertEqual(masked, '***')
        self.assertNotIn('123', masked)


class ContactRecord(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {privacy.SECRET_ENV: SECRET})
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_record_never_contains_raw_contact(self):
        record = privacy.contact_record('+62 812-3456')
        self.assertNotIn('+62 812-3456', str(record))
        self.assertNotIn('628123456', str(record))

    def test_record_has_index_and_mask(self):
        record = privacy.contact_record('+62 812-3456')
        self.assertIn('contact_blind_index', record)
        self.assertIn('contact_masked', record)


class Retention(unittest.TestCase):
    def test_retention_due_when_past_window(self):
        old = (datetime.now(timezone.utc) - timedelta(days=privacy.RETENTION_DAYS + 1)).isoformat()
        self.assertTrue(privacy.is_retention_due({'created_at': old}))

    def test_not_due_inside_window(self):
        recent = datetime.now(timezone.utc).isoformat()
        self.assertFalse(privacy.is_retention_due({'created_at': recent}))

    def test_not_due_when_already_purged(self):
        old = (datetime.now(timezone.utc) - timedelta(days=privacy.RETENTION_DAYS + 1)).isoformat()
        self.assertFalse(privacy.is_retention_due({'created_at': old, 'contact_purged': True}))

    def test_unparseable_timestamp_is_not_due(self):
        self.assertFalse(privacy.is_retention_due({'created_at': 'not-a-date'}))


class Purge(unittest.TestCase):
    def test_purge_removes_pii_fields(self):
        claim = {
            'claim_id': 'c1',
            'reporter_contact': '+62 812-3456',
            'reporter_contact_normalized': '+628123456',
            'contact_blind_index': 'deadbeef',
            'contact_masked': '****3456',
            'status': 'submitted',
        }
        purged = privacy.purge_claim(claim)
        for field in ('reporter_contact', 'reporter_contact_normalized', 'contact_blind_index', 'contact_masked'):
            self.assertNotIn(field, purged)
        self.assertTrue(purged['contact_purged'])
        self.assertIn('contact_purged_at', purged)

    def test_purge_does_not_mutate_input(self):
        claim = {'reporter_contact': '+628123456'}
        privacy.purge_claim(claim)
        self.assertIn('reporter_contact', claim)


class PublicView(unittest.TestCase):
    def test_public_view_excludes_internal_fields(self):
        claim = {
            'claim_id': 'c1',
            'meal_date': '2026-10-18',
            'symptoms': ['nausea'],
            'status': 'submitted',
            'contact_masked': '****3456',
            'contact_blind_index': 'deadbeef',
            'reporter_contact': '+628123456',
            'reporter_name': 'Real Name',
            'fraud_score': 0.9,
            'internal_note': 'do not expose',
        }
        view = privacy.public_view(claim)
        for forbidden in ('contact_blind_index', 'reporter_contact', 'reporter_name', 'internal_note', 'fraud_score'):
            self.assertNotIn(forbidden, view)
        self.assertIn('claim_id', view)


if __name__ == '__main__':
    unittest.main()