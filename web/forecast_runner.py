import subprocess
import os
import json
from pathlib import Path
from datetime import datetime

JOBS = {}  # Global dict to store job statuses in memory
DATA_DIR = Path('.')  # Base directory for data

def run_rscript(job_id, params):
    # Create status directory if it doesn't exist
    status_dir = DATA_DIR / "output" / job_id
    status_dir.mkdir(parents=True, exist_ok=True)
    status_file = status_dir / "status.json"
    
    # Initial status
    status = {
        "status": "running",
        "started": datetime.now().isoformat(),
        "job_id": job_id
    }
    with open(status_file, 'w') as f:
        json.dump(status, f)
    JOBS[job_id] = status
    
    # Get HOST_PWD from environment
    host_pwd = os.getenv('HOST_PWD', '.')
    env_file = os.path.join(host_pwd, '.env')
    
    # Volume bindings
    input_vol = f"{host_pwd}/input:/app/input:ro"
    output_vol = f"{host_pwd}/output:/app/output:rw"
    
    # Docker run command
    cmd = [
        'docker', 'run', '--rm',
        '--env-file', env_file,
        '--network', 'host',
        '--cap-add', 'SYS_NICE',
        '-v', input_vol,
        '-v', output_vol,
        'mvevans89/pridec_forecast:latest',
        '--config', params['config'],
        '--external_data', params['external_data'],
        '--climate_data', params['climate_data'],
        '--disease_data', params['disease_data'],
        '--orgUnit_poly', params['orgUnit_poly']
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
    
    # Update status file and in-memory dict
    with open(status_file, 'w') as f:
        json.dump(status, f)
    JOBS[job_id] = status