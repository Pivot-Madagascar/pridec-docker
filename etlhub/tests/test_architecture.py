"""Guard: imports between etlhub layers follow the hexagonal direction (etlhub/CLAUDE.md, "Architecture").

Every source file outside tests/ is checked, every import too: lazy ones, `if TYPE_CHECKING:` ones, relative ones
(resolved) and `from etlhub import x` ones. Two rules: which etlhub modules a unit may import, and which
third-party libraries. A new crossing fails this test; fix the code, never extend ALLOWED_DEBT.
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYERS = {"domain", "application", "infrastructure", "api", "core"}
# Files at etlhub's root, imported bare when the cwd is etlhub/ (`from main import app` in run_server.py).
LOCAL = {path.stem for path in ROOT.glob("*.py")}
# What application and infrastructure may read of core: settings and the mode / request contextvars (CLAUDE.md, A3).
CORE_SHARED = {"core.config", "core.job_context", "core.request_context"}

# Unit (layer folder or root file) -> etlhub modules it may import (a module and everything under it).
ALLOWED = {
    "domain": {"domain"},
    "application": {"application", "domain", *CORE_SHARED},
    "infrastructure": {"infrastructure", "application", "domain", *CORE_SHARED, "core.celery_app"},
    "api": {"api", "application", "domain", "core"},
    "core": {"core"},
    "script_config.py": {"infrastructure", *CORE_SHARED},  # adapter of etl/scripts/config.py (A4)
    "migrate.py": {"infrastructure", *CORE_SHARED},
    "__init__.py": {"script_config"},
}
# Composition roots and entry points: they bind adapters to ports, so they may import every etlhub module.
COMPOSITION_ROOTS = {"core/dependencies.py", "main.py", "run_server.py", "run_celery.py"}

# Third-party libraries (top-level names; the stdlib is always allowed), per unit, then per file on top of it.
# I/O libraries (redis, sqlite3 is stdlib, httpx, requests, docker...) belong in infrastructure, which may import any.
THIRD_PARTY = {
    "domain": {"pydantic"},
    "application": {"pydantic"},
    "api": {"fastapi", "starlette", "pydantic"},
    "core": set(),
    "script_config.py": {"etl"},
    "migrate.py": set(),
    "__init__.py": set(),
    "main.py": {"fastapi"},
    "run_server.py": {"uvicorn"},
    "run_celery.py": set(),
}
THIRD_PARTY_FILES = {
    # core builds the settings, the Celery app and the FastAPI dependencies.
    "core/config.py": {"pydantic_settings"},
    "core/celery_app.py": {"celery"},
    "core/dependencies.py": {"fastapi"},
    # The ETL copies and wrappers, tolerated by decision (CLAUDE.md, "Architecture"; `ponytail:` in each file).
    "application/use_cases/etl_use_cases.py": {"etl"},
    "application/use_cases/build_analytics.py": {"etl", "httpx"},
    "application/use_cases/calc_alerts.py": {"etl", "pivot_dhis_tools"},
    "application/use_cases/fetch_pivot.py": {"etl", "pivot_dhis_tools"},
    "application/use_cases/gee_import.py": {"etl", "ee", "pridec_gee"},
    "application/use_cases/post_forecast.py": {"etl", "pivot_dhis_tools"},
    "application/use_cases/validation_use_cases.py": {"etl", "pandas", "geopandas"},
    # pridec_gee.AVAILABLE_VARIABLES only (a constant list, no I/O): not an ETL copy, accepted by the owner (2026-11-27).
    "application/use_cases/ingestion_service.py": {"pridec_gee"},
}
INFRASTRUCTURE_ANY = "infrastructure"

# Known debt, (file, module reached): empty since 2026-10-23 (docs/known-issues.md §2). Never add an entry.
ALLOWED_DEBT: set[tuple[str, str]] = set()


def _unit(rel: Path) -> str:
    return rel.parts[0] if rel.parts[0] in LAYERS else rel.as_posix()


def _imports(path: Path, rel: Path):
    """Absolute module names imported by a file, `from x import y` giving `x.y`."""
    package = ["etlhub", *rel.parts[:-1]]
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = ".".join(package[:len(package) - node.level + 1] + ([base] if base else []))
            yield from (f"{base}.{alias.name}" for alias in node.names)


def _crossings(root: Path = ROOT):
    """(file, module) for every import its unit may not make; (file, 'no rule') for a file no rule covers."""
    for path, rel in ((p, p.relative_to(root)) for p in sorted(root.rglob("*.py"))):
        if rel.parts[0] == "tests" or "__pycache__" in rel.parts:
            continue
        unit, name = _unit(rel), rel.as_posix()
        if unit not in ALLOWED and name not in COMPOSITION_ROOTS:
            yield name, "no rule"
            continue
        for module in _imports(path, rel):
            parts = module.split(".")
            if parts[0] in LOCAL:
                parts = ["etlhub", *parts]
            if parts[0] == "etlhub":
                target = ".".join(parts[1:])
                if target and name not in COMPOSITION_ROOTS and not any(
                        target == allowed or target.startswith(allowed + ".") for allowed in ALLOWED[unit]):
                    yield name, target
            elif parts[0] not in sys.stdlib_module_names and unit != INFRASTRUCTURE_ANY and parts[0] not in (
                    THIRD_PARTY.get(unit, set()) | THIRD_PARTY_FILES.get(name, set())):
                yield name, parts[0]


def test_no_new_layer_crossing():
    assert sorted(set(_crossings()) - ALLOWED_DEBT) == []


def test_debt_list_has_no_stale_entry():
    """A fixed crossing must leave ALLOWED_DEBT, so it cannot come back unnoticed."""
    assert sorted(ALLOWED_DEBT - set(_crossings())) == []


def test_the_guard_catches_the_holes_it_had(tmp_path):
    """Each import below passed the guard before 2026-11-27 (docs/known-issues.md §2)."""
    files = {
        "application/a.py": "from etlhub.core.dependencies import get_fetched_imports",
        "application/b.py": "from etlhub import infrastructure",
        "application/c.py": "from ..infrastructure import tasks",
        "application/d.py": "import requests",
        "domain/e.py": "from etlhub.core.config import get_settings",
        "api/f.py": "import redis.asyncio",
        "core/g.py": "from etlhub.infrastructure.job_store import JobStore",
        "script_config.py": "from etlhub.api import middleware",
        "migrate.py": "from etlhub.application.use_cases import etl_use_cases",
        "new_root.py": "",
    }
    for name, line in files.items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(line + "\n")
    assert sorted(_crossings(tmp_path)) == [
        ("api/f.py", "redis"), ("application/a.py", "core.dependencies.get_fetched_imports"),
        ("application/b.py", "infrastructure"), ("application/c.py", "infrastructure.tasks"),
        ("application/d.py", "requests"), ("core/g.py", "infrastructure.job_store.JobStore"),
        ("domain/e.py", "core.config.get_settings"), ("migrate.py", "application.use_cases.etl_use_cases"),
        ("new_root.py", "no rule"), ("script_config.py", "api.middleware"),
    ]
