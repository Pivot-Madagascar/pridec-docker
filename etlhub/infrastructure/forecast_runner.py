import subprocess
import os
import json
import stat
from pathlib import Path
from datetime import datetime

from etlhub.infrastructure.job_store import JobStore


def _get_output_dir() -> str:
    """Get the output directory path."""
    settings = __import__('etlhub.core.config', fromlist=['get_settings']).get_settings()
    return os.path.join(settings.data_dir, "output")


def generate_signature() -> str:
    """Generate a unique signature for this server session."""
    import secrets
    settings = __import__('etlhub.core.config', fromlist=['get_settings']).get_settings()
    sig_file = os.path.join(settings.data_dir, ".output_sig")
    
    sig = secrets.token_hex(32)
    with open(sig_file, 'w') as f:
        f.write(sig)
    
    return sig


def verify_signature() -> bool:
    """Verify that the signature exists and is valid."""
    settings = __import__('etlhub.core.config', fromlist=['get_settings']).get_settings()
    sig_file = os.path.join(settings.data_dir, ".output_sig")
    
    if not os.path.exists(sig_file):
        return False
    
    # If we can read it, we're authorized
    try:
        with open(sig_file, 'r') as f:
            return len(f.read().strip()) > 0
    except Exception:
        return False


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
        'mvevans89/pridec_forecast:0.1.0',
        'forecast',
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

    # Generate signature and chown output directory to allow API deletion
    try:
        generate_signature()
        output_dir = _get_output_dir()
        if os.path.exists(output_dir):
            # Get current user's uid/gid
            uid = os.getuid()
            gid = os.getgid()
            # Recursively chown to current user
            for root, dirs, files in os.walk(output_dir):
                for d in dirs:
                    os.chown(os.path.join(root, d), uid, gid)
                for f in files:
                    os.chown(os.path.join(root, f), uid, gid)
            os.chown(output_dir, uid, gid)
    except Exception as e:
        print(f"Warning: Could not setup output permissions: {e}")

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

    logs = status.get("logs") or status.get("message") or ""
    if logs:
        try:
            job_store.save_logs(job_id, logs)
        except Exception:
            pass
        try:
            from etlhub.api.etl_events import get_etl_event_manager
            get_etl_event_manager().publish_log(job_id, "ERROR" if status.get("status") == "error" else "INFO", logs)
        except Exception:
            pass
        try:
            from etlhub.api.etl_events import get_etl_event_manager
            get_etl_event_manager().publish_status(job_id, status.get("status"), status.get("message"))
        except Exception:
            pass