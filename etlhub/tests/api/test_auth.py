"""DHIS2 username/password login, session cookie, token revocation.

DHIS2 is faked with httpx.MockTransport and Redis with an in-memory dict: these tests
say nothing about real Redis expiry, only about what etlhub writes and reads.
"""
import base64
import fnmatch
import logging
import os
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from etlhub.api.auth import router as auth_router_module
from etlhub.core.config import get_settings
from etlhub.infrastructure import auth_store

DHIS2_URL = "https://dhis2.test"
PASSWORD = "s3cret-Pa55word"
USERS = {"admin": PASSWORD, "jdoe": "an0ther-Pa55word"}
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

    def scan_iter(self, pattern):
        return [k for k in list(self.data) if fnmatch.fnmatchcase(k, pattern)]

    def execute(self):
        pass


class FakeDHIS2:
    """Basic auth for USERS, ApiToken for the tokens it created (each one acts as the user who created it)."""

    def __init__(self):
        self.tokens = {}  # uid -> key
        self.owners = {}  # key -> username
        self.created = 0
        self.calls = []
        self.down = False
        self.fail_create = False

    def _basic_user(self, request):
        for name, password in USERS.items():
            if request.headers.get("authorization") == "Basic " + base64.b64encode(f"{name}:{password}".encode()).decode():
                return name
        return None

    def _token_user(self, request):
        header = request.headers.get("authorization", "")
        key = header[9:] if header.startswith("ApiToken ") else None
        return self.owners[key] if key in self.tokens.values() else None

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.down:
            raise httpx.ConnectError("down", request=request)
        self.calls.append((request.method, request.url.path))
        user = self._basic_user(request) or self._token_user(request)
        if request.url.path == "/api/me.json":
            if not user:
                return httpx.Response(401)
            return httpx.Response(200, json={"id": f"id_{user}", "username": user, "email": None, "displayName": user})
        if request.method == "POST" and request.url.path == "/api/apiToken":
            if not self._basic_user(request):
                return httpx.Response(401)
            if self.fail_create:
                return httpx.Response(500)
            if b'"MethodAllowedList"' not in request.content or b'"expire"' not in request.content:
                return httpx.Response(415)
            self.created += 1
            n = self.created
            uid, key = f"tokenUid{n:03d}", f"d2pat_key{n}"
            self.tokens[uid], self.owners[key] = key, self._basic_user(request)
            return httpx.Response(201, json={"httpStatusCode": 201, "response": {"key": key, "uid": uid}})
        if request.method == "DELETE" and request.url.path.startswith("/api/apiToken/"):
            uid = request.url.path.rsplit("/", 1)[1]
            if not user or uid not in self.tokens:
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


def _login(client, password=None, url=DHIS2_URL, username="admin"):
    return client.post("/auth/login", json={"dhis2_url": url, "username": username,
                                            "password": password or USERS[username]})


def _session_ends(client):
    """What the browser does after 24 h: the session cookie is gone, the device cookie stays."""
    client.cookies.delete("etlhub_session")


def test_login_sets_httponly_cookie_and_stores_the_token_server_side(https_client, fake_redis, dhis2, caplog):
    caplog.set_level(logging.DEBUG)
    response = _login(https_client)

    assert response.status_code == 200
    assert response.json()["user"]["username"] == "admin"
    assert "is_admin" not in response.json()["user"]  # no roles: every DHIS2 user of an allowed host is equal
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


def test_the_session_lasts_24_h_the_token_and_the_browser_id_30_days(https_client):
    response = _login(https_client)

    cookies = response.headers.get_list("set-cookie")
    assert any(c.startswith("etlhub_session=") and "Max-Age=86400" in c for c in cookies)
    assert any(c.startswith("etlhub_device=") and f"Max-Age={30 * 24 * 3600}" in c and "HttpOnly" in c for c in cookies)
    credential = auth_store.get_credential("admin")
    assert credential["expires_at"] - time.time() > 29 * 24 * 3600
    assert response.json()["expires_at"] == credential["expires_at"]
    assert credential["token"] not in str(cookies)


def test_a_login_from_the_same_browser_after_24_h_keeps_the_token(https_client, dhis2):
    first = _login(https_client).json()
    uid = auth_store.get_credential("admin")["pat_uid"]
    _session_ends(https_client)
    assert https_client.get("/auth/me").status_code == 401  # logged out by the browser

    second = _login(https_client)

    assert second.status_code == 200 and second.json()["expires_at"] == first["expires_at"]
    assert auth_store.get_credential("admin")["pat_uid"] == uid and dhis2.created == 1 and uid in dhis2.tokens
    assert https_client.get("/auth/me").status_code == 200


def test_a_login_of_the_same_account_from_another_browser_replaces_its_token(anon_app, https_client, dhis2):
    _login(https_client)
    first_uid = auth_store.get_credential("admin")["pat_uid"]

    other_browser = TestClient(anon_app, base_url="https://testserver")
    assert _login(other_browser).status_code == 200

    assert first_uid not in dhis2.tokens and len(dhis2.tokens) == 1
    assert https_client.get("/auth/me").status_code == 401  # the first browser is logged out
    assert other_browser.get("/auth/me").status_code == 200


