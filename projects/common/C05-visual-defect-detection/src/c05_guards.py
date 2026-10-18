"""Request guards for C05: scoped asset reads and public-intake rate limiting.

Both guards run as HTTP middleware in front of the shared runtime. They exist because the
donor had neither control, and the Phase 0 safety review found:

- `shared_mvp` registers `GET /api/assets/{name}` with no scope at all. Any caller who knows or
  guesses an image id can download a tray photo. Tray photos are the most sensitive asset in the
  product, so reads are now bound to a declared role/kitchen scope.
- Nothing bounded request rate, so public intake could be flooded.

Both guards are demo-strength on purpose: the prototype has no authentication, so `role` is still
client-supplied (see D5). What these guards add is a *consistent, tested* boundary rather than an
accidental open door, and a real rate bound that survives a naive flood.

Asset scope rule: an asset may be read only if it is referenced by a record inside the caller's
declared kitchen scope. The mapping is derived from the store, never from the filename.
"""
from __future__ import annotations

from c05_ratelimit import RateLimiter, identity

ASSET_PREFIX = '/api/assets/'
RATE_LIMITED_PREFIXES = ('/api/claims', '/api/delivery-verifications')
PUBLIC_INTAKE_CAPACITY = 30
PUBLIC_INTAKE_REFILL_PER_SECOND = 0.5

# Collections whose rows reference an asset by id, and the field holding that id.
_ASSET_OWNERS = (
    ('inspection', 'image_id'),
    ('delivery_verification', 'image_id'),
)


def _owns_asset(store, asset_name: str) -> str | None:
    """Return the kitchen_id that owns `asset_name`, or None when unclaimed.

    `asset_name` looks like `<uuid>.png`. The stem is matched against the stored records, so a
    caller cannot reach an asset by guessing a path outside the registry.
    """
    stem = asset_name.rsplit('.', 1)[0]
    for kind, field in _ASSET_OWNERS:
        for row in store.list_kind(kind):
            if row.get(field) == stem:
                kitchen = row.get('kitchen_id')
                if kitchen:
                    return kitchen
    return None


def install_guards(app, store, scope_fn, *, limiter: RateLimiter | None = None) -> RateLimiter:
    """Attach the asset-scope and rate-limit guards to `app`.

    `scope_fn(role)` returns the set of kitchens that role may touch, mirroring the backend's own
    `_scope`. Passing it in keeps the two definitions from drifting.
    """
    limiter = limiter or RateLimiter(
        limit=PUBLIC_INTAKE_CAPACITY,
        per_second=PUBLIC_INTAKE_REFILL_PER_SECOND,
    )

    @app.middleware('http')
    async def c05_guards(request, call_next):
        path = request.url.path

        if path.startswith(ASSET_PREFIX):
            asset_name = path[len(ASSET_PREFIX):]
            role = request.query_params.get('role', '')
            allowed = scope_fn(role) if role else set()
            owner_kitchen = _owns_asset(store, asset_name)
            if owner_kitchen is None or owner_kitchen not in allowed:
                # 404 rather than 403: a 403 would confirm that the asset exists.
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail': 'Unknown asset'}, status_code=404)

        if path.startswith(RATE_LIMITED_PREFIXES):
            bucket_key = identity(request.scope, role=request.query_params.get('role') or None)
            if not limiter.allow(bucket_key):
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    {'detail': 'Rate limit exceeded. Try again shortly.'},
                    status_code=429,
                    headers={'Retry-After': str(int(limiter.retry_after(bucket_key)) or 1)},
                )

        return await call_next(request)

    app.state.rate_limiter = limiter
    return limiter