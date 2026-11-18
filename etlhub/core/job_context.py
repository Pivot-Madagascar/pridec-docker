from contextvars import ContextVar

# DRYRUN of the job running in this context (its launch's choice, else the default the gate gave): what the ETL
# scripts read through script_config._get("DRYRUN"). None outside a job: they read DRYRUN from Redis (.env).
job_dry_run: ContextVar[bool | None] = ContextVar("job_dry_run", default=None)
