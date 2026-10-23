import subprocess
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

from etlhub.core.config import get_settings
from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure.config_store import ConfigStore
from etlhub.infrastructure import etl_events


def _container_user() -> list[str]:
    """Run the container as the worker's user, not root.

    Files the forecast writes in output/ then belong to the etlhub user, so opening
    the next run can empty output/ without sudo. HOME points to a writable
    directory because the image has no home for that user.
    """
    if os.getuid() == 0:
        return []
    return ['--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp']


def _build_dynamic_env_file(host_pwd: str, job_id: str) -> str:
    """Merge the project's root .env file with Redis-based overrides into a
    temporary file, to be used with `docker run --env-file`."""
    base_env_path = os.path.join(host_pwd, '.env')
    with open(base_env_path) as f:
        base_lines = f.readlines()

    # The R pipeline does not call DHIS2: never hand it the DHIS2 URL or token.
    excluded = {"DHIS_URL", "DHIS_TOKEN"}
    overrides = {k: v for k, v in ConfigStore().get_all().items() if k not in excluded}

    # Filter lines from the original .env that will be overridden or excluded
    override_keys = set(overrides.keys()) | excluded
    filtered_base = []
    for line in base_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            key = stripped.split('=')[0].split(';')[0]  # handle KEY=value and KEY;export
            if key not in override_keys:
                filtered_base.append(line)
        else:
            filtered_base.append(line)

    env_path = os.path.join(tempfile.gettempdir(), f"forecast_{job_id}.env")
    with open(env_path, 'w') as f:
        f.writelines(filtered_base)
        if overrides:
            f.write("\n")
            for k, v in overrides.items():
                f.write(f"{k}={v}\n")
    return env_path


def run_rscript(job_id, params, job_store: JobStore):
    status = {
        "status": "running",
        "started": datetime.now().isoformat(),
        "job_id": job_id
    }
    job_store.set(job_id, status)

    host_pwd = get_settings().host_pwd
    env_file = None

    input_vol = f"{host_pwd}/input:/app/input:ro"
    output_vol = f"{host_pwd}/output:/app/output:rw"

    try:
        env_file = _build_dynamic_env_file(host_pwd, job_id)
        # Create output/ ourselves: if it is missing, Docker creates the mount source as root
        # and the container, running as our user, could not write into it.
        os.makedirs(os.path.join(host_pwd, "output"), exist_ok=True)
        cmd = [
            'docker', 'run', '--rm',
            '--env-file', env_file,
            '--network', 'host',
            '--cap-add', 'SYS_NICE',
            *_container_user(),
            '-v', input_vol,
            '-v', output_vol,
            'mvevans89/pridec_forecast:1.0.0',
            'forecast',
            '--config_valid', params['config_valid_path'],
            '--input_valid', params['input_valid_path'],
            '--polygon_valid', params['polygon_valid_path']
        ]
        # R cli/message() output goes to stderr: merge it so the logs keep the order the R run printed.
        # Each line is stored then published as it comes: the log WebSocket follows the run live.
        lines = []
        with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1) as proc:
            for line in proc.stdout:
                lines.append(line)
                job_store.append_logs(job_id, line)  # history first: a client connecting now loses nothing
                try:
                    etl_events.publish_log(job_id, "INFO", line.rstrip("\n"))
                except Exception:
                    pass
        output = "".join(lines)
        completed = datetime.now().isoformat()
        if proc.returncode == 0:
            status.update({
                "status": "success",
                "completed": completed,
                "logs": output
            })
        else:
            status.update({
                "status": "error",
                "completed": completed,
                "logs": output,
                "message": "\n".join(output.splitlines()[-20:])
                           or f"Forecast container exited with code {proc.returncode}"
            })
    except FileNotFoundError as e:
        status.update({
            "status": "error",
            "completed": datetime.now().isoformat(),
            "message": f".env file not found: {e.filename} (check HOST_PWD)"
        })
    except Exception as e:
        status.update({
            "status": "error",
            "completed": datetime.now().isoformat(),
            "message": str(e)
        })
    finally:
        if env_file:
            try:
                os.remove(env_file)
            except OSError:
                pass

    try:
        settings = get_settings()
        logs_dir = Path(settings.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        status_file = logs_dir / f"{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"Warning: Could not write status file: {e}")

    job_store.set(job_id, status)

    if not status.get("logs") and status.get("message"):  # nothing streamed: a failure to start
        job_store.append_logs(job_id, status["message"])
        try:
            etl_events.publish_log(job_id, "ERROR", status["message"])
        except Exception:
            pass

    return status