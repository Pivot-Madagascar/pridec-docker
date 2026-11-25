import sys

from etlhub.core.celery_app import celery_app

if __name__ == "__main__":
    # Extra arguments go to the worker. Without -Q it serves both queues (a single worker: development, e2e);
    # -Q celery and -Q forecast run one worker per queue, only the second one needing Docker.
    args = sys.argv[1:]
    if "-Q" not in args:
        args += ["-Q", "celery,forecast"]
    celery_app.worker_main(["worker", "--loglevel=info", *args])
