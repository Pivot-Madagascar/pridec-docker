import subprocess
import os
import json
from pathlib import Path
from datetime import datetime

from etlhub.infrastructure.job_store import JobStore


def run_rscript(job_id, params, job_store: JobStore):
    status = {
        "status": "running",
        "started": datetime.now().isoformat(),
        "job_id": job_id
    }
    job_store.set(job_id, status)

    host_pwd = os.getenv('HOST_PWD', '.')
    env_file = os.path.join(host_pwd, '.env')

    input_vol = f"{host_pwd}/input:/app/input:ro"
    output_vol = f"{host_pwd}/output:/app/output:rw"

    cmd = [
        'docker', 'run', '--rm',
        '--env-file', env_file,
        '--network', 'host',
        '--cap-add', 'SYS_NICE',
        '-v', input_vol,
        '-v', output_vol,
        'mvevans89/pridec_forecast:latest',
        '--config_valid', params['config_valid_path'],
        '--input_valid', params['input_valid_path'],
        '--polygon_valid', params['polygon_valid_path']
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        completed = datetime.now().isoformat()
        if result.returncode == 0:
            status.update({
                "status": "success",
                "completed": completed,
                "logs": result.stdout
            })
        else:
            status.update({
                "status": "error",
                "completed": completed,
                "logs": result.stdout,
                "message": result.stderr
            })
    except Exception as e:
        status.update({
            "status": "error",
            "completed": datetime.now().isoformat(),
            "message": str(e)
        })

    try:
        settings = __import__('etlhub.core.config', fromlist=['get_settings']).get_settings()
        logs_dir = Path(settings.logs_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        status_file = logs_dir / f"{job_id}.json"
        with open(status_file, 'w') as f:
            json.dump(status, f)
    except Exception as e:
        print(f"Warning: Could not write status file: {e}")

    job_store.set(job_id, status)
