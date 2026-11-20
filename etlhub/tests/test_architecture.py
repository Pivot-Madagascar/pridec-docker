"""Guard: imports between etlhub layers follow the hexagonal direction (etlhub/CLAUDE.MD, "Architecture").

Every import is checked, lazy ones and `if TYPE_CHECKING:` ones included.
A new crossing fails this test; fix the code, never extend ALLOWED_DEBT.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Layer -> etlhub packages it may import. `core` is the composition root and configuration: not checked.
ALLOWED = {
    "domain": {"domain"},
    "application": {"application", "domain", "core"},
    "infrastructure": {"infrastructure", "application", "domain", "core"},
    "api": {"api", "application", "domain", "core"},
}

# Known debt, file -> layer it reaches: empty since 2026-10-23 (docs/known-issues.md §2). Never add an entry.
ALLOWED_DEBT: set[tuple[str, str]] = set()


def _crossings():
    for layer, allowed in ALLOWED.items():
        for path in (ROOT / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    parts = module.split(".")
                    if parts[0] == "etlhub" and len(parts) > 1 and parts[1] in ALLOWED.keys() - allowed:
                        yield path.relative_to(ROOT).as_posix(), parts[1]


def test_no_new_layer_crossing():
    assert sorted(set(_crossings()) - ALLOWED_DEBT) == []


def test_debt_list_has_no_stale_entry():
    """A fixed crossing must leave ALLOWED_DEBT, so it cannot come back unnoticed."""
    assert sorted(ALLOWED_DEBT - set(_crossings())) == []
