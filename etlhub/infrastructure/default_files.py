from pathlib import Path

from etlhub.domain.pipeline import DISEASES, LEVEL

ASSETS = Path(__file__).resolve().parents[2] / "assets"
_CONFIGS = {"Malaria": "config_malaria.json", "Diarrhea": "config_diarrhea.json", "Respinf": "config_respiratory.json"}
_LEVELS = sorted(set(LEVEL.values()))
# Item → file under assets/, per mode. Test mode offers the same two files everywhere: assets/test/inputs/ is a
# CSB/Malaria set (its orgUnits are the CSB ones, its config needs mosquito_net), so fkt runs fail in the forecast.
SOURCES: dict[str, dict[str, str]] = {
    "production": {
        **{f"config/{disease}": f"forecast_configs/{name}" for disease, name in _CONFIGS.items()},
        **{f"external_data/{level}": f"forecast_configs/external_data_{level}.csv" for level in _LEVELS},
    },
    "test": {
        **{f"config/{disease}": "test/inputs/config.json" for disease in DISEASES},
        **{f"external_data/{level}": "test/inputs/external_data.csv" for level in _LEVELS},
    },
}


class DefaultFiles:
    """Default config.json / external_data.csv offered for each item: the files of the repo (assets/), read as they are now.

    ponytail: no history, a git pull changes the default at once; record defaults (SQLite, content in
    data/defaults/<hash>) when admins can replace one (etlhub/docs/decision-design/pipeline-config/pipeline-config.md, phase 4).
    """

    def __init__(self, assets: Path = ASSETS, sources: dict[str, dict[str, str]] = SOURCES):
        self._assets, self._sources = assets, sources

    def path(self, mode: str, item: str) -> Path | None:
        """File of the default offered for item, None when there is none or its file is missing."""
        relative = self._sources[mode].get(item)
        path = self._assets / relative if relative else None
        return path if path and path.is_file() else None

    def current(self, mode: str) -> dict[str, dict]:
        """item → {filename, size} of the default offered now; items whose file is missing are left out."""
        paths = {item: self.path(mode, item) for item in sorted(self._sources[mode])}
        return {item: {"filename": p.name, "size": p.stat().st_size} for item, p in paths.items() if p}
