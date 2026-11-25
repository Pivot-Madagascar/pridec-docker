import subprocess
import os
import json
import logging
from pathlib import Path
from datetime import datetime

from etlhub.core.config import get_settings
from etlhub.core.job_context import current_test_mode, work_dir
from etlhub.infrastructure.job_store import JobStore
from etlhub.infrastructure import etl_events

logger = logging.getLogger(__name__)

# Pinned by digest: a tag can be pushed again. The tag stays for reading (Docker checks the digest only).
# A new version: `docker buildx imagetools inspect mvevans89/pridec_forecast:<tag>`, the top-level Digest.
FORECAST_IMAGE = ('mvevans89/pridec_forecast:1.1.0'
                  '@sha256:7dcf83ced71bd8f77e1cde82c0c64144f90a33b823318af0eee3e94009f893c8')


def _container_user() -> list[str]:
    """Run the container as the worker's user, not root.

    Files the forecast writes in output/ then belong to the etlhub user, so opening
    the next run can empty output/ without sudo. HOME points to a writable
    directory because the image has no home for that user.
    """
    if os.getuid() == 0:
        return []
    return ['--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp']


def run_rscript(job_id, params, job_store: JobStore):
    status = {
        "status": "running",
        "started": datetime.now().isoformat(),
        "job_id": job_id
    }
    job_store.set(job_id, status)

    host_pwd = get_settings().host_pwd

    # Host side of the mounts: the job's mode (test/input, test/output in test); the container keeps /app/input, /app/output.
    input_dir, output_dir = (work_dir(host_pwd, name, current_test_mode()) for name in ("input", "output"))
    input_vol = f"{input_dir}:/app/input:ro"
    output_vol = f"{output_dir}:/app/output:rw"

    try:
        # Create output/ ourselves: if it is missing, Docker creates the mount source as root
        # and the container, running as our user, could not write into it.
        os.makedirs(output_dir, exist_ok=True)
        # Sandboxed: the R pipeline reads its input files and arguments only (no Sys.getenv in forecast/, no download
        # at run time), so it gets no .env, no network (neither Redis nor the API nor DHIS2), and no capability but
        # SYS_NICE. ponytail: no --memory / --pids-limit until a real run is measured (INLA threads count as pids).
        cmd = [
            'docker', 'run', '--rm',
            '--network', 'none',
            '--cap-drop', 'ALL', '--cap-add', 'SYS_NICE',
            '--security-opt', 'no-new-privileges',
            *_container_user(),
            '-v', input_vol,
            '-v', output_vol,
            FORECAST_IMAGE,
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
                except Exception as e:  # the line is in the history already: a client reconnecting reads it
                    logger.warning("Could not publish a log line of %s: %s", job_id, e)
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
    except Exception as e:
        status.update({
            "status": "error",
            "completed": datetime.now().isoformat(),
            "message": str(e)
        })

    try:
        settings = get_settings()
        logs_dir = Path(settings.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        status_file = logs_dir / f"{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        logger.warning("Could not write the status file of %s: %s", job_id, e)

    job_store.set(job_id, status)

    if not status.get("logs") and status.get("message"):  # nothing streamed: a failure to start
        job_store.append_logs(job_id, status["message"])
        try:
            etl_events.publish_log(job_id, "ERROR", status["message"])
        except Exception as e:
            logger.warning("Could not publish the start failure of %s: %s", job_id, e)

    return status