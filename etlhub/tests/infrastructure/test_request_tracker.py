import sqlite3

import pytest

from etlhub.infrastructure.request_tracker import RequestTracker


def _log(request_id: str, url: str) -> dict:
    return {
        "request_id": request_id,
        "method": "GET",
        "url": url,
        "status_code": 200,
        "duration_ms": 1.0,
        "client_host": None,
        "error": None,
    }


@pytest.fixture
def tracker(tmp_path):
    return RequestTracker(db_path=tmp_path / "etlhub.db")


def test_save_stores_in_sqlite_without_json_files(tracker, tmp_path):
    log = _log("../../evil", "http://x/import_gee")

    tracker.save(log)

    assert tracker.get("../../evil") == log
    assert sorted(p.name for p in tmp_path.rglob("*")) == ["etlhub.db"]


def test_get_unknown_returns_none(tracker):
    assert tracker.get("missing") is None


def test_list_recent_newest_first_with_limit_and_filter(tracker):
    tracker.save(_log("a", "http://x/import_gee"))
    tracker.save(_log("b", "http://x/fetch_climate"))
    tracker.save(_log("c", "http://x/import_gee?webhook_url=y"))

    assert [l["request_id"] for l in tracker.list_recent()] == ["c", "b", "a"]
    assert [l["request_id"] for l in tracker.list_recent(limit=1)] == ["c"]
    assert [l["request_id"] for l in tracker.list_recent(endpoint="import_gee")] == ["c", "a"]


def test_save_deletes_entries_older_than_the_retention(tracker, tmp_path):
    tracker.save(_log("old", "http://x/import_gee"))
    with sqlite3.connect(tmp_path / "etlhub.db") as conn:
        conn.execute("UPDATE request_log SET created_at = '2000-01-01T00:00:00.000' WHERE request_id = 'old'")

    tracker.save(_log("new", "http://x/import_gee"))

    assert tracker.get("old") is None
    assert tracker.get("new") is not None


def test_the_purge_keeps_requests_of_the_journal(tracker, tmp_path):
    tracker.save({**_log("journaled", "http://x/import_gee"), "journal": True})
    with sqlite3.connect(tmp_path / "etlhub.db") as conn:
        conn.execute("UPDATE request_log SET created_at = '2000-01-01T00:00:00.000'")

    tracker.save(_log("new", "http://x/import_gee"))

    assert tracker.get("journaled") is not None
    assert set(tracker.get_many({"journaled", "new", "missing"})) == {"journaled", "new"}
