"""check_import_availability.py copies COM_ELEMENTS, CSB_IDS and CSB_ELEMENTS from pivot_dhis_tools, and computes the
periods create_period_range gives: they must match.

conftest.py replaces pivot_dhis_tools with a MagicMock, so the real library is read in a subprocess. Skipped when the
library is not installed.
"""
import json
from datetime import date
import subprocess
import sys

import pytest

from etlhub.application.use_cases import check_import_availability as availability

_READ = """
import importlib.util, json, sys
if importlib.util.find_spec("pivot_dhis_tools") is None:
    sys.exit(3)
from pivot_dhis_tools.pridec import import_pivot as lib
from datetime import date
from dateutil.relativedelta import relativedelta
from pivot_dhis_tools import create_period_range
days = [date(2026, 1, 31), date(2026, 3, 31), date(2026, 11, 27), date(2026, 12, 1), date(2027, 2, 28)]
print(json.dumps({"COM_ELEMENTS": list(lib.COM_ELEMENTS), "CSB_IDS": list(lib.CSB_IDS),
                  "CSB_ELEMENTS": list(lib.CSB_ELEMENTS),
                  # availability_plan's periods: import_pivot_* from 8 months ago, import_gee from the 1st, 3 months ago
                  "periods": {d.isoformat(): [create_period_range(start=d - relativedelta(months=8), end=d.replace(day=1)),
                                              create_period_range(start=d.replace(day=1) - relativedelta(months=3),
                                                                  end=d.replace(day=1))] for d in days}}))
"""


def test_the_copied_constants_match_the_installed_library():
    run = subprocess.run([sys.executable, "-I", "-c", _READ], capture_output=True, text=True)
    if run.returncode == 3:
        pytest.skip("pivot_dhis_tools is not installed")
    assert run.returncode == 0, run.stderr
    library = json.loads(run.stdout)
    periods = library.pop("periods")
    assert {"COM_ELEMENTS": availability.COM_ELEMENTS, "CSB_IDS": availability.CSB_IDS,
            "CSB_ELEMENTS": availability.CSB_ELEMENTS} == library
    for day, (pivot, gee) in periods.items():  # _last_months replaces create_period_range (no library in application)
        today = date.fromisoformat(day)
        assert ["pe:" + ";".join(availability._last_months(n, today)) for n in (8, 3)] == [pivot, gee], day
