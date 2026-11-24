# PRIDE-C repository

Multi-service repo. Each service owns its details; this file only holds the map and the rules that apply everywhere.

## Services

- `etl/` — Python ETL scripts (`etl/scripts/*.py`), `cli.sh`, own Dockerfile. Imported in-process by `etlhub`.
- `etlhub/` — FastAPI + Celery + Redis API that exposes the ETL scripts and the forecast pipeline. **Read `etlhub/CLAUDE.md` before working there.**
- `etlui/` — Vue front-end for `etlhub`. Has its own `CLAUDE.md`.
- `forecast/` — R forecast pipeline, run in Docker by `etlhub`.
- `e2e/` — end-to-end scenario in a headless Chromium (pytest + Playwright, `e2e/requirements.txt`) against a running stack: `DHIS2_TEST_URL=… DHIS2_TEST_USERNAME=… DHIS2_TEST_PASSWORD=… test-venv/bin/python -m pytest e2e -v` (needs no active test pass and no running job; screenshots in `e2e/artifacts/`). It launches real jobs in test mode (DHIS2 writes in dry run, GEE, the forecast in Docker): ask before running it. CI: `.github/workflows/e2e-playwright.yml` (manual and on PRs, environment `init_test`, secrets listed in its header).
- Root: `compose.yaml` (only `etl` and `forecast`), `install.sh`, `pridec` (wrapper around `docker compose run`), `input/`, `output/`, `logs/`.

## Rules for the whole repo

- Never run anything against a real DHIS2 or the host without explicit approval. Many endpoints and scripts write to DHIS2, run `docker run`, or delete `output/`. Use `DRYRUN=true` for manual runs.
- Never print or copy secrets. `.env`, `.env.debug` and `.gee-private-key.json` exist locally: mention variable names only.
- Python 3.12. Use `test-venv`; the system `python3` is 3.11.
- Do not change a contract shared between `etlhub` and `etlui` on one side only.
- Say what you could not verify. Do not guess.
- Every implementation (feature, fix, refactor, review) is done with the **ponytail** skill (`/ponytail`, level `full`): understand the flow first, then climb the ladder (does it need to exist → already in the repo → stdlib → native → installed dependency → one line → minimum code), shortest working diff, no speculative abstraction. A deliberate shortcut with a known limit gets a `ponytail:` comment naming the limit and the upgrade path (`/ponytail-debt` lists them). Non-trivial logic leaves one runnable check. Ponytail never skips the rules above, input validation, error handling that prevents data loss, or security.

## Where things are documented

- `etlhub/CLAUDE.md` — rules and gotchas for the API service
- `etlhub/docs/` — `ARCHITECTURE.md`, `known-issues.md`, `DEVELOPMENT.md` (test, architecture and clean-code state, proposed rules)
- `etlhub/docs/testing-QA/` — manual test logs (`test-incident-log.md`, `test-pipeline-michelle.md`) and local tickets (`ticket-*.md`)
- `etlhub/docs/decision-design/` — design and decision docs, implemented or under discussion, one folder per feature (`pipeline-checkpoints/`, `pipeline-config/`, `default-input-files/`, `cycle-journal/`, `cycle-passes/`, `pass-folders/`, `dry-run/`, `import-availability/`, `db-migrations/`, `foreign-keys/`, `mode-isolation/`, `pass-config/`, `gee-import/`). A new feature's docs go in a new folder there
- `etlui/docs/decision-design/` — same for etlui (`tailwind-migration/`, `shadcn-migration/`, `page-layout/`, `app-shell/`)
- `.claude/skills/etlhub/` — how etlhub is built (architecture, tables)
- `.claude/skills/etlhub-practices/` — how to change etlhub well (templates, migrations, checklists)