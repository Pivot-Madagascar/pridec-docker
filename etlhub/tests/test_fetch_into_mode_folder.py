"""B2: a test-mode fetch_* job (etl/ writes into os.getcwd()/input) ends in test/input; production's file stays."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from etlhub.application.use_cases import etl_use_cases
from etlhub.core.job_context import pipeline_test_mode


@pytest.fixture
def root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(etl_use_cases, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path)))
    (tmp_path / "input").mkdir()
    (tmp_path / "input" / "climate_data.json").write_text("production")
    return tmp_path


def _fetch(content):
    Path("input/climate_data.json").write_text(content)  # what the script does: relative to the cwd


def test_a_test_fetch_goes_to_test_input_and_production_keeps_its_file(root):
    pipeline_test_mode.set(True)
    with etl_use_cases._into_mode_folder("fetch_climate"):
        _fetch("test")

    assert (root / "test" / "input" / "climate_data.json").read_text() == "test"
    assert (root / "input" / "climate_data.json").read_text() == "production"
    assert sorted(p.name for p in (root / "input").iterdir()) == ["climate_data.json"]  # nothing left aside


def test_a_failed_test_fetch_leaves_production_as_it_was(root):
    pipeline_test_mode.set(True)
    with pytest.raises(RuntimeError):
        with etl_use_cases._into_mode_folder("fetch_climate"):
            _fetch("half written")
            raise RuntimeError("DHIS2 down")

    assert (root / "input" / "climate_data.json").read_text() == "production"
    assert not (root / "test" / "input" / "climate_data.json").exists()


def test_a_production_fetch_or_another_job_is_left_alone(root):
    pipeline_test_mode.set(False)
    with etl_use_cases._into_mode_folder("fetch_climate"):
        _fetch("new production")
    pipeline_test_mode.set(True)
    with etl_use_cases._into_mode_folder("import_gee"):
        pass

    assert (root / "input" / "climate_data.json").read_text() == "new production"
    assert not (root / "test").exists()
