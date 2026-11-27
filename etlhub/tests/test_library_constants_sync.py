"""check_import_availability.py copies COM_ELEMENTS, CSB_IDS and CSB_ELEMENTS from pivot_dhis_tools: they must match.

conftest.py replaces pivot_dhis_tools with a MagicMock, so the real library is read in a subprocess. Skipped when the
library is not installed.
"""
import json
import subprocess
import sys

import pytest

from etlhub.application.use_cases import check_import_availability as availability

_READ = """
import importlib.util, json, sys
if importlib.util.find_spec("pivot_dhis_tools") is None:
    sys.exit(3)
from pivot_dhis_tools.pridec import import_pivot as lib
print(json.dumps({"COM_ELEMENTS": list(lib.COM_ELEMENTS), "CSB_IDS": list(lib.CSB_IDS),
                  "CSB_ELEMENTS": list(lib.CSB_ELEMENTS)}))
"""


def test_the_copied_constants_match_the_installed_library():
    run = subprocess.run([sys.executable, "-I", "-c", _READ], capture_output=True, text=True)
    if run.returncode == 3:
        pytest.skip("pivot_dhis_tools is not installed")
    assert run.returncode == 0, run.stderr
    library = json.loads(run.stdout)
    assert {"COM_ELEMENTS": availability.COM_ELEMENTS, "CSB_IDS": availability.CSB_IDS,
            "CSB_ELEMENTS": availability.CSB_ELEMENTS} == library