def test_each_account_has_its_own_token_and_jobs_use_the_latest(anon_app, https_client, dhis2):
    _login(https_client)
    admin_uid = auth_store.get_credential("admin")["pat_uid"]
    jdoe_browser = TestClient(anon_app, base_url="https://testserver")
    _login(jdoe_browser, username="jdoe")
    jdoe_uid = auth_store.get_credential("jdoe")["pat_uid"]

    assert admin_uid != jdoe_uid and {admin_uid, jdoe_uid} <= set(dhis2.tokens)
    assert https_client.get("/auth/me").json()["username"] == "admin"  # nobody logged out by another account
    assert jdoe_browser.get("/auth/me").json()["username"] == "jdoe"
    assert auth_store.get_credential()["pat_uid"] == jdoe_uid  # the jobs' token: the most recently created
    assert dhis2.owners[auth_store.get_credential("admin")["token"]] == "admin"  # each token acts as its account

    assert jdoe_browser.post("/auth/logout", headers={"Origin": FRONTEND}).status_code == 204
    assert jdoe_uid not in dhis2.tokens  # a logout revokes that account's token only
    assert https_client.get("/auth/me").status_code == 200
    assert auth_store.get_credential()["pat_uid"] == admin_uid  # the jobs fall back on the remaining token


def test_a_token_revoked_in_dhis2_is_replaced_at_login(https_client, dhis2):
    _login(https_client)
    uid = auth_store.get_credential("admin")["pat_uid"]
    del dhis2.tokens[uid]  # revoked by hand in DHIS2
    _session_ends(https_client)

    assert _login(https_client).status_code == 200
    assert auth_store.get_credential("admin")["pat_uid"] != uid and dhis2.created == 2


def test_failed_login_from_another_browser_does_not_leave_the_revoked_token_active(anon_app, https_client, dhis2):
    _login(https_client)
    first_uid = auth_store.get_credential("admin")["pat_uid"]
    dhis2.fail_create = True

    other_browser = TestClient(anon_app, base_url="https://testserver")
    assert _login(other_browser).status_code == 502

    assert first_uid not in dhis2.tokens
    assert auth_store.get_credential("admin") is None
    assert https_client.get("/auth/me").status_code == 401


def test_logout_revokes_the_token_and_clears_the_session(https_client, dhis2):
    _login(https_client)

    response = https_client.post("/auth/logout", headers={"Origin": FRONTEND})

    assert response.status_code == 204
    assert dhis2.tokens == {}
    assert auth_store.get_credential("admin") is None
    assert https_client.get("/auth/me").status_code == 401


def test_a_login_or_logout_while_a_job_runs_keeps_the_token_that_job_read(anon_app, https_client, dhis2, checkpoint_store):
    _login(https_client)
    first_uid = auth_store.get_credential("admin")["pat_uid"]
    checkpoint_store.start("import_gee", "import_gee_1")  # read DHIS_TOKEN at its start

    other_browser = TestClient(anon_app, base_url="https://testserver")
    assert _login(other_browser).status_code == 200
    second_uid = auth_store.get_credential("admin")["pat_uid"]
    assert first_uid in dhis2.tokens  # the running import keeps working; the token expires on its own
    assert https_client.get("/auth/me").status_code == 401  # its session is still replaced

    assert other_browser.post("/auth/logout", headers={"Origin": FRONTEND}).status_code == 204
    assert second_uid in dhis2.tokens and auth_store.get_credential("admin") is None

    # Logged out: etlhub no longer knows that token, it is left to expire (30 days at most).
    checkpoint_store.finish("import_gee_1", "success")
    _login(other_browser)
    third_uid = auth_store.get_credential("admin")["pat_uid"]
    _login(https_client)  # another browser, no job any more: the token it replaces is revoked
    assert third_uid not in dhis2.tokens


def test_expired_credential_logs_the_user_out(https_client, fake_redis):
    _login(https_client)
    fake_redis.delete(f"{auth_store.CREDENTIAL_KEY}:admin")  # what Redis does when the TTL ends

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
    """Against a real DHIS2: creates a PAT, reads GET /api/me with it, then revokes it.

    Needs DHIS2_TEST_URL, DHIS2_TEST_USERNAME and DHIS2_TEST_PASSWORD in the environment
    (a test account, never the .env token: that one may be expired or in use by jobs).
    """
    import time

    from etlhub.api.auth.dhis2_auth import create_pat, dhis2_client, fetch_me, revoke_pat

    url = os.getenv("DHIS2_TEST_URL", "").rstrip("/")
    basic = (os.getenv("DHIS2_TEST_USERNAME"), os.getenv("DHIS2_TEST_PASSWORD"))
    if not url or not all(basic):
        pytest.skip("DHIS2_TEST_URL, DHIS2_TEST_USERNAME and DHIS2_TEST_PASSWORD not set")

    with dhis2_client() as client:
        key, uid = create_pat(client, url, basic, (int(time.time()) + 600) * 1000)
        try:
            user = fetch_me(client, url, token=key)
        finally:
            revoked = revoke_pat(client, url, uid, token=key)
        assert user is not None and user["id"] and user["username"] == basic[0]
        assert revoked
        # Deleted in DHIS2. Not "fetch_me(token) is None": DHIS2 2.40 keeps accepting a deleted token from its cache for a while.
        assert client.get(f"{url}/api/apiToken/{uid}", auth=basic).status_code == 404


def test_dhis2_urls_lists_allowed_hosts_with_the_scheme_login_accepts(anon_app, monkeypatch):
    monkeypatch.setattr(get_settings(), "dhis2_allowed_hosts", " localhost:8082, DHIS2.test ,,")
    response = TestClient(anon_app).get("/auth/dhis2-urls")
    assert response.status_code == 200
    assert response.json() == ["http://localhost:8082", "https://dhis2.test"]
