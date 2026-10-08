"""DHIS2 username/password login, session cookie, token revocation.

DHIS2 is faked with httpx.MockTransport and Redis with an in-memory dict: these tests
say nothing about real Redis expiry, only about what etlhub writes and reads.
"""
import base64
import logging
import os

import httpx
import pytest
from fastapi.testclient import TestClient

from etlhub.api.auth import router as auth_router_module
from etlhub.core.config import get_settings
from etlhub.infrastructure import auth_store

DHIS2_URL = "https://dhis2.test"
PASSWORD = "s3cret-Pa55word"
FRONTEND = "http://localhost:5173"


class FakeRedis:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, ex=None):
        self.data[key] = value

    def delete(self, *keys):
        for k in keys:
            self.data.pop(k, None)

    def incr(self, key):
        self.data[key] = str(int(self.data.get(key, 0)) + 1)

    def expire(self, key, seconds):
        pass

    def pipeline(self):
        return self

    def execute(self):
        pass


class FakeDHIS2:
    """Basic auth for admin, ApiToken for the tokens it created."""

    def __init__(self):
        self.tokens = {}  # uid -> key
        self.created = 0
        self.calls = []
        self.down = False
        self.fail_create = False

    def _basic_ok(self, request):
        expected = "Basic " + base64.b64encode(f"admin:{PASSWORD}".encode()).decode()
        return request.headers.get("authorization") == expected

    def _token_ok(self, request):
        header = request.headers.get("authorization", "")
        return header.startswith("ApiToken ") and header[9:] in self.tokens.values()

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down", request=request)
        self.calls.append((request.method, request.url.path))
        authed = self._basic_ok(request) or self._token_ok(request)
        if request.url.path == "/api/me.json":
            if not authed:
                return httpx.Response(401)
            return httpx.Response(200, json={"id": "u1", "username": "admin", "email": None, "displayName": "Admin"})
        if request.method == "POST" and request.url.path == "/api/apiToken":
            if not self._basic_ok(request):
                return httpx.Response(401)
            if self.fail_create:
                return httpx.Response(500)
            if b'"MethodAllowedList"' not in request.content or b'"expire"' not in request.content:
                return httpx.Response(415)
            self.created += 1
            n = self.created
            uid, key = f"tokenUid{n:03d}", f"d2pat_key{n}"
            self.tokens[uid] = key
            return httpx.Response(201, json={"httpStatusCode": 201, "response": {"key": key, "uid": uid}})
        if request.method == "DELETE" and request.url.path.startswith("/api/apiToken/"):
            uid = request.url.path.rsplit("/", 1)[1]
            if not authed or uid not in self.tokens:
                return httpx.Response(404)
            del self.tokens[uid]
            return httpx.Response(200, json={"httpStatusCode": 200, "response": {"uid": uid}})
        return httpx.Response(404)


