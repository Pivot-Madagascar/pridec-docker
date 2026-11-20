"""The user's mode lives in their session (auth_store): test at login, changed for that session only."""
from etlhub.infrastructure import auth_store


class Redis(dict):
    def __init__(self):
        super().__init__()
        self.ttls = {}

    def set(self, key, value, ex=None):
        self[key], self.ttls[key] = value, ex

    def ttl(self, key):
        return self.ttls.get(key, -2) if key in self else -2


def test_a_session_starts_in_test_mode_and_switches_alone_keeping_its_expiry(monkeypatch):
    redis = Redis()
    monkeypatch.setattr(auth_store, "get_redis", lambda: redis)
    mine = auth_store.create_session({"username": "jdoe"}, "pat1", 3600)
    other = auth_store.create_session({"username": "asmith"}, "pat1", 3600)
    assert auth_store.get_session(mine)["test_mode"] is True

    assert auth_store.set_session_mode(mine, False) is True

    assert auth_store.get_session(mine)["test_mode"] is False
    assert auth_store.get_session(other)["test_mode"] is True  # another user keeps theirs
    assert redis.ttls[auth_store._session_key(mine)] == 3600
    assert auth_store.set_session_mode("expired", False) is False
