"""Behaviour tests for the C05 in-process rate limiter.

Run from the repository root:
    python -m pytest projects/common/C05-visual-defect-detection/tests/test_c05_ratelimit.py -q
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / 'src'
ROOT = HERE.parent.parent.parent.parent
for extra in (str(SRC), str(ROOT)):
    if extra not in sys.path:
        sys.path.insert(0, extra)

from c05_ratelimit import RateLimiter, client_ip, identity, scoped_endpoints_only  # noqa: E402


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class TokenBucket(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.limiter = RateLimiter(limit=3, per_second=1.0, clock=self.clock)

    def test_burst_up_to_capacity_is_allowed(self):
        self.assertTrue(self.limiter.allow('a'))
        self.assertTrue(self.limiter.allow('a'))
        self.assertTrue(self.limiter.allow('a'))

    def test_request_beyond_capacity_is_rejected(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.assertFalse(self.limiter.allow('a'))

    def test_tokens_refill_over_time(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.assertFalse(self.limiter.allow('a'))
        self.clock.advance(2.0)
        self.assertTrue(self.limiter.allow('a'))

    def test_refill_is_capped_at_capacity(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.clock.advance(10_000.0)
        self.assertTrue(self.limiter.allow('a'))
        self.assertTrue(self.limiter.allow('a'))
        self.assertTrue(self.limiter.allow('a'))
        self.assertFalse(self.limiter.allow('a'), 'must not accumulate more than capacity')

    def test_keys_are_independent(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.assertFalse(self.limiter.allow('a'))
        self.assertTrue(self.limiter.allow('b'))

    def test_remaining_decreases_on_allow(self):
        self.assertEqual(self.limiter.remaining('a'), 3)
        self.limiter.allow('a')
        self.assertLess(self.limiter.remaining('a'), 3)

    def test_retry_after_is_at_least_one_second(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.assertFalse(self.limiter.allow('a'))
        self.assertGreaterEqual(self.limiter.retry_after('a'), 1.0)

    def test_retry_after_zero_when_tokens_available(self):
        self.assertEqual(self.limiter.retry_after('a'), 0.0)

    def test_zero_capacity_fails_closed(self):
        limiter = RateLimiter(limit=0, per_second=1.0, clock=self.clock)
        self.assertFalse(limiter.allow('a'))

    def test_zero_rate_fails_closed(self):
        limiter = RateLimiter(limit=5, per_second=0, clock=self.clock)
        self.assertFalse(limiter.allow('a'))

    def test_clock_going_backwards_does_not_grant_tokens(self):
        self.limiter.allow('a')
        self.limiter.allow('a')
        self.clock.advance(-100.0)
        self.assertLessEqual(self.limiter.remaining('a'), 2)

    def test_reset_clears_one_key(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.limiter.reset('a')
        self.assertTrue(self.limiter.allow('a'))

    def test_reset_all(self):
        for _ in range(3):
            self.limiter.allow('a')
        self.limiter.reset()
        self.assertTrue(self.limiter.allow('a'))

    def test_cost_larger_than_capacity_is_rejected(self):
        limiter = RateLimiter(limit=2, per_second=1.0, clock=self.clock)
        self.assertFalse(limiter.allow('a', cost=5))


class ClientIdentity(unittest.TestCase):
    def test_client_ip_reads_scope(self):
        self.assertEqual(client_ip({'client': ('10.0.0.7', 5555)}), '10.0.0.7')

    def test_client_ip_without_client_is_unknown(self):
        self.assertEqual(client_ip({}), 'unknown')
        self.assertEqual(client_ip({'client': None}), 'unknown')

    def test_identity_includes_scope(self):
        scope = {'client': ('10.0.0.7', 1)}
        self.assertEqual(identity(scope, role='ADMIN', kitchen_id='KITCHEN-A'),
                         ('10.0.0.7', 'ADMIN', 'KITCHEN-A'))

    def test_identity_without_scope_uses_placeholders(self):
        scope = {'client': ('10.0.0.7', 1)}
        self.assertEqual(identity(scope), ('10.0.0.7', '-', '-'))

    def test_different_kitchens_have_different_budgets(self):
        limiter = RateLimiter(limit=1, per_second=1.0, clock=FakeClock())
        a = identity({'client': ('10.0.0.7', 1)}, role='ADMIN', kitchen_id='KITCHEN-A')
        b = identity({'client': ('10.0.0.7', 1)}, role='ADMIN', kitchen_id='KITCHEN-B')
        self.assertTrue(limiter.allow(a))
        self.assertFalse(limiter.allow(a))
        self.assertTrue(limiter.allow(b))


class ScopedPaths(unittest.TestCase):
    def test_filters_empty_entries(self):
        result = scoped_endpoints_only(None, {'/api/claims', '', '/api/delivery-verifications'})
        self.assertEqual(result, {'/api/claims', '/api/delivery-verifications'})


if __name__ == '__main__':
    unittest.main()