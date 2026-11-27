"""DHIS2Reader: requests for the raw values and the system info, pivot_dhis_tools for the analytics."""
import requests
from pivot_dhis_tools import get_dataElements


class HttpDHIS2Reader:
    def _get(self, url: str, token: str, path: str, params: dict | None = None) -> dict:
        resp = requests.get(f"{url}{path}", params=params, headers={'Authorization': f'ApiToken {token}'}, timeout=600)
        resp.raise_for_status()
        return resp.json()

    def data_values(self, url: str, token: str, params: dict) -> list[dict]:
        return self._get(url, token, "/api/dataValueSets.json", params).get("dataValues", [])

    def analytics(self, url: str, token: str, code: str, periods: list[str], ou_query: str) -> list[dict]:
        df = get_dataElements(dhis_url=url, token=token, dx_query=f"dx:{code}", pe_query=f"pe:{';'.join(periods)}",
                              ou_query=ou_query, dx_id_scheme="CODE")
        # A row without orgUnit is dropped: the check counts orgUnits per period (pandas nunique skipped NaN before).
        return [] if df.empty else df.dropna(subset=["ou"]).to_dict(orient="records")

    def system_info(self, url: str, token: str) -> dict:
        return self._get(url, token, "/api/system/info.json")
