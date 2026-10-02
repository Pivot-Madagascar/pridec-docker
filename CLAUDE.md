# PRIDE-C repository

Multi-service repo. Each service owns its details; this file only holds the map and the rules that apply everywhere.

## Services

- `etl/` — Python ETL scripts (`etl/scripts/*.py`), `cli.sh`, own Dockerfile. Imported in-process by `etlhub`.
- `etlhub/` — FastAPI + Celery + Redis API that exposes the ETL scripts and the forecast pipeline. **Read `etlhub/CLAUDE.md` before working there.**
- `etlui/` — Vue front-end for `etlhub`. Has its own `CLAUDE.md`.
- `forecast/` — R forecast pipeline, run in Docker by `etlhub`.
- Root: `compose.yaml` (only `etl` and `forecast`), `install.sh`, `pridec` (wrapper around `docker compose run`), `input/`, `output/`, `logs/`.

## Rules for the whole repo

- Never run anything against a real DHIS2 or the host without explicit approval. Many endpoints and scripts write to DHIS2, run `docker run`, or delete `output/`. Use `DRYRUN=true` for manual runs.
- Never print or copy secrets. `.env`, `.env.debug` and `.gee-private-key.json` exist locally: mention variable names only.
- Python 3.12. Use `test-venv`; the system `python3` is 3.11.
- Do not change a contract shared between `etlhub` and `etlui` on one side only.
- Say what you could not verify. Do not guess.

## Where things are documented

- `etlhub/CLAUDE.md` — rules and gotchas for the API service
- `etlhub/docs/` — `ARCHITECTURE.md`, `known-issues.md`, `DEVELOPMENT.md` (test, architecture and clean-code state, proposed rules)
- `.claude/skills/etlhub/` — how etlhub is built (architecture, tables)
- `.claude/skills/etlhub-practices/` — how to change etlhub well (templates, migrations, checklists)