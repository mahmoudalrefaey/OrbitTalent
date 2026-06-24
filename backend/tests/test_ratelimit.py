"""Rate-limiter unit tests.

The full app suite runs with RATE_LIMIT_ENABLED=false (conftest) so many auth
calls from one client don't trip the limit. Here we exercise the limiter
directly with it enabled, independent of the app wiring.
"""
import importlib

import pytest


@pytest.fixture
def limiter(monkeypatch):
    """Fresh limiter module with rate limiting forced ON and counters cleared."""
    from app.config import get_settings

    rl = importlib.import_module("app.services.ratelimit")
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", True)
    rl.reset()
    return rl


def _ip_request(ip: str):
    """Minimal stand-in for a Starlette Request the dependency needs."""
    class _Client:
        host = ip

    class _Req:
        client = _Client()
        headers: dict = {}

    return _Req()


def test_allows_up_to_limit_then_blocks(limiter):
    dep = limiter.rate_limit("test", limit=3, window_s=60)
    req = _ip_request("1.2.3.4")
    # First 3 succeed.
    for _ in range(3):
        dep(req)
    # 4th is blocked with 429.
    with pytest.raises(Exception) as exc:
        dep(req)
    assert getattr(exc.value, "status_code", None) == 429


def test_limit_is_per_ip(limiter):
    dep = limiter.rate_limit("test", limit=2, window_s=60)
    a, b = _ip_request("10.0.0.1"), _ip_request("10.0.0.2")
    dep(a); dep(a)            # A exhausts its budget
    dep(b); dep(b)            # B has its own budget — unaffected
    with pytest.raises(Exception):
        dep(a)


def test_buckets_are_independent(limiter):
    login = limiter.rate_limit("login", limit=1, window_s=60)
    register = limiter.rate_limit("register", limit=1, window_s=60)
    req = _ip_request("9.9.9.9")
    login(req)                # uses the login bucket
    register(req)             # different bucket — still allowed
    with pytest.raises(Exception):
        login(req)            # login bucket now exhausted


def test_x_forwarded_for_is_used(limiter):
    dep = limiter.rate_limit("test", limit=1, window_s=60)

    class _Req:
        client = None
        headers = {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}

    dep(_Req())
    with pytest.raises(Exception):
        dep(_Req())


def test_disabled_is_noop(monkeypatch):
    from app.config import get_settings

    rl = importlib.import_module("app.services.ratelimit")
    monkeypatch.setattr(get_settings(), "rate_limit_enabled", False)
    rl.reset()
    dep = rl.rate_limit("test", limit=1, window_s=60)
    req = _ip_request("8.8.8.8")
    # Far exceeds the limit, but disabled -> never raises.
    for _ in range(50):
        dep(req)
