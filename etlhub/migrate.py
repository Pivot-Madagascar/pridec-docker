"""Brings etlhub.db and the test-mode db (Redis) to the schema of this code, by hand only.

    python -m etlhub.migrate          # backs each db up in logs/, then migrates it
    python -m etlhub.migrate --check  # lists what is pending, exit 1 if anything is

Stop the API and the workers first. See docs/decision-design/db-migrations/db-migrations.md.
"""
import os
import sys
from pathlib import Path

os.chdir(Path(__file__).resolve().parents[1])  # the repo root, like main.py: logs/ and input/ are relative to it

from etlhub.infrastructure.checkpoint_store import SCHEMA_VERSION, get_checkpoint_store

if __name__ == "__main__":
    check = "--check" in sys.argv
    lines = get_checkpoint_store().migrate(check=check)
    print("\n".join(lines) or f"Nothing to migrate: schema version {SCHEMA_VERSION}")
    sys.exit(1 if check and lines else 0)
