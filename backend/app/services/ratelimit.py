"""Tiny in-memory sliding-window rate limiter for sensitive endpoints.

Brute-force / credential-stuffing protection for the auth routes without a new
dependency or Redis. State is a per-process dict of recent hit timestamps keyed
by (bucket, client-ip); it's adequate for the single-instance deployment. If the
app is ever scaled to multiple workers/instances, move this to a shared store
(Redis) so the window is global rather than per-process.

Usage (as a FastAPI dependency factory):

    from app.services.ratelimit import rate_limit

    @router.post("/login", dependencies=[Depends(rate_limit("login", 10, 60))])
    def login(...): ...

When `settings.rate_limit_enabled` is False (tests), the dependency is a no-op.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.config import get_settings

settings = get_settings()

# (bucket, client_ip) -> deque[float] of hit timestamps within the window.
_hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _client_ip(request: Request) -> str:
    """Best-effort client IP.

    Behind a reverse proxy (Nginx/ALB) the real client is in X-Forwarded-For;
    take the first hop. Falls back to the socket peer. Note: X-Forwarded-For is
    client-spoofable when NOT behind a trusted proxy that overwrites it — keep a
    trusted proxy in front in production (the H2 TLS setup does exactly this).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _allow(bucket: str, ip: str, limit: int, window_s: int, now: float) -> bool:
    """Record a hit and return whether it's within the limit (sliding window)."""
    key = (bucket, ip)
    with _lock:
        dq = _hits[key]
        cutoff = now - window_s
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        # Opportunistic cleanup so empty buckets don't accumulate forever.
        if not dq:
            _hits.pop(key, None)
        return True


def rate_limit(bucket: str, limit: int, window_s: int):
    """Build a FastAPI dependency enforcing `limit` requests per `window_s` per IP.

    `bucket` namespaces the counter so different endpoints don't share a budget.
    """

    def dependency(request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        now = time.monotonic()
        if not _allow(bucket, _client_ip(request), limit, window_s, now):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please wait a moment and try again.",
                headers={"Retry-After": str(window_s)},
            )

    return dependency


def reset() -> None:
    """Clear all counters — used by tests to isolate cases."""
    with _lock:
        _hits.clear()
