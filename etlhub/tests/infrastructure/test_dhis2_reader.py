"""HttpDHIS2Reader: the requests the availability check sent before its port (requests and the library replaced)."""
from types import SimpleNamespace

import pandas as pd

from etlhub.infrastructure import dhis2_reader


def test_the_reads_send_the_token_and_return_what_the_check_counts(monkeypatch):
    sent = []

    def get(url, params, headers, timeout):
        sent.append((url, params, headers, timeout))
        body = {"dataValues": [{"orgUnit": "a"}]} if "dataValueSets" in url else {"lastAnalyticsTableSuccess": "x"}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: body)

    monkeypatch.setattr(dhis2_reader.requests, "get", get)
    monkeypatch.setattr(dhis2_reader, "get_dataElements", lambda **kw: sent.append(kw) or pd.DataFrame(
        [{"dx": "c", "ou": "a", "pe": "202608", "value": "1"}]))
    reader = dhis2_reader.HttpDHIS2Reader()

    assert reader.data_values("http://d", "t", {"period": ["202608"]}) == [{"orgUnit": "a"}]
    assert reader.system_info("http://d", "t") == {"lastAnalyticsTableSuccess": "x"}
    assert reader.analytics("http://d", "t", "c", ["202608", "202609"], "ou:X") == [
        {"dx": "c", "ou": "a", "pe": "202608", "value": "1"}]
    auth = {"Authorization": "ApiToken t"}
    assert sent == [("http://d/api/dataValueSets.json", {"period": ["202608"]}, auth, 600),
                    ("http://d/api/system/info.json", None, auth, 600),
                    {"dhis_url": "http://d", "token": "t", "dx_query": "dx:c", "pe_query": "pe:202608;202609",
                     "ou_query": "ou:X", "dx_id_scheme": "CODE"}]
    monkeypatch.setattr(dhis2_reader, "get_dataElements", lambda **kw: pd.DataFrame())
    assert reader.analytics("http://d", "t", "c", ["202608"], "ou:X") == []
    monkeypatch.setattr(dhis2_reader, "get_dataElements", lambda **kw: pd.DataFrame(  # a row without orgUnit: not counted
        [{"dx": "c", "ou": "a", "pe": "202608", "value": "1"}, {"dx": "c", "ou": None, "pe": "202608", "value": "2"}]))
    assert [r["ou"] for r in reader.analytics("http://d", "t", "c", ["202608"], "ou:X")] == ["a"]