@pytest.fixture
def fake_redis(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(auth_store, "get_redis", lambda: fake)
    return fake


@pytest.fixture
def dhis2(monkeypatch):
    fake = FakeDHIS2()
    monkeypatch.setattr(
        auth_router_module, "dhis2_client", lambda: httpx.Client(transport=httpx.MockTransport(fake.handler))
    )
    return fake


@pytest.fixture
def settings(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "dhis2_allowed_hosts", "dhis2.test")
    monkeypatch.setattr(s, "cookie_secure", True)
    monkeypatch.setattr(s, "frontend_url", FRONTEND)
    return s


@pytest.fixture
def https_client(anon_app, fake_redis, dhis2, settings):
    # https base URL: the session cookie is Secure.
    return TestClient(anon_app, base_url="https://testserver")


def _login(client, password=PASSWORD, url=DHIS2_URL):
    return client.post("/auth/login", json={"dhis2_url": url, "username": "admin", "password": password})


def test_login_sets_httponly_cookie_and_stores_the_token_server_side(https_client, fake_redis, dhis2, caplog):
    caplog.set_level(logging.DEBUG)
    response = _login(https_client)

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "admin"
    cookie = response.headers["set-cookie"]
    assert "etlhub_session=" in cookie
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=strict" in cookie

    credential = auth_store.get_credential()
    assert credential["url"] == DHIS2_URL
    assert credential["token"] in dhis2.tokens.values()
    assert credential["token"] not in response.text
    assert PASSWORD not in caplog.text
    assert credential["token"] not in caplog.text

    assert https_client.get("/auth/me").json()["username"] == "admin"


def test_wrong_password_returns_401_and_stores_nothing(https_client, fake_redis, dhis2):
    response = _login(https_client, password="wrong")

    assert response.status_code == 401
    assert auth_store.get_credential() is None
    assert dhis2.tokens == {}


def test_too_many_failures_returns_429_without_calling_dhis2(https_client, dhis2):
    for _ in range(5):
        assert _login(https_client, password="wrong").status_code == 401
    calls = len(dhis2.calls)

    assert _login(https_client).status_code == 429
    assert len(dhis2.calls) == calls


@pytest.mark.parametrize("url", [
    "https://evil.test",                 # not in DHIS2_ALLOWED_HOSTS
    "http://dhis2.test",                 # plain http outside localhost
    "https://user:pw@dhis2.test",        # credentials in the URL
    "https://dhis2.test/?next=evil",     # query string
    "ftp://dhis2.test",
])
def test_disallowed_url_returns_400(https_client, dhis2, url):
    assert _login(https_client, url=url).status_code == 400
    assert dhis2.calls == []


def test_empty_allowlist_refuses_every_login(https_client, settings, dhis2, monkeypatch):
    monkeypatch.setattr(settings, "dhis2_allowed_hosts", "")
    assert _login(https_client).status_code == 400


def test_second_login_revokes_previous_token_and_invalidates_previous_session(anon_app, https_client, dhis2):
    _login(https_client)
    first_uid = auth_store.get_credential()["pat_uid"]

    other_browser = TestClient(anon_app, base_url="https://testserver")
    assert _login(other_browser).status_code == 200

    assert first_uid not in dhis2.tokens
    assert len(dhis2.tokens) == 1
    assert https_client.get("/auth/me").status_code == 401
    assert other_browser.get("/auth/me").status_code == 200


def test_failed_second_login_does_not_leave_the_revoked_token_active(anon_app, https_client, dhis2):
    _login(https_client)
    first_uid = auth_store.get_credential()["pat_uid"]
    dhis2.fail_create = True

    other_browser = TestClient(anon_app, base_url="https://testserver")
    assert _login(other_browser).status_code == 502

    assert first_uid not in dhis2.tokens
    assert auth_store.get_credential() is None
    assert https_client.get("/auth/me").status_code == 401


def test_logout_revokes_token_and_clears_session(https_client, dhis2):
    _login(https_client)

    response = https_client.post("/auth/logout", headers={"Origin": FRONTEND})

    assert response.status_code == 204
    assert dhis2.tokens == {}
    assert auth_store.get_credential() is None
    assert https_client.get("/auth/me").status_code == 401


def test_expired_credential_logs_the_user_out(https_client, fake_redis):
    _login(https_client)
    fake_redis.delete(auth_store.CREDENTIAL_KEY)  # what Redis does when the TTL ends

    assert https_client.get("/auth/me").status_code == 401


def test_dhis2_unreachable_returns_502(https_client, dhis2):
    dhis2.down = True
    assert _login(https_client).status_code == 502


def test_token_creation_failure_returns_502_and_stores_nothing(https_client, dhis2):
    dhis2.fail_create = True

    assert _login(https_client).status_code == 502
    assert auth_store.get_credential() is None


def test_redis_failure_after_token_creation_revokes_the_new_token(https_client, fake_redis, dhis2, monkeypatch):
    import redis

    def broken_set(*args, **kwargs):
        raise redis.RedisError("down")

    monkeypatch.setattr(fake_redis, "set", broken_set)

    assert _login(https_client).status_code == 503
    assert dhis2.tokens == {}


def test_request_from_another_origin_is_refused(https_client):
    _login(https_client)

    assert https_client.post("/auth/logout", headers={"Origin": "http://localhost:8082"}).status_code == 403
    assert https_client.get("/auth/me").status_code == 200


def test_me_without_cookie_returns_401(https_client):
    assert https_client.get("/auth/me").status_code == 401


def test_config_never_returns_the_token(https_client, monkeypatch):
    from etlhub.infrastructure.config_store import ConfigStore
    monkeypatch.setattr(ConfigStore, "get_all", lambda self: {})
    _login(https_client)

    body = https_client.get("/api/config/").json()

    assert body["has_dhis_token"] is True
    assert body["dhis_url"] == DHIS2_URL
    assert "dhis_token" not in body
    assert auth_store.get_credential()["token"] not in str(body)


@pytest.mark.integration
def test_fetch_me_with_a_real_token():
    """Read-only check against a real DHIS2 (GET /api/me). Needs DHIS_URL and DHIS_TOKEN."""
    from etlhub.api.auth.dhis2_auth import fetch_me

    url, token = os.getenv("DHIS_URL"), os.getenv("DHIS_TOKEN")
    if not url or not token:
        pytest.skip("DHIS_URL and DHIS_TOKEN environment variables not set")

    with httpx.Client(timeout=10) as client:
        user = fetch_me(client, url.rstrip("/"), token=token)

    assert user is not None and user["id"]
